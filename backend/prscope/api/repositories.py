"""Repository endpoints. SPDX-License-Identifier: MIT"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from ..models import Repository, RepositoryCreate, RepositoryDetail
from ..services import repository_manager as rm
from ..services import store
from ..services.gitutil import GitError
from . import db_dep, require

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.get("", response_model=list[Repository])
def list_repositories(conn: Connection = Depends(db_dep)):
    return store.list_repositories(conn)


@router.post("", response_model=Repository, status_code=201)
def create_repository(payload: RepositoryCreate, conn: Connection = Depends(db_dep)):
    try:
        path = rm.validate_repository(payload.path)
    except GitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    name = payload.name or rm.repo_display_name(path)
    repo_id = store.upsert_repository(conn, name, str(path), rm.default_branch(path))
    return store.get_repository(conn, repo_id)


@router.get("/{repo_id}", response_model=RepositoryDetail)
def get_repository(repo_id: int, conn: Connection = Depends(db_dep)):
    repo = require(store.get_repository(conn, repo_id), "Repository not found")
    try:
        meta = rm.metadata(rm.validate_repository(repo["path"]))
    except GitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **repo,
        "branches": meta["branches"] + meta["tags"],
        "recent_commits": meta["recent_commits"],
        "head": meta["head"],
        "default_branch": meta["default_branch"] or repo.get("default_branch"),
    }


@router.delete("/{repo_id}", status_code=204)
def delete_repository(repo_id: int, conn: Connection = Depends(db_dep)):
    require(store.get_repository(conn, repo_id), "Repository not found")
    store.delete_repository(conn, repo_id)


@router.post("/validate")
def validate_path(payload: RepositoryCreate):
    """Validate a path is a usable git repo without persisting it."""
    try:
        path = rm.validate_repository(payload.path)
    except GitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"valid": True, "path": str(path), "name": rm.repo_display_name(path),
            "default_branch": rm.default_branch(path)}
