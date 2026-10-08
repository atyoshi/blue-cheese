"""Atomic, self-contained demo report exports and offline integrity checks."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

from bluecheese.adapters.suricata import normalize_suricata_event
from bluecheese.agents.reporting import json_report, markdown_report

FILES = (
    "report.json",
    "report.md",
    "run_manifest.json",
    "tool_trace.jsonl",
    "evidence.json",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reference_ids(report):
    ids = set(report["supporting_ids"] + report["contradicting_ids"])
    for claim in report["claims"]:
        ids.update(claim["citations"])
    for key in ("returned_ids", "counterevidence_ids"):
        ids.update(report["falsifier"].get(key, []))
    for candidate in report.get("triage", {}).get("candidates", []):
        ids.update(candidate["seed_ids"])
    for correlation in report.get("correlation", []):
        ids.update(correlation["member_ids"])
    return ids


def export_bundle(runtime, report, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for event_id in sorted(reference_ids(report)):
        row = runtime.command(
            "get_event",
            report["scenario"],
            report["variant"],
            report["snapshot"],
            event_id,
            snapshot_id=report.get("snapshot_id"),
        )
        if row is None:
            raise ValueError(f"Citation cannot be exported: {event_id}")
        rows.append(row)
    scope = {key: report[key] for key in ("scenario", "variant", "snapshot")}
    manifest = {
        "version": 1,
        "scope": scope,
        "provider": report["provider"],
        "synthetic": report.get("synthetic", True),
        "evidence_ids": [row["id"] for row in rows],
    }
    if report.get("snapshot_id"):
        manifest["snapshot_manifest"] = runtime.command(
            "snapshot_manifest", report["snapshot_id"]
        )
    temporary = Path(tempfile.mkdtemp(prefix=".bundle-", dir=destination.parent))
    try:
        contents = {
            "report.json": json_report(report) + "\n",
            "report.md": markdown_report(report),
            "run_manifest.json": json.dumps(manifest, indent=2) + "\n",
            "tool_trace.jsonl": "".join(
                json.dumps(call) + "\n" for call in report["tool_activity"]
            ),
            "evidence.json": json.dumps(rows, indent=2) + "\n",
        }
        for name, content in contents.items():
            (temporary / name).write_text(content, encoding="utf-8")
        checksums = {name: digest((temporary / name).read_bytes()) for name in FILES}
        (temporary / "checksums.json").write_text(
            json.dumps(checksums, indent=2) + "\n", encoding="utf-8"
        )
        verify_bundle(temporary)
        # Never overwrite a historical bundle or partially replace its contents.
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def verify_bundle(directory):
    directory = Path(directory)
    expected = set(FILES) | {"checksums.json"}
    if {p.name for p in directory.iterdir()} != expected:
        raise ValueError("Unexpected or missing bundle files")
    if any((directory / name).is_symlink() for name in expected):
        raise ValueError("Bundle symlinks are not allowed")
    if (directory / "checksums.json").stat().st_size > 16384:
        raise ValueError("Checksum manifest exceeds size limit")
    checksums = json.loads((directory / "checksums.json").read_text(encoding="utf-8"))
    if set(checksums) != set(FILES):
        raise ValueError("Invalid checksum manifest")
    for name in FILES:
        path = directory / name
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Bundle member exceeds 16 MiB")
        if digest(path.read_bytes()) != checksums[name]:
            raise ValueError(f"Checksum mismatch: {name}")
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    rows = json.loads((directory / "evidence.json").read_text(encoding="utf-8"))
    trace = [
        json.loads(line)
        for line in (directory / "tool_trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    scope = manifest["scope"]
    if manifest["version"] != 1 or scope != {
        key: report[key] for key in ("scenario", "variant", "snapshot")
    }:
        raise ValueError("Report scope differs from manifest")
    if trace != report["tool_activity"]:
        raise ValueError("Tool trace differs from report")
    visible = {event_id for call in trace for event_id in call["returned_ids"]}
    ids = reference_ids(report)
    if not ids <= visible:
        raise ValueError("Citation was not retrieved")
    if (
        len(rows) != len(ids)
        or {row["id"] for row in rows} != ids
        or set(manifest["evidence_ids"]) != ids
    ):
        raise ValueError("Citation evidence is missing or duplicated")
    snapshot_manifest = manifest.get("snapshot_manifest")
    if snapshot_manifest:
        members = snapshot_manifest["members"]
        if (
            len(members) > 10000
            or len({member[0] for member in members}) != len(members)
            or members != sorted(members)
            or digest(json.dumps(members, separators=(",", ":")).encode())
            != snapshot_manifest["digest"]
            or snapshot_manifest["digest"] != report.get("snapshot_digest")
            or any(
                snapshot_manifest[key] != report.get(key)
                for key in (
                    "snapshot_id",
                    "case_id",
                    "case_revision",
                    "scenario",
                    "variant",
                    "snapshot",
                )
            )
        ):
            raise ValueError("Snapshot manifest mismatch")
        interpretation_hashes = dict(members)
        if not ids <= interpretation_hashes.keys():
            raise ValueError("Citation outside materialized snapshot")
    for row in rows:
        if (
            snapshot_manifest
            and digest(
                json.dumps(
                    row["normalized"], sort_keys=True, separators=(",", ":")
                ).encode()
            )
            != interpretation_hashes[row["id"]]
        ):
            raise ValueError("Cited interpretation differs from snapshot")
        identity = digest(
            f"{scope['scenario']}\0{scope['variant']}\0{row['source']}\0{row['position']}\0".encode()
            + row["raw"].encode("utf-8")
        )[:24]
        if identity != row["id"] or not 0 < row["seq"] <= scope["snapshot"]:
            raise ValueError("Evidence identity or snapshot mismatch")
        if json.loads(row["raw"]) != row["parsed"]:
            raise ValueError("Parsed evidence differs from raw text")
        if asdict(normalize_suricata_event(row["parsed"])) != row["normalized"]:
            raise ValueError("Normalized evidence differs from parser output")
    return {"valid": True, "citations": len(ids), "scope": scope}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle")
    args = parser.parse_args()
    print(json.dumps(verify_bundle(args.bundle), indent=2))


if __name__ == "__main__":
    main()
