"""rc01_types.py -- RC-0.1/0.2 typed objects, HARDENED per OWNER DIRECTIVE RC-0.2.

Repairs in this revision (owner audit of 60b36e06):
  - VersionedIntent.intent_digest now INCLUDES a canonical digest of new_value
    (the owner reproduced a collision: two intents differing only in new_value had
    identical digests -- fixed and test-locked).
  - ComputeBudget.spend accepts ONLY a positive non-bool int (spend(-1) previously
    INCREASED the budget; spend(True) was accepted -- both reproduced by the owner).
  - EffectPublicationIntent upgraded to a real authority object (episode, tick,
    cause_id, effect_digest, producer, verdict, verifier receipt digest, base state
    version+digest, its own intent digest).
  - VerifierReceipt is a typed, sealed object issued only by the verifier capability;
    raw-string receipt registration is dead.
  - Deep immutability: Cause/EffectCandidate/CJTStepResult/BiasState-nested containers
    must be deeply immutable (validated recursively); numeric fields validated
    fail-closed (bool/NaN/inf/negative rejected).

Deterministic CPU only. No neural network. No randomness, no wall-clock in
state-bearing paths.
"""
from __future__ import annotations

import enum
import hashlib
import json
import math
from dataclasses import dataclass

from rc0_types import BiasState  # frozen Bias shell (hardened in rc0_types)


# ---------------------------------------------------------------- guards
def require_finite_nonneg(name: str, v) -> float:
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


def require_pos_int(name: str, v) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{name} must be an int (bool rejected), got {type(v).__name__}")
    if v <= 0:
        raise ValueError(f"{name} must be a positive int, got {v!r}")
    return v


def require_nonneg_int(name: str, v) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{name} must be an int (bool rejected), got {type(v).__name__}")
    if v < 0:
        raise ValueError(f"{name} must be >= 0, got {v!r}")
    return v


def require_str(name: str, v) -> str:
    if not isinstance(v, str):
        raise TypeError(f"{name} must be a str, got {type(v).__name__}")
    return v


IMMUTABLE_LEAF_TYPES = (str, int, float, bool, bytes, type(None))


def require_deeply_immutable(name: str, v):
    """RC-0.3 allow-list: a state-bearing value may contain ONLY canonical immutable
    leaves (str/int/float/bool/bytes/None), tuples/frozensets of them, or enum members.
    Arbitrary custom objects are rejected even inside tuples -- a frozen wrapper around
    a mutable object is still mutable through that object."""
    import enum as _enum
    if isinstance(v, tuple):
        for i, x in enumerate(v):
            require_deeply_immutable(f"{name}[{i}]", x)
        return v
    if isinstance(v, frozenset):
        for x in v:
            require_deeply_immutable(name + "{}", x)
        return v
    if isinstance(v, bool) or isinstance(v, IMMUTABLE_LEAF_TYPES):
        return v
    if isinstance(v, _enum.Enum):
        return v
    raise TypeError(f"{name} contains {type(v).__name__}, which is not on the canonical "
                    "immutable allow-list (str/int/float/bool/bytes/None/tuple/frozenset/enum)")


def validate_allocation(alloc: dict, tol: float = 1e-9) -> dict:
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
    """The routed object. Carries ONLY non-gold structural evidence; the TYPE has no
    slot for required operations or expected outcomes."""

    cause_id: str
    evidence: tuple
    payload: str = ""

    def __post_init__(self):
        require_str("Cause.cause_id", self.cause_id)
        require_str("Cause.payload", self.payload)
        if not isinstance(self.evidence, tuple):
            raise TypeError("Cause.evidence must be a tuple of markers")
        for m in self.evidence:
            require_str("Cause.evidence[]", m)
        forbidden = {"required_op", "expected_expert", "expected_outcome", "gold"}
        if any(any(f in m for f in forbidden) for m in self.evidence):
            raise ValueError("Cause.evidence may not carry gold verifier fields")


# ---------------------------------------------------------------- effects
@dataclass(frozen=True)
class EffectCandidate:
    """A candidate Effect ENVELOPE produced by CJTStep (RC-0.3: carries its originating
    tick and the Bias snapshot it was computed from, so a stale Effect cannot be
    re-presented at a later tick or laundered past a changed Bias). NOT published until
    the publication coordinator commits it."""

    producer_expert_id: str
    cause_id: str
    op_kind: str
    payload: str
    originating_tick: int = 0
    base_bias_version: int = 0
    base_bias_digest: str = ""

    def __post_init__(self):
        for f in ("producer_expert_id", "cause_id", "op_kind", "payload",
                  "base_bias_digest"):
            require_str(f"EffectCandidate.{f}", getattr(self, f))
        require_nonneg_int("EffectCandidate.originating_tick", self.originating_tick)
        require_nonneg_int("EffectCandidate.base_bias_version", self.base_bias_version)

    @property
    def effect_digest(self) -> str:
        return digest({"producer": self.producer_expert_id, "cause": self.cause_id,
                       "op": self.op_kind, "payload": self.payload,
                       "tick": self.originating_tick,
                       "bias_v": self.base_bias_version,
                       "bias_d": self.base_bias_digest})


class PublicationStatus(enum.Enum):
    PUBLISHED = "PUBLISHED"
    REFUSED = "REFUSED"
    ABSTAINED = "ABSTAINED"

    def _refuse(self, *_a, **_k):
        raise TypeError("PublicationStatus is a status, not a number")

    __mul__ = __rmul__ = __add__ = __radd__ = __float__ = __int__ = _refuse


@dataclass(frozen=True)
class CJTStepResult:
    """(E_t, proposed updates) = CJTStep(C_t, B_t). Proposed updates are (field, value,
    reason) tuples the ENGINE wraps into VersionedIntents -- they are real proposals,
    not decoration."""

    effect_candidate: EffectCandidate
    observations: tuple
    proposed_updates: tuple            # ((fld, value, reason), ...)
    actual_compute_used: int
    producer_expert_id: str
    originating_tick: int
    authoritative_bias_version: int
    base_state_version: int = 0        # snapshot captured AT STEP TIME (RC-0.3)
    base_state_digest: str = ""        # intents are built from THESE, never a later read

    def __post_init__(self):
        if not isinstance(self.effect_candidate, EffectCandidate):
            raise TypeError("CJTStepResult.effect_candidate must be an EffectCandidate")
        require_deeply_immutable("CJTStepResult.observations", self.observations)
        require_deeply_immutable("CJTStepResult.proposed_updates", self.proposed_updates)
        require_pos_int("CJTStepResult.actual_compute_used", self.actual_compute_used)
        require_nonneg_int("CJTStepResult.originating_tick", self.originating_tick)
        require_nonneg_int("CJTStepResult.authoritative_bias_version",
                           self.authoritative_bias_version)
        require_nonneg_int("CJTStepResult.base_state_version", self.base_state_version)
        require_str("CJTStepResult.base_state_digest", self.base_state_digest)


# ---------------------------------------------------------------- verifier receipts
@dataclass(frozen=True)
class VerifierReceipt:
    """Typed, sealed verifier receipt. Issued ONLY by the verifier capability (which
    seals it with a private token); the coordinator validates the seal through the
    verifier-provided validator, so raw strings and self-built receipts are rejected.
    Bound to episode, tick, cause, the FULL Effect digest, producer, verdict, and
    examiner identity. Consumed exactly once per publication."""

    episode_id: str
    tick: int
    cause_id: str
    effect_digest: str
    producer_expert_id: str
    verdict: str
    examiner_id: str
    receipt_version: int
    seal: str = ""    # set by the verifier at issue time

    def __post_init__(self):
        require_str("VerifierReceipt.episode_id", self.episode_id)
        require_nonneg_int("VerifierReceipt.tick", self.tick)
        require_str("VerifierReceipt.cause_id", self.cause_id)
        require_str("VerifierReceipt.effect_digest", self.effect_digest)
        require_str("VerifierReceipt.producer_expert_id", self.producer_expert_id)
        if self.verdict not in ("intended", "opposite", "off_axis", "unassessed"):
            raise ValueError(f"unknown verdict {self.verdict!r}")
        require_str("VerifierReceipt.examiner_id", self.examiner_id)
        require_pos_int("VerifierReceipt.receipt_version", self.receipt_version)

    @property
    def content(self) -> dict:
        return {"ep": self.episode_id, "tick": self.tick, "cause": self.cause_id,
                "effect": self.effect_digest, "producer": self.producer_expert_id,
                "verdict": self.verdict, "examiner": self.examiner_id,
                "version": self.receipt_version}

    @property
    def receipt_digest(self) -> str:
        return digest(self.content)


# ---------------------------------------------------------------- versioned intents
@dataclass(frozen=True)
class VersionedIntent:
    """Hardened intent envelope. intent_digest INCLUDES the canonical digest of
    new_value (RC-0.2 repair of the owner-reproduced collision)."""

    episode_id: str
    tick: int
    producer_id: str
    expert_id: str
    fld: str
    new_value: object
    base_state_version: int
    base_state_digest: str
    verifier_receipt_digest: str = ""
    reason: str = ""

    def __post_init__(self):
        require_str("VersionedIntent.episode_id", self.episode_id)
        require_nonneg_int("VersionedIntent.tick", self.tick)
        require_str("VersionedIntent.producer_id", self.producer_id)
        require_str("VersionedIntent.expert_id", self.expert_id)
        require_str("VersionedIntent.fld", self.fld)
        require_nonneg_int("VersionedIntent.base_state_version", self.base_state_version)
        require_str("VersionedIntent.base_state_digest", self.base_state_digest)

    @property
    def new_value_digest(self) -> str:
        return digest(self.new_value)

    @property
    def intent_digest(self) -> str:
        return digest({"ep": self.episode_id, "tick": self.tick, "producer": self.producer_id,
                       "expert": self.expert_id, "fld": self.fld,
                       "new_value_digest": self.new_value_digest,
                       "base_v": self.base_state_version, "base_d": self.base_state_digest,
                       "vr": self.verifier_receipt_digest, "reason": self.reason})


@dataclass(frozen=True)
class DiagnosticCommitReceipt:
    """Emitted ONLY by the state coordinator after a SUCCESSFUL atomic commit (RC-0.3).
    Publication requires this receipt: a Boolean named committed is not authority."""

    episode_id: str
    tick: int
    cause_id: str
    effect_digest: str
    verifier_receipt_digest: str
    expert_id: str
    pre_state_version: int
    pre_state_digest: str
    post_state_version: int
    post_state_digest: str
    committed_intent_digests: tuple

    @property
    def commit_digest(self) -> str:
        return digest({"ep": self.episode_id, "tick": self.tick, "cause": self.cause_id,
                       "effect": self.effect_digest, "vr": self.verifier_receipt_digest,
                       "expert": self.expert_id,
                       "pre": (self.pre_state_version, self.pre_state_digest),
                       "post": (self.post_state_version, self.post_state_digest),
                       "intents": self.committed_intent_digests})


@dataclass(frozen=True)
class EffectPublicationIntent:
    """The REAL publication authority object. RC-0.3: carries the DiagnosticCommitReceipt
    digest; the PublicationCoordinator validates base/post state versions AND digests
    against the authoritative coordinator and the named commit receipt -- the fields
    are load-bearing, not decorative."""

    episode_id: str
    tick: int
    cause_id: str
    effect_digest: str
    producer_expert_id: str
    verdict: str
    verifier_receipt_digest: str
    base_state_version: int
    base_state_digest: str
    diagnostic_commit_digest: str = ""

    def __post_init__(self):
        require_str("EffectPublicationIntent.episode_id", self.episode_id)
        require_nonneg_int("EffectPublicationIntent.tick", self.tick)
        require_str("EffectPublicationIntent.cause_id", self.cause_id)
        require_str("EffectPublicationIntent.effect_digest", self.effect_digest)
        require_str("EffectPublicationIntent.producer_expert_id", self.producer_expert_id)
        require_str("EffectPublicationIntent.verifier_receipt_digest", self.verifier_receipt_digest)
        require_nonneg_int("EffectPublicationIntent.base_state_version", self.base_state_version)
        require_str("EffectPublicationIntent.base_state_digest", self.base_state_digest)

    @property
    def intent_digest(self) -> str:
        return digest({"ep": self.episode_id, "tick": self.tick, "cause": self.cause_id,
                       "effect": self.effect_digest, "producer": self.producer_expert_id,
                       "verdict": self.verdict, "vr": self.verifier_receipt_digest,
                       "base_v": self.base_state_version, "base_d": self.base_state_digest,
                       "dc": self.diagnostic_commit_digest})


# ---------------------------------------------------------------- compute budget
class ComputeBudget:
    """Single frozen unit: CJT_EXPERT_EVALUATION. RC-0.3 hardening: construction is
    validated (no negative totals, no arbitrary units), attributes are read-only
    properties, and spend() is the ONLY mutator (positive non-bool int only)."""

    __slots__ = ("_unit", "_total", "_left", "_sealed")

    def __init__(self, unit: str, total: int, left: int):
        if unit != "CJT_EXPERT_EVALUATION":
            raise ValueError("budget unit is frozen to CJT_EXPERT_EVALUATION")
        require_nonneg_int("budget total", total)
        require_nonneg_int("budget left", left)
        if left > total:
            raise ValueError("budget left cannot exceed total")
        object.__setattr__(self, "_unit", unit)
        object.__setattr__(self, "_total", total)
        object.__setattr__(self, "_left", left)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name, value):
        if getattr(self, "_sealed", False):
            raise AttributeError("ComputeBudget attributes are read-only; use spend()")
        object.__setattr__(self, name, value)

    @property
    def unit(self):
        return self._unit

    @property
    def total(self):
        return self._total

    @property
    def left(self):
        return self._left

    @classmethod
    def make(cls, total: int):
        require_nonneg_int("budget total", total)
        return cls(unit="CJT_EXPERT_EVALUATION", total=total, left=total)

    def spend(self, n: int = 1) -> bool:
        require_pos_int("budget spend amount", n)
        if self._left < n:
            return False
        object.__setattr__(self, "_left", self._left - n)
        return True
