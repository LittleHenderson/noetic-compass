"""Compounding governor (CAS Forex AMPLIFY layer) — the lacunarity / RPM / CJT /
cascade gate on WHEN and HOW MANY units to add to an ALREADY-CONFIRMED winner.

WHAT THIS IS (and, just as important, WHAT IT IS NOT)
=====================================================
This module governs money management ON TOP OF a confirmed edge. It decides
whether to ADD units to a live, floating-profitable position, HOLD it, or CUT it.
It CANNOT create expectancy. Compounding a zero- or negative-expectancy signal
still loses money in expectation; pyramiding only AMPLIFIES an edge that some
other layer already proved out-of-sample and that a FRESH edge-gate PASS confirms
is still live RIGHT NOW.

The honesty core is the ``fresh_edge_pass`` gate. Every single ADD must be backed
by a NEW edge-test PASS token — never the parent trade's inherited token. A
position that was authorized an hour ago has a stale edge; adding to it without a
fresh re-test would be compounding on faith, not on measured edge. So an ADD is
refused whenever ``fresh_edge_pass`` is False, no matter how green every other
governor reads. This is the same fail-closed discipline as the entry gate, applied
to every increment.

WHERE THE THREE GOVERNOR SCALARS COME FROM
==========================================
``decide`` takes three pre-computed scalars plus a CJT region string. They map
directly onto existing measurement modules (read those modules for the full
anti-leakage story; this module only consumes their outputs, it computes none of
them itself):

* ``cell_reliability`` (lacunarity / RPM) — from ``cas_forex.nested_lacunarity``.
  The bias-state map fills cells ``(symbol x timeframe x regime)`` with a MEASURED
  gap/non-gap verdict via the leak-free OOS null. A position sitting in a NON-GAP
  cell (``is_gap == False``) is in a pocket where SOME strategy cleared the null;
  a GAP cell has no measured edge. ``cell_reliability`` is the trust we place in
  the current cell: 1.0 for a confirmed non-gap, lower as gap-fraction rises.
  ``reliability_from_lacunarity`` below maps a ``TFCellResult`` (or a roll-up
  gap-fraction from ``nested_lacunarity_tf``) to this scalar. Honest default for
  price-only signals is LOW reliability (the map measures ALL_GAPS), so the
  governor sits on its hands until a real non-gap cell exists.

* ``cascade_confidence`` (cascade) — from ``cas_forex.cascade_forecast``. A
  ``CascadeForecast`` projects the current regime forward and decays a TRUST weight
  (NOT a directional probability) as a running product; it also flags BREAKDOWN
  (the regime is at risk of inverting to its involution pair) and OPEN-CAUSE (a
  scheduled macro event lands in the horizon). ``cascade_confidence`` is that
  trust weight at the step we care about; ``cascade_flags_breakdown`` reads the
  forecast's ``breakdown_step``. ``cascade_scalars`` below extracts both from a
  ``CascadeForecast``.

* ``cjt_region`` (CJT) — from ``cas_forex.regime_sim.classify_region`` /
  ``schemas.cjt.CjtRegion``. The CJT operating region of the live signal:
  ``'active'`` (trading, controlled drawdown, working as designed) is the only
  region in which we add; ``'breakdown'`` (deep drawdown / blow-up / regime
  inverting) forces a CUT; ``'cutoff'`` / ``'saturation'`` / ``'unknown'`` HOLD.

None of these scalars predict DIRECTION. Direction was decided upstream in
STRATEGIZE and confirmed by the edge gate; the governors here only gate and size.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

# These imports document the provenance of the three governor scalars and back the
# mapping helpers below. They are read-only; this module computes none of the
# leak-free measurements itself.
from cas_forex.regime_sim import lacunarity  # noqa: F401  (provenance: CJT/lacunarity)

# ---------------------------------------------------------------------------
# Tunable thresholds (all overridable per-call)
# ---------------------------------------------------------------------------

#: cell_reliability at or above this is "high" — the cell is a measured non-gap
#: pocket we trust enough to pyramid into.
RELIABILITY_HIGH: float = 0.6

#: cascade_confidence at or above this is "high" — the regime-persistence trust
#: weight has not decayed below the point where adding is defensible.
CASCADE_CONFIDENCE_HIGH: float = 0.55

#: floating_r below this (in R-multiples) is "deeply negative" — a CUT trigger
#: even if the CJT region has not yet printed breakdown.
DEEP_NEGATIVE_R: float = -0.8

#: CJT regions in which an ADD is permitted (only the working-as-designed region).
ADD_REGIONS: frozenset = frozenset({"active"})

#: CJT regions that force a CUT (hard-boundary failure / regime inverting).
CUT_REGIONS: frozenset = frozenset({"breakdown"})


# ---------------------------------------------------------------------------
# Shared data contract
# ---------------------------------------------------------------------------


@dataclass
class CompoundDecision:
    """Money-management verdict for an already-confirmed winner.

    ``action`` is one of ``'ADD'`` / ``'HOLD'`` / ``'CUT'``. ``add_units`` is the
    number of NEW units to pyramid on (0 for HOLD/CUT). ``reason`` is a short,
    honest explanation of which governor drove the verdict. This dataclass carries
    NO directional or expectancy claim: it only amplifies, holds, or trims an edge
    that was confirmed elsewhere.
    """

    action: str  # 'ADD' | 'HOLD' | 'CUT'
    add_units: int
    reason: str


# ---------------------------------------------------------------------------
# Provenance helpers — map measurement-module outputs to the three scalars
# ---------------------------------------------------------------------------


def reliability_from_lacunarity(source: Any) -> float:
    """Map a lacunarity output to the ``cell_reliability`` scalar in ``[0, 1]``.

    Accepts either:
      * a ``cas_forex.nested_lacunarity.TFCellResult`` (uses ``is_gap``):
        a confirmed NON-GAP cell -> 1.0, a GAP cell -> 0.0; or
      * a float gap-fraction (e.g. a value from ``nested_lacunarity_tf`` or
        ``regime_sim.lacunarity``): reliability = ``1 - gap_fraction`` clamped to
        ``[0, 1]``.

    Honest default: price-only signals measure ALL_GAPS (gap_fraction == 1.0), so
    reliability == 0.0 and the governor never adds — exactly the intended
    fail-closed behaviour until a real measured non-gap pocket exists.
    """
    is_gap = getattr(source, "is_gap", None)
    if is_gap is not None:
        return 0.0 if bool(is_gap) else 1.0
    try:
        frac = float(source)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, 1.0 - frac))


def cascade_scalars(forecast: Any, step: Optional[int] = None) -> tuple[float, bool]:
    """Extract ``(cascade_confidence, cascade_flags_breakdown)`` from a
    ``cas_forex.cascade_forecast.CascadeForecast``.

    ``cascade_confidence`` is the trust-decay weight at ``step`` (1-indexed). When
    ``step`` is None the FINAL step's confidence is used (the most-decayed, most
    conservative read). ``cascade_flags_breakdown`` is True iff the forecast has a
    ``breakdown_step`` at or before the step we read (the regime is projected to
    invert to its involution pair inside the horizon).

    This reads only the forecast's confidence curve and breakdown step; it makes
    no directional claim (the cascade module carries none).
    """
    curve = list(getattr(forecast, "confidence_curve", []) or [])
    breakdown_step = getattr(forecast, "breakdown_step", None)
    if not curve:
        return 0.0, breakdown_step is not None
    if step is None:
        idx = len(curve) - 1
        read_step = len(curve)
    else:
        read_step = max(1, min(int(step), len(curve)))
        idx = read_step - 1
    confidence = float(curve[idx])
    flags_breakdown = breakdown_step is not None and int(breakdown_step) <= read_step
    return confidence, flags_breakdown


# ---------------------------------------------------------------------------
# The governor
# ---------------------------------------------------------------------------


def _scaled_add_units(
    cell_reliability: float, current_units: int, max_units: int
) -> int:
    """Number of units to add, scaling with reliability, capped by headroom.

    Headroom = ``max_units - current_units`` (>= 1 when this is reached). Higher
    reliability authorizes a bigger increment, but never beyond headroom and never
    fewer than 1 (the ADD path is only entered when at least one unit is allowed).
    ``add_units = ceil(reliability * headroom)`` clamped to ``[1, headroom]``.
    """
    headroom = max_units - current_units
    if headroom <= 0:
        return 0
    rel = max(0.0, min(1.0, float(cell_reliability)))
    units = math.ceil(rel * headroom)
    if units < 1:
        units = 1
    if units > headroom:
        units = headroom
    return units


def decide(
    position: dict,
    cell_reliability: float,
    cascade_confidence: float,
    cjt_region: str,
    floating_r: float,
    *,
    max_units: int = 4,
    current_units: int = 1,
    fresh_edge_pass: bool,
    cascade_flags_breakdown: bool = False,
    reliability_high: float = RELIABILITY_HIGH,
    cascade_confidence_high: float = CASCADE_CONFIDENCE_HIGH,
    deep_negative_r: float = DEEP_NEGATIVE_R,
) -> CompoundDecision:
    """Decide whether to ADD / HOLD / CUT units on a CONFIRMED winner.

    Governs WHEN and HOW MANY units to compound a position whose edge was already
    confirmed out-of-sample upstream. It CANNOT create expectancy — pyramiding a
    zero/negative-expectancy signal still loses; this only amplifies a real,
    freshly re-tested edge and trims it when the structure breaks.

    Parameters
    ----------
    position:
        The live position dict (symbol/direction/units/etc.). Read for context /
        reason text only; the verdict is driven by the governor scalars.
    cell_reliability:
        Lacunarity / RPM trust in the current cell (``[0, 1]``); see
        :func:`reliability_from_lacunarity`. HIGH (>= ``reliability_high``) is a
        precondition for ADD.
    cascade_confidence:
        Cascade trust-decay weight (``[0, 1]``); see :func:`cascade_scalars`. HIGH
        (>= ``cascade_confidence_high``) is a precondition for ADD.
    cjt_region:
        CJT operating region of the live signal. ``'active'`` is the only ADD
        region; ``'breakdown'`` forces a CUT.
    floating_r:
        Current open profit in R-multiples (risk units). ADD requires it strictly
        positive; a deeply negative value (<= ``deep_negative_r``) forces a CUT.
    max_units / current_units:
        Pyramid cap and the units already on. ADD is impossible once
        ``current_units >= max_units``.
    fresh_edge_pass:
        REQUIRED. True iff a NEW edge-gate PASS token backs THIS add — never the
        parent's inherited token. Absent a fresh PASS, ADD is refused regardless
        of every other green signal (fail-closed re-test discipline).
    cascade_flags_breakdown:
        True iff the cascade forecast projects a breakdown (regime inverting) at
        or before the read step; forces a CUT.

    Returns
    -------
    CompoundDecision
    """
    # --- CUT first: structural-break signals dominate everything else --------
    region = (cjt_region or "").strip().lower()
    if region in CUT_REGIONS:
        return CompoundDecision(
            action="CUT",
            add_units=0,
            reason=f"CJT region '{region}' — structural breakdown; trim the position.",
        )
    if cascade_flags_breakdown:
        return CompoundDecision(
            action="CUT",
            add_units=0,
            reason="Cascade flags breakdown (regime inverting to involution pair); trim.",
        )
    if float(floating_r) <= float(deep_negative_r):
        return CompoundDecision(
            action="CUT",
            add_units=0,
            reason=(
                f"floating_r {float(floating_r):.2f}R <= deep-negative threshold "
                f"{float(deep_negative_r):.2f}R; trim to protect capital."
            ),
        )

    # --- ADD path: every condition must hold, including a FRESH edge PASS -----
    rel_high = float(cell_reliability) >= float(reliability_high)
    casc_high = float(cascade_confidence) >= float(cascade_confidence_high)
    in_profit = float(floating_r) > 0.0
    region_ok = region in ADD_REGIONS
    has_headroom = int(current_units) < int(max_units)

    if in_profit and rel_high and casc_high and region_ok and has_headroom:
        if not fresh_edge_pass:
            # Honesty core: never inherit the parent's edge token. No fresh PASS
            # => no ADD, even when every other governor reads green.
            return CompoundDecision(
                action="HOLD",
                add_units=0,
                reason=(
                    "All governors green but NO fresh edge-gate PASS for this add; "
                    "re-test required before compounding (fail-closed)."
                ),
            )
        units = _scaled_add_units(cell_reliability, int(current_units), int(max_units))
        return CompoundDecision(
            action="ADD",
            add_units=units,
            reason=(
                f"Fresh edge PASS + floating {float(floating_r):.2f}R, reliability "
                f"{float(cell_reliability):.2f}>= {float(reliability_high):.2f}, cascade "
                f"{float(cascade_confidence):.2f}>= {float(cascade_confidence_high):.2f}, "
                f"CJT '{region}'; amplify by {units} unit(s) "
                f"({current_units}->{int(current_units) + units}/{max_units})."
            ),
        )

    # --- HOLD: nothing breaking, but not all ADD preconditions met ------------
    blockers = []
    if not in_profit:
        blockers.append(f"floating_r {float(floating_r):.2f}R not > 0")
    if not rel_high:
        blockers.append(
            f"reliability {float(cell_reliability):.2f}< {float(reliability_high):.2f}"
        )
    if not casc_high:
        blockers.append(
            f"cascade {float(cascade_confidence):.2f}< {float(cascade_confidence_high):.2f}"
        )
    if not region_ok:
        blockers.append(f"CJT region '{region}' not in {sorted(ADD_REGIONS)}")
    if not has_headroom:
        blockers.append(f"units {current_units}>= max {max_units}")
    return CompoundDecision(
        action="HOLD",
        add_units=0,
        reason="HOLD — ADD preconditions unmet: " + "; ".join(blockers) + ".",
    )
