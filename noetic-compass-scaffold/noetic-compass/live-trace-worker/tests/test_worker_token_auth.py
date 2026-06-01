"""Tests for the optional X-Atlas-Worker-Token auth shim (app/auth.py).

The middleware must be a no-op by default (env var unset) so dev / CI / the
existing SSH-tunnel deploy are unaffected, and must enforce the shared secret
on non-health routes once ATLAS_LIVE_WORKER_TOKEN is set.

These tests build a fresh app per env-var state instead of reusing the
session-wide ``client`` fixture, because the middleware reads the env var at
request time but the app is constructed once per client.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth import WORKER_TOKEN_ENV, WORKER_TOKEN_HEADER
from app.main import create_app

_TOKEN = "s3cret-worker-token"
_SESSION_BODY = {"prompt": "A warm coffee cup on the table.", "seed": 42}


@pytest.fixture()
def fresh_client() -> TestClient:
    """A TestClient over a freshly constructed app (picks up current env)."""
    return TestClient(create_app())


def test_auth_disabled_by_default_allows_protected_route(monkeypatch, fresh_client):
    monkeypatch.delenv(WORKER_TOKEN_ENV, raising=False)
    r = fresh_client.post("/sessions", json=_SESSION_BODY)
    assert r.status_code == 200, r.text


def test_auth_disabled_when_token_blank(monkeypatch, fresh_client):
    # Whitespace-only token counts as "not configured".
    monkeypatch.setenv(WORKER_TOKEN_ENV, "   ")
    r = fresh_client.post("/sessions", json=_SESSION_BODY)
    assert r.status_code == 200, r.text


def test_protected_route_rejects_missing_token(monkeypatch, fresh_client):
    monkeypatch.setenv(WORKER_TOKEN_ENV, _TOKEN)
    r = fresh_client.post("/sessions", json=_SESSION_BODY)
    assert r.status_code == 401
    body = r.json()
    assert body["header"] == WORKER_TOKEN_HEADER


def test_protected_route_rejects_wrong_token(monkeypatch, fresh_client):
    monkeypatch.setenv(WORKER_TOKEN_ENV, _TOKEN)
    r = fresh_client.post(
        "/sessions",
        json=_SESSION_BODY,
        headers={WORKER_TOKEN_HEADER: "not-the-token"},
    )
    assert r.status_code == 401


def test_protected_route_accepts_correct_token(monkeypatch, fresh_client):
    monkeypatch.setenv(WORKER_TOKEN_ENV, _TOKEN)
    r = fresh_client.post(
        "/sessions",
        json=_SESSION_BODY,
        headers={WORKER_TOKEN_HEADER: _TOKEN},
    )
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("path", ["/health", "/health/realmode"])
def test_health_paths_exempt_even_with_token_set(monkeypatch, fresh_client, path):
    # RunPod health checks + the API real-mode proxy must work without the
    # secret, so health endpoints are exempt from the token gate.
    monkeypatch.setenv(WORKER_TOKEN_ENV, _TOKEN)
    r = fresh_client.get(path)
    assert r.status_code == 200, r.text


def test_token_compare_is_whitespace_tolerant_on_header(monkeypatch, fresh_client):
    # A header value with surrounding whitespace still matches; this mirrors the
    # strip() applied to the configured secret.
    monkeypatch.setenv(WORKER_TOKEN_ENV, _TOKEN)
    r = fresh_client.post(
        "/sessions",
        json=_SESSION_BODY,
        headers={WORKER_TOKEN_HEADER: f"  {_TOKEN}  "},
    )
    assert r.status_code == 200, r.text
