# PRScope

**Pull Request Verification & Review Evidence Planner**

> Understand the impact. Know what to verify. Review with evidence.

`License: MIT` &nbsp;·&nbsp; `Python 3.10+` &nbsp;·&nbsp; `React 18`

PRScope is a local-first, open-source developer tool for change-impact analysis and verification planning. It turns a pull request into a clear, explainable trail — from the lines that changed, through the components they affect, to the verification each change demands and the evidence that satisfies it. Instead of emitting an opaque AI score, PRScope shows exactly how every finding was derived.

---

## Why PRScope

Reviewing a pull request usually means guessing: *What does this change actually touch? What could break? What do I need to check before I approve it — and did anyone already check it?* Most tools answer with a single number or a dependency picture, leaving the reviewer to reconstruct the reasoning.

PRScope answers those questions deterministically and transparently. Its central feature is the **Verification Evidence Ledger**: a living record that links each change to the verification it requires and the evidence collected against it, so review readiness is something you can read and justify — not a black box.

- **Explainable, not opaque.** Every risk finding and every verification task records the rule that produced it, the files involved, and the reasoning. No magic scores.
- **Local-first and private.** Core analysis runs entirely on your machine. No API keys, no cloud services, no telemetry. Your source code is never uploaded.
- **Deterministic by default.** The same repository and PR produce the same analysis every time. AI is strictly optional.

---

## Change-to-Verification Traceability

PRScope's primary original contribution is a single, connected chain that it builds and keeps linked end to end:

```
CODE CHANGE
   ↓
AFFECTED COMPONENTS
   ↓
POTENTIAL IMPACT
   ↓
REQUIRED VERIFICATION
   ↓
AVAILABLE EVIDENCE
   ↓
REVIEW READINESS
```

Each stage is derived from the one before it by inspectable, deterministic rules. The Verification Evidence Ledger ties the last three stages together: for every required verification you can see what evidence exists, what is still missing, and therefore how ready the change is to merge.

---

## Features

- **PR diff analysis** — parses three-dot / merge-base diffs to find exactly what a pull request changes.
- **Deterministic file classification** — ordered, rule-based categorization of every changed file (source, test, API contract, migration, config, security, UI, dependency, infrastructure, build/CI, documentation).
- **Dependency analysis** — resolves intra-repo edges for Python (via the standard-library `ast`) and relative JS/TS imports (via regex).
- **Impact Explorer** — BFS over reverse dependency edges classifies every file as changed, directly affected, indirectly affected, or unaffected, with a per-file drill-down view.
- **Review-attention model** — a deterministic, additive scoring model (low / moderate / high / critical) that highlights where review attention is best spent. It is **review attention, not a probability of bugs**. See [docs/RISK_MODEL.md](docs/RISK_MODEL.md).
- **Verification planner** — generates stable, per-category verification tasks with steps, reasons, evidence requirements, priority, and status.
- **Verification Evidence Ledger** — attach evidence (test results, CI, manual checks, screenshots, reports, builds, API checks, security scans, reviewer notes, docs) to tasks, track status changes through an audit history, and compute verification completeness.
- **Potential test-gap detection** — cautiously flags *potential* gaps (e.g. source changed with no name/import-matched test) without ever claiming "no tests exist."
- **Interactive dependency & impact graph** — rendered in the React frontend.
- **Reports** — export an analysis as Markdown, JSON, or HTML.
- **Optional AI explanations** — via a local [Ollama](https://ollama.com) runtime. If Ollama is absent, every core feature still works through a deterministic fallback.
- **One-click demo** — builds a real local git repository and runs the actual engine against it.

> **Screenshots:** see [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for a visual walkthrough of the interface.

---

## Local-first & private

PRScope reads your source code and git history, which are sensitive. It is built so that:

- Core analysis is **fully deterministic** and needs **no AI model, no API keys, and no paid or cloud services**.
- Your repository source code is **never uploaded anywhere**.
- There is **no telemetry**.
- AI is **optional** and runs locally via Ollama; disable it and nothing is lost but the optional natural-language explanations.

See [SECURITY.md](SECURITY.md) for the full security model, including path-traversal protection, git ref validation, and shell-free git execution.

---

## Quick Start

### Prerequisites

- **Python 3.10+** (developed and tested on 3.11)
- **Node.js** with npm (for the frontend)
- **git** available on your `PATH`

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run the API server
PYTHONPATH=. uvicorn prscope.main:app --port 8000
# or:
python -m prscope.main
```

The API is served under the `/api` prefix, with interactive Swagger docs at <http://localhost:8000/docs>.

Run the tests and linter:

```bash
PYTHONPATH=. pytest
ruff check .
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # Vite dev server on http://localhost:5173, proxies /api to :8000
```

Build and test:

```bash
npm run build
npm test        # vitest
```

### One-click demo

With both the backend and frontend running, open the app and click **"Run demo"**, or trigger it directly:

```bash
curl -X POST http://localhost:8000/api/demo/setup
```

The demo builds a **real** local git repository (the "Payment Processing Refactor" scenario) and runs the actual analysis engine against it — the results are produced by the engine, not hardcoded.

### Environment variables

| Variable | Purpose |
| --- | --- |
| `PRSCOPE_DATA_DIR` | Base directory for PRScope data |
| `PRSCOPE_DB_PATH` | Path to the SQLite database file |
| `PRSCOPE_ALLOWED_ROOTS` | Optional allow-list of root paths that may be analyzed |
| `PRSCOPE_MAX_FILE_BYTES` | Per-file size cap (default 2 MB) |
| `PRSCOPE_MAX_DIFF_FILES` | Cap on the number of diff files processed |
| `PRSCOPE_AI_ENABLED` | Enable/disable optional AI assistance |
| `PRSCOPE_AI_ENDPOINT` | Local Ollama endpoint |
| `PRSCOPE_AI_MODEL` | Ollama model name |

---

## Architecture overview

PRScope has two parts:

- **Backend** — a Python / FastAPI service (`prscope` package) with a modular, deterministic analysis engine. Analysis stages live in `backend/prscope/services/` (diff parsing, classification, dependency analysis, impact analysis, risk analysis, verification planning, test-gap detection, the evidence manager, persistence, and report generation), orchestrated by an analysis service. Data is persisted in SQLite via the standard-library `sqlite3` module; the schema is in `backend/prscope/schema.sql`.
- **Frontend** — a React 18 + TypeScript app built with Vite 5, using `react-router-dom`, `@xyflow/react` for the graph, and `react-markdown`, on a hand-written CSS design system with light and dark themes. No proprietary UI library.

For the full design, module responsibilities, and data model, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Tech stack

- **Backend:** Python 3.10+, FastAPI, Pydantic v2, standard-library `sqlite3`. git is invoked via the standard-library `subprocess` module with fixed argument lists and **no shell**. Python dependency parsing uses the standard-library `ast`; JS/TS parsing uses regex. Runtime deps: `fastapi`, `uvicorn[standard]`, `pydantic`. Dev deps: `pytest`, `httpx`, `ruff`, `pip-licenses`.
- **Frontend:** React 18, TypeScript, Vite 5, `react-router-dom` 6, `@xyflow/react` 12, `react-markdown` 9. Dev/test: `vitest`, `@testing-library/react`.
- **Database:** SQLite (stdlib `sqlite3`). Tables: `repositories`, `analyses`, `changed_files`, `dependency_edges`, `impact_nodes`, `risk_findings`, `verification_tasks`, `task_history`, `evidence_records`, `test_gaps`, `checklist_items`, `settings`.

### Repository layout

```
backend/    prscope package (config, db, models, schema.sql, main) + services/ + api/ + tests/
frontend/   React + Vite app (src/pages, src/components, src/api.ts, src/styles.css)
docs/       documentation
.github/    workflows + templates
scripts/    helper scripts
```

---

## Limitations

PRScope is a proof of concept, and its analysis is intentionally cautious. Be aware that:

- File-level static analysis **approximates** impact and does **not guarantee** runtime behavior.
- Dependency analysis supports **Python and relative JS/TS imports only**. Bare/package specifiers, `tsconfig` path aliases, and dynamic imports are not resolved.
- Test gaps are **potential** gaps, inferred from imports and naming — they are not based on coverage data, and PRScope never claims that no tests exist.
- The review-attention level is **not a defect probability**.
- **GitHub integration is not implemented** in this POC. It is documented as a roadmap item and is not mocked.

---

## License

PRScope is released under the **MIT License**.

SPDX-License-Identifier: `MIT`

Copyright (c) 2026 PRScope Contributors. See [LICENSE](LICENSE) for the full text.

---

## Documentation & project files

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, modules, and data model
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) — walkthrough and screenshots
- [docs/RISK_MODEL.md](docs/RISK_MODEL.md) — the deterministic review-attention model and its thresholds
- [docs/ORIGINALITY.md](docs/ORIGINALITY.md) — how PRScope compares to related tools
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute
- [SECURITY.md](SECURITY.md) — security model and how to report a vulnerability
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community expectations
- [CHANGELOG.md](CHANGELOG.md) — release history
