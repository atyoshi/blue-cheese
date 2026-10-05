import json
from pathlib import Path

from bluecheese.domain.models import NormalizedAlert


def normalize_suricata_alert(record: dict) -> NormalizedAlert:
    alert = record.get("alert", {})

    return NormalizedAlert(
        timestamp=record["timestamp"],
        sensor="suricata",
        event_type="alert",
        src_ip=record.get("src_ip"),
        src_port=record.get("src_port"),
        dest_ip=record.get("dest_ip"),
        dest_port=record.get("dest_port"),
        protocol=record.get("proto"),
        alert_signature=alert.get("signature", "Unknown alert"),
        severity=alert.get("severity"),
        signature_id=alert.get("signature_id"),
        community_id=record.get("community_id"),
        flow_id=str(record["flow_id"]) if record.get("flow_id") is not None else None,
    )


def read_suricata_alerts(path: str):
    with Path(path).open(encoding="utf-8") as log:
        for line_number, line in enumerate(log, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}"
                ) from error

            if record.get("event_type") == "alert":
                yield normalize_suricata_alert(record)


if __name__ == "__main__":
    for alert in read_suricata_alerts("data/suricata/eve.json"):
        print(alert)


def normalize_suricata_event(record: dict) -> NormalizedAlert:
    """Reuse the canonical alert fields for alert/flow evidence."""
    from dataclasses import replace
    from datetime import datetime

    if not isinstance(record, dict) or record.get("event_type") not in (
        "alert",
        "flow",
    ):
        raise ValueError("Expected Suricata alert or flow")
    timestamp = record["timestamp"]
    if not isinstance(timestamp, str):
        raise TypeError("Timestamp must be a string")
    datetime.fromisoformat(timestamp)
    if record.get("alert") is not None and not isinstance(record["alert"], dict):
        raise ValueError("Alert must be an object")
    if record.get("flow") is not None and not isinstance(record["flow"], dict):
        raise ValueError("Flow must be an object")
    return replace(
        normalize_suricata_alert(record),
        event_type=record["event_type"],
        alert_signature=record.get("alert", {}).get("signature", ""),
        bytes_toserver=record.get("flow", {}).get("bytes_toserver"),
        bytes_toclient=record.get("flow", {}).get("bytes_toclient"),
        flow_state=record.get("flow", {}).get("state"),
    )
