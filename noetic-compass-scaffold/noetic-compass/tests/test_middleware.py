"""Tests for middleware: auth, rate limiting, audit."""

import time

from api.middleware.auth import create_token
from api.config import settings
from jose import jwt


def test_health_no_auth_required(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_missing_auth_header(client):
    resp = client.post("/assess", json={})
    assert resp.status_code == 401
    assert "Missing" in resp.json()["detail"]


def test_invalid_token(client):
    resp = client.post("/assess", json={}, headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


def test_valid_token(client, auth_headers, valid_assess_payload):
    resp = client.post("/assess", json=valid_assess_payload, headers=auth_headers)
    assert resp.status_code == 200


def test_expired_token(client, valid_assess_payload):
    # Create token that expired 1 minute ago
    token = create_token(sub="test", exp_minutes=-1)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/assess", json=valid_assess_payload, headers=headers)
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_rate_limit_not_triggered_within_limit(client, auth_headers, valid_assess_payload):
    """Normal request rate should not trigger rate limiting."""
    for _ in range(3):
        resp = client.post("/assess", json=valid_assess_payload, headers=auth_headers)
        assert resp.status_code == 200


def test_create_token_roundtrip():
    """Verify create_token produces a valid JWT."""

    token = create_token(sub="user1", api_key="key1")
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "user1"
    assert payload["api_key"] == "key1"
    assert "exp" in payload


def test_auth_token_route_uses_per_username_api_key(client):
    resp = client.post("/auth/token", json={"username": "StakeholderA"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "StakeholderA"
    assert payload["api_key"] == "dashboard:stakeholdera"


def test_dashboard_tokens_skip_monthly_cap(client):
    token = create_token(sub="StakeholderA", api_key="dashboard:stakeholdera")
    headers = {"Authorization": f"Bearer {token}"}

    for _ in range(51):
        resp = client.get("/notation/grammar", headers=headers)
        assert resp.status_code == 200
