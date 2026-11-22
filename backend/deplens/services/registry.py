"""npm registry client.

Fetches public package metadata (latest version, license, repository, publish
times, deprecation) used by the update, license and maintenance analyzers.

Privacy: the only thing sent to the registry is the package *name* in the URL
path and a generic client identifier. No repository contents, no project name,
no personal data. All calls are opt-in via the scan's ``online`` flag.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

DEFAULT_REGISTRY = "https://registry.npmjs.org"
USER_AGENT = "DepLens/0.1 (+https://github.com/deplens/deplens)"
REQUEST_TIMEOUT = 15.0
MAX_CONCURRENCY = 8


@dataclass
class RegistryInfo:
    name: str
    available: bool
    latest: Optional[str] = None
    all_versions: List[str] = field(default_factory=list)
    license: Optional[str] = None
    deprecated: Optional[str] = None
    repository: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    # publish timestamps keyed by version (ISO 8601 strings)
    version_times: Dict[str, str] = field(default_factory=dict)
    modified: Optional[str] = None
    error: Optional[str] = None


def _extract_license(version_doc: dict) -> Optional[str]:
    lic = version_doc.get("license")
    if isinstance(lic, str):
        return lic
    if isinstance(lic, dict):  # legacy {type: "..."}
        return lic.get("type")
    licenses = version_doc.get("licenses")
    if isinstance(licenses, list) and licenses:
        parts = [
            item.get("type")
            for item in licenses
            if isinstance(item, dict) and item.get("type")
        ]
        if parts:
            return " OR ".join(parts)
    return None


def _extract_repository(doc: dict) -> Optional[str]:
    repo = doc.get("repository")
    if isinstance(repo, str):
        return repo
    if isinstance(repo, dict):
        return repo.get("url")
    return None


class RegistryClient:
    def __init__(
        self, registry: str = DEFAULT_REGISTRY, client: Optional[httpx.AsyncClient] = None
    ):
        self.registry = registry.rstrip("/")
        self._client = client
        self._owns_client = client is None
        self._cache: Dict[str, RegistryInfo] = {}

    async def __aenter__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
            )
        return self

    async def __aexit__(self, *exc):
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def get(self, name: str) -> RegistryInfo:
        if name in self._cache:
            return self._cache[name]
        info = await self._fetch(name)
        self._cache[name] = info
        return info

    async def _fetch(self, name: str) -> RegistryInfo:
        # Scoped names must be URL-encoded (@scope/pkg -> @scope%2Fpkg).
        encoded = name.replace("/", "%2F")
        url = f"{self.registry}/{encoded}"
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            return RegistryInfo(name=name, available=False, error=f"network error: {exc}")
        if resp.status_code == 404:
            return RegistryInfo(name=name, available=False, error="package not found on registry")
        if resp.status_code != 200:
            return RegistryInfo(
                name=name, available=False, error=f"registry returned HTTP {resp.status_code}"
            )
        try:
            doc = resp.json()
        except ValueError:
            return RegistryInfo(name=name, available=False, error="invalid JSON from registry")

        dist_tags = doc.get("dist-tags") or {}
        latest = dist_tags.get("latest")
        versions = doc.get("versions") or {}
        latest_doc = versions.get(latest, {}) if latest else {}
        times = doc.get("time") or {}
        version_times = {v: t for v, t in times.items() if v not in ("created", "modified")}

        return RegistryInfo(
            name=name,
            available=True,
            latest=latest,
            all_versions=list(versions.keys()),
            license=_extract_license(latest_doc) or _extract_license(doc),
            deprecated=latest_doc.get("deprecated") if isinstance(latest_doc, dict) else None,
            repository=_extract_repository(latest_doc) or _extract_repository(doc),
            homepage=doc.get("homepage"),
            description=doc.get("description"),
            version_times=version_times,
            modified=times.get("modified"),
        )

    async def get_many(self, names: List[str]) -> Dict[str, RegistryInfo]:
        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async def _one(n: str):
            async with sem:
                return n, await self.get(n)

        results = await asyncio.gather(*(_one(n) for n in names))
        return dict(results)
