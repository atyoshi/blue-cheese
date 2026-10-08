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


def migrate(db):
    checksum = hashlib.sha256(SQL.encode()).hexdigest()
    db.execute("BEGIN")
    try:
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, checksum VARCHAR)"
        )
        rows = db.execute("SELECT version,checksum FROM schema_migrations").fetchall()
        if any(version != VERSION or stored != checksum for version, stored in rows):
            raise RuntimeError(
                "Unsupported or modified presentation database schema migration"
            )
        if not rows:
            db.execute(SQL)
            db.execute(
                "INSERT INTO schema_migrations VALUES (?, ?)", [VERSION, checksum]
            )
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
