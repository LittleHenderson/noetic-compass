"""Shared test fixtures and configuration for CAS-Native tests."""

import sys
from pathlib import Path

import pytest
import torch


# Ensure the parent directory is on the Python path so that
# `import cas_native` resolves from the noetic-compass root.
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture(autouse=True)
def set_random_seed():
    """Set a fixed random seed for reproducibility in tests."""
    torch.manual_seed(42)
    yield
