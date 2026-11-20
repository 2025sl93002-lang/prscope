# PRScope Technical Decisions (ADRs)

This document records the significant technical decisions behind PRScope and the
reasoning for each, in lightweight Architecture Decision Record (ADR) form. The
decisions reflect the implementation as built, not aspirations.

Guiding constraints that recur throughout:

- **Local-first.** Core analysis must run with no AI model, no API keys, and no
  paid or cloud services.
- **Repository source is never uploaded**, and there is no telemetry.
- **Deterministic and explainable** output over opaque scoring.

---

## ADR-001 — FastAPI for the backend API

**Status:** Accepted

**Context.** PRScope needs a local HTTP API that a React SPA can call, with
typed request/response validation and zero-config interactive documentation for
developers exploring the tool.

**Decision.** Use **FastAPI** with **Pydantic v2** models.

**Rationale.**
- Pydantic v2 gives declarative request/response validation, so the HTTP layer
  stays thin and all domain logic lives in `services/*`.
- FastAPI auto-generates Swagger UI at `/docs`, which is valuable for a developer
  tool whose users are developers.
- `uvicorn[standard]` is a small, well-understood ASGI server for a local
  single-process deployment.
- Runtime dependencies are deliberately few: `fastapi`, `uvicorn`, `pydantic`.

**Consequences.** The web layer is replaceable and the engine is fully usable
without it (it is exercised directly in tests). CORS is restricted to the local
dev frontend.

---

## ADR-002 — SQLite via the stdlib `sqlite3` module

**Status:** Accepted

**Context.** Analyses produce structured, related artifacts (changed files,
edges, impact nodes, findings, tasks, history, evidence) that must persist
between requests and across restarts, on a single user's machine.

**Decision.** Persist to **SQLite** through the Python **stdlib `sqlite3`**
module. The schema lives in `backend/prscope/schema.sql`.

**Rationale.**
- A relational store with foreign keys and cascading deletes models the
  analysis-derived data cleanly (delete a repository → everything derived goes).
- SQLite is a local file: no server to run, nothing to provision, aligned with
  local-first.
- Using the stdlib driver means **zero** extra runtime dependency for storage.
- All values are parameterized, which also closes SQL-injection as a class.

**Consequences.** Single-writer semantics are fine for a single-user tool.
Re-running an analysis uses `store.replace_*` operations for idempotency.

---

## ADR-003 — Standard-library-only analysis (git, AST, regex)

**Status:** Accepted

**Context.** The engine must parse git diffs and build a dependency graph.
Pulling in heavyweight parsing/VCS libraries would add dependencies, supply-chain
surface, and version churn.

**Decision.** Use the **standard library** for analysis primitives:
- Git is invoked via **`subprocess`**.
- Python dependency parsing uses the stdlib **`ast`** module.
- JS/TS relative imports are matched with **regex**.

**Rationale.**
- Keeps the runtime dependency set tiny and auditable.
- `ast` gives accurate Python import extraction without executing any code.
- Regex is sufficient for *relative* JS/TS import detection, which is the scope
  PRScope resolves.

**Consequences (and limitations).** Dependency analysis resolves Python and
relative JS/TS imports only. Bare/package specifiers, `tsconfig` path aliases,
and dynamic imports are **not** resolved. This is a deliberate, documented scope
boundary, not a defect.

---

## ADR-004 — Git via `subprocess` with fixed arg-lists, not GitPython

**Status:** Accepted

**Context.** PRScope reads local source and git repositories, which are
sensitive. The git-invocation path is the most security-relevant part of the
engine.

**Decision.** Invoke git directly through **`subprocess` with fixed argument
lists and no shell** (the `gitutil` module), rather than adopting GitPython or
any third-party git wrapper. Validate paths and refs before every call.

**Rationale.**
- **No shell** means no shell-injection class at all.
- Fixed arg-lists plus strict ref validation (allow-list regex that blocks
  leading `-` option-injection, shell metacharacters, and `..`) keep attacker
  control out of git invocation.
- Path validation (`safe_repo_path`, with an optional `PRSCOPE_ALLOWED_ROOTS`
  allow-list) provides path-traversal protection.
- Avoiding a git library removes a dependency and keeps the exact git command
  under PRScope's direct control and review.
- PRScope **never executes repository code or scripts** and **never installs
  dependencies** from the analyzed repo.

**Consequences.** All repository access funnels through one small, auditable
module. See `SECURITY.md` for the full threat model and controls.

---

## ADR-005 — Deterministic-first, AI-optional

**Status:** Accepted

**Context.** Many comparable tools emit a single opaque AI score. PRScope's
primary contribution is **Change-to-Verification Traceability** with a
Verification Evidence Ledger that explains how every finding was derived.

**Decision.** Make **all core analysis deterministic**. Treat AI as a strictly
optional, additive layer via a **local Ollama** runtime.

**Rationale.**
- Determinism makes results reproducible and every finding traceable to the
  input that produced it — the opposite of an opaque score.
- It requires no API keys, no cloud, and no network, which satisfies local-first
  and no-upload.
- Optional AI (natural-language explanations) adds convenience without becoming
  a dependency: if Ollama is absent, the deterministic fallback keeps every core
  feature working. `GET /api/ai/status` reports availability.

**Consequences.** Risk is expressed as **review attention** from summed,
inspectable rule contributions (see `docs/RISK_MODEL.md`), not a probability of
bugs. Test gaps are reported as **potential**, never asserted as absence of
tests.

---

## ADR-006 — Three-dot / merge-base diff semantics

**Status:** Accepted

**Context.** PRScope analyzes pull-request-shaped changes. A naive two-dot diff
(`base..target`) includes commits that merely landed on `base` after the branch
diverged, overstating what the PR actually changed.

**Decision.** Compute the PR diff using **three-dot / merge-base** semantics —
the changes on the target relative to the common ancestor of base and target.

**Rationale.**
- Three-dot (`base...target`) answers the reviewer's real question: *what did
  this branch change relative to where it diverged?*
- It matches how code-review platforms present a PR, so impact, risk, and
  verification are computed against the right set of changes.

**Consequences.** The recorded range kind reflects the merge-base computation;
diff parsing is implemented in `git_diff`.

---

## ADR-007 — React 18 + TypeScript + Vite 5, with @xyflow/react for graphs

**Status:** Accepted

**Context.** The client must render analysis tables, the dependency/impact
graph, and Markdown reports, with a fast local dev loop.

**Decision.** Build the frontend with **React 18 + TypeScript**, bundled by
**Vite 5**, routed with **react-router-dom 6**, using **@xyflow/react 12** for
the graph view and **react-markdown 9** for rendered reports.

**Rationale.**
- Vite gives a fast dev server (`http://localhost:5173`) that proxies `/api` to
  the backend on port 8000, so frontend and backend develop independently.
- `@xyflow/react` is purpose-built for interactive node/edge graphs, which is
  exactly the dependency and impact visualization PRScope needs.
- `react-markdown` renders the engine's Markdown reports in the browser without
  a separate rendering step.
- TypeScript keeps the API client (`src/api.ts`) in step with backend contracts.

**Consequences.** Frontend testing uses **vitest** and
**@testing-library/react**. For a packaged build, FastAPI serves the compiled
`frontend/dist` as static files so the whole product runs from one process.

---

## ADR-008 — Hand-written CSS design system, no UI component library

**Status:** Accepted

**Context.** The UI needs a consistent look with light and dark themes.

**Decision.** Use a **hand-written CSS design system** (`src/styles.css`) rather
than a proprietary or third-party UI component library.

**Rationale.**
- Avoids a large styling/runtime dependency and the lock-in and bundle weight
  that come with it.
- Gives full control over the light/dark theming and the tool's visual identity.
- Keeps the frontend dependency surface small and auditable, consistent with the
  project's minimal-dependency stance.

**Consequences.** Components carry their own styling conventions; there is no
external design-system upgrade treadmill to track.

---

## ADR-009 — Python version support: target 3.10+, pin 3.11 locally

**Status:** Accepted

**Context.** The backend targets a broad range of modern Python, but the
toolchain must be stable for contributors.

**Decision.** Support **Python 3.10+** while developing and testing on **3.11**.

**Rationale.**
- 3.10+ covers the language and typing features PRScope uses.
- At the time of development, **Python 3.15 was incompatible with
  `pydantic-core`** (Pydantic v2's Rust core), so the local toolchain is pinned
  to **3.11** to keep the environment reproducible and the 69 backend tests
  green, rather than chasing a bleeding-edge interpreter.

**Consequences.** Contributors should develop on 3.11 for a known-good
environment; the codebase remains compatible with 3.10+. Revisit the pin once
`pydantic-core` ships wheels for newer interpreters.

---

## Decision summary

```
 Concern                     Decision                         ADR
 ───────────────────────────────────────────────────────────────
 HTTP API                    FastAPI + Pydantic v2            001
 Persistence                 SQLite via stdlib sqlite3        002
 Analysis primitives         stdlib: subprocess / ast / regex 003
 Git access / safety         subprocess, no shell (not GitPy) 004
 Analysis philosophy         deterministic-first, AI-optional 005
 PR diff semantics           three-dot / merge-base           006
 Frontend framework          React 18 + TS + Vite 5 + xyflow  007
 Styling                     hand-written CSS, no UI lib      008
 Python support              3.10+, pin 3.11 (pydantic-core)  009
```

See `docs/ARCHITECTURE.md` for how these pieces fit together and
`docs/RISK_MODEL.md` for the deterministic risk rules referenced in ADR-005.
