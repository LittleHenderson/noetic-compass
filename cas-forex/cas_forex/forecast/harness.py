"""Forecast Harness - structured model evidence before CAS audit."""

from __future__ import annotations

import importlib.util
import time
import uuid
from typing import Dict, List, Optional, Tuple

import numpy as np

from cas_forex.config import config
from cas_forex.forecast.models import TechnicalModel, TimeGPTModel
from cas_forex.schemas.forecast import Direction, ForecastProposal, ModelSource, pip_multiplier
from cas_forex.schemas.forecast_harness import (
    ForecastHarnessReport,
    ForecastHarnessVerdict,
    ForecastSignal,
    ForecastSignalStatus,
)


class ForecastHarness:
    """Runs optional model adapters and deterministic baselines with evidence."""

    def __init__(self, require_primary_models: bool = False, drift_breach: bool = False):
        self.require_primary_models = require_primary_models
        self.drift_breach = drift_breach
        self.technical = TechnicalModel()
        self.timegpt = TimeGPTModel()

    def propose(
        self,
        symbol: str,
        candles: List[dict],
        horizon: int = 60,
        timeframe: str = "H1",
    ) -> Tuple[Optional[ForecastProposal], ForecastHarnessReport]:
        baselines = self._baselines(candles)
        signals = [
            self._proposal_signal("technical", "local", self._call_technical, symbol, candles, horizon, timeframe, baselines),
            self._chronos_signal(symbol),
            self._timesfm_signal(symbol),
            self._proposal_signal("timegpt", "v2", self._call_timegpt, symbol, candles, horizon, timeframe, baselines),
        ]
        ok = [s for s in signals if s.status == ForecastSignalStatus.OK and s.direction is not None]
        reason_codes: list[str] = []

        if self.drift_breach:
            reason_codes.append("model_drift_breach")
            verdict = ForecastHarnessVerdict.LIVE_LOCKED
        elif self.require_primary_models and any(
            s.model in {"chronos", "timesfm"} and s.status == ForecastSignalStatus.UNAVAILABLE
            for s in signals
        ):
            reason_codes.append("primary_model_unavailable")
            verdict = ForecastHarnessVerdict.SUPPRESS
        elif not ok:
            reason_codes.append("no_model_signal")
            verdict = ForecastHarnessVerdict.SUPPRESS
        elif len(ok) < 2:
            reason_codes.append("single_model_only")
            verdict = ForecastHarnessVerdict.SUPPRESS
        elif len({s.direction for s in ok}) > 1:
            reason_codes.append("model_disagreement")
            verdict = ForecastHarnessVerdict.SUPPRESS
        elif any(self._interval_unstable(s) for s in ok):
            reason_codes.append("interval_instability")
            verdict = ForecastHarnessVerdict.SUPPRESS
        elif any((s.expected_move_pips or 0.0) <= 0.0 for s in ok):
            reason_codes.append("weak_edge")
            verdict = ForecastHarnessVerdict.SUPPRESS
        else:
            verdict = ForecastHarnessVerdict.PASS

        agreement = 0.0
        if ok:
            majority = max({d: sum(1 for s in ok if s.direction == d) for d in {s.direction for s in ok}}.values())
            agreement = majority / len(ok)

        report = ForecastHarnessReport(
            report_id=str(uuid.uuid4()),
            symbol=symbol,
            signals=signals,
            baseline_results=baselines,
            agreement_score=round(agreement, 4),
            interval_stable=not any(self._interval_unstable(s) for s in ok),
            drift_breach=self.drift_breach,
            verdict=verdict,
            reason_codes=reason_codes,
        )
        if verdict != ForecastHarnessVerdict.PASS:
            return None, report

        best = max(ok, key=lambda s: s.confidence)
        current = float(candles[-1]["close"])
        move = abs(best.expected_move_pips or 10.0) / pip_multiplier(symbol)
        if best.direction == Direction.LONG:
            sl = current - max(move, current * 0.002)
            tp = current + max(move * 2, current * 0.004)
        else:
            sl = current + max(move, current * 0.002)
            tp = current - max(move * 2, current * 0.004)
        return ForecastProposal(
            proposal_id=str(uuid.uuid4()),
            symbol=symbol,
            direction=best.direction,
            entry_price=round(current, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            confidence=best.confidence,
            model_source=ModelSource.ENSEMBLE,
            horizon_minutes=horizon,
            timeframe=timeframe,
            rationale=f"ForecastHarness pass: agreement={agreement:.2f}",
        ), report

    def _call_technical(self, symbol, candles, horizon, timeframe):
        return self.technical.predict(symbol, candles, horizon)

    def _call_timegpt(self, symbol, candles, horizon, timeframe):
        if not config.timegpt_api_key:
            return None
        return self.timegpt.predict(symbol, candles, horizon, timeframe=timeframe)

    def _proposal_signal(self, model, version, fn, symbol, candles, horizon, timeframe, baselines):
        started = time.perf_counter()
        try:
            proposal = fn(symbol, candles, horizon, timeframe)
        except Exception as exc:
            return ForecastSignal(
                model=model,
                model_version=version,
                status=ForecastSignalStatus.ERROR,
                error=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        latency = round((time.perf_counter() - started) * 1000, 2)
        if proposal is None:
            status = ForecastSignalStatus.UNAVAILABLE if model == "timegpt" and not config.timegpt_api_key else ForecastSignalStatus.NO_SIGNAL
            return ForecastSignal(model=model, model_version=version, status=status, latency_ms=latency)
        move = proposal.reward_pips
        return ForecastSignal(
            model=model,
            model_version=version,
            status=ForecastSignalStatus.OK,
            direction=proposal.direction,
            confidence=proposal.confidence,
            point_forecast=proposal.take_profit,
            expected_move_pips=round(move, 2),
            interval_low=min(proposal.stop_loss, proposal.take_profit),
            interval_high=max(proposal.stop_loss, proposal.take_profit),
            baseline_comparison=baselines,
            latency_ms=latency,
        )

    def _chronos_signal(self, symbol: str) -> ForecastSignal:
        if importlib.util.find_spec("chronos") is None and importlib.util.find_spec("chronos_forecasting") is None:
            return ForecastSignal(
                model="chronos",
                model_version="chronos-2-or-bolt",
                status=ForecastSignalStatus.UNAVAILABLE,
                error="chronos optional dependency unavailable",
            )
        return ForecastSignal(
            model="chronos",
            model_version="chronos-2-or-bolt",
            status=ForecastSignalStatus.NO_SIGNAL,
            error="chronos adapter dependency present but inference worker not configured",
        )

    def _timesfm_signal(self, symbol: str) -> ForecastSignal:
        if importlib.util.find_spec("timesfm") is None:
            return ForecastSignal(
                model="timesfm",
                model_version="2.5-compatible",
                status=ForecastSignalStatus.UNAVAILABLE,
                error="timesfm optional dependency unavailable",
            )
        return ForecastSignal(
            model="timesfm",
            model_version="2.5-compatible",
            status=ForecastSignalStatus.NO_SIGNAL,
            error="timesfm adapter dependency present but inference worker not configured",
        )

    @staticmethod
    def _baselines(candles: List[dict]) -> Dict[str, float]:
        if not candles:
            return {"no_trade": 0.0}
        closes = [float(c["close"]) for c in candles]
        current = closes[-1]
        ma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else current
        high20 = max(closes[-20:]) if len(closes) >= 20 else current
        low20 = min(closes[-20:]) if len(closes) >= 20 else current
        volatility = float(np.std(closes[-20:])) if len(closes) >= 20 else 0.0
        return {
            "last_price": current,
            "moving_average": ma20,
            "breakout_high": high20,
            "breakout_low": low20,
            "volatility_filter": volatility,
            "no_trade": 0.0,
        }

    @staticmethod
    def _interval_unstable(signal: ForecastSignal) -> bool:
        if signal.interval_low is None or signal.interval_high is None:
            return False
        return signal.interval_low >= signal.interval_high
