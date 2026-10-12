"""Offline deployment checks. No sensors or providers are contacted."""

import hashlib
import os
import shutil
import sys
from pathlib import Path

import duckdb

from bluecheese.adapters.demo_schema import MIGRATIONS
from bluecheese.adapters.model_provider import configured_provider
from bluecheese.application.source_path import readable_eve_path
from bluecheese.application.state_lock import StateLock


def doctor(state_dir, eve_path=None):
    state = Path(state_dir).resolve()
    checks = {
        "python_supported": sys.version_info >= (3, 11),
        "state_directory": str(state),
        "database_initialized": False,
        "suricata_on_path": shutil.which("suricata") is not None,
        "provider": "offline rules",
        "errors": [],
    }
    try:
        provider = configured_provider()
        if provider:
            checks["provider"] = provider.label
            checks["provider_live_verified"] = False
    except ValueError as error:
        checks["errors"].append(str(error))
    source = eve_path or os.environ.get("BLUECHEESE_EVE")
    if source:
        checks["eve_path"] = str(Path(source).expanduser().resolve())
        try:
            readable_eve_path(source)
            checks["eve_readable"] = True
        except (OSError, ValueError) as error:
            checks["eve_readable"] = False
            checks["errors"].append(str(error))
    if (state / "evidence.duckdb").exists():
        try:
            lock = StateLock(state)
            try:
                db = duckdb.connect(str(state / "evidence.duckdb"), read_only=True)
                try:
                    versions = dict(
                        db.execute(
                            "SELECT version,checksum FROM schema_migrations"
                        ).fetchall()
                    )
                    if any(
                        v not in MIGRATIONS
                        or checksum
                        != hashlib.sha256(MIGRATIONS[v].encode()).hexdigest()
                        for v, checksum in versions.items()
                    ):
                        raise ValueError("Unsupported or modified schema migration")
                    if versions and set(versions) != set(range(1, max(versions) + 1)):
                        raise ValueError("Incomplete database schema migration history")
                    checks["database_initialized"] = True
                    checks["schema_version"] = max(versions, default=0)
                    checks["upgrade_pending"] = sorted(set(MIGRATIONS) - set(versions))
                finally:
                    db.close()
            finally:
                lock.close()
        except (OSError, RuntimeError, ValueError, duckdb.Error) as error:
            checks["errors"].append(str(error))
    checks["ok"] = checks["python_supported"] and not checks["errors"]
    return checks
