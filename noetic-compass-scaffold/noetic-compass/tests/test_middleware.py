"""Tests for middleware: auth, rate limiting, audit."""

import time

import pytest
from fastapi.testclient import TestClient

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
    # The suite runs with NC_DEBUG=true (see root conftest), so the credential-free
    # local/dev mint path is open. This documents that dev-only behavior.
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


# --- CAS Harness scoped-beta Phase 1: /auth/token mint lock --------------------


def test_auth_token_refused_in_prod_without_credential(client, monkeypatch):
    """Production posture (debug off, no mint secret) must refuse the open mint."""
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "auth_mint_secret", "")

    resp = client.post("/auth/token", json={"username": "Attacker"})
    assert resp.status_code == 401
    assert "disabled" in resp.json()["detail"].lower()


def test_auth_token_refused_in_prod_with_wrong_credential(client, monkeypatch):
    """A configured mint secret is required everywhere; a mismatch is refused."""
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "auth_mint_secret", "real-shared-secret")

    # No credential presented.
    resp = client.post("/auth/token", json={"username": "Attacker"})
    assert resp.status_code == 401

    # Wrong credential presented.
    resp = client.post(
        "/auth/token",
        json={"username": "Attacker"},
        headers={"X-Auth-Mint-Secret": "wrong"},
    )
    assert resp.status_code == 401


def test_auth_token_mint_with_credential_header(client, monkeypatch):
    """With the configured mint secret presented (header), minting works in prod."""
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "auth_mint_secret", "real-shared-secret")

    resp = client.post(
        "/auth/token",
        json={"username": "StakeholderA"},
        headers={"X-Auth-Mint-Secret": "real-shared-secret"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "StakeholderA"
    assert payload["api_key"] == "dashboard:stakeholdera"


def test_auth_token_mint_with_credential_body(client, monkeypatch):
    """The mint secret can also travel in the request body (parity with the header)."""
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "auth_mint_secret", "real-shared-secret")

    resp = client.post(
        "/auth/token",
        json={"username": "StakeholderB", "mint_secret": "real-shared-secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["expires_in_minutes"] == settings.jwt_expiry_minutes


def test_startup_fails_with_default_jwt_secret_in_prod(monkeypatch):
    """The lifespan must fail loud when debug=False and jwt_secret is the default."""
    from api.main import app

    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "jwt_secret", "change-me-in-production")

    with pytest.raises(RuntimeError, match="change-me-in-production"):
        with TestClient(app):
            pass


def test_startup_ok_in_prod_with_real_jwt_secret(monkeypatch):
    """A non-default secret in prod lets the app start (guard is satisfied)."""
    from api.main import app

    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "jwt_secret", "a-real-production-secret")

    # Entering the context runs the lifespan startup; no RuntimeError expected.
    with TestClient(app) as started:
        resp = started.get("/health")
        assert resp.status_code == 200
