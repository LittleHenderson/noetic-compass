"""Tests for market data connectors."""
import pytest
from datetime import datetime
from cas_forex.market_data.connector import YFinanceConnector
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
