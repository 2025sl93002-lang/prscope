# PRScope User Guide

**PRScope** — Pull Request Verification & Review Evidence Planner

> Understand the impact. Know what to verify. Review with evidence.

This guide walks you through installing PRScope, analyzing a change set, and
working through every screen in the app — from adding a repository to exporting a
review report.

PRScope is **local-first**: the core analysis is fully deterministic, requires no
AI model, no API keys, and no cloud services. Your repository's source code is
never uploaded anywhere, and there is no telemetry. Optional AI explanations run
against a **local** [Ollama](https://ollama.com) runtime; if Ollama is absent,
every core feature still works through a deterministic fallback.

---

## Table of contents

1. [What PRScope does](#what-prscope-does)
2. [Installation](#installation)
3. [Running PRScope](#running-prscope)
4. [The one-click demo](#the-one-click-demo)
5. [Adding a repository](#adding-a-repository)
6. [Running an analysis](#running-an-analysis)
7. [Navigating the app](#navigating-the-app)
8. [Reading each tab](#reading-each-tab)
   - [Overview](#overview)
   - [Changes](#changes)
   - [Impact Graph](#impact-graph)
   - [Risk](#risk)
   - [Verification](#verification)
   - [Evidence](#evidence)
   - [Checklist](#checklist)
   - [Report](#report)
9. [Recording evidence and interpreting completeness](#recording-evidence-and-interpreting-completeness)
10. [Exporting reports](#exporting-reports)
11. [Optional local AI](#optional-local-ai)
12. [Settings](#settings)
13. [Limitations](#limitations)

---

## What PRScope does

PRScope analyzes a proposed change (a "PR" expressed as two git refs — a base and
a target) and builds a single, explainable **Change-to-Verification Traceability**
chain:

```
CODE CHANGE  ->  AFFECTED COMPONENTS  ->  POTENTIAL IMPACT
          ->  REQUIRED VERIFICATION  ->  AVAILABLE EVIDENCE  ->  REVIEW READINESS
```

Instead of emitting a single opaque AI score, PRScope shows *how every finding was
derived*. The central feature is the **Verification Evidence Ledger**: a record of
what must be verified for a change, what evidence has been attached, and how close
the review is to being ready.

---

## Installation

### Prerequisites

- **Python 3.10+** (developed and tested on 3.11) for the backend.
- **Node.js** (with `npm`) for the frontend.
- **git** available on your `PATH` — PRScope invokes it to read repositories.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` installs the runtime dependencies (`fastapi`,
`uvicorn[standard]`, `pydantic`) plus the development tools (`pytest`, `httpx`,
`ruff`, `pip-licenses`). If you only want to run the server, `pip install -r
requirements.txt` is enough.

### Frontend

```bash
cd frontend
npm install
```

---

## Running PRScope

PRScope runs as two processes during development: the FastAPI backend and the Vite
frontend dev server.

### Start the backend

From the `backend` directory, with your virtual environment active:

```bash
PYTHONPATH=. uvicorn prscope.main:app --port 8000
```

or equivalently:

```bash
PYTHONPATH=. python -m prscope.main
```

The API is served at `http://127.0.0.1:8000`. Interactive API documentation
(Swagger UI) is available at `http://127.0.0.1:8000/docs`, and a health check at
`http://127.0.0.1:8000/api/health`.

### Start the frontend

From the `frontend` directory:

```bash
npm run dev
```

The Vite dev server starts on `http://localhost:5173` and proxies all `/api`
requests to the backend on port `8000`. Open `http://localhost:5173` in your
browser.

> **Single-process option:** if you run `npm run build` in `frontend/`, the
> backend will automatically serve the built app from `frontend/dist` when it
> starts, so you can use PRScope from `http://127.0.0.1:8000` alone.

---

## The one-click demo

The fastest way to see PRScope in action is the built-in demo. It is **not** a set
of hardcoded screenshots: it creates a **real local git repository** (a sample
"Payment Processing Refactor" change) and runs the actual analysis engine against
it.

With both the backend and frontend running:

1. Open the app at `http://localhost:5173`.
2. Click **Run demo**.

The button calls `POST /api/demo/setup`. You can trigger the same flow from a
terminal:

```bash
curl -X POST http://localhost:8000/api/demo/setup
```

When it finishes, PRScope drops you into a fully populated analysis so you can
explore every tab immediately.

---

## Adding a repository

To analyze your own project:

1. Go to the **Repositories** screen from the sidebar.
2. Choose **Add repository** and enter the **local filesystem path** to a git
   repository (for example `/Users/you/code/my-project`). PRScope reads the
   repository in place — it is never copied or uploaded.
3. PRScope validates the path before saving it (this calls
   `POST /api/repositories/validate`). Validation confirms the path exists, is a
   git repository, and — if your administrator has set the
   `PRSCOPE_ALLOWED_ROOTS` allow-list — that the path lives under an allowed
   root. If validation fails, you will see the reason and the repository is not
   added.

Repositories you add are listed so you can run multiple analyses against them over
time.

---

## Running an analysis

An analysis compares two points in history — a **base ref** and a **target ref** —
exactly as a pull request does.

1. Select a repository.
2. Choose a **base ref** (what you are merging *into*, e.g. `main`) and a
   **target ref** (the branch or commit with your changes, e.g. `feature/x` or a
   commit SHA).
3. Start the analysis.

PRScope computes the diff using git's three-dot / merge-base semantics, so you see
the changes introduced on the target relative to where it diverged from the base —
the same set of changes a reviewer would see in a PR. Refs are validated against a
strict allow-list before they are passed to git (see
[Limitations](#limitations) and `docs/SECURITY.md`).

Each analysis is stored locally (in SQLite) so you can return to it, record
evidence over time, and export a report whenever you like.

---

## Navigating the app

The **sidebar** is the primary navigation. It gives you access to:

- **Repositories** — add, validate, and select repositories; start a new
  analysis.
- **Analyses** — the list of analyses you have run; open one to view its tabs.
- **Settings** — local configuration, including optional AI.

When an analysis is open, its content is organized into tabs:
**Overview**, **Changes**, **Impact Graph**, **Risk**, **Verification**,
**Evidence**, **Checklist**, and **Report**. These follow the traceability chain
left-to-right: from *what changed* through *what to verify* to *review readiness*.

---

## Reading each tab

### Overview

The Overview summarizes the analysis at a glance: the repository, the base and
target refs, the size of the change (files and lines), the overall **review
attention level**, the number of verification tasks, and the current verification
completeness. Use it as the landing page for a review and as a jumping-off point
to the detail tabs.

### Changes

The Changes tab lists every changed file with its **classification** — the
category PRScope assigned (for example *source*, *test*, *api_contract*,
*migration*, *config*, *security*, *ui*, *dependency*, *infrastructure*,
*build_ci*, or *documentation*). Classification is rule-based and deterministic:
the first matching rule wins, and PRScope records *which rule matched and why*, so
you can always see the reason a file landed in its category. Added, modified, and
deleted lines are shown per file.

### Impact Graph

The Impact Graph visualizes how the changed files relate to the rest of the
codebase through the dependency graph. PRScope resolves intra-repository
dependency edges (Python via the standard-library `ast` module; relative
JavaScript/TypeScript imports via regex) and then performs a breadth-first search
over the **reverse** dependency edges to classify every node as:

- **changed** — files directly in the diff,
- **direct** — files that directly depend on a changed file,
- **indirect** — files reachable transitively from a changed file,
- **unaffected** — everything else.

Select a changed file to open its **Impact Explorer** view, which shows that
file's dependents and the reach of its change. This answers "if I change this,
what else might be affected?" — the *affected components* step of the traceability
chain.

### Risk

The Risk tab shows the **review attention level** and the individual findings that
produced it. Attention is the **sum of independent, deterministic rule
contributions** — it measures *how much reviewer attention the change warrants*,
**not** a probability of bugs.

Levels are derived from the total score:

| Level      | Score      |
|------------|------------|
| low        | `< 20`     |
| moderate   | `>= 20`    |
| high       | `>= 45`    |
| critical   | `>= 75`    |

Every finding records its **title, severity, related files, explanation,
evidence, suggested action, the rule name, and that rule's score contribution** —
so you can see exactly why the number is what it is. For the full rule table and
all thresholds, see `docs/RISK_MODEL.md`. All thresholds live in
`backend/prscope/services/risk_analyzer.py` and are inspectable and configurable.

### Verification

The Verification tab is your **work list**. PRScope generates verification tasks
deterministically from the change set — one or more per changed-file category.
Each task has:

- a **stable key** (re-running the analysis on the same diff yields the same
  plan),
- a **title**, **description**, and **reason** (why it was generated),
- the **related files** that triggered it,
- suggested **steps**,
- **evidence requirements** (what evidence it expects),
- a **priority**, and
- a **status**: *open*, *completed*, *blocked*, or *not_applicable*.

Change a task's status as you work through the review. Every status change is
recorded in an **audit history** you can inspect per task, so the review is
traceable. You can also add your own tasks to an analysis.

Marking a task **not_applicable** removes it from the completeness denominator
(see below), which is the correct way to dismiss a task that does not apply to
your change — rather than falsely completing it.

### Evidence

The Evidence tab is the **Verification Evidence Ledger** — the heart of PRScope.
It collects the evidence attached to each verification task and shows, at a
glance, what has been proven and what still needs proof.

Supported evidence types are: `test_result`, `ci`, `manual`, `screenshot`,
`report`, `build`, `api`, `security_scan`, `reviewer_note`, and `doc`. Evidence
records are attached to a specific task and stored **locally**.

### Checklist

The Checklist tab holds review-readiness checklist items for the analysis. Use it
for the human judgment calls that complement the generated tasks — things a
reviewer confirms before approving. You can add, check off, and remove items.

### Report

The Report tab renders a consolidated review report combining the change summary,
impact, risk findings, verification tasks and their status, attached evidence, and
readiness. From here you can **export** the report (see below).

---

## Recording evidence and interpreting completeness

The workflow for a review is:

1. Open the **Verification** tab and read the generated tasks.
2. For each applicable task, do the work (run the tests, the CI job, the manual
   check, etc.).
3. Attach the resulting **evidence** to the task on the **Evidence** tab (for
   example a `test_result` or a `ci` record), then set the task's status to
   **completed**.
4. Mark any task that genuinely does not apply as **not_applicable**.

**Verification completeness** is computed as:

```
completeness = completed applicable tasks / applicable tasks
```

Tasks marked *not_applicable* are excluded from both the numerator and the
denominator, so completeness reflects only the tasks that actually matter for this
change. A review is "ready" in the sense PRScope reports when the applicable tasks
are complete and backed by evidence — PRScope never approves a change for you; it
shows you the evidence so *you* can decide.

---

## Exporting reports

PRScope exports the full review report in three formats directly from the API:

- **Markdown** — `GET /api/analyses/{id}/report.md`
- **JSON** — `GET /api/analyses/{id}/report.json`
- **HTML** — `GET /api/analyses/{id}/report.html`

The Report tab provides the export controls; you can also fetch any format
directly, for example:

```bash
curl http://localhost:8000/api/analyses/1/report.md -o review.md
```

Markdown and JSON are convenient for attaching to a PR or archiving; HTML is handy
for sharing a self-contained rendered report.

---

## Optional local AI

AI in PRScope is strictly **optional** and strictly **local**. When enabled, it
uses a local Ollama runtime to produce plain-language explanations of findings. It
never changes a score, never gates a feature, and never sends your source code to
any external service.

- Check availability: `GET /api/ai/status`.
- Request an explanation: `POST /api/ai/explain`.

If Ollama is not installed or not enabled, every core feature continues to work
through the deterministic engine — you simply do not get the optional narrative
explanations. AI is disabled by default.

---

## Settings

The Settings screen (and `GET`/`PUT /api/settings`) lets you view and change local
configuration, including whether optional AI is enabled and which local endpoint
and model it uses. Several defaults can also be set via environment variables when
you start the backend:

| Variable                | Purpose                                              |
|-------------------------|------------------------------------------------------|
| `PRSCOPE_DATA_DIR`      | Directory for the local database and artifacts       |
| `PRSCOPE_DB_PATH`       | Explicit path to the SQLite database file            |
| `PRSCOPE_ALLOWED_ROOTS` | Allow-list of base directories for repository paths  |
| `PRSCOPE_MAX_FILE_BYTES`| Per-file read cap (default 2 MB)                     |
| `PRSCOPE_MAX_DIFF_FILES`| Cap on the number of changed files analyzed          |
| `PRSCOPE_AI_ENABLED`    | Enable optional local AI (`true`/`false`)            |
| `PRSCOPE_AI_ENDPOINT`   | Local Ollama endpoint (default `http://localhost:11434`) |
| `PRSCOPE_AI_MODEL`      | Local model name                                     |

See `docs/SECURITY.md` for the full security model behind these limits.

---

## Limitations

PRScope is a proof of concept. Please keep the following in mind when reading its
output:

- **Static analysis is approximate.** File-level analysis does not guarantee
  runtime impact; treat the Impact Graph as guidance, not proof.
- **Dependency analysis covers Python and *relative* JS/TS imports only.** Bare
  or package specifiers and `tsconfig` path aliases are not resolved, and dynamic
  imports are not resolved.
- **Test gaps are *potential*.** PRScope flags gaps inferred from imports and
  naming, not from coverage data. It deliberately uses cautious wording such as
  "potential test gap" and "no related test detected" — it never claims that "no
  tests exist."
- **Review attention is not a defect probability.** It measures how much reviewer
  attention a change warrants.
- **GitHub integration is not implemented** in this POC. It is a documented
  roadmap item, not a mocked feature; you provide changes as local git refs.

For how PRScope relates to other tools in this space, see `docs/ORIGINALITY.md`.
