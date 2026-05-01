"""Structured-token schema for the CAS-Native tokenizer.

Every token produced by the tokenizer is a structured record carrying:

  - ``surface_text``    — the literal characters this token spans.
  - ``surface_span``    — ``(start, end)`` character offsets in the original
                          input. Preserved end-to-end for audit; the diagram
                          exporter walks attention back to these spans.
  - ``cas_signature``   — explicit CAS-axis affinity vectors (Noetic, Domain,
                          Drive, Register) plus role-tag annotations. The
                          first layer of CAS reasoning lives here, not in the
                          encoder.
  - ``confidence``      — float in ``[0.0, 1.0]`` indicating how sure the
                          tokenizer is of the signature.
  - ``source``          — provenance flag (LEXICON / LEARNED / CAS_NOTATION /
                          FALLBACK). Used by audit tooling to know how this
                          token's signature was assigned.
  - ``vocab_id``        — optional vocabulary index, filled in later by the
                          embedding-layer adapter. ``None`` until then.

This module defines only the data contract. The pre-tokenizer, CAS-notation
recognizer, lexicon, and assembler in sibling modules produce instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


SCHEMA_VERSION = "structured_token.v1"

# Axis cardinality — locked to the CAS v7.7 ontology.
NOETIC_AXIS_LEN = 10   # ^0 .. ^9
DOMAIN_AXIS_LEN = 4    # P, C, E, O
DRIVE_AXIS_LEN = 7     # F1 .. F7
REGISTER_AXIS_LEN = 4  # T, A, f, E

DOMAIN_LABELS: tuple[str, ...] = ("P", "C", "E", "O")
REGISTER_LABELS: tuple[str, ...] = ("T", "A", "f", "E")


def _zero(n: int) -> tuple[float, ...]:
    return tuple(0.0 for _ in range(n))


class TokenSource(str, Enum):
    """Provenance flag for a token's CAS signature.

    LEXICON       — signature came from a hand-built lexicon entry.
    LEARNED       — signature came from the learned CAS-axis tagger (Wave 3+).
    CAS_NOTATION  — token IS literal CAS notation; signature is a direct axis
                    assertion at confidence 1.0.
    FALLBACK      — no lexicon/notation/learned signal; neutral signature with
                    confidence 0.0. Encoder treats these as surface-only.
    """

    LEXICON = "lexicon"
    LEARNED = "learned"
    CAS_NOTATION = "cas_notation"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class CASSignature:
    """Per-token CAS-axis affinity vectors plus role-tag annotations.

    Each axis vector is a tuple of floats in ``[-1.0, +1.0]``:

      0.0   = no affinity on that axis position
      +1.0  = strong canonical affinity (e.g., ^2 attraction)
      -1.0  = strong inverse (e.g., F3 vitality depleted by "exhausted")

    The signature is *additive context* for the encoder: the embedding layer
    consumes these vectors alongside the vocab embedding, so the encoder is
    handed CAS structure rather than asked to discover it from raw IDs.

    ``role_tags`` carries non-axis labels that still inform CAS reasoning —
    e.g., ``self_reference``, ``confidence_hedge``, ``demonstrative``. These
    are used by the assembler and downstream IntentIR resolver.
    """

    noetic: tuple[float, ...] = field(default_factory=lambda: _zero(NOETIC_AXIS_LEN))
    domain: tuple[float, ...] = field(default_factory=lambda: _zero(DOMAIN_AXIS_LEN))
    drive: tuple[float, ...] = field(default_factory=lambda: _zero(DRIVE_AXIS_LEN))
    register: tuple[float, ...] = field(default_factory=lambda: _zero(REGISTER_AXIS_LEN))
    role_tags: tuple[str, ...] = ()

    @classmethod
    def neutral(cls) -> "CASSignature":
        """Empty signature — every axis zero, no role tags."""
        return cls()

    def is_neutral(self) -> bool:
        if any(v != 0.0 for v in self.noetic):
            return False
        if any(v != 0.0 for v in self.domain):
            return False
        if any(v != 0.0 for v in self.drive):
            return False
        if any(v != 0.0 for v in self.register):
            return False
        if self.role_tags:
            return False
        return True

    def validate(self) -> list[str]:
        errors: list[str] = []
        for axis_name, axis, expected_len in (
            ("noetic", self.noetic, NOETIC_AXIS_LEN),
            ("domain", self.domain, DOMAIN_AXIS_LEN),
            ("drive", self.drive, DRIVE_AXIS_LEN),
            ("register", self.register, REGISTER_AXIS_LEN),
        ):
            if len(axis) != expected_len:
                errors.append(
                    f"{axis_name} axis must be length {expected_len}, got {len(axis)}"
                )
                continue
            for index, value in enumerate(axis):
                if not isinstance(value, (int, float)):
                    errors.append(f"{axis_name}[{index}] must be numeric, got {type(value).__name__}")
                    continue
                if value < -1.0 or value > 1.0:
                    errors.append(f"{axis_name}[{index}]={value} outside [-1.0, +1.0]")
        for index, tag in enumerate(self.role_tags):
            if not isinstance(tag, str) or not tag:
                errors.append(f"role_tags[{index}] must be non-empty string")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "noetic": list(self.noetic),
            "domain": list(self.domain),
            "drive": list(self.drive),
            "register": list(self.register),
            "role_tags": list(self.role_tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CASSignature":
        return cls(
            noetic=tuple(float(v) for v in data.get("noetic", _zero(NOETIC_AXIS_LEN))),
            domain=tuple(float(v) for v in data.get("domain", _zero(DOMAIN_AXIS_LEN))),
            drive=tuple(float(v) for v in data.get("drive", _zero(DRIVE_AXIS_LEN))),
            register=tuple(float(v) for v in data.get("register", _zero(REGISTER_AXIS_LEN))),
            role_tags=tuple(str(t) for t in data.get("role_tags", ())),
        )


@dataclass(frozen=True)
class StructuredToken:
    """One unit of CAS-tokenized input.

    Token streams are ordered by ``surface_span[0]`` (start offset). The
    encoder consumes a contiguous list of these.
    """

    surface_text: str
    surface_span: tuple[int, int]
    cas_signature: CASSignature
    confidence: float = 0.0
    source: TokenSource = TokenSource.FALLBACK
    vocab_id: int | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.surface_text, str):
            errors.append("surface_text must be str")
        if not isinstance(self.surface_span, tuple) or len(self.surface_span) != 2:
            errors.append("surface_span must be (start, end) tuple")
        else:
            start, end = self.surface_span
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append("surface_span entries must be int")
            elif start < 0 or end < start:
                errors.append(f"surface_span invalid: ({start}, {end})")
        if not isinstance(self.confidence, (int, float)):
            errors.append("confidence must be numeric")
        elif self.confidence < 0.0 or self.confidence > 1.0:
            errors.append(f"confidence={self.confidence} outside [0.0, 1.0]")
        if not isinstance(self.source, TokenSource):
            errors.append("source must be TokenSource enum value")
        if self.vocab_id is not None and not isinstance(self.vocab_id, int):
            errors.append("vocab_id must be int or None")
        errors.extend(self.cas_signature.validate())
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "surface_text": self.surface_text,
            "surface_span": list(self.surface_span),
            "cas_signature": self.cas_signature.to_dict(),
            "confidence": float(self.confidence),
            "source": self.source.value,
            "vocab_id": self.vocab_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredToken":
        span = tuple(int(v) for v in data["surface_span"])
        if len(span) != 2:
            raise ValueError(f"surface_span must have 2 entries, got {span}")
        return cls(
            surface_text=str(data["surface_text"]),
            surface_span=(span[0], span[1]),
            cas_signature=CASSignature.from_dict(data.get("cas_signature", {})),
            confidence=float(data.get("confidence", 0.0)),
            source=TokenSource(data.get("source", TokenSource.FALLBACK.value)),
            vocab_id=data.get("vocab_id"),
        )


__all__ = [
    "SCHEMA_VERSION",
    "NOETIC_AXIS_LEN",
    "DOMAIN_AXIS_LEN",
    "DRIVE_AXIS_LEN",
    "REGISTER_AXIS_LEN",
    "DOMAIN_LABELS",
    "REGISTER_LABELS",
    "TokenSource",
    "CASSignature",
    "StructuredToken",
]
