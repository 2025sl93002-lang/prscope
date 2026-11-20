"""Runtime configuration for PRScope.

All settings are local and overridable via environment variables. No value here
causes network calls or telemetry. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Directory that holds the SQLite database and any local artifacts.
DATA_DIR = Path(os.environ.get("PRSCOPE_DATA_DIR", Path.cwd() / "prscope_data")).resolve()
DB_PATH = Path(os.environ.get("PRSCOPE_DB_PATH", DATA_DIR / "prscope.db")).resolve()

# Safety limits for analysis (resource bounds — see SECURITY.md).
MAX_FILE_BYTES = _env_int("PRSCOPE_MAX_FILE_BYTES", 2_000_000)        # per-file read cap
MAX_SOURCE_FILES = _env_int("PRSCOPE_MAX_SOURCE_FILES", 20_000)       # repo scan cap
MAX_DIFF_FILES = _env_int("PRSCOPE_MAX_DIFF_FILES", 5_000)            # changed-file cap
GIT_TIMEOUT_SECONDS = _env_int("PRSCOPE_GIT_TIMEOUT", 60)

# Optional: allow-list of base directories a repository path must live under.
# Empty => any readable local git repo is allowed (POC default, documented).
_allow = os.environ.get("PRSCOPE_ALLOWED_ROOTS", "").strip()
ALLOWED_ROOTS = [Path(p).resolve() for p in _allow.split(os.pathsep) if p] if _allow else []

# CORS origins for the local dev frontend.
CORS_ORIGINS = os.environ.get(
    "PRSCOPE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Optional local AI (Ollama). Disabled by default; core never depends on it.
AI_ENABLED_DEFAULT = os.environ.get("PRSCOPE_AI_ENABLED", "false").lower() == "true"
AI_ENDPOINT_DEFAULT = os.environ.get("PRSCOPE_AI_ENDPOINT", "http://localhost:11434")
AI_MODEL_DEFAULT = os.environ.get("PRSCOPE_AI_MODEL", "llama3.2")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
