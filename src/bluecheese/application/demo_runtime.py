"""One process-local runtime serializes all database commands."""
import atexit
import threading
from importlib.resources import files
from pathlib import Path

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.agents.investigator import investigate

SCENARIOS = {'suspicious': ('clean', 'poisoned'), 'benign': ('clean',),
             'insufficient': ('clean',)}


class DemoRuntime:
    def __init__(self, state_dir):
        self.state_dir = Path(state_dir)
        self.lock = threading.RLock()
        self.store = EvidenceStore(self.state_dir / 'evidence.duckdb')
        self.investigation_runs = 0
        self.closed = False
        with self.lock:
            for scenario, variants in SCENARIOS.items():
                for variant in variants:
                    self.store.import_file(files('bluecheese.data').joinpath(f'{scenario}-{variant}.jsonl'), scenario, variant)
        atexit.register(self.close)

    def command(self, method, *args, **kwargs):
        with self.lock:
            if self.closed:
                raise RuntimeError('Runtime is closed')
            return getattr(self.store, method)(*args, **kwargs)

    def run(self, scenario, variant, **settings):
        with self.lock:
            self.investigation_runs += 1
            return investigate(self.store, scenario, variant, **settings)

    def close(self):
        with self.lock:
            if not self.closed:
                self.store.close()
                self.closed = True
