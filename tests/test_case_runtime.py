import json
import threading
from concurrent.futures import ThreadPoolExecutor

import duckdb
import pytest
from test_demo_store import DATA

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.agents.investigator import DemoInvestigator, EvidenceTools
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.store_worker import WorkerStore


def test_provider_does_not_block_ingestion_and_cancellation(tmp_path):
    runtime = DemoRuntime(tmp_path)
    entered, release = threading.Event(), threading.Event()

    class WaitingProvider(DemoInvestigator):
        def investigate(self, tools, falsification):
            tools.call("list_alerts")
            entered.set()
            assert release.wait(5)
            return super().investigate(tools, falsification)

    try:
        runtime.start(interval=3600)
        runtime.stop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            running = executor.submit(
                runtime.run, "suspicious", "clean", provider=WaitingProvider()
            )
            try:
                assert entered.wait(5)
                before = runtime.status()["counts"]["accepted"]
                runtime.poll_once()
                assert runtime.status()["counts"]["accepted"] == before + 1
                with pytest.raises(RuntimeError, match="already active"):
                    runtime.run("benign", "clean")
                assert runtime.cancel()
            finally:
                release.set()
            report = running.result(5)
        assert report["run_status"] == "CANCELLED"
        saved = runtime.command("get_run", "suspicious", "clean", report["run_id"])
        assert saved["status"] == "CANCELLED"
        assert saved["tool_activity"] == report["tool_activity"]
    finally:
        release.set()
        runtime.close()


def test_snapshot_successor_and_restart_history(tmp_path):
    runtime = DemoRuntime(tmp_path)
    first = runtime.run("suspicious", "clean")
    cited = first["supporting_ids"][0]
    frozen = runtime.command(
        "get_event",
        "suspicious",
        "clean",
        first["snapshot"],
        cited,
        snapshot_id=first["snapshot_id"],
    )
    # An interpretation update must never rewrite a prior run's interpretation.
    runtime.database.apply(
        lambda store: store.db.execute(
            "UPDATE evidence SET normalized=? WHERE id=?",
            [json.dumps({"changed": True}), cited],
        )
    )
    assert (
        runtime.command(
            "get_event",
            "suspicious",
            "clean",
            first["snapshot"],
            cited,
            snapshot_id=first["snapshot_id"],
        )
        == frozen
    )
    scoped = WorkerStore(runtime.database, first["snapshot_id"], first["snapshot"])
    cross = runtime.command("list_alerts", "benign", "clean", first["snapshot"])[0][
        "id"
    ]
    assert scoped.get_event("suspicious", "clean", first["snapshot"], cross) is None
    # Restore current interpretation for the successor policy.
    runtime.database.apply(
        lambda store: store.db.execute(
            "UPDATE evidence SET normalized=? WHERE id=?",
            [json.dumps(frozen["normalized"]), cited],
        )
    )
    second = runtime.run("suspicious", "clean", parent_run_id=first["run_id"])
    assert second["case_revision"] == first["case_revision"] + 1
    assert second["parent_run_id"] == first["run_id"]
    with pytest.raises(ValueError, match="same case"):
        runtime.run("benign", "clean", parent_run_id=first["run_id"])
    runtime.close()
    runtime = DemoRuntime(tmp_path)
    try:
        saved = runtime.command("get_run", "suspicious", "clean", first["run_id"])
        assert saved["report"] == first
        assert len(runtime.command("list_runs", "suspicious", "clean")) == 2
        assert runtime.command("get_run", "benign", "clean", first["run_id"]) is None
    finally:
        runtime.close()


def test_old_schema_upgrade_unknown_version_and_interruption(tmp_path):
    path = tmp_path / "e.duckdb"
    # Existing release schema: no migration or case tables.
    db = duckdb.connect(str(path))
    db.execute(
        "CREATE TABLE evidence (seq BIGINT,id VARCHAR PRIMARY KEY,scenario VARCHAR,variant VARCHAR,source VARCHAR,position BIGINT,raw VARCHAR,parsed VARCHAR,normalized VARCHAR,event_type VARCHAR,src_ip VARCHAR,dest_ip VARCHAR)"
    )
    db.close()
    store = EvidenceStore(path)
    store.import_file(DATA / "suspicious-clean.jsonl", "suspicious", "clean")
    run = store.create_run("suspicious", "clean", "Question")
    activity = {"tool": "list_alerts", "returned_ids": [], "arguments": {}}
    store.record_tool(run["run_id"], activity)
    store.close()
    store = EvidenceStore(path)
    saved = store.get_run("suspicious", "clean", run["run_id"])
    assert saved["status"] == "INTERRUPTED"
    assert saved["tool_activity"] == [activity]
    assert store.counts("suspicious", "clean")["accepted"] == 30
    with pytest.raises(ValueError, match="cap"):
        store.create_run("suspicious", "clean", "Question", max_members=1)
    assert len(store.list_runs("suspicious", "clean")) == 1
    store.db.execute("UPDATE schema_migrations SET version=999")
    store.close()
    with pytest.raises(RuntimeError, match="schema migration"):
        EvidenceStore(path)
    # Failed startup released its OS lock.
    db = duckdb.connect(str(path))
    db.execute("UPDATE schema_migrations SET version=1")
    db.close()
    store = EvidenceStore(path)
    store.close()


def test_byte_cap_limits_visible_citations_and_errors_charge_attempts(tmp_path):
    store = EvidenceStore(tmp_path / "e.duckdb")
    try:
        store.import_file(DATA / "suspicious-clean.jsonl", "suspicious", "clean")
        tools = EvidenceTools(
            store, "suspicious", "clean", store.snapshot(), max_bytes=2
        )
        assert tools.call("list_alerts") == []
        assert tools.activity[0]["truncated"]
        event = store.list_alerts("suspicious", "clean", store.snapshot())[0]
        with pytest.raises(ValueError, match="citation"):
            tools.validate([event["id"]])
        with pytest.raises(ValueError):
            tools.call("search_events", event_type="unsupported")
        assert len(tools.activity) == 2
        assert tools.activity[1]["status"] == "ERROR"
    finally:
        store.close()


def test_failed_validation_and_background_executor(tmp_path):
    runtime = DemoRuntime(tmp_path)

    class InvalidProvider(DemoInvestigator):
        def investigate(self, tools, falsification):
            tools.call("list_alerts")
            return {"verdict": "force-clear"}

    try:
        future = runtime.begin_run("suspicious", "clean", provider=InvalidProvider())
        with pytest.raises(ValueError, match="verdict"):
            future.result(5)
        history = runtime.command("list_runs", "suspicious", "clean")
        assert history[0]["status"] == "FAILED"
        saved = runtime.command("get_run", "suspicious", "clean", history[0]["run_id"])
        assert saved["tool_activity"][0]["returned_ids"]
        recovered = runtime.begin_run(
            "suspicious", "clean", parent_run_id=history[0]["run_id"]
        ).result(5)
        assert recovered["run_status"] == "COMPLETED"
        assert recovered["parent_run_id"] == history[0]["run_id"]
        assert recovered["validation_state"] == "MECHANICALLY_VALIDATED"
        incomplete = runtime.run("benign", "clean", max_calls=0)
        assert incomplete["run_status"] == "INCOMPLETE"
        assert (
            runtime.command("get_run", "benign", "clean", incomplete["run_id"])[
                "status"
            ]
            == "INCOMPLETE"
        )
    finally:
        runtime.close()
    with pytest.raises(RuntimeError, match="closed"):
        runtime.start()
    with pytest.raises(RuntimeError, match="closed"):
        runtime.begin_run("benign", "clean")


def test_worker_thread_ownership_bounded_queue_and_exception_recovery(tmp_path):
    from bluecheese.application.store_worker import StoreWorker

    worker = StoreWorker(tmp_path / "worker" / "e.duckdb", capacity=1)
    entered, release = threading.Event(), threading.Event()

    def blocked(store):
        assert threading.current_thread() is worker.thread
        entered.set()
        assert release.wait(5)
        return store.snapshot()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            active = executor.submit(worker.apply, blocked)
            assert entered.wait(5)
            # Seed exactly one queued command without relying on scheduler timing.
            from concurrent.futures import Future

            queued = Future()
            worker.queue.put_nowait((lambda store: store.snapshot(), (), {}, queued))
            with pytest.raises(RuntimeError, match="queue is full"):
                worker.call("snapshot")
            release.set()
            assert active.result(5) == 0
            assert queued.result(5) == 0
        with pytest.raises(AttributeError):
            worker.call("unknown")
        assert worker.call("snapshot") == 0
    finally:
        release.set()
        worker.close()
    assert not worker.thread.is_alive()


def test_bundle_exports_frozen_interpretation(tmp_path):
    from bluecheese.application.report_bundle import export_bundle, verify_bundle

    runtime = DemoRuntime(tmp_path / "state")
    try:
        report = runtime.run("suspicious", "clean")
        runtime.database.apply(
            lambda store: store.db.execute(
                "UPDATE evidence SET normalized='{}' WHERE scenario='suspicious' AND variant='clean'"
            )
        )
        bundle = export_bundle(runtime, report, tmp_path / "bundle")
        assert verify_bundle(bundle)["valid"]
        manifest = json.loads((bundle / "run_manifest.json").read_text())
        assert len(manifest["snapshot_manifest"]["members"]) == 30
    finally:
        runtime.close()


def test_startup_failure_releases_worker_and_directory_lock(tmp_path, monkeypatch):
    original = EvidenceStore.import_file

    def failed_import(self, *args):
        raise ValueError("fixture unavailable")

    monkeypatch.setattr(EvidenceStore, "import_file", failed_import)
    with pytest.raises(ValueError, match="fixture unavailable"):
        DemoRuntime(tmp_path)
    monkeypatch.setattr(EvidenceStore, "import_file", original)
    runtime = DemoRuntime(tmp_path)
    runtime.close()
