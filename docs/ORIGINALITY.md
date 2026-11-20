# Originality

> Understand the impact. Know what to verify. Review with evidence.

This document explains what problem PRScope addresses, which categories of
existing software overlap with it, which specific tools share functionality,
and what PRScope does differently. It is written in the spirit of honest
attribution: PRScope is **not** claimed to be unique in the entire industry.
Many good tools already analyze code change, risk, dependencies, and test
impact. PRScope's contribution is the *combination* it makes and the
*workflow* it centers on, described below.

---

## The problem

Reviewing a pull request well is hard for reasons that have little to do with
reading the diff itself:

- A reviewer must work out **what the change actually affects** — not just the
  edited files, but the components that depend on them.
- From that impact, the reviewer must decide **what needs to be verified** before
  the change is safe to merge.
- The reviewer must then find **evidence** that the required verification was
  actually done — tests run, CI passed, a migration rehearsed, a security scan
  completed — rather than assuming it.
- Finally, the reviewer has to judge **whether the change is ready**, and be able
  to justify that judgment to others.

Most tooling helps with pieces of this. Static analyzers flag code smells.
Risk-scoring bots emit a number. Dependency-graph tools draw an import graph.
Coverage tools report line coverage. Checklist bots paste a list of reminders.
Each is useful, but the reviewer is left to stitch them together by hand, and
several of them hand back an opaque score with little explanation of how it was
derived.

PRScope's goal is to connect these steps into one explainable chain:

```
CODE CHANGE -> AFFECTED COMPONENTS -> POTENTIAL IMPACT -> REQUIRED VERIFICATION
           -> AVAILABLE EVIDENCE -> REVIEW READINESS
```

This chain — **Change-to-Verification Traceability** — is the project's primary
original contribution, and the **Verification Evidence Ledger** is the central
feature that realizes it.

---

## Existing software categories that overlap

PRScope touches several established categories. It overlaps with all of them to
some degree and is a complete replacement for none of them:

- **AI code-review tools** — assistants that summarize or critique a diff.
- **PR risk scoring** — tools that assign a risk or priority number to a change.
- **Change-impact analyzers** — tools that estimate what a change affects.
- **Test-impact analysis** — tools that map changes to the tests that exercise them.
- **Dependency-graph tools** — tools that build and visualize import/module graphs.
- **Coverage tools** — tools that measure which code is exercised by tests.
- **PR checklist generators** — bots that attach review checklists to pull requests.

---

## Similar tools identified

The following tools have **functional overlap** with parts of PRScope. They are
listed for honest comparison. None of their code was copied or adapted; PRScope
was implemented independently (see "Why it is independently developed" below).

| Tool | Category | Overlap with PRScope |
|------|----------|----------------------|
| **Danger JS** | PR rule automation | Automates PR-time checks and reminders, similar in spirit to PRScope's verification tasks and checklist, but rule-scripted rather than derived from change impact. |
| **SonarQube** | Static analysis / quality gates | Flags issues and enforces gates on a change; overlaps with PRScope's risk findings, but is a quality-gate engine rather than a verification-evidence workflow. |
| **CodeScene** | Behavioral code analysis / hotspots | Identifies risky or high-churn areas; overlaps with the idea of focusing review attention, but uses behavioral/historical signals rather than per-change deterministic rules. |
| **PullApprove / review-checklist bots** | PR checklist generators | Produce review checklists on PRs, overlapping with PRScope's checklist and task generation. |
| **dependency-cruiser / madge** | JS dependency graphs | Build and visualize JS/TS module dependency graphs, overlapping with PRScope's dependency and impact analysis for JS/TS. |
| **pydeps** | Python import graphs | Builds Python import graphs, overlapping with PRScope's Python dependency analysis. |
| **coverage.py / Istanbul** | Coverage tools | Measure test coverage; overlap with PRScope's test-gap detection — but PRScope infers *potential* gaps from imports and naming, not from coverage data. |

---

## Functional overlap

Stated plainly, so there is no ambiguity about what is and isn't novel:

- Flagging risky changes and drawing attention to them is **not** novel — risk
  scorers, quality gates, and hotspot tools already do this.
- Building a dependency or import graph is **not** novel — dependency-cruiser,
  madge, and pydeps already do this.
- Generating a PR review checklist is **not** novel — checklist bots already do
  this.
- Reporting what tests do or do not cover is **not** novel — coverage tools
  already do this (and, where they consume real coverage data, do it more
  precisely than PRScope's inference).

PRScope reuses these well-understood *ideas*. What it contributes is how it
combines them.

---

## What PRScope does differently

PRScope unifies the whole chain —
**change -> impact -> required verification -> evidence -> review readiness** —
into a single, deterministic, explainable, local-first workflow, centered on a
verification **Evidence Ledger** rather than on a single opaque score or a bare
dependency graph.

Concretely, the differences are:

- **One connected workflow, not isolated signals.** Impact analysis feeds
  verification planning, which feeds the evidence ledger, which feeds the
  readiness judgment. Each stage references the one before it.

- **Explainability over opaque scoring.** PRScope does not emit a single AI
  "risk number" with no justification. The review-attention level is a sum of
  independent, named, deterministic rule contributions, and every risk finding
  records its title, severity, related files, explanation, evidence, suggested
  action, the rule that fired, and that rule's score contribution. The thresholds
  and score weights live in source and are inspectable and configurable.

- **Review attention, not a defect probability.** PRScope is explicit that its
  attention level means "how much review attention this change warrants," not
  "the probability that this change contains a bug." It does not claim predictive
  accuracy it cannot support.

- **A verification Evidence Ledger as the center of gravity.** Verification tasks
  are generated deterministically per changed-file category, each with a stable
  key, steps, and evidence requirements. Evidence records are attached to tasks,
  status changes are recorded in an audit history, and verification completeness
  is computed as completed applicable tasks over applicable tasks. The question
  PRScope answers is not only "is this risky?" but "has the work needed to trust
  this change actually been done, and where is the proof?"

- **Cautious test-gap wording.** PRScope flags only *potential* test gaps, with
  wording such as "potential test gap" and "no related test detected." It never
  claims that no tests exist, because it infers gaps from imports and naming, not
  from coverage data.

- **Local-first and private by default.** Core analysis is fully deterministic
  and needs no AI model, no API keys, and no paid or cloud services. Repository
  source code is never uploaded anywhere, and there is no telemetry. AI is
  optional via a local Ollama runtime; if it is absent, every core feature still
  works through the deterministic fallback.

---

## Original features

The features below are the concrete expression of PRScope's contribution:

- **Change-to-Verification Traceability** — the explicit, navigable link from a
  code change through affected components, potential impact, required
  verification, available evidence, and review readiness.
- **Verification Evidence Ledger** — deterministic per-category verification
  tasks with stable keys, evidence requirements, attached evidence records,
  status audit history, and a computed verification-completeness measure.
- **Explainable review-attention model** — an attention level built from named,
  deterministic rule contributions, with every finding carrying its own
  explanation, evidence, suggested action, rule, and score contribution.
- **Per-file Impact Explorer** — impact classified as changed / direct / indirect
  / unaffected via a breadth-first traversal over reverse dependency edges, with
  a per-file view.
- **Cautious, inference-aware test-gap detection** — potential gaps surfaced from
  imports and naming, worded so as never to overstate what is known.

These features individually resemble things other tools do; the originality is
in combining them into one explainable, local-first, evidence-centered workflow.

---

## Why it is independently developed

PRScope is independently implemented and does not copy code from any of the tools
listed above. Its analysis engine is built on the Python standard library and
hand-written parsing:

- Git is invoked through `subprocess` with fixed argument lists and no shell.
- Python dependency analysis uses the standard-library `ast` module.
- JavaScript/TypeScript relative-import analysis uses regular expressions.
- Persistence uses the standard-library `sqlite3` module.

No third-party dependency-graph engine, static-analysis platform, or risk-scoring
library is embedded or vendored. The similar tools named here are referenced for
functional comparison only.

---

## POC limitations

PRScope is a proof of concept, and its analysis is deliberately approximate. The
originality claims above should be read with these limits in mind:

- **File-level static analysis is approximate.** It estimates impact from files
  and imports and does not guarantee runtime behavior or true runtime impact.
- **Dependency analysis is limited in scope.** It supports Python imports and
  *relative* JS/TS imports only. Bare/package specifiers, `tsconfig` path aliases,
  and dynamic imports are not resolved.
- **Test gaps are potential, not proven.** They are inferred from imports and
  naming, not from coverage data, and are always worded as potential gaps.
- **Review attention is not a defect probability.** It indicates where to focus
  review, nothing more.
- **No GitHub integration.** GitHub integration is not implemented in this POC.
  It is documented as a roadmap item and is not mocked or stubbed to appear
  present.

None of these limitations is unique to PRScope, and none of them changes the
core claim: the contribution is the unified, explainable, local-first
change-to-verification-to-evidence workflow, not any single analysis technique.

---

## Comparison sources

The tools referenced above, listed for attribution and comparison (functional
overlap only, no code reused):

- **Danger JS** — PR rule automation.
- **SonarQube** — static analysis and quality gates.
- **CodeScene** — behavioral code analysis and hotspots.
- **PullApprove** and other review-checklist bots — PR checklist generation.
- **dependency-cruiser** and **madge** — JavaScript/TypeScript dependency graphs.
- **pydeps** — Python import graphs.
- **coverage.py** and **Istanbul** — test coverage measurement.
