"""License analysis and policy evaluation.

Classifies SPDX license identifiers into coarse families and evaluates them
against a configurable policy. This is an engineering aid, NOT legal advice:
classifications are heuristic and the UI says so. Unknown or unparseable
licenses are reported as "unknown", never guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

# Coarse license families.
PERMISSIVE = "permissive"
WEAK_COPYLEFT = "weak-copyleft"
COPYLEFT = "copyleft"
PROPRIETARY = "proprietary"
UNKNOWN = "unknown"
OTHER = "other"

# Policy verdicts.
ALLOWED = "allowed"
REVIEW = "review"
RESTRICTED = "restricted"

# SPDX id (uppercased) -> family. Covers the licenses that dominate npm.
_FAMILY: Dict[str, str] = {
    "MIT": PERMISSIVE,
    "MIT-0": PERMISSIVE,
    "ISC": PERMISSIVE,
    "BSD-2-CLAUSE": PERMISSIVE,
    "BSD-3-CLAUSE": PERMISSIVE,
    "0BSD": PERMISSIVE,
    "APACHE-2.0": PERMISSIVE,
    "UNLICENSE": PERMISSIVE,
    "CC0-1.0": PERMISSIVE,
    "ZLIB": PERMISSIVE,
    "WTFPL": PERMISSIVE,
    "BLUEOAK-1.0.0": PERMISSIVE,
    "PYTHON-2.0": PERMISSIVE,
    "MPL-2.0": WEAK_COPYLEFT,
    "LGPL-2.1": WEAK_COPYLEFT,
    "LGPL-2.1-ONLY": WEAK_COPYLEFT,
    "LGPL-2.1-OR-LATER": WEAK_COPYLEFT,
    "LGPL-3.0": WEAK_COPYLEFT,
    "LGPL-3.0-ONLY": WEAK_COPYLEFT,
    "LGPL-3.0-OR-LATER": WEAK_COPYLEFT,
    "EPL-2.0": WEAK_COPYLEFT,
    "CDDL-1.0": WEAK_COPYLEFT,
    "GPL-2.0": COPYLEFT,
    "GPL-2.0-ONLY": COPYLEFT,
    "GPL-2.0-OR-LATER": COPYLEFT,
    "GPL-3.0": COPYLEFT,
    "GPL-3.0-ONLY": COPYLEFT,
    "GPL-3.0-OR-LATER": COPYLEFT,
    "AGPL-3.0": COPYLEFT,
    "AGPL-3.0-ONLY": COPYLEFT,
    "AGPL-3.0-OR-LATER": COPYLEFT,
    "UNLICENSED": PROPRIETARY,
}

# Default policy: family -> verdict. Documented in docs/license-policy.md.
DEFAULT_POLICY: Dict[str, str] = {
    PERMISSIVE: ALLOWED,
    WEAK_COPYLEFT: REVIEW,
    COPYLEFT: RESTRICTED,
    PROPRIETARY: RESTRICTED,
    OTHER: REVIEW,
    UNKNOWN: REVIEW,
}


@dataclass
class LicenseResult:
    package: str
    license: Optional[str]  # raw SPDX string as reported
    family: str
    verdict: str
    note: str


def _split_expression(expr: str) -> List[str]:
    """Split a simple SPDX expression (AND/OR/WITH, parens) into identifiers."""
    cleaned = re.sub(r"[()]", " ", expr)
    tokens = re.split(r"\b(?:AND|OR|WITH)\b", cleaned, flags=re.IGNORECASE)
    return [t.strip() for t in tokens if t.strip()]


def classify_license(raw: Optional[str]) -> str:
    if not raw or not isinstance(raw, str):
        return UNKNOWN
    text = raw.strip()
    if not text or text.upper() in ("UNKNOWN", "SEE LICENSE IN LICENSE", "NOLICENSE"):
        return UNKNOWN
    ids = _split_expression(text)
    families = set()
    for ident in ids:
        fam = _FAMILY.get(ident.upper().rstrip("+"))
        families.add(fam if fam else OTHER)
    # Most restrictive family wins for a conjunction/disjunction.
    for fam in (PROPRIETARY, COPYLEFT, WEAK_COPYLEFT, OTHER, PERMISSIVE):
        if fam in families:
            return fam
    return UNKNOWN


def evaluate_license(
    package: str, raw: Optional[str], policy: Optional[Dict[str, str]] = None
) -> LicenseResult:
    policy = policy or DEFAULT_POLICY
    family = classify_license(raw)
    verdict = policy.get(family, REVIEW)
    notes = {
        PERMISSIVE: "Permissive license — generally safe for most projects.",
        WEAK_COPYLEFT: "Weak copyleft — review obligations for modified files / linking.",
        COPYLEFT: "Strong copyleft — may impose source-disclosure obligations.",
        PROPRIETARY: "Marked proprietary / unlicensed — review carefully.",
        OTHER: "License not in DepLens's known set — manual review recommended.",
        UNKNOWN: "No license metadata found — treat as requiring review.",
    }
    return LicenseResult(
        package=package,
        license=raw,
        family=family,
        verdict=verdict,
        note=notes.get(family, "Review recommended."),
    )
