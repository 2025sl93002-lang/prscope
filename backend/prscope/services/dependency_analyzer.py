"""Dependency analyzer.

Extracts intra-repository dependency edges for **Python** and
**JavaScript/TypeScript** by reading file contents at a specific commit via
``git show`` (the working tree is never modified or executed).

Limitations (documented, not hidden):
  * Python resolution is heuristic over common source roots; dynamic imports and
    ``sys.path`` tricks are not resolved.
  * JS/TS resolves **relative** specifiers only. Bare/package specifiers and
    tsconfig path aliases are treated as external and not linked.
  * This is file-level static analysis — it approximates, and never guarantees,
    runtime behaviour.

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .. import config
from .gitutil import run_git

PY_EXT = (".py",)
JS_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_PY_SOURCE_ROOTS = ("src/", "backend/", "lib/", "app/", "source/")
_JS_RESOLVE_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte")


@dataclass
class DependencyGraphData:
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (src, dst, relation)
    files: set[str] = field(default_factory=set)
    python_files: int = 0
    js_files: int = 0
    unresolved: int = 0
    note: str = ""

    def edge_set(self) -> set[tuple[str, str]]:
        return {(s, d) for s, d, _ in self.edges}


# --------------------------------------------------------------------------- #
# File listing & content access
# --------------------------------------------------------------------------- #


def list_tree_files(repo_path, target_sha: str) -> list[str]:
    out = run_git(repo_path, ["ls-tree", "-r", "--name-only", "-z", target_sha], check=True)
    files = [p for p in out.split("\x00") if p]
    return files


def read_file_at(repo_path, target_sha: str, path: str) -> str | None:
    """Read a blob at a commit. Returns None on binary/oversized/missing files."""
    try:
        # Size guard first.
        size_out = run_git(
            repo_path, ["cat-file", "-s", f"{target_sha}:{path}"], check=False
        ).strip()
        if size_out.isdigit() and int(size_out) > config.MAX_FILE_BYTES:
            return None
        content = run_git(repo_path, ["show", f"{target_sha}:{path}"], check=False)
        return content
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Python
# --------------------------------------------------------------------------- #


def extract_python_imports(source: str) -> list[tuple[str, int, list[str]]]:
    """Return (module, relative_level, imported_names) for each import statement."""
    results: list[tuple[str, int, list[str]]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return results
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name, 0, []))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [a.name for a in node.names]
            results.append((module, node.level or 0, names))
    return results


def _module_candidates(path: str) -> list[str]:
    """Dotted module names a .py file can be imported as."""
    p = PurePosixPath(path)
    parts = list(p.parts)
    if parts and parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip .py
    candidates: list[str] = []
    if parts:
        candidates.append(".".join(parts))
    # Also expose module names with common source roots stripped.
    joined = "/".join(p.parts)
    for root in _PY_SOURCE_ROOTS:
        if joined.startswith(root):
            rest = joined[len(root):]
            rp = list(PurePosixPath(rest).parts)
            if rp and rp[-1] == "__init__.py":
                rp = rp[:-1]
            elif rp:
                rp[-1] = rp[-1][:-3]
            if rp:
                candidates.append(".".join(rp))
    return candidates


def _build_python_module_map(py_files: list[str]) -> dict[str, str]:
    module_map: dict[str, str] = {}
    for f in py_files:
        for name in _module_candidates(f):
            module_map.setdefault(name, f)
    return module_map


def _resolve_python_relative(importer: str, level: int, module: str) -> str:
    """Resolve a relative import to an absolute dotted module name."""
    pkg_parts = list(PurePosixPath(importer).parts)
    # Drop the filename to get the package; __init__.py counts as its own package.
    if pkg_parts and pkg_parts[-1] == "__init__.py":
        pkg_parts = pkg_parts[:-1]
    else:
        pkg_parts = pkg_parts[:-1]
    # Each extra level beyond 1 climbs one package.
    climb = level - 1
    if climb > 0:
        pkg_parts = pkg_parts[: len(pkg_parts) - climb] if climb <= len(pkg_parts) else []
    base = ".".join(pkg_parts)
    if module:
        return f"{base}.{module}" if base else module
    return base


def _resolve_python_module(
    module_map: dict[str, str], dotted: str, names: list[str]
) -> str | None:
    if not dotted and not names:
        return None
    # Prefer "<module>.<name>" submodule hits, then the module itself.
    for name in names:
        full = f"{dotted}.{name}" if dotted else name
        if full in module_map:
            return module_map[full]
    if dotted in module_map:
        return module_map[dotted]
    # Try progressively shorter prefixes (import a.b.c resolves to a.b or a).
    parts = dotted.split(".")
    for end in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:end])
        if prefix in module_map:
            return module_map[prefix]
    return None


# --------------------------------------------------------------------------- #
# JavaScript / TypeScript
# --------------------------------------------------------------------------- #

_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"]*?\sfrom\s+)?|export\s+[^'"]*?\sfrom\s+|"""
    r"""require\s*\(\s*|import\s*\(\s*)['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def extract_js_imports(source: str) -> list[str]:
    return [m.group(1) for m in _JS_IMPORT_RE.finditer(source)]


def _resolve_js_relative(importer: str, spec: str, file_set: set[str]) -> str | None:
    if not spec.startswith("."):
        return None  # bare/package specifier — external
    base_dir = PurePosixPath(importer).parent
    target = (base_dir / spec)
    # Normalize ".." and "." segments.
    norm = PurePosixPath(*_normalize(target.parts))
    candidates: list[str] = []
    s = str(norm)
    # Exact (with existing extension)
    candidates.append(s)
    for ext in _JS_RESOLVE_EXT:
        candidates.append(s + ext)
    for ext in _JS_RESOLVE_EXT:
        candidates.append(str(norm / ("index" + ext)))
    for c in candidates:
        if c in file_set:
            return c
    return None


def _normalize(parts: tuple[str, ...]) -> list[str]:
    stack: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if stack:
                stack.pop()
        else:
            stack.append(part)
    return stack


# --------------------------------------------------------------------------- #
# Graph construction
# --------------------------------------------------------------------------- #


def build_dependency_graph(repo_path, target_sha: str) -> DependencyGraphData:
    all_files = list_tree_files(repo_path, target_sha)
    if len(all_files) > config.MAX_SOURCE_FILES:
        all_files = all_files[: config.MAX_SOURCE_FILES]
    file_set = set(all_files)
    py_files = [f for f in all_files if f.endswith(PY_EXT)]
    js_files = [f for f in all_files if f.endswith(JS_EXT)]

    data = DependencyGraphData(files=file_set, python_files=len(py_files), js_files=len(js_files))
    module_map = _build_python_module_map(py_files)
    seen: set[tuple[str, str]] = set()

    for f in py_files:
        content = read_file_at(repo_path, target_sha, f)
        if content is None:
            continue
        for module, level, names in extract_python_imports(content):
            if level > 0:
                dotted = _resolve_python_relative(f, level, module)
                target = _resolve_python_module(module_map, dotted, names)
            else:
                target = _resolve_python_module(module_map, module, names)
            if target and target != f and (f, target) not in seen:
                seen.add((f, target))
                data.edges.append((f, target, "import"))
            elif target is None:
                data.unresolved += 1

    for f in js_files:
        content = read_file_at(repo_path, target_sha, f)
        if content is None:
            continue
        for spec in extract_js_imports(content):
            target = _resolve_js_relative(f, spec, file_set)
            if target and target != f and (f, target) not in seen:
                seen.add((f, target))
                data.edges.append((f, target, "import"))
            elif target is None and spec.startswith("."):
                data.unresolved += 1

    data.note = (
        f"Analyzed {len(py_files)} Python and {len(js_files)} JS/TS files; "
        f"{len(data.edges)} intra-repo edges, {data.unresolved} specifiers unresolved. "
        "File-level static analysis — relative JS/TS imports and heuristic Python "
        "module resolution only."
    )
    return data
