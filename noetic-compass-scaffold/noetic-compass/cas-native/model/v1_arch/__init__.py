"""Path C-1 simplex-native architecture variant.

This subpackage holds the FIRST prototype phase of the Path C
simplex-native CAS architecture rebuild. C-1 ships:

- :class:`SimplexStateEncoder` — token sequence -> Δ°₃₉ open-simplex
  trajectory (mirror-descent multiplicative update; no transformer
  self-attention on the encoder side).
- :class:`FisherRaoLoss` and :func:`fisher_rao_distance` — geodesic
  metric on the open simplex per CAS Correction 4 plus a drift penalty
  over the per-step trace.
- :class:`RPMGateStub` — Boolean admissibility check stub over
  (state, transition_op) pairs. Reads the compiler's existing
  ``_is_admissible`` table; emits ``passed`` and ``broken_at`` evidence.
  Full RPM-as-meta-logic-evidence is C-5, NOT C-1.
- :class:`V1ArchModel` — wires SimplexStateEncoder + FisherRaoLoss +
  RPMGateStub on top of the EXISTING transformer decoder
  (:class:`CASNativeModel`). Encoder side changes; decoder preserved.

What C-1 does NOT include (deferred to later phases per Path C §3.3):

- Drive 7-dim non-negative intensity vector  → C-2.
- Register 4-dim Bernoulli activation        → C-3.
- Meta-logic proof module                    → C-4.
- RPM uses meta-logic proofs as gate evidence → C-5.

Everything in this subpackage is CODE + TESTS only. No training, no
GPU. The falsification gate (within 5-10pp of K=9 on CAS prediction;
better trace quality than K=9) is measured LATER on the running v1
retrain after Path D corpus + Path C arch land together.

Hard rules (per CLAUDE.md and ``feedback_no_foreign_architecture_cas_only``):
- NO foreign pretrained models / weights.
- Cognitive State stays Δ°₃₉ open simplex (CAS Correction 4).
- Drive is NOT a simplex (Path C §3.1.3a).
- Register is NOT a simplex (Path C §3.1.3b).
"""

from .simplex_state_encoder import (
    SimplexStateEncoder,
    SimplexStateEncoderConfig,
    NUM_COGNITIVE_STATES,
    SIMPLEX_FLOOR,
)
from .fisher_rao_loss import (
    FisherRaoLoss,
    fisher_rao_distance,
    smooth_one_hot,
)
from .rpm_gate_stub import (
    RPMGateStub,
    RPMGateResult,
    TRANSITION_OPS,
)
from .v1_arch_model import (
    V1ArchModel,
    V1ArchConfig,
)

__all__ = [
    "SimplexStateEncoder",
    "SimplexStateEncoderConfig",
    "NUM_COGNITIVE_STATES",
    "SIMPLEX_FLOOR",
    "FisherRaoLoss",
    "fisher_rao_distance",
    "smooth_one_hot",
    "RPMGateStub",
    "RPMGateResult",
    "TRANSITION_OPS",
    "V1ArchModel",
    "V1ArchConfig",
]
