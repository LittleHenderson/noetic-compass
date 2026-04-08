"""Tests for POST /benchmark endpoint."""


def test_benchmark_mock_single(client, auth_headers):
    """5 runs on mock provider — verify scores length, mean, std_dev."""
    payload = {
        "text": "Analyze cognitive patterns in this benchmark text.",
        "providers": ["mock"],
        "runs_per_provider": 5,
    }
    resp = client.post("/benchmark", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["runs_per_provider"] == 5
    assert data["total_runs"] == 5
    assert len(data["results"]) == 1

    r = data["results"][0]
    assert r["provider"] == "mock"
    assert len(r["scores"]) == 5
    assert "mean" in r
    assert "std_dev" in r
    assert r["failed_runs"] == 0


def test_benchmark_mock_multi(client, auth_headers):
    """2 mock providers — verify both appear in results."""
    payload = {
        "text": "Multi-provider benchmark test prompt.",
        "providers": ["mock", "mock"],
        "runs_per_provider": 3,
    }
    resp = client.post("/benchmark", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    assert data["total_runs"] == 6
    for r in data["results"]:
        assert r["provider"] == "mock"
        assert len(r["scores"]) == 3


def test_benchmark_low_variance_mock(client, auth_headers):
    """Mock is deterministic — std_dev should be ~0, high_variance False."""
    payload = {
        "text": "Deterministic mock benchmark test.",
        "providers": ["mock"],
        "runs_per_provider": 5,
    }
    resp = client.post("/benchmark", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    r = resp.json()["results"][0]
    assert r["std_dev"] < 1.0
    assert r["high_variance"] is False


def test_benchmark_requires_auth(client):
    """401 without auth token."""
    payload = {
        "text": "Auth test.",
        "providers": ["mock"],
        "runs_per_provider": 2,
    }
    resp = client.post("/benchmark", json=payload)
    assert resp.status_code == 401


def test_benchmark_invalid_provider(client, auth_headers):
    """Unknown provider → all runs fail."""
    payload = {
        "text": "Invalid provider benchmark test.",
        "providers": ["nonexistent_provider_xyz"],
        "runs_per_provider": 3,
    }
    resp = client.post("/benchmark", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    r = resp.json()["results"][0]
    assert r["provider"] == "nonexistent_provider_xyz"
    assert r["failed_runs"] == 3
    assert len(r["scores"]) == 0
