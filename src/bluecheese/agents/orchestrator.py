"""Deterministic coordination of bounded logical roles; no agent framework."""

import hashlib
import json

from bluecheese.agents.correlation import CorrelationAgent
from bluecheese.agents.triage import TriageAgent


class Orchestrator:
    def __init__(self, triage=None, correlation=None):
        self.triage = triage or TriageAgent()
        self.correlation = correlation or CorrelationAgent()

    def investigate(self, tools, provider, falsification):
        tools.emit(
            "Orchestrator",
            "working",
            "Loading alerts from the frozen evidence snapshot.",
        )
        alerts = tools.call("list_alerts", limit=20)
        requested = getattr(tools, "requested_seed_id", None)
        if requested:
            seed = tools.call("get_event", event_id=requested)
            if seed is None or seed["normalized"]["event_type"] != "alert":
                raise ValueError("Requested alert is outside the run snapshot")
            alerts = [seed] + [row for row in alerts if row["id"] != requested]
        tools.emit(
            "Orchestrator",
            "handoff",
            "Sending retrieved alerts to Triage for prioritization.",
            handoff_to="Triage",
        )
        tools.emit(
            "Triage",
            "working",
            "Grouping alerts and assigning review priorities.",
            kind="rules",
        )
        triage = self.triage.triage_events(alerts)
        tools.emit(
            "Triage",
            "handoff",
            f"Returning {len(triage['candidates'])} prioritized group(s) to Orchestrator.",
            kind="rules",
            handoff_to="Orchestrator",
        )
        correlations = []
        tools.role_activity = {"triage": triage, "correlation": correlations}
        # One bounded seed group per demo run; other triggers remain inspectable.
        if triage["candidates"]:
            selected = triage["candidates"][0]
            seed = next(
                row
                for row in alerts
                if row["id"] == (requested or selected["seed_ids"][0])
            )
            ip = seed["normalized"].get("src_ip")
            if ip:
                tools.emit(
                    "Orchestrator",
                    "handoff",
                    f"Selected {seed['normalized'].get('alert_signature') or 'alert'}: {ip} → {seed['normalized'].get('dest_ip')}. Sending to Correlation.",
                    handoff_to="Correlation",
                )
                tools.emit(
                    "Correlation",
                    "working",
                    "Linking evidence by source, sensor, time and connection.",
                    kind="rules",
                )
                related = tools.call(
                    "find_related_events",
                    seed_id=seed["id"],
                    event_types=["flow", "http", "dns", "tls", "alert"],
                    limit=100,
                )
                correlations.append(self.correlation.correlate(seed, related))
                tools.emit(
                    "Correlation",
                    "handoff",
                    f"Linked {len(correlations[-1]['member_ids'])} records for {ip}; excluded {correlations[-1]['excluded_count']} candidates.",
                    kind="rules",
                    handoff_to="Orchestrator",
                )
        if not correlations:
            tools.emit(
                "Correlation",
                "skipped",
                "No eligible alert endpoint is available for correlation.",
                kind="rules",
            )
        tools.correlated_ids = {
            event_id
            for correlation in correlations
            for event_id in correlation["member_ids"]
        }
        tools.seed_alerts = alerts
        tools.selected_seed_id = (
            correlations[0]["seed_id"]
            if correlations
            else (alerts[0]["id"] if alerts else None)
        )
        tools.context_ids = []
        if getattr(tools, "investigation_scope", "connection") == "host":
            tools.emit(
                "Orchestrator",
                "working",
                "Retrieving diverse protocol observations across the selected host's frozen five-minute neighborhood; these are context, not causal links.",
            )
            context_rows = tools.call(
                "find_host_context", seed_id=tools.selected_seed_id, limit=24
            )
            tools.context_ids = [row["id"] for row in context_rows]
        elif getattr(provider, "prefetch_protocol_context", False):
            # Alert-heavy broad queries can exhaust delivery bytes before protocol
            # observations. Acquire one bounded typed slice of an observed protocol.
            kinds = {
                row["normalized"]["event_type"] for row in tools.retrieved.values()
            }
            kind = next(
                (value for value in ("http", "dns", "tls") if value in kinds), None
            )
            if kind:
                tools.emit(
                    "Orchestrator",
                    "working",
                    "Retrieving bounded protocol context to complement alert and flow evidence.",
                )
                tools.call(
                    "find_related_events",
                    seed_id=tools.selected_seed_id,
                    event_types=[kind],
                    limit=20,
                )
        advisor = getattr(tools, "decision_provider", None)
        if advisor is not None:
            advisor.assess(tools)
        if not falsification:
            tools.emit(
                "Falsifier",
                "skipped",
                "Counterevidence checks are disabled for this run.",
            )
        tools.emit(
            "Orchestrator",
            "handoff",
            "Assigning the selected evidence to Investigator for assessment.",
            handoff_to="Investigator",
        )
        tools.emit(
            "Investigator", "working", "Starting assessment of the selected evidence."
        )
        report = provider.investigate(tools, falsification)
        tools.emit(
            "Orchestrator",
            "working",
            "Received the assessment; preparing it for validation.",
        )
        report["triage"] = triage
        report["correlation"] = correlations
        report["workflow"] = {
            "policy_version": "bounded-workflow-v2",
            "roles": [
                "Orchestrator",
                "Triage",
                "Correlation",
                *(["Decision model"] if advisor else []),
                "Investigator",
                "Falsifier",
                "Reporter",
            ],
            "investigation_scope": getattr(tools, "investigation_scope", "connection"),
            "context_ids": tools.context_ids,
            "selection": "Analyst-selected source host; same-source traffic to and from that host within five minutes. Cross-connection observations are context, not causal links."
            if getattr(tools, "investigation_scope", "connection") == "host"
            else "Analyst-selected alert; same-source endpoint neighborhood within five minutes."
            if requested
            else "Highest triage priority, then stable occurrence ID; one seed group per run.",
            "automatic_response": False,
        }
        return report

    def complete(self, database, run, report, synthetic):
        """Assemble run provenance and commit a validated terminal report."""
        report.update(run)
        report.update(
            synthetic=synthetic,
            report_id=run["run_id"],
            parser_version="suricata-canonical-v1",
        )
        configuration = {
            "provider": report["provider"],
            "falsification": report["falsification_enabled"],
            "max_calls": report["budget"]["max_calls"],
            "max_seconds": report["budget"]["max_seconds"],
            "max_bytes_per_call": report["budget"]["max_bytes_per_call"],
            "workflow_policy": "bounded-workflow-v1",
        }
        report["broker_configuration_hash"] = hashlib.sha256(
            json.dumps(configuration, sort_keys=True).encode()
        ).hexdigest()
        database.call("finish_run", run["run_id"], report["run_status"], report)
        return report
