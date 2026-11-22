import json
import time

from deplens.parsers.lockfile import ROOT_ID
from deplens.services.apply_fix import compute_fix, write_fix


def _seed_project(db, tmp_path):
    """A real on-disk project + a scan with a direct and a transitive vuln."""
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "app",
                "version": "1.0.0",
                "dependencies": {"lodash": "^4.17.11", "express": "4.17.1"},
            },
            indent=2,
        )
        + "\n"
    )
    pid = db.upsert_project("app", str(tmp_path))
    cur = db.execute(
        "INSERT INTO scans(project_id, created_at, status, online, summary_json) "
        "VALUES (?,?,?,?,?)",
        (pid, time.time(), "completed", 1, "{}"),
    )
    sid = cur.lastrowid
    for nid, name, ver, direct in [
        ("lodash@4.17.11", "lodash", "4.17.11", 1),
        ("express@4.17.1", "express", "4.17.1", 1),
        ("qs@6.7.0", "qs", "6.7.0", 0),
    ]:
        db.execute(
            "INSERT INTO packages(scan_id, node_id, name, version, is_direct, scope) "
            "VALUES (?,?,?,?,?,?)",
            (sid, nid, name, ver, direct, "prod"),
        )
    for s, t in [(ROOT_ID, "lodash@4.17.11"), (ROOT_ID, "express@4.17.1"),
                 ("express@4.17.1", "qs@6.7.0")]:
        db.execute(
            "INSERT INTO edges(scan_id, source, target, edge_type, spec) VALUES (?,?,?,?,?)",
            (sid, s, t, "prod", "*"),
        )
    db.execute(
        "INSERT INTO vulnerabilities(scan_id, package, installed_version, osv_id, cve, severity, "
        "summary, fixed_version, url) VALUES (?,?,?,?,?,?,?,?,?)",
        (sid, "lodash", "4.17.11", "G1", "CVE-1", "critical", "x", "4.17.21", "http://x"),
    )
    db.execute(
        "INSERT INTO vulnerabilities(scan_id, package, installed_version, osv_id, cve, severity, "
        "summary, fixed_version, url) VALUES (?,?,?,?,?,?,?,?,?)",
        (sid, "qs", "6.7.0", "G2", "CVE-2", "high", "x", "6.11.0", "http://x"),
    )
    return sid


def test_compute_fix_direct_preserves_caret(db, tmp_path):
    sid = _seed_project(db, tmp_path)
    edit = compute_fix(db, sid)
    lodash = next(c for c in edit.changes if c.package == "lodash")
    assert lodash.kind == "dependency"
    assert lodash.from_spec == "^4.17.11"
    assert lodash.to_spec == "^4.17.21"  # caret preserved


def test_compute_fix_transitive_uses_overrides(db, tmp_path):
    sid = _seed_project(db, tmp_path)
    edit = compute_fix(db, sid)
    qs = next(c for c in edit.changes if c.package == "qs")
    assert qs.kind == "override"
    assert qs.to_spec == "6.11.0"
    new = json.loads(edit.new_content)
    assert new["overrides"]["qs"] == "6.11.0"
    assert new["dependencies"]["lodash"] == "^4.17.21"


def test_compute_fix_does_not_touch_disk(db, tmp_path):
    sid = _seed_project(db, tmp_path)
    before = (tmp_path / "package.json").read_text()
    compute_fix(db, sid)
    assert (tmp_path / "package.json").read_text() == before  # unchanged
    assert list(tmp_path.glob("*.bak*")) == []


def test_write_fix_writes_and_backs_up(db, tmp_path):
    sid = _seed_project(db, tmp_path)
    original = (tmp_path / "package.json").read_text()
    edit = write_fix(db, sid)
    assert edit.written is True
    written = json.loads((tmp_path / "package.json").read_text())
    assert written["dependencies"]["lodash"] == "^4.17.21"
    assert written["overrides"]["qs"] == "6.11.0"
    # Backup preserves the original exactly.
    backups = list(tmp_path.glob("package.json.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == original


def test_diff_is_produced(db, tmp_path):
    sid = _seed_project(db, tmp_path)
    edit = compute_fix(db, sid)
    assert "4.17.21" in edit.diff
    assert edit.install_command == "npm install"
