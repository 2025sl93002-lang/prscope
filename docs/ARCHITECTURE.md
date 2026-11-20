# PRScope Architecture

> Pull Request Verification & Review Evidence Planner
> *Understand the impact. Know what to verify. Review with evidence.*

This document describes how PRScope is structured, how a request flows through
the system, the deterministic analysis pipeline, each backend service module and
its responsibility, and the persistence schema.

PRScope is a **modular monolith**: a single FastAPI process exposes a REST API,
delegates all work to a set of focused, independently testable service modules,
and persists results to a local SQLite database. A React single-page application
is the client. There are no distributed components, no message queues, and no
external services in the core product.

---

## 1. High-level structure

```
                           Browser (localhost)
 ┌───────────────────────────────────────────────────────────────────┐
 │  Frontend — React 18 + TypeScript + Vite 5                          │
 │  pages/  components/  api.ts  styles.css                            │
 │  Graph view via @xyflow/react · Markdown via react-markdown         │
 └───────────────────────────────┬───────────────────────────────────┘
                                  │  HTTP/JSON  (dev: Vite proxy /api → :8000)
                                  ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  FastAPI REST API  (prefix /api)                                    │
 │  api/repositories · analyses · verification · evidence · checklist  │
 │  api/reports · settings · ai · demo        Swagger UI at /docs      │
 └───────────────────────────────┬───────────────────────────────────┘
                                  │  in-process Python calls
                                  ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  Services engine  (prscope/services/*)                              │
 │  Deterministic analysis pipeline + persistence + reporting          │
 │  Optional: ai_assistant → local Ollama runtime                      │
 └───────────────────────────────┬───────────────────────────────────┘
                                  │  stdlib sqlite3 (parameterized)
                                  ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  SQLite database  (file on local disk, schema.sql)                  │
 └───────────────────────────────────────────────────────────────────┘

 Side inputs (read-only, never uploaded):
   local git repositories ──▶ gitutil/git_diff (subprocess git, no shell)
```

Key properties:

- **Local-first.** Core analysis is fully deterministic and requires no AI
  model, no API keys, and no paid or cloud services.
- **Repository source is never uploaded** anywhere, and there is no telemetry.
- **AI is optional.** The `ai_assistant` module talks to a local Ollama runtime
  for natural-language explanations only. If Ollama is absent, every core
  feature still works via the deterministic path.
- **Single process in a packaged build.** When `frontend/dist` exists, FastAPI
  serves the compiled SPA as static files, so the whole product runs from one
  process. In development the Vite dev server (`http://localhost:5173`) proxies
  `/api` to the backend on port 8000.

---

## 2. Repository layout

```
backend/
  prscope/
    config.py        # settings, data dir, env-var resolution
    db.py            # SQLite connection + schema bootstrap
    models.py        # Pydantic v2 request/response models
    schema.sql       # table definitions
    main.py          # FastAPI app, routers, static-SPA mount
    services/        # the analysis engine (see §4)
    api/             # HTTP routers, one module per resource
    tests/           # pytest suite (69 passing backend tests)
frontend/
  src/pages/         # route-level screens
  src/components/    # reusable UI (incl. @xyflow/react graph)
  src/api.ts         # typed API client
  src/styles.css     # hand-written CSS design system (light/dark)
docs/                # this documentation
.github/             # CI workflows + issue/PR templates
scripts/             # helper scripts
```

---

## 3. The analysis pipeline

An analysis is the central unit of work. `services/analysis_service.py` is the
orchestrator: given a connection, an analysis id, and a repository path, it runs
the following stages **in strict order**, persisting every artifact as it goes,
and sets the analysis status to `running` → `complete` (or `failed` on error).

```
  (1) diff  ─▶  (2) classify  ─▶  (3) dependency graph  ─▶  (4) impact
                                                                 │
   (8) review checklist ◀─ (7) test gaps ◀─ (6) verification ◀─ (5) risk
```

| # | Stage | Module | What it produces |
|---|-------|--------|------------------|
| 1 | Diff | `git_diff` | Changed files (path, old_path, change type, line counts) for the PR range, plus a summary. |
| 2 | Classify | `classifier` | A deterministic category for every changed file. |
| 3 | Dependency graph | `dependency_analyzer` | Intra-repo import/reference edges at the target commit. |
| 4 | Impact | `impact_analyzer` | Each file labelled `changed` / `direct` / `indirect` / `unaffected` with hop distance. |
| 5 | Risk | `risk_analyzer` | Review-attention findings and an attention level (see `docs/RISK_MODEL.md`). |
| 6 | Verification plan | `verification_planner` | Deterministic verification tasks per changed-file category. |
| 7 | Test gaps | `test_gap` | Potential (never asserted) test gaps. |
| 8 | Review checklist | `analysis_service` | A de-duplicated checklist built from findings + tasks + recommended tests. |

Each stage consumes only the outputs of the stages before it. Because every
stage is deterministic, the same repository range always yields the same result,
and every finding can be traced back to the input that produced it — the core of
PRScope's **Change-to-Verification Traceability**:

```
  CODE CHANGE ─▶ AFFECTED COMPONENTS ─▶ POTENTIAL IMPACT ─▶
      REQUIRED VERIFICATION ─▶ AVAILABLE EVIDENCE ─▶ REVIEW READINESS
```

---

## 4. Service modules and responsibilities

All modules live in `backend/prscope/services/`.

- **`gitutil`** — Safe git execution. Runs git through `subprocess` with fixed
  argument lists and **no shell**, and validates repository paths and refs
  before any command runs (strict allow-list regex for refs; path-traversal
  protection). The single choke point for touching a repository.
- **`repository_manager`** — Registers, validates, and resolves repositories
  that the user wants to analyze (name, path, default branch).
- **`git_diff`** — Computes the PR diff using three-dot / merge-base semantics,
  parses per-file change type and line counts, and summarizes totals.
- **`classifier`** — Applies ordered, deterministic rules to map each changed
  file path to a category (source, test, api_contract, migration, config,
  security, ui, dependency, infrastructure, build_ci, documentation, …), with a
  recorded reason, confidence, and matched rule.
- **`dependency_analyzer`** — Builds the intra-repo dependency graph: Python
  imports via the stdlib `ast`, and relative JS/TS imports via regex. Resolves
  only edges that point inside the repository.
- **`impact_analyzer`** — Runs a breadth-first search over the **reverse**
  dependency edges to classify every file as `changed`, `direct`, `indirect`, or
  `unaffected`, recording hop distance, and provides the per-file Impact Explorer
  view and the reverse-dependency (fan-in) counts the risk model consumes.
- **`risk_analyzer`** — Computes review-attention findings by summing
  independent deterministic rule contributions into an attention level. Every
  threshold is defined here and is inspectable and configurable. See
  `docs/RISK_MODEL.md`.
- **`verification_planner`** — Generates verification tasks deterministically,
  one or more per changed-file category, each with a stable key, title,
  description, reason, related files, steps, evidence requirements, and priority.
- **`test_gap`** — Flags **potential** test gaps from imports and naming
  (never from coverage data), using cautious wording and never claiming that no
  tests exist.
- **`evidence_manager`** — The Verification Evidence Ledger: attaches evidence
  records to tasks, records task status-change history, and computes
  verification readiness / completeness.
- **`store`** — All SQLite persistence. Reads and writes every artifact with
  parameterized queries; owns the `replace_*` operations that make a re-run
  idempotent.
- **`report_generator`** — Renders an analysis to Markdown, JSON, or HTML.
- **`analysis_service`** — The orchestrator described in §3.
- **`ai_assistant`** — Optional natural-language explanations via a local Ollama
  runtime. Strictly additive; never required for a core feature.
- **`demo_builder`** — Builds a real local git repository ("Payment Processing
  Refactor") on demand and runs the actual engine against it, so the demo
  reflects genuine output rather than hardcoded results.

---

## 5. Request / data flow

A typical end-to-end interaction:

```
1. User registers a repository
   POST /api/repositories (or /validate)
   → api/repositories → repository_manager → gitutil (validate path/refs)
   → store (persist repository row)

2. User starts an analysis for base_ref..target_ref
   POST /api/analyses
   → api/analyses → store (create analyses row, status=pending)
   → analysis_service.run_analysis(...) runs the 8-stage pipeline (§3),
     persisting changed_files, dependency_edges, impact_nodes, risk_findings,
     verification_tasks, test_gaps, checklist_items; status → complete

3. Frontend reads the results
   GET /api/analyses/{id}/changes | graph | impact | impact/file?path=…
                               | risk | test-gaps | readiness | checklist | evidence
   → api/analyses → store → JSON → React pages render tables + the
     @xyflow/react dependency/impact graph

4. Reviewer works the Evidence Ledger
   PATCH /api/tasks/{id}            (status open|completed|blocked|not_applicable)
   → api/verification → evidence_manager → store (+ task_history audit row)
   POST  /api/tasks/{id}/evidence   (attach evidence record)
   GET   /api/analyses/{id}/readiness  (completed applicable / applicable tasks)

5. Reviewer exports the result
   GET /api/analyses/{id}/report.{md,json,html}
   → api/reports → report_generator → store

   Optional: POST /api/ai/explain  → api/ai → ai_assistant → local Ollama
             (GET /api/ai/status reports availability)
```

The HTTP layer (`api/*`) is thin: it validates input with Pydantic v2 models,
calls a service function, and serializes the result. All domain logic lives in
`services/*`, which keeps the engine fully usable and testable without the web
layer. Interactive API documentation is available at `/docs` (Swagger) while the
server runs.

---

## 6. Database schema

SQLite via the stdlib `sqlite3` module. The schema lives in
`backend/prscope/schema.sql`; `db.py` bootstraps it on startup. Foreign keys are
enabled and child rows cascade on delete, so removing a repository or analysis
removes everything derived from it. All values are written with parameterized
queries.

| Table | Purpose |
|-------|---------|
| `repositories` | Registered local repositories (name, path, default branch). |
| `analyses` | One analysis run: base/target refs, status, file & line counts, attention level, risk score. |
| `changed_files` | Per-file diff entries with change type, line counts, and classification (category, reason, confidence, matched rule). |
| `dependency_edges` | Intra-repo dependency edges (source → target, import/reference, direct/inferred). |
| `impact_nodes` | Impact classification per file (changed/direct/indirect/unaffected) with hop distance. |
| `risk_findings` | Review-attention findings (title, severity, related files, explanation, evidence, suggested action, rule, score contribution). |
| `verification_tasks` | Generated and user-added verification tasks with stable key, steps, evidence requirements, priority, status. |
| `task_history` | Audit trail of task status changes (from/to status, note, actor, timestamp). |
| `evidence_records` | Evidence attached to tasks (type, note, link, command, result, performed_by). |
| `test_gaps` | Potential test gaps flagged by the detector. |
| `checklist_items` | Generated and user-added review checklist items. |
| `settings` | Local application settings (including AI toggles). |

Idempotency is achieved through `store.replace_*` operations: re-running an
analysis replaces the derived rows for that analysis id rather than
accumulating duplicates. User-authored tasks and checklist items are marked
(`generated = 0`) so they survive re-generation of engine output.

---

## 7. Design boundaries and limitations

- Analysis is **file-level static analysis**. It approximates and does not
  guarantee runtime impact.
- Dependency analysis resolves **Python** and **relative JS/TS** imports only;
  bare/package specifiers, `tsconfig` path aliases, and dynamic imports are not
  resolved.
- Test gaps are **potential**, inferred from imports and naming — not from
  coverage data.
- The risk/attention level is **review attention, not a defect probability**.
- **GitHub integration is not implemented** in this POC; it is a documented
  roadmap item and is not mocked.

See `docs/RISK_MODEL.md`, `docs/ORIGINALITY.md`, and `SECURITY.md` for the risk
rules, the originality comparison, and the security model respectively.
