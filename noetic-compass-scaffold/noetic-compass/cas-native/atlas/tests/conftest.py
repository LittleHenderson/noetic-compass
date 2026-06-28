"""Test fixtures for cas_native.atlas.

We deliberately avoid the parent ``cas-native/tests/conftest.py`` (which pulls
in torch) — the atlas package is pure stdlib and these tests should run
without the heavy ML stack installed. We replicate just enough sys.path
plumbing to make ``import cas_native.atlas`` work.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path


_package_root = Path(__file__).resolve().parents[2]
_project_root = _package_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_package_root / "__init__.py")
    package.__path__ = [str(_package_root)]
    sys.modules["cas_native"] = package
