"""Regression coverage for the CAS Forex settings/dashboard API surface.

These tests intentionally drive the FastAPI ASGI app directly instead of relying
on a live uvicorn process. They catch stale-route and stale-dashboard-shape
regressions like:
  * /settings/authority-boundary returning 404
  * /settings/runtime-gates returning 404
  * owner-control/dashboard missing personal-utilization-only fields
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from api.server import app


async def _asgi_get(path: str) -> tuple[int, dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return int(status), json.loads(body.decode("utf-8"))


def test_settings_owner_control_exposes_personal_only_scope():
    status, body = asyncio.run(_asgi_get("/api/forex/settings/owner-control"))
    assert status == 200
    assert body["personal_utilization_only"] is True
    assert body["account_scope"] == "PERSONAL_ONLY"
    assert "client_money" in body["disallowed_scopes"]
    assert "pooled_capital" in body["disallowed_scopes"]


def test_settings_authority_and_runtime_gate_routes_are_registered():
    status, authority = asyncio.run(_asgi_get("/api/forex/settings/authority-boundary"))
    assert status == 200
    assert authority["live_trading_status"] in {"CURRENTLY NOT LICENSED", "AUTHORIZED"}
    assert authority["trading_edge_status"] == "OPEN"

    status, gates = asyncio.run(_asgi_get("/api/forex/settings/runtime-gates"))
    assert status == 200
    assert sorted(gates["decisions"]) == [
        "auto_deposit",
        "bank_card_movement",
        "broker_accept",
        "live_trading",
        "payout_automation",
    ]


def test_dashboard_contains_personal_only_and_runtime_gates():
    status, body = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert body["ownerControl"]["personal_utilization_only"] is True
    assert body["ownerControl"]["account_scope"] == "PERSONAL_ONLY"
    assert "runtimeGates" in body
    assert "authorityBoundary" in body
