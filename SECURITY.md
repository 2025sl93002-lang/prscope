# Security Policy

PRScope (Pull Request Verification & Review Evidence Planner) analyzes **local
source code and git history**, which is sensitive by nature. Security is a
first-class concern for the project. This document describes the threat model,
how PRScope handles data, the controls that are implemented, known limitations,
and how to report a vulnerability.

---

## Threat model

PRScope reads local source repositories and their git metadata in order to
compute change-impact and verification plans. The primary risks the design
addresses are:

- **Exfiltration of sensitive source code.** Analyzed repositories may contain
  proprietary code and secrets. PRScope must not transmit source off the
  machine.
- **Execution of untrusted repository content.** An analyzed repository is
  attacker-influenced input. PRScope must never run its code, scripts, build
  steps, or install its dependencies.
- **Command/option injection via git.** Repository paths, refs, and diff targets
  flow into git invocations. These must not be exploitable to inject shell
  commands or git options.
- **Path traversal.** Repository path inputs must not be usable to read
  arbitrary files outside an intended location.
- **Injection into persistence and logs.** Stored values and log output must not
  be a vector for SQL injection or secret leakage.

---

## Data handling

- **Local-first processing.** Core analysis is fully deterministic and runs
  entirely on the local machine. It requires no AI model, no API keys, and no
  paid or cloud services.
- **No source upload by default.** Repository source code is never uploaded
  anywhere as part of normal operation.
- **No telemetry.** PRScope does not collect or transmit usage analytics.
- **Optional, local-only AI.** AI assistance is optional and is provided through
  a **local Ollama runtime** only. If Ollama is absent, all core features
  continue to work via the deterministic fallback. The AI integration is guarded
  and targets a local endpoint.

### Local storage

PRScope persists analysis state in a local **SQLite** database via the Python
standard library `sqlite3` module (schema in `backend/prscope/schema.sql`). The
data directory and database path are configurable through the `PRSCOPE_DATA_DIR`
and `PRSCOPE_DB_PATH` environment variables. Stored data includes repository
references, analyses, changed files, dependency edges, impact nodes, risk
findings, verification tasks and their status history, evidence records, test
gaps, checklist items, and settings. This data stays on the local machine. All
SQL values are parameterized.

---

## Implemented controls

- **Local-first processing** with no source upload by default and no telemetry.
- **Repository path validation and path-traversal protection** via a
  `safe_repo_path` check, with an optional allow-list of permitted roots
  configured through `PRSCOPE_ALLOWED_ROOTS`.
- **Strict git ref validation.** Refs and diff targets are validated against a
  strict allow-list regular expression that blocks option-injection (e.g. a
  leading `-`), shell metacharacters, and `..` sequences.
- **Safe git execution.** git is invoked through `subprocess` with **fixed
  argument lists and no shell**, eliminating shell-injection vectors.
- **No execution of repository content.** PRScope **never** executes the
  analyzed repository's code or scripts, and **never** installs dependencies
  declared by the analyzed repository. Analysis is purely static.
- **Resource caps.** A per-file size cap (`PRSCOPE_MAX_FILE_BYTES`, default
  2 MB) plus diff and source file-count caps (e.g. `PRSCOPE_MAX_DIFF_FILES`)
  bound the work performed on any input.
- **Input validation** via Pydantic models on API inputs.
- **No secrets in logs** and **no hardcoded credentials** in the codebase.
- **Parameterized SQL** for all values written to SQLite.

---

## Known limitations

PRScope is a proof of concept. Please keep the following in mind when deploying
or evaluating it:

- **Default access is broad.** Unless `PRSCOPE_ALLOWED_ROOTS` is set, PRScope
  may analyze **any readable local git repository**. Set an allow-list to
  restrict which paths can be analyzed.
- **Single-user, no authentication or authorization.** PRScope does not
  implement any authn/authz. Do not expose the API to untrusted networks; run it
  locally.
- **Static analysis is approximate.** File-level static analysis approximates
  and does not guarantee runtime behavior or impact. Dependency analysis covers
  Python (via `ast`) and relative JS/TS imports only. Findings and review
  attention levels are advisory, not guarantees.

---

## Reporting a vulnerability

Please report security vulnerabilities **privately** — do not open a public
GitHub issue for a security problem.

<!-- MAINTAINERS: configure one of the options below and remove the placeholder. -->

- Preferred: open a **private security advisory** via GitHub
  (**Security → Report a vulnerability** on the repository), or
- Email the maintainers at **[INSERT SECURITY CONTACT EMAIL]**.

When reporting, please include:

- a description of the vulnerability and its potential impact,
- steps to reproduce (proof-of-concept input, commands, affected refs/paths),
- the affected version or commit, and
- any suggested remediation, if you have one.

We will acknowledge your report, investigate, and keep you informed of progress
toward a fix. Please give us a reasonable opportunity to address the issue
before any public disclosure. Thank you for helping keep PRScope and its users
safe.
