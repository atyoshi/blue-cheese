import pytest

from bluecheese.application.backup import backup, restore, verify_backup
from bluecheese.application.demo_runtime import DemoRuntime


def test_backup_restore_preserves_evidence_and_history(tmp_path):
    state = tmp_path / "state"
    runtime = DemoRuntime(state)
    report = runtime.run("suspicious", "poisoned")
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            backup(state, tmp_path / "busy")
    finally:
        runtime.close()
    destination = backup(state, tmp_path / "backup")
    assert verify_backup(destination)["evidence_count"] == 63
    with pytest.raises(FileExistsError):
        backup(state, destination)
    with pytest.raises(FileExistsError):
        restore(destination, state)
    restored = restore(destination, tmp_path / "restored")
    runtime = DemoRuntime(restored)
    try:
        saved = runtime.command("get_run", "suspicious", "poisoned", report["run_id"])
        assert saved["report"] == report
        assert saved["tool_activity"] == report["tool_activity"]
        for cited in report["supporting_ids"] + report["contradicting_ids"]:
            assert runtime.command(
                "get_event",
                "suspicious",
                "poisoned",
                report["snapshot"],
                cited,
                snapshot_id=report["snapshot_id"],
            )
    finally:
        runtime.close()
    assert not list(tmp_path.glob(".backup-*"))


def test_backup_tamper_rejected_before_restore(tmp_path):
    runtime = DemoRuntime(tmp_path / "state")
    runtime.close()
    destination = backup(tmp_path / "state", tmp_path / "backup")
    with (destination / "evidence.duckdb").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="size mismatch"):
        restore(destination, tmp_path / "restore")
    assert not (tmp_path / "restore").exists()
