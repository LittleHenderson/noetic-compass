"""Make tests/ importable as a flat namespace.

Test modules import shared helpers from sibling files (e.g. ``from ui_contract
import assert_panel_wired``). pytest's rootdir insertion covers the repo root
but not tests/ itself on all invocation styles, so pin it explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
