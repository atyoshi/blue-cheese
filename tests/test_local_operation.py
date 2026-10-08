import json
import subprocess
import sys

import pytest

from bluecheese.adapters.duckdb_store import EvidenceStore
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.report_bundle import export_bundle, verify_bundle


def test_state_lock_alias_process_and_release(tmp_path):
    state = tmp_path / "state"
    store = EvidenceStore(state / "evidence.duckdb")
    alias = tmp_path / "alias"
    alias.symlink_to(state, target_is_directory=True)
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            EvidenceStore(alias / "other.duckdb")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from bluecheese.application.state_lock import StateLock; "
                    f"StateLock({str(state)!r})"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "already in use" in result.stderr
    finally:
        store.close()
    reopened = EvidenceStore(alias / "evidence.duckdb")
    reopened.close()


def test_bundle_offline_verification_and_tampering(tmp_path):
    runtime = DemoRuntime(tmp_path / "state")
    try:
        report = runtime.run("suspicious", "poisoned")
        bundle = export_bundle(runtime, report, tmp_path / "bundle")
        with pytest.raises(OSError):
            export_bundle(runtime, report, bundle)
    finally:
        runtime.close()
    assert verify_bundle(bundle)["citations"] > 0
    evidence = bundle / "evidence.json"
    rows = json.loads(evidence.read_text())
    rows[0]["raw"] += " "
    evidence.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify_bundle(bundle)
    # Recomputing a file checksum still cannot bypass occurrence identity checks.
    from bluecheese.application.report_bundle import digest

    checksum_path = bundle / "checksums.json"
    checksums = json.loads(checksum_path.read_text())
    checksums["evidence.json"] = digest(evidence.read_bytes())
    checksum_path.write_text(json.dumps(checksums))
    with pytest.raises(ValueError, match="identity"):
        verify_bundle(bundle)
    assert not list(tmp_path.glob(".bundle-*"))


def test_bundle_rejects_unseen_citation_before_publication(tmp_path):
    runtime = DemoRuntime(tmp_path / "state")
    try:
        report = runtime.run("suspicious", "clean")
        unseen = runtime.command("query", "suspicious", "clean", report["snapshot"])[
            -1
        ]["id"]
        for call in report["tool_activity"]:
            call["returned_ids"] = [i for i in call["returned_ids"] if i != unseen]
        report["claims"].append({"text": "Unseen", "citations": [unseen]})
        with pytest.raises(ValueError, match="not retrieved"):
            export_bundle(runtime, report, tmp_path / "bundle")
        assert not (tmp_path / "bundle").exists()
        assert not list(tmp_path.glob(".bundle-*"))
    finally:
        runtime.close()
