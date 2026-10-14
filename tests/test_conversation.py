"""Read-only conversation, captured selection, isolated practice and real traces."""

import json
import threading
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.view_context import ViewContext, read_answer
from bluecheese.interfaces.console_workflow import practice_checkpoints
from bluecheese.interfaces.terminal import TerminalSession, route

SCOPE = ("live", "external")
ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "src/bluecheese/data/suspicious-clean.jsonl"
APP = ROOT / "src/bluecheese/interfaces/console.py"


@pytest.fixture
def runtime(tmp_path):
    instance = DemoRuntime(tmp_path / "practice", load_fixtures=False, practice=True)
    instance.command("import_file", FIXTURE, *SCOPE)
    yield instance
    instance.close()


@pytest.mark.parametrize(
    "question,intent",
    [
        ("Summarize these alerts", "summarize"),
        ("Summarize that investigation", "summarize"),
        ("What is a flow?", "explain"),
        ("What does this alert mean?", "explain"),
        ("What am I looking at?", "explain"),
        ("What are you doing?", "status"),
        ("Explain this view", "explain"),
        ("Show the evidence", "explain"),
        ("What should I check next?", "explain"),
    ],
)
def test_reading_intents_never_investigate_or_call_model(runtime, question, intent):
    assert route(question, model_chat=True)[0] == intent

    def unavailable(*args):
        pytest.fail("Read-only conversation called a model")

    runtime.configure_provider(
        AgentModelProvider(
            ModelProfile("http://localhost/v1/chat/completions", "unavailable"),
            unavailable,
        )
    )
    result = runtime.begin_chat(question).result(5)
    assert not result.get("error")
    assert result["action"] == "answer"
    assert result["scope"] and result["reply"]
    assert runtime.command("list_runs", *SCOPE) == []
    assert runtime.investigation_runs == 0
    assert not runtime.automatic


def test_practice_checkpoints_and_trace_survive_restart(runtime):
    checks = practice_checkpoints(runtime)
    assert checks == {
        "Input ready": True,
        "Target selected": False,
        "Evidence retrieved": False,
        "Analysis finished": False,
        "Decision recorded": False,
    }
    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]["id"]
    report = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(10)
    run_id = report["run_id"]
    assert all(
        value
        for key, value in practice_checkpoints(runtime, run_id).items()
        if key != "Decision recorded"
    )
    assert "Synthetic data" in report["warnings"][0]
    saved = runtime.command("get_run", *SCOPE, run_id)
    completed = [
        e
        for e in saved["workflow_activity"]
        if e["kind"] == "tool" and e.get("outcome") == "OK"
    ]
    assert len(completed) == len(saved["tool_activity"])
    for call, event in zip(saved["tool_activity"], completed, strict=True):
        for key in (
            "operation_id",
            "returned_count",
            "returned_ids",
            "arguments",
            "truncated",
            "duration_seconds",
        ):
            assert call[key] == event[key]
        assert event["duration_seconds"] >= 0
    runtime.command(
        "save_case_decision",
        *SCOPE,
        run_id,
        "Analyst",
        "On-call",
        "ESCALATED",
        "Need endpoint context",
    )
    assert all(practice_checkpoints(runtime, run_id).values())
    state_dir = runtime.state_dir
    runtime.close()
    restored = DemoRuntime(state_dir, load_fixtures=False, practice=True)
    try:
        assert all(practice_checkpoints(restored, run_id).values())
        answer = restored.begin_chat("Summarize that investigation", run_id).result(5)
        assert run_id in answer["scope"]
        assert "Execution: completed" in answer["reply"]
        assert "Unknowns:" in answer["reply"]
        assert restored.investigation_runs == 0
    finally:
        restored.close()


def test_terminal_summary_scope_and_actual_command_context(runtime):
    output = []
    terminal = TerminalSession(runtime, read=lambda _: "yes", write=output.append)
    terminal.execute("summary", "")
    assert "bounded workspace overview" in output[0]
    terminal.execute("alerts", "")
    displayed = json.loads(output[-1])
    terminal.execute(*route("Summarize these alerts", model_chat=True))
    assert "Alerts" in output[-2]
    assert displayed[0]["id"] in output[-1]
    assert "no new investigation" in output[-1]
    report = runtime.begin_run(
        *SCOPE, seed_event_id=displayed[0]["id"], max_calls=8
    ).result(10)
    terminal.execute("report", report["run_id"])
    terminal.execute(*route("Summarize that investigation"))
    assert report["run_id"] in output[-2]
    terminal.execute("explain", "flow")
    assert "General definition" in output[-2]
    assert "network conversation" in output[-1]
    terminal.execute("summary", report["run_id"])
    assert report["run_id"] in output[-2]
    assert runtime.investigation_runs == 1
    assert (
        terminal.last_result["output"]
        and terminal.view_context.run_id == report["run_id"]
    )


def test_captured_selection_drives_model_evidence_despite_navigation(runtime):
    entered, release = threading.Event(), threading.Event()
    rows = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))
    selected, other = rows[0]["id"], rows[-1]["id"]
    contexts = []

    def transport(profile, payload, timeout):
        context = json.loads(payload["messages"][1]["content"].split(": ", 1)[1])
        contexts.append(context)
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
                                "reply": "Selected alert was retrieved.",
                                "citations": [selected],
                            }
                        )
                    },
                }
            ]
        }

    runtime.configure_provider(
        AgentModelProvider(
            ModelProfile("http://localhost/v1/chat/completions", "mock"), transport
        )
    )
    view = ViewContext(
        page="Alerts", evidence_id=selected, snapshot=runtime.command("snapshot")
    )
    future = runtime.begin_chat("Why is this suspicious?", view_context=view)
    try:
        assert entered.wait(5)
        view = ViewContext(page="Flows", evidence_id=other)
        assert not future.done()
        assert contexts[0]["view_context"]["evidence_id"] == selected
        assert [row["id"] for row in contexts[0]["observations"]] == [selected]
    finally:
        release.set()
    result = future.result(5)
    assert result["view_context"]["evidence_id"] == selected
    assert result["citations"] == [selected]
    assert not runtime.command("list_runs", *SCOPE)


def test_selected_connection_summary_is_bounded_and_scoped(runtime):
    first = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0][
        "normalized"
    ]
    pair = (first["src_ip"], first["dest_ip"])
    view = ViewContext(page="Network", connection=pair, record_limit=2)
    answer = read_answer(runtime, "summarize", "this connection", view)
    assert " → ".join(pair) in answer["scope"]
    assert len(answer["citations"]) <= 2
    for event_id in answer["citations"]:
        row = runtime.command("get_event", *SCOPE, answer["snapshot"], event_id)[
            "normalized"
        ]
        assert (row["src_ip"], row["dest_ip"]) == pair
    assert "not an exhaustive review" in answer["reply"]
    assert not runtime.command("list_runs", *SCOPE)
    missing = runtime.begin_chat("/summary missing-run").result(5)
    assert missing["error"] and "unavailable" in missing["reply"]


def test_practice_gui_navigation_and_refresh_never_start_work(tmp_path, monkeypatch):
    operational = DemoRuntime(tmp_path / "operations", load_fixtures=False)
    practice = DemoRuntime(tmp_path / "practice", load_fixtures=False, practice=True)
    monkeypatch.setenv("BLUECHEESE_STATE", str(tmp_path / "operations"))
    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime",
        lambda *a, **kw: practice if kw.get("practice") else operational,
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()

    def button(label):
        return next(item for item in app.button if item.label == label)

    try:
        app.sidebar.radio[0].set_value("Practice investigation").run()
        assert not app.exception
        assert practice.command("counts", *SCOPE)["accepted"] == 0
        button("Prepare practice input").click().run()
        assert practice.command("counts", *SCOPE)["accepted"] == 30
        seed = next(
            item for item in app.selectbox if item.label == "Practice target"
        ).options[1]
        next(item for item in app.selectbox if item.label == "Practice target").select(
            seed
        ).run()
        assert practice.investigation_runs == 0
        button("Run practice investigation").click().run()
        practice.pending_run.result(10)
        app.run()
        assert not app.exception
        assert any("Current activity" in item.value for item in app.markdown)
        assert any(item.label == "Review findings" for item in app.button)
        run_id = practice.command("list_runs", *SCOPE)[0]["run_id"]
        connection = next(
            item for item in app.selectbox if item.label == "Selected connection"
        )
        connection.set_value(tuple(connection.options[1].split(" → "))).run()
        button("Explain this view").click().run()
        answer = practice.pending_chat.result(5)
        assert answer["view_context"]["task"] == "Findings"
        assert not app.exception
        app.run()
        next(item for item in app.text_input if item.label == "Analyst").set_value(
            "Practice analyst"
        )
        next(item for item in app.selectbox if item.label == "Disposition").set_value(
            "ESCALATED"
        )
        button("Save analyst action").click().run()
        assert all(practice_checkpoints(practice, run_id).values())
        for _ in range(2):
            button("Refresh now").click().run()
        assert not app.exception
        assert app.session_state["case-tab-" + run_id] == "Findings"
        assert app.session_state["connection-" + run_id]
        assert practice.investigation_runs == 1
        assert practice.worker_starts == 0
        assert operational.command("counts", *SCOPE)["accepted"] == 0
        assert not operational.command("list_runs", *SCOPE)
    finally:
        practice.close()
        operational.close()


def test_timeout_trace_and_saved_summary_remain_readonly(runtime):
    def transport(*args):
        raise TimeoutError("Synthetic model timeout")

    runtime.configure_provider(
        AgentModelProvider(
            ModelProfile("http://localhost/v1/chat/completions", "mock-timeout"),
            transport,
        )
    )
    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]["id"]
    with pytest.raises(TimeoutError):
        runtime.begin_run(*SCOPE, seed_event_id=seed).result(5)
    run_id = runtime.command("list_runs", *SCOPE)[0]["run_id"]
    saved = runtime.command("get_run", *SCOPE, run_id)
    attempts = [e for e in saved["workflow_activity"] if e["kind"] == "model"]
    assert attempts[0]["outcome"] == "STARTED"
    assert attempts[-1]["outcome"] == "TIMEOUT"
    assert attempts[0]["operation_id"] == attempts[-1]["operation_id"]
    assert attempts[-1]["duration_seconds"] >= 0
    answer = runtime.begin_chat("Summarize that investigation", run_id).result(5)
    assert "Execution: failed" in answer["reply"]
    assert runtime.investigation_runs == 1
    assert not practice_checkpoints(runtime, run_id)["Analysis finished"]


def test_historical_trace_unavailable_and_source_gap_explanation(runtime, tmp_path):
    from bluecheese.application.ingestion import SourceGap

    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]["id"]
    run = runtime.command(
        "create_run", *SCOPE, "Historical case", None, seed_event_id=seed
    )
    state_dir = runtime.state_dir
    runtime.close()
    restored = DemoRuntime(state_dir, load_fixtures=False, practice=True)
    try:
        result = restored.begin_chat("What are you doing?", run["run_id"]).result(5)
        assert "Historical operation details are unavailable" in result["reply"]
        assert "interrupted" in result["reply"]
        path = tmp_path / "sensor.jsonl"
        path.write_bytes(FIXTURE.read_bytes())
        restored.start(path=path, replay=False, interval=3600)
        path.write_bytes(b"")
        with pytest.raises(SourceGap):
            restored.poll_once()
        # Exercise the worker's real failure boundary without a timed poll wait.
        restored._loop(0)
        result = restored.begin_chat("What is happening now?").result(5)
        assert "truncated" in result["reply"]
        assert not restored.status()["running"]
        assert restored.command("source_incidents")
        assert restored.investigation_runs == 0
    finally:
        restored.close()


def test_explicit_target_overrides_terminal_context(runtime):
    from bluecheese.application.telemetry_visuals import connection_graph

    first = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]
    report = runtime.begin_run(*SCOPE, seed_event_id=first["id"], max_calls=8).result(5)
    old = ViewContext(page="Terminal", run_id=report["run_id"], evidence_id=first["id"])
    answer = read_answer(runtime, "summarize", "Summarize endpoint 203.0.113.250", old)
    assert answer["run_id"] is None
    assert "endpoint 203.0.113.250" in answer["scope"]
    assert answer["citations"] == []
    assert runtime.investigation_runs == 1
    pairs = [{"source": "a", "destination": "b", "alerts": 1, "flows": 1, "records": 2}]
    graph = connection_graph(pairs, ("a", "b"))
    assert graph.count(" -> ") == 1
    assert "#e59b30" in graph


def test_capture_actual_tab_and_selection(runtime, monkeypatch):
    from bluecheese.interfaces.console_workflow import captured_view

    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]["id"]
    report = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(5)
    saved = runtime.command("get_run", *SCOPE, report["run_id"])
    run_id = report["run_id"]
    state = {
        "current-view-page": "Investigations",
        "case-tab-" + run_id: "Evidence and connections",
        "evidence-" + run_id: seed,
        "connection-" + run_id: ("10.0.0.8", "198.51.100.23"),
        "endpoint-" + run_id: "10.0.0.8",
        "kind-" + run_id: "alert",
    }
    monkeypatch.setattr(
        "bluecheese.interfaces.console_workflow.st.session_state", state
    )
    view = captured_view(runtime, saved)
    assert view.task == "Evidence and connections"
    assert view.evidence_id == seed and view.connection == state["connection-" + run_id]
    assert view.endpoint == "10.0.0.8" and view.event_type == "alert"
    state["case-tab-" + run_id] = "Findings"
    changed = captured_view(runtime, saved)
    assert not changed.evidence_id and changed.connection is None
    assert view.evidence_id == seed  # Previously captured context stays fixed.


@pytest.mark.parametrize(
    "question",
    [
        "What is quarantine?",
        "What is an endpoint?",
        "Explain a flow",
        "Explain severity",
        "What is the snapshot?",
        "What is an investigation budget?",
    ],
)
def test_plain_definitions_do_not_retrieve_or_investigate(runtime, question):
    result = runtime.begin_chat(question).result(5)
    assert result["scope"].startswith("General definition")
    assert not result["citations"] and not result.get("retrieval")
    assert runtime.investigation_runs == 0


def test_live_header_updates_status_without_rebuilding_case(runtime, monkeypatch):
    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]["id"]
    run = runtime.command(
        "create_run", *SCOPE, "Header state", None, seed_event_id=seed
    )
    monkeypatch.setattr(
        "bluecheese.interfaces.console_workflow._preview_runtime",
        runtime,
        raising=False,
    )
    monkeypatch.setattr(
        "bluecheese.interfaces.console_workflow._preview_run",
        run["run_id"],
        raising=False,
    )
    app = AppTest.from_string("""
from bluecheese.interfaces import console_workflow as workflow
workflow.activity_header(workflow._preview_runtime, workflow._preview_run)
""").run()
    assert (
        next(item for item in app.metric if item.label == "Analysis").value == "Running"
    )
    runtime.command("finish_run", run["run_id"], "FAILED", error="Synthetic failure")
    app.run()
    assert not app.exception
    assert (
        next(item for item in app.metric if item.label == "Analysis").value == "Failed"
    )
    assert any("Saved result" in item.value for item in app.caption)
    assert not any("Live execution" in item.value for item in app.caption)


def test_chat_submission_callback_once_per_explicit_question(runtime, monkeypatch):
    monkeypatch.setenv("BLUECHEESE_STATE", str(runtime.state_dir))
    monkeypatch.setattr(
        "bluecheese.application.demo_runtime.DemoRuntime", lambda *a, **kw: runtime
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    for expected in (2, 4):
        app.chat_input[0].set_value("Summarize these alerts").run()
        runtime.pending_chat.result(5)
        app.run()
        app.run()
        assert not app.exception
        assert len(runtime.command("chat_history", *SCOPE, None)) == expected
    assert runtime.investigation_runs == 0
