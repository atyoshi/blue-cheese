import json
from pathlib import Path

from bluecheese.adapters.duckdb_store import EvidenceStore

DATA = Path(__file__).parents[1] / 'src/bluecheese/data'


def test_raw_normalization_retry_and_isolation(tmp_path):
    store = EvidenceStore(tmp_path / 'test.duckdb')
    path = DATA / 'suspicious-clean.jsonl'
    store.import_file(path, 'suspicious', 'clean')
    store.import_file(path, 'suspicious', 'clean')
    store.import_file(DATA / 'suspicious-poisoned.jsonl', 'suspicious', 'poisoned')
    assert store.counts('suspicious', 'clean') == dict(accepted=30, invalid=0)
    snap = store.snapshot()
    event = store.list_alerts('suspicious', 'clean', snap)[0]
    assert event['raw'] == path.read_text().splitlines(keepends=True)[0]
    assert event['parsed'] == json.loads(event['raw'])
    assert event['normalized']['src_ip'] == '10.0.0.8'
    assert store.get_event('suspicious', 'poisoned', snap, event['id']) is None
    assert len(store.find_events_by_ip('suspicious', 'clean', snap, '10.0.0.8')) == 6
    assert len(store.search_events('suspicious', 'clean', snap, 'flow')) == 29
    assert len({r['id'] for r in store.query('suspicious', 'clean', snap)}) == 30
    store.close()


def test_poison_manifest_separate_and_clean_unchanged():
    import hashlib
    manifest = json.loads((DATA.parents[2] / 'docs/evaluator/transformation.json').read_text())
    assert hashlib.sha256((DATA / 'suspicious-clean.jsonl').read_bytes()).hexdigest() == manifest['clean_sha256']
    for path in DATA.glob('*.jsonl'):
        for record in map(json.loads, path.read_text().splitlines()):
            assert not {'variant', 'ground_truth', 'injected', 'label'} & record.keys()
