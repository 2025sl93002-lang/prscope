"""Impact simulator endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deplens.analyzers.impact import report_to_dict, simulate
from deplens.api.deps import db_dep
from deplens.db import Database

router = APIRouter(prefix="/api/scans", tags=["impact"])


class ImpactRequest(BaseModel):
    package: str
    action: str  # upgrade | remove | replace | keep
    proposed_version: Optional[str] = None
    alternative: Optional[str] = None
    online: bool = True


@router.post("/{scan_id}/impact")
async def run_impact(scan_id: int, req: ImpactRequest, db: Database = Depends(db_dep)):
    if db.query_one("SELECT id FROM scans WHERE id=?", (scan_id,)) is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    alternative_info = None
    if req.action == "replace" and req.alternative and req.online:
        from deplens.services.registry import RegistryClient

        try:
            async with RegistryClient() as reg:
                info = await reg.get(req.alternative)
            if info.available:
                alternative_info = {
                    "license": info.license,
                    "latest": info.latest,
                    "modified": info.modified,
                    "deprecated": info.deprecated,
                    "description": info.description,
                }
        except Exception:
            alternative_info = None

    try:
        report = simulate(
            db, scan_id, req.package, req.action,
            proposed_version=req.proposed_version,
            alternative=req.alternative,
            alternative_info=alternative_info,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return report_to_dict(report)
