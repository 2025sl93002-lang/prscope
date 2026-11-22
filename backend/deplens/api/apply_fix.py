"""Apply-fix endpoints: compute a package.json edit, or write it to disk.

Neither endpoint ever runs npm or any process — writing only edits the manifest
text and keeps a backup. The caller runs ``npm install`` themselves afterwards.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deplens.api.deps import db_dep
from deplens.db import Database
from deplens.services.apply_fix import ApplyError, compute_fix, edit_to_dict, write_fix

router = APIRouter(prefix="/api/scans", tags=["apply-fix"])


class FixRequest(BaseModel):
    packages: Optional[List[str]] = None  # None = all fixable packages


@router.post("/{scan_id}/fix-plan")
def fix_plan(scan_id: int, req: FixRequest, db: Database = Depends(db_dep)):
    """Compute the package.json edit WITHOUT touching disk (copy / patch mode)."""
    try:
        edit = compute_fix(db, scan_id, req.packages)
    except ApplyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return edit_to_dict(edit)


@router.post("/{scan_id}/fix-apply")
def fix_apply(scan_id: int, req: FixRequest, db: Database = Depends(db_dep)):
    """Write the edit to package.json (opt-in), keeping a .bak backup. No install."""
    try:
        edit = write_fix(db, scan_id, req.packages)
    except ApplyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return edit_to_dict(edit)
