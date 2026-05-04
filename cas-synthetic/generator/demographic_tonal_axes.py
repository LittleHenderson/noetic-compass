"""Demographic + tonal axes for CAS SDG surface variation.

This module is the canonical spec for both:

- Task #68 — SDG demographic-tonal expansion (this generator pipeline)
- Task #69 — demographic-robustness eval gate (sibling agent)

Both consumers MUST reference the profiles and tones defined here. Any
extension (a 9th profile, a 6th tone) belongs in this module so the eval
gate and the SDG pipeline see exactly the same surface taxonomy.

The 8 demographic profiles + 5 tonal registers were ratified on 2026-05-04
as part of the user's "Phase 1 SDG and Phase 2-3 architecture run in
parallel from day one" decision. They are deliberately curated (not the
full 8x5 = 40 cross-product) so the rule-based rewriter has tractable
template surface area while still covering the long tail of speaker
populations the deployed model will see.

Stratified sampling helpers in this module pick K (profile, tone) pairs
per canonical record deterministically from the 40 cell space. Default
K = 4. Sampling spreads across all 8 profiles before doubling, then
spreads across all 5 tones, then biases the residual cells toward
under-represented (profile, tone) combinations.

Public surface:

    PROFILES                tuple of DemographicProfile
    TONES                   tuple of TonalRegister
    PROFILE_BY_CODE         dict[str, DemographicProfile]
    TONE_BY_CODE            dict[str, TonalRegister]
    ALL_PROFILE_TONE_PAIRS  tuple of (profile_code, tone_code)
    stratified_sample(...)  K (profile, tone) draws given a seed
    profile_for(...)        lookup by code
    tone_for(...)           lookup by code

Pure stdlib. No external dependencies.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DemographicProfile:
    """A demographic speaker profile for surface-form variation.

    The fields below are deliberately concrete (not vibes-level): the
    rewriter consumes ``speech_traits``, ``typical_lexicon``, and
    ``avoid_lexicon`` directly as deterministic constraints.

    Fields
    ------
    code:
        Stable short identifier ("P1".."P8"). Used in metadata so
        downstream eval-gate joins survive renames.
    name:
        Human-readable lower_snake_case name.
    description:
        One-sentence prose summary used in spec doc and review tools.
    speech_traits:
        Tuple of qualitative phrasing markers. Examples: "direct",
        "technical", "indirect", "hedging".
    typical_lexicon:
        Concrete tokens / short phrases the profile WOULD use. The
        rewriter samples from this set when filling profile-flavored
        templates.
    avoid_lexicon:
        Tokens / phrases the profile would NOT use. The rewriter
        explicitly skips these in template selection.
    cultural_markers:
        Tags such as "US_idiomatic", "global_english_L2",
        "academic_register". Available to the eval gate for stratified
        slicing.
    """

    code: str
    name: str
    description: str
    speech_traits: tuple[str, ...]
    typical_lexicon: tuple[str, ...]
    avoid_lexicon: tuple[str, ...]
    cultural_markers: tuple[str, ...]


@dataclass(frozen=True)
class TonalRegister:
    """A tonal register applied on top of a demographic profile.

    Tone modifies the SAME content (same CAS structure, same labels)
    along an emotional / energy axis. Tone is orthogonal to profile: a
    young technical professional can speak in any of the 5 tones; a
    skeptical analyst can speak in any of the 5 tones; the rewriter
    composes them by first choosing profile lexicon and then layering
    tone-shaped phrasing on top.

    Fields
    ------
    code:
        Stable short identifier ("T1".."T5").
    name:
        Human-readable lower_snake_case name.
    description:
        One-sentence prose summary.
    sentence_starters:
        Phrases the rewriter can prepend ("Honestly,", "Look,").
    sentence_enders:
        Phrases the rewriter can append, or empty for tones that don't
        modify the tail.
    hedge_density:
        Float in [0.0, 1.0]. 0.0 = no "I think" / "maybe" softening.
        1.0 = saturated hedge phrasing. The rewriter samples hedge
        insertions proportional to this value.
    energy_level:
        One of "low", "medium", "high". Drives interjection density.
    sentence_length_bias:
        One of "short", "medium", "long". The rewriter chooses
        templates whose paraphrase fits the bias.
    """

    code: str
    name: str
    description: str
    sentence_starters: tuple[str, ...]
    sentence_enders: tuple[str, ...]
    hedge_density: float
    energy_level: str
    sentence_length_bias: str


# ---------------------------------------------------------------------------
# 8 demographic profiles
# ---------------------------------------------------------------------------

PROFILES: tuple[DemographicProfile, ...] = (
    DemographicProfile(
        code="P1",
        name="young_professional_technical",
        description=(
            "Early-career engineer or analyst, US-based, comfortable "
            "with technical jargon, prefers concise direct phrasing."
        ),
        speech_traits=("direct", "technical", "concise", "outcome_oriented"),
        typical_lexicon=(
            "optimize", "trade-off", "spec", "edge case", "stack", "ship",
            "iterate", "pipeline", "blocker", "scope", "MVP", "latency",
        ),
        avoid_lexicon=(
            "I reckon", "verily", "if I might be so bold", "old chap",
            "spiritually speaking",
        ),
        cultural_markers=("US_idiomatic", "tech_industry"),
    ),
    DemographicProfile(
        code="P2",
        name="senior_academic_humanities",
        description=(
            "University professor or senior researcher in a humanities "
            "discipline, English L1, formal register, careful qualified "
            "claims."
        ),
        speech_traits=("formal", "qualified", "citation_minded", "essayistic"),
        typical_lexicon=(
            "thus", "however", "one might suggest", "consider that",
            "the literature", "in some sense", "broadly speaking",
            "to a first approximation", "ostensibly", "qua",
        ),
        avoid_lexicon=(
            "lol", "tbh", "ngl", "vibes", "omg", "ship it", "blocker",
        ),
        cultural_markers=("academic_register", "humanities_lineage"),
    ),
    DemographicProfile(
        code="P3",
        name="mid_career_clinician_direct",
        description=(
            "Mid-career clinician (medical or therapeutic), action-"
            "oriented, plain language, comfortable with clinical "
            "framing."
        ),
        speech_traits=("plain", "action_oriented", "clinical", "patient_focused"),
        typical_lexicon=(
            "intake", "presentation", "course of action", "first line",
            "rule out", "clinically", "in my experience", "the patient",
            "treatment plan", "follow up",
        ),
        avoid_lexicon=(
            "ship", "stack", "epistemically speaking", "qua",
        ),
        cultural_markers=("clinical_register",),
    ),
    DemographicProfile(
        code="P4",
        name="global_english_indirect",
        description=(
            "Non-native English speaker (L2), uses indirect phrasing, "
            "carefully constructed sentences, occasional non-idiomatic "
            "constructions."
        ),
        speech_traits=("indirect", "polite", "careful", "L2_constructions"),
        typical_lexicon=(
            "perhaps", "maybe is possible", "if I may", "kindly",
            "please to explain", "I would like to know", "actually",
            "the same", "in the case of",
        ),
        avoid_lexicon=(
            "y'all", "gonna", "tbh", "lol", "ship it",
        ),
        cultural_markers=("global_english_L2", "indirect_register"),
    ),
    DemographicProfile(
        code="P5",
        name="lay_casual",
        description=(
            "Non-specialist, conversational, uses everyday English, "
            "comfortable with idioms and contractions."
        ),
        speech_traits=("casual", "idiomatic", "contractive", "everyday"),
        typical_lexicon=(
            "kinda", "sorta", "you know", "this thing", "the whole",
            "honestly", "like", "I dunno", "way too", "super",
        ),
        avoid_lexicon=(
            "qua", "ostensibly", "in some sense", "to a first approximation",
            "first line", "rule out",
        ),
        cultural_markers=("US_idiomatic", "casual_register"),
    ),
    DemographicProfile(
        code="P6",
        name="skeptical_analyst",
        description=(
            "Cautious analyst (often quant or policy), asks for evidence, "
            "challenges premises, prefers conditional framing."
        ),
        speech_traits=("skeptical", "conditional", "evidence_seeking", "tight"),
        typical_lexicon=(
            "what's the evidence", "assuming", "conditional on",
            "I'd want to see", "before I accept", "is it really the case",
            "what's the prior", "show me", "bear with me",
        ),
        avoid_lexicon=(
            "obviously", "clearly", "everyone knows", "vibes", "lol",
        ),
        cultural_markers=("analytic_register", "evidence_first"),
    ),
    DemographicProfile(
        code="P7",
        name="anxious_first_timer",
        description=(
            "First-time user, uncertain about the system, hedge-heavy "
            "phrasing, apologetic openings, prone to over-qualifying."
        ),
        speech_traits=("hedging", "apologetic", "uncertain", "verbose_qualifier"),
        typical_lexicon=(
            "sorry", "I'm new to this", "this might be a dumb question",
            "I think maybe", "is it okay if", "I'm not sure", "I hope",
            "if it's not too much trouble",
        ),
        avoid_lexicon=(
            "ship", "obviously", "trivially", "qua",
        ),
        cultural_markers=("novice_register", "deferential"),
    ),
    DemographicProfile(
        code="P8",
        name="confident_veteran",
        description=(
            "Domain expert with deep practice, terse, high information "
            "density, omits scaffolding the listener already has."
        ),
        speech_traits=("terse", "high_density", "expert", "elliptical"),
        typical_lexicon=(
            "look", "right", "the read is", "obvious move", "skip ahead",
            "cut to it", "the play is", "give me", "here's the thing",
        ),
        avoid_lexicon=(
            "I'm new to this", "is it okay if", "kindly please",
            "this might be a dumb question",
        ),
        cultural_markers=("expert_register", "terse"),
    ),
)


# ---------------------------------------------------------------------------
# 5 tonal registers
# ---------------------------------------------------------------------------

TONES: tuple[TonalRegister, ...] = (
    TonalRegister(
        code="T1",
        name="neutral",
        description="Matter-of-fact baseline; no affective coloring.",
        sentence_starters=("",),
        sentence_enders=("",),
        hedge_density=0.10,
        energy_level="medium",
        sentence_length_bias="medium",
    ),
    TonalRegister(
        code="T2",
        name="anxious",
        description=(
            "Uncertain, hedge-heavy phrasing; verbose softeners, "
            "apologies, second-guessing."
        ),
        sentence_starters=(
            "I think maybe", "I could be wrong but", "Sorry,",
            "I'm not totally sure but", "I might be misreading this but",
        ),
        sentence_enders=(
            ", I think", ", maybe", ", does that make sense?",
            ", I'm probably overthinking this",
        ),
        hedge_density=0.85,
        energy_level="low",
        sentence_length_bias="long",
    ),
    TonalRegister(
        code="T3",
        name="frustrated",
        description=(
            "Venting, complaint-shaped phrasing; short emphatic lines, "
            "negative-affect punctuation."
        ),
        sentence_starters=(
            "Honestly,", "Look,", "Ugh,", "Frankly,", "I keep running into this:",
        ),
        sentence_enders=(
            ".", "...", " and I'm tired of it.", " — every single time.",
        ),
        hedge_density=0.05,
        energy_level="high",
        sentence_length_bias="short",
    ),
    TonalRegister(
        code="T4",
        name="excited",
        description=(
            "Enthusiastic, high-energy phrasing; positive interjections, "
            "exclamatory punctuation."
        ),
        sentence_starters=(
            "Okay so", "Oh wow,", "This is great —", "Hey, quick one:",
            "Loving this:",
        ),
        sentence_enders=(
            "!", " — exciting stuff!", "!", " — neat right?",
        ),
        hedge_density=0.05,
        energy_level="high",
        sentence_length_bias="short",
    ),
    TonalRegister(
        code="T5",
        name="reflective",
        description=(
            "Introspective, slow, thoughtful; longer sentences, "
            "self-examining phrasing."
        ),
        sentence_starters=(
            "I've been sitting with this:", "Thinking out loud here —",
            "Slowly working through this:", "Let me take a moment.",
        ),
        sentence_enders=(
            ".", " — at least that's where I land for now.",
            " — though I suspect there's more to it.",
        ),
        hedge_density=0.40,
        energy_level="low",
        sentence_length_bias="long",
    ),
)


PROFILE_BY_CODE: dict[str, DemographicProfile] = {p.code: p for p in PROFILES}
TONE_BY_CODE: dict[str, TonalRegister] = {t.code: t for t in TONES}

ALL_PROFILE_TONE_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (p.code, t.code) for p in PROFILES for t in TONES
)


def profile_for(code: str) -> DemographicProfile:
    """Look up a profile by its short code; raises KeyError on miss."""
    try:
        return PROFILE_BY_CODE[code]
    except KeyError as exc:
        raise KeyError(
            f"unknown demographic profile code: {code!r}; "
            f"valid codes are {sorted(PROFILE_BY_CODE)}"
        ) from exc


def tone_for(code: str) -> TonalRegister:
    """Look up a tone by its short code; raises KeyError on miss."""
    try:
        return TONE_BY_CODE[code]
    except KeyError as exc:
        raise KeyError(
            f"unknown tonal register code: {code!r}; "
            f"valid codes are {sorted(TONE_BY_CODE)}"
        ) from exc


def stratified_sample(
    pairs: Sequence[tuple[str, str]] = ALL_PROFILE_TONE_PAIRS,
    *,
    k: int,
    seed: int,
) -> list[tuple[str, str]]:
    """Pick K (profile, tone) pairs deterministically from ``pairs``.

    The sampler aims to (a) cover as many distinct profiles as possible
    given K, then (b) cover as many distinct tones as possible, then
    (c) fall back to fully random selection from the unused remainder.
    Determinism: same ``pairs``, ``k``, ``seed`` always returns the same
    list (preserves output order).

    Parameters
    ----------
    pairs:
        Allowed (profile_code, tone_code) pool. Defaults to the full
        40 combinations.
    k:
        Number of pairs to return. Must be 1 <= k <= len(pairs).
    seed:
        RNG seed used for tie-breaking and residual fill. Passing the
        same canonical record's ``source_level2_id`` derived seed
        guarantees stability across reruns.

    Returns
    -------
    list[tuple[str, str]]
        K (profile, tone) pairs, no duplicates.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if k > len(pairs):
        raise ValueError(
            f"k={k} exceeds the {len(pairs)} available (profile, tone) pairs"
        )

    rng = random.Random(seed)
    pool = list(pairs)
    rng.shuffle(pool)

    chosen: list[tuple[str, str]] = []
    used_profiles: set[str] = set()
    used_tones: set[str] = set()

    # Phase 1: maximize profile coverage.
    remaining: list[tuple[str, str]] = []
    for pair in pool:
        if len(chosen) >= k:
            break
        profile_code, tone_code = pair
        if profile_code not in used_profiles:
            chosen.append(pair)
            used_profiles.add(profile_code)
            used_tones.add(tone_code)
        else:
            remaining.append(pair)

    # Phase 2: among the residual, prefer unused tones.
    if len(chosen) < k:
        deferred: list[tuple[str, str]] = []
        for pair in remaining:
            if len(chosen) >= k:
                deferred.append(pair)
                continue
            profile_code, tone_code = pair
            if tone_code not in used_tones:
                chosen.append(pair)
                used_profiles.add(profile_code)
                used_tones.add(tone_code)
            else:
                deferred.append(pair)
        remaining = deferred

    # Phase 3: random residual fill.
    if len(chosen) < k:
        for pair in remaining:
            if len(chosen) >= k:
                break
            chosen.append(pair)

    return chosen


__all__ = [
    "DemographicProfile",
    "TonalRegister",
    "PROFILES",
    "TONES",
    "PROFILE_BY_CODE",
    "TONE_BY_CODE",
    "ALL_PROFILE_TONE_PAIRS",
    "profile_for",
    "tone_for",
    "stratified_sample",
]
