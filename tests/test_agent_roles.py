from copy import deepcopy

from bluecheese.agents.correlation import CorrelationAgent
from bluecheese.agents.triage import TriageAgent
from bluecheese.application.demo_runtime import DemoRuntime


def event(event_id, **fields):
    normalized = {
        "sensor": "suricata",
        "event_type": "flow",
        "timestamp": "2026-01-10T12:00:00+00:00",
        "src_ip": "10.0.0.8",
        "dest_ip": "198.51.100.23",
        "src_port": 43000,
        "dest_port": 443,
        "protocol": "TCP",
        "flow_id": "900",
        **fields,
    }
    return {"id": event_id, "source": "source-a", "normalized": normalized}


def test_triage_groups_distinct_occurrences_without_inventing_importance():
    first = event("a", event_type="alert", severity=2, signature_id=10)
    second = event("b", event_type="alert", severity=1, signature_id=10)
    missing = event("c", event_type="alert", severity=None, signature_id=11)
    result = TriageAgent().triage_events([first, second, missing])
    group = result["candidates"][0]
    assert group["priority"] == "high"
    assert group["seed_ids"] == ["a", "b"]
    assert group["occurrence_count"] == 2
    assert group["sensor_severities"] == [2, 1]
    assert group["asset_importance"] == "unknown"
    assert result["candidates"][1]["priority"] == "unknown"


def test_correlation_rejects_ip_only_old_ambiguous_and_cross_source_matches():
    seed = event("seed", event_type="alert")
    same = event("same", timestamp="2026-01-10T12:01:00+00:00")
    tuple_match = event("tuple", flow_id="different")
    unrelated = event("unrelated", flow_id="different", dest_ip="192.0.2.99")
    stale = event("stale", timestamp="2026-01-11T12:00:00+00:00")
    missing_time = event("missing", timestamp=None)
    other_source = deepcopy(same)
    other_source.update(id="other-source", source="source-b")
    result = CorrelationAgent().correlate(
        seed, [same, tuple_match, unrelated, stale, missing_time, other_source]
    )
    assert result["member_ids"] == ["seed", "same", "tuple"]
    assert {link["basis"] for link in result["links"]} == {
        "same_sensor_flow_id_and_endpoints",
        "exact_endpoint_tuple",
    }
    assert result["excluded_count"] == 4
    capped = CorrelationAgent(max_events=2).correlate(
        seed, [same, tuple_match, unrelated]
    )
    assert len(capped["member_ids"]) == 2
    assert capped["capped"]


def test_all_logical_roles_connected_with_one_shared_budget(tmp_path):
    runtime = DemoRuntime(tmp_path)
    try:
        report = runtime.run("suspicious", "clean")
        assert report["workflow"]["roles"] == [
            "Orchestrator",
            "Triage",
            "Correlation",
            "Investigator",
            "Falsifier",
            "Reporter",
        ]
        assert report["triage"]["candidates"][0]["priority"] == "high"
        correlation = report["correlation"][0]
        assert len(correlation["member_ids"]) == 6
        assert all(link["rule_version"] for link in correlation["links"])
        assert report["budget"]["calls"] == 4
        assert report["budget"]["calls"] <= report["budget"]["max_calls"]
        assert report["verdict"] == "SUSPICIOUS"
        saved = runtime.command("get_run", "suspicious", "clean", report["run_id"])
        assert saved["report"]["triage"] == report["triage"]
        assert saved["report"]["correlation"] == report["correlation"]
        assert saved["tool_activity"] == report["tool_activity"]
    finally:
        runtime.close()
