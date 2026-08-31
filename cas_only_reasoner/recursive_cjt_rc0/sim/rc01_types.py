"""rc01_types.py -- RC-0.1 typed objects: Cause, EffectCandidate, CJTStepResult,
publication intents, and numeric fail-closed guards.

PHASE RC-0.1 (feedback, action, and evidence closure). Deterministic CPU only. No
neural network. No randomness, no wall-clock in state-bearing paths.

Key laws enforced here:
  - NUMERIC FAIL-CLOSED: bool, NaN, +/-inf, and negatives are rejected wherever a
    nonnegative finite number is required. Allocations must be a valid simplex.
  - GOLD WALL: the Cause carries only NON-gold structural evidence. Gold fields
    (required_op / expected outcomes) exist ONLY inside the verifier's sealed table;
    no routing object has a field for them.
  - LATENT vs ENFORCED readiness: latent prerequisite truth is a property of the
    Bias; whether the controller ENFORCES it is a separate engine flag. Disabling RPM
    removes enforcement; it never rewrites the truth.
  - Effect publication is a SEPARATE authority from diagnostic state commitment.
"""
from __future__ import annotations

import enum
import hashlib
import json
import math
from dataclasses import dataclass, field

from rc0_types import BiasState  # reuse the frozen Bias shell from RC-0


# ---------------------------------------------------------------- numeric guards
def require_finite_nonneg(name: str, v) -> float:
    """Fail-closed scalar guard: number, not bool, finite, >= 0."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"{name} must be a real number (bool rejected), got {type(v).__name__}")
    fv = float(v)
    if math.isnan(fv) or math.isinf(fv):
        raise ValueError(f"{name} must be finite, got {v!r}")
    if fv < 0:
        raise ValueError(f"{name} must be >= 0, got {v!r}")
    return fv


def require_positive(name: str, v) -> float:
    fv = require_finite_nonneg(name, v)
    if fv <= 0:
        raise ValueError(f"{name} must be > 0, got {v!r}")
    return fv


def validate_allocation(alloc: dict, tol: float = 1e-9) -> dict:
    """Postcondition on every normalized allocation: finite, nonnegative, sums to 1."""
    total = 0.0
    for k, v in alloc.items():
        fv = require_finite_nonneg(f"allocation[{k}]", v)
        total += fv
    if abs(total - 1.0) > tol:
        raise ValueError(f"allocation must sum to 1 within {tol}, got {total}")
    return alloc


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- cause (gold wall)
@dataclass(frozen=True)
class Cause:
    """The routed object. Carries ONLY non-gold structural evidence.

    evidence: sorted tuple of structural markers derivable from the input itself
    (e.g. surface cues produced by a deterministic feature pass). There is NO field
    for the required operation or the expected outcome -- those live behind the
    verifier wall and this class cannot represent them.
    """

    cause_id: str
    evidence: tuple
    payload: str = ""

    def __post_init__(self):
        if not isinstance(self.evidence, tuple):
            raise TypeError("Cause.evidence must be a tuple of markers")
        for m in self.evidence:
            if not isinstance(m, str):
                raise TypeError("Cause.evidence markers must be strings")
        forbidden = {"required_op", "expected_expert", "expected_outcome", "gold"}
        if any(any(f in m for f in forbidden) for m in self.evidence):
            raise ValueError("Cause.evidence may not carry gold verifier fields")


# ---------------------------------------------------------------- effects
@dataclass(frozen=True)
class EffectCandidate:
    """A candidate Effect produced by CJTStep. NOT published until the latch says so."""

    producer_expert_id: str
    cause_id: str
    op_kind: str          # the transformation the expert actually performed
    payload: str          # the transformed content (deterministic)


class PublicationStatus(enum.Enum):
    PUBLISHED = "PUBLISHED"
    REFUSED = "REFUSED"
    ABSTAINED = "ABSTAINED"

    def _refuse(self, *_a, **_k):
        raise TypeError("PublicationStatus is a status, not a number")

    __mul__ = __rmul__ = __add__ = __radd__ = __float__ = __int__ = _refuse


@dataclass(frozen=True)
class CJTStepResult:
    """Return type of CJTStep(cause, bias, allocation, budget)."""

    effect_candidate: EffectCandidate
    observations: tuple
    intents: tuple                 # BiasUpdateIntents PROPOSED (committed only by coordinator)
    actual_compute_used: int
    producer_expert_id: str
    originating_tick: int
    authoritative_bias_version: int


# ---------------------------------------------------------------- authority-bearing intents
@dataclass(frozen=True)
class VersionedIntent:
    """RC-0.1 hardened intent envelope: every intent binds to the exact state it was
    computed from, the episode/tick it belongs to, and (for publication) the verifier
    receipt that authorizes it."""

    episode_id: str
    tick: int
    producer_id: str
    expert_id: str
    fld: str
    new_value: object
    base_state_version: int
    base_state_digest: str
    verifier_receipt_digest: str = ""   # required for publication-consequence intents
    reason: str = ""

    @property
    def intent_digest(self) -> str:
        return digest({"ep": self.episode_id, "tick": self.tick, "producer": self.producer_id,
                       "expert": self.expert_id, "fld": self.fld,
                       "base_v": self.base_state_version, "base_d": self.base_state_digest,
                       "vr": self.verifier_receipt_digest, "reason": self.reason})


@dataclass(frozen=True)
class EffectPublicationIntent:
    """Requests permission to publish an Effect. Distinct authority path from
    DiagnosticStateCommit. Must carry the verifier receipt digest."""

    episode_id: str
    tick: int
    effect: EffectCandidate
    verifier_receipt_digest: str


# ---------------------------------------------------------------- compute budget
@dataclass
class ComputeBudget:
    """Single frozen unit: CJT_EXPERT_EVALUATION. Vector budgets need registered
    conversion profiles and are out of scope for RC-0.1."""

    unit: str
    total: int
    left: int

    @classmethod
    def make(cls, total: int):
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise TypeError("budget total must be a nonnegative int")
        return cls(unit="CJT_EXPERT_EVALUATION", total=total, left=total)

    def spend(self, n: int = 1) -> bool:
        if self.left < n:
            return False
        self.left -= n
        return True
