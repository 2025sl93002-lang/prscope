"""Scan orchestration: the SCAN stage of DepLens.

Ties the parsers, graph engine and analyzers together into a single scan, runs
each stage with honest success/partial/failed/skipped status, computes the
health score, and persists everything to SQLite. Nothing here executes project
code; the only outbound calls are opt-in registry/OSV metadata lookups.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from deplens.analyzers import health, licenses, maintenance, usage, versions
from deplens.db import Database
from deplens.parsers import parse_lockfile_text, parse_manifest_text
from deplens.parsers.lockfile import ROOT_ID
from deplens.services.graph import build_graph
from deplens.services.osv import SEVERITY_ORDER, OSVClient
from deplens.services.registry import RegistryClient
from deplens.services.safety import resolve_project_root

MANIFEST = "package.json"
LOCKFILES = ["package-lock.json", "npm-shrinkwrap.json"]


class ScanError(Exception):
    """Raised when a scan cannot start (e.g. no manifest found)."""


@dataclass
class Stage:
    key: str
    label: str
    status: str = "pending"  # pending | ok | partial | skipped | failed
    detail: str = ""
    duration_ms: int = 0


@dataclass
class ScanContext:
    path: str
    online: bool
    stages: List[Stage] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def stage(self, key: str, label: str) -> Stage:
        s = Stage(key=key, label=label)
        self.stages.append(s)
        return s


def _primary_scope(scopes: List[str]) -> str:
    for s in ("prod", "optional", "peer", "dev"):
        if s in scopes:
            return s
    return "prod"


async def run_scan(db: Database, path: str, online: bool = True) -> int:
    """Run a full scan of the npm project at ``path`` and persist it.

    Returns the new scan id.
    """
    ctx = ScanContext(path=path, online=online)
    started = time.time()

    # Stage 1 — discover project ------------------------------------------------
    st = ctx.stage("discover", "Discovering project")
    t0 = time.time()
    root = resolve_project_root(path)
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        st.status = "failed"
        st.detail = "No package.json found in the selected directory."
        raise ScanError(st.detail)
    lock_path = None
    for lf in LOCKFILES:
        if (root / lf).is_file():
            lock_path = root / lf
            break
    st.status = "ok"
    st.detail = f"Found {MANIFEST}" + (f" and {lock_path.name}" if lock_path else "")
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 2 — read manifests --------------------------------------------------
    st = ctx.stage("manifest", "Reading manifests")
    t0 = time.time()
    manifest = parse_manifest_text(manifest_path.read_text(encoding="utf-8", errors="replace"))
    ctx.warnings.extend(manifest.warnings)
    project_name = manifest.name or root.name
    st.status = "ok"
    st.detail = f"{len(manifest.declared())} declared dependencies"
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 3 — resolve dependency graph ---------------------------------------
    st = ctx.stage("resolve", "Resolving dependency graph")
    t0 = time.time()
    if lock_path is None:
        st.status = "partial"
        st.detail = (
            "No lockfile found. Only direct dependencies from package.json are available; "
            "the transitive graph cannot be resolved without a lockfile."
        )
        lockfile = _manifest_only_lockfile(manifest)
    else:
        try:
            lockfile = parse_lockfile_text(lock_path.read_text(encoding="utf-8", errors="replace"))
            ctx.warnings.extend(lockfile.warnings)
            st.status = "ok" if not lockfile.warnings else "partial"
            st.detail = (
                f"{len(lockfile.packages)} packages, {len(lockfile.edges)} edges "
                f"(lockfile {lockfile.fmt})"
            )
        except ValueError as exc:
            st.status = "failed"
            st.detail = str(exc)
            lockfile = _manifest_only_lockfile(manifest)
    graph = build_graph(lockfile)
    st.duration_ms = int((time.time() - t0) * 1000)

    package_names = sorted({p.name for p in lockfile.packages.values()})

    # Stage 4 — registry metadata (updates / license / maintenance) ------------
    registry_info: Dict[str, Any] = {}
    registry_ratio = 0.0
    st = ctx.stage("registry", "Analyzing versions & metadata")
    t0 = time.time()
    if online and package_names:
        try:
            async with RegistryClient() as reg:
                registry_info = await reg.get_many(package_names)
            available = sum(1 for i in registry_info.values() if i.available)
            registry_ratio = available / len(package_names) if package_names else 0.0
            st.status = "ok" if registry_ratio >= 0.95 else "partial"
            st.detail = f"Fetched metadata for {available}/{len(package_names)} packages"
        except Exception as exc:  # network / unexpected
            st.status = "failed"
            st.detail = f"Registry unavailable: {exc}"
    else:
        st.status = "skipped"
        st.detail = "Offline mode — update, license and maintenance data not fetched."
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 5 — security advisories (OSV) --------------------------------------
    vulns_by_pkg: Dict[str, list] = {}
    security_checked = False
    st = ctx.stage("security", "Checking security advisories")
    t0 = time.time()
    if online and lockfile.packages:
        try:
            query = [(p.name, p.version) for p in lockfile.packages.values()]
            async with OSVClient() as osv:
                vulns_by_pkg = await osv.query_packages(query)
            security_checked = True
            total_vulns = sum(len(v) for v in vulns_by_pkg.values())
            st.status = "ok"
            st.detail = f"{total_vulns} advisories across {len(vulns_by_pkg)} package(s)"
        except Exception as exc:
            st.status = "failed"
            st.detail = f"OSV unavailable: {exc}. Security status is UNKNOWN, not secure."
    else:
        st.status = "skipped"
        st.detail = "Offline mode — security not checked. Status is UNKNOWN, not secure."
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 6 — license analysis ------------------------------------------------
    st = ctx.stage("license", "Analyzing licenses")
    t0 = time.time()
    policy = db.get_setting("license_policy", None)
    license_results = {}
    for name in package_names:
        info = registry_info.get(name)
        raw = info.license if info else None
        license_results[name] = licenses.evaluate_license(name, raw, policy)
    st.status = "ok" if online else "partial"
    st.detail = f"Classified {len(license_results)} package licenses"
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 7 — usage analysis (offline, local source) -------------------------
    st = ctx.stage("usage", "Checking package usage")
    t0 = time.time()
    try:
        usage_results = usage.analyze_usage(root, manifest)
        st.status = "ok"
        st.detail = f"Analyzed usage of {len(usage_results)} direct dependencies"
    except Exception as exc:
        usage_results = {}
        st.status = "failed"
        st.detail = f"Usage analysis failed: {exc}"
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 8 — build findings & health ----------------------------------------
    st = ctx.stage("findings", "Generating health findings")
    t0 = time.time()
    maint_results = {
        name: maintenance.analyze_maintenance(name, registry_info.get(name))
        for name in package_names
    }
    update_results = {
        name: versions.analyze_update(
            name,
            _version_of(name, lockfile),
            registry_info.get(name),
        )
        for name in package_names
    }

    vuln_severity_counts: Counter = Counter()
    for vlist in vulns_by_pkg.values():
        for v in vlist:
            vuln_severity_counts[v.severity] += 1
    outdated_counts: Counter = Counter()
    for _name, u in update_results.items():
        if u.is_outdated and u.update_type in ("major", "minor", "patch"):
            outdated_counts[u.update_type] += 1
    license_counts: Counter = Counter()
    for lr in license_results.values():
        if lr.verdict == "restricted":
            license_counts["restricted"] += 1
        elif lr.verdict == "review":
            license_counts["review" if lr.family != "unknown" else "unknown"] += 1
    unused_count = sum(1 for u in usage_results.values() if u.status == "none")
    maintenance_count = sum(
        1 for m in maint_results.values() if m.status in ("concerns", "deprecated")
    )

    health_score = health.compute_health(
        vuln_counts=dict(vuln_severity_counts),
        outdated_counts=dict(outdated_counts),
        license_counts=dict(license_counts),
        unused_count=unused_count,
        maintenance_count=maintenance_count,
        security_checked=security_checked,
        registry_available_ratio=registry_ratio if online else 0.0,
    )
    st.status = "ok"
    st.detail = f"Health score {health_score.score} ({health_score.grade})"
    st.duration_ms = int((time.time() - t0) * 1000)

    # Stage 9 — persist ---------------------------------------------------------
    st = ctx.stage("persist", "Preparing report")
    t0 = time.time()
    for name, info in registry_info.items():
        if info and info.description:
            _DESC_CACHE[name] = info.description
    summary = _build_summary(
        graph, lockfile, vulns_by_pkg, update_results, license_results, usage_results,
        maint_results, vuln_severity_counts,
    )
    project_id = db.upsert_project(project_name, str(root), "npm")
    scan_id = _persist(
        db, project_id, ctx, lockfile, graph, vulns_by_pkg, update_results,
        license_results, usage_results, maint_results, health_score, summary,
    )
    st.status = "ok"
    st.detail = f"Saved scan #{scan_id}"
    st.duration_ms = int((time.time() - t0) * 1000)

    ctx.warnings.append(f"Scan completed in {int((time.time() - started) * 1000)} ms")
    # Re-save the finalized stages/warnings (the persist stage finalizes after
    # the initial row is written, so update it now).
    db.execute(
        "UPDATE scans SET stages_json=?, warnings_json=? WHERE id=?",
        (
            json.dumps([asdict(s) for s in ctx.stages]),
            json.dumps(ctx.warnings),
            scan_id,
        ),
    )
    return scan_id


def _version_of(name: str, lockfile) -> str:
    for p in lockfile.packages.values():
        if p.name == name:
            return p.version
    return "0.0.0"


def _manifest_only_lockfile(manifest):
    """Build a minimal lockfile from the manifest alone (no transitive data)."""
    from deplens.parsers.lockfile import LockEdge, Lockfile, LockPackage

    packages = {}
    edges = []
    direct = {}
    for dep in manifest.declared().values():
        # Without a lockfile we do not know the resolved version.
        node = LockPackage(name=dep.name, version="unknown", scopes={dep.scope}, is_direct=True)
        packages[node.id] = node
        edges.append(LockEdge(ROOT_ID, node.id, dep.spec, dep.scope))
        direct[dep.name] = dep.scope
    return Lockfile(
        lockfile_version=0, fmt="manifest-only", root_name=manifest.name,
        root_version=manifest.version, packages=packages, edges=edges, direct=direct,
        warnings=["No lockfile: resolved versions and transitive dependencies are unavailable."],
    )


def _build_summary(
    graph, lockfile, vulns_by_pkg, update_results, license_results, usage_results,
    maint_results, vuln_severity_counts,
) -> Dict[str, Any]:
    total = len(lockfile.packages)
    direct = len(graph.direct_ids())
    scope_counts: Counter = Counter()
    for p in lockfile.packages.values():
        scope_counts[_primary_scope(sorted(p.scopes))] += 1
    update_dist: Counter = Counter(u.update_type for u in update_results.values())
    license_family_dist: Counter = Counter(lr.family for lr in license_results.values())
    vulnerable_packages = len([k for k, v in vulns_by_pkg.items() if v])
    return {
        "total": total,
        "direct": direct,
        "transitive": total - direct,
        "scope_distribution": dict(scope_counts),
        "outdated": sum(1 for u in update_results.values() if u.is_outdated),
        "update_distribution": dict(update_dist),
        "vulnerable_packages": vulnerable_packages,
        "severity_distribution": dict(vuln_severity_counts),
        "license_distribution": dict(license_family_dist),
        "unknown_licenses": sum(1 for lr in license_results.values() if lr.family == "unknown"),
        "license_warnings": sum(
            1 for lr in license_results.values() if lr.verdict in ("review", "restricted")
        ),
        "potentially_unused": sum(1 for u in usage_results.values() if u.status == "none"),
        "maintenance_concerns": sum(
            1 for m in maint_results.values() if m.status in ("concerns", "deprecated")
        ),
    }


def _persist(
    db, project_id, ctx, lockfile, graph, vulns_by_pkg, update_results,
    license_results, usage_results, maint_results, health_score, summary,
) -> int:
    cur = db.execute(
        "INSERT INTO scans(project_id, created_at, status, online, lockfile_format, "
        "root_name, root_version, health_score, health_grade, health_confidence, "
        "summary_json, stages_json, warnings_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            project_id, time.time(), "completed", int(ctx.online), lockfile.fmt,
            lockfile.root_name, lockfile.root_version, health_score.score,
            health_score.grade, health_score.confidence,
            json.dumps({**summary, "health": asdict(health_score)}),
            json.dumps([asdict(s) for s in ctx.stages]),
            json.dumps(ctx.warnings),
        ),
    )
    scan_id = cur.lastrowid

    pkg_rows = []
    for node in graph.nodes.values():
        name = node.name
        u = update_results.get(name)
        lr = license_results.get(name)
        mr = maint_results.get(name)
        ur = usage_results.get(name) if node.is_direct else None
        pkg_vulns = vulns_by_pkg.get(node.id, [])
        max_sev = _max_severity([v.severity for v in pkg_vulns])
        data = {
            "update": asdict(u) if u else None,
            "license": asdict(lr) if lr else None,
            "maintenance": asdict(mr) if mr else None,
            "usage": _usage_to_dict(ur) if ur else None,
            "scopes": node.scopes,
            "description": _desc(name),
        }
        pkg_rows.append(
            (
                scan_id, node.id, name, node.version, int(node.is_direct),
                _primary_scope(node.scopes), node.depth, node.dependents, node.path_count,
                u.update_type if u else None, u.latest if u else None,
                lr.license if lr else None, lr.family if lr else None,
                lr.verdict if lr else None,
                ur.status if ur else None, mr.status if mr else None,
                max_sev, len(pkg_vulns), json.dumps(data),
            )
        )
    db.executemany(
        "INSERT INTO packages(scan_id, node_id, name, version, is_direct, scope, depth, "
        "dependents, path_count, update_type, latest, license, license_family, "
        "license_verdict, usage_status, maintenance_status, max_severity, vuln_count, data_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        pkg_rows,
    )

    db.executemany(
        "INSERT INTO edges(scan_id, source, target, edge_type, spec) VALUES (?,?,?,?,?)",
        [(scan_id, e.source, e.target, e.edge_type, e.spec) for e in lockfile.edges],
    )

    vuln_rows = []
    for vlist in vulns_by_pkg.values():
        for v in vlist:
            url = v.references[0] if v.references else f"https://osv.dev/vulnerability/{v.id}"
            vuln_rows.append(
                (
                    scan_id, v.package, v.installed_version, v.id, v.cve, v.severity,
                    v.summary, v.fixed_version, url, v.published, json.dumps(asdict(v)),
                )
            )
    if vuln_rows:
        db.executemany(
            "INSERT INTO vulnerabilities(scan_id, package, installed_version, osv_id, cve, "
            "severity, summary, fixed_version, url, published, data_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            vuln_rows,
        )
    return scan_id


def _usage_to_dict(ur) -> dict:
    return {
        "package": ur.package,
        "status": ur.status,
        "confidence": ur.confidence,
        "explanation": ur.explanation,
        "evidence": [asdict(e) for e in ur.evidence],
    }


def _max_severity(sevs: List[str]) -> Optional[str]:
    best = None
    best_rank = -1
    for s in sevs:
        rank = SEVERITY_ORDER.get(s, 0)
        if rank > best_rank:
            best_rank = rank
            best = s
    return best


_DESC_CACHE: Dict[str, str] = {}


def _desc(name: str) -> Optional[str]:
    return _DESC_CACHE.get(name)
