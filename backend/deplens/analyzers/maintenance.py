"""Maintenance health signals, derived from public registry metadata.

Every signal shows its source and timestamp. DepLens does not compute an
arbitrary maintenance score; it reports concrete facts (last publish date,
release count, deprecation) and a coarse status with an explanation. Missing
data is reported as "unknown", never filled in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from deplens.services.registry import RegistryInfo

ACTIVE = "active"
LOW_ACTIVITY = "low-activity"
CONCERNS = "concerns"
DEPRECATED = "deprecated"
UNKNOWN = "unknown"


@dataclass
class MaintenanceResult:
    package: str
    status: str
    last_publish: Optional[str]
    days_since_publish: Optional[int]
    release_count: Optional[int]
    deprecated: bool
    deprecation_message: Optional[str]
    repository: Optional[str]
    signals: List[str]


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def analyze_maintenance(
    package: str, info: Optional[RegistryInfo], now: Optional[datetime] = None
) -> MaintenanceResult:
    now = now or datetime.now(timezone.utc)
    if info is None or not info.available:
        return MaintenanceResult(
            package=package,
            status=UNKNOWN,
            last_publish=None,
            days_since_publish=None,
            release_count=None,
            deprecated=False,
            deprecation_message=None,
            repository=None,
            signals=["No registry data available (offline or package not found)."],
        )

    signals: List[str] = []
    last_dt: Optional[datetime] = None
    last_str: Optional[str] = None
    for _ver, ts in info.version_times.items():
        dt = _parse_iso(ts)
        if dt and (last_dt is None or dt > last_dt):
            last_dt = dt
            last_str = ts
    days = None
    if last_dt is not None:
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        days = (now - last_dt).days
        signals.append(f"Most recent release published {days} days ago (registry 'time').")
    release_count = len(info.version_times) or None
    if release_count:
        signals.append(f"{release_count} published versions on the registry.")

    deprecated = bool(info.deprecated)
    if deprecated:
        signals.append(f"Latest version is marked deprecated: {info.deprecated}")

    # Status decision — conservative, based only on available data.
    if deprecated:
        status = DEPRECATED
    elif days is None:
        status = UNKNOWN
        signals.append("No publish timestamps available to judge activity.")
    elif days <= 365:
        status = ACTIVE
    elif days <= 730:
        status = LOW_ACTIVITY
        signals.append("No release in over a year — reduced activity.")
    else:
        status = CONCERNS
        signals.append("No release in over two years — possible maintenance concerns.")

    return MaintenanceResult(
        package=package,
        status=status,
        last_publish=last_str,
        days_since_publish=days,
        release_count=release_count,
        deprecated=deprecated,
        deprecation_message=info.deprecated,
        repository=info.repository,
        signals=signals,
    )
