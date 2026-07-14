"""Tests for middleware: auth, rate limiting, audit."""

import json
import logging
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.auth import create_token
from api.config import settings
from api.main import _browser_managed_cors_credentials_allowed, app
from api.middleware.rate_limit import RateLimitMiddleware
from jose import jwt


def test_health_no_auth_required(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_missing_auth_header(client):
    resp = client.post("/assess", json={})
    assert resp.status_code == 401
    assert "Missing" in resp.json()["detail"]


def test_direct_auth_error_keeps_cors_headers(client):
    origin = "https://account-preview.vercel.app"
    resp = client.post("/assess", json={}, headers={"Origin": origin})
    assert resp.status_code == 401
    assert resp.headers.get("access-control-allow-origin") in {"*", origin}


def test_invalid_token(client):
    resp = client.post("/assess", json={}, headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


def test_failed_auth_is_written_to_structured_audit_log(client, caplog):
    """Audit logging must wrap JWT auth so rejected probes remain observable."""
    with caplog.at_level(logging.INFO, logger="noetic.audit"):
        resp = client.post("/assess", json={})

    assert resp.status_code == 401
    entries = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "noetic.audit" and record.message.startswith("{")
    ]
    assert any(
        entry["method"] == "POST"
        and entry["path"] == "/assess"
        and entry["status"] == 401
        and entry["user"] == "anonymous"
        and entry["request_id"]
        for entry in entries
    )


def test_cors_never_grants_browser_credentials_to_regex_preview_origin(client):
    """A regex-matched preview may use Bearer headers but never browser credentials."""
    resp = client.options(
        "/assess",
        headers={
            "Origin": "https://attacker-preview.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in resp.headers
    allowed_headers = resp.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers

def test_explicit_allowlist_plus_preview_regex_cannot_enable_browser_credentials():
    assert _browser_managed_cors_credentials_allowed(
        ["https://trusted.example"],
        r"https://([a-z0-9-]+\.)*vercel\.app",
    ) is False


def test_cors_wraps_failed_auth_response(client):
    origin = "https://attacker-preview.vercel.app"
    resp = client.post("/assess", json={}, headers={"Origin": origin})

    assert resp.status_code == 401
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in resp.headers
    assert resp.headers["x-request-id"]


def test_cors_wraps_rate_limit_response(client):
    # Build the middleware stack, then exhaust one unique dashboard bucket.
    client.get("/health")
    current = app.middleware_stack
    while current is not None and not isinstance(current, RateLimitMiddleware):
        current = getattr(current, "app", None)
    assert isinstance(current, RateLimitMiddleware)

    api_key = "dashboard:cors-rate-limit-regression"
    bucket = current._get_bucket(api_key)
    bucket.tokens = 0.0
    bucket.last_refill = time.monotonic()
    token = create_token(sub="cors-test", api_key=api_key)
    resp = client.get(
        "/notation/grammar",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "https://attacker-preview.vercel.app",
        },
    )

    assert resp.status_code == 429
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in resp.headers
    assert resp.headers["x-request-id"]


def test_anonymous_evidence_share_has_dedicated_rate_limit() -> None:
    isolated = FastAPI()

    @isolated.get("/evidence/shared/{share_id}")
    def fetch_share(share_id: str) -> dict[str, str]:
        return {"share_id": share_id}

    isolated.add_middleware(RateLimitMiddleware)
    path = "/evidence/shared/shr_" + "a" * 24
    with TestClient(isolated) as isolated_client:
        assert isolated_client.get(path).status_code == 200
        current = isolated.middleware_stack
        while current is not None and not isinstance(current, RateLimitMiddleware):
            current = getattr(current, "app", None)
        assert isinstance(current, RateLimitMiddleware)
        client_buckets = [
            bucket
            for key, bucket in current.sensitive_buckets.items()
            if key.startswith("evidence-share-client:")
        ]
        assert len(client_buckets) == 1
        share_buckets = [
            bucket
            for key, bucket in current.sensitive_buckets.items()
            if key.startswith("evidence-share:")
        ]
        assert len(share_buckets) == 1

        # The client-wide bucket is consumed before allocating a per-share
        # bucket, so cycling random share ids cannot bypass the edge guard.
        client_buckets[0].tokens = 0.0
        client_buckets[0].last_refill = time.monotonic()
        cycled = isolated_client.get("/evidence/shared/shr_" + "b" * 24)
        assert cycled.status_code == 429
        assert len(current.sensitive_buckets) == 2

        client_buckets[0].tokens = float(client_buckets[0].capacity)
        share_buckets[0].tokens = 0.0
        share_buckets[0].last_refill = time.monotonic()

        limited = isolated_client.get(path)
        assert limited.status_code == 429
        assert limited.json() == {"detail": "Rate limit exceeded (evidence share)"}
        assert limited.headers["cache-control"].startswith("no-store")



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


def test_create_token_omits_account_claims_by_default():
    """Backward-compat: with no account args, the payload is exactly {sub, api_key, exp}."""
    token = create_token(sub="user1", api_key="key1")
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert set(payload.keys()) == {"sub", "api_key", "exp"}
    assert "account_id" not in payload
    assert "tenant_id" not in payload
    assert "role" not in payload


def test_create_token_embeds_server_derived_account_claims():
    """When the server supplies account claims, they are embedded additively."""
    token = create_token(
        sub="member@example.com",
        api_key="account:acct-123",
        account_id="acct-123",
        tenant_id="tenant-L",
        role="member",
    )
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "member@example.com"
    assert payload["account_id"] == "acct-123"
    assert payload["tenant_id"] == "tenant-L"
    assert payload["role"] == "member"


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
