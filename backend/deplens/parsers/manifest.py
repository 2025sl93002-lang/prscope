"""Parse ``package.json`` manifests safely.

Manifest content is untrusted. We read it as JSON only (no code execution),
enforce a size limit, and tolerate malformed or partial data by returning what
we can plus a list of warnings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

MAX_MANIFEST_BYTES = 5 * 1024 * 1024  # 5 MB — a package.json this large is already suspect.

DEP_FIELDS = {
    "dependencies": "prod",
    "devDependencies": "dev",
    "optionalDependencies": "optional",
    "peerDependencies": "peer",
}


@dataclass
class ManifestDependency:
    name: str
    spec: str  # the version range as written in the manifest
    scope: str  # prod | dev | optional | peer


@dataclass
class Manifest:
    name: Optional[str]
    version: Optional[str]
    private: bool
    dependencies: List[ManifestDependency]
    scripts: Dict[str, str]
    raw: dict
    warnings: List[str] = field(default_factory=list)

    def declared(self) -> Dict[str, ManifestDependency]:
        """Return a {name: dependency} map, with prod winning over dev/optional/peer."""
        order = {"prod": 0, "optional": 1, "peer": 2, "dev": 3}
        out: Dict[str, ManifestDependency] = {}
        for dep in self.dependencies:
            existing = out.get(dep.name)
            if existing is None or order[dep.scope] < order[existing.scope]:
                out[dep.name] = dep
        return out


def parse_manifest_text(text: str) -> Manifest:
    warnings: List[str] = []
    if len(text.encode("utf-8", errors="ignore")) > MAX_MANIFEST_BYTES:
        raise ValueError("package.json exceeds the maximum supported size (5 MB)")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"package.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("package.json must contain a JSON object")

    deps: List[ManifestDependency] = []
    for field_name, scope in DEP_FIELDS.items():
        section = data.get(field_name)
        if section is None:
            continue
        if not isinstance(section, dict):
            warnings.append(f"'{field_name}' is not an object; ignored")
            continue
        for pkg, spec in section.items():
            if not isinstance(pkg, str) or not isinstance(spec, str):
                warnings.append(f"skipped malformed entry in {field_name}")
                continue
            deps.append(ManifestDependency(name=pkg, spec=spec, scope=scope))

    scripts = {}
    raw_scripts = data.get("scripts")
    if isinstance(raw_scripts, dict):
        scripts = {k: v for k, v in raw_scripts.items() if isinstance(v, str)}

    name = data.get("name") if isinstance(data.get("name"), str) else None
    version = data.get("version") if isinstance(data.get("version"), str) else None
    private = bool(data.get("private", False))

    return Manifest(
        name=name,
        version=version,
        private=private,
        dependencies=deps,
        scripts=scripts,
        raw=data,
        warnings=warnings,
    )
