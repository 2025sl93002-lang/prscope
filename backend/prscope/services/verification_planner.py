"""Verification planner.

Generates verification **tasks** deterministically from the change set. Each task
records why it was generated, which files triggered it, suggested steps, and the
evidence it expects. Task keys are stable so re-running analysis on the same diff
yields the same plan. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import FileCategory, Priority


@dataclass
class PlannedTask:
    task_key: str
    title: str
    description: str
    reason: str
    related_files: list[str]
    verification_type: str
    priority: Priority
    steps: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)


# Each rule: category -> task template(s). Functions receive the matching files.
def _source_tasks(files: list[str]) -> list[PlannedTask]:
    return [
        PlannedTask(
            "source:unit-tests", "Unit-test changed source logic",
            "Add or run unit tests covering the modified functions/classes.",
            "Application source code changed.", files, "unit_test", Priority.high,
            ["Identify the changed functions/classes.",
             "Run existing unit tests for the affected modules.",
             "Add unit tests for new or modified behaviour."],
            ["Unit test run output", "List of tests covering the change"],
        ),
        PlannedTask(
            "source:regression", "Run regression tests for affected modules",
            "Execute regression/integration tests for modules that depend on the changed code.",
            "Application source code changed; dependents may be affected.", files,
            "regression_test", Priority.medium,
            ["Determine downstream dependents from the Impact Explorer.",
             "Run regression/integration suites for those modules."],
            ["Regression test run output"],
        ),
    ]


def _test_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "test:confirm-pass", "Confirm modified tests pass and assert meaningfully",
        "Review changed tests and confirm they pass and still assert the intended behaviour.",
        "Test code changed.", files, "test_review", Priority.medium,
        ["Run the modified test files.",
         "Confirm assertions were not weakened or skipped."],
        ["Test run output"],
    )]


def _api_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "api:compatibility", "Validate API contract and consumer compatibility",
        "Validate the API contract change and confirm consumers remain compatible.",
        "API contract changed.", files, "contract_test", Priority.high,
        ["Diff the API contract for breaking changes.",
         "Run contract/consumer tests.",
         "Validate request/response payloads against the schema."],
        ["Contract test output", "Compatibility assessment note"],
    )]


def _migration_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "migration:validate", "Validate database migration and rollback",
        "Validate the migration applies cleanly, rolls back, and preserves data compatibility.",
        "Database migration changed.", files, "migration_validation", Priority.high,
        ["Apply the migration to a disposable database.",
         "Verify rollback restores the prior schema.",
         "Check data compatibility for existing rows.",
         "Validate the resulting schema."],
        ["Migration apply log", "Rollback log", "Schema validation result"],
    )]


def _config_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "config:validate", "Validate configuration changes",
        "Validate configuration changes across target environments and review security implications.",
        "Configuration changed.", files, "config_validation", Priority.medium,
        ["Validate configuration syntax/schema.",
         "Test application startup with the new configuration.",
         "Review for environment-specific and security implications."],
        ["Startup validation output", "Config review note"],
    )]


def _security_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "security:permission-tests", "Verify authentication/authorization behaviour",
        "Test permission and authentication behaviour, including negative cases, for the changed code.",
        "Security-sensitive code changed.", files, "security_test", Priority.high,
        ["Test authenticated and unauthenticated access paths.",
         "Add negative test cases (denied/invalid credentials).",
         "Run security regression checks."],
        ["Security test output", "Negative-case test results"],
    )]


def _ui_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "ui:behaviour-a11y", "Verify UI behaviour, accessibility, and responsiveness",
        "Verify UI behaviour, accessibility, and responsive layout for the changed components.",
        "UI components changed.", files, "ui_test", Priority.medium,
        ["Manually verify the changed UI behaviour.",
         "Check keyboard navigation and contrast (accessibility).",
         "Verify responsive layout at small and large viewports.",
         "Run UI regression tests if available."],
        ["Screenshot reference", "Accessibility check note"],
    )]


def _dependency_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "dependency:review", "Review dependency changes (build, vulnerabilities, license)",
        "Review dependency additions/upgrades for build compatibility, vulnerabilities, and license.",
        "Dependency manifest changed.", files, "dependency_review", Priority.high,
        ["Confirm the project builds with the updated dependencies.",
         "Check new/updated dependencies for known vulnerabilities.",
         "Verify license compatibility."],
        ["Build output", "Vulnerability scan note", "License check note"],
    )]


def _infra_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "infra:validate", "Validate infrastructure changes",
        "Validate container/IaC changes in a non-production environment.",
        "Infrastructure definition changed.", files, "infra_validation", Priority.medium,
        ["Build/apply the infrastructure change in a disposable environment.",
         "Confirm services start and are reachable."],
        ["Deployment/apply log"],
    )]


def _ci_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "ci:pipeline", "Confirm build/CI pipeline still works",
        "Confirm the build/CI pipeline builds the project and runs the full test suite.",
        "Build/CI definition changed.", files, "build_verification", Priority.medium,
        ["Trigger or simulate the pipeline.",
         "Confirm build and tests run as expected."],
        ["Pipeline run reference"],
    )]


def _doc_tasks(files: list[str]) -> list[PlannedTask]:
    return [PlannedTask(
        "doc:review", "Review documentation accuracy and links",
        "Review documentation changes for accuracy and verify links resolve.",
        "Documentation changed.", files, "doc_review", Priority.low,
        ["Proofread the documentation change for accuracy.",
         "Verify any links resolve."],
        ["Documentation review note"],
    )]


_CATEGORY_RULES = {
    FileCategory.source: _source_tasks,
    FileCategory.test: _test_tasks,
    FileCategory.api_contract: _api_tasks,
    FileCategory.migration: _migration_tasks,
    FileCategory.config: _config_tasks,
    FileCategory.security: _security_tasks,
    FileCategory.ui: _ui_tasks,
    FileCategory.dependency: _dependency_tasks,
    FileCategory.infrastructure: _infra_tasks,
    FileCategory.build_ci: _ci_tasks,
    FileCategory.documentation: _doc_tasks,
}


def plan_verification(changed_files: list[dict]) -> list[PlannedTask]:
    """Generate the verification plan from classified changed files."""
    by_category: dict[FileCategory, list[str]] = {}
    for f in changed_files:
        try:
            cat = FileCategory(f.get("category", "unknown"))
        except ValueError:
            cat = FileCategory.unknown
        by_category.setdefault(cat, []).append(f["path"])

    tasks: list[PlannedTask] = []
    for category, files in by_category.items():
        rule = _CATEGORY_RULES.get(category)
        if rule:
            tasks.extend(rule(sorted(files)))

    # Stable ordering by priority then key.
    priority_rank = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
    tasks.sort(key=lambda t: (priority_rank[t.priority], t.task_key))
    return tasks
