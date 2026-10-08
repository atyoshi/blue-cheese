"""Serializable reports with explicit citations and provenance."""

import json


def json_report(report):
    return json.dumps(report, indent=2)


def markdown_report(report):
    lines = [
        "# Blue Cheese investigation",
        "",
        "Synthetic data"
        if report.get("synthetic", True)
        else "External telemetry; sensor coverage may be incomplete",
        "",
        report["provider"],
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        report["hypothesis"],
        "",
        f"Scope: {report['scenario']} / {report['variant']}; snapshot {report['snapshot']}",
        "",
        "## Claims",
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
        json.dumps(report["falsifier"], indent=2),
        "",
        "Disconfirmation test: " + report["disconfirmation_test"],
        "",
        "## Unresolved evidence",
        "",
        *["- " + q for q in report["unresolved"]],
        "",
        "## Warnings",
        "",
        *["- " + q for q in report["warnings"]],
        "",
        "## Tool activity and consumed budget",
        "",
        "```json",
        json.dumps(
            {"tools": report["tool_activity"], "budget": report["budget"]}, indent=2
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"
