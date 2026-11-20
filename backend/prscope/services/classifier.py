"""Change classification engine.

Classifies changed files into categories using **ordered, deterministic rules**.
The first matching rule wins; every classification records the rule name and a
human-readable reason so users can see exactly why a file landed in a category.

Rules are data (:data:`DEFAULT_RULES`) and can be extended by passing extra
rules to :func:`classify_path`. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass

from ..models import FileCategory


@dataclass(frozen=True)
class ClassificationRule:
    name: str
    category: FileCategory
    reason: str
    confidence: float
    # Any matcher that returns True classifies the file.
    globs: tuple[str, ...] = ()
    basename_globs: tuple[str, ...] = ()
    regex: str | None = None

    def matches(self, path: str) -> bool:
        p = path.replace("\\", "/")
        base = p.rsplit("/", 1)[-1]
        for g in self.globs:
            if fnmatch.fnmatch(p, g):
                return True
        for g in self.basename_globs:
            if fnmatch.fnmatch(base, g):
                return True
        if self.regex and re.search(self.regex, p):
            return True
        return False


@dataclass
class Classification:
    path: str
    category: FileCategory
    reason: str
    confidence: float
    matched_rule: str


# Order matters: more specific / higher-signal rules come first.
DEFAULT_RULES: tuple[ClassificationRule, ...] = (
    ClassificationRule(
        name="dependency-manifest",
        category=FileCategory.dependency,
        reason="Dependency manifest or lockfile",
        confidence=0.97,
        basename_globs=(
            "requirements*.txt", "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock",
            "setup.py", "setup.cfg", "package.json", "package-lock.json", "yarn.lock",
            "pnpm-lock.yaml", "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "Gemfile",
            "Gemfile.lock", "pom.xml", "build.gradle", "build.gradle.kts",
        ),
    ),
    ClassificationRule(
        name="ci-workflow",
        category=FileCategory.build_ci,
        reason="CI / build pipeline definition",
        confidence=0.95,
        globs=(
            ".github/workflows/*", ".gitlab-ci.yml", ".circleci/*", "azure-pipelines.yml",
            "Jenkinsfile", "*/Jenkinsfile", ".travis.yml", "Makefile", "*/Makefile",
            "*.mk", "Taskfile.yml",
        ),
    ),
    ClassificationRule(
        name="infrastructure",
        category=FileCategory.infrastructure,
        reason="Infrastructure / container / orchestration definition",
        confidence=0.9,
        globs=(
            "Dockerfile", "*/Dockerfile", "*.dockerfile", "docker-compose*.yml",
            "docker-compose*.yaml", "*.tf", "*.tfvars", "k8s/*", "kubernetes/*",
            "helm/*", "*.helm", "charts/*", "ansible/*", "*.nomad",
        ),
    ),
    ClassificationRule(
        name="db-migration",
        category=FileCategory.migration,
        reason="Database migration / schema change",
        confidence=0.9,
        regex=r"(^|/)(migrations?|migrate|alembic|flyway|liquibase)(/|_)|\.sql$",
    ),
    ClassificationRule(
        name="api-contract",
        category=FileCategory.api_contract,
        reason="API contract / schema definition (OpenAPI, GraphQL, protobuf…)",
        confidence=0.88,
        globs=(
            "*.proto", "*.graphql", "*.gql", "openapi*.yaml", "openapi*.yml", "openapi*.json",
            "swagger*.yaml", "swagger*.yml", "swagger*.json", "*.openapi.json", "*/api/*.yaml",
        ),
        regex=r"(^|/)(openapi|swagger|api[-_]?spec)\b",
    ),
    ClassificationRule(
        name="security-sensitive",
        category=FileCategory.security,
        reason="Security / authentication / authorization related file",
        confidence=0.82,
        regex=(
            r"(^|/)(auth|authn|authz|login|session|password|crypto|secret|token|jwt|oauth|"
            r"permission|rbac|acl|security|credential)s?([._/]|$)"
        ),
    ),
    ClassificationRule(
        name="test-code",
        category=FileCategory.test,
        reason="Automated test file",
        confidence=0.95,
        globs=(
            "test/*", "tests/*", "*/test/*", "*/tests/*", "__tests__/*", "*/__tests__/*",
            "spec/*", "*/spec/*",
        ),
        basename_globs=(
            "test_*.py", "*_test.py", "*_test.go", "*.test.ts", "*.test.tsx", "*.test.js",
            "*.test.jsx", "*.spec.ts", "*.spec.tsx", "*.spec.js", "*.spec.jsx", "*Test.java",
            "*Tests.java", "*_spec.rb",
        ),
    ),
    ClassificationRule(
        name="documentation",
        category=FileCategory.documentation,
        reason="Documentation file",
        confidence=0.92,
        basename_globs=("*.md", "*.mdx", "*.rst", "*.txt", "LICENSE", "NOTICE", "CHANGELOG*"),
        globs=("docs/*", "*/docs/*", "*.adoc"),
    ),
    ClassificationRule(
        name="ui-component",
        category=FileCategory.ui,
        reason="UI component, stylesheet, or markup",
        confidence=0.8,
        basename_globs=(
            "*.tsx", "*.jsx", "*.vue", "*.svelte", "*.css", "*.scss", "*.sass", "*.less",
            "*.html", "*.htm",
        ),
    ),
    ClassificationRule(
        name="config",
        category=FileCategory.config,
        reason="Configuration file",
        confidence=0.78,
        basename_globs=(
            "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg", "*.conf", "*.properties",
            "*.env", ".env*", "*.json",
        ),
    ),
    ClassificationRule(
        name="source-code",
        category=FileCategory.source,
        reason="Application source code",
        confidence=0.85,
        basename_globs=(
            "*.py", "*.ts", "*.js", "*.mjs", "*.cjs", "*.go", "*.java", "*.rb", "*.rs",
            "*.c", "*.h", "*.cpp", "*.hpp", "*.cs", "*.kt", "*.php", "*.scala", "*.swift",
        ),
    ),
)


def classify_path(
    path: str, extra_rules: tuple[ClassificationRule, ...] = ()
) -> Classification:
    """Classify a single path. Extra rules are evaluated first (highest priority)."""
    for rule in (*extra_rules, *DEFAULT_RULES):
        if rule.matches(path):
            return Classification(
                path=path,
                category=rule.category,
                reason=rule.reason,
                confidence=rule.confidence,
                matched_rule=rule.name,
            )
    return Classification(
        path=path,
        category=FileCategory.unknown,
        reason="No classification rule matched this file type/location",
        confidence=0.0,
        matched_rule="none",
    )


def classify_many(
    paths: list[str], extra_rules: tuple[ClassificationRule, ...] = ()
) -> list[Classification]:
    return [classify_path(p, extra_rules) for p in paths]
