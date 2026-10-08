"""Exclusive OS-owned local state lock for Linux and macOS.

The lock file stays on disk: unlinking it could let writers lock different inodes.
Ownership ends when the descriptor closes, including after process termination.
"""

import fcntl
from pathlib import Path


class StateLock:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.stream = (self.directory / ".bluecheese.lock").open("a+b")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.stream.close()
            raise RuntimeError(
                f"Blue Cheese state is already in use: {self.directory}. "
                "Stop the application/export or choose another state directory."
            ) from error

    def close(self):
        if not self.stream.closed:
            self.stream.close()
