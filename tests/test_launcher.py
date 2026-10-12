import os
import subprocess
from pathlib import Path


def test_launcher_from_path_symlink(tmp_path):
    launcher = Path(__file__).resolve().parents[1] / "bluecheese"
    link = tmp_path / "bluecheese"
    link.symlink_to(launcher)
    environment = {**os.environ, "PYTHONPATH": ""}
    result = subprocess.run(
        [str(link), "--help"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "import-pcap" in result.stdout


def test_short_gui_commands_use_operational_state_and_respect_override(
    monkeypatch, tmp_path
):
    from types import SimpleNamespace

    from bluecheese.cli import main

    calls = []
    monkeypatch.setattr(
        "bluecheese.cli.subprocess.run",
        lambda command, **kwargs: (
            calls.append((command, kwargs)) or SimpleNamespace(returncode=0)
        ),
    )
    monkeypatch.chdir(tmp_path)
    for arguments, expected in (
        ([], tmp_path / "bluecheese-operations"),
        (["gui"], tmp_path / "bluecheese-operations"),
        (["--data-dir", "chosen", "gui", "--port", "8502"], tmp_path / "chosen"),
    ):
        monkeypatch.setattr("sys.argv", ["bluecheese", *arguments])
        main()
        command, kwargs = calls[-1]
        assert command[1:4] == ["-m", "streamlit", "run"]
        assert command[4].endswith("/interfaces/console.py")
        assert kwargs["env"]["BLUECHEESE_STATE"] == str(expected)
        # The installed command must retain its theme outside the repository.
        assert "--theme.base=dark" in command
        assert "--theme.primaryColor=#38bdb4" in command
    assert not any(arg.startswith("--server.port=") for arg in calls[0][0])
    assert not any(arg.startswith("--server.port=") for arg in calls[1][0])
    assert "--server.port=8502" in calls[-1][0]
