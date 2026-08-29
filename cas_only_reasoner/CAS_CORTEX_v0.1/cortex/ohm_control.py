"""The CAS-Ohm Native Attention CONTROL plane v0.1 (active, not just
a meter).

Implements the control protocol's executable core:
  - CASOhmBoardProfile: the versioned per-board calibration profile
  - MEASURE / DESIGN / DIAGNOSE: the three active equations
  - I_Q quantization (Q1-Q4, exact decimals, trend arrows)
  - lambda overload ratio and the split-before-clipping law
  - candidate-branch allocation with a fairness floor + child probes
  - learning as measured resistance reduction (before/after records)
  - CAS-GEM retrieval flow decisions (retrieve / compete / more-clue /
    anchor-reject)
  - the flow-region x semantic-outcome matrix with INDEPENDENT axes
  - CASOhmReadiness commitment packets

AUTHORITY LAW: these functions govern FLOW - budgets, floors, splits,
routing. None of them may decide truth, meaning, validity, or
permission, and none of them derives a semantic outcome from a flow
region (the classifier REQUIRES both as separate inputs).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class CASOhmBoardProfile:
    profile_id: str
    board_id: str
    board_version: str
    mode: str                      # native | neural_calibrated | behavioral_proxy
    v_range: tuple                 # (min, max)
    i_full_scale: float
    i_target_band: tuple           # (low, high)
    minimum_required_i: float
    overload_limit: float          # lambda ceiling before control acts
    residual_tolerance: float
    cutoff_i: float
    saturation_i: float
    effect_expectation: str
    fairness_floor: float = 0.1    # minimum branch budget share

    def calibration_digest(self) -> str:
        return _digest(self.__dict__)


# The live language-pipeline profile (authored, native mode).
LANGUAGE_PIPELINE_PROFILE = CASOhmBoardProfile(
    profile_id="lang_pipeline_native_v1",
    board_id="CAS_CORTEX_v0.1",
    board_version="0.1",
    mode="native",
    v_range=(0.0, 10.0),
    i_full_scale=6.0,
    i_target_band=(2.5, 6.0),
    minimum_required_i=1.0,
    overload_limit=1.0,
    residual_tolerance=0.5,
    cutoff_i=0.5,
    saturation_i=6.0,
    effect_expectation="typed semantic packet or typed refusal",
)


# ----------------------------------------------------------------------
# The three active equations.
def measure_i(v_drive: float, r_total: float) -> float:
    """MEASURE: how much attention will this path receive?"""
    return round(v_drive / r_total, 4)


def design_v(i_target: float, r_total: float) -> float:
    """DESIGN: what Drive produces the target flow? (a control law)"""
    return round(i_target * r_total, 4)


def diagnose_r(v_drive: float, i_observed: float) -> float:
    """DIAGNOSE: what effective constraint does observed flow imply?"""
    return round(v_drive / i_observed, 4)


# ----------------------------------------------------------------------
def quantize_iq(i_value: float, profile: CASOhmBoardProfile,
                previous_i: Optional[float] = None) -> Dict:
    """The guide's Q4 system: exact decimals, band, trend arrow."""
    i_q = round(10.0 * i_value / profile.i_full_scale, 2)
    i_q = max(0.0, min(10.0, i_q))
    if i_q < 2.5:
        band, budget = "Q1", "minimum_maintenance"
    elif i_q < 5.0:
        band, budget = "Q2", "exploratory"
    elif i_q < 7.5:
        band, budget = "Q3", "normal_working"
    else:
        band, budget = "Q4", "high_priority"
    trend = "→"
    if previous_i is not None:
        if i_value > previous_i + 1e-9:
            trend = "↑"
        elif i_value < previous_i - 1e-9:
            trend = "↓"
    return {"I_Q": i_q, "band": band, "budget_class": budget,
            "trend": trend,
            "display": f"I_Q = {i_q:.2f}{trend} [{band}]"}


# ----------------------------------------------------------------------
def overload(raw_demand: float, profile: CASOhmBoardProfile) -> Dict:
    """lambda = raw demand / full scale, with the control decision."""
    lam = round(raw_demand / profile.i_full_scale, 4)
    if lam <= 0.75:
        decision = "NORMAL"
    elif lam <= profile.overload_limit:
        decision = "NEAR_CAPACITY_WARNING"
    else:
        decision = "OVERLOAD_SPLIT_REQUIRED"
    return {"lambda": lam, "decision": decision,
            "note": "split into child goals or raise deliberate "
                    "constraint BEFORE the junction clips"
            if decision == "OVERLOAD_SPLIT_REQUIRED" else ""}


def overload_by_demand(raw_demand: float,
                       full_scale_demand: float) -> Dict:
    """Overload in DEMAND units (e.g. proposition count vs the
    board's per-turn capacity) - same lambda law, explicit unit."""
    lam = round(raw_demand / full_scale_demand, 4)
    if lam <= 0.75:
        decision = "NORMAL"
    elif lam <= 1.0:
        decision = "NEAR_CAPACITY_WARNING"
    else:
        decision = "OVERLOAD_SPLIT_REQUIRED"
    return {"lambda": lam, "decision": decision, "unit": "demand",
            "note": "split into child goals BEFORE the junction clips"
            if decision == "OVERLOAD_SPLIT_REQUIRED" else ""}


# ----------------------------------------------------------------------
def allocate_branches(branch_flows: Dict[str, float],
                      profile: CASOhmBoardProfile) -> Dict:
    """Normalize genuine-alternative branch flows to budget shares
    with a FAIRNESS FLOOR - a high-current early favorite can never
    erase alternatives before comparison. Child probes retained."""
    total = sum(branch_flows.values())
    if total <= 0:
        share = 1.0 / len(branch_flows)
        raw = {name: share for name in branch_flows}
    else:
        raw = {name: flow / total for name, flow in branch_flows.items()}
    floor = profile.fairness_floor
    floored = {name: max(share, floor) for name, share in raw.items()}
    norm = sum(floored.values())
    shares = {name: round(value / norm, 4)
              for name, value in floored.items()}
    child_probes = {
        name: {"I": flow,
               "region": ("cutoff" if flow < profile.cutoff_i
                          else "saturated" if flow >= profile.saturation_i
                          else "active")}
        for name, flow in branch_flows.items()}
    return {"shares": shares, "child_probes": child_probes,
            "fairness_floor": floor}


def parallel_health(branch_flows: Dict[str, float],
                    profile: CASOhmBoardProfile) -> Dict:
    """T5: the parent aggregate NEVER hides child failures. The
    aggregate may look healthy while one child saturates and another
    starves - health is decided from the CHILD probes."""
    probes = allocate_branches(branch_flows, profile)["child_probes"]
    aggregate_i = sum(branch_flows.values())
    unhealthy = {name: probe for name, probe in probes.items()
                 if probe["region"] != "active"}
    return {"aggregate_I": round(aggregate_i, 4),
            "aggregate_looks_healthy":
                profile.i_target_band[0] <= aggregate_i,
            "child_probes": probes,
            "healthy": not unhealthy,
            "unhealthy_children": unhealthy}


# ----------------------------------------------------------------------
def capability_resistance(p_cap: float) -> float:
    """The guide's capability mapping: higher capability, lower
    capability-derived resistance. Authored map: R_cap = 10 - P_cap
    on the 0-10 scale, floored above zero."""
    return round(max(0.2, 10.0 - p_cap), 4)


def learning_repair_record(p_cap_before: float, p_cap_after: float,
                           v_drive: float, r_other: float,
                           profile: CASOhmBoardProfile,
                           effect_before: str, effect_after: str) -> Dict:
    """T6: learning as a measured MECHANISM - capability rose,
    capability resistance fell, the path entered the active region,
    the effect type became correct. Never just 'test passed now'."""
    r_before = capability_resistance(p_cap_before)
    r_after = capability_resistance(p_cap_after)
    i_before = measure_i(v_drive, r_before + r_other)
    i_after = measure_i(v_drive, r_after + r_other)

    def region(i):
        if i < profile.cutoff_i:
            return "cutoff"
        if i >= profile.saturation_i:
            return "saturated"
        return "active"

    return {
        "before": {"P_cap": p_cap_before, "R_cap": r_before,
                   "I_pred": i_before, "region": region(i_before),
                   "effect_type": effect_before},
        "after": {"P_cap": p_cap_after, "R_cap": r_after,
                  "I_pred": i_after, "region": region(i_after),
                  "effect_type": effect_after},
        "mechanism": {
            "capability_increased": p_cap_after > p_cap_before,
            "resistance_fell": r_after < r_before,
            "entered_active": region(i_before) != "active"
            and region(i_after) == "active",
            "effect_corrected": effect_before != "intended"
            and effect_after == "intended",
        },
    }


# ----------------------------------------------------------------------
def retrieval_decision(candidate_flows: Dict[str, float],
                       anchor_conflicts: Dict[str, bool],
                       profile: CASOhmBoardProfile,
                       similarity_margin: float = 0.25) -> Dict:
    """T7 + section 11: memory retrieval as flow control.
    - one dominant flow: retrieve it
    - similar flows: keep BOTH as competing branches, ask for a clue
    - all below cutoff: NEEDS_MORE_CLUE
    - strong flow with an exact-anchor conflict: REJECT the semantic
      effect despite the flow (flow never overrides an anchor)."""
    viable = {name: flow for name, flow in candidate_flows.items()
              if flow >= profile.cutoff_i}
    if not viable:
        return {"decision": "NEEDS_MORE_CLUE", "retrieved": None,
                "competing": []}
    ranked = sorted(viable.items(), key=lambda kv: (-kv[1], kv[0]))
    best_name, best_flow = ranked[0]
    if anchor_conflicts.get(best_name):
        return {"decision": "ANCHOR_CONFLICT_REJECT",
                "retrieved": None,
                "note": f"candidate {best_name} has dominant flow "
                        f"{best_flow} but violates an exact anchor - "
                        f"flow never overrides an anchor",
                "competing": [name for name, _ in ranked[1:]]}
    if len(ranked) > 1 and best_flow - ranked[1][1] < similarity_margin:
        return {"decision": "AMBIGUOUS_ASK_FOR_CLUE", "retrieved": None,
                "competing": [name for name, _ in ranked[:2]],
                "note": "similar flows stay separate competing "
                        "branches; narratives are never merged"}
    return {"decision": "RETRIEVE", "retrieved": best_name,
            "competing": [name for name, _ in ranked[1:]]}


# ----------------------------------------------------------------------
FLOW_REGIONS = ("cutoff", "active", "saturated", "breakdown")
SEMANTIC_OUTCOMES = ("intended", "opposite", "off_axis", "unknown",
                     "verified", "contradicted")

DIAGNOSIS_MATRIX = {
    ("active", "intended"): "healthy",
    ("cutoff", "unknown"): "missing knowledge or blocked path",
    ("active", "off_axis"): "well-powered misunderstanding",
    ("saturated", "intended"): "correct but overloaded",
    ("saturated", "off_axis"): "confidently wrong and clipped",
    ("breakdown", "opposite"): "inversion",
}


def classify(flow_region: str, semantic_outcome: str) -> Dict:
    """The two-axis matrix. BOTH axes are REQUIRED inputs - this
    function cannot and will not derive the semantic outcome from the
    flow region (protocol section 13 prohibition)."""
    if flow_region not in FLOW_REGIONS:
        raise ValueError(f"unknown flow region {flow_region!r}")
    if semantic_outcome not in SEMANTIC_OUTCOMES:
        raise ValueError(f"unknown semantic outcome {semantic_outcome!r}")
    label = DIAGNOSIS_MATRIX.get((flow_region, semantic_outcome),
                                 f"{flow_region} + {semantic_outcome}")
    repair = None
    if flow_region == "active" and semantic_outcome in ("off_axis",
                                                        "opposite"):
        repair = ("semantic or topology repair - NEVER gain "
                  "adjustment (T8: a small residual does not mean "
                  "the answer is correct)")
    elif flow_region == "cutoff":
        repair = "supply the missing prerequisite or unblock the path"
    elif flow_region == "saturated":
        repair = "split the task or raise deliberate constraint"
    return {"flow_region": flow_region,
            "semantic_outcome": semantic_outcome,
            "diagnosis": label, "repair_class": repair}


# ----------------------------------------------------------------------
def readiness(profile: CASOhmBoardProfile, i_pred: float, i_obs: float,
              lambda_value: float, effect_type: str,
              child_probes_healthy: bool = True) -> Dict:
    """The CASOhmReadiness packet the commitment controller may
    require. Certifies ENERGIZATION - the checking machinery received
    enough flow, in range, not bypassed. NEVER certifies truth: the
    verifier does that separately."""
    residual = round(i_obs - i_pred, 4)
    conditions = {
        "region_active": i_obs >= profile.minimum_required_i
        and i_obs < profile.saturation_i,
        "residual_within_tolerance":
            abs(residual) <= profile.residual_tolerance,
        "not_overloaded": lambda_value <= profile.overload_limit,
        "effect_type_intended": effect_type == "intended",
        "child_probes_healthy": child_probes_healthy,
    }
    return {"ok": all(conditions.values()),
            "conditions": conditions,
            "I_pred": i_pred, "I_obs": i_obs, "residual": residual,
            "lambda": lambda_value,
            "certifies": "energization only - never truth",
            "profile": profile.profile_id,
            "calibration_digest": profile.calibration_digest()}
