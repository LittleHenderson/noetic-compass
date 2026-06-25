"""Tests for the /webhook-notifications route — HTTP face of the chassis.

Drives a FastAPI ASGI app directly so the tests catch route-registration
regressions without spinning up uvicorn. The parent integrator wires
:mod:`api.routes.webhook_notifications` into :mod:`api.server` in a
follow-on slice; until then these tests mount the router on a local
FastAPI app so the route surface is verifiable in isolation.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI

from api.routes import webhook_notifications as route_module
from cas_forex.webhook_notifications import (
    WebhookDispatchResult,
    WebhookSubscriptionStore,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/webhook-notifications")
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


def _isolate(tmp_path) -> tuple[FastAPI, WebhookSubscriptionStore]:
    """Build a fresh app + isolate the route's store under tmp_path."""
    store = WebhookSubscriptionStore(path=tmp_path / "subscriptions.jsonl")
    route_module.set_store_for_testing(store)
    route_module.set_transport_for_testing(None)
    return _build_app(), store


# ---------------------------------------------------------------------------


def test_subscribe_missing_url_returns_400(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/subscribe",
            method="POST",
            body={"label": "slack"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "missing_field"


def test_subscribe_then_list_returns_one(tmp_path):
    app, _ = _isolate(tmp_path)

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/subscribe",
            method="POST",
            body={
                "webhook_url": "https://hooks.slack.example/services/A/B/C",
                "label": "slack-trades",
            },
        )
    )
    assert status == 200
    assert body["total_subscriptions"] == 1
    assert body["subscription"]["webhook_url"] == "https://hooks.slack.example/services/A/B/C"
    assert body["subscription"]["label"] == "slack-trades"

    status, body = asyncio.run(
        _asgi(app, "/api/forex/webhook-notifications/subscriptions")
    )
    assert status == 200
    assert body["total_subscriptions"] == 1
    assert len(body["subscriptions"]) == 1
    assert body["subscriptions"][0]["webhook_url"] == "https://hooks.slack.example/services/A/B/C"


def test_subscribe_then_unsubscribe_then_list_returns_zero(tmp_path):
    app, _ = _isolate(tmp_path)

    asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/subscribe",
            method="POST",
            body={"webhook_url": "https://hooks.example/abc"},
        )
    )

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/unsubscribe",
            method="POST",
            body={"webhook_url": "https://hooks.example/abc"},
        )
    )
    assert status == 204
    assert body is None

    status, body = asyncio.run(
        _asgi(app, "/api/forex/webhook-notifications/subscriptions")
    )
    assert status == 200
    assert body == {"subscriptions": [], "total_subscriptions": 0}


def test_unsubscribe_unknown_url_is_idempotent(tmp_path):
    app, _ = _isolate(tmp_path)
    status, _ = asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/unsubscribe",
            method="POST",
            body={"webhook_url": "https://hooks.example/never-added"},
        )
    )
    assert status == 204


def test_test_with_no_subscriptions_returns_empty_results(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/test",
            method="POST",
            body={},
        )
    )
    assert status == 200
    assert body == {"results": []}


def test_test_with_injected_transport_reports_success(tmp_path):
    app, _ = _isolate(tmp_path)

    asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/subscribe",
            method="POST",
            body={
                "webhook_url": "https://hooks.example/abc",
                "label": "slack-trades",
            },
        )
    )

    captured: list = []

    class _Resp:
        def __init__(self):
            self.status_code = 200
            self.text = "ok"

    def fake_transport(url, json, headers, timeout):
        captured.append({"url": url, "json": json})
        return _Resp()

    route_module.set_transport_for_testing(fake_transport)
    try:
        status, body = asyncio.run(
            _asgi(
                app,
                "/api/forex/webhook-notifications/test",
                method="POST",
                body={"title": "CAS Forex", "body": "Loop stalled (observational)."},
            )
        )
    finally:
        route_module.set_transport_for_testing(None)

    assert status == 200
    assert len(body["results"]) == 1
    only = body["results"][0]
    assert only["webhook_url"] == "https://hooks.example/abc"
    assert only["success"] is True
    assert only["status_code"] == 200
    assert only["error_message"] is None
    assert only["response_snippet"] == "ok"

    assert captured == [
        {
            "url": "https://hooks.example/abc",
            "json": {
                "title": "CAS Forex",
                "body": "Loop stalled (observational).",
            },
        }
    ]


def test_test_label_filter_targets_only_matching_subscriptions(tmp_path):
    app, _ = _isolate(tmp_path)

    for url, label in (
        ("https://hooks.example/slack", "slack"),
        ("https://hooks.example/discord", "discord"),
    ):
        asyncio.run(
            _asgi(
                app,
                "/api/forex/webhook-notifications/subscribe",
                method="POST",
                body={"webhook_url": url, "label": label},
            )
        )

    captured: list = []

    class _Resp:
        def __init__(self):
            self.status_code = 200
            self.text = ""

    def fake_transport(url, json, headers, timeout):
        captured.append(url)
        return _Resp()

    route_module.set_transport_for_testing(fake_transport)
    try:
        status, body = asyncio.run(
            _asgi(
                app,
                "/api/forex/webhook-notifications/test",
                method="POST",
                body={"label": "slack", "title": "CAS Forex", "body": "Observational."},
            )
        )
    finally:
        route_module.set_transport_for_testing(None)

    assert status == 200
    assert [r["webhook_url"] for r in body["results"]] == ["https://hooks.example/slack"]
    assert captured == ["https://hooks.example/slack"]


def test_test_refuses_advisory_payload_at_dispatch_time(tmp_path):
    app, _ = _isolate(tmp_path)

    asyncio.run(
        _asgi(
            app,
            "/api/forex/webhook-notifications/subscribe",
            method="POST",
            body={"webhook_url": "https://hooks.example/abc"},
        )
    )

    transport_calls: list = []

    def transport_should_not_be_called(*_args, **_kwargs):
        transport_calls.append("called")

        class _R:
            status_code = 200
            text = ""

        return _R()

    route_module.set_transport_for_testing(transport_should_not_be_called)
    try:
        status, body = asyncio.run(
            _asgi(
                app,
                "/api/forex/webhook-notifications/test",
                method="POST",
                body={"title": "Hot tip", "body": "You should buy EURUSD now"},
            )
        )
    finally:
        route_module.set_transport_for_testing(None)

    assert status == 200
    assert len(body["results"]) == 1
    only = body["results"][0]
    assert only["success"] is False
    assert "advisory phrase" in (only["error_message"] or "")
    # And the transport was never invoked — the guard is enforced before
    # any HTTP attempt.
    assert transport_calls == []
