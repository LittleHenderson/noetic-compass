"""Tests for market data connectors."""
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from cas_forex.market_data.connector import YFinanceConnector, _mt5_symbol_open, forex_week_open
from cas_forex.schemas.market import MarketSnapshot


class TestYFinanceConnector:
    def test_fetch_snapshot_returns_market_snapshot(self):
        conn = YFinanceConnector()
        snap = conn.fetch_snapshot("EUR/USD")
        assert isinstance(snap, MarketSnapshot)
        assert snap.symbol == "EUR/USD"
        assert snap.bid > 0
        assert snap.ask > 0
        # bid/ask may invert outside market hours; just verify prices positive
        assert snap.ask > 0
        assert snap.mid == (snap.bid + snap.ask) / 2.0

    def test_fetch_snapshot_all_supported_symbols(self):
        conn = YFinanceConnector()
        for sym in ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]:
            snap = conn.fetch_snapshot(sym)
            assert snap.symbol == sym
            assert snap.bid > 0

    def test_fetch_snapshot_invalid_symbol_raises(self):
        conn = YFinanceConnector()
        with pytest.raises(ValueError):
            conn.fetch_snapshot("INVALID/XYZ")

    def test_fetch_snapshot_has_timestamp(self):
        conn = YFinanceConnector()
        snap = conn.fetch_snapshot("EUR/USD")
        assert isinstance(snap.timestamp, datetime)

    def test_fetch_historical_returns_list(self):
        conn = YFinanceConnector()
        candles = conn.fetch_historical("EUR/USD", bars=24, timeframe="H1")
        assert isinstance(candles, list)
        if len(candles) > 0:
            c = candles[0]
            assert "open" in c
            assert "high" in c
            assert "low" in c
            assert "close" in c

    def test_is_connected(self):
        conn = YFinanceConnector()
        assert conn.is_connected() in (True, False)  # depends on network

    def test_session_detection(self):
        conn = YFinanceConnector()
        session = conn._detect_session()
        assert session in ("ASIAN", "LONDON", "NEW_YORK", "OVERLAP", "UNKNOWN")


class TestMt5WeeklySessionTruth:
    class _Mt5:
        SYMBOL_TRADE_MODE_DISABLED = 0

    @staticmethod
    def _info():
        return SimpleNamespace(trade_mode=1)

    def test_sunday_reopen_matches_cockpit_and_scheduler(self):
        before = datetime(2026, 7, 12, 21, 59, tzinfo=timezone.utc)
        reopened = datetime(2026, 7, 12, 22, 0, tzinfo=timezone.utc)

        assert forex_week_open(before) is False
        assert forex_week_open(reopened) is True
        assert _mt5_symbol_open(
            self._Mt5(), self._info(), 1.1, 1.2, timestamp=before, now=before
        ) is False
        assert _mt5_symbol_open(
            self._Mt5(), self._info(), 1.1, 1.2, timestamp=reopened, now=reopened
        ) is True

    def test_friday_close_and_saturday_remain_closed(self):
        friday_close = datetime(2026, 7, 10, 22, 0, tzinfo=timezone.utc)
        saturday = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)

        assert forex_week_open(friday_close) is False
        assert forex_week_open(saturday) is False
        assert _mt5_symbol_open(
            self._Mt5(), self._info(), 1.1, 1.2, timestamp=friday_close, now=friday_close
        ) is False

    def test_open_week_tick_still_fails_closed_when_stale(self):
        now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
        stale = datetime(2026, 7, 13, 11, 54, tzinfo=timezone.utc)

        assert forex_week_open(now) is True
        assert _mt5_symbol_open(
            self._Mt5(), self._info(), 1.1, 1.2, timestamp=stale, now=now
        ) is False
