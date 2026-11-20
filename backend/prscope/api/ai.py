"""Optional local-AI explanation endpoints. SPDX-License-Identifier: MIT

The core product never depends on this. When AI is disabled or the local runtime
is unreachable, these endpoints return the deterministic explanation so the
workflow continues unaffected.
"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from ..models import AIExplainRequest, AIExplainResponse
from ..services import ai_assistant, store
from . import db_dep, require

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _deterministic_context(conn: Connection, req: AIExplainRequest) -> str:
    findings = store.list_risk_findings(conn, req.analysis_id)
    if req.kind == "risk":
        parts = ["Deterministic risk findings for this change:"]
        for f in findings:
            parts.append(f"- {f['title']} ({f['severity']}): {f['explanation']} "
                         f"Evidence: {f['evidence']} Action: {f['suggested_action']}")
        return "\n".join(parts) if findings else "No deterministic risk findings."
    if req.kind == "task" and req.target_id:
        task = store.get_task(conn, req.target_id)
        if task:
            return (f"Verification task '{task['title']}': {task['description']} "
                    f"Reason: {task['reason']}. Steps: {'; '.join(task['steps'])}.")
    analysis = store.get_analysis(conn, req.analysis_id)
    if analysis:
        return (f"Change summary: {analysis['files_changed']} files changed, "
                f"+{analysis['lines_added']}/-{analysis['lines_removed']} lines, "
                f"attention {analysis['attention_level']}.")
    return "No analysis data available."


@router.get("/status")
def ai_status(conn: Connection = Depends(db_dep)):
    enabled = store.get_setting(conn, "ai_enabled", "false") == "true"
    endpoint = store.get_setting(conn, "ai_endpoint", "http://localhost:11434")
    model = store.get_setting(conn, "ai_model", "llama3.2")
    available = ai_assistant.is_available(endpoint) if enabled else False
    return {"enabled": enabled, "endpoint": endpoint, "model": model, "available": available}


@router.post("/explain", response_model=AIExplainResponse)
def explain(req: AIExplainRequest, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, req.analysis_id), "Analysis not found")
    context = _deterministic_context(conn, req)
    enabled = store.get_setting(conn, "ai_enabled", "false") == "true"
    endpoint = store.get_setting(conn, "ai_endpoint", "http://localhost:11434")
    model = store.get_setting(conn, "ai_model", "llama3.2")

    if enabled and ai_assistant.is_available(endpoint):
        prompt = (
            "Explain the following deterministic analysis findings for a code reviewer "
            "in 3-5 sentences. Do not invent anything beyond these findings.\n\n" + context
        )
        text = ai_assistant.explain(endpoint, model, prompt)
        if text:
            return AIExplainResponse(available=True, source="ai", text=text, model=model)

    return AIExplainResponse(
        available=False,
        source="deterministic-fallback",
        text=context,
        model=None,
    )
