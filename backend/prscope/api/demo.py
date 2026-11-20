"""Demo setup endpoint — one-click "Payment Processing Refactor" scenario.

Builds a real sample git repository and runs the actual analysis engine against
it. The resulting data is clearly identifiable as a demo (the repository name is
prefixed ``[demo]``). SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from .. import config
from ..services import analysis_service, demo_builder, store
from ..services.gitutil import GitError
from . import db_dep

router = APIRouter(prefix="/api/demo", tags=["demo"])

_DEMO_BASE = "main"
_DEMO_TARGET = "feature/payment-refactor"


@router.post("/setup")
def setup_demo(force: bool = False, conn: Connection = Depends(db_dep)):
    dest = config.DATA_DIR / "demo_repo"
    try:
        repo_path = demo_builder.build_demo_repo(dest, force=force)
    except GitError as exc:
        raise HTTPException(status_code=500, detail=f"Could not build demo repo: {exc}") from exc

    repo_id = store.upsert_repository(conn, "[demo] Payment Processing Refactor", str(repo_path), "main")
    analysis_id = store.create_analysis(conn, repo_id, _DEMO_BASE, _DEMO_TARGET)
    try:
        result = analysis_service.run_analysis(conn, analysis_id, repo_path)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Demo analysis failed: {exc}") from exc

    return {
        "repository_id": repo_id,
        "analysis_id": analysis_id,
        "base_ref": _DEMO_BASE,
        "target_ref": _DEMO_TARGET,
        "is_demo": True,
        "result": result,
    }
