"""Pydantic models — the API contract shared by every service and the frontend.

These mirror the SQLite schema (``schema.sql``) and define request/response
shapes for the REST API. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #


class ChangeType(str, Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"
    renamed = "renamed"


class FileCategory(str, Enum):
    source = "source"
    test = "test"
    config = "config"
    infrastructure = "infrastructure"
    migration = "migration"
    api_contract = "api_contract"
    documentation = "documentation"
    dependency = "dependency"
    security = "security"
    build_ci = "build_ci"
    ui = "ui"
    unknown = "unknown"


class AttentionLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class TaskStatus(str, Enum):
    open = "open"
    completed = "completed"
    blocked = "blocked"
    not_applicable = "not_applicable"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ImpactType(str, Enum):
    changed = "changed"
    direct = "direct"
    indirect = "indirect"
    unaffected = "unaffected"


class EvidenceType(str, Enum):
    test_result = "test_result"
    ci = "ci"
    manual = "manual"
    screenshot = "screenshot"
    report = "report"
    build = "build"
    api = "api"
    security_scan = "security_scan"
    reviewer_note = "reviewer_note"
    doc = "doc"


class AnalysisStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


# --------------------------------------------------------------------------- #
# Repositories
# --------------------------------------------------------------------------- #


class RepositoryCreate(BaseModel):
    path: str = Field(..., description="Absolute or relative path to a local git repository")
    name: str | None = Field(None, description="Optional display name; defaults to folder name")


class Repository(BaseModel):
    id: int
    name: str
    path: str
    default_branch: str | None = None
    created_at: str


class RefInfo(BaseModel):
    name: str
    kind: str  # branch | tag | head
    commit: str


class RepositoryDetail(Repository):
    branches: list[str] = []
    recent_commits: list[dict] = []
    head: str | None = None


# --------------------------------------------------------------------------- #
# Analyses & changed files
# --------------------------------------------------------------------------- #


class AnalysisCreate(BaseModel):
    repository_id: int
    base_ref: str
    target_ref: str


class ChangedFile(BaseModel):
    id: int | None = None
    path: str
    old_path: str | None = None
    change_type: ChangeType
    lines_added: int = 0
    lines_removed: int = 0
    category: FileCategory = FileCategory.unknown
    classification_reason: str | None = None
    confidence: float = 0.0
    matched_rule: str | None = None


class Analysis(BaseModel):
    id: int
    repository_id: int
    base_ref: str
    target_ref: str
    status: AnalysisStatus
    error: str | None = None
    files_changed: int = 0
    files_added: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    files_renamed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    attention_level: AttentionLevel | None = None
    risk_score: int = 0
    created_at: str


# --------------------------------------------------------------------------- #
# Dependency graph & impact
# --------------------------------------------------------------------------- #


class DependencyEdge(BaseModel):
    source_path: str
    target_path: str
    relation_type: str  # import | reference
    detection: str = "direct"  # direct | inferred


class ImpactNode(BaseModel):
    path: str
    impact_type: ImpactType
    distance: int = 0
    category: str | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    impact_type: ImpactType
    category: str | None = None
    distance: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    relation_type: str
    detection: str


class DependencyGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    function_level: bool = False
    note: str | None = None


class FileImpact(BaseModel):
    """Per-file impact view used by the Impact Explorer."""
    path: str
    category: str | None = None
    direct_dependencies: list[str] = []      # files this file imports
    reverse_dependencies: list[str] = []     # files that import this file
    downstream_impact: list[str] = []        # indirect reverse-dependency closure
    related_tests: list[str] = []
    path_explanations: list[str] = []


# --------------------------------------------------------------------------- #
# Risk
# --------------------------------------------------------------------------- #


class RiskFinding(BaseModel):
    id: int | None = None
    title: str
    severity: AttentionLevel
    related_files: list[str] = []
    explanation: str
    evidence: str
    suggested_action: str
    rule: str
    score_contribution: int = 0


class RiskReport(BaseModel):
    attention_level: AttentionLevel
    score: int
    findings: list[RiskFinding] = []
    methodology_note: str


# --------------------------------------------------------------------------- #
# Verification tasks, history, evidence
# --------------------------------------------------------------------------- #


class VerificationTask(BaseModel):
    id: int | None = None
    task_key: str
    title: str
    description: str
    reason: str
    related_files: list[str] = []
    verification_type: str
    priority: Priority = Priority.medium
    status: TaskStatus = TaskStatus.open
    steps: list[str] = []
    evidence_requirements: list[str] = []
    generated: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    title: str | None = None
    description: str | None = None
    priority: Priority | None = None
    note: str | None = None
    actor: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    verification_type: str = "manual"
    priority: Priority = Priority.medium
    related_files: list[str] = []
    steps: list[str] = []
    evidence_requirements: list[str] = []


class TaskHistoryEntry(BaseModel):
    id: int
    from_status: str | None
    to_status: str
    note: str | None = None
    actor: str | None = None
    created_at: str


class EvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    note: str | None = None
    link: str | None = None
    command: str | None = None
    result: str | None = None
    performed_by: str | None = None


class EvidenceRecord(EvidenceCreate):
    id: int
    task_id: int
    analysis_id: int
    created_at: str


# --------------------------------------------------------------------------- #
# Test gaps
# --------------------------------------------------------------------------- #


class TestGap(BaseModel):
    id: int | None = None
    changed_file: str
    related_tests: list[str] = []
    detection_method: str
    missing_coverage: str
    recommended_tests: list[str] = []
    severity: AttentionLevel = AttentionLevel.moderate


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #


class ChecklistItem(BaseModel):
    id: int | None = None
    text: str
    checked: bool = False
    reviewer_note: str | None = None
    source: str = "generated"  # generated | custom
    sort_order: int = 0
    created_at: str | None = None


class ChecklistItemCreate(BaseModel):
    text: str


class ChecklistItemUpdate(BaseModel):
    text: str | None = None
    checked: bool | None = None
    reviewer_note: str | None = None


# --------------------------------------------------------------------------- #
# Review readiness
# --------------------------------------------------------------------------- #


class ReviewReadiness(BaseModel):
    attention_level: AttentionLevel | None = None
    risk_score: int = 0
    total_tasks: int = 0
    applicable_tasks: int = 0
    completed_tasks: int = 0
    pending_tasks: int = 0
    blocked_tasks: int = 0
    not_applicable_tasks: int = 0
    tasks_with_evidence: int = 0
    tasks_without_evidence: int = 0
    completeness_percent: float = 0.0
    completeness_label: str = ""
    test_gap_count: int = 0
    risk_finding_count: int = 0
    changed_file_count: int = 0
    affected_module_count: int = 0


# --------------------------------------------------------------------------- #
# Settings & AI
# --------------------------------------------------------------------------- #


class SettingsModel(BaseModel):
    ai_enabled: bool = False
    ai_endpoint: str = "http://localhost:11434"
    ai_model: str = "llama3.2"
    theme: str = "system"  # system | light | dark


class AIExplainRequest(BaseModel):
    analysis_id: int
    kind: str = "risk"  # risk | task | summary
    target_id: int | None = None


class AIExplainResponse(BaseModel):
    available: bool
    source: str  # "ai" | "deterministic-fallback"
    text: str
    model: str | None = None
