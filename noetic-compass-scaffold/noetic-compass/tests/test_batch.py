"""Tests for POST /batch endpoint."""


def test_batch_single(client, auth_headers):
    payload = {
        "texts": ["Analyze this text for cognitive patterns."],
        "provider": "mock",
        "mock": True,
    }
    resp = client.post("/batch", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1


def test_batch_multiple(client, auth_headers):
    payload = {
        "texts": [f"Test prompt number {i}" for i in range(5)],
        "provider": "mock",
        "mock": True,
        "max_concurrency": 3,
    }
    resp = client.post("/batch", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["succeeded"] == 5
    assert data["failed"] == 0
    assert len(data["results"]) == 5

    # Each result should have a valid NCCS
    for r in data["results"]:
        assert 0 <= r["nccs"]["composite"] <= 100


def test_batch_requires_auth(client):
    payload = {"texts": ["hello"], "mock": True}
    resp = client.post("/batch", json=payload)
    assert resp.status_code == 401


def test_batch_empty_list_422(client, auth_headers):
    payload = {"texts": [], "mock": True}
    resp = client.post("/batch", json=payload, headers=auth_headers)
    assert resp.status_code == 422
