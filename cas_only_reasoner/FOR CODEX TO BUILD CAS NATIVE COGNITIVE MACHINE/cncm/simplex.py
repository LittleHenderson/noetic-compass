"""Fisher-Rao metric on the open probability simplex (CAS Correction 4).

The cognitive state space is NOT the discrete 40-element set of CAS states. It is
the open probability simplex

    S°_I = Δ39° = { p in R^40 : p_k > 0 for every k, Σ_k p_k = 1 }

and distances on it are measured with the Fisher-Rao metric. This module
implements that metric, the tangent space at a point, and the geodesic
(Bhattacharyya) distance.

    Fisher-Rao inner product   g^FR_p(u, v) = Σ_k (u_k * v_k / p_k)
    Fisher-Rao norm            ||u||_p     = sqrt(g^FR_p(u, u))
    Bhattacharyya coefficient  BC(p, q)     = Σ_k sqrt(p_k * q_k)
    Geodesic distance          d(p, q)      = 2 * arccos(BC(p, q))

Provenance and source identity
------------------------------
Derived from the Noetic Compass Rust engine, which is an external read-only input
to this homebase:

    path   noetic-compass-scaffold/noetic-compass/cas-engine/src/metric/mod.rs
    bytes  23347
    sha256 66fcee7d8801e4fa9607789a802d495e01e528252f1375d2cf0bf154dfb72b10

The formulas and the validation rules (including the clamping of the arccos
argument for numerical stability) are taken from that source. Two deliberate
conflicts with it are recorded rather than silently carried over:

1. That module is Rust and lives in a different project. This is an independent
   pure-Python implementation inside the CNCM homebase, not a binding. No Rust
   build or PyO3 layer is involved, and nothing here imports it.
2. Errors are raised as :class:`SimplexError` subclasses with the same reason
   names as the Rust ``MetricError`` variants, so a caller can map them one to one.
3. That source tests a tangent vector's sum against a flat absolute tolerance.
   This module scales the tolerance by the vector's L1 norm, so a large tangent
   vector is not refused for a floating-point residue that is proportionally
   zero. The reported ``total`` is always the raw, unscaled sum, so a refusal
   message quotes an exact number. A vector summing to 40.0 is refused under
   both rules.

The metric is one of the four mathematical corrections the project's own master
instructions mark MUST IMPLEMENT. It was absent from this homebase before this
module: neither ``cncm/`` nor ``tests/`` nor ``tools/`` referenced the Fisher-Rao
metric, the open simplex or the geodesic distance.

Pure standard library. No neural runtime, no device, no wall-clock input.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from .canonical import content_id, digest

#: CAS cognitive states: 10 Noetics x 4 Domains (P, C, E, O).
NUM_STATES = 40

#: Probabilities must sum to 1 within this tolerance (absolute).
SUM_TOLERANCE = 1e-9

#: A tangent vector must sum to 0 within this tolerance (absolute).
TANGENT_TOLERANCE = 1e-9

SCHEMA_VERSION = "cncm.simplex/0.1"


class SimplexError(ValueError):
    """A point or tangent vector violated the open-simplex contract."""

    def __post_init__(self) -> None:
        """Copy the rendered reason into ``args``.

        A dataclass-generated ``__init__`` does not call ``BaseException``'s, so
        without this the exception would carry empty ``args`` and a caller
        reading ``exc.args[0]`` would get an IndexError instead of the reason.
        The reason is already fixed by the subclass ``__str__`` and the fields
        set by the generated ``__init__``, both of which run before this.
        """
        BaseException.__init__(self, str(self))


@dataclass(frozen=True)
class WrongDimension(SimplexError):
    expected: int
    got: int

    def __str__(self) -> str:  # pragma: no cover - exercised through callers
        return f"expected {self.expected} components, got {self.got}"


@dataclass(frozen=True)
class NotPositive(SimplexError):
    index: int
    value: float

    def __str__(self) -> str:  # pragma: no cover
        return f"component {self.index} is not strictly positive: {self.value!r}"


@dataclass(frozen=True)
class NotNormalized(SimplexError):
    total: float

    def __str__(self) -> str:  # pragma: no cover
        return f"components sum to {self.total!r}, not 1"


@dataclass(frozen=True)
class NotTangent(SimplexError):
    total: float

    def __str__(self) -> str:  # pragma: no cover
        return f"tangent vector sums to {self.total!r}, not 0"


@dataclass(frozen=True)
class NotFinite(SimplexError):
    index: int

    def __str__(self) -> str:  # pragma: no cover
        return f"component {self.index} is not finite"


def _components(value: Iterable[float], expected: int) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)):
        raise SimplexError("components must be a sequence of numbers")
    items = tuple(value)
    if len(items) != expected:
        raise WrongDimension(expected=expected, got=len(items))
    out = []
    for index, item in enumerate(items):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise SimplexError(f"component {index} is not a real number")
        number = float(item)
        if not math.isfinite(number):
            raise NotFinite(index=index)
        out.append(number)
    return tuple(out)


@dataclass(frozen=True)
class TangentVector:
    """A tangent vector on the open simplex at some point.

    The simplex constraint Σ_k p_k = 1 forces Σ_k u_k = 0 for every tangent
    vector, so a vector that does not sum to zero is not a direction the state
    can move in and is refused.
    """

    values: tuple[float, ...]

    def as_tuple(self) -> tuple[float, ...]:
        return self.values

    def dim(self) -> int:
        return len(self.values)

    def component(self, index: int) -> float:
        return self.values[index]

    def scaled(self, factor: float) -> "TangentVector":
        if not math.isfinite(float(factor)):
            raise SimplexError("scale factor must be finite")
        return TangentVector(tuple(value * float(factor) for value in self.values))


def validate_tangent_vector(values: Sequence[float]) -> TangentVector:
    """Return a validated :class:`TangentVector`, or raise.

    The tolerance is scaled by the vector's L1 norm (see provenance note 3), so
    a large tangent vector is judged on proportional rather than absolute
    residue. The raised ``total`` is the raw sum.
    """
    components = _components(values, NUM_STATES)
    total = math.fsum(components)
    scale = math.fsum(abs(value) for value in components)
    if abs(total) > TANGENT_TOLERANCE * max(1.0, scale):
        raise NotTangent(total=total)
    return TangentVector(components)


@dataclass(frozen=True)
class CognitiveStateVector:
    """A point of the OPEN simplex: 40 strictly positive probabilities summing to 1.

    Zero is refused. That is the substance of Correction 4 — the state space is
    the open simplex S°_I, not the discrete set of 40 states and not the closed
    simplex. A zero component would place the point on the boundary, where the
    Fisher-Rao metric is degenerate.
    """

    probabilities: tuple[float, ...]

    def as_tuple(self) -> tuple[float, ...]:
        return self.probabilities

    def dim(self) -> int:
        return len(self.probabilities)

    def component(self, index: int) -> float:
        return self.probabilities[index]

    def identity(self) -> str:
        return content_id("cncm-simplex-state", {"probabilities": list(self.probabilities)})

    def digest(self) -> str:
        return digest({"probabilities": list(self.probabilities)})

    def entropy(self) -> float:
        """Shannon entropy in nats; finite because every component is > 0."""
        return -math.fsum(p * math.log(p) for p in self.probabilities)

    def maximum_entropy(self) -> float:
        return math.log(NUM_STATES)

    def uniformity(self) -> float:
        """1.0 at the uniform point, 0.0 as the point approaches the boundary."""
        return self.entropy() / self.maximum_entropy()


def validate_state_vector(probabilities: Sequence[float]) -> CognitiveStateVector:
    """Return a validated :class:`CognitiveStateVector`, or raise."""
    components = _components(probabilities, NUM_STATES)
    for index, value in enumerate(components):
        if value <= 0.0:
            raise NotPositive(index=index, value=value)
    total = math.fsum(components)
    if abs(total - 1.0) > SUM_TOLERANCE:
        raise NotNormalized(total=total)
    return CognitiveStateVector(components)


def from_weights(weights: Sequence[float]) -> CognitiveStateVector:
    """Normalize strictly positive weights onto the simplex."""
    components = _components(weights, NUM_STATES)
    for index, value in enumerate(components):
        if value <= 0.0:
            raise NotPositive(index=index, value=value)
    total = math.fsum(components)
    if total <= 0.0:
        raise SimplexError("weights must sum to a positive value")
    return CognitiveStateVector(tuple(value / total for value in components))


def from_logits(logits: Sequence[float]) -> CognitiveStateVector:
    """Softmax onto the open simplex.

    Strict: if any component underflows to exactly 0.0 the result is on the
    boundary, not in the open simplex, and is refused rather than silently
    nudged. In practice this bounds the admissible spread of the logits; a
    caller with an unbounded logit range must bound it deliberately rather than
    rely on an implicit floor invented here.
    """
    components = _components(logits, NUM_STATES)
    peak = max(components)
    exps = [math.exp(value - peak) for value in components]
    for index, value in enumerate(exps):
        if value <= 0.0:
            raise NotPositive(index=index, value=value)
    total = math.fsum(exps)
    return CognitiveStateVector(tuple(value / total for value in exps))


def tangent_from_direction(direction: Sequence[float]) -> TangentVector:
    """Project an arbitrary direction onto the tangent space (subtract the mean)."""
    components = _components(direction, NUM_STATES)
    mean = math.fsum(components) / NUM_STATES
    return validate_tangent_vector(tuple(value - mean for value in components))


def fisher_rao_inner_product(
    point: CognitiveStateVector,
    u: TangentVector,
    v: TangentVector,
) -> float:
    """g^FR_p(u, v) = Σ_k (u_k * v_k / p_k).

    Every ``p_k`` is strictly positive by construction, so the division is safe
    without a guard — which is exactly why the open simplex is required.
    """
    if not isinstance(point, CognitiveStateVector):
        raise SimplexError("point must be a CognitiveStateVector")
    if not isinstance(u, TangentVector) or not isinstance(v, TangentVector):
        raise SimplexError("operands must be TangentVector instances")
    return math.fsum(
        u.component(k) * v.component(k) / point.component(k) for k in range(NUM_STATES)
    )


def fisher_rao_norm(point: CognitiveStateVector, u: TangentVector) -> float:
    """||u||_p = sqrt(g^FR_p(u, u))."""
    inner = fisher_rao_inner_product(point, u, u)
    if inner < 0.0:  # pragma: no cover - guarded by positive-definiteness
        raise SimplexError("Fisher-Rao norm is negative; the metric is not positive definite")
    return math.sqrt(inner)


def bhattacharyya_coefficient(p: CognitiveStateVector, q: CognitiveStateVector) -> float:
    """BC(p, q) = Σ_k sqrt(p_k * q_k), in [0, 1], equal to 1 iff p = q."""
    if not isinstance(p, CognitiveStateVector) or not isinstance(q, CognitiveStateVector):
        raise SimplexError("operands must be CognitiveStateVector instances")
    return math.fsum(
        math.sqrt(p.component(k) * q.component(k)) for k in range(NUM_STATES)
    )


def geodesic_distance(p: CognitiveStateVector, q: CognitiveStateVector) -> float:
    """d(p, q) = 2 * arccos(BC(p, q)), the shortest path length under the metric.

    The arccos argument is clamped to [0, 1]: floating-point arithmetic can carry
    the coefficient a hair outside the interval when p == q, and the true distance
    there is exactly zero.
    """
    coefficient = bhattacharyya_coefficient(p, q)
    clamped = min(1.0, max(0.0, coefficient))
    return 2.0 * math.acos(clamped)


def metric_profile() -> dict:
    """Self-describing profile for evidence records."""
    return {
        "schema": SCHEMA_VERSION,
        "num_states": NUM_STATES,
        "space": "OPEN_PROBABILITY_SIMPLEX",
        "correction": "CORRECTION_4_OPEN_SIMPLEX",
        "inner_product": "sum_k(u_k*v_k/p_k)",
        "norm": "sqrt(g_fr(u,u))",
        "distance": "2*arccos(sum_k sqrt(p_k*q_k))",
        "zero_probability": "REFUSED",
        "source": {
            "project": "noetic-compass",
            "path": "noetic-compass-scaffold/noetic-compass/cas-engine/src/metric/mod.rs",
            "bytes": 23347,
            "sha256": "66fcee7d8801e4fa9607789a802d495e01e528252f1375d2cf0bf154dfb72b10",
        },
    }
