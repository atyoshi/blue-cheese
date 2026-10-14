"""Read-only conversation, captured selection, isolated practice and real traces."""

import json
import threading
from pathlib import Path

import pytest

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.view_context import ViewContext, read_answer
from bluecheese.interfaces.terminal import TerminalSession, route

SCOPE = ("live", "external")
ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "src/bluecheese/data/suspicious-clean.jsonl"


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
def test_reading_intents_use_model_without_investigating(runtime, question, intent):
    assert route(question, model_chat=True)[0] == intent

    calls = []

    def conversational(profile, payload, timeout):
        calls.append(payload)
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "answer",
                                "argument": "",
                                "reply": "Here is a concise explanation of the supplied context.",
                                "citations": [],
                            }
                        )
                    },
                }
            ]
        }

    runtime.configure_provider(
        AgentModelProvider(
            ModelProfile("http://localhost/v1/chat/completions", "unavailable"),
            conversational,
        )
    )
    result = runtime.begin_chat(question).result(5)
    assert not result.get("error")
    assert len(calls) == 1
    assert result["blocks"]
    assert result["action"] == "answer"
    assert result["scope"] and result["reply"]
    assert runtime.command("list_runs", *SCOPE) == []
    assert runtime.investigation_runs == 0
    assert not runtime.automatic


def test_case_trace_and_decision_survive_restart(runtime):
    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]["id"]
    report = runtime.begin_run(*SCOPE, seed_event_id=seed, max_calls=8).result(10)
    run_id = report["run_id"]
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
    assert runtime.command("analyst_history", *SCOPE, run_id)
    state_dir = runtime.state_dir
    runtime.close()
    restored = DemoRuntime(state_dir, load_fixtures=False, practice=True)
    try:
        assert restored.command("analyst_history", *SCOPE, run_id)
        answer = restored.begin_chat("Summarize that investigation", run_id).result(5)
        assert run_id in answer["scope"]
        assert "is completed" in answer["reply"]
        assert (
            answer["blocks"]
            and "Intent and endpoint activity are not available" not in answer["reply"]
        )
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
    assert displayed[0]["id"] in terminal.last_result["citations"]
    assert "no new investigation" in output[-1].lower()
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
    assert answer["coverage"]["delivered"] <= 2
    assert not runtime.command("list_runs", *SCOPE)
    missing = runtime.begin_chat("/summary missing-run").result(5)
    assert missing["error"] and "unavailable" in missing["reply"]


def test_timeout_trace_and_saved_summary_remain_readonly(runtime):
    def transport(*args):
        raise TimeoutError("Synthetic model timeout")

    runtime.configure_provider(
        AgentModelProvider(
            ModelProfile("http://localhost/v1/chat/completions", "mock-timeout"),
            transport,
        )
    )
    seed = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[-1]["id"]
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
    assert "is failed" in answer["reply"]
    assert answer["error"]
    assert answer["blocks"][0]["title"] == "Model unavailable"
    assert answer["citations"][0] == seed
    assert len(answer["citations"]) <= 4
    assert runtime.investigation_runs == 1
    assert saved["status"] == "FAILED"


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
    first = runtime.command("list_alerts", *SCOPE, runtime.command("snapshot"))[0]
    report = runtime.begin_run(*SCOPE, seed_event_id=first["id"], max_calls=8).result(5)
    old = ViewContext(page="Terminal", run_id=report["run_id"], evidence_id=first["id"])
    answer = read_answer(runtime, "summarize", "Summarize endpoint 203.0.113.250", old)
    assert answer["run_id"] is None
    assert "endpoint 203.0.113.250" in answer["scope"]
    assert answer["citations"] == []
    assert runtime.investigation_runs == 1


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
