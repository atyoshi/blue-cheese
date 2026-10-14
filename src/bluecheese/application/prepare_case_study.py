"""Convert an existing capture offline and record reproducible sensor provenance."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path


def file_hash(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def prepare_capture(
    pcap,
    destination,
    config,
    rules,
    *,
    source_url=None,
    suricata="suricata",
    timeout=600,
):
    pcap, config, rules = (
        Path(path).resolve(strict=True) for path in (pcap, config, rules)
    )
    inputs = {
        name: {"sha256": file_hash(path), "bytes": path.stat().st_size}
        for name, path in (
            ("capture", pcap),
            ("configuration", config),
            ("rules", rules),
        )
    }
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    sensor = destination / "sensor"
    sensor.mkdir()
    command = [
        suricata,
        "-r",
        str(pcap),
        "-c",
        str(config),
        "-S",
        str(rules),
        "-l",
        str(sensor),
        "--runmode",
        "single",
    ]
    manifest = {
        "version": 1,
        "status": "PROCESSING",
        "inputs": inputs,
        "sensor_version": None,
        "source_url": source_url,
        "attribution": "Requires independent source/content review; source URL is not a capture checksum.",
        "mode": "offline PCAP processing; no packet transmission",
        "redistribution": "Capture is not copied or bundled. Verify source terms before redistribution.",
    }
    try:
        manifest["sensor_version"] = subprocess.run(
            [suricata, "-V"], capture_output=True, text=True, check=True, timeout=20
        ).stdout.strip()
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
        (destination / "sensor-output.txt").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("Suricata processing failed; inspect sensor-output.txt")
        counts = Counter()
        first = last = None
        with (sensor / "eve.json").open() as source:
            for line in source:
                record = json.loads(line)
                counts[record.get("event_type", "unknown")] += 1
                timestamp = record.get("timestamp")
                if timestamp and record.get("event_type") != "stats":
                    parsed = datetime.fromisoformat(timestamp)
                    first = min(first, parsed) if first else parsed
                    last = max(last, parsed) if last else parsed
        for name, path in (
            ("capture", pcap),
            ("configuration", config),
            ("rules", rules),
        ):
            if file_hash(path) != inputs[name]["sha256"]:
                raise RuntimeError("Capture or sensor inputs changed during processing")
        manifest.update(
            status="PROCESSED",
            eve_sha256=file_hash(sensor / "eve.json"),
            event_counts=dict(counts),
            first_timestamp=first.isoformat() if first else None,
            last_timestamp=last.isoformat() if last else None,
        )
    except Exception:
        manifest["status"] = "FAILED"
        raise
    finally:
        (destination / "capture-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcap", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--rules",
        type=Path,
        required=True,
        help="Explicit rule file; recorded by hash and passed with -S",
    )
    parser.add_argument("--source-url")
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_capture(
                args.pcap, args.out, args.config, args.rules, source_url=args.source_url
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
