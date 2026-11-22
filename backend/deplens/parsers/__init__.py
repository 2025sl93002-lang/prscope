"""Safe parsers for npm project files (manifests and lockfiles)."""

from deplens.parsers.lockfile import (
    ROOT_ID,
    LockEdge,
    Lockfile,
    LockPackage,
    parse_lockfile_text,
)
from deplens.parsers.manifest import (
    Manifest,
    ManifestDependency,
    parse_manifest_text,
)

__all__ = [
    "ROOT_ID",
    "Lockfile",
    "LockEdge",
    "LockPackage",
    "parse_lockfile_text",
    "Manifest",
    "ManifestDependency",
    "parse_manifest_text",
]
