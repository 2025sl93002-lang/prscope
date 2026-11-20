# PRScope Roadmap

> Understand the impact. Know what to verify. Review with evidence.

This roadmap describes where PRScope is today and the directions we intend to
explore next. PRScope is currently a proof of concept (POC). Items below are
grouped by status so you can tell what already works from what is still an idea.

Status legend:

- **Done** — implemented and covered by the test suite in this release.
- **Planned** — intended work that has a clear shape but is not yet built.
- **Experimental** — early or partial work whose design may change, or that is
  only useful under narrow conditions.

Nothing in the "Planned" or "Experimental" sections is available today. Where a
feature is explicitly not implemented, it is listed as a roadmap item and is
**not** mocked or stubbed in the product.

---

## Done — current POC status

The core of PRScope is implemented, deterministic, and local-first. The
following capabilities ship in the current release:

- **Change-to-Verification Traceability.** The end-to-end chain of
  CODE CHANGE -> AFFECTED COMPONENTS -> POTENTIAL IMPACT -> REQUIRED
  VERIFICATION -> AVAILABLE EVIDENCE -> REVIEW READINESS, with every finding
  explaining how it was derived rather than emitting an opaque score.
- **Deterministic analysis engine** requiring no AI model, no API keys, and no
  paid or cloud services. Repository source code is never uploaded, and there is
  no telemetry.
- **PR diff parsing** using three-dot / merge-base comparison.
- **File classification** via ordered, deterministic rules.
- **Dependency analysis** for Python (via the standard-library `ast` module) and
  relative JS/TS imports (via regex), resolving intra-repository edges.
- **Impact analysis** using breadth-first search over reverse dependency edges,
  categorizing files as changed / direct / indirect / unaffected, plus a
  per-file Impact Explorer view.
- **Review-attention risk model** built from independent, inspectable, and
  configurable deterministic rule contributions (see
  [RISK_MODEL.md](RISK_MODEL.md)).
- **Verification planning** that generates deterministic tasks per changed-file
  category, each with a stable key, steps, evidence requirements, priority, and
  status.
- **Verification Evidence Ledger** — the central feature — with locally stored
  evidence records, task status audit history, and a completeness measure
  (completed applicable tasks / applicable tasks).
- **Test gap detection** that flags only *potential* gaps, using cautious
  wording and import/name-matching signals rather than coverage data.
- **Report generation** in Markdown, JSON, and HTML.
- **Optional AI explanations** via a local Ollama runtime. When Ollama is
  absent, all core features continue to work through the deterministic
  fallback.
- **One-click demo** that builds a real local git repository
  ("Payment Processing Refactor") and runs the actual engine against it.
- **FastAPI backend** with interactive API docs at `/docs`, and a React 18 +
  Vite frontend with a hand-written light/dark design system.

---

## Near-term — planned

These items extend the existing engine. They are planned, not built.

- **More languages.** Broaden dependency and classification support beyond
  Python and relative JS/TS imports — for example additional ecosystems and
  more import styles.
- **Function-level analysis.** Move from file-level approximation toward
  resolving impact at the function or symbol level for more precise traceability.
- **Coverage-data integration.** Incorporate real coverage reports so test-gap
  detection can go beyond import-and-naming inference. Until this lands, test
  gaps remain *potential* signals only.
- **Richer AI explanations.** Deepen the optional, local Ollama-backed
  explanations while preserving the deterministic fallback and the local-first,
  no-upload guarantees.

---

## Experimental

- **Optional GitHub PR import.** Importing pull requests directly from GitHub is
  **not implemented** in this POC. It is a roadmap item and is intentionally not
  mocked. The design and scope may change before any implementation.

---

## Limitations to keep in mind

The roadmap is shaped by the honest limitations of the current approach:

- File-level static analysis approximates impact and does not guarantee runtime
  behavior.
- Dependency analysis supports Python and relative JS/TS imports only. Bare or
  package specifiers, `tsconfig` path aliases, and dynamic imports are not
  resolved.
- Test gaps are inferred from imports and naming; they are potential gaps, not
  coverage-derived facts.
- Review attention is not a probability of defects.
- GitHub integration is not implemented in this POC.

See the project's limitations and security documentation for the full context.
