"""Browser-test process harness; the application has no test-specific routes."""
import os
import runpy
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "src"))
with TemporaryDirectory(prefix="bluecheese-browser-") as state:
    os.environ["BLUECHEESE_STATE"] = state
    os.environ.pop("BLUECHEESE_MODEL_ENDPOINT", None)
    sys.argv = ["server", "--port", "8579", "--no-browser"]
    runpy.run_module("bluecheese.interfaces.server", run_name="__main__")
