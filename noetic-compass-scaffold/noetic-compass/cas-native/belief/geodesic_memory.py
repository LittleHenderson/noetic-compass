"""Geodesic retrieval for the CAS-as-Belief-Substrate.

This module is the first CABS "thought-space" slice:

* each remembered belief carries a point on the 40-state CAS simplex,
* Fisher-Rao distance measures how close the current thought is,
* belief mass controls how strongly that memory pulls nearby reasoning.

The retrieval layer is intentionally pure and storage-agnostic.  The existing
``BeliefStore`` still owns persistence, vibration/rhythm/RPM/inversion gates;
this file turns those locked or candidate beliefs into geometry-aware memory
records that can be ranked and rendered as model context.

This is Step 1 of the CABS gravity design, not the full persisted retrieval
system.  Store migration, ``BeliefStore.search_by_proximity``, contradiction
filtering, confirmation-kind weighting, decay-at-query-time, and Mode 7 tracing
remain integration work.  The pure-Python Fisher-Rao implementation mirrors
``cas_native.model.v1_arch.fisher_rao_loss.fisher_rao_distance`` without
requiring torch in the belief-store runtime.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence

from .belief import Belief


NUM_COGNITIVE_STATES = 40
SIMPLEX_TOLERANCE = 1e-5
DEFAULT_DISTANCE_FLOOR = 1e-6
LOCKED_MASS_BOOST = 1.25


def _as_float_tuple(values: Sequence[float]) -> tuple[float, ...]:
    return tuple(float(v) for v in values)


def validate_simplex_vector(
    values: Sequence[float],
    *,
    dim: int = NUM_COGNITIVE_STATES,
    tolerance: float = SIMPLEX_TOLERANCE,
) -> tuple[float, ...]:
    """Validate and normalize the representation of an open-simplex point.

    The vector must be one-dimensional, strictly positive, and sum to one
    within ``tolerance``.  The function returns an immutable float tuple so
    retrieval records are safe to keep in memory and easy to serialize later.
    """
    vector = _as_float_tuple(values)
    if len(vector) != dim:
        raise ValueError(f"simplex vector must have {dim} values, got {len(vector)}")
    if any(v <= 0.0 for v in vector):
        raise ValueError("simplex vector must be strictly positive")
    total = math.fsum(vector)
    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"simplex vector must sum to 1.0 within {tolerance}; got {total:.12f}"
        )
    return vector


def fisher_rao_distance_values(
    p: Sequence[float],
    q: Sequence[float],
    *,
    tolerance: float = SIMPLEX_TOLERANCE,
) -> float:
    """Fisher-Rao geodesic distance for two open-simplex vectors.

    Formula: ``d(p, q) = 2 * arccos(sum_k sqrt(p_k * q_k))``.
    The implementation is pure Python so CABS retrieval does not depend on
    torch at runtime.
    """
    p_vec = validate_simplex_vector(p, tolerance=tolerance)
    q_vec = validate_simplex_vector(q, dim=len(p_vec), tolerance=tolerance)
    bc = math.fsum(math.sqrt(a * b) for a, b in zip(p_vec, q_vec))
    bc = min(1.0, max(0.0, bc))
    if abs(1.0 - bc) < 1e-12:
        return 0.0
    return 2.0 * math.acos(bc)


def compute_belief_mass(
    belief: Belief,
    *,
    locked_boost: float = LOCKED_MASS_BOOST,
) -> float:
    """Map existing CABS gates to a scalar memory mass.

    ``vibration`` captures resonance strength and ``rhythm_count`` captures
    repeated exposure.  A locked belief gets a small boost because it has
    cleared RPM + inversion gates as well.
    """
    if belief.vibration < 0.0 or belief.rhythm_count < 0:
        raise ValueError("belief mass requires non-negative vibration and rhythm")
    mass = belief.vibration * (1.0 + math.log1p(float(belief.rhythm_count)))
    if belief.locked:
        mass *= locked_boost
    return mass


@dataclass(frozen=True)
class GeodesicBelief:
    """A CABS belief projected into CAS thought-space."""

    claim_key: str
    claim_text: str
    cas_expression: str
    simplex: tuple[float, ...]
    mass: float
    confidence: float
    source: str
    timestamp: datetime
    locked: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.claim_key:
            raise ValueError("claim_key must be non-empty")
        if self.mass < 0.0:
            raise ValueError("mass must be non-negative")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        object.__setattr__(self, "simplex", validate_simplex_vector(self.simplex))

    @property
    def effective_mass(self) -> float:
        """Mass discounted by confidence."""
        return self.mass * self.confidence

    @classmethod
    def from_belief(
        cls,
        belief: Belief,
        *,
        simplex: Sequence[float],
        mass: float | None = None,
        confidence: float | None = None,
        source: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> "GeodesicBelief":
        """Project an existing persisted CABS belief into thought-space."""
        if mass is None:
            mass = compute_belief_mass(belief)
        if confidence is None:
            confidence = 1.0 if belief.locked else 0.5
        if source is None:
            source = belief.sources[-1] if belief.sources else "belief-store"
        return cls(
            claim_key=belief.claim_key,
            claim_text=belief.claim_text,
            cas_expression=belief.cas_expression,
            simplex=validate_simplex_vector(simplex),
            mass=mass,
            confidence=confidence,
            source=source,
            timestamp=belief.last_reinforced,
            locked=belief.locked,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class GeodesicRetrievalResult:
    """One retrieved belief plus its geometry diagnostics."""

    belief: GeodesicBelief
    distance: float
    gravity: float
    rank: int

    @property
    def claim_key(self) -> str:
        return self.belief.claim_key


def gravity_score(
    *,
    effective_mass: float,
    distance: float,
    distance_floor: float = DEFAULT_DISTANCE_FLOOR,
) -> float:
    """Compute memory pull from mass and Fisher-Rao distance."""
    if effective_mass < 0.0:
        raise ValueError("effective_mass must be non-negative")
    if distance < 0.0:
        raise ValueError("distance must be non-negative")
    if distance_floor <= 0.0:
        raise ValueError("distance_floor must be positive")
    return effective_mass / (distance + distance_floor)


def retrieve_by_geodesic_gravity(
    *,
    query_simplex: Sequence[float],
    beliefs: Iterable[GeodesicBelief],
    top_k: int = 3,
    locked_only: bool = False,
    distance_floor: float = DEFAULT_DISTANCE_FLOOR,
) -> list[GeodesicRetrievalResult]:
    """Rank beliefs by ``mass / Fisher-Rao distance``.

    Nearby heavy beliefs rise to the top.  Far beliefs can still win if their
    mass is genuinely high, which is the intended "idea gravity" behavior.
    """
    if top_k <= 0:
        return []
    query = validate_simplex_vector(query_simplex)
    scored: list[GeodesicRetrievalResult] = []
    for belief in beliefs:
        if locked_only and not belief.locked:
            continue
        distance = fisher_rao_distance_values(query, belief.simplex)
        gravity = gravity_score(
            effective_mass=belief.effective_mass,
            distance=distance,
            distance_floor=distance_floor,
        )
        scored.append(
            GeodesicRetrievalResult(
                belief=belief,
                distance=distance,
                gravity=gravity,
                rank=0,
            )
        )

    scored.sort(
        key=lambda r: (
            -r.gravity,
            r.distance,
            -r.belief.effective_mass,
            r.belief.claim_key,
        )
    )
    return [
        GeodesicRetrievalResult(
            belief=result.belief,
            distance=result.distance,
            gravity=result.gravity,
            rank=i + 1,
        )
        for i, result in enumerate(scored[:top_k])
    ]


def render_retrieval_context(
    results: Sequence[GeodesicRetrievalResult],
    *,
    title: str = "Relevant CABS beliefs",
) -> str:
    """Render retrieved beliefs as a compact context block for generation."""
    if not results:
        return f"{title}: none"

    lines = [f"{title}:"]
    for result in results:
        belief = result.belief
        status = "locked" if belief.locked else "candidate"
        lines.append(
            f"{result.rank}. [{status}] {belief.claim_text} "
            f"(CAS: {belief.cas_expression}; distance={result.distance:.4f}; "
            f"gravity={result.gravity:.4f}; confidence={belief.confidence:.2f})"
        )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_DISTANCE_FLOOR",
    "GeodesicBelief",
    "GeodesicRetrievalResult",
    "LOCKED_MASS_BOOST",
    "NUM_COGNITIVE_STATES",
    "SIMPLEX_TOLERANCE",
    "compute_belief_mass",
    "fisher_rao_distance_values",
    "gravity_score",
    "render_retrieval_context",
    "retrieve_by_geodesic_gravity",
    "validate_simplex_vector",
]
