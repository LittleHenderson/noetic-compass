"""CAS-notation recognizer: parse literal CAS expressions out of input.

When the input contains explicit CAS notation (training records, multi-turn
conversations referencing CAS, expert users typing CAS directly), those
spans are the strongest possible CAS signal: a direct axis assertion at
confidence 1.0. This module recognizes them and produces matching
``CASSignature`` instances.

Coverage spans CAS v7.7 notation:

  - ^n            Noetic primitive (^0..^9)
  - ^D            Domain primitive (^P, ^C, ^E, ^O)
  - F_k / Fk      Drive primitive (F1..F7)
  - |R            Register primitive (|T, |A, |f, |E)
  - |⟨R1,R2,...⟩  Register-set specification (v7.7)
  - ^n^D_{F_k}|R  Compound state
  - Ω_label       Production target
  - Θ            Recipe target opener
  - →, ←, ↔     Transition arrows
  - ∈ ∉ ⊂ ⊆ ⊃ ⊇ ∪ ∩ ∖ ∅  Set-relation operators

The recognizer is regex-driven, longest-match-first. It is *only* called on
``cas_candidate`` spans surfaced by the pre-tokenizer, so cost is bounded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .structured_token import (
    DOMAIN_AXIS_LEN,
    DOMAIN_LABELS,
    DRIVE_AXIS_LEN,
    NOETIC_AXIS_LEN,
    REGISTER_AXIS_LEN,
    REGISTER_LABELS,
    CASSignature,
)


# ---------------------------------------------------------------------------
# Match record.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CASNotationMatch:
    """A successfully matched CAS-notation span."""

    matched_text: str
    span: tuple[int, int]
    kind: str  # see KIND_* constants below
    signature: CASSignature


# Match kinds.
KIND_COMPOUND_STATE = "compound_state"        # ^n^D_{F_k}|R or partial
KIND_NOETIC = "noetic"                        # ^n alone
KIND_DOMAIN = "domain"                        # ^D alone
KIND_DRIVE = "drive"                          # F_k or Fk
KIND_REGISTER = "register"                    # |R alone
KIND_REGISTER_SET = "register_set"            # |⟨R1,R2,...⟩
KIND_OMEGA = "omega"                          # Ω_label
KIND_OMEGA_BARE = "omega_bare"                # bare Ω (no _label suffix)
KIND_THETA_BARE = "theta_bare"                # bare Θ (no opening paren)
KIND_LAMBDA_BARE = "lambda_bare"              # bare Λ (v7.6 leakage marker)
KIND_RECIPE_OPENER = "recipe_opener"          # Θ(
KIND_ARROW = "arrow"                          # →, ←, ↔
KIND_SET_RELATION = "set_relation"            # ∈ ∉ ⊂ ⊆ ⊃ ⊇ ∪ ∩ ∖ ∅
KIND_TYPED_CONSTRUCTOR = "typed_constructor"  # NoeticCluster / StateSet / etc.


# ---------------------------------------------------------------------------
# Regex patterns. ORDER MATTERS — longest match first.
# ---------------------------------------------------------------------------

_COMPOUND_FULL = re.compile(
    r"\^([0-9])\^([PCEO])_\{F([1-7])\}\|([TAfE])"
)
_COMPOUND_NOETIC_DOMAIN_DRIVE = re.compile(
    r"\^([0-9])\^([PCEO])_\{F([1-7])\}"
)
_COMPOUND_NOETIC_DOMAIN_REGISTER = re.compile(
    r"\^([0-9])\^([PCEO])\|([TAfE])"
)
_COMPOUND_NOETIC_DRIVE = re.compile(
    r"\^([0-9])_\{F([1-7])\}(?:\|([TAfE]))?"
)
_COMPOUND_NOETIC_REGISTER = re.compile(
    r"\^([0-9])\|([TAfE])"
)
_COMPOUND_NOETIC_DOMAIN = re.compile(
    r"\^([0-9])\^([PCEO])"
)
_REGISTER_SET = re.compile(
    r"\|⟨([TAfE](?:,[TAfE])*)⟩"
)
_NOETIC = re.compile(r"\^([0-9])")
_DOMAIN = re.compile(r"\^([PCEO])")
_DRIVE = re.compile(r"F_?([1-7])")
_REGISTER = re.compile(r"\|([TAfE])")
_OMEGA = re.compile(r"Ω_[A-Za-z][A-Za-z0-9_]*")
_OMEGA_BARE = re.compile(r"Ω(?![_A-Za-z0-9])")
_THETA_BARE = re.compile(r"Θ(?!\()")
_LAMBDA_BARE = re.compile(r"Λ(?![_A-Za-z0-9])")
_RECIPE_OPENER = re.compile(r"Θ\(")
_ARROW = re.compile(r"→|←|↔|->|<-|<->")
_SET_RELATION = re.compile(r"∈|∉|⊂|⊆|⊃|⊇|∪|∩|∖|∅")
# Typed meta-logic constructor names. Anchored full-word: must NOT be followed
# by a word-class character so we don't accidentally match a longer identifier
# that begins with one of these names.
_TYPED_CONSTRUCTOR = re.compile(
    r"(NoeticCluster|StateCluster|StateSet|RelationCluster|CoverOf|PartitionOf|Product)(?![A-Za-z0-9_])"
)


# Ordered match attempts: (pattern, kind, signature_builder).
_PATTERN_ORDER = [
    (_COMPOUND_FULL, KIND_COMPOUND_STATE, "_full"),
    (_COMPOUND_NOETIC_DOMAIN_DRIVE, KIND_COMPOUND_STATE, "_ndd"),
    (_COMPOUND_NOETIC_DOMAIN_REGISTER, KIND_COMPOUND_STATE, "_ndr"),
    (_COMPOUND_NOETIC_DRIVE, KIND_COMPOUND_STATE, "_nfk"),
    (_COMPOUND_NOETIC_REGISTER, KIND_COMPOUND_STATE, "_nr"),
    (_COMPOUND_NOETIC_DOMAIN, KIND_COMPOUND_STATE, "_nd"),
    (_REGISTER_SET, KIND_REGISTER_SET, "_rset"),
    (_NOETIC, KIND_NOETIC, "_n"),
    (_DOMAIN, KIND_DOMAIN, "_d"),
    (_DRIVE, KIND_DRIVE, "_f"),
    (_REGISTER, KIND_REGISTER, "_r"),
    (_OMEGA, KIND_OMEGA, "_om"),
    (_OMEGA_BARE, KIND_OMEGA_BARE, "_om_bare"),
    (_THETA_BARE, KIND_THETA_BARE, "_th_bare"),
    (_LAMBDA_BARE, KIND_LAMBDA_BARE, "_la_bare"),
    (_RECIPE_OPENER, KIND_RECIPE_OPENER, "_rec"),
    (_ARROW, KIND_ARROW, "_arr"),
    (_SET_RELATION, KIND_SET_RELATION, "_setrel"),
    (_TYPED_CONSTRUCTOR, KIND_TYPED_CONSTRUCTOR, "_typed"),
]


# ---------------------------------------------------------------------------
# Signature builders.
# ---------------------------------------------------------------------------


def _zero_axis(n: int) -> list[float]:
    return [0.0] * n


def _noetic_signature(noetic_idx: int) -> CASSignature:
    n = _zero_axis(NOETIC_AXIS_LEN)
    n[noetic_idx] = 1.0
    return CASSignature(
        noetic=tuple(n),
        domain=tuple(_zero_axis(DOMAIN_AXIS_LEN)),
        drive=tuple(_zero_axis(DRIVE_AXIS_LEN)),
        register=tuple(_zero_axis(REGISTER_AXIS_LEN)),
        role_tags=("cas_literal",),
    )


def _domain_signature(domain_label: str) -> CASSignature:
    d = _zero_axis(DOMAIN_AXIS_LEN)
    d[DOMAIN_LABELS.index(domain_label)] = 1.0
    return CASSignature(
        noetic=tuple(_zero_axis(NOETIC_AXIS_LEN)),
        domain=tuple(d),
        drive=tuple(_zero_axis(DRIVE_AXIS_LEN)),
        register=tuple(_zero_axis(REGISTER_AXIS_LEN)),
        role_tags=("cas_literal",),
    )


def _drive_signature(drive_idx_one_based: int) -> CASSignature:
    f = _zero_axis(DRIVE_AXIS_LEN)
    f[drive_idx_one_based - 1] = 1.0
    return CASSignature(
        noetic=tuple(_zero_axis(NOETIC_AXIS_LEN)),
        domain=tuple(_zero_axis(DOMAIN_AXIS_LEN)),
        drive=tuple(f),
        register=tuple(_zero_axis(REGISTER_AXIS_LEN)),
        role_tags=("cas_literal",),
    )


def _register_signature(register_label: str) -> CASSignature:
    r = _zero_axis(REGISTER_AXIS_LEN)
    r[REGISTER_LABELS.index(register_label)] = 1.0
    return CASSignature(
        noetic=tuple(_zero_axis(NOETIC_AXIS_LEN)),
        domain=tuple(_zero_axis(DOMAIN_AXIS_LEN)),
        drive=tuple(_zero_axis(DRIVE_AXIS_LEN)),
        register=tuple(r),
        role_tags=("cas_literal",),
    )


def _register_set_signature(labels: tuple[str, ...]) -> CASSignature:
    r = _zero_axis(REGISTER_AXIS_LEN)
    for label in labels:
        r[REGISTER_LABELS.index(label)] = 1.0
    return CASSignature(
        noetic=tuple(_zero_axis(NOETIC_AXIS_LEN)),
        domain=tuple(_zero_axis(DOMAIN_AXIS_LEN)),
        drive=tuple(_zero_axis(DRIVE_AXIS_LEN)),
        register=tuple(r),
        role_tags=("cas_literal", "register_set"),
    )


def _compound_signature(
    *,
    noetic_idx: int | None = None,
    domain_label: str | None = None,
    drive_idx: int | None = None,
    register_label: str | None = None,
) -> CASSignature:
    n = _zero_axis(NOETIC_AXIS_LEN)
    d = _zero_axis(DOMAIN_AXIS_LEN)
    f = _zero_axis(DRIVE_AXIS_LEN)
    r = _zero_axis(REGISTER_AXIS_LEN)
    if noetic_idx is not None:
        n[noetic_idx] = 1.0
    if domain_label is not None:
        d[DOMAIN_LABELS.index(domain_label)] = 1.0
    if drive_idx is not None:
        f[drive_idx - 1] = 1.0
    if register_label is not None:
        r[REGISTER_LABELS.index(register_label)] = 1.0
    return CASSignature(
        noetic=tuple(n),
        domain=tuple(d),
        drive=tuple(f),
        register=tuple(r),
        role_tags=("cas_literal", "compound_state"),
    )


def _omega_signature() -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "omega_target"))


def _omega_bare_signature() -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "omega_bare"))


def _theta_bare_signature() -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "theta_bare", "recipe_function"))


def _lambda_bare_signature() -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "lambda_bare", "leakage_marker"))


def _recipe_opener_signature() -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "recipe_opener"))


def _arrow_signature() -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "arrow"))


def _set_relation_signature(symbol: str) -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "set_relation", f"set_relation:{symbol}"))


def _typed_constructor_signature(name: str) -> CASSignature:
    return CASSignature(role_tags=("cas_literal", "typed_constructor", f"typed_constructor:{name}"))


# ---------------------------------------------------------------------------
# Public match function.
# ---------------------------------------------------------------------------


def match_cas_notation(
    text: str,
    start: int = 0,
    end: int | None = None,
) -> CASNotationMatch | None:
    """Try to match a CAS-notation literal at ``text[start:]``.

    Returns the longest match anchored at ``start`` (not anywhere later in
    the substring), or ``None`` if no pattern matches at that position.
    """
    if end is None:
        end = len(text)
    if start >= end:
        return None
    best: CASNotationMatch | None = None
    for pattern, kind, builder_key in _PATTERN_ORDER:
        match = pattern.match(text, start, end)
        if match is None:
            continue
        signature = _build_signature(builder_key, match)
        candidate = CASNotationMatch(
            matched_text=match.group(0),
            span=(match.start(), match.end()),
            kind=kind,
            signature=signature,
        )
        if best is None or (candidate.span[1] - candidate.span[0]) > (best.span[1] - best.span[0]):
            best = candidate
    return best


def find_all_cas_notation(text: str) -> list[CASNotationMatch]:
    """Scan the full input and return all (non-overlapping) CAS-notation
    matches, longest-first at each position. Useful for debugging and
    audit."""
    cursor = 0
    out: list[CASNotationMatch] = []
    while cursor < len(text):
        match = match_cas_notation(text, cursor)
        if match is None:
            cursor += 1
            continue
        out.append(match)
        cursor = match.span[1]
    return out


def _build_signature(builder_key: str, match: re.Match[str]) -> CASSignature:
    if builder_key == "_full":
        return _compound_signature(
            noetic_idx=int(match.group(1)),
            domain_label=match.group(2),
            drive_idx=int(match.group(3)),
            register_label=match.group(4),
        )
    if builder_key == "_ndd":
        return _compound_signature(
            noetic_idx=int(match.group(1)),
            domain_label=match.group(2),
            drive_idx=int(match.group(3)),
        )
    if builder_key == "_ndr":
        return _compound_signature(
            noetic_idx=int(match.group(1)),
            domain_label=match.group(2),
            register_label=match.group(3),
        )
    if builder_key == "_nfk":
        return _compound_signature(
            noetic_idx=int(match.group(1)),
            drive_idx=int(match.group(2)),
            register_label=match.group(3) if match.lastindex and match.group(3) else None,
        )
    if builder_key == "_nr":
        return _compound_signature(
            noetic_idx=int(match.group(1)),
            register_label=match.group(2),
        )
    if builder_key == "_nd":
        return _compound_signature(
            noetic_idx=int(match.group(1)),
            domain_label=match.group(2),
        )
    if builder_key == "_rset":
        labels = tuple(match.group(1).split(","))
        return _register_set_signature(labels)
    if builder_key == "_n":
        return _noetic_signature(int(match.group(1)))
    if builder_key == "_d":
        return _domain_signature(match.group(1))
    if builder_key == "_f":
        return _drive_signature(int(match.group(1)))
    if builder_key == "_r":
        return _register_signature(match.group(1))
    if builder_key == "_om":
        return _omega_signature()
    if builder_key == "_om_bare":
        return _omega_bare_signature()
    if builder_key == "_th_bare":
        return _theta_bare_signature()
    if builder_key == "_la_bare":
        return _lambda_bare_signature()
    if builder_key == "_rec":
        return _recipe_opener_signature()
    if builder_key == "_arr":
        return _arrow_signature()
    if builder_key == "_setrel":
        return _set_relation_signature(match.group(0))
    if builder_key == "_typed":
        return _typed_constructor_signature(match.group(1))
    raise ValueError(f"unknown builder_key {builder_key!r}")


__all__ = [
    "KIND_COMPOUND_STATE",
    "KIND_NOETIC",
    "KIND_DOMAIN",
    "KIND_DRIVE",
    "KIND_REGISTER",
    "KIND_REGISTER_SET",
    "KIND_OMEGA",
    "KIND_OMEGA_BARE",
    "KIND_THETA_BARE",
    "KIND_LAMBDA_BARE",
    "KIND_RECIPE_OPENER",
    "KIND_ARROW",
    "KIND_SET_RELATION",
    "KIND_TYPED_CONSTRUCTOR",
    "CASNotationMatch",
    "match_cas_notation",
    "find_all_cas_notation",
]
