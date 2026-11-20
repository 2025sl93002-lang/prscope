"""Repository manager — validate local git repos and extract metadata.

No repository code is ever executed; only read-only ``git`` plumbing commands
are run. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from pathlib import Path

from .gitutil import GitError, is_git_repo, run_git, safe_repo_path, validate_ref


def validate_repository(raw_path: str) -> Path:
    """Return a validated Path to an existing local git repository, or raise."""
    path = safe_repo_path(raw_path)
    if not is_git_repo(path):
        raise GitError(f"Not a git repository (or no work tree): {path}")
    return path


def repo_display_name(path: Path) -> str:
    return path.name or str(path)


def default_branch(path: Path) -> str | None:
    """Best-effort detection of the repository's default branch."""
    # Try the symbolic ref of origin/HEAD first.
    out = run_git(path, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], check=False)
    if out.strip():
        return out.strip().rsplit("/", 1)[-1]
    # Fall back to the current branch.
    out = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"], check=False).strip()
    if out and out != "HEAD":
        return out
    for candidate in ("main", "master"):
        if run_git(path, ["rev-parse", "--verify", "--quiet", candidate], check=False).strip():
            return candidate
    return None


def list_branches(path: Path) -> list[str]:
    out = run_git(path, ["branch", "--format=%(refname:short)"], check=False)
    return [line.strip() for line in out.splitlines() if line.strip()]


def list_tags(path: Path) -> list[str]:
    out = run_git(path, ["tag", "--list"], check=False)
    return [line.strip() for line in out.splitlines() if line.strip()]


def head_commit(path: Path) -> str | None:
    out = run_git(path, ["rev-parse", "HEAD"], check=False).strip()
    return out or None


def recent_commits(path: Path, limit: int = 10) -> list[dict]:
    """Return recent commits as dicts (hash, author, date, subject)."""
    limit = max(1, min(int(limit), 100))
    fmt = "%h%x1f%an%x1f%ad%x1f%s"
    out = run_git(
        path,
        ["log", f"-{limit}", "--date=short", f"--pretty=format:{fmt}"],
        check=False,
    )
    commits: list[dict] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) == 4:
            commits.append(
                {"hash": parts[0], "author": parts[1], "date": parts[2], "subject": parts[3]}
            )
    return commits


def ref_exists(path: Path, ref: str) -> bool:
    validate_ref(ref)
    out = run_git(path, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], check=False)
    return bool(out.strip())


def resolve_ref(path: Path, ref: str) -> str:
    """Return the full commit SHA a ref resolves to (validated)."""
    validate_ref(ref)
    out = run_git(path, ["rev-parse", "--verify", f"{ref}^{{commit}}"], check=True).strip()
    if not out:
        raise GitError(f"Could not resolve ref: {ref}")
    return out


def metadata(path: Path) -> dict:
    return {
        "default_branch": default_branch(path),
        "branches": list_branches(path),
        "tags": list_tags(path),
        "head": head_commit(path),
        "recent_commits": recent_commits(path),
    }
