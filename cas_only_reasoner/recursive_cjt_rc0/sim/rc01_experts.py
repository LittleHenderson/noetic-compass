"""rc01_experts.py -- BIAS-CONDITIONED typed CJTStep implementations (RC-0.2 repair).

Owner audit finding (major 1): the previous CJTStep type-checked the Bias and then
ignored it, and always returned empty intents -- the recurrent equation was a label.
Repaired, option A of the directive:

  - the transformation is REGISTERED as theta-conditioned: Bias.theta[0] selects the
    transformation mode ("K_identity" vs "K_coarse"), so changing the Bias changes the
    Effect (test-locked);
  - CJTStep PROPOSES real updates: it returns a proposed memory append built from the
    Bias it read; the engine wraps proposals into VersionedIntents and commits them --
    the proposed_updates field is load-bearing, not decorative.

The registered transformation table (deterministic, frozen):

  expert          K_identity                          K_coarse
  ^2_attract      approach(P)                         approach!(P)
  ^3_averse       withdraw(P)                         withdraw!(P)
  ^6_decompose    parts[w1|w2|...|wn]                 parts[first-half words|second-half words]
  ^8_trigger      assoc(P->recalled_N)                assoc!(P->recalled_N)     (N = len(P))
"""
from __future__ import annotations

from rc0_types import BiasState
from rc01_types import Cause, CJTStepResult, ComputeBudget, EffectCandidate

EVIDENCE_MARKERS = {
    "^2_attract": ("valence_positive", "preference_cue"),
    "^3_averse": ("valence_negative", "avoidance_cue"),
    "^6_decompose": ("structure_cue", "multi_part"),
    "^8_trigger": ("association_cue", "reminder_cue"),
}

MODES = ("K_identity", "K_coarse")


def registered_transform(expert_id: str, payload: str, mode: str) -> tuple:
    """The registered deterministic, theta-conditioned transformation.
    Returns (op_kind, output). Raises on unknown expert or mode."""
    if mode not in MODES:
        raise ValueError(f"unknown transformation mode {mode!r}")
    bang = "!" if mode == "K_coarse" else ""
    if expert_id == "^2_attract":
        return "attract", f"approach{bang}({payload})"
    if expert_id == "^3_averse":
        return "avert", f"withdraw{bang}({payload})"
    if expert_id == "^6_decompose":
        parts = payload.split()
        if mode == "K_coarse":
            half = max(1, len(parts) // 2)
            return "decompose", "parts[" + " ".join(parts[:half]) + "|" + " ".join(parts[half:]) + "]"
        return "decompose", "parts[" + "|".join(parts) + "]"
    if expert_id == "^8_trigger":
        return "trigger", f"assoc{bang}({payload}->recalled_{len(payload)})"
    raise KeyError(f"unknown expert {expert_id!r}")


def cjt_step(expert_id: str, cause: Cause, bias: BiasState, allocation: float,
             budget: ComputeBudget, tick: int, bias_version: int) -> CJTStepResult:
    """The typed, Bias-conditioned CJT transformation. Spends exactly 1 unit.

    Reads the Bias: theta[0] selects the transformation mode; memory is read to build
    the PROPOSED memory append (a real update proposal the engine commits)."""
    if not isinstance(cause, Cause):
        raise TypeError("cjt_step requires a typed Cause")
    if not isinstance(bias, BiasState):
        raise TypeError("cjt_step requires a BiasState")
    if not budget.spend(1):
        raise RuntimeError("BUDGET_EXHAUSTED")
    mode = bias.theta[0] if bias.theta else "K_identity"
    op_kind, out = registered_transform(expert_id, cause.payload, mode)
    effect = EffectCandidate(producer_expert_id=expert_id, cause_id=cause.cause_id,
                             op_kind=op_kind, payload=out)
    # a REAL proposed update, built from the Bias this step read
    proposed_memory = (bias.memory + ((cause.cause_id, "executed", mode),))[-8:]
    return CJTStepResult(
        effect_candidate=effect,
        observations=(f"allocation={allocation:.6f}", f"op={op_kind}", f"mode={mode}"),
        proposed_updates=(("memory", proposed_memory, "cjt self-report"),),
        actual_compute_used=1,
        producer_expert_id=expert_id,
        originating_tick=tick,
        authoritative_bias_version=bias_version)
