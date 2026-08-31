"""rc01_experts.py -- the actual typed CJTStep implementations (RC-0.1 requirement 1).

Each simulator expert implements the SAME interface:

    CJTStep(cause: Cause, bias: BiasState, allocation: float, budget: ComputeBudget)
        -> CJTStepResult

while performing a DISTINCT registered deterministic transformation. The Effect is a
typed EffectCandidate produced from the Cause payload -- never a bare display string.

Candidate relevance is declared per expert as structural evidence markers (non-gold):
the engine proposes an expert as a candidate only if its markers intersect the Cause
evidence. No expert, and no routing code, can see the verifier's gold fields -- the
types have no slot for them.
"""
from __future__ import annotations

from rc0_types import BiasState
from rc01_types import Cause, CJTStepResult, ComputeBudget, EffectCandidate

# structural evidence markers each expert responds to (NON-gold surface cues)
EVIDENCE_MARKERS = {
    "^2_attract": ("valence_positive", "preference_cue"),
    "^3_averse": ("valence_negative", "avoidance_cue"),
    "^6_decompose": ("structure_cue", "multi_part"),
    "^8_trigger": ("association_cue", "reminder_cue"),
}


def _transform(expert_id: str, payload: str) -> tuple:
    """The registered deterministic transformation per expert. Returns (op_kind, out)."""
    if expert_id == "^2_attract":
        return "attract", f"approach({payload})"
    if expert_id == "^3_averse":
        return "avert", f"withdraw({payload})"
    if expert_id == "^6_decompose":
        parts = payload.split()
        return "decompose", "parts[" + "|".join(parts) + "]"
    if expert_id == "^8_trigger":
        return "trigger", f"assoc({payload}->recalled_{len(payload)})"
    raise KeyError(f"unknown expert {expert_id!r}")


def cjt_step(expert_id: str, cause: Cause, bias: BiasState, allocation: float,
             budget: ComputeBudget, tick: int, bias_version: int) -> CJTStepResult:
    """The typed CJT transformation. Spends exactly 1 CJT_EXPERT_EVALUATION."""
    if not isinstance(cause, Cause):
        raise TypeError("cjt_step requires a typed Cause")
    if not isinstance(bias, BiasState):
        raise TypeError("cjt_step requires a BiasState")
    if not budget.spend(1):
        raise RuntimeError("BUDGET_EXHAUSTED")  # caller converts to typed HALT
    op_kind, out = _transform(expert_id, cause.payload)
    effect = EffectCandidate(producer_expert_id=expert_id, cause_id=cause.cause_id,
                             op_kind=op_kind, payload=out)
    return CJTStepResult(
        effect_candidate=effect,
        observations=(f"allocation={allocation:.6f}", f"op={op_kind}"),
        intents=(),                       # engine assembles versioned intents itself
        actual_compute_used=1,
        producer_expert_id=expert_id,
        originating_tick=tick,
        authoritative_bias_version=bias_version)
