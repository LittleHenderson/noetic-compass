"""Pytest fixtures + path shim for the DST scaffold tests.

Mirrors the cas-native dialectic + cas-synthetic conftest.py path-shim
approach so tests can run without setup.py installation: we register
the directory ``cas-native/`` under the importable name ``cas_native``
and ``cas-synthetic/`` under ``cas_synthetic`` in ``sys.modules``.

Tests in this directory must run in <30 seconds total. They rely only
on the stdlib + the DST scaffold + the multi_turn generator.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path


_HERE = Path(__file__).resolve()
_DST_PACKAGE = _HERE.parent.parent           # cas-native/dst/
_CAS_NATIVE_DIR = _DST_PACKAGE.parent        # cas-native/
_NC_ROOT = _CAS_NATIVE_DIR.parent            # noetic-compass/
_SCAFFOLD_ROOT = _NC_ROOT.parent             # noetic-compass-scaffold/
_REPO_ROOT = _SCAFFOLD_ROOT.parent           # tksCAS/
_CAS_SYNTHETIC_DIR = _REPO_ROOT / "cas-synthetic"

# Project root on sys.path so direct `cas_native.*` resolves via __path__.
if str(_NC_ROOT) not in sys.path:
    sys.path.insert(0, str(_NC_ROOT))

# Register the directory cas-native/ under the importable name
# ``cas_native``. With ``__path__`` set, submodule imports such as
# ``cas_native.dst`` resolve automatically against the dst/ subdir.
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__file__ = str(_CAS_NATIVE_DIR / "__init__.py")
    pkg.__path__ = [str(_CAS_NATIVE_DIR)]
    sys.modules["cas_native"] = pkg

# Register cas_synthetic the same way so cross-package imports work.
if _CAS_SYNTHETIC_DIR.exists() and "cas_synthetic" not in sys.modules:
    pkg2 = types.ModuleType("cas_synthetic")
    pkg2.__file__ = str(_CAS_SYNTHETIC_DIR / "__init__.py")
    pkg2.__path__ = [str(_CAS_SYNTHETIC_DIR)]
    sys.modules["cas_synthetic"] = pkg2

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
