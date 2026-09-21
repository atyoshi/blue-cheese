from pathlib import Path

from bluecheese.adapters.suricata import (
    normalize_suricata_alert,
    read_suricata_alerts,
)


FIXTURE = Path(__file__).parent / "fixtures" / "sample_eve.json"


def test_normalize_suricata_alert():
    record = {
        "timestamp": "2025-01-22T19:59:46.284Z",
        "event_type": "alert",
        "src_ip": "10.1.17.215",
        "src_port": 51724,
        "dest_ip": "185.188.32.5",
        "dest_port": 443,
        "proto": "TCP",
        "alert": {
            "signature": "ET INFO TeamViewer Dyngate User-Agent",
            "severity": 2,
        },
    }

    result = normalize_suricata_alert(record)

    assert result.sensor == "suricata"
    assert result.src_ip == "10.1.17.215"
    assert result.dest_port == 443
    assert result.alert_signature == (
        "ET INFO TeamViewer Dyngate User-Agent"
    )


def test_reader_returns_only_alerts():
    alerts = list(read_suricata_alerts(FIXTURE))

    assert len(alerts) == 1
    assert alerts[0].event_type == "alert"
