from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


os.chdir(_resolve_root())

from src.gui_app import main


if __name__ == "__main__":
    main()
