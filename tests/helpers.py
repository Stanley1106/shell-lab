"""Test-only helpers."""

import atexit
import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SECRET_HEX = "ab" * 32


def scratch_dir():
    """A temporary directory removed when the test run ends (one lab build is about 30 MB)."""
    path = Path(tempfile.mkdtemp(prefix="labctl-test-"))
    atexit.register(shutil.rmtree, path, True)
    return path
