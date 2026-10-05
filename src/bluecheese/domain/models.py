from dataclasses import dataclass


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
class TriageResult:
    priority: str
    disposition: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
