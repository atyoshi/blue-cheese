import json
import secrets
import shutil
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

from bluecheese.adapters.sqlite_store import EvidenceStore
from bluecheese.application.import_pcap import import_eve
from bluecheese.application.investigate_alert import triage_alert
from bluecheese.interfaces.web import make_handler

FIXTURE = Path(__file__).parent / 'fixtures' / 'sample_eve.json'


def test_web_import_triage_and_report(tmp_path):
    token = secrets.token_urlsafe(32)
    handler_type = make_handler(tmp_path, token)
    results = []

    def get(path):
        handler = object.__new__(handler_type)
        handler.path = path
        handler.respond = lambda status, title, body: results.append((status, title, body))
        handler.do_GET()
        return results[-1]

    def post(path, fields):
        handler = object.__new__(handler_type)
        handler.path = path
        body = urlencode({'csrf': token, **fields}).encode()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = BytesIO(body)
        handler.respond = lambda status, title, content: results.append((status, title, content))
        handler.redirect = lambda destination: results.append((303, 'redirect', destination))
        handler.do_POST()
        return results[-1]

    assert 'Import evidence' in get('/')[2]
    imported = post('/imports', {'kind': 'eve', 'path': str(FIXTURE)})
    assert imported[:2] == (303, 'redirect')
    assert imported[2].startswith('/alerts?import_id=')
    assert 'sample_eve.json' in get('/')[2]
    assert 'sample_eve.json' in get('/alerts')[2]
    assert 'TeamViewer' in get(imported[2])[2]
    assert 'All imports' in get('/alerts?import_id=all')[2]
    assert get('/alerts?import_id=000000000000000000000000')[0] == 400
    assert get(imported[2] + '&page=2')[0] == 400
    with EvidenceStore(tmp_path / 'bluecheese.sqlite3') as store:
        event_id = store.list_alerts()[0]['id']
    detail = get('/alerts/' + event_id)[2]
    assert 'Run triage' in detail
    assert 'sample_eve.json' in detail
    assert 'All alerts from this import' in detail
    assert post('/triage/' + event_id, {}) == (303, 'redirect', '/reports/' + event_id)
    assert 'needs_review' in get('/reports/' + event_id)[2]
    assert 'Original record' in get('/evidence/' + event_id)[2]
    assert post('/triage/' + event_id, {'csrf': 'wrong'})[0] == 403

    if shutil.which('suricata'):
        fixtures = Path(__file__).parent / 'fixtures'
        pcap_import = post('/imports', {
            'kind': 'pcap',
            'path': str(fixtures / 'bluecheese-demo.pcap'),
            'config': str(fixtures / 'suricata-demo.yaml'),
            'rules': str(fixtures / 'bluecheese-demo.rules'),
        })
        assert pcap_import[:2] == (303, 'redirect')
        assert 'Blue Cheese demo UDP payload' in get(pcap_import[2])[2]
        assert 'bluecheese-demo.pcap' in get('/alerts')[2]
        assert 'sample_eve.json' in get('/alerts?import_id=all')[2]


def test_low_alert_priority_does_not_label_whole_import(tmp_path):
    records = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    low_alert = dict(records[0])
    low_alert['alert'] = {**low_alert['alert'], 'signature': 'Informational test alert',
                          'severity': 3}
    eve = tmp_path / 'mixed-eve.json'
    eve.write_text('\n'.join(json.dumps(record) for record in
                             [records[0], low_alert, records[1]]) + '\n')
    run = import_eve(eve, tmp_path / 'data')
    with EvidenceStore(tmp_path / 'data' / 'bluecheese.sqlite3') as store:
        low_id = store.db.execute(
            "SELECT id FROM events WHERE import_id=? AND event_type='alert' AND severity=3",
            (run['id'],)).fetchone()['id']
    triage_alert(tmp_path / 'data', low_id)
    handler_type = make_handler(tmp_path / 'data', 'token')

    def get(path):
        handler = object.__new__(handler_type)
        handler.path = path
        result = []
        handler.respond = lambda status, title, body: result.append((status, body))
        handler.do_GET()
        return result[0]

    overview = get('/')[1]
    detail = get('/alerts/' + low_id)[1]
    report = get('/reports/' + low_id)[1]
    assert 'Medium (2): 1' in overview and 'Low (3): 1' in overview
    assert 'Medium (2): 1' in detail and 'Low (3): 1' in detail
    assert 'This priority applies to this alert only' in detail
    assert 'Medium (2): 1' in report and 'Low (3): 1' in report
    assert 'not a verdict on the entire capture' in report
