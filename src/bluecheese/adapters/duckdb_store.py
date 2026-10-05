"""Append-only, scoped evidence store. Runtime owns the connection."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import duckdb

from bluecheese.adapters.suricata import normalize_suricata_event


class EvidenceStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = duckdb.connect(str(path))
        self.db.execute('''CREATE TABLE IF NOT EXISTS evidence (
            seq BIGINT, id VARCHAR PRIMARY KEY, scenario VARCHAR, variant VARCHAR,
            source VARCHAR, position BIGINT, raw VARCHAR, parsed VARCHAR,
            normalized VARCHAR, event_type VARCHAR, src_ip VARCHAR, dest_ip VARCHAR);
            CREATE TABLE IF NOT EXISTS quarantine (
            scenario VARCHAR, variant VARCHAR, source VARCHAR, position BIGINT,
            raw BLOB, error VARCHAR, UNIQUE(scenario, variant, source, position));
            CREATE TABLE IF NOT EXISTS cursors (
            source VARCHAR PRIMARY KEY, identity VARCHAR, offset_bytes BIGINT,
            prefix_hash VARCHAR);''')

    def close(self):
        self.db.close()

    def insert(self, scenario, variant, source, position, raw):
        try:
            parsed = json.loads(raw)
            normalized = asdict(normalize_suricata_event(parsed))
        except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as error:
            self.db.execute('INSERT INTO quarantine VALUES (?, ?, ?, ?, ?, ?) '
                            'ON CONFLICT DO NOTHING',
                            [scenario, variant, source, position, raw, str(error)])
            return None
        event_id = hashlib.sha256(
            f'{scenario}\0{variant}\0{source}\0{position}\0'.encode() + raw
        ).hexdigest()[:24]
        seq = self.snapshot() + 1
        self.db.execute('INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                        'ON CONFLICT DO NOTHING',
                        [seq, event_id, scenario, variant, source, position,
                         raw.decode('utf-8'), json.dumps(parsed), json.dumps(normalized),
                         normalized['event_type'], normalized['src_ip'], normalized['dest_ip']])
        return event_id

    def import_file(self, path, scenario, variant):
        path = Path(path)
        source = 'bundle:' + hashlib.sha256(path.read_bytes()).hexdigest()
        self.db.execute('BEGIN')
        try:
            with path.open('rb') as stream:
                while True:
                    position = stream.tell()
                    raw = stream.readline()
                    if not raw:
                        break
                    self.insert(scenario, variant, source, position, raw)
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def snapshot(self):
        return self.db.execute('SELECT coalesce(max(seq), 0) FROM evidence').fetchone()[0]

    def query(self, scenario, variant, snapshot, clause='TRUE', args=(), limit=100):
        rows = self.db.execute(
            'SELECT seq,id,source,position,raw,parsed,normalized FROM evidence '
            'WHERE scenario=? AND variant=? AND seq<=? AND ' + clause +
            ' ORDER BY seq LIMIT ?',
            [scenario, variant, snapshot, *args, max(1, min(int(limit), 100))]).fetchall()
        return [dict(seq=r[0], id=r[1], source=r[2], position=r[3], raw=r[4],
                     parsed=json.loads(r[5]), normalized=json.loads(r[6])) for r in rows]

    def get_event(self, scenario, variant, snapshot, event_id):
        rows = self.query(scenario, variant, snapshot, 'id=?', [event_id], 1)
        return rows[0] if rows else None

    def list_alerts(self, scenario, variant, snapshot, limit=100):
        return self.query(scenario, variant, snapshot, "event_type='alert'", limit=limit)

    def find_events_by_ip(self, scenario, variant, snapshot, ip, limit=100):
        return self.query(scenario, variant, snapshot, '(src_ip=? OR dest_ip=?)',
                          [ip, ip], limit)

    def search_events(self, scenario, variant, snapshot, event_type, limit=100):
        if event_type not in ('alert', 'flow', 'dns', 'http', 'tls'):
            raise ValueError('Unsupported event type')
        return self.query(scenario, variant, snapshot, 'event_type=?', [event_type], limit)

    def counts(self, scenario, variant):
        accepted = self.db.execute('SELECT count(*) FROM evidence WHERE scenario=? '
                                   'AND variant=?', [scenario, variant]).fetchone()[0]
        invalid = self.db.execute('SELECT count(*) FROM quarantine WHERE scenario=? '
                                  'AND variant=?', [scenario, variant]).fetchone()[0]
        return dict(accepted=accepted, invalid=invalid)
