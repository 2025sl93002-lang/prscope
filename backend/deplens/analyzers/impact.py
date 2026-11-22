"""Dependency impact simulator.

Given a persisted scan, simulate a decision about one package — upgrade, remove,
or replace — and produce explainable, evidence-labelled findings. Everything is
computed from the resolved lockfile graph, the declared version ranges, usage
evidence and known advisories. The simulator never claims to *prove*
compatibility; it surfaces what can be inferred and what must be verified.

Every finding carries an evidence class:
  * ``lockfile``   — grounded in the resolved lockfile/manifest (high confidence)
  * ``static``     — inferred from static source analysis
  * ``potential``  — a plausible impact that needs verification
  * ``unknown``    — data was unavailable
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import networkx as nx

from deplens import semver
from deplens.db import Database
from deplens.parsers.lockfile import ROOT_ID

LOCKFILE = "lockfile"
STATIC = "static"
POTENTIAL = "potential"
UNKNOWN = "unknown"


@dataclass
class Finding:
    kind: str  # breaking | constraint-conflict | dependents | usage | security | tree | license
    severity: str  # info | warning | critical
    evidence: str  # one of the evidence classes above
    message: str
    detail: Optional[str] = None


@dataclass
class ImpactReport:
    package: str
    current_version: Optional[str]
    action: str
    proposed_version: Optional[str]
    alternative: Optional[str]
    summary: str
    dependency_paths: List[List[str]] = field(default_factory=list)
    affected_packages: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


@dataclass
class _Loaded:
    graph: nx.DiGraph
    versions: Dict[str, str]  # name -> installed version (first match)
    node_ids: Dict[str, List[str]]  # name -> [node ids]
    specs: Dict[tuple, str]  # (source, target) -> declared spec
    data: Dict[str, dict]  # node_id -> data_json
    direct: Dict[str, bool]  # name -> is_direct
    vulns: Dict[str, List[dict]]  # name -> vuln dicts


def _load(db: Database, scan_id: int) -> _Loaded:
    g = nx.DiGraph()
    g.add_node(ROOT_ID)
    versions: Dict[str, str] = {}
    node_ids: Dict[str, List[str]] = {}
    data: Dict[str, dict] = {}
    direct: Dict[str, bool] = {}
    for row in db.query("SELECT * FROM packages WHERE scan_id=?", (scan_id,)):
        g.add_node(row["node_id"], name=row["name"], version=row["version"])
        versions.setdefault(row["name"], row["version"])
        node_ids.setdefault(row["name"], []).append(row["node_id"])
        direct[row["name"]] = bool(row["is_direct"])
        try:
            data[row["node_id"]] = json.loads(row["data_json"]) if row["data_json"] else {}
        except (ValueError, TypeError):
            data[row["node_id"]] = {}
    specs: Dict[tuple, str] = {}
    for e in db.query("SELECT * FROM edges WHERE scan_id=?", (scan_id,)):
        if e["source"] in g and e["target"] in g:
            g.add_edge(e["source"], e["target"], spec=e["spec"], edge_type=e["edge_type"])
            specs[(e["source"], e["target"])] = e["spec"]
    vulns: Dict[str, List[dict]] = {}
    for v in db.query("SELECT * FROM vulnerabilities WHERE scan_id=?", (scan_id,)):
        try:
            vulns.setdefault(v["package"], []).append(json.loads(v["data_json"]))
        except (ValueError, TypeError):
            pass
    return _Loaded(g, versions, node_ids, specs, data, direct, vulns)


def _paths_to(loaded: _Loaded, node_id: str, limit: int = 15) -> List[List[str]]:
    if node_id not in loaded.graph:
        return []
    out: List[List[str]] = []
    try:
        for p in nx.all_simple_paths(loaded.graph, ROOT_ID, node_id, cutoff=40):
            out.append(p)
            if len(out) >= limit:
                break
    except (nx.NodeNotFound, nx.NetworkXNoPath):
        pass
    return out


def simulate(
    db: Database,
    scan_id: int,
    package: str,
    action: str,
    proposed_version: Optional[str] = None,
    alternative: Optional[str] = None,
    alternative_info: Optional[dict] = None,
) -> ImpactReport:
    loaded = _load(db, scan_id)
    if package not in loaded.node_ids:
        raise ValueError(f"Package {package!r} is not present in scan #{scan_id}")

    current = loaded.versions.get(package)
    report = ImpactReport(
        package=package,
        current_version=current,
        action=action,
        proposed_version=proposed_version,
        alternative=alternative,
        summary="",
    )
    node_ids = loaded.node_ids[package]
    # Dependency paths and dependents (shared across actions).
    for nid in node_ids:
        report.dependency_paths.extend(_paths_to(loaded, nid))
    report.dependency_paths = report.dependency_paths[:15]

    dependents = set()
    for nid in node_ids:
        dependents.update(p for p in loaded.graph.predecessors(nid) if p != ROOT_ID)
    report.affected_packages = sorted(dependents)

    if action == "upgrade":
        _simulate_upgrade(loaded, report, package, current, proposed_version, dependents, node_ids)
    elif action == "remove":
        _simulate_remove(loaded, report, package, node_ids)
    elif action == "replace":
        _simulate_replace(loaded, report, package, alternative, alternative_info, node_ids)
    elif action == "keep":
        _simulate_keep(loaded, report, package)
    else:
        raise ValueError(f"Unknown action: {action!r}")
    return report


def _usage_files(loaded: _Loaded, node_ids: List[str]) -> List[str]:
    files = []
    for nid in node_ids:
        usage = (loaded.data.get(nid) or {}).get("usage")
        if usage:
            files.extend(e["file"] for e in usage.get("evidence", []) if e.get("file"))
    return sorted(set(files))


def _simulate_upgrade(loaded, report, package, current, proposed, dependents, node_ids):
    if not proposed:
        raise ValueError("An upgrade simulation requires a proposed version.")
    report.affected_files = _usage_files(loaded, node_ids)

    # Breaking-change classification from semver.
    change = None
    if current:
        try:
            change = semver.diff(current, proposed)
        except semver.InvalidVersion:
            change = None
    if change == "major":
        report.findings.append(
            Finding(
                "breaking", "warning", LOCKFILE,
                f"{current} → {proposed} is a MAJOR version change — potentially breaking.",
                "Review the package's migration notes and changelog before upgrading.",
            )
        )
    elif change in ("minor", "patch"):
        report.findings.append(
            Finding(
                "breaking", "info", LOCKFILE,
                f"{current} → {proposed} is a {change} change — expected backward compatible.",
            )
        )

    # Version-constraint conflicts: does the proposed version satisfy the ranges
    # that each dependent declared for this package?
    conflicts = 0
    for dep_node in dependents:
        for nid in node_ids:
            spec = loaded.specs.get((dep_node, nid))
            if not spec:
                continue
            try:
                ok = semver.satisfies(proposed, spec)
            except semver.InvalidRange:
                ok = True  # non-semver spec (git/url) — cannot judge
            if not ok:
                conflicts += 1
                dep_name = loaded.graph.nodes[dep_node].get("name", dep_node)
                report.findings.append(
                    Finding(
                        "constraint-conflict", "warning", LOCKFILE,
                        f"{dep_name} requires '{spec}', which {proposed} does not satisfy.",
                        "That dependent may need its own update, or may refuse the new version.",
                    )
                )
    if dependents and conflicts == 0:
        report.findings.append(
            Finding(
                "dependents", "info", LOCKFILE,
                f"{len(dependents)} package(s) depend on {package}; all declared ranges "
                f"accept {proposed}.",
            )
        )

    # Security implications: which current advisories would this upgrade resolve?
    resolved, unresolved = _security_delta(loaded, package, proposed)
    if resolved:
        report.findings.append(
            Finding(
                "security", "info", LOCKFILE,
                f"Upgrading to {proposed} resolves {len(resolved)} known advisory(ies): "
                + ", ".join(resolved[:6]),
            )
        )
    if unresolved:
        report.findings.append(
            Finding(
                "security", "warning", LOCKFILE,
                f"{len(unresolved)} advisory(ies) would remain at {proposed}: "
                + ", ".join(unresolved[:6]),
            )
        )

    if report.affected_files:
        report.findings.append(
            Finding(
                "usage", "info", STATIC,
                f"{package} is imported in {len(report.affected_files)} source file(s) that "
                "should be re-tested after upgrading.",
                detail="; ".join(report.affected_files[:10]),
            )
        )

    report.summary = (
        f"Upgrading {package} {current} → {proposed}: "
        f"{'MAJOR (possibly breaking), ' if change == 'major' else ''}"
        f"{conflicts} constraint conflict(s), "
        f"{len(resolved)} advisory(ies) resolved, "
        f"{len(report.affected_files)} source file(s) to re-test."
    )
    report.verification = _upgrade_checklist(package, current, proposed, change, resolved)
    report.limitations = [
        "Compatibility is inferred from declared version ranges and static usage, not proven.",
        "Runtime behaviour, type changes and transitive peer requirements are not fully modelled.",
    ]
    if change is None:
        report.limitations.append(
            "The current or proposed version is not standard semver; change type is UNKNOWN."
        )


def _simulate_remove(loaded, report, package, node_ids):
    report.affected_files = _usage_files(loaded, node_ids)
    is_direct = loaded.direct.get(package, False)

    # Who else depends on it (besides the root)?
    non_root_dependents = report.affected_packages
    if non_root_dependents:
        report.findings.append(
            Finding(
                "dependents", "warning", LOCKFILE,
                f"{len(non_root_dependents)} other package(s) depend on {package}: "
                + ", ".join(loaded.graph.nodes[d].get("name", d) for d in non_root_dependents[:8]),
                "Removing it from package.json will not uninstall it while these remain.",
            )
        )

    if report.affected_files:
        report.findings.append(
            Finding(
                "usage", "critical", STATIC,
                f"{package} is imported in {len(report.affected_files)} source file(s). "
                "Removing it will break those imports until the code is changed.",
                detail="; ".join(report.affected_files[:10]),
            )
        )
    elif is_direct:
        report.findings.append(
            Finding(
                "usage", "info", STATIC,
                "No direct import of this package was found in project source. Removal may be "
                "safe, but verify dynamic/plugin usage first.",
            )
        )

    # Orphaned subtree: descendants reachable ONLY through this package.
    orphans = _would_be_orphaned(loaded, node_ids)
    if orphans:
        report.findings.append(
            Finding(
                "tree", "info", LOCKFILE,
                f"Removing {package} would also prune {len(orphans)} transitive package(s) "
                "that are only reachable through it.",
                detail="; ".join(sorted(orphans)[:12]),
            )
        )

    safe = not report.affected_files and not non_root_dependents
    report.summary = (
        f"Removing {package}: "
        + ("no source usage and no other dependents — likely safe to remove. "
           if safe else "has usage or dependents — review carefully. ")
        + f"{len(orphans)} transitive package(s) would be pruned."
    )
    report.verification = [
        f"Confirm no remaining import/require of '{package}' (including dynamic imports).",
        "Search configuration files and scripts for the package name.",
        "Run the full build.",
        "Run unit and integration tests.",
        "Run lint.",
        "Re-scan the dependency graph after removal to confirm the tree is as expected.",
    ]
    report.limitations = [
        "Dynamic requires, plugin systems and framework conventions may use the package "
        "without a static import; absence of evidence is not proof of non-use.",
    ]


def _simulate_replace(loaded, report, package, alternative, alternative_info, node_ids):
    if not alternative:
        raise ValueError("A replace simulation requires an alternative package name.")
    report.affected_files = _usage_files(loaded, node_ids)
    report.findings.append(
        Finding(
            "usage", "warning", STATIC,
            f"{len(report.affected_files)} source file(s) import {package} and would need to be "
            f"rewritten to use {alternative}.",
            detail="; ".join(report.affected_files[:10]) or "No direct imports found.",
        )
    )
    # Compare metadata when provided (fetched online by the API layer).
    cur_license = None
    for nid in node_ids:
        lic = (loaded.data.get(nid) or {}).get("license")
        if lic:
            cur_license = lic.get("license")
            break
    if alternative_info:
        alt_license = alternative_info.get("license")
        report.findings.append(
            Finding(
                "license", "info", LOCKFILE if alt_license else UNKNOWN,
                f"License: {package}={cur_license or 'unknown'} vs {alternative}="
                f"{alt_license or 'unknown'}.",
            )
        )
        if alternative_info.get("latest"):
            report.findings.append(
                Finding(
                    "dependents", "info", LOCKFILE,
                    f"{alternative} latest version is {alternative_info['latest']}; "
                    f"last publish {alternative_info.get('modified', 'unknown')}.",
                )
            )
        if alternative_info.get("deprecated"):
            report.findings.append(
                Finding(
                    "dependents", "warning", LOCKFILE,
                    f"{alternative} is marked deprecated — not a good replacement.",
                )
            )
    else:
        report.limitations.append(
            "No registry metadata for the alternative was provided (offline); license, "
            "maintenance and security of the alternative were not compared."
        )

    report.summary = (
        f"Replacing {package} with {alternative}: {len(report.affected_files)} source file(s) "
        "to rewrite. Review API differences, license and maintenance before committing."
    )
    report.verification = [
        f"Map the {package} API surface used in the project to {alternative} equivalents.",
        f"Rewrite the {len(report.affected_files)} affected source file(s).",
        f"Review {alternative}'s license against the project policy.",
        f"Check {alternative} for known advisories at the version you would install.",
        "Run the full test suite and build.",
    ]


def _simulate_keep(loaded, report, package):
    nid = loaded.node_ids[package][0]
    data = loaded.data.get(nid, {})
    update = data.get("update") or {}
    vulns = loaded.vulns.get(package, [])
    if vulns:
        report.findings.append(
            Finding(
                "security", "warning", LOCKFILE,
                f"Keeping {package} {report.current_version} retains {len(vulns)} known "
                "advisory(ies).",
            )
        )
    if update.get("is_outdated"):
        report.findings.append(
            Finding(
                "breaking", "info", LOCKFILE,
                f"A {update.get('update_type')} update is available but will not be applied.",
            )
        )
    report.summary = (
        f"Keeping {package} {report.current_version} as-is. "
        + (f"{len(vulns)} advisory(ies) remain. " if vulns else "No known advisories. ")
    )
    report.verification = [
        "Record the rationale for keeping the current version.",
        "Set a reminder to re-evaluate after the next scan.",
    ]


def _security_delta(loaded, package, proposed):
    """Split current advisories into those fixed by ``proposed`` and those not."""
    resolved, unresolved = [], []
    for v in loaded.vulns.get(package, []):
        fixed = v.get("fixed_version")
        label = v.get("cve") or v.get("id")
        if fixed:
            try:
                if semver.compare(proposed, fixed) >= 0:
                    resolved.append(label)
                else:
                    unresolved.append(label)
            except semver.InvalidVersion:
                unresolved.append(label)
        else:
            unresolved.append(label)
    return resolved, unresolved


def _would_be_orphaned(loaded, node_ids) -> set:
    """Descendants that become unreachable from root if node_ids are removed."""
    g = loaded.graph
    targets = set(node_ids)
    # Descendants of the removed nodes.
    descendants = set()
    for nid in node_ids:
        descendants.update(nx.descendants(g, nid))
    descendants -= targets
    if not descendants:
        return set()
    # Build a graph without the removed nodes and see what's still reachable.
    h = g.copy()
    h.remove_nodes_from(targets)
    if ROOT_ID not in h:
        return set()
    reachable = set(nx.descendants(h, ROOT_ID))
    orphaned = {
        g.nodes[d].get("name", d) for d in descendants if d not in reachable
    }
    return orphaned


def _upgrade_checklist(package, current, proposed, change, resolved):
    tasks = [
        f"Review the release notes / changelog for {package} between {current} and {proposed}.",
    ]
    if change == "major":
        tasks.append("Review the major-version migration guide for breaking changes.")
    tasks += [
        "Confirm compatibility with the current framework/runtime version.",
        "Run unit tests.",
        "Run integration tests.",
        "Run the build.",
        "Run lint.",
    ]
    if resolved:
        tasks.append("Confirm the previously-reported advisories are resolved after the upgrade.")
    tasks += [
        "Confirm the license is unchanged and still policy-compliant.",
        "Re-scan the dependency graph and review new transitive dependencies.",
    ]
    return tasks


def report_to_dict(report: ImpactReport) -> dict:
    d = asdict(report)
    return d
