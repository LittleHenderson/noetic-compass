"""A-4: Differential-pair matched-control harness.

Runs the same input under two bias profiles (e.g. full system constitution vs.
a minimal one) and measures how far the two outputs diverge on the CAS state
simplex using the Fisher-Rao geodesic distance:

    d(p, q) = 2 · arccos( Σ_k √(p_k · q_k) )

(CLAUDE.md, Correction 4). Large divergence means the bias profile is doing
heavy lifting — structurally suspicious, the way a differential amplifier's
output reveals what the common-mode (shared assumptions) cancelled out.

Claim boundary: divergence is a HEURISTIC signal. Above threshold it routes to
``FLAG_FOR_HUMAN_REVIEW``; it is not proof of an attack, and never ACCEPT.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from cas_forex.schemas.cjt import (
    CjtCircuitDiagnostic,
    CjtClaimCeiling,
    CjtDiagnosticKind,
    CjtObservation,
    CjtRegion,
)

DEFAULT_DIVERGENCE_THRESHOLD = 0.5  # radians-scaled; π is the max distance


class DifferentialPairResult(BaseModel):
    divergence: float
    threshold: float
    diverged: bool
    common_mode: float = Field(
        description="Bhattacharyya overlap Σ√(p_k q_k) — the shared (rejected) common mode."
    )


def _normalize(vector: Sequence[float]) -> list[float]:
    if not vector:
        raise ValueError("activation vector is empty")
    if any(v < 0 for v in vector):
        raise ValueError("activation vector has negative entries")
    total = float(sum(vector))
    if total <= 0:
        raise ValueError("activation vector sums to zero")
    return [v / total for v in vector]


def fisher_rao_distance(p: Sequence[float], q: Sequence[float]) -> float:
    """Fisher-Rao geodesic distance between two activation distributions."""

    if len(p) != len(q):
        raise ValueError("activation vectors must have equal length")
    pn = _normalize(p)
    qn = _normalize(q)
    overlap = sum(math.sqrt(pk * qk) for pk, qk in zip(pn, qn))
    overlap = max(-1.0, min(1.0, overlap))  # numerical clamp for arccos
    return 2.0 * math.acos(overlap)


def differential_pair_divergence(
    output_sys: Sequence[float],
    output_shadow: Sequence[float],
) -> DifferentialPairResult:
    """Compute divergence between system-bias and shadow-bias outputs."""

    pn = _normalize(output_sys)
    qn = _normalize(output_shadow)
    overlap = max(-1.0, min(1.0, sum(math.sqrt(a * b) for a, b in zip(pn, qn))))
    divergence = 2.0 * math.acos(overlap)
    return DifferentialPairResult(
        divergence=divergence,
        threshold=DEFAULT_DIVERGENCE_THRESHOLD,
        diverged=divergence > DEFAULT_DIVERGENCE_THRESHOLD,
        common_mode=overlap,
    )


def build_differential_diagnostic(
    trace_id: str,
    *,
    output_sys: Sequence[float],
    output_shadow: Sequence[float],
    input_ref: str = "input",
    threshold: float = DEFAULT_DIVERGENCE_THRESHOLD,
) -> CjtCircuitDiagnostic:
    """Run a differential-pair comparison and emit a claim-bounded diagnostic."""

    pn = _normalize(output_sys)
    qn = _normalize(output_shadow)
    overlap = max(-1.0, min(1.0, sum(math.sqrt(a * b) for a, b in zip(pn, qn))))
    divergence = 2.0 * math.acos(overlap)
    diverged = divergence > threshold

    ceiling = (
        CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW if diverged else CjtClaimCeiling.OPEN
    )
    note = (
        "Differential pair diverged beyond threshold: bias profile is doing heavy "
        "lifting; route to human review."
        if diverged
        else "Differential pair within tolerance: outputs agree under both bias profiles."
    )
    observation = CjtObservation(
        observation_id=f"{trace_id}:obs:differential:0",
        cause_ref=input_ref,
        bias_ref="system_constitution vs minimal_constitution",
        effect_ref="output_divergence",
        region=CjtRegion.BREAKDOWN if diverged else CjtRegion.ACTIVE,
        beta_estimate=divergence,
        beta_source="fisher_rao_geodesic",
        confidence=min(1.0, divergence / math.pi),
        claim_ceiling=ceiling,
        notes=[note],
        evidence={
            "divergence": divergence,
            "threshold": threshold,
            "common_mode_overlap": overlap,
        },
    )
    return CjtCircuitDiagnostic(
        diagnostic_id=f"{trace_id}:cjt:differential",
        kind=CjtDiagnosticKind.GENERAL,
        trace_id=trace_id,
        observations=[observation],
        overall_region=CjtRegion.BREAKDOWN if diverged else CjtRegion.ACTIVE,
        claim_ceiling=ceiling,
        evidence={"divergence": divergence, "diverged": diverged},
    )
