import socket
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.ingestion import SourceGap
from bluecheese.application.unix_stream import UnixStreamFollower

RAW = (
    (Path(__file__).parent / "fixtures/sample_eve.json")
    .read_bytes()
    .splitlines(keepends=True)
)


@pytest.fixture
def short_paths():
    # macOS sockaddr_un has a small path limit; pytest's nested paths exceed it.
    with TemporaryDirectory(prefix="bc-stream-", dir="/tmp") as directory:
        yield Path(directory)


def test_fragmented_stream_exact_raw_duplicate_positions_disconnect_and_resume(
    short_paths,
):
    store = EvidenceStore(short_paths / "state/evidence.duckdb")
    path = short_paths / "eve.sock"
    receiver = UnixStreamFollower(store, path, short_paths / "state")
    producer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        assert receiver.poll_once()["bytes_read"] == 0
        producer.connect(str(path))
        producer.sendall(RAW[0][:30])
        receiver.poll_once()
        assert store.counts("live", "external")["accepted"] == 0
        producer.sendall(RAW[0][30:] + RAW[1] + RAW[0])
        receiver.poll_once()
        rows = store.query("live", "external", store.snapshot())
        assert len(rows) == 3
        assert [r["raw"].encode() for r in rows] == [RAW[0], RAW[1], RAW[0]]
        assert len({r["id"] for r in rows}) == 3
        assert receiver.spool.read_bytes() == RAW[0] + RAW[1] + RAW[0]
        producer.close()
        with pytest.raises(SourceGap, match="disconnected"):
            receiver.poll_once()
        spool = receiver.spool
        receiver.close()
        assert not path.exists()
        # Durable bytes received before a database commit are recovered on restart.
        with spool.open("ab") as stream:
            stream.write(RAW[1])
        receiver = UnixStreamFollower(store, path, short_paths / "state")
        receiver.poll_once()
        assert store.counts("live", "external")["accepted"] == 4
        receiver.poll_once()
        assert store.counts("live", "external")["accepted"] == 4
    finally:
        producer.close()
        receiver.close()
        store.close()


def test_partial_disconnect_and_quota_stop_without_merging_or_deleting(short_paths):
    store = EvidenceStore(short_paths / "state/evidence.duckdb")
    path = short_paths / "eve.sock"
    receiver = UnixStreamFollower(store, path, short_paths / "state")
    producer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        producer.connect(str(path))
        producer.sendall(b'{"timestamp":')
        receiver.poll_once()
        producer.close()
        with pytest.raises(SourceGap, match="partial record"):
            receiver.poll_once()
        spool = receiver.spool
        receiver.close()
        with pytest.raises(SourceGap, match="Previous stream"):
            UnixStreamFollower(store, path, short_paths / "state")
        assert spool.read_bytes() == b'{"timestamp":'
        receiver = UnixStreamFollower(
            store,
            short_paths / "other.sock",
            short_paths / "state",
            max_bytes=len(RAW[0]),
        )
        producer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        producer.connect(str(receiver.path))
        producer.sendall(RAW[0] + RAW[1])
        receiver.poll_once()
        with pytest.raises(SourceGap, match="limit"):
            receiver.poll_once()
        assert receiver.spool.read_bytes() == RAW[0]
        assert store.counts("live", "external")["accepted"] == 1
    finally:
        producer.close()
        receiver.close()
        store.close()


def test_receiver_never_replaces_existing_paths_and_only_unlinks_owned_socket(
    short_paths,
):
    store = EvidenceStore(short_paths / "state/evidence.duckdb")
    path = short_paths / "eve.sock"
    path.write_text("keep")
    try:
        with pytest.raises(ValueError, match="already exists"):
            UnixStreamFollower(store, path, short_paths / "state")
        assert path.read_text() == "keep"
        path.unlink()
        receiver = UnixStreamFollower(store, path, short_paths / "state")
        path.unlink()
        path.write_text("replacement")
        receiver.close()
        assert path.read_text() == "replacement"
    finally:
        store.close()


def test_suricata_real_unix_stream_output(short_paths):
    import json
    import shutil
    import subprocess

    executable = shutil.which("suricata")
    if executable is None:
        pytest.skip("Suricata is not installed")
    fixtures = Path(__file__).parent / "fixtures"
    store = EvidenceStore(short_paths / "state/evidence.duckdb")
    path = short_paths / "sensor.sock"
    receiver = UnixStreamFollower(store, path, short_paths / "state")
    try:
        config = short_paths / "suricata.yaml"
        config.write_text(
            (fixtures / "suricata-demo.yaml")
            .read_text()
            .replace("filetype: regular", "filetype: unix_stream")
            .replace("filename: eve.json", "filename: " + json.dumps(str(path)))
        )
        result = subprocess.run(
            [
                executable,
                "-c",
                str(config),
                "-S",
                str(fixtures / "bluecheese-demo.rules"),
                "-r",
                str(fixtures / "bluecheese-demo.pcap"),
                "-l",
                str(short_paths),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        receiver.poll_once()
        records = store.query("live", "external", store.snapshot())
        assert any(r["normalized"]["event_type"] == "alert" for r in records)
        assert any(r["normalized"]["event_type"] == "flow" for r in records)
        assert any("Blue Cheese demo UDP payload" in r["raw"] for r in records)
        with pytest.raises(SourceGap, match="disconnected"):
            receiver.poll_once()
    finally:
        receiver.close()
        store.close()
