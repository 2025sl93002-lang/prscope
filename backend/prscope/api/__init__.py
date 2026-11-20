"""Shared API dependencies and helpers. SPDX-License-Identifier: MIT"""
from __future__ import annotations

from collections.abc import Iterator
from sqlite3 import Connection

from fastapi import HTTPException

from ..db import get_conn


def db_dep() -> Iterator[Connection]:
    with get_conn() as conn:
        yield conn


def require(obj, message: str = "Not found"):
    if obj is None:
        raise HTTPException(status_code=404, detail=message)
    return obj
