"""Deterministic evidence policy behind a replaceable provider interface."""

import json
import math
import time
from typing import Protocol

from bluecheese.agents.orchestrator import Orchestrator

PROVIDER_LABEL = "Deterministic demo provider (offline rules; no model)"


class BudgetExceeded(RuntimeError):
    pass


class RunCancelled(BudgetExceeded):
    pass


class EvidenceTools:
    """Fixed scope/snapshot, bounded typed queries, auditable retrieval ledger."""

    def __init__(
        self,
        store,
        scenario,
        variant,
        snapshot,
        max_calls=6,
        max_seconds=5.0,
        clock=time.monotonic,
        cancel_event=None,
        max_bytes=65536,
    ):
        self.cancel_event = cancel_event
        self.max_bytes = max(2, int(max_bytes))
        self.bytes_returned = 0
        self.store = store
        self.scope = (scenario, variant, snapshot)
        self.max_calls = max(0, int(max_calls))
        self.max_seconds = max(0.0, float(max_seconds))
        if not math.isfinite(float(max_seconds)):
            raise ValueError("Elapsed-time budget must be finite")
        self.clock = clock
        self.started = clock()
        self.activity = []
        self.retrieved = {}

    def check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise RunCancelled("Investigation cancelled by operator")

    def call(self, tool, **args):
        self.check_cancelled()
        if tool not in (
            "get_event",
            "list_alerts",
            "find_events_by_ip",
            "search_events",
        ):
            raise ValueError("Unknown typed tool")
        if (
            len(self.activity) >= self.max_calls
            or self.clock() - self.started >= self.max_seconds
        ):
            raise BudgetExceeded("Tool-call or elapsed-time limit reached")
        activity = {
            "tool": tool,
            "arguments": args,
            "returned_ids": [],
            "status": "ERROR",
            "returned_count": 0,
            "bytes": 0,
            "truncated": False,
        }
        try:
            result = getattr(self.store, tool)(*self.scope, **args)
            rows = ([result] if result else []) if tool == "get_event" else result
            delivered = []
            for row in rows:
                candidate = delivered + [row]
                size = len(json.dumps(candidate, ensure_ascii=False).encode("utf-8"))
                if size > self.max_bytes:
                    activity["truncated"] = True
                    break
                delivered.append(row)
            activity.update(
                status="OK",
                returned_ids=[r["id"] for r in delivered],
                returned_count=len(delivered),
                bytes=len(json.dumps(delivered, ensure_ascii=False).encode("utf-8")),
            )
            self.bytes_returned += activity["bytes"]
            self.retrieved.update({r["id"]: r for r in delivered})
        finally:
            self.activity.append(activity)
            if hasattr(self.store, "audit_tool"):
                self.store.audit_tool(activity)
        self.check_cancelled()
        if self.clock() - self.started >= self.max_seconds:
            raise BudgetExceeded("Elapsed-time limit reached during query")
        return (
            (delivered[0] if delivered else None) if tool == "get_event" else delivered
        )

    def validate(self, ids):
        for event_id in ids:
            if event_id not in self.retrieved:
                raise ValueError(f"Invented, cross-case or unseen citation: {event_id}")
            if self.store.get_event(*self.scope, event_id) is None:
                raise ValueError(f"Citation outside fixed snapshot: {event_id}")


class InvestigationProvider(Protocol):
    label: str

    def investigate(self, tools: EvidenceTools, falsification: bool) -> dict: ...


def active_flow(row):
    n = row["normalized"]
    amount = n.get("bytes_toserver")
    return (
        n["event_type"] == "flow"
        and n.get("flow_state") == "established"
        and isinstance(amount, (int, float))
        and amount >= 10000
    )


def failed_flow(row):
    n = row["normalized"]
    return (
        n["event_type"] == "flow"
        and n.get("flow_state") == "closed"
        and n.get("bytes_toserver") == 0
        and n.get("bytes_toclient") == 0
    )


def related_flow(row, alert):
    n, a = row["normalized"], alert["normalized"]
    return (
        n["event_type"] == "flow"
        and a.get("flow_id") is not None
        and n.get("flow_id") == a["flow_id"]
        and n["src_ip"] == a["src_ip"]
        and n["dest_ip"] == a["dest_ip"]
    )


class Falsifier:
    def check(self, tools, alert):
        # This independent query is executable and can reveal a failed connection
        # that the Investigator's initial alert retrieval never observed.
        rows = tools.call(
            "find_events_by_ip", ip=alert["normalized"]["src_ip"], limit=100
        )
        member_ids = getattr(tools, "correlated_ids", None)
        relevant = [
            r
            for r in rows
            if related_flow(r, alert) and (member_ids is None or r["id"] in member_ids)
        ]
        counters = [r["id"] for r in relevant if failed_flow(r)]
        return {
            "status": "evidence contradicted"
            if counters
            else ("not observed" if relevant else "not available"),
            "checked": "Alternative explanation: the alerted flow closed with zero bytes in both directions.",
            "query": tools.activity[-1],
            "returned_ids": [r["id"] for r in relevant],
            "counterevidence_ids": counters,
            "limitation": "Flow counters cannot establish intent; missing flow evidence cannot clear an alert.",
        }


class DemoInvestigator:
    label = PROVIDER_LABEL

    def investigate(self, tools, falsification=True):
        alerts = getattr(tools, "seed_alerts", None)
        if alerts is None:
            alerts = tools.call("list_alerts", limit=20)
        result = {
            "verdict": "UNCERTAIN",
            "hypothesis": "No alert available for investigation.",
            "supporting_ids": [],
            "contradicting_ids": [],
            "claims": [],
            "disconfirmation_test": "Find the alerted flow closing with zero bytes in both directions.",
            "unresolved": [
                "Intent and endpoint activity are not available in network logs."
            ],
            "falsifier": {
                "status": "disabled",
                "checked": "Falsification disabled",
                "returned_ids": [],
            },
        }
        if not alerts:
            result["unresolved"].append("No alert observed in this snapshot.")
            return result
        selected_seed = getattr(tools, "selected_seed_id", None)
        alert = next((row for row in alerts if row["id"] == selected_seed), alerts[0])
        result["hypothesis"] = (
            "The alerted connection may be command and control traffic."
        )
        result["supporting_ids"] = [alert["id"]]
        flows = tools.call("search_events", event_type="flow", limit=100)
        member_ids = getattr(tools, "correlated_ids", None)
        relevant = [
            r
            for r in flows
            if related_flow(r, alert) and (member_ids is None or r["id"] in member_ids)
        ]
        active = [r["id"] for r in relevant if active_flow(r)]
        result["supporting_ids"] += active
        if active:
            result["verdict"] = "SUSPICIOUS"
        else:
            result["unresolved"].append(
                "No established high-volume alerted flow observed."
            )
        if falsification:
            check = Falsifier().check(tools, alert)
            result["falsifier"] = check
            result["contradicting_ids"] = check["counterevidence_ids"]
            if check["counterevidence_ids"]:
                result["verdict"] = "UNCERTAIN" if active else "BENIGN_CONFOUNDER"
                if active:
                    result["unresolved"].append(
                        "Conflicting flow counters require independent validation."
                    )
            if check["status"] == "not available":
                result["unresolved"].append(
                    "Flow evidence needed to test the alternative explanation is unavailable."
                )
        result["claims"] = [
            {
                "text": "A sensor alert flags this connection; this is not proof of compromise.",
                "citations": [alert["id"]],
            }
        ]
        if active:
            result["claims"].append(
                {
                    "text": "Related established flows report at least 10,000 outbound bytes.",
                    "citations": active,
                }
            )
        if result["contradicting_ids"]:
            result["claims"].append(
                {
                    "text": "Related flow evidence reports a closed connection with zero bytes.",
                    "citations": result["contradicting_ids"],
                }
            )
        return result


def validate_report(report, tools):
    if not isinstance(report, dict) or report.get("verdict") not in {
        "UNCERTAIN",
        "SUSPICIOUS",
        "BENIGN_CONFOUNDER",
        "MALICIOUS",
        "BENIGN",
    }:
        raise ValueError("Provider returned an invalid verdict structure")
    for key in ("hypothesis", "disconfirmation_test"):
        if not isinstance(report.get(key), str) or len(report[key]) > 8192:
            raise ValueError(f"Invalid report field: {key}")
    for key in ("supporting_ids", "contradicting_ids", "claims", "unresolved"):
        if not isinstance(report.get(key), list) or len(report[key]) > 1000:
            raise ValueError(f"Invalid report collection: {key}")
    if not all(isinstance(item, str) for item in report["unresolved"]):
        raise ValueError("Unresolved questions must be text")
    if not isinstance(report.get("falsifier"), dict):
        raise ValueError("Invalid falsifier structure")  # noqa: TRY004 - provider boundary errors are validation failures
    ids = report["supporting_ids"] + report["contradicting_ids"]
    for claim in report["claims"]:
        if (
            not isinstance(claim, dict)
            or not isinstance(claim.get("text"), str)
            or len(claim["text"]) > 8192
            or not isinstance(claim.get("citations"), list)
            or not claim["citations"]
        ):
            raise ValueError("Claims require text and nonempty citations")
        ids += claim["citations"]
    for key in ("returned_ids", "counterevidence_ids"):
        references = report["falsifier"].get(key, [])
        if not isinstance(references, list):
            raise ValueError("Falsifier references must be a list")  # noqa: TRY004 - provider boundary
        ids += references
    if not all(isinstance(event_id, str) for event_id in ids):
        raise ValueError("Citation IDs must be strings")
    for candidate in report.get("triage", {}).get("candidates", []):
        ids += candidate["seed_ids"]
    for correlation in report.get("correlation", []):
        ids += correlation["member_ids"]
    tools.validate(ids)
    try:
        json.dumps(report, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("Provider output must be finite JSON data") from error


def investigate(
    store,
    scenario,
    variant,
    *,
    falsification=True,
    max_calls=6,
    max_seconds=5.0,
    provider=None,
    clock=time.monotonic,
    cancel_event=None,
    max_bytes=65536,
):
    provider = provider or DemoInvestigator()
    snapshot = store.snapshot()
    tools = EvidenceTools(
        store,
        scenario,
        variant,
        snapshot,
        max_calls,
        max_seconds,
        clock,
        cancel_event,
        max_bytes,
    )
    warnings = [
        "Synthetic data; rule-based verdicts are not a measurement of LLM performance.",
        "Log text and enrichment are untrusted. Claims use normalized telemetry fields.",
        "Evidence retrieval is capped at 100 rows per query; results may be incomplete.",
    ]
    run_status = "COMPLETED"
    try:
        tools.check_cancelled()
        report = Orchestrator().investigate(tools, provider, falsification)
        tools.check_cancelled()
        if clock() - tools.started >= tools.max_seconds:
            raise BudgetExceeded("Elapsed-time limit reached")
    except BudgetExceeded as error:
        run_status = "CANCELLED" if isinstance(error, RunCancelled) else "INCOMPLETE"
        warnings.append(str(error))
        report = {
            "verdict": "UNCERTAIN",
            "hypothesis": (
                "Investigation was cancelled by the operator."
                if run_status == "CANCELLED"
                else "Investigation did not complete within its budget."
            ),
            "supporting_ids": [],
            "contradicting_ids": [],
            "claims": [],
            "disconfirmation_test": "Retrieve related flow counterevidence within budget.",
            "unresolved": ["Evidence collection or falsification remains incomplete."],
            "falsifier": {
                "status": "not available",
                "checked": "Budget exhausted",
                "returned_ids": [],
            },
        }
    report.update(getattr(tools, "role_activity", {}))
    if any(call["truncated"] for call in tools.activity):
        warnings.append(
            "Evidence payload byte cap reached; only delivered records may be cited."
        )
    validate_report(report, tools)
    for index, claim in enumerate(report["claims"], 1):
        claim.setdefault("claim_id", f"claim-{index}")
        claim.setdefault(
            "proposition_type",
            "observation" if isinstance(provider, DemoInvestigator) else "unassessed",
        )
        claim.setdefault(
            "support_status",
            "SUPPORTED" if type(provider) is DemoInvestigator else "UNASSESSED",
        )
        claim.setdefault(
            "limitations",
            ["Network records do not establish intent or endpoint compromise."],
        )
    report.update(
        scenario=scenario,
        variant=variant,
        snapshot=snapshot,
        provider=provider.label,
        warnings=warnings,
        tool_activity=tools.activity,
        budget={
            "calls": len(tools.activity),
            "max_calls": tools.max_calls,
            "elapsed_seconds": round(clock() - tools.started, 6),
            "max_seconds": tools.max_seconds,
            "bytes_returned": tools.bytes_returned,
            "max_bytes_per_call": tools.max_bytes,
        },
        falsification_enabled=falsification,
        run_status=run_status,
        report_version=1,
        validation_state="MECHANICALLY_VALIDATED",
        qualifiers={
            "intent": "UNDETERMINED",
            "endpoint_compromise": "UNAVAILABLE",
            "confidence": "uncalibrated deterministic policy"
            if type(provider) is DemoInvestigator
            else "uncalibrated",
        },
    )
    return report
