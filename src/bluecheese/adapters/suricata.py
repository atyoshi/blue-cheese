import json
from bluecheese.domain.models import NormalizedAlert
from pathlib import Path

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
