"""Legacy TKS 40-element specificity hints for CABS compression.

The original TKS format used four planes (A/B/C/D) and ten elements per
plane.  CAS v7.x now represents the same 40-state surface as
``^noetic^domain`` over P/C/E/O domains and noetics 0-9.

This module keeps a compact, paraphrased bridge for memory compression.  It is
not a theological or metaphysical assertion layer; it is a specificity glossary
that helps CAS-SDG compress old memories into more precise CAS records without
dumping long source prose into context.
"""

from __future__ import annotations

from dataclasses import dataclass


LEGACY_DOMAIN_TO_CAS: dict[str, str] = {
    "A": "P",  # Spiritual -> Principled / foundational
    "B": "C",  # Mental -> Cognitive / thinking
    "C": "E",  # Emotional -> Evaluative / feeling-judgment
    "D": "O",  # Physical -> Operational / embodied action
}

LEGACY_DOMAIN_LABEL: dict[str, str] = {
    "A": "spiritual",
    "B": "mental",
    "C": "emotional",
    "D": "physical",
}

CAS_DOMAIN_LABEL: dict[str, str] = {
    "P": "principled",
    "C": "cognitive",
    "E": "evaluative",
    "O": "operational",
}

LEGACY_ELEMENT_TO_NOETIC: dict[int, int] = {
    1: 1,  # Mind
    2: 2,  # Positive
    3: 3,  # Negative
    4: 4,  # Vibration
    5: 5,  # Female
    6: 6,  # Male
    7: 7,  # Rhythm
    8: 8,  # Above
    9: 9,  # Below
    10: 0,  # Idea
}

NOETIC_LABEL: dict[int, str] = {
    0: "idea",
    1: "mind",
    2: "positive",
    3: "negative",
    4: "vibration",
    5: "female",
    6: "male",
    7: "rhythm",
    8: "above",
    9: "below",
}


@dataclass(frozen=True)
class TKS40Element:
    """One legacy TKS element mapped to its current CAS state."""

    legacy_code: str
    legacy_domain: str
    legacy_element: int
    cas_domain: str
    cas_noetic: int
    cas_expression: str
    label: str
    compression_hint: str


_HINTS: dict[str, str] = {
    # A: Spiritual -> Principled
    "A1": "ultimate-purpose awareness, spiritual identity, spirit-guided mind",
    "A2": "soul-evolving truth, virtue, peace, spiritual agreement",
    "A3": "soul disturbance, vice, fear, spiritual hindrance or trial",
    "A4": "aura, psychic/aetheric energy, purpose-frequency",
    "A5": "spiritual nurturance, soul-growth yearning, divine-mother matrix",
    "A6": "austere spiritual discipline, trial, transmission of influence",
    "A7": "life-journey rhythm, destiny pattern, spiritual ups and downs",
    "A8": "inner meaning, esoteric truth, initiation, higher moral view",
    "A9": "outer symbol without inner grasp, exoteric surface, lower ethics",
    "A10": "spiritual idea or aspect, true self, Akashic/spirit-world content",
    # B: Mental -> Cognitive
    "B1": "ego, memory, analysis, logic-driven mental processing",
    "B2": "clarity, optimism, sanity, benevolent or enlightened thought",
    "B3": "confusion, indecision, dissonance, pessimistic or malicious thought",
    "B4": "thought resonance, psychic mind-energy, brainwave signature",
    "B5": "imagination, openness, creativity, subconscious/right-brain thought",
    "B6": "logic, critique, rigidity, conscious/left-brain thought",
    "B7": "thought pattern, recurring idea, transition between ego states",
    "B8": "complex comprehension, contemplation, high intelligence or insight",
    "B9": "limited comprehension, menial focus, low-importance thought",
    "B10": "mental idea or aspect, content existing primarily in mind",
    # C: Emotional -> Evaluative
    "C1": "emotional awareness, feeling-driven choice, emotional intelligence",
    "C2": "joy, calm, love, pleasurable or harmonizing feeling",
    "C3": "sadness, anger, resentment, loneliness, painful feeling",
    "C4": "mood energy, ambiance, felt aura of person/place/event",
    "C5": "compassion, sympathy, acceptance, sensual/feminine feeling",
    "C6": "aggression, pride, dominance, masculine-coded feeling",
    "C7": "mood swing, emotional sequence, feeling-cycle",
    "C8": "emotional resolve, healed psyche, mastery over lower emotions",
    "C9": "overwhelm, being controlled by emotion",
    "C10": "emotional sheath of an idea, residual felt presence or ambiance",
    # D: Physical -> Operational
    "D1": "body/brain hardware, cellular substrate, machine or physical host",
    "D2": "ordered parts, symmetry, functional complementarity",
    "D3": "misplaced parts, disorder, dysfunction, sickness or asymmetry",
    "D4": "physical wave/oscillation, light, sound, radiation, heat signature",
    "D5": "receiver, womb, receptacle, physical female/nurturing container",
    "D6": "transmitter, seed, appendage, physical male/delivering force",
    "D7": "movement routine, music, time, dance, exercise, repeated action",
    "D8": "height, high quality, high grade, elevated material/social status",
    "D9": "lowness, poor quality, low integrity, lower material/social status",
    "D10": "physical idea or aspect, material manifestation, inert matter",
}


def _build_element(code: str, hint: str) -> TKS40Element:
    legacy_domain = code[0]
    legacy_element = int(code[1:])
    cas_domain = LEGACY_DOMAIN_TO_CAS[legacy_domain]
    cas_noetic = LEGACY_ELEMENT_TO_NOETIC[legacy_element]
    cas_expression = f"^{cas_noetic}^{cas_domain}"
    label = (
        f"{LEGACY_DOMAIN_LABEL[legacy_domain]} "
        f"{NOETIC_LABEL[cas_noetic]}"
    )
    return TKS40Element(
        legacy_code=code,
        legacy_domain=legacy_domain,
        legacy_element=legacy_element,
        cas_domain=cas_domain,
        cas_noetic=cas_noetic,
        cas_expression=cas_expression,
        label=label,
        compression_hint=hint,
    )


TKS40_ELEMENTS: tuple[TKS40Element, ...] = tuple(
    _build_element(code, hint) for code, hint in sorted(_HINTS.items())
)

TKS40_BY_LEGACY_CODE: dict[str, TKS40Element] = {
    element.legacy_code: element for element in TKS40_ELEMENTS
}

TKS40_BY_CAS_EXPRESSION: dict[str, TKS40Element] = {
    element.cas_expression: element for element in TKS40_ELEMENTS
}


def lookup_tks40(legacy_code: str) -> TKS40Element:
    """Return specificity metadata for a legacy code such as ``A1``."""
    code = legacy_code.strip().upper()
    try:
        return TKS40_BY_LEGACY_CODE[code]
    except KeyError as exc:
        raise KeyError(f"unknown TKS40 legacy code: {legacy_code!r}") from exc


def lookup_cas_state(cas_expression: str) -> TKS40Element:
    """Return specificity metadata for a current CAS state such as ``^1^P``."""
    expr = cas_expression.strip()
    try:
        return TKS40_BY_CAS_EXPRESSION[expr]
    except KeyError as exc:
        raise KeyError(f"unknown mapped CAS state: {cas_expression!r}") from exc


def compression_hint_for_cas(cas_expression: str) -> str:
    """Short specificity hint for CAS-SDG memory compression prompts."""
    element = lookup_cas_state(cas_expression)
    return element.compression_hint


def compression_prompt_fragment(cas_expression: str) -> str:
    """Render one compact hint block for a memory-compression prompt."""
    element = lookup_cas_state(cas_expression)
    return (
        f"{element.cas_expression} ({element.label}; legacy "
        f"{element.legacy_code}): {element.compression_hint}"
    )


__all__ = [
    "CAS_DOMAIN_LABEL",
    "LEGACY_DOMAIN_LABEL",
    "LEGACY_DOMAIN_TO_CAS",
    "LEGACY_ELEMENT_TO_NOETIC",
    "NOETIC_LABEL",
    "TKS40_BY_CAS_EXPRESSION",
    "TKS40_BY_LEGACY_CODE",
    "TKS40_ELEMENTS",
    "TKS40Element",
    "compression_hint_for_cas",
    "compression_prompt_fragment",
    "lookup_cas_state",
    "lookup_tks40",
]
