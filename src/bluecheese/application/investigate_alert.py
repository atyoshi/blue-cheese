"""Read-only evidence retrieval and persisted triage."""

import json
from dataclasses import asdict
from pathlib import Path

from bluecheese.adapters.sqlite_store import EvidenceStore
from bluecheese.agents.triage import POLICY_VERSION, TriageAgent
from bluecheese.application.import_pcap import utcnow


def triage_alert(evidence_dir, event_id):
    with EvidenceStore(Path(evidence_dir) / 'bluecheese.sqlite3') as store:
        alert = store.get_event(event_id)
        if alert is None or alert['event_type'] != 'alert':
            raise ValueError(f'Alert not found: {event_id}')
        related = store.related_events(alert)
        result = TriageAgent().analyze(alert, related)
        for ref in result.evidence_ids:
            store.resolve(ref)
        store.save_triage(event_id, result, POLICY_VERSION, utcnow())
        return {'alert_id': event_id, 'triage': asdict(result),
                'related_events': [event['id'] for event in related],
                'policy_version': POLICY_VERSION}


def case_report(evidence_dir, event_id):
    with EvidenceStore(Path(evidence_dir) / 'bluecheese.sqlite3') as store:
        alert = store.get_event(event_id)
        if alert is None or alert['event_type'] != 'alert':
            raise ValueError(f'Alert not found: {event_id}')
        triage = store.db.execute('SELECT * FROM triage WHERE event_id=?',
                                  (event_id,)).fetchone()
        if triage is None:
            raise ValueError('Run triage before creating a report')
        related = store.related_events(alert)
        import_run = store.get_import(alert['import_id'])
        return {
            'case_id': f'case-{event_id}',
            'observation': {'event_id': event_id, 'timestamp': alert['timestamp'],
                            'src_ip': alert['src_ip'], 'dest_ip': alert['dest_ip']},
            'detection': {'signature': alert['signature'],
                          'signature_id': alert['signature_id'],
                          'severity': alert['severity']},
            'interpretation': {'priority': triage['priority'],
                               'disposition': triage['disposition'],
                               'rationale': triage['rationale'],
                               'limitations': json.loads(triage['limitations_json'])},
            'evidence': [
                {'event_id': ref, 'artifact_id': resolved['artifact_id'],
                 'line_number': resolved['line_number'], 'artifact_sha256': resolved['sha256']}
                for ref in json.loads(triage['evidence_ids_json'])
                for resolved in [store.resolve(ref)]
            ],
            'timeline': [{'event_id': event['id'], 'timestamp': event['timestamp'],
                          'event_type': event['event_type']} for event in [alert, *related]],
            'import': {'id': import_run['id'], 'status': import_run['status'],
                       'elapsed_seconds': import_run['elapsed_seconds'],
                       'peak_rss_kib': import_run['peak_rss_kib'],
                       'sensor_elapsed_seconds': import_run['sensor_elapsed_seconds'],
                       'sensor_peak_rss_kib': import_run['sensor_peak_rss_kib']},
        }
