"""Tests for the /api/forex/autonomous-loop route."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest

from api.server import app
from api.routes import autonomous_loop as route_module


async def _asgi_get(path: str) -> tuple[int, Any]:
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    payload = json.loads(body.decode("utf-8")) if body else None
    return int(status), payload


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def test_route_returns_200_when_no_evidence():
    route_module.set_loader_for_testing(lambda: {
        "autowake_report": None,
        "latest_cycle_report": None,
        "recent_event_journal": [],
        "daily_rollup": None,
    })
    status, body = asyncio.run(_asgi_get("/api/forex/autonomous-loop/health"))
    assert status == 200
    assert body["overall_status"] == "unknown"


def test_payload_carries_required_fields():
    route_module.set_loader_for_testing(lambda: {
        "autowake_report": None,
        "latest_cycle_report": None,
        "recent_event_journal": [],
        "daily_rollup": None,
    })
    _, body = asyncio.run(_asgi_get("/api/forex/autonomous-loop/health"))
    required = {
        "overall_status",
        "last_cycle_at_iso",
        "seconds_since_last_cycle",
        "cycles_today",
        "decisions_today",
        "executions_today",
        "blocked_today",
        "autowake_present",
        "autowake_next_due_iso",
        "plain_english_summary",
        "diagnostic_hints",
    }
    assert required.issubset(set(body.keys()))


def test_plain_english_summary_never_advises_future_trade():
    route_module.set_loader_for_testing(lambda: {
        "autowake_report": None,
        "latest_cycle_report": None,
        "recent_event_journal": [],
        "daily_rollup": None,
    })
    _, body = asyncio.run(_asgi_get("/api/forex/autonomous-loop/health"))
    summary = body["plain_english_summary"].lower()
    forbidden = ("buy now", "should you trade", "good entry", "place a trade", "what should i do")
    for phrase in forbidden:
        assert phrase not in summary, f"forbidden trade-advisory phrase: {phrase!r}"


def test_default_loader_uses_loop_health_inputs():
    route_module.reset_loader_for_testing()
    assert route_module._LOADER is route_module._default_loader
