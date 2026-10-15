"""Budget, delivery and retention behavior with no network or real models."""

import json
import stat
from copy import deepcopy
from types import SimpleNamespace

import pytest
from test_agent_provider import assessment, profile, tool

from bluecheese.adapters.agent_provider import (
    AGENT_REPORT_SCHEMA,
    AgentModelProvider,
    bounded_observations,
    fact_catalog,
    investigator_ceiling,
    output_guide,
)
from bluecheese.adapters.rejected_output import RejectedOutputSink, content_hash
from bluecheese.agents.investigator import EvidenceTools
from bluecheese.application.demo_runtime import DemoRuntime


@pytest.mark.parametrize("cap", range(2, 13))
def test_allocation_preserves_final_reviews_at_every_supported_cap(tmp_path, cap):
    calls = []

    def transport(config, payload, timeout):
        calls.append(payload)
        context = json.loads(payload["messages"][1]["content"])
        budget = context["run_budget"]
        assert budget["global_calls_remaining"] == cap - len(calls) + 1
        assert budget["role_calls_remaining"] >= 1
        return assessment(context["selected_seed_id"])

    runtime = DemoRuntime(tmp_path)
    try:
        report = runtime.run(
            "suspicious",
            "clean",
            provider=AgentModelProvider(
                profile(), transport, max_attempts=cap, falsifier_model="reviewer"
            ),
        )
        activity = report["provider_activity"]
        assert activity["attempts"] == 2
        assert activity["investigator_call_ceiling"] == investigator_ceiling(cap)
        assert activity["stages"][1]["call_ceiling"] == cap - 1
        assert report["falsifier"]["model_review"] == "completed"
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "investigator_queries,falsifier_queries", [(2, 2), (3, 1), (1, 3)]
)
def test_complex_dependent_queries_fit_six_calls(
    tmp_path, investigator_queries, falsifier_queries
):
    counts = {"investigator": 0, "reviewer": 0}
    queries = {"investigator": investigator_queries, "reviewer": falsifier_queries}

    def transport(config, payload, timeout):
        role = payload["model"]
        counts[role] += 1
        context = json.loads(payload["messages"][1]["content"])
        if counts[role] <= queries[role]:
            assert "tools" in payload, (
                "Exploration was cut off before the dependent check"
            )
            if counts[role] == 1:
                return tool(
                    "find_related_events",
                    {
                        "seed_id": context["selected_seed_id"],
                        "event_types": ["flow"],
                        "limit": 2,
                    },
                )
            previous = json.loads(payload["messages"][-1]["content"])
            # The next query depends on evidence delivered by the preceding query.
            event_id = previous["observations"][0]["id"]
            return tool("get_event", {"event_id": event_id})
        # A role may finish early while tools are still offered; unused calls transfer.
        return assessment(context["selected_seed_id"], "UNCERTAIN")

    runtime = DemoRuntime(tmp_path)
    try:
        report = runtime.run(
            "suspicious",
            "clean",
            provider=AgentModelProvider(
                profile(), transport, falsifier_model="reviewer"
            ),
            max_calls=12,
        )
        assert report["run_status"] == "COMPLETED"
        assert report["provider_activity"]["attempts"] == 6
        assert report["falsifier"]["model_review"] == "completed"
    finally:
        runtime.close()


def test_output_guide_tracks_schema_bounds():
    schema = deepcopy(AGENT_REPORT_SCHEMA)
    schema["properties"]["claims"]["maxItems"] = 7
    guide = output_guide(schema)
    assert 'report.claims: {"type":"array","maxItems":7}' in guide
    assert 'report.claims[].limitations[]: {"type":"string","maxLength":128}' in guide
    assert 'report.claims[].facts: {"type":"array","maxItems":2}' in guide


def test_catalog_uses_actual_record_fields_and_exact_types():
    rows = [
        {
            "id": "dns",
            "normalized": {
                "event_type": "dns",
                "src_port": 53,
                "protocol_details": {"rrname": "example.test"},
            },
        },
        {
            "id": "http",
            "normalized": {
                "event_type": "http",
                "protocol_details": {"url": "/path", "response_length_bytes": 0},
            },
        },
    ]
    catalog = fact_catalog(rows)
    dns = {f["field"]: f["value"] for f in catalog[0]["facts"]}
    http = {f["field"]: f["value"] for f in catalog[1]["facts"]}
    assert "url" not in dns and "response_length_bytes" not in dns
    assert dns["src_port"] == 53 and type(dns["src_port"]) is int
    assert http["url"] == "/path" and http["response_length_bytes"] == 0


def test_catalog_and_observations_share_context_budget_and_keep_counterevidence():
    rows = {
        str(i): {
            "id": str(i),
            "normalized": {
                "event_type": "http",
                "protocol_details": {"url": "x" * 500},
            },
        }
        for i in range(30)
    }
    tools = SimpleNamespace(retrieved=rows, correlated_ids=set())
    delivered, coverage = bounded_observations(
        tools, ["29"], max_bytes=4096, with_catalog=True
    )
    assert delivered[0]["id"] == "29"
    assert (
        len(json.dumps(delivered).encode())
        + len(json.dumps(fact_catalog(delivered)).encode())
        <= 4096
    )
    assert coverage["omitted"] > 0
    with pytest.raises(RuntimeError, match="bounded model context"):
        bounded_observations(tools, list(rows), max_bytes=4096, with_catalog=True)


def test_retrieved_but_not_delivered_citation_is_rejected():
    store = SimpleNamespace(get_event=lambda *args: {"id": args[-1]})
    tools = EvidenceTools(store, "case", "variant", 1)
    tools.retrieved = {"shown": {}, "hidden": {}}
    tools.role = "Falsifier"
    tools.role_delivered = {"Falsifier": {"shown"}}
    tools.validate(["shown"], model_role="Falsifier")
    tools.validate(["hidden"])  # Software provenance is still retrieval-bound.
    with pytest.raises(ValueError, match="not delivered"):
        tools.validate(["hidden"], model_role="Falsifier")
    with pytest.raises(ValueError, match="unseen"):
        tools.validate(["invented"])


def metadata(candidate):
    return {
        "run_id": "run",
        "role": "Falsifier",
        "operation_id": "model-2",
        "candidate_sha256": content_hash(candidate),
        "request_sha256": "request",
        "schema_sha256": "schema",
        "rejection": "SCHEMA_ERROR",
        "validation_issue": "/claims",
    }


def test_retention_is_redacted_bounded_private_and_immutable(tmp_path):
    candidate = 'known-secret Bearer abc123 password="hidden" ' + "é" * 20000
    directory = tmp_path / "rejected-output"
    sink = RejectedOutputSink(directory, secrets=("known-secret",))
    result = sink(candidate, metadata(candidate))
    path = next(directory.iterdir())
    record = json.loads(path.read_text())
    assert result == {"status": "SAVED", "redacted": True, "truncated": True}
    assert (
        "known-secret" not in record["candidate"]
        and "abc123" not in record["candidate"]
    )
    assert "hidden" not in record["candidate"]
    assert len(record["candidate"].encode()) <= 16384
    assert record["candidate_sha256"] == content_hash(candidate)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    with pytest.raises(FileExistsError):
        sink(candidate, metadata(candidate))


@pytest.mark.parametrize("enabled", [False, True])
def test_rejected_candidate_retention_never_enters_saved_case(tmp_path, enabled):
    def fail_write(candidate, metadata):
        assert "test-secret" in candidate
        raise OSError("private-local-path")

    runtime = DemoRuntime(tmp_path)
    try:
        provider = AgentModelProvider(
            profile(),
            lambda *args: {
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '"test-secret"'}}
                ]
            },
            candidate_sink=fail_write if enabled else None,
        )
        with pytest.raises(ValueError, match="schema"):
            runtime.run("suspicious", "clean", provider=provider)
        saved = runtime.command("list_runs", "suspicious", "clean")[0]
        detail = runtime.command("get_run", "suspicious", "clean", saved["run_id"])
        activity = detail["provider_diagnostics"]
        assert activity["candidate_retention_enabled"] is enabled
        assert activity["turns"][0]["candidate_sha256"] == content_hash('"test-secret"')
        assert "test-secret" not in json.dumps(detail)
        assert "private-local-path" not in json.dumps(detail)
        assert (
            activity["turns"][0].get("retention") == {"status": "WRITE_FAILED"}
        ) is enabled
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "expire_during", ["provider", "validation", "retention", "none"]
)
def test_local_processing_obeys_cooperative_deadline(
    tmp_path, monkeypatch, expire_during
):
    from bluecheese.adapters import agent_provider
    from bluecheese.adapters.duckdb_store import EvidenceStore
    from bluecheese.agents.investigator import investigate

    now = [0.0]
    calls = []
    original_validate = agent_provider.validate_report

    def validate(report, tools):
        original_validate(report, tools)
        if expire_during == "validation":
            now[0] = 1801

    def retain(candidate, metadata):
        if expire_during == "retention":
            now[0] = 1801
        return {"status": "SAVED"}

    def transport(config, payload, timeout):
        calls.append(payload)
        assert timeout <= min(300, 1800 - now[0])
        context = json.loads(payload["messages"][1]["content"])
        now[0] += 1801 if expire_during == "provider" else 250
        if expire_during == "retention":
            return {
                "choices": [
                    {"finish_reason": "stop", "message": {"content": "invalid-json"}}
                ]
            }
        return assessment(context["selected_seed_id"])

    monkeypatch.setattr(agent_provider, "validate_report", validate)
    store = EvidenceStore(tmp_path / "evidence.duckdb")
    try:
        store.import_file("tests/fixtures/sample_eve.json", "live", "external")
        result = investigate(
            store,
            "live",
            "external",
            max_calls=12,
            max_seconds=1800,
            clock=lambda: now[0],
            provider=AgentModelProvider(profile(), transport, candidate_sink=retain),
        )
        if expire_during == "none":
            assert result["run_status"] == "COMPLETED"
            assert len(calls) == 2
        else:
            assert result["run_status"] == "INCOMPLETE"
            assert len(calls) == 1
            assert result["claims"] == []
        if expire_during != "provider":
            assert "validation_seconds" in result["provider_activity"]["turns"][0]
    finally:
        store.close()


def test_ceiling_denial_and_unavailable_correction_are_persisted(tmp_path):
    calls = []

    def transport(config, payload, timeout):
        calls.append(payload)
        context = json.loads(payload["messages"][1]["content"])
        if payload["model"] == "investigator":
            return tool("get_event", {"event_id": context["selected_seed_id"]})
        return assessment(context["selected_seed_id"])

    runtime = DemoRuntime(tmp_path)
    try:
        with pytest.raises(ValueError, match="before its final turn"):
            runtime.run(
                "suspicious",
                "clean",
                max_calls=12,
                provider=AgentModelProvider(
                    profile(), transport, falsifier_model="reviewer"
                ),
            )
        saved = runtime.command("list_runs", "suspicious", "clean")[0]
        activity = runtime.command("get_run", "suspicious", "clean", saved["run_id"])[
            "provider_diagnostics"
        ]
        assert len(calls) == 4
        assert activity["stages"][0]["exploration_denied"] == "ROLE_CALL_CEILING"
        assert all(turn["role"] == "Investigator" for turn in activity["turns"])
    finally:
        runtime.close()


@pytest.mark.parametrize("role", ["investigator", "reviewer"])
@pytest.mark.parametrize(
    "defect", ["facts", "limitations_type", "limitations_length", "url_binding"]
)
@pytest.mark.parametrize("repair", [False, True])
def test_both_roles_correct_once_or_reject(tmp_path, role, defect, repair):
    from test_decision_advice import model_response

    seen = {"investigator": 0, "reviewer": 0}
    retained = []

    def transport(config, payload, timeout):
        current = payload["model"]
        seen[current] += 1
        context = json.loads(payload["messages"][1]["content"])
        response = model_response(context)
        if current == role:
            if seen[current] == 2:
                assert "tools" not in payload
                assert "Output field guide" in payload["messages"][-1]["content"]
            if seen[current] == 1 or not repair:
                report = json.loads(response["choices"][0]["message"]["content"])
                claim = report["claims"][0]
                if defect == "facts":
                    claim["facts"] = [
                        {
                            "evidence_id": context["selected_seed_id"],
                            "field": "event_type",
                            "value": "alert",
                        }
                    ] * 3
                elif defect == "limitations_type":
                    claim["limitations"] = "wrong type"
                elif defect == "limitations_length":
                    claim["limitations"] = ["x" * 129]
                else:
                    # A valid retrieved alert ID has no URL. The binding must fail.
                    claim["facts"] = [
                        {
                            "evidence_id": context["selected_seed_id"],
                            "field": "url",
                            "value": "/unsupported",
                        }
                    ]
                response["choices"][0]["message"]["content"] = json.dumps(report)
        return response

    runtime = DemoRuntime(tmp_path)
    try:
        provider = AgentModelProvider(
            profile(),
            transport,
            falsifier_model="reviewer",
            candidate_sink=lambda candidate, metadata: (
                retained.append((candidate, metadata)) or {"status": "SAVED"}
            ),
        )
        if repair:
            report = runtime.run("suspicious", "clean", provider=provider)
            assert report["falsifier"]["model_review"] == "completed"
            assert seen[role] == 2 and len(retained) == 1
        else:
            with pytest.raises(ValueError):
                runtime.run("suspicious", "clean", provider=provider)
            assert seen[role] == 2 and len(retained) == 2
            if role == "investigator":
                assert seen["reviewer"] == 0
        assert all(
            record["role"].lower() == ("falsifier" if role == "reviewer" else role)
            for _, record in retained
        )
    finally:
        runtime.close()


def test_falsifier_retains_late_delivered_counterevidence_across_restart(
    tmp_path, monkeypatch
):
    from bluecheese.adapters import agent_provider

    runtime = DemoRuntime(tmp_path, load_fixtures=False)
    common = {
        "timestamp": "2026-01-01T12:00:00+00:00",
        "src_ip": "10.0.0.5",
        "dest_ip": "192.0.2.1",
        "src_port": 50000,
        "dest_port": 80,
        "proto": "TCP",
    }
    records = [
        {
            **common,
            "event_type": "alert",
            "flow_id": 1,
            "alert": {"signature": "Review", "severity": 2},
        },
        {
            **common,
            "event_type": "flow",
            "flow_id": 1,
            "flow": {
                "state": "established",
                "bytes_toserver": 50000,
                "bytes_toclient": 500,
            },
        },
        {
            **common,
            "event_type": "flow",
            "flow_id": 2,
            "flow": {"state": "closed", "bytes_toserver": 0, "bytes_toclient": 0},
        },
    ]
    ids = runtime.database.apply(
        lambda store: [
            store.insert("live", "external", "sensor", i, json.dumps(record).encode())
            for i, record in enumerate(records)
        ]
    )
    late_id = ids[2]
    original_bound = agent_provider.bounded_observations

    def omit_optional_background(tools, required_ids=(), **kwargs):
        rows, coverage = original_bound(tools, required_ids, **kwargs)
        assert late_id not in required_ids
        # Simulate disclosed context clipping, without changing the retrieval ledger.
        filtered = [row for row in rows if row["id"] != late_id]
        coverage["delivered"] = len(filtered)
        coverage["omitted"] = len(tools.retrieved) - len(filtered)
        coverage["background_ids"] = [
            i for i in coverage["background_ids"] if i != late_id
        ]
        return filtered, coverage

    monkeypatch.setattr(
        agent_provider, "bounded_observations", omit_optional_background
    )
    review_calls = []

    def transport(config, payload, timeout):
        context = json.loads(payload["messages"][1]["content"])
        assert late_id not in {row["id"] for row in context["observations"]}
        if payload["model"] == "reviewer":
            review_calls.append(payload)
            if len(review_calls) == 1:
                return tool("search_events", {"event_type": "flow", "limit": 10})
            delivered = json.loads(payload["messages"][-1]["content"])
            assert late_id in {row["id"] for row in delivered["observations"]}
            response = assessment(context["selected_seed_id"], "UNCERTAIN")
            report = json.loads(response["choices"][0]["message"]["content"])
            report["contradicting_ids"] = [late_id]
            report["unresolved"] = [
                "Separate successful and failed flow observations need reconciliation."
            ]
            response["choices"][0]["message"]["content"] = json.dumps(report)
            return response
        return assessment(context["selected_seed_id"])

    try:
        report = runtime.run(
            "live",
            "external",
            seed_event_id=ids[0],
            max_calls=12,
            provider=AgentModelProvider(
                profile(), transport, falsifier_model="reviewer"
            ),
        )
        assert report["contradicting_ids"] == [late_id]
        assert report["falsifier"]["model_review"] == "completed"
        run_id = report["run_id"]
    finally:
        runtime.close()
    restarted = DemoRuntime(tmp_path, load_fixtures=False)
    try:
        assert len(restarted.command("list_runs", "live", "external")) == 1
        saved = restarted.command("get_run", "live", "external", run_id)
        assert saved["report"]["contradicting_ids"] == [late_id]
    finally:
        restarted.close()
