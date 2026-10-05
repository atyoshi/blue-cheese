import json

import pytest
from test_demo_store import DATA

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.agents.investigator import EvidenceTools, investigate
from bluecheese.agents.reporting import json_report, markdown_report


@pytest.fixture
def store(tmp_path):
    store = EvidenceStore(tmp_path / "e.duckdb")
    for scenario, variant in [
        ("suspicious", "clean"),
        ("suspicious", "poisoned"),
        ("benign", "clean"),
        ("insufficient", "clean"),
    ]:
        store.import_file(DATA / f"{scenario}-{variant}.jsonl", scenario, variant)
    yield store
    store.close()


@pytest.mark.parametrize(
    "scenario,variant,verdict,status",
    [
        ("suspicious", "clean", "SUSPICIOUS", "not observed"),
        ("suspicious", "poisoned", "UNCERTAIN", "evidence contradicted"),
        ("benign", "clean", "BENIGN_CONFOUNDER", "evidence contradicted"),
        ("insufficient", "clean", "UNCERTAIN", "not available"),
    ],
)
def test_semantic_pipeline(store, scenario, variant, verdict, status):
    report = investigate(store, scenario, variant)
    assert report["verdict"] == verdict
    assert report["falsifier"]["status"] == status
    assert report["tool_activity"][-1]["tool"] == "find_events_by_ip"
    for ref in report["supporting_ids"] + report["contradicting_ids"]:
        assert store.get_event(scenario, variant, report["snapshot"], ref)
    assert json.loads(json_report(report)) == report
    assert report["provider"] in markdown_report(report)


def test_ablation_and_budgets(store):
    assert (
        investigate(store, "benign", "clean", falsification=False)["verdict"]
        == "UNCERTAIN"
    )
    for kwargs in [{"max_calls": 0}, {"max_calls": 2}, {"max_seconds": 0}]:
        report = investigate(store, "suspicious", "clean", **kwargs)
        assert report["verdict"] == "UNCERTAIN"
        assert report["budget"]["calls"] <= report["budget"]["max_calls"]
    times = iter([0, 0, 10, 10])
    assert (
        investigate(
            store, "suspicious", "clean", max_seconds=1, clock=lambda: next(times)
        )["verdict"]
        == "UNCERTAIN"
    )


def test_unseen_invented_cross_scope_snapshot(store):
    snapshot = store.snapshot()
    tools = EvidenceTools(store, "suspicious", "clean", snapshot)
    unseen = store.search_events("suspicious", "clean", snapshot, "flow")[0]["id"]
    cross = store.list_alerts("suspicious", "poisoned", snapshot)[0]["id"]
    for ref in ["invented", unseen, cross]:
        with pytest.raises(ValueError, match="citation"):
            tools.validate([ref])
    alert = tools.call("list_alerts")[0]
    tools.validate([alert["id"]])
    old = EvidenceTools(store, "suspicious", "clean", 0)
    assert old.call("get_event", event_id=alert["id"]) is None
    with pytest.raises(ValueError):
        old.validate([alert["id"]])


def test_provider_receives_tools_only(store):
    from bluecheese.agents.investigator import DemoInvestigator

    class InspectingProvider(DemoInvestigator):
        def investigate(self, tools, falsification):
            for row in tools.call("list_alerts"):
                assert (
                    not {"ground_truth", "injected", "variant"} & row["parsed"].keys()
                )
                assert "metadata" not in row["normalized"]
            return super().investigate(tools, falsification)

    assert (
        investigate(store, "suspicious", "clean", provider=InspectingProvider())[
            "verdict"
        ]
        == "SUSPICIOUS"
    )
