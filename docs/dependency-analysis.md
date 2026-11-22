# Dependency Analysis

This document explains how DepLens turns a project's files into an explainable
dependency graph and a set of findings. All of the logic described here is
implemented from scratch in `backend/deplens/` — see `originality.md`.

## Parsing manifests and lockfiles

### `package.json`

`parsers/manifest.py` reads the manifest to learn what the project *declares*:
`dependencies`, `devDependencies`, `optionalDependencies`, and
`peerDependencies`, plus project metadata. The manifest tells us the **intended**
version ranges; the lockfile tells us what is **actually resolved**.

### `package-lock.json` (v1, v2, v3)

`parsers/lockfile.py` handles all three lockfile formats:

- **v1** — the tree lives under a nested `dependencies` object, where each
  package may itself contain a nested `dependencies` object for versions it
  needs that conflict with a sibling.
- **v2 / v3** — the tree lives in a flat `packages` map keyed by
  `node_modules/...` paths. v2 also carries a legacy `dependencies` block for
  backward compatibility; v3 drops it. DepLens reads the `packages` map as the
  source of truth.

### npm `node_modules` walk-up resolution

npm hoists packages, so a dependency declared by package A may be resolved from a
`node_modules` folder several levels up. To reconstruct which installed copy a
requirement actually binds to, DepLens replicates npm's **walk-up resolution**:
starting from the requiring package's own `node_modules`, it walks up the
directory chain toward the project root, taking the first matching package it
finds. This is how the same declared range can resolve to different installed
versions in different parts of the tree.

## Direct vs transitive

A package is **direct** if it appears in a dependency section of the root
`package.json`; otherwise it is **transitive**. DepLens records this distinction
per package because it changes how a finding should be acted on — you control
direct dependencies directly, while transitive ones are pulled in by something
else (and the graph shows you by what).

## Building the graph

`services/graph.py` builds a directed graph with NetworkX: nodes are resolved
packages, edges are "depends on" relationships recovered from the lockfile and
walk-up resolution. From the graph DepLens computes:

- **depth** — shortest distance from the root,
- **dependents** — who depends on a given package,
- **dependency paths** — the chains from the root to a package,
- **upstream / downstream** reach — what a package pulls in and what would be
  affected if it changed.

### Why multiple paths arise

A single package is often reached by more than one route — e.g. the root depends
on both `a` and `b`, and both depend on `c`. DepLens enumerates these distinct
paths so you can see every reason a package is present. This matters for the
impact simulator: removing one requirer may not remove a shared transitive
dependency if another path still needs it.

## Update analysis

`analyzers/versions` compares each installed version against the registry's
latest (via `services/registry.py`) using the from-scratch `semver.py` engine.
`semver.diff` classifies the gap as **major**, **minor**, or **patch**, which
feeds both the outdatedness display and the health penalties. Versions that can
not be compared (missing or non-semver versions) are reported as unknown rather
than guessed.

## Security analysis

`analyzers` + `services/osv.py` query the public OSV.dev database:

1. **Batch query** — send all name+version pairs to OSV's batch endpoint to find
   which packages have advisories.
2. **Per-advisory detail** — fetch the full record for each matched advisory
   (severity, affected ranges, references).
3. **Fixed-version selection** — for each advisory, pick the fixed version by
   matching the **installed version's range** against the advisory's affected
   ranges, so the suggested fix is the relevant one for *this* install, not an
   arbitrary later release.

When DepLens runs offline, security analysis is **skipped**, the stage is marked
accordingly, and the health score becomes **partial** (see `scoring-model.md`).

## Usage analysis

`analyzers/usage` looks for evidence that a package is actually used, by scanning
source for `import`, `require`, and dynamic `import()` references. Each package
gets a **confidence level**:

- **confirmed** — a reference to the package was found;
- **potential** — indirect or ambiguous evidence;
- **none** — no reference found;
- **incomplete** — source could not be fully scanned.

Crucially, DepLens **never claims a package is definitively unused.** Static
analysis cannot see every form of use (config-driven loading, string-built
specifiers, build tooling, runtime plugins). A package with no detected
reference is reported as **potentially-unused**, and users can correct the result
via `usage_overrides`.

## Maintenance signals

`analyzers/maintenance` surfaces signals that a package may be poorly maintained
— for example staleness relative to registry metadata. These are **signals, not
verdicts**: they raise a "maintenance concern" finding (a capped penalty in the
score) and point you to review, rather than asserting a package is abandoned.

## Impact simulator

`analyzers/impact` models a change **before** you make it. It supports:

- **upgrade** — move a package to a target version,
- **remove** — drop a package,
- **replace** — swap one package for another.

Each predicted consequence carries an **evidence class** describing how sure
DepLens is:

| Evidence class | Meaning |
| --- | --- |
| `lockfile` | Derived directly from the resolved graph — high certainty. |
| `static` | Backed by static source analysis. |
| `potential` | Plausible but not confirmed. |
| `unknown` | Could not be determined. |

The simulator never performs the change; it reports what *would* happen, with
its evidence, so you can proceed to **DECIDE** and **VERIFY** with eyes open.
