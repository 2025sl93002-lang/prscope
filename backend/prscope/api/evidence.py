"""Evidence ledger endpoints. SPDX-License-Identifier: MIT"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from ..models import EvidenceCreate, EvidenceRecord
from ..services import evidence_manager, store
from . import db_dep, require

router = APIRouter(prefix="/api", tags=["evidence"])


@router.get("/tasks/{task_id}/evidence", response_model=list[EvidenceRecord])
def list_task_evidence(task_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_task(conn, task_id), "Task not found")
    return evidence_manager.list_evidence_for_task(conn, task_id)


@router.post("/tasks/{task_id}/evidence", response_model=EvidenceRecord, status_code=201)
def add_task_evidence(task_id: int, payload: EvidenceCreate, conn: Connection = Depends(db_dep)):
    try:
        return evidence_manager.add_evidence(conn, task_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.get("/analyses/{analysis_id}/evidence", response_model=list[EvidenceRecord])
def list_analysis_evidence(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return evidence_manager.list_evidence_for_analysis(conn, analysis_id)


@router.delete("/evidence/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: int, conn: Connection = Depends(db_dep)):
    evidence_manager.delete_evidence(conn, evidence_id)
