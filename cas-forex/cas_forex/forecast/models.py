"""Forecast models: TimeGPT (API), Technical Indicators, Chronos (local)."""
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import numpy as np
from cas_forex.config import config
from cas_forex.schemas.forecast import ForecastProposal, Direction, ModelSource
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.forecast.integrity import ForecastIntegrityGate, ForecastIntegrityResult


class ForecastModel(ABC):
    @abstractmethod
    def predict(self, symbol: str, candles: List[dict], horizon: int = 60) -> Optional[ForecastProposal]:
        ...


class TimeGPTModel(ForecastModel):
    """Forecast using Nixtla TimeGPT v2 REST API (nixtlats incompatible with Python 3.14)."""

    FREQ_MAP = {"M1": "min", "M5": "5min", "M15": "15min", "M30": "30min",
                "H1": "h", "H4": "4h", "D1": "D", "W1": "W"}

    def predict(self, symbol, candles, horizon=60, timeframe="H1"):
        if not config.timegpt_api_key or len(candles) < 10:
            return None
        try:
            import requests
            closes = [c["close"] for c in candles]
            freq = self.FREQ_MAP.get(timeframe, "h")
            pred_horizon = max(1, horizon // {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
                                              "H1": 60, "H4": 240, "D1": 1440, "W1": 10080}.get(timeframe, 60))

            body = {
                "freq": freq, "h": pred_horizon, "model": "timegpt-1",
                "series": {"y": closes[-200:], "sizes": [min(len(closes), 200)]}
            }
            resp = requests.post(
                "https://api.nixtla.io/v2/forecast",
                json=body,
                headers={"Authorization": f"Bearer {config.timegpt_api_key}",
                         "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            forecast_vals = data.get("mean", [])
            if not forecast_vals:
                return None
            forecast_val = float(forecast_vals[-1])
            if forecast_val <= 0:
                return None

            current = closes[-1]
            pct = (forecast_val - current) / current * 100
            direction = Direction.LONG if forecast_val > current else Direction.SHORT
            confidence = min(abs(pct) / 2.0 + 0.3, 0.95)
            if confidence < config.min_forecast_confidence:
                return None
            sp = 0.005
            if direction == Direction.LONG:
                sl, tp = current * (1 - sp), forecast_val * 0.999
            else:
                sl, tp = current * (1 + sp), forecast_val * 1.001
            return ForecastProposal(
                proposal_id=str(uuid.uuid4()), symbol=symbol, direction=direction,
                entry_price=round(current, 5), stop_loss=round(sl, 5),
                take_profit=round(tp, 5), confidence=round(confidence, 4),
                model_source=ModelSource.TIMEGPT, horizon_minutes=horizon,
                timeframe=timeframe,
            )
        except Exception:
            return None


class TechnicalModel(ForecastModel):
    def predict(self, symbol, candles, horizon=60):
        if len(candles) < 20:
            return None
        closes = np.array([c["close"] for c in candles])
        cur = closes[-1]
        sma20 = float(np.mean(closes[-20:]))
        sma50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else sma20
        sma5 = float(np.mean(closes[-5:]))
        trend = 1.0 if sma5 > sma20 > sma50 else (-1.0 if sma5 < sma20 < sma50 else 0.0)
        if trend == 0:
            return None
        d = Direction.LONG if trend > 0 else Direction.SHORT
        conf = min(abs(sma5 - sma20) / cur * 1000, 0.7)
        if conf < config.min_forecast_confidence:
            return None
        sp = 0.005
        tpp = 0.008
        sl = round(cur * (1 - sp), 5) if d == Direction.LONG else round(cur * (1 + sp), 5)
        tp = round(cur * (1 + tpp), 5) if d == Direction.LONG else round(cur * (1 - tpp), 5)
        return ForecastProposal(
            proposal_id=str(uuid.uuid4()), symbol=symbol, direction=d,
            entry_price=round(cur, 5), stop_loss=sl, take_profit=tp,
            confidence=round(conf, 4), model_source=ModelSource.TECHNICAL,
            horizon_minutes=horizon,
            rationale=f"SMA5={sma5:.5f} SMA20={sma20:.5f} SMA50={sma50:.5f}"
        )


class ChronosModel(ForecastModel):
    def predict(self, symbol, candles, horizon=60):
        try:
            import importlib.util
            if importlib.util.find_spec("chronos") is None:
                return None
            return None  # Chronos local not wired yet - install chronos-forecasting
        except Exception:
            return None
