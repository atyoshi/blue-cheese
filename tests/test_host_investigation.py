"""Host investigation scope and recoverable model fact errors in the actual runtime."""

import json
import subprocess
import sys
import textwrap

import pytest

from bluecheese.adapters.agent_provider import AgentModelProvider
from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.adapters.model_provider import ModelProfile
from bluecheese.application.demo_runtime import DemoRuntime

SCOPE = ("live", "external")
BASE = {
    "timestamp": "2026-09-24T16:39:00-0600",
    "sensor_name": "sensor",
    "src_ip": "10.0.0.5",
    "src_port": 53000,
    "dest_ip": "192.0.2.53",
    "dest_port": 53,
    "proto": "UDP",
    "event_type": "alert",
    "flow_id": 1,
    "alert": {"signature": "Review DNS lookup", "severity": 3},
}


def http(method, path, destination="192.0.2.80"):
    return {
        **BASE,
        "event_type": "http",
        "dest_ip": destination,
        "dest_port": 80,
        "proto": "TCP",
        "flow_id": 2,
        "http": {"http_method": method, "url": path, "status": 200, "length": 8},
    }


def insert(store, record, position, source="sensor", scope=SCOPE):
    return store.insert(*scope, source, position, json.dumps(record).encode())


def test_large_host_snapshot_survives_commit_retrieval_and_restart(tmp_path):
    # Isolate native failures so a storage regression cannot terminate pytest.
    script = textwrap.dedent(
        """
        import json
        import sys
        from pathlib import Path
        from bluecheese.application.demo_runtime import DemoRuntime
        from bluecheese.application.report_bundle import export_bundle, verify_bundle

        root = Path(sys.argv[1])
        eve = root / "observations.jsonl"
        base = {
            "timestamp": "2026-01-01T12:00:00+00:00", "flow_id": 1,
            "src_ip": "10.0.0.5", "dest_ip": "192.0.2.1",
            "src_port": 53000, "dest_port": 80, "proto": "TCP",
        }
        with eve.open("w") as stream:
            for index in range(5500):
                record = {**base, "event_type": "alert" if index % 2 else "http"}
                record["alert"] = {"signature": "Review traffic", "severity": 2}
                record["http"] = {
                    "http_method": "POST", "status": 200, "length": index,
                    "url": "/opaque/" + str(index) + ("\\x00Ω" * 300),
                }
                stream.write(json.dumps(record) + "\\n")
        original = eve.read_bytes()
        runtime = DemoRuntime(root / "state", load_fixtures=False)
        runtime.configure_provider(None)
        try:
            runtime.command("import_file", eve, "live", "external")
            seed = runtime.command(
                "list_alerts", "live", "external", runtime.command("snapshot"), limit=1
            )[0]["id"]
            report = runtime.run(
                "live", "external", seed_event_id=seed,
                investigation_scope="host", max_calls=12, max_seconds=30,
            )
            saved = runtime.command("get_run", "live", "external", report["run_id"])
            assert saved["record_count"] == 5500
            assert saved["status"] == "COMPLETED"
            export_bundle(runtime, report, root / "bundle")
            assert verify_bundle(root / "bundle")["valid"]
        finally:
            runtime.close()
        runtime = DemoRuntime(root / "state", load_fixtures=False)
        try:
            saved = runtime.command("get_run", "live", "external", report["run_id"])
            assert saved["status"] == "COMPLETED" and saved["record_count"] == 5500
            runtime.command("import_file", eve, "live", "external")
            assert runtime.command("counts", "live", "external") == {
                "accepted": 5500, "invalid": 0,
            }
            row = runtime.command("get_event", "live", "external", 5500, seed)
            assert row["raw"].encode() == original.splitlines(keepends=True)[1]
        finally:
            runtime.close()
        assert eve.read_bytes() == original
        """
    )
    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", script, str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_host_snapshot_includes_cross_destination_context_and_preserves_boundaries(
    tmp_path,
):
    store = EvidenceStore(tmp_path / "evidence.duckdb")
    try:
        seed = insert(store, BASE, 0)
        download = insert(store, http("GET", "/download", "192.0.2.81"), 1)
        reporting = insert(store, http("POST", "/report"), 2)
        reverse = insert(
            store,
            {
                **http("POST", "/reply"),
                "src_ip": "192.0.2.80",
                "dest_ip": BASE["src_ip"],
            },
            3,
        )
        excluded = [
            insert(store, http("GET", "/other-source"), 4, source="other"),
            insert(
                store,
                {**http("GET", "/old"), "timestamp": "2026-09-24T15:00:00-0600"},
                5,
            ),
            insert(store, {**http("GET", "/other-host"), "src_ip": "10.0.0.6"}, 6),
            insert(store, http("GET", "/other-case"), 8, scope=("other", "external")),
        ]
        narrow = store.create_run(*SCOPE, "Review alert", seed_event_id=seed)
        host = store.create_run(
            *SCOPE, "Review alert", seed_event_id=seed, investigation_scope="host"
        )
        later = insert(store, http("POST", "/later"), 9)
        args = (*SCOPE, host["snapshot"], seed)
        rows = store.find_host_context(*args, snapshot_id=host["snapshot_id"])
        assert {r["id"] for r in rows} == {download, reporting, reverse}
        assert all(r["id"] not in excluded + [later] for r in rows)
        assert (
            store.find_host_context(
                *SCOPE, narrow["snapshot"], seed, snapshot_id=narrow["snapshot_id"]
            )
            == []
        )
        assert host["case_id"] != narrow["case_id"]
        saved = store.get_run(*SCOPE, host["run_id"])
        assert saved["investigation_scope"] == "host"
        assert saved["target_host"] == BASE["src_ip"]
        store.finish_run(host["run_id"], "FAILED", error="Test terminal state")
        with pytest.raises(ValueError, match="Parent run"):
            store.create_run(
                *SCOPE, "Review alert", parent_run_id=host["run_id"], seed_event_id=seed
            )
        revision = store.create_run(
            *SCOPE,
            "Review alert",
            parent_run_id=host["run_id"],
            seed_event_id=seed,
            investigation_scope="host",
        )
        assert revision["case_id"] == host["case_id"]
    finally:
        store.close()


def test_host_context_diversity_prevents_repeated_requests_hiding_other_behaviors(
    tmp_path,
):
    store = EvidenceStore(tmp_path / "evidence.duckdb")
    try:
        seed = insert(store, BASE, 0)
        for i in range(50):
            insert(store, http("POST", "/report"), i + 1)
        expected = [
            insert(store, http(method, path, destination), i + 100)
            for i, (method, path, destination) in enumerate(
                [
                    ("GET", "/download", "192.0.2.81"),
                    ("POST", "/api/credentials", "192.0.2.80"),
                    ("GET", "/api/shell/agent", "192.0.2.80"),
                ]
            )
        ]
        for i in range(50):
            record = {
                **BASE,
                "event_type": "dns",
                "dns": {
                    "type": "request",
                    "queries": [{"rrname": "example.test", "rrtype": "A"}],
                },
            }
            insert(store, record, i + 200)
        host = store.create_run(
            *SCOPE, "Review host", seed_event_id=seed, investigation_scope="host"
        )
        rows = store.find_host_context(
            *SCOPE, host["snapshot"], seed, limit=8, snapshot_id=host["snapshot_id"]
        )
        assert set(expected).issubset({r["id"] for r in rows})
        assert len(rows) == 8
    finally:
        store.close()


@pytest.mark.parametrize("malformed_first", [False, True])
def test_fact_correction_preserves_rejection_and_reserves_independent_review(
    tmp_path, malformed_first
):
    from test_analyst_accuracy import complete
    from test_decision_advice import model_response

    calls = []
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        seed = runtime.database.apply(lambda store: insert(store, BASE, 0))

        def transport(profile, payload, timeout):
            calls.append(payload)
            if malformed_first and len(calls) == 1:
                return complete({"malformed": True})
            fact_attempt = 2 if malformed_first else 1
            report = json.loads(
                model_response({"selected_seed_id": seed})["choices"][0]["message"][
                    "content"
                ]
            )
            report["claims"][0].update(
                text="The alert source port is 53000."
                if len(calls) > fact_attempt
                else "The alert source port is 1.",
                facts=[
                    {
                        "evidence_id": seed,
                        "field": "src_port",
                        "value": 53000 if len(calls) > fact_attempt else 1,
                    }
                ],
            )
            if len(calls) == fact_attempt + 1:
                assert "tools" not in payload
                assert '"actual_value": 53000' in payload["messages"][-2]["content"]
                assert "affected prose" in payload["messages"][-2]["content"]
            return complete(report)

        report = runtime.run(
            *SCOPE,
            seed_event_id=seed,
            max_calls=8,
            provider=AgentModelProvider(
                ModelProfile("http://localhost/v1", "mock"), transport, max_attempts=4
            ),
        )
        assert len(calls) == 3 + int(malformed_first)
        assert (
            report["provider_activity"]["turns"][int(malformed_first)]["validation"]
            == "SOURCE_FACT_ERROR"
        )
        assert (
            report["provider_activity"]["turns"][1 + int(malformed_first)]["validation"]
            == "VALID"
        )
        assert report["falsifier"]["model_review"] == "completed"
        assert report["claims"][0]["facts"][0]["value"] == 53000
    finally:
        runtime.close()


def test_host_context_reaches_provider_without_changing_flow_correlation(tmp_path):
    from test_analyst_accuracy import assessment, complete

    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    calls = []
    try:
        seed, context_id = runtime.database.apply(
            lambda store: (
                insert(store, BASE, 0),
                insert(store, http("GET", "/download", "192.0.2.81"), 1),
            )
        )

        def transport(profile, payload, timeout):
            context = json.loads(payload["messages"][1]["content"])
            calls.append(context)
            assert context["investigation_scope"] == "host"
            assert "combined network behavior" in context["question"]
            assert context_id in context["host_context_ids"]
            assert context_id in {row["id"] for row in context["observations"]}
            return complete(assessment(seed))

        report = runtime.run(
            *SCOPE,
            seed_event_id=seed,
            investigation_scope="host",
            max_calls=8,
            provider=AgentModelProvider(
                ModelProfile("http://localhost/v1", "mock"), transport
            ),
        )
        assert len(calls) == 2
        assert context_id not in report["correlation"][0]["member_ids"]
        assert context_id in report["workflow"]["context_ids"]
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("src_port", "53000"),
        ("status", "200"),
        ("response_length_bytes", "1032012"),
        ("url", 200),
    ],
)
def test_fact_schema_requires_field_specific_json_types(field, value):
    from jsonschema import ValidationError, validate

    from bluecheese.adapters.agent_provider import AGENT_REPORT_SCHEMA

    schema = AGENT_REPORT_SCHEMA["properties"]["claims"]["items"]["properties"]["facts"]
    with pytest.raises(ValidationError):
        validate(
            [{"evidence_id": "retrieved-record", "field": field, "value": value}],
            schema,
        )
    correct = int(value) if field != "url" else "/path"
    validate(
        [{"evidence_id": "retrieved-record", "field": field, "value": correct}], schema
    )


def test_record_chat_keeps_report_completion_even_when_claim_citations_are_not_selected(
    tmp_path,
):
    from test_analyst_accuracy import complete

    from bluecheese.application.view_context import ViewContext

    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        seed, record_id = runtime.database.apply(
            lambda store: (
                insert(store, BASE, 0),
                insert(store, http("GET", "/download", "192.0.2.81"), 1),
            )
        )
        report = runtime.run(
            *SCOPE, seed_event_id=seed, investigation_scope="host", max_calls=8
        )

        def transport(profile, payload, timeout):
            context = json.loads(payload["messages"][1]["content"].split(": ", 1)[1])
            assert context["execution_summary"]["final_report_accepted"] is True
            assert context["execution_summary"]["investigation_status"] == "COMPLETED"
            assert context["saved_assessment"]["claims"] == []
            return complete(
                {
                    "action": "answer",
                    "argument": "",
                    "reply": "The saved investigation completed. This selection shows an HTTP request.",
                    "citations": [record_id],
                }
            )

        runtime.configure_provider(
            AgentModelProvider(ModelProfile("http://localhost/v1", "mock"), transport)
        )
        response = runtime.begin_chat(
            "Explain this selected record",
            report["run_id"],
            ViewContext(
                page="Cases",
                task="Evidence",
                run_id=report["run_id"],
                evidence_id=record_id,
            ),
        ).result(5)
        assert not response.get("error"), response
        assert response["citations"] == [record_id]
    finally:
        runtime.close()
