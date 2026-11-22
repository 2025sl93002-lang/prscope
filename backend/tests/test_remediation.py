import time

from deplens.analyzers.remediation import plan_remediation
from deplens.parsers.lockfile import ROOT_ID


def _seed(db):
    """root -> app-dep (direct, vulnerable) ; root -> express -> qs (transitive, vulnerable)."""
    pid = db.upsert_project("app", "/tmp/app")
    cur = db.execute(
        "INSERT INTO scans(project_id, created_at, status, online, summary_json) "
        "VALUES (?,?,?,?,?)",
        (pid, time.time(), "completed", 1, "{}"),
    )
    sid = cur.lastrowid

    def pkg(node_id, name, version, direct):
        db.execute(
            "INSERT INTO packages(scan_id, node_id, name, version, is_direct, scope) "
            "VALUES (?,?,?,?,?,?)",
            (sid, node_id, name, version, int(direct), "prod"),
        )

    pkg("lodash@4.17.11", "lodash", "4.17.11", True)
    pkg("express@4.17.1", "express", "4.17.1", True)
    pkg("qs@6.7.0", "qs", "6.7.0", False)
    for s, t in [(ROOT_ID, "lodash@4.17.11"), (ROOT_ID, "express@4.17.1"),
                 ("express@4.17.1", "qs@6.7.0")]:
        db.execute(
            "INSERT INTO edges(scan_id, source, target, edge_type, spec) VALUES (?,?,?,?,?)",
            (sid, s, t, "prod", "*"),
        )

    def vuln(pkg_name, ver, oid, cve, sev, fixed):
        db.execute(
            "INSERT INTO vulnerabilities(scan_id, package, installed_version, osv_id, cve, "
            "severity, summary, fixed_version, url) VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, pkg_name, ver, oid, cve, sev, "x", fixed, "http://x"),
        )

    # lodash: two advisories, highest fix 4.17.21 (minor from 4.17.11 -> patch actually)
    vuln("lodash", "4.17.11", "GHSA-a", "CVE-1", "critical", "4.17.12")
    vuln("lodash", "4.17.11", "GHSA-b", "CVE-2", "high", "4.17.21")
    # qs transitive: fix 6.11.0, and one with no fix
    vuln("qs", "6.7.0", "GHSA-c", "CVE-3", "high", "6.11.0")
    vuln("qs", "6.7.0", "GHSA-d", None, "moderate", None)
    return sid


def test_plan_clears_fixable_and_counts_unfixable(db):
    sid = _seed(db)
    plan = plan_remediation(db, sid)
    assert plan.total_advisories == 4
    assert plan.fixable_advisories == 3   # both lodash + one qs
    assert plan.unfixable_advisories == 1  # the qs advisory with no fix
    assert plan.packages_to_upgrade == 2


def test_lodash_target_is_highest_fix(db):
    sid = _seed(db)
    plan = plan_remediation(db, sid)
    lodash = next(a for a in plan.actions if a.package == "lodash")
    assert lodash.target_version == "4.17.21"  # max of 4.17.12 and 4.17.21
    assert lodash.strategy == "direct"
    assert len(lodash.cleared) == 2
    assert lodash.max_severity_cleared == "critical"


def test_transitive_action_attributes_to_direct_parent(db):
    sid = _seed(db)
    plan = plan_remediation(db, sid)
    qs = next(a for a in plan.actions if a.package == "qs")
    assert qs.strategy == "transitive"
    assert qs.via_direct == ["express"]
    assert len(qs.cleared) == 1
    assert len(qs.unfixable) == 1


def test_actions_ranked_by_severity(db):
    sid = _seed(db)
    plan = plan_remediation(db, sid)
    # lodash (critical) must rank ahead of qs (high).
    assert plan.actions[0].package == "lodash"


def test_empty_plan_when_no_vulns(db):
    pid = db.upsert_project("app", "/tmp/app2")
    cur = db.execute(
        "INSERT INTO scans(project_id, created_at, status, online, summary_json) "
        "VALUES (?,?,?,?,?)",
        (pid, time.time(), "completed", 1, "{}"),
    )
    plan = plan_remediation(db, cur.lastrowid)
    assert plan.total_advisories == 0
    assert "nothing to remediate" in plan.summary.lower()
