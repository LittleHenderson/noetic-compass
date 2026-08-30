"""rc0_routing.py -- the corrected route equation (RC-0 requirement 4).

    score_j,t = hard_mask(G_j,t)
              * rpm_ready_j,t
              * route_multiplier(region_j,t-1)
              * V_j,t / (r_j,t + epsilon)

- route_multiplier is a SCALAR in [0,1], a pure function of the LAST COMMITTED region
  (Z_{t-1}) -- the same-tick causal loop is closed by construction.
- The control action (RUN/CAP/SPLIT/REPAIR/QUARANTINE/HALT) is a SEPARATE typed value;
  it never enters the arithmetic (ControlAction raises if anyone tries).
- If every score is zero, normalization raises NoReadyCJT (code NO_READY_CJT) -- no
  divide-by-zero, ever. The caller (kernel) then opens an RPM repair subgoal or halts.
- Non-duplication contract (RC-0 requirement 6): V comes from Desire ABOVE its hard
  threshold; Wisdom appears ONLY in readiness; Power gates readiness (hard) and may
  modulate r_cap above threshold; policy is the hard mask, never a resistance.

CPU-only, deterministic.
"""
from __future__ import annotations

from rc0_types import (ControlAction, Governance, NoReadyCJT, RegionRecord, Resistance,
                       RPMState, FIRST_BLOCK_POLICY)

EPSILON = 1e-9

# scalar multiplier per last-committed region. CAP is expressed as a scalar here;
# the ACTION 'CAP'/'SPLIT'/... is decided separately by control_action().
ROUTE_MULTIPLIER = {
    "cutoff": 0.0,
    "active": 1.0,
    "saturation": 0.5,   # capped, still routable
    "breakdown": 0.0,
    "unassessed": 1.0,   # no evidence yet: do not silently starve a new expert
}


def route_multiplier(region_prev: str) -> float:
    """kappa in [0,1] from the PREVIOUS committed region only."""
    if region_prev not in ROUTE_MULTIPLIER:
        raise ValueError(f"unknown region {region_prev!r}")
    return ROUTE_MULTIPLIER[region_prev]


def control_action(region_prev: str, quarantined: bool) -> ControlAction:
    """The typed action for this expert this tick. Separate from all arithmetic."""
    if quarantined:
        return ControlAction.QUARANTINE
    return {
        "cutoff": ControlAction.REPAIR,
        "active": ControlAction.RUN,
        "saturation": ControlAction.CAP,       # or SPLIT, decided by the kernel
        "breakdown": ControlAction.QUARANTINE,
        "unassessed": ControlAction.RUN,
    }[region_prev]


def rpm_ready(rpm: RPMState, tau_d: float, tau_w: float, tau_p: float):
    """Hard readiness gate. Returns (ready: 0|1, first_block: str|None).

    FIRST_BLOCK follows the frozen D -> W -> P policy order. The typed reason is ALWAYS
    produced -- a scalar without the cause of failure is forbidden.
    """
    if not isinstance(rpm, RPMState):
        raise TypeError(f"rpm_ready requires an RPMState, got {type(rpm).__name__}")
    checks = (("DESIRE", rpm.desire, tau_d), ("WISDOM", rpm.wisdom, tau_w),
              ("POWER", rpm.power, tau_p))
    assert tuple(c[0] for c in checks) == FIRST_BLOCK_POLICY
    for name, value, tau in checks:
        if value < tau:
            return 0, name
    return 1, None


def drive_potential(rpm: RPMState, tau_d: float) -> float:
    """V: Desire's ABOVE-threshold magnitude (registered dual role of Desire).

    Below threshold, readiness already gates the route; V is defined as the surplus so
    the same deficiency is not counted twice.
    """
    if not isinstance(rpm, RPMState):
        raise TypeError(f"drive_potential requires an RPMState, got {type(rpm).__name__}")
    return max(0.0, rpm.desire - tau_d)


def route_score(governance: Governance, ready: int, region_prev: str,
                V: float, resistance: Resistance) -> float:
    """One expert's raw route score. Type-checked at every argument."""
    if not isinstance(governance, Governance):
        raise TypeError("route_score: governance must be a Governance")
    if ready not in (0, 1):
        raise TypeError("route_score: ready must be the hard gate value 0 or 1")
    if isinstance(V, (RPMState, ControlAction)):
        raise TypeError("route_score: V must be a scalar drive potential")
    if not isinstance(resistance, Resistance):
        raise TypeError(
            f"route_score: resistance must be a Resistance, got {type(resistance).__name__} "
            "(an RPMState is a prerequisite record, not a resistance)")
    kappa = route_multiplier(region_prev)
    return governance.effective_mask * ready * kappa * (V / (resistance.total + EPSILON))


def normalize_scores(scores: dict) -> dict:
    """scores: expert_id -> raw score. Returns the ALLOCATION simplex, or raises
    NoReadyCJT when the denominator would be zero. Never divides by zero."""
    total = sum(scores.values())
    if total <= 0.0:
        raise NoReadyCJT(
            "NO_READY_CJT: every route is masked, unready, starved, or quarantined; "
            "RPM must open a repair subgoal or the kernel must halt")
    return {k: v / total for k, v in scores.items()}
