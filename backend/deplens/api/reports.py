"""Report export endpoints (Markdown, JSON, CSV)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from deplens.api.deps import db_dep
from deplens.db import Database
from deplens.report import build_report_data, render_csv, render_json, render_markdown

router = APIRouter(prefix="/api/scans", tags=["reports"])


@router.get("/{scan_id}/report")
def export_report(
    scan_id: int,
    format: str = Query("markdown", pattern="^(markdown|json|csv)$"),
    db: Database = Depends(db_dep),
):
    try:
        data = build_report_data(db, scan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if format == "json":
        return PlainTextResponse(render_json(data), media_type="application/json")
    if format == "csv":
        return PlainTextResponse(
            render_csv(data),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="deplens-scan-{scan_id}.csv"'},
        )
    return PlainTextResponse(render_markdown(data), media_type="text/markdown")
