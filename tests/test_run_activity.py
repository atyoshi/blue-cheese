import threading
from pathlib import Path

from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.run_activity import RunActivity

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


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
