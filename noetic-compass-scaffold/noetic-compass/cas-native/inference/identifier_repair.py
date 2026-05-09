"""Constrained post-generation repair for arbitrary symbolic identifiers.

The architecture-fix diagnostic (2026-05-09) showed that with the
cas_prefix_mask path enabled, the model learns operator aliases,
register words, and domain words cleanly via continuous semantic
learning, but does NOT learn to copy arbitrary symbolic identifiers
verbatim from prompt to output. The model produces "outcome called
rehearsal_67" when the source CAS specifies "Ω_decision_60", because
each Ω name is seen ~35 times across the corpus competing against
~1000 other unique Ω names — not enough to memorize against the rest
of parameter capacity.

This module is the **fast path fix**: extract symbolic identifiers
from source CAS, scan the generated English for identifier-shaped
slots, and repair-by-substitution so the output carries the exact
source identifiers. Longer-term, a pointer/copy attention head in
the decoder is the cleaner architectural answer; this module exists
to confirm exact-symbol copying is the only remaining bottleneck.

Repair scope (this iteration):
  - Ω names (recipe targets, side products, fusion outcomes)
  - Numeric coefficients (recipe stoichiometry)
  - Variable names (let-binding stage IDs)

Out of scope (continuous learning is the right path for these):
  - Operator-alias mismatches ("struck a chord" vs "rubs the wrong way")
  - Domain-word mismatches ("cognitive" vs "principled")
  - Register-word mismatches
  - Mode-count drift ("three modes" vs "two modes")

Slot-detection strategy: positional matching. The Nth Ω name in
source goes into the Nth Ω-shaped slot in gen output. For unique
identifiers (like Ω names that may repeat in source), we map by
position-of-first-occurrence so a recipe with main + side Ω lands
correctly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Source-side identifier extraction (ordered, position-preserving)
# ---------------------------------------------------------------------------

_SRC_OMEGA_RX = re.compile(r"(?:Ω|Omega)_([A-Za-z][A-Za-z0-9_]*)")
_SRC_COEFFICIENT_RX = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*\*")
_SRC_LET_VAR_RX = re.compile(r"\blet\s+([A-Za-z_][A-Za-z0-9_]*)\s*=")


@dataclass
class SourceIdentifiers:
    """All symbolic identifiers extracted from a source CAS expression,
    preserving order of appearance for positional repair."""
    omega_names_in_order: list[str] = field(default_factory=list)
    omega_unique_in_order: list[str] = field(default_factory=list)
    coefficients_in_order: list[str] = field(default_factory=list)
    variable_names_in_order: list[str] = field(default_factory=list)


def _canonical_coef(value: str) -> str:
    """Canonicalize a numeric coefficient string. Strips trailing zeros
    so "1.0" and "1" compare equal; "0.10" → "0.1"."""
    try:
        f = float(value)
    except ValueError:
        return value
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


def extract_source_identifiers(source_cas: str) -> SourceIdentifiers:
    """Extract ordered identifier lists from a source CAS expression.

    Coefficients are canonicalized (1.0 -> 1, 0.10 -> 0.1).

    Returns a :class:`SourceIdentifiers` with both ordered (with
    repeats) and unique-in-order lists for Ω names so callers can
    pick whichever matches their slot model.
    """
    omegas_ordered: list[str] = []
    seen_omegas: set[str] = set()
    omegas_unique_ordered: list[str] = []
    for m in _SRC_OMEGA_RX.finditer(source_cas):
        name = m.group(1)
        omegas_ordered.append(name)
        if name not in seen_omegas:
            seen_omegas.add(name)
            omegas_unique_ordered.append(name)

    coefs_ordered: list[str] = []
    for m in _SRC_COEFFICIENT_RX.finditer(source_cas):
        coefs_ordered.append(_canonical_coef(m.group(1)))

    vars_ordered: list[str] = []
    for m in _SRC_LET_VAR_RX.finditer(source_cas):
        vars_ordered.append(m.group(1))

    return SourceIdentifiers(
        omega_names_in_order=omegas_ordered,
        omega_unique_in_order=omegas_unique_ordered,
        coefficients_in_order=coefs_ordered,
        variable_names_in_order=vars_ordered,
    )


# ---------------------------------------------------------------------------
# Output-side slot detection
# ---------------------------------------------------------------------------

# Ω-shaped slots in English: anything after "called" / "outcome called" /
# "named outcome" / "to (produce|build) the outcome called". The capture
# group is the identifier candidate.
_GEN_OMEGA_SLOT_RX = re.compile(
    r"\b(?:outcome called|the outcome called|named outcome|named the outcome|outcome named)\s+"
    r"([A-Za-z][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

# Coefficients in English: standalone numbers acting as multipliers.
# The CAS-Native model emits coefficients in several surface forms,
# observed in v1 PREFIX128 5ep diverse eval (2026-05-09):
#   - "1 of something"               — base case
#   - "1 unit of something"          — quantity-noun form
#   - "1 units of something"         — pluralized quantity-noun form
#   - "1.5 times something"          — multiplier form
#   - "0.7 times"                    — multiplier (no following object yet)
#   - "1 part of"                    — fractional form
#   - "0.7 contribution from"        — contribution form (observed v1 5ep)
#   - "0.7 contribution of"          — contribution form variant
# We restrict to these qualifier-bearing patterns so we don't pick up
# unrelated numbers (e.g., serial suffixes inside Ω names like "_60").
_GEN_COEF_SLOT_RX = re.compile(
    r"(?<![\w.])"
    r"(\d+(?:\.\d+)?)"
    r"\s+(?:"
    r"of"
    r"|unit\s+of"
    r"|units\s+of"
    r"|times"
    r"|parts?\s+of"
    r"|contribution\s+(?:from|of)"
    r")\b"
)

# Variable-name slots: identifier-shaped tokens following naming verbs.
# We're permissive on the verb to catch "Let X name", "name X as", "X as".
_GEN_VAR_SLOT_RX = re.compile(
    r"\b(?:Let\s+|name(?:\s+\")?)?([a-z][A-Za-z]*\d?_[A-Za-z0-9_]+)",
)


@dataclass
class GenSlot:
    start: int
    end: int
    text: str          # the identifier token currently in the slot
    kind: str          # "omega" | "coefficient" | "variable"


def find_omega_slots(english: str) -> list[GenSlot]:
    """Find Ω-shaped slots in generated English, in left-to-right order."""
    slots: list[GenSlot] = []
    seen: set[str] = set()  # track unique Ω-tokens at first appearance
    for m in _GEN_OMEGA_SLOT_RX.finditer(english):
        token = m.group(1)
        slots.append(GenSlot(
            start=m.start(1), end=m.end(1), text=token, kind="omega",
        ))
    return slots


def find_coefficient_slots(english: str) -> list[GenSlot]:
    """Find coefficient slots in generated English ("X of ..." patterns)."""
    slots: list[GenSlot] = []
    for m in _GEN_COEF_SLOT_RX.finditer(english):
        slots.append(GenSlot(
            start=m.start(1), end=m.end(1),
            text=_canonical_coef(m.group(1)), kind="coefficient",
        ))
    return slots


def find_variable_slots(english: str) -> list[GenSlot]:
    """Find variable-name-shaped slots in generated English.

    Heuristic: tokens of shape ``[a-z][A-Za-z]*\\d?_[A-Za-z0-9_]+``
    (e.g. ``stageA0_3_0234``, ``vsrc_0460``, ``gamma_0244``).
    """
    slots: list[GenSlot] = []
    for m in _GEN_VAR_SLOT_RX.finditer(english):
        slots.append(GenSlot(
            start=m.start(1), end=m.end(1), text=m.group(1), kind="variable",
        ))
    return slots


# ---------------------------------------------------------------------------
# Repair (positional substitution)
# ---------------------------------------------------------------------------

@dataclass
class RepairLog:
    """Audit log of all substitutions applied during repair."""
    omega_substitutions: list[tuple[str, str]] = field(default_factory=list)
    coefficient_substitutions: list[tuple[str, str]] = field(default_factory=list)
    variable_substitutions: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.omega_substitutions)
            + len(self.coefficient_substitutions)
            + len(self.variable_substitutions)
        )


def _apply_positional_substitutions(
    text: str,
    slots: list[GenSlot],
    sources_in_order: list[str],
) -> tuple[str, list[tuple[str, str]]]:
    """Replace text within each slot's [start, end) range with the
    corresponding source identifier, in order. Substitutions are
    applied right-to-left so earlier positions don't shift.

    Returns (new_text, [(old, new), ...]) for every slot where the
    source identifier was different from the existing slot text.

    If the gen has more slots than the source has identifiers, the
    extra trailing slots are left unchanged. If the source has more
    identifiers than the gen has slots, the extra source identifiers
    are simply not inserted (this would be over-repair — we don't
    invent new slots).
    """
    if not slots or not sources_in_order:
        return text, []
    # Pair slots with sources by position, capped by min length.
    pairs = list(zip(slots, sources_in_order))
    # Build replacements (only where they differ).
    replacements: list[tuple[GenSlot, str, str]] = []  # (slot, old, new)
    for slot, src in pairs:
        if slot.text != src:
            replacements.append((slot, slot.text, src))
    # Apply right-to-left so earlier indices stay valid.
    new_text = text
    log: list[tuple[str, str]] = []
    for slot, old, new in sorted(replacements, key=lambda r: -r[0].start):
        new_text = new_text[: slot.start] + new + new_text[slot.end :]
        log.append((old, new))
    log.reverse()  # restore left-to-right order in the log
    return new_text, log


def repair_identifiers(
    *,
    source_cas: str,
    english: str,
    repair_omega: bool = True,
    repair_coefficients: bool = True,
    repair_variables: bool = True,
) -> tuple[str, RepairLog]:
    """Apply positional identifier repair to generated English.

    The order of operations matters: variable repair first (longest
    tokens, lowest collision risk), then Ω names, then coefficients
    (shortest tokens, easy to mis-target if applied first).
    """
    src = extract_source_identifiers(source_cas)
    repaired = english
    log = RepairLog()

    if repair_variables and src.variable_names_in_order:
        # Variables can repeat in the English (intro + later reference).
        # We map first-N gen slots to source variables in order. Future
        # iteration could co-reference-resolve repeat mentions.
        var_slots = find_variable_slots(repaired)
        repaired, subs = _apply_positional_substitutions(
            repaired, var_slots, src.variable_names_in_order,
        )
        log.variable_substitutions.extend(subs)

    if repair_omega and src.omega_unique_in_order:
        omega_slots = find_omega_slots(repaired)
        # Map source Ω names by FIRST occurrence — recipes typically
        # have the main Ω repeat (in Θ() and after =), so the unique-
        # in-order list aligns with the unique gen slots.
        # Fallback: if gen has more Ω mentions than source uniques
        # (because gen repeats), repair only as many as source has.
        repaired, subs = _apply_positional_substitutions(
            repaired, omega_slots, src.omega_unique_in_order,
        )
        log.omega_substitutions.extend(subs)

    if repair_coefficients and src.coefficients_in_order:
        coef_slots = find_coefficient_slots(repaired)
        repaired, subs = _apply_positional_substitutions(
            repaired, coef_slots, src.coefficients_in_order,
        )
        log.coefficient_substitutions.extend(subs)

    return repaired, log


# ---------------------------------------------------------------------------
# Eval metrics: exact-identifier recovery
# ---------------------------------------------------------------------------

@dataclass
class IdentifierRecoveryScore:
    omega_recovered: int = 0
    omega_total: int = 0
    coefficient_recovered: int = 0
    coefficient_total: int = 0
    variable_recovered: int = 0
    variable_total: int = 0

    @property
    def omega_rate(self) -> float:
        return self.omega_recovered / self.omega_total if self.omega_total else 1.0

    @property
    def coefficient_rate(self) -> float:
        return (
            self.coefficient_recovered / self.coefficient_total
            if self.coefficient_total else 1.0
        )

    @property
    def variable_rate(self) -> float:
        return (
            self.variable_recovered / self.variable_total
            if self.variable_total else 1.0
        )

    def to_dict(self) -> dict[str, float | int]:
        return {
            "omega_recovered": self.omega_recovered,
            "omega_total": self.omega_total,
            "omega_rate": round(self.omega_rate, 4),
            "coefficient_recovered": self.coefficient_recovered,
            "coefficient_total": self.coefficient_total,
            "coefficient_rate": round(self.coefficient_rate, 4),
            "variable_recovered": self.variable_recovered,
            "variable_total": self.variable_total,
            "variable_rate": round(self.variable_rate, 4),
        }


def score_identifier_recovery(
    *,
    source_cas: str,
    english: str,
) -> IdentifierRecoveryScore:
    """Score how many distinct source identifiers appear verbatim in the
    English output. Multiset semantics: a source identifier counts as
    recovered if it appears at least once in the English."""
    src = extract_source_identifiers(source_cas)
    score = IdentifierRecoveryScore()

    for om in src.omega_unique_in_order:
        score.omega_total += 1
        if re.search(rf"\b{re.escape(om)}\b", english):
            score.omega_recovered += 1

    for coef in src.coefficients_in_order:
        score.coefficient_total += 1
        # Match coef as a STANDALONE numeric token: not preceded by
        # word-char or dot (so "1" doesn't match inside "v_1") and
        # not followed by digit or dot (so "1" doesn't match inside
        # "1.2"). Also accept the explicit ".0" form ("1" matches "1.0").
        if (
            re.search(rf"(?<![\w.]){re.escape(coef)}(?![\d.])", english)
            or re.search(rf"(?<![\w.]){re.escape(coef)}\.0(?![\d.])", english)
        ):
            score.coefficient_recovered += 1

    for var in src.variable_names_in_order:
        score.variable_total += 1
        if re.search(rf"\b{re.escape(var)}\b", english):
            score.variable_recovered += 1

    return score


__all__ = [
    "SourceIdentifiers",
    "GenSlot",
    "RepairLog",
    "IdentifierRecoveryScore",
    "extract_source_identifiers",
    "find_omega_slots",
    "find_coefficient_slots",
    "find_variable_slots",
    "repair_identifiers",
    "score_identifier_recovery",
]
