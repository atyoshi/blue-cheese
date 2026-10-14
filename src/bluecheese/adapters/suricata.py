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
    """Preserve alert/flow v1 interpretations; add bounded protocol context."""
    from dataclasses import asdict, replace
    from datetime import datetime

    if not isinstance(record, dict) or record.get("event_type") not in (
        "alert",
        "flow",
        "dns",
        "http",
        "tls",
    ):
        raise ValueError("Expected Suricata alert, flow, dns, http or tls")
    timestamp = record["timestamp"]
    if not isinstance(timestamp, str):
        raise TypeError("Timestamp must be a string")
    datetime.fromisoformat(timestamp)
    if record.get("alert") is not None and not isinstance(record["alert"], dict):
        raise ValueError("Alert must be an object")
    if record.get("flow") is not None and not isinstance(record["flow"], dict):
        raise ValueError("Flow must be an object")
    normalized = replace(
        normalize_suricata_alert(record),
        event_type=record["event_type"],
        alert_signature=record.get("alert", {}).get("signature", ""),
        bytes_toserver=record.get("flow", {}).get("bytes_toserver"),
        bytes_toclient=record.get("flow", {}).get("bytes_toclient"),
        flow_state=record.get("flow", {}).get("state"),
    )
    kind = record["event_type"]
    if kind in ("alert", "flow"):
        return normalized
    from bluecheese.domain.models import NormalizedNetworkContext

    section = record.get(kind, {})
    if not isinstance(section, dict):
        raise TypeError("Protocol context must be an object")
    fields = {
        "dns": ("type", "rrname", "rrtype", "rcode", "rdata"),
        "http": (
            "hostname",
            "url",
            "http_method",
            "status",
            "http_user_agent",
            "length",
        ),
        "tls": ("sni", "version", "subject", "issuerdn", "fingerprint"),
    }[kind]
    details = {}
    for key in fields:
        value = section.get(key)
        if isinstance(value, str):
            details[key] = value[:2048]
            if len(value) > 2048:
                details[key + "_truncated"] = True
        elif type(value) is int:
            details[key] = value
    # DNS v3 may place query names in a bounded queries array.
    if kind == "dns" and isinstance(section.get("queries"), list):
        details["queries"] = [
            {
                key: str(query[key])[:2048]
                for key in ("rrname", "rrtype")
                if key in query
            }
            for query in section["queries"][:20]
            if isinstance(query, dict)
        ]
        if len(section["queries"]) > 20:
            details["queries_truncated"] = True
    return NormalizedNetworkContext(**asdict(normalized), protocol_details=details)
