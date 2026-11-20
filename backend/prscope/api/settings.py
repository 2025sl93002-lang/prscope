"""Settings endpoints (local, persisted in SQLite). SPDX-License-Identifier: MIT"""
from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from .. import config
from ..models import SettingsModel
from ..services import store
from . import db_dep

router = APIRouter(prefix="/api/settings", tags=["settings"])

_DEFAULTS = {
    "ai_enabled": lambda: "true" if config.AI_ENABLED_DEFAULT else "false",
    "ai_endpoint": lambda: config.AI_ENDPOINT_DEFAULT,
    "ai_model": lambda: config.AI_MODEL_DEFAULT,
    "theme": lambda: "system",
}


@router.get("", response_model=SettingsModel)
def get_settings(conn: Connection = Depends(db_dep)):
    return SettingsModel(
        ai_enabled=store.get_setting(conn, "ai_enabled", _DEFAULTS["ai_enabled"]()) == "true",
        ai_endpoint=store.get_setting(conn, "ai_endpoint", _DEFAULTS["ai_endpoint"]()),
        ai_model=store.get_setting(conn, "ai_model", _DEFAULTS["ai_model"]()),
        theme=store.get_setting(conn, "theme", "system"),
    )


@router.put("", response_model=SettingsModel)
def update_settings(payload: SettingsModel, conn: Connection = Depends(db_dep)):
    store.set_setting(conn, "ai_enabled", "true" if payload.ai_enabled else "false")
    store.set_setting(conn, "ai_endpoint", payload.ai_endpoint)
    store.set_setting(conn, "ai_model", payload.ai_model)
    store.set_setting(conn, "theme", payload.theme)
    return payload
