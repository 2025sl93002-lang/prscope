# Security Policy

DepLens is a local-first tool for inspecting the dependency health of
Node.js/npm projects. Because it analyzes real project directories, security is
central to its design. This document describes DepLens's security model, the
versions we support, and how to report a vulnerability.

## Security model

DepLens treats every scanned repository as **untrusted input**. A project you
analyze may be malicious, malformed, or crafted to attack the tool itself.
DepLens is built to inspect such projects safely:

- **No code execution.** DepLens never executes project code, test suites, or
  application entry points.
- **No lifecycle scripts.** It never runs `package.json` lifecycle scripts
  (`preinstall`, `install`, `postinstall`, `prepare`, and so on).
- **No installation.** It never runs `npm install`, `npm ci`, or any other
  package manager command. All analysis is performed by statically reading
  `package.json`, lockfiles, and source files.
- **Path traversal protection.** File access is validated and confined to the
  scanned project root. Symlinks and `..` segments cannot be used to escape the
  project directory or read arbitrary files on the host.
- **File size limits.** Oversized files are skipped or truncated to prevent
  memory exhaustion from maliciously large inputs.
- **Timeouts.** Parsing and analysis operations are bounded by timeouts to
  prevent denial-of-service from pathological inputs.

If you believe any of these guarantees can be bypassed, we consider that a
security vulnerability and want to hear about it.

## Supported versions

DepLens is pre-1.0 and under active development. Security fixes are applied to
the current `0.x` release line only.

| Version | Supported          |
| ------- | ------------------ |
| 0.x     | :white_check_mark: |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public issues.**

Instead, report privately using GitHub's security advisory feature:

1. Go to the repository's **Security** tab.
2. Select **Report a vulnerability** to open a private security advisory.

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, including a minimal sample project if relevant.
- The DepLens version and your environment (OS, Python version, Node version).
- Any suggested remediation, if you have one.

## Response expectations

- We aim to acknowledge new reports within **3 business days**.
- We will provide an initial assessment and severity estimate within
  **7 business days**.
- We will keep you informed as we work on a fix and coordinate a disclosure
  timeline with you.
- With your permission, we will credit you once a fix is released.

Thank you for helping keep DepLens and its users safe.
