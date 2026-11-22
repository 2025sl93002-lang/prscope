"""Remediation planner.

Turns the flat list of advisories into an actionable, ranked upgrade plan:
for each vulnerable package, the single version to upgrade to that clears the
most advisories, the risk of that upgrade (patch/minor/major via semver), and —
crucially — whether it can be fixed directly (bump package.json) or only via a
parent update / npm ``overrides`` because the package is transitive.

Everything is computed from data already captured by the scan (advisories with
fixed versions, the resolved graph). No network, no AI, no new data sources.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import networkx as nx

from deplens import semver
from deplens.db import Database
from deplens.parsers.lockfile import ROOT_ID
from deplens.services.osv import SEVERITY_ORDER


@dataclass
class ClearedAdvisory:
    id: str
    cve: Optional[str]
    severity: str
    fixed_version: Optional[str]


@dataclass
class RemediationAction:
    package: str
    current_version: str
    target_version: Optional[str]
    update_type: Optional[str]  # patch | minor | major | prerelease | None
    strategy: str  # "direct" | "transitive" | "no-fix"
    is_direct: bool
    via_direct: List[str]  # direct dependencies whose subtree contains this package
    cleared: List[ClearedAdvisory]
    unfixable: List[ClearedAdvisory]
    max_severity_cleared: str
    quick_win: bool  # low-risk upgrade (patch/minor) that clears a high/critical advisory


@dataclass
class RemediationPlan:
    actions: List[RemediationAction] = field(default_factory=list)
    total_advisories: int = 0
    fixable_advisories: int = 0
    unfixable_advisories: int = 0
    packages_to_upgrade: int = 0
    quick_wins: int = 0
    summary: str = ""


def _severity_rank(sev: str) -> int:
    return SEVERITY_ORDER.get(sev, 0)


def plan_remediation(db: Database, scan_id: int) -> RemediationPlan:
    vulns = [dict(v) for v in db.query(
        "SELECT * FROM vulnerabilities WHERE scan_id=?", (scan_id,)
    )]
    plan = RemediationPlan()
    if not vulns:
        plan.summary = "No advisories — nothing to remediate."
        return plan

    # direct flags + resolved graph for transitive attribution.
    direct_flag: Dict[str, bool] = {}
    name_of: Dict[str, str] = {}
    first_node: Dict[str, str] = {}
    g = nx.DiGraph()
    g.add_node(ROOT_ID)
    for r in db.query("SELECT node_id, name, is_direct FROM packages WHERE scan_id=?", (scan_id,)):
        g.add_node(r["node_id"])
        name_of[r["node_id"]] = r["name"]
        direct_flag[r["name"]] = direct_flag.get(r["name"], False) or bool(r["is_direct"])
        first_node.setdefault(r["name"], r["node_id"])
    for e in db.query("SELECT source, target FROM edges WHERE scan_id=?", (scan_id,)):
        if e["source"] in g and e["target"] in g:
            g.add_edge(e["source"], e["target"])

    direct_children = {
        name_of[t] for _s, t in g.out_edges(ROOT_ID) if t in name_of
    }

    # Group advisories by package.
    by_pkg: Dict[str, List[dict]] = {}
    for v in vulns:
        by_pkg.setdefault(v["package"], []).append(v)

    plan.total_advisories = len(vulns)

    for pkg, advisories in by_pkg.items():
        installed = advisories[0]["installed_version"]
        fixed_versions = [a["fixed_version"] for a in advisories if a["fixed_version"]]
        cleared: List[ClearedAdvisory] = []
        unfixable: List[ClearedAdvisory] = []
        target: Optional[str] = None
        if fixed_versions:
            # The highest fixed version clears every fixable advisory for this package.
            target = max(fixed_versions, key=_version_key)

        for a in advisories:
            entry = ClearedAdvisory(a["osv_id"], a["cve"], a["severity"], a["fixed_version"])
            if a["fixed_version"] and target and _le(a["fixed_version"], target):
                cleared.append(entry)
            else:
                unfixable.append(entry)

        update_type = None
        if target:
            try:
                update_type = semver.diff(installed, target)
            except semver.InvalidVersion:
                update_type = None

        is_direct = direct_flag.get(pkg, False)
        via_direct: List[str] = []
        if not is_direct:
            node = first_node.get(pkg)
            if node:
                ancestors = nx.ancestors(g, node)
                via_direct = sorted({
                    name_of[a] for a in ancestors if name_of.get(a) in direct_children
                })

        if not target:
            strategy = "no-fix"
        elif is_direct:
            strategy = "direct"
        else:
            strategy = "transitive"

        max_sev = "unknown"
        for c in cleared:
            if _severity_rank(c.severity) > _severity_rank(max_sev):
                max_sev = c.severity
        quick_win = (
            update_type in ("patch", "minor")
            and _severity_rank(max_sev) >= _severity_rank("high")
        )

        plan.actions.append(
            RemediationAction(
                package=pkg,
                current_version=installed,
                target_version=target,
                update_type=update_type,
                strategy=strategy,
                is_direct=is_direct,
                via_direct=via_direct,
                cleared=cleared,
                unfixable=unfixable,
                max_severity_cleared=max_sev,
                quick_win=quick_win,
            )
        )
        plan.fixable_advisories += len(cleared)
        plan.unfixable_advisories += len(unfixable)

    # Rank: most severe first, then most advisories cleared, quick wins ahead of ties.
    plan.actions.sort(
        key=lambda a: (
            _severity_rank(a.max_severity_cleared),
            len(a.cleared),
            a.quick_win,
        ),
        reverse=True,
    )
    plan.packages_to_upgrade = sum(1 for a in plan.actions if a.target_version)
    plan.quick_wins = sum(1 for a in plan.actions if a.quick_win)

    cleared_total = plan.fixable_advisories
    plan.summary = (
        f"Upgrading {plan.packages_to_upgrade} package(s) clears "
        f"{cleared_total} of {plan.total_advisories} advisory(ies)."
        + (f" {plan.unfixable_advisories} have no fixed release yet."
           if plan.unfixable_advisories else "")
        + (f" {plan.quick_wins} are low-risk quick win(s)." if plan.quick_wins else "")
    )
    return plan


def _version_key(v: str):
    try:
        return semver.parse(v)
    except semver.InvalidVersion:
        return semver.parse("0.0.0")


def _le(a: str, b: str) -> bool:
    try:
        return semver.compare(a, b) <= 0
    except semver.InvalidVersion:
        return False


def plan_to_dict(plan: RemediationPlan) -> dict:
    return json.loads(json.dumps(asdict(plan)))
