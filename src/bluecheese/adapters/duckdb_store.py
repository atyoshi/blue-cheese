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
            self.db.execute("""UPDATE decision_advice
                SET assessment=json_merge_patch(assessment,
                    '{"status":"INTERRUPTED","failure_reason":"Runtime stopped before advice completion"}')
                WHERE run_id IN (SELECT run_id FROM runs WHERE status='INTERRUPTED')
                AND json_extract_string(assessment, '$.status')='STARTED'""")
            self.db.execute(
                "UPDATE investigation_work SET status='INTERRUPTED', error='Runtime stopped during scheduled work; retry explicitly' WHERE status='RUNNING'"
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
        if self.db.execute(
            "SELECT 1 FROM retention_tombstones WHERE event_id=?", [event_id]
        ).fetchone():
            return None
        if self.db.execute("SELECT 1 FROM evidence WHERE id=?", [event_id]).fetchone():
            return event_id
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
        self.db.execute("UPDATE evidence_watermark SET seq=? WHERE singleton=1", [seq])
        if (
            scenario == "live"
            and variant == "external"
            and normalized["event_type"] == "alert"
        ):
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                "INSERT INTO investigation_work VALUES (?, 'QUEUED', NULL, ?, ?, NULL) ON CONFLICT DO NOTHING",
                [event_id, now, now],
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
        return self.db.execute(
            "SELECT seq FROM evidence_watermark WHERE singleton=1"
        ).fetchone()[0]

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
        related_first=False,
        diverse_first=False,
    ):
        table = "snapshot_evidence" if snapshot_id else "evidence"
        membership = "snapshot_id=? AND " if snapshot_id else ""
        select = "SELECT seq,id,source,position,raw,parsed,normalized FROM "
        if diverse_first:
            select = """WITH scoped AS (SELECT * FROM """
        sql = (
            select
            + table
            + " "
            + "WHERE "
            + membership
            + "scenario=? AND variant=? AND seq<=? AND "
            + clause
            + (
                """), distinct_context AS (
                    SELECT *,row_number() OVER (
                        PARTITION BY event_type,src_ip,dest_ip,
                        json_extract_string(normalized,'$.protocol_details.http_method'),
                        json_extract_string(normalized,'$.protocol_details.url'),
                        json_extract_string(normalized,'$.protocol_details.queries'),
                        json_extract_string(normalized,'$.protocol_details.sni')
                        ORDER BY seq) AS duplicate_rank FROM scoped), ranked AS (
                    SELECT *,row_number() OVER (PARTITION BY event_type
                        ORDER BY duplicate_rank,seq) AS protocol_rank FROM distinct_context)
                    SELECT seq,id,source,position,raw,parsed,normalized FROM ranked
                    ORDER BY protocol_rank,CASE event_type WHEN 'http' THEN 0
                        WHEN 'flow' THEN 1 WHEN 'dns' THEN 2 WHEN 'tls' THEN 3 ELSE 4 END,seq LIMIT ?"""
                if diverse_first
                else " ORDER BY CASE event_type WHEN 'flow' THEN 0 WHEN 'http' THEN 1 WHEN 'dns' THEN 2 WHEN 'tls' THEN 3 ELSE 4 END,seq LIMIT ?"
                if related_first
                else " ORDER BY seq DESC LIMIT ?"
                if newest_first
                else " ORDER BY seq LIMIT ?"
            )
        )
        rows = self.db.execute(
            sql,
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

    def find_related_events(
        self,
        scenario,
        variant,
        snapshot,
        seed_id,
        event_types,
        limit=100,
        *,
        snapshot_id=None,
    ):
        """Filter before limiting; the seed and every result belong to one snapshot."""
        if (
            not isinstance(event_types, list)
            or not 1 <= len(event_types) <= 5
            or any(
                kind not in ("alert", "flow", "dns", "http", "tls")
                for kind in event_types
            )
        ):
            raise ValueError("Unsupported related event types")
        seed = self.get_event(
            scenario, variant, snapshot, seed_id, snapshot_id=snapshot_id
        )
        if seed is None:
            raise ValueError("Related-event seed is outside the fixed snapshot")
        n = seed["normalized"]
        try:
            timestamp = datetime.fromisoformat(n["timestamp"])
            if timestamp.tzinfo is None:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            return []
        clause = """source=? AND json_extract_string(normalized,'$.sensor') IS NOT DISTINCT FROM ?
            AND src_ip=? AND dest_ip=?
            AND abs(epoch(try_cast(json_extract_string(normalized,'$.timestamp') AS TIMESTAMPTZ))-?)<=300
            AND (json_extract_string(normalized,'$.flow_id')=? OR
                (json_extract_string(normalized,'$.src_port')=? AND
                 json_extract_string(normalized,'$.dest_port')=? AND
                 json_extract_string(normalized,'$.protocol')=?))
            AND event_type IN (SELECT unnest(?))"""
        return self.query(
            scenario,
            variant,
            snapshot,
            clause,
            [
                seed["source"],
                n.get("sensor"),
                n.get("src_ip"),
                n.get("dest_ip"),
                timestamp.timestamp(),
                str(n["flow_id"]) if n.get("flow_id") is not None else None,
                str(n["src_port"]) if n.get("src_port") is not None else None,
                str(n["dest_port"]) if n.get("dest_port") is not None else None,
                n.get("protocol"),
                event_types,
            ],
            limit,
            snapshot_id=snapshot_id,
            related_first=True,
        )

    def find_host_context(
        self, scenario, variant, snapshot, seed_id, limit=24, *, snapshot_id=None
    ):
        """Diverse host observations inside the authorized snapshot, never causal links."""
        seed = self.get_event(
            scenario, variant, snapshot, seed_id, snapshot_id=snapshot_id
        )
        if seed is None or not seed["normalized"].get("src_ip"):
            raise ValueError("Host-context seed is outside the fixed snapshot")
        n = seed["normalized"]
        timestamp = datetime.fromisoformat(n["timestamp"])
        if timestamp.tzinfo is None:
            raise ValueError("Host context requires a timezone-aware seed")
        return self.query(
            scenario,
            variant,
            snapshot,
            """source=? AND json_extract_string(normalized,'$.sensor') IS NOT DISTINCT FROM ?
                AND (src_ip=? OR dest_ip=?)
                AND abs(epoch(try_cast(json_extract_string(normalized,'$.timestamp') AS TIMESTAMPTZ))-?)<=300
                AND event_type IN ('http','flow','dns','tls')""",
            [
                seed["source"],
                n.get("sensor"),
                n["src_ip"],
                n["src_ip"],
                timestamp.timestamp(),
            ],
            limit,
            snapshot_id=snapshot_id,
            diverse_first=True,
        )

    def record_provider(self, run_id, activity):
        self.db.execute(
            "INSERT INTO provider_diagnostics VALUES (?,?) ON CONFLICT(run_id) DO UPDATE SET activity=excluded.activity",
            [run_id, json.dumps(activity, allow_nan=False)],
        )

    def get_provider(self, run_id):
        row = self.db.execute(
            "SELECT activity FROM provider_diagnostics WHERE run_id=?", [run_id]
        ).fetchone()
        return json.loads(row[0]) if row else None

    def telemetry_coverage(self, scenario, variant, snapshot, *, snapshot_id=None):
        table = "snapshot_evidence" if snapshot_id else "evidence"
        where = "scenario=? AND variant=? AND seq<=?"
        args = [scenario, variant, snapshot]
        if snapshot_id:
            where += " AND snapshot_id=?"
            args.append(snapshot_id)
        counts = dict(
            self.db.execute(
                "SELECT event_type,count(*) FROM "
                + table
                + " WHERE "
                + where
                + " GROUP BY event_type",
                args,
            ).fetchall()
        )
        rejected = self.db.execute(
            "SELECT error,count(*) FROM quarantine WHERE scenario=? AND variant=? GROUP BY error ORDER BY count(*) DESC LIMIT 20",
            [scenario, variant],
        ).fetchall()
        times = self.db.execute(
            "SELECT epoch(min(try_cast(json_extract_string(normalized, '$.timestamp') AS TIMESTAMPTZ))),epoch(max(try_cast(json_extract_string(normalized, '$.timestamp') AS TIMESTAMPTZ))) FROM "
            + table
            + " WHERE "
            + where,
            args,
        ).fetchone()
        return {
            "time_window": [
                datetime.fromtimestamp(t, UTC).isoformat() if t is not None else None
                for t in times
            ],
            "accepted_types": counts,
            "quarantine_reasons": [
                {"reason": reason, "count": count} for reason, count in rejected
            ],
            "quarantine_scope": "Workspace ingestion history; quarantine is not frozen with the investigation.",
        }

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

    def telemetry_totals(self, scenario, variant):
        """Operational counters; no latest-N cutoff and no investigation retrieval."""
        row = self.db.execute(
            "SELECT count(*), count(*) FILTER (WHERE event_type='alert'), "
            "count(*) FILTER (WHERE event_type='flow') FROM evidence "
            "WHERE scenario=? AND variant=?",
            [scenario, variant],
        ).fetchone()
        return dict(zip(("accepted", "alerts", "flows"), row))

    def browse_telemetry(
        self,
        scenario,
        variant,
        snapshot,
        *,
        event_type="alert",
        ip="",
        signature="",
        severity=None,
        before=None,
        page=1,
    ):
        """Bounded analyst search, independent of provider retrieval/citations."""
        if event_type not in ("all", "alert", "flow"):
            raise ValueError("Unsupported event type")
        clauses = ["scenario=?", "variant=?", "seq<=?"]
        args = [scenario, variant, snapshot]
        if before is not None:
            clauses.append("seq<?")
            args.append(int(before))
        if event_type != "all":
            clauses.append("event_type=?")
            args.append(event_type)
        if ip:
            clauses.append("(src_ip=? OR dest_ip=?)")
            args.extend([ip, ip])
        if signature:
            clauses.append(
                "contains(lower(json_extract_string(normalized, '$.alert_signature')), lower(?))"
            )
            args.append(signature[:512])
        if severity is not None:
            clauses.append(
                "try_cast(json_extract_string(normalized, '$.severity') AS INTEGER)=?"
            )
            args.append(int(severity))
        where = " AND ".join(clauses)
        total = self.db.execute(
            "SELECT count(*) FROM evidence WHERE " + where, args
        ).fetchone()[0]
        page = max(1, min(int(page), max(1, (total + 49) // 50)))
        rows = self.db.execute(
            "SELECT seq,id,source,normalized FROM evidence WHERE "
            + where
            + " ORDER BY seq DESC LIMIT 50 OFFSET ?",
            [*args, (page - 1) * 50],
        ).fetchall()
        return {
            "total": total,
            "page": page,
            "rows": [
                {
                    "sequence": seq,
                    "id": event_id,
                    "source": source,
                    **json.loads(normalized),
                }
                for seq, event_id, source, normalized in rows
            ],
        }

    def visual_telemetry(self, scenario, variant, snapshot, limit=1000):
        """Bounded normalized rows for analyst visuals, never provider retrieval."""
        limit = max(1, min(int(limit), 5000))
        rows = self.db.execute(
            "SELECT seq,id,normalized FROM evidence "
            "WHERE scenario=? AND variant=? AND seq<=? ORDER BY seq DESC LIMIT ?",
            [scenario, variant, snapshot, limit],
        ).fetchall()
        return [
            {"sequence": seq, "id": event_id, **json.loads(normalized)}
            for seq, event_id, normalized in rows
        ]

    def quarantine_records(self, scenario, variant):
        rows = self.db.execute(
            "SELECT source,position,error FROM quarantine WHERE scenario=? AND variant=? ORDER BY source,position DESC LIMIT 50",
            [scenario, variant],
        ).fetchall()
        return [dict(zip(("source", "position", "error"), row)) for row in rows]

    def add_analyst_action(self, scenario, variant, run_id, actor, disposition, note):
        if disposition not in (
            "OPEN",
            "INVESTIGATING",
            "ESCALATED",
            "CLOSED_BENIGN",
            "CLOSED_INCIDENT",
        ):
            raise ValueError("Unknown analyst disposition")
        if (
            not isinstance(note, str)
            or len(note) > 8192
            or not actor.strip()
            or len(actor) > 128
        ):
            raise ValueError("Actor and note exceed the allowed limits")
        row = self.db.execute(
            "SELECT r.case_id FROM runs r JOIN cases c ON r.case_id=c.case_id WHERE r.run_id=? AND c.scenario=? AND c.variant=?",
            [run_id, scenario, variant],
        ).fetchone()
        if not row:
            raise ValueError("Run outside selected scope")
        self.db.execute(
            "INSERT INTO analyst_actions VALUES (?, ?, ?, ?, ?, ?)",
            [
                uuid4().hex,
                row[0],
                datetime.now(UTC).isoformat(),
                actor,
                disposition,
                note,
            ],
        )

    def analyst_history(self, scenario, variant, run_id):
        rows = self.db.execute(
            "SELECT a.created_at,a.actor,a.disposition,a.note FROM analyst_actions a JOIN runs r ON r.case_id=a.case_id JOIN cases c ON c.case_id=a.case_id WHERE r.run_id=? AND c.scenario=? AND c.variant=? ORDER BY a.created_at DESC LIMIT 100",
            [run_id, scenario, variant],
        ).fetchall()
        return [
            dict(zip(("created_at", "actor", "disposition", "note"), row))
            for row in rows
        ]

    def record_source_incident(self, source, offset, diagnostic):
        self.db.execute(
            "INSERT INTO source_incidents VALUES (?, ?, ?, ?, ?)",
            [
                uuid4().hex,
                source,
                datetime.now(UTC).isoformat(),
                offset,
                str(diagnostic)[:4096],
            ],
        )

    def source_incidents(self):
        return [
            dict(zip(("source", "created_at", "committed_offset", "diagnostic"), row))
            for row in self.db.execute(
                "SELECT source,created_at,committed_offset,diagnostic FROM source_incidents ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        ]

    def case_source_incidents(self, snapshot_id):
        sources = [
            row[0]
            for row in self.db.execute(
                "SELECT DISTINCT source FROM snapshot_evidence WHERE snapshot_id=?",
                [snapshot_id],
            ).fetchall()
        ]
        return [
            incident
            for incident in self.source_incidents()
            if any(
                source == incident["source"]
                or source == "file:" + incident["source"]
                or source.startswith("file:" + incident["source"] + "@")
                for source in sources
            )
        ]

    def claim_work(self):
        self.db.execute("BEGIN")
        try:
            row = self.db.execute(
                "SELECT event_id FROM investigation_work WHERE status='QUEUED' ORDER BY created_at,event_id LIMIT 1"
            ).fetchone()
            if row:
                self.db.execute(
                    "UPDATE investigation_work SET status='RUNNING',updated_at=? WHERE event_id=?",
                    [datetime.now(UTC).isoformat(), row[0]],
                )
            self.db.execute("COMMIT")
            return row[0] if row else None
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def finish_work(self, event_id, status, run_id=None, error=None):
        if status not in ("COMPLETED", "FAILED", "INCOMPLETE", "CANCELLED"):
            raise ValueError("Invalid scheduled work status")
        self.db.execute(
            "UPDATE investigation_work SET status=?,run_id=?,error=?,updated_at=? WHERE event_id=? AND status='RUNNING'",
            [
                status,
                run_id,
                str(error)[:4096] if error else None,
                datetime.now(UTC).isoformat(),
                event_id,
            ],
        )

    def work_queue(self):
        return [
            dict(
                zip(
                    (
                        "event_id",
                        "status",
                        "run_id",
                        "created_at",
                        "updated_at",
                        "error",
                    ),
                    row,
                )
            )
            for row in self.db.execute(
                "SELECT * FROM investigation_work ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        ]

    def retry_work(self, event_id):
        self.db.execute(
            "UPDATE investigation_work SET status='QUEUED',error=NULL,updated_at=? WHERE event_id=? AND status IN ('FAILED','INTERRUPTED','CANCELLED','INCOMPLETE')",
            [datetime.now(UTC).isoformat(), event_id],
        )

    def retention(self, before_sequence, *, apply=False):
        """Explicit bounded pruning; snapshots and work references pin evidence."""
        cutoff = int(before_sequence)
        if cutoff < 0:
            raise ValueError("Retention cutoff must be nonnegative")
        predicate = "e.seq<? AND NOT EXISTS (SELECT 1 FROM snapshot_evidence s WHERE s.id=e.id) AND NOT EXISTS (SELECT 1 FROM investigation_work w WHERE w.event_id=e.id)"
        self.db.execute("BEGIN")
        try:
            total = self.db.execute(
                "SELECT count(*) FROM evidence e WHERE " + predicate, [cutoff]
            ).fetchone()[0]
            rows = self.db.execute(
                "SELECT id,seq FROM evidence e WHERE "
                + predicate
                + " ORDER BY seq LIMIT 1000",
                [cutoff],
            ).fetchall()
            operation_id = uuid4().hex if apply else None
            if apply:
                now = datetime.now(UTC).isoformat()
                for event_id, seq in rows:
                    self.db.execute(
                        "INSERT INTO retention_tombstones VALUES (?, ?, ?, ?)",
                        [event_id, seq, now, operation_id],
                    )
                    self.db.execute("DELETE FROM evidence WHERE id=?", [event_id])
                self.db.execute(
                    "INSERT INTO retention_operations VALUES (?, ?, ?, ?)",
                    [operation_id, now, cutoff, len(rows)],
                )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return {
            "apply": apply,
            "operation_id": operation_id,
            "before_sequence": cutoff,
            "eligible": total,
            "batch_count": len(rows),
            "batch_cap": 1000,
            "removed": len(rows) if apply else 0,
            "event_ids": [row[0] for row in rows],
            "policy": "All snapshot members and work references remain pinned; report closure does not unpin.",
        }

    def create_run(
        self,
        scenario,
        variant,
        question,
        parent_run_id=None,
        max_members=10000,
        seed_event_id=None,
        investigation_scope="connection",
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
        if investigation_scope not in ("connection", "host"):
            raise ValueError("Investigation scope must be connection or host")
        if investigation_scope == "host" and not seed_event_id:
            raise ValueError("Host investigation requires a selected alert")
        identity = [scenario, variant, question]
        if investigation_scope == "host":
            identity.append("host")
        if seed_event_id:
            identity.append(seed_event_id)
        case_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
        snapshot_id, run_id = uuid4().hex, uuid4().hex
        created = datetime.now(UTC).isoformat()
        self.db.execute("BEGIN")
        try:
            if parent_run_id:
                parent = self.db.execute(
                    "SELECT r.case_id,r.status,s.scenario,s.variant,rc.seed_event_id,rc.investigation_scope FROM runs r JOIN snapshots s ON s.snapshot_id=r.snapshot_id LEFT JOIN run_context rc ON rc.run_id=r.run_id WHERE r.run_id=?",
                    [parent_run_id],
                ).fetchone()
                if (
                    not parent
                    or parent[1] == "RUNNING"
                    or tuple(parent[2:4]) != (scenario, variant)
                    or parent[4] != seed_event_id
                    or (parent[5] or "connection") != investigation_scope
                ):
                    raise ValueError(
                        "Parent run must be a terminal run in the same case"
                    )
                case_id = parent[0]
            if self.db.execute(
                "SELECT count(*) FROM runs WHERE case_id=? AND status='RUNNING'",
                [case_id],
            ).fetchone()[0]:
                raise ValueError("Case already has an active run")
            watermark = self.snapshot()
            member_where = "scenario=? AND variant=? AND seq<=?"
            member_args = [scenario, variant, watermark]
            if seed_event_id:
                seed = self.get_event(scenario, variant, watermark, seed_event_id)
                if not seed or seed["normalized"]["event_type"] != "alert":
                    raise ValueError("Select an alert in the current external scope")
                n = seed["normalized"]
                if investigation_scope == "host" and not n.get("src_ip"):
                    raise ValueError("Host investigation requires a source IP")
                timestamp = datetime.fromisoformat(n["timestamp"])
                if timestamp.tzinfo is None:
                    raise ValueError(
                        "Scoped investigation requires a timezone-aware alert"
                    )
                # Same source generation, directional endpoints and a five-minute window.
                endpoints = (
                    "(src_ip=? OR dest_ip=?)"
                    if investigation_scope == "host"
                    else "(src_ip=? AND dest_ip=?)"
                )
                member_where += (
                    " AND source=? AND (id=? OR ("
                    + endpoints
                    + " AND abs(epoch(try_cast(json_extract_string(normalized, '$.timestamp') AS TIMESTAMPTZ)) - ?) <= 300))"
                )
                member_args.extend(
                    [
                        seed["source"],
                        seed_event_id,
                        n["src_ip"],
                        n["src_ip"] if investigation_scope == "host" else n["dest_ip"],
                        timestamp.timestamp(),
                    ]
                )
                if investigation_scope == "host":
                    member_where += " AND json_extract_string(normalized,'$.sensor') IS NOT DISTINCT FROM ?"
                    member_args.append(n.get("sensor"))
            members = self.db.execute(
                "SELECT id,normalized FROM evidence WHERE "
                + member_where
                + " ORDER BY id LIMIT ?",
                [*member_args, max_members + 1],
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
                "INSERT INTO snapshot_evidence SELECT ?, * FROM evidence WHERE "
                + member_where,
                [snapshot_id, *member_args],
            )
            self.db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, 'RUNNING', ?, NULL, NULL, NULL)",
                [run_id, case_id, snapshot_id, parent_run_id, created],
            )
            self.db.execute(
                "INSERT INTO run_context (run_id,seed_event_id,investigation_scope) VALUES (?, ?, ?)",
                [run_id, seed_event_id, investigation_scope],
            )
            title = question[:180]
            if seed_event_id:
                title = f"{n.get('src_ip') or 'Unknown endpoint'} → {n.get('dest_ip') or '?'} · {n.get('alert_signature') or 'Alert review'}"[
                    :240
                ]
                if investigation_scope == "host":
                    title = f"{n['src_ip']} · Host investigation · {n.get('alert_signature') or 'Alert review'}"[
                        :240
                    ]
            self.db.execute(
                "INSERT INTO case_workspace VALUES (?, ?, '', 'OPEN', ?) ON CONFLICT DO NOTHING",
                [case_id, title, created],
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
            "seed_event_id": seed_event_id,
            "investigation_scope": investigation_scope,
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

    def save_decision_advice(self, run_id, advice):
        row = self.db.execute(
            "SELECT snapshot_id FROM runs WHERE run_id=? AND status='RUNNING'", [run_id]
        ).fetchone()
        if not row or advice["scope"]["snapshot_id"] != row[0]:
            raise ValueError("Decision advice must belong to an active run snapshot")
        self.db.execute(
            "INSERT INTO decision_advice VALUES (?, ?, ?) ON CONFLICT(run_id) DO UPDATE SET assessment=excluded.assessment",
            [run_id, row[0], json.dumps(advice, allow_nan=False)],
        )

    def get_decision_advice(self, scenario, variant, run_id):
        row = self.db.execute(
            "SELECT d.assessment FROM decision_advice d JOIN snapshots s ON d.snapshot_id=s.snapshot_id WHERE d.run_id=? AND s.scenario=? AND s.variant=?",
            [run_id, scenario, variant],
        ).fetchone()
        return json.loads(row[0]) if row else None

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
            "SELECT r.run_id,r.status,s.revision,r.created_at,r.parent_run_id,s.snapshot_id,s.question,w.title,w.owner,w.disposition,r.case_id FROM runs r JOIN snapshots s ON r.snapshot_id=s.snapshot_id LEFT JOIN case_workspace w ON w.case_id=r.case_id WHERE s.scenario=? AND s.variant=? ORDER BY r.created_at DESC,r.run_id LIMIT ?",
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
                        "question",
                        "title",
                        "owner",
                        "disposition",
                        "case_id",
                    ),
                    row,
                )
            )
            for row in rows
        ]

    def get_run(self, scenario, variant, run_id):
        row = self.db.execute(
            "SELECT r.status,r.report,r.error,s.question,s.snapshot_id,s.watermark,r.case_id,w.title,w.owner,w.disposition,rc.seed_event_id,r.created_at,rc.investigation_scope FROM runs r JOIN snapshots s ON r.snapshot_id=s.snapshot_id LEFT JOIN case_workspace w ON w.case_id=r.case_id LEFT JOIN run_context rc ON rc.run_id=r.run_id WHERE r.run_id=? AND s.scenario=? AND s.variant=?",
            [run_id, scenario, variant],
        ).fetchone()
        if not row:
            return None
        trace = self.db.execute(
            "SELECT activity FROM tool_calls WHERE run_id=? ORDER BY ordinal", [run_id]
        ).fetchall()
        pairs = self.db.execute(
            "SELECT coalesce(src_ip,'Unknown'),coalesce(dest_ip,'Unknown'),count(*) FROM snapshot_evidence WHERE snapshot_id=? GROUP BY 1,2 ORDER BY 3 DESC,1,2 LIMIT 4",
            [row[4]],
        ).fetchall()
        record_count, pair_count = self.db.execute(
            "SELECT count(*),count(DISTINCT (src_ip,dest_ip)) FROM snapshot_evidence WHERE snapshot_id=?",
            [row[4]],
        ).fetchone()
        seed = (
            self.get_event(scenario, variant, row[5], row[10], snapshot_id=row[4])
            if row[10]
            else None
        )
        return {
            "question": row[3],
            "snapshot_id": row[4],
            "snapshot": row[5],
            "case_id": row[6],
            "title": row[7] or row[3],
            "owner": row[8] or "",
            "disposition": row[9] or "OPEN",
            "seed_event_id": row[10],
            "created_at": row[11],
            "investigation_scope": row[12] or "connection",
            "target_host": seed["normalized"].get("src_ip") if seed else None,
            "workflow_activity": self.run_events(scenario, variant, run_id),
            "record_count": record_count,
            "pair_count": pair_count,
            "pairs": [
                dict(zip(("source", "destination", "records"), pair)) for pair in pairs
            ],
            "run_id": run_id,
            "status": row[0],
            "report": json.loads(row[1]) if row[1] else None,
            "error": row[2],
            "tool_activity": [json.loads(call[0]) for call in trace],
            "decision_advice": self.get_decision_advice(scenario, variant, run_id),
            "provider_diagnostics": self.get_provider(run_id),
        }

    def attention(self, scenario, variant, snapshot, page=1):
        """Priority-ranked pages; no older alert is hidden by a latest-N cutoff."""
        page = max(1, int(page))
        total = self.db.execute(
            "SELECT count(*) FROM evidence WHERE scenario=? AND variant=? AND seq<=? AND event_type='alert'",
            [scenario, variant, snapshot],
        ).fetchone()[0]
        page = min(page, max(1, (total + 19) // 20))
        rows = self.db.execute(
            "SELECT id,source,normalized FROM evidence WHERE scenario=? AND variant=? AND seq<=? AND event_type='alert' "
            "ORDER BY CASE try_cast(json_extract_string(normalized,'$.severity') AS INTEGER) WHEN 1 THEN 0 WHEN 2 THEN 1 WHEN 3 THEN 3 ELSE 2 END,seq DESC LIMIT 20 OFFSET ?",
            [scenario, variant, snapshot, (page - 1) * 20],
        ).fetchall()
        from bluecheese.agents.triage import TriageAgent

        events = [
            dict(zip(("id", "source", "normalized"), (r[0], r[1], json.loads(r[2]))))
            for r in rows
        ]
        groups = TriageAgent().triage_events(events)["candidates"]
        by_id = {event["id"]: event for event in events}
        for group in groups:
            seed = by_id[group["seed_ids"][0]]
            group["seed"] = seed
            times = [
                by_id[event_id]["normalized"].get("timestamp") or "Unknown"
                for event_id in group["seed_ids"]
            ]
            group["first_seen"], group["last_seen"] = min(times), max(times)
            recent = self.db.execute(
                "SELECT r.run_id,r.status,s.watermark,w.disposition,w.owner,rc.investigation_scope FROM run_context rc JOIN runs r ON r.run_id=rc.run_id JOIN snapshots s ON s.snapshot_id=r.snapshot_id LEFT JOIN case_workspace w ON w.case_id=r.case_id WHERE rc.seed_event_id IN (SELECT unnest(?)) AND s.scenario=? AND s.variant=? ORDER BY r.created_at DESC LIMIT 1",
                [group["seed_ids"], scenario, variant],
            ).fetchone()
            group["run_id"] = recent[0] if recent else None
            group["run_status"] = recent[1] if recent else None
            group["disposition"] = recent[3] if recent else None
            group["owner"] = recent[4] if recent else None
            group["investigation_scope"] = recent[5] if recent else "connection"
            group["new_alerts"] = (
                self.db.execute(
                    "SELECT count(*) FROM evidence WHERE scenario=? AND variant=? AND seq>? AND id IN (SELECT unnest(?))",
                    [scenario, variant, recent[2], group["seed_ids"]],
                ).fetchone()[0]
                if recent
                else 0
            )
        return {"total": total, "page": page, "groups": groups}

    def record_activity(self, run_id, event):
        self.db.execute(
            "INSERT INTO run_activity VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            [run_id, event["sequence"], json.dumps(event)],
        )

    def run_events(self, scenario, variant, run_id):
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT a.event FROM run_activity a JOIN runs r ON r.run_id=a.run_id JOIN snapshots s ON s.snapshot_id=r.snapshot_id WHERE a.run_id=? AND s.scenario=? AND s.variant=? ORDER BY a.sequence DESC LIMIT 128",
                [run_id, scenario, variant],
            ).fetchall()
        ][::-1]

    def case_evidence(self, scenario, variant, run_id, limit=1000):
        return [
            {"id": row[0], "sequence": row[1], **json.loads(row[2])}
            for row in self.db.execute(
                "SELECT e.id,e.seq,e.normalized FROM snapshot_evidence e JOIN runs r ON r.snapshot_id=e.snapshot_id WHERE r.run_id=? AND e.scenario=? AND e.variant=? ORDER BY e.seq DESC LIMIT ?",
                [run_id, scenario, variant, max(1, min(int(limit), 1000))],
            ).fetchall()
        ]

    def save_case_decision(
        self, scenario, variant, run_id, actor, owner, disposition, note
    ):
        if not isinstance(owner, str) or len(owner) > 128:
            raise ValueError("Owner must be at most 128 characters")
        self.db.execute("BEGIN")
        try:
            self.add_analyst_action(scenario, variant, run_id, actor, disposition, note)
            row = self.db.execute(
                "SELECT case_id FROM runs WHERE run_id=?", [run_id]
            ).fetchone()
            now = datetime.now(UTC).isoformat()
            self.db.execute(
                "INSERT INTO case_workspace VALUES (?, 'Evidence investigation', ?, ?, ?) ON CONFLICT(case_id) DO UPDATE SET owner=excluded.owner,disposition=excluded.disposition,updated_at=excluded.updated_at",
                [row[0], owner.strip(), disposition, now],
            )
            self.add_analyst_action(
                scenario,
                variant,
                run_id,
                actor,
                disposition,
                "Assigned to: " + (owner.strip() or "Unassigned"),
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def append_chat(self, scenario, variant, run_id, role, content):
        if (
            role not in ("user", "assistant")
            or not isinstance(content, str)
            or not 0 < len(content) <= 65536
        ):
            raise ValueError("Invalid chat message")
        if (
            run_id
            and not self.db.execute(
                "SELECT 1 FROM runs r JOIN snapshots s ON r.snapshot_id=s.snapshot_id WHERE r.run_id=? AND s.scenario=? AND s.variant=?",
                [run_id, scenario, variant],
            ).fetchone()
        ):
            raise ValueError("Chat run outside selected scope")
        self.db.execute(
            "INSERT INTO workspace_chat VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                uuid4().hex,
                scenario,
                variant,
                run_id,
                role,
                content,
                datetime.now(UTC).isoformat(),
            ],
        )

    def chat_history(self, scenario, variant, run_id=None):
        return [
            dict(zip(("role", "content", "created_at"), row))
            for row in self.db.execute(
                "SELECT role,content,created_at FROM workspace_chat WHERE scenario=? AND variant=? AND run_id IS NOT DISTINCT FROM ? ORDER BY created_at DESC LIMIT 40",
                [scenario, variant, run_id],
            ).fetchall()
        ][::-1]

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
