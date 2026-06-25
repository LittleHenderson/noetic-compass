"""Tests for the /api/forex/timeframes route — the HTTP face of the
multi-timeframe runtime selector.

Drives the FastAPI ASGI app directly so the tests catch route-registration
regressions and don't need a live uvicorn process.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from api.server import app
from api.routes import timeframes as tf_route
from cas_forex.multi_timeframe_runtime import (
    CANONICAL_TIMEFRAMES,
    MultiTimeframeRuntime,
)


async def _asgi(path: str, *, method: str = "GET") -> tuple[int, Any]:
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
        "method": method,
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


def _isolate_runtime() -> MultiTimeframeRuntime:
    """Swap the route's process-singleton runtime with a fresh instance so
    tests don't share state with each other or with prior server use."""
    fresh = MultiTimeframeRuntime()
    tf_route.set_runtime_for_testing(fresh)
    return fresh


# ---------------------------------------------------------------------------


def test_canonical_endpoint_lists_runtime_vocabulary():
    _isolate_runtime()
    status, body = asyncio.run(_asgi("/api/forex/timeframes/canonical"))
    assert status == 200
    assert sorted(body["canonical_timeframes"]) == sorted(CANONICAL_TIMEFRAMES)


def test_list_active_is_empty_by_default():
    _isolate_runtime()
    status, body = asyncio.run(_asgi("/api/forex/timeframes"))
    assert status == 200
    assert body == {"symbols": []}


def test_get_unknown_symbol_returns_empty_selection_not_404():
    _isolate_runtime()
    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD"))
    assert status == 200
    assert body == {"symbol": "EURUSD", "active_timeframes": []}


def test_activate_then_query_roundtrip():
    runtime = _isolate_runtime()

    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD/M5", method="POST"))
    assert status == 200
    assert body == {"symbol": "EURUSD", "active_timeframes": ["M5"]}

    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD/H1", method="POST"))
    assert status == 200
    assert body == {"symbol": "EURUSD", "active_timeframes": ["H1", "M5"]}

    # Runtime reflects both activations.
    assert runtime.active_timeframes_for("EURUSD") == frozenset({"M5", "H1"})

    status, body = asyncio.run(_asgi("/api/forex/timeframes"))
    assert status == 200
    assert body == {
        "symbols": [{"symbol": "EURUSD", "active_timeframes": ["H1", "M5"]}]
    }


def test_activate_unknown_timeframe_returns_400_with_canonical_list():
    _isolate_runtime()
    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD/Q1", method="POST"))
    assert status == 400
    assert body["detail"]["error"] == "unknown_timeframe"
    assert "Q1" in body["detail"]["message"]
    assert sorted(body["detail"]["canonical_timeframes"]) == sorted(CANONICAL_TIMEFRAMES)


def test_activate_is_idempotent():
    _isolate_runtime()
    asyncio.run(_asgi("/api/forex/timeframes/EURUSD/M15", method="POST"))
    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD/M15", method="POST"))
    assert status == 200
    assert body == {"symbol": "EURUSD", "active_timeframes": ["M15"]}


def test_deactivate_removes_only_target_timeframe():
    runtime = _isolate_runtime()
    asyncio.run(_asgi("/api/forex/timeframes/EURUSD/M5", method="POST"))
    asyncio.run(_asgi("/api/forex/timeframes/EURUSD/H1", method="POST"))

    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD/M5", method="DELETE"))
    assert status == 200
    assert body == {"symbol": "EURUSD", "active_timeframes": ["H1"]}
    assert runtime.active_timeframes_for("EURUSD") == frozenset({"H1"})


def test_deactivate_last_drops_symbol_from_listing():
    _isolate_runtime()
    asyncio.run(_asgi("/api/forex/timeframes/GBPUSD/D1", method="POST"))
    asyncio.run(_asgi("/api/forex/timeframes/GBPUSD/D1", method="DELETE"))

    status, body = asyncio.run(_asgi("/api/forex/timeframes"))
    assert status == 200
    assert body == {"symbols": []}


def test_deactivate_unknown_timeframe_returns_400():
    _isolate_runtime()
    status, body = asyncio.run(_asgi("/api/forex/timeframes/EURUSD/Q1", method="DELETE"))
    assert status == 400
    assert body["detail"]["error"] == "unknown_timeframe"


def test_multi_symbol_listing_is_sorted_for_stable_ui():
    _isolate_runtime()
    asyncio.run(_asgi("/api/forex/timeframes/USDJPY/M1", method="POST"))
    asyncio.run(_asgi("/api/forex/timeframes/EURUSD/H4", method="POST"))

    status, body = asyncio.run(_asgi("/api/forex/timeframes"))
    assert status == 200
    assert [s["symbol"] for s in body["symbols"]] == ["EURUSD", "USDJPY"]
    assert body["symbols"][0]["active_timeframes"] == ["H4"]
    assert body["symbols"][1]["active_timeframes"] == ["M1"]
