# Changelog

All notable changes to PRScope are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-19

Initial proof-of-concept (POC) release of PRScope — Pull Request Verification &
Review Evidence Planner.

### Added

- **Change-to-Verification Traceability** linking CODE CHANGE -> AFFECTED
  COMPONENTS -> POTENTIAL IMPACT -> REQUIRED VERIFICATION -> AVAILABLE EVIDENCE
  -> REVIEW READINESS, with every finding explaining how it was derived rather
  than emitting an opaque score.
- **Verification Evidence Ledger** as the central feature: locally stored
  evidence records, task status audit history, and a verification completeness
  measure (completed applicable tasks / applicable tasks).
- **Deterministic, local-first analysis engine** requiring no AI model, no API
  keys, and no paid or cloud services. Repository source code is never uploaded
  and there is no telemetry.
- **PR diff parsing** using three-dot / merge-base comparison.
- **Deterministic file classification** via ordered rules.
- **Dependency analysis** for Python (standard-library `ast`) and relative JS/TS
  imports (regex), resolving intra-repository edges.
- **Impact analysis** using breadth-first search over reverse dependency edges,
  categorizing files as changed / direct / indirect / unaffected, with a
  per-file Impact Explorer view.
- **Review-attention risk model** built from independent, inspectable, and
  configurable deterministic rule contributions, with low / moderate / high /
  critical levels. Each finding records its title, severity, related files,
  explanation, evidence, suggested action, rule, and score contribution.
- **Verification planning** generating deterministic tasks per changed-file
  category (source, test, api_contract, migration, config, security, ui,
  dependency, infrastructure, build_ci, documentation), each with a stable key,
  description, reason, related files, steps, evidence requirements, priority, and
  status (open / completed / blocked / not_applicable).
- **Evidence records** of types test_result, ci, manual, screenshot, report,
  build, api, security_scan, reviewer_note, and doc, attached to tasks and
  stored locally.
- **Test gap detection** flagging only potential gaps (cautious wording such as
  "potential test gap" and "no related test detected"), based on import and
  naming signals rather than coverage data.
- **Report generation** in Markdown, JSON, and HTML.
- **Optional AI explanations** via a local Ollama runtime, with a deterministic
  fallback so all core features work when Ollama is absent.
- **One-click demo** (`POST /api/demo/setup`) that builds a real local git
  repository ("Payment Processing Refactor") and runs the actual engine against
  it, with no hardcoded results.
- **FastAPI backend** (prefix `/api`) with repositories, analyses, tasks,
  evidence, checklist, reports, settings, AI, and demo routes, plus interactive
  API docs at `/docs`.
- **React 18 + Vite frontend** with a hand-written light/dark CSS design system,
  dependency/impact graph views (`@xyflow/react`), and Markdown rendering.
- **SQLite persistence** via the standard-library `sqlite3` module, with the
  schema in `backend/prscope/schema.sql`.
- **Security controls**: repository path validation with path-traversal
  protection, git ref validation via a strict allow-list regex, git executed via
  subprocess with fixed argument lists and no shell, per-file and diff size caps,
  Pydantic input validation, and parameterized SQLite queries. PRScope never
  executes repository code or installs dependencies from the analyzed repo.

[0.1.0]: https://keepachangelog.com/en/1.0.0/
