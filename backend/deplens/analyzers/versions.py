"""Update intelligence: classify how far behind each dependency is.

Uses the installed version (from the lockfile) and the registry's published
versions. Every claim is grounded in registry data; when the registry is
unavailable the status is honestly "unknown".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from deplens import semver
from deplens.services.registry import RegistryInfo

# update_type values
UP_TO_DATE = "up-to-date"
PATCH = "patch"
MINOR = "minor"
MAJOR = "major"
PRERELEASE = "prerelease"
UNKNOWN = "unknown"


@dataclass
class UpdateStatus:
    package: str
    installed: str
    latest: Optional[str]
    update_type: str
    is_outdated: bool
    versions_behind: Optional[int]
    available: bool
    recommendation: str


def _stable_versions(info: RegistryInfo):
    out = []
    for v in info.all_versions:
        try:
            parsed = semver.parse(v)
        except semver.InvalidVersion:
            continue
        if not parsed.is_prerelease:
            out.append(v)
    return out


def analyze_update(package: str, installed: str, info: Optional[RegistryInfo]) -> UpdateStatus:
    if info is None or not info.available or not info.latest:
        reason = (
            info.error
            if info and info.error
            else "No registry data available (offline or unknown)."
        )
        return UpdateStatus(
            package=package,
            installed=installed,
            latest=info.latest if info else None,
            update_type=UNKNOWN,
            is_outdated=False,
            versions_behind=None,
            available=False,
            recommendation=f"Latest version could not be verified. {reason}",
        )

    latest = info.latest
    try:
        cmp = semver.compare(installed, latest)
    except semver.InvalidVersion:
        return UpdateStatus(
            package=package,
            installed=installed,
            latest=latest,
            update_type=UNKNOWN,
            is_outdated=False,
            versions_behind=None,
            available=True,
            recommendation="Installed version is not a standard semver string; cannot compare.",
        )

    if cmp >= 0:
        return UpdateStatus(
            package=package,
            installed=installed,
            latest=latest,
            update_type=UP_TO_DATE,
            is_outdated=False,
            versions_behind=0,
            available=True,
            recommendation="Up to date with the latest published release.",
        )

    change = semver.diff(installed, latest) or UNKNOWN
    # Count stable releases strictly newer than the installed version.
    behind = None
    try:
        stable = _stable_versions(info)
        behind = sum(1 for v in stable if semver.compare(v, installed) > 0)
    except semver.InvalidVersion:
        behind = None

    recs = {
        PATCH: "Patch update available — low risk; review the changelog and apply.",
        MINOR: "Minor update available — new features, should be backward compatible.",
        MAJOR: "Major update available — potentially breaking. Review the migration notes.",
        PRERELEASE: "Only a newer prerelease is available.",
    }
    return UpdateStatus(
        package=package,
        installed=installed,
        latest=latest,
        update_type=change,
        is_outdated=True,
        versions_behind=behind,
        available=True,
        recommendation=recs.get(change, "An update is available."),
    )
