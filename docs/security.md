# Security Model for Analyzing Untrusted Projects

> This document describes how DepLens **safely analyzes untrusted
> repositories**. For how to report a vulnerability in DepLens itself, see the
> root `SECURITY.md`.

DepLens is frequently pointed at code you did not write — a dependency you are
evaluating, a third-party repo, a project from a colleague. **DepLens treats
every scanned project as untrusted input** and is built to analyze it without
giving it any opportunity to run or to read beyond its own directory.

## No code execution

- **No project code is executed.** DepLens is a static analyzer; it reads files
  and reasons about them.
- **No npm lifecycle scripts.** `preinstall`, `postinstall`, and friends are
  never triggered. DepLens parses `package.json`, it does not run it.
- **No `npm install`.** DepLens reconstructs the installed tree from the existing
  `package-lock.json`; it never invokes npm or any package manager.

Because nothing is executed, a malicious package in the tree cannot use DepLens
as a vector to run on your machine.

## Filesystem protection

All project file access goes through `services/safety.py`, which enforces:

- **Path-traversal protection** — resolved paths must stay within the project
  root; `..` escapes are rejected.
- **Symlink protection** — symlinks that point outside the project boundary are
  refused, so a crafted repo cannot trick DepLens into reading arbitrary files
  (e.g. `~/.ssh/id_rsa`).
- **File size caps** — oversized files are rejected rather than loaded, bounding
  memory use and resisting decompression/oversize denial-of-service inputs.

## Resource and parsing safety

- **Timeouts** apply to network calls (registry, OSV) so a slow or hostile
  endpoint cannot hang a scan indefinitely.
- **Safe JSON parsing** — manifests and lockfiles are parsed defensively.
  Malformed, unexpectedly shaped, or pathological JSON produces a `partial` or
  `failed` stage status (see `architecture.md`) instead of a crash or a silently
  wrong result.
- **Graceful degradation** — when a stage cannot complete safely, DepLens records
  the limitation and continues, rather than guessing.

## Network boundary

The only outbound traffic is the npm registry and OSV.dev lookups described in
`privacy.md`, carrying only package names (and versions, for OSV). Running
offline disables these calls entirely.

## Summary

| Risk from an untrusted repo | DepLens mitigation |
| --- | --- |
| Arbitrary code execution | No code run, no lifecycle scripts, no `npm install`. |
| Reading files outside the project | Path-traversal and symlink protection. |
| Resource exhaustion | File size caps, network timeouts. |
| Parser crashes / confusion | Defensive JSON parsing, explicit stage statuses. |
| Data exfiltration | Local-first; only package names/versions sent (see `privacy.md`). |
