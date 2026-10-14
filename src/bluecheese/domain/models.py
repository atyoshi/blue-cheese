from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime


def model_observation(row):
    """Clarify protocol semantics without changing immutable stored interpretations."""
    normalized = deepcopy(row["normalized"])
    try:
        timestamp = datetime.fromisoformat(normalized["timestamp"])
        if timestamp.tzinfo is not None:
            normalized["timestamp_utc"] = timestamp.astimezone(UTC).isoformat()
    except (KeyError, TypeError, ValueError):
        pass
    details = normalized.get("protocol_details", {})
    if normalized.get("event_type") == "http" and "length" in details:
        details["response_length_bytes"] = details.pop("length")
    return {"id": row["id"], "normalized": normalized}


@dataclass(frozen=True)
class NormalizedAlert:
    timestamp: str
    sensor: str
    event_type: str
    src_ip: str | None
    src_port: int | None
    dest_ip: str | None
    dest_port: int | None
    protocol: str | None
    alert_signature: str
    severity: int | None
    signature_id: int | None = None
    community_id: str | None = None
    flow_id: str | None = None
    bytes_toserver: int | None = None
    bytes_toclient: int | None = None
    flow_state: str | None = None


@dataclass(frozen=True)
class NormalizedNetworkContext(NormalizedAlert):
    protocol_details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TriageResult:
    priority: str
    disposition: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
