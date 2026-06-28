"""CAS-Native predictor wrapper that accepts axis-priming hints.

This is the per-instance shim. Each ``CASInstance`` wraps the K=9
structured-token predictor exposed by
``cas_native.inference.predict_cas.load_predictor`` and records a
priming envelope (Noetic / Domain / Drive / Register / temperature)
alongside every prediction.

IMPORTANT: priming is RECORDED, NOT YET APPLIED.

Actual axis-priming requires logits-level intervention -- see e.g.
``cas_native.inference.constrained_sampling`` for the logits-mask machinery
and ``cas_native.inference.generate_samples_primed`` for the priming
surface. The K=9 baseline checkpoint exposes 12 classifier heads, not a
generative LM, so priming for this scaffold is plumbing-only: every
prediction round-trips with a ``priming_applied`` field that records what
SHOULD have been biased, but ``predictor.__call__`` itself is unchanged.

Once Lever 3 lands a generative or logits-exposed predictor, the call
shim here is the single place to wire the bias in. The interface stays
identical; callers do not change.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# --------------------------------------------------------------------------
# AxisPriming envelope
# --------------------------------------------------------------------------

VALID_DOMAINS: tuple[str, ...] = ("P", "C", "E", "O")
VALID_DRIVES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
VALID_REGISTERS: tuple[str, ...] = ("T", "A", "f", "E")


@dataclass(frozen=True)
class AxisPriming:
    """Per-rotation hint envelope.

    Each field is OPTIONAL. ``None`` means "do not bias this axis".

    Fields:
        noetic_bias: 0..9 or None. Which Noetic primitive to favour.
        domain_bias: "P"/"C"/"E"/"O" or None. Which domain to favour.
        drive_bias:  "F1".."F7" or None. Which Drive to favour.
        register_bias: "T"/"A"/"f"/"E" or None. Which Register to favour.
        temperature: sampling temperature in (0, ~2.0]. Default 0.7.
        label: optional human-readable label so traces stay readable
            ("noetic-2", "domain-P", "drive-F1", "register-T", etc.).
    """

    noetic_bias: Optional[int] = None
    domain_bias: Optional[str] = None
    drive_bias: Optional[str] = None
    register_bias: Optional[str] = None
    temperature: float = 0.7
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if self.noetic_bias is not None and not (0 <= int(self.noetic_bias) <= 9):
            raise ValueError(
                f"noetic_bias must be 0..9 or None, got {self.noetic_bias!r}"
            )
        if self.domain_bias is not None and self.domain_bias not in VALID_DOMAINS:
            raise ValueError(
                f"domain_bias must be in {VALID_DOMAINS} or None, got {self.domain_bias!r}"
            )
        if self.drive_bias is not None and self.drive_bias not in VALID_DRIVES:
            raise ValueError(
                f"drive_bias must be in {VALID_DRIVES} or None, got {self.drive_bias!r}"
            )
        if self.register_bias is not None and self.register_bias not in VALID_REGISTERS:
            raise ValueError(
                f"register_bias must be in {VALID_REGISTERS} or None, got {self.register_bias!r}"
            )
        if not (0.0 < float(self.temperature) <= 4.0):
            raise ValueError(
                f"temperature must be in (0, 4.0], got {self.temperature!r}"
            )

    def is_empty(self) -> bool:
        """True iff no axis is biased."""
        return (
            self.noetic_bias is None
            and self.domain_bias is None
            and self.drive_bias is None
            and self.register_bias is None
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Drop ``None`` fields for compactness in trace output.
        return {k: v for k, v in d.items() if v is not None}

    def short_label(self) -> str:
        """One-line slug suitable for trace lines."""
        if self.label:
            return self.label
        parts: list[str] = []
        if self.noetic_bias is not None:
            parts.append(f"^{self.noetic_bias}")
        if self.domain_bias is not None:
            parts.append(f"^{self.domain_bias}")
        if self.drive_bias is not None:
            parts.append(self.drive_bias)
        if self.register_bias is not None:
            parts.append(f"|{self.register_bias}")
        if not parts:
            return "neutral"
        return "".join(parts)


# --------------------------------------------------------------------------
# CASInstance wrapper
# --------------------------------------------------------------------------

@dataclass
class InstancePrediction:
    """Output of ``CASInstance.predict``.

    Wraps the underlying predictor's prediction dict with priming trace.
    """

    instance_name: str
    text: str
    priming_applied: dict[str, Any]
    prediction: dict[str, Any]
    elapsed_ms: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_name": self.instance_name,
            "text": self.text,
            "priming_applied": self.priming_applied,
            "prediction": self.prediction,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "notes": list(self.notes),
        }


class CASInstance:
    """Predictor wrapper accepting AxisPriming hints.

    The predictor is the K=9 structured-token classifier from
    ``cas_native.inference.predict_cas.load_predictor``. ``CASInstance``
    holds a name, a default priming, and a reference to the (already
    loaded) predictor. ``predict`` returns an ``InstancePrediction``.

    Multiple ``CASInstance`` objects can share the same underlying
    ``predictor`` -- there is no per-instance model state. The "instances"
    in the dialectic architecture are LOGICAL roles (Instance A, B, scorer)
    on top of a single weight set; this scaffolding does not duplicate
    weights. When Lever 3 introduces logits-exposed generation, the
    AxisPriming will translate into per-call logit adjustments at this
    layer, and instances may legitimately diverge in behaviour even with
    shared weights.
    """

    def __init__(
        self,
        predictor: Any,
        name: str,
        default_priming: Optional[AxisPriming] = None,
    ) -> None:
        if predictor is None:
            raise ValueError("predictor must not be None")
        if not name:
            raise ValueError("name must be a non-empty string")
        self.predictor = predictor
        self.name = str(name)
        self.default_priming = default_priming or AxisPriming()

    def predict(
        self,
        text: str,
        priming: Optional[AxisPriming] = None,
    ) -> InstancePrediction:
        """Run the predictor on ``text`` and return an InstancePrediction.

        ``priming`` overrides ``default_priming`` for this single call.
        Priming is recorded in ``InstancePrediction.priming_applied`` and
        passed through ``notes`` as a STUBBED marker until logits-level
        intervention lands.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")

        active_priming = priming if priming is not None else self.default_priming
        notes: list[str] = []

        if not active_priming.is_empty():
            # STUB: Real implementation will translate axis bias into a
            # logits mask / temperature schedule / token-prefix prepend
            # against the underlying predictor. K=9 baseline has no
            # logits surface to bias. Recording only.
            notes.append(
                f"priming-stubbed: {active_priming.short_label()} "
                "(logits intervention pending Lever 3)"
            )

        t0 = time.perf_counter()
        prediction = self.predictor(text)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if not isinstance(prediction, dict):
            raise RuntimeError(
                f"predictor returned non-dict: {type(prediction).__name__}"
            )

        return InstancePrediction(
            instance_name=self.name,
            text=text,
            priming_applied=active_priming.to_dict(),
            prediction=prediction,
            elapsed_ms=elapsed_ms,
            notes=notes,
        )

    def __repr__(self) -> str:
        return (
            f"CASInstance(name={self.name!r}, "
            f"default_priming={self.default_priming.short_label()!r})"
        )


__all__ = [
    "AxisPriming",
    "CASInstance",
    "InstancePrediction",
    "VALID_DOMAINS",
    "VALID_DRIVES",
    "VALID_REGISTERS",
]
