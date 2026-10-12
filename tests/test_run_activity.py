import json
import threading
from pathlib import Path

from streamlit.testing.v1 import AppTest

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.run_activity import RunActivity

APP = Path(__file__).parents[1] / "src/bluecheese/interfaces/console.py"
FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


def test_live_model_wait_handoffs_gui_rerenders_and_cancellation(tmp_path, monkeypatch):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    entered, release = threading.Event(), threading.Event()
    calls = []

    def transport(profile, payload, timeout):
        calls.append(payload)
        entered.set()
        assert release.wait(10), "Test did not release the model transport"
        context = json.loads(payload["messages"][1]["content"])
        event_id = context["selected_seed_id"]
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "verdict": "UNCERTAIN",
                                "hypothesis": "Sensor alert observed.",
                                "supporting_ids": [event_id],
                                "contradicting_ids": [],
                                "claims": [
                                    {
                                        "text": "An alert was retrieved.",
                                        "citations": [event_id],
                                    }
                                ],
                                "disconfirmation_test": "Review related flows.",
                                "unresolved": ["Intent unknown."],
                            }
                        )
                    },
                }
            ]
        }

    try:
        runtime.command("import_file", FIXTURE, "live", "external")
        runtime.configure_provider(
            AgentModelProvider(
                ModelProfile("http://localhost:8080/v1/chat/completions", "test-model"),
                transport,
            )
        )
        future = runtime.begin_run("live", "external", max_seconds=30)
        assert entered.wait(5)
        activity = runtime.activity.snapshot()
        assert activity["state"] == "RUNNING"
        assert activity["events"][-1]["role"] == "Investigator"
        assert activity["events"][-1]["kind"] == "model"
        assert "Awaiting model response" in activity["events"][-1]["message"]
        assert any(
            e["role"] == "Triage" and e["handoff_to"] == "Orchestrator"
            for e in activity["events"]
        )
        assert any(
            e["role"] == "Orchestrator" and e["handoff_to"] == "Investigator"
            for e in activity["events"]
        )
        activity["events"][-1]["message"] = "mutated"
        assert runtime.activity.snapshot()["events"][-1]["message"] != "mutated"
        monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "state"))
        monkeypatch.setattr(
            "bluecheese.application.demo_runtime.DemoRuntime",
            lambda *args, **kwargs: runtime,
        )
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        assert not app.exception
        assert any("Awaiting model response" in item.value for item in app.text)
        assert any("Passed to Orchestrator" == item.value for item in app.text)
        assert any("Model call" == item.value for item in app.caption)
        app.run()
        assert len(calls) == 1
        assert runtime.status()["investigation_runs"] == 1
        assert runtime.status()["worker_starts"] == 0
        runtime.cancel()
        app.run()
        assert any("Cancellation requested" in item.value for item in app.text)
        release.set()
        assert future.result(5)["run_status"] == "CANCELLED"
        app.run()
        assert not app.exception
        assert runtime.activity.snapshot()["state"] == "CANCELLED"
        assert any("Investigation cancelled" in item.value for item in app.text)
        assert len(calls) == 1
    finally:
        release.set()
        runtime.close()


def test_finished_trace_is_saved_and_new_run_replaces_live_trace(tmp_path):
    runtime = DemoRuntime(tmp_path)
    try:
        report = runtime.run("suspicious", "clean")
        live = runtime.activity.snapshot()
        assert live["state"] == "COMPLETED"
        assert live["run_id"] == report["run_id"]
        assert live["events"][-1]["status"] == "completed"
        assert {event["role"] for event in live["events"]} == {
            "Orchestrator",
            "Triage",
            "Correlation",
            "Investigator",
            "Falsifier",
            "Reporter",
        }
        assert not any(event["kind"] == "model" for event in live["events"])
        saved = runtime.command("get_run", "suspicious", "clean", report["run_id"])
        assert saved["report"]["workflow_activity"] == report["workflow_activity"]
        assert any(e["handoff_to"] == "Falsifier" for e in report["workflow_activity"])
        next_report = runtime.run("benign", "clean", falsification=False)
        next_live = runtime.activity.snapshot()
        assert next_live["run_id"] == next_report["run_id"] != live["run_id"]
        assert next_live["events"][0]["sequence"] == 1
        assert any(
            e["role"] == "Falsifier" and e["status"] == "skipped"
            for e in next_live["events"]
        )
        assert report["workflow_activity"] == saved["report"]["workflow_activity"]
    finally:
        runtime.close()


def test_failed_and_budget_exhausted_runs_leave_terminal_activity(tmp_path):
    runtime = DemoRuntime(tmp_path)
    try:

        class FailedProvider:
            label = "Failing test provider"

            def investigate(self, tools, falsification):
                raise RuntimeError("Provider unavailable")

        import pytest

        with pytest.raises(RuntimeError, match="unavailable"):
            runtime.run("suspicious", "clean", provider=FailedProvider())
        activity = runtime.activity.snapshot()
        assert activity["state"] == "FAILED"
        assert activity["events"][-1]["role"] == "Investigator"
        assert activity["events"][-1]["status"] == "failed"
        report = runtime.run("suspicious", "clean", max_calls=0)
        assert report["run_status"] == "INCOMPLETE"
        assert runtime.activity.snapshot()["state"] == "INCOMPLETE"
        assert runtime.activity.snapshot()["events"][-1]["status"] == "incomplete"
    finally:
        runtime.close()


def test_activity_history_is_bounded_and_elapsed_stops_at_finish():
    now = [0.0]
    activity = RunActivity(threading.RLock(), clock=lambda: now[0])
    assert activity.snapshot()["state"] == "IDLE"
    activity.reset()
    for index in range(200):
        activity.emit("Investigator", "working", f"Step {index}")
    assert len(activity.snapshot()["events"]) == 128
    now[0] = 3.0
    activity.finish("COMPLETED")
    now[0] = 20.0
    assert activity.snapshot()["elapsed_seconds"] == 3.0
