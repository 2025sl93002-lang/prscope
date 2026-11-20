"""FastAPI application entry point for PRScope.

Local-first. CORS is restricted to the local dev frontend. In a packaged build
the compiled frontend (``frontend/dist``) is served as static files so the whole
product runs from a single process. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, config, db
from .api import (
    ai as ai_router,
)
from .api import (
    analyses,
    checklist,
    demo,
    evidence,
    reports,
    repositories,
    verification,
)
from .api import (
    settings as settings_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.ensure_data_dir()
    db.init_db()
    yield


app = FastAPI(
    title="PRScope API",
    version=__version__,
    description="Pull Request Verification & Review Evidence Planner — local, deterministic.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "version": __version__, "name": "PRScope"}


app.include_router(repositories.router)
app.include_router(analyses.router)
app.include_router(verification.router)
app.include_router(evidence.router)
app.include_router(checklist.router)
app.include_router(reports.router)
app.include_router(settings_router.router)
app.include_router(ai_router.router)
app.include_router(demo.router)

# Optionally serve the built frontend (single-process deployment).
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        candidate = _DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")


def run() -> None:
    """Console-script entry point: ``prscope``."""
    import uvicorn

    uvicorn.run("prscope.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
