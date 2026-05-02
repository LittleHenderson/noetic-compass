"""Generator for ``seed_lexicon.jsonl``.

The seed lexicon is the deterministic ground floor of CAS-axis tagging.
Entries are derived from:

  - The 10 authoritative Noetic definitions (Tootra-canonical, per CLAUDE.md).
  - The canonical colloquialism map (CLAUDE.md / CAS_FOUNDATIONAL_CLARIFICATIONS.md
    Clarification 6).
  - The authoritative verbs ("affinity for," "attracted toward," "adverse to,"
    "repelled by," "resonates with," "impregnated with," "triggers,"
    "brought to Mind").
  - The 4 Domains (P / C / E / O), 7 Drives (F1..F7), 4 Registers (T / A / f / E).
  - Demographic register variants (academic / working_class / child) for
    cross-register robustness eval coverage.

Anti-drift compliance (CLAUDE.md anti-drift annotations):

  - ^3 Negative entries are VISCERAL: aversion, repulsion, gut rejection.
    Analytical critique vocabulary (audit / scrutinize / find flaws / examine /
    decompose) maps to ^6 Male, NOT ^3.
  - ^8 Above/Cause entries are ASSOCIATIVE TRIGGERING: surfacing of related
    Ideas. Deductive causal reasoning is a compound (^6 + ^9), not ^8.
  - ^4 Vibration prefers etymological cognates ("struck a chord") where
    available.

Re-running this script regenerates ``seed_lexicon.jsonl`` deterministically.
Hand-edits to the JSONL should be backported here so the source of truth
stays in typed Python.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..structured_token import (
    DOMAIN_AXIS_LEN,
    DOMAIN_LABELS,
    DRIVE_AXIS_LEN,
    NOETIC_AXIS_LEN,
    REGISTER_AXIS_LEN,
    REGISTER_LABELS,
    CASSignature,
)
from .schema import LexiconEntry


def _zero(n: int) -> list[float]:
    return [0.0] * n


def _noetic_vec(idx: int, val: float) -> tuple[float, ...]:
    v = _zero(NOETIC_AXIS_LEN)
    v[idx] = val
    return tuple(v)


def _domain_vec(label: str, val: float) -> tuple[float, ...]:
    v = _zero(DOMAIN_AXIS_LEN)
    v[DOMAIN_LABELS.index(label)] = val
    return tuple(v)


def _drive_vec(idx_one_based: int, val: float) -> tuple[float, ...]:
    v = _zero(DRIVE_AXIS_LEN)
    v[idx_one_based - 1] = val
    return tuple(v)


def _register_vec(label: str, val: float) -> tuple[float, ...]:
    v = _zero(REGISTER_AXIS_LEN)
    v[REGISTER_LABELS.index(label)] = val
    return tuple(v)


def _sig(
    *,
    noetic: tuple[float, ...] | None = None,
    domain: tuple[float, ...] | None = None,
    drive: tuple[float, ...] | None = None,
    register: tuple[float, ...] | None = None,
    role_tags: tuple[str, ...] = (),
) -> CASSignature:
    return CASSignature(
        noetic=noetic if noetic is not None else tuple(_zero(NOETIC_AXIS_LEN)),
        domain=domain if domain is not None else tuple(_zero(DOMAIN_AXIS_LEN)),
        drive=drive if drive is not None else tuple(_zero(DRIVE_AXIS_LEN)),
        register=register if register is not None else tuple(_zero(REGISTER_AXIS_LEN)),
        role_tags=role_tags,
    )


# ---------------------------------------------------------------------------
# Seed entries.
#
# Confidence guidance:
#   1.00 — verbatim CAS notation literal (handled by cas_notation module, not lexicon)
#   0.90 — canonical colloquialism / authoritative verb / etymological cognate
#   0.80 — strong domain-specific term
#   0.70 — single content word with clear axis affinity
#   0.55 — common word with weak axis bias
# ---------------------------------------------------------------------------


def seed_entries() -> list[LexiconEntry]:
    e: list[LexiconEntry] = []

    # ---- Self-reference & Mind (^1) ----
    e.append(LexiconEntry(
        surface="I", signature=_sig(noetic=_noetic_vec(1, 0.6), role_tags=("self_reference",)),
        confidence=0.7, notes="first-person subject; ^1 Mind reference"))
    e.append(LexiconEntry(
        surface="me", signature=_sig(noetic=_noetic_vec(1, 0.5), role_tags=("self_reference",)),
        confidence=0.7, notes="first-person object pronoun"))
    e.append(LexiconEntry(
        surface="my", signature=_sig(noetic=_noetic_vec(1, 0.4), role_tags=("self_reference", "possessive")),
        confidence=0.65))
    e.append(LexiconEntry(
        surface="myself", signature=_sig(noetic=_noetic_vec(1, 0.5),
                                          role_tags=("self_reference", "reflexive")),
        confidence=0.6, notes="reflexive emphasis distinguishes from bare 'I/me/my'"))
    e.append(LexiconEntry(
        surface="we", signature=_sig(noetic=_noetic_vec(1, 0.55), role_tags=("self_reference", "plural")),
        confidence=0.6))
    e.append(LexiconEntry(
        surface="us", signature=_sig(noetic=_noetic_vec(1, 0.5), role_tags=("self_reference", "plural")),
        confidence=0.6))
    e.append(LexiconEntry(
        surface="our", signature=_sig(noetic=_noetic_vec(1, 0.4), role_tags=("self_reference", "possessive", "plural")),
        confidence=0.55))

    # ---- ^2 Positive (attraction, affinity) ----
    e.append(LexiconEntry(
        surface="drawn to", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.95), role_tags=("affinity_marker",)),
        confidence=0.95, notes="authoritative verb: 'attracted toward'"))
    e.append(LexiconEntry(
        surface="attracted to", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.95), role_tags=("affinity_marker",)),
        confidence=0.95, notes="authoritative verb"))
    e.append(LexiconEntry(
        surface="speaks to me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.85), role_tags=("affinity_marker",)),
        confidence=0.9, notes="canonical colloquialism for ^2"))
    e.append(LexiconEntry(
        surface="moth to a flame", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.95), role_tags=("affinity_marker", "metaphor")),
        confidence=0.95, notes="canonical colloquialism for ^2"))
    e.append(LexiconEntry(
        surface="can't resist", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.9), role_tags=("affinity_marker",)),
        confidence=0.9, notes="canonical colloquialism for ^2"))
    e.append(LexiconEntry(
        surface="love",
        signature=_sig(noetic=_noetic_vec(2, 0.7), register=_register_vec("f", 0.4)),
        confidence=0.7, notes="^2 attraction with affective register affinity"))
    e.append(LexiconEntry(
        surface="want", signature=_sig(noetic=_noetic_vec(2, 0.6)),
        confidence=0.65))
    e.append(LexiconEntry(
        surface="desire", signature=_sig(noetic=_noetic_vec(2, 0.75)),
        confidence=0.75))
    e.append(LexiconEntry(
        surface="crave",
        signature=_sig(noetic=_noetic_vec(2, 0.85), register=_register_vec("E", 0.3)),
        confidence=0.85, notes="visceral attraction; mild |E embodied tilt"))
    e.append(LexiconEntry(
        surface="appealing", signature=_sig(noetic=_noetic_vec(2, 0.8)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="attractive", signature=_sig(noetic=_noetic_vec(2, 0.7)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="like", signature=_sig(noetic=_noetic_vec(2, 0.6)),
        confidence=0.65, notes="weak ^2 affinity; very common word"))
    e.append(LexiconEntry(
        surface="adore",
        signature=_sig(noetic=_noetic_vec(2, 0.85), register=_register_vec("f", 0.4)),
        confidence=0.85, notes="strong attraction with affective register"))
    e.append(LexiconEntry(
        surface="enjoy", signature=_sig(noetic=_noetic_vec(2, 0.7)),
        confidence=0.75))
    e.append(LexiconEntry(
        surface="fond of", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.85), role_tags=("affinity_marker",)),
        confidence=0.85, notes="canonical-family for ^2"))
    e.append(LexiconEntry(
        surface="pulled toward", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.9), role_tags=("affinity_marker",)),
        confidence=0.9, notes="etymological cognate of authoritative 'attracted toward'"))
    e.append(LexiconEntry(
        surface="compelled by", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.85), role_tags=("affinity_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="magnetized by", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.85), role_tags=("affinity_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="partial to", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.8), role_tags=("affinity_marker",)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="taken with", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.8), role_tags=("affinity_marker",)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="smitten by", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(2, 0.85), role_tags=("affinity_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="fancy", signature=_sig(noetic=_noetic_vec(2, 0.7)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="delighted",
        signature=_sig(noetic=_noetic_vec(2, 0.75), register=_register_vec("f", 0.4)),
        confidence=0.75))

    # ---- ^3 Negative (VISCERAL aversion — anti-drift discipline) ----
    e.append(LexiconEntry(
        surface="averse to", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), role_tags=("aversion_marker",)),
        confidence=0.95, notes="authoritative verb: 'adverse to'"))
    e.append(LexiconEntry(
        surface="can't stomach", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), register=_register_vec("E", 0.3),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.95, notes="canonical visceral colloquialism (anti-drift exemplar)"))
    e.append(LexiconEntry(
        surface="rubs me the wrong way", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.9), register=_register_vec("f", 0.4),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.9, notes="canonical visceral colloquialism"))
    e.append(LexiconEntry(
        surface="wouldn't touch with a ten-foot pole", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), role_tags=("aversion_marker", "visceral")),
        confidence=0.95, notes="canonical visceral colloquialism"))
    e.append(LexiconEntry(
        surface="repelled by", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), role_tags=("aversion_marker",)),
        confidence=0.95, notes="authoritative verb"))
    e.append(LexiconEntry(
        surface="hate", signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.5)),
        confidence=0.85, notes="strong ^3 aversion with affective register"))
    e.append(LexiconEntry(
        surface="despise",
        signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="loathe",
        signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="abhor", signature=_sig(noetic=_noetic_vec(3, 0.9)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="repulsed",
        signature=_sig(noetic=_noetic_vec(3, 0.9), register=_register_vec("E", 0.3)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="disgusted",
        signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.5)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="nervous",
        signature=_sig(noetic=_noetic_vec(3, 0.7), register=_register_vec("f", 0.7),
                       drive=_drive_vec(3, -0.4)),
        confidence=0.85, notes="^3 with affective register and mild F3 vitality drag"))
    e.append(LexiconEntry(
        surface="detest",
        signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.4),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="can't bear", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.9), role_tags=("aversion_marker", "visceral")),
        confidence=0.9, notes="visceral colloquialism for ^3"))
    e.append(LexiconEntry(
        surface="can't stand", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.85), role_tags=("aversion_marker", "visceral")),
        confidence=0.85, notes="visceral colloquialism for ^3"))
    e.append(LexiconEntry(
        surface="makes me sick", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), register=_register_vec("E", 0.4),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.95, notes="visceral etymological cognate (literal sickness)"))
    e.append(LexiconEntry(
        surface="turns my stomach", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), register=_register_vec("E", 0.5),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.95, notes="visceral etymological cognate"))
    e.append(LexiconEntry(
        surface="makes my skin crawl", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.95), register=_register_vec("E", 0.5),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.95, notes="visceral etymological cognate"))
    e.append(LexiconEntry(
        surface="dread",
        signature=_sig(noetic=_noetic_vec(3, 0.8), register=_register_vec("f", 0.5),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="recoil from", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.9), register=_register_vec("E", 0.3),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.9, notes="etymological — physical recoil"))
    e.append(LexiconEntry(
        surface="sickens me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(3, 0.9), register=_register_vec("E", 0.4),
                       role_tags=("aversion_marker", "visceral")),
        confidence=0.9, notes="etymological cognate"))
    e.append(LexiconEntry(
        surface="ick",
        signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.5),
                       role_tags=("aversion_marker", "visceral", "interjection")),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="eww",
        signature=_sig(noetic=_noetic_vec(3, 0.85), register=_register_vec("f", 0.5),
                       role_tags=("aversion_marker", "visceral", "interjection")),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="ugh",
        signature=_sig(noetic=_noetic_vec(3, 0.7), register=_register_vec("f", 0.4),
                       role_tags=("aversion_marker", "visceral", "interjection")),
        confidence=0.65))

    # ---- ^4 Vibration (resonance, impression) ----
    e.append(LexiconEntry(
        surface="struck a chord", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.95), role_tags=("resonance_marker",)),
        confidence=0.95,
        notes="etymological cognate (literal vibration metaphor); strongest ^4 anchor"))
    e.append(LexiconEntry(
        surface="resonates with", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.95), role_tags=("resonance_marker",)),
        confidence=0.95, notes="authoritative verb"))
    e.append(LexiconEntry(
        surface="resonated", signature=_sig(noetic=_noetic_vec(4, 0.9)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="hit me hard", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.9), register=_register_vec("E", 0.3)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="made an impression", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="moved me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.85), register=_register_vec("f", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="resonate", signature=_sig(noetic=_noetic_vec(4, 0.9), role_tags=("resonance_marker",)),
        confidence=0.9, notes="etymological cognate"))
    e.append(LexiconEntry(
        surface="resonating", signature=_sig(noetic=_noetic_vec(4, 0.9), role_tags=("resonance_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="resonance", signature=_sig(noetic=_noetic_vec(4, 0.9), role_tags=("resonance_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="hit home", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.9), role_tags=("resonance_marker",)),
        confidence=0.9, notes="canonical colloquialism for ^4"))
    e.append(LexiconEntry(
        surface="hits home", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.9), role_tags=("resonance_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="struck me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(4, 0.85), role_tags=("resonance_marker",)),
        confidence=0.85, notes="etymological cognate"))
    e.append(LexiconEntry(
        surface="evocative", signature=_sig(noetic=_noetic_vec(4, 0.8)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="profound", signature=_sig(noetic=_noetic_vec(4, 0.6)),
        confidence=0.6,
        notes="weak ^4; word is broadly polysemous (profound silence, profound grief)"))

    # ---- ^5 Female (accumulated experience / composition) ----
    e.append(LexiconEntry(
        surface="sum of my experiences", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.95), role_tags=("composition_marker",)),
        confidence=0.95,
        notes="canonical pedagogical phrase: 'we are each the sum of our experiences'"))
    e.append(LexiconEntry(
        surface="who I am", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.85), role_tags=("composition_marker", "identity")),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="part of me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.85), role_tags=("composition_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="what makes me me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.95), role_tags=("composition_marker", "identity")),
        confidence=0.95))
    e.append(LexiconEntry(
        surface="shaped me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.9), role_tags=("composition_marker", "formation")),
        confidence=0.9,
        notes="^5 composition; ^7 (rhythmic process of shaping) overlap flagged for Wave 2-B tagger"))
    e.append(LexiconEntry(
        surface="formed me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.85), role_tags=("composition_marker", "formation")),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="ingrained",
        signature=_sig(noetic=_noetic_vec(5, 0.85), role_tags=("composition_marker",)),
        confidence=0.85, notes="lasting cognitive formation"))
    e.append(LexiconEntry(
        surface="baked in", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(5, 0.85), role_tags=("composition_marker",)),
        confidence=0.85))

    # ---- ^6 Male (decomposition / unpacking — anti-drift sink for analytical critique) ----
    e.append(LexiconEntry(
        surface="unpacking", signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.3)),
        confidence=0.85, notes="canonical colloquialism for ^6"))
    e.append(LexiconEntry(
        surface="breaking down", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.3)),
        confidence=0.85, notes="canonical colloquialism for ^6"))
    e.append(LexiconEntry(
        surface="pulling apart", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.3)),
        confidence=0.85, notes="canonical colloquialism for ^6"))
    e.append(LexiconEntry(
        surface="scrutinize", signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.5)),
        confidence=0.85, notes="^6, NOT ^3 — analytical critique is decomposition"))
    e.append(LexiconEntry(
        surface="audit", signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.5)),
        confidence=0.8, notes="^6, NOT ^3 — anti-drift exemplar"))
    e.append(LexiconEntry(
        surface="examine", signature=_sig(noetic=_noetic_vec(6, 0.7), register=_register_vec("A", 0.3)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="analyze", signature=_sig(noetic=_noetic_vec(6, 0.8), register=_register_vec("A", 0.5)),
        confidence=0.8, notes="explicit decomposition; |A register"))
    e.append(LexiconEntry(
        surface="decompose", signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="find flaws", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.8), register=_register_vec("A", 0.4)),
        confidence=0.8, notes="^6, NOT ^3 — analytical, not visceral"))
    e.append(LexiconEntry(
        surface="dissect",
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.4)),
        confidence=0.85, notes="analytical decomposition; ^6 not ^3"))
    e.append(LexiconEntry(
        surface="parse",
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.5)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="deconstruct",
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.5)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="investigate",
        signature=_sig(noetic=_noetic_vec(6, 0.8), register=_register_vec("A", 0.4)),
        confidence=0.8, notes="^6 not ^3 — investigation is decomposition"))
    e.append(LexiconEntry(
        surface="probe",
        signature=_sig(noetic=_noetic_vec(6, 0.8), register=_register_vec("A", 0.4)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="inspect",
        signature=_sig(noetic=_noetic_vec(6, 0.75), register=_register_vec("A", 0.3)),
        confidence=0.75))
    e.append(LexiconEntry(
        surface="pick apart", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.4)),
        confidence=0.85, notes="canonical colloquialism for ^6"))
    e.append(LexiconEntry(
        surface="take apart", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.85), register=_register_vec("A", 0.3)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="look into", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.7), register=_register_vec("A", 0.3)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="dig into", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(6, 0.75)),
        confidence=0.75))

    # ---- ^7 Rhythm (pattern, conditioning) ----
    e.append(LexiconEntry(
        surface="muscle memory", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(7, 0.95), register=_register_vec("E", 0.5),
                       role_tags=("rhythm_marker",)),
        confidence=0.95, notes="canonical colloquialism for ^7; |E embodied"))
    e.append(LexiconEntry(
        surface="practice makes perfect", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(7, 0.95), role_tags=("rhythm_marker",)),
        confidence=0.95, notes="canonical colloquialism for ^7"))
    e.append(LexiconEntry(
        surface="into a groove", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(7, 0.9), role_tags=("rhythm_marker",)),
        confidence=0.9, notes="canonical colloquialism for ^7"))
    e.append(LexiconEntry(
        surface="habit", signature=_sig(noetic=_noetic_vec(7, 0.8)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="routine", signature=_sig(noetic=_noetic_vec(7, 0.75)),
        confidence=0.75))
    e.append(LexiconEntry(
        surface="repeatedly", signature=_sig(noetic=_noetic_vec(7, 0.7)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="pattern", signature=_sig(noetic=_noetic_vec(7, 0.8), role_tags=("rhythm_marker",)),
        confidence=0.8, notes="primary rhythm/pattern sense"))
    e.append(LexiconEntry(
        surface="conditioning", signature=_sig(noetic=_noetic_vec(7, 0.85), role_tags=("rhythm_marker",)),
        confidence=0.85, notes="authoritative-verb-adjacent ('entraining/conditioning')"))
    e.append(LexiconEntry(
        surface="drilled in", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(7, 0.85), role_tags=("rhythm_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="repetition", signature=_sig(noetic=_noetic_vec(7, 0.8)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="rote", signature=_sig(noetic=_noetic_vec(7, 0.8)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="second nature", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(7, 0.9), role_tags=("rhythm_marker",)),
        confidence=0.9,
        notes="canonical colloquialism for ^7; ^5 (composition) overlap flagged for Wave 2-B tagger"))

    # ---- ^8 Above/Cause (ASSOCIATIVE triggering — anti-drift discipline) ----
    e.append(LexiconEntry(
        surface="reminds me of", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(8, 0.95), role_tags=("trigger_marker",)),
        confidence=0.95, notes="canonical colloquialism for ^8; associative, NOT deductive"))
    e.append(LexiconEntry(
        surface="that reminds me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(8, 0.9), role_tags=("trigger_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="made me think of", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(8, 0.9), role_tags=("trigger_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="one thing leads to another", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(8, 0.9), role_tags=("trigger_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="triggered", signature=_sig(noetic=_noetic_vec(8, 0.85), role_tags=("trigger_marker",)),
        confidence=0.85, notes="authoritative verb 'triggers'; ^8 not ^9"))
    e.append(LexiconEntry(
        surface="brought to mind", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(8, 0.95), role_tags=("trigger_marker",)),
        confidence=0.95,
        notes="trigger-side reading; canonical phrase 'X brought Y to mind'"))
    e.append(LexiconEntry(
        surface="called to mind", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(8, 0.9), role_tags=("trigger_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="prompted", signature=_sig(noetic=_noetic_vec(8, 0.8), role_tags=("trigger_marker",)),
        confidence=0.8, notes="associative trigger; ^8 not deductive"))
    e.append(LexiconEntry(
        surface="sparked", signature=_sig(noetic=_noetic_vec(8, 0.85), role_tags=("trigger_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="conjured", signature=_sig(noetic=_noetic_vec(8, 0.8), role_tags=("trigger_marker",)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="summoned", signature=_sig(noetic=_noetic_vec(8, 0.75), role_tags=("trigger_marker",)),
        confidence=0.75))

    # ---- ^9 Below/Effect (the Idea brought to mind) ----
    e.append(LexiconEntry(
        surface="popped into my head", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.95), role_tags=("effect_marker",)),
        confidence=0.95, notes="canonical colloquialism for ^9"))
    e.append(LexiconEntry(
        surface="it just clicked", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.9), role_tags=("effect_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="the thought came to me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.95), role_tags=("effect_marker",)),
        confidence=0.95))
    e.append(LexiconEntry(
        surface="out of nowhere I thought", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.9), role_tags=("effect_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="because", signature=_sig(noetic=_noetic_vec(9, 0.6), role_tags=("effect_link",)),
        confidence=0.6, notes="weak ^9 link; context-dependent"))
    e.append(LexiconEntry(
        surface="dawned on me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.95), role_tags=("effect_marker",)),
        confidence=0.95, notes="canonical colloquialism for ^9"))
    e.append(LexiconEntry(
        surface="occurred to me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.9), role_tags=("effect_marker",)),
        confidence=0.9, notes="canonical colloquialism for ^9"))
    e.append(LexiconEntry(
        surface="came to me", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.85), role_tags=("effect_marker",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="crossed my mind", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.9), role_tags=("effect_marker",)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="flashed in my head", is_multiword=True,
        signature=_sig(noetic=_noetic_vec(9, 0.85), role_tags=("effect_marker",)),
        confidence=0.85))
    # NOTE: 'then' was considered for ^9 effect_link but deferred to Phase 1B.
    # Temporal-sequence sense dominates in NL; would over-fire even at low confidence.
    # Reconsider with context-disambiguation rules (e.g., "and then [verb-of-thought]").

    # ---- Register markers ----
    e.append(LexiconEntry(
        surface="feel", signature=_sig(register=_register_vec("f", 0.9), role_tags=("register_marker",)),
        confidence=0.85, notes="strong |f register marker"))
    e.append(LexiconEntry(
        surface="feeling", signature=_sig(register=_register_vec("f", 0.85), role_tags=("register_marker",)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="felt", signature=_sig(register=_register_vec("f", 0.85)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="emotionally", signature=_sig(register=_register_vec("f", 0.9)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="think", signature=_sig(register=_register_vec("A", 0.8), domain=_domain_vec("C", 0.4)),
        confidence=0.8, notes="|A analytical register; C cognitive domain"))
    e.append(LexiconEntry(
        surface="consider", signature=_sig(register=_register_vec("A", 0.85), domain=_domain_vec("C", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="vision", signature=_sig(register=_register_vec("T", 0.8)),
        confidence=0.8, notes="|T transcendent register"))
    e.append(LexiconEntry(
        surface="purpose",
        signature=_sig(register=_register_vec("T", 0.85), drive=_drive_vec(7, 0.85)),
        confidence=0.85, notes="|T register + F7 Purpose drive"))
    e.append(LexiconEntry(
        surface="calling", signature=_sig(register=_register_vec("T", 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="physically", signature=_sig(register=_register_vec("E", 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="gut", signature=_sig(register=_register_vec("E", 0.85), role_tags=("embodied_marker",)),
        confidence=0.7,
        context_required=r"feel|sense|reaction|response|told|tells|tell",
        notes="|E only when used as gut-feeling; anatomy sense gets fallback"))
    e.append(LexiconEntry(
        surface="sense", signature=_sig(register=_register_vec("f", 0.7), role_tags=("register_marker",)),
        confidence=0.65,
        context_required=r"\b(feel|felt|inner|gut|deep|deeply|vague|strange|profound|quiet|growing)\b|\b(have|had|got|getting)\b\s+a\s+sense",
        notes="|f only when felt-sense reading is anchored; common/analytical sense falls to fallback"))
    e.append(LexiconEntry(
        surface="sensed", signature=_sig(register=_register_vec("f", 0.75), role_tags=("register_marker",)),
        confidence=0.75, notes="past-tense narrows polysemy vs bare 'sense'"))
    e.append(LexiconEntry(
        surface="reason",
        signature=_sig(register=_register_vec("A", 0.85), domain=_domain_vec("C", 0.4),
                       role_tags=("register_marker",)),
        confidence=0.85, notes="|A analytical register"))
    e.append(LexiconEntry(
        surface="reasoned",
        signature=_sig(register=_register_vec("A", 0.85), domain=_domain_vec("C", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="bodily", signature=_sig(register=_register_vec("E", 0.85), role_tags=("embodied_marker",)),
        confidence=0.85, notes="|E embodied register"))
    e.append(LexiconEntry(
        surface="broaden my horizons", is_multiword=True,
        signature=_sig(register=_register_vec("T", 0.85), role_tags=("register_marker",)),
        confidence=0.85,
        notes="|T figurative; bare 'horizon' falls to fallback to avoid literal-spatial misfire"))

    # ---- Drive markers ----
    e.append(LexiconEntry(
        surface="connection", signature=_sig(drive=_drive_vec(4, 0.85)),
        confidence=0.85, notes="F4 Connection drive"))
    e.append(LexiconEntry(
        surface="connect", signature=_sig(drive=_drive_vec(4, 0.7)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="wisdom", signature=_sig(drive=_drive_vec(2, 0.85)),
        confidence=0.85, notes="F2 Wisdom drive"))
    e.append(LexiconEntry(
        surface="vitality", signature=_sig(drive=_drive_vec(3, 0.85)),
        confidence=0.85, notes="F3 Vitality drive"))
    e.append(LexiconEntry(
        surface="energy", signature=_sig(drive=_drive_vec(3, 0.7)),
        confidence=0.7))
    e.append(LexiconEntry(
        surface="tired",
        signature=_sig(drive=_drive_vec(3, -0.7), register=_register_vec("E", 0.3)),
        confidence=0.85, notes="F3 vitality depletion; |E embodied"))
    e.append(LexiconEntry(
        surface="exhausted",
        signature=_sig(drive=_drive_vec(3, -0.85), register=_register_vec("E", 0.3)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="fatigued",
        signature=_sig(drive=_drive_vec(3, -0.85), register=_register_vec("E", 0.3)),
        confidence=0.85, register_variants=("academic",)))
    e.append(LexiconEntry(
        surface="structure", signature=_sig(drive=_drive_vec(6, 0.85)),
        confidence=0.85, notes="F6 Structure drive"))
    e.append(LexiconEntry(
        surface="agency", signature=_sig(drive=_drive_vec(5, 0.85)),
        confidence=0.85, notes="F5 Agency drive"))
    e.append(LexiconEntry(
        surface="unity", signature=_sig(drive=_drive_vec(1, 0.85)),
        confidence=0.85, notes="F1 Unity drive"))
    e.append(LexiconEntry(
        surface="drained",
        signature=_sig(drive=_drive_vec(3, -0.85), register=_register_vec("E", 0.3)),
        confidence=0.9, notes="F3 vitality depletion; |E embodied"))
    e.append(LexiconEntry(
        surface="depleted",
        signature=_sig(drive=_drive_vec(3, -0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="wiped out", is_multiword=True,
        signature=_sig(drive=_drive_vec(3, -0.85), register=_register_vec("E", 0.3)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="weary",
        signature=_sig(drive=_drive_vec(3, -0.7)),
        confidence=0.75))
    e.append(LexiconEntry(
        surface="burnt out", is_multiword=True,
        signature=_sig(drive=_drive_vec(3, -0.9)),
        confidence=0.9, notes="strong F3 depletion"))
    e.append(LexiconEntry(
        surface="bond", signature=_sig(drive=_drive_vec(4, 0.85)),
        confidence=0.85, notes="F4 Connection"))
    e.append(LexiconEntry(
        surface="kinship", signature=_sig(drive=_drive_vec(4, 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="belonging", signature=_sig(drive=_drive_vec(4, 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="meaning",
        signature=_sig(drive=_drive_vec(7, 0.85), register=_register_vec("T", 0.5)),
        confidence=0.85, notes="F7 Purpose with |T register affinity"))
    e.append(LexiconEntry(
        surface="vocation",
        signature=_sig(drive=_drive_vec(7, 0.85), register=_register_vec("T", 0.4)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="mission", signature=_sig(drive=_drive_vec(7, 0.8)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="control", signature=_sig(drive=_drive_vec(5, 0.75)),
        confidence=0.7, notes="F5 Agency; multi-sense (also restraint), keep modest"))
    e.append(LexiconEntry(
        surface="choice", signature=_sig(drive=_drive_vec(5, 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="self-determination", signature=_sig(drive=_drive_vec(5, 0.9)),
        confidence=0.9))
    e.append(LexiconEntry(
        surface="order", signature=_sig(drive=_drive_vec(6, 0.75)),
        confidence=0.7, notes="F6 Structure; multi-sense (sequence vs structure)"))
    e.append(LexiconEntry(
        surface="framework", signature=_sig(drive=_drive_vec(6, 0.85)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="insight", signature=_sig(drive=_drive_vec(2, 0.85)),
        confidence=0.85, notes="F2 Wisdom"))
    e.append(LexiconEntry(
        surface="understanding",
        signature=_sig(drive=_drive_vec(2, 0.8), register=_register_vec("A", 0.3)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="oneness", signature=_sig(drive=_drive_vec(1, 0.85)),
        confidence=0.85, notes="F1 Unity variant"))
    e.append(LexiconEntry(
        surface="wholeness", signature=_sig(drive=_drive_vec(1, 0.85)),
        confidence=0.85))

    # ---- Demographic register variants (cross-register robustness coverage) ----
    e.append(LexiconEntry(
        surface="hella tired", is_multiword=True,
        signature=_sig(drive=_drive_vec(3, -0.8), register=_register_vec("E", 0.3)),
        confidence=0.85, register_variants=("working_class",),
        notes="working-class register; same axis as 'exhausted'/'profoundly fatigued'"))
    e.append(LexiconEntry(
        surface="super sleepy", is_multiword=True,
        signature=_sig(drive=_drive_vec(3, -0.7), register=_register_vec("E", 0.3)),
        confidence=0.8, register_variants=("child",),
        notes="child register; same F3 axis as 'tired'"))
    e.append(LexiconEntry(
        surface="profoundly fatigued", is_multiword=True,
        signature=_sig(drive=_drive_vec(3, -0.9), register=_register_vec("E", 0.3)),
        confidence=0.9, register_variants=("academic",),
        notes="academic register; same F3 axis as 'exhausted'"))

    # ---- Confidence hedges (role tags, no axis) ----
    e.append(LexiconEntry(
        surface="kind of", is_multiword=True,
        signature=_sig(role_tags=("confidence_hedge", "ambiguity")),
        confidence=0.8,
        context_required=r"\b(am|is|are|was|were|feel|feels|felt|seem|seems|seemed|sound|sounds|look|looks)\b|␟\s*[a-z]+(ly)?\b",
        notes="hedge; requires linking-verb context to disambiguate from 'what kind of X'"))
    e.append(LexiconEntry(
        surface="sort of", is_multiword=True,
        signature=_sig(role_tags=("confidence_hedge", "ambiguity")),
        confidence=0.8,
        context_required=r"\b(am|is|are|was|were|feel|feels|felt|seem|seems|seemed)\b|␟\s*[a-z]+(ly)?\b"))
    e.append(LexiconEntry(
        surface="in a way", is_multiword=True,
        signature=_sig(role_tags=("confidence_hedge",)),
        confidence=0.8))
    e.append(LexiconEntry(
        surface="maybe", signature=_sig(role_tags=("confidence_hedge",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="perhaps", signature=_sig(role_tags=("confidence_hedge",)),
        confidence=0.85))
    e.append(LexiconEntry(
        surface="I guess", is_multiword=True,
        signature=_sig(role_tags=("confidence_hedge",)),
        confidence=0.85))

    # ---- Demonstratives & referents ----
    e.append(LexiconEntry(
        surface="this", signature=_sig(role_tags=("demonstrative",)),
        confidence=0.6))
    e.append(LexiconEntry(
        surface="that", signature=_sig(role_tags=("demonstrative",)),
        confidence=0.55))
    e.append(LexiconEntry(
        surface="it", signature=_sig(role_tags=("referent_pronoun",)),
        confidence=0.6))
    e.append(LexiconEntry(
        surface="about", signature=_sig(role_tags=("reference_marker",)),
        confidence=0.6))

    # ---- Operational domain markers ----
    e.append(LexiconEntry(
        surface="doing", signature=_sig(domain=_domain_vec("O", 0.85)),
        confidence=0.85, notes="O Operational domain"))
    e.append(LexiconEntry(
        surface="action", signature=_sig(domain=_domain_vec("O", 0.7)),
        confidence=0.7))

    return e


def write_seed_jsonl(path: Path) -> int:
    entries = seed_entries()
    path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    written = 0
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            errors = entry.validate()
            if errors:
                raise ValueError(f"seed entry {entry.surface!r} invalid: {errors}")
            if entry.surface_lower in seen:
                raise ValueError(f"duplicate seed entry surface={entry.surface!r}")
            seen.add(entry.surface_lower)
            payload: dict[str, Any] = entry.to_dict()
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            written += 1
    return written


def main() -> None:
    out_path = Path(__file__).resolve().parent / "seed_lexicon.jsonl"
    n = write_seed_jsonl(out_path)
    print(f"wrote {n} entries to {out_path}")


if __name__ == "__main__":
    main()
