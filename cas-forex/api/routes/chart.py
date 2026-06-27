"""HTTP route for the Trading Windows cockpit — live-ish candles + quote per symbol.

``GET /window?symbol=&timeframe=&bars=`` returns OHLC candles plus the current
quote for one symbol, ready for the ``CandlestickChart`` component. The data
comes from ``cas_forex.market_data.connector.get_connector()`` (yfinance by
default; OANDA when configured).

A small in-process TTL cache (~20s) keyed by (symbol, timeframe, bars) sits in
front of the connector: yfinance is slow / rate-limited and uvicorn is a single
worker, so the UI can poll several windows every 10-15s without hammering the
upstream. ``GET /symbols`` lists the tradeable symbols for the selectors.

HONESTY: yfinance is delayed, retail market data — not a pro tick feed, and there
is no connected *broker* price feed running. So ``live_feed`` is reported false
and ``source`` names the real provider; the UI labels this "near-real-time".
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Query

from cas_forex.market_data.connector import get_connector

router = APIRouter()

# (symbol, timeframe, bars) -> (monotonic_expiry, payload)
_CACHE: dict[tuple[str, str, int], tuple[float, dict[str, Any]]] = {}
_TTL_SECONDS = 20.0

_VALID_TIMEFRAMES = ("M1", "M5", "M15", "H1", "D1")


def _supported_symbols() -> list[str]:
    from cas_forex.schemas.forecast import SUPPORTED_SYMBOLS

    return sorted(SUPPORTED_SYMBOLS)


def _provider_name() -> str:
    from cas_forex.config import config

    provider = str(getattr(config, "market_data_provider", "yfinance")).upper()
    if provider == "OANDA" and getattr(config, "oanda_api_key", None):
        return "oanda"
    return "yfinance"


def _build_window(symbol: str, timeframe: str, bars: int) -> dict[str, Any]:
    connector = get_connector()
    raw_candles = connector.fetch_historical(symbol, bars=bars, timeframe=timeframe)
    snapshot = connector.fetch_snapshot(symbol)

    candles = [
        {
            "time": c.get("timestamp", ""),
            "open": c.get("open", 0.0),
            "high": c.get("high", 0.0),
            "low": c.get("low", 0.0),
            "close": c.get("close", 0.0),
        }
        for c in raw_candles
    ]

    quote = {
        "bid": snapshot.bid,
        "ask": snapshot.ask,
        "mid": round((snapshot.bid + snapshot.ask) / 2.0, 5),
        "spread": snapshot.spread,
        "is_market_open": snapshot.is_market_open,
        "session": snapshot.session,
        "timestamp": snapshot.timestamp.isoformat(),
    }

    return {
        "report_kind": "cas_forex_chart_window",
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": len(candles),
        "candles": candles,
        "quote": quote,
        "source": _provider_name(),
        # No connected broker tick feed is running; this is delayed retail data.
        "live_feed": False,
        "feed_label": "near-real-time market data (delayed)",
    }


@router.get("/symbols")
async def get_symbols() -> dict[str, Any]:
    """Tradeable symbols + valid timeframes for the window selectors."""
    return {"symbols": _supported_symbols(), "timeframes": list(_VALID_TIMEFRAMES)}


@router.get("/window")
async def get_chart_window(
    symbol: str = Query(default="EUR/USD"),
    timeframe: str = Query(default="M5"),
    bars: int = Query(default=60, ge=5, le=400),
) -> dict[str, Any]:
    """OHLC candles + current quote for one symbol, TTL-cached ~20s."""
    symbol = symbol.upper()
    timeframe = timeframe.upper()
    if timeframe not in _VALID_TIMEFRAMES:
        timeframe = "M5"
    if symbol not in _supported_symbols():
        return {
            "report_kind": "cas_forex_chart_window",
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": 0,
            "candles": [],
            "quote": None,
            "source": _provider_name(),
            "live_feed": False,
            "feed_label": "unsupported symbol",
            "error": f"Unsupported symbol {symbol}. Supported: {_supported_symbols()}",
        }

    key = (symbol, timeframe, int(bars))
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached is not None and cached[0] > now:
        payload = dict(cached[1])
        payload["cached"] = True
        return payload

    payload = _build_window(symbol, timeframe, int(bars))
    _CACHE[key] = (now + _TTL_SECONDS, payload)
    out = dict(payload)
    out["cached"] = False
    return out
