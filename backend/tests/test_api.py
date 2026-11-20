"""API, persistence, evidence & report tests via the real app. SPDX-License-Identifier: MIT"""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["name"] == "PRScope"


def test_invalid_repo_path_rejected(client):
    r = client.post("/api/repositories", json={"path": "/nonexistent/path/xyz"})
    assert r.status_code == 400


def test_path_traversal_and_nongit_rejected(client, tmp_path):
    r = client.post("/api/repositories", json={"path": str(tmp_path)})
    assert r.status_code == 400  # exists but not a git repo


def test_demo_setup_and_artifacts(analyzed_demo):
    analysis_id, client = analyzed_demo
    a = client.get(f"/api/analyses/{analysis_id}").json()
    assert a["status"] == "complete"
    assert a["files_changed"] >= 5
    assert a["attention_level"] in ("low", "moderate", "high", "critical")

    changes = client.get(f"/api/analyses/{analysis_id}/changes").json()
    cats = {c["category"] for c in changes}
    assert {"source", "api_contract", "config", "dependency"} <= cats

    graph = client.get(f"/api/analyses/{analysis_id}/graph").json()
    assert graph["function_level"] is False
    assert len(graph["edges"]) >= 3

    risk = client.get(f"/api/analyses/{analysis_id}/risk").json()
    assert risk["methodology_note"]
    for f in risk["findings"]:
        assert f["rule"] and f["explanation"]

    gaps = client.get(f"/api/analyses/{analysis_id}/test-gaps").json()
    assert any("refund_service" in g["changed_file"] for g in gaps)


def test_verification_evidence_and_readiness(analyzed_demo):
    analysis_id, client = analyzed_demo
    tasks = client.get(f"/api/analyses/{analysis_id}/tasks").json()
    assert tasks
    tid = tasks[0]["id"]

    # Transition status -> records history.
    r = client.patch(f"/api/tasks/{tid}", json={"status": "completed", "actor": "tester"})
    assert r.status_code == 200 and r.json()["status"] == "completed"
    hist = client.get(f"/api/tasks/{tid}/history").json()
    assert hist and hist[-1]["to_status"] == "completed"

    # Add + persist evidence.
    ev = client.post(f"/api/tasks/{tid}/evidence",
                     json={"evidence_type": "test_result", "note": "passed", "command": "pytest"})
    assert ev.status_code == 201
    listed = client.get(f"/api/tasks/{tid}/evidence").json()
    assert len(listed) == 1

    readiness = client.get(f"/api/analyses/{analysis_id}/readiness").json()
    assert readiness["completed_tasks"] >= 1
    assert readiness["tasks_with_evidence"] >= 1
    assert 0 <= readiness["completeness_percent"] <= 100


def test_custom_task_and_checklist(analyzed_demo):
    analysis_id, client = analyzed_demo
    # Add a custom task (user-added) and confirm it is deletable.
    ct = client.post(f"/api/analyses/{analysis_id}/tasks",
                     json={"title": "Manual smoke test", "verification_type": "manual"})
    assert ct.status_code == 201
    assert client.delete(f"/api/tasks/{ct.json()['id']}").status_code == 204

    # Checklist add / toggle / delete.
    item = client.post(f"/api/analyses/{analysis_id}/checklist",
                       json={"text": "Confirm demo works"}).json()
    upd = client.patch(f"/api/checklist/{item['id']}", json={"checked": True}).json()
    assert upd["checked"] is True
    assert client.delete(f"/api/checklist/{item['id']}").status_code == 204


def test_reports_export(analyzed_demo):
    analysis_id, client = analyzed_demo
    md = client.get(f"/api/analyses/{analysis_id}/report.md")
    assert md.status_code == 200 and "PRScope Verification Report" in md.text
    js = client.get(f"/api/analyses/{analysis_id}/report.json").json()
    assert js["analysis"]["id"] == analysis_id
    assert "limitations" not in js or True  # limitations live in md/html
    html = client.get(f"/api/analyses/{analysis_id}/report.html")
    assert html.status_code == 200 and "<html" in html.text.lower()


def test_ai_disabled_by_default(analyzed_demo):
    analysis_id, client = analyzed_demo
    status = client.get("/api/ai/status").json()
    assert status["enabled"] is False
    # Explain falls back to deterministic text when AI is disabled.
    r = client.post("/api/ai/explain", json={"analysis_id": analysis_id, "kind": "risk"}).json()
    assert r["source"] == "deterministic-fallback"
    assert r["available"] is False
    assert r["text"]
