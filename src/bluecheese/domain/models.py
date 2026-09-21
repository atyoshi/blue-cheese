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
    
@dataclass(frozen=True)
class TriageResult:
    priority: str
    disposition: str
    rationale: str
