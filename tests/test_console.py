import json
from pathlib import Path

import pytest

from bluecheese.application.demo_runtime import DemoRuntime

FIXTURE = Path(__file__).parent / "fixtures/sample_eve.json"


def test_operational_runtime_has_no_synthetic_evidence_and_search_is_scoped(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        assert runtime.command("snapshot") == 0
        with pytest.raises(ValueError, match="disabled"):
            runtime.start(replay=True)
        runtime.start(path=FIXTURE, replay=False, interval=3600)
        runtime.stop()
        snapshot = runtime.command("snapshot")
        result = runtime.command(
            "browse_telemetry",
            "live",
            "external",
            snapshot,
            ip="10.1.17.215",
            severity=2,
            signature="teamviewer",
        )
        assert result["total"] == 1
        assert result["rows"][0]["alert_signature"].startswith("ET INFO")
        assert (
            runtime.command(
                "browse_telemetry",
                "live",
                "external",
                snapshot,
                signature="' OR TRUE --",
            )["total"]
            == 0
        )
        assert (
            runtime.command("browse_telemetry", "live", "replay", snapshot)["total"]
            == 0
        )
        report = runtime.begin_run("live", "external").result(10)
        assert not report["synthetic"]
    finally:
        runtime.close()


def test_console_pagination_snapshot_and_quarantine(tmp_path):
    runtime = DemoRuntime(tmp_path / "state", load_fixtures=False)
    try:
        row = json.loads(FIXTURE.read_text().splitlines()[0])
        source = tmp_path / "eve.json"
        source.write_text((json.dumps(row) + "\n") * 55 + "invalid\n")
        runtime.start(path=source, replay=False, interval=3600)
        runtime.stop()
        snapshot = runtime.command("snapshot")
        page = runtime.command("browse_telemetry", "live", "external", snapshot, page=2)
        assert page["total"] == 55
        assert len(page["rows"]) == 5
        assert runtime.command("quarantine_records", "live", "external")
        with source.open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        runtime.poll_once()
        assert (
            runtime.command("browse_telemetry", "live", "external", snapshot)["total"]
            == 55
        )
        assert (
            runtime.command(
                "browse_telemetry", "live", "external", runtime.command("snapshot")
            )["total"]
            == 56
        )
    finally:
        runtime.close()
