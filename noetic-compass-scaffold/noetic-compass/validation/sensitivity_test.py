"""Sensitivity tests — the pipeline must respond to meaningful input changes."""

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
    token = create_token(sub="validation-user", api_key="validation-key")
    return {"Authorization": f"Bearer {token}"}


def _wrap(client: TestClient, headers: dict, text: str, dials: list[int]) -> dict:
    resp = client.post(
        "/wrap",
        json={
            "text": text,
            "provider": "mock",
            "dial_config": {"values": dials},
            "mock": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _stage_data(result: dict, stage_name: str) -> dict:
    """Extract the data dict from a named pipeline stage."""
    for stage in result["stages"]:
        if stage["stage"] == stage_name:
            return stage.get("data", {})
    return {}


def test_dial_sensitivity(client: TestClient, auth_headers: dict) -> None:
    """Different dial settings must produce different dial_adjustment stage data."""
    text = "Analyze this text for cognitive operator patterns and drive alignment."
    low = _wrap(client, auth_headers, text, [5] * 10)
    high = _wrap(client, auth_headers, text, [8] * 10)

    low_dials = _stage_data(low, "dial_adjustment").get("dial_values")
    high_dials = _stage_data(high, "dial_adjustment").get("dial_values")

    assert low_dials is not None, "dial_adjustment stage missing dial_values"
    assert high_dials is not None, "dial_adjustment stage missing dial_values"
    assert low_dials != high_dials, (
        f"Dials=5 and dials=8 produced identical dial_values: {low_dials}"
    )


def test_prompt_sensitivity(client: TestClient, auth_headers: dict) -> None:
    """Different prompts must produce different operator scores."""
    dials = [6] * 10
    a = _wrap(client, auth_headers, "Short.", dials)
    b = _wrap(client, auth_headers,
              "This is a much longer and more detailed text designed to produce "
              "significantly different SHA-256 hashing results and therefore different "
              "operator scores in the mock connector pipeline.", dials)

    a_scores = _stage_data(a, "operator_scoring").get("scores")
    b_scores = _stage_data(b, "operator_scoring").get("scores")

    assert a_scores is not None, "operator_scoring stage missing scores"
    assert b_scores is not None, "operator_scoring stage missing scores"
    assert a_scores != b_scores, "Different prompts produced identical operator scores"


def test_open_simplex_validation(client: TestClient, auth_headers: dict) -> None:
    """Domain averages must satisfy open simplex constraints (all > 0, sum ~ 1)."""
    text = "Analyze this text for cognitive operator patterns and drive alignment."
    result = _wrap(client, auth_headers, text, [6] * 10)

    domain_avgs = _stage_data(result, "domain_coherence").get("domain_averages")
    assert domain_avgs is not None, "domain_coherence stage missing domain_averages"
    assert len(domain_avgs) == 4, f"Expected 4 domain averages, got {len(domain_avgs)}"

    for i, val in enumerate(domain_avgs):
        assert val > 0, f"domain_averages[{i}] = {val} violates open simplex (must be > 0)"

    total = sum(domain_avgs)
    assert abs(total - 1.0) < 0.02, f"domain_averages sum = {total}, expected ~1.0"
