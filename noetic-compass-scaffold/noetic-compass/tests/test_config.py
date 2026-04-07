"""Tests for GET/PUT /config — dial configuration validation."""


def test_get_default_config(client, auth_headers):
    resp = client.get("/config", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["values"] == [6] * 10


def test_put_valid_config(client, auth_headers):
    payload = {"values": [5, 6, 7, 7, 8, 5, 6, 4, 5, 6]}
    resp = client.put("/config", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["values"] == [5, 6, 7, 7, 8, 5, 6, 4, 5, 6]

    # Verify it persists
    resp2 = client.get("/config", headers=auth_headers)
    assert resp2.json()["values"] == [5, 6, 7, 7, 8, 5, 6, 4, 5, 6]


def test_put_dial_out_of_range_422(client, auth_headers):
    payload = {"values": [2, 6, 6, 6, 6, 6, 6, 6, 6, 6]}  # 2 < 3
    resp = client.put("/config", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_put_dial_too_high_422(client, auth_headers):
    payload = {"values": [10, 6, 6, 6, 6, 6, 6, 6, 6, 6]}  # 10 > 9
    resp = client.put("/config", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_put_involution_divergence_422(client, auth_headers):
    """CO-2=3, CO-3=8 => divergence 5 > 4."""
    payload = {"values": [6, 6, 3, 8, 6, 6, 6, 6, 6, 6]}
    resp = client.put("/config", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_put_involution_max_divergence_ok(client, auth_headers):
    """CO-2=3, CO-3=7 => divergence 4 = max, should be OK."""
    payload = {"values": [6, 6, 3, 7, 6, 6, 6, 6, 6, 6]}
    resp = client.put("/config", json=payload, headers=auth_headers)
    assert resp.status_code == 200


def test_config_requires_auth(client):
    resp = client.get("/config")
    assert resp.status_code == 401
