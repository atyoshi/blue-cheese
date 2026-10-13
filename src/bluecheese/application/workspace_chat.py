"""Contextual GUI chat using the CLI's typed planner; never executes proposals."""

import json

from bluecheese.agents.investigator import EvidenceTools
from bluecheese.application.store_worker import WorkerStore

SCOPE = ("live", "external")


def status_reply(status):
    state = status.get("stream_state") or (
        "Connected" if status["running"] else "Disconnected"
    )
    return (
        f"Sensor: {state}. {status['status']}. "
        f"Current source: {status.get('source') or 'not connected this session'}. "
        f"Last successful check: {status.get('last_poll') or 'none this session'}. "
        f"Last newly accepted record: {status.get('last_accepted') or 'none this session'}. "
        f"Stored evidence: {status['counts']['accepted']:,} accepted, {status['counts']['invalid']:,} quarantined. "
        f"Automatic investigations: {'on' if status['automatic_investigation'] else 'off'}. "
        + (
            "An investigation is running."
            if status["investigation_pending"]
            else "No investigation is running."
        )
    )


def respond(runtime, message, run_id):
    # Import here to keep the operational runtime independent of terminal UI startup.
    from bluecheese.interfaces.terminal import CHAT_SCHEMA, TerminalSession, route

    result = {
        "reply": "",
        "action": "answer",
        "argument": "",
        "citations": [],
        "run_id": run_id,
    }
    try:
        status = runtime.status()
        saved = runtime.command("get_run", *SCOPE, run_id) if run_id else None
        if run_id and saved is None:
            raise ValueError("Selected investigation no longer exists")
        provider = runtime.provider
        action, argument = route(message, model_chat=provider is not None)
        if not provider and not message.startswith("/"):
            lower = message.lower().strip()
            if any(
                word in lower
                for word in (
                    "what is running",
                    "what is happening",
                    "what are you doing",
                    "being investigated",
                    "activity",
                )
            ):
                action = "status"
        if action == "chat" and provider:
            snapshot = saved["snapshot"] if saved else runtime.command("snapshot")
            tools = EvidenceTools(
                WorkerStore(
                    runtime.database, saved["snapshot_id"] if saved else None, snapshot
                ),
                *SCOPE,
                snapshot,
                max_calls=6,
                max_seconds=30,
                cancel_event=runtime.chat_cancel,
            )
            report = saved.get("report") if saved else None
            if report:
                ids = list(
                    dict.fromkeys(
                        report["supporting_ids"] + report["contradicting_ids"]
                    )
                )[:4]
                for event_id in ids:
                    tools.call("get_event", event_id=event_id)
            else:
                tools.call("list_alerts", limit=10)
            observations = [
                {"id": item["id"], "normalized": item["normalized"]}
                for item in tools.retrieved.values()
            ]
            # Host paths and raw logs are unnecessary for model planning.
            health = {
                key: status.get(key)
                for key in (
                    "running",
                    "status",
                    "source_mode",
                    "stream_state",
                    "last_ingest",
                    "last_poll",
                    "last_accepted",
                    "counts",
                    "investigation_pending",
                    "automatic_investigation",
                )
            }
            context = {
                "health": health,
                "engine": provider.label,
                "role_implementations": {
                    "Triage": "rules",
                    "Correlation": "rules",
                    "Orchestrator": "software",
                    "Investigator": "configured model",
                    "Falsifier": "evidence countertest plus model review",
                },
                "selected_investigation": {
                    key: saved.get(key)
                    for key in (
                        "title",
                        "question",
                        "status",
                        "record_count",
                        "owner",
                        "disposition",
                    )
                }
                if saved
                else None,
                "activity": (saved.get("workflow_activity", [])[-12:] if saved else []),
                "observations": observations,
                "saved_assessment": {
                    "verdict": report.get("verdict"),
                    "hypothesis": report.get("hypothesis", "")[:1024],
                    "claims": [
                        claim
                        for claim in report.get("claims", [])
                        if set(claim["citations"]).issubset(tools.retrieved)
                    ][:8],
                    "unresolved": [
                        item[:512] for item in report.get("unresolved", [])[:10]
                    ],
                    "disconfirmation_test": report.get("disconfirmation_test", "")[
                        :1024
                    ],
                }
                if report
                else None,
                "instructions": (
                    "Answer questions about existing findings and current activity from this context. "
                    "Only propose investigate when the user requests NEW analysis or additional evidence checks. "
                    "Use citations containing actual observation IDs for evidence claims; no other IDs are permitted. "
                    "No endpoint processes, asset inventory, approved scan schedules or identity logs are connected. "
                    "Never imply an action executed: this response only proposes actions. "
                    "Return the required citations array even when empty."
                ),
            }
            schema = {
                **CHAT_SCHEMA,
                "properties": {
                    **CHAT_SCHEMA["properties"],
                    "citations": {
                        "type": "array",
                        "maxItems": 20,
                        "items": {"type": "string"},
                    },
                },
                "required": [*CHAT_SCHEMA["required"], "citations"],
            }
            session = TerminalSession(runtime)
            # Historical model text is conversational context, never evidence or proof of execution.
            session.chat_history = [
                {"role": item["role"], "content": item["content"][:2048]}
                for item in runtime.command("chat_history", *SCOPE, run_id)[-6:-1]
            ]
            plan = session.plan(
                message,
                context=context,
                schema=schema,
                transport=getattr(provider, "transport", None),
                max_input_bytes=65536,
            )
            if any(event_id not in tools.retrieved for event_id in plan["citations"]):
                raise ValueError(
                    "Chat cited evidence it did not retrieve; answer rejected"
                )
            result.update(plan)
            result["retrieval"] = tools.activity
            result["snapshot"] = snapshot
            action, argument = plan["action"], plan["argument"]
        result["action"] = action
        if runtime.chat_cancel.is_set():
            raise ValueError("Chat cancelled. No proposed action was executed")
        if action == "status":
            result["reply"] = status_reply(status)
            if saved:
                result["reply"] += (
                    f"\nSelected investigation: {saved['title']}. Analysis {saved['status'].lower()}."
                )
                if saved.get("workflow_activity"):
                    event = saved["workflow_activity"][-1]
                    result["reply"] += (
                        f"\nLatest recorded operation: {event['role']} · {event['message']}"
                    )
        elif action == "history":
            history = runtime.command("list_runs", *SCOPE)
            result["reply"] = (
                "\n".join(
                    f"{row.get('title') or row.get('question')} · {row['status']} · {row['created_at'][:19]}"
                    for row in history[:10]
                )
                or "No investigations saved yet."
            )
        elif action == "report":
            if saved and saved["report"]:
                result["reply"] = (
                    saved["report"]["hypothesis"]
                    + "\n\nUnknowns: "
                    + "; ".join(saved["report"]["unresolved"])
                )
                result["show_report"] = True
            else:
                result["reply"] = (
                    "This investigation has no completed report yet."
                    if saved
                    else "Open an investigation to review its report."
                )
        elif action in ("alerts", "triage", "network"):
            snapshot = saved["snapshot"] if saved else runtime.command("snapshot")
            if action == "network":
                from bluecheese.application.telemetry_visuals import summarize

                rows = (
                    runtime.command("case_evidence", *SCOPE, run_id)
                    if saved
                    else runtime.command(
                        "visual_telemetry", *SCOPE, snapshot, limit=1000
                    )
                )
                summary = summarize(rows)
                result["reply"] = (
                    f"{len(rows)} recent {'snapshot' if saved else 'workspace'} records across {len(summary['connections'])} directed IP pairs.\n"
                    + "\n".join(
                        f"{pair['source']} → {pair['destination']}: {pair['alerts']} alerts, {pair['flows']} flow records"
                        for pair in summary["connections"][:10]
                    )
                )
            else:
                tools = EvidenceTools(
                    WorkerStore(
                        runtime.database,
                        saved["snapshot_id"] if saved else None,
                        snapshot,
                    ),
                    *SCOPE,
                    snapshot,
                    max_calls=1,
                    max_seconds=30,
                )
                alerts = tools.call("list_alerts", limit=20)
                if action == "triage":
                    from bluecheese.agents.triage import TriageAgent

                    groups = TriageAgent().triage_events(alerts)["candidates"]
                    by_id = {row["id"]: row["normalized"] for row in alerts}
                    result["reply"] = (
                        "\n".join(
                            f"{group['priority'].title()} priority · {by_id[group['seed_ids'][0]].get('src_ip')} → {by_id[group['seed_ids'][0]].get('dest_ip')} · {group['occurrence_count']} alerts · {group['reason']}"
                            for group in groups
                        )
                        or "No alerts available for triage."
                    )
                else:
                    result["reply"] = (
                        "\n".join(
                            f"{row['normalized'].get('alert_signature') or 'Alert'} · {row['normalized'].get('src_ip')} → {row['normalized'].get('dest_ip')} · {row['normalized'].get('timestamp')}"
                            for row in alerts
                        )
                        or "No alerts in this evidence scope."
                    )
                result["citations"] = list(tools.retrieved)
                result["retrieval"] = tools.activity
            result["snapshot"] = snapshot
            result["view"] = (
                "Evidence"
                if saved
                else ("Network" if action == "network" else "Needs attention")
            )
        elif action == "help" or (action == "chat" and not provider):
            result["reply"] = (
                "Ask for status, history, reports, alerts or network connections. Select a case and ask to investigate it. "
                "For conversational explanations, configure a model under Settings → Agents and model endpoint. "
                "Refresh reloads saved state; it does not generate traffic. Investigation limits bound tool queries and cooperative run time."
            )
        elif action == "investigate":
            if not saved or not saved.get("seed_event_id"):
                result["reply"] = (
                    "Choose a specific alert under Needs attention before starting analysis."
                )
                result["action"] = "answer"
            else:
                result["reply"] = (
                    "Proposed follow-up: analyze this target using a new evidence snapshot. Previous findings stay available."
                )
                result["argument"] = message
        elif action in ("import", "follow", "stop", "test"):
            result["reply"] = "Proposed action: " + action + " " + argument
        elif action not in ("answer",):
            result["reply"] = "Use Settings to configure the sensor or model."
            result["action"] = "answer"
        if not result["reply"]:
            result["reply"] = (
                "Open a specific investigation so I can explain its evidence and activity."
            )
    except Exception as error:  # noqa: BLE001 - background request boundary records failures
        result = {
            "reply": str(error)[:4096],
            "action": "answer",
            "argument": "",
            "citations": [],
            "run_id": run_id,
            "error": True,
        }
    runtime.command("append_chat", *SCOPE, run_id, "assistant", json.dumps(result))
    return result
