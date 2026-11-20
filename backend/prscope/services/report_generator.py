"""Report generator — Markdown, JSON, and print-friendly HTML.

Assembles a full verification report from persisted analysis data. Contains only
real analysis results (no placeholders). SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import json
import sqlite3
from html import escape

from . import evidence_manager, store

_LIMITATIONS = (
    "File-level static analysis: dependency edges approximate, and never guarantee, "
    "runtime behaviour.",
    "Dependency analysis supports Python and relative JS/TS imports only; other "
    "languages and dynamic imports are not resolved.",
    "Test gaps are *potential* gaps inferred from imports and naming, not from "
    "coverage data.",
    "Review-attention level reflects how much review a change warrants — not a "
    "probability that the code contains defects.",
)


def _gather(conn: sqlite3.Connection, analysis_id: int) -> dict:
    analysis = store.get_analysis(conn, analysis_id)
    if not analysis:
        raise KeyError("Analysis not found")
    repo = store.get_repository(conn, analysis["repository_id"])
    return {
        "analysis": analysis,
        "repository": repo,
        "changed_files": store.list_changed_files(conn, analysis_id),
        "impact": store.list_impact(conn, analysis_id),
        "edges": store.list_edges(conn, analysis_id),
        "risk": store.list_risk_findings(conn, analysis_id),
        "tasks": store.list_tasks(conn, analysis_id),
        "gaps": store.list_test_gaps(conn, analysis_id),
        "checklist": store.list_checklist(conn, analysis_id),
        "evidence": evidence_manager.list_evidence_for_analysis(conn, analysis_id),
        "readiness": evidence_manager.compute_readiness(conn, analysis_id).model_dump(),
    }


def build_json(conn: sqlite3.Connection, analysis_id: int) -> dict:
    data = _gather(conn, analysis_id)
    data["generated"] = {"tool": "PRScope", "note": "Deterministic local analysis."}
    return data


def build_markdown(conn: sqlite3.Connection, analysis_id: int) -> str:
    d = _gather(conn, analysis_id)
    a = d["analysis"]
    repo = d["repository"] or {}
    r = d["readiness"]
    lines: list[str] = []
    w = lines.append

    w(f"# PRScope Verification Report — Analysis #{analysis_id}")
    w("")
    w("## 1. Repository")
    w(f"- **Repository:** {repo.get('name', 'unknown')}")
    w(f"- **Path:** `{repo.get('path', '')}`")
    w("")
    w("## 2. Comparison range")
    w(f"- **Base:** `{a['base_ref']}`")
    w(f"- **Target:** `{a['target_ref']}`")
    w(f"- **Analyzed at:** {a['created_at']}")
    w(f"- **Status:** {a['status']}")
    w("")
    w("## 3. Change summary")
    w(f"- Files changed: **{a['files_changed']}** "
      f"(added {a['files_added']}, modified {a['files_modified']}, "
      f"deleted {a['files_deleted']}, renamed {a['files_renamed']})")
    w(f"- Lines: **+{a['lines_added']} / -{a['lines_removed']}**")
    w(f"- Review attention: **{(a['attention_level'] or 'n/a').upper()}** "
      f"(score {a['risk_score']})")
    w("")
    w("## 4. Changed files & classification")
    w("| File | Change | Category | Reason | +/- |")
    w("|------|--------|----------|--------|-----|")
    for f in d["changed_files"]:
        w(f"| `{f['path']}` | {f['change_type']} | {f['category']} | "
          f"{f['classification_reason'] or ''} | +{f['lines_added']}/-{f['lines_removed']} |")
    w("")
    w("## 5. Impact analysis")
    direct = [n for n in d["impact"] if n["impact_type"] == "direct"]
    indirect = [n for n in d["impact"] if n["impact_type"] == "indirect"]
    w(f"- Directly affected files: **{len(direct)}**")
    w(f"- Indirectly affected files: **{len(indirect)}**")
    w(f"- Dependency edges detected: **{len(d['edges'])}**")
    if direct:
        w("")
        w("**Directly affected:**")
        for n in direct[:50]:
            w(f"- `{n['path']}`")
    w("")
    w("## 6. Risk / review-attention findings")
    if not d["risk"]:
        w("_No risk findings generated._")
    for f in d["risk"]:
        w(f"### {f['title']} — {f['severity'].upper()}")
        w(f"- **Explanation:** {f['explanation']}")
        w(f"- **Evidence:** {f['evidence']}")
        w(f"- **Suggested action:** {f['suggested_action']}")
        w(f"- **Rule:** `{f['rule']}` (score +{f['score_contribution']})")
        if f["related_files"]:
            w(f"- **Files:** {', '.join('`'+x+'`' for x in f['related_files'])}")
        w("")
    w("## 7. Potential test gaps")
    if not d["gaps"]:
        w("_No potential test gaps detected._")
    for g in d["gaps"]:
        w(f"- **`{g['changed_file']}`** — {g['missing_coverage']} "
          f"_(detection: {g['detection_method']})_")
    w("")
    w("## 8. Verification plan")
    for t in d["tasks"]:
        box = {"completed": "x", "not_applicable": "-"}.get(t["status"], " ")
        w(f"- [{box}] **{t['title']}** ({t['status']}, {t['priority']}) — {t['reason']}")
    w("")
    w("## 9. Evidence summary")
    w(f"- Tasks with evidence: **{r['tasks_with_evidence']} / {r['total_tasks']}**")
    for e in d["evidence"]:
        w(f"- [{e['evidence_type']}] task #{e['task_id']}: "
          f"{e.get('note') or e.get('result') or e.get('link') or ''}")
    w("")
    w("## 10. Review checklist")
    for c in d["checklist"]:
        w(f"- [{'x' if c['checked'] else ' '}] {c['text']}")
    w("")
    w("## 11. Review readiness")
    w(f"- {r['completeness_label']}")
    w(f"- Completeness: **{r['completeness_percent']}%** "
      f"(completed {r['completed_tasks']}, pending {r['pending_tasks']}, "
      f"blocked {r['blocked_tasks']}, N/A {r['not_applicable_tasks']})")
    w("")
    w("## 12. Limitations")
    for lim in _LIMITATIONS:
        w(f"- {lim}")
    w("")
    w(f"_Generated by PRScope — deterministic local analysis. Report time: {a['created_at']}._")
    return "\n".join(lines)


def build_html(conn: sqlite3.Connection, analysis_id: int) -> str:
    md = build_markdown(conn, analysis_id)
    body = escape(md)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>PRScope Report #{analysis_id}</title>"
        "<style>body{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;"
        "max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#1a1a1a}"
        "pre{white-space:pre-wrap;word-wrap:break-word}@media print{body{margin:0}}</style>"
        f"</head><body><pre>{body}</pre></body></html>"
    )


def to_json_string(conn: sqlite3.Connection, analysis_id: int) -> str:
    return json.dumps(build_json(conn, analysis_id), indent=2, default=str)
