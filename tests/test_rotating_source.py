from pathlib import Path

import pytest

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.ingestion import EveFollower, SourceGap
from bluecheese.application.rotating_source import RotatingEveFollower

RAW = (
    (Path(__file__).parent / "fixtures/sample_eve.json")
    .read_bytes()
    .splitlines(keepends=True)[0]
)


def test_rename_drains_old_generation_and_keeps_identical_new_occurrences(tmp_path):
    store = EvidenceStore(tmp_path / "state/evidence.duckdb")
    path = tmp_path / "eve.json"
    path.write_bytes(RAW)
    clock = [0.0]
    follower = RotatingEveFollower(store, path, clock=lambda: clock[0], drain_seconds=1)
    try:
        follower.poll_once()
        path.rename(tmp_path / "eve.json.1")
        path.write_bytes(RAW)
        with (tmp_path / "eve.json.1").open("ab") as stream:
            stream.write(RAW)
        follower.poll_once()
        assert store.counts("live", "external")["accepted"] == 2
        clock[0] = 1
        follower.poll_once()  # switch only after bounded old-generation drain
        follower.poll_once()
        rows = store.query("live", "external", store.snapshot())
        assert len(rows) == 3
        assert len({row["id"] for row in rows}) == 3
        assert all(row["raw"].encode() == RAW for row in rows)
        assert rows[0]["source"] == rows[1]["source"]
        assert rows[2]["source"] != rows[0]["source"]
        assert follower.transitions == 1
    finally:
        follower.close()
        store.close()


def test_restart_recovers_archive_and_adopts_previous_cursor_without_duplication(
    tmp_path,
):
    path = tmp_path / "eve.json"
    path.write_bytes(RAW)
    state = tmp_path / "state/evidence.duckdb"
    store = EvidenceStore(state)
    # Compatibility: existing append-only release cursor/source IDs must survive.
    EveFollower(store, path, "live", "external").poll_once()
    path.rename(tmp_path / "eve.json.1")
    with (tmp_path / "eve.json.1").open("ab") as stream:
        stream.write(RAW)
    path.write_bytes(RAW)
    store.close()
    store = EvidenceStore(state)
    clock = [0.0]
    follower = RotatingEveFollower(store, path, clock=lambda: clock[0], drain_seconds=1)
    try:
        follower.poll_once()
        assert store.counts("live", "external")["accepted"] == 2
        clock[0] = 1
        follower.poll_once()
        follower.poll_once()
        assert store.counts("live", "external")["accepted"] == 3
    finally:
        follower.close()
        store.close()
    store = EvidenceStore(state)
    follower = RotatingEveFollower(store, path)
    try:
        follower.poll_once()
        assert store.counts("live", "external")["accepted"] == 3
    finally:
        follower.close()
        store.close()


def test_truncation_partial_old_record_and_missing_archive_fail_visibly(tmp_path):
    store = EvidenceStore(tmp_path / "state/evidence.duckdb")
    path = tmp_path / "eve.json"
    path.write_bytes(RAW)
    follower = RotatingEveFollower(store, path)
    try:
        follower.poll_once()
        path.write_bytes(b"{}\n")
        with pytest.raises(SourceGap, match="truncated"):
            follower.poll_once()
    finally:
        follower.close()
    # The original generation is now unrecoverable; no silent reset to the new file.
    replacement = tmp_path / "replacement"
    replacement.write_bytes(RAW)
    path.unlink()
    replacement.rename(path)
    with pytest.raises(SourceGap):
        RotatingEveFollower(store, path)
    store.close()

    store = EvidenceStore(tmp_path / "partial/evidence.duckdb")
    path.write_bytes(RAW + b"{")
    clock = [0.0]
    follower = RotatingEveFollower(store, path, clock=lambda: clock[0], drain_seconds=1)
    try:
        follower.poll_once()
        path.rename(tmp_path / "eve.json.2")
        path.write_bytes(RAW)
        follower.poll_once()
        clock[0] = 1
        with pytest.raises(SourceGap, match="partial record"):
            follower.poll_once()
        assert store.counts("live", "external")["accepted"] == 1
    finally:
        follower.close()
        store.close()


def test_multiple_rotation_before_drain_is_not_silently_skipped(tmp_path):
    store = EvidenceStore(tmp_path / "state/evidence.duckdb")
    path = tmp_path / "eve.json"
    path.write_bytes(RAW)
    clock = [0.0]
    follower = RotatingEveFollower(store, path, clock=lambda: clock[0], drain_seconds=1)
    try:
        follower.poll_once()
        path.rename(tmp_path / "eve.json.1")
        path.write_bytes(RAW)
        follower.poll_once()
        path.rename(tmp_path / "eve.json.2")
        path.write_bytes(RAW)
        clock[0] = 1
        with pytest.raises(SourceGap, match="Multiple rotations"):
            follower.poll_once()
        assert store.counts("live", "external")["accepted"] == 1
    finally:
        follower.close()
        store.close()
    store = EvidenceStore(tmp_path / "state/evidence.duckdb")
    try:
        with pytest.raises(SourceGap, match="Untracked archived"):
            RotatingEveFollower(store, path)
    finally:
        store.close()
