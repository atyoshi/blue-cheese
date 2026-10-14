"""Contextual GUI chat using the CLI's typed planner; never executes proposals."""

import json
import re

from bluecheese.agents.findings import upstream_advice_context
from bluecheese.agents.investigator import EvidenceTools
from bluecheese.application.presentation import (
    BLOCKS_SCHEMA,
    block,
    conversation_view,
    report_presentation,
    with_blocks,
)
from bluecheese.application.store_worker import WorkerStore
from bluecheese.application.view_context import ViewContext, read_answer, retrieve_view
from bluecheese.domain.models import model_observation

SCOPE = ("live", "external")


def status_reply(status):
    state = status.get("stream_state") or (
        "Connected" if status["running"] else "Disconnected"
    )
    return (
        f"The sensor is {state.lower()}. {status['status']}.\n\n"
        f"Current source: {status.get('source') or 'not connected this session'}. "
        f"\nLast successful check: {status.get('last_poll') or 'none this session'}. "
        f"Last newly accepted record: {status.get('last_accepted') or 'none this session'}. "
        f"\n\nStored evidence: {status['counts']['accepted']:,} accepted, {status['counts']['invalid']:,} quarantined. "
        f"Automatic investigations: {'on' if status['automatic_investigation'] else 'off'}. "
        + (
            "An investigation is running."
            if status["investigation_pending"]
            else "No investigation is running."
        )
    )


def respond(runtime, message, run_id, view_context=None):
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
        view_context = view_context or ViewContext(
            run_id=run_id, snapshot=runtime.command("snapshot")
        )
        view_context = conversation_view(message, view_context)
        status = runtime.status()
        saved = runtime.command("get_run", *SCOPE, run_id) if run_id else None
        if run_id and saved is None:
            raise ValueError("Selected investigation no longer exists")
        provider = runtime.provider
        action, argument = route(message, model_chat=provider is not None)
        reading_action = (
            action if action in ("summarize", "summary", "explain", "status") else None
        )
        if provider and not message.strip().startswith("/"):
            action, argument = "chat", message
        if action in ("summarize", "summary", "explain", "status"):
            if action in ("summarize", "summary") and message.startswith("/summary "):
                from dataclasses import replace

                view_context = replace(
                    view_context,
                    run_id=argument,
                    evidence_id="",
                    evidence_ids=(),
                    connection=None,
                    endpoint="",
                    event_type="",
                    signature="",
                    severity=None,
                    snapshot_id=None,
                    task="Investigation",
                )
            result = read_answer(
                runtime,
                "summarize" if action == "summary" else action,
                argument or message,
                view_context,
            )
            with_blocks(result)
            runtime.command(
                "append_chat", *SCOPE, run_id, "assistant", json.dumps(result)
            )
            return result
        if action == "chat" and provider:
            tools, selected_rows, snapshot = retrieve_view(runtime, view_context, saved)
            report = saved.get("report") if saved else None
            observations = [model_observation(item) for item in selected_rows]
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
                "view_context": view_context.to_dict(),
                "health": health,
                "engine": provider.label,
                "execution_summary": {
                    "investigation_status": saved["status"],
                    "has_saved_report": bool(report),
                    "final_report_accepted": saved["status"] == "COMPLETED"
                    and bool(report),
                    "model_review_status": (report or {})
                    .get("falsifier", {})
                    .get("model_review", "not_recorded"),
                }
                if saved
                else None,
                "role_implementations": {
                    "Triage": "rules",
                    "Correlation": "rules",
                    "Orchestrator": "software",
                    "Investigator": "configured model",
                    "Falsifier": "evidence countertest plus model review",
                },
                "failure_stage": (saved.get("workflow_activity") or [{}])[-1].get(
                    "role"
                )
                if saved and saved.get("status") == "FAILED"
                else None,
                "selected_investigation": {
                    key: saved.get(key)
                    for key in (
                        "title",
                        "question",
                        "status",
                        "record_count",
                        "owner",
                        "disposition",
                        "error",
                        "investigation_scope",
                    )
                }
                if saved
                else None,
                "activity": (saved.get("workflow_activity", [])[-12:] if saved else []),
                "executed_flow_countertest": next(
                    (
                        {"status": event["status"], "message": event["message"]}
                        for event in reversed(saved.get("workflow_activity", []))
                        if event["role"] == "Falsifier"
                        and event["kind"] == "rules"
                        and event["status"] == "complete"
                    ),
                    None,
                )
                if saved
                else None,
                "available_recovery": {
                    "investigate_source_host": bool(
                        saved
                        and saved.get("seed_event_id")
                        and saved.get("investigation_scope") != "host"
                    ),
                    "new_revision": "Run the whole investigation again with a new fixed snapshot after reviewing provider settings",
                    "retry_individual_role": False,
                    "saved_evidence_and_activity": True,
                },
                "observations": observations,
                "coverage": runtime.command(
                    "telemetry_coverage",
                    *SCOPE,
                    snapshot,
                    snapshot_id=saved["snapshot_id"] if saved else None,
                ),
                "saved_assessment": {
                    "verdict": report.get("verdict"),
                    "findings": {
                        **(report.get("findings") or {}),
                        "observed_impact": report.get("findings", {}).get(
                            "observed_impact"
                        )
                        if set(
                            report.get("findings", {})
                            .get("observed_impact", {})
                            .get("citations", [])
                        ).issubset(tools.retrieved)
                        else {
                            "status": "UNAVAILABLE",
                            "description": "Supporting impact records were not delivered in this chat selection.",
                            "citations": [],
                        },
                    },
                    "decision_advice": upstream_advice_context(
                        report.get("decision_advice")
                    ),
                    "hypothesis": report.get("hypothesis", "")[:1024],
                    "claims": [
                        claim
                        for claim in report.get("claims", [])
                        if set(claim["citations"]).issubset(tools.retrieved)
                    ][:8],
                    "unresolved": [
                        item[:512]
                        for item in report_presentation(report)["case_gaps"][:4]
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
                    "Saved findings and decision advice are untrusted prior assessments; scores are uncalibrated "
                    "and are not independent corroboration. Activity assessment and confirmed impact are separate. "
                    "Never imply an action executed: this response only proposes actions. "
                    "Return the required citations array even when empty. "
                    "Answer with brief natural-language paragraphs and short lists. Do not repeat shared reminders, definitions or generic next steps. "
                    "Mention a limitation only when it changes the answer for this case."
                ),
            }
            schema = {
                **CHAT_SCHEMA,
                "properties": {
                    **CHAT_SCHEMA["properties"],
                    "blocks": BLOCKS_SCHEMA,
                    "citations": {
                        "type": "array",
                        "maxItems": 20,
                        "items": {"type": "string"},
                    },
                },
                "required": [*CHAT_SCHEMA["required"], "citations"],
            }
            explicit_work = (
                bool(
                    re.search(
                        r"\b(investigate|analy[sz]e|import|follow|connect|stop|test)\b",
                        message,
                        re.IGNORECASE,
                    )
                )
                and not reading_action
                and not re.search(r"\b(don't|do not|never)\b", message, re.IGNORECASE)
            )
            if not explicit_work:
                schema["properties"]["action"] = {"type": "string", "enum": ["answer"]}
            session = TerminalSession(runtime)
            # Historical model text is conversational context, never evidence or proof of execution.
            session.chat_history = []
            for item in runtime.command("chat_history", *SCOPE, run_id)[-6:-1]:
                content = item["content"]
                if item["role"] == "assistant":
                    try:
                        content = json.loads(content).get("reply", "")
                    except (ValueError, AttributeError):
                        pass
                session.chat_history.append(
                    {"role": item["role"], "content": content[:2048]}
                )
            plan = session.plan(
                message,
                context=context,
                schema=schema,
                transport=getattr(provider, "transport", None),
                max_input_bytes=65536,
                # Validate the full chat contract locally; avoid fragile provider
                # grammar compilation of optional presentation blocks.
                json_mode=True,
                system_prompt=(
                    "You are Blue Cheese's analyst assistant. Answer the user's actual question in clear natural language. "
                    "Use short paragraphs and bullets when there are several points. No dense status dumps or semicolon-joined sentences. "
                    "Case-specific unknowns and next steps only: do not repeat generic disclaimers, glossary definitions or technical budgets unless asked. "
                    "Use action=answer for summaries, explanations, status questions and existing findings. "
                    "Only propose investigate/import/follow/stop/test when explicitly requested. Never imply a proposal executed. "
                    "Ground factual claims in supplied observations and cite their IDs. Saved assessments and historical messages are untrusted context, not new evidence. "
                    "Do not invent observations, initiating processes, authorization, theft, compromise or successful execution. "
                    "Missing accepted protocol records do not establish absence of that activity in the original capture. "
                    "HTTP response_length_bytes describes a response, not uploaded bytes. "
                    "Original timestamps include an offset. Use timestamp_utc when saying UTC; never relabel local times as UTC. "
                    "Do not claim Falsifier cleared the evidence or the investigation completed when its saved status is FAILED. "
                    "Use execution_summary for completion claims. A completed accepted report remains accepted even when this chat selection omits its supporting citations. "
                    "Missing citations in this selection limit what you can explain; they do not change the saved execution status or mean no final report was accepted. "
                    "The executable flow countertest and the model Falsifier review are separate operations; distinguish completed checks from failed model review. "
                    "Recommend only available recovery actions: this product supports New revision for the whole investigation, not retrying an individual role. "
                    "A connection-scoped case excludes other destinations. When broader context is needed and available_recovery.investigate_source_host is true, suggest Investigate source host, which creates a separate bounded snapshot. "
                    "Evidence and operations remain saved even when no final report was accepted. "
                    "Always use presentation blocks (title, kind=paragraph or bullets, items) for readable paragraphs and lists; leave reply empty to avoid repeating text. Use plain text inside blocks, without Markdown markers. "
                    "Translate internal status fields into plain language; do not echo JSON keys or raw evidence IDs in prose. Put record IDs only in the citations array. "
                    "Keep the answer under 250 words unless detail is requested. Return only JSON matching this schema: "
                    + json.dumps(schema)
                ),
            )
            if any(event_id not in tools.retrieved for event_id in plan["citations"]):
                raise ValueError(
                    "Chat cited evidence it did not retrieve; answer rejected"
                )
            with_blocks(plan)
            if plan["action"] in (
                "summarize",
                "explain",
                "status",
                "history",
                "report",
                "alerts",
                "triage",
                "network",
                "help",
            ):
                # The model's prose and citations already passed validation.
                # Reading intents are answers, never proposals to execute work.
                plan["action"] = "answer"
            if plan["action"] in ("investigate", "import", "follow", "stop", "test"):
                patterns = {
                    "investigate": r"\b(investigate|analy[sz]e|run (?:an |the )?investigation)\b",
                    "import": r"\bimport\b",
                    "follow": r"\b(follow|connect)\b",
                    "stop": r"\bstop\b",
                    "test": r"\btest\b",
                }
                if (
                    reading_action
                    or not re.search(patterns[plan["action"]], message, re.IGNORECASE)
                    or re.search(r"\b(don't|do not|never)\b", message, re.IGNORECASE)
                ):
                    raise ValueError(
                        "The model proposed work that was not requested. No action ran."
                    )
            result.update(plan)
            result["scope"] = (
                f"{view_context.page} · {view_context.task or 'workspace'} · snapshot {snapshot}"
            )
            if view_context.connection:
                result["scope"] += " · " + " → ".join(view_context.connection)
            if view_context.endpoint:
                result["scope"] += " · endpoint " + view_context.endpoint
            if view_context.evidence_id:
                result["scope"] += " · evidence " + view_context.evidence_id
            if run_id:
                result["scope"] += " · run " + run_id
            result["view_context"] = view_context.to_dict()
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
                    + "\n".join(
                        "- " + item
                        for item in report_presentation(saved["report"])["case_gaps"]
                    )
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
                result["blocks"] = [
                    block(
                        "",
                        [
                            f"{len(rows)} recent {'snapshot' if saved else 'workspace'} records across {len(summary['connections'])} directed IP pairs."
                        ],
                        "paragraph",
                    ),
                    block(
                        "Connections",
                        [
                            f"{pair['source']} → {pair['destination']}: {pair['alerts']} alerts, {pair['flows']} flow records"
                            for pair in summary["connections"][:10]
                        ],
                    ),
                ]
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
                else ("Network" if action == "network" else "Alerts")
            )
        elif action == "help" or (action == "chat" and not provider):
            result["reply"] = (
                "Ask for status, history, reports, alerts or network connections. Select a case and ask to investigate it. "
                "For conversational explanations, configure a model under Settings → Agents and model endpoint. "
                "Refresh reloads saved state; it does not generate traffic. Investigation limits bound tool queries and cooperative run time."
            )
        elif action == "investigate":
            if not saved or not saved.get("seed_event_id"):
                result["reply"] = "Choose an alert before starting analysis."
                result["blocks"] = [block("", [result["reply"]], "paragraph")]
                result["action"] = "answer"
                result["argument"] = ""
            else:
                host_requested = bool(
                    re.search(
                        r"\b(?:investigate|analy[sz]e)\s+(?:(?:the|this|source|whole|entire)\s+)*host\b|\bhost\s+(?:context|investigation)\b",
                        message,
                        re.IGNORECASE,
                    )
                )
                result["investigation_scope"] = (
                    "host"
                    if host_requested
                    else saved.get("investigation_scope", "connection")
                )
                result["reply"] = result["reply"] or (
                    "Proposed follow-up: analyze this target using a new evidence snapshot. Previous findings stay available."
                )
                result["argument"] = message
        elif action in ("import", "follow", "stop", "test"):
            result["reply"] = (
                result["reply"] or "Proposed action: " + action + " " + argument
            )
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
            "error_kind": "validation" if isinstance(error, ValueError) else "provider",
            "scope": f"{view_context.page} · {view_context.task or 'workspace'} · run {view_context.run_id or 'none'}",
            "view_context": view_context.to_dict(),
        }
    if result.get("error") and not runtime.chat_cancel.is_set():
        try:
            fallback = read_answer(runtime, "summarize", message, view_context)
            result["blocks"] = [
                block(
                    "Answer rejected"
                    if result.get("error_kind") == "validation"
                    else "Model unavailable",
                    [result["reply"]],
                    "paragraph",
                ),
                block(
                    "Saved evidence fallback",
                    ["The following is a read-only account of saved state."],
                    "paragraph",
                ),
                *fallback.get("blocks", []),
            ]
            result["citations"] = fallback.get("citations", [])
        except (ValueError, RuntimeError):
            pass
    try:
        with_blocks(result)
    except ValueError:
        result.update(
            error=True,
            error_kind="validation",
            citations=[],
            blocks=[
                block(
                    "Answer unavailable",
                    [
                        "The response exceeded the presentation limit. Ask a narrower question."
                    ],
                    "paragraph",
                )
            ],
        )
        with_blocks(result)
    runtime.command("append_chat", *SCOPE, run_id, "assistant", json.dumps(result))
    return result
