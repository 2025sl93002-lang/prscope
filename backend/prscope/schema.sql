-- PRScope SQLite schema (SPDX-License-Identifier: MIT)
-- Deterministic, local-first storage. No external services.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS repositories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    path        TEXT NOT NULL UNIQUE,
    default_branch TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    base_ref      TEXT NOT NULL,
    target_ref    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',   -- pending|running|complete|failed
    error         TEXT,
    files_changed INTEGER NOT NULL DEFAULT 0,
    files_added   INTEGER NOT NULL DEFAULT 0,
    files_modified INTEGER NOT NULL DEFAULT 0,
    files_deleted INTEGER NOT NULL DEFAULT 0,
    files_renamed INTEGER NOT NULL DEFAULT 0,
    lines_added   INTEGER NOT NULL DEFAULT 0,
    lines_removed INTEGER NOT NULL DEFAULT 0,
    attention_level TEXT,                              -- low|moderate|high|critical
    risk_score    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS changed_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    path          TEXT NOT NULL,
    old_path      TEXT,
    change_type   TEXT NOT NULL,                       -- added|modified|deleted|renamed
    lines_added   INTEGER NOT NULL DEFAULT 0,
    lines_removed INTEGER NOT NULL DEFAULT 0,
    category      TEXT NOT NULL DEFAULT 'unknown',
    classification_reason TEXT,
    confidence    REAL NOT NULL DEFAULT 0.0,
    matched_rule  TEXT
);

CREATE TABLE IF NOT EXISTS dependency_edges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    source_path   TEXT NOT NULL,
    target_path   TEXT NOT NULL,
    relation_type TEXT NOT NULL,                       -- import|reference
    detection     TEXT NOT NULL DEFAULT 'direct'       -- direct|inferred
);

CREATE TABLE IF NOT EXISTS impact_nodes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    path          TEXT NOT NULL,
    impact_type   TEXT NOT NULL,                       -- changed|direct|indirect|unaffected
    distance      INTEGER NOT NULL DEFAULT 0,          -- hops from nearest changed file
    category      TEXT
);

CREATE TABLE IF NOT EXISTS risk_findings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    severity      TEXT NOT NULL,                        -- low|moderate|high|critical
    related_files TEXT NOT NULL DEFAULT '[]',           -- JSON array
    explanation   TEXT NOT NULL,
    evidence      TEXT NOT NULL,
    suggested_action TEXT NOT NULL,
    rule          TEXT NOT NULL,
    score_contribution INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS verification_tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    task_key      TEXT NOT NULL,                        -- stable deterministic id within analysis
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    reason        TEXT NOT NULL,
    related_files TEXT NOT NULL DEFAULT '[]',           -- JSON array
    verification_type TEXT NOT NULL,
    priority      TEXT NOT NULL DEFAULT 'medium',       -- low|medium|high
    status        TEXT NOT NULL DEFAULT 'open',         -- open|completed|blocked|not_applicable
    steps         TEXT NOT NULL DEFAULT '[]',           -- JSON array of strings
    evidence_requirements TEXT NOT NULL DEFAULT '[]',   -- JSON array of strings
    generated     INTEGER NOT NULL DEFAULT 1,           -- 1 = engine-generated, 0 = user-added
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id       INTEGER NOT NULL REFERENCES verification_tasks(id) ON DELETE CASCADE,
    from_status   TEXT,
    to_status     TEXT NOT NULL,
    note          TEXT,
    actor         TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id       INTEGER NOT NULL REFERENCES verification_tasks(id) ON DELETE CASCADE,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,                        -- test_result|ci|manual|screenshot|report|build|api|security_scan|reviewer_note|doc
    note          TEXT,
    link          TEXT,
    command       TEXT,
    result        TEXT,
    performed_by  TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_gaps (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    changed_file  TEXT NOT NULL,
    related_tests TEXT NOT NULL DEFAULT '[]',           -- JSON array
    detection_method TEXT NOT NULL,
    missing_coverage TEXT NOT NULL,
    recommended_tests TEXT NOT NULL DEFAULT '[]',       -- JSON array
    severity      TEXT NOT NULL DEFAULT 'moderate'
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    text          TEXT NOT NULL,
    checked       INTEGER NOT NULL DEFAULT 0,
    reviewer_note TEXT,
    source        TEXT NOT NULL DEFAULT 'generated',    -- generated|custom
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_changed_files_analysis ON changed_files(analysis_id);
CREATE INDEX IF NOT EXISTS idx_dep_edges_analysis ON dependency_edges(analysis_id);
CREATE INDEX IF NOT EXISTS idx_impact_analysis ON impact_nodes(analysis_id);
CREATE INDEX IF NOT EXISTS idx_risk_analysis ON risk_findings(analysis_id);
CREATE INDEX IF NOT EXISTS idx_tasks_analysis ON verification_tasks(analysis_id);
CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence_records(task_id);
CREATE INDEX IF NOT EXISTS idx_gaps_analysis ON test_gaps(analysis_id);
CREATE INDEX IF NOT EXISTS idx_checklist_analysis ON checklist_items(analysis_id);
