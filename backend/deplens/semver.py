"""A focused, dependency-free implementation of a useful subset of node-semver.

DepLens needs to parse npm package versions, compare them with correct semantic
version precedence (including prerelease handling), decide whether a version
satisfies a range from a manifest (``^1.2.0``, ``~1.2``, ``1.x``, ``>=1.0 <2``,
``1.2.3 - 2.0.0``, ``a || b``), and classify the gap between two versions as a
major / minor / patch / prerelease update.

This is a deliberate subset of the full npm range grammar. It covers the forms
that appear in real ``package.json`` files. Anything it genuinely cannot parse
raises :class:`InvalidRange` / returns ``None`` so callers can surface an honest
"unknown" state rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import List, Optional

__all__ = [
    "Version",
    "InvalidVersion",
    "InvalidRange",
    "parse",
    "compare",
    "satisfies",
    "max_satisfying",
    "diff",
    "clean",
]

_NUM = r"0|[1-9]\d*"
_VERSION_RE = re.compile(
    rf"^v?(?P<major>{_NUM})"
    rf"\.(?P<minor>{_NUM})"
    rf"\.(?P<patch>{_NUM})"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


class InvalidVersion(ValueError):
    """Raised when a string cannot be parsed as a semantic version."""


class InvalidRange(ValueError):
    """Raised when a range string cannot be parsed."""


@total_ordering
@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple = ()
    build: tuple = ()

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += "-" + ".".join(str(p) for p in self.prerelease)
        return base

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == (
            other.major,
            other.minor,
            other.patch,
            other.prerelease,
        )

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def __lt__(self, other: "Version") -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        # A version WITH a prerelease has lower precedence than one without.
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return _compare_prerelease(self.prerelease, other.prerelease) < 0


def _coerce_identifier(ident: str):
    """Numeric identifiers compare numerically; everything else lexically."""
    if ident.isdigit():
        return (0, int(ident))
    return (1, ident)


def _compare_prerelease(a: tuple, b: tuple) -> int:
    for x, y in zip(a, b):
        cx, cy = _coerce_identifier(str(x)), _coerce_identifier(str(y))
        if cx != cy:
            return -1 if cx < cy else 1
    if len(a) != len(b):
        return -1 if len(a) < len(b) else 1
    return 0


def parse(version: str) -> Version:
    if not isinstance(version, str):
        raise InvalidVersion(f"version must be a string, got {type(version)!r}")
    match = _VERSION_RE.match(version.strip())
    if not match:
        raise InvalidVersion(f"not a valid semver version: {version!r}")
    pre = tuple(match.group("prerelease").split(".")) if match.group("prerelease") else ()
    build = tuple(match.group("build").split(".")) if match.group("build") else ()
    return Version(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        pre,
        build,
    )


def clean(version: str) -> Optional[str]:
    """Return the normalized version string, or ``None`` if unparseable."""
    try:
        return str(parse(version))
    except InvalidVersion:
        return None


def compare(a: str, b: str) -> int:
    """Return -1, 0, or 1 comparing versions ``a`` and ``b``."""
    va, vb = parse(a), parse(b)
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


def diff(a: str, b: str) -> Optional[str]:
    """Classify the change from version ``a`` to ``b``.

    Returns ``"major"``, ``"minor"``, ``"patch"``, ``"prerelease"`` or ``None``
    when the versions are equal. Order-independent.
    """
    va, vb = parse(a), parse(b)
    if va == vb:
        return None
    if va.major != vb.major:
        return "major"
    if va.minor != vb.minor:
        return "minor"
    if va.patch != vb.patch:
        return "patch"
    return "prerelease"


# --------------------------------------------------------------------------- #
# Range handling
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Comparator:
    op: str  # one of < <= > >= =
    version: Version

    def test(self, v: Version) -> bool:
        if self.op == "=":
            return v == self.version
        if self.op == "<":
            return v < self.version
        if self.op == "<=":
            return v <= self.version
        if self.op == ">":
            return v > self.version
        if self.op == ">=":
            return v >= self.version
        raise InvalidRange(f"unknown comparator op {self.op!r}")


_XRANGE_RE = re.compile(
    r"^(?P<op>[<>]=?|=|\^|~)?\s*"
    r"v?(?P<major>\d+|[xX*])"
    r"(?:\.(?P<minor>\d+|[xX*]))?"
    r"(?:\.(?P<patch>\d+|[xX*]))?"
    r"(?:-(?P<prerelease>[0-9A-Za-z-.]+))?"
    r"(?:\+[0-9A-Za-z-.]+)?$"
)


def _is_wildcard(part: Optional[str]) -> bool:
    return part is None or part in ("x", "X", "*")


def _parse_simple(token: str) -> List[_Comparator]:
    """Parse a single simple range token into >=/< comparators."""
    token = token.strip()
    if token in ("", "*", "x", "X"):
        return [_Comparator(">=", Version(0, 0, 0))]

    m = _XRANGE_RE.match(token)
    if not m:
        raise InvalidRange(f"unparseable range token: {token!r}")

    op = m.group("op") or "="
    major_raw, minor_raw, patch_raw = m.group("major"), m.group("minor"), m.group("patch")
    pre = tuple(m.group("prerelease").split(".")) if m.group("prerelease") else ()

    major_wild = _is_wildcard(major_raw)
    minor_wild = _is_wildcard(minor_raw)
    patch_wild = _is_wildcard(patch_raw)

    major = 0 if major_wild else int(major_raw)
    minor = 0 if minor_wild else int(minor_raw)
    patch = 0 if patch_wild else int(patch_raw)
    base = Version(major, minor, patch, pre)

    # Caret: compatible within the left-most non-zero component.
    if op == "^":
        if major > 0 or major_wild:
            upper = Version(major + 1, 0, 0)
        elif minor > 0 or minor_wild:
            upper = Version(0, minor + 1, 0)
        else:
            upper = Version(0, 0, patch + 1)
        return [_Comparator(">=", base), _Comparator("<", upper)]

    # Tilde: allow patch-level (or minor-level if no minor given) changes.
    if op == "~":
        if minor_wild:
            upper = Version(major + 1, 0, 0)
        else:
            upper = Version(major, minor + 1, 0)
        return [_Comparator(">=", base), _Comparator("<", upper)]

    # Implicit equality ("=") with wildcards expands to a family range,
    # e.g. 1.x -> >=1.0.0 <2.0.0, 1.2.x -> >=1.2.0 <1.3.0, 1 -> >=1.0.0 <2.0.0.
    if op == "=":
        if major_wild:
            return [_Comparator(">=", Version(0, 0, 0))]
        if minor_wild:
            return [
                _Comparator(">=", Version(major, 0, 0)),
                _Comparator("<", Version(major + 1, 0, 0)),
            ]
        if patch_wild:
            return [
                _Comparator(">=", Version(major, minor, 0)),
                _Comparator("<", Version(major, minor + 1, 0)),
            ]
        return [_Comparator("=", base)]

    # Explicit comparators with partial versions follow node-semver's rules:
    # partial lower bounds fill zeros; partial upper/strict bounds bump a component.
    if op == ">":
        if minor_wild:
            return [_Comparator(">=", Version(major + 1, 0, 0))]
        if patch_wild:
            return [_Comparator(">=", Version(major, minor + 1, 0))]
        return [_Comparator(">", base)]
    if op == "<=":
        if minor_wild:
            return [_Comparator("<", Version(major + 1, 0, 0))]
        if patch_wild:
            return [_Comparator("<", Version(major, minor + 1, 0))]
        return [_Comparator("<=", base)]
    # ">=" and "<" simply fill the missing components with zeros (base already has them).
    return [_Comparator(op, base)]


def _parse_hyphen(lower: str, upper: str) -> List[_Comparator]:
    """Parse a hyphen range ``lower - upper`` (inclusive on both ends)."""
    low = _parse_simple(">=" + lower.strip())
    # Upper bound: if partial, it's inclusive of the whole family.
    up = _XRANGE_RE.match(upper.strip())
    if not up:
        raise InvalidRange(f"unparseable hyphen upper bound: {upper!r}")
    if _is_wildcard(up.group("minor")):
        high = [_Comparator("<", Version(int(up.group("major")) + 1, 0, 0))]
    elif _is_wildcard(up.group("patch")):
        high = [
            _Comparator("<", Version(int(up.group("major")), int(up.group("minor")) + 1, 0))
        ]
    else:
        high = _parse_simple("<=" + upper.strip())
    return low + high


def _parse_comparator_set(part: str) -> List[_Comparator]:
    part = part.strip()
    if not part:
        return [_Comparator(">=", Version(0, 0, 0))]
    # Hyphen range (surrounded by spaces).
    hyphen = re.split(r"\s+-\s+", part)
    if len(hyphen) == 2:
        return _parse_hyphen(hyphen[0], hyphen[1])
    comparators: List[_Comparator] = []
    for token in part.split():
        comparators.extend(_parse_simple(token))
    return comparators


def _allows_prerelease(comparators: List[_Comparator]) -> bool:
    return any(c.version.prerelease for c in comparators)


def satisfies(version: str, range_str: str, include_prerelease: bool = False) -> bool:
    """Return whether ``version`` satisfies ``range_str``.

    Mirrors npm's default behaviour: a prerelease version only satisfies a range
    when the range itself names a prerelease at the same [major, minor, patch],
    unless ``include_prerelease`` is set.
    """
    try:
        v = parse(version)
    except InvalidVersion:
        return False
    if range_str is None:
        raise InvalidRange("range is None")
    range_str = range_str.strip()
    # npm treats these dist-tag / url / git specs as "any resolved version is fine".
    if range_str in ("", "*", "latest", "x", "X") or _is_non_semver_spec(range_str):
        return True

    for part in range_str.split("||"):
        comparators = _parse_comparator_set(part)
        if all(c.test(v) for c in comparators):
            if v.prerelease and not include_prerelease and not _allows_prerelease(comparators):
                # Allow only when a comparator targets the same tuple.
                if not any(
                    c.version.prerelease
                    and (c.version.major, c.version.minor, c.version.patch)
                    == (v.major, v.minor, v.patch)
                    for c in comparators
                ):
                    continue
            return True
    return False


def _is_non_semver_spec(spec: str) -> bool:
    """Detect npm specifiers that are not semver ranges (git, url, file, workspace)."""
    lowered = spec.lower()
    return (
        "://" in lowered
        or lowered.startswith(("file:", "link:", "workspace:", "npm:", "git+", "github:"))
        or "/" in spec
        and not any(ch in spec for ch in "<>=~^")
    )


def max_satisfying(
    versions: List[str], range_str: str, include_prerelease: bool = False
) -> Optional[str]:
    """Return the highest version in ``versions`` that satisfies ``range_str``."""
    best: Optional[Version] = None
    for raw in versions:
        try:
            v = parse(raw)
        except InvalidVersion:
            continue
        if satisfies(raw, range_str, include_prerelease=include_prerelease):
            if best is None or v > best:
                best = v
    return str(best) if best is not None else None
