"""Persistence layer — all SQLite reads/writes for analyses and their artifacts.

Keeps SQL in one place so services and the API share consistent access.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(value) -> str:
    return json.dumps(value or [])


def _loads(value: str | None):
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


# --------------------------------------------------------------------------- #
# Repositories
# --------------------------------------------------------------------------- #


def upsert_repository(conn: sqlite3.Connection, name: str, path: str, default_branch: str | None) -> int:
    existing = conn.execute("SELECT id FROM repositories WHERE path = ?", (path,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE repositories SET name = ?, default_branch = ? WHERE id = ?",
            (name, default_branch, existing["id"]),
        )
        return existing["id"]
    cur = conn.execute(
        "INSERT INTO repositories (name, path, default_branch, created_at) VALUES (?, ?, ?, ?)",
        (name, path, default_branch, now_iso()),
    )
    return cur.lastrowid


def get_repository(conn: sqlite3.Connection, repo_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
    return dict(row) if row else None


def list_repositories(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM repositories ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def delete_repository(conn: sqlite3.Connection, repo_id: int) -> None:
    conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))


# --------------------------------------------------------------------------- #
# Analyses
# --------------------------------------------------------------------------- #


def create_analysis(conn: sqlite3.Connection, repo_id: int, base_ref: str, target_ref: str) -> int:
    cur = conn.execute(
        "INSERT INTO analyses (repository_id, base_ref, target_ref, status, created_at) "
        "VALUES (?, ?, ?, 'pending', ?)",
        (repo_id, base_ref, target_ref, now_iso()),
    )
    return cur.lastrowid


def set_analysis_status(
    conn: sqlite3.Connection, analysis_id: int, status: str, error: str | None = None
) -> None:
    conn.execute(
        "UPDATE analyses SET status = ?, error = ? WHERE id = ?", (status, error, analysis_id)
    )


def update_analysis_summary(
    conn: sqlite3.Connection, analysis_id: int, summary: dict,
    attention_level: str, risk_score: int,
) -> None:
    conn.execute(
        """UPDATE analyses SET files_changed=?, files_added=?, files_modified=?,
               files_deleted=?, files_renamed=?, lines_added=?, lines_removed=?,
               attention_level=?, risk_score=? WHERE id=?""",
        (
            summary["files_changed"], summary["files_added"], summary["files_modified"],
            summary["files_deleted"], summary["files_renamed"], summary["lines_added"],
            summary["lines_removed"], attention_level, risk_score, analysis_id,
        ),
    )


def get_analysis(conn: sqlite3.Connection, analysis_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    return dict(row) if row else None


def list_analyses(conn: sqlite3.Connection, repo_id: int | None = None) -> list[dict]:
    if repo_id is not None:
        rows = conn.execute(
            "SELECT * FROM analyses WHERE repository_id = ? ORDER BY created_at DESC", (repo_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM analyses ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def delete_analysis(conn: sqlite3.Connection, analysis_id: int) -> None:
    conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))


# --------------------------------------------------------------------------- #
# Changed files / edges / impact
# --------------------------------------------------------------------------- #


def replace_changed_files(conn: sqlite3.Connection, analysis_id: int, files: list[dict]) -> None:
    conn.execute("DELETE FROM changed_files WHERE analysis_id = ?", (analysis_id,))
    conn.executemany(
        """INSERT INTO changed_files (analysis_id, path, old_path, change_type, lines_added,
               lines_removed, category, classification_reason, confidence, matched_rule)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [
            (analysis_id, f["path"], f.get("old_path"), f["change_type"], f["lines_added"],
             f["lines_removed"], f["category"], f.get("classification_reason"),
             f.get("confidence", 0.0), f.get("matched_rule"))
            for f in files
        ],
    )


def list_changed_files(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM changed_files WHERE analysis_id = ? ORDER BY path", (analysis_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def replace_edges(conn: sqlite3.Connection, analysis_id: int, edges: list[tuple[str, str, str]]) -> None:
    conn.execute("DELETE FROM dependency_edges WHERE analysis_id = ?", (analysis_id,))
    conn.executemany(
        "INSERT INTO dependency_edges (analysis_id, source_path, target_path, relation_type, detection) "
        "VALUES (?,?,?,?,?)",
        [(analysis_id, s, d, rel, "direct") for s, d, rel in edges],
    )


def list_edges(conn: sqlite3.Connection, analysis_id: int) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        "SELECT source_path, target_path, relation_type FROM dependency_edges WHERE analysis_id = ?",
        (analysis_id,),
    ).fetchall()
    return [(r["source_path"], r["target_path"], r["relation_type"]) for r in rows]


def replace_impact(conn: sqlite3.Connection, analysis_id: int, nodes: list[dict]) -> None:
    conn.execute("DELETE FROM impact_nodes WHERE analysis_id = ?", (analysis_id,))
    conn.executemany(
        "INSERT INTO impact_nodes (analysis_id, path, impact_type, distance, category) VALUES (?,?,?,?,?)",
        [(analysis_id, n["path"], n["impact_type"], n["distance"], n.get("category")) for n in nodes],
    )


def list_impact(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM impact_nodes WHERE analysis_id = ? ORDER BY distance, path", (analysis_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Risk findings
# --------------------------------------------------------------------------- #


def replace_risk_findings(conn: sqlite3.Connection, analysis_id: int, findings: list[dict]) -> None:
    conn.execute("DELETE FROM risk_findings WHERE analysis_id = ?", (analysis_id,))
    conn.executemany(
        """INSERT INTO risk_findings (analysis_id, title, severity, related_files, explanation,
               evidence, suggested_action, rule, score_contribution)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [
            (analysis_id, f["title"],
             f["severity"].value if hasattr(f["severity"], "value") else f["severity"],
             _j(f.get("related_files")), f["explanation"], f["evidence"],
             f["suggested_action"], f["rule"], f.get("score_contribution", 0))
            for f in findings
        ],
    )


def list_risk_findings(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM risk_findings WHERE analysis_id = ? ORDER BY score_contribution DESC", (analysis_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["related_files"] = _loads(d["related_files"])
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# Verification tasks
# --------------------------------------------------------------------------- #


def replace_generated_tasks(conn: sqlite3.Connection, analysis_id: int, tasks: list[dict]) -> None:
    """Insert engine-generated tasks. Existing generated tasks (and their evidence/history)
    are replaced; user-added tasks are preserved."""
    conn.execute(
        "DELETE FROM verification_tasks WHERE analysis_id = ? AND generated = 1", (analysis_id,)
    )
    ts = now_iso()
    for t in tasks:
        conn.execute(
            """INSERT INTO verification_tasks (analysis_id, task_key, title, description, reason,
                   related_files, verification_type, priority, status, steps,
                   evidence_requirements, generated, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (analysis_id, t["task_key"], t["title"], t["description"], t["reason"],
             _j(t.get("related_files")), t["verification_type"],
             t["priority"].value if hasattr(t["priority"], "value") else t["priority"],
             "open", _j(t.get("steps")), _j(t.get("evidence_requirements")), ts, ts),
        )


def add_task(conn: sqlite3.Connection, analysis_id: int, data: dict) -> int:
    ts = now_iso()
    key = f"custom:{ts}:{data['title'][:40]}"
    cur = conn.execute(
        """INSERT INTO verification_tasks (analysis_id, task_key, title, description, reason,
               related_files, verification_type, priority, status, steps,
               evidence_requirements, generated, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?)""",
        (analysis_id, key, data["title"], data.get("description", ""),
         data.get("reason", "User-added verification task."),
         _j(data.get("related_files")), data.get("verification_type", "manual"),
         data.get("priority", "medium"), "open", _j(data.get("steps")),
         _j(data.get("evidence_requirements")), ts, ts),
    )
    return cur.lastrowid


def get_task(conn: sqlite3.Connection, task_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM verification_tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["related_files"] = _loads(d["related_files"])
    d["steps"] = _loads(d["steps"])
    d["evidence_requirements"] = _loads(d["evidence_requirements"])
    d["generated"] = bool(d["generated"])
    return d


def list_tasks(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM verification_tasks WHERE analysis_id = ? ORDER BY id", (analysis_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["related_files"] = _loads(d["related_files"])
        d["steps"] = _loads(d["steps"])
        d["evidence_requirements"] = _loads(d["evidence_requirements"])
        d["generated"] = bool(d["generated"])
        out.append(d)
    return out


def update_task_fields(conn: sqlite3.Connection, task_id: int, fields: dict) -> None:
    if not fields:
        return
    fields = {**fields, "updated_at": now_iso()}
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE verification_tasks SET {cols} WHERE id = ?", (*fields.values(), task_id))


def delete_task(conn: sqlite3.Connection, task_id: int) -> None:
    conn.execute("DELETE FROM verification_tasks WHERE id = ?", (task_id,))


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #


def replace_generated_checklist(conn: sqlite3.Connection, analysis_id: int, items: list[str]) -> None:
    conn.execute(
        "DELETE FROM checklist_items WHERE analysis_id = ? AND source = 'generated'", (analysis_id,)
    )
    ts = now_iso()
    for i, text in enumerate(items):
        conn.execute(
            "INSERT INTO checklist_items (analysis_id, text, checked, source, sort_order, created_at) "
            "VALUES (?,?,0,'generated',?,?)",
            (analysis_id, text, i, ts),
        )


def add_checklist_item(conn: sqlite3.Connection, analysis_id: int, text: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) AS m FROM checklist_items WHERE analysis_id = ?",
        (analysis_id,),
    ).fetchone()
    cur = conn.execute(
        "INSERT INTO checklist_items (analysis_id, text, checked, source, sort_order, created_at) "
        "VALUES (?,?,0,'custom',?,?)",
        (analysis_id, text, (row["m"] or 0) + 1, now_iso()),
    )
    return cur.lastrowid


def list_checklist(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM checklist_items WHERE analysis_id = ? ORDER BY sort_order, id", (analysis_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["checked"] = bool(d["checked"])
        out.append(d)
    return out


def update_checklist_item(conn: sqlite3.Connection, item_id: int, fields: dict) -> None:
    if not fields:
        return
    if "checked" in fields:
        fields["checked"] = 1 if fields["checked"] else 0
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE checklist_items SET {cols} WHERE id = ?", (*fields.values(), item_id))


def delete_checklist_item(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))


# --------------------------------------------------------------------------- #
# Test gaps
# --------------------------------------------------------------------------- #


def replace_test_gaps(conn: sqlite3.Connection, analysis_id: int, gaps: list[dict]) -> None:
    conn.execute("DELETE FROM test_gaps WHERE analysis_id = ?", (analysis_id,))
    conn.executemany(
        """INSERT INTO test_gaps (analysis_id, changed_file, related_tests, detection_method,
               missing_coverage, recommended_tests, severity) VALUES (?,?,?,?,?,?,?)""",
        [
            (analysis_id, g["changed_file"], _j(g.get("related_tests")), g["detection_method"],
             g["missing_coverage"], _j(g.get("recommended_tests")),
             g["severity"].value if hasattr(g["severity"], "value") else g["severity"])
            for g in gaps
        ],
    )


def list_test_gaps(conn: sqlite3.Connection, analysis_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM test_gaps WHERE analysis_id = ? ORDER BY id", (analysis_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["related_tests"] = _loads(d["related_tests"])
        d["recommended_tests"] = _loads(d["recommended_tests"])
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
