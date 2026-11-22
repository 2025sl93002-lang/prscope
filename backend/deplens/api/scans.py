"""Scan detail, package explorer, graph, security, licenses, usage, comparison."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from deplens.api.deps import db_dep
from deplens.db import Database
from deplens.parsers.lockfile import ROOT_ID

router = APIRouter(prefix="/api/scans", tags=["scans"])

_SEV_RANK = {"critical": 0, "high": 1, "moderate": 2, "low": 3}


def _get_scan(db: Database, scan_id: int):
    scan = db.query_one("SELECT * FROM scans WHERE id=?", (scan_id,))
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}")
def scan_detail(scan_id: int, db: Database = Depends(db_dep)):
    scan = _get_scan(db, scan_id)
    project = db.get_project(scan["project_id"])
    return {
        "id": scan["id"],
        "project": project,
        "created_at": scan["created_at"],
        "online": bool(scan["online"]),
        "lockfile_format": scan["lockfile_format"],
        "root_name": scan["root_name"],
        "root_version": scan["root_version"],
        "health_score": scan["health_score"],
        "health_grade": scan["health_grade"],
        "health_confidence": scan["health_confidence"],
        "summary": json.loads(scan["summary_json"]) if scan["summary_json"] else {},
        "stages": json.loads(scan["stages_json"]) if scan["stages_json"] else [],
        "warnings": json.loads(scan["warnings_json"]) if scan["warnings_json"] else [],
    }


@router.get("/{scan_id}/packages")
def scan_packages(
    scan_id: int,
    q: Optional[str] = None,
    type: Optional[str] = Query(None, pattern="^(direct|transitive)$"),
    scope: Optional[str] = None,
    filter: Optional[str] = None,
    sort: str = "name",
    order: str = "asc",
    db: Database = Depends(db_dep),
):
    _get_scan(db, scan_id)
    rows = [dict(r) for r in db.query("SELECT * FROM packages WHERE scan_id=?", (scan_id,))]
    for r in rows:
        r["is_direct"] = bool(r["is_direct"])
        try:
            r["data"] = json.loads(r["data_json"]) if r["data_json"] else {}
        except (ValueError, TypeError):
            r["data"] = {}
        r.pop("data_json", None)

    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r["name"].lower()]
    if type == "direct":
        rows = [r for r in rows if r["is_direct"]]
    elif type == "transitive":
        rows = [r for r in rows if not r["is_direct"]]
    if scope:
        rows = [r for r in rows if r["scope"] == scope]

    filters = {
        "outdated": lambda r: r["update_type"] in ("major", "minor", "patch"),
        "vulnerable": lambda r: (r["vuln_count"] or 0) > 0,
        "unused": lambda r: r["usage_status"] == "none",
        "unknown-license": lambda r: r["license_family"] == "unknown",
        "license-warning": lambda r: r["license_verdict"] in ("review", "restricted"),
        "deprecated": lambda r: r["maintenance_status"] in ("deprecated", "concerns"),
        "dev": lambda r: r["scope"] == "dev",
        "prod": lambda r: r["scope"] == "prod",
    }
    if filter and filter in filters:
        rows = [r for r in rows if filters[filter](r)]

    def sort_key(r):
        if sort == "severity":
            return _SEV_RANK.get(r["max_severity"], 9)
        val = r.get(sort)
        return (val is None, val if val is not None else "")

    rows.sort(key=sort_key, reverse=(order == "desc"))
    return {"packages": rows, "count": len(rows)}


@router.get("/{scan_id}/package/{name}")
def package_detail(scan_id: int, name: str, db: Database = Depends(db_dep)):
    _get_scan(db, scan_id)
    row = db.query_one(
        "SELECT * FROM packages WHERE scan_id=? AND name=? ORDER BY is_direct DESC LIMIT 1",
        (scan_id, name),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Package not found in this scan")
    data = json.loads(row["data_json"]) if row["data_json"] else {}
    vulns = [dict(v) for v in db.query(
        "SELECT * FROM vulnerabilities WHERE scan_id=? AND package=?", (scan_id, name)
    )]
    for v in vulns:
        try:
            v["data"] = json.loads(v["data_json"])
        except (ValueError, TypeError):
            v["data"] = {}
        v.pop("data_json", None)

    node_id = row["node_id"]
    paths, dependents = _paths_and_dependents(db, scan_id, node_id)
    return {
        "name": row["name"],
        "version": row["version"],
        "node_id": node_id,
        "is_direct": bool(row["is_direct"]),
        "scope": row["scope"],
        "depth": row["depth"],
        "dependents": row["dependents"],
        "path_count": row["path_count"],
        "latest": row["latest"],
        "license": row["license"],
        "license_family": row["license_family"],
        "license_verdict": row["license_verdict"],
        "update_type": row["update_type"],
        "usage_status": row["usage_status"],
        "maintenance_status": row["maintenance_status"],
        "max_severity": row["max_severity"],
        "data": data,
        "vulnerabilities": vulns,
        "dependency_paths": paths,
        "dependent_names": dependents,
    }


def _paths_and_dependents(db: Database, scan_id: int, node_id: str, limit: int = 15):
    import networkx as nx

    g = nx.DiGraph()
    g.add_node(ROOT_ID)
    name_of = {}
    for r in db.query("SELECT node_id, name FROM packages WHERE scan_id=?", (scan_id,)):
        g.add_node(r["node_id"])
        name_of[r["node_id"]] = r["name"]
    for e in db.query("SELECT source, target FROM edges WHERE scan_id=?", (scan_id,)):
        if e["source"] in g and e["target"] in g:
            g.add_edge(e["source"], e["target"])
    paths = []
    if node_id in g:
        try:
            for p in nx.all_simple_paths(g, ROOT_ID, node_id, cutoff=40):
                paths.append([name_of.get(n, n) if n != ROOT_ID else "(root)" for n in p])
                if len(paths) >= limit:
                    break
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            pass
    dependents = sorted({
        name_of.get(p, p) for p in g.predecessors(node_id) if p != ROOT_ID
    }) if node_id in g else []
    return paths, dependents


@router.get("/{scan_id}/graph")
def scan_graph(
    scan_id: int,
    include_dev: bool = True,
    include_optional: bool = True,
    db: Database = Depends(db_dep),
):
    import networkx as nx

    _get_scan(db, scan_id)
    # Build the full resolved graph first so we can compute blast radius
    # (how many packages transitively depend on each node).
    g = nx.DiGraph()
    g.add_node(ROOT_ID)
    rows = {r["node_id"]: dict(r) for r in db.query(
        "SELECT * FROM packages WHERE scan_id=?", (scan_id,)
    )}
    for nid in rows:
        g.add_node(nid)
    for e in db.query("SELECT source, target FROM edges WHERE scan_id=?", (scan_id,)):
        if e["source"] in g and e["target"] in g:
            g.add_edge(e["source"], e["target"])
    blast: dict = {}
    for nid in rows:
        anc = nx.ancestors(g, nid)
        anc.discard(ROOT_ID)
        blast[nid] = len(anc)

    nodes = []
    allowed = set()
    for r in rows.values():
        if not include_dev and r["scope"] == "dev":
            continue
        if not include_optional and r["scope"] == "optional":
            continue
        allowed.add(r["node_id"])
        nodes.append({
            "id": r["node_id"],
            "name": r["name"],
            "version": r["version"],
            "direct": bool(r["is_direct"]),
            "scope": r["scope"],
            "depth": r["depth"],
            "dependents": r["dependents"],
            "blast_radius": blast.get(r["node_id"], 0),
            "max_severity": r["max_severity"],
            "update_type": r["update_type"],
            "license_verdict": r["license_verdict"],
            "vuln_count": r["vuln_count"],
        })
    edges = []
    for e in db.query("SELECT * FROM edges WHERE scan_id=?", (scan_id,)):
        src_ok = e["source"] == ROOT_ID or e["source"] in allowed
        if src_ok and e["target"] in allowed:
            edges.append({
                "source": "__root__" if e["source"] == ROOT_ID else e["source"],
                "target": e["target"],
                "edge_type": e["edge_type"],
            })
    nodes.append({"id": "__root__", "name": "(root project)", "version": "", "direct": False,
                  "scope": "root", "depth": 0, "blast_radius": 0, "root": True})
    return {"nodes": nodes, "edges": edges}


@router.get("/{scan_id}/remediation")
def scan_remediation(scan_id: int, db: Database = Depends(db_dep)):
    from deplens.analyzers.remediation import plan_remediation, plan_to_dict

    _get_scan(db, scan_id)
    return plan_to_dict(plan_remediation(db, scan_id))


@router.get("/{scan_id}/vulnerabilities")
def scan_vulnerabilities(scan_id: int, db: Database = Depends(db_dep)):
    _get_scan(db, scan_id)
    rows = [dict(v) for v in db.query(
        "SELECT * FROM vulnerabilities WHERE scan_id=?", (scan_id,)
    )]
    for v in rows:
        try:
            v["data"] = json.loads(v["data_json"])
        except (ValueError, TypeError):
            v["data"] = {}
        v.pop("data_json", None)
    rows.sort(key=lambda v: _SEV_RANK.get(v["severity"], 9))
    scan = db.query_one("SELECT online FROM scans WHERE id=?", (scan_id,))
    return {"vulnerabilities": rows, "checked": bool(scan["online"]), "count": len(rows)}


@router.get("/{scan_id}/licenses")
def scan_licenses(scan_id: int, db: Database = Depends(db_dep)):
    _get_scan(db, scan_id)
    rows = db.query("SELECT name, version, license, license_family, license_verdict, is_direct "
                    "FROM packages WHERE scan_id=?", (scan_id,))
    inventory = [dict(r) for r in rows]
    from collections import Counter
    family = Counter(r["license_family"] for r in inventory)
    verdict = Counter(r["license_verdict"] for r in inventory)
    return {
        "inventory": inventory,
        "family_distribution": dict(family),
        "verdict_distribution": dict(verdict),
    }


@router.get("/{scan_id}/usage")
def scan_usage(scan_id: int, db: Database = Depends(db_dep)):
    scan = _get_scan(db, scan_id)
    project_id = scan["project_id"]
    overrides = {
        o["package"]: {"state": o["state"], "note": o["note"]}
        for o in db.query("SELECT * FROM usage_overrides WHERE project_id=?", (project_id,))
    }
    results = []
    for r in db.query(
        "SELECT name, version, usage_status, data_json FROM packages "
        "WHERE scan_id=? AND is_direct=1", (scan_id,)
    ):
        data = json.loads(r["data_json"]) if r["data_json"] else {}
        usage = data.get("usage") or {}
        results.append({
            "package": r["name"],
            "version": r["version"],
            "status": r["usage_status"],
            "confidence": usage.get("confidence"),
            "explanation": usage.get("explanation"),
            "evidence": usage.get("evidence", []),
            "override": overrides.get(r["name"]),
        })
    return {"usage": results}


@router.get("/{scan_id}/compare/{other_id}")
def compare_scans(scan_id: int, other_id: int, db: Database = Depends(db_dep)):
    _get_scan(db, scan_id)
    _get_scan(db, other_id)

    def pkg_map(sid):
        return {
            r["name"]: r["version"]
            for r in db.query("SELECT name, version FROM packages WHERE scan_id=?", (sid,))
        }

    def vuln_set(sid):
        return {
            f"{r['package']}:{r['osv_id']}"
            for r in db.query("SELECT package, osv_id FROM vulnerabilities WHERE scan_id=?", (sid,))
        }

    old, new = pkg_map(other_id), pkg_map(scan_id)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    updated = [
        {"name": n, "from": old[n], "to": new[n]}
        for n in sorted(set(old) & set(new)) if old[n] != new[n]
    ]
    old_v, new_v = vuln_set(other_id), vuln_set(scan_id)
    s_old = db.query_one("SELECT health_score FROM scans WHERE id=?", (other_id,))
    s_new = db.query_one("SELECT health_score FROM scans WHERE id=?", (scan_id,))
    return {
        "base_scan": other_id,
        "target_scan": scan_id,
        "added": added,
        "removed": removed,
        "updated": updated,
        "vulnerabilities_added": sorted(new_v - old_v),
        "vulnerabilities_resolved": sorted(old_v - new_v),
        "health_change": {
            "from": s_old["health_score"], "to": s_new["health_score"],
            "delta": (s_new["health_score"] or 0) - (s_old["health_score"] or 0),
        },
    }
