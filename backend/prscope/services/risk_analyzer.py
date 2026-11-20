"""Risk & review-attention analyzer.

Produces **deterministic, explainable** review-attention findings. Each finding
names the rule that generated it, the evidence it saw, and a suggested action.
An overall attention level is derived from a transparent additive score with
documented thresholds (see ``docs/RISK_MODEL.md``).

This is *review-attention*, not a probability that the code contains bugs.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import AttentionLevel, FileCategory

# --------------------------------------------------------------------------- #
# Tunable scoring parameters (inspectable; see docs/RISK_MODEL.md)
# --------------------------------------------------------------------------- #
LARGE_CHANGE_LINES = 400
VERY_LARGE_CHANGE_LINES = 1200
MANY_FILES = 20
VERY_MANY_FILES = 60
HIGH_FAN_IN = 5
VERY_HIGH_FAN_IN = 15

# Score thresholds -> attention level
THRESHOLDS = ((75, AttentionLevel.critical), (45, AttentionLevel.high), (20, AttentionLevel.moderate))

SCORE = {
    "security": 25,
    "api_contract": 20,
    "migration": 22,
    "dependency": 12,
    "infrastructure": 14,
    "build_ci": 8,
    "config": 10,
    "large_change": 12,
    "very_large_change": 22,
    "many_files": 10,
    "very_many_files": 18,
    "high_fan_in": 12,
    "very_high_fan_in": 20,
    "missing_tests": 15,
}


@dataclass
class RiskContext:
    changed_files: list[dict]  # {path, category, change_type, lines_added, lines_removed}
    reverse_dep_counts: dict[str, int] = field(default_factory=dict)
    source_changed: bool = False
    test_changed: bool = False
    total_lines: int = 0
    files_changed: int = 0


@dataclass
class Finding:
    title: str
    severity: AttentionLevel
    related_files: list[str]
    explanation: str
    evidence: str
    suggested_action: str
    rule: str
    score_contribution: int


def _files_in(ctx: RiskContext, category: FileCategory) -> list[str]:
    return [f["path"] for f in ctx.changed_files if f.get("category") == category.value]


def analyze_risk(ctx: RiskContext) -> dict:
    findings: list[Finding] = []

    # --- Category-driven findings ---------------------------------------- #
    security = _files_in(ctx, FileCategory.security)
    if security:
        findings.append(Finding(
            title="Security-sensitive files changed",
            severity=AttentionLevel.high,
            related_files=security,
            explanation="Changes touch authentication, authorization, secrets, or "
                        "crypto-related code, where regressions have outsized impact.",
            evidence=f"{len(security)} file(s) classified as security-related.",
            suggested_action="Add negative/permission test cases and request a security-focused review.",
            rule="security-files-changed",
            score_contribution=SCORE["security"],
        ))

    api = _files_in(ctx, FileCategory.api_contract)
    if api:
        findings.append(Finding(
            title="API contract changed",
            severity=AttentionLevel.high,
            related_files=api,
            explanation="API/schema contracts changed; consumers may break if the change "
                        "is not backward compatible.",
            evidence=f"{len(api)} API contract file(s) changed.",
            suggested_action="Verify backward compatibility and run consumer/contract tests.",
            rule="api-contract-changed",
            score_contribution=SCORE["api_contract"],
        ))

    migration = _files_in(ctx, FileCategory.migration)
    if migration:
        findings.append(Finding(
            title="Database migration present",
            severity=AttentionLevel.high,
            related_files=migration,
            explanation="Schema/migration changes are hard to roll back and can affect "
                        "data integrity.",
            evidence=f"{len(migration)} migration/schema file(s) changed.",
            suggested_action="Validate the migration, test rollback, and check data compatibility.",
            rule="db-migration",
            score_contribution=SCORE["migration"],
        ))

    deps = _files_in(ctx, FileCategory.dependency)
    if deps:
        findings.append(Finding(
            title="Dependency manifest changed",
            severity=AttentionLevel.moderate,
            related_files=deps,
            explanation="Dependency additions/upgrades can introduce vulnerabilities, "
                        "license issues, or build breakage.",
            evidence=f"{len(deps)} dependency file(s) changed.",
            suggested_action="Review new/updated dependencies for vulnerabilities and license compatibility.",
            rule="dependency-change",
            score_contribution=SCORE["dependency"],
        ))

    infra = _files_in(ctx, FileCategory.infrastructure)
    if infra:
        findings.append(Finding(
            title="Infrastructure definition changed",
            severity=AttentionLevel.moderate,
            related_files=infra,
            explanation="Container/orchestration/IaC changes affect runtime environments.",
            evidence=f"{len(infra)} infrastructure file(s) changed.",
            suggested_action="Validate in a non-production environment before rollout.",
            rule="infrastructure-change",
            score_contribution=SCORE["infrastructure"],
        ))

    config = _files_in(ctx, FileCategory.config)
    if config:
        findings.append(Finding(
            title="Configuration changed",
            severity=AttentionLevel.moderate,
            related_files=config,
            explanation="Configuration changes can alter behaviour across environments and "
                        "may carry security implications.",
            evidence=f"{len(config)} configuration file(s) changed.",
            suggested_action="Validate configuration and startup across target environments.",
            rule="config-change",
            score_contribution=SCORE["config"],
        ))

    ci = _files_in(ctx, FileCategory.build_ci)
    if ci:
        findings.append(Finding(
            title="Build / CI definition changed",
            severity=AttentionLevel.low,
            related_files=ci,
            explanation="Build or CI pipeline changes can affect how the project is built and tested.",
            evidence=f"{len(ci)} build/CI file(s) changed.",
            suggested_action="Confirm the pipeline still builds and runs the full test suite.",
            rule="build-ci-change",
            score_contribution=SCORE["build_ci"],
        ))

    # --- Size-driven findings -------------------------------------------- #
    if ctx.total_lines >= VERY_LARGE_CHANGE_LINES:
        findings.append(Finding(
            title="Very large change",
            severity=AttentionLevel.high,
            related_files=[],
            explanation="Large changes are harder to review thoroughly and more likely to hide regressions.",
            evidence=f"{ctx.total_lines} lines changed (threshold {VERY_LARGE_CHANGE_LINES}).",
            suggested_action="Consider splitting into smaller PRs; allocate extra review time.",
            rule="very-large-change",
            score_contribution=SCORE["very_large_change"],
        ))
    elif ctx.total_lines >= LARGE_CHANGE_LINES:
        findings.append(Finding(
            title="Large change",
            severity=AttentionLevel.moderate,
            related_files=[],
            explanation="Sizeable change set warrants careful review.",
            evidence=f"{ctx.total_lines} lines changed (threshold {LARGE_CHANGE_LINES}).",
            suggested_action="Allocate adequate review time and verify the main code paths.",
            rule="large-change",
            score_contribution=SCORE["large_change"],
        ))

    if ctx.files_changed >= VERY_MANY_FILES:
        findings.append(Finding(
            title="Very many files changed",
            severity=AttentionLevel.high,
            related_files=[],
            explanation="Changes spanning many files increase the surface area for regressions.",
            evidence=f"{ctx.files_changed} files changed (threshold {VERY_MANY_FILES}).",
            suggested_action="Map the change set to subsystems and verify each independently.",
            rule="very-many-files",
            score_contribution=SCORE["very_many_files"],
        ))
    elif ctx.files_changed >= MANY_FILES:
        findings.append(Finding(
            title="Many files changed",
            severity=AttentionLevel.moderate,
            related_files=[],
            explanation="A broad change set touches multiple areas.",
            evidence=f"{ctx.files_changed} files changed (threshold {MANY_FILES}).",
            suggested_action="Verify affected subsystems and watch for cross-cutting effects.",
            rule="many-files",
            score_contribution=SCORE["many_files"],
        ))

    # --- Connectivity (fan-in) ------------------------------------------- #
    for path, count in sorted(ctx.reverse_dep_counts.items(), key=lambda kv: -kv[1]):
        if count >= VERY_HIGH_FAN_IN:
            findings.append(Finding(
                title="Change to a highly-connected module",
                severity=AttentionLevel.high,
                related_files=[path],
                explanation="Many files depend on this module, so a regression here can "
                            "propagate widely.",
                evidence=f"{path} is imported by {count} file(s) (threshold {VERY_HIGH_FAN_IN}).",
                suggested_action="Run regression tests for all dependents of this module.",
                rule="very-high-fan-in",
                score_contribution=SCORE["very_high_fan_in"],
            ))
            break
        if count >= HIGH_FAN_IN:
            findings.append(Finding(
                title="Change to a connected module",
                severity=AttentionLevel.moderate,
                related_files=[path],
                explanation="Several files depend on this module.",
                evidence=f"{path} is imported by {count} file(s) (threshold {HIGH_FAN_IN}).",
                suggested_action="Verify the direct dependents of this module.",
                rule="high-fan-in",
                score_contribution=SCORE["high_fan_in"],
            ))
            break

    # --- Missing tests --------------------------------------------------- #
    if ctx.source_changed and not ctx.test_changed:
        findings.append(Finding(
            title="Source changed without test changes",
            severity=AttentionLevel.moderate,
            related_files=[],
            explanation="Application source changed but no test files were modified, so the "
                        "change may be unverified by automated tests.",
            evidence="At least one source file changed; no test files changed in this diff.",
            suggested_action="Add or update tests covering the changed behaviour, or "
                             "record manual verification.",
            rule="missing-test-changes",
            score_contribution=SCORE["missing_tests"],
        ))

    total = sum(f.score_contribution for f in findings)
    level = AttentionLevel.low
    for threshold, lvl in THRESHOLDS:
        if total >= threshold:
            level = lvl
            break

    findings.sort(key=lambda f: -f.score_contribution)
    methodology = (
        "Attention level is an additive score of independent deterministic rules "
        f"(see docs/RISK_MODEL.md). Thresholds: moderate≥20, high≥45, critical≥75. "
        f"Total score for this analysis: {total}. This reflects how much review "
        "attention the change warrants — not a probability of defects."
    )
    return {
        "attention_level": level,
        "score": total,
        "findings": [f.__dict__ | {"severity": f.severity} for f in findings],
        "methodology_note": methodology,
    }
