"""Test-gap detector.

Flags *potential* test gaps using deterministic signals. Wording is deliberately
cautious ("potential gap", "no related test **detected**") — the detector reasons
over static signals and naming conventions, not actual coverage data, so it never
claims "no tests exist". SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from pathlib import PurePosixPath

from ..models import AttentionLevel, FileCategory
from .impact_analyzer import _looks_like_test, build_adjacency

_SOURCE_LIKE = {FileCategory.source.value, FileCategory.ui.value, FileCategory.api_contract.value}


def _stem(path: str) -> str:
    name = PurePosixPath(path).name
    for suffix in (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _name_matches_test(source_path: str, test_path: str) -> bool:
    """Heuristic: does test_path look like a test for source_path (by stem)?"""
    s = _stem(source_path).lower()
    t = _stem(test_path).lower()
    if not s:
        return False
    return (
        t == f"test_{s}"
        or t == f"{s}_test"
        or t == f"{s}.test"
        or t == f"{s}.spec"
        or t == f"test{s}"
        or t == s  # mirrored test/ tree with same basename
    )


def detect_test_gaps(
    changed_files: list[dict],
    edges: list[tuple[str, str, str]],
    all_files: set[str],
) -> list[dict]:
    _forward, reverse = build_adjacency(edges)
    all_tests = {f for f in all_files if _looks_like_test(f)}
    changed_paths = {f["path"] for f in changed_files}
    changed_tests = {p for p in changed_paths if _looks_like_test(p)}

    gaps: list[dict] = []

    for f in changed_files:
        path = f["path"]
        category = f.get("category", "unknown")
        if f.get("change_type") == "deleted":
            continue
        if category not in _SOURCE_LIKE:
            continue
        if _looks_like_test(path):
            continue

        # Related tests: reverse-dependency tests + name-matched tests in the repo.
        rev_tests = sorted(d for d in reverse.get(path, set()) if _looks_like_test(d))
        name_tests = sorted(t for t in all_tests if _name_matches_test(path, t))
        related = sorted(set(rev_tests) | set(name_tests))

        significant = (f.get("lines_added", 0) + f.get("lines_removed", 0)) >= 15

        if not related:
            gaps.append({
                "changed_file": path,
                "related_tests": [],
                "detection_method": "No test imports this file and no name-matched test file found.",
                "missing_coverage": "No related test detected for this changed source file.",
                "recommended_tests": [f"Add a test covering {PurePosixPath(path).name}."],
                "severity": (AttentionLevel.high if significant else AttentionLevel.moderate),
            })
        elif not (set(related) & changed_tests) and significant:
            gaps.append({
                "changed_file": path,
                "related_tests": related,
                "detection_method": "Related test(s) detected by import/name match but "
                                    "none changed in this diff.",
                "missing_coverage": "Significant logic change with no corresponding update to related tests.",
                "recommended_tests": [f"Review/update: {t}" for t in related[:5]],
                "severity": AttentionLevel.moderate,
            })

        # Specialized category checks.
        if category == FileCategory.api_contract.value and not any(
            "contract" in t.lower() for t in related
        ):
            gaps.append({
                "changed_file": path,
                "related_tests": related,
                "detection_method": "API contract changed without a detected contract test.",
                "missing_coverage": "Potential gap: no contract/consumer test detected for this API change.",
                "recommended_tests": ["Add a contract or consumer-compatibility test."],
                "severity": AttentionLevel.moderate,
            })

    # Test-only changes: tests changed but no source changed at all.
    source_changed = any(
        (f.get("category") in _SOURCE_LIKE and not _looks_like_test(f["path"]))
        for f in changed_files
    )
    if changed_tests and not source_changed:
        gaps.append({
            "changed_file": sorted(changed_tests)[0],
            "related_tests": sorted(changed_tests),
            "detection_method": "Test files changed without corresponding source changes.",
            "missing_coverage": "Tests changed alone — confirm they reflect intended behaviour "
                                "and are not merely adjusting to a defect.",
            "recommended_tests": ["Confirm the test change is intentional and still meaningful."],
            "severity": AttentionLevel.low,
        })

    return gaps
