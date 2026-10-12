"""Opt-in rename-and-create recovery. Truncation and missing archives stop visibly."""

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from bluecheese.application.ingestion import EveFollower, SourceGap


def identity(stat):
    return f"{stat.st_dev}:{stat.st_ino}"


class RotatingEveFollower:
    def __init__(self, store, path, *, clock=time.monotonic, drain_seconds=5.0):
        self.store = store
        self.path = Path(path).resolve()
        self.source = f"file:{self.path}"
        self.clock, self.drain_seconds = clock, drain_seconds
        self.rotation_started = None
        self.replacement_identity = None
        self.stream = None
        self.transitions = 0
        self.notice = None
        previous = store.db.execute(
            "SELECT source_key,identity FROM file_generations WHERE source=? AND active=TRUE",
            [self.source],
        ).fetchall()
        if len(previous) > 1:
            raise SourceGap(
                "Multiple active file generations; stop and inspect state integrity"
            )
        if previous:
            key, expected = previous[0]
        else:
            # Adopt the prior release's cursor namespace without reimporting evidence.
            cursor = store.db.execute(
                "SELECT identity FROM cursors WHERE source=?", [self.source]
            ).fetchone()
            key, expected = (self.source, cursor[0]) if cursor else (None, None)
        selected = self.path
        if expected and (
            not selected.exists() or identity(selected.stat()) != expected
        ):
            selected = self._find_archive(expected)
        stream = selected.open("rb")
        try:
            observed = identity(os.fstat(stream.fileno()))
            if expected and observed != expected:
                raise SourceGap("Source changed while opening a retained generation")
            if not previous:
                key = self._register(stream, key)
            self.follower = EveFollower(
                store, self.path, "live", "external", source_key=key, held_stream=stream
            )
            self.stream = stream
        except Exception:
            stream.close()
            raise

    def _find_archive(self, expected):
        # Bounded search in the configured source's directory; no recursive traversal.
        found = None
        for index, candidate in enumerate(self.path.parent.iterdir()):
            if index >= 1000:
                break
            if (
                not candidate.name.startswith(self.path.name + ".")
                or candidate.is_symlink()
            ):
                continue
            try:
                if candidate.is_file():
                    observed = identity(candidate.stat())
                    if observed == expected:
                        found = candidate
                    elif not self.store.db.execute(
                        "SELECT 1 FROM file_generations WHERE source=? AND identity=? LIMIT 1",
                        [self.source, observed],
                    ).fetchone():
                        raise SourceGap(
                            "Untracked archived generation found during restart; stopped because rotation order and coverage are uncertain"
                        )
            except FileNotFoundError:
                continue
        if found:
            return found
        raise SourceGap(
            "Previous generation unavailable in the first 1000 directory entries; continuity lost. Stop and restore the archived source or select a new state."
        )

    def _register(self, stream, source_key=None):
        generation = uuid4().hex
        key = source_key or f"{self.source}@{generation}"
        self.store.db.execute("BEGIN")
        try:
            self.store.db.execute(
                "UPDATE file_generations SET active=FALSE WHERE source=?", [self.source]
            )
            self.store.db.execute(
                "INSERT INTO file_generations VALUES (?, ?, ?, ?, ?, TRUE)",
                [
                    self.source,
                    generation,
                    key,
                    identity(os.fstat(stream.fileno())),
                    datetime.now(UTC).isoformat(),
                ],
            )
            self.store.db.execute("COMMIT")
        except Exception:
            self.store.db.execute("ROLLBACK")
            raise
        return key

    @property
    def committed(self):
        return self.follower.committed

    @property
    def scanned(self):
        return self.follower.scanned

    def poll_once(self):
        result = self.follower.poll_once()
        try:
            current_identity = identity(self.path.stat())
        except FileNotFoundError:
            # Retain/drain the old descriptor while the producer creates its replacement.
            current_identity = None
        old_identity = identity(os.fstat(self.stream.fileno()))
        if current_identity == old_identity:
            self.rotation_started = None
            self.replacement_identity = None
            return result
        if self.rotation_started is None:
            self.rotation_started = self.clock()
        if current_identity:
            if (
                self.replacement_identity
                and self.replacement_identity != current_identity
            ):
                raise SourceGap(
                    "Multiple rotations occurred before the old generation drained; stopped rather than skipping an intermediate generation"
                )
            self.replacement_identity = current_identity
        # Always drain the old generation before accepting any new generation bytes.
        if self.clock() - self.rotation_started < self.drain_seconds:
            return result
        if (
            result["bytes_read"]
            or os.fstat(self.stream.fileno()).st_size > self.scanned
        ):
            raise SourceGap(
                "Rotation drain deadline reached while the old generation is still receiving data; stopped to avoid silent trailing loss"
            )
        if self.scanned != self.committed:
            raise SourceGap(
                "Rotated generation ends in a partial record; stopped with an unresolved byte interval"
            )
        if current_identity is None:
            raise SourceGap(
                "Rotation replacement did not appear before the drain deadline"
            )
        replacement = self.path.open("rb")
        try:
            if identity(os.fstat(replacement.fileno())) != current_identity:
                raise SourceGap("Replacement changed while opening the next generation")
            key = self._register(replacement)
            follower = EveFollower(
                self.store,
                self.path,
                "live",
                "external",
                source_key=key,
                held_stream=replacement,
            )
        except Exception:
            replacement.close()
            raise
        self.stream.close()
        self.stream, self.follower = replacement, follower
        self.rotation_started = None
        self.replacement_identity = None
        self.transitions += 1
        self.notice = "Rename rotation recovered after bounded drain; writes to retired generations after the drain deadline cannot be recovered automatically."
        return result  # Read the new generation on the next bounded tick.

    def close(self):
        if self.stream is not None and not self.stream.closed:
            self.stream.close()
