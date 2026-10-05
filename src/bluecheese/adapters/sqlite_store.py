"""Single-process evidence index. Original artifacts remain on disk."""

import hashlib
import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, kind TEXT NOT NULL,
  original_name TEXT NOT NULL, path TEXT NOT NULL, size_bytes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS imports (
  id TEXT PRIMARY KEY, input_artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  config_hash TEXT NOT NULL, status TEXT NOT NULL, sensor_version TEXT,
  started_at TEXT NOT NULL, completed_at TEXT, error TEXT,
  elapsed_seconds REAL, peak_rss_kib INTEGER,
  sensor_elapsed_seconds REAL, sensor_peak_rss_kib INTEGER,
  UNIQUE(input_artifact_id, config_hash)
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, import_id TEXT NOT NULL REFERENCES imports(id),
  artifact_id TEXT NOT NULL REFERENCES artifacts(id), line_number INTEGER NOT NULL,
  timestamp TEXT NOT NULL, sensor TEXT NOT NULL, event_type TEXT NOT NULL,
  src_ip TEXT, src_port INTEGER, dest_ip TEXT, dest_port INTEGER,
  protocol TEXT, community_id TEXT, flow_id TEXT,
  signature_id INTEGER, signature TEXT, severity INTEGER,
  raw_json TEXT NOT NULL,
  UNIQUE(artifact_id, line_number)
);
CREATE INDEX IF NOT EXISTS events_by_import ON events(import_id);
CREATE INDEX IF NOT EXISTS events_by_time ON events(timestamp);
CREATE INDEX IF NOT EXISTS events_by_src ON events(src_ip, timestamp);
CREATE INDEX IF NOT EXISTS events_by_dest ON events(dest_ip, timestamp);
CREATE INDEX IF NOT EXISTS events_by_community ON events(community_id, timestamp);
CREATE TABLE IF NOT EXISTS import_errors (
  import_id TEXT NOT NULL REFERENCES imports(id), artifact_id TEXT NOT NULL,
  line_number INTEGER NOT NULL, error TEXT NOT NULL, raw_line TEXT NOT NULL,
  PRIMARY KEY(import_id, artifact_id, line_number)
);
CREATE TABLE IF NOT EXISTS triage (
  event_id TEXT PRIMARY KEY REFERENCES events(id), priority TEXT NOT NULL,
  disposition TEXT NOT NULL, rationale TEXT NOT NULL,
  evidence_ids_json TEXT NOT NULL, limitations_json TEXT NOT NULL,
  policy_version TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class EvidenceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def get_import(self, import_id):
        row = self.db.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone()
        return dict(row) if row else None

    def get_event(self, event_id):
        row = self.db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return dict(row) if row else None

    def list_alerts(self, import_id=None, limit=100):
        limit = max(1, min(int(limit), 1000))
        if import_id:
            rows = self.db.execute(
                "SELECT * FROM events WHERE event_type='alert' AND import_id=? "
                "ORDER BY timestamp, id LIMIT ?", (import_id, limit)
            )
        else:
            rows = self.db.execute(
                "SELECT * FROM events WHERE event_type='alert' "
                "ORDER BY timestamp, id LIMIT ?", (limit,)
            )
        return [dict(row) for row in rows]

    def related_events(self, alert, limit=20):
        """Only records from the same import; no cross-capture joins."""
        limit = max(1, min(int(limit), 100))
        rows = self.db.execute(
            "SELECT * FROM events WHERE import_id=? AND id<>? "
            "AND abs((julianday(timestamp)-julianday(?))*86400)<=900 AND "
            "((community_id IS NOT NULL AND community_id=?) OR "
            "(flow_id IS NOT NULL AND flow_id=?) OR "
            "(src_ip IS NOT NULL AND (src_ip=? OR src_ip=?)) OR "
            "(dest_ip IS NOT NULL AND (dest_ip=? OR dest_ip=?))) "
            "ORDER BY timestamp, id LIMIT ?",
            (alert['import_id'], alert['id'], alert['timestamp'], alert['community_id'],
             alert['flow_id'], alert['src_ip'], alert['dest_ip'],
             alert['src_ip'], alert['dest_ip'], limit),
        )
        return [dict(row) for row in rows]

    def resolve(self, event_id):
        row = self.db.execute(
            "SELECT e.*, a.path, a.sha256 FROM events e JOIN artifacts a "
            "ON e.artifact_id=a.id WHERE e.id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise KeyError(event_id)
        result = dict(row)
        path = Path(result['path'])
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != result['sha256']:
            raise ValueError(f'Evidence artifact hash mismatch: {path}')
        with path.open('r', encoding='utf-8') as source:
            for number, line in enumerate(source, 1):
                if number == result['line_number']:
                    result['original_record'] = line.rstrip('\n')
                    return result
        raise FileNotFoundError(f"Evidence line {result['line_number']} missing: {path}")

    def save_triage(self, event_id, result, policy_version, created_at):
        self.db.execute(
            "INSERT INTO triage VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(event_id) "
            "DO UPDATE SET priority=excluded.priority, disposition=excluded.disposition, "
            "rationale=excluded.rationale, evidence_ids_json=excluded.evidence_ids_json, "
            "limitations_json=excluded.limitations_json, policy_version=excluded.policy_version, "
            "created_at=excluded.created_at",
            (event_id, result.priority, result.disposition, result.rationale,
             json.dumps(result.evidence_ids), json.dumps(result.limitations),
             policy_version, created_at),
        )
        self.db.commit()
