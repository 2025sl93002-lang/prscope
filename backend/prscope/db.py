"""SQLite access layer for PRScope.

Thin, dependency-free wrapper over the stdlib ``sqlite3`` module. The schema is
applied idempotently from ``schema.sql``. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import config

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    config.ensure_data_dir()
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create tables if they do not yet exist."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn = _connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_conn(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Context-managed connection that commits on success, rolls back on error."""
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]
