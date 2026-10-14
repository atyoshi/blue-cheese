"""Shared, escaped-text presentation; stored evidence and historical reports stay intact."""

import json
import re

SHARED_GUIDANCE = [
    "Alerts are sensor rule matches, not proof of compromise. Severity indicates review priority.",
    "Network evidence does not identify an initiating process or establish authorization by itself.",
    "Model assessments and scores require analyst review; scores are not calibrated probabilities.",
]
# Exact legacy notices only. Unknown text remains visible; never hide by fuzzy matching.
LEGACY_GUIDANCE = {
    "Intent and endpoint activity are not available in network logs.",
    "Log text and enrichment are untrusted. Claims use normalized telemetry fields.",
    "Evidence retrieval is capped at 100 rows per query; results may be incomplete.",
    "Synthetic data; rule-based verdicts are not a measurement of LLM performance.",
    "External telemetry; machine findings require analyst review and do not establish compromise.",
    "Network records do not establish intent or endpoint compromise.",
    "Flow counters cannot establish intent; missing flow evidence cannot clear an alert.",
}

BLOCKS_SCHEMA = {
    "type": "array",
    "maxItems": 6,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "maxLength": 80},
            "kind": {"type": "string", "enum": ["paragraph", "bullets"]},
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {"type": "string", "minLength": 1, "maxLength": 1200},
            },
        },
        "required": ["title", "kind", "items"],
    },
}


def clean_sentence(value):
    return str(value).strip().rstrip("; ")


def block(title, items, kind="bullets"):
    return {
        "title": title,
        "kind": kind,
        "items": [clean_sentence(i) for i in items if str(i).strip()],
    }


def with_blocks(result):
    """One canonical compatibility reply, with paragraphs/lists available to any UI."""
    blocks = result.get("blocks")
    if not blocks:
        paragraphs = [
            part.strip()
            for part in re.split(r"\n\s*\n", result.get("reply", ""))
            if part.strip()
        ]
        blocks = []
        for part in paragraphs:
            lines = [line.strip() for line in part.splitlines() if line.strip()]
            blocks.append(
                block(
                    "",
                    [re.sub(r"^[-*]\s+", "", line) for line in lines],
                    "bullets" if len(lines) > 1 else "paragraph",
                )
            )
    blocks = [b for b in blocks if b.get("items")]
    result["blocks"] = blocks
    result["reply"] = "\n\n".join(
        (b["title"] + "\n" if b.get("title") else "")
        + "\n".join(
            ("- " if b["kind"] == "bullets" else "") + item for item in b["items"]
        )
        for b in blocks
    )
    if len(result["reply"]) > 8192:
        raise ValueError("Chat presentation exceeds the response limit")
    return result


def report_presentation(report):
    shared = list(SHARED_GUIDANCE)
    gaps, limits = [], []
    for item in report.get("unresolved", []):
        if item not in LEGACY_GUIDANCE:
            gaps.append(clean_sentence(item))
    for item in report.get("warnings", []):
        if item not in LEGACY_GUIDANCE:
            limits.append(clean_sentence(item))
    if report.get("synthetic"):
        limits.insert(0, "Synthetic evidence is selected for this investigation.")
    return {
        "case_gaps": list(dict.fromkeys(gaps)),
        "run_limitations": list(dict.fromkeys(limits)),
        "shared_guidance": list(dict.fromkeys(shared)),
    }


def conversation_view(message, view):
    """An explicit case-wide question outranks incidental persisted drawer selection."""
    from dataclasses import replace

    text = message.lower()
    if any(
        term in text
        for term in (
            "this case",
            "the case",
            "that investigation",
            "this investigation",
            "whole case",
            "entire case",
        )
    ):
        return replace(
            view,
            evidence_id="",
            evidence_ids=(),
            connection=None,
            endpoint="",
            event_type="",
            signature="",
            severity=None,
        )
    return view


def chat_history_presentation(messages):
    """Adapt known historical templates for display without rewriting their content."""
    from bluecheese.application.view_context import DEFINITIONS

    shared_lines = {
        "Coverage: at most 20 records per query and 6 queries; selection filters apply within that sample. This is not an exhaustive review.",
        DEFINITIONS["alert"] + " " + DEFINITIONS["severity"],
        "Next: inspect the cited records and confirm authorization with the asset owner; endpoint process and identity logs are not connected. Record an analyst decision after review.",
    }
    displayed = []
    for message in messages:
        item = dict(message)
        if message["role"] == "assistant":
            try:
                result = json.loads(message["content"])
                if not isinstance(result, dict):
                    raise TypeError()
                reply = result.get("reply", "")
                if not result.get("blocks") and reply.startswith("Observed sample:"):
                    blocks = []
                    for line in reply.splitlines():
                        if line in shared_lines or line in LEGACY_GUIDANCE:
                            continue
                        if line.startswith("Unknowns: "):
                            gaps = [
                                part
                                for part in line.removeprefix("Unknowns: ").split("; ")
                                if part not in LEGACY_GUIDANCE
                            ]
                            if gaps:
                                blocks.append(block("Open questions", gaps))
                        else:
                            blocks.append(block("", [line], "paragraph"))
                    result["blocks"] = blocks
                with_blocks(result)
                item["presentation"] = {
                    "reply": result["reply"],
                    "blocks": result["blocks"],
                }
            except (ValueError, TypeError, KeyError, AttributeError):
                # Old free-text messages remain readable through the prose renderer.
                pass
        displayed.append(item)
    return displayed
