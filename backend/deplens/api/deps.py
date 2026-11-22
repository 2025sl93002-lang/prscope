"""Shared API dependencies."""

from __future__ import annotations

from deplens.db import Database, get_db


def db_dep() -> Database:
    return get_db()
