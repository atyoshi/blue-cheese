import json
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import pytest

from bluecheese.adapters.model_provider import ModelProfile, StructuredModelProvider
from bluecheese.application.demo_runtime import DemoRuntime

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


@pytest.mark.parametrize(
    "remote,insecure", [(False, False), (False, True), (True, False)]
)
def test_remote_http_requires_both_opt_ins(remote, insecure):
    with pytest.raises(ValueError):
        ModelProfile(
            "http://grain.utep.edu:11434/v1/chat/completions",
            "model",
            allow_remote=remote,
            allow_insecure_http=insecure,
        )


def test_remote_http_explicit_opt_in_and_environment(monkeypatch):
    from bluecheese.adapters.model_provider import configured_provider

    endpoint = "http://grain.utep.edu:11434/v1/chat/completions"
    profile = ModelProfile(
        endpoint, "model", allow_remote=True, allow_insecure_http=True
    )
    assert profile.endpoint == endpoint
    assert ModelProfile(
        "https://example.com/v1/chat/completions", "model", allow_remote=True
    )
    monkeypatch.setenv("BLUECHEESE_MODEL_ENDPOINT", endpoint)
    monkeypatch.setenv("BLUECHEESE_MODEL", "model")
    monkeypatch.setenv("BLUECHEESE_ALLOW_REMOTE_MODEL", "true")
    monkeypatch.delenv("BLUECHEESE_ALLOW_INSECURE_HTTP", raising=False)
    with pytest.raises(ValueError, match="allow_insecure_http"):
        configured_provider()
    monkeypatch.setenv("BLUECHEESE_ALLOW_INSECURE_HTTP", "true")
    assert configured_provider().profile == profile


@pytest.mark.parametrize(
    "failure,expected",
    [
        (TimeoutError(), "timed out \\(configured limit: 20 seconds\\)"),
        (URLError(TimeoutError()), "timed out \\(configured limit: 20 seconds\\)"),
        (URLError("private error details"), "connection failed"),
    ],
)
def test_transport_distinguishes_timeouts_without_leaking_details(
    monkeypatch, failure, expected
):
    from bluecheese.adapters.model_provider import request_completion

    class Opener:
        def open(self, *args, **kwargs):
            raise failure

    monkeypatch.setattr(
        "bluecheese.adapters.model_provider.build_opener", lambda *a: Opener()
    )
    with pytest.raises(RuntimeError, match=expected) as caught:
        request_completion(
            ModelProfile("http://localhost/v1/chat/completions", "test"), {}, 20
        )
    assert "private error details" not in str(caught.value)


@pytest.mark.parametrize("thinking", [None, False, True])
def test_thinking_extension_is_explicit_and_does_not_mutate_payload(
    monkeypatch, thinking
):
    from bluecheese.adapters.model_provider import request_completion

    sent = []

    class Opener:
        def open(self, request, **kwargs):
            sent.append(json.loads(request.data))
            return BytesIO(b"{}")

    monkeypatch.setattr(
        "bluecheese.adapters.model_provider.build_opener", lambda *a: Opener()
    )
    payload = {"messages": []}
    request_completion(
        ModelProfile(
            "http://localhost/v1/chat/completions", "test", enable_thinking=thinking
        ),
        payload,
        20,
    )
    assert payload == {"messages": []}
    if thinking is None:
        assert "chat_template_kwargs" not in sent[0]
    else:
        assert sent[0]["chat_template_kwargs"] == {"enable_thinking": thinking}


def test_slow_inference_timeout_stays_bounded():
    assert (
        ModelProfile(
            "http://localhost/v1/chat/completions", "test", timeout=300
        ).timeout
        == 300
    )
    with pytest.raises(ValueError, match="timeout"):
        ModelProfile("http://localhost/v1/chat/completions", "test", timeout=601)


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
