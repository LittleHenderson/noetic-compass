"""Cascade Confidence-and-Break layer (CAS Forex DISCIPLINE + MEASUREMENT).

WHAT THIS IS (and, just as important, WHAT IT IS NOT)
=====================================================
This module is **discipline + measurement**, not a price forecaster. It carries
ZERO directional edge. It never outputs LONG/SHORT, never a price target, never
an entry/stop/take-profit, and never a sign of expected return. It takes a
prediction that *someone else* already made -- namely "the current market regime
will persist for N bars under gain ``beta``" -- and answers exactly two
questions:

  1. "How much can I trust this prediction the further out I project it?"
     -> the CONFIDENCE curve (a trust-decay weight, NOT a probability of being
        directionally correct, NOT a position size).
  2. "Where does this prediction structurally break?"
     -> the BREAKDOWN flag (cumulative gain runs away and the regime is at risk
        of inverting to its involution pair) and the OPEN-CAUSE flag (a scheduled
        macro event lands inside the horizon and overrides the predicted cause
        from outside the chain).

The "train of thought" framing (the owner's CAS artifacts): a train of thought is
a horizontal chain of CJTs, each ``^9`` effect becoming the next ``^8`` cause (an
involution pair). FORECAST projects that cascade forward and decays CONFIDENCE as
a running product of per-step certainty. Two things break a forecast:

  * a BREAKDOWN -- ``beta`` past a runaway threshold inverts the effect to its
    involution pair (trend -> reversal, high_vol <-> low_vol); and
  * an OPEN-CAUSE GAP -- an exogenous ``^8`` from *outside* the chain (a
    macro/news event) overrides the predicted cause; past it the forecast is
    dead reckoning.

HONESTY / ANTI-LEAKAGE GUARANTEES
=================================
* The cascade projection reads NO future price. ``projected_regime[k]`` is a
  deterministic function of ``(start_regime, beta, horizon, calendar timings)``.
  The ONLY price touch in the whole module is :func:`detect_regime` on the
  trailing closes to FIX the starting regime, and that function is already
  proven causal / prefix-stable (``tests/test_edge_oos.py``). No close at index
  past the anchor is ever read.
* Confidence depends only on ``beta`` + module decay constants + the step index
  ``k``. Appending arbitrary future bars after the anchor leaves every
  confidence value, the breakdown step, and the open-cause step unchanged.
* The calendar wiring reads ONLY ``event.scheduled_at_utc``,
  ``event.event_type``, and ``event.impact``. The surprise-content fields
  (``actual`` / ``expected`` / ``surprise_abs`` / ``surprise_pct`` /
  ``shock_active``) are FORBIDDEN -- they are the unknown outcome and reading
  them would be lookahead. Scheduled timing is publicly known ahead of time, so
  using only the schedule is explicitly NOT lookahead.
* No directional output: the involution flip after a breakdown is a confidence
  DEGRADATION signal ("the prediction is now as likely its opposite, trust it
  less"), never a buy/sell call.

Any tradeable edge must STILL come from a model with genuine out-of-sample
price-skill or from genuinely new information. This module adds none of its own.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from cas_forex.mtfa import tf_minutes
from cas_forex.regime_sim import REGIMES, detect_regime
from cas_forex.schemas.macro import MacroImpact
from cas_forex.time_utils import ensure_utc
from cas_forex.verifier.macro_gate import (
    MacroCalendarProvider,
    StaticMacroCalendarProvider,
)

# ---------------------------------------------------------------------------
# Module-level constants (all overridable per-call)
# ---------------------------------------------------------------------------

#: regime -> its involution-pair regime.  trend_up<->trend_down and
#: high_vol<->low_vol are the true directional/volatility opposites (mirrors the
#: CO-2<->CO-3 / CO-8<->CO-9 involution discipline in the CAS ontology and the
#: natural opposites in regime_sim.REGIMES).  The self-paired regimes
#: (range / vol_cluster / shock) have no directional opposite, so a "breakdown"
#: does not flip their label -- it still collapses confidence.
INVOLUTION: Dict[str, str] = {
    "trend_up": "trend_down",
    "trend_down": "trend_up",
    "high_vol": "low_vol",
    "low_vol": "high_vol",
    "range": "range",
    "vol_cluster": "vol_cluster",
    "shock": "shock",
}

#: Base per-step decay rate constant (the beta-neutral trust bleed).
LAMBDA0: float = 0.03

#: Beta sensitivity inside the exponent.  Higher beta amplifies per-step error,
#: so the running product of certainties falls faster.
BETA_GAIN: float = 0.15

#: Cumulative gain G_k = beta * k crossing this flags a breakdown (runaway).
RUNAWAY_THRESHOLD: float = 1.0

#: Per-step EXTRA confidence multiplier applied from the breakdown step onward.
#: In (0, 1]; default 0.5 makes the break visible while preserving monotonicity.
BREAKDOWN_PENALTY: float = 0.5

#: Per-step confidence multiplier applied from the open-cause step onward.
#: Small by design: past an exogenous cause the forecast is dead reckoning.
OPEN_CAUSE_COLLAPSE: float = 0.1

#: Numerical safety cap on beta so the exponent stays finite.
BETA_CAP: float = 10.0

#: The constant no-edge statement carried on every CascadeForecast.
NO_EDGE_DISCLAIMER: str = (
    "DISCIPLINE+MEASUREMENT ONLY. This carries NO directional-edge claim. It does "
    "not predict which way price will move, never emits LONG/SHORT, a price, an "
    "entry, stop, or target, and never claims a positive expected return. The "
    "confidence number is a trust-DECAY weight (how far a given prediction can be "
    "relied upon), NOT a probability of being directionally correct and NOT a "
    "position size. The cascade is a naive persistence-then-involution projection "
    "of the CURRENT regime; the involution flip on breakdown means 'the prediction "
    "is now as likely its opposite -- trust it less', a degradation marker, never a "
    "reversal trade signal. The open-cause flag uses only publicly-known scheduled "
    "event TIMING and asserts nothing about the surprise outcome. Any tradeable edge "
    "must still come from a model with genuine out-of-sample price-skill or new "
    "information; this module adds none."
)


# ---------------------------------------------------------------------------
# Pure helpers (no price, no future)
# ---------------------------------------------------------------------------


def per_step_certainty(
    beta: float, lam: float = LAMBDA0, k_beta: float = BETA_GAIN
) -> float:
    """Return the per-step trust-decay multiplicand ``exp(-(lam + k_beta*beta))``.

    The result lies in ``(0, 1)`` for ``beta >= 0`` and ``lam > 0`` (strictly
    less than 1, so the running product strictly decays), and is strictly
    decreasing in ``beta`` (faster decay at higher gain).

    NOTE: this is a trust-decay weight, NOT a probability of being directionally
    right. We make no directional claim here.
    """
    if beta < 0:
        raise ValueError("beta (gain) must be non-negative")
    b = min(beta, BETA_CAP)
    return math.exp(-(lam + k_beta * b))


def breakdown_step_for(
    beta: float, horizon: int, threshold: float = RUNAWAY_THRESHOLD
) -> Optional[int]:
    """First step ``k`` (1-indexed) where cumulative gain ``G_k = beta*k`` crosses
    ``threshold``; ``None`` if it never crosses inside ``[1, horizon]``.

    Cumulative gain is modelled as the simple, explicit, monotone-increasing form
    ``G_k = beta * k`` so the crossing is deterministic and trivially testable.
    With ``beta == 0`` the gain never accumulates, so there is no breakdown.
    The crossing step is ``ceil(threshold / beta)`` clamped to ``[1, horizon]``.
    """
    if horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if beta < 0:
        raise ValueError("beta (gain) must be non-negative")
    if beta == 0:
        # beta == 0 -> gain never accumulates -> no runaway ever.
        return None
    b = min(beta, BETA_CAP)
    step = math.ceil(threshold / b)
    if step < 1:
        step = 1
    if step > horizon:
        return None
    return step


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CascadeStep:
    """One projected step of the cascade.

    ``confidence`` is a trust-decay weight in ``(0, 1]`` -- NOT a directional
    probability.  ``projected_regime`` is the naive persistence (pre-breakdown)
    or its involution pair (post-breakdown); it is never a trade direction.
    """

    step: int
    projected_regime: str
    confidence: float
    breakdown_flag: bool
    open_cause_flag: bool
    cumulative_gain: float
    step_time: datetime
    matched_event_id: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "projected_regime": self.projected_regime,
            "confidence": self.confidence,
            "breakdown_flag": self.breakdown_flag,
            "open_cause_flag": self.open_cause_flag,
        }


@dataclass
class CascadeForecast:
    """A trust-and-break scoring of a GIVEN regime-persistence prediction.

    Holds the per-step cascade plus summary fields.  Carries no directional-edge
    claim (see :data:`NO_EDGE_DISCLAIMER`, attached as ``disclaimer``).
    """

    symbol: str
    timeframe: str
    start_regime: str
    beta: float
    horizon: int
    anchor_time: datetime
    steps: List[CascadeStep]
    breakdown_step: Optional[int]
    open_cause_step: Optional[int]
    involution_regime: str
    params: Dict[str, float]
    evidence: Dict[str, Any] = field(default_factory=dict)
    disclaimer: str = NO_EDGE_DISCLAIMER

    @property
    def confidence_curve(self) -> List[float]:
        """The list of per-step confidence weights (for monotonicity testing)."""
        return [s.confidence for s in self.steps]

    def as_dicts(self) -> List[Dict[str, Any]]:
        """Per-step list of exactly ``{step, projected_regime, confidence,
        breakdown_flag, open_cause_flag}`` as named in the task."""
        return [s.as_dict() for s in self.steps]

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe representation of the whole forecast (ISO-format times)."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_regime": self.start_regime,
            "beta": self.beta,
            "horizon": self.horizon,
            "anchor_time": ensure_utc(self.anchor_time).isoformat(),
            "involution_regime": self.involution_regime,
            "breakdown_step": self.breakdown_step,
            "open_cause_step": self.open_cause_step,
            "params": dict(self.params),
            "evidence": _json_safe(self.evidence),
            "disclaimer": self.disclaimer,
            "steps": [
                {
                    **s.as_dict(),
                    "cumulative_gain": s.cumulative_gain,
                    "step_time": ensure_utc(s.step_time).isoformat(),
                    "matched_event_id": s.matched_event_id,
                }
                for s in self.steps
            ],
        }


def _json_safe(obj: Any) -> Any:
    """Coerce datetimes inside evidence to ISO strings for JSON safety."""
    if isinstance(obj, datetime):
        return ensure_utc(obj).isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Core projection
# ---------------------------------------------------------------------------


def project_cascade(
    closes: Sequence[float],
    horizon: int,
    beta: float,
    *,
    start_regime: Optional[str] = None,
    anchor_time: Optional[datetime] = None,
    symbol: str = "EUR/USD",
    timeframe: str = "H1",
    calendar: Optional[MacroCalendarProvider] = None,
    min_impact: MacroImpact = MacroImpact.HIGH,
    currencies: Optional[Sequence[str]] = None,
    detect_window: int = 60,
    lam: float = LAMBDA0,
    k_beta: float = BETA_GAIN,
    runaway_threshold: float = RUNAWAY_THRESHOLD,
    breakdown_penalty: float = BREAKDOWN_PENALTY,
    open_cause_collapse: float = OPEN_CAUSE_COLLAPSE,
    **detect_kwargs: Any,
) -> CascadeForecast:
    """Project a regime-persistence cascade forward and score its trust + breaks.

    This does NOT forecast price direction.  It propagates the CURRENT regime
    forward (persistence), marks where the prediction self-inverts (breakdown)
    or is overridden from outside (open-cause), and decays a trust weight as a
    running product so the confidence curve is monotone non-increasing by
    construction.

    Parameters
    ----------
    closes:
        Trailing close series.  Used ONLY (via :func:`detect_regime`) to fix the
        starting regime when ``start_regime`` is None.  No close past the anchor
        is read.
    horizon:
        Number of forward bars to project (must be > 0).
    beta:
        Caller-supplied gain (>= 0).  Higher beta decays trust faster and reaches
        the runaway threshold sooner.
    start_regime:
        If given, used directly (must be in ``REGIMES``).  Otherwise detected
        from ``closes``.
    anchor_time:
        Timestamp of the LAST trailing bar (the present).  Coerced to UTC.  When
        None a fixed far-past epoch is used so the projection stays deterministic
        and no calendar event can spuriously match without a real present-time
        anchor.
    calendar:
        Macro calendar provider.  Defaults to :class:`StaticMacroCalendarProvider`.
        Only ``scheduled_at_utc`` / ``event_type`` / ``impact`` are read.
    min_impact:
        Minimum impact to treat an event as an open-cause (default HIGH).
    currencies:
        Optional currency filter (default: flag all qualifying events; the seed
        feed is USD-centric and USD is in every supported major).

    Returns
    -------
    CascadeForecast
    """
    # --- input validation ---------------------------------------------------
    if horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if beta < 0:
        raise ValueError("beta (gain) must be non-negative")

    # --- 1. resolve the starting regime (the ONLY price touch) --------------
    if start_regime is None:
        # detect_regime is causal / prefix-stable: it reads only the trailing
        # window of closes, never anything past the anchor.
        start_regime = detect_regime(list(closes), window=detect_window, **detect_kwargs)
    if start_regime not in REGIMES:
        raise ValueError(
            f"start_regime {start_regime!r} not in REGIMES {REGIMES!r}"
        )
    involution_regime = INVOLUTION[start_regime]

    # --- anchor time --------------------------------------------------------
    if anchor_time is None:
        # A deterministic, far-past anchor so no calendar event can match when
        # the caller did not supply a real present-time anchor.
        anchor = ensure_utc(datetime(1970, 1, 1))
    else:
        anchor = ensure_utc(anchor_time)

    tf_min = tf_minutes(timeframe)

    def step_time(k: int) -> datetime:
        # Pure arithmetic mapping of a forward step to wall-clock time.  Uses
        # only the (publicly-known-ahead) timeframe cadence and the anchor; it
        # never reads timestamps of not-yet-existing bars.
        return anchor + timedelta(minutes=k * tf_min)

    # --- 2. per-step base certainty (scalar; no future) ---------------------
    c_step = per_step_certainty(beta, lam=lam, k_beta=k_beta)
    # conf_base[k] = c_step ** k = exp(-(lam + k_beta*beta) * k), running PRODUCT
    # of identical per-step certainties.
    #   - strictly decreasing in k (each factor < 1) => monotone non-increasing.
    #   - strictly decreasing in beta for fixed k:
    #       d/dbeta log conf_base[k] = -k_beta * k < 0   (faster decay at higher beta)
    #   - conf_base[0] := 1.0 (the present, full certainty before any step).

    # --- 3 & 4. breakdown step ---------------------------------------------
    b = breakdown_step_for(beta, horizon, threshold=runaway_threshold)

    # --- 5. open-cause step from the calendar (timing only) -----------------
    cal = calendar or StaticMacroCalendarProvider()
    open_cause_step, matched_events = _scan_open_cause(
        cal,
        horizon=horizon,
        step_time=step_time,
        min_impact=min_impact,
        currencies=currencies,
    )
    # First matched event index -> per-step matched_event_id stamping.
    event_id_at_step: Dict[int, str] = {}
    for ev in matched_events:
        event_id_at_step.setdefault(ev["step"], ev["event_id"])

    # --- 6 & 7. assemble per-step records -----------------------------------
    steps: List[CascadeStep] = []
    for k in range(1, horizon + 1):
        conf_base = c_step ** k

        # breakdown penalty compounded from step b onward (1.0 if no breakdown).
        if b is not None and k >= b:
            bd_factor = breakdown_penalty ** (k - b + 1)
            breakdown_flag = True
            projected_regime = involution_regime
        else:
            bd_factor = 1.0
            breakdown_flag = False
            projected_regime = start_regime

        # open-cause collapse compounded from step o onward (1.0 if no event).
        if open_cause_step is not None and k >= open_cause_step:
            oc_factor = open_cause_collapse ** (k - open_cause_step + 1)
            open_cause_flag = True
        else:
            oc_factor = 1.0
            open_cause_flag = False

        # Combined confidence: a product of factors each in (0, 1] whose
        # exponents are non-decreasing in k => provably monotone non-increasing.
        conf = conf_base * bd_factor * oc_factor

        steps.append(
            CascadeStep(
                step=k,
                projected_regime=projected_regime,
                confidence=conf,
                breakdown_flag=breakdown_flag,
                open_cause_flag=open_cause_flag,
                cumulative_gain=beta * k,
                step_time=step_time(k),
                matched_event_id=event_id_at_step.get(k),
            )
        )

    params: Dict[str, float] = {
        "lam": lam,
        "k_beta": k_beta,
        "runaway_threshold": runaway_threshold,
        "breakdown_penalty": breakdown_penalty,
        "open_cause_collapse": open_cause_collapse,
        "c_step": c_step,
        "beta_cap": BETA_CAP,
    }
    evidence: Dict[str, Any] = {
        "matched_events": matched_events,
        "min_impact": min_impact.value,
        "tf_minutes": tf_min,
        "detect_window": detect_window,
        "anchor_time": anchor.isoformat(),
        "note": (
            "open-cause uses scheduled event TIMING only (publicly known ahead); "
            "surprise-content fields are never read."
        ),
    }

    return CascadeForecast(
        symbol=symbol,
        timeframe=timeframe,
        start_regime=start_regime,
        beta=beta,
        horizon=horizon,
        anchor_time=anchor,
        steps=steps,
        breakdown_step=b,
        open_cause_step=open_cause_step,
        involution_regime=involution_regime,
        params=params,
        evidence=evidence,
    )


def _scan_open_cause(
    calendar: MacroCalendarProvider,
    *,
    horizon: int,
    step_time: Callable[[int], datetime],
    min_impact: MacroImpact,
    currencies: Optional[Sequence[str]],
) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    """Find the first forward step whose ``(prev, this]`` interval contains a
    qualifying scheduled macro event.  Returns ``(open_cause_step, matched)``.

    Only ``scheduled_at_utc``, ``event_type``, and ``impact`` are read from each
    event.  The surprise-content fields ``actual`` / ``expected`` /
    ``surprise_abs`` / ``surprise_pct`` / ``shock_active`` (cas_forex/schemas/
    macro.py) are FORBIDDEN lookahead fields and MUST NOT be referenced here.
    """
    impact_rank = {MacroImpact.LOW: 0, MacroImpact.MEDIUM: 1, MacroImpact.HIGH: 2}
    min_rank = impact_rank[min_impact]
    cur_filter = {c.upper() for c in currencies} if currencies else None

    matched: List[Dict[str, Any]] = []

    # Precompute step boundary times once.  boundaries[k] == wall-clock at step k.
    boundaries = [step_time(k) for k in range(0, horizon + 1)]

    for event in calendar.events():
        # --- forbidden-field guard: read ONLY timing/type/impact ------------
        scheduled = ensure_utc(event.scheduled_at_utc)  # publicly known ahead -> not lookahead
        impact = event.impact  # impact tier is published on the schedule
        # event.actual / event.expected / event.surprise_abs / event.surprise_pct
        # / event.shock_active are FORBIDDEN here (unknown surprise content =
        # lookahead).  They are deliberately never referenced.
        if impact_rank[impact] < min_rank:
            continue
        if cur_filter is not None and getattr(event, "currency", "USD").upper() not in cur_filter:
            continue

        for k in range(1, horizon + 1):
            prev_t = boundaries[k - 1]
            this_t = boundaries[k]
            # Half-open interval so an event is attributed to exactly one step.
            if prev_t < scheduled <= this_t:
                matched.append(
                    {
                        "step": k,
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "impact": impact.value,
                        "scheduled_at_utc": scheduled.isoformat(),
                    }
                )
                break

    open_cause_step: Optional[int] = None
    if matched:
        matched.sort(key=lambda m: m["step"])
        open_cause_step = matched[0]["step"]

    return open_cause_step, matched
