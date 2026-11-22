# Roadmap

An honest view of where DepLens is and where it may go. Everything beyond the
current release is aspirational and **not yet implemented**.

## Current — 0.1.0

Supported and working today:

- **npm / Node.js** ecosystem (`package.json` + `package-lock.json` v1/v2/v3).
- Dependency graph resolution with npm `node_modules` walk-up resolution.
- Update analysis via the npm registry and a from-scratch semver engine.
- Security advisories from OSV.dev.
- License classification and a configurable license policy.
- Usage detection with explicit confidence levels.
- Maintenance signals.
- Health scoring with explainable, capped penalties.
- Impact simulator (upgrade / remove / replace) with evidence classes.
- Reports in markdown, JSON, and CSV.
- Local-first, offline-capable, no telemetry.

## Planned — not yet implemented

The following are **not available yet**. They describe intended direction only.

- **Additional ecosystems** — PyPI (Python) and Cargo (Rust).
- **GitHub Advisory Database** — optional additional advisory source alongside
  OSV.
- **Package size analysis** — installed/bundle size as a health signal.
- **SBOM export** — CycloneDX and SPDX software bill-of-materials output.
- **Optional local-LLM assistance** — an opt-in helper that never leaves the
  machine and is **never required** to use DepLens.

> Items in the "Planned" section are not guarantees or timelines. They are marked
> here to be transparent about scope; none of them ship in 0.1.0.
