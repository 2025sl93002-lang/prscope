"""Filesystem safety helpers.

Scanned repositories are untrusted. These helpers validate that every path we
touch stays inside the selected project root, refuse to follow symlinks out of
it, and cap how much we read. Nothing here ever executes project code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

MAX_FILE_BYTES = 2 * 1024 * 1024  # per-file read cap for source scanning
MAX_FILES_SCANNED = 20_000  # overall cap to bound analysis time


class PathSafetyError(ValueError):
    """Raised when a path escapes the project root or is otherwise unsafe."""


def resolve_project_root(raw_path: str) -> Path:
    """Resolve and validate a user-supplied project directory path."""
    if not raw_path or not isinstance(raw_path, str):
        raise PathSafetyError("A project path is required.")
    expanded = os.path.expanduser(raw_path)
    try:
        root = Path(expanded).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathSafetyError(f"Path does not exist or is not accessible: {raw_path}") from exc
    if not root.is_dir():
        raise PathSafetyError(f"Not a directory: {root}")
    return root


def is_within(root: Path, candidate: Path) -> bool:
    """Return True if ``candidate`` resolves to a location inside ``root``."""
    try:
        candidate.resolve().relative_to(root)
        return True
    except (ValueError, OSError):
        return False


SKIP_DIRS = {
    "node_modules",
    ".git",
    ".hg",
    ".svn",
    "dist",
    "build",
    "out",
    "coverage",
    ".next",
    ".nuxt",
    ".cache",
    ".vite",
    "vendor",
    "__pycache__",
}


def iter_source_files(
    root: Path, extensions: set, max_files: int = MAX_FILES_SCANNED
) -> Iterator[Path]:
    """Yield source files under ``root`` with safe traversal.

    Skips dependency/build directories, never descends into symlinked
    directories (symlink-loop and escape protection), and stops at ``max_files``.
    """
    count = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune skip-dirs and any symlinked directories in place.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d))
        ]
        for fname in filenames:
            full = Path(dirpath) / fname
            if full.suffix.lower() not in extensions:
                continue
            if full.is_symlink():
                continue
            if not is_within(root, full):
                continue
            yield full
            count += 1
            if count >= max_files:
                return


def read_text_capped(path: Path, cap: int = MAX_FILE_BYTES) -> str:
    """Read a file as UTF-8 text, capped at ``cap`` bytes, tolerating bad bytes."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(cap + 1)
    except OSError:
        return ""
    if len(data) > cap:
        data = data[:cap]
    return data.decode("utf-8", errors="replace")
