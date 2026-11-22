# Originality Statement

DepLens is an **original work** created for an academic Open-Source Software
Engineering project.

## Implemented from scratch

All of the core analysis logic is written from scratch for this project:

- the **semver engine** (`semver.py`) — a from-scratch subset of node-semver
  (parse, compare, satisfies, diff, max_satisfying);
- the **lockfile resolver** (`parsers/lockfile.py`) — parses `package-lock.json`
  v1/v2/v3 and reconstructs the installed tree via npm `node_modules` walk-up
  resolution;
- the **graph engine** (`services/graph.py`) — dependency graph construction and
  analysis (depth, dependents, paths, upstream/downstream);
- the **analyzers** — versions, licenses, maintenance, usage, and health scoring;
- the **impact simulator** — upgrade/remove/replace modeling with evidence
  classes.

## Dependencies and provenance

- DepLens uses only **open-source libraries** (FastAPI, Uvicorn, Pydantic, httpx,
  NetworkX on the backend; React and related MIT/ISC libraries on the frontend).
  These are listed in `THIRD_PARTY_NOTICES.md`.
- DepLens is **not a fork or copy** of any existing dependency tool. The analysis
  algorithms were designed and implemented for this project.
- Security advisory data comes from the **public OSV.dev database** and is
  **never fabricated**. DepLens reports what OSV returns; it does not invent
  vulnerabilities.

The project is released under the MIT License.
