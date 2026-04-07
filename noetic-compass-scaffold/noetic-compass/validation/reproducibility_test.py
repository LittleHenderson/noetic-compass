"""Reproducibility tests — identical inputs must produce identical outputs."""

from __future__ import annotations

import json
from pathlib import Path

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


@pytest.fixture
def wrap_payload() -> dict:
    return {
        "text": "Analyze this text for cognitive operator patterns and drive alignment.",
        "provider": "mock",
        "dial_config": {"values": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6]},
        "mock": True,
    }


@pytest.fixture
def benchmark() -> dict:
    fixture_path = Path(__file__).parent / "benchmark_fixture.json"
    return json.loads(fixture_path.read_text())


def test_mock_determinism(client: TestClient, auth_headers: dict, wrap_payload: dict) -> None:
    """5 identical /wrap calls must all produce the same composite score."""
    scores: list[float] = []
    for _ in range(5):
        resp = client.post("/wrap", json=wrap_payload, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        scores.append(resp.json()["nccs"]["composite"])

    assert len(set(scores)) == 1, f"Non-deterministic scores: {scores}"


def test_benchmark_fixture(client: TestClient, auth_headers: dict, benchmark: dict) -> None:
    """Pipeline output must match the frozen benchmark ranges."""
    resp = client.post("/wrap", json=benchmark["input"], headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    nccs = data["nccs"]
    expected = benchmark["expected"]

    # Composite within expected range
    assert expected["composite_min"] <= nccs["composite"] <= expected["composite_max"], (
        f"Composite {nccs['composite']} outside [{expected['composite_min']}, {expected['composite_max']}]"
    )

    # Certification matches
    assert nccs["certification"] == expected["certification"], (
        f"Expected {expected['certification']}, got {nccs['certification']}"
    )

    # All 8 stages present and passing
    stages = data["stages"]
    assert len(stages) == expected["stage_count"], (
        f"Expected {expected['stage_count']} stages, got {len(stages)}"
    )
    if expected["all_stages_pass"]:
        for stage in stages:
            assert stage["success"], f"Stage {stage['stage']} failed: {stage.get('error')}"
