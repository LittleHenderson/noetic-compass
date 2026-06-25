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

from fastapi import FastAPI

from api.routes import notifications as notif_route
from cas_forex.push_notifications import (
    PushDispatchResult,
    PushSubscriptionStore,
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
    return _build_app(), store


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
    assert body["subscription"]["endpoint"] == "https://push.example/abc"
    assert body["subscription"]["keys"] == {"p256dh": "p", "auth": "a"}
    assert body["subscription"]["label"] == "phone"

    status, body = asyncio.run(_asgi(app, "/api/forex/notifications/subscriptions"))
    assert status == 200
    assert body["total_subscriptions"] == 1
    assert len(body["subscriptions"]) == 1
    assert body["subscriptions"][0]["endpoint"] == "https://push.example/abc"


def test_subscribe_then_unsubscribe_then_list_returns_zero(tmp_path):
    app, _ = _isolate(tmp_path)

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
            "/api/forex/notifications/unsubscribe",
            method="POST",
            body={"endpoint": "https://push.example/abc"},
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
            "endpoint": "https://push.example/abc",
            "success": True,
            "status_code": 201,
            "error_message": None,
        }
    ]
    assert captured == [
        (
            "https://push.example/abc",
            {"title": "CAS Forex", "body": "Loop stalled (observational)."},
        )
    ]


def test_test_push_without_transport_reports_missing_backend(tmp_path):
    app, _ = _isolate(tmp_path)

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
