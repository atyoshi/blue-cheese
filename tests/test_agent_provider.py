import json

import pytest

from bluecheese.adapters.agent_provider import AgentModelProvider, completion_endpoint
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.application.demo_runtime import DemoRuntime


def tool(name, args):
    return {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args),
                            },
                        }
                    ],
                },
            }
        ]
    }


def assessment(event_id, verdict="SUSPICIOUS"):
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "verdict": verdict,
                            "hypothesis": "An alert warrants review.",
                            "disconfirmation_test": "Examine flow counters.",
                            "supporting_ids": [event_id],
                            "contradicting_ids": [],
                            "unresolved": ["Endpoint intent is unavailable."],
                            "claims": [
                                {
                                    "text": "A sensor alert is present.",
                                    "citations": [event_id],
                                }
                            ],
                        }
                    )
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def profile():
    return ModelProfile(
        "http://localhost:8080/v1/chat/completions",
        "investigator",
        api_key="test-secret",
    )


def test_agents_acquire_evidence_critic_revises_report_and_audit_is_saved(tmp_path):
    calls = []

    def transport(config, payload, timeout):
        calls.append(payload)
        assert timeout > 0
        assert "test-secret" not in json.dumps(payload)
        context = json.loads(payload["messages"][1]["content"])
        assert all(set(row) == {"id", "normalized"} for row in context["observations"])
        event_id = context["selected_seed_id"]
        if len(calls) == 1:
            return tool("search_events", {"event_type": "flow", "limit": 10})
        if len(calls) == 3:
            assert context["candidate"]["verdict"] == "SUSPICIOUS"
            return tool("get_event", {"event_id": event_id})
        assert payload["messages"][-1]["role"] == "tool"
        assert "raw_text" not in payload["messages"][-1]["content"]
        return assessment(event_id, "UNCERTAIN" if len(calls) == 4 else "SUSPICIOUS")

    runtime = DemoRuntime(tmp_path)
    try:
        provider = AgentModelProvider(profile(), transport, falsifier_model="critic")
        report = runtime.run(
            "suspicious", "clean", provider=provider, question="Did data move?"
        )
        assert report["run_status"] == "COMPLETED"
        assert report["verdict"] == "UNCERTAIN"
        assert report["falsifier"]["model_review"] == "completed"
        assert [c["model"] for c in calls] == [
            "investigator",
            "investigator",
            "critic",
            "critic",
        ]
        assert (
            json.loads(calls[0]["messages"][1]["content"])["question"]
            == "Did data move?"
        )
        assert report["provider_activity"]["attempts"] == 4
        assert report["provider_activity"]["turns"][0]["usage"]["total_tokens"] is None
        assert report["provider_activity"]["turns"][1]["usage"]["total_tokens"] == 30
        assert report["tool_activity"][-2]["role"] == "Investigator"
        assert report["tool_activity"][-1]["role"] == "Falsifier"
        saved = runtime.command("get_run", "suspicious", "clean", report["run_id"])
        assert saved["report"]["provider_activity"]["attempts"] == 4
        assert "test-secret" not in json.dumps(saved)
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "name,args",
    [
        ("shell", {"command": "whoami"}),
        ("list_alerts", {"limit": 1000}),
        ("search_events", {"event_type": "flow", "limit": 10, "variant": "poisoned"}),
        ("get_event", {"event_id": "other", "snapshot_id": "other"}),
    ],
)
def test_model_cannot_widen_scope_or_tool_authority(tmp_path, name, args):
    runtime = DemoRuntime(tmp_path)
    try:
        provider = AgentModelProvider(profile(), lambda *unused: tool(name, args))
        with pytest.raises(ValueError, match="tool"):
            runtime.run("suspicious", "clean", provider=provider)
        saved = runtime.command("list_runs", "suspicious", "clean")[0]
        assert saved["status"] == "FAILED"
    finally:
        runtime.close()


def test_invented_citation_is_rejected_before_critic(tmp_path):
    calls = []
    runtime = DemoRuntime(tmp_path)
    try:

        def transport(*unused):
            calls.append(1)
            return assessment("unseen-id")

        with pytest.raises(ValueError, match="unseen"):
            runtime.run(
                "suspicious", "clean", provider=AgentModelProvider(profile(), transport)
            )
        assert len(calls) == 1
    finally:
        runtime.close()


def test_cancellation_retains_attempt_and_stops_new_model_calls(tmp_path):
    runtime = DemoRuntime(tmp_path)
    try:

        def transport(*unused):
            runtime.cancel()
            return assessment("ignored")

        report = runtime.run(
            "suspicious", "clean", provider=AgentModelProvider(profile(), transport)
        )
        assert report["run_status"] == "CANCELLED"
        assert report["provider_activity"]["attempts"] == 1
        assert report["provider_activity"]["turns"][0]["status"] == "ERROR"
    finally:
        runtime.close()


def test_shared_tool_budget_stops_agent_loop(tmp_path):
    runtime = DemoRuntime(tmp_path)
    calls = []
    try:

        def transport(*unused):
            calls.append(1)
            return tool("list_alerts", {"limit": 1})

        report = runtime.run(
            "suspicious",
            "clean",
            max_calls=3,
            provider=AgentModelProvider(profile(), transport),
        )
        assert report["run_status"] == "INCOMPLETE"
        assert report["budget"]["calls"] == 3
        assert len(calls) == 1
    finally:
        runtime.close()


def test_connection_probe_tool_round_trip_and_json_mode():
    calls = []

    def transport(config, payload, timeout):
        calls.append(payload)
        if len(calls) == 1:
            assert payload["tool_choice"]["function"]["name"] == "get_event"
            return tool("get_event", {"event_id": "probe-alert"})
        assert payload["response_format"] == {"type": "json_object"}
        return assessment("probe-alert", "UNCERTAIN")

    provider = AgentModelProvider(profile(), transport, json_mode=True)
    assert provider.test_connection()["status"] == "passed"
    assert len(calls) == 2
    assert "test-secret" not in repr(profile())
    assert completion_endpoint("http://localhost:8080/v1/") == profile().endpoint
    assert completion_endpoint("http://localhost:8080") == profile().endpoint
    assert completion_endpoint(profile().endpoint) == profile().endpoint


def test_configuration_is_blocked_while_provider_is_in_use(tmp_path):
    runtime = DemoRuntime(tmp_path, load_fixtures=False)
    try:
        runtime.configure_provider(AgentModelProvider(profile()))
        runtime.run_lock.acquire()
        try:
            with pytest.raises(RuntimeError, match="Wait"):
                runtime.configure_provider(None)
            with pytest.raises(RuntimeError, match="Wait"):
                runtime.test_provider()
        finally:
            runtime.run_lock.release()
        runtime.configure_provider(None)
        assert runtime.provider is None
    finally:
        runtime.close()
