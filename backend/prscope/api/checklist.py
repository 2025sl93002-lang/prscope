"""Review checklist endpoints. SPDX-License-Identifier: MIT"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from ..models import ChecklistItem, ChecklistItemCreate, ChecklistItemUpdate
from ..services import store
from . import db_dep, require

router = APIRouter(prefix="/api", tags=["checklist"])


@router.get("/analyses/{analysis_id}/checklist", response_model=list[ChecklistItem])
def list_checklist(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return store.list_checklist(conn, analysis_id)


@router.post("/analyses/{analysis_id}/checklist", response_model=ChecklistItem, status_code=201)
def add_item(analysis_id: int, payload: ChecklistItemCreate, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    item_id = store.add_checklist_item(conn, analysis_id, payload.text)
    items = {i["id"]: i for i in store.list_checklist(conn, analysis_id)}
    return items[item_id]


@router.patch("/checklist/{item_id}", response_model=ChecklistItem)
def update_item(item_id: int, payload: ChecklistItemUpdate, conn: Connection = Depends(db_dep)):
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    store.update_checklist_item(conn, item_id, fields)
    row = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
    require(row, "Checklist item not found")
    d = dict(row)
    d["checked"] = bool(d["checked"])
    return d


@router.delete("/checklist/{item_id}", status_code=204)
def delete_item(item_id: int, conn: Connection = Depends(db_dep)):
    store.delete_checklist_item(conn, item_id)
