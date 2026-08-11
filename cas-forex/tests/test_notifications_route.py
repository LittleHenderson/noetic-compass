"""Tests for the /notifications route — HTTP face of the push chassis.

Drives a FastAPI ASGI app directly so the tests catch route-registration
regressions without spinning up uvicorn.

The parent integrator wires :mod:`api.routes.notifications` into
:mod:`api.server` after the fleet rollout. Until then these tests
mount the router on a local FastAPI app so the route surface is
verifiable in isolation.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import notifications as notif_route
from cas_forex import push_delivery_control
from cas_forex.push_notifications import (
    DISPATCH_BACKEND_MISSING_MESSAGE,
    PushDispatchResult,
    PushSubscriptionStore,
    push_subscription_id,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(notif_route.router, prefix="/api/forex/notifications")
    return app


async def _asgi(
    app: FastAPI,
    path: str,
    *,
    method: str = "GET",
    body: Any | None = None,
) -> tuple[int, Any]:
    sent: list[dict[str, Any]] = []

    encoded = b""
    headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        headers.append((b"content-type", b"application/json"))
        headers.append((b"content-length", str(len(encoded)).encode("ascii")))

    request_sent = {"done": False}

    async def receive() -> dict[str, Any]:
        if request_sent["done"]:
            return {"type": "http.disconnect"}
        request_sent["done"] = True
        return {"type": "http.request", "body": encoded, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    raw_body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    payload = json.loads(raw_body.decode("utf-8")) if raw_body else None
    return int(status), payload


def _isolate(tmp_path) -> tuple[FastAPI, PushSubscriptionStore]:
    """Build a fresh app + isolate the route's store under tmp_path."""
    store = PushSubscriptionStore(path=tmp_path / "subscriptions.jsonl")
    notif_route.set_store_for_testing(store)
    notif_route.set_transport_for_testing(None)
    push_delivery_control.set_override_path_for_tests(tmp_path / "push-delivery-overrides.json")
    return _build_app(), store


@pytest.fixture(autouse=True)
def _reset_push_backend_overrides():
    yield
    push_delivery_control.clear_push_delivery_overrides()
    push_delivery_control.set_override_path_for_tests(None)


# ---------------------------------------------------------------------------


def test_subscribe_missing_endpoint_returns_400(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/subscribe",
            method="POST",
            body={"keys": {"p256dh": "p", "auth": "a"}, "label": "phone"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "missing_field"


def test_subscribe_missing_keys_returns_400(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/subscribe",
            method="POST",
            body={"endpoint": "https://push.example/abc", "label": "phone"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "missing_field"


def test_subscribe_then_list_returns_one(tmp_path):
    app, store = _isolate(tmp_path)

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/subscribe",
            method="POST",
            body={
                "endpoint": "https://push.example/abc",
                "keys": {"p256dh": "p", "auth": "a"},
                "label": "phone",
            },
        )
    )
    assert status == 200
    assert body["total_subscriptions"] == 1
    assert body["subscription"]["subscription_id"] == push_subscription_id("https://push.example/abc")
    assert body["subscription"]["endpoint_masked"] == "https://push.example/..."
    assert body["subscription"]["label"] == "phone"
    assert "https://push.example/abc" not in json.dumps(body)
    assert '"p256dh"' not in json.dumps(body)
    assert '"auth"' not in json.dumps(body)
    persisted = store.path.read_text(encoding="utf-8")
    assert "https://push.example/abc" not in persisted
    assert '"encrypted": true' in persisted.lower()

    status, body = asyncio.run(_asgi(app, "/api/forex/notifications/subscriptions"))
    assert status == 200
    assert body["total_subscriptions"] == 1
    assert len(body["subscriptions"]) == 1
    assert body["subscriptions"][0]["subscription_id"] == push_subscription_id("https://push.example/abc")
    assert body["subscriptions"][0]["endpoint_masked"] == "https://push.example/..."
    assert "https://push.example/abc" not in json.dumps(body)


def test_subscribe_then_unsubscribe_then_list_returns_zero(tmp_path):
    app, _ = _isolate(tmp_path)

    _, subscribe_body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/subscribe",
            method="POST",
            body={
                "endpoint": "https://push.example/abc",
                "keys": {"p256dh": "p", "auth": "a"},
            },
        )
    )

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/unsubscribe",
            method="POST",
            body={"subscription_id": subscribe_body["subscription"]["subscription_id"]},
        )
    )
    assert status == 204
    assert body is None  # 204 has no body

    status, body = asyncio.run(_asgi(app, "/api/forex/notifications/subscriptions"))
    assert status == 200
    assert body == {"subscriptions": [], "total_subscriptions": 0}


def test_unsubscribe_unknown_endpoint_is_idempotent(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/unsubscribe",
            method="POST",
            body={"endpoint": "https://push.example/never-added"},
        )
    )
    assert status == 204


def test_test_push_with_no_subscriptions_returns_empty_results(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/test-push",
            method="POST",
            body={},
        )
    )
    assert status == 200
    assert body == {"results": []}


def test_test_push_with_injected_transport_reports_success(tmp_path):
    app, _ = _isolate(tmp_path)

    asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/subscribe",
            method="POST",
            body={
                "endpoint": "https://push.example/abc",
                "keys": {"p256dh": "p", "auth": "a"},
                "label": "phone",
            },
        )
    )

    captured: list = []

    def fake_transport(subscription, payload):
        captured.append((subscription.endpoint, payload))
        return PushDispatchResult(
            endpoint=subscription.endpoint,
            success=True,
            status_code=201,
            error_message=None,
        )

    notif_route.set_transport_for_testing(fake_transport)
    try:
        status, body = asyncio.run(
            _asgi(
                app,
                "/api/forex/notifications/test-push",
                method="POST",
                body={
                    "payload": {
                        "title": "CAS Forex",
                        "body": "Loop stalled (observational).",
                    }
                },
            )
        )
    finally:
        notif_route.set_transport_for_testing(None)

    assert status == 200
    assert body["results"] == [
        {
            "subscription_id": push_subscription_id("https://push.example/abc"),
            "endpoint_masked": "https://push.example/...",
            "success": True,
            "status_code": 201,
            "error_message": None,
        }
    ]
    assert "https://push.example/abc" not in json.dumps(body)
    assert captured == [
        (
            "https://push.example/abc",
            {"title": "CAS Forex", "body": "Loop stalled (observational)."},
        )
    ]


def test_test_push_without_transport_reports_missing_backend(tmp_path, monkeypatch):
    app, _ = _isolate(tmp_path)
    monkeypatch.setattr(
        "cas_forex.push_notifications._resolve_default_transport",
        lambda: (None, DISPATCH_BACKEND_MISSING_MESSAGE),
    )

    asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/subscribe",
            method="POST",
            body={
                "endpoint": "https://push.example/abc",
                "keys": {"p256dh": "p", "auth": "a"},
            },
        )
    )

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/test-push",
            method="POST",
            body={},
        )
    )
    assert status == 200
    assert len(body["results"]) == 1
    only = body["results"][0]
    assert only["success"] is False
    assert only["status_code"] is None
    assert "pywebpush" in (only["error_message"] or "")


def test_backend_route_reports_push_backend_status(tmp_path, monkeypatch):
    app, _ = _isolate(tmp_path)
    monkeypatch.setattr(
        push_delivery_control,
        "probe_push_delivery_backend",
        lambda: {"available": True, "package": "pywebpush", "version": "2.3.0"},
    )
    push_delivery_control.set_push_delivery_overrides(
        vapid_public_key="PUBLIC_KEY_1234567890",
        vapid_private_key="PRIVATE_KEY_0987654321",
        vapid_subject="mailto:owner@example.com",
    )

    status, body = asyncio.run(_asgi(app, "/api/forex/notifications/backend"))

    assert status == 200
    assert body["report_kind"] == "cas_forex_push_delivery_backend"
    assert body["dispatch_backend_available"] is True
    assert body["subscription_registration_ready"] is True
    assert body["dispatch_ready"] is True
    assert body["fully_ready"] is True
    assert body["vapid_public_key"] == "PUBLIC_KEY_1234567890"
    assert body["vapid_private_key"]["configured"] is True
    assert body["vapid_private_key"]["masked_value"]
    assert "PRIVATE_KEY_0987654321" not in json.dumps(body)


def test_backend_update_and_reset_routes_persist_encrypted_vapid_material(tmp_path, monkeypatch):
    app, _ = _isolate(tmp_path)
    monkeypatch.setattr(
        push_delivery_control,
        "probe_push_delivery_backend",
        lambda: {"available": True, "package": "pywebpush", "version": "2.3.0"},
    )

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/backend/update",
            method="POST",
            body={
                "vapid_public_key": "PUBLIC_KEY_1234567890",
                "vapid_private_key": "PRIVATE_KEY_0987654321",
                "vapid_subject": "mailto:owner@example.com",
            },
        )
    )

    assert status == 200
    assert body["status"] == "UPDATED"
    assert sorted(body["applied_keys"]) == [
        "vapid_private_key",
        "vapid_public_key",
        "vapid_subject",
    ]
    assert body["push_backend"]["dispatch_ready"] is True
    persisted = (tmp_path / "push-delivery-overrides.json").read_text(encoding="utf-8")
    assert "PUBLIC_KEY_1234567890" not in persisted
    assert "PRIVATE_KEY_0987654321" not in persisted
    assert '"encrypted": true' in persisted.lower()

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/notifications/backend/reset",
            method="POST",
            body={},
        )
    )

    assert status == 200
    assert body["status"] == "RESET"
    assert sorted(body["applied_keys"]) == [
        "vapid_private_key",
        "vapid_public_key",
        "vapid_subject",
    ]
    assert body["push_backend"]["dispatch_ready"] is False
    assert not (tmp_path / "push-delivery-overrides.json").exists()
