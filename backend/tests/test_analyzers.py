from datetime import datetime, timedelta, timezone

from deplens.analyzers import health, licenses, maintenance, usage, versions
from deplens.analyzers.licenses import ALLOWED, COPYLEFT, PERMISSIVE, RESTRICTED, UNKNOWN
from deplens.parsers import parse_manifest_text
from deplens.services.registry import RegistryInfo

# --- versions ---------------------------------------------------------------


def _info(latest, versions_list=None):
    return RegistryInfo(
        name="pkg", available=True, latest=latest,
        all_versions=versions_list or [latest],
    )


def test_update_major():
    u = versions.analyze_update("pkg", "1.0.0", _info("2.0.0", ["1.0.0", "2.0.0"]))
    assert u.update_type == "major" and u.is_outdated


def test_update_up_to_date():
    u = versions.analyze_update("pkg", "2.0.0", _info("2.0.0"))
    assert u.update_type == "up-to-date" and not u.is_outdated


def test_update_unknown_when_offline():
    u = versions.analyze_update("pkg", "1.0.0", None)
    assert u.update_type == "unknown" and not u.available


def test_update_versions_behind():
    info = _info("1.3.0", ["1.0.0", "1.1.0", "1.2.0", "1.3.0"])
    u = versions.analyze_update("pkg", "1.0.0", info)
    assert u.versions_behind == 3


# --- licenses ---------------------------------------------------------------


def test_license_families():
    assert licenses.classify_license("MIT") == PERMISSIVE
    assert licenses.classify_license("Apache-2.0") == PERMISSIVE
    assert licenses.classify_license("GPL-3.0-only") == COPYLEFT
    assert licenses.classify_license("LGPL-3.0") == "weak-copyleft"
    assert licenses.classify_license(None) == UNKNOWN
    assert licenses.classify_license("Some-Weird-License") == "other"


def test_license_expression_most_restrictive_wins():
    # MIT OR GPL-3.0 -> copyleft dominates in our conservative classifier.
    assert licenses.classify_license("(MIT OR GPL-3.0-only)") == COPYLEFT


def test_license_policy_verdicts():
    assert licenses.evaluate_license("p", "MIT").verdict == ALLOWED
    assert licenses.evaluate_license("p", "GPL-3.0-only").verdict == RESTRICTED
    assert licenses.evaluate_license("p", None).verdict == "review"


def test_license_custom_policy():
    policy = dict(licenses.DEFAULT_POLICY)
    policy[PERMISSIVE] = RESTRICTED
    assert licenses.evaluate_license("p", "MIT", policy).verdict == RESTRICTED


# --- maintenance ------------------------------------------------------------


def _reg_with_last_publish(days_ago, deprecated=None):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ts = (now - timedelta(days=days_ago)).isoformat()
    return RegistryInfo(
        name="pkg", available=True, latest="1.0.0",
        version_times={"1.0.0": ts}, deprecated=deprecated,
    ), now


def test_maintenance_active():
    info, now = _reg_with_last_publish(30)
    assert maintenance.analyze_maintenance("pkg", info, now).status == "active"


def test_maintenance_concerns():
    info, now = _reg_with_last_publish(900)
    assert maintenance.analyze_maintenance("pkg", info, now).status == "concerns"


def test_maintenance_deprecated():
    info, now = _reg_with_last_publish(10, deprecated="use something else")
    r = maintenance.analyze_maintenance("pkg", info, now)
    assert r.status == "deprecated" and r.deprecated


def test_maintenance_unknown_offline():
    assert maintenance.analyze_maintenance("pkg", None).status == "unknown"


# --- usage ------------------------------------------------------------------


def test_usage_detects_require_and_unused(tmp_npm_project):
    manifest = parse_manifest_text((tmp_npm_project / "package.json").read_text())
    results = usage.analyze_usage(tmp_npm_project, manifest)
    assert results["lodash"].status == "confirmed"
    assert results["unused-pkg"].status == "none"
    # rimraf appears only in a script -> potential.
    assert results["rimraf"].status == "potential"


def test_usage_incomplete_when_no_sources(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies":{"x":"^1.0.0"}}')
    manifest = parse_manifest_text((tmp_path / "package.json").read_text())
    results = usage.analyze_usage(tmp_path, manifest)
    assert results["x"].status == "incomplete"


# --- health -----------------------------------------------------------------


def test_health_perfect_when_no_findings():
    h = health.compute_health(
        vuln_counts={}, outdated_counts={}, license_counts={}, unused_count=0,
        maintenance_count=0, security_checked=True, registry_available_ratio=1.0,
    )
    assert h.score == 100 and h.grade == "A" and h.confidence == "complete"


def test_health_penalises_and_caps():
    h = health.compute_health(
        vuln_counts={"critical": 10}, outdated_counts={}, license_counts={},
        unused_count=0, maintenance_count=0, security_checked=True,
        registry_available_ratio=1.0,
    )
    # Critical cap is 40, so score floors at 60 from that single category.
    assert h.score == 60
    assert any(f.category == "security" for f in h.factors)


def test_health_partial_when_offline():
    h = health.compute_health(
        vuln_counts={}, outdated_counts={}, license_counts={}, unused_count=0,
        maintenance_count=0, security_checked=False, registry_available_ratio=0.0,
    )
    assert h.confidence == "partial"
    assert h.notes


def test_health_deterministic():
    args = dict(
        vuln_counts={"high": 2}, outdated_counts={"major": 3}, license_counts={"unknown": 1},
        unused_count=2, maintenance_count=1, security_checked=True,
        registry_available_ratio=1.0,
    )
    assert health.compute_health(**args).score == health.compute_health(**args).score
