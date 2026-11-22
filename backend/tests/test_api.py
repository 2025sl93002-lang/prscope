"""API and persistence integration tests — all offline (no network).

Scans run with online=False, so registry/OSV are skipped and the pipeline is
fully deterministic against the committed demo fixture.
"""

import pytest
from fastapi.testclient import TestClient

from deplens.main import app


@pytest.fixture
def client(db):
    return TestClient(app)


def _scan(client, demo_project, online=False):
    r = client.post("/api/scan", json={"path": str(demo_project), "online": online})
    assert r.status_code == 200, r.text
    return r.json()["scan_id"], r.json()["project_id"]


def test_health_endpoint(client):
    assert client.get("/api/health").json()["product"] == "DepLens"


def test_scan_and_detail(client, demo_project):
    sid, pid = _scan(client, demo_project)
    detail = client.get(f"/api/scans/{sid}").json()
    assert detail["summary"]["total"] == 73
    assert detail["summary"]["direct"] == 8
    # Offline: security stage skipped, health confidence is partial (honest).
    assert detail["health_confidence"] == "partial"
    stages = {s["key"]: s["status"] for s in detail["stages"]}
    assert stages["security"] == "skipped"
    assert stages["resolve"] == "ok"


def test_packages_filtering(client, demo_project):
    sid, _ = _scan(client, demo_project)
    direct = client.get(f"/api/scans/{sid}/packages", params={"type": "direct"}).json()
    assert direct["count"] == 8
    unused = client.get(f"/api/scans/{sid}/packages", params={"filter": "unused"}).json()
    names = {p["name"] for p in unused["packages"]}
    assert "moment" in names  # declared but not imported in the fixture


def test_package_detail_paths(client, demo_project):
    sid, _ = _scan(client, demo_project)
    detail = client.get(f"/api/scans/{sid}/package/express").json()
    assert detail["is_direct"]
    assert detail["dependency_paths"]
    assert detail["data"]["usage"]["status"] == "confirmed"


def test_graph_endpoint(client, demo_project):
    sid, _ = _scan(client, demo_project)
    g = client.get(f"/api/scans/{sid}/graph").json()
    assert any(n.get("root") for n in g["nodes"])
    assert len(g["edges"]) > 50
    # Blast radius: deep shared packages have several dependents.
    assert any((n.get("blast_radius") or 0) > 1 for n in g["nodes"])


def test_remediation_endpoint(client, demo_project):
    sid, _ = _scan(client, demo_project)  # offline -> no advisories
    plan = client.get(f"/api/scans/{sid}/remediation").json()
    assert plan["total_advisories"] == 0
    assert "remediate" in plan["summary"].lower()
    assert plan["actions"] == []


def test_graph_filter_excludes_dev(client, demo_project):
    sid, _ = _scan(client, demo_project)
    full = client.get(f"/api/scans/{sid}/graph").json()
    no_dev = client.get(f"/api/scans/{sid}/graph", params={"include_dev": False}).json()
    assert len(no_dev["nodes"]) <= len(full["nodes"])


def test_usage_endpoint(client, demo_project):
    sid, _ = _scan(client, demo_project)
    usage = client.get(f"/api/scans/{sid}/usage").json()["usage"]
    statuses = {u["package"]: u["status"] for u in usage}
    assert statuses["moment"] == "none"
    assert statuses["lodash"] == "confirmed"


def test_impact_endpoint_offline(client, demo_project):
    sid, _ = _scan(client, demo_project)
    r = client.post(f"/api/scans/{sid}/impact",
                    json={"package": "express", "action": "remove", "online": False})
    assert r.status_code == 200
    body = r.json()
    assert body["affected_files"]  # express is imported
    assert any(f["kind"] == "tree" for f in body["findings"])


def test_decision_lifecycle(client, demo_project):
    sid, pid = _scan(client, demo_project)
    created = client.post(
        f"/api/projects/{pid}/decisions",
        json={"package": "lodash", "action": "upgrade", "decision": "upgrade",
              "reason": "fix vulns", "verification": [{"text": "run tests"}]},
    ).json()
    did = created["id"]
    assert created["verification"][0]["text"] == "run tests"
    updated = client.put(
        f"/api/decisions/{did}",
        json={"package": "lodash", "action": "upgrade", "decision": "upgrade",
              "status": "verified",
              "verification": [{"text": "run tests", "status": "complete"}]},
    ).json()
    assert updated["status"] == "verified"
    listed = client.get(f"/api/projects/{pid}/decisions").json()["decisions"]
    assert len(listed) == 1
    assert client.delete(f"/api/decisions/{did}").status_code == 200
    assert client.get(f"/api/projects/{pid}/decisions").json()["decisions"] == []


def test_usage_override_persists(client, demo_project):
    sid, pid = _scan(client, demo_project)
    client.post(f"/api/projects/{pid}/usage-override",
                json={"package": "moment", "state": "intentional", "note": "used via plugin"})
    usage = client.get(f"/api/scans/{sid}/usage").json()["usage"]
    moment = next(u for u in usage if u["package"] == "moment")
    assert moment["override"]["state"] == "intentional"


def test_reports_all_formats(client, demo_project):
    sid, _ = _scan(client, demo_project)
    md = client.get(f"/api/scans/{sid}/report", params={"format": "markdown"})
    assert "# DepLens Report" in md.text
    js = client.get(f"/api/scans/{sid}/report", params={"format": "json"})
    assert js.json()["summary"]["total"] == 73
    csv = client.get(f"/api/scans/{sid}/report", params={"format": "csv"})
    assert "name,version,latest" in csv.text


def test_scan_comparison(client, demo_project):
    sid1, pid = _scan(client, demo_project)
    sid2, _ = _scan(client, demo_project)
    cmp = client.get(f"/api/scans/{sid2}/compare/{sid1}").json()
    # Identical scans -> no changes.
    assert cmp["added"] == [] and cmp["removed"] == []
    assert cmp["health_change"]["delta"] == 0


def test_settings_roundtrip(client):
    client.get("/api/health")  # ensure db init
    settings = client.get("/api/settings").json()
    assert settings["privacy"]["telemetry"]
    client.put("/api/settings", json={"online_default": False})
    assert client.get("/api/settings").json()["online_default"] is False


def test_scan_bad_path_returns_400(client):
    r = client.post("/api/scan", json={"path": "/nonexistent/path/xyz", "online": False})
    assert r.status_code == 400


def test_project_without_manifest_422(client, tmp_path):
    r = client.post("/api/scan", json={"path": str(tmp_path), "online": False})
    assert r.status_code == 422
