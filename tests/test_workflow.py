"""End-to-end workflow checks: scoped evidence, real activity, chat and decisions."""

import json
import threading
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.telemetry_visuals import rank_endpoints

APP = Path(__file__).parents[1] / "src/bluecheese/interfaces/console.py"
FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"
SCOPE = ("live", "external")


def import_scenario(runtime, tmp_path):
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    for row in rows:
        row["src_ip"], row["dest_ip"] = "10.0.0.24", "198.51.100.8"
        if row["event_type"] == "alert":
            row["alert"]["severity"] = 1
            row["alert"]["signature"] = "Example suspicious outbound connection"
    path = tmp_path / "scenario.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    runtime.command("import_file", path, *SCOPE)
    return runtime.command("attention", *SCOPE, runtime.command("snapshot"))["groups"][
        0
    ]["seed_ids"][0]


def test_case_journey_snapshot_followup_decision_and_restart(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    seed = import_scenario(runtime, tmp_path)
    try:
        first = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(10)
        saved = runtime.command("get_run", *SCOPE, first["run_id"])
        assert "10.0.0.24" in saved["title"]
        assert saved["record_count"] == 2
        assert saved["workflow_activity"][-1]["status"] == "completed"
        assert any(
            "records returned" in event["message"]
            for event in saved["workflow_activity"]
        )
        assert saved["tool_activity"]
        immutable = saved["report"]
        runtime.command(
            "save_case_decision",
            *SCOPE,
            first["run_id"],
            "Analyst",
            "On-call",
            "ESCALATED",
            "Endpoint logs needed",
        )
        with pytest.raises(ValueError, match="scope"):
            runtime.command(
                "save_case_decision",
                "other",
                "scope",
                first["run_id"],
                "Analyst",
                "Owner",
                "OPEN",
                "",
            )
        result = runtime.begin_chat("/status", first["run_id"]).result(10)
        assert "Stored evidence: 2 accepted" in result["reply"]
        second = runtime.begin_run(
            *SCOPE,
            question="Check the authorized scanning explanation",
            seed_event_id=seed,
            parent_run_id=first["run_id"],
            max_calls=8,
        ).result(10)
        assert second["case_id"] == first["case_id"]
        assert second["case_revision"] == 2
        assert (
            runtime.command("get_run", *SCOPE, first["run_id"])["report"] == immutable
        )
    finally:
        runtime.close()
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        saved = runtime.command("get_run", *SCOPE, first["run_id"])
        assert saved["owner"] == "On-call"
        assert saved["disposition"] == "ESCALATED"
        assert saved["report"] == immutable
        assert runtime.command("chat_history", *SCOPE, first["run_id"])
        assert saved["workflow_activity"][-1]["status"] == "completed"
    finally:
        runtime.close()


def test_chat_grounding_rejects_fabrication_and_never_executes_proposals(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    seed = import_scenario(runtime, tmp_path)
    try:
        report = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(10)
        mode = {"action": "answer", "unknown": False}
        calls = []

        def transport(profile, payload, timeout):
            calls.append(payload)
            context = json.loads(payload["messages"][1]["content"].split(": ", 1)[1])
            assert context["selected_investigation"]["record_count"] == 2
            assert all("raw" not in item for item in context["observations"])
            assert "api_key" not in json.dumps(context)
            citation = (
                "invented-record"
                if mode["unknown"]
                else context["observations"][0]["id"]
            )
            return {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": mode["action"],
                                    "argument": "Check this target",
                                    "reply": "The sensor recorded this alert.",
                                    "citations": [citation],
                                }
                            )
                        },
                    }
                ]
            }

        runtime.configure_provider(
            AgentModelProvider(
                ModelProfile("http://localhost:8080/v1/chat/completions", "fake"),
                transport,
            )
        )
        reply = runtime.begin_chat("Why is this suspicious?", report["run_id"]).result(
            10
        )
        assert not reply.get("error")
        assert reply["citations"]
        assert reply["retrieval"]
        assert runtime.status()["investigation_runs"] == 1
        mode["unknown"] = True
        rejected = runtime.begin_chat("Explain the evidence", report["run_id"]).result(
            10
        )
        assert rejected["error"]
        assert "did not retrieve" in rejected["reply"]
        mode.update(unknown=False, action="investigate")
        proposed = runtime.begin_chat("Investigate further", report["run_id"]).result(
            10
        )
        assert proposed["action"] == "investigate"
        assert runtime.status()["investigation_runs"] == 1
        assert len(calls) == 3
    finally:
        runtime.close()


def test_chat_wait_duplicate_request_and_cancellation(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    entered, release = threading.Event(), threading.Event()
    try:

        def transport(*args):
            entered.set()
            assert release.wait(5)
            return {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": "answer",
                                    "argument": "",
                                    "reply": "No evidence.",
                                    "citations": [],
                                }
                            )
                        },
                    }
                ]
            }

        runtime.configure_provider(
            AgentModelProvider(
                ModelProfile("http://localhost:8080/v1/chat/completions", "fake"),
                transport,
            )
        )
        future = runtime.begin_chat("Explain the workspace")
        assert entered.wait(5)
        with pytest.raises(RuntimeError, match="already running"):
            runtime.begin_chat("Duplicate request")
        runtime.cancel_chat()
        release.set()
        result = future.result(5)
        assert result["error"] and "cancelled" in result["reply"]
        assert len(runtime.command("chat_history", *SCOPE)) == 2
    finally:
        release.set()
        runtime.close()


def test_real_journey_in_gui_and_readonly_refresh(tmp_path, monkeypatch):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    import_scenario(runtime, tmp_path)
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "state"))
    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime",
        lambda *args, **kwargs: runtime,
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    try:
        assert app.sidebar.radio[0].value == "Needs attention"
        next(
            button for button in app.button if button.label == "Investigate"
        ).click().run()
        runtime.pending_run.result(10)
        app.run()
        assert not app.exception
        assert app.sidebar.radio[0].value == "Investigations"
        assert any("10.0.0.24" in item.value for item in app.text)
        assert any("records returned" in item.value for item in app.text)
        assert (
            next(
                metric for metric in app.metric if metric.label == "Host compromise"
            ).value
            == "Unconfirmed"
        )
        app.chat_input[0].set_value("/status").run()
        runtime.pending_chat.result(5)
        app.run()
        assert not app.exception
        assert any("Stored evidence: 2 accepted" in item.value for item in app.text)
        next(item for item in app.text_input if item.label == "Analyst").set_value(
            "Analyst"
        )
        next(item for item in app.text_input if item.label == "Assigned to").set_value(
            "On-call"
        )
        next(item for item in app.selectbox if item.label == "Disposition").set_value(
            "ESCALATED"
        )
        next(
            item for item in app.button if item.label == "Save analyst action"
        ).click().run()
        next(
            button for button in app.sidebar.button if button.label == "Refresh now"
        ).click().run()
        assert not app.exception
        assert (
            next(metric for metric in app.metric if metric.label == "Assigned to").value
            == "On-call"
        )
        assert any("View refreshed" in item.value for item in app.success)
        assert runtime.status()["investigation_runs"] == 1
        assert runtime.status()["worker_starts"] == 0
        assert (
            len(
                runtime.command(
                    "chat_history",
                    *SCOPE,
                    runtime.command("list_runs", *SCOPE)[0]["run_id"],
                )
            )
            == 2
        )
    finally:
        runtime.close()


def test_endpoint_ranking_counts_self_connections_once():
    rows = [
        {"src_ip": "a", "dest_ip": "b", "event_type": "flow"},
        {"src_ip": "b", "dest_ip": "b", "event_type": "alert"},
    ]
    assert rank_endpoints(rows) == [
        {"ip": "b", "records": 2, "alerts": 1},
        {"ip": "a", "records": 1, "alerts": 0},
    ]


def test_attention_pages_old_high_priority_and_flags_new_activity(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        seed = import_scenario(runtime, tmp_path)
        first = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(10)
        raw = json.loads((tmp_path / "scenario.jsonl").read_text().splitlines()[0])
        # Appending at distinct positions creates distinct accepted occurrences.
        path = tmp_path / "more.jsonl"
        path.write_text((json.dumps(raw) + "\n") * 25)
        runtime.command("import_file", path, *SCOPE)
        result = runtime.command(
            "attention", *SCOPE, runtime.command("snapshot"), page=2
        )
        assert result["page"] == 2 and result["total"] == 26
        group = next(group for group in result["groups"] if seed in group["seed_ids"])
        assert group["run_id"] == first["run_id"]
        assert (
            group["new_alerts"] == 0
        )  # New file has a distinct source identity/group.
        assert runtime.command("get_run", *SCOPE, first["run_id"])["record_count"] == 2
    finally:
        runtime.close()


def test_new_activity_same_source_and_saved_snapshot_stays_fixed(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        path = tmp_path / "sensor.jsonl"
        path.write_bytes(FIXTURE.read_bytes())
        assert runtime.start(path=path, replay=False, interval=3600)
        seed = runtime.command("attention", *SCOPE, runtime.command("snapshot"))[
            "groups"
        ][0]["seed_ids"][0]
        first = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(10)
        last_accepted = runtime.status()["last_accepted"]
        runtime.poll_once()
        assert runtime.status()["last_poll"]
        assert runtime.status()["last_accepted"] == last_accepted
        with path.open("ab") as stream:
            stream.write(FIXTURE.read_bytes().splitlines(keepends=True)[0])
        runtime.poll_once()
        group = runtime.command("attention", *SCOPE, runtime.command("snapshot"))[
            "groups"
        ][0]
        assert group["new_alerts"] == 1
        assert group["run_id"] == first["run_id"]
        assert runtime.command("get_run", *SCOPE, first["run_id"])["record_count"] == 2
    finally:
        runtime.close()


def test_failed_activity_survives_restart_and_chat_local_commands(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        seed = import_scenario(runtime, tmp_path)

        class FailedProvider:
            label = "Failure test"

            def investigate(self, *args):
                raise RuntimeError("Model unavailable")

        runtime.configure_provider(FailedProvider())
        with pytest.raises(RuntimeError, match="Model unavailable"):
            runtime.begin_run(*SCOPE, seed_event_id=seed).result(10)
        run_id = runtime.command("list_runs", *SCOPE)[0]["run_id"]
    finally:
        runtime.close()
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        saved = runtime.command("get_run", *SCOPE, run_id)
        assert saved["status"] == "FAILED"
        assert saved["workflow_activity"][-1]["status"] == "failed"
        answer = runtime.begin_chat("/alerts", run_id).result(5)
        assert answer["citations"] == [seed]
        assert "10.0.0.24" in answer["reply"]
        assert (
            runtime.begin_chat("/network", run_id)
            .result(5)["reply"]
            .startswith("2 recent snapshot records")
        )
        assert (
            "Latest recorded operation"
            in runtime.begin_chat("What is being investigated?", run_id).result(5)[
                "reply"
            ]
        )
    finally:
        runtime.close()
