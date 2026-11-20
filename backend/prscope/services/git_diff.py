"""Git diff parser.

Produces a structured list of changed files between two refs using read-only
``git`` plumbing. Uses three-dot (merge-base) range semantics by default to
mirror how a pull request is reviewed — "what the target branch introduces
relative to the base" — and falls back to a two-dot range when no merge base
exists. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import repository_manager as repo_mgr
from .gitutil import GitError, run_git, validate_ref


@dataclass
class DiffFile:
    path: str
    change_type: str  # added | modified | deleted | renamed
    old_path: str | None = None
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class DiffResult:
    base_ref: str
    target_ref: str
    base_sha: str
    target_sha: str
    range_kind: str  # "three-dot" | "two-dot"
    files: list[DiffFile] = field(default_factory=list)

    @property
    def total_added(self) -> int:
        return sum(f.lines_added for f in self.files)

    @property
    def total_removed(self) -> int:
        return sum(f.lines_removed for f in self.files)


_STATUS_MAP = {"A": "added", "M": "modified", "D": "deleted"}


def _coerce_int(value: str) -> int:
    return 0 if value == "-" else int(value)


def _split_z(raw: str) -> list[str]:
    parts = raw.split("\x00")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _parse_numstat(raw: str) -> dict[str, tuple[int, int]]:
    """Map path -> (added, removed). Rename detection disabled so every path is plain."""
    out: dict[str, tuple[int, int]] = {}
    for token in _split_z(raw):
        # Each token is "<added>\t<removed>\t<path>"
        fields = token.split("\t")
        if len(fields) < 3:
            continue
        added, removed, path = fields[0], fields[1], "\t".join(fields[2:])
        out[path] = (_coerce_int(added), _coerce_int(removed))
    return out


def _parse_name_status(tokens: list[str]) -> list[DiffFile]:
    """Parse ``--name-status -M -z`` token stream into DiffFile records."""
    files: list[DiffFile] = []
    i = 0
    n = len(tokens)
    while i < n:
        status = tokens[i]
        i += 1
        code = status[0] if status else ""
        if code in ("R", "C"):  # rename/copy: next two tokens are old, new
            if i + 1 >= n:
                break
            old_path, new_path = tokens[i], tokens[i + 1]
            i += 2
            files.append(
                DiffFile(path=new_path, old_path=old_path, change_type="renamed")
            )
        elif code in _STATUS_MAP:
            if i >= n:
                break
            path = tokens[i]
            i += 1
            files.append(DiffFile(path=path, change_type=_STATUS_MAP[code]))
        elif code in ("T",):  # type change — treat as modified
            if i >= n:
                break
            files.append(DiffFile(path=tokens[i], change_type="modified"))
            i += 1
        else:
            # Unknown status; skip its path token defensively.
            i += 1
    return files


def _merge_base(path: Path, base_sha: str, target_sha: str) -> str | None:
    out = run_git(path, ["merge-base", base_sha, target_sha], check=False).strip()
    return out or None


def compute_diff(repo_path: Path, base_ref: str, target_ref: str) -> DiffResult:
    """Compute the structured diff between two validated refs."""
    validate_ref(base_ref)
    validate_ref(target_ref)
    base_sha = repo_mgr.resolve_ref(repo_path, base_ref)
    target_sha = repo_mgr.resolve_ref(repo_path, target_ref)
    if base_sha == target_sha:
        return DiffResult(base_ref, target_ref, base_sha, target_sha, "two-dot", [])

    mb = _merge_base(repo_path, base_sha, target_sha)
    range_kind = "three-dot" if mb else "two-dot"
    diff_from = mb if mb else base_sha

    name_status_raw = run_git(
        repo_path,
        ["diff", "--name-status", "-M", "-z", diff_from, target_sha],
        check=True,
    )
    numstat_raw = run_git(
        repo_path,
        ["diff", "--numstat", "--no-renames", "-z", diff_from, target_sha],
        check=True,
    )

    files = _parse_name_status(_split_z(name_status_raw))
    numstat = _parse_numstat(numstat_raw)

    from .. import config as _cfg  # local import to honour runtime overrides

    if len(files) > _cfg.MAX_DIFF_FILES:
        raise GitError(
            f"Diff contains {len(files)} files, exceeding the safety limit of "
            f"{_cfg.MAX_DIFF_FILES} (PRSCOPE_MAX_DIFF_FILES)."
        )

    for f in files:
        if f.change_type == "deleted":
            added, removed = numstat.get(f.path, (0, 0))
            f.lines_added, f.lines_removed = added, removed
        elif f.change_type == "renamed":
            a_new, r_new = numstat.get(f.path, (0, 0))
            a_old, r_old = numstat.get(f.old_path or "", (0, 0))
            f.lines_added = a_new
            f.lines_removed = r_old or r_new
        else:
            added, removed = numstat.get(f.path, (0, 0))
            f.lines_added, f.lines_removed = added, removed

    files.sort(key=lambda x: x.path)
    return DiffResult(base_ref, target_ref, base_sha, target_sha, range_kind, files)


def summarize(diff: DiffResult) -> dict:
    counts = {"added": 0, "modified": 0, "deleted": 0, "renamed": 0}
    for f in diff.files:
        counts[f.change_type] = counts.get(f.change_type, 0) + 1
    return {
        "files_changed": len(diff.files),
        "files_added": counts["added"],
        "files_modified": counts["modified"],
        "files_deleted": counts["deleted"],
        "files_renamed": counts["renamed"],
        "lines_added": diff.total_added,
        "lines_removed": diff.total_removed,
    }
