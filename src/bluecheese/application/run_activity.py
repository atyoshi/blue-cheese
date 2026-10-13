"""Bounded, process-local observation of work; never schedules investigations."""

import time
from collections import deque
from datetime import UTC, datetime


class RunActivity:
    def __init__(self, lock, clock=time.monotonic, persist=None):
        self.lock, self.clock = lock, clock
        self.persist = persist
        self.events = deque(maxlen=128)
        self.run_id = None
        self.state = "IDLE"
        self.started = None
        self.finished = None
        self.sequence = 0

    def reset(self, state="RUNNING"):
        with self.lock:
            self.events.clear()
            self.sequence = 0
            self.run_id = None
            self.state = state
            self.started = self.clock()
            self.finished = None

    def emit(self, role, status, message, *, kind="software", handoff_to=None):
        with self.lock:
            if self.started is None:
                self.started = self.clock()
            self.sequence += 1
            self.events.append(
                {
                    "sequence": self.sequence,
                    "time": datetime.now(UTC).isoformat(),
                    "elapsed_seconds": round(self.clock() - self.started, 3),
                    "role": role,
                    "status": status,
                    "kind": kind,
                    "message": message[:4096],
                    "handoff_to": handoff_to,
                }
            )
            if self.run_id and self.persist:
                self.persist(self.run_id, dict(self.events[-1]))

    def bind(self, run_id):
        with self.lock:
            self.run_id = run_id
            if self.persist:
                for event in self.events:
                    self.persist(run_id, dict(event))

    def finish(self, state):
        with self.lock:
            self.state = state
            self.finished = self.clock()

    def snapshot(self):
        with self.lock:
            return {
                "run_id": self.run_id,
                "state": self.state,
                "elapsed_seconds": round(
                    (self.finished if self.finished is not None else self.clock())
                    - self.started,
                    1,
                )
                if self.started is not None
                else 0.0,
                "events": [dict(event) for event in self.events],
            }
