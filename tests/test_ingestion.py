import pytest

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.ingestion import EveFollower, SourceGap
from bluecheese.application.demo_runtime import DemoRuntime
from test_demo_store import DATA

LINE = (DATA / 'suspicious-clean.jsonl').read_bytes().splitlines(keepends=True)[0]


def test_append_partial_malformed_retry_restart(tmp_path):
    db = tmp_path / 'e.duckdb'
    path = tmp_path / 'eve.jsonl'
    path.write_bytes(LINE + LINE[:20])
    store = EvidenceStore(db)
    follower = EveFollower(store, path)
    follower.poll_once()
    assert store.counts('live', 'replay') == dict(accepted=1, invalid=0)
    assert follower.committed == len(LINE)
    follower.poll_once()
    store.close()
    store = EvidenceStore(db)
    follower = EveFollower(store, path)
    with path.open('ab') as stream:
        stream.write(LINE[20:] + b'bad json\n' + LINE)
    follower.poll_once()
    assert store.counts('live', 'replay') == dict(accepted=3, invalid=1)
    rows = store.query('live', 'replay', store.snapshot())
    assert len({r['id'] for r in rows}) == 3  # identical lines remain distinct
    assert all(r['raw'].encode() == LINE for r in rows)
    assert follower.committed == path.stat().st_size
    EveFollower(store, path).poll_once()
    assert store.counts('live', 'replay')['accepted'] == 3
    store.close()


def test_bound_reads_oversized_quarantine_and_truncation(tmp_path):
    path = tmp_path / 'eve'
    path.write_bytes(b'x'*2000 + b'\n' + LINE)
    store = EvidenceStore(tmp_path / 'e.duckdb')
    follower = EveFollower(store, path, max_read=300, max_line=1000)
    while follower.scanned < path.stat().st_size:
        assert follower.poll_once()['bytes_read'] <= 300
        assert len(follower.pending) <= 1000
    assert store.counts('live', 'replay') == dict(accepted=1, invalid=1)
    path.write_bytes(b'')
    with pytest.raises(SourceGap, match='truncated'):
        follower.poll_once()
    store.close()


def test_replacement_stops(tmp_path):
    path = tmp_path / 'eve'
    path.write_bytes(LINE)
    store = EvidenceStore(tmp_path / 'e.duckdb')
    follower = EveFollower(store, path)
    follower.poll_once()
    other = tmp_path / 'other'
    other.write_bytes(LINE)
    other.replace(path)
    with pytest.raises(SourceGap, match='replaced'):
        EveFollower(store, path).poll_once()
    store.close()


def test_transaction_rollback_offset_with_insert(tmp_path, monkeypatch):
    path = tmp_path / 'eve'
    path.write_bytes(LINE)
    store = EvidenceStore(tmp_path / 'e.duckdb')
    follower = EveFollower(store, path)
    original = store.insert
    def fail(*args):
        original(*args)
        raise RuntimeError('simulate interruption')
    monkeypatch.setattr(store, 'insert', fail)
    with pytest.raises(RuntimeError):
        follower.poll_once()
    assert store.snapshot() == 0
    assert store.db.execute('SELECT count(*) FROM cursors').fetchone()[0] == 0
    monkeypatch.setattr(store, 'insert', original)
    follower.poll_once()
    assert store.counts('live', 'replay')['accepted'] == 1
    store.close()


def test_runtime_single_worker_fixed_snapshot(tmp_path):
    runtime = DemoRuntime(tmp_path)
    assert runtime.start(interval=3600)
    assert not runtime.start(interval=3600)
    runtime.stop()  # join ensures the first tick completed, no sleeps
    before = runtime.status()['counts']['accepted']
    assert before >= 1
    report = runtime.run('live', 'replay')
    runtime.poll_once()
    assert runtime.status()['counts']['accepted'] == before + 1
    rows = runtime.command('query', 'live', 'replay', report['snapshot'])
    assert len(rows) == before
    runtime.close()
    restarted = DemoRuntime(tmp_path)
    restarted.start(interval=3600)
    restarted.stop()
    assert restarted.status()['counts']['accepted'] == before + 2
    restarted.close()
