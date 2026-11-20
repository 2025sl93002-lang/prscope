"""Safe git invocation helpers.

All git calls go through :func:`run_git`, which uses ``subprocess`` with a fixed
argument list and **never** a shell, preventing command/shell injection. Refs
supplied by users are validated by :func:`validate_ref` before use, and paths by
:func:`safe_repo_path`. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .. import config


class GitError(RuntimeError):
    """Raised when a git command fails or a path/ref is rejected."""


# A git ref/commit we are willing to pass to git. Conservative allow-list:
# letters, digits, and the handful of punctuation chars valid in ref names.
# Explicitly forbids whitespace, shell metacharacters, and option-injection ("-").
_REF_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._/@^~-]{0,254})$")


def validate_ref(ref: str) -> str:
    """Validate a user-supplied git ref/commit. Returns it unchanged or raises."""
    if not isinstance(ref, str) or not ref:
        raise GitError("Empty git ref.")
    if ".." in ref or ref.endswith(".lock") or "//" in ref:
        raise GitError(f"Invalid git ref: {ref!r}")
    if not _REF_RE.match(ref):
        raise GitError(f"Invalid git ref: {ref!r}")
    return ref


def safe_repo_path(raw_path: str) -> Path:
    """Resolve and validate a repository path.

    Protects against path traversal by fully resolving the path and, when
    ``PRSCOPE_ALLOWED_ROOTS`` is configured, confirming it lives under one of
    the allowed roots. The path must be an existing directory.
    """
    if not raw_path or not isinstance(raw_path, str):
        raise GitError("Repository path is required.")
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise GitError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise GitError(f"Path is not a directory: {path}")
    if config.ALLOWED_ROOTS:
        if not any(_is_within(path, root) for root in config.ALLOWED_ROOTS):
            raise GitError(
                "Repository path is outside the configured allowed roots "
                "(PRSCOPE_ALLOWED_ROOTS)."
            )
    return path


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def run_git(repo_path: Path, args: list[str], *, check: bool = True) -> str:
    """Run ``git <args>`` inside *repo_path* with no shell. Returns stdout.

    A leading ``--`` style option in a position that could be an injected ref is
    the caller's responsibility to avoid; refs must be pre-validated.
    """
    cmd = ["git", "-C", str(repo_path), *args]
    try:
        proc = subprocess.run(  # noqa: S603 - fixed arg list, shell disabled
            cmd,
            capture_output=True,
            text=True,
            timeout=config.GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("git executable not found on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git command timed out after {config.GIT_TIMEOUT_SECONDS}s.") from exc
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed.")
    return proc.stdout


def is_git_repo(repo_path: Path) -> bool:
    try:
        out = run_git(repo_path, ["rev-parse", "--is-inside-work-tree"], check=False)
        return out.strip() == "true"
    except GitError:
        return False
