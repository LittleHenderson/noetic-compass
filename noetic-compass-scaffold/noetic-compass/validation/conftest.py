"""Validation suite conftest — ensures project root is on sys.path."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root so `api` is importable
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
