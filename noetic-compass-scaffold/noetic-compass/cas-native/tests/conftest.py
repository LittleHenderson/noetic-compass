"""Shared test fixtures and configuration for CAS-Native tests."""

import shutil
import sys
import tempfile
import types
from pathlib import Path

import pytest
import torch


# Ensure the project root is importable, then alias the historical
# `cas-native/` package directory to the importable `cas_native` name
# used throughout the tests.
_package_root = Path(__file__).resolve().parent.parent
_project_root = _package_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_vendor_root = Path(__file__).resolve().parent / "_vendor"
if str(_vendor_root) not in sys.path:
    sys.path.insert(0, str(_vendor_root))

if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_package_root / "__init__.py")
    package.__path__ = [str(_package_root)]
    sys.modules["cas_native"] = package

_tmp_root = Path(__file__).resolve().parent / "_tmp_runtime"
_tmp_root.mkdir(exist_ok=True)


@pytest.fixture(autouse=True)
def set_random_seed():
    """Set a fixed random seed for reproducibility in tests."""
    torch.manual_seed(42)
    yield


@pytest.fixture
def tmp_path():
    """Workspace-local tmp_path to avoid blocked system temp directories."""
    path = Path(tempfile.mkdtemp(dir=_tmp_root))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
