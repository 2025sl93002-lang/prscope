"""Tests for the git diff parser against the real demo repo. SPDX-License-Identifier: MIT"""
from prscope.services import git_diff


def test_demo_diff_counts(demo_repo):
    diff = git_diff.compute_diff(demo_repo, "main", "feature/payment-refactor")
    paths = {f.path for f in diff.files}
    assert "src/payment/refund_service.py" in paths
    assert "src/payment/payment_service.py" in paths
    assert diff.range_kind in ("three-dot", "two-dot")

    summary = git_diff.summarize(diff)
    assert summary["files_changed"] == len(diff.files)
    assert summary["files_added"] >= 1  # refund_service.py is new
    assert summary["lines_added"] > 0


def test_change_types(demo_repo):
    diff = git_diff.compute_diff(demo_repo, "main", "feature/payment-refactor")
    by_path = {f.path: f for f in diff.files}
    assert by_path["src/payment/refund_service.py"].change_type == "added"
    assert by_path["src/payment/payment_service.py"].change_type == "modified"


def test_identical_refs_empty(demo_repo):
    diff = git_diff.compute_diff(demo_repo, "main", "main")
    assert diff.files == []
