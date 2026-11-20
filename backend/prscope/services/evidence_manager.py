"""Evidence ledger & task lifecycle.

Manages verification evidence records, task status transitions with an
audit-style history, and the verification-completeness metric. All data is
stored locally; nothing is uploaded. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import sqlite3

from ..models import ReviewReadiness, TaskStatus
from . import store

_VALID_TRANSITIONS = {s.value for s in TaskStatus}


def record_status_change(
    conn: sqlite3.Connection, task_id: int, from_status: str | None, to_status: str,
    note: str | None = None, actor: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO task_history (task_id, from_status, to_status, note, actor, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (task_id, from_status, to_status, note, actor, store.now_iso()),
    )


def change_task_status(
    conn: sqlite3.Connection, task_id: int, to_status: str,
    note: str | None = None, actor: str | None = None,
) -> dict:
    if to_status not in _VALID_TRANSITIONS:
        raise ValueError(f"Invalid task status: {to_status}")
    task = store.get_task(conn, task_id)
    if not task:
        raise KeyError("Task not found")
    from_status = task["status"]
    store.update_task_fields(conn, task_id, {"status": to_status})
    if from_status != to_status:
        record_status_change(conn, task_id, from_status, to_status, note, actor)
    return store.get_task(conn, task_id)


def list_task_history(conn: sqlite3.Connection, task_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM task_history WHERE task_id = ? ORDER BY id", (task_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Evidence records
# --------------------------------------------------------------------------- #


def add_evidence(conn: sqlite3.Connection, task_id: int, data: dict) -> dict:
    task = store.get_task(conn, task_id)
    if not task:
        raise KeyError("Task not found")
    cur = conn.execute(
        """INSERT INTO evidence_records (task_id, analysis_id, evidence_type, note, link,
               command, result, performed_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (task_id, task["analysis_id"], data["evidence_type"], data.get("note"),
         data.get("link"), data.get("command"), data.get("result"),
         data.get("performed_by"), store.now_iso()),
    )
    return get_evidence(conn, cur.lastrowid)


def get_evidence(conn: sqlite3.Connection, evidence_id: int) -> dict:
    row = conn.execute("SELECT * FROM evidence_records WHERE id = ?", (evidence_id,)).fetchone()
    return dict(row)


def list_evidence_for_task(conn: sqlite3.Connection, task_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM evidence_records WHERE task_id = ? ORDER BY id", (task_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def list_evidence_for_analysis(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM evidence_records WHERE analysis_id = ? ORDER BY id", (analysis_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def delete_evidence(conn: sqlite3.Connection, evidence_id: int) -> None:
    conn.execute("DELETE FROM evidence_records WHERE id = ?", (evidence_id,))


def count_tasks_with_evidence(conn: sqlite3.Connection, analysis_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(DISTINCT task_id) AS c FROM evidence_records WHERE analysis_id = ?",
        (analysis_id,),
    ).fetchone()
    return row["c"] or 0


# --------------------------------------------------------------------------- #
# Review readiness / completeness metric
# --------------------------------------------------------------------------- #


def compute_readiness(conn: sqlite3.Connection, analysis_id: int) -> ReviewReadiness:
    analysis = store.get_analysis(conn, analysis_id)
    tasks = store.list_tasks(conn, analysis_id)
    gaps = store.list_test_gaps(conn, analysis_id)
    findings = store.list_risk_findings(conn, analysis_id)
    impact = store.list_impact(conn, analysis_id)

    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == TaskStatus.completed.value)
    blocked = sum(1 for t in tasks if t["status"] == TaskStatus.blocked.value)
    not_applicable = sum(1 for t in tasks if t["status"] == TaskStatus.not_applicable.value)
    pending = sum(1 for t in tasks if t["status"] == TaskStatus.open.value)
    applicable = total - not_applicable

    tasks_with_ev = count_tasks_with_evidence(conn, analysis_id)
    tasks_without_ev = max(0, total - tasks_with_ev)

    completeness = (completed / applicable * 100.0) if applicable > 0 else 0.0
    affected = sum(1 for n in impact if n["impact_type"] in ("direct", "indirect"))

    label = (
        f"Verification plan completion: {completed} of {applicable} applicable checks completed."
        if applicable
        else "No applicable verification tasks."
    )

    return ReviewReadiness(
        attention_level=analysis["attention_level"] if analysis else None,
        risk_score=analysis["risk_score"] if analysis else 0,
        total_tasks=total,
        applicable_tasks=applicable,
        completed_tasks=completed,
        pending_tasks=pending,
        blocked_tasks=blocked,
        not_applicable_tasks=not_applicable,
        tasks_with_evidence=tasks_with_ev,
        tasks_without_evidence=tasks_without_ev,
        completeness_percent=round(completeness, 1),
        completeness_label=label,
        test_gap_count=len(gaps),
        risk_finding_count=len(findings),
        changed_file_count=analysis["files_changed"] if analysis else 0,
        affected_module_count=affected,
    )
