# Contributing to PRScope

Thanks for your interest in contributing to **PRScope** — the Pull Request
Verification & Review Evidence Planner. PRScope is a local-first, deterministic
developer tool for change-impact analysis and verification planning, and we
welcome bug reports, documentation fixes, tests, and new features.

This guide explains how to set up a development environment, the conventions we
follow, and how to get a change merged.

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

---

## Table of contents

- [Ground rules](#ground-rules)
- [Project layout](#project-layout)
- [Development setup](#development-setup)
  - [Backend (Python)](#backend-python)
  - [Frontend (React + TypeScript)](#frontend-react--typescript)
  - [Running the demo](#running-the-demo)
- [Running tests and lint](#running-tests-and-lint)
- [Code style](#code-style)
- [Branch naming](#branch-naming)
- [Commit messages](#commit-messages)
- [Pull request process](#pull-request-process)
- [Filing issues](#filing-issues)

---

## Ground rules

A few principles are core to PRScope. Please keep changes aligned with them:

- **Local-first and deterministic.** Core analysis must run fully offline with
  no AI model, no API keys, and no paid or cloud services. Do not introduce a
  hard dependency on a network service in any core code path.
- **Never upload repository source.** PRScope reads local source and git
  history, which is sensitive. Do not add telemetry or any feature that
  transmits analyzed source code off the machine by default.
- **AI is optional.** AI assistance is available only through a local Ollama
  runtime. If Ollama is absent, every core feature must still work through the
  deterministic fallback.
- **Explainable over opaque.** PRScope's defining contribution is
  change-to-verification traceability and the Verification Evidence Ledger.
  Findings should explain *how* they were derived rather than emit an opaque
  score. New analysis logic should record its reasoning (rule, evidence,
  score contribution) in the same spirit.

If a proposed change conflicts with any of these, please open an issue to
discuss it before investing in an implementation.

---

## Project layout

```
backend/    Python package `prscope` (config.py, db.py, models.py, schema.sql,
            main.py; services/*; api/*; tests/*)
frontend/   React + Vite app (src/pages, src/components, src/api.ts, src/styles.css)
docs/       Documentation
.github/    CI workflows and issue templates
scripts/    Helper scripts
```

The analysis engine lives in `backend/prscope/services/` — notable modules
include `gitutil` (safe git execution + path/ref validation), `git_diff`,
`classifier`, `dependency_analyzer`, `impact_analyzer`, `risk_analyzer`,
`verification_planner`, `test_gap`, `evidence_manager`, `store` (SQLite
persistence), `report_generator`, `analysis_service` (orchestrator), and the
optional `ai_assistant`.

---

## Development setup

### Prerequisites

- **Python 3.10+** (the project is developed and tested on 3.11)
- **Node.js** with npm (for the frontend)
- **git** available on your `PATH`
- *(Optional)* a local [Ollama](https://ollama.com) runtime if you want to work
  on or exercise the optional AI features

### Backend (Python)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the API server:

```bash
PYTHONPATH=. uvicorn prscope.main:app --port 8000
# or:
python -m prscope.main
```

Interactive API documentation (Swagger UI) is available at
`http://localhost:8000/docs` while the server is running.

Runtime dependencies are `fastapi`, `uvicorn[standard]`, and `pydantic`.
Development/test dependencies add `pytest`, `httpx`, `ruff`, and `pip-licenses`.

### Frontend (React + TypeScript)

```bash
cd frontend
npm install
npm run dev     # Vite dev server on http://localhost:5173 (proxies /api to :8000)
```

Build a production bundle with:

```bash
npm run build
```

The frontend is React 18 + TypeScript on Vite 5, using react-router-dom 6,
`@xyflow/react` for the dependency graph, and react-markdown. The UI uses a
hand-written CSS design system (light/dark); there is no proprietary UI library.

### Running the demo

With both the backend and frontend running, open the app and click **Run demo**,
or call the endpoint directly:

```bash
curl -X POST http://localhost:8000/api/demo/setup
```

The demo builds a **real** local git repository ("Payment Processing Refactor")
and runs the actual analysis engine against it — results are computed, not
hardcoded. It is a good way to exercise an end-to-end change before and after
your edits.

---

## Running tests and lint

Please run the full test suite and the linter locally and make sure both pass
before opening a pull request.

**Backend:**

```bash
cd backend
PYTHONPATH=. pytest        # run the test suite
ruff check .               # lint
```

**Frontend:**

```bash
cd frontend
npm test                   # vitest
```

If you add or change behavior, add or update tests to cover it. Backend tests
live in `backend/tests/`; frontend tests use vitest and
`@testing-library/react`.

---

## Code style

### Python

- Target **Python 3.10+**; code is written and tested against 3.11.
- Formatting and linting are handled by **ruff**. Configuration lives in
  `backend/pyproject.toml`:
  - Line length **110**.
  - Lint rule sets enabled: `E`, `F`, `I` (import sorting), `B`, `UP`, `S`
    (security/bandit-style checks).
  - A small, documented set of rules is ignored project-wide (e.g. `S101` for
    `assert` in tests, `B008` for FastAPI `Depends()` defaults). See
    `pyproject.toml` for the exact list and rationale — do not expand it without
    discussion.
- Run `ruff check .` before pushing. Many issues can be auto-fixed with
  `ruff check --fix .`.
- Prefer the standard library where the project already does (git via
  `subprocess` with fixed argument lists and **no shell**, SQLite via `sqlite3`,
  Python dependency parsing via `ast`). Do not introduce new runtime
  dependencies without a strong reason and a discussion in an issue.
- Validate external input with Pydantic models, keep SQL values parameterized,
  and never log secrets.

### TypeScript / React

- TypeScript with React 18 function components and hooks.
- Follow the existing structure: pages in `src/pages`, reusable pieces in
  `src/components`, API access centralized in `src/api.ts`, and styles in
  `src/styles.css`.
- Keep to the existing hand-written CSS design system and its light/dark
  theming rather than adding a UI framework.
- Make sure `npm run build` and `npm test` both succeed.

---

## Branch naming

Create a topic branch off `main`. Use a short, descriptive, hyphenated name
prefixed by the kind of change:

```
feature/<short-description>     e.g. feature/impact-explorer-filter
fix/<short-description>         e.g. fix/git-ref-validation-edge-case
docs/<short-description>        e.g. docs/clarify-risk-thresholds
chore/<short-description>       e.g. chore/bump-ruff
test/<short-description>        e.g. test/dependency-analyzer-js
```

---

## Commit messages

Write clear, imperative-mood commit subjects ("Add impact filter", not "Added"
or "Adds"). We follow a lightweight [Conventional
Commits](https://www.conventionalcommits.org/) style:

```
<type>: <short summary>

<optional body explaining what and why, wrapped at ~72 columns>
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

- Keep the subject line under ~72 characters.
- Explain *why* in the body when the change is not obvious.
- Reference related issues in the body (e.g. `Refs #123` or `Closes #123`).
- Keep each commit focused; avoid mixing unrelated changes.

---

## Pull request process

1. **Fork** the repository and create a topic branch from `main`.
2. Make your change, keeping commits focused and the scope aligned with the
   [ground rules](#ground-rules).
3. **Add or update tests** for any behavior you change.
4. Run the backend tests + `ruff check .` and the frontend tests, and make sure
   they pass. Update documentation in `docs/` when your change affects it.
5. Push your branch and open a pull request against `main`.
6. In the PR description, explain **what** changed and **why**, how you tested
   it, and link any related issues.
7. Keep the PR focused and reasonably small — smaller changes are easier to
   review and merge. (PRScope itself is designed to help reviewers reason about
   change impact, so this one is close to our hearts.)
8. Be responsive to review feedback. A maintainer will merge once the change is
   approved and CI is green.

By submitting a pull request, you agree that your contribution is licensed under
the project's [MIT License](LICENSE).

---

## Filing issues

Please file bugs and feature requests through **GitHub Issues**, using the issue
templates in `.github/ISSUE_TEMPLATE` where one applies.

When reporting a bug, include:

- what you did (commands, the repository/branch/refs analyzed, if relevant),
- what you expected to happen,
- what actually happened (error messages, logs, screenshots),
- your environment (OS, Python version, Node version, PRScope version/commit).

Please do **not** report security vulnerabilities in public issues. See
[SECURITY.md](SECURITY.md) for how to report them privately.

---

Thank you for helping make PRScope better!
