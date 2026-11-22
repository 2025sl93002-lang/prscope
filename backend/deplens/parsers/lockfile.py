"""Parse ``package-lock.json`` (npm lockfile versions 1, 2 and 3) safely.

The lockfile is the authoritative source of the *resolved* dependency tree: the
exact installed versions and the edges between them. We never execute anything;
we read JSON, enforce a size limit, and reconstruct the graph using npm's own
``node_modules`` resolution rules.

Output is normalised across all three formats:

* :class:`LockPackage` — one unique ``name@version`` installed package.
* :class:`LockEdge` — a resolved dependency relationship (who requires whom).

Unsupported or malformed input yields explicit warnings rather than silent,
incomplete results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

MAX_LOCKFILE_BYTES = 50 * 1024 * 1024  # 50 MB upper bound to avoid memory blow-ups.

ROOT_ID = "(root project)"


@dataclass
class LockPackage:
    name: str
    version: str
    scopes: Set[str] = field(default_factory=set)  # prod | dev | optional | peer
    resolved: Optional[str] = None
    integrity: Optional[str] = None
    is_direct: bool = False

    @property
    def id(self) -> str:
        return f"{self.name}@{self.version}"


@dataclass
class LockEdge:
    source: str  # node id (or ROOT_ID)
    target: str  # node id
    spec: str  # the range the source declared
    edge_type: str  # prod | dev | optional | peer


@dataclass
class Lockfile:
    lockfile_version: int
    fmt: str  # "v1" | "v2" | "v3"
    root_name: Optional[str]
    root_version: Optional[str]
    packages: Dict[str, LockPackage]  # keyed by name@version
    edges: List[LockEdge]
    direct: Dict[str, str]  # name -> scope, for packages declared by the root
    warnings: List[str] = field(default_factory=list)


def _name_from_path(path: str, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    marker = "node_modules/"
    idx = path.rfind(marker)
    if idx == -1:
        return None
    return path[idx + len(marker):]


def parse_lockfile_text(text: str) -> Lockfile:
    if len(text.encode("utf-8", errors="ignore")) > MAX_LOCKFILE_BYTES:
        raise ValueError("package-lock.json exceeds the maximum supported size (50 MB)")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"package-lock.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("package-lock.json must contain a JSON object")

    version = data.get("lockfileVersion")
    if not isinstance(version, int):
        # Pre-v5 npm lockfiles sometimes omit it; infer from structure.
        version = 2 if isinstance(data.get("packages"), dict) else 1

    if version >= 2 and isinstance(data.get("packages"), dict):
        return _parse_packages_format(data, version)
    if isinstance(data.get("dependencies"), dict):
        return _parse_dependencies_format(data, version)
    raise ValueError(
        f"Unsupported package-lock.json structure (lockfileVersion={version}). "
        "Expected a 'packages' map (v2/v3) or a 'dependencies' tree (v1)."
    )


# --------------------------------------------------------------------------- #
# v2 / v3: the modern "packages" map keyed by install path
# --------------------------------------------------------------------------- #


def _resolve_in_packages(requiring_path: str, dep_name: str, raw_packages: dict) -> Optional[str]:
    """Resolve ``dep_name`` from ``requiring_path`` using node_modules walk-up."""
    prefix = requiring_path
    while True:
        base = f"{prefix}/node_modules/{dep_name}" if prefix else f"node_modules/{dep_name}"
        if base in raw_packages:
            return base
        if not prefix:
            return None
        idx = prefix.rfind("/node_modules/")
        prefix = prefix[:idx] if idx != -1 else ""


def _parse_packages_format(data: dict, version: int) -> Lockfile:
    warnings: List[str] = []
    raw_packages: dict = data["packages"]
    root_entry = raw_packages.get("", {})
    root_name = root_entry.get("name") or data.get("name")
    root_version = root_entry.get("version") or data.get("version")

    packages: Dict[str, LockPackage] = {}
    edges: List[LockEdge] = []

    # First pass: register every installed package node (deduped by name@version).
    path_to_id: Dict[str, str] = {}
    for path, entry in raw_packages.items():
        if path == "" or not isinstance(entry, dict):
            continue
        if entry.get("link"):
            # Workspace symlink — not an installed third-party package.
            continue
        name = _name_from_path(path, entry.get("name"))
        ver = entry.get("version")
        if not name or not isinstance(ver, str):
            warnings.append(f"skipped lockfile entry without name/version: {path!r}")
            continue
        node_id = f"{name}@{ver}"
        path_to_id[path] = node_id
        pkg = packages.get(node_id)
        if pkg is None:
            pkg = LockPackage(
                name=name,
                version=ver,
                resolved=entry.get("resolved"),
                integrity=entry.get("integrity"),
            )
            packages[node_id] = pkg
        if entry.get("dev"):
            pkg.scopes.add("dev")
        elif entry.get("optional"):
            pkg.scopes.add("optional")
        else:
            pkg.scopes.add("prod")

    # Root direct dependencies by scope.
    direct: Dict[str, str] = {}
    scope_fields = [
        ("dependencies", "prod"),
        ("devDependencies", "dev"),
        ("optionalDependencies", "optional"),
        ("peerDependencies", "peer"),
    ]
    for fieldname, scope in scope_fields:
        section = root_entry.get(fieldname)
        if not isinstance(section, dict):
            continue
        for dep_name, spec in section.items():
            direct.setdefault(dep_name, scope)
            resolved_path = _resolve_in_packages("", dep_name, raw_packages)
            if resolved_path and resolved_path in path_to_id:
                tid = path_to_id[resolved_path]
                packages[tid].is_direct = True
                edges.append(LockEdge(ROOT_ID, tid, spec if isinstance(spec, str) else "*", scope))

    # Second pass: edges between installed packages.
    for path, entry in raw_packages.items():
        if path == "" or not isinstance(entry, dict) or path not in path_to_id:
            continue
        source_id = path_to_id[path]
        for fieldname, scope in [
            ("dependencies", "prod"),
            ("optionalDependencies", "optional"),
            ("peerDependencies", "peer"),
        ]:
            section = entry.get(fieldname)
            if not isinstance(section, dict):
                continue
            for dep_name, spec in section.items():
                resolved_path = _resolve_in_packages(path, dep_name, raw_packages)
                if resolved_path and resolved_path in path_to_id:
                    edges.append(
                        LockEdge(
                            source_id,
                            path_to_id[resolved_path],
                            spec if isinstance(spec, str) else "*",
                            scope,
                        )
                    )

    return Lockfile(
        lockfile_version=version,
        fmt="v3" if version >= 3 else "v2",
        root_name=root_name,
        root_version=root_version,
        packages=packages,
        edges=_dedupe_edges(edges),
        direct=direct,
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# v1: the legacy nested "dependencies" tree
# --------------------------------------------------------------------------- #


def _parse_dependencies_format(data: dict, version: int) -> Lockfile:
    warnings: List[str] = []
    packages: Dict[str, LockPackage] = {}
    edges: List[LockEdge] = []
    root_name = data.get("name")
    root_version = data.get("version")

    # Build nested scope chain so "requires" can be resolved by walking up.
    def register(name: str, entry: dict, scope: str) -> Optional[str]:
        ver = entry.get("version")
        if not isinstance(ver, str):
            warnings.append(f"skipped v1 lock entry without version: {name!r}")
            return None
        node_id = f"{name}@{ver}"
        pkg = packages.get(node_id)
        if pkg is None:
            pkg = LockPackage(
                name=name,
                version=ver,
                resolved=entry.get("resolved"),
                integrity=entry.get("integrity"),
            )
            packages[node_id] = pkg
        if entry.get("dev"):
            pkg.scopes.add("dev")
        elif entry.get("optional"):
            pkg.scopes.add("optional")
        else:
            pkg.scopes.add("prod")
        return node_id

    # scope_stack: list of dicts mapping name -> node_id available at each level.
    def resolve_require(name: str, scope_stack: List[Dict[str, str]]) -> Optional[str]:
        for level in reversed(scope_stack):
            if name in level:
                return level[name]
        return None

    pending_edges: List[Tuple[str, str, str, str, List[Dict[str, str]]]] = []

    def walk(deps: dict, scope_stack: List[Dict[str, str]], is_root: bool) -> Dict[str, str]:
        # Register this level's packages first so siblings can resolve each other.
        level: Dict[str, str] = {}
        local_entries = []
        for name, entry in deps.items():
            if not isinstance(entry, dict):
                continue
            inferred_scope = "dev" if entry.get("dev") else (
                "optional" if entry.get("optional") else "prod"
            )
            node_id = register(name, entry, inferred_scope)
            if node_id is None:
                continue
            level[name] = node_id
            if is_root:
                packages[node_id].is_direct = True
            local_entries.append((name, entry, node_id, inferred_scope))
        new_stack = scope_stack + [level]
        for _name, entry, node_id, scope in local_entries:
            if is_root:
                edges.append(LockEdge(ROOT_ID, node_id, "*", scope))
            # Recurse into this entry's own nested deps first; they are installed
            # under this package's node_modules and take priority for its requires.
            nested = entry.get("dependencies")
            children: Dict[str, str] = {}
            if isinstance(nested, dict):
                children = walk(nested, new_stack, is_root=False)
            requires = entry.get("requires")
            if isinstance(requires, dict):
                # Own nested deps (children) resolve before ancestor scopes.
                resolve_stack = new_stack + [children]
                for req_name, spec in requires.items():
                    pending_edges.append(
                        (node_id, req_name, spec if isinstance(spec, str) else "*", scope,
                         resolve_stack)
                    )
        return level

    root_deps = data.get("dependencies", {})
    walk(root_deps, [], is_root=True)

    for source_id, req_name, spec, scope, stack in pending_edges:
        target = resolve_require(req_name, stack)
        if target:
            edges.append(LockEdge(source_id, target, spec, scope))

    direct = {p.name: next(iter(p.scopes), "prod") for p in packages.values() if p.is_direct}

    return Lockfile(
        lockfile_version=version,
        fmt="v1",
        root_name=root_name,
        root_version=root_version,
        packages=packages,
        edges=_dedupe_edges(edges),
        direct=direct,
        warnings=warnings,
    )


def _dedupe_edges(edges: List[LockEdge]) -> List[LockEdge]:
    seen: Set[Tuple[str, str, str]] = set()
    out: List[LockEdge] = []
    for e in edges:
        key = (e.source, e.target, e.edge_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out
