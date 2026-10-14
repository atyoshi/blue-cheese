"""Captured, bounded reading context and read-only conversational answers."""

import re
from dataclasses import asdict, dataclass, replace
from ipaddress import ip_address

from bluecheese.agents.investigator import EvidenceTools
from bluecheese.application.store_worker import WorkerStore

SCOPE = ("live", "external")
DEFINITIONS = {
    "alert": "An alert is a sensor rule match in network traffic. It asks for review; it does not prove compromise.",
    "flow": "A flow is a record of a network conversation between endpoints, usually including addresses, ports, protocol, timing and byte counts. It is not a packet capture or a process identity.",
    "endpoint": "An endpoint is one side of a network conversation, shown here by its IP address. An IP alone does not establish the device owner or user.",
    "quarantine": "Quarantine holds malformed or unsupported input records. Supported evidence includes alerts, flows, DNS, HTTP and TLS. It does not isolate a device.",
    "snapshot": "A snapshot freezes the evidence membership and interpretations used by an investigation. Later arrivals do not change its findings.",
    "severity": "Severity is the sensor rule's review priority: 1 is high, 2 medium and 3 low. It is not a probability of compromise.",
    "budget": "An investigation budget limits evidence queries and elapsed time. Time limits and cancellation are cooperative: an active model request must return before work stops.",
}


@dataclass(frozen=True)
class ViewContext:
    page: str = "Workspace"
    task: str = ""
    run_id: str | None = None
    snapshot: int | None = None
    snapshot_id: str | None = None
    endpoint: str = ""
    connection: tuple[str, str] | None = None
    evidence_id: str = ""
    evidence_ids: tuple[str, ...] = ()
    event_type: str = ""
    signature: str = ""
    severity: int | None = None
    record_limit: int = 20
    graph_limit: int = 12
    display_limit: int = 20

    def to_dict(self):
        return asdict(self)


def reading_intent(message):
    """Resolve read-only requests before model planning or analysis keywords."""
    text = message.strip().lower()
    if text.startswith(
        (
            "investigate ",
            "please investigate ",
            "start an investigation",
            "run an investigation",
            "analyze ",
            "analyse ",
        )
    ):
        return None
    if text.startswith("/summary") and text.split()[0] == "/summary":
        return "summarize", message.partition(" ")[2].strip()
    if text.startswith("/explain") and text.split()[0] == "/explain":
        return "explain", message.partition(" ")[2].strip()
    if any(word in text for word in ("summarize", "summarise", "summary")):
        return "summarize", message
    if any(
        word in text
        for word in (
            "what is happening",
            "what are you doing",
            "what is running",
            "what is being investigated",
            "being investigated",
        )
    ):
        return "status", message
    if text in ("show the evidence", "show evidence"):
        return "explain", "show the evidence"
    if any(
        word in text
        for word in (
            "explain",
            "what am i looking at",
            "what does this",
            "what should i check next",
        )
    ):
        return "explain", message
    if text.startswith(("what is ", "define ")) and any(
        term in text for term in DEFINITIONS
    ):
        return "explain", message
    return None


def definition(message):
    text = message.lower().strip(" ?.")
    if any(word in text for word in ("this ", "these ", "view", "next")):
        return None
    if text.startswith("explain "):
        text = text.removeprefix("explain ")
        for article in ("a ", "an ", "the "):
            text = text.removeprefix(article)
    text = text.replace("investigation budget", "budget")
    for term, explanation in DEFINITIONS.items():
        if text == term or text in (
            f"what is a {term}",
            f"what is an {term}",
            f"what is {term}",
            f"what is the {term}",
            f"define {term}",
            f"investigation {term}",
        ):
            return explanation
    return None


def resolve_view(message, view):
    """Explicit targets outrank the previous reading context."""
    run = re.search(
        r"\b(?:run|investigation)\s+([0-9a-f]{32})\b", message, re.IGNORECASE
    )
    evidence = re.search(
        r"\b(?:evidence|record|alert)\s+([0-9a-f]{24})\b", message, re.IGNORECASE
    )
    if run:
        return replace(
            view,
            run_id=run[1].lower(),
            task="Investigation",
            evidence_id="",
            evidence_ids=(),
            connection=None,
            endpoint="",
            event_type="",
            signature="",
            severity=None,
            snapshot_id=None,
        )
    if evidence:
        return replace(
            view, evidence_id=evidence[1].lower(), evidence_ids=(), event_type=""
        )
    addresses = []
    for candidate in re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", message):
        try:
            addresses.append(str(ip_address(candidate)))
        except ValueError:
            continue
    if addresses:
        explicit = replace(
            view,
            evidence_id="",
            evidence_ids=(),
            endpoint=addresses[0] if len(addresses) == 1 else "",
            connection=tuple(addresses[:2]) if len(addresses) >= 2 else None,
        )
        if view.page == "Terminal":
            explicit = replace(
                explicit,
                run_id=None,
                snapshot=None,
                snapshot_id=None,
                task="Explicit network target",
                event_type="",
                signature="",
                severity=None,
            )
        return explicit
    if "alerts" in message.lower() and not any(
        word in message.lower() for word in ("investigation", "report")
    ):
        return replace(view, task="Alerts", event_type="alert")
    return view


def retrieve_view(runtime, view, saved, *, max_calls=6):
    """Only delivered snapshot-bound records may support a response."""
    snapshot = saved["snapshot"] if saved else view.snapshot
    if snapshot is None:
        snapshot = runtime.command("snapshot")
    tools = EvidenceTools(
        WorkerStore(
            runtime.database, saved["snapshot_id"] if saved else None, snapshot
        ),
        *SCOPE,
        snapshot,
        max_calls=max_calls,
        max_seconds=30,
        cancel_event=runtime.chat_cancel,
    )
    limit = max(1, min(view.record_limit, 20))
    if view.evidence_id:
        tools.call("get_event", event_id=view.evidence_id)
    elif view.evidence_ids:
        for event_id in view.evidence_ids[:max_calls]:
            tools.call("get_event", event_id=event_id)
    elif view.connection or view.endpoint:
        ip = view.connection[0] if view.connection else view.endpoint
        rows = tools.call("find_events_by_ip", ip=ip, limit=limit)
        if view.connection:
            # Keep the ledger intact; only matching observations enter the answer.
            rows = [
                r
                for r in rows
                if (r["normalized"].get("src_ip"), r["normalized"].get("dest_ip"))
                == tuple(view.connection)
            ]
            if view.event_type:
                rows = [
                    r
                    for r in rows
                    if r["normalized"].get("event_type") == view.event_type
                ]
            return tools, rows, snapshot
    elif view.event_type:
        tools.call("search_events", event_type=view.event_type, limit=limit)
    elif (
        saved and saved.get("report") and view.task not in ("Alerts", "Needs attention")
    ):
        report = saved["report"]
        ids = list(
            dict.fromkeys(
                report["supporting_ids"]
                + report["contradicting_ids"]
                + [i for c in report.get("claims", []) for i in c["citations"]]
                + report.get("findings", {})
                .get("observed_impact", {})
                .get("citations", [])
            )
        )[:max_calls]
        for event_id in ids:
            tools.call("get_event", event_id=event_id)
    elif saved and saved.get("seed_event_id"):
        tools.call("get_event", event_id=saved["seed_event_id"])
        tools.call(
            "find_related_events",
            seed_id=saved["seed_event_id"],
            event_types=["flow", "http", "dns", "tls", "alert"],
            limit=limit,
        )
    else:
        tools.call("list_alerts", limit=limit)
    rows = list(tools.retrieved.values())
    if view.event_type:
        rows = [r for r in rows if r["normalized"].get("event_type") == view.event_type]
    if view.signature:
        rows = [
            r
            for r in rows
            if view.signature.lower()
            in (r["normalized"].get("alert_signature") or "").lower()
        ]
    if view.severity is not None:
        rows = [r for r in rows if r["normalized"].get("severity") == view.severity]
    return tools, rows, snapshot


def read_answer(runtime, intent, message, view):
    """Offline prose about observed state; never creates or schedules a run."""
    from bluecheese.application.presentation import conversation_view

    view = conversation_view(message, resolve_view(message, view))
    saved = runtime.command("get_run", *SCOPE, view.run_id) if view.run_id else None
    if view.run_id and saved is None:
        raise ValueError("Selected investigation is unavailable; choose another scope")
    if saved:
        view = replace(
            view, snapshot=saved["snapshot"], snapshot_id=saved["snapshot_id"]
        )
    if runtime.chat_cancel.is_set():
        raise ValueError("Chat cancelled. No proposed action was executed")
    scope = (
        f"{saved.get('title') or saved['question']} · run {view.run_id} · frozen snapshot {saved['snapshot']}"
        if saved
        else f"{view.page} · bounded workspace overview"
    )
    if view.task:
        scope += " · " + view.task
    if view.connection:
        scope += " · " + " → ".join(view.connection)
    if view.endpoint:
        scope += " · endpoint " + view.endpoint
    if view.evidence_id:
        scope += " · evidence " + view.evidence_id
    result = {
        "reply": "",
        "action": "answer",
        "argument": "",
        "citations": [],
        "run_id": view.run_id,
        "scope": scope,
        "view_context": view.to_dict(),
    }
    general = definition(message) if intent == "explain" else None
    if general:
        result.update(
            reply=general, scope="General definition · no evidence assessment"
        )
        return result
    if intent == "status":
        from bluecheese.application.workspace_chat import status_reply

        result["reply"] = status_reply(runtime.status())
        if saved:
            events = saved.get("workflow_activity") or []
            result["reply"] += (
                f"\nSelected investigation: {saved['title']}. Analysis {saved['status'].lower()}."
            )
            if events:
                result["reply"] += (
                    "\nLatest recorded operation: "
                    + events[-1]["role"]
                    + " · "
                    + events[-1]["message"]
                )
                next_stage = events[-1].get("handoff_to")
                if next_stage:
                    result["reply"] += (
                        " Next software-controlled stage: " + next_stage + "."
                    )
            else:
                result["reply"] += " Historical operation details are unavailable."
        return result
    tools, rows, snapshot = retrieve_view(runtime, view, saved)
    if not saved:
        result["scope"] += f" · snapshot watermark {snapshot}"
    result.update(
        citations=[row["id"] for row in rows],
        retrieval=tools.activity,
        snapshot=snapshot,
    )
    normalized = [row["normalized"] for row in rows]
    alerts = [row for row in normalized if row.get("event_type") == "alert"]
    flows = [row for row in normalized if row.get("event_type") == "flow"]
    view_explanations = {
        "Connections": "The map shows directed IP relationships and counts from a bounded record window. Selecting a connection narrows its evidence; the map does not establish device ownership.",
        "Evidence and connections": "The map links directed IP pairs from the frozen snapshot. The connection list and evidence drawer show records behind that relationship.",
        "Activity": "The timeline counts records by event time in labelled bins. It is a summary of saved input, not a packet capture or evidence that a task is running.",
        "Evidence": "These are accepted records behind the view. Original log text is retained exactly; normalized fields support filtering and evidence queries.",
        "Findings": "These are saved machine findings for a fixed snapshot. Execution status describes whether analysis finished; the assessment describes what the available evidence supports.",
        "Agent activity": "This view records executed software, rule, model and retrieval operations. A model wait means a request is in flight; it does not mean findings have been produced.",
        "Analyst decision": "This form records your attribution, assignment, disposition and notes separately from machine findings. Saving a decision preserves the evidence and report.",
    }
    from bluecheese.application.presentation import (
        block,
        report_presentation,
        with_blocks,
    )

    blocks = []
    if intent == "explain":
        explanation = view_explanations.get(view.task)
        if explanation:
            blocks.append(block("", [explanation], "paragraph"))
    if saved:
        report = saved.get("report") or {}
        summary = f"The investigation of {saved.get('title') or saved['question']} is {saved['status'].lower()}."
        if report.get("hypothesis"):
            summary += " " + report["hypothesis"][:1024]
        elif saved.get("error"):
            summary += " Analysis failed: " + saved["error"][:512]
        else:
            summary += " No final assessment has been recorded."
        blocks.append(block("", [summary], "paragraph"))
        presentation = report_presentation(report)
        if presentation["case_gaps"]:
            blocks.append(block("Open questions", presentation["case_gaps"][:4]))
        checks = report.get("findings", {}).get("recommended_checks", [])
        if checks:
            blocks.append(block("Next checks", [c["action"] for c in checks[:3]]))
        if presentation["run_limitations"]:
            blocks.append(block("Analysis limits", presentation["run_limitations"][:3]))
    if rows:
        if not saved or not saved.get("report"):
            result["citations"] = [row["id"] for row in rows[:4]]
        blocks.append(
            block(
                "Evidence reviewed",
                [
                    f"{r.get('alert_signature') or r.get('flow_state') or r.get('event_type')} from {r.get('src_ip') or '?'} to {r.get('dest_ip') or '?'} at {r.get('timestamp') or 'an unavailable time'}."
                    for r in normalized[:4]
                ],
            )
        )
    else:
        blocks.append(
            block(
                "Evidence coverage",
                [
                    "No matching accepted records were delivered for this selection. This does not establish absence of activity."
                ],
                "paragraph",
            )
        )
    if not saved:
        blocks.insert(
            0,
            block(
                "",
                [
                    f"This selection contains {len(alerts)} {'alert' if len(alerts) == 1 else 'alerts'} and {len(flows)} {'flow' if len(flows) == 1 else 'flows'} among {len(rows)} delivered {'record' if len(rows) == 1 else 'records'}. No new investigation has started."
                ],
                "paragraph",
            ),
        )
    result["blocks"] = blocks
    result["coverage"] = {
        "delivered": len(rows),
        "truncated": any(c["truncated"] for c in tools.activity),
    }
    return with_blocks(result)
