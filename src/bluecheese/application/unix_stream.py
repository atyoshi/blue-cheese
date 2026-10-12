"""One nonblocking Unix stream receiver, polled by the owning database worker."""

import hashlib
import os
import socket
import stat
from pathlib import Path

from bluecheese.application.ingestion import EveFollower, SourceGap


class UnixStreamFollower:
    def __init__(self, store, path, state_dir, max_bytes=268435456):
        if not str(path).strip():
            raise ValueError("Enter a Unix socket path.")
        supplied = Path(path).expanduser().absolute()
        if supplied.is_symlink():
            raise ValueError("Socket path must not be a symlink")
        self.path = supplied.parent.resolve() / supplied.name
        if len(os.fsencode(self.path)) > 100:
            raise ValueError(
                "Unix socket path is too long; use a path of at most 100 bytes"
            )
        if not self.path.parent.is_dir():
            raise ValueError("Socket parent directory must already exist")
        if self.path.exists():
            raise ValueError(
                "Socket path already exists. Stop the other receiver or choose an unused path; existing files and stale sockets are never deleted automatically."
            )
        self.listener = self.client = None
        self.owned_identity = None
        self.state = "Waiting for a producer"
        self.closed = False
        self.received_bytes = 0
        self.max_bytes = max_bytes
        spool_dir = Path(state_dir) / "streams"
        spool_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(os.fsencode(self.path)).hexdigest()[:24]
        self.spool = spool_dir / (key + ".jsonl")
        if self.spool.is_symlink():
            raise ValueError("Stream spool must not be a symlink")
        if self.spool.exists() and not self.spool.is_file():
            raise ValueError("Stream spool must be a regular file")
        self.spool.touch(exist_ok=True)
        with self.spool.open("rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Stream spool must be a regular file")
            if stream.seek(0, os.SEEK_END):
                stream.seek(-1, os.SEEK_END)
                if stream.read(1) != b"\n":
                    raise SourceGap(
                        "Previous stream ends in a partial record. Received bytes are preserved; choose a new socket path/state rather than merging a new producer into that record."
                    )
        self.follower = EveFollower(store, self.spool, "live", "external")
        try:
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.setblocking(False)
            self.listener.bind(str(self.path))
            bound = self.path.lstat()
            self.owned_identity = (bound.st_dev, bound.st_ino)
            os.chmod(self.path, 0o600)
            self.listener.listen(1)
        except Exception:
            self.close()
            raise

    @property
    def committed(self):
        return self.follower.committed

    @property
    def scanned(self):
        return self.follower.scanned

    def poll_once(self):
        if self.closed:
            raise RuntimeError("Stream receiver is stopped")
        # Recover already-spooled bytes before accepting new data after restart/failure.
        if self.follower.scanned < self.spool.stat().st_size:
            return self.follower.poll_once()
        remaining = self.max_bytes - self.spool.stat().st_size
        if remaining <= 0:
            raise SourceGap(
                "Stream spool reached its 256 MiB limit; stopped. Preserve/archive the stopped state and select a new state before continuing. No source bytes are deleted automatically."
            )
        if self.client is None:
            try:
                self.client, _ = self.listener.accept()
                self.client.setblocking(False)
                self.state = "Producer connected"
            except BlockingIOError:
                return self.follower.poll_once()
        try:
            chunk = self.client.recv(min(262144, remaining))
        except BlockingIOError:
            return self.follower.poll_once()
        except (ConnectionResetError, BrokenPipeError) as error:
            raise SourceGap(
                "Stream producer connection failed; continuity is uncertain. Reconnect explicitly."
            ) from error
        if not chunk:
            suffix = " with a partial record" if self.scanned != self.committed else ""
            raise SourceGap(
                f"Stream producer disconnected{suffix}; stopped. Received bytes are preserved; reconnect explicitly. Producer-side drops cannot be detected from this stream alone."
            )
        with self.spool.open("ab") as stream:
            stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        self.received_bytes += len(chunk)
        return self.follower.poll_once()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.state = "Stopped"
        for connection in (self.client, self.listener):
            if connection is not None:
                connection.close()
        if self.owned_identity:
            try:
                current = self.path.lstat()
                if (
                    stat.S_ISSOCK(current.st_mode)
                    and (current.st_dev, current.st_ino) == self.owned_identity
                ):
                    self.path.unlink()
            except FileNotFoundError:
                pass
