"""Additive presentation schema migration, preserving existing evidence/cursors."""

import hashlib

VERSION = 1
SQL = """
CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR PRIMARY KEY, scenario VARCHAR, variant VARCHAR,
    question VARCHAR, revision BIGINT, status VARCHAR);
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id VARCHAR PRIMARY KEY, case_id VARCHAR, revision BIGINT,
    scenario VARCHAR, variant VARCHAR, watermark BIGINT, digest VARCHAR,
    created_at VARCHAR, question VARCHAR);
CREATE TABLE IF NOT EXISTS snapshot_evidence AS
    SELECT CAST(NULL AS VARCHAR) AS snapshot_id, * FROM evidence WHERE FALSE;
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR PRIMARY KEY, case_id VARCHAR, snapshot_id VARCHAR,
    parent_run_id VARCHAR, status VARCHAR, created_at VARCHAR,
    finished_at VARCHAR, report VARCHAR, error VARCHAR);
CREATE TABLE IF NOT EXISTS tool_calls (
    run_id VARCHAR, ordinal BIGINT, activity VARCHAR,
    PRIMARY KEY(run_id, ordinal));
"""

OPERATIONS_SQL = """
CREATE TABLE IF NOT EXISTS analyst_actions (
    action_id VARCHAR PRIMARY KEY, case_id VARCHAR, created_at VARCHAR,
    actor VARCHAR, disposition VARCHAR, note VARCHAR);
CREATE TABLE IF NOT EXISTS source_incidents (
    incident_id VARCHAR PRIMARY KEY, source VARCHAR, created_at VARCHAR,
    committed_offset BIGINT, diagnostic VARCHAR);
"""
WORK_SQL = """
CREATE TABLE IF NOT EXISTS investigation_work (
    event_id VARCHAR PRIMARY KEY, status VARCHAR, run_id VARCHAR,
    created_at VARCHAR, updated_at VARCHAR, error VARCHAR);
"""
RETENTION_SQL = """
CREATE TABLE IF NOT EXISTS evidence_watermark (singleton INTEGER PRIMARY KEY, seq BIGINT);
INSERT INTO evidence_watermark SELECT 1, greatest(
    (SELECT coalesce(max(seq),0) FROM evidence),
    (SELECT coalesce(max(seq),0) FROM snapshot_evidence)) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS retention_tombstones (
    event_id VARCHAR PRIMARY KEY, seq BIGINT, removed_at VARCHAR, operation_id VARCHAR);
CREATE TABLE IF NOT EXISTS retention_operations (
    operation_id VARCHAR PRIMARY KEY, created_at VARCHAR, before_sequence BIGINT, removed BIGINT);
"""
GENERATIONS_SQL = """
CREATE TABLE IF NOT EXISTS file_generations (
    source VARCHAR, generation VARCHAR PRIMARY KEY, source_key VARCHAR,
    identity VARCHAR, opened_at VARCHAR, active BOOLEAN);
"""
MIGRATIONS = {
    1: SQL,
    2: OPERATIONS_SQL,
    3: WORK_SQL,
    4: RETENTION_SQL,
    5: GENERATIONS_SQL,
}


def migrate(db):
    db.execute("BEGIN")
    try:
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, checksum VARCHAR)"
        )
        rows = db.execute("SELECT version,checksum FROM schema_migrations").fetchall()
        if any(
            version not in MIGRATIONS
            or stored != hashlib.sha256(MIGRATIONS[version].encode()).hexdigest()
            for version, stored in rows
        ):
            raise RuntimeError(
                "Unsupported or modified presentation database schema migration"
            )
        applied = {version for version, _ in rows}
        if applied and applied != set(range(1, max(applied) + 1)):
            raise RuntimeError("Incomplete database schema migration history")
        for version, sql in MIGRATIONS.items():
            if version not in applied:
                db.execute(sql)
                db.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?)",
                    [version, hashlib.sha256(sql.encode()).hexdigest()],
                )
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
