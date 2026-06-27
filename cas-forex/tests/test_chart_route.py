"""Tests for the Trading Windows chart route: candles + quote, TTL-cached.

Network-free: the market data connector is monkeypatched so the test pins the
route's shape, the TTL cache behaviour, and the honest source/live_feed labels
without hitting yfinance/OANDA.
"""

import dataclasses

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


@pytest.fixture(autouse=True)
def _patch_connector(monkeypatch):
    chart_route._CACHE.clear()
    _FakeConnector.calls = 0
    monkeypatch.setattr(chart_route, "get_connector", lambda: _FakeConnector())
    yield
    chart_route._CACHE.clear()


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
async def test_symbols_endpoint_lists_supported():
    out = await chart_route.get_symbols()
    assert "EUR/USD" in out["symbols"]
    assert out["timeframes"] == ["M1", "M5", "M15", "H1", "D1"]
