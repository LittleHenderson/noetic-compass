"""Shared test fixtures for cas_native.trace.

We keep this conftest small and side-effect-free: the parent
``cas-native/tests/conftest.py`` already takes care of the
``cas_native`` package alias and the project-root sys.path entry.

We add this conftest so that the trace tests can be collected
when invoked from the trace subtree (e.g. ``pytest trace/tests``)
without relying on the parent conftest having run first.
"""

from __future__ import annotations

import shutil
import sys
import types
import uuid
from pathlib import Path

import pytest


_package_root = Path(__file__).resolve().parents[2]  # .../cas-native
_project_root = _package_root.parent  # .../noetic-compass

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_package_root / "__init__.py")
    package.__path__ = [str(_package_root)]
    sys.modules["cas_native"] = package


_tmp_root = Path(__file__).resolve().parent / "_tmp_runtime"
_tmp_root.mkdir(exist_ok=True)


@pytest.fixture
def tmp_path():
    path = _tmp_root / f"tmp_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_input() -> str:
    return "How do I refuse a request that conflicts with principled aversion?"


@pytest.fixture
def empty_input() -> str:
    return ""
