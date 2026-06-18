"""B: CJT analytical engine — gain (β), transconductance (gm), operating region.

Implements the blueprint's Part III analytical layer with the math that is
well-defined NOW:

  - large-signal β = d_FR(E_after, E_before) / d_FR(C_after, C_before)
  - small-signal β ≈ finite-difference ratio for a small cause perturbation
  - transconductance gm = d_FR(E) / d_FR(B) at constant cause
  - operating region from cause/effect activation + cutoff/saturation thresholds

Status: ANALYTICAL / heuristic. The *computation* is real and tested. What is
OPEN is empirical validation against real generation traces — a β number here is
a geometric estimate, not a measured model property. ``CjtAnalysis.validated``
is always False until trace validation lands (see Q-002 in the blueprint).
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from cas_forex.cjt_differential import fisher_rao_distance
from cas_forex.schemas.cjt import CjtRegion

DEFAULT_CUTOFF = 0.1
DEFAULT_SATURATION = 0.9


class CjtAnalysis(BaseModel):
    beta: Optional[float] = None
    beta_kind: str = "large_signal"
    gm: Optional[float] = None
    region: CjtRegion = CjtRegion.UNKNOWN
    beta_source: str = "analytical_fisher_rao"
    validated: bool = Field(
        default=False,
        description="Always False: analytical estimate, not validated against real traces.",
    )
    notes: list[str] = Field(default_factory=list)


def large_signal_beta(
    cause_before: Sequence[float],
    cause_after: Sequence[float],
    effect_before: Sequence[float],
    effect_after: Sequence[float],
) -> Optional[float]:
    """β_large = d_FR(E_after, E_before) / d_FR(C_after, C_before).

    Returns None if the cause did not move (gain undefined — no input change).
    """

    cause_delta = fisher_rao_distance(cause_before, cause_after)
    if cause_delta <= 1e-12:
        return None
    effect_delta = fisher_rao_distance(effect_before, effect_after)
    return effect_delta / cause_delta


def small_signal_beta(
    cause_before: Sequence[float],
    cause_after: Sequence[float],
    effect_before: Sequence[float],
    effect_after: Sequence[float],
    *,
    max_cause_step: float = 0.2,
) -> Optional[float]:
    """Finite-difference small-signal gain.

    Only meaningful for a small cause perturbation; if the cause moved more than
    ``max_cause_step`` (Fisher-Rao), this is the large-signal regime and we say so.
    """

    cause_delta = fisher_rao_distance(cause_before, cause_after)
    if cause_delta <= 1e-12:
        return None
    if cause_delta > max_cause_step:
        # Not a small-signal perturbation — caller should use large_signal_beta.
        return None
    effect_delta = fisher_rao_distance(effect_before, effect_after)
    return effect_delta / cause_delta


def transconductance(
    bias_before: Sequence[float],
    bias_after: Sequence[float],
    effect_before: Sequence[float],
    effect_after: Sequence[float],
) -> Optional[float]:
    """gm = d_FR(E) / d_FR(B) at constant cause — sensitivity of output to bias."""

    bias_delta = fisher_rao_distance(bias_before, bias_after)
    if bias_delta <= 1e-12:
        return None
    effect_delta = fisher_rao_distance(effect_before, effect_after)
    return effect_delta / bias_delta


def classify_region(
    cause_activation: float,
    effect_activation: float,
    *,
    cutoff: float = DEFAULT_CUTOFF,
    saturation: float = DEFAULT_SATURATION,
    involution_flip: bool = False,
) -> CjtRegion:
    """Classify operating region from activation levels (blueprint Part III.1)."""

    for value, name in ((cause_activation, "cause"), (effect_activation, "effect")):
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{name}_activation must be in [0, 1]")

    if involution_flip:
        return CjtRegion.BREAKDOWN
    if cause_activation > cutoff and effect_activation <= cutoff:
        # Cause present but effect ~0 → did not conduct.
        return CjtRegion.CUTOFF
    if effect_activation >= saturation:
        return CjtRegion.SATURATION
    return CjtRegion.ACTIVE


def analyze_transition(
    cause_before: Sequence[float],
    cause_after: Sequence[float],
    bias_before: Sequence[float],
    bias_after: Sequence[float],
    effect_before: Sequence[float],
    effect_after: Sequence[float],
    *,
    cutoff: float = DEFAULT_CUTOFF,
    saturation: float = DEFAULT_SATURATION,
    involution_flip: bool = False,
) -> CjtAnalysis:
    """Full analytical readout for one cause/bias/effect transition."""

    beta = large_signal_beta(cause_before, cause_after, effect_before, effect_after)
    gm = transconductance(bias_before, bias_after, effect_before, effect_after)
    cause_act = max(cause_after) if cause_after else 0.0
    effect_act = max(effect_after) if effect_after else 0.0
    region = classify_region(
        min(1.0, cause_act),
        min(1.0, effect_act),
        cutoff=cutoff,
        saturation=saturation,
        involution_flip=involution_flip,
    )
    notes = ["Analytical Fisher-Rao estimate; NOT validated against real model traces."]
    if beta is None:
        notes.append("β undefined: cause did not move.")
    return CjtAnalysis(beta=beta, gm=gm, region=region, notes=notes)
