"""Apply-fix: turn remediation targets into a concrete package.json edit.

Two modes, both of which NEVER run npm or any process:

* ``compute_fix`` — produce the exact edit, a unified diff, and the new file
  content, WITHOUT touching disk (powers copy / download / patch).
* ``write_fix`` — write the new package.json to disk after validating the path,
  keeping a timestamped ``.bak`` backup.

Direct dependencies are bumped in place (preserving the user's ``^``/``~``/exact
operator). Transitive packages can't be bumped directly, so they're pinned via
an npm ``overrides`` entry. After either mode the caller must run ``npm install``
themselves — DepLens deliberately does not, because install runs lifecycle
scripts (arbitrary code) in what we treat as an untrusted repository.
"""

from __future__ import annotations

import difflib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from deplens.analyzers.remediation import plan_remediation
from deplens.db import Database
from deplens.services.safety import PathSafetyError, is_within, resolve_project_root

DEP_FIELDS = ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]


@dataclass
class FixChange:
    package: str
    kind: str  # "dependency" | "override"
    field: Optional[str]  # which manifest section (for dependency)
    from_spec: Optional[str]
    to_spec: str


@dataclass
class FixEdit:
    manifest_path: str
    changes: List[FixChange] = field(default_factory=list)
    diff: str = ""
    old_content: str = ""
    new_content: str = ""
    install_command: str = "npm install"
    warnings: List[str] = field(default_factory=list)
    written: bool = False
    backup_path: Optional[str] = None


class ApplyError(Exception):
    pass


def _bump_spec(original: Optional[str], target: str) -> str:
    """Produce a new range for ``target`` preserving the original operator style."""
    if original and re.match(r"^\^\d", original):
        return f"^{target}"
    if original and re.match(r"^~\d", original):
        return f"~{target}"
    if original and re.match(r"^\d", original):  # exact pin
        return target
    # Non-standard spec (range, url, tag) → default to caret.
    return f"^{target}"


def _detect_indent(text: str):
    for line in text.splitlines():
        stripped = line.lstrip(" \t")
        if stripped and line != stripped:
            prefix = line[: len(line) - len(stripped)]
            return "\t" if "\t" in prefix else len(prefix)
    return 2


def _manifest_path(db: Database, scan_id: int) -> Path:
    scan = db.query_one("SELECT project_id FROM scans WHERE id=?", (scan_id,))
    if scan is None:
        raise ApplyError("Scan not found")
    project = db.get_project(scan["project_id"])
    if project is None:
        raise ApplyError("Project not found")
    try:
        root = resolve_project_root(project["path"])
    except PathSafetyError as exc:
        raise ApplyError(f"Project path is no longer accessible: {exc}") from exc
    manifest = root / "package.json"
    if not manifest.is_file() or not is_within(root, manifest):
        raise ApplyError("package.json not found in the project directory")
    return manifest


def compute_fix(db: Database, scan_id: int, packages: Optional[List[str]] = None) -> FixEdit:
    manifest_path = _manifest_path(db, scan_id)
    old_content = manifest_path.read_text(encoding="utf-8")
    try:
        data = json.loads(old_content)
    except json.JSONDecodeError as exc:
        raise ApplyError(f"package.json is not valid JSON: {exc}") from exc

    plan = plan_remediation(db, scan_id)
    wanted = set(packages) if packages else None
    actions = [
        a for a in plan.actions
        if a.target_version and (wanted is None or a.package in wanted)
    ]

    edit = FixEdit(manifest_path=str(manifest_path), old_content=old_content)
    if not actions:
        edit.warnings.append("No applicable fixes (no fixable advisories selected).")
        edit.new_content = old_content
        return edit

    overrides = dict(data.get("overrides") or {})
    for a in actions:
        if a.strategy == "direct":
            placed = False
            for fieldname in DEP_FIELDS:
                section = data.get(fieldname)
                if isinstance(section, dict) and a.package in section:
                    new_spec = _bump_spec(section[a.package], a.target_version)
                    edit.changes.append(
                        FixChange(a.package, "dependency", fieldname,
                                  section[a.package], new_spec)
                    )
                    section[a.package] = new_spec
                    placed = True
                    break
            if not placed:
                # Declared-direct but missing from the manifest — fall back to override.
                overrides[a.package] = a.target_version
                edit.changes.append(
                    FixChange(a.package, "override", None, None, a.target_version)
                )
        else:
            # Transitive (or no-direct) → npm overrides pin.
            prev = overrides.get(a.package)
            overrides[a.package] = a.target_version
            edit.changes.append(
                FixChange(a.package, "override", None, prev, a.target_version)
            )

    if overrides:
        data["overrides"] = overrides
        edit.warnings.append(
            "Transitive fixes use npm `overrides`, which require npm 8.3+."
        )

    indent = _detect_indent(old_content)
    new_content = json.dumps(data, indent=indent, ensure_ascii=False)
    if old_content.endswith("\n"):
        new_content += "\n"
    edit.new_content = new_content
    edit.diff = "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="package.json",
            tofile="package.json (proposed)",
        )
    )
    return edit


def write_fix(db: Database, scan_id: int, packages: Optional[List[str]] = None) -> FixEdit:
    edit = compute_fix(db, scan_id, packages)
    if not edit.changes:
        return edit
    manifest = Path(edit.manifest_path)
    backup = manifest.with_suffix(f".json.bak-{int(time.time())}")
    backup.write_text(edit.old_content, encoding="utf-8")
    manifest.write_text(edit.new_content, encoding="utf-8")
    edit.written = True
    edit.backup_path = str(backup)
    return edit


def edit_to_dict(edit: FixEdit) -> dict:
    return json.loads(json.dumps(asdict(edit)))
