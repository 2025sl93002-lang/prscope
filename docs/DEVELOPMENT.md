# PRScope Development Guide

This guide covers setting up a development environment for **PRScope**, running
the backend and frontend in watch mode, running tests and lint, the project
layout, and how to extend the engine (classification rules, risk rules,
verification task templates, and API routes).

PRScope is intentionally built on the standard library where possible: git is
invoked via `subprocess` with fixed argument lists (never a shell), Python
dependency parsing uses the stdlib `ast` module, JS/TS parsing uses regex, and
persistence uses the stdlib `sqlite3`. The only runtime third-party dependencies
are FastAPI, Uvicorn, and Pydantic.

---

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Backend setup](#backend-setup)
3. [Frontend setup](#frontend-setup)
4. [Running in watch mode](#running-in-watch-mode)
5. [Running tests](#running-tests)
6. [Linting and type checking](#linting-and-type-checking)
7. [Running the demo](#running-the-demo)
8. [Project layout](#project-layout)
9. [How the engine fits together](#how-the-engine-fits-together)
10. [Extending the engine](#extending-the-engine)
    - [Add a classification rule](#add-a-classification-rule)
    - [Add a risk rule](#add-a-risk-rule)
    - [Add a verification task template](#add-a-verification-task-template)
    - [Extend the API](#extend-the-api)
11. [Coding conventions](#coding-conventions)

---

## Prerequisites

- **Python 3.10+** — developed and tested on 3.11.
- **Node.js** with `npm`.
- **git** on your `PATH`.

---

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` pulls in the runtime dependencies (`fastapi`,
`uvicorn[standard]`, `pydantic`) plus the dev tools: `pytest`, `httpx` (the
FastAPI test client transport), `ruff` (lint + format), and `pip-licenses`
(dependency license audit).

The backend package is `prscope`. Because the project runs from source during
development, set `PYTHONPATH=.` (from the `backend` directory) when invoking it
directly.

---

## Frontend setup

```bash
cd frontend
npm install
```

The frontend is React 18 + TypeScript built with Vite 5. Key libraries:
`react-router-dom` 6 for routing, `@xyflow/react` 12 for the impact graph, and
`react-markdown` 9 for rendering reports. The UI is a hand-written CSS design
system (light/dark) in `src/styles.css` — there is no proprietary UI library.
Tests use `vitest` and `@testing-library/react`.

---

## Running in watch mode

Run the two processes in separate terminals.

### Backend (auto-reload)

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. uvicorn prscope.main:app --port 8000 --reload
```

`--reload` restarts the server when backend files change. The API serves at
`http://127.0.0.1:8000`, with Swagger UI at `/docs` and a health check at
`/api/health`.

### Frontend (HMR)

```bash
cd frontend
npm run dev
```

Vite serves the app at `http://localhost:5173` with hot module replacement and
proxies `/api` to `http://127.0.0.1:8000`, so you develop against the live
backend without CORS friction.

> To test the single-process path (backend serving the built SPA), run
> `npm run build` in `frontend/` and then start the backend; it mounts
> `frontend/dist` automatically when that directory exists.

---

## Running tests

### Backend

```bash
cd backend
PYTHONPATH=. pytest
```

`pyproject.toml` sets `testpaths = ["tests"]` and quiet output. The suite lives in
`backend/tests/` and covers the engine modules individually
(`test_classifier.py`, `test_dependency_analyzer.py`, `test_git_diff.py`,
`test_gitutil.py`, `test_impact_analyzer.py`, `test_risk_analyzer.py`,
`test_test_gap.py`, `test_verification_planner.py`) plus the HTTP API
(`test_api.py`, via the FastAPI test client). Shared fixtures are in
`conftest.py`.

Run a single file or test:

```bash
PYTHONPATH=. pytest tests/test_risk_analyzer.py
PYTHONPATH=. pytest tests/test_api.py -k health
```

### Frontend

```bash
cd frontend
npm test          # vitest run (single pass)
npm run test:watch  # vitest in watch mode
```

Vitest runs in a `jsdom` environment with globals enabled and
`src/test/setup.ts` as the setup file (see `vite.config.ts`).

---

## Linting and type checking

### Backend

```bash
cd backend
ruff check .          # lint
ruff format .         # format (optional)
```

Ruff is configured in `pyproject.toml` with line length 110, target `py310`, and
the rule sets `E, F, I, B, UP, S`. A few rules are intentionally ignored with
documented reasons (e.g. `S101` for asserts, `B008` for FastAPI `Depends()`
defaults, `S310`/`S608` for the guarded localhost Ollama calls and fixed-identifier
SQL). Test files additionally ignore subprocess-related rules.

### Frontend

```bash
cd frontend
npm run lint        # eslint
npm run typecheck   # tsc -b --noEmit
```

---

## Running the demo

The demo builds a **real** local git repository ("Payment Processing Refactor")
and runs the actual engine against it — useful when developing engine changes end
to end.

With the backend running:

```bash
curl -X POST http://localhost:8000/api/demo/setup
```

Or, with the frontend running, click **Run demo** in the app (it calls the same
endpoint). The demo builder lives in `backend/prscope/services/demo_builder.py`.

---

## Project layout

```
backend/
  prscope/
    config.py        # env-driven runtime config (paths, caps, AI defaults)
    db.py            # SQLite connection helpers
    models.py        # Pydantic v2 models + enums (FileCategory, Priority, ...)
    schema.sql       # database schema (see tables below)
    main.py          # FastAPI app, router wiring, SPA mount, `run()` entry point
    services/        # the analysis engine (see below)
    api/             # FastAPI routers, one module per resource group
    tests/           # pytest suite + conftest fixtures
  pyproject.toml     # package metadata, ruff + pytest config
  requirements.txt / requirements-dev.txt

frontend/
  src/
    pages/           # route-level screens (one per sidebar item / analysis tab)
    components/       # reusable UI components
    api.ts           # typed client for the backend API
    styles.css       # hand-written design system (light/dark)
  package.json, vite.config.ts, tsconfig.json

docs/                # documentation (this file, USER_GUIDE, RISK_MODEL, etc.)
.github/             # workflows + issue templates
scripts/             # helper scripts
```

### Database schema

Persistence is SQLite via the stdlib `sqlite3`; the schema is in
`backend/prscope/schema.sql`. Tables: `repositories`, `analyses`,
`changed_files`, `dependency_edges`, `impact_nodes`, `risk_findings`,
`verification_tasks`, `task_history`, `evidence_records`, `test_gaps`,
`checklist_items`, and `settings`.

---

## How the engine fits together

All analysis logic lives in `backend/prscope/services/`. The `analysis_service`
module is the orchestrator; it drives the other modules in order and persists
results via `store`:

| Module                 | Responsibility                                                            |
|------------------------|---------------------------------------------------------------------------|
| `gitutil`              | Safe git execution + path/ref validation                                  |
| `repository_manager`   | Register and validate repositories                                        |
| `git_diff`             | Three-dot / merge-base PR diff parsing                                    |
| `classifier`           | Ordered, deterministic file classification                                |
| `dependency_analyzer`  | Python (`ast`) + relative JS/TS (regex) intra-repo edge resolution        |
| `impact_analyzer`      | BFS over reverse edges → changed/direct/indirect/unaffected + Impact Explorer |
| `risk_analyzer`        | Deterministic review-attention scoring                                    |
| `verification_planner` | Deterministic per-category verification task generation                   |
| `test_gap`             | Potential test-gap detection                                              |
| `evidence_manager`     | Evidence ledger, task status history, readiness                           |
| `store`                | SQLite persistence                                                        |
| `report_generator`     | Markdown / JSON / HTML report rendering                                   |
| `analysis_service`     | Orchestrator                                                              |
| `ai_assistant`         | Optional local Ollama explanations (deterministic fallback when absent)   |
| `demo_builder`         | Builds the real sample repo for the one-click demo                        |

The engine is deterministic: the same diff produces the same classifications,
scores, and task keys every time.

---

## Extending the engine

### Add a classification rule

Rules are **data**, defined in `backend/prscope/services/classifier.py` as a tuple
`DEFAULT_RULES` of `ClassificationRule` dataclasses. A rule declares a `name`,
target `category` (a `FileCategory` from `models.py`), a human-readable `reason`,
a `confidence`, and one or more matchers: `globs` (full-path globs),
`basename_globs` (filename globs), and/or a `regex`. The matching is **ordered**:
the first rule whose `matches()` returns `True` wins, and the match records the
rule name and reason.

To add a rule:

1. If you need a new category, add it to the `FileCategory` enum in `models.py`.
2. Insert a `ClassificationRule(...)` into `DEFAULT_RULES` **in priority order** —
   more specific / higher-signal rules come first, because the first match wins.
3. Add a test in `tests/test_classifier.py` asserting that a representative path
   classifies into your category via your rule.

`classify_path` also accepts extra rules, so you can prepend project-specific
rules without editing the defaults when needed.

### Add a risk rule

Risk logic is in `backend/prscope/services/risk_analyzer.py`. The attention level
is the **sum of independent, deterministic score contributions**; the mapping to a
level is the `THRESHOLDS` table, and all per-rule points live in the `SCORE`
dictionary alongside the size/fan-in constants (`LARGE_CHANGE_LINES`,
`MANY_FILES`, `HIGH_FAN_IN`, etc.).

To add a rule:

1. Add a point value to the `SCORE` dict (and a threshold constant if your rule
   needs one).
2. In `analyze_risk(...)`, detect your condition from the `RiskContext` and, when
   it fires, append a finding that records **title, severity, related_files,
   explanation, evidence, suggested_action, rule, and score_contribution** — use
   `SCORE["your_rule"]` for the contribution so the number is traceable.
3. Add a case to `tests/test_risk_analyzer.py` that exercises the new rule and
   asserts both the finding and its score contribution.

Keep contributions additive and independent so the total remains explainable, and
remember the output is *review attention*, not a bug probability. Thresholds and
scores are deliberately inspectable and configurable — document any change in
`docs/RISK_MODEL.md`.

### Add a verification task template

Task generation is in `backend/prscope/services/verification_planner.py`. Tasks
are produced deterministically from the change set: each changed-file category
maps to one or more template functions that receive the matching files and return
`PlannedTask` dataclasses.

A `PlannedTask` carries a **stable `task_key`**, `title`, `description`, `reason`,
`related_files`, `verification_type`, `priority`, `steps`, and
`evidence_requirements`. Stable keys matter: re-running analysis on the same diff
must yield the same plan.

To add a template:

1. Write (or extend) a `_<category>_tasks(files)` function that returns
   `PlannedTask(...)` entries. Give each task a unique, stable key such as
   `"<category>:<short-slug>"`.
2. Wire the category to its function in the planner's category→template mapping.
3. Populate `steps` (what the reviewer should do) and `evidence_requirements`
   (what evidence closes the task) so the task plugs into the Evidence Ledger.
4. Add a test in `tests/test_verification_planner.py` asserting the task is
   generated for the triggering category and that its key is stable.

### Extend the API

Routes live in `backend/prscope/api/`, one module per resource group (`ai.py`,
`analyses.py`, `checklist.py`, `demo.py`, `evidence.py`, `reports.py`,
`repositories.py`, `settings.py`, `verification.py`). Each exposes a FastAPI
`router`, and `main.py` wires them in via `app.include_router(...)` under the
`/api` prefix.

To add an endpoint:

1. Add the route to the appropriate existing router (or create a new module with
   its own `router` and include it in `main.py`).
2. Use **Pydantic v2 models** from `models.py` for request and response bodies so
   input is validated and the OpenAPI schema stays accurate.
3. Call into the `services/` layer for logic and `store` for persistence — keep
   routers thin.
4. Add an API test to `tests/test_api.py` using the FastAPI test client.

The interactive docs at `/docs` update automatically from your type hints and
Pydantic models.

---

## Coding conventions

- **Deterministic core.** The engine must produce the same output for the same
  input. No randomness, no network calls, and no dependence on AI in any core
  path — AI is strictly optional and always has a deterministic fallback.
- **Security first.** Never run a shell for git: use `subprocess` with fixed
  argument lists. Validate every repository path (`safe_repo_path`, optional
  `PRSCOPE_ALLOWED_ROOTS` allow-list) and every git ref (strict allow-list regex
  that blocks option-injection, shell metacharacters, and `..`). Never execute
  repository code, never install the analyzed repo's dependencies, and keep SQL
  values parameterized. See `docs/SECURITY.md`.
- **Explainability.** Prefer emitting the *reason* for a result (the matched rule,
  the score contribution, the triggering files) over an opaque number. Findings
  and tasks record how they were derived.
- **Cautious wording for inferences.** Test-gap and impact results are
  approximations — phrase them as "potential" and "detected," never as absolute
  claims (e.g. "potential test gap", not "no tests exist").
- **Standard library first.** Reach for stdlib (`ast`, `subprocess`, `sqlite3`,
  `re`) before adding a dependency; runtime third-party deps are limited to
  FastAPI, Uvicorn, and Pydantic.
- **Lint and type-check before committing.** Run `ruff check .` (backend) and
  `npm run lint` + `npm run typecheck` (frontend), and keep the test suites green.
- **Tests accompany engine changes.** Any new classification rule, risk rule,
  verification template, or endpoint ships with a test.
