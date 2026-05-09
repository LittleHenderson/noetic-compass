"""Legacy TKS 28 Foundations specificity hints.

The source document ``28 fOUNDATIONS 1.0.pdf`` enumerates the cross-product of
seven foundations and four worlds.  CAS v7.5 represents the same structural
surface as ``F1-F7`` drives crossed with registers ``T/A/f/E``.

This module keeps compact paraphrases for CAS-SDG memory compression.  The
legacy source's religious, magical, and culturally specific claims are not
asserted by this code; they are translated into drive-register specificity
hints so old memories can be compressed into CABS records with more precision.
"""

from __future__ import annotations

from dataclasses import dataclass


LEGACY_WORLD_TO_REGISTER: dict[str, str] = {
    "a": "T",  # Spiritual -> Transcendent
    "b": "A",  # Mental -> Analytical
    "c": "f",  # Emotional -> Affective
    "d": "E",  # Physical -> Embodied
}

LEGACY_WORLD_LABEL: dict[str, str] = {
    "a": "spiritual",
    "b": "mental",
    "c": "emotional",
    "d": "physical",
}

REGISTER_LABEL: dict[str, str] = {
    "T": "transcendent",
    "A": "analytical",
    "f": "affective",
    "E": "embodied",
}

DRIVE_LABEL: dict[int, str] = {
    1: "unity",
    2: "wisdom",
    3: "vitality",
    4: "connection",
    5: "agency",
    6: "structure",
    7: "purpose",
}


@dataclass(frozen=True)
class TKS28Foundation:
    """One legacy Foundation x World entry mapped to CAS Drive x Register."""

    legacy_code: str
    foundation: int
    legacy_world: str
    cas_drive: int
    cas_register: str
    cas_expression: str
    label: str
    compression_hint: str


_HINTS: dict[str, str] = {
    # Foundation 1: Unity / desire to be and be with ultimate source.
    "1a": "ultimate union, transcending ego, deepest meaning, contemplative devotion",
    "1b": "mental model of ultimate unity, humility before mystery, thought-as-communion",
    "1c": "awe, surrender, longing, peace or emptiness around sacred connection",
    "1d": "bodily ritual, pilgrimage, fasting, endurance, physicalized longing for unity",
    # Foundation 2: Wisdom / insight / knowledge.
    "2a": "hidden truth, esoteric insight, symbol-reading, cosmic pattern intuition",
    "2b": "analysis, discernment, synthesis, pattern recognition, lifelong learning",
    "2c": "gut knowing, emotional intelligence, empathy, heart-centered clarity",
    "2d": "embodied know-how, muscle memory, tactile learning, mind-body integration",
    # Foundation 3: Vitality / life / health.
    "3a": "soul-level vigor, subtle-body purification, spiritual immunity",
    "3b": "cognitive resilience, mindfulness, neuroplasticity, mental nourishment",
    "3c": "enthusiasm, resilient joy, cathartic release, self-compassion",
    "3d": "fitness, nutrition, longevity, physical performance, bodily health",
    # Foundation 4: Connection / companionship / love / friendship.
    "4a": "soul-deep bond, lineage, unconditional love, unity beyond separation",
    "4b": "intellectual compatibility, shared models, mutual understanding",
    "4c": "affection, intimacy, vulnerability, empathy, emotional bonding",
    "4d": "touch, proximity, co-presence, hugging, dance, physical bonding",
    # Foundation 5: Agency / power / influence / control.
    "5a": "will shaping reality, mastery, distant influence, spiritual authority",
    "5b": "strategic thinking, persuasion, focus, ethical use of mental influence",
    "5c": "charisma, emotional self-mastery, moving or guiding others' feelings",
    "5d": "bodily strength, presence, territorial control, physical dominance",
    # Foundation 6: Structure / material food and things.
    "6a": "spiritual sustenance, talismanic objects, subtle blueprint of matter",
    "6b": "mental resources, frameworks, thought-forms, doctrines, food for thought",
    "6c": "comfort objects, nostalgia, material gratitude, aesthetic nourishment",
    "6d": "tangible resources, consumption, security, possessions, material abundance",
    # Foundation 7: Purpose / lust, sex, reproduction, generativity.
    "7a": "sacred union, elevated generative energy, spiritual rebirth, creation-plane intent",
    "7b": "intellectual reproduction, debate, spreading ideas, replicating mentality",
    "7c": "romantic desire, bonding, fertility feeling, transmitting emotion to another",
    "7d": "bodily pleasure, procreation, fertility, sensual drive, reproductive success",
}


def _build_foundation(code: str, hint: str) -> TKS28Foundation:
    foundation = int(code[:-1])
    world = code[-1]
    register = LEGACY_WORLD_TO_REGISTER[world]
    cas_expression = f"F{foundation}|{register}"
    label = f"{DRIVE_LABEL[foundation]} in the {REGISTER_LABEL[register]} register"
    return TKS28Foundation(
        legacy_code=code,
        foundation=foundation,
        legacy_world=world,
        cas_drive=foundation,
        cas_register=register,
        cas_expression=cas_expression,
        label=label,
        compression_hint=hint,
    )


TKS28_FOUNDATIONS: tuple[TKS28Foundation, ...] = tuple(
    _build_foundation(code, hint)
    for code, hint in sorted(_HINTS.items(), key=lambda item: (int(item[0][:-1]), item[0][-1]))
)

TKS28_BY_LEGACY_CODE: dict[str, TKS28Foundation] = {
    foundation.legacy_code: foundation for foundation in TKS28_FOUNDATIONS
}

TKS28_BY_CAS_EXPRESSION: dict[str, TKS28Foundation] = {
    foundation.cas_expression: foundation for foundation in TKS28_FOUNDATIONS
}


def lookup_tks28(legacy_code: str) -> TKS28Foundation:
    """Return specificity metadata for a legacy code such as ``1a``."""
    code = legacy_code.strip().lower()
    try:
        return TKS28_BY_LEGACY_CODE[code]
    except KeyError as exc:
        raise KeyError(f"unknown TKS28 legacy code: {legacy_code!r}") from exc


def lookup_drive_register(cas_expression: str) -> TKS28Foundation:
    """Return specificity metadata for a drive-register expression."""
    expr = cas_expression.strip()
    try:
        return TKS28_BY_CAS_EXPRESSION[expr]
    except KeyError as exc:
        raise KeyError(f"unknown mapped drive-register: {cas_expression!r}") from exc


def foundation_hint_for_drive_register(cas_expression: str) -> str:
    """Short specificity hint for CAS-SDG memory compression prompts."""
    return lookup_drive_register(cas_expression).compression_hint


def foundation_prompt_fragment(cas_expression: str) -> str:
    """Render a compact Drive x Register hint block."""
    foundation = lookup_drive_register(cas_expression)
    return (
        f"{foundation.cas_expression} ({foundation.label}; legacy "
        f"{foundation.legacy_code}): {foundation.compression_hint}"
    )


__all__ = [
    "DRIVE_LABEL",
    "LEGACY_WORLD_LABEL",
    "LEGACY_WORLD_TO_REGISTER",
    "REGISTER_LABEL",
    "TKS28_BY_CAS_EXPRESSION",
    "TKS28_BY_LEGACY_CODE",
    "TKS28_FOUNDATIONS",
    "TKS28Foundation",
    "foundation_hint_for_drive_register",
    "foundation_prompt_fragment",
    "lookup_drive_register",
    "lookup_tks28",
]
