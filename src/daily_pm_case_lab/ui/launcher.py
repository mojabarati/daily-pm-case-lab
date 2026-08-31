from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Launch the packaged Streamlit entrypoint with any supplied server options."""
    app_path = Path(__file__).with_name("app.py")
    completed = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]],
        check=False,
    )
    return completed.returncode
