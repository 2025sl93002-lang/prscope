"""Report export endpoints (Markdown / JSON / HTML). SPDX-License-Identifier: MIT"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from ..services import report_generator, store
from . import db_dep, require

router = APIRouter(prefix="/api/analyses", tags=["reports"])


@router.get("/{analysis_id}/report.json")
def report_json(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return JSONResponse(report_generator.build_json(conn, analysis_id))


@router.get("/{analysis_id}/report.md", response_class=PlainTextResponse)
def report_markdown(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return PlainTextResponse(
        report_generator.build_markdown(conn, analysis_id),
        headers={"Content-Disposition": f'attachment; filename="prscope-report-{analysis_id}.md"'},
    )


@router.get("/{analysis_id}/report.html", response_class=HTMLResponse)
def report_html(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return HTMLResponse(report_generator.build_html(conn, analysis_id))
