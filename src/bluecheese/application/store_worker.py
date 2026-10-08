"""Bounded command queue; one thread creates, uses and closes the connection."""

import queue
import threading
from concurrent.futures import Future

from bluecheese.adapters.duckdb_store import EvidenceStore


class StoreWorker:
    def __init__(self, path, capacity=64):
        self.queue = queue.Queue(maxsize=capacity)
        self.guard = threading.Lock()
        self.closed = False
        self.ready = Future()
        self.thread = threading.Thread(
            target=self._serve, args=(path,), name="bluecheese-database", daemon=True
        )
        self.thread.start()
        self.ready.result()

    def _serve(self, path):
        try:
            store = EvidenceStore(path)
        except Exception as error:  # noqa: BLE001 - propagate worker failure to caller
            self.ready.set_exception(error)
            return
        self.ready.set_result(None)
        try:
            while True:
                item = self.queue.get()
                if item is None:
                    break
                operation, args, kwargs, future = item
                try:
                    result = operation(store, *args, **kwargs)
                except Exception as error:  # noqa: BLE001 - propagate worker failure to caller
                    future.set_exception(error)
                else:
                    future.set_result(result)
        finally:
            store.close()

    def apply(self, operation, *args, **kwargs):
        if threading.current_thread() is self.thread:
            raise RuntimeError("Database commands cannot recursively queue commands")
        future = Future()
        with self.guard:
            if self.closed:
                raise RuntimeError("Database worker is closed")
            try:
                self.queue.put_nowait((operation, args, kwargs, future))
            except queue.Full as error:
                raise RuntimeError(
                    "Database command queue is full; retry later"
                ) from error
        return future.result()

    def call(self, method, *args, **kwargs):
        return self.apply(lambda store: getattr(store, method)(*args, **kwargs))

    def close(self):
        with self.guard:
            if not self.closed:
                self.closed = True
                # A full queue is drained by the worker; shutdown preserves commands.
                self.queue.put(None)
        self.thread.join()


class WorkerStore:
    """Restricted synchronous facade used by the evidence broker."""

    METHODS = frozenset(
        {
            "snapshot",
            "get_event",
            "list_alerts",
            "find_events_by_ip",
            "search_events",
        }
    )

    def __init__(self, worker, snapshot_id=None, watermark=None, run_id=None):
        self.worker = worker
        self.snapshot_id = snapshot_id
        self.watermark = watermark
        self.run_id = run_id

    def __getattr__(self, method):
        if method not in self.METHODS:
            raise AttributeError(method)
        if method == "snapshot" and self.snapshot_id is not None:
            return lambda: self.watermark

        def command(*args, **kwargs):
            if self.snapshot_id is not None and method != "snapshot":
                kwargs["snapshot_id"] = self.snapshot_id
            return self.worker.call(method, *args, **kwargs)

        return command

    def audit_tool(self, activity):
        if self.run_id:
            self.worker.call("record_tool", self.run_id, activity)
