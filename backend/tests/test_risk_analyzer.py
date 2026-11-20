"""Tests for the deterministic risk analyzer. SPDX-License-Identifier: MIT"""
from prscope.models import AttentionLevel
from prscope.services import risk_analyzer as ra


def _ctx(**kw):
    base = dict(changed_files=[], reverse_dep_counts={}, source_changed=False,
               test_changed=False, total_lines=0, files_changed=0)
    base.update(kw)
    return ra.RiskContext(**base)


def test_empty_change_is_low():
    report = ra.analyze_risk(_ctx())
    assert report["attention_level"] == AttentionLevel.low
    assert report["score"] == 0
    assert report["findings"] == []


def test_security_change_raises_attention():
    ctx = _ctx(changed_files=[{"path": "auth.py", "category": "security", "change_type": "modified",
                               "lines_added": 5, "lines_removed": 1}])
    report = ra.analyze_risk(ctx)
    rules = {f["rule"] for f in report["findings"]}
    assert "security-files-changed" in rules
    assert report["score"] >= ra.SCORE["security"]


def test_missing_tests_rule():
    ctx = _ctx(source_changed=True, test_changed=False,
               changed_files=[{"path": "a.py", "category": "source", "change_type": "modified",
                               "lines_added": 10, "lines_removed": 0}])
    report = ra.analyze_risk(ctx)
    assert any(f["rule"] == "missing-test-changes" for f in report["findings"])


def test_no_missing_tests_when_tests_changed():
    ctx = _ctx(source_changed=True, test_changed=True)
    report = ra.analyze_risk(ctx)
    assert not any(f["rule"] == "missing-test-changes" for f in report["findings"])


def test_thresholds_escalate():
    # Large change + many files + api + migration -> high/critical.
    files = [{"path": f"f{i}.py", "category": "source", "change_type": "modified",
              "lines_added": 20, "lines_removed": 20} for i in range(70)]
    files.append({"path": "api.yaml", "category": "api_contract", "change_type": "modified",
                  "lines_added": 5, "lines_removed": 0})
    files.append({"path": "m.sql", "category": "migration", "change_type": "added",
                  "lines_added": 5, "lines_removed": 0})
    ctx = _ctx(changed_files=files, total_lines=3000, files_changed=72, source_changed=True)
    report = ra.analyze_risk(ctx)
    assert report["attention_level"] in (AttentionLevel.high, AttentionLevel.critical)


def test_every_finding_is_explainable():
    ctx = _ctx(changed_files=[{"path": "api.yaml", "category": "api_contract",
                               "change_type": "modified", "lines_added": 1, "lines_removed": 0}])
    report = ra.analyze_risk(ctx)
    for f in report["findings"]:
        assert f["explanation"] and f["evidence"] and f["suggested_action"] and f["rule"]
