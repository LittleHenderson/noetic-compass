"""Public Atlas account-mode capability handshake contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.config import settings
from api.main import app
from api.middleware.auth import (
    is_public_account_capability_request,
    is_public_path,
)


def test_public_capabilities_is_exactly_public_and_suffixes_remain_protected() -> None:
    assert is_public_path("/public/capabilities") is False
    assert is_public_path("/public/capabilities/extra") is False
    assert is_public_account_capability_request(
        "/public/capabilities", "GET"
    ) is True
    assert is_public_account_capability_request(
        "/public/capabilities", "POST"
    ) is False
    assert is_public_account_capability_request(
        "/public/capabilities", "GET", "debug=true"
    ) is False

    response = TestClient(app).get("/public/capabilities")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"accounts_enabled": settings.accounts_enabled}

    client = TestClient(app)
    for method, path in (
        ("get", "/public/capabilities?debug=true"),
        ("get", "/public/capabilities/extra"),
        ("post", "/public/capabilities"),
        ("head", "/public/capabilities"),
    ):
        blocked = getattr(client, method)(path)
        assert blocked.status_code == 401
        if method == "head":
            assert blocked.content == b""
        else:
            assert blocked.json() == {
                "detail": "Missing or invalid Authorization header"
            }


def test_public_capabilities_returns_only_the_runtime_account_boolean(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "accounts_enabled", True)

    enabled = TestClient(app).get(
        "/public/capabilities",
        headers={"Authorization": "Bearer must-not-be-needed"},
    )

    assert enabled.status_code == 200
    assert enabled.json() == {"accounts_enabled": True}
    assert set(enabled.json()) == {"accounts_enabled"}

    monkeypatch.setattr(settings, "accounts_enabled", False)
    disabled = TestClient(app).get("/public/capabilities")
    assert disabled.status_code == 200
    assert disabled.json() == {"accounts_enabled": False}
