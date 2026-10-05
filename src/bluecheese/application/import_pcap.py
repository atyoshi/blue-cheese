"""Offline Suricata evidence ingestion with repeatable imports."""

import hashlib
import json
import resource
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from bluecheese.adapters.sqlite_store import EvidenceStore


def utcnow():
    return datetime.now(UTC).isoformat()


def normalize_timestamp(value):
    if not isinstance(value, str):
        raise TypeError('Timestamp must be a string')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'Invalid timestamp: {value}') from exc
    if parsed.tzinfo is None:
        raise ValueError('Timestamp needs a timezone')
    return parsed.astimezone(UTC).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_artifact(db, source, evidence_dir, kind):
    source = Path(source).resolve()
    digest = sha256_file(source)
    artifact_id = f"sha256:{digest}"
    destination = Path(evidence_dir) / 'artifacts' / digest[:2] / digest
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copyfile(source, destination)
    db.execute(
        "INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?,?,?)",
        (artifact_id, digest, kind, source.name, str(destination.resolve()),
         source.stat().st_size),
    )
    db.commit()
    return artifact_id


def _import_id(artifact_id, config):
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    import_id = hashlib.sha256(f'{artifact_id}:{config_hash}'.encode()).hexdigest()[:24]
    return import_id, config_hash


def _ingest_eve(store, eve_path, input_artifact_id, config, sensor_version=None):
    start = time.monotonic()
    import_id, config_hash = _import_id(input_artifact_id, config)
    previous = store.get_import(import_id)
    if previous and previous['status'] == 'complete':
        return summary(store, import_id)

    evidence_id = _copy_artifact(store.db, eve_path, store.path.parent, 'suricata_eve')
    db = store.db
    db.execute(
        "INSERT INTO imports (id,input_artifact_id,config_hash,status,sensor_version,started_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status='processing', "
        "started_at=excluded.started_at, error=NULL",
        (import_id, input_artifact_id, config_hash, 'processing', sensor_version, utcnow()),
    )
    db.execute("DELETE FROM triage WHERE event_id IN (SELECT id FROM events WHERE import_id=?)",
               (import_id,))
    db.execute("DELETE FROM events WHERE import_id=?", (import_id,))
    db.execute("DELETE FROM import_errors WHERE import_id=?", (import_id,))
    db.commit()
    errors = 0
    with Path(eve_path).open(encoding='utf-8', errors='replace') as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict) or not record.get('timestamp') or not record.get('event_type'):
                    raise ValueError('Record needs timestamp and event_type')
                alert = record.get('alert') or {}
                if record['event_type'] == 'alert' and not isinstance(alert, dict):
                    raise ValueError('Alert must be an object')
                timestamp = normalize_timestamp(record['timestamp'])
                event_id = hashlib.sha256(f'{evidence_id}:{line_number}'.encode()).hexdigest()[:24]
                db.execute(
                    "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id, import_id, evidence_id, line_number,
                     timestamp, 'suricata', record['event_type'],
                     record.get('src_ip'), record.get('src_port'),
                     record.get('dest_ip'), record.get('dest_port'),
                     record.get('proto'), record.get('community_id'),
                     str(record['flow_id']) if record.get('flow_id') is not None else None,
                     alert.get('signature_id'), alert.get('signature'),
                     alert.get('severity'), json.dumps(record, sort_keys=True)),
                )
            except (ValueError, TypeError, KeyError) as exc:
                errors += 1
                db.execute(
                    "INSERT INTO import_errors VALUES (?,?,?,?,?)",
                    (import_id, evidence_id, line_number, str(exc), line.rstrip('\n')),
                )
            if line_number % 1000 == 0:
                db.commit()
    db.execute(
        "UPDATE imports SET status=?, completed_at=?, error=?, elapsed_seconds=?, "
        "peak_rss_kib=? WHERE id=?",
        ('incomplete' if errors else 'complete', utcnow(),
         f'{errors} invalid record(s)' if errors else None,
         time.monotonic() - start, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         import_id),
    )
    db.commit()
    return summary(store, import_id)


def summary(store, import_id):
    run = store.get_import(import_id)
    counts = store.db.execute(
        "SELECT COUNT(*) AS events, SUM(CASE WHEN event_type='alert' THEN 1 ELSE 0 END) "
        "AS alerts FROM events WHERE import_id=?", (import_id,)
    ).fetchone()
    errors = store.db.execute(
        "SELECT COUNT(*) FROM import_errors WHERE import_id=?", (import_id,)
    ).fetchone()[0]
    storage_bytes = sum(path.stat().st_size for path in store.path.parent.rglob('*')
                        if path.is_file())
    return {**run, 'events': counts['events'], 'alerts': counts['alerts'] or 0,
            'invalid_records': errors, 'storage_bytes': storage_bytes}


def import_eve(eve_path, evidence_dir):
    eve_path = Path(eve_path)
    with EvidenceStore(Path(evidence_dir) / 'bluecheese.sqlite3') as store:
        input_id = _copy_artifact(store.db, eve_path, evidence_dir, 'suricata_eve')
        return _ingest_eve(store, eve_path, input_id, {'source': 'eve', 'parser': 2})


def validate_pcap(path):
    with Path(path).open('rb') as source:
        magic = source.read(4)
    if magic not in (b'\xd4\xc3\xb2\xa1', b'\xa1\xb2\xc3\xd4',
                     b'\x4d\x3c\xb2\xa1', b'\xa1\xb2\x3c\x4d',
                     b'\x0a\x0d\x0d\x0a'):
        raise ValueError('Input is not a PCAP or PCAPNG file')


def import_pcap(pcap_path, evidence_dir, suricata='suricata', config_path=None,
                rules_path=None, timeout=300):
    pcap_path = Path(pcap_path).resolve()
    validate_pcap(pcap_path)
    executable = shutil.which(suricata)
    if executable is None:
        raise RuntimeError(f'Suricata executable not found: {suricata}')
    version = subprocess.run([executable, '--build-info'], capture_output=True,
                             text=True, timeout=30, check=False).stdout.splitlines()[:1]
    version = version[0] if version else 'unknown'
    config = {'source': 'pcap', 'parser': 2, 'sensor_version': version,
              'config_sha256': sha256_file(config_path) if config_path else None,
              'rules_sha256': sha256_file(rules_path) if rules_path else None}
    with EvidenceStore(Path(evidence_dir) / 'bluecheese.sqlite3') as store:
        input_id = _copy_artifact(store.db, pcap_path, evidence_dir, 'pcap')
        import_id, config_hash = _import_id(input_id, config)
        previous = store.get_import(import_id)
        if previous and previous['status'] == 'complete':
            return summary(store, import_id)
        store.db.execute(
            "INSERT INTO imports (id,input_artifact_id,config_hash,status,sensor_version,started_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status='processing', "
            "started_at=excluded.started_at, error=NULL",
            (import_id, input_id, config_hash, 'processing', version, utcnow()),
        )
        store.db.commit()
        with tempfile.TemporaryDirectory(prefix='bluecheese-suricata-') as output_dir:
            command = [executable, '-r', str(pcap_path), '-l', output_dir]
            if config_path:
                command.extend(['-c', str(Path(config_path).resolve())])
            if rules_path:
                command.extend(['-S', str(Path(rules_path).resolve())])
            try:
                sensor_start = time.monotonic()
                run = subprocess.run(command, capture_output=True, text=True,
                                     timeout=timeout, check=False)
                sensor_elapsed = time.monotonic() - sensor_start
                sensor_peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
                eve = Path(output_dir) / 'eve.json'
                if run.returncode != 0 or not eve.exists():
                    raise RuntimeError((run.stderr or run.stdout or 'No eve.json produced')[-1000:])
                _ingest_eve(store, eve, input_id, config, version)
                store.db.execute(
                    'UPDATE imports SET sensor_elapsed_seconds=?, sensor_peak_rss_kib=? WHERE id=?',
                    (sensor_elapsed, sensor_peak, import_id),
                )
                store.db.commit()
                return summary(store, import_id)
            except (subprocess.TimeoutExpired, RuntimeError) as exc:
                store.db.execute(
                    "UPDATE imports SET status='incomplete', completed_at=?, error=? WHERE id=?",
                    (utcnow(), str(exc)[-1000:], import_id),
                )
                store.db.commit()
                raise
