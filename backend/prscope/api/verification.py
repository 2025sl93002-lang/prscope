"""Verification task & review-readiness endpoints. SPDX-License-Identifier: MIT"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    ReviewReadiness,
    TaskCreate,
    TaskHistoryEntry,
    TaskUpdate,
    VerificationTask,
)
from ..services import evidence_manager, store
from . import db_dep, require

router = APIRouter(prefix="/api", tags=["verification"])


@router.get("/analyses/{analysis_id}/tasks", response_model=list[VerificationTask])
def list_tasks(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return store.list_tasks(conn, analysis_id)


@router.post("/analyses/{analysis_id}/tasks", response_model=VerificationTask, status_code=201)
def create_task(analysis_id: int, payload: TaskCreate, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    task_id = store.add_task(conn, analysis_id, payload.model_dump())
    return store.get_task(conn, task_id)


@router.get("/analyses/{analysis_id}/readiness", response_model=ReviewReadiness)
def readiness(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return evidence_manager.compute_readiness(conn, analysis_id)


@router.get("/tasks/{task_id}", response_model=VerificationTask)
def get_task(task_id: int, conn: Connection = Depends(db_dep)):
    return require(store.get_task(conn, task_id), "Task not found")


@router.patch("/tasks/{task_id}", response_model=VerificationTask)
def update_task(task_id: int, payload: TaskUpdate, conn: Connection = Depends(db_dep)):
    task = require(store.get_task(conn, task_id), "Task not found")
    fields = {}
    for key in ("title", "description"):
        val = getattr(payload, key)
        if val is not None:
            fields[key] = val
    if payload.priority is not None:
        fields["priority"] = payload.priority.value
    if fields:
        store.update_task_fields(conn, task_id, fields)
    if payload.status is not None and payload.status.value != task["status"]:
        try:
            evidence_manager.change_task_status(
                conn, task_id, payload.status.value, payload.note, payload.actor
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return store.get_task(conn, task_id)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, conn: Connection = Depends(db_dep)):
    task = require(store.get_task(conn, task_id), "Task not found")
    if task["generated"]:
        raise HTTPException(status_code=400, detail="Generated tasks cannot be deleted; mark N/A instead.")
    store.delete_task(conn, task_id)


@router.get("/tasks/{task_id}/history", response_model=list[TaskHistoryEntry])
def task_history(task_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_task(conn, task_id), "Task not found")
    return evidence_manager.list_task_history(conn, task_id)
