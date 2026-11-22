"""Shared pytest fixtures for the DepLens backend test suite.

All tests run offline and deterministically — no network calls. Online analysis
(registry/OSV) is exercised separately via crafted inputs, not live services.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from deplens.db import Database, set_db

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_PROJECT = REPO_ROOT / "fixtures" / "demo-project"


@pytest.fixture
def db() -> Database:
    database = Database(":memory:")
    set_db(database)
    yield database
    database.close()


@pytest.fixture
def demo_project() -> Path:
    assert DEMO_PROJECT.is_dir(), "demo fixture is missing"
    return DEMO_PROJECT


@pytest.fixture
def tmp_npm_project(tmp_path: Path) -> Path:
    """A minimal npm project with a lockfile and source for usage analysis."""
    (tmp_path / "package.json").write_text(
        """
        {
          "name": "tmp-app", "version": "1.0.0",
          "dependencies": {"lodash": "^4.0.0", "unused-pkg": "^1.0.0"},
          "devDependencies": {"rimraf": "^3.0.0"},
          "scripts": {"clean": "rimraf dist"}
        }
        """
    )
    (tmp_path / "package-lock.json").write_text(
        """
        {
          "name": "tmp-app", "version": "1.0.0", "lockfileVersion": 3,
          "packages": {
            "": {"name": "tmp-app", "version": "1.0.0",
                 "dependencies": {"lodash": "^4.0.0", "unused-pkg": "^1.0.0"},
                 "devDependencies": {"rimraf": "^3.0.0"}},
            "node_modules/lodash": {"version": "4.17.21", "license": "MIT"},
            "node_modules/unused-pkg": {"version": "1.2.0", "license": "MIT"},
            "node_modules/rimraf": {"version": "3.0.2", "dev": true, "license": "ISC",
                                    "dependencies": {"glob": "^7.0.0"}},
            "node_modules/glob": {"version": "7.2.3", "dev": true, "license": "ISC"}
          }
        }
        """
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.js").write_text("const _ = require('lodash');\nmodule.exports = _.noop;\n")
    return tmp_path
