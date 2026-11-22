"""Report generation: Markdown, JSON and CSV exports from a persisted scan.

Reports are built entirely from stored scan data so they are reproducible and
honest about limitations and data sources.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from deplens import __version__
from deplens.db import Database


def build_report_data(db: Database, scan_id: int) -> Dict[str, Any]:
    scan = db.query_one("SELECT * FROM scans WHERE id=?", (scan_id,))
    if scan is None:
        raise ValueError(f"Scan #{scan_id} not found")
    project = db.get_project(scan["project_id"])
    summary = json.loads(scan["summary_json"]) if scan["summary_json"] else {}
    packages = [dict(r) for r in db.query(
        "SELECT * FROM packages WHERE scan_id=? ORDER BY is_direct DESC, name", (scan_id,)
    )]
    vulns = [dict(r) for r in db.query(
        "SELECT * FROM vulnerabilities WHERE scan_id=? ORDER BY "
        "CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'moderate' THEN 2 "
        "WHEN 'low' THEN 3 ELSE 4 END, package", (scan_id,)
    )]
    decisions = [dict(r) for r in db.query(
        "SELECT * FROM decisions WHERE project_id=? ORDER BY updated_at DESC",
        (scan["project_id"],)
    )]
    return {
        "generator": f"DepLens {__version__}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "scan": {
            "id": scan["id"],
            "created_at": datetime.fromtimestamp(scan["created_at"], timezone.utc).isoformat(),
            "online": bool(scan["online"]),
            "lockfile_format": scan["lockfile_format"],
            "health_score": scan["health_score"],
            "health_grade": scan["health_grade"],
            "health_confidence": scan["health_confidence"],
        },
        "summary": summary,
        "packages": packages,
        "vulnerabilities": vulns,
        "decisions": decisions,
        "data_sources": [
            "npm registry (registry.npmjs.org) — versions, licenses, publish times",
            "OSV.dev — open-source vulnerability advisories",
            "Local static source analysis — usage evidence",
        ],
        "limitations": [
            "Analysis reflects the lockfile and registry data at scan time.",
            "Usage analysis cannot prove a package is unused (dynamic/plugin loading).",
            "The health score is a prioritisation aid, not a validated risk probability.",
            "Security status is UNKNOWN (not secure) when advisories were not checked.",
            "License classification is heuristic and is not legal advice.",
        ],
    }


def render_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def render_csv(data: Dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "name", "version", "latest", "type", "scope", "depth", "dependents",
        "license", "license_verdict", "update_type", "usage_status",
        "maintenance_status", "max_severity", "vuln_count",
    ])
    for p in data["packages"]:
        writer.writerow([
            p["name"], p["version"], p.get("latest") or "",
            "direct" if p["is_direct"] else "transitive", p["scope"], p.get("depth"),
            p.get("dependents"), p.get("license") or "", p.get("license_verdict") or "",
            p.get("update_type") or "", p.get("usage_status") or "",
            p.get("maintenance_status") or "", p.get("max_severity") or "", p.get("vuln_count", 0),
        ])
    return buf.getvalue()


def render_markdown(data: Dict[str, Any]) -> str:
    s = data["summary"]
    scan = data["scan"]
    project = data["project"] or {}
    health = s.get("health", {})
    lines: List[str] = []
    lines.append(f"# DepLens Report — {project.get('name', 'Unknown project')}")
    lines.append("")
    lines.append(f"- **Generated:** {data['generated_at']}")
    lines.append(f"- **Generator:** {data['generator']}")
    lines.append(f"- **Project path:** `{project.get('path', '')}`")
    lines.append(f"- **Ecosystem:** {project.get('ecosystem', 'npm')}")
    lines.append(f"- **Scan date:** {scan['created_at']}")
    lines.append(f"- **Lockfile format:** {scan['lockfile_format']}")
    lines.append(f"- **Online analysis:** {'yes' if scan['online'] else 'no (offline)'}")
    lines.append("")
    lines.append("## Health score")
    lines.append("")
    lines.append(
        f"**{scan['health_score']}/100 (grade {scan['health_grade']})** — "
        f"confidence: {scan['health_confidence']}"
    )
    lines.append("")
    if health.get("factors"):
        lines.append("Contributing factors:")
        lines.append("")
        for f in health["factors"]:
            lines.append(f"- {f['impact']:+.0f}: {f['label']}")
        lines.append("")
    for note in health.get("notes", []):
        lines.append(f"> {note}")
    lines.append("")
    lines.append("## Dependency summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Total dependencies | {s.get('total', 0)} |")
    lines.append(f"| Direct | {s.get('direct', 0)} |")
    lines.append(f"| Transitive | {s.get('transitive', 0)} |")
    lines.append(f"| Outdated | {s.get('outdated', 0)} |")
    lines.append(f"| Vulnerable packages | {s.get('vulnerable_packages', 0)} |")
    lines.append(f"| License warnings | {s.get('license_warnings', 0)} |")
    lines.append(f"| Unknown licenses | {s.get('unknown_licenses', 0)} |")
    lines.append(f"| Potentially unused | {s.get('potentially_unused', 0)} |")
    lines.append(f"| Maintenance concerns | {s.get('maintenance_concerns', 0)} |")
    lines.append("")

    if data["vulnerabilities"]:
        lines.append("## Security findings")
        lines.append("")
        lines.append("| Package | Version | Severity | Advisory | Fixed in | Summary |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for v in data["vulnerabilities"]:
            adv = v.get("cve") or v.get("osv_id")
            lines.append(
                f"| {v['package']} | {v['installed_version']} | {v['severity']} | "
                f"{adv} | {v.get('fixed_version') or '—'} | {(v.get('summary') or '')[:80]} |"
            )
        lines.append("")

    outdated = [p for p in data["packages"] if p.get("update_type") in ("major", "minor", "patch")]
    if outdated:
        lines.append("## Outdated packages")
        lines.append("")
        lines.append("| Package | Installed | Latest | Update |")
        lines.append("| --- | --- | --- | --- |")
        for p in outdated[:200]:
            lines.append(
                f"| {p['name']} | {p['version']} | {p.get('latest') or '?'} | {p['update_type']} |"
            )
        lines.append("")

    if data["decisions"]:
        lines.append("## Decision records")
        lines.append("")
        lines.append("| Package | Action | Decision | Status | Reason |")
        lines.append("| --- | --- | --- | --- | --- |")
        for d in data["decisions"]:
            lines.append(
                f"| {d['package']} | {d['action']} | {d['decision']} | {d['status']} | "
                f"{(d.get('reason') or '')[:60]} |"
            )
        lines.append("")

    lines.append("## Data sources")
    lines.append("")
    for src in data["data_sources"]:
        lines.append(f"- {src}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for lim in data["limitations"]:
        lines.append(f"- {lim}")
    lines.append("")
    return "\n".join(lines)
