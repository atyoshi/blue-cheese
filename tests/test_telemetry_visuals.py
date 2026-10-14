from pathlib import Path

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.telemetry_visuals import summarize

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


def test_visual_rows_respect_scope_snapshot_limit_and_summary_reconciles(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.duckdb")
    try:
        raw = FIXTURE.read_bytes().splitlines(keepends=True)
        store.insert("live", "external", "sensor", 0, raw[0])
        store.insert("live", "external", "sensor", 1000, raw[1])
        snapshot = store.snapshot()
        store.insert("live", "replay", "fixture", 0, raw[0])
        store.insert("live", "external", "sensor", 2000, raw[0])
        rows = store.visual_telemetry("live", "external", snapshot)
        assert len(rows) == 2
        assert rows[0]["event_type"] == "flow"
        assert len(store.visual_telemetry("live", "external", snapshot, limit=1)) == 1
        result = summarize(rows)
        assert sum(r["alerts"] for r in result["severities"]) == 1
        assert sum(r["records"] for r in result["protocols"]) == 2
        assert sum(r["records"] for r in result["connections"]) == 2
        assert sum(r["records"] for r in result["timeline"]) == 2
        assert result["untimed"] == 0
    finally:
        store.close()


def test_time_bins_preserve_gaps_and_missing_times_are_not_fabricated():
    base = {
        "event_type": "flow",
        "src_ip": "192.0.2.1",
        "dest_ip": "192.0.2.2",
        "protocol": None,
    }
    rows = [
        {**base, "timestamp": value}
        for value in (
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:03:00Z",
            "invalid",
            "2026-01-01T00:00:00",
        )
    ]
    result = summarize(rows)
    assert result["untimed"] == 2
    assert len(result["timeline"]) == 8
    assert sum(r["records"] for r in result["timeline"]) == 2
    assert sum(r["records"] for r in result["protocols"]) == 4
    assert all(r["records"] == 0 for r in result["timeline"] if "00:01:" in r["time"])
    assert summarize([])["timeline"] == []
    distant = summarize(
        [
            {**base, "timestamp": "2020-01-01T00:00:00Z"},
            {**base, "timestamp": "2026-01-01T00:00:00Z"},
        ]
    )
    assert len(distant["timeline"]) <= 242
    assert sum(r["records"] for r in distant["timeline"]) == 2


def test_protocol_records_are_counted_without_becoming_flows():
    rows = [
        {
            "event_type": kind,
            "src_ip": "a",
            "dest_ip": "b",
            "protocol": "TCP",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        for kind in ("alert", "flow", "dns", "http", "tls")
    ]
    result = summarize(rows)
    assert result["connections"][0] == {
        "source": "a",
        "destination": "b",
        "records": 5,
        "alerts": 1,
        "flows": 1,
    }
    assert sum(row["records"] for row in result["timeline"]) == 5
