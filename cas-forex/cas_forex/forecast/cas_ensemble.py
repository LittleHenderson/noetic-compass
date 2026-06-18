"""CAS-Native Forecast — outputs proposals expressed in executable CAS notation.

Every proposal carries a cas_expression field using the real compiler format
(^k^D_{Fd}|R) so trades are CAS-compilable from the moment they're generated.
"""

import uuid
from typing import List, Optional

import numpy as np

from cas_forex.config import config
from cas_forex.schemas.forecast import ForecastProposal, Direction, ModelSource
from cas_forex.compiler_bridge import (
    CASCompilerBridge,
    market_to_cas_state,
    market_to_cas_relation,
    market_to_cas_recipe,
    get_bridge,
)
from cas_forex.forecast.integrity import ForecastIntegrityGate
from cas_forex.forecast.models import ForecastModel, TechnicalModel, TimeGPTModel


class CASNativeEnsemble:
    """Forecast ensemble that outputs CAS-native proposals.

    Every proposal includes:
      - cas_state: the market condition as a CAS state literal
      - cas_relation: the full dependency chain as a CAS relation
      - cas_recipe: the trade setup as a CAS v7.6 recipe (Θ/Ω)

    Only proposals that COMPILE through the real CAS compiler are returned.
    """

    def __init__(self):
        self.models: List[ForecastModel] = [TechnicalModel()]
        if config.timegpt_api_key:
            self.models.append(TimeGPTModel())
        self.bridge = get_bridge()
        self.integrity_gate = ForecastIntegrityGate()

    def propose(
        self,
        symbol: str,
        candles: List[dict],
        snapshot=None,
        horizon: int = 60,
        timeframe: str = "H1",
    ):
        """Generate CAS-native proposals from all models.

        Returns (best_proposal, cas_reports) where cas_reports contains
        compilation and integrity results for every model.
        """
        from cas_forex.schemas.market import MarketSnapshot
        if snapshot is None and candles:
            last = candles[-1]
            snapshot = MarketSnapshot(
                symbol=symbol, bid=last["close"] * 0.99995,
                ask=last["close"] * 1.00005, spread=0.5,
                close=last["close"], session="LONDON",
            )

        valid_proposals = []
        cas_reports = []

        for model in self.models:
            # TimeGPTModel takes timeframe; TechnicalModel doesn't
            try:
                raw = model.predict(symbol, candles, horizon, timeframe)
            except TypeError:
                raw = model.predict(symbol, candles, horizon)
            if raw is None:
                cas_reports.append({"model": model.__class__.__name__, "status": "NO_SIGNAL"})
                continue

            # Build CAS expression for this proposal
            cas_state = market_to_cas_state(snapshot, raw.direction)
            cas_relation = market_to_cas_relation(
                snapshot, raw.direction, raw.entry_price, raw.stop_loss, raw.take_profit,
            )
            cas_recipe = market_to_cas_recipe(snapshot, raw.direction, raw.confidence)

            # Compile through the real CAS compiler
            state_result = self.bridge.compile_expression(cas_state)
            relation_result = self.bridge.compile_expression(cas_relation)
            recipe_result = self.bridge.compile_expression(cas_recipe) if cas_recipe else None

            # Run RPM/Lacunarity integrity check
            integrity = self.integrity_gate.evaluate(
                raw, snapshot=snapshot, candles=candles,
            )

            report = {
                "model": model.__class__.__name__,
                "cas_state": cas_state,
                "cas_relation": cas_relation,
                "cas_recipe": cas_recipe,
                "state_compiled": state_result.valid,
                "relation_compiled": relation_result.valid,
                "relation_admissible": relation_result.admissible,
                "relation_descent_ok": relation_result.domain_descent_ok,
                "recipe_compiled": recipe_result.valid if recipe_result else None,
                "rpm_intact": integrity.rpm_chain_intact,
                "rpm_break": integrity.rpm_break_step,
                "lacunarity": round(integrity.lacunarity_score, 4),
                "leakage_detected": integrity.leakage_detected,
            }

            # Gate: must compile AND have intact RPM chain
            if not relation_result.valid:
                report["status"] = "REJECTED_COMPILER"
                cas_reports.append(report)
                continue

            if recipe_result is not None and not recipe_result.valid:
                report["status"] = "REJECTED_RECIPE_COMPILER"
                report["recipe_error"] = recipe_result.error
                cas_reports.append(report)
                continue

            if not integrity.rpm_chain_intact:
                report["status"] = "REJECTED_RPM_BREAK"
                cas_reports.append(report)
                continue

            if integrity.lacunarity_score > 2.0:
                report["status"] = "REJECTED_LACUNARITY"
                cas_reports.append(report)
                continue

            if integrity.leakage_detected:
                report["status"] = "REJECTED_LEAKAGE"
                cas_reports.append(report)
                continue

            # Passed all CAS gates! Stamp with CAS expression
            raw.rationale = cas_relation
            report["status"] = "ACCEPTED_CAS"
            cas_reports.append(report)
            valid_proposals.append(raw)

        if not valid_proposals:
            return None, cas_reports

        # Ensemble: majority direction vote
        longs = sum(1 for p in valid_proposals if p.direction == Direction.LONG)
        consensus_dir = Direction.LONG if longs >= len(valid_proposals) - longs else Direction.SHORT
        cp = [p for p in valid_proposals if p.direction == consensus_dir] or valid_proposals
        best = max(cp, key=lambda p: p.confidence)

        # Weight by model agreement
        agreement = len(cp) / len(valid_proposals)
        best.confidence = round(best.confidence * (0.5 + 0.5 * agreement), 4)
        best.model_source = ModelSource.ENSEMBLE
        best.rationale = market_to_cas_relation(
            snapshot, best.direction, best.entry_price, best.stop_loss, best.take_profit
        )

        return best, cas_reports
