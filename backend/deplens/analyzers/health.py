"""Deterministic, explainable dependency health score.

The score starts at 100 and subtracts weighted penalties for concrete findings.
Every penalty is capped per category so no single category can dominate, and
every contributing factor is returned so the UI can show exactly how the score
was reached. The score is a prioritisation aid, NOT a validated risk
probability — and it is marked "partial" whenever analysis data was incomplete
(e.g. security was not checked), rather than being inflated.

Formula and weights are documented in docs/scoring-model.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# (per-item penalty, category cap)
VULN_WEIGHTS = {
    "critical": (20.0, 40.0),
    "high": (10.0, 40.0),
    "moderate": (4.0, 24.0),
    "low": (1.0, 10.0),
}
OUTDATED_WEIGHTS = {
    "major": (2.0, 20.0),
    "minor": (1.0, 10.0),
    "patch": (0.5, 8.0),
}
LICENSE_WEIGHTS = {
    "restricted": (6.0, 24.0),
    "review": (1.0, 8.0),
    "unknown": (2.0, 12.0),
}
UNUSED_WEIGHT = (1.0, 8.0)
MAINTENANCE_WEIGHT = (3.0, 15.0)


@dataclass
class HealthFactor:
    category: str
    label: str
    impact: float  # negative points
    detail: str


@dataclass
class HealthScore:
    score: int
    grade: str
    confidence: str  # "complete" | "partial"
    factors: List[HealthFactor] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _apply(count: int, weight) -> float:
    per, cap = weight
    return min(count * per, cap)


def compute_health(
    *,
    vuln_counts: Dict[str, int],
    outdated_counts: Dict[str, int],
    license_counts: Dict[str, int],
    unused_count: int,
    maintenance_count: int,
    security_checked: bool,
    registry_available_ratio: float,
) -> HealthScore:
    factors: List[HealthFactor] = []
    notes: List[str] = []
    total_penalty = 0.0

    for sev, weight in VULN_WEIGHTS.items():
        c = vuln_counts.get(sev, 0)
        if c:
            impact = _apply(c, weight)
            total_penalty += impact
            factors.append(
                HealthFactor(
                    "security", f"{c} {sev} vulnerability finding(s)", -impact,
                    f"Known {sev}-severity advisories affect installed packages.",
                )
            )
    for kind, weight in OUTDATED_WEIGHTS.items():
        c = outdated_counts.get(kind, 0)
        if c:
            impact = _apply(c, weight)
            total_penalty += impact
            factors.append(
                HealthFactor(
                    "updates", f"{c} package(s) a {kind} version behind", -impact,
                    f"{c} dependency(ies) have a newer {kind} release available.",
                )
            )
    for kind, weight in LICENSE_WEIGHTS.items():
        c = license_counts.get(kind, 0)
        if c:
            impact = _apply(c, weight)
            total_penalty += impact
            label = {
                "restricted": "restricted-license package(s)",
                "review": "package(s) needing license review",
                "unknown": "package(s) with unknown license",
            }[kind]
            factors.append(
                HealthFactor("licenses", f"{c} {label}", -impact, "Per the active license policy.")
            )
    if unused_count:
        impact = _apply(unused_count, UNUSED_WEIGHT)
        total_penalty += impact
        factors.append(
            HealthFactor(
                "usage", f"{unused_count} potentially unused package(s)", -impact,
                "No usage evidence was found (verify before removing).",
            )
        )
    if maintenance_count:
        impact = _apply(maintenance_count, MAINTENANCE_WEIGHT)
        total_penalty += impact
        factors.append(
            HealthFactor(
                "maintenance", f"{maintenance_count} package(s) with maintenance concerns", -impact,
                "Deprecated, or no release in a long time.",
            )
        )

    score = max(0, min(100, round(100 - total_penalty)))

    confidence = "complete"
    if not security_checked:
        confidence = "partial"
        notes.append(
            "Security advisories were not checked (offline). The score does not reflect "
            "vulnerabilities and should be treated as a best case."
        )
    if registry_available_ratio < 0.95:
        confidence = "partial"
        notes.append(
            f"Registry metadata was available for only {registry_available_ratio:.0%} of packages; "
            "update, license and maintenance findings may be incomplete."
        )
    if not factors:
        notes.append("No penalising findings were detected from the available data.")

    return HealthScore(
        score=score, grade=_grade(score), confidence=confidence, factors=factors, notes=notes
    )
