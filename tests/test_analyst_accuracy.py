"""Reviewed factual regressions; no network and no real model or LLM judge."""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.agents.findings import protocol_observations, validate_facts
from bluecheese.agents.investigator import EvidenceTools, investigate
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.presentation import LEGACY_GUIDANCE, report_presentation
from bluecheese.application.view_context import ViewContext

SCOPE = ("live", "external")
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/analyst_accuracy.json").read_text()
)


@pytest.fixture
def evidence(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.duckdb")
    ids = [
        store.insert(*SCOPE, "sensor", i, json.dumps(record).encode())
        for i, record in enumerate(FIXTURE["records"])
    ]
    yield store, ids
    store.close()


def complete(report):
    return {
        "choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps(report)}}
        ]
    }


def assessment(event_id):
    return {
        "verdict": "UNCERTAIN",
        "hypothesis": "The sensor matched the selected connection.",
        "disconfirmation_test": "Check matching flow records.",
        "supporting_ids": [event_id],
        "contradicting_ids": [],
        "unresolved": ["The purpose of this specific connection remains unconfirmed."],
        "claims": [{"text": "A sensor alert exists.", "citations": [event_id]}],
    }


def test_reviewed_http_facts_preserve_record_associations_and_response_semantics(
    evidence,
):
    store, ids = evidence
    rows = store.search_events(*SCOPE, store.snapshot(), "http")
    actual = protocol_observations(rows)
    assert [
        {key: row[key] for key in expected}
        for row, expected in zip(actual, FIXTURE["expected_http"], strict=True)
    ] == FIXTURE["expected_http"]
    assert [row["evidence_id"] for row in actual] == ids[1:3]
    assert (
        datetime.fromisoformat(actual[1]["timestamp"]).timestamp()
        == datetime.fromisoformat("2026-09-24T22:39:10+00:00").timestamp()
    )
    assert all("upload_bytes" not in row for row in actual)


@pytest.mark.parametrize(
    "field,value",
    [
        ("http_method", "POST"),
        ("status", 200),
        ("response_length_bytes", 45),
        ("timestamp", "2026-09-24T22:39:10-06:00"),
        ("src_ip", "192.0.2.99"),
        ("url", "/api/credentials"),
        ("dest_port", "8133"),
    ],
)
def test_true_citation_with_incorrect_fact_is_rejected(evidence, field, value):
    store, ids = evidence
    tools = EvidenceTools(store, *SCOPE, store.snapshot())
    tools.call("get_event", event_id=ids[2])
    claim = {
        "text": "An observable field is asserted.",
        "citations": [ids[2]],
        "facts": [{"evidence_id": ids[2], "field": field, "value": value}],
    }
    with pytest.raises(ValueError, match="Source fact conflicts"):
        validate_facts({"claims": [claim]}, tools)


def test_correct_source_fact_and_retrieval_required(evidence):
    store, ids = evidence
    tools = EvidenceTools(store, *SCOPE, store.snapshot())
    claim = {
        "text": "A GET response switched protocols.",
        "citations": [ids[2]],
        "facts": [{"evidence_id": ids[2], "field": "status", "value": 101}],
    }
    with pytest.raises(ValueError, match="unseen citation"):
        validate_facts({"claims": [claim]}, tools)
    tools.call("get_event", event_id=ids[2])
    validate_facts({"claims": [claim]}, tools)
    claim["citations"] = [ids[1]]
    with pytest.raises(ValueError, match="own observation"):
        validate_facts({"claims": [claim]}, tools)


def test_targeted_retrieval_filters_before_row_and_byte_limits(evidence):
    store, ids = evidence
    # Use another source scope with many early, large unrelated alerts.
    alert = FIXTURE["records"][0]
    for i in range(30):
        record = {
            **alert,
            "flow_id": 1000 + i,
            "src_port": 44000 + i,
            "payload": "x" * 8000,
        }
        store.insert("noise", "external", "sensor", i, json.dumps(record).encode())
    scoped_ids = [
        store.insert("noise", "external", "sensor", i + 50, json.dumps(record).encode())
        for i, record in enumerate(FIXTURE["records"])
    ]
    tools = EvidenceTools(store, "noise", "external", store.snapshot())
    assert tools.call("find_events_by_ip", ip=alert["src_ip"], limit=100)
    assert tools.activity[-1]["truncated"]
    rows = tools.call(
        "find_related_events", seed_id=scoped_ids[0], event_types=["flow"], limit=1
    )
    assert [r["id"] for r in rows] == [scoped_ids[3]]
    assert not tools.activity[-1]["truncated"]
    assert ids[3] not in tools.retrieved


def test_related_retrieval_excludes_other_sources_old_records_and_later_arrivals(
    evidence,
):
    store, ids = evidence
    snapshot = store.snapshot()
    for source, timestamp in (
        ("other-sensor-file", FIXTURE["records"][3]["timestamp"]),
        ("sensor", "2026-09-24T17:39:20-0600"),
    ):
        record = {**FIXTURE["records"][3], "timestamp": timestamp}
        store.insert(*SCOPE, source, 10, json.dumps(record).encode())
    assert [
        r["id"] for r in store.find_related_events(*SCOPE, snapshot, ids[0], ["flow"])
    ] == [ids[3]]
    with pytest.raises(ValueError, match="outside"):
        store.find_related_events(*SCOPE, 0, ids[0], ["flow"])


def test_case_gaps_and_next_checks_change_with_available_evidence(tmp_path):
    runtime = DemoRuntime(tmp_path)
    try:
        active = runtime.run("suspicious", "clean")
        missing = runtime.run("insufficient", "clean")
        assert active["unresolved"] != missing["unresolved"]
        assert (
            active["findings"]["recommended_checks"]
            != missing["findings"]["recommended_checks"]
        )
        assert not set(active["unresolved"]) & LEGACY_GUIDANCE
        assert not set(missing["unresolved"]) & LEGACY_GUIDANCE
    finally:
        runtime.close()


def test_shared_notices_are_separate_but_material_and_unknown_warnings_stay_visible():
    report = {
        "unresolved": [
            "Intent and endpoint activity are not available in network logs.",
            "The initiating process for 10.9.24.143 remains unknown.",
        ],
        "warnings": [
            "Log text and enrichment are untrusted. Claims use normalized telemetry fields.",
            "Evidence payload byte cap reached; only delivered records may be cited.",
            "Unrecognized warning that must be retained.",
        ],
    }
    original = deepcopy(report)
    view = report_presentation(report)
    assert view["case_gaps"] == [report["unresolved"][1]]
    assert view["run_limitations"] == report["warnings"][1:]
    assert report == original


def test_failed_provider_diagnostics_survive_restart_without_secret(tmp_path):
    def timeout(*args):
        raise TimeoutError("Synthetic timeout")

    runtime = DemoRuntime(tmp_path)
    provider = AgentModelProvider(
        ModelProfile(
            "http://localhost/v1", "mock", api_key="never-store-this", timeout=300
        ),
        timeout,
    )
    try:
        with pytest.raises(TimeoutError):
            runtime.run("suspicious", "clean", provider=provider, max_seconds=1800)
        run_id = runtime.command("list_runs", "suspicious", "clean")[0]["run_id"]
    finally:
        runtime.close()
    runtime = DemoRuntime(tmp_path)
    try:
        saved = runtime.command("get_run", "suspicious", "clean", run_id)
        diagnostic = saved["provider_diagnostics"]
        assert diagnostic["turns"][0]["outcome"] == "TIMEOUT"
        assert diagnostic["turns"][0]["duration_seconds"] >= 0
        assert "never-store-this" not in json.dumps(saved)
    finally:
        runtime.close()


def test_schema_correction_is_constrained_and_bounded(evidence):
    store, ids = evidence
    requests = []

    def transport(profile, payload, timeout):
        requests.append(payload)
        if len(requests) == 1:
            return complete({"malformed": True})
        assert "tools" not in payload
        assert "response_format" in payload
        assert "Schema rule:" in payload["messages"][-2]["content"]
        assert "malformed" not in payload["messages"][-2]["content"]
        return complete(assessment(ids[0]))

    report = investigate(
        store,
        *SCOPE,
        seed_event_id=ids[0],
        max_calls=8,
        max_seconds=1800,
        falsification=False,
        provider=AgentModelProvider(
            ModelProfile("http://localhost/v1", "mock", timeout=300),
            transport,
            max_attempts=4,
        ),
    )
    assert report["run_status"] == "COMPLETED"
    assert len(requests) == 2
    assert report["provider_activity"]["turns"][0]["validation"] == "SCHEMA_ERROR"
    assert report["provider_activity"]["turns"][0]["validation_issue"].startswith(
        "Schema rule: /"
    )


def test_invalid_citation_is_not_repaired_by_another_model_request(evidence):
    store, _ids = evidence
    requests = []

    def transport(profile, payload, timeout):
        requests.append(payload)
        return complete(assessment("not-retrieved"))

    with pytest.raises(ValueError, match="citation"):
        investigate(
            store,
            *SCOPE,
            max_calls=8,
            provider=AgentModelProvider(
                ModelProfile("http://localhost/v1", "mock"), transport
            ),
        )
    assert len(requests) == 1


def test_whole_case_chat_clears_incidental_selection_and_preserves_plain_history(
    tmp_path,
):
    runtime = DemoRuntime(tmp_path, load_fixtures=False)
    ids = [
        runtime.command("insert", *SCOPE, "sensor", i, json.dumps(record).encode())
        for i, record in enumerate(FIXTURE["records"])
    ]
    report = runtime.run(*SCOPE, seed_event_id=ids[0], max_calls=8)
    contexts = []

    def transport(profile, payload, timeout):
        context = json.loads(payload["messages"][1]["content"].partition(": ")[2])
        contexts.append(context)
        assert timeout == 300
        assert "analyst assistant" in payload["messages"][0]["content"]
        if len(contexts) == 2:
            history = [m for m in payload["messages"][2:-1] if m["role"] == "assistant"]
            assert history and '"action"' not in history[0]["content"]
        return complete(
            {
                "action": "answer",
                "argument": "",
                "reply": "",
                "blocks": [
                    {
                        "title": "",
                        "kind": "paragraph",
                        "items": [
                            "The selected sensor alert warrants checking the connection's purpose."
                        ],
                    }
                ],
                "citations": [ids[0]],
            }
        )

    try:
        runtime.configure_provider(
            AgentModelProvider(
                ModelProfile("http://localhost/v1", "mock", timeout=300), transport
            )
        )
        view = ViewContext(run_id=report["run_id"], evidence_id=ids[2])
        first = runtime.begin_chat(
            "Summarize this case with natural language", report["run_id"], view
        ).result(5)
        assert first["blocks"] and not first.get("error")
        assert contexts[0]["view_context"]["evidence_id"] == ""
        assert len(contexts[0]["observations"]) > 1
        runtime.begin_chat("What should I check next?", report["run_id"], view).result(
            5
        )
        assert runtime.investigation_runs == 1
    finally:
        runtime.close()


def test_network_paths_and_response_sizes_do_not_become_compromise_or_theft(evidence):
    store, ids = evidence
    report = investigate(store, *SCOPE, seed_event_id=ids[0], max_calls=8)
    assert report["findings"]["observed_impact"]["status"] == "UNCONFIRMED"
    prose = " ".join([report["hypothesis"], *[c["text"] for c in report["claims"]]])
    for unsupported in FIXTURE["forbidden_conclusions"]:
        assert unsupported not in prose
    assert report["qualifiers"]["endpoint_compromise"] != "SUPPORTED"


def test_utc_projection_is_explicit_and_does_not_change_stored_time(evidence):
    from bluecheese.domain.models import model_observation

    store, ids = evidence
    row = store.get_event(*SCOPE, store.snapshot(), ids[2])
    original = deepcopy(row)
    projected = model_observation(row)["normalized"]
    assert projected["timestamp_utc"] == "2026-09-24T22:39:10+00:00"
    assert projected["timestamp"] == "2026-09-24T16:39:10-0600"
    assert row == original


def test_empty_citation_final_can_use_one_reserved_correction(evidence):
    from test_agent_provider import tool

    store, ids = evidence
    requests = []

    def transport(profile, payload, timeout):
        requests.append(payload)
        if len(requests) <= 2:
            return tool("get_event", {"event_id": ids[0]})
        report = assessment(ids[0])
        if len(requests) == 3:
            report["claims"][0]["citations"] = []
        return complete(report)

    report = investigate(
        store,
        *SCOPE,
        seed_event_id=ids[0],
        max_calls=12,
        max_seconds=1800,
        provider=AgentModelProvider(
            ModelProfile("http://localhost/v1", "mock"), transport
        ),
    )
    assert len(requests) == 5
    assert report["falsifier"]["model_review"] == "completed"
    assert report["provider_activity"]["turns"][2]["validation"] == "SCHEMA_ERROR"
    assert "response_format" in requests[3]
    assert "tools" not in requests[3]


def test_reading_model_schema_cannot_propose_actions(tmp_path):
    runtime = DemoRuntime(tmp_path, load_fixtures=False)
    try:

        def transport(profile, payload, timeout):
            assert payload["response_format"] == {"type": "json_object"}
            assert '"enum": ["answer"]' in payload["messages"][0]["content"]
            return complete(
                {
                    "action": "answer",
                    "argument": "",
                    "reply": "No investigation is running.",
                    "citations": [],
                }
            )

        runtime.configure_provider(
            AgentModelProvider(ModelProfile("http://localhost/v1", "mock"), transport)
        )
        for question in (
            "What should I check next?",
            "What is going on right now?",
            "Summarize with natural language",
        ):
            answer = runtime.begin_chat(question).result(5)
            assert not answer.get("error")

        def invalid_action(*_):
            return complete(
                {
                    "action": "investigate",
                    "argument": "",
                    "reply": "Unrequested action",
                    "citations": [],
                }
            )

        runtime.configure_provider(
            AgentModelProvider(
                ModelProfile("http://localhost/v1", "mock"), invalid_action
            )
        )
        rejected = runtime.begin_chat("Summarize with natural language").result(5)
        assert rejected["error"] and rejected["error_kind"] == "validation"
        assert runtime.investigation_runs == 0
    finally:
        runtime.close()


def test_unrelated_source_incident_does_not_become_a_case_warning(evidence):
    store, ids = evidence
    run = store.create_run(*SCOPE, "Review target", seed_event_id=ids[0])
    store.record_source_incident("another-file", 0, "Unrelated source gap")
    store.record_source_incident("sensor", 0, "This source gap affects the case")
    incidents = store.case_source_incidents(run["snapshot_id"])
    assert [item["diagnostic"] for item in incidents] == [
        "This source gap affects the case"
    ]


def test_incomplete_output_retains_returned_usage_and_finish_reason(tmp_path):
    def transport(*args):
        return {
            "choices": [{"finish_reason": "length", "message": {"content": "{"}}],
            "usage": {
                "prompt_tokens": 42,
                "completion_tokens": 2048,
                "total_tokens": 2090,
            },
        }

    runtime = DemoRuntime(tmp_path)
    try:
        with pytest.raises(ValueError, match="incomplete"):
            runtime.run(
                "suspicious",
                "clean",
                provider=AgentModelProvider(
                    ModelProfile("http://localhost/v1", "mock"), transport
                ),
            )
        run_id = runtime.command("list_runs", "suspicious", "clean")[0]["run_id"]
        saved = runtime.command("get_run", "suspicious", "clean", run_id)
        turn = saved["provider_diagnostics"]["turns"][0]
        assert turn["finish_reason"] == "length"
        assert turn["usage"]["completion_tokens"] == 2048
        assert turn["status"] == "ERROR"
    finally:
        runtime.close()


def test_claim_constraints_do_not_alias_unresolved_or_contradicting_ids():
    from jsonschema import validate
    from test_decision_advice import model_response

    from bluecheese.adapters.agent_provider import AGENT_REPORT_SCHEMA

    report = json.loads(
        model_response({"selected_seed_id": "actual-id"})["choices"][0]["message"][
            "content"
        ]
    )
    report.pop("verdict")
    report["unresolved"] = []
    report["contradicting_ids"] = []
    validate(report, AGENT_REPORT_SCHEMA)
    report["claims"][0]["citations"] = []
    from jsonschema import ValidationError

    with pytest.raises(ValidationError):
        validate(report, AGENT_REPORT_SCHEMA)


def test_incorrect_field_association_fails_the_full_model_pipeline(evidence):
    from test_decision_advice import model_response

    store, ids = evidence
    requests = []

    def transport(profile, payload, timeout):
        requests.append(payload)
        report = json.loads(
            model_response({"selected_seed_id": ids[0]})["choices"][0]["message"][
                "content"
            ]
        )
        report["claims"][0].update(
            text="The shell agent used POST.",
            citations=[ids[2]],
            facts=[{"evidence_id": ids[2], "field": "http_method", "value": "POST"}],
        )
        return complete(report)

    with pytest.raises(ValueError, match="Source fact conflicts"):
        investigate(
            store,
            *SCOPE,
            seed_event_id=ids[0],
            max_calls=8,
            provider=AgentModelProvider(
                ModelProfile("http://localhost/v1", "mock"), transport
            ),
        )
    assert len(requests) == 2


def test_coverage_window_uses_portable_utc_timestamps(evidence):
    store, _ids = evidence
    coverage = store.telemetry_coverage(*SCOPE, store.snapshot())
    assert coverage["time_window"] == [
        "2026-09-24T22:38:45+00:00",
        "2026-09-24T22:39:20+00:00",
    ]
    assert coverage["accepted_types"] == {"alert": 1, "http": 2, "flow": 1}


def test_model_context_prioritizes_cited_evidence_and_discloses_omissions():
    from types import SimpleNamespace

    from bluecheese.adapters.agent_provider import bounded_observations

    rows = {
        str(i): {
            "id": str(i),
            "normalized": {
                "event_type": "http",
                "protocol_details": {"url": "x" * 2000},
            },
        }
        for i in range(100)
    }
    tools = SimpleNamespace(retrieved=rows, correlated_ids={"99"})
    observations, coverage = bounded_observations(tools, ["99"])
    assert observations[0]["id"] == "99"
    assert coverage["omitted"] > 0
    assert len(json.dumps(observations).encode()) <= 32768
    assert len(rows) == 100


def test_empty_optional_blocks_preserve_prose_and_response_bounds():
    from bluecheese.application.presentation import with_blocks

    answer = with_blocks(
        {"reply": "A useful paragraph.\n\n- First check\n- Second check", "blocks": []}
    )
    assert answer["blocks"][0]["kind"] == "paragraph"
    assert answer["blocks"][1]["items"] == ["First check", "Second check"]
    assert "A useful paragraph." in answer["reply"]
    with pytest.raises(ValueError, match="response limit"):
        with_blocks(
            {"blocks": [{"title": "Title", "kind": "paragraph", "items": ["x" * 8192]}]}
        )


def test_historical_template_is_legible_without_rewriting_transcript():
    from bluecheese.application.presentation import chat_history_presentation

    reply = (
        "Observed sample: 1 alert(s), 0 flow record(s), 1 delivered record(s).\n"
        "Unknowns: Intent and endpoint activity are not available in network logs.; No established high-volume alerted flow observed.; Flow evidence needed to test the alternative explanation is unavailable.\n"
        "Coverage: at most 20 records per query and 6 queries; selection filters apply within that sample. This is not an exhaustive review.\n"
        "An alert is a sensor rule match in network traffic. It asks for review; it does not prove compromise. Severity is the sensor rule's review priority: 1 is high, 2 medium and 3 low. It is not a probability of compromise.\n"
        "Next: inspect the cited records and confirm authorization with the asset owner; endpoint process and identity logs are not connected. Record an analyst decision after review."
    )
    messages = [
        {"role": "assistant", "content": json.dumps({"reply": reply, "citations": []})}
    ]
    original = deepcopy(messages)
    display = chat_history_presentation(messages)[0]
    assert messages == original
    assert display["content"] == original[0]["content"]
    assert "logs.;" not in display["presentation"]["reply"]
    assert "Coverage: at most" not in display["presentation"]["reply"]
    assert display["presentation"]["blocks"][1]["items"] == [
        "No established high-volume alerted flow observed.",
        "Flow evidence needed to test the alternative explanation is unavailable.",
    ]


def test_missing_target_replaces_model_proposal_with_actionable_answer(tmp_path):
    runtime = DemoRuntime(tmp_path, load_fixtures=False)
    try:

        def transport(*args):
            return complete(
                {
                    "action": "investigate",
                    "argument": "New analysis",
                    "reply": "",
                    "citations": [],
                    "blocks": [
                        {
                            "title": "",
                            "kind": "paragraph",
                            "items": ["I propose investigating this target."],
                        }
                    ],
                }
            )

        runtime.configure_provider(
            AgentModelProvider(ModelProfile("http://localhost/v1", "mock"), transport)
        )
        reply = runtime.begin_chat("Please investigate this").result(5)
        assert reply["action"] == "answer"
        assert reply["reply"] == "Choose an alert before starting analysis."
        assert runtime.investigation_runs == 0
    finally:
        runtime.close()


def test_truncated_output_gets_one_constrained_correction_without_accepting_partial(
    evidence,
):
    store, ids = evidence
    requests = []

    def transport(profile, payload, timeout):
        requests.append(payload)
        if len(requests) == 1:
            return {
                "choices": [
                    {"finish_reason": "length", "message": {"content": "{partial"}}
                ]
            }
        assert "response_format" in payload and "tools" not in payload
        return complete(assessment(ids[0]))

    report = investigate(
        store,
        *SCOPE,
        seed_event_id=ids[0],
        max_calls=8,
        falsification=False,
        provider=AgentModelProvider(
            ModelProfile("http://localhost/v1", "mock"), transport
        ),
    )
    assert len(requests) == 2
    assert report["run_status"] == "COMPLETED"
    assert report["provider_activity"]["turns"][0]["finish_reason"] == "length"
    assert report["provider_activity"]["turns"][0]["status"] == "ERROR"
