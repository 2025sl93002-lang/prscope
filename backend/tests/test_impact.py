import json
import time

from deplens.analyzers.impact import simulate
from deplens.parsers.lockfile import ROOT_ID


def _seed(db):
    """Seed a deterministic scan graph:

        root -> A (direct, used in src/a.js)
        root -> B (direct)
        A -> C (spec ^1.0.0)      A -> D (only via A)
        B -> C (spec ~1.0.0)
        C@1.0.0 has an advisory fixed in 1.0.3
    """
    pid = db.upsert_project("app", "/tmp/app")
    cur = db.execute(
        "INSERT INTO scans(project_id, created_at, status, online, lockfile_format, "
        "summary_json) VALUES (?,?,?,?,?,?)",
        (pid, time.time(), "completed", 1, "v3", "{}"),
    )
    sid = cur.lastrowid

    def pkg(node_id, name, version, direct, usage=None):
        data = {"usage": usage} if usage else {}
        data["license"] = {"license": "MIT"}
        db.execute(
            "INSERT INTO packages(scan_id, node_id, name, version, is_direct, scope, depth, "
            "dependents, path_count, vuln_count, data_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (sid, node_id, name, version, int(direct), "prod", 1, 0, 1, 0, json.dumps(data)),
        )

    pkg("A@1.0.0", "A", "1.0.0", True,
        usage={"status": "confirmed", "confidence": "high", "explanation": "",
               "evidence": [{"file": "src/a.js", "line": 1, "method": "require", "snippet": ""}]})
    pkg("B@1.0.0", "B", "1.0.0", True)
    pkg("C@1.0.0", "C", "1.0.0", False)
    pkg("D@1.0.0", "D", "1.0.0", False)

    edges = [
        (ROOT_ID, "A@1.0.0", "prod", "^1.0.0"),
        (ROOT_ID, "B@1.0.0", "prod", "^1.0.0"),
        ("A@1.0.0", "C@1.0.0", "prod", "^1.0.0"),
        ("B@1.0.0", "C@1.0.0", "prod", "~1.0.0"),
        ("A@1.0.0", "D@1.0.0", "prod", "^1.0.0"),
    ]
    db.executemany(
        "INSERT INTO edges(scan_id, source, target, edge_type, spec) VALUES (?,?,?,?,?)",
        [(sid, s, t, et, sp) for s, t, et, sp in edges],
    )
    db.execute(
        "INSERT INTO vulnerabilities(scan_id, package, installed_version, osv_id, cve, severity, "
        "summary, fixed_version, url, data_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, "C", "1.0.0", "GHSA-test", "CVE-2020-0001", "high", "test advisory", "1.0.3",
         "https://osv.dev/x",
         json.dumps({"id": "GHSA-test", "cve": "CVE-2020-0001", "fixed_version": "1.0.3"})),
    )
    return sid


def test_upgrade_constraint_conflict_and_breaking(db):
    sid = _seed(db)
    r = simulate(db, sid, "C", "upgrade", "2.0.0")
    kinds = [f.kind for f in r.findings]
    assert "breaking" in kinds  # major change
    conflicts = [f for f in r.findings if f.kind == "constraint-conflict"]
    assert len(conflicts) == 2  # A (^1.0.0) and B (~1.0.0) both reject 2.0.0


def test_upgrade_resolves_security(db):
    sid = _seed(db)
    r = simulate(db, sid, "C", "upgrade", "1.0.5")
    sec = [f for f in r.findings if f.kind == "security"]
    assert any("resolves" in f.message for f in sec)
    # 1.0.5 satisfies ^1.0.0 and ~1.0.0 -> no conflicts.
    assert not any(f.kind == "constraint-conflict" for f in r.findings)


def test_remove_direct_with_usage_is_critical(db):
    sid = _seed(db)
    r = simulate(db, sid, "A", "remove")
    usage_findings = [f for f in r.findings if f.kind == "usage"]
    assert any(f.severity == "critical" for f in usage_findings)
    # Removing A orphans D (only reachable via A) but not C (also via B).
    tree = [f for f in r.findings if f.kind == "tree"]
    assert tree and "D" in (tree[0].detail or "")


def test_remove_shared_package_lists_dependents(db):
    sid = _seed(db)
    r = simulate(db, sid, "C", "remove")
    deps = [f for f in r.findings if f.kind == "dependents"]
    assert deps  # A and B depend on C


def test_replace_requires_alternative(db):
    sid = _seed(db)
    r = simulate(db, sid, "A", "replace", alternative="A-fork",
                 alternative_info={"license": "MIT", "latest": "3.0.0"})
    assert r.alternative == "A-fork"
    assert r.verification


def test_simulate_unknown_package_raises(db):
    sid = _seed(db)
    import pytest

    with pytest.raises(ValueError):
        simulate(db, sid, "does-not-exist", "upgrade", "1.0.0")
