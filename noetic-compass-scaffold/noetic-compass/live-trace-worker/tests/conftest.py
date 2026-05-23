"""pytest fixtures.

Forces LIVE_TRACE_DEMO_MODE=1 for the whole test session so the worker
stays in demo mode even on a developer box with torch installed. That
keeps the integration tests fast + reproducible. Real-Pythia tests
explicitly mock the loaded model + clear the cache via
``runtime.reset_for_test``.
"""

from __future__ import annotations

import os

# Set BEFORE the FastAPI app is constructed so warm_load picks it up.
os.environ.setdefault("LIVE_TRACE_DEMO_MODE", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.runtime import reset_for_test  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_loaded_model() -> None:
    """Each test starts with no warm-loaded model in the singleton."""
    reset_for_test()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())
