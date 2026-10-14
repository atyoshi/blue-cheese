"""One process-local runtime serializes all database commands."""

import atexit
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from bluecheese.adapters.model_provider import (
    configured_provider,
    investigation_seconds,
)
from bluecheese.agents.investigator import investigate
from bluecheese.agents.orchestrator import Orchestrator
from bluecheese.application.ingestion import EveFollower
from bluecheese.application.rotating_source import RotatingEveFollower
from bluecheese.application.run_activity import RunActivity
from bluecheese.application.store_worker import StoreWorker, WorkerStore
from bluecheese.application.unix_stream import UnixStreamFollower

SCENARIOS = {
    "suspicious": ("clean", "poisoned"),
    "benign": ("clean",),
    "insufficient": ("clean",),
}


class DemoRuntime:
    def __init__(self, state_dir, *, load_fixtures=True, practice=False):
        self.state_dir = Path(state_dir)
        self.practice = practice
        self.lock = threading.RLock()
        self.activity = RunActivity(self.lock)
        self.provider = None if load_fixtures or practice else configured_provider()
        self.database = StoreWorker(self.state_dir / "evidence.duckdb")
        self.activity.persist = lambda run_id, event: self.database.call(
            "record_activity", run_id, event
        )
        self.store = WorkerStore(self.database)
        self.orchestrator = Orchestrator()
        self.run_lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.active_run_id = None
        self.investigation_runs = 0
        self.closed = False
        self.closing = False
        self.worker = None
        self.stop_event = threading.Event()
        self.follower = None
        self.replay = False
        self.replay_index = 0
        self.last_ingest = None
        self.last_poll = None
        self.last_accepted = None
        self.source_status = "Stopped"
        self.worker_starts = 0
        self.automatic = False
        try:
            self.replay_lines = (
                (
                    files("bluecheese.data")
                    .joinpath("suspicious-clean.jsonl")
                    .read_bytes()
                    .splitlines(keepends=True)
                )
                if load_fixtures
                else []
            )
            with self.lock:
                for scenario, variants in SCENARIOS.items() if load_fixtures else ():
                    for variant in variants:
                        self.database.call(
                            "import_file",
                            files("bluecheese.data").joinpath(
                                f"{scenario}-{variant}.jsonl"
                            ),
                            scenario,
                            variant,
                        )
        except Exception:
            self.database.close()
            self.closed = True
            raise
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="bluecheese-investigation"
        )
        self.pending_run = None
        self.chat_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="bluecheese-chat"
        )
        self.pending_chat = None
        self.chat_cancel = threading.Event()
        self.chat_started = None
        atexit.register(self.close)

    def command(self, method, *args, **kwargs):
        with self.lock:
            if self.closed:
                raise RuntimeError("Runtime is closed")
        return self.database.call(method, *args, **kwargs)

    def configure_provider(self, provider):
        """Apply process-local settings only between investigations."""
        with self.lock:
            if self.closed or self.closing:
                raise RuntimeError("Runtime is closed")
            if (
                self.run_lock.locked()
                or (self.pending_run and not self.pending_run.done())
                or (self.pending_chat and not self.pending_chat.done())
            ):
                raise RuntimeError(
                    "Wait for the current investigation before changing providers"
                )
            self.provider = provider

    def begin_chat(self, message, run_id=None, view_context=None):
        from bluecheese.application.workspace_chat import respond

        with self.lock:
            if self.closed or self.closing:
                raise RuntimeError("Runtime is closed")
            if self.pending_chat and not self.pending_chat.done():
                raise RuntimeError("A chat request is already running")
            if (
                not isinstance(message, str)
                or not message.strip()
                or len(message) > 4096
            ):
                raise ValueError("Message must contain 1–4,096 characters")
            from bluecheese.application.view_context import ViewContext

            if view_context is None:
                view_context = ViewContext(
                    run_id=run_id, snapshot=self.command("snapshot")
                )
            if view_context.run_id != run_id:
                raise ValueError("Chat scope does not match the selected investigation")
            self.chat_cancel.clear()
            self.chat_started = datetime.now(UTC)
            self.command("append_chat", "live", "external", run_id, "user", message)
            self.pending_chat = self.chat_executor.submit(
                respond, self, message, run_id, view_context
            )
            return self.pending_chat

    def cancel_chat(self):
        self.chat_cancel.set()

    def test_provider(self):
        if not self.run_lock.acquire(blocking=False):
            raise RuntimeError(
                "Wait for the current investigation before testing the provider"
            )
        try:
            with self.lock:
                if self.closed or self.closing:
                    raise RuntimeError("Runtime is closed")
                if self.pending_run and not self.pending_run.done():
                    raise RuntimeError(
                        "Wait for the pending investigation before testing the provider"
                    )
                provider = self.provider
            if not provider or not hasattr(provider, "test_connection"):
                raise ValueError("Apply a tool-using agent provider before testing")
            return provider.test_connection()
        finally:
            self.run_lock.release()

    def run(
        self,
        scenario,
        variant,
        *,
        question="What does the observed alert and related flow evidence support?",
        parent_run_id=None,
        seed_event_id=None,
        **settings,
    ):
        if not self.run_lock.acquire(blocking=False):
            raise RuntimeError("An investigation is already active; cancel it or wait")
        run = None
        try:
            with self.lock:
                if self.closed or self.closing:
                    raise RuntimeError("Runtime is closed")
                self.cancel_event.clear()
                self.activity.reset()
                self.activity.emit(
                    "Orchestrator",
                    "working",
                    "Freezing case evidence for this investigation.",
                )
                run = self.database.call(
                    "create_run",
                    scenario,
                    variant,
                    question,
                    parent_run_id,
                    seed_event_id=seed_event_id,
                )
                self.active_run_id = run["run_id"]
                self.activity.bind(run["run_id"])
                self.investigation_runs += 1
                provider = self.provider
            scoped = WorkerStore(
                self.database, run["snapshot_id"], run["snapshot"], run["run_id"]
            )
            report = investigate(
                scoped,
                scenario,
                variant,
                cancel_event=self.cancel_event,
                seed_event_id=seed_event_id,
                question=question,
                activity_callback=self.activity.emit,
                synthetic=self.practice
                or scenario in SCENARIOS
                or (scenario == "live" and variant == "replay"),
                **{"provider": provider, **settings},
            )
            if scenario == "live" and variant == "external":
                report["source_incidents"] = self.database.call("source_incidents")
                if report["source_incidents"]:
                    report["warnings"].append(
                        "Source incidents are recorded for this state directory; telemetry coverage is incomplete or uncertain. Inspect sensor health before relying on absence of activity."
                    )
                    if report["verdict"] in ("BENIGN", "BENIGN_CONFOUNDER"):
                        report["verdict"] = "UNCERTAIN"
                        report["unresolved"].append(
                            "Resolve source continuity incidents before accepting a benign interpretation."
                        )
            self.activity.emit(
                "Orchestrator",
                "handoff",
                "Validation finished; passing the result to Reporter.",
                handoff_to="Reporter",
            )
            self.activity.emit(
                "Reporter",
                "working",
                "Assembling the cited report and saving the investigation result.",
            )
            report["workflow_activity"] = self.activity.snapshot()["events"]
            self.orchestrator.complete(
                self.database,
                run,
                report,
                synthetic=self.practice
                or scenario in SCENARIOS
                or (scenario == "live" and variant == "replay"),
            )
            self.activity.emit(
                "Reporter",
                "complete",
                "Cited report saved; available in investigation history.",
            )
            self.activity.emit(
                "Orchestrator",
                report["run_status"].lower(),
                {
                    "COMPLETED": "Investigation completed. Review the saved findings and citations.",
                    "CANCELLED": "Investigation cancelled. The saved report records unfinished work.",
                    "INCOMPLETE": "Investigation stopped at its budget limit. The saved report records unfinished work.",
                }.get(report["run_status"], "Investigation finished."),
            )
            self.activity.finish(report["run_status"])
            return report
        except Exception as error:
            current = self.activity.snapshot()["events"]
            role = current[-1]["role"] if current else "Orchestrator"
            self.activity.emit(
                role,
                "failed",
                "This step failed. Inspect the saved investigation error before retrying.",
            )
            self.activity.finish("FAILED")
            if run:
                self.database.call(
                    "finish_run", run["run_id"], "FAILED", error=str(error)[:4096]
                )
            raise
        finally:
            with self.lock:
                self.active_run_id = None
            self.run_lock.release()

    def begin_run(self, scenario, variant, **settings):
        with self.lock:
            if self.closed or self.closing:
                raise RuntimeError("Runtime is closed")
            if (
                self.run_lock.locked()
                or self.active_run_id
                or (self.pending_run and not self.pending_run.done())
            ):
                raise RuntimeError(
                    "An investigation is already active; cancel it or wait"
                )
            self.activity.reset("QUEUED")
            self.activity.emit(
                "Orchestrator",
                "queued",
                "Investigation queued; waiting for the investigation worker.",
            )
            self.pending_run = self.executor.submit(
                self.run, scenario, variant, **settings
            )
            return self.pending_run

    def cancel(self):
        with self.lock:
            if self.active_run_id is None:
                return False
            self.cancel_event.set()
            self.activity.emit(
                "Orchestrator",
                "cancel_requested",
                "Cancellation requested; an active model call must return before the run can stop.",
            )
            return True

    def start(
        self,
        path=None,
        replay=True,
        interval=0.5,
        recover_rotation=False,
        unix_stream=False,
    ):
        if interval <= 0:
            raise ValueError("Poll interval must be positive")
        if unix_stream and replay:
            raise ValueError("Unix streaming cannot be combined with synthetic replay")
        with self.lock:
            if self.closed or self.closing:
                raise RuntimeError("Runtime is closed")
            if self.worker and self.worker.is_alive():
                return False
            self.replay = replay
            if replay:
                if not self.replay_lines:
                    raise ValueError(
                        "Synthetic replay is disabled in the operational console"
                    )
                spool = Path(
                    os.environ.get("BLUECHEESE_REPLAY", str(self.state_dir / "replay"))
                )
                spool.mkdir(parents=True, exist_ok=True)
                path = spool / "eve.jsonl"
                path.touch(exist_ok=True)
            if self.follower and hasattr(self.follower, "close"):
                self.database.apply(lambda store: self.follower.close())
            self.follower = None
            try:
                self.follower = self.database.apply(
                    lambda store: (
                        UnixStreamFollower(store, path, self.state_dir)
                        if unix_stream
                        else RotatingEveFollower(store, path)
                        if recover_rotation and not replay
                        else EveFollower(
                            store, path, "live", "replay" if replay else "external"
                        )
                    )
                )
            except (OSError, RuntimeError, ValueError) as error:
                self.source_status = str(error)
                self.database.call("record_source_incident", str(path), 0, str(error))
                self.stop_event.set()
                return False
            self.stop_event.clear()
            self.source_status = (
                "Running replay (not packet capture)"
                if replay
                else "Following append-only EVE file"
            )
            if unix_stream:
                self.source_status = "Following Unix stream"
            try:
                self.poll_once()  # first tick is synchronous and inspectable
            except Exception as error:  # noqa: BLE001 - surface source failure to UI
                self.source_status = str(error)
                self.database.call(
                    "record_source_incident",
                    str(self.follower.path),
                    self.follower.committed,
                    str(error),
                )
                self.stop_event.set()
                if isinstance(self.follower, UnixStreamFollower):
                    self.database.apply(lambda store: self.follower.close())
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
                    self.database.call(
                        "record_source_incident",
                        str(self.follower.path),
                        self.follower.committed,
                        str(error),
                    )
                self.stop_event.set()
                if isinstance(self.follower, UnixStreamFollower):
                    self.database.apply(lambda store: self.follower.close())
                break

    def poll_once(self):
        with self.lock:
            if self.closed:
                raise RuntimeError("Runtime is closed")
            if self.replay:
                with self.follower.path.open("ab") as stream:
                    stream.write(
                        self.replay_lines[self.replay_index % len(self.replay_lines)]
                    )
                self.replay_index += 1

            def poll(store):
                before = store.snapshot()
                result = self.follower.poll_once()
                result["accepted"] = store.snapshot() - before
                return result

            result = self.database.apply(poll)
            self.last_poll = datetime.now(UTC).isoformat()
            if result["bytes_read"]:
                self.last_ingest = datetime.now(UTC).isoformat()
            if result.get("accepted", 0):
                self.last_accepted = self.last_poll
            if self.automatic:
                self.schedule_once()
            return result

    def schedule_once(self):
        """One durable task at a time; polling discovers commit-before-notify work."""
        with self.lock:
            if (
                self.closed
                or self.closing
                or self.active_run_id
                or self.run_lock.locked()
                or (self.pending_run and not self.pending_run.done())
            ):
                return False
            event_id = self.database.call("claim_work")
            if not event_id:
                return False
            self.activity.reset("QUEUED")
            self.activity.emit(
                "Orchestrator",
                "queued",
                "Alert investigation queued for the investigation worker.",
            )
            self.pending_run = self.executor.submit(self._run_work, event_id)
            return True

    def set_automatic(self, enabled):
        with self.lock:
            self.automatic = bool(enabled)

    def _run_work(self, event_id):
        try:
            report = self.run(
                "live",
                "external",
                seed_event_id=event_id,
                max_calls=8,
                max_seconds=investigation_seconds(self.provider),
            )
            self.database.call(
                "finish_work", event_id, report["run_status"], report["run_id"]
            )
            return report
        except Exception as error:
            self.database.call("finish_work", event_id, "FAILED", error=str(error))
            raise

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
                "last_poll": self.last_poll,
                "last_accepted": self.last_accepted,
                "committed_offset": self.follower.committed if self.follower else 0,
                "counts": self.database.call("counts", "live", variant),
                "worker_starts": self.worker_starts,
                "investigation_runs": self.investigation_runs,
                "active_run_id": self.active_run_id,
                "investigation_pending": bool(
                    self.pending_run and not self.pending_run.done()
                ),
                "automatic_investigation": self.automatic,
                "rotation_recovery": isinstance(self.follower, RotatingEveFollower),
                "rotation_notice": getattr(self.follower, "notice", None),
                "source_mode": "unix_stream"
                if isinstance(self.follower, UnixStreamFollower)
                else "file",
                "stream_state": self.follower.state
                if isinstance(self.follower, UnixStreamFollower)
                else None,
                "stream_spool": str(self.follower.spool)
                if isinstance(self.follower, UnixStreamFollower)
                else None,
            }

    def stop(self):
        self.stop_event.set()
        worker = self.worker
        if worker and worker is not threading.current_thread():
            worker.join(timeout=5)
        with self.lock:
            if worker and worker.is_alive():
                raise RuntimeError("Ingestion worker has not stopped")
            if (
                isinstance(self.follower, UnixStreamFollower)
                and not self.follower.closed
            ):
                if (
                    self.follower.client is not None
                    or self.follower.scanned != self.follower.committed
                ):
                    reason = "Stream receiver stopped; producer-side delivery completeness cannot be confirmed"
                    if self.follower.scanned != self.follower.committed:
                        reason += "; partial record retained in spool"
                    self.database.call(
                        "record_source_incident",
                        str(self.follower.path),
                        self.follower.committed,
                        reason,
                    )
                self.database.apply(lambda store: self.follower.close())
            if self.source_status.startswith(("Running", "Following")):
                self.source_status = "Stopped; committed cursor retained for resume"

    def close(self):
        with self.lock:
            self.closing = True
        self.cancel()
        self.cancel_chat()
        self.stop()
        self.executor.shutdown(wait=True)
        self.chat_executor.shutdown(wait=True)
        with self.run_lock, self.lock:
            if not self.closed:
                if self.follower and hasattr(self.follower, "close"):
                    self.database.apply(lambda store: self.follower.close())
                self.closed = True
                self.database.close()
