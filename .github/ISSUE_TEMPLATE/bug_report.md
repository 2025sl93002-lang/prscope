---
name: Bug report
about: Report a problem with PRScope so we can fix it
title: "[Bug]: "
labels: bug
assignees: ''
---

## Description

A clear and concise description of what the bug is. Explain what you expected PRScope to do and what went wrong.

## Steps to reproduce

Steps to reproduce the behavior:

1. Add/validate repository '...'
2. Run analysis on base ref '...' and head ref '...'
3. Open the '...' view (e.g. Impact Explorer, Risk, Verification, Evidence Ledger)
4. See error

If possible, include the exact API request (route and body) or the demo setup (`POST /api/demo/setup`) that triggers the issue.

## Expected behavior

A clear and concise description of what you expected to happen.

## Actual behavior

A clear and concise description of what actually happened. Include screenshots if they help explain the problem.

## Environment

Please complete the following information:

- **OS:** [e.g. macOS 14.5, Ubuntu 22.04, Windows 11]
- **Python version:** [e.g. 3.11.6 — PRScope requires 3.10+]
- **Node version:** [e.g. 20.11.0 — only if the bug is in the frontend]
- **PRScope version / commit:** [e.g. v0.1.0 or git commit SHA]

Relevant configuration (only include values you are comfortable sharing; omit anything sensitive):

- `PRSCOPE_DATA_DIR`, `PRSCOPE_DB_PATH`, `PRSCOPE_ALLOWED_ROOTS` (set or unset)
- `PRSCOPE_AI_ENABLED` (and whether a local Ollama runtime is available)

## Logs

Paste relevant backend (uvicorn) and/or browser console output here. Please redact any file paths, repository contents, or other information you consider private — PRScope processes local source code and we do not need it to diagnose most issues.

```
<paste logs here>
```

## Additional context

Add any other context about the problem here (e.g. does it only happen on large diffs, specific file types, Python vs. relative JS/TS dependency resolution, etc.).
