"""Forecast Ensemble - orchestrates multiple models with RPM/Lacunarity filtering."""
from typing import Dict, List, Optional, Tuple
import numpy as np
from cas_forex.config import config
from cas_forex.schemas.forecast import ForecastProposal, Direction, ModelSource
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.forecast.integrity import ForecastIntegrityGate
from cas_forex.forecast.models import ForecastModel, TechnicalModel, TimeGPTModel, ChronosModel


class ForecastEnsemble:
    """Runs all forecast models, filters by RPM/Lacunarity/Leakage, returns best."""

    def __init__(self):
        self.models: List[ForecastModel] = [TechnicalModel()]
        if config.timegpt_api_key:
            self.models.append(TimeGPTModel())
        # Chronos requires local GPU; add when available
        self.integrity_gate = ForecastIntegrityGate()

    def propose(
        self,
        symbol: str,
        candles: List[dict],
        snapshot: Optional[MarketSnapshot] = None,
        horizon: int = 60,
    ) -> Tuple[Optional[ForecastProposal], List[dict]]:
        proposals: List[ForecastProposal] = []
        reports: List[dict] = []
        atr = self._compute_atr(candles)
        baselines = self._compute_baselines(candles)

        for model in self.models:
            proposal = model.predict(symbol, candles, horizon)
            if proposal is None:
                continue

            integrity = self.integrity_gate.evaluate(
                proposal, snapshot=snapshot, candles=candles,
                atr=atr, baselines=baselines,
            )
            report = integrity.to_dict()

            if not integrity.rpm_chain_intact:
                report["status"] = "REJECTED_RPM_BREAK"
                reports.append(report)
                continue
            if integrity.lacunarity_score > 0.5:
                report["status"] = "REJECTED_HIGH_LACUNARITY"
                reports.append(report)
                continue
            if integrity.leakage_detected:
                report["status"] = "REJECTED_LEAKAGE"
                reports.append(report)
                continue

            report["status"] = "PASSED"
            reports.append(report)
            proposals.append(proposal)

        if not proposals:
            return None, reports

        # Majority direction vote
        longs = sum(1 for p in proposals if p.direction == Direction.LONG)
        consensus = Direction.LONG if longs >= len(proposals) - longs else Direction.SHORT

        cp = [p for p in proposals if p.direction == consensus] or proposals
        best = max(cp, key=lambda p: p.confidence)

        agreement = len(cp) / len(proposals)
        best.confidence = round(best.confidence * (0.5 + 0.5 * agreement), 4)
        best.model_source = ModelSource.ENSEMBLE
        return best, reports

    @staticmethod
    def _compute_atr(candles, period=14):
        if len(candles) < period + 1:
            return 0.0
        trs = []
        for i in range(1, len(candles)):
            h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return float(np.mean(trs[-period:]))

    @staticmethod
    def _compute_baselines(candles):
        if len(candles) < 2:
            return {}
        closes = [c["close"] for c in candles]
        cur = closes[-1]
        return {
            "last_price": cur,
            "ma20": float(np.mean(closes[-20:])) if len(closes) >= 20 else cur,
            "naive": closes[-2],
        }


_ensemble: Optional[ForecastEnsemble] = None


def get_ensemble() -> ForecastEnsemble:
    global _ensemble
    if _ensemble is None:
        _ensemble = ForecastEnsemble()
    return _ensemble
