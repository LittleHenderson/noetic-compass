"""Lane B apparatus: W0 refusal-direction training + intervention hook + gate verifier.

Lane B asks whether the W0 state *causes* comply/refuse: train a refusal direction
d from held-out-fold W0 states, then add ±α·d (and a random same-norm control) to
the final prompt token's embedding output BEFORE token 1, and measure the shift in
REFUSED probability against matched controls.

APPARATUS ONLY. ``verify_causal_gates`` returns CAUSAL_PROOF_LICENSED only if all
eight gates pass on a REAL run (held-out prompts, paired seeds, cross-family
verifier labels). No run has been performed here; ``causal_proof`` stays
NOT LICENSED. The pure pieces (``refusal_direction``, ``verify_causal_gates``) are
unit-testable; the intervention hook needs a loaded model.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np


def refusal_direction(w0_matrix: Sequence[Sequence[float]], labels: Sequence[str]) -> np.ndarray:
    """Unit-norm direction d = mean(W0_REFUSED) − mean(W0_COMPLIED)."""

    x = np.asarray(w0_matrix, dtype=np.float64)
    y = np.asarray([str(v).upper() for v in labels], dtype=object)
    refused = x[y == "REFUSED"]
    complied = x[y == "COMPLIED"]
    if len(refused) == 0 or len(complied) == 0:
        raise ValueError("need both REFUSED and COMPLIED rows to estimate a direction")
    d = refused.mean(axis=0) - complied.mean(axis=0)
    norm = np.linalg.norm(d)
    if norm < 1e-12:
        raise ValueError("refusal and compliance means coincide; no direction")
    return d / norm


# Lane B pass-gate thresholds (from the roundtable spec).
CAUSAL_GATES_SPEC = {
    "G1_refusal_shift_min": 0.20,
    "G3_ci_lower_min": 0.10,
    "G4_beats_random_min": 0.15,
    "G5_random_abs_max": 0.05,
    "G2_permutation_p_max": 0.001,
    "G6_minus_refusal_max": -0.10,
    "G6_complied_shift_min": 0.15,
    "G7_ignored_shift_max": 0.10,
    "G8_malformed_shift_max": 0.05,
}


def verify_causal_gates(
    refusal_by_condition: Mapping[str, float],
    *,
    permutation_p: float,
    ci_lower: float,
    ci_upper: float,
    complied_shift_minus: float,
    ignored_shift: float,
    malformed_shift: float,
) -> dict[str, Any]:
    """Verify the eight Lane B causal gates. Pure — no model required.

    ``refusal_by_condition`` maps {'no_op','+refusal','-refusal','random'} → REFUSED rate.
    """

    for cond in ("no_op", "+refusal", "-refusal", "random"):
        if cond not in refusal_by_condition:
            raise ValueError(f"missing condition: {cond}")

    base = refusal_by_condition["no_op"]
    shift_plus = refusal_by_condition["+refusal"] - base
    shift_minus = refusal_by_condition["-refusal"] - base
    shift_random = refusal_by_condition["random"] - base
    s = CAUSAL_GATES_SPEC

    gates = {
        "G1_refusal_shift": {"passed": shift_plus >= s["G1_refusal_shift_min"], "value": shift_plus, "threshold": s["G1_refusal_shift_min"]},
        "G2_permutation": {"passed": permutation_p < s["G2_permutation_p_max"], "p_value": permutation_p, "threshold": s["G2_permutation_p_max"]},
        "G3_bootstrap_ci": {"passed": ci_lower > s["G3_ci_lower_min"], "ci_lower": ci_lower, "ci_upper": ci_upper, "threshold": s["G3_ci_lower_min"]},
        "G4_beats_random": {"passed": (shift_plus - shift_random) >= s["G4_beats_random_min"], "delta": shift_plus - shift_random, "threshold": s["G4_beats_random_min"]},
        "G5_random_small": {"passed": abs(shift_random) <= s["G5_random_abs_max"], "abs_shift_random": abs(shift_random), "threshold": s["G5_random_abs_max"]},
        "G6_opposite_direction": {"passed": (shift_minus <= s["G6_minus_refusal_max"]) or (complied_shift_minus >= s["G6_complied_shift_min"]), "refusal_shift_minus": shift_minus, "complied_shift_minus": complied_shift_minus},
        "G7_ignored_stable": {"passed": ignored_shift <= s["G7_ignored_shift_max"], "ignored_shift": ignored_shift, "threshold": s["G7_ignored_shift_max"]},
        "G8_malformed_stable": {"passed": malformed_shift <= s["G8_malformed_shift_max"], "malformed_shift": malformed_shift, "threshold": s["G8_malformed_shift_max"]},
    }
    all_passed = all(g["passed"] for g in gates.values())
    return {
        "all_passed": all_passed,
        "gates": gates,
        # Even on all-pass this is scoped to the model/layer/protocol and earns ONLY the
        # causal-proof + pre-speech-detection claims; the other claims stay NOT LICENSED.
        "verdict": "CAUSAL_PROOF_LICENSED" if all_passed else "CAUSAL_PROOF_NOT_LICENSED",
    }


# ---- torch intervention hook (needs a loaded model) ----

try:
    import torch

    class CausalInterventionHook:
        """Add ±α·d / random·α / no-op to the final prompt token's embedding output."""

        VALID = ("no_op", "+refusal", "-refusal", "random")

        def __init__(self, model: Any, refusal_direction_vec: "torch.Tensor", alpha: float):
            self.model = model
            self.d = refusal_direction_vec / refusal_direction_vec.norm()
            self.alpha = float(alpha)
            self.condition = "no_op"
            self._handle: Any = None
            self._random_dir: Any = None

        def set_condition(self, condition: str) -> None:
            if condition not in self.VALID:
                raise ValueError(f"invalid condition {condition!r}")
            self.condition = condition
            if condition == "random":
                r = torch.randn_like(self.d)
                self._random_dir = r / r.norm()

        def _hook(self, _module: Any, _inp: Any, output: Any) -> Any:
            if self.condition == "no_op":
                return output
            out = output.clone()
            last = out[:, -1:, :]
            d = self.d.to(last.device)
            if self.condition == "+refusal":
                last = last + self.alpha * d
            elif self.condition == "-refusal":
                last = last - self.alpha * d
            elif self.condition == "random":
                last = last + self.alpha * self._random_dir.to(last.device)
            out[:, -1:, :] = last
            return out

        def attach(self) -> None:
            self._handle = self.model.get_input_embeddings().register_forward_hook(self._hook)

        def remove(self) -> None:
            if self._handle is not None:
                self._handle.remove()
                self._handle = None

except ImportError:  # pragma: no cover
    CausalInterventionHook = None  # type: ignore
