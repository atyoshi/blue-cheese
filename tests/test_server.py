"""Production API journeys use isolated state and deterministic local evidence."""

import json
import threading
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.interfaces.server import create_app

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"
SCOPE = ("live", "external")


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "state")) as client:
        token = client.get("/api/v1/session").json()["csrf"]
        client.headers["x-csrf-token"] = token
        yield client


def seed(client):
    response = client.post(
        "/api/v1/source", json={"action": "import", "path": str(FIXTURE.resolve())}
    )
    assert response.status_code == 200, response.text
    return client.get("/api/v1/alerts").json()["groups"][0]["seed_ids"][0]


def run_case(client):
    event_id = seed(client)
    response = client.post("/api/v1/cases", json={"seed_event_id": event_id})
    assert response.status_code == 200, response.text
    runtime = client.app.state.runtime
    report = runtime.pending_run.result(10)
    return report["run_id"], event_id


def test_api_alert_to_decision_restart_and_export(client, tmp_path):
    run_id, event_id = run_case(client)
    base = "/api/v1/cases/" + run_id
    saved = client.get(base).json()
    assert saved["status"] == "COMPLETED"
    assert saved["findings"] and saved["protocol_observations"] == []
    assert client.get(base + "/activity").json()["events"][-1]["status"] == "completed"
    records = client.get(base + "/evidence").json()
    assert records["rows"] and records["total"] == saved["record_count"]
    evidence = client.get(f"/api/v1/evidence/{event_id}?run_id={run_id}").json()
    assert evidence["raw"] in FIXTURE.read_text()
    assert (
        client.post(
            base + "/decisions",
            json={
                "actor": "Analyst",
                "owner": "On call",
                "disposition": "ESCALATED",
                "note": "Need endpoint context",
            },
        ).status_code
        == 200
    )
    assert client.get(base).json()["owner"] == "On call"
    assert client.get(base + "/decisions").json()[0]["actor"] == "Analyst"
    for suffix in ("report.json", "report.md"):
        response = client.get(base + "/" + suffix)
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
    assert (
        client.post(
            "/api/v1/chat",
            json={
                "run_id": run_id,
                "message": "Summarize this case",
                "task": "Evidence",
                "evidence_id": event_id,
            },
        ).status_code
        == 200
    )
    client.app.state.runtime.pending_chat.result(10)
    chat = client.get("/api/v1/chat?run_id=" + run_id).json()
    assert chat["messages"][-1]["role"] == "assistant"
    assert not chat["error"]
    successor = client.post("/api/v1/cases", json={"parent_run_id": run_id})
    assert successor.status_code == 200
    second = client.app.state.runtime.pending_run.result(10)
    assert second["run_id"] != run_id
    assert client.get(base).json()["snapshot_id"] == saved["snapshot_id"]
    client.app.state.runtime.close()
    with TestClient(create_app(tmp_path / "state")) as restarted:
        assert restarted.get(base).json()["owner"] == "On call"
        assert restarted.get("/api/v1/status").json()["investigation_runs"] == 0


def test_security_boundaries_and_readonly_render(client):
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/").status_code == 200
    assert "script-src 'self'" in client.get("/").headers["content-security-policy"]
    assert client.get("/api/v1/command").status_code == 404
    assert (
        client.post(
            "/api/v1/source", json={"action": "stop"}, headers={"x-csrf-token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/source",
            json={"action": "stop"},
            headers={"origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/cases", json={"scenario": "suspicious", "variant": "clean"}
        ).status_code
        == 400
    )
    assert (
        client.get("/api/v1/status", headers={"host": "attacker.example"}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/source", json={"action": "stop", "extra": True}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/source", content="{}", headers={"content-type": "text/plain"}
        ).status_code
        == 415
    )
    assert client.post("/api/v1/chat", json={"message": "x" * 33000}).status_code == 413
    assert client.get("/api/v1/alerts?page=-1").status_code == 400
    for _ in range(3):
        for path in (
            "status",
            "alerts",
            "cases",
            "network",
            "settings",
            "chat",
            "records",
        ):
            assert client.get("/api/v1/" + path).status_code == 200
    assert client.app.state.runtime.investigation_runs == 0
    assert client.app.state.runtime.worker_starts == 0
    assert client.app.state.runtime.command("snapshot") == 0


def test_evidence_snapshot_scope_and_escaped_content(client, tmp_path):
    run_id, _ = run_case(client)
    path = tmp_path / "late.jsonl"
    row = json.loads(FIXTURE.read_text().splitlines()[0])
    row["alert"]["signature"] = '<script>alert("x")</script>'
    path.write_text(json.dumps(row) + "\n")
    client.app.state.runtime.command("import_file", path, *SCOPE)
    event_id = client.get("/api/v1/records").json()["rows"][0]["id"]
    assert client.get(f"/api/v1/evidence/{event_id}?run_id={run_id}").status_code == 404
    assert "<script>" in client.get(f"/api/v1/evidence/{event_id}").json()["raw"]
    assert client.get("/api/v1/cases/missing/evidence").status_code == 404
    assert (
        client.post("/api/v1/cases", json={"parent_run_id": "missing"}).status_code
        == 404
    )


def test_settings_keep_keys_private_and_probe_only_on_request(client, monkeypatch):
    probes = []
    monkeypatch.setattr(
        AgentModelProvider,
        "test_connection",
        lambda _: probes.append(1) or {"status": "passed"},
    )
    response = client.post(
        "/api/v1/settings",
        json={
            "mode": "model",
            "endpoint": "http://127.0.0.1:8080/v1",
            "model": "local",
            "api_key": "private-value",
        },
    )
    assert response.status_code == 200
    assert "private-value" not in response.text
    for _ in range(3):
        assert "private-value" not in client.get("/api/v1/settings").text
    assert probes == []
    assert client.post("/api/v1/probe", json={}).status_code == 200
    client.app.state.probe.result(5)
    assert client.get("/api/v1/probe").json()["result"] == {"status": "passed"}
    assert probes == [1]
    assert client.post("/api/v1/settings", json={"mode": "rules"}).status_code == 200
    assert client.app.state.runtime.provider is None


def test_live_activity_cancel_and_refresh_do_not_duplicate_requests(client):
    seed_id = seed(client)
    entered, release = threading.Event(), threading.Event()
    calls = []

    def transport(profile, payload, timeout):
        calls.append(payload)
        entered.set()
        assert release.wait(10)
        raise RuntimeError("Stopped model")

    runtime = client.app.state.runtime
    runtime.configure_provider(
        AgentModelProvider(
            ModelProfile("http://localhost/v1/chat/completions", "local"), transport
        )
    )
    try:
        assert (
            client.post("/api/v1/cases", json={"seed_event_id": seed_id}).status_code
            == 200
        )
        assert entered.wait(5)
        run_id = runtime.activity.snapshot()["run_id"]
        for _ in range(3):
            activity = client.get(f"/api/v1/cases/{run_id}/activity").json()
            assert activity["status"] == "RUNNING"
            assert activity["events"][-1]["kind"] == "model"
            assert client.get(f"/api/v1/cases/{run_id}").status_code == 200
        assert len(calls) == 1 and runtime.investigation_runs == 1
        assert client.post(f"/api/v1/cases/{run_id}/cancel", json={}).status_code == 200
        release.set()
        assert runtime.pending_run.result(5)["run_status"] == "CANCELLED"
        assert (
            client.get(f"/api/v1/cases/{run_id}/activity").json()["status"]
            == "CANCELLED"
        )
    finally:
        release.set()


def test_proposals_are_server_owned_and_cannot_be_replayed(client):
    run_id, _ = run_case(client)
    runtime = client.app.state.runtime
    runtime.command(
        "append_chat",
        *SCOPE,
        run_id,
        "assistant",
        json.dumps(
            {
                "action": "investigate",
                "argument": "Review this case",
                "reply": "Review proposed",
                "citations": [],
            }
        ),
    )
    item = client.get("/api/v1/chat?run_id=" + run_id).json()["messages"][-1]
    body = {"run_id": run_id, "created_at": item["created_at"]}
    assert (
        client.post("/api/v1/proposals", json={**body, "action": "stop"}).status_code
        == 400
    )
    assert client.post("/api/v1/proposals", json=body).status_code == 200
    runtime.pending_run.result(10)
    assert client.post("/api/v1/proposals", json=body).status_code == 400
    assert runtime.investigation_runs == 2


def test_source_validation_and_polling_owner(client):
    assert (
        client.post(
            "/api/v1/source", json={"action": "connect", "path": "/missing/eve"}
        ).status_code
        == 400
    )
    assert client.app.state.runtime.worker_starts == 0
    body = {"action": "connect", "path": str(FIXTURE.resolve())}
    assert client.post("/api/v1/source", json=body).status_code == 200
    assert client.post("/api/v1/source", json=body).status_code == 400
    for _ in range(3):
        client.get("/api/v1/status")
    assert client.app.state.runtime.worker_starts == 1
    assert client.post("/api/v1/source", json={"action": "stop"}).status_code == 200


def test_native_provider_roundtrip_and_captured_case_selection(client):
    body = {
        "mode": "model",
        "decision": True,
        "endpoint": "http://localhost:8080/v1",
        "model": "native",
        "api_key": "native-secret",
    }
    assert client.post("/api/v1/settings", json=body).status_code == 200
    configured = client.get("/api/v1/settings").json()["decision"]
    assert configured["endpoint"] == "http://localhost:8080/v1/systemone"
    assert (
        client.post(
            "/api/v1/settings",
            json={**body, "endpoint": configured["endpoint"], "api_key": ""},
        ).status_code
        == 200
    )
    assert client.app.state.runtime.decision_provider.profile.api_key == "native-secret"
    assert (
        client.app.state.runtime.decision_provider.profile.endpoint
        == configured["endpoint"]
    )
    # Configure-only and reads never call the endpoint.
    client.app.state.runtime.configure_provider(None, decision=True)
    run_id, _event_id = run_case(client)
    saved = client.get("/api/v1/cases/" + run_id).json()
    assert client.get("/api/v1/cases").json()[0]["case_id"] == saved["case_id"]
    pair = saved["pairs"][0]
    assert (
        client.post(
            "/api/v1/chat",
            json={
                "run_id": run_id,
                "message": "Explain this view",
                "task": "Activity",
                "connection": [pair["source"], pair["destination"]],
            },
        ).status_code
        == 200
    )
    result = client.app.state.runtime.pending_chat.result(10)
    assert result["view_context"]["task"] == "Agent activity"
    assert "operations" in result["reply"]
    assert (
        client.post("/api/v1/cases", json={"seed_event_id": "missing"}).status_code
        == 400
    )
    assert client.app.state.runtime.investigation_runs == 1
    assert client.get("/api/v1/status").json()["counts"]["alerts"] == 1
