"""Launcher for the control vs treatment comparison."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from h3_abt.experiment_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
