# User Guide

This guide walks through using DepLens end to end, following its six-phase
workflow: **SCAN → UNDERSTAND → INVESTIGATE → SIMULATE → DECIDE → VERIFY**.

## 1. Scan a project

Start the app (see `development.md`) and point DepLens at a project directory, or
scan the bundled demo at `fixtures/demo-project` to try it without a real repo.

You can also scan from the CLI:

```bash
python -m deplens scan <path-to-project>
```

A scan runs nine stages (discover, read manifests, resolve graph, versions,
security, licenses, usage, findings, persist). Each stage reports
`ok` / `partial` / `skipped` / `failed`, and those statuses are shown so you
always know how complete the result is.

## 2. Read the overview dashboard

The dashboard shows the **health score** (0–100) and its **grade** (A–F). The
score is a prioritization aid, not a risk probability — see `scoring-model.md`.
Every point deducted traces back to a specific finding, so you can see *why* the
score is what it is. If security couldn't be checked (offline) or registry data
was incomplete, the score is labelled **partial**.

## 3. Explore the dependency graph

The graph view shows direct and transitive packages, their depth from the root,
and the edges between them. Select a package to see its **dependents** and the
**dependency paths** that bring it into the project. A package reached by several
paths is present for several reasons — useful before you try to remove it.

## 4. Use the dependency table and filters

The table lists every resolved package with version, direct/transitive status,
license, latest available version, and findings. Filter and sort to focus — for
example, show only direct dependencies, only outdated packages, or only those
with advisories.

## 5. Review findings by concern

- **Security** — advisories from OSV.dev, their severity, and the suggested
  fixed version for your installed range.
- **Licenses** — each package's license family and policy outcome
  (allowed / review / restricted); see `license-policy.md`.
- **Updates** — how far behind latest each package is (major / minor / patch).
- **Usage** — whether a package is confirmed used, potentially used, or has no
  detected use. DepLens never flatly declares a package unused (see
  `dependency-analysis.md`).

## 6. Run an impact simulation

Before changing anything, simulate it. Pick a package and choose **upgrade**,
**remove**, or **replace**. DepLens reports what *would* happen, with an
**evidence class** on each predicted consequence:

- `lockfile` — derived from the resolved graph (high certainty),
- `static` — backed by source analysis,
- `potential` — plausible but unconfirmed,
- `unknown` — undetermined.

Nothing is actually changed; the simulator only predicts.

## 7. Record a decision with a verification checklist

When you decide on a course of action, record it against the current scan with
its rationale. DepLens produces a **verification checklist** — the concrete steps
to confirm the change is safe (e.g. run tests, check the affected paths). This is
the DECIDE and VERIFY phases.

## 8. Compare scans

Re-scan after making changes and compare against a previous scan to confirm the
score moved the way you expected and that findings were actually resolved.

## 9. Export a report

Export the results as **markdown**, **JSON**, or **CSV** for sharing, archiving,
or feeding into other tooling.

## Reading uncertainty states

DepLens is explicit about what it does and doesn't know. You'll see:

| State | Meaning |
| --- | --- |
| **unknown** | DepLens could not determine this (e.g. an unrecognized license or non-semver version). Not a guess. |
| **not analyzed** | A stage was skipped for this item. |
| **partial** | Results are incomplete — some data source was unavailable or incomplete; the score reflects only what was verified. |
| **offline** | Network-dependent steps (registry, OSV) were skipped because there was no network. |

Treat these as prompts to look closer, not as pass/fail verdicts. DepLens is
built to under-claim rather than over-claim.
