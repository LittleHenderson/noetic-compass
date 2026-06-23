"""Market data connector - OANDA REST API and yfinance fallback."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import requests  # type: ignore

from cas_forex.instruments import default_mid, price_unit_size, round_price, yahoo_ticker
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
            df = ticker.history(period=f"{bars * 5}m", interval=yf_tf)
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
    if provider == "OANDA" and config.oanda_api_key:
        return OANDARestConnector()
    return YFinanceConnector()


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
