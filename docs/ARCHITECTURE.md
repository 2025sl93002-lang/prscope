# DepLens Architecture

DepLens is a local-first dependency health explorer for Node.js / npm projects.
It reads a project's manifests and lockfile, reconstructs the dependency graph,
enriches it with registry, advisory, license, and usage data, and produces an
explainable health report. Everything runs on your machine; the only outbound
traffic is to the public npm registry and OSV.dev (see `privacy.md`).

## Workflow

DepLens is organized around a six-phase mental model. Each phase builds on the
previous one, and every output records its own confidence.

```
SCAN  ──▶  UNDERSTAND  ──▶  INVESTIGATE  ──▶  SIMULATE  ──▶  DECIDE  ──▶  VERIFY
 │           │                │                 │             │            │
 read       graph:          versions,         impact        record       checklist
 manifests  depth,          advisories,       of upgrade/   a decision   of steps to
 + lockfile dependents,     licenses,         remove/       with its     confirm the
 resolve    paths           usage,            replace       rationale    change is safe
 the tree                   maintenance
```

- **SCAN** — discover the project, read manifests, resolve the dependency graph,
  gather registry metadata, query advisories, classify licenses, check usage,
  generate findings, and persist the result.
- **UNDERSTAND** — explore the resolved graph: direct vs transitive packages,
  depth, who depends on what, and the paths between packages.
- **INVESTIGATE** — drill into a package's outdatedness, vulnerabilities,
  license family, usage evidence, and maintenance signals.
- **SIMULATE** — model the blast radius of upgrading, removing, or replacing a
  package before you touch anything.
- **DECIDE** — record a decision and its rationale against the current scan.
- **VERIFY** — follow a generated checklist to confirm the change is safe.

## The 9-stage scan

`scanner.py` orchestrates the scan. Each stage reports one of
`ok` / `partial` / `skipped` / `failed`, and those statuses flow into the final
report so nothing is silently assumed.

1. **Discover project** — locate `package.json` / `package-lock.json`.
2. **Read manifests** — parse declared dependencies.
3. **Resolve dependency graph** — reconstruct the installed tree from the lockfile.
4. **Analyze versions & registry metadata** — compare installed vs latest.
5. **Check security advisories** — query OSV.dev (skipped when offline).
6. **Analyze licenses** — classify each package's license into a policy outcome.
7. **Check package usage** — look for imports/requires in source.
8. **Generate health findings** — compute penalties and the health score.
9. **Persist** — write the scan and all derived rows to SQLite.

## Backend modules

Located in `backend/deplens/`.

| Module | Responsibility |
| --- | --- |
| `semver.py` | From-scratch subset of node-semver: `parse`, `compare`, `satisfies`, `diff`, `max_satisfying`. |
| `parsers/manifest.py` | Parse `package.json` (dependency sections, metadata). |
| `parsers/lockfile.py` | Parse `package-lock.json` v1/v2/v3 and reconstruct the resolved tree via npm `node_modules` walk-up resolution. |
| `services/graph.py` | Build a NetworkX graph; compute depth, dependents, dependency paths, upstream/downstream reach. |
| `services/safety.py` | Path-traversal and symlink protection, file size caps. |
| `services/registry.py` | npm registry client (package metadata, versions, `dist-tags`). |
| `services/osv.py` | OSV.dev advisory client (batch query + per-advisory detail). |
| `analyzers/` | Per-concern analysis: versions, licenses, maintenance, usage, health, impact. |
| `scanner.py` | Orchestrates the 9-stage scan. |
| `report.py` | Render reports as markdown, JSON, or CSV. |
| `db.py` | SQLite schema and access; versioned via a `meta` table. |
| `api/` | FastAPI routers exposing scans, graph, findings, simulations, decisions. |
| `main.py` | FastAPI app; also serves the built frontend. |
| `__main__.py` | CLI entry point: `deplens serve` / `deplens scan <path>`. |

## Data model (SQLite)

No ORM — plain `sqlite3` from the standard library. The schema is versioned
through a `meta` table so migrations are explicit.

| Table | Contents |
| --- | --- |
| `projects` | A scanned project path and its identity. |
| `scans` | One row per scan: timestamp, stage statuses, health score, confidence. |
| `packages` | Resolved packages for a scan: name, version, direct/transitive, depth, license, latest version. |
| `edges` | Dependency edges (from → to) backing the graph. |
| `vulnerabilities` | Advisories matched to packages: severity, ranges, fixed version. |
| `decisions` | Recorded decisions (upgrade/remove/replace) with rationale, tied to a scan. |
| `usage_overrides` | User corrections to automatic usage detection. |
| `settings` | Persisted configuration (e.g. license policy overrides). |

## Request flow

```
┌────────────┐   HTTP /api    ┌──────────────┐   calls    ┌───────────┐
│  Frontend  │ ─────────────▶ │   FastAPI    │ ─────────▶ │ analyzers │
│ (React/TS) │ ◀───────────── │   routers    │ ◀───────── │ + scanner │
└────────────┘    JSON        └──────────────┘            └─────┬─────┘
                                      │                         │
                                      ▼                         ▼
                                ┌──────────┐             ┌─────────────┐
                                │  SQLite  │             │ npm / OSV   │
                                │  (local) │             │ (read-only) │
                                └──────────┘             └─────────────┘
```

The frontend is a thin client. All analysis happens in the backend; the frontend
reads persisted results and triggers scans/simulations through the API. In a
packaged deployment `main.py` also serves the built frontend assets, so the whole
tool runs from a single local process.

## Threat model

**Scanned repositories are untrusted.** A project under analysis may contain
hostile file names, symlinks pointing outside the project, pathologically large
or malformed JSON, or lockfiles crafted to mislead a resolver. DepLens therefore:

- never executes project code, npm lifecycle scripts, or `npm install`;
- reads only the files it needs, through `services/safety.py`, which rejects
  path traversal and symlink escapes and enforces file size caps;
- parses JSON defensively and degrades to `partial`/`failed` stage statuses
  rather than crashing or guessing.

See `security.md` for the full untrusted-input security model, and `privacy.md`
for the data-flow boundary.
