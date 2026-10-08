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
        alerts = tools.call("list_alerts", limit=20)
        triage = self.triage.triage_events(alerts)
        correlations = []
        tools.role_activity = {"triage": triage, "correlation": correlations}
        # One bounded seed group per demo run; other triggers remain inspectable.
        if triage["candidates"]:
            selected = triage["candidates"][0]
            seed = next(row for row in alerts if row["id"] == selected["seed_ids"][0])
            ip = seed["normalized"].get("src_ip")
            if ip:
                related = tools.call("find_events_by_ip", ip=ip, limit=100)
                correlations.append(self.correlation.correlate(seed, related))
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
        report = provider.investigate(tools, falsification)
        report["triage"] = triage
        report["correlation"] = correlations
        report["workflow"] = {
            "policy_version": "bounded-workflow-v1",
            "roles": [
                "Orchestrator",
                "Triage",
                "Correlation",
                "Investigator",
                "Falsifier",
                "Reporter",
            ],
            "selection": "Highest triage priority, then stable occurrence ID; one seed group per run.",
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
