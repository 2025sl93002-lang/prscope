"""SQLite persistence for DepLens.

Local-first storage: projects, scans, resolved packages, edges, vulnerabilities,
decisions, usage overrides and settings. Uses the stdlib ``sqlite3`` driver (no
ORM, no extra dependency). The schema is versioned via a ``meta`` table so future
migrations are explicit.

No personal data is stored — only project paths the user chose and package
analysis results.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

DEFAULT_DB_PATH = os.environ.get(
    "DEPLENS_DB",
    str(Path.home() / ".deplens" / "deplens.db"),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    ecosystem TEXT NOT NULL DEFAULT 'npm',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    status TEXT NOT NULL,
    online INTEGER NOT NULL,
    lockfile_format TEXT,
    root_name TEXT,
    root_version TEXT,
    health_score INTEGER,
    health_grade TEXT,
    health_confidence TEXT,
    summary_json TEXT,
    stages_json TEXT,
    warnings_json TEXT
);

CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    is_direct INTEGER NOT NULL,
    scope TEXT NOT NULL,
    depth INTEGER,
    dependents INTEGER,
    path_count INTEGER,
    update_type TEXT,
    latest TEXT,
    license TEXT,
    license_family TEXT,
    license_verdict TEXT,
    usage_status TEXT,
    maintenance_status TEXT,
    max_severity TEXT,
    vuln_count INTEGER DEFAULT 0,
    data_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_packages_scan ON packages(scan_id);
CREATE INDEX IF NOT EXISTS idx_packages_name ON packages(scan_id, name);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    spec TEXT
);
CREATE INDEX IF NOT EXISTS idx_edges_scan ON edges(scan_id);

CREATE TABLE IF NOT EXISTS vulnerabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    package TEXT NOT NULL,
    installed_version TEXT NOT NULL,
    osv_id TEXT NOT NULL,
    cve TEXT,
    severity TEXT,
    summary TEXT,
    fixed_version TEXT,
    url TEXT,
    published TEXT,
    data_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_vulns_scan ON vulnerabilities(scan_id);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    package TEXT NOT NULL,
    current_version TEXT,
    action TEXT NOT NULL,
    proposed_version TEXT,
    decision TEXT NOT NULL,
    reason TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    impact_json TEXT,
    verification_json TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);

CREATE TABLE IF NOT EXISTS usage_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    package TEXT NOT NULL,
    state TEXT NOT NULL,
    note TEXT,
    updated_at REAL NOT NULL,
    UNIQUE(project_id, package)
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""


class Database:
    def __init__(self, path: str = DEFAULT_DB_PATH):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(_SCHEMA)
            row = self._conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            self._conn.commit()

    def close(self):
        self._conn.close()

    # -- low-level helpers ---------------------------------------------------
    def execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def executemany(self, sql: str, seq):
        with self._lock:
            self._conn.executemany(sql, seq)
            self._conn.commit()

    # -- projects ------------------------------------------------------------
    def upsert_project(self, name: str, path: str, ecosystem: str = "npm") -> int:
        existing = self.query_one("SELECT id FROM projects WHERE path=?", (path,))
        if existing:
            self.execute("UPDATE projects SET name=? WHERE id=?", (name, existing["id"]))
            return existing["id"]
        cur = self.execute(
            "INSERT INTO projects(name, path, ecosystem, created_at) VALUES (?,?,?,?)",
            (name, path, ecosystem, time.time()),
        )
        return cur.lastrowid

    def get_projects(self) -> List[Dict[str, Any]]:
        rows = self.query("SELECT * FROM projects ORDER BY created_at DESC")
        projects = []
        for r in rows:
            last = self.query_one(
                "SELECT id, created_at, status, health_score, health_grade "
                "FROM scans WHERE project_id=? ORDER BY created_at DESC LIMIT 1",
                (r["id"],),
            )
            projects.append(
                {
                    **dict(r),
                    "last_scan": dict(last) if last else None,
                }
            )
        return projects

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        row = self.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
        return dict(row) if row else None

    def delete_project(self, project_id: int):
        self.execute("DELETE FROM projects WHERE id=?", (project_id,))

    # -- settings ------------------------------------------------------------
    def get_setting(self, key: str, default=None):
        row = self.query_one("SELECT value FROM settings WHERE key=?", (key,))
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (ValueError, TypeError):
            return row["value"]

    def set_setting(self, key: str, value):
        self.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )


_db_singleton: Optional[Database] = None


def get_db() -> Database:
    global _db_singleton
    if _db_singleton is None:
        _db_singleton = Database()
    return _db_singleton


def set_db(db: Database):
    """Used by tests to inject an in-memory database."""
    global _db_singleton
    _db_singleton = db
