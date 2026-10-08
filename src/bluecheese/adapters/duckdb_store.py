"""Append-only, scoped evidence store. Runtime owns the connection."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from bluecheese.adapters.demo_schema import migrate
from bluecheese.adapters.suricata import normalize_suricata_event
from bluecheese.application.state_lock import StateLock


class EvidenceStore:
    def __init__(self, path):
        path = Path(path).resolve()
        self.state_lock = StateLock(path.parent)
        try:
            self.db = duckdb.connect(str(path))
        except Exception:
            self.state_lock.close()
            raise
        try:
            self.db.execute("""CREATE TABLE IF NOT EXISTS evidence (
                seq BIGINT, id VARCHAR PRIMARY KEY, scenario VARCHAR, variant VARCHAR,
                source VARCHAR, position BIGINT, raw VARCHAR, parsed VARCHAR,
                normalized VARCHAR, event_type VARCHAR, src_ip VARCHAR, dest_ip VARCHAR);
                CREATE TABLE IF NOT EXISTS quarantine (
                scenario VARCHAR, variant VARCHAR, source VARCHAR, position BIGINT,
                raw BLOB, error VARCHAR, UNIQUE(scenario, variant, source, position));
                CREATE TABLE IF NOT EXISTS cursors (
                source VARCHAR PRIMARY KEY, identity VARCHAR, offset_bytes BIGINT,
                prefix_hash VARCHAR);""")
            migrate(self.db)
            self.db.execute(
                "UPDATE runs SET status='INTERRUPTED', error='Application stopped before run completion' WHERE status='RUNNING'"
            )
        except Exception:
            self.db.close()
            self.state_lock.close()
            raise

    def close(self):
        try:
            self.db.close()
        finally:
            self.state_lock.close()

    def insert(self, scenario, variant, source, position, raw):
        try:
            parsed = json.loads(raw)
            normalized = asdict(normalize_suricata_event(parsed))
        except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as error:
            self.db.execute(
                "INSERT INTO quarantine VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING",
                [scenario, variant, source, position, raw, str(error)],
            )
            return None
        event_id = hashlib.sha256(
            f"{scenario}\0{variant}\0{source}\0{position}\0".encode() + raw
        ).hexdigest()[:24]
        seq = self.snapshot() + 1
        self.db.execute(
            "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT DO NOTHING",
            [
                seq,
                event_id,
                scenario,
                variant,
                source,
                position,
                raw.decode("utf-8"),
                json.dumps(parsed),
                json.dumps(normalized),
                normalized["event_type"],
                normalized["src_ip"],
                normalized["dest_ip"],
            ],
        )
        return event_id

    def import_file(self, path, scenario, variant):
        path = Path(path)
        source = "bundle:" + hashlib.sha256(path.read_bytes()).hexdigest()
        self.db.execute("BEGIN")
        try:
            with path.open("rb") as stream:
                while True:
                    position = stream.tell()
                    raw = stream.readline()
                    if not raw:
                        break
                    self.insert(scenario, variant, source, position, raw)
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def snapshot(self):
        return self.db.execute("SELECT coalesce(max(seq), 0) FROM evidence").fetchone()[
            0
        ]

    def query(
        self,
        scenario,
        variant,
        snapshot,
        clause="TRUE",
        args=(),
        limit=100,
        newest_first=False,
        snapshot_id=None,
    ):
        table = "snapshot_evidence" if snapshot_id else "evidence"
        membership = "snapshot_id=? AND " if snapshot_id else ""
        rows = self.db.execute(
            "SELECT seq,id,source,position,raw,parsed,normalized FROM "
            + table
            + " "
            + "WHERE "
            + membership
            + "scenario=? AND variant=? AND seq<=? AND "
            + clause
            + (
                " ORDER BY seq DESC LIMIT ?"
                if newest_first
                else " ORDER BY seq LIMIT ?"
            ),
            [
                *([snapshot_id] if snapshot_id else []),
                scenario,
                variant,
                snapshot,
                *args,
                max(1, min(int(limit), 100)),
            ],
        ).fetchall()
        return [
            {
                "seq": r[0],
                "id": r[1],
                "source": r[2],
                "position": r[3],
                "raw": r[4],
                "parsed": json.loads(r[5]),
                "normalized": json.loads(r[6]),
            }
            for r in rows
        ]

    def get_event(self, scenario, variant, snapshot, event_id, *, snapshot_id=None):
        rows = self.query(
            scenario, variant, snapshot, "id=?", [event_id], 1, snapshot_id=snapshot_id
        )
        return rows[0] if rows else None

    def list_alerts(self, scenario, variant, snapshot, limit=100, *, snapshot_id=None):
        return self.query(
            scenario,
            variant,
            snapshot,
            "event_type='alert'",
            limit=limit,
            snapshot_id=snapshot_id,
        )

    def find_events_by_ip(
        self, scenario, variant, snapshot, ip, limit=100, *, snapshot_id=None
    ):
        return self.query(
            scenario,
            variant,
            snapshot,
            "(src_ip=? OR dest_ip=?)",
            [ip, ip],
            limit,
            snapshot_id=snapshot_id,
        )

    def search_events(
        self, scenario, variant, snapshot, event_type, limit=100, *, snapshot_id=None
    ):
        if event_type not in ("alert", "flow", "dns", "http", "tls"):
            raise ValueError("Unsupported event type")
        return self.query(
            scenario,
            variant,
            snapshot,
            "event_type=?",
            [event_type],
            limit,
            snapshot_id=snapshot_id,
        )

    def counts(self, scenario, variant):
        accepted = self.db.execute(
            "SELECT count(*) FROM evidence WHERE scenario=? AND variant=?",
            [scenario, variant],
        ).fetchone()[0]
        invalid = self.db.execute(
            "SELECT count(*) FROM quarantine WHERE scenario=? AND variant=?",
            [scenario, variant],
        ).fetchone()[0]
        return {"accepted": accepted, "invalid": invalid}

    def create_run(
        self, scenario, variant, question, parent_run_id=None, max_members=10000
    ):
        """Freeze current scoped interpretations and create durable pending work atomically."""
        if (
            not isinstance(question, str)
            or not question.strip()
            or len(question) > 4096
        ):
            raise ValueError(
                "Case question must be nonempty and at most 4096 characters"
            )
        case_id = hashlib.sha256(
            json.dumps([scenario, variant, question]).encode()
        ).hexdigest()[:24]
        snapshot_id, run_id = uuid4().hex, uuid4().hex
        created = datetime.now(UTC).isoformat()
        self.db.execute("BEGIN")
        try:
            if parent_run_id:
                parent = self.db.execute(
                    "SELECT case_id,status FROM runs WHERE run_id=?", [parent_run_id]
                ).fetchone()
                if not parent or parent[0] != case_id or parent[1] == "RUNNING":
                    raise ValueError(
                        "Parent run must be a terminal run in the same case"
                    )
            if self.db.execute(
                "SELECT count(*) FROM runs WHERE case_id=? AND status='RUNNING'",
                [case_id],
            ).fetchone()[0]:
                raise ValueError("Case already has an active run")
            watermark = self.snapshot()
            members = self.db.execute(
                "SELECT id,normalized FROM evidence WHERE scenario=? AND variant=? AND seq<=? ORDER BY id LIMIT ?",
                [scenario, variant, watermark, max_members + 1],
            ).fetchall()
            if len(members) > max_members:
                raise ValueError(
                    "Case exceeds snapshot member cap; narrow the case scope"
                )
            snapshot_digest = hashlib.sha256(
                json.dumps(
                    [
                        (
                            event_id,
                            hashlib.sha256(
                                json.dumps(
                                    json.loads(normalized),
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ).encode()
                            ).hexdigest(),
                        )
                        for event_id, normalized in members
                    ],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            previous = self.db.execute(
                "SELECT revision FROM cases WHERE case_id=?", [case_id]
            ).fetchone()
            revision = previous[0] + 1 if previous else 1
            self.db.execute(
                "INSERT INTO cases VALUES (?, ?, ?, ?, ?, 'INVESTIGATING') ON CONFLICT(case_id) DO UPDATE SET revision=excluded.revision,status=excluded.status",
                [case_id, scenario, variant, question, revision],
            )
            self.db.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    snapshot_id,
                    case_id,
                    revision,
                    scenario,
                    variant,
                    watermark,
                    snapshot_digest,
                    created,
                    question,
                ],
            )
            self.db.execute(
                "INSERT INTO snapshot_evidence SELECT ?, * FROM evidence WHERE scenario=? AND variant=? AND seq<=?",
                [snapshot_id, scenario, variant, watermark],
            )
            self.db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, 'RUNNING', ?, NULL, NULL, NULL)",
                [run_id, case_id, snapshot_id, parent_run_id, created],
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return {
            "run_id": run_id,
            "case_id": case_id,
            "case_revision": revision,
            "snapshot_id": snapshot_id,
            "snapshot": watermark,
            "snapshot_digest": snapshot_digest,
            "scope_question": question,
            "parent_run_id": parent_run_id,
            "created_at": created,
        }

    def record_tool(self, run_id, activity):
        status = self.db.execute(
            "SELECT status FROM runs WHERE run_id=?", [run_id]
        ).fetchone()
        if not status or status[0] != "RUNNING":
            raise ValueError("Cannot record tool activity for an inactive run")
        ordinal = self.db.execute(
            "SELECT count(*) FROM tool_calls WHERE run_id=?", [run_id]
        ).fetchone()[0]
        self.db.execute(
            "INSERT INTO tool_calls VALUES (?, ?, ?)",
            [run_id, ordinal, json.dumps(activity)],
        )

    def finish_run(self, run_id, status, report=None, error=None):
        if status not in {"COMPLETED", "INCOMPLETE", "CANCELLED", "FAILED"}:
            raise ValueError("Invalid terminal run status")
        self.db.execute("BEGIN")
        try:
            row = self.db.execute(
                "SELECT case_id,status FROM runs WHERE run_id=?", [run_id]
            ).fetchone()
            if not row or row[1] != "RUNNING":
                raise ValueError("Run has already finished or does not exist")
            self.db.execute(
                "UPDATE runs SET status=?,finished_at=?,report=?,error=? WHERE run_id=?",
                [
                    status,
                    datetime.now(UTC).isoformat(),
                    json.dumps(report) if report else None,
                    error,
                    run_id,
                ],
            )
            self.db.execute(
                "UPDATE cases SET status='NEEDS_REVIEW' WHERE case_id=?", [row[0]]
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def list_runs(self, scenario, variant, limit=100):
        rows = self.db.execute(
            "SELECT r.run_id,r.status,s.revision,r.created_at,r.parent_run_id,s.snapshot_id FROM runs r JOIN snapshots s ON r.snapshot_id=s.snapshot_id WHERE s.scenario=? AND s.variant=? ORDER BY r.created_at DESC,r.run_id LIMIT ?",
            [scenario, variant, max(1, min(int(limit), 100))],
        ).fetchall()
        return [
            dict(
                zip(
                    (
                        "run_id",
                        "status",
                        "case_revision",
                        "created_at",
                        "parent_run_id",
                        "snapshot_id",
                    ),
                    row,
                )
            )
            for row in rows
        ]

    def get_run(self, scenario, variant, run_id):
        row = self.db.execute(
            "SELECT r.status,r.report,r.error FROM runs r JOIN snapshots s ON r.snapshot_id=s.snapshot_id WHERE r.run_id=? AND s.scenario=? AND s.variant=?",
            [run_id, scenario, variant],
        ).fetchone()
        if not row:
            return None
        trace = self.db.execute(
            "SELECT activity FROM tool_calls WHERE run_id=? ORDER BY ordinal", [run_id]
        ).fetchall()
        return {
            "run_id": run_id,
            "status": row[0],
            "report": json.loads(row[1]) if row[1] else None,
            "error": row[2],
            "tool_activity": [json.loads(call[0]) for call in trace],
        }

    def snapshot_manifest(self, snapshot_id):
        row = self.db.execute(
            "SELECT case_id,revision,scenario,variant,watermark,digest FROM snapshots WHERE snapshot_id=?",
            [snapshot_id],
        ).fetchone()
        if not row:
            raise ValueError("Snapshot does not exist")
        members = self.db.execute(
            "SELECT id,normalized FROM snapshot_evidence WHERE snapshot_id=? ORDER BY id LIMIT 10001",
            [snapshot_id],
        ).fetchall()
        if len(members) > 10000:
            raise ValueError("Stored snapshot exceeds membership limit")
        return {
            "snapshot_id": snapshot_id,
            "case_id": row[0],
            "case_revision": row[1],
            "scenario": row[2],
            "variant": row[3],
            "snapshot": row[4],
            "digest": row[5],
            "parser_version": "suricata-canonical-v1",
            "members": [
                [
                    event_id,
                    hashlib.sha256(
                        json.dumps(
                            json.loads(normalized),
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest(),
                ]
                for event_id, normalized in members
            ],
        }
