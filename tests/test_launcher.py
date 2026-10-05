import os
import subprocess
from pathlib import Path


def test_launcher_from_path_symlink(tmp_path):
    launcher = Path(__file__).resolve().parents[1] / 'bluecheese'
    link = tmp_path / 'bluecheese'
    link.symlink_to(launcher)
    environment = {**os.environ, 'PYTHONPATH': ''}
    result = subprocess.run([str(link), '--help'], cwd=tmp_path,
                            env=environment, capture_output=True, text=True,
                            timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    assert 'import-pcap' in result.stdout
