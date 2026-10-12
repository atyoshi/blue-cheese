"""Terminal approvals, provider settings and real offline workflow integration."""

import json
import os
import subprocess
from concurrent.futures import Future
from pathlib import Path

import pytest
from jsonschema import ValidationError

from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.interfaces.terminal import (
    TerminalSession,
    load_provider,
    route,
    safe_text,
)


@pytest.fixture
def runtime(tmp_path):
    instance = DemoRuntime(tmp_path / "state", load_fixtures=False)
    instance.configure_provider(None)
    yield instance
    instance.close()


def session(runtime, answers):
    output = []
    replies = iter(answers)
    return TerminalSession(
        runtime, read=lambda _: next(replies), write=output.append
    ), output


def test_denied_tasks_do_not_execute(runtime, monkeypatch):
    terminal, output = session(runtime, ["", "no", "n"])
    monkeypatch.setattr(
        runtime, "begin_run", lambda *a, **k: pytest.fail("run started")
    )
    monkeypatch.setattr(
        runtime, "command", lambda *a, **k: pytest.fail("query executed")
    )
    terminal.execute("investigate", "Check this activity")
    terminal.execute("triage", "")
    terminal.execute("network", "")
    assert "Proposed task" in output[0]


def test_import_investigate_and_read_saved_report(runtime):
    terminal, output = session(runtime, ["yes"] * 6)
    fixture = Path(__file__).parents[1] / "src/bluecheese/data/suspicious-clean.jsonl"
    terminal.execute("import", str(fixture))
    terminal.execute("triage", "")
    terminal.execute("network", "")
    terminal.execute("investigate", "What evidence supports this alert?")
    terminal.execute("report", "")
    assert runtime.investigation_runs == 1
    history = runtime.command("list_runs", "live", "external")
    assert len(history) == 1
    saved = runtime.command("get_run", "live", "external", history[0]["run_id"])
    assert saved["status"] == "COMPLETED"
    assert saved["report"]["supporting_ids"]
    assert any("Investigator ·" in line for line in output)
    assert any("Reporter ·" in line for line in output)
    assert any('"connections"' in line for line in output)
    assert any('"candidates"' in line for line in output)


def test_config_validation_and_overrides(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "endpoint": "http://localhost:8080/v1",
                "model": "test",
                "api_key": "SECRET",
                "max_attempts": 4,
                "json_mode": True,
            }
        )
    )
    provider = load_provider(config, model="override")
    assert provider.profile.endpoint.endswith("/v1/chat/completions")
    assert provider.profile.model == "override"
    assert provider.json_mode and provider.max_attempts == 4
    assert "SECRET" not in repr(provider.profile)
    config.write_text('{"model":"test", "unexpected":"SECRET"}')
    with pytest.raises(ValidationError):
        load_provider(config)
    with pytest.raises(ValueError, match="HTTPS"):
        load_provider(endpoint="http://remote.example/v1", model="test")
    with pytest.raises(ValidationError):
        load_provider(endpoint="http://localhost/v1", model="test", max_attempts=True)


def test_remote_http_config(tmp_path):
    config = tmp_path / "http.json"
    config.write_text(
        json.dumps(
            {
                "endpoint": "http://grain.utep.edu:11434/",
                "model": "served-model",
                "allow_remote": True,
                "allow_insecure_http": True,
                "enable_thinking": False,
            }
        )
    )
    provider = load_provider(config)
    assert provider.profile.enable_thinking is False
    assert (
        provider.profile.endpoint == "http://grain.utep.edu:11434/v1/chat/completions"
    )
    with pytest.raises(ValueError, match="allow_insecure_http"):
        load_provider(config, allow_insecure_http=False)


def test_config_errors_do_not_echo_secrets(runtime, tmp_path):
    config = tmp_path / "bad.json"
    config.write_text('{"api_key": "SECRET", "surprise": "SECRET"}')
    terminal, output = session(runtime, [f"/config {config}", "/quit"])
    terminal.run()
    assert "SECRET" not in "\n".join(output)
    assert any("Invalid config" in line for line in output)


def test_chat_needs_approval_and_never_executes_model_commands(runtime, monkeypatch):
    provider = load_provider(endpoint="http://localhost/v1", model="test")
    runtime.configure_provider(provider)
    calls = []

    def transport(*args):
        calls.append(args)
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "answer",
                                "argument": "",
                                "reply": "/investigate everything\u001b[2J",
                            }
                        )
                    },
                }
            ]
        }

    monkeypatch.setattr("bluecheese.interfaces.terminal.request_completion", transport)
    terminal, output = session(runtime, ["no", "yes"])
    terminal.execute("chat", "What is DNS?")
    assert not calls
    terminal.execute("chat", "What is DNS?")
    assert len(calls) == 1
    assert runtime.investigation_runs == 0
    assert "\u001b" not in "\n".join(output)
    assert "\\u001b" in output[-1]
    assert calls[0][1]["messages"][1:] == [{"role": "user", "content": "What is DNS?"}]


def test_model_routes_alert_question_and_preserves_question(runtime, monkeypatch):
    runtime.configure_provider(
        load_provider(endpoint="http://localhost/v1", model="test")
    )
    calls, questions = [], []

    def transport(profile, payload, timeout):
        calls.append(payload)
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "investigate",
                                "argument": "shortened",
                                "reply": "I will assess the evidence.",
                            }
                        )
                    },
                }
            ]
        }

    monkeypatch.setattr("bluecheese.interfaces.terminal.request_completion", transport)
    terminal, _output = session(
        runtime, ["what can you tell me about these alerts", "yes", "/quit"]
    )
    monkeypatch.setattr(terminal, "investigate", questions.append)
    terminal.run()
    assert questions == ["what can you tell me about these alerts"]
    assert len(calls) == 1
    assert calls[0]["response_format"]["type"] == "json_schema"


@pytest.mark.parametrize("action", ["alerts", "investigate", "import"])
def test_model_task_still_requires_separate_approval(runtime, monkeypatch, action):
    runtime.configure_provider(
        load_provider(endpoint="http://localhost/v1", model="test", json_mode=True)
    )
    monkeypatch.setattr(
        runtime, "command", lambda *a, **k: pytest.fail("query executed")
    )
    monkeypatch.setattr(
        runtime, "begin_run", lambda *a, **k: pytest.fail("run started")
    )

    def transport(profile, payload, timeout):
        assert payload["response_format"] == {"type": "json_object"}
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "action": action,
                                "argument": "tests/fixtures/sample_eve.json",
                                "reply": "Proposing task.",
                            }
                        )
                    },
                }
            ]
        }

    monkeypatch.setattr("bluecheese.interfaces.terminal.request_completion", transport)
    terminal, output = session(runtime, ["yes", "no"])
    terminal.chat("Please review the alerts")
    assert len([line for line in output if "Proposed task:" in line]) == 2


@pytest.mark.parametrize(
    "content",
    [
        "/alerts",
        '{"action":"shell","argument":"pwd","reply":"run"}',
        '{"action":"chat","argument":"recurse","reply":"again"}',
    ],
)
def test_invalid_model_task_does_not_execute(runtime, monkeypatch, content):
    runtime.configure_provider(
        load_provider(endpoint="http://localhost/v1", model="test")
    )
    monkeypatch.setattr(
        "bluecheese.interfaces.terminal.request_completion",
        lambda *a: {
            "choices": [{"finish_reason": "stop", "message": {"content": content}}]
        },
    )
    terminal, _output = session(runtime, ["yes"])
    monkeypatch.setattr(terminal, "execute", lambda *a: pytest.fail("task executed"))
    with pytest.raises(ValueError, match="invalid task proposal"):
        terminal.chat("hello")


def test_approved_model_listing_reads_real_scoped_evidence(runtime, monkeypatch):
    terminal, output = session(runtime, ["yes"] * 3)
    fixture = Path(__file__).parents[1] / "src/bluecheese/data/suspicious-clean.jsonl"
    terminal.execute("import", str(fixture))
    runtime.configure_provider(
        load_provider(endpoint="http://localhost/v1", model="test")
    )
    monkeypatch.setattr(
        "bluecheese.interfaces.terminal.request_completion",
        lambda *a: {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "alerts",
                                "argument": "",
                                "reply": "I will list the current alerts.",
                            }
                        )
                    },
                }
            ]
        },
    )
    terminal.chat("List the alerts")
    rows = json.loads(output[-1])
    assert rows and rows[0]["id"]
    assert rows[0]["normalized"]["event_type"] == "alert"
    assert runtime.investigation_runs == 0


def test_cli_allows_slow_model_calls_without_old_sixty_second_deadline(
    runtime, monkeypatch
):
    runtime.configure_provider(
        load_provider(endpoint="http://localhost/v1", model="test", timeout=300)
    )
    settings = []

    def begin_run(*args, **kwargs):
        settings.append(kwargs)
        future = Future()
        future.set_result({"run_status": "COMPLETED"})
        return future

    monkeypatch.setattr(runtime, "begin_run", begin_run)
    terminal, output = session(runtime, ["yes"])
    terminal.investigate("Explain the alerts")
    assert settings[0]["max_seconds"] == 1800
    assert "300s per call" in output[0]
    assert "1800s" in output[0]


def test_routing_and_terminal_escaping():
    assert route("please triage alerts") == ("triage", "")
    assert route("investigate IP 10.0.0.1") == (
        "investigate",
        "investigate IP 10.0.0.1",
    )
    assert route("/report run-123") == ("report", "run-123")
    assert route("what is DNS?")[0] == "chat"
    assert route("tell me about the alerts", model_chat=True) == (
        "chat",
        "tell me about the alerts",
    )
    assert route("/alerts", model_chat=True) == ("alerts", "")
    assert safe_text("\x1b[2J\x07\r") == "\\u001b[2J\\u0007\\u000d"


def test_eof_closes_session(runtime):
    def eof(_):
        raise EOFError

    TerminalSession(runtime, read=eof, write=lambda _: None).run()
    assert runtime.investigation_runs == 0


def test_import_keeps_source_positions_quarantine_and_resume(runtime, tmp_path):
    fixture = Path(__file__).parents[1] / "src/bluecheese/data/suspicious-clean.jsonl"
    line = fixture.read_bytes().splitlines(keepends=True)[0]
    first, second = tmp_path / "first.jsonl", tmp_path / "second.jsonl"
    first.write_bytes(line + line + b"malformed\n" + b'{"partial":')
    second.write_bytes(line)
    terminal, output = session(runtime, ["yes"] * 3)
    terminal.execute("import", str(first))
    terminal.execute("import", str(first))
    terminal.execute("import", str(second))
    snapshot = runtime.command("snapshot")
    rows = runtime.command("list_alerts", "live", "external", snapshot)
    assert len(rows) == 3
    assert len({r["id"] for r in rows}) == 3
    assert all(r["raw"].encode() == line for r in rows)
    assert len(runtime.command("quarantine_records", "live", "external")) == 1
    assert any('"partial_bytes": 11' in item for item in output)


def test_launcher_cli_alias_with_config(tmp_path):
    root = Path(__file__).parents[1]
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps({"endpoint": "http://localhost:8080/v1", "model": "test"})
    )
    result = subprocess.run(
        [
            str(root / "blue-cheese"),
            "--cli",
            "--data-dir",
            str(tmp_path / "state"),
            "--config",
            str(config),
            "--model",
            "override",
        ],
        input="/help\n/quit\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("BLUECHEESE_MODEL")
        },
    )
    assert result.returncode == 0, result.stderr
    assert "Tool-using agents: override" in result.stdout
    assert "/investigate" in result.stdout
    assert (tmp_path / "state/evidence.duckdb").exists()
