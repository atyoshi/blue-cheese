"""Serializable reports with explicit citations and provenance."""

import json


def json_report(report):
    return json.dumps(report, indent=2)


def markdown_report(report):
    lines = [
        "# Blue Cheese investigation",
        "",
        "Synthetic data",
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
    for claim in report["claims"]:
        lines.append(f"- {claim['text']} Evidence: {', '.join(claim['citations'])}")
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
