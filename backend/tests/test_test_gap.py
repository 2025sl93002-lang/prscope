"""Tests for test-gap detection. SPDX-License-Identifier: MIT"""
from prscope.services import test_gap


def test_new_source_without_test_flagged():
    changed = [{"path": "src/refund.py", "category": "source", "change_type": "added",
                "lines_added": 20, "lines_removed": 0}]
    gaps = test_gap.detect_test_gaps(changed, edges=[], all_files={"src/refund.py"})
    assert any(g["changed_file"] == "src/refund.py" for g in gaps)
    assert any("No related test detected" in g["missing_coverage"] for g in gaps)


def test_source_with_related_test_by_name_not_flagged_as_missing():
    changed = [{"path": "src/payment.py", "category": "source", "change_type": "modified",
                "lines_added": 3, "lines_removed": 1}]
    all_files = {"src/payment.py", "tests/test_payment.py"}
    gaps = test_gap.detect_test_gaps(changed, edges=[], all_files=all_files)
    # Related test exists and change is small -> no "no related test" gap.
    assert not any("No related test detected" in g["missing_coverage"] for g in gaps)


def test_significant_change_without_updated_test():
    changed = [{"path": "src/payment.py", "category": "source", "change_type": "modified",
                "lines_added": 40, "lines_removed": 10}]
    all_files = {"src/payment.py", "tests/test_payment.py"}
    gaps = test_gap.detect_test_gaps(changed, edges=[], all_files=all_files)
    assert any(
        "not updated" in g["missing_coverage"]
        or "no corresponding update" in g["missing_coverage"].lower()
        for g in gaps
    )


def test_wording_is_cautious():
    changed = [{"path": "src/x.py", "category": "source", "change_type": "added",
                "lines_added": 5, "lines_removed": 0}]
    gaps = test_gap.detect_test_gaps(changed, edges=[], all_files={"src/x.py"})
    for g in gaps:
        # Never claims definitively that no tests exist.
        assert "No tests exist" not in g["missing_coverage"]
