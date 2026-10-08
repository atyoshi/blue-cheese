"""Offline database backup/restore; stop the application before either operation.

Source telemetry is external to the database and is not included or relocated.
"""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import duckdb

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.state_lock import StateLock


def file_digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def verify_backup(directory):
    directory = Path(directory)
    if {p.name for p in directory.iterdir()} != {"evidence.duckdb", "manifest.json"}:
        raise ValueError("Unexpected or missing backup members")
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ValueError("Backup members must be ordinary files")
    manifest_path = directory / "manifest.json"
    if manifest_path.stat().st_size > 16384:
        raise ValueError("Backup manifest exceeds size limit")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    database = directory / "evidence.duckdb"
    if manifest["format_version"] != 1 or manifest["size"] != database.stat().st_size:
        raise ValueError("Backup version or size mismatch")
    if manifest["sha256"] != file_digest(database):
        raise ValueError("Backup database checksum mismatch")
    # Read-only validation cannot create evidence or treat reports as telemetry.
    db = duckdb.connect(str(database), read_only=True)
    try:
        versions = [
            list(row)
            for row in db.execute(
                "SELECT version,checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]
        if versions != manifest["schema_migrations"]:
            raise ValueError("Backup schema differs from manifest")
        if (
            db.execute("SELECT count(*) FROM evidence").fetchone()[0]
            != manifest["evidence_count"]
        ):
            raise ValueError("Backup evidence count mismatch")
    finally:
        db.close()
    return manifest


def backup(state_dir, destination):
    state_dir, destination = Path(state_dir).resolve(), Path(destination)
    if not (state_dir / "evidence.duckdb").is_file():
        raise ValueError("No evidence database exists in the source state directory")
    if destination.exists():
        raise FileExistsError("Backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".backup-", dir=destination.parent))
    store = None
    try:
        store = EvidenceStore(state_dir / "evidence.duckdb")
        manifest = {
            "format_version": 1,
            "schema_migrations": [
                list(row)
                for row in store.db.execute(
                    "SELECT version,checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            ],
            "evidence_count": store.db.execute(
                "SELECT count(*) FROM evidence"
            ).fetchone()[0],
            "source_telemetry_included": False,
        }
        store.db.execute("CHECKPOINT")
        # Keep the directory lock until the closed database has been copied.
        store.db.close()
        copied = temporary / "evidence.duckdb"
        shutil.copyfile(state_dir / "evidence.duckdb", copied)
        manifest.update(size=copied.stat().st_size, sha256=file_digest(copied))
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        verify_backup(temporary)
        os.rename(temporary, destination)
    finally:
        if store is not None:
            store.close()
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def restore(source, state_dir):
    source, state_dir = Path(source), Path(state_dir).resolve()
    verify_backup(source)
    lock = StateLock(state_dir)
    temporary = None
    try:
        if any(p.name != ".bluecheese.lock" for p in state_dir.iterdir()):
            raise FileExistsError("Restore requires an empty state directory")
        descriptor, name = tempfile.mkstemp(prefix=".restore-", dir=state_dir)
        os.close(descriptor)
        temporary = Path(name)
        shutil.copyfile(source / "evidence.duckdb", temporary)
        manifest = verify_backup(source)
        if file_digest(temporary) != manifest["sha256"]:
            raise ValueError("Restore copy checksum mismatch")
        os.rename(temporary, state_dir / "evidence.duckdb")
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        lock.close()
    return state_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("backup")
    save.add_argument("--state", required=True)
    save.add_argument("--out", required=True)
    load = commands.add_parser("restore")
    load.add_argument("--source", required=True)
    load.add_argument("--state", required=True)
    check = commands.add_parser("verify")
    check.add_argument("source")
    args = parser.parse_args()
    if args.command == "backup":
        print(backup(args.state, args.out))
    elif args.command == "restore":
        print(restore(args.source, args.state))
    else:
        print(json.dumps(verify_backup(args.source), indent=2))


if __name__ == "__main__":
    main()
