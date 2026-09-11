"""Launcher for the unstaked control/baseline simulation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from h3_abt.baseline import main

if __name__ == "__main__":
    raise SystemExit(main())
