"""Tests for the /api/forex/live-telemetry route.

Drives the FastAPI ASGI app directly (same pattern as
``tests/test_timeframes_api.py``) and patches the route's evidence
collectors so we control upstream shape without touching real evidence
files. The route MUST never fabricate prices or PnL when no data exists.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import pytest

from api.server import app
from api.routes import live_telemetry as lt_route


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


@pytest.fixture(autouse=True)
def _empty_sources(monkeypatch: pytest.MonkeyPatch):
    """Default to no live evidence; individual tests opt in to mocked data."""
    monkeypatch.setattr(lt_route, "_collect_from_mt5_terminal", lambda: None)
    monkeypatch.setattr(lt_route, "_collect_from_movement_stream", lambda: None)
    yield


# ---------------------------------------------------------------------------


def test_endpoint_registered_and_returns_200():
    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert isinstance(body, dict)


def test_response_schema_has_all_required_fields():
    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert set(body.keys()) >= {
        "as_of_iso",
        "open_positions",
        "totals",
        "data_freshness",
    }
    assert set(body["totals"].keys()) >= {"open_position_count", "total_floating_pnl"}
    assert set(body["data_freshness"].keys()) >= {"source", "stale", "last_update_iso"}


def test_no_live_evidence_returns_none_source_and_stale():
    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["open_positions"] == []
    assert body["totals"]["open_position_count"] == 0
    assert body["totals"]["total_floating_pnl"] == 0.0
    assert body["data_freshness"]["source"] == "none"
    assert body["data_freshness"]["stale"] is True
    assert body["data_freshness"]["last_update_iso"] is None


def test_mocked_paper_evidence_echoed_with_correct_totals(monkeypatch: pytest.MonkeyPatch):
    """When canonical mt5-terminal evidence is missing, fall back to the
    paper/demo movement stream and surface those positions verbatim."""
    paper_positions = [
        {
            "symbol": "EURUSD",
            "side": "LONG",
            "lot_size": 0.01,
            "open_price": 1.0850,
            "current_price": 1.0855,
            "floating_pnl_usd": 0.50,
            "broker_ticket": "P-100",
        },
        {
            "symbol": "GBPUSD",
            "side": "SHORT",
            "lot_size": 0.02,
            "open_price": 1.2700,
            "current_price": 1.2680,
            "floating_pnl_usd": 4.00,
            "broker_ticket": None,
        },
    ]
    from cas_forex.time_utils import utc_now

    fresh_ts = utc_now().isoformat()
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (
            [lt_route._normalize_paper_position(p) for p in paper_positions],
            fresh_ts,
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["data_freshness"]["source"] == "movement_stream"
    assert body["data_freshness"]["stale"] is False
    assert body["totals"]["open_position_count"] == 2
    symbols = {row["symbol"] for row in body["open_positions"]}
    assert symbols == {"EURUSD", "GBPUSD"}


def test_total_floating_pnl_equals_sum_of_positions(monkeypatch: pytest.MonkeyPatch):
    positions = [
        {
            "symbol": "EURUSD",
            "direction": "BUY",
            "lots": 0.01,
            "entry_price": 1.0,
            "current_price": 1.001,
            "floating_pnl": 1.25,
            "opened_at_iso": None,
            "broker_ticket": None,
        },
        {
            "symbol": "USDJPY",
            "direction": "SELL",
            "lots": 0.05,
            "entry_price": 150.0,
            "current_price": 149.8,
            "floating_pnl": -3.40,
            "opened_at_iso": None,
            "broker_ticket": None,
        },
        {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "lots": 0.10,
            "entry_price": 2000.0,
            "current_price": 2001.5,
            "floating_pnl": 15.00,
            "opened_at_iso": None,
            "broker_ticket": None,
        },
    ]
    from cas_forex.time_utils import utc_now

    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (positions, utc_now().isoformat()),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    expected = round(sum(p["floating_pnl"] for p in positions), 2)
    assert body["totals"]["total_floating_pnl"] == expected
    assert body["totals"]["open_position_count"] == 3


def test_direction_is_normalized_to_buy_or_sell(monkeypatch: pytest.MonkeyPatch):
    """MT5 verifier reports direction as an int (0=BUY, 1=SELL); paper
    movement stream reports it as ``side: LONG|SHORT``. Both must
    surface as the canonical "BUY" / "SELL" tokens."""
    mt5_positions_raw = [
        {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": 0,  # 0 = BUY
            "volume": 0.01,
            "price_open": 1.0850,
            "price_current": 1.0855,
            "profit": 0.50,
        },
        {
            "ticket": 12346,
            "symbol": "GBPUSD",
            "type": 1,  # 1 = SELL
            "volume": 0.02,
            "price_open": 1.2700,
            "price_current": 1.2680,
            "profit": 4.00,
        },
        # Tolerate already-string upstream shapes too.
        {
            "ticket": 12347,
            "symbol": "USDJPY",
            "type": "SELL",
            "volume": 0.03,
            "price_open": 150.0,
            "price_current": 149.8,
            "profit": 6.00,
        },
    ]
    from cas_forex.time_utils import utc_now

    monkeypatch.setattr(
        lt_route,
        "_collect_from_mt5_terminal",
        lambda: (
            [lt_route._normalize_mt5_position(p) for p in mt5_positions_raw],
            utc_now().isoformat(),
        ),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["data_freshness"]["source"] == "mt5_terminal_api_verifier"
    by_symbol = {row["symbol"]: row["direction"] for row in body["open_positions"]}
    assert by_symbol == {"EURUSD": "BUY", "GBPUSD": "SELL", "USDJPY": "SELL"}
    # And the only allowed values are BUY / SELL.
    assert {row["direction"] for row in body["open_positions"]} <= {"BUY", "SELL"}


def test_stale_flag_set_when_last_update_is_old(monkeypatch: pytest.MonkeyPatch):
    """Evidence older than the staleness window must surface stale=True
    even though the source is non-empty."""
    from datetime import timedelta
    from cas_forex.time_utils import utc_now

    old_ts = (utc_now() - timedelta(hours=2)).isoformat()
    positions = [
        {
            "symbol": "EURUSD",
            "direction": "BUY",
            "lots": 0.01,
            "entry_price": 1.0,
            "current_price": 1.001,
            "floating_pnl": 1.0,
            "opened_at_iso": None,
            "broker_ticket": None,
        }
    ]
    monkeypatch.setattr(
        lt_route,
        "_collect_from_movement_stream",
        lambda: (positions, old_ts),
    )

    status, body = asyncio.run(_asgi("/api/forex/live-telemetry"))
    assert status == 200
    assert body["data_freshness"]["stale"] is True
    assert body["data_freshness"]["last_update_iso"] == old_ts
