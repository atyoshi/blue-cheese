import json
from pathlib import Path

import duckdb
import pytest

from bluecheese.adapters.demo_schema import SQL
from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.demo_runtime import DemoRuntime

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


def test_selected_alert_freezes_only_neighborhood_and_preserves_history(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        records = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
        records[0]["flow_id"] = 99
        records[1]["flow_id"] = 99
        records[1]["flow"] = {"state": "established", "bytes_toserver": 20000}
        unrelated = {**records[0], "src_ip": "192.0.2.1"}
        old = {**records[1], "timestamp": "2024-01-01T00:00:00+00:00"}
        eve = tmp_path / "eve.json"
        eve.write_text(
            "".join(json.dumps(record) + "\n" for record in [*records, unrelated, old])
        )
        runtime.start(path=eve, replay=False, interval=3600)
        runtime.stop()
        seed = next(
            r
            for r in runtime.command(
                "list_alerts", "live", "external", runtime.command("snapshot")
            )
            if r["normalized"]["src_ip"] == "10.1.17.215"
        )
        report = runtime.run("live", "external", seed_event_id=seed["id"], max_calls=8)
        manifest = runtime.command("snapshot_manifest", report["snapshot_id"])
        assert len(manifest["members"]) == 2
        assert report["correlation"][0]["seed_id"] == seed["id"]
        assert not report["synthetic"]
        assert all("Synthetic data" not in warning for warning in report["warnings"])
        runtime.command(
            "add_analyst_action",
            "live",
            "external",
            report["run_id"],
            "Analyst",
            "ESCALATED",
            "Check endpoint",
        )
        with pytest.raises(ValueError, match="scope"):
            runtime.command(
                "add_analyst_action",
                "live",
                "replay",
                report["run_id"],
                "Analyst",
                "OPEN",
                "",
            )
        successor = runtime.run(
            "live",
            "external",
            seed_event_id=seed["id"],
            parent_run_id=report["run_id"],
            max_calls=8,
        )
        assert successor["case_revision"] == 2
        assert (
            runtime.command("analyst_history", "live", "external", successor["run_id"])[
                0
            ]["note"]
            == "Check endpoint"
        )
        assert (
            runtime.command("get_run", "live", "external", report["run_id"])["report"]
            == report
        )
    finally:
        runtime.close()


def test_durable_queue_recovers_commit_before_notification_and_interrupted_work(
    tmp_path,
):
    state = tmp_path / "state"
    runtime = DemoRuntime(state, load_fixtures=False)
    runtime.start(path=FIXTURE, replay=False, interval=3600)
    runtime.stop()
    assert runtime.status()["investigation_runs"] == 0
    assert runtime.command("work_queue")[0]["status"] == "QUEUED"
    runtime.close()
    runtime = DemoRuntime(state, load_fixtures=False)
    try:
        assert runtime.schedule_once()
        runtime.pending_run.result(5)
        assert runtime.command("work_queue")[0]["status"] == "COMPLETED"
        assert not runtime.schedule_once()
        assert runtime.status()["investigation_runs"] == 1
        row = runtime.command("work_queue")[0]
        runtime.database.apply(
            lambda store: store.db.execute(
                "UPDATE investigation_work SET status='RUNNING' WHERE event_id=?",
                [row["event_id"]],
            )
        )
    finally:
        runtime.close()
    runtime = DemoRuntime(state, load_fixtures=False)
    try:
        assert runtime.command("work_queue")[0]["status"] == "INTERRUPTED"
        assert not runtime.schedule_once()
        runtime.command("retry_work", row["event_id"])
        assert runtime.schedule_once()
        runtime.pending_run.result(5)
        assert runtime.command("work_queue")[0]["status"] == "COMPLETED"
    finally:
        runtime.close()


def test_v1_migration_is_additive_and_checksums_are_preserved(tmp_path):
    import hashlib

    path = tmp_path / "e.duckdb"
    store = EvidenceStore(path)
    store.close()
    db = duckdb.connect(str(path))
    for table in (
        "analyst_actions",
        "source_incidents",
        "investigation_work",
        "evidence_watermark",
        "retention_tombstones",
        "retention_operations",
        "file_generations",
        "case_workspace",
        "run_context",
        "run_activity",
        "workspace_chat",
        "decision_advice",
        "provider_diagnostics",
    ):
        db.execute("DROP TABLE " + table)
    db.execute("DELETE FROM schema_migrations WHERE version>1")
    db.close()
    store = EvidenceStore(path)
    try:
        rows = store.db.execute(
            "SELECT version,checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert len(rows) == 8
        assert rows[0] == (1, hashlib.sha256(SQL.encode()).hexdigest())
    finally:
        store.close()


def test_retention_pins_snapshots_and_work_preserves_watermark_and_prevents_resurrection(
    tmp_path,
):
    store = EvidenceStore(tmp_path / "state/evidence.duckdb")
    records = [line.encode() + b"\n" for line in FIXTURE.read_text().splitlines()]
    try:
        pinned = store.insert("scope", "external", "source", 0, records[0])
        run = store.create_run("scope", "external", "Case")
        unpinned = store.insert("scope", "external", "source", 1000, records[1])
        queued = store.insert("live", "external", "sensor", 0, records[0])
        watermark = store.snapshot()
        preview = store.retention(watermark + 1)
        assert preview["event_ids"] == [unpinned]
        assert preview["removed"] == 0
        result = store.retention(watermark + 1, apply=True)
        assert result["removed"] == 1
        assert store.snapshot() == watermark
        assert store.get_event("scope", "external", watermark, pinned)
        assert store.get_event("live", "external", watermark, queued)
        assert store.insert("scope", "external", "source", 1000, records[1]) is None
        assert store.get_event("scope", "external", watermark, unpinned) is None
        later = store.insert("scope", "external", "source", 2000, records[1])
        assert store.snapshot() == watermark + 1
        assert (
            store.get_event(
                "scope",
                "external",
                store.snapshot(),
                later,
                snapshot_id=run["snapshot_id"],
            )
            is None
        )
    finally:
        store.close()


def test_doctor_no_network_no_initialization_and_conflicting_runtime(tmp_path):
    from bluecheese.application.doctor import doctor

    state = tmp_path / "state"
    result = doctor(state, FIXTURE)
    assert result["ok"]
    assert not state.exists()
    runtime = DemoRuntime(state, load_fixtures=False)
    try:
        assert not doctor(state)["ok"]
    finally:
        runtime.close()
    result = doctor(state)
    assert result["ok"]
    assert result["schema_version"] == 8


def test_source_preflight_rejects_directory_fifo_and_expands_home(
    tmp_path, monkeypatch
):
    import os

    from bluecheese.application.doctor import doctor
    from bluecheese.application.source_path import readable_eve_path

    monkeypatch.setenv("HOME", str(tmp_path))
    eve = tmp_path / "eve.json"
    eve.write_bytes(FIXTURE.read_bytes())
    assert readable_eve_path("~/eve.json") == eve
    assert doctor(tmp_path / "state", "~/eve.json")["eve_readable"]
    for value in ("", tmp_path, tmp_path / "missing"):
        with pytest.raises(ValueError):
            readable_eve_path(value)
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular file"):
        readable_eve_path(fifo)
    assert not doctor(tmp_path / "state", fifo)["ok"]
