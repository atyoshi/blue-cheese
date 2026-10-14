"""Serializable reports with explicit citations and provenance."""

import json

from bluecheese.agents.findings import findings_view
from bluecheese.application.presentation import report_presentation


def json_report(report):
    return json.dumps(report, indent=2)


def markdown_report(report):
    details = findings_view(report)
    presentation = report_presentation(report)
    lines = [
        "# " + (report.get("title") or "Blue Cheese investigation"),
        "",
        "Synthetic data"
        if report.get("synthetic", True)
        else "External telemetry; sensor coverage may be incomplete",
        "",
        report["provider"],
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        *protocol_table(report.get("protocol_observations", [])),
        "## Working hypothesis (unverified)",
        "",
        report["hypothesis"],
        "",
        f"Scope: {report['scenario']} / {report['variant']}; snapshot {report['snapshot']}",
        "",
        "## Assessed findings",
        "",
    ]
    if report.get("run_id"):
        lines[1:1] = [
            "",
            f"Run: {report['run_id']} | Case revision: {report['case_revision']} | Status: {report['run_status']}",
            f"Snapshot digest: {report['snapshot_digest']}",
            "Validation: mechanical citation checks; semantic support is a separate obligation.",
        ]
    for claim in report["claims"]:
        lines.append(f"- {claim['text']} Evidence: {', '.join(claim['citations'])}")
        lines.append(
            f"  Type: {claim.get('proposition_type', 'Not recorded')}; support: {claim.get('support_status', 'Model assessed; requires review')}"
        )
        lines.extend("  Limitation: " + item for item in claim.get("limitations", []))
        if claim.get("contradicting_ids"):
            lines.append(
                "  Contradicting evidence: " + ", ".join(claim["contradicting_ids"])
            )
    lines += [
        "",
        "## Activity and impact",
        "",
        details["activity_assessment"],
        details["observed_impact"]["status"],
        details["observed_impact"]["description"],
        "Evidence: " + ", ".join(details["observed_impact"]["citations"]),
        "Evidence limits: " + details["evidence_completeness"],
        "",
        "## Recommended next checks",
        "",
    ]
    for check in details["recommended_checks"]:
        lines.append(
            f"- **{check['action']}**\n  - Purpose: {check['purpose']}\n  - Required source: {check['required_source']}"
        )
    if not details["recommended_checks"]:
        lines.append("Case-specific next checks were not recorded.")
    if report.get("decision_advice"):
        lines += [
            "",
            "## Decision-model advice (uncalibrated)",
            "",
            "Scores are model choices, not calibrated attack likelihood or independent corroboration.",
            "```json",
            json.dumps(report["decision_advice"], indent=2),
            "```",
        ]
    if report.get("triage"):
        lines += [
            "",
            "## Triage and correlation",
            "",
            "```json",
            json.dumps(
                {
                    "triage": report["triage"],
                    "correlation": report.get("correlation", []),
                },
                indent=2,
            ),
            "```",
        ]
    lines += [
        "",
        "## Falsifier",
        "",
        "Status: " + report["falsifier"].get("status", "not recorded"),
        "",
        report["falsifier"].get("checked", "No countertest description recorded."),
        "",
        "Disconfirmation test: " + report["disconfirmation_test"],
        "",
        "## Unresolved evidence",
        "",
        *["- " + q for q in presentation["case_gaps"]],
        "",
        "## Analysis limits",
        "",
        *["- " + q for q in presentation["run_limitations"]],
        "",
        "## Interpretation guidance",
        "",
        *["- " + q for q in presentation["shared_guidance"]],
        "",
        "## Tool activity and consumed budget",
        "",
        "```json",
        json.dumps(
            {
                "falsifier": report["falsifier"],
                "tools": report["tool_activity"],
                "budget": report["budget"],
                "provider_activity": report.get("provider_activity"),
                "workflow_activity": report.get("workflow_activity"),
            },
            indent=2,
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"


def protocol_table(rows):
    if not rows:
        return []

    def cell(value):
        return (
            str(value if value is not None else "—")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("|", "&#124;")
            .replace("`", "&#96;")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    lines = [
        "## Observed protocol activity",
        "",
        "| Time | Source → destination | Method | Path | Status | Response bytes | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        values = [
            row.get("timestamp"),
            str(row.get("source")) + " → " + str(row.get("destination")),
            row.get("method"),
            row.get("path"),
            row.get("response_status"),
            row.get("response_length_bytes"),
            row.get("evidence_id"),
        ]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    return [*lines, ""]
