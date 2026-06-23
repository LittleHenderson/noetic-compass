"""Regression coverage for the live PCBA dashboard/API surface."""

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


def test_pcba_cockpit_route_is_active_and_bounded():
    status, body = asyncio.run(_asgi_get("/api/forex/pcba/cockpit"))
    assert status == 200
    assert body["report_kind"] == "cas_forex_pcba_cockpit"
    assert body["panels_active"] is True
    assert body["pcba_readiness"]["any_broker_accept_authority"] is False
    assert body["cjt_readiness"]["any_broker_accept_authority"] is False
    assert body["optimizer_guard"]["can_create_broker_accept"] is False
    assert body["optimizer_guard"]["can_unlock_live_trading"] is False
    assert body["reference_boards"]
    assert body["component_catalog"]


def test_dashboard_embeds_pcba_payload():
    status, body = asyncio.run(_asgi_get("/api/forex/dashboard"))
    assert status == 200
    assert body["pcba"]["panels_active"] is True
    assert body["pcba"]["summary"]["pcba_total_checks"] >= 1
    assert body["pcba"]["summary"]["cjt_total_checks"] >= 1


def test_pcba_subroutes_are_registered():
    for path in [
        "/api/forex/pcba/readiness/pcba",
        "/api/forex/pcba/readiness/cjt",
        "/api/forex/pcba/readiness/ccb",
        "/api/forex/pcba/optimizer-guard",
    ]:
        status, _ = asyncio.run(_asgi_get(path))
        assert status == 200
