"""Market data connector - MT5 terminal, OANDA REST API, and yfinance fallback."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import re
from typing import Any, List, Optional

import requests  # type: ignore

from cas_forex.broker.mt5_bridge import MT5_INIT_TIMEOUT_MS, _add_local_mt5_deps
from cas_forex.instruments import (
    broker_symbol,
    default_mid,
    price_unit_size,
    round_price,
    yahoo_ticker,
)
from cas_forex.schemas.forecast import pip_multiplier as _pip_for
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.config import config
from cas_forex.time_utils import utc_now


class MarketDataConnector(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        """Fetch current market snapshot for a symbol."""
        ...

    @abstractmethod
    def fetch_historical(
        self, symbol: str, bars: int = 100, timeframe: str = "M5"
    ) -> List[dict]:
        """Fetch historical OHLCV candles."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the data provider is reachable."""
        ...


def _yf_period_for_interval(yf_interval: str) -> str:
    """A valid Yahoo `period` that covers a useful window for each interval.

    Yahoo only accepts named periods (1d/5d/1mo/3mo/...) and caps intraday
    history: 1m up to 7d, other intraday up to 60d, hourly up to ~730d.
    """
    return {
        "1m": "5d",
        "5m": "1mo",
        "15m": "1mo",
        "30m": "1mo",
        "1h": "3mo",
        "1d": "2y",
    }.get(yf_interval, "1mo")


class YFinanceConnector(MarketDataConnector):
    """Free market data via Yahoo Finance. No API key required."""

    TIMEFRAME_MAP = {"M1": "1m", "M5": "5m", "M15": "15m", "H1": "1h", "D1": "1d"}

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        ticker_str = yahoo_ticker(symbol)
        try:
            import yfinance as yf  # type: ignore
            ticker = yf.Ticker(ticker_str)
            info = ticker.info or {}
            fast = ticker.fast_info or {}
            bid = float(getattr(fast, "bid", 0) or info.get("bid", 0))
            ask = float(getattr(fast, "ask", 0) or info.get("ask", 0))
            price = float(getattr(fast, "last_price", 0) or info.get("regularMarketPrice", 0))

            if bid <= 0:
                bid = price * 0.9999
            if ask <= 0:
                ask = price * 1.0001

            spread = (ask - bid) * _pip_for(symbol)

            return MarketSnapshot(
                symbol=symbol,
                timestamp=utc_now(),
                bid=round_price(symbol, bid),
                ask=round_price(symbol, ask),
                spread=round(spread, 1),
                high=float(info.get("dayHigh", price)),
                low=float(info.get("dayLow", price)),
                close=price,
                timeframe="M5",
                session=self._detect_session(),
                is_market_open=self._is_market_open(symbol),
            )
        except Exception:
            return _closed_snapshot(symbol)

    def fetch_historical(
        self, symbol: str, bars: int = 100, timeframe: str = "M5"
    ) -> List[dict]:
        ticker_str = yahoo_ticker(symbol)
        try:
            import yfinance as yf
            ticker = yf.Ticker(ticker_str)
            yf_tf = self.TIMEFRAME_MAP.get(timeframe, "5m")
            # Yahoo requires a named period (1d/5d/1mo/...), NOT "<minutes>m", and
            # caps intraday history (1m<=7d, intraday<=60d). Pick a valid window
            # that comfortably covers `bars`, then take the last `bars` rows.
            df = ticker.history(period=_yf_period_for_interval(yf_tf), interval=yf_tf)
            if df is None or df.empty:
                return []
            candles = []
            for idx, row in df.tail(bars).iterrows():
                candles.append({
                    "timestamp": idx.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row.get("Volume", 0)),
                })
            return candles
        except Exception:
            return []

    def is_connected(self) -> bool:
        try:
            import yfinance as yf
            return True
        except ImportError:
            return False

    @staticmethod
    def _detect_session() -> str:
        now = utc_now()
        h = now.hour
        if 0 <= h < 8:
            return "ASIAN"
        elif 8 <= h < 12:
            return "LONDON"
        elif 12 <= h < 16:
            return "OVERLAP"
        elif 16 <= h < 21:
            return "NEW_YORK"
        return "ASIAN"

    @staticmethod
    def _is_market_open(symbol: str) -> bool:
        now = utc_now()
        wd = now.weekday()
        if wd >= 5:  # Weekend
            return False
        if wd == 4 and now.hour >= 22:  # Friday after 22:00 UTC = closed
            return False
        if wd == 6 and now.hour < 22:  # Sunday before 22:00 UTC = closed
            return False
        return True


class MT5TerminalMarketDataConnector(MarketDataConnector):
    """Read-only market data from the locally running MetaTrader 5 terminal.

    This connector reads broker-terminal candles and ticks through the official
    MT5 Python API. It never sends, modifies, or closes orders and it does not
    authorize live trading. If the terminal is missing or disconnected it simply
    returns no candles, letting WASTE fall back to the next evidence source.
    """

    broker_grade_market_truth = True
    read_only_market_data = True
    claim_boundary = (
        "MT5TerminalMarketDataConnector reads broker-terminal candles and tick "
        "spread only. It does not place orders, close positions, create broker "
        "ACCEPT, create owner ACCEPT, authorize live trading, deposit, withdraw, "
        "transfer funds, or automate payouts."
    )

    TIMEFRAME_CONSTANTS = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }
    SYMBOL_ALIASES = {
        "NAS100": ("NAS100", "USTEC", "US100", "NAS100.cash", "USTEC.cash", "NAS100m", "NAS100.i"),
        "US30": ("US30", "DJ30", "WS30", "US30.cash", "DJ30.cash", "US30m", "US30.i"),
        "SPX500": ("SPX500", "SP500", "US500", "SPX500.cash", "US500.cash", "SPX500m"),
        "XAU/USD": ("XAUUSD", "XAU/USD", "GOLD", "XAUUSD.cash", "XAUUSDm"),
    }

    def __init__(
        self,
        *,
        mt5_module: Any | None = None,
        mt5_path: Optional[str] = None,
    ) -> None:
        self._mt5 = mt5_module
        self.mt5_path = mt5_path if mt5_path is not None else config.mt5_path
        self._initialized = mt5_module is not None
        self.last_error = ""
        self.last_symbol_resolution: dict[str, Any] = {}
        self._symbol_cache: dict[str, str] = {}

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        if not self._connect():
            if not self.last_error:
                self.last_error = "MT5 terminal unavailable or not connected for snapshot"
            return _closed_snapshot(symbol)
        mt5_symbol = self._resolve_symbol(symbol)
        if not mt5_symbol:
            return _closed_snapshot(symbol)
        tick = self._mt5.symbol_info_tick(mt5_symbol)
        info = self._mt5.symbol_info(mt5_symbol)
        bid = _float_attr(tick, "bid", 0.0)
        ask = _float_attr(tick, "ask", 0.0)
        last = _float_attr(tick, "last", 0.0)
        if bid <= 0 and ask <= 0 and last > 0:
            bid = last
            ask = last
        if bid <= 0 or ask <= 0:
            return _closed_snapshot(symbol)
        spread = (ask - bid) * _pip_for(symbol)
        tick_time = _float_attr(tick, "time", 0.0)
        timestamp = (
            datetime.fromtimestamp(tick_time, tz=timezone.utc)
            if tick_time > 0
            else utc_now()
        )
        return MarketSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            bid=round_price(symbol, bid),
            ask=round_price(symbol, ask),
            spread=round(max(0.0, spread), 3),
            close=round_price(symbol, (bid + ask) / 2.0),
            timeframe="M5",
            volume_1m=_int_attr(tick, "volume", None),
            session=YFinanceConnector._detect_session(),
            is_market_open=_mt5_symbol_open(self._mt5, info, bid, ask),
        )

    def fetch_historical(
        self, symbol: str, bars: int = 100, timeframe: str = "M5"
    ) -> List[dict]:
        if not self._connect():
            if not self.last_error:
                self.last_error = "MT5 terminal unavailable or not connected for historical candles"
            return []
        mt5_symbol = self._resolve_symbol(symbol)
        if not mt5_symbol:
            return []
        tf = self._timeframe(timeframe)
        if tf is None:
            self.last_error = f"Unsupported MT5 timeframe {timeframe!r}"
            return []
        try:
            rates = self._mt5.copy_rates_from_pos(mt5_symbol, tf, 0, int(bars))
        except Exception as exc:
            self.last_error = f"copy_rates_from_pos failed: {type(exc).__name__}: {exc}"
            return []
        if rates is None:
            self.last_error = f"MT5 returned no rates for {symbol} resolved as {mt5_symbol}"
            return []
        candles: list[dict[str, Any]] = []
        for row in list(rates)[-int(bars):]:
            ts = _row_get(row, "time", 0)
            candles.append(
                {
                    "timestamp": _mt5_time_iso(ts),
                    "open": float(_row_get(row, "open", 0.0)),
                    "high": float(_row_get(row, "high", 0.0)),
                    "low": float(_row_get(row, "low", 0.0)),
                    "close": float(_row_get(row, "close", 0.0)),
                    "volume": float(
                        _row_get(row, "tick_volume", _row_get(row, "real_volume", 0.0))
                    ),
                    "spread": float(_row_get(row, "spread", 0.0)),
                }
            )
        return [candle for candle in candles if candle["open"] > 0 and candle["close"] > 0]

    def is_connected(self) -> bool:
        return self._connect()

    def _connect(self) -> bool:
        if self._mt5 is None:
            try:
                _add_local_mt5_deps()
                import MetaTrader5 as mt5  # type: ignore

                self._mt5 = mt5
            except Exception as exc:
                self.last_error = f"MetaTrader5 unavailable: {type(exc).__name__}: {exc}"
                return False
        if self._terminal_connected():
            self._initialized = True
            return True
        kwargs: dict[str, Any] = {"timeout": MT5_INIT_TIMEOUT_MS}
        if self.mt5_path:
            kwargs["path"] = self.mt5_path
        try:
            self._initialized = bool(self._mt5.initialize(**kwargs))
        except Exception as exc:
            self.last_error = f"MT5 initialize failed: {type(exc).__name__}: {exc}"
            self._initialized = False
            return False
        connected = self._terminal_connected() or self._initialized
        if not connected:
            self.last_error = f"MT5 initialize returned false: {_mt5_last_error(self._mt5)}"
        return connected

    def _terminal_connected(self) -> bool:
        if self._mt5 is None:
            return False
        try:
            info = self._mt5.terminal_info()
        except Exception:
            return False
        if info is None:
            return False
        connected = getattr(info, "connected", None)
        return bool(True if connected is None else connected)

    def _select_symbol(self, mt5_symbol: str) -> None:
        selector = getattr(self._mt5, "symbol_select", None)
        if callable(selector):
            try:
                selector(mt5_symbol, True)
            except Exception:
                pass

    def _resolve_symbol(self, symbol: str) -> str | None:
        canonical = str(symbol or "").strip()
        key = canonical.upper()
        if key in self._symbol_cache:
            return self._symbol_cache[key]

        configured = _configured_symbol_candidates(canonical)
        static_candidates = _dedupe(
            [
                *configured,
                broker_symbol(canonical),
                canonical,
                canonical.replace("/", ""),
                *self.SYMBOL_ALIASES.get(key, ()),
            ]
        )
        tried: list[str] = []
        for candidate in static_candidates:
            tried.append(candidate)
            if self._symbol_available(candidate):
                return self._cache_symbol(canonical, candidate, "STATIC_OR_OWNER_OVERRIDE", tried, [])

        discovered = self._discover_symbol_candidates(canonical)
        for candidate in discovered:
            if candidate in tried:
                continue
            tried.append(candidate)
            if self._symbol_available(candidate):
                return self._cache_symbol(canonical, candidate, "BROKER_SYMBOL_DISCOVERY", tried, discovered)

        self.last_symbol_resolution = {
            "canonical_symbol": canonical,
            "configured_candidates": configured,
            "tried_candidates": tried[:40],
            "discovered_candidates": discovered[:40],
            "selected_symbol": None,
            "resolution_source": "UNRESOLVED",
            "status": "UNRESOLVED",
        }
        self.last_error = (
            f"MT5 symbol unresolved for {canonical}; set CAS_FOREX_MT5_SYMBOL_OVERRIDES "
            "or make the symbol visible in Market Watch."
        )
        return None

    def _cache_symbol(
        self,
        canonical: str,
        selected: str,
        source: str,
        tried: list[str],
        discovered: list[str],
    ) -> str:
        self._symbol_cache[canonical.upper()] = selected
        self.last_symbol_resolution = {
            "canonical_symbol": canonical,
            "configured_candidates": _configured_symbol_candidates(canonical),
            "tried_candidates": tried[:40],
            "discovered_candidates": discovered[:40],
            "selected_symbol": selected,
            "resolution_source": source,
            "status": "RESOLVED",
        }
        return selected

    def _symbol_available(self, mt5_symbol: str) -> bool:
        if not mt5_symbol:
            return False
        self._select_symbol(mt5_symbol)
        try:
            return self._mt5.symbol_info(mt5_symbol) is not None
        except Exception:
            return False

    def _discover_symbol_candidates(self, symbol: str) -> list[str]:
        symbols_get = getattr(self._mt5, "symbols_get", None)
        if not callable(symbols_get):
            return []
        found: list[str] = []
        for pattern in _symbol_discovery_patterns(symbol):
            try:
                rows = symbols_get(pattern)
            except Exception:
                rows = None
            found.extend(_symbol_name(row) for row in (rows or []))
        if not found:
            try:
                rows = symbols_get()
            except Exception:
                rows = None
            found.extend(
                name
                for name in (_symbol_name(row) for row in (rows or []))
                if _symbol_name_matches(symbol, name)
            )
        return _rank_symbol_candidates(symbol, found)

    def _timeframe(self, timeframe: str) -> Any | None:
        const_name = self.TIMEFRAME_CONSTANTS.get(str(timeframe or "M5").upper())
        if const_name is None:
            return None
        return getattr(self._mt5, const_name, None)


class OANDARestConnector(MarketDataConnector):
    """OANDA REST v20 API connector. Requires API key and account ID."""

    BASE_URLS = {
        "practice": "https://api-fxpractice.oanda.com/v3",
        "live": "https://api-fxtrade.oanda.com/v3",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        environment: str = "practice",
    ):
        self.api_key = api_key or config.oanda_api_key
        self.account_id = account_id or config.oanda_account_id
        self.environment = environment or config.oanda_environment or "practice"
        self.base_url = self.BASE_URLS.get(self.environment, self.BASE_URLS["practice"])
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        if not self.api_key or not self.account_id:
            return _closed_snapshot(symbol)

        oanda_symbol = symbol.replace("/", "_")
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/pricing"
            params = {"instruments": oanda_symbol}
            resp = self._session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            prices = data.get("prices", [])
            if prices:
                p = prices[0]
                bid = float(p.get("bids", [{}])[0].get("price", 0))
                ask = float(p.get("asks", [{}])[0].get("price", 0))
                spread = (ask - bid) * _pip_for(symbol)
                return MarketSnapshot(
                    symbol=symbol,
                    timestamp=utc_now(),
                    bid=round(bid, 5),
                    ask=round(ask, 5),
                    spread=round(spread, 1),
                    session=self._detect_session(),
                    is_market_open=True,
                )
        except Exception:
            pass

        return _closed_snapshot(symbol)

    def fetch_historical(
        self, symbol: str, bars: int = 100, timeframe: str = "M5"
    ) -> List[dict]:
        if not self.api_key or not self.account_id:
            return []

        oanda_symbol = symbol.replace("/", "_")
        oanda_tf = timeframe.replace("M", "M").replace("H", "H").replace("D", "D")
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/instruments/{oanda_symbol}/candles"
            params = {"count": bars, "granularity": oanda_tf, "price": "MBA"}
            resp = self._session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            candles = []
            for c in data.get("candles", []):
                mid = c.get("mid", {})
                candles.append({
                    "timestamp": c.get("time", ""),
                    "open": float(mid.get("o", 0)),
                    "high": float(mid.get("h", 0)),
                    "low": float(mid.get("l", 0)),
                    "close": float(mid.get("c", 0)),
                    "volume": int(c.get("volume", 0)),
                })
            return candles
        except Exception:
            return []

    def is_connected(self) -> bool:
        if not self.api_key or not self.account_id:
            return False
        try:
            url = f"{self.base_url}/accounts/{self.account_id}"
            resp = self._session.get(url, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _detect_session() -> str:
        return YFinanceConnector._detect_session()


def get_connector() -> MarketDataConnector:
    """Factory: return the configured market data connector."""
    provider = config.market_data_provider.upper()
    if provider in {"MT5", "BROKER", "BROKER_MT5", "MT5_TERMINAL"}:
        return MT5TerminalMarketDataConnector()
    if provider == "OANDA" and config.oanda_api_key:
        return OANDARestConnector()
    return YFinanceConnector()


def _configured_symbol_candidates(symbol: str) -> list[str]:
    raw = str(getattr(config, "mt5_symbol_overrides", "") or "").strip()
    if not raw:
        return []
    key = str(symbol or "").strip().upper()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = _parse_symbol_override_pairs(raw)
    if not isinstance(parsed, dict):
        return []
    value = parsed.get(key) or parsed.get(str(symbol or "").strip())
    if value is None:
        return []
    if isinstance(value, str):
        return _dedupe([item.strip() for item in re.split(r"[|,]", value) if item.strip()])
    if isinstance(value, (list, tuple)):
        return _dedupe([str(item).strip() for item in value if str(item).strip()])
    return []


def _parse_symbol_override_pairs(raw: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for pair in re.split(r"[;\n]", raw):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        names = [item.strip() for item in value.split("|") if item.strip()]
        if key.strip() and names:
            out[key.strip().upper()] = names
    return out


def _symbol_discovery_patterns(symbol: str) -> list[str]:
    key = _symbol_key(symbol)
    if key == "NAS100":
        return ["*NAS*", "*USTEC*", "*US100*"]
    if key == "US30":
        return ["*US30*", "*DJ30*", "*WS30*", "*DOW*"]
    if key == "SPX500":
        return ["*SPX*", "*SP500*", "*US500*"]
    if key == "XAUUSD":
        return ["*XAU*", "*GOLD*"]
    return [f"*{key}*", f"*{symbol.replace('/', '')}*"]


def _rank_symbol_candidates(symbol: str, names: list[str]) -> list[str]:
    clean_target = _symbol_key(symbol)

    def score(name: str) -> tuple[int, int, str]:
        clean = _symbol_key(name)
        if clean == clean_target:
            bucket = 0
        elif clean.startswith(clean_target) or clean_target in clean:
            bucket = 1
        elif _symbol_name_matches(symbol, name):
            bucket = 2
        else:
            bucket = 9
        return bucket, len(name), name

    return [name for name in sorted(_dedupe(names), key=score) if name]


def _symbol_name_matches(symbol: str, name: str) -> bool:
    clean_name = _symbol_key(name)
    clean_symbol = _symbol_key(symbol)
    if clean_symbol and (clean_symbol in clean_name or clean_name in clean_symbol):
        return True
    aliases = MT5TerminalMarketDataConnector.SYMBOL_ALIASES.get(str(symbol or "").upper(), ())
    return any(_symbol_key(alias) in clean_name for alias in aliases)


def _symbol_name(row: Any) -> str:
    if row is None:
        return ""
    if isinstance(row, str):
        return row
    if isinstance(row, dict):
        return str(row.get("name") or row.get("symbol") or "")
    return str(getattr(row, "name", "") or getattr(row, "symbol", "") or "")


def _symbol_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _closed_snapshot(symbol: str) -> MarketSnapshot:
    mid = default_mid(symbol)
    pip_size = price_unit_size(symbol)
    return MarketSnapshot(
        symbol=symbol,
        timestamp=utc_now(),
        bid=round_price(symbol, mid - pip_size),
        ask=round_price(symbol, mid + pip_size),
        spread=2.0,
        high=mid,
        low=mid,
        close=mid,
        timeframe="M5",
        session=YFinanceConnector._detect_session(),
        is_market_open=False,
    )


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)


def _float_attr(obj: Any, key: str, default: float) -> float:
    value = getattr(obj, key, default) if obj is not None else default
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int_attr(obj: Any, key: str, default: Optional[int]) -> Optional[int]:
    value = getattr(obj, key, default) if obj is not None else default
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mt5_time_iso(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return ""
    if seconds <= 0:
        return ""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def _mt5_symbol_open(mt5: Any, info: Any, bid: float, ask: float) -> bool:
    if bid <= 0 or ask <= 0:
        return False
    disabled = getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", None)
    trade_mode = getattr(info, "trade_mode", None) if info is not None else None
    return disabled is None or trade_mode != disabled


def _mt5_last_error(mt5: Any) -> str:
    last_error = getattr(mt5, "last_error", None)
    if not callable(last_error):
        return "last_error unavailable"
    try:
        return str(last_error())
    except Exception as exc:
        return f"last_error failed: {type(exc).__name__}: {exc}"
