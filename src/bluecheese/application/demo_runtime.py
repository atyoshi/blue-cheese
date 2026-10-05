"""One process-local runtime serializes all database commands."""

import atexit
import os
import threading
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.agents.investigator import investigate
from bluecheese.application.ingestion import EveFollower

SCENARIOS = {
    "suspicious": ("clean", "poisoned"),
    "benign": ("clean",),
    "insufficient": ("clean",),
}


class DemoRuntime:
    def __init__(self, state_dir):
        self.state_dir = Path(state_dir)
        self.lock = threading.RLock()
        self.store = EvidenceStore(self.state_dir / "evidence.duckdb")
        self.investigation_runs = 0
        self.closed = False
        self.worker = None
        self.stop_event = threading.Event()
        self.follower = None
        self.replay = False
        self.replay_index = 0
        self.last_ingest = None
        self.source_status = "Stopped"
        self.worker_starts = 0
        self.replay_lines = (
            files("bluecheese.data")
            .joinpath("suspicious-clean.jsonl")
            .read_bytes()
            .splitlines(keepends=True)
        )
        with self.lock:
            for scenario, variants in SCENARIOS.items():
                for variant in variants:
                    self.store.import_file(
                        files("bluecheese.data").joinpath(
                            f"{scenario}-{variant}.jsonl"
                        ),
                        scenario,
                        variant,
                    )
        atexit.register(self.close)

    def command(self, method, *args, **kwargs):
        with self.lock:
            if self.closed:
                raise RuntimeError("Runtime is closed")
            return getattr(self.store, method)(*args, **kwargs)

    def run(self, scenario, variant, **settings):
        with self.lock:
            self.investigation_runs += 1
            return investigate(self.store, scenario, variant, **settings)

    def start(self, path=None, replay=True, interval=0.5):
        with self.lock:
            if self.worker and self.worker.is_alive():
                return False
            self.replay = replay
            if replay:
                spool = Path(
                    os.environ.get("BLUECHEESE_REPLAY", str(self.state_dir / "replay"))
                )
                spool.mkdir(parents=True, exist_ok=True)
                path = spool / "eve.jsonl"
                path.touch(exist_ok=True)
            self.follower = EveFollower(
                self.store, path, "live", "replay" if replay else "external"
            )
            self.stop_event.clear()
            self.source_status = (
                "Running replay (not packet capture)"
                if replay
                else "Following append-only EVE file"
            )
            try:
                self.poll_once()  # first tick is synchronous and inspectable
            except Exception as error:  # noqa: BLE001 - surface source failure to UI
                self.source_status = str(error)
                self.stop_event.set()
                return False
            self.worker = threading.Thread(
                target=self._loop,
                args=(interval,),
                name="bluecheese-ingestion",
                daemon=True,
            )
            self.worker_starts += 1
            self.worker.start()
            return True

    def _loop(self, interval):
        while not self.stop_event.wait(interval):
            try:
                self.poll_once()
            except Exception as error:  # noqa: BLE001 - worker boundary records failure and stops
                with self.lock:
                    self.source_status = str(error)
                self.stop_event.set()
                break

    def poll_once(self):
        with self.lock:
            if self.replay:
                with self.follower.path.open("ab") as stream:
                    stream.write(
                        self.replay_lines[self.replay_index % len(self.replay_lines)]
                    )
                self.replay_index += 1
            result = self.follower.poll_once()
            if result["bytes_read"]:
                self.last_ingest = datetime.now(UTC).isoformat()
            return result

    def status(self):
        with self.lock:
            variant = "replay" if self.replay else "external"
            return {
                "running": bool(
                    self.worker
                    and self.worker.is_alive()
                    and not self.stop_event.is_set()
                ),
                "status": self.source_status,
                "source": str(self.follower.path) if self.follower else None,
                "last_ingest": self.last_ingest,
                "committed_offset": self.follower.committed if self.follower else 0,
                "counts": self.store.counts("live", variant),
                "worker_starts": self.worker_starts,
                "investigation_runs": self.investigation_runs,
            }

    def stop(self):
        self.stop_event.set()
        worker = self.worker
        if worker and worker is not threading.current_thread():
            worker.join(timeout=5)
        with self.lock:
            if worker and worker.is_alive():
                raise RuntimeError("Ingestion worker has not stopped")
            if self.source_status.startswith(("Running", "Following")):
                self.source_status = "Stopped; committed cursor retained for resume"

    def close(self):
        self.stop()
        with self.lock:
            if not self.closed:
                self.store.close()
                self.closed = True
