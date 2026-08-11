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

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from cas_forex.config import config
from cas_forex.instruments import canonical_symbol
from cas_forex.market_data.connector import (
    MT5TerminalMarketDataConnector,
    YFinanceConnector,
    get_connector,
)

router = APIRouter()

# (symbol, timeframe, bars) -> (monotonic_expiry, payload)
_CACHE: dict[tuple[str, str, int], tuple[float, dict[str, Any]]] = {}
_TTL_SECONDS = 20.0
# The provider build continues in the isolated worker after this response
# budget expires. The cockpit gets a bounded warming/stale packet instead of
# waiting behind slow terminal IPC or a delayed retail-data request.
_BUILD_TIMEOUT_SECONDS = 1.5

# MT5's Python package performs blocking terminal IPC. Keep chart reads on one
# isolated worker so an unresponsive terminal cannot freeze the API event loop
# or consume the shared FastAPI thread pool used by Operator chat.
_BUILD_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cas-chart")
_IN_FLIGHT: dict[tuple[str, str, int], asyncio.Future[dict[str, Any]]] = {}

_VALID_TIMEFRAMES = ("M1", "M5", "M15", "H1", "D1")
_COMMON_MT5_TERMINAL_PATHS = (
    r"C:\Program Files\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Risen MT5 Terminal\terminal64.exe",
    r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files (x86)\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
)


def _supported_symbols() -> list[str]:
    from cas_forex.schemas.forecast import SUPPORTED_SYMBOLS

    return sorted(SUPPORTED_SYMBOLS)


def _provider_name(connector: Any | None = None) -> str:
    connector_name = type(connector).__name__.upper() if connector is not None else ""
    if isinstance(connector, MT5TerminalMarketDataConnector) or "MT5" in connector_name:
        return "mt5"
    if isinstance(connector, YFinanceConnector) or "YFINANCE" in connector_name:
        return "yfinance"
    if "OANDA" in connector_name:
        return "oanda"
    provider = str(getattr(config, "market_data_provider", "yfinance")).upper()
    if provider == "MT5":
        return "mt5"
    if provider == "OANDA" and getattr(config, "oanda_api_key", None):
        return "oanda"
    return "yfinance"


def _discover_mt5_terminal_path() -> str | None:
    configured = str(getattr(config, "mt5_path", "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    for candidate in _COMMON_MT5_TERMINAL_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def _mt5_market_truth_enabled(auto_path: str | None = None) -> bool:
    provider = str(getattr(config, "market_data_provider", "") or "").upper()
    if provider in {"MT5", "BROKER", "BROKER_MT5", "MT5_TERMINAL"}:
        return True
    if not bool(getattr(config, "prefer_mt5", True)):
        return False
    return bool(getattr(config, "mt5_login", 0) or getattr(config, "mt5_path", None) or auto_path)


def _has_connector_kind(candidates: list[Any], connector: Any) -> bool:
    return any(type(candidate) is type(connector) for candidate in candidates)


def _connector_candidates() -> list[Any]:
    candidates: list[Any] = []
    primary = get_connector()
    candidates.append(primary)
    mt5_auto_path = _discover_mt5_terminal_path()
    if _mt5_market_truth_enabled(mt5_auto_path):
        mt5_connector = MT5TerminalMarketDataConnector(mt5_path=mt5_auto_path)
        if not _has_connector_kind(candidates, mt5_connector):
            candidates.append(mt5_connector)
    if not any(isinstance(candidate, YFinanceConnector) for candidate in candidates):
        candidates.append(YFinanceConnector())
    return candidates


def _is_broker_grade_market_truth(connector: Any) -> bool:
    return bool(getattr(connector, "broker_grade_market_truth", False))


def _connector_feed_label(connector: Any, *, fallback_reason: str | None = None) -> str:
    if _is_broker_grade_market_truth(connector):
        label = "read-only MT5 broker-terminal candles and tick spread"
    elif isinstance(connector, YFinanceConnector):
        label = "near-real-time market data (delayed)"
    elif type(connector).__name__ == "OANDARestConnector":
        label = "account-scoped provider market data"
    else:
        label = "market data connector feed"
    if fallback_reason:
        return f"{label}; {fallback_reason}"
    return label


def _connector_detail(connector: Any) -> str | None:
    detail = str(getattr(connector, "last_error", "") or "").strip()
    return detail or None


def _snapshot_to_quote(snapshot: Any) -> dict[str, Any] | None:
    if snapshot is None or bool(getattr(snapshot, "synthetic_fallback", False)):
        return None
    return {
        "bid": snapshot.bid,
        "ask": snapshot.ask,
        "mid": round((snapshot.bid + snapshot.ask) / 2.0, 5),
        "spread": snapshot.spread,
        "is_market_open": snapshot.is_market_open,
        "session": snapshot.session,
        "timestamp": snapshot.timestamp.isoformat(),
    }


def _build_window(symbol: str, timeframe: str, bars: int) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    selected_connector: Any | None = None
    selected_candles: list[dict[str, Any]] = []
    selected_snapshot: Any | None = None
    best_snapshot: Any | None = None
    best_snapshot_connector: Any | None = None
    primary_connector_name = ""

    for index, connector in enumerate(_connector_candidates()):
        connector_name = type(connector).__name__
        if index == 0:
            primary_connector_name = connector_name
        try:
            raw_candles = connector.fetch_historical(symbol, bars=bars, timeframe=timeframe)
        except Exception as exc:
            attempts.append(
                {
                    "connector": connector_name,
                    "status": "HISTORICAL_ERROR",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
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
        try:
            snapshot = connector.fetch_snapshot(symbol)
        except Exception as exc:
            snapshot = None
            attempts.append(
                {
                    "connector": connector_name,
                    "status": "SNAPSHOT_ERROR",
                    "detail": f"{type(exc).__name__}: {exc}",
                    "candle_count": len(candles),
                }
            )
        else:
            snapshot_detail = _connector_detail(connector)
            attempts.append(
                {
                    "connector": connector_name,
                    "status": "CANDLES_FETCHED" if candles else "NO_CANDLES",
                    "candle_count": len(candles),
                    "detail": snapshot_detail,
                    "synthetic_fallback": bool(getattr(snapshot, "synthetic_fallback", False)),
                    "broker_grade_market_truth": _is_broker_grade_market_truth(connector),
                }
            )
            if best_snapshot is None and snapshot is not None and not bool(getattr(snapshot, "synthetic_fallback", False)):
                best_snapshot = snapshot
                best_snapshot_connector = connector
        if candles:
            selected_connector = connector
            selected_candles = candles
            selected_snapshot = snapshot
            break

    fallback_used = len({attempt.get("connector") for attempt in attempts if attempt.get("connector")}) > 1
    quote = _snapshot_to_quote(selected_snapshot) if selected_snapshot is not None else None
    if quote is None and best_snapshot is not None:
        quote = _snapshot_to_quote(best_snapshot)

    if selected_connector is None:
        source_connector = best_snapshot_connector
        source = _provider_name(source_connector)
        error = "; ".join(
            str(attempt.get("detail") or attempt.get("status"))
            for attempt in attempts
            if str(attempt.get("detail") or attempt.get("status")).strip()
        ) or f"No chart-capable connector produced candles for {symbol}."
        return {
            "report_kind": "cas_forex_chart_window",
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": 0,
            "candles": [],
            "quote": quote,
            "source": source,
            "live_feed": bool(source_connector and _is_broker_grade_market_truth(source_connector)),
            "feed_label": "no chart-capable candle feed",
            "error": error,
            "fallback_used": fallback_used,
            "connector_attempts": attempts,
        }

    source = _provider_name(selected_connector)
    source_detail = None
    if fallback_used and type(selected_connector).__name__ != primary_connector_name:
        primary_failure = next(
            (
                str(attempt.get("detail") or "").strip()
                for attempt in attempts
                if str(attempt.get("connector") or "").strip() == primary_connector_name
                and str(attempt.get("detail") or "").strip()
            ),
            "",
        )
        source_detail = primary_failure or "configured primary provider could not serve this symbol/timeframe"

    return {
        "report_kind": "cas_forex_chart_window",
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": len(selected_candles),
        "candles": selected_candles,
        "quote": quote,
        "source": source,
        "live_feed": _is_broker_grade_market_truth(selected_connector),
        "feed_label": _connector_feed_label(selected_connector, fallback_reason=source_detail),
        "fallback_used": fallback_used,
        "connector_attempts": attempts,
    }


def _finish_chart_build(
    key: tuple[str, str, int],
    future: asyncio.Future[dict[str, Any]],
) -> None:
    """Cache a late chart result and release the one-flight slot."""

    try:
        payload = future.result()
    except (asyncio.CancelledError, Exception):
        payload = None
    if isinstance(payload, dict):
        _CACHE[key] = (time.monotonic() + _TTL_SECONDS, payload)
    if _IN_FLIGHT.get(key) is future:
        _IN_FLIGHT.pop(key, None)


def _chart_refresh_timeout_payload(
    *,
    key: tuple[str, str, int],
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    """Fail soft without taking Operator chat or the rest of the API down."""

    cached = _CACHE.get(key)
    if cached is not None:
        payload = dict(cached[1])
        payload.update(
            {
                "cached": True,
                "stale": True,
                "refresh_timeout": True,
                "refresh_detail": (
                    "Chart refresh exceeded its control-plane response budget; "
                    "the last completed chart remains visible while refresh continues."
                ),
            }
        )
        return payload
    return {
        "report_kind": "cas_forex_chart_window",
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": 0,
        "candles": [],
        "quote": None,
        "source": _provider_name(),
        "live_feed": False,
        "feed_label": "chart refresh isolated from control plane",
        "cached": False,
        "stale": False,
        "refresh_timeout": True,
        "error": (
            "Chart refresh is still warming in its isolated worker. Operator chat "
            "and trading control remain "
            "available; this observational chart request did not block them."
        ),
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
    try:
        symbol = canonical_symbol(symbol)
    except ValueError:
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

    loop = asyncio.get_running_loop()
    future = _IN_FLIGHT.get(key)
    if future is not None and future.get_loop() is not loop:
        # Direct route tests may create a fresh event loop between calls.
        _IN_FLIGHT.pop(key, None)
        future = None
    if future is None:
        future = loop.run_in_executor(
            _BUILD_EXECUTOR,
            partial(_build_window, symbol, timeframe, int(bars)),
        )
        _IN_FLIGHT[key] = future
        future.add_done_callback(partial(_finish_chart_build, key))
    try:
        payload = await asyncio.wait_for(
            asyncio.shield(future),
            timeout=_BUILD_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return _chart_refresh_timeout_payload(
            key=key,
            symbol=symbol,
            timeframe=timeframe,
        )
    except Exception as exc:
        return {
            "report_kind": "cas_forex_chart_window",
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": 0,
            "candles": [],
            "quote": None,
            "source": _provider_name(),
            "live_feed": False,
            "feed_label": "chart refresh failed in isolated worker",
            "cached": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    _CACHE[key] = (time.monotonic() + _TTL_SECONDS, payload)
    out = dict(payload)
    out["cached"] = False
    return out
