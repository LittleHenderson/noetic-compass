"""Compress raw activations into a readable summary.

Where ``activations.py`` and ``attribution.py`` compute the raw fields that go
into a ``MechanisticTrace``, this module is the *narrative* layer: take the
raw fields, return a small set of human-readable strings the dashboard and the
markdown renderer can drop in directly.

This module is real (not stubbed). It works on whatever captures and
attributions are passed in — stub-generated or real-model-generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cas_native.trace.activations import HEAD_NAMES, ActivationCapture


@dataclass(frozen=True)
class ActivationSummary:
    """Compact human-readable summary of a captured forward pass."""

    bottleneck_norm: float
    """L2 norm of the post-bottleneck z vector. High values can indicate a
    confident prediction; very low values can indicate under-driven heads."""

    bottleneck_active_dims: int
    """Count of bottleneck dims with |activation| above ``active_threshold``."""

    bottleneck_sparsity: float
    """1 - (active_dims / total_dims). High sparsity = few-dim prediction;
    low sparsity = many dims contributing."""

    most_confident_head: str
    """Name of the head with the highest per-head confidence."""

    least_confident_head: str
    """Name of the head with the lowest per-head confidence."""

    confidence_gap: float
    """``most_confident_confidence - least_confident_confidence``. Large gaps
    indicate uneven head training or capacity stealing."""

    most_capacity_head: str
    """Name of the head with the largest capacity allocation share."""

    capacity_dominance: float
    """Capacity share of the most-capacity head. Values > 0.5 are flagged."""

    headline: str
    """One-line natural-language summary, suitable for log lines and
    dashboard tooltips."""


def summarize_activations(
    capture: ActivationCapture,
    *,
    per_head_confidence: dict[str, float],
    capacity_allocation: dict[str, float],
    active_threshold: float = 0.5,
) -> ActivationSummary:
    """Build an ``ActivationSummary`` from raw fields.

    Pure: no torch, no model. Operates on plain Python collections.
    """
    z = capture.post_bottleneck
    bottleneck_norm = _l2_norm(z)
    active = sum(1 for v in z if abs(v) >= active_threshold)
    total = max(1, len(z))
    sparsity = 1.0 - (active / total)

    most_conf = _argmax_str(per_head_confidence) if per_head_confidence else "unknown"
    least_conf = _argmin_str(per_head_confidence) if per_head_confidence else "unknown"
    gap = (
        per_head_confidence.get(most_conf, 0.0)
        - per_head_confidence.get(least_conf, 0.0)
        if per_head_confidence
        else 0.0
    )
    most_cap = _argmax_str(capacity_allocation) if capacity_allocation else "unknown"
    cap_dom = capacity_allocation.get(most_cap, 0.0) if capacity_allocation else 0.0

    flags: list[str] = []
    if cap_dom > 0.5:
        flags.append(f"capacity-dominance:{most_cap}")
    if gap > 0.5:
        flags.append(f"confidence-spread:{most_conf}>>{least_conf}")
    if sparsity > 0.95:
        flags.append("bottleneck-near-silent")
    if bottleneck_norm == 0.0:
        flags.append("bottleneck-empty")

    flag_str = f" [{'; '.join(flags)}]" if flags else ""
    headline = (
        f"bottleneck_norm={bottleneck_norm:.2f} "
        f"active_dims={active}/{total} "
        f"top_head={most_conf} bot_head={least_conf} "
        f"gap={gap:.2f}{flag_str}"
    )

    return ActivationSummary(
        bottleneck_norm=bottleneck_norm,
        bottleneck_active_dims=active,
        bottleneck_sparsity=sparsity,
        most_confident_head=most_conf,
        least_confident_head=least_conf,
        confidence_gap=gap,
        most_capacity_head=most_cap,
        capacity_dominance=cap_dom,
        headline=headline,
    )


def build_head_agreement_matrix(
    prediction: dict,
) -> dict[tuple[str, str], float]:
    """Symmetric pairwise agreement scores over the 12-key prediction.

    Rule table (see spec §4.4). Each rule produces a [0.0, 1.0] score for one
    pair. Pairs not in the rule table are 1.0 (no judgment). Diagonal entries
    are 1.0.

    Returns ``dict[(head_a, head_b), score]`` with both orderings populated
    so consumers don't have to canonicalise.
    """
    matrix: dict[tuple[str, str], float] = {}

    register_mode = prediction.get("register_mode")
    registers = prediction.get("registers") or []
    family = prediction.get("expression_family")
    has_omega = bool(prediction.get("has_omega"))
    has_meta_logic = bool(prediction.get("has_meta_logic"))
    transition_kind = prediction.get("transition_kind")
    turn_type = prediction.get("turn_type")
    authority = prediction.get("authority")

    # Rule 1: register_mode vs registers consistency.
    rm_reg_score = 1.0
    if register_mode == "single" and len(registers) != 1:
        rm_reg_score = 0.0
    elif register_mode == "none" and len(registers) > 0:
        rm_reg_score = 0.3
    elif register_mode == "integration" and len(registers) < 2:
        rm_reg_score = 0.2
    elif register_mode in {"set_spec", "co_presence"} and len(registers) < 2:
        rm_reg_score = 0.4
    _set_pair(matrix, "register_mode", "register", rm_reg_score)

    # Rule 2: expression_family vs has_omega.
    fam_omega_score = 1.0
    if has_omega and family not in {"production", "omega"}:
        fam_omega_score = 0.2
    _set_pair(matrix, "expression_family", "omega", fam_omega_score)

    # Rule 3: expression_family vs has_meta_logic.
    fam_ml_score = 1.0
    if has_meta_logic and family != "meta_logic":
        fam_ml_score = 0.4
    if family == "meta_logic" and not has_meta_logic:
        fam_ml_score = min(fam_ml_score, 0.3)
    _set_pair(matrix, "expression_family", "meta_logic", fam_ml_score)

    # Rule 4: transition_kind vs expression_family.
    tk_fam_score = 1.0
    if transition_kind == "meta_logic_move" and family != "meta_logic":
        tk_fam_score = 0.2
    if transition_kind == "production" and family != "production":
        tk_fam_score = 0.4
    if transition_kind == "omega_bind" and family not in {"production", "omega"}:
        tk_fam_score = 0.3
    _set_pair(matrix, "transition_kind", "expression_family", tk_fam_score)

    # Rule 5: turn_type vs transition_kind (REFUSE turns shouldn't ANSWER).
    tt_tk_score = 1.0
    if turn_type in {"REFUSE", "REFUSE_CLAIM"} and transition_kind in {"production"}:
        tt_tk_score = 0.4
    _set_pair(matrix, "turn_type", "transition_kind", tt_tk_score)

    # Rule 6: authority vs turn_type.
    auth_tt_score = 1.0
    if turn_type == "REFUSE_CLAIM" and authority != "blocked":
        auth_tt_score = 0.3
    if authority == "blocked" and turn_type not in {"REFUSE", "REFUSE_CLAIM"}:
        auth_tt_score = 0.5
    _set_pair(matrix, "authority", "turn_type", auth_tt_score)

    # Rule 7-9: noetic/domain, drive/domain, register/register_mode pass-through.
    _set_pair(matrix, "noetic", "domain", 1.0)
    _set_pair(matrix, "drive", "domain", 1.0)
    _set_pair(matrix, "register", "register_mode", rm_reg_score)

    # Diagonal.
    for name in HEAD_NAMES:
        matrix[(name, name)] = 1.0

    # Mirror for symmetry.
    mirrored = {(b, a): score for (a, b), score in matrix.items() if a != b}
    matrix.update(mirrored)

    return matrix


def _set_pair(
    matrix: dict[tuple[str, str], float],
    a: str,
    b: str,
    score: float,
) -> None:
    matrix[(a, b)] = max(0.0, min(1.0, score))


def _l2_norm(values: list[float]) -> float:
    if not values:
        return 0.0
    return (sum(v * v for v in values)) ** 0.5


def _argmax_str(d: dict[str, float]) -> str:
    if not d:
        return ""
    return max(d.items(), key=lambda kv: kv[1])[0]


def _argmin_str(d: dict[str, float]) -> str:
    if not d:
        return ""
    return min(d.items(), key=lambda kv: kv[1])[0]


def flagged_disagreements(
    matrix: dict[tuple[str, str], float],
    *,
    threshold: float = 0.5,
) -> list[tuple[str, str, float]]:
    """Return all unique pairs with score below ``threshold``, sorted ascending.

    Used by the markdown renderer to surface "heads that disagree" at a glance.
    """
    seen: set[frozenset[str]] = set()
    out: list[tuple[str, str, float]] = []
    for (a, b), score in matrix.items():
        if a == b:
            continue
        key = frozenset({a, b})
        if key in seen:
            continue
        seen.add(key)
        if score < threshold:
            out.append((a, b, score))
    out.sort(key=lambda triple: triple[2])
    return out
