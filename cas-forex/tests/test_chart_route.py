"""Tests for the Trading Windows chart route: candles + quote, TTL-cached.

Network-free: the market data connector is monkeypatched so the test pins the
route's shape, the TTL cache behaviour, and the honest source/live_feed labels
without hitting yfinance/OANDA.
"""

import dataclasses
import asyncio
import time

import pytest

from api.routes import chart as chart_route


@dataclasses.dataclass
class _FakeSnapshot:
    bid: float = 1.1000
    ask: float = 1.1002
    spread: float = 2.0
    is_market_open: bool = True
    session: str = "LONDON"

    @property
    def timestamp(self):
        from cas_forex.time_utils import utc_now

        return utc_now()


class _FakeConnector:
    calls = 0

    def fetch_historical(self, symbol, bars=100, timeframe="M5"):
        type(self).calls += 1
        return [
            {"timestamp": "2026-06-27T00:00:00Z", "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15}
            for _ in range(bars)
        ]

    def fetch_snapshot(self, symbol):
        return _FakeSnapshot()


class _EmptyConnector:
    def __init__(self, *, detail: str = ""):
        self.last_error = detail

    def fetch_historical(self, symbol, bars=100, timeframe="M5"):
        return []

    def fetch_snapshot(self, symbol):
        return _FakeSnapshot(is_market_open=False, session="CLOSED")


class _Mt5FallbackConnector:
    broker_grade_market_truth = True

    def fetch_historical(self, symbol, bars=100, timeframe="M5"):
        return [
            {"timestamp": "2026-06-27T00:00:00Z", "open": 29100.0, "high": 29120.0, "low": 29080.0, "close": 29110.0}
            for _ in range(bars)
        ]

    def fetch_snapshot(self, symbol):
        return _FakeSnapshot(bid=29110.0, ask=29111.0, spread=1.0, session="NEW_YORK")


class _Mt5UnavailableConnector(_EmptyConnector):
    pass


@pytest.fixture(autouse=True)
def _patch_connector(monkeypatch):
    chart_route._CACHE.clear()
    chart_route._IN_FLIGHT.clear()
    _FakeConnector.calls = 0
    monkeypatch.setattr(chart_route, "get_connector", lambda: _FakeConnector())
    yield
    chart_route._CACHE.clear()
    chart_route._IN_FLIGHT.clear()


@pytest.mark.asyncio
async def test_window_returns_candles_and_quote():
    out = await chart_route.get_chart_window(symbol="EUR/USD", timeframe="M5", bars=30)
    assert out["symbol"] == "EUR/USD"
    assert out["bars"] == 30
    assert len(out["candles"]) == 30
    assert set(out["candles"][0]) == {"time", "open", "high", "low", "close"}
    assert out["quote"]["mid"] == pytest.approx(1.1001)
    assert out["live_feed"] is False  # honest: no broker tick feed
    assert out["cached"] is False


@pytest.mark.asyncio
async def test_window_is_ttl_cached():
    await chart_route.get_chart_window(symbol="EUR/USD", timeframe="M5", bars=30)
    assert _FakeConnector.calls == 1
    second = await chart_route.get_chart_window(symbol="EUR/USD", timeframe="M5", bars=30)
    # Served from cache — the connector was not hit again.
    assert _FakeConnector.calls == 1
    assert second["cached"] is True


@pytest.mark.asyncio
async def test_unsupported_symbol_is_handled():
    out = await chart_route.get_chart_window(symbol="ZZZ/ZZZ", timeframe="M5", bars=30)
    assert out["candles"] == []
    assert "error" in out


@pytest.mark.asyncio
async def test_invalid_timeframe_falls_back_to_m5():
    out = await chart_route.get_chart_window(symbol="EUR/USD", timeframe="BOGUS", bars=10)
    assert out["timeframe"] == "M5"


@pytest.mark.asyncio
async def test_window_falls_back_to_mt5_when_primary_has_no_candles(monkeypatch):
    primary = _EmptyConnector(detail="configured provider cannot serve NAS100 on this account")
    fallback = _Mt5FallbackConnector()
    monkeypatch.setattr(chart_route, "_connector_candidates", lambda: [primary, fallback])

    out = await chart_route.get_chart_window(symbol="NAS100", timeframe="M5", bars=20)

    assert out["bars"] == 20
    assert out["source"] == "mt5"
    assert out["live_feed"] is True
    assert out["fallback_used"] is True
    assert "configured provider cannot serve NAS100 on this account" in out["feed_label"]
    assert any(
        attempt["connector"] == "_EmptyConnector" and attempt["status"] == "NO_CANDLES"
        for attempt in out["connector_attempts"]
    )
    assert any(
        attempt["connector"] == "_Mt5FallbackConnector" and attempt["status"] == "CANDLES_FETCHED"
        for attempt in out["connector_attempts"]
    )


@pytest.mark.asyncio
async def test_window_returns_explicit_error_when_no_connector_has_candles(monkeypatch):
    primary = _EmptyConnector(detail="OANDA account does not expose NAS100")
    secondary = _Mt5UnavailableConnector(detail="MT5 terminal unavailable")
    monkeypatch.setattr(chart_route, "_connector_candidates", lambda: [primary, secondary])

    out = await chart_route.get_chart_window(symbol="NAS100", timeframe="M5", bars=20)

    assert out["bars"] == 0
    assert out["candles"] == []
    assert out["fallback_used"] is True
    assert out["feed_label"] == "no chart-capable candle feed"
    assert "OANDA account does not expose NAS100" in out["error"]
    assert "MT5 terminal unavailable" in out["error"]
    assert len(out["connector_attempts"]) == 2


@pytest.mark.asyncio
async def test_symbols_endpoint_lists_supported():
    out = await chart_route.get_symbols()
    assert "EUR/USD" in out["symbols"]
    assert out["timeframes"] == ["M1", "M5", "M15", "H1", "D1"]


@pytest.mark.asyncio
async def test_slow_chart_refresh_times_out_without_blocking_event_loop(monkeypatch):
    def slow_build(symbol, timeframe, bars):
        time.sleep(0.08)
        return {
            "report_kind": "cas_forex_chart_window",
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": 0,
            "candles": [],
            "quote": None,
            "source": "mt5",
            "live_feed": True,
            "feed_label": "late test result",
        }

    monkeypatch.setattr(chart_route, "_build_window", slow_build)
    monkeypatch.setattr(chart_route, "_BUILD_TIMEOUT_SECONDS", 0.01)

    started = time.monotonic()
    chart_task = asyncio.create_task(
        chart_route.get_chart_window(symbol="EUR/USD", timeframe="M5", bars=30)
    )
    await asyncio.sleep(0)
    heartbeat = time.monotonic() - started
    out = await chart_task

    assert heartbeat < 0.05
    assert out["refresh_timeout"] is True
    assert "Operator chat" in out["error"]
    await asyncio.sleep(0.1)
