"""OSV.dev client for open-source vulnerability advisories.

OSV (https://osv.dev) is a free, open-source vulnerability database operated by
the OpenSSF. Its API requires no key and no account. DepLens uses the batch
endpoint to discover which installed packages have advisories, then fetches full
details for each unique advisory.

Privacy: only ``{ecosystem: "npm", name, version}`` tuples are sent. No source
code, project name, or personal data. All calls are opt-in via ``online``.

DepLens never invents advisories. If OSV is unreachable, security status is
reported as "unknown / not checked" — never as "secure".
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

OSV_API = "https://api.osv.dev"
USER_AGENT = "DepLens/0.1 (+https://github.com/deplens/deplens)"
REQUEST_TIMEOUT = 20.0
MAX_DETAIL_CONCURRENCY = 8

SEVERITY_ORDER = {"critical": 4, "high": 3, "moderate": 2, "low": 1, "unknown": 0}


@dataclass
class Vulnerability:
    id: str
    package: str
    installed_version: str
    severity: str  # critical | high | moderate | low | unknown
    summary: str
    details: str
    aliases: List[str] = field(default_factory=list)  # CVE ids etc.
    fixed_version: Optional[str] = None
    affected_ranges: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    published: Optional[str] = None
    modified: Optional[str] = None

    @property
    def cve(self) -> Optional[str]:
        for a in self.aliases:
            if a.upper().startswith("CVE-"):
                return a
        return None


def _normalize_severity(vuln: dict) -> str:
    db = vuln.get("database_specific") or {}
    raw = db.get("severity")
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in SEVERITY_ORDER:
            return low
        if low in ("medium",):
            return "moderate"
    # Derive from CVSS vectors if present.
    best = 0.0
    for sev in vuln.get("severity") or []:
        score = sev.get("score")
        if isinstance(score, (int, float)):
            best = max(best, float(score))
    if best:
        if best >= 9.0:
            return "critical"
        if best >= 7.0:
            return "high"
        if best >= 4.0:
            return "moderate"
        return "low"
    return "unknown"


def _extract_fixed_and_ranges(vuln: dict, pkg_name: str, installed: Optional[str] = None):
    """Extract affected ranges and the fix relevant to the installed version.

    OSV advisories often cover several release lines (e.g. a 0.x fix and a 1.x
    fix). We prefer the ``fixed`` version from the range whose
    ``[introduced, fixed)`` window actually contains the installed version, so
    the suggested upgrade target is the right one for this project.
    """
    from deplens import semver as _sv

    fixed: Optional[str] = None
    fixed_matching: Optional[str] = None
    ranges: List[str] = []
    for affected in vuln.get("affected") or []:
        pkg = affected.get("package") or {}
        if pkg.get("ecosystem") != "npm" or pkg.get("name") != pkg_name:
            continue
        for rng in affected.get("ranges") or []:
            introduced = None
            fixed_here = None
            for event in rng.get("events") or []:
                if "introduced" in event:
                    introduced = event["introduced"]
                if "fixed" in event:
                    fixed_here = event["fixed"]
            if introduced is not None or fixed_here is not None:
                lo = introduced if introduced not in (None, "0") else "0"
                hi = f"< {fixed_here}" if fixed_here else "(no fixed release)"
                ranges.append(f">= {lo}, {hi}")
            if fixed_here and fixed is None:
                fixed = fixed_here
            # Does this range contain the installed version?
            if installed and fixed_here:
                try:
                    lo_ok = introduced in (None, "0") or _sv.compare(installed, introduced) >= 0
                    hi_ok = _sv.compare(installed, fixed_here) < 0
                    if lo_ok and hi_ok and fixed_matching is None:
                        fixed_matching = fixed_here
                except _sv.InvalidVersion:
                    pass
    return (fixed_matching or fixed), ranges


class OSVClient:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
            )
        return self

    async def __aexit__(self, *exc):
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def query_packages(
        self, packages: List[tuple]
    ) -> Dict[str, List[Vulnerability]]:
        """Return {``name@version``: [Vulnerability, ...]} for the given packages.

        ``packages`` is a list of ``(name, version)`` tuples.
        """
        if not packages:
            return {}
        queries = [
            {"package": {"ecosystem": "npm", "name": n}, "version": v} for n, v in packages
        ]
        resp = await self._client.post(f"{OSV_API}/v1/querybatch", json={"queries": queries})
        resp.raise_for_status()
        batch = resp.json().get("results", [])

        # Collect unique vuln IDs and which package they belong to.
        id_to_packages: Dict[str, List[tuple]] = {}
        for (name, version), result in zip(packages, batch):
            for v in result.get("vulns") or []:
                vid = v.get("id")
                if vid:
                    id_to_packages.setdefault(vid, []).append((name, version))

        details = await self._fetch_details(list(id_to_packages.keys()))

        out: Dict[str, List[Vulnerability]] = {}
        for vid, pkgs in id_to_packages.items():
            raw = details.get(vid)
            if raw is None:
                continue
            for name, version in pkgs:
                fixed, ranges = _extract_fixed_and_ranges(raw, name, version)
                refs = [r.get("url") for r in (raw.get("references") or []) if r.get("url")]
                vuln = Vulnerability(
                    id=vid,
                    package=name,
                    installed_version=version,
                    severity=_normalize_severity(raw),
                    summary=raw.get("summary") or vid,
                    details=(raw.get("details") or "")[:4000],
                    aliases=raw.get("aliases") or [],
                    fixed_version=fixed,
                    affected_ranges=ranges,
                    references=refs[:10],
                    published=raw.get("published"),
                    modified=raw.get("modified"),
                )
                out.setdefault(f"{name}@{version}", []).append(vuln)
        return out

    async def _fetch_details(self, ids: List[str]) -> Dict[str, dict]:
        sem = asyncio.Semaphore(MAX_DETAIL_CONCURRENCY)

        async def _one(vid: str):
            async with sem:
                try:
                    r = await self._client.get(f"{OSV_API}/v1/vulns/{vid}")
                    if r.status_code == 200:
                        return vid, r.json()
                except httpx.HTTPError:
                    return vid, None
                return vid, None

        results = await asyncio.gather(*(_one(v) for v in ids))
        return {vid: doc for vid, doc in results if doc is not None}
