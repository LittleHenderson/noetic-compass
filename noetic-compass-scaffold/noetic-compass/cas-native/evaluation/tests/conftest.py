"""Local conftest — make ``cas_native`` importable from this test file's location."""

from __future__ import annotations

import sys
import types
from pathlib import Path

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package
