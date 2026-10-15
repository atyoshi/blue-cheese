"""Versioned analyst findings; structural checks do not establish semantic truth."""

import json
from copy import deepcopy

from jsonschema import validate

from bluecheese.domain.models import model_observation

ACTIVITY = [
    "MALICIOUS_ACTIVITY",
    "SUSPICIOUS_ACTIVITY",
    "BENIGN_EXPLANATION",
    "INSUFFICIENT_EVIDENCE",
]


class SourceFactConflict(ValueError):
    def __init__(self, evidence_id, field, expected):
        self.evidence_id, self.field, self.expected = evidence_id, field, expected
        super().__init__("Source fact conflicts with retrieved observation: " + field)


DETAILS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "activity_assessment": {"type": "string", "enum": ACTIVITY},
        "observed_impact": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "NETWORK_ACTIVITY_OBSERVED",
                        "COMPROMISE_SUPPORTED",
                        "UNCONFIRMED",
                        "UNAVAILABLE",
                    ],
                },
                "description": {"type": "string", "maxLength": 2048},
                "citations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 20,
                },
            },
            "required": ["status", "description", "citations"],
        },
        "evidence_completeness": {"type": "string", "maxLength": 2048},
        "recommended_checks": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    key: {"type": "string", "minLength": 1, "maxLength": 2048}
                    for key in ("action", "purpose", "required_source")
                },
                "required": ["action", "purpose", "required_source"],
            },
        },
    },
    "required": [
        "activity_assessment",
        "observed_impact",
        "evidence_completeness",
        "recommended_checks",
    ],
}


def extended_schema(base):
    # JSON round-trip deliberately breaks shared IDS/TEXT object aliases in the legacy schema.
    schema = json.loads(json.dumps(base))
    # Activity is the model's single decision; legacy verdict is a software projection.
    schema["properties"].pop("verdict")
    schema["required"].remove("verdict")
    schema["properties"]["findings"] = deepcopy(DETAILS_SCHEMA)
    schema["required"].append("findings")
    details = schema["properties"]["findings"]["properties"]
    details["evidence_completeness"]["maxLength"] = 256
    details["observed_impact"]["properties"]["description"]["maxLength"] = 256
    checks = details["recommended_checks"]
    checks["maxItems"] = 2
    for field in checks["items"]["properties"].values():
        field["maxLength"] = 192
    for key in ("hypothesis", "disconfirmation_test"):
        schema["properties"][key]["maxLength"] = 256
    schema["properties"]["unresolved"].update(
        maxItems=3, items={"type": "string", "maxLength": 128}
    )
    for key in ("supporting_ids", "contradicting_ids"):
        schema["properties"][key]["maxItems"] = 6
    schema["properties"]["claims"]["maxItems"] = 2
    claim = schema["properties"]["claims"]["items"]
    claim["properties"]["text"]["maxLength"] = 256
    claim["properties"]["citations"].update(minItems=1, maxItems=6)
    claim["properties"].update(
        proposition_type={"type": "string", "enum": ["observation", "inference"]},
        limitations={
            "type": "array",
            "maxItems": 1,
            "items": {"type": "string", "maxLength": 128},
        },
        contradicting_ids={
            "type": "array",
            "maxItems": 6,
            "items": {"type": "string"},
        },
    )
    # Discriminated branches prevent numeric facts being emitted as quoted strings.
    numeric_fields = ["src_port", "dest_port", "status", "response_length_bytes"]
    text_fields = [
        "timestamp",
        "timestamp_utc",
        "src_ip",
        "dest_ip",
        "event_type",
        "protocol",
        "http_method",
        "url",
    ]
    claim["properties"]["facts"] = {
        "type": "array",
        "maxItems": 2,
        "items": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "evidence_id": {"type": "string", "maxLength": 256},
                        "field": {"type": "string", "enum": fields},
                        "value": value_schema,
                    },
                    "required": ["evidence_id", "field", "value"],
                }
                for fields, value_schema in (
                    (numeric_fields, {"type": "integer"}),
                    (text_fields, {"type": "string", "maxLength": 2048}),
                )
            ]
        },
    }
    claim["required"] += ["proposition_type", "limitations", "contradicting_ids"]
    return schema


def validate_model_report(report, base_schema, model_schema):
    if "findings" not in report:
        validate(report, base_schema)
        return
    supplied = report.pop("verdict", None)
    if supplied is not None and supplied not in (
        "UNCERTAIN",
        "SUSPICIOUS",
        "BENIGN_CONFOUNDER",
        "BENIGN",
        "MALICIOUS",
    ):
        raise ValueError("Invalid legacy verdict")
    validate(report, model_schema)
    report["verdict"] = {
        "MALICIOUS_ACTIVITY": "MALICIOUS",
        "SUSPICIOUS_ACTIVITY": "SUSPICIOUS",
        "BENIGN_EXPLANATION": "BENIGN_CONFOUNDER",
        "INSUFFICIENT_EVIDENCE": "UNCERTAIN",
    }[report["findings"]["activity_assessment"]]
    report["assessment_projection"] = {
        "source": "findings.activity_assessment",
        "supplied_legacy_verdict": supplied,
    }


def validate_facts(report, tools):
    """Check explicit source assertions. This does not prove arbitrary prose or inferences."""
    for claim in report.get("claims", []):
        for fact in claim.get("facts", []):
            event_id = fact["evidence_id"]
            tools.validate([event_id])
            if event_id not in claim["citations"]:
                raise ValueError("A source fact must cite its own observation")
            field = fact["field"]
            actual = observation_fact(
                model_observation(tools.retrieved[event_id]), field
            )
            if (
                actual is None
                or type(actual) is not type(fact["value"])
                or actual != fact["value"]
            ):
                raise SourceFactConflict(event_id, field, actual)


def observation_fact(observation, field):
    """One projection for catalog values and strict source-fact validation."""
    normalized = observation["normalized"]
    return (
        normalized[field]
        if field in normalized
        else normalized.get("protocol_details", {}).get(field)
    )


def validate_findings(report, tools):
    validate_facts(report, tools)
    details = report.get("findings")
    if details is None:
        return
    validate(details, DETAILS_SCHEMA)
    impact = details["observed_impact"]
    if (
        impact["status"] in ("NETWORK_ACTIVITY_OBSERVED", "COMPROMISE_SUPPORTED")
        and not impact["citations"]
    ):
        raise ValueError("Observed impact requires retrieved citations")
    tools.validate(impact["citations"])
    for claim in report["claims"]:
        tools.validate(claim.get("contradicting_ids", []))
    expected = {
        "MALICIOUS_ACTIVITY": "MALICIOUS",
        "SUSPICIOUS_ACTIVITY": "SUSPICIOUS",
        "INSUFFICIENT_EVIDENCE": "UNCERTAIN",
    }.get(details["activity_assessment"])
    if expected and report["verdict"] != expected:
        raise ValueError("Activity assessment conflicts with legacy verdict")
    if details["activity_assessment"] == "BENIGN_EXPLANATION" and report[
        "verdict"
    ] not in ("BENIGN", "BENIGN_CONFOUNDER"):
        raise ValueError("Benign activity assessment conflicts with verdict")
    if (
        details["activity_assessment"] != "INSUFFICIENT_EVIDENCE"
        and not report["claims"]
    ):
        raise ValueError("An activity assessment requires cited findings")


def findings_view(report):
    """Read old reports without promoting legacy verdicts to new conclusions."""
    return report.get("findings") or {
        "activity_assessment": "NOT_RECORDED",
        "observed_impact": {
            "status": "UNAVAILABLE",
            "description": "Impact assessment was not recorded.",
            "citations": [],
        },
        "evidence_completeness": "Structured evidence completeness was not recorded; review unresolved questions and the retrieval audit.",
        "recommended_checks": [],
    }


def upstream_advice_context(advice):
    """Expose audit scope without leaking evaluator scenario or variant names."""
    if not advice:
        return None
    return {
        **advice,
        "scope": {key: advice["scope"].get(key) for key in ("snapshot", "snapshot_id")},
    }


def protocol_observations(rows):
    """Source-derived HTTP facts, independent of model prose or classification."""
    result = []
    for row in rows:
        n = model_observation(row)["normalized"]
        if n.get("event_type") != "http":
            continue
        details = n.get("protocol_details", {})
        result.append(
            {
                "evidence_id": row["id"],
                "timestamp": n.get("timestamp"),
                "source": n.get("src_ip"),
                "destination": n.get("dest_ip"),
                "destination_port": n.get("dest_port"),
                "method": details.get("http_method"),
                "path": details.get("url"),
                "path_truncated": details.get("url_truncated", False),
                "response_status": details.get("status"),
                "response_length_bytes": details.get("response_length_bytes"),
            }
        )
        if len(result) == 20:
            break
    return result


def rule_findings(report, tools):
    """Describe the existing offline rule policy without implying model judgment."""
    seed = tools.retrieved.get(getattr(tools, "selected_seed_id", None), {})
    observation = seed.get("normalized", {})
    pair = f"{observation.get('src_ip', 'unknown source')} → {observation.get('dest_ip', 'unknown destination')}"
    checks = []
    if seed:
        checks.append(
            {
                "action": "Confirm the purpose of " + pair + ".",
                "purpose": "Resolve whether the flagged connection was expected at "
                + observation.get("timestamp", "the observed time")
                + ".",
                "required_source": "The endpoint owner's task or change record for this time.",
            }
        )
    related = [
        r
        for r in tools.retrieved.values()
        if r["id"] in getattr(tools, "correlated_ids", set())
        and r["normalized"]["event_type"] == "flow"
    ]
    if seed and not related:
        checks.insert(
            0,
            {
                "action": "Obtain the missing flow record for " + pair + ".",
                "purpose": "No matching flow was delivered, so the connection outcome could not be checked.",
                "required_source": "Sensor flow telemetry for the cited connection and time.",
            },
        )
    elif report["contradicting_ids"]:
        checks.insert(
            0,
            {
                "action": "Verify the cited zero-byte closed flow against the original sensor record.",
                "purpose": "Check whether the flagged connection failed; a failed connection does not establish benign intent.",
                "required_source": "Original records for the cited flow IDs.",
            },
        )
    elif seed and report.get("verdict") == "SUSPICIOUS":
        checks.insert(
            0,
            {
                "action": "Identify the process responsible for " + pair + ".",
                "purpose": "The cited active flow warrants checking the originating process and endpoint outcome.",
                "required_source": "Endpoint process telemetry for the source IP and observed time.",
            },
        )
    return {
        "activity_assessment": {
            "SUSPICIOUS": "SUSPICIOUS_ACTIVITY",
            "BENIGN_CONFOUNDER": "BENIGN_EXPLANATION",
            "BENIGN": "BENIGN_EXPLANATION",
            "MALICIOUS": "MALICIOUS_ACTIVITY",
        }.get(report["verdict"], "INSUFFICIENT_EVIDENCE"),
        "observed_impact": {
            "status": "UNCONFIRMED" if seed else "UNAVAILABLE",
            "description": f"{len(related)} matching flow {'record was' if len(related) == 1 else 'records were'} delivered for {pair}; endpoint impact remains unconfirmed."
            if seed
            else "No eligible alert was available to assess.",
            "citations": [],
        },
        "evidence_completeness": "Bounded alert/flow rule review; protocol context is not assessed by this policy. "
        + " ".join(report["unresolved"]),
        "recommended_checks": checks[:2],
    }
