"""Analysis orchestrator.

Runs the full deterministic pipeline for one analysis and persists every
artifact: diff → classify → dependency graph → impact → risk → verification plan
→ test gaps → review checklist. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import (
    classifier,
    dependency_analyzer,
    git_diff,
    impact_analyzer,
    risk_analyzer,
    store,
    test_gap,
    verification_planner,
)


def _build_checklist(findings: list[dict], tasks: list[dict], gaps: list[dict]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        key = text.strip().lower()
        if key and key not in seen:
            seen.add(key)
            items.append(text)

    for f in findings:
        add(f["suggested_action"])
    for t in tasks:
        add(t["title"])
    for g in gaps:
        for rec in g.get("recommended_tests", []):
            add(rec)
    return items


def run_analysis(conn: sqlite3.Connection, analysis_id: int, repo_path: Path) -> dict:
    """Execute the analysis pipeline, persist results, and return a summary dict."""
    store.set_analysis_status(conn, analysis_id, "running")
    analysis = store.get_analysis(conn, analysis_id)
    if not analysis:
        raise KeyError("Analysis not found")

    try:
        # 1. Diff --------------------------------------------------------- #
        diff = git_diff.compute_diff(repo_path, analysis["base_ref"], analysis["target_ref"])
        summary = git_diff.summarize(diff)

        # 2. Classification ---------------------------------------------- #
        changed: list[dict] = []
        for f in diff.files:
            c = classifier.classify_path(f.path)
            changed.append({
                "path": f.path, "old_path": f.old_path, "change_type": f.change_type,
                "lines_added": f.lines_added, "lines_removed": f.lines_removed,
                "category": c.category.value, "classification_reason": c.reason,
                "confidence": c.confidence, "matched_rule": c.matched_rule,
            })
        store.replace_changed_files(conn, analysis_id, changed)

        # 3. Dependency graph (at target commit) ------------------------- #
        dep = dependency_analyzer.build_dependency_graph(repo_path, diff.target_sha)
        store.replace_edges(conn, analysis_id, dep.edges)

        # 4. Impact ------------------------------------------------------- #
        categories = {f["path"]: f["category"] for f in changed}
        changed_paths = [f["path"] for f in changed if f["change_type"] != "deleted"]
        impact = impact_analyzer.compute_impact(changed_paths, dep.edges, categories)
        store.replace_impact(conn, analysis_id, impact.nodes)

        # Reverse-dep counts for risk connectivity rule.
        _fwd, reverse = impact_analyzer.build_adjacency(dep.edges)
        reverse_counts = {p: len(reverse.get(p, set())) for p in changed_paths}

        # 5. Risk --------------------------------------------------------- #
        source_changed = any(f["category"] in ("source", "ui") and f["change_type"] != "deleted"
                             for f in changed)
        test_changed = any(f["category"] == "test" for f in changed)
        ctx = risk_analyzer.RiskContext(
            changed_files=changed, reverse_dep_counts=reverse_counts,
            source_changed=source_changed, test_changed=test_changed,
            total_lines=summary["lines_added"] + summary["lines_removed"],
            files_changed=summary["files_changed"],
        )
        risk = risk_analyzer.analyze_risk(ctx)
        store.replace_risk_findings(conn, analysis_id, risk["findings"])
        store.update_analysis_summary(
            conn, analysis_id, summary, risk["attention_level"].value, risk["score"]
        )

        # 6. Verification plan ------------------------------------------- #
        planned = verification_planner.plan_verification(changed)
        store.replace_generated_tasks(conn, analysis_id, [p.__dict__ for p in planned])

        # 7. Test gaps ---------------------------------------------------- #
        gaps = test_gap.detect_test_gaps(changed, dep.edges, dep.files)
        store.replace_test_gaps(conn, analysis_id, gaps)

        # 8. Review checklist -------------------------------------------- #
        tasks = store.list_tasks(conn, analysis_id)
        checklist = _build_checklist(risk["findings"], tasks, gaps)
        store.replace_generated_checklist(conn, analysis_id, checklist)

        store.set_analysis_status(conn, analysis_id, "complete")
        return {
            "status": "complete", "summary": summary,
            "attention_level": risk["attention_level"].value, "risk_score": risk["score"],
            "range_kind": diff.range_kind, "dependency_note": dep.note,
            "edges": len(dep.edges), "tasks": len(planned), "gaps": len(gaps),
        }
    except Exception as exc:  # pragma: no cover - defensive
        store.set_analysis_status(conn, analysis_id, "failed", str(exc))
        raise
