"""Projects and scan lifecycle endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deplens.api.deps import db_dep
from deplens.db import Database
from deplens.scanner import ScanError, run_scan
from deplens.services.safety import PathSafetyError

router = APIRouter(prefix="/api", tags=["projects"])


class ScanRequest(BaseModel):
    path: str
    online: bool = True


@router.get("/projects")
def list_projects(db: Database = Depends(db_dep)):
    return {"projects": db.get_projects()}


@router.get("/demo")
def demo_path():
    """Return the absolute path of the bundled demo fixture for one-click scanning."""
    # backend/deplens/api/projects.py -> repo root is four parents up.
    repo_root = Path(__file__).resolve().parents[3]
    demo = repo_root / "fixtures" / "demo-project"
    return {"path": str(demo), "exists": demo.is_dir()}


@router.post("/scan")
async def scan_project(req: ScanRequest, db: Database = Depends(db_dep)):
    try:
        scan_id = await run_scan(db, req.path, online=req.online)
    except PathSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ScanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    scan = db.query_one("SELECT project_id FROM scans WHERE id=?", (scan_id,))
    return {"scan_id": scan_id, "project_id": scan["project_id"]}


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Database = Depends(db_dep)):
    if db.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete_project(project_id)
    return {"ok": True}


@router.get("/projects/{project_id}/scans")
def project_scans(project_id: int, db: Database = Depends(db_dep)):
    if db.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = db.query(
        "SELECT id, created_at, status, online, health_score, health_grade, "
        "health_confidence, summary_json FROM scans WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )
    scans = []
    for r in rows:
        summary = json.loads(r["summary_json"]) if r["summary_json"] else {}
        scans.append(
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "status": r["status"],
                "online": bool(r["online"]),
                "health_score": r["health_score"],
                "health_grade": r["health_grade"],
                "health_confidence": r["health_confidence"],
                "total": summary.get("total"),
                "vulnerable_packages": summary.get("vulnerable_packages"),
                "outdated": summary.get("outdated"),
                "license_warnings": summary.get("license_warnings"),
            }
        )
    return {"scans": scans}
