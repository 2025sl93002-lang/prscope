"""Decision workspace, verification checklists, and usage overrides."""

from __future__ import annotations

import json
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deplens.api.deps import db_dep
from deplens.db import Database

router = APIRouter(prefix="/api", tags=["workspace"])


class VerificationTask(BaseModel):
    text: str
    status: str = "pending"  # pending | complete | blocked | not-applicable
    note: Optional[str] = None
    evidence_url: Optional[str] = None


class DecisionBody(BaseModel):
    package: str
    current_version: Optional[str] = None
    action: str
    proposed_version: Optional[str] = None
    decision: str  # upgrade | remove | replace | keep | investigate-later
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: str = "open"
    impact: Optional[dict] = None
    verification: Optional[List[VerificationTask]] = None


def _row_to_decision(r) -> dict:
    return {
        "id": r["id"],
        "package": r["package"],
        "current_version": r["current_version"],
        "action": r["action"],
        "proposed_version": r["proposed_version"],
        "decision": r["decision"],
        "reason": r["reason"],
        "notes": r["notes"],
        "status": r["status"],
        "impact": json.loads(r["impact_json"]) if r["impact_json"] else None,
        "verification": json.loads(r["verification_json"]) if r["verification_json"] else [],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


@router.get("/projects/{project_id}/decisions")
def list_decisions(project_id: int, db: Database = Depends(db_dep)):
    if db.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = db.query(
        "SELECT * FROM decisions WHERE project_id=? ORDER BY updated_at DESC", (project_id,)
    )
    return {"decisions": [_row_to_decision(r) for r in rows]}


@router.post("/projects/{project_id}/decisions")
def create_decision(project_id: int, body: DecisionBody, db: Database = Depends(db_dep)):
    if db.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    now = time.time()
    verification = [t.model_dump() for t in (body.verification or [])]
    cur = db.execute(
        "INSERT INTO decisions(project_id, package, current_version, action, proposed_version, "
        "decision, reason, notes, status, impact_json, verification_json, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            project_id, body.package, body.current_version, body.action, body.proposed_version,
            body.decision, body.reason, body.notes, body.status,
            json.dumps(body.impact) if body.impact else None,
            json.dumps(verification), now, now,
        ),
    )
    row = db.query_one("SELECT * FROM decisions WHERE id=?", (cur.lastrowid,))
    return _row_to_decision(row)


@router.put("/decisions/{decision_id}")
def update_decision(decision_id: int, body: DecisionBody, db: Database = Depends(db_dep)):
    row = db.query_one("SELECT * FROM decisions WHERE id=?", (decision_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    verification = [t.model_dump() for t in (body.verification or [])]
    db.execute(
        "UPDATE decisions SET package=?, current_version=?, action=?, proposed_version=?, "
        "decision=?, reason=?, notes=?, status=?, impact_json=?, verification_json=?, updated_at=? "
        "WHERE id=?",
        (
            body.package, body.current_version, body.action, body.proposed_version,
            body.decision, body.reason, body.notes, body.status,
            json.dumps(body.impact) if body.impact else row["impact_json"],
            json.dumps(verification), time.time(), decision_id,
        ),
    )
    return _row_to_decision(db.query_one("SELECT * FROM decisions WHERE id=?", (decision_id,)))


@router.delete("/decisions/{decision_id}")
def delete_decision(decision_id: int, db: Database = Depends(db_dep)):
    if db.query_one("SELECT id FROM decisions WHERE id=?", (decision_id,)) is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    db.execute("DELETE FROM decisions WHERE id=?", (decision_id,))
    return {"ok": True}


class UsageOverrideBody(BaseModel):
    package: str
    state: str  # intentional | dismissed | cleared
    note: Optional[str] = None


@router.post("/projects/{project_id}/usage-override")
def set_usage_override(project_id: int, body: UsageOverrideBody, db: Database = Depends(db_dep)):
    if db.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.state == "cleared":
        db.execute(
            "DELETE FROM usage_overrides WHERE project_id=? AND package=?",
            (project_id, body.package),
        )
        return {"ok": True, "cleared": True}
    db.execute(
        "INSERT INTO usage_overrides(project_id, package, state, note, updated_at) "
        "VALUES (?,?,?,?,?) ON CONFLICT(project_id, package) DO UPDATE SET "
        "state=excluded.state, note=excluded.note, updated_at=excluded.updated_at",
        (project_id, body.package, body.state, body.note, time.time()),
    )
    return {"ok": True}
