"""Tests for impact analysis. SPDX-License-Identifier: MIT"""
from prscope.services import impact_analyzer as ia


def _edges():
    # checkout -> payment, order -> payment, test -> payment, api -> checkout
    return [
        ("checkout.py", "payment.py", "import"),
        ("order.py", "payment.py", "import"),
        ("test_payment.py", "payment.py", "import"),
        ("api.py", "checkout.py", "import"),
    ]


def test_direct_and_indirect_impact():
    result = ia.compute_impact(["payment.py"], _edges())
    by_path = {n["path"]: n for n in result.nodes}
    assert by_path["payment.py"]["impact_type"] == "changed"
    # checkout/order/test import payment directly
    assert by_path["checkout.py"]["impact_type"] == "direct"
    assert by_path["order.py"]["impact_type"] == "direct"
    # api imports checkout which imports payment -> indirect (distance 2)
    assert by_path["api.py"]["impact_type"] == "indirect"
    assert by_path["api.py"]["distance"] == 2


def test_file_impact_reverse_and_tests():
    fi = ia.file_impact("payment.py", _edges())
    assert "checkout.py" in fi["reverse_dependencies"]
    assert "test_payment.py" in fi["related_tests"]
    assert "api.py" in fi["downstream_impact"]  # transitive reverse dep
    assert fi["path_explanations"]


def test_unrelated_file_not_impacted():
    result = ia.compute_impact(["payment.py"], _edges())
    paths = {n["path"] for n in result.nodes}
    assert "unrelated.py" not in paths
