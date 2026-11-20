"""Shared pytest fixtures. SPDX-License-Identifier: MIT

A temporary data directory and a freshly-built demo repository are created once
per test session so tests exercise the *real* analysis engine deterministically.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Point PRScope at an isolated temp data dir BEFORE importing the app/config.
_TMP = tempfile.mkdtemp(prefix="prscope_tests_")
os.environ["PRSCOPE_DATA_DIR"] = _TMP

from fastapi.testclient import TestClient  # noqa: E402

from prscope import config, db  # noqa: E402
from prscope.main import app  # noqa: E402
from prscope.services import demo_builder  # noqa: E402


@pytest.fixture(scope="session")
def demo_repo() -> Path:
    return demo_builder.build_demo_repo(Path(_TMP) / "demo_repo", force=True)


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """A clean database per test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    db.init_db(db_path)
    return db_path


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def analyzed_demo(client, demo_repo):
    """Run the demo analysis via the API and return (analysis_id, client)."""
    resp = client.post("/api/demo/setup", params={"force": True})
    assert resp.status_code == 200, resp.text
    return resp.json()["analysis_id"], client
