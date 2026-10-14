"""Comparison artifacts must preserve scoped membership and reproducible settings."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bluecheese.application.compare_investigations import run_comparison
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.report_bundle import verify_bundle


def test_host_comparison_requires_seed_before_creating_output(tmp_path):
    destination = tmp_path / "comparison"
    with pytest.raises(ValueError, match="explicit seed"):
        run_comparison([], destination, investigation_scope="host")
    assert not destination.exists()
    with pytest.raises(ValueError, match="scope"):
        run_comparison([], destination, investigation_scope="unknown")
    assert not destination.exists()


def test_comparison_scope_changes_membership_and_exports_verified_bundles(tmp_path):
    seed_record = {
        "timestamp": "2026-01-01T12:00:00+00:00",
        "event_type": "alert",
        "src_ip": "10.0.0.5",
        "dest_ip": "192.0.2.1",
        "src_port": 50000,
        "dest_port": 80,
        "proto": "TCP",
        "alert": {"signature": "Review traffic", "severity": 2},
    }
    records = [
        seed_record,
        {
            **seed_record,
            "event_type": "http",
            "dest_ip": "192.0.2.2",
            "http": {"http_method": "GET", "url": "/second-destination", "status": 200},
        },
        {
            **seed_record,
            "event_type": "http",
            "dest_ip": "192.0.2.3",
            "timestamp": "2026-01-01T12:06:00+00:00",
            "http": {"http_method": "GET", "url": "/outside-window", "status": 200},
        },
    ]
    eve = tmp_path / "observations.jsonl"
    eve.write_text("".join(json.dumps(record) + "\n" for record in records))
    original = eve.read_bytes()
    runtime = DemoRuntime(tmp_path / "seed-state", load_fixtures=False)
    try:
        runtime.command("import_file", eve, "live", "external")
        seed = runtime.command(
            "query", "live", "external", runtime.command("snapshot")
        )[0]["id"]
    finally:
        runtime.close()
    artifacts = {}
    for scope in ("connection", "host"):
        destination = tmp_path / scope
        result = run_comparison(
            [eve],
            destination,
            repetitions=1,
            seed_event_id=seed,
            investigation_scope=scope,
            max_calls=12,
            max_seconds=1800,
        )
        row = result["results"][0]
        assert row["status"] == "COMPLETED"
        assert row["investigation_scope"] == scope and row["seed_event_id"] == seed
        assert row["effective_settings"]["max_seconds"] == 1800
        assert row["application_revision"]["commit"]
        assert verify_bundle(destination / row["bundle"])["valid"]
        manifest = json.loads(
            (destination / row["bundle"] / "run_manifest.json").read_text()
        )
        artifacts[scope] = manifest["snapshot_manifest"]
    assert artifacts["connection"]["digest"] != artifacts["host"]["digest"]
    assert len(artifacts["connection"]["members"]) == 1
    assert len(artifacts["host"]["members"]) == 2
    assert eve.read_bytes() == original


def test_default_connection_and_failed_seed_have_reviewable_artifacts(tmp_path):
    eve = Path(__file__).parent / "fixtures/sample_eve.json"
    result = run_comparison([eve], tmp_path / "default", repetitions=1)
    assert result["settings"]["investigation_scope"] == "connection"
    assert result["results"][0]["bundle_verification"]["valid"]
    failed = run_comparison(
        [eve],
        tmp_path / "failed",
        repetitions=1,
        investigation_scope="host",
        seed_event_id="missing-seed",
    )
    row = failed["results"][0]
    assert row["status"] == "FAILED" and row["run_id"] is None
    assert (tmp_path / "failed" / row["diagnostics"]).is_file()


def test_comparison_cli_exposes_scope():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bluecheese.application.compare_investigations",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--scope {connection,host}" in result.stdout
