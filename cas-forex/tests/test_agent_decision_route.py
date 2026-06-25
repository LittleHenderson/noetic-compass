"""Tests for the /api/forex/agent-decision route."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest

from api.server import app
from api.routes import agent_decision as route_module


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


def test_route_returns_200_with_no_evidence():
    route_module.set_loader_for_testing(lambda: {
        "agent_cycle_report": None,
        "agent_memory_report": None,
        "daily_learning_rollup": None,
        "strategy_dev_queue_report": None,
        "strategy_leads": None,
        "walk_forward_report": None,
        "pcba_report": None,
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/latest"))
    assert status == 200
    assert body["overall_status"] == "no_recent_decision"
    assert isinstance(body["chain"], list)
    assert len(body["chain"]) >= 1


def test_payload_shape_matches_dataclass():
    route_module.set_loader_for_testing(lambda: {
        "agent_cycle_report": None,
        "agent_memory_report": None,
        "daily_learning_rollup": None,
        "strategy_dev_queue_report": None,
        "strategy_leads": None,
        "walk_forward_report": None,
        "pcba_report": None,
    })
    status, body = asyncio.run(_asgi_get("/api/forex/agent-decision/latest"))
    assert status == 200
    expected_top_keys = {
        "cycle_id",
        "overall_status",
        "plain_english_summary",
        "chain",
        "next_action_hint",
    }
    assert expected_top_keys.issubset(set(body.keys()))
    step = body["chain"][0]
    expected_step_keys = {"name", "headline", "detail", "evidence", "status"}
    assert expected_step_keys.issubset(set(step.keys()))


def test_plain_english_summary_never_advises_future_trade():
    """The route exposes the explainer; the explainer guarantees no
    advisory language. Smoke-check at the route boundary."""
    route_module.set_loader_for_testing(lambda: {
        "agent_cycle_report": None,
        "agent_memory_report": None,
        "daily_learning_rollup": None,
        "strategy_dev_queue_report": None,
        "strategy_leads": None,
        "walk_forward_report": None,
        "pcba_report": None,
    })
    _, body = asyncio.run(_asgi_get("/api/forex/agent-decision/latest"))
    summary = body["plain_english_summary"].lower()
    forbidden = ("buy now", "should you trade", "good entry", "place a trade", "what should i do")
    for phrase in forbidden:
        assert phrase not in summary, f"forbidden trade-advisory phrase: {phrase!r}"


def test_default_loader_is_pure_function():
    """When set_loader_for_testing is reset, default loader is the disk one."""
    route_module.reset_loader_for_testing()
    assert route_module._LOADER is route_module._default_loader
