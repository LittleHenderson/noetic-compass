"""Test configuration for cas-synthetic scaffold.

Registers the `cas_synthetic` alias so pytest can `from cas_synthetic.generator
import V74BaselineGenerator` without installing the package. Mirrors the
pattern used by the sibling cas-native test suite.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_CAS_SYNTHETIC_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _CAS_SYNTHETIC_DIR.parent

# Make `cas_synthetic` importable even though the directory is hyphenated.
if "cas_synthetic" not in sys.modules:
    pkg = types.ModuleType("cas_synthetic")
    pkg.__file__ = str(_CAS_SYNTHETIC_DIR / "__init__.py")
    pkg.__path__ = [str(_CAS_SYNTHETIC_DIR)]
    sys.modules["cas_synthetic"] = pkg

# Repo root on sys.path for any cross-package imports.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_CAS_SYNTHETIC_DIR) not in sys.path:
    sys.path.insert(0, str(_CAS_SYNTHETIC_DIR))
