# Changelog

All notable changes to DepLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Nothing yet.

### Changed

- Nothing yet.

### Fixed

- Nothing yet.

## [0.1.0] - 2026-11-21

### Added

- Local npm project scanning — point DepLens at a project directory and it reads
  `package.json` and the lockfile without ever installing or executing anything.
- Dependency graph construction and visualization across direct and transitive
  dependencies.
- Security analysis surfacing known vulnerabilities in the dependency tree.
- License analysis flagging license types and potential compatibility concerns.
- Update analysis highlighting outdated packages and available newer versions.
- Usage analysis identifying which declared dependencies are actually imported.
- Impact simulator for previewing the effect of adding, removing, or upgrading
  a dependency before making the change.
- Decision workspace for recording and tracking dependency decisions.
- Report generation summarizing project dependency health.
- Scan history for reviewing and comparing previous scans over time.

[Unreleased]: https://github.com/2025sl93002-lang/prscope/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/2025sl93002-lang/prscope/releases/tag/v0.1.0
