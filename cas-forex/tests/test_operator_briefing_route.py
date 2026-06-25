"""ASGI tests for the /api/forex/operator-briefing route.

The router is mounted on a local FastAPI app so the parent ``api.server``
integration is not a prerequisite. Loader-injection (``set_loader_for_testing``)
keeps tests fully deterministic.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import operator_briefing as route_module


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/operator-briefing")
    return app


async def _asgi_get(app: FastAPI, path: str) -> tuple[int, Any]:
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


def _empty_inputs() -> dict[str, Any]:
    return {
        "loop_health": None,
        "latest_decision": None,
        "live_telemetry": None,
        "mt5_probe": None,
        "readiness": None,
    }


def _full_inputs() -> dict[str, Any]:
    return {
        "loop_health": {
            "overall_status": "running",
            "cycles_today": 2,
            "decisions_today": 4,
            "executions_today": 1,
            "blocked_today": 0,
            "autowake_present": True,
            "autowake_next_due_iso": "2026-06-24T13:00:00+00:00",
            "diagnostic_hints": [],
        },
        "latest_decision": {
            "cycle_id": "cycle-xyz",
            "overall_status": "executed",
            "plain_english_summary": "Latest decision summary.",
        },
        "live_telemetry": {
            "totals": {"open_position_count": 1, "total_floating_pnl": 5.5},
            "open_positions": [{"symbol": "EURUSD", "floating_pnl": 5.5}],
        },
        "mt5_probe": {"summary": {"terminal_connected": True, "broker_api_verified": True}},
        "readiness": {"checks_total": 10, "checks_passed": 8, "next_actions": []},
    }


def test_empty_inputs_returns_200_with_unknown_briefing():
    route_module.set_loader_for_testing(_empty_inputs)
    app = _make_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    assert status == 200
    assert body["loop_health_status"] == "unknown"
    assert body["cycles_today"] == 0
    assert body["latest_decision_summary"] is None
    assert body["mt5_terminal_connected"] is False


def test_full_inputs_returns_200_with_populated_briefing():
    route_module.set_loader_for_testing(_full_inputs)
    app = _make_app()
    status, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    assert status == 200
    assert body["loop_health_status"] == "running"
    assert body["cycles_today"] == 2
    assert body["latest_decision_cycle_id"] == "cycle-xyz"
    assert body["open_position_count"] == 1
    assert body["mt5_terminal_connected"] is True
    assert body["readiness_gates_open"] == 8
    assert body["readiness_gates_total"] == 10


def test_payload_carries_all_required_keys():
    route_module.set_loader_for_testing(_full_inputs)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    required = {
        "generated_at_iso",
        "loop_health_status",
        "cycles_today",
        "decisions_today",
        "executions_today",
        "blocked_today",
        "latest_decision_summary",
        "latest_decision_cycle_id",
        "latest_decision_overall_status",
        "open_position_count",
        "total_floating_pnl",
        "mt5_terminal_connected",
        "mt5_broker_api_verified",
        "readiness_gates_open",
        "readiness_gates_total",
        "autowake_present",
        "autowake_next_due_iso",
        "plain_english_briefing",
        "diagnostic_hints",
    }
    assert required.issubset(set(body.keys()))


def test_payload_is_json_serializable_and_briefing_never_advises():
    route_module.set_loader_for_testing(_full_inputs)
    app = _make_app()
    _, body = asyncio.run(_asgi_get(app, "/api/forex/operator-briefing"))
    # JSON-roundtrips cleanly.
    text = json.dumps(body)
    assert isinstance(text, str)
    # Briefing has no advisory phrases.
    summary = body["plain_english_briefing"].lower()
    forbidden = (
        "buy now",
        "should you trade",
        "good entry",
        "place a trade",
        "what should i do",
        "you should sell",
        "now is the time",
    )
    for phrase in forbidden:
        assert phrase not in summary, f"forbidden advisory phrase in briefing: {phrase!r}"


def test_default_loader_uses_load_operator_briefing_inputs():
    route_module.reset_loader_for_testing()
    assert route_module._LOADER is route_module._default_loader
