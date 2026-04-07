"""Shared test fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import create_token


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Valid JWT auth headers for testing."""
    token = create_token(sub="test-user", api_key="test-key")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def valid_assess_payload() -> dict:
    """Valid payload for POST /assess."""
    return {
        "operator_scores": [0.8] * 10,
        "domain_averages": [0.25, 0.25, 0.25, 0.25],
        "drive_scores": [0.7] * 7,
        "rpm_completeness": 0.8,
        "pathway_rpm_completeness": 0.8,
        "bias_flag_count": 0,
        "inversion_axis_scores": [0.9] * 7,
        "stealth_resistance": 0.9,
        "compound_severity": 0.1,
        "manipulation_resistance": 0.85,
        "overton_drift_resistance": 0.8,
    }


@pytest.fixture
def valid_wrap_payload() -> dict:
    """Valid payload for POST /wrap."""
    return {
        "text": "Analyze this text for cognitive operator patterns and drive alignment.",
        "provider": "mock",
        "dial_config": {"values": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6]},
        "mock": True,
    }
