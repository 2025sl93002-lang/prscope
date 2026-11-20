"""Analysis endpoints: create/run analysis and read its artifacts.

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    Analysis,
    AnalysisCreate,
    ChangedFile,
    DependencyGraph,
    FileImpact,
    ImpactNode,
    RiskReport,
    TestGap,
)
from ..services import analysis_service, impact_analyzer, store
from ..services import repository_manager as rm
from ..services.gitutil import GitError
from . import db_dep, require

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.get("", response_model=list[Analysis])
def list_analyses(repository_id: int | None = None, conn: Connection = Depends(db_dep)):
    return store.list_analyses(conn, repository_id)


@router.post("", response_model=Analysis, status_code=201)
def create_analysis(payload: AnalysisCreate, conn: Connection = Depends(db_dep)):
    repo = require(store.get_repository(conn, payload.repository_id), "Repository not found")
    try:
        repo_path = rm.validate_repository(repo["path"])
    except GitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis_id = store.create_analysis(conn, repo["id"], payload.base_ref, payload.target_ref)
    try:
        analysis_service.run_analysis(conn, analysis_id, repo_path)
    except GitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - surfaced to client
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    return store.get_analysis(conn, analysis_id)


@router.get("/{analysis_id}", response_model=Analysis)
def get_analysis(analysis_id: int, conn: Connection = Depends(db_dep)):
    return require(store.get_analysis(conn, analysis_id), "Analysis not found")


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    store.delete_analysis(conn, analysis_id)


@router.get("/{analysis_id}/changes", response_model=list[ChangedFile])
def get_changes(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return store.list_changed_files(conn, analysis_id)


@router.get("/{analysis_id}/graph", response_model=DependencyGraph)
def get_graph(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    edges = store.list_edges(conn, analysis_id)
    impact_rows = store.list_impact(conn, analysis_id)
    changed = [f["path"] for f in store.list_changed_files(conn, analysis_id)]
    categories = {f["path"]: f["category"] for f in store.list_changed_files(conn, analysis_id)}
    impact = impact_analyzer.ImpactResult(nodes=impact_rows)
    all_paths = {e[0] for e in edges} | {e[1] for e in edges} | set(changed)
    payload = impact_analyzer.build_graph_payload(all_paths, edges, impact, categories, changed)
    payload["function_level"] = False
    payload["note"] = (
        "File-level dependency graph. Function-level resolution is not performed; "
        "edges represent import/reference relationships between files."
    )
    return payload


@router.get("/{analysis_id}/impact", response_model=list[ImpactNode])
def get_impact(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return store.list_impact(conn, analysis_id)


@router.get("/{analysis_id}/impact/file", response_model=FileImpact)
def get_file_impact(analysis_id: int, path: str, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    edges = store.list_edges(conn, analysis_id)
    categories = {f["path"]: f["category"] for f in store.list_changed_files(conn, analysis_id)}
    return impact_analyzer.file_impact(path, edges, categories)


@router.get("/{analysis_id}/risk", response_model=RiskReport)
def get_risk(analysis_id: int, conn: Connection = Depends(db_dep)):
    analysis = require(store.get_analysis(conn, analysis_id), "Analysis not found")
    findings = store.list_risk_findings(conn, analysis_id)
    return {
        "attention_level": analysis["attention_level"] or "low",
        "score": analysis["risk_score"],
        "findings": findings,
        "methodology_note": (
            "Attention level is an additive score of independent deterministic rules. "
            "Thresholds: moderate>=20, high>=45, critical>=75. See docs/RISK_MODEL.md."
        ),
    }


@router.get("/{analysis_id}/test-gaps", response_model=list[TestGap])
def get_test_gaps(analysis_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_analysis(conn, analysis_id), "Analysis not found")
    return store.list_test_gaps(conn, analysis_id)
