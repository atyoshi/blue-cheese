import json
from pathlib import Path

import pytest

from bluecheese.adapters.model_provider import ModelProfile, StructuredModelProvider
from bluecheese.application.demo_runtime import DemoRuntime

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


def transport(profile, payload, timeout):
    assert timeout > 0
    assert payload["response_format"]["json_schema"]["strict"]
    assert not payload["store"]
    context = json.loads(payload["messages"][1]["content"])
    assert all("raw" not in row for row in context["observations"])
    event_id = context["observations"][0]["id"]
    report = {
        "verdict": "UNCERTAIN",
        "hypothesis": "An alert was observed.",
        "disconfirmation_test": "Examine related flows.",
        "supporting_ids": [event_id],
        "contradicting_ids": [],
        "unresolved": ["Endpoint activity unavailable."],
        "claims": [{"text": "Sensor alert observed.", "citations": [event_id]}],
    }
    return {
        "choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps(report)}}
        ]
    }


def test_structured_provider_is_connected_to_real_broker_and_rejects_invented_ids(
    tmp_path,
):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    profile = ModelProfile(
        "http://127.0.0.1:8080/v1/chat/completions", "configured-local-model"
    )
    try:
        runtime.start(path=FIXTURE, replay=False, interval=3600)
        runtime.stop()
        provider = StructuredModelProvider(profile, transport)
        report = runtime.run("live", "external", provider=provider)
        assert report["provider_activity"]["attempts"] == 1
        assert report["claims"][0]["support_status"] == "UNASSESSED"
        assert report["falsifier"]["status"] == "not available"

        def invented(*args):
            response = transport(*args)
            content = json.loads(response["choices"][0]["message"]["content"])
            content["supporting_ids"] = ["invented"]
            response["choices"][0]["message"]["content"] = json.dumps(content)
            return response

        with pytest.raises(ValueError, match="unseen"):
            runtime.run(
                "live", "external", provider=StructuredModelProvider(profile, invented)
            )
        assert runtime.command("list_runs", "live", "external")[0]["status"] == "FAILED"
    finally:
        runtime.close()


def test_remote_opt_in_profile_limits_and_provider_failure_persist(tmp_path):
    with pytest.raises(ValueError, match="allow_remote"):
        ModelProfile("https://example.com/v1/chat/completions", "model")
    with pytest.raises(ValueError, match="allow_remote"):
        ModelProfile(
            "http://example.com/v1/chat/completions", "model", allow_remote=True
        )
    with pytest.raises(ValueError, match="timeout"):
        ModelProfile("http://localhost/completions", "model", timeout=float("inf"))
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        runtime.start(path=FIXTURE, replay=False, interval=3600)
        runtime.stop()

        def unavailable(*args):
            raise RuntimeError("Provider unavailable")

        provider = StructuredModelProvider(
            ModelProfile("http://localhost/completions", "model"), unavailable
        )
        with pytest.raises(RuntimeError, match="unavailable"):
            runtime.run("live", "external", provider=provider)
        saved = runtime.command(
            "get_run",
            "live",
            "external",
            runtime.command("list_runs", "live", "external")[0]["run_id"],
        )
        assert saved["status"] == "FAILED"
        assert saved["tool_activity"]
    finally:
        runtime.close()
