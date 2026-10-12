"""Approval-gated terminal workspace over the operational runtime."""

import json
import shlex
import unicodedata
from concurrent.futures import TimeoutError
from pathlib import Path

from jsonschema import ValidationError, validate

from bluecheese.adapters.agent_provider import AgentModelProvider, completion_endpoint
from bluecheese.adapters.model_provider import ModelProfile, request_completion
from bluecheese.agents.triage import TriageAgent
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.ingestion import EveFollower, SourceGap
from bluecheese.application.source_path import readable_eve_path
from bluecheese.application.telemetry_visuals import summarize

SCOPE = ("live", "external")
FIELDS = {
    "endpoint": {"type": "string"},
    "model": {"type": "string"},
    "api_key": {"type": "string"},
    "api_key_env": {"type": "string"},
    "allow_remote": {"type": "boolean"},
    "timeout": {"type": "number", "exclusiveMinimum": 0, "maximum": 120},
    "max_output_tokens": {"type": "integer", "minimum": 128, "maximum": 8192},
    "max_attempts": {"type": "integer", "minimum": 2, "maximum": 12},
    "json_mode": {"type": "boolean"},
    "falsifier_model": {"type": "string", "maxLength": 128},
}


def load_provider(path=None, **overrides):
    values = {}
    if path:
        with Path(path).expanduser().open() as source:
            values = json.load(source)
    validate(
        values, {"type": "object", "properties": FIELDS, "additionalProperties": False}
    )
    values.update({key: value for key, value in overrides.items() if value is not None})
    if not values:
        return None
    validate(
        values,
        {
            "type": "object",
            "properties": FIELDS,
            "required": ["endpoint", "model"],
            "additionalProperties": False,
        },
    )
    agent = {
        key: values.pop(key)
        for key in ("max_attempts", "json_mode", "falsifier_model")
        if key in values
    }
    values["endpoint"] = completion_endpoint(values["endpoint"])
    return AgentModelProvider(ModelProfile(**values), **agent)


def safe_text(value):
    """Prevent telemetry/model text from executing terminal control sequences."""
    return "".join(
        c
        if c == "\n" or not unicodedata.category(c).startswith("C")
        else f"\\u{ord(c):04x}"
        for c in str(value)
    )


def import_static_eve(store, path):
    """Reuse ingestion identities, quarantine and atomic cursors on the DB owner."""
    follower = EveFollower(store, path, *SCOPE)
    try:
        # 16 MiB plus an EOF check; a growing source cannot make this unbounded.
        for _ in range(65):
            result = follower.poll_once()
            if not result["bytes_read"]:
                return result
        return {**result, "notice": "Read limit reached; use /follow to continue"}
    except SourceGap as error:
        store.record_source_incident(str(path), follower.committed, str(error))
        raise


HELP = """Commands (also accepts: 'triage alerts', 'show network information',
'investigate why this traffic is suspicious', 'show the latest report'):
  /import PATH        Import a stopped, readable EVE JSONL file once
  /follow PATH        Follow an append-only EVE file; /stop stops following
  /alerts             List up to 20 alerts with evidence IDs
  /triage             Group and prioritize up to 20 alerts using rules
  /network            Summarize up to 1,000 recent network records
  /investigate [QUESTION]  Run Triage → Correlation → Investigator → Falsifier → Reporter
  /report [RUN_ID]     Read a saved cited report (latest by default)
  /history            List saved runs
  /config [PATH]      Select a JSON provider config; /rules uses offline rules
  /test               Test model tools/schema using synthetic requests
  /status             Show source and investigation state
  /help /quit         Help or exit; Ctrl-C during a run requests cancellation
Unknown chat can be sent to the configured model after approval. It sees only
your message, and can propose an action for separate approval. No shell tools.
"""


def route(message):
    text = message.strip()
    if text.startswith("/"):
        name, _, argument = text[1:].partition(" ")
        return name.lower(), argument.strip()
    lower = text.lower()
    if any(word in lower for word in ("investigat", "analyz", "analyse")):
        return "investigate", text
    for word, action in (
        ("triage", "triage"),
        ("report", "report"),
        ("network", "network"),
        ("connection", "network"),
        ("alerts", "alerts"),
        ("history", "history"),
        ("status", "status"),
        ("help", "help"),
    ):
        if word in lower:
            return action, ""
    return "chat", text


class TerminalSession:
    def __init__(self, runtime, read=input, write=print):
        self.runtime, self.read, self.write = runtime, read, write

    def say(self, value):
        self.write(safe_text(value))

    def show(self, value):
        self.say(json.dumps(value, indent=2, default=str, ensure_ascii=True))

    def approve(self, description):
        self.say("\nProposed task: " + description)
        return self.read("Approve? [y/N] > ").strip().lower() in ("y", "yes")

    def activity(self, after):
        for event in self.runtime.activity.snapshot()["events"]:
            if event["sequence"] > after:
                self.say(
                    f"  {event['elapsed_seconds']:6.1f}s  {event['role']}"
                    f" · {event['status']} · {event['message']}"
                )
                after = event["sequence"]
        return after

    def investigate(self, question):
        provider = self.runtime.provider
        label = provider.label if provider else "deterministic offline rules"
        description = (
            f"Investigate live/external evidence using {label}; freeze a "
            "snapshot and save a cited report. Approves bounded read-only "
            "agent tools and model calls for this run. "
            + (
                "Normalized evidence is sent to the configured endpoint. "
                if provider
                else ""
            )
            + "Question: "
            + question
        )
        if not self.approve(description):
            return
        future = self.runtime.begin_run(
            *SCOPE, question=question, max_seconds=60 if provider else 5
        )
        after = 0
        while True:
            try:
                result = future.result(timeout=0.2)
                self.activity(after)
                self.show(result)
                return
            except TimeoutError:
                if future.done():
                    raise
                after = self.activity(after)
            except KeyboardInterrupt:
                self.runtime.cancel()
                self.say(
                    "Cancellation requested; waiting for the active call to return."
                )

    def chat(self, message):
        provider = self.runtime.provider
        if not provider:
            self.say("Use /help for local tasks or /config to select a chat model.")
            return
        if not self.approve(
            "Send this chat message to the configured model: " + message
        ):
            return
        self.say("Chat assistant · awaiting model response")
        response = request_completion(
            provider.profile,
            {
                "model": provider.profile.model,
                "store": False,
                "max_completion_tokens": provider.profile.max_output_tokens,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Blue Cheese's terminal assistant. You have no evidence "
                        "or tool access in this chat. Answer general network questions, "
                        "or suggest one of /triage, /network, /alerts, /investigate QUESTION, "
                        "/report, /history. Never claim to have executed tasks or observed "
                        "evidence. The user must enter and approve suggested commands.",
                    },
                    {"role": "user", "content": message},
                ],
            },
            provider.profile.timeout,
        )
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
            if choice["finish_reason"] != "stop" or not isinstance(content, str):
                raise ValueError("Chat returned incomplete output")
        except (KeyError, IndexError, TypeError):
            raise ValueError("Invalid chat response envelope") from None
        self.say(content)

    def execute(self, action, argument):
        if action == "help":
            self.say(HELP)
        elif action == "config":
            path = argument or self.read("Config JSON path > ").strip()
            provider = load_provider(path)
            self.runtime.configure_provider(provider)
            self.say("Provider config applied (no request sent).")
        elif action == "rules":
            self.runtime.configure_provider(None)
            self.say("Offline rules selected.")
        elif action == "status":
            self.show(self.runtime.status())
        elif action == "investigate":
            self.investigate(
                argument or "What does the observed network evidence support?"
            )
        elif action == "chat":
            self.chat(argument)
        elif action in ("import", "follow"):
            parts = shlex.split(argument)
            if len(parts) != 1:
                raise ValueError(
                    "Supply one EVE file path; quote paths containing spaces"
                )
            path = readable_eve_path(parts[0])
            if not self.approve(
                f"{action.title()} EVE file {path} into live/external evidence"
            ):
                return
            if action == "follow":
                self.runtime.start(path=path, replay=False)
                self.say(
                    "Following EVE file; automatic investigations remain disabled."
                )
            else:
                if self.runtime.status()["running"]:
                    raise ValueError("Stop following before a one-shot import")
                if path.stat().st_size > 16 * 1024 * 1024:
                    raise ValueError(
                        "One-shot imports are limited to 16 MiB; use /follow"
                    )
                self.show(self.runtime.database.apply(import_static_eve, path))
                self.say("EVE import completed. Use /triage or /investigate.")
        elif action == "stop":
            self.runtime.stop()
            self.say("Source stopped.")
        elif action in ("alerts", "triage", "network", "history", "report", "test"):
            if not self.approve(
                {
                    "alerts": "Read up to 20 scoped alerts",
                    "triage": "Run rule triage on up to 20 scoped alerts",
                    "network": "Summarize up to 1,000 recent scoped records (no network scan)",
                    "history": "Read saved scoped runs",
                    "report": "Read saved scoped report " + (argument or "(latest)"),
                    "test": "Send synthetic capability probes to the configured model endpoint",
                }[action]
            ):
                return
            self.say(action.title() + " · working")
            snapshot = self.runtime.command("snapshot")
            if action in ("alerts", "triage"):
                rows = self.runtime.command("list_alerts", *SCOPE, snapshot, limit=20)
                result = (
                    TriageAgent().triage_events(rows)
                    if action == "triage"
                    else [{"id": r["id"], "normalized": r["normalized"]} for r in rows]
                )
            elif action == "network":
                result = summarize(
                    self.runtime.command(
                        "visual_telemetry", *SCOPE, snapshot, limit=1000
                    )
                )
            elif action == "test":
                result = self.runtime.test_provider()
            else:
                history = self.runtime.command("list_runs", *SCOPE)
                result = history
                if action == "report":
                    run_id = argument or (history[0]["run_id"] if history else None)
                    result = (
                        self.runtime.command("get_run", *SCOPE, run_id)
                        if run_id
                        else None
                    )
            self.show(result)
        else:
            self.say("Unknown command. Use /help.")

    def run(self):
        self.say(
            "╭─ Blue Cheese · agent terminal\n╰─ /help for tasks · approvals default to No · /quit to exit"
        )
        self.say("State: " + str(self.runtime.state_dir.resolve()))
        self.say(
            "Engine: "
            + (
                self.runtime.provider.label
                if self.runtime.provider
                else "offline rules"
            )
        )
        while True:
            try:
                message = self.read("\nYou > ").strip()
                if not message:
                    continue
                action, argument = route(message)
                if action in ("quit", "exit"):
                    return
                self.execute(action, argument)
            except EOFError:
                return
            except KeyboardInterrupt:
                self.say("Task interrupted. /quit exits.")
            except (
                OSError,
                ValueError,
                RuntimeError,
                KeyError,
                ValidationError,
            ) as error:
                # Validation diagnostics may include config contents (including keys).
                self.say(
                    "Error: "
                    + (
                        "Invalid config fields/types; see config example."
                        if isinstance(error, ValidationError)
                        else str(error)
                    )
                )


def launch(directory, args):
    provider = load_provider(
        args.config,
        endpoint=args.endpoint,
        model=args.model,
        api_key_env=args.api_key_env,
        allow_remote=args.allow_remote,
        json_mode=args.json_mode,
        falsifier_model=args.falsifier_model,
        timeout=args.timeout,
        max_output_tokens=args.max_output_tokens,
        max_attempts=args.max_attempts,
    )
    runtime = DemoRuntime(directory, load_fixtures=False)
    try:
        if provider:
            runtime.configure_provider(provider)
        TerminalSession(runtime).run()
    finally:
        runtime.close()
