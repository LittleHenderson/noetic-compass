"""Forecast Integrity Gate — RPM and Lacunarity for CAS Forex.

CAS Definitions from TKS v7.4 FULL_CORRECTED (Def 6.31, Thm 6.41):

  RPM = sequential/logical dependency chain (D→W→P).
        "Are prerequisites in the correct sequence?"

  Lacunarity (Definition 6.31):
    Λ_ε(A) = Var(µ_ε) / E[µ_ε]² + 1 = E[µ_ε²] / E[µ_ε]²
    where µ_ε(x) = |A ∩ B_ε(x)| is the local mass at scale ε.
    Λ = 1 → homogeneous density. Λ > 1 → gappy/clustered structure.
    "Measures gappiness/heterogeneity of density beyond what dimension alone captures."
    Two sets can have same dimension but different lacunarity.

  Lacunarity-Noetic Correspondence (Theorem 6.41):
    (A) Entropy-lacunarity: L(AS) = exp(α(σ)·H(p)/λ) · L₀
    (B) Periodicity in noetic sequence → log-periodic lacunarity
    (C) Uniform noetic sampling → lacunarity → 1 (minimum gappiness)
    (D) Clustering (repeated noetics) → high lacunarity: L ∝ 1 + c·κ²

  Leakage = prerequisite PRESENT but producing wrong product.
  Limiting Reagent = proportional bottleneck among present prerequisites.

Applied to Forex:
  RPM gate: Checks D→W→P chain completeness (Data→Direction→Entry/Risk/Confidence).
  Lacunarity gate: Gliding-box variance/mean² of local evidence density across
    the price/indicator state space. Rising Λ = growing gappiness in forecast support.
  Leakage check: Detects look-ahead bias, overfitting, high confidence from thin data.
  Limiting Reagent: Identifies which evidence factor most constrains forecast quality.
"""

from typing import Dict, List, Optional

import numpy as np

from cas_forex.config import config
from cas_forex.schemas.forecast import ForecastProposal, pip_multiplier
from cas_forex.schemas.market import MarketSnapshot


class ForecastIntegrityResult:
    """Result of RPM/Lacunarity/Leakage/LimitingReagent checks on a forecast."""

    def __init__(
        self,
        rpm_chain_intact: bool = True,
        rpm_break_step: Optional[str] = None,
        rpm_completeness: float = 1.0,
        lacunarity_score: float = 0.0,
        lacunarity_voids: Optional[List[str]] = None,
        leakage_detected: bool = False,
        leakage_source: Optional[str] = None,
        limiting_reagent: Optional[str] = None,
        limiting_impact: float = 0.0,
    ):
        self.rpm_chain_intact = rpm_chain_intact
        self.rpm_break_step = rpm_break_step
        self.rpm_completeness = rpm_completeness
        self.lacunarity_score = lacunarity_score
        self.lacunarity_voids = lacunarity_voids or []
        self.leakage_detected = leakage_detected
        self.leakage_source = leakage_source
        self.limiting_reagent = limiting_reagent
        self.limiting_impact = limiting_impact

    @property
    def is_clean(self) -> bool:
        return (
            self.rpm_chain_intact
            and self.lacunarity_score < 0.3
            and not self.leakage_detected
        )

    def to_dict(self) -> dict:
        return {
            "rpm_chain_intact": self.rpm_chain_intact,
            "rpm_break_step": self.rpm_break_step,
            "rpm_completeness": round(self.rpm_completeness, 4),
            "lacunarity_score": round(self.lacunarity_score, 4),
            "lacunarity_voids": self.lacunarity_voids,
            "leakage_detected": self.leakage_detected,
            "leakage_source": self.leakage_source,
            "limiting_reagent": self.limiting_reagent,
            "limiting_impact": round(self.limiting_impact, 4),
        }


class ForecastIntegrityGate:
    """Applies CAS RPM and Lacunarity checks to forecast proposals.

    RPM (prerequisite chain) for forex:
      D (Data):        Market data is present and valid
      W (Will/Dir):    Direction signal has supporting evidence
      P (Purpose):     Entry/exit/target are logically derived from D and W

    Lacunarity (void detection):
      Checks for missing evidence that should be present:
      - Missing volatility context (ATR)
      - Missing spread/session check
      - Missing baseline comparison
      - Missing confidence calibration

    Leakage (signal validity):
      Checks if the signal might be based on:
      - Look-ahead bias (using future data)
      - Noise (low SNR)
      - Overfitting (too many indicators agreeing perfectly)

    Limiting Reagent (bottleneck):
      Identifies which evidence component most constrains forecast quality.
    """

    # RPM chain steps in order (D → W → P)
    RPM_CHAIN = ["data", "direction", "entry_exit", "risk_reward", "confidence"]

    # Required evidence fields for lacunarity check
    REQUIRED_EVIDENCE = [
        "atr_14",
        "spread_pips",
        "session",
        "baseline_comparison",
        "model_agreement",
    ]

    def evaluate(
        self,
        proposal: ForecastProposal,
        snapshot: Optional[MarketSnapshot] = None,
        candles: Optional[List[dict]] = None,
        atr: Optional[float] = None,
        baselines: Optional[Dict[str, float]] = None,
    ) -> ForecastIntegrityResult:
        """Run all four integrity checks on a forecast proposal.

        Returns ForecastIntegrityResult with detailed findings.
        """

        # --- Lacunarity Check (void detection) ---
        lac_voids, lac_score = self._check_lacunarity(
            proposal, snapshot, candles, atr, baselines
        )

        # --- RPM Check (prerequisite chain) ---
        rpm_intact, rpm_break, rpm_comp = self._check_rpm_chain(
            proposal, snapshot, atr, lac_voids
        )

        # --- Leakage Check (signal validity) ---
        leakage, leak_src = self._check_leakage(proposal, candles)

        # --- Limiting Reagent (bottleneck) ---
        lim_reagent, lim_impact = self._find_limiting_reagent(
            proposal, snapshot, atr, lac_voids
        )

        return ForecastIntegrityResult(
            rpm_chain_intact=rpm_intact,
            rpm_break_step=rpm_break,
            rpm_completeness=rpm_comp,
            lacunarity_score=lac_score,
            lacunarity_voids=lac_voids,
            leakage_detected=leakage,
            leakage_source=leak_src,
            limiting_reagent=lim_reagent,
            limiting_impact=lim_impact,
        )

    def _check_rpm_chain(
        self,
        proposal: ForecastProposal,
        snapshot: Optional[MarketSnapshot],
        atr: Optional[float],
        lacunarity_voids: List[str],
    ) -> tuple:
        """Check RPM prerequisite chain: D → W → P.

        Returns: (chain_intact, break_step, completeness)
        """
        chain_status = {}

        # D: Data check
        has_data = snapshot is not None and snapshot.bid > 0
        chain_status["data"] = has_data

        # W: Direction/Will check
        has_direction = (
            proposal.direction is not None
            and proposal.confidence >= config.min_forecast_confidence
        )
        chain_status["direction"] = has_direction

        # P1: Entry/Exit check
        has_entry_exit = (
            proposal.entry_price > 0
            and proposal.stop_loss > 0
            and proposal.take_profit > 0
        )
        if proposal.direction.value == "LONG":
            has_entry_exit = has_entry_exit and (
                proposal.stop_loss < proposal.entry_price < proposal.take_profit
            )
        else:
            has_entry_exit = has_entry_exit and (
                proposal.take_profit < proposal.entry_price < proposal.stop_loss
            )
        chain_status["entry_exit"] = has_entry_exit

        # P2: Risk/reward check
        risk = abs(proposal.entry_price - proposal.stop_loss)
        reward = abs(proposal.take_profit - proposal.entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        chain_status["risk_reward"] = rr_ratio >= 2.0  # 1:2 R:R means reward >= 2x risk

        # P3: Confidence
        chain_status["confidence"] = proposal.confidence >= 0.3

        # Find first break in chain order
        break_step = None
        for step in self.RPM_CHAIN:
            if not chain_status.get(step, False):
                break_step = step
                break

        completeness = sum(1 for v in chain_status.values() if v) / len(chain_status)
        return (break_step is None, break_step, completeness)

    def _check_lacunarity(
        self,
        proposal: ForecastProposal,
        snapshot: Optional[MarketSnapshot],
        candles: Optional[List[dict]],
        atr: Optional[float],
        baselines: Optional[Dict[str, float]],
    ) -> tuple:
        """Check for voids/absences in forecast evidence.

        Returns: (voids_list, lacunarity_score)
        """
        voids = []

        # ATR void
        if atr is None or atr <= 0:
            voids.append("atr_14")

        # Spread void
        if snapshot is None or snapshot.spread < 0:
            voids.append("spread_pips")

        # Session void
        if snapshot is None or snapshot.session == "UNKNOWN":
            voids.append("session")

        # Baseline comparison void
        if baselines is None or not baselines:
            voids.append("baseline_comparison")

        # Historical data void
        if candles is None or len(candles) < 10:
            voids.append("historical_data")

        # Model agreement (will be checked by ensemble, but flag if single-model)
        if proposal.model_source.value not in ("ENSEMBLE",):
            voids.append("model_agreement")

        # Rationale void
        if not proposal.rationale:
            voids.append("rationale")

        # Lacunarity: compute gliding-box Λ = E[µ²] / E[µ]² per TKS Def 6.31
        evidence_values = self._collect_evidence_values(
            proposal, snapshot, candles, atr, baselines
        )
        if len(evidence_values) < 4:
            score = 1.0
            voids.append("insufficient_evidence_for_lacunarity")
        else:
            vals = np.array(evidence_values, dtype=np.float64)
            v_min, v_max = vals.min(), vals.max()
            if v_max - v_min < 1e-9:
                score = 1.0
            else:
                score = self._gliding_box_lacunarity((vals - v_min) / (v_max - v_min))

        return voids, score

    @staticmethod
    def _collect_evidence_values(proposal, snapshot, candles, atr, baselines):
        vals = []
        if snapshot and snapshot.bid > 0:
            vals.extend([snapshot.bid, snapshot.ask, snapshot.mid])
            if snapshot.spread > 0:
                vals.append(snapshot.spread / pip_multiplier(snapshot.symbol))
            if snapshot.high and snapshot.low:
                vals.append(abs(snapshot.high - snapshot.low))
        if atr and atr > 0:
            vals.append(atr)
        if candles and len(candles) >= 2:
            closes = [c["close"] for c in candles]
            rets = [abs(closes[i]/closes[i-1]-1) for i in range(1, len(closes))]
            vals.extend(rets[-10:] if len(rets) >= 10 else rets)
        if baselines:
            vals.extend(v for v in baselines.values() if isinstance(v, (int,float)) and v > 0)
        vals.append(proposal.confidence)
        risk = abs(proposal.entry_price - proposal.stop_loss)
        reward = abs(proposal.take_profit - proposal.entry_price)
        if risk > 0:
            vals.append(reward / risk)
        return vals

    @staticmethod
    def _gliding_box_lacunarity(values: np.ndarray, box_size: float = 0.1) -> float:
        """Λ = E[µ²] / E[µ]² over gliding boxes (TKS Def 6.31/6.33)."""
        step = box_size / 2.0
        positions = np.arange(0.0, 1.0 - box_size + step/2, step)
        if len(positions) == 0:
            return 1.0
        masses = np.array([np.sum((values >= p) & (values < p + box_size)) for p in positions], dtype=np.float64)
        mean_m = masses.mean()
        if mean_m < 1e-9:
            return 1.0
        return float((masses * masses).mean() / (mean_m * mean_m))

    def _check_leakage(
        self,
        proposal: ForecastProposal,
        candles: Optional[List[dict]],
    ) -> tuple:
        """Check for signal leakage (look-ahead bias, noise, overfitting).

        Returns: (leakage_detected, source)
        """
        if candles is None or len(candles) < 20:
            return False, None

        closes = [c["close"] for c in candles]
        current = closes[-1]

        # Check 1: Entry price far from market = possible look-ahead
        price_deviation = abs(proposal.entry_price - current) / current
        if price_deviation > 0.02:  # More than 2% away
            return True, f"look_ahead_bias: entry deviates {price_deviation:.1%} from market"

        # Check 2: Perfect directional alignment with recent trend = possible overfit
        if len(closes) >= 10:
            recent_returns = [closes[i] / closes[i - 1] - 1 for i in range(-10, 0)]
            all_same_direction = all(
                (r > 0 and proposal.direction.value == "LONG")
                or (r < 0 and proposal.direction.value == "SHORT")
                for r in recent_returns
            )
            if all_same_direction and proposal.confidence > 0.9:
                return True, "overfitting: perfect alignment with recent trend"

        # Check 3: Confidence too high with thin data
        if len(candles) < 50 and proposal.confidence > 0.85:
            return True, "low_snr: high confidence with thin data"

        return False, None

    def _find_limiting_reagent(
        self,
        proposal: ForecastProposal,
        snapshot: Optional[MarketSnapshot],
        atr: Optional[float],
        lacunarity_voids: List[str],
    ) -> tuple:
        """Identify the most constraining factor for forecast quality.

        Returns: (limiting_reagent, impact_score)
        """
        candidates = {}

        # Spread as limiting reagent
        if snapshot and snapshot.spread > 5.0:
            candidates["spread"] = min(snapshot.spread / 20.0, 1.0)

        # ATR as limiting reagent (high volatility = less predictable)
        if atr and atr > 0:
            atr_pips = atr * pip_multiplier(proposal.symbol)
            if atr_pips > 50:
                candidates["volatility"] = min(atr_pips / 200.0, 1.0)

        # Thin data as limiting reagent
        if "historical_data" in lacunarity_voids:
            candidates["data_thinness"] = 0.8

        # Model confidence as limiting reagent
        if proposal.confidence < 0.5:
            candidates["low_confidence"] = 1.0 - proposal.confidence

        # Baseline as limiting reagent
        if "baseline_comparison" in lacunarity_voids:
            candidates["missing_baseline"] = 0.6

        if not candidates:
            return None, 0.0

        # Find the most impactful (highest score)
        limiting = max(candidates, key=candidates.get)
        return limiting, candidates[limiting]
