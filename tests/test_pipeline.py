import json
import shutil
from pathlib import Path

import pytest

from bluecheese.adapters.sqlite_store import EvidenceStore
from bluecheese.application.import_pcap import import_eve, import_pcap
from bluecheese.application.investigate_alert import case_report, triage_alert

FIXTURE = Path(__file__).parent / 'fixtures' / 'sample_eve.json'


def test_eve_to_traceable_triage(tmp_path):
    first = import_eve(FIXTURE, tmp_path)
    second = import_eve(FIXTURE, tmp_path)
    assert first['id'] == second['id']
    assert first['events'] == second['events'] == 2
    assert first['alerts'] == 1
    with EvidenceStore(tmp_path / 'bluecheese.sqlite3') as store:
        alert = store.list_alerts()[0]
        assert json.loads(store.resolve(alert['id'])['original_record'])['alert']['severity'] == 2
    result = triage_alert(tmp_path, alert['id'])
    assert result['triage']['priority'] == 'medium'
    assert len(result['triage']['evidence_ids']) == 2
    report = case_report(tmp_path, alert['id'])
    assert report['detection']['signature'].startswith('ET INFO TeamViewer')
    assert len(report['evidence']) == 2
    assert report['import']['status'] == 'complete'


def test_invalid_record_is_quarantined(tmp_path):
    eve = tmp_path / 'eve.json'
    eve.write_text(FIXTURE.read_text() + 'not json\n')
    run = import_eve(eve, tmp_path / 'data')
    assert run['status'] == 'incomplete'
    assert run['events'] == 2
    assert run['invalid_records'] == 1


def test_interrupted_import_rebuilds_without_duplicates(tmp_path):
    first = import_eve(FIXTURE, tmp_path)
    with EvidenceStore(tmp_path / 'bluecheese.sqlite3') as store:
        store.db.execute("UPDATE imports SET status='processing' WHERE id=?", (first['id'],))
        store.db.commit()
    resumed = import_eve(FIXTURE, tmp_path)
    assert resumed['status'] == 'complete'
    assert resumed['events'] == 2


def test_modified_evidence_is_rejected(tmp_path):
    import_eve(FIXTURE, tmp_path)
    with EvidenceStore(tmp_path / 'bluecheese.sqlite3') as store:
        alert = store.list_alerts()[0]
        artifact = store.db.execute('SELECT path FROM artifacts WHERE id=?',
                                    (alert['artifact_id'],)).fetchone()['path']
        Path(artifact).write_text('changed\n')
        with pytest.raises(ValueError, match='hash mismatch'):
            store.resolve(alert['id'])


@pytest.mark.skipif(shutil.which('suricata') is None, reason='Suricata is not installed')
def test_pcap_with_real_suricata(tmp_path):
    fixtures = Path(__file__).parent / 'fixtures'
    pcap = fixtures / 'bluecheese-demo.pcap'
    config = fixtures / 'suricata-demo.yaml'
    rules = fixtures / 'bluecheese-demo.rules'
    run = import_pcap(pcap, tmp_path / 'data', config_path=config, rules_path=rules)
    assert run['status'] == 'complete'
    assert run['events'] == 2
    assert run['alerts'] == 1
    assert 'Suricata version' in run['sensor_version']
    assert run['sensor_elapsed_seconds'] >= 0
    assert import_pcap(pcap, tmp_path / 'data', config_path=config,
                       rules_path=rules)['id'] == run['id']
    with EvidenceStore(tmp_path / 'data' / 'bluecheese.sqlite3') as store:
        alert = store.list_alerts()[0]
        assert alert['signature_id'] == 1000001
        assert alert['timestamp'].endswith('+00:00')
        assert store.resolve(alert['id'])['original_record']
    result = triage_alert(tmp_path / 'data', alert['id'])
    assert len(result['triage']['evidence_ids']) == 2
    assert case_report(tmp_path / 'data', alert['id'])['import']['sensor_elapsed_seconds'] >= 0
