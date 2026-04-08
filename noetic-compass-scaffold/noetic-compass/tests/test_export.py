"""Tests for the assessment export endpoint and store persistence."""

from __future__ import annotations

from api.store import clear_memory_store


def test_export_empty(client, auth_headers):
    """GET /assessments/export with no saved assessments returns empty list."""
    clear_memory_store()
    resp = client.get("/assessments/export", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessments"] == []
    assert data["count"] == 0


def test_wrap_then_export(client, auth_headers, valid_wrap_payload):
    """POST /wrap persists the result, GET /assessments/export retrieves it."""
    clear_memory_store()

    # Run a wrap
    wrap_resp = client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)
    assert wrap_resp.status_code == 200
    wrap_data = wrap_resp.json()

    # Export should now contain one record
    export_resp = client.get("/assessments/export", headers=auth_headers)
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["count"] == 1

    record = export_data["assessments"][0]
    assert record["text"] == valid_wrap_payload["text"]
    assert record["response"]["nccs"]["composite"] == wrap_data["nccs"]["composite"]


def test_export_pagination(client, auth_headers, valid_wrap_payload):
    """Export supports limit and offset query parameters."""
    clear_memory_store()

    # Create 3 assessments
    for _ in range(3):
        resp = client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)
        assert resp.status_code == 200

    # Limit 2
    resp = client.get("/assessments/export?limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["limit"] == 2

    # Offset 2 should return 1
    resp = client.get("/assessments/export?limit=10&offset=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1


def test_export_requires_auth(client):
    """GET /assessments/export requires authentication."""
    resp = client.get("/assessments/export")
    assert resp.status_code == 401


def test_store_persistence_across_requests(client, auth_headers, valid_wrap_payload):
    """Data stored by /wrap survives across separate GET requests (not just in-flight)."""
    clear_memory_store()

    # Store two assessments
    client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)
    client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)

    # First retrieval
    resp1 = client.get("/assessments/export", headers=auth_headers)
    assert resp1.json()["count"] == 2

    # Second retrieval — same data should still be there
    resp2 = client.get("/assessments/export", headers=auth_headers)
    assert resp2.json()["count"] == 2
