"""Native NL SDG v1 — 5K seed corpus for the from-scratch CAS-Native decoder.

This script produces a paired (CAS expression, English reply) corpus that
trains the from-scratch 6-layer / d_model=512 / ~50M-param decoder one of
the four sibling agents is building. It is the proof-of-pipeline seed for
the full 100K-340K corpus described in
``docs/working/native_nl_sdg_strategy_2026_05_04.md``.

THREE-TIER DESIGN

  Tier 1 (~2,500 records, $0, ~1 hour) — deterministic templates.
    Source: ``noetic-compass/cas-native/data/english_generator.py`` style
    templates extended with v7.5/v7.6/v7.7 grammar. Axis-complete: every
    (Noetic, Domain, Drive, Register) cell is hit at least once.
    Generator model: ``deterministic``.

  Tier 2 (~2,500 records, $0-$50, 1-2 hours) — Claude API rewrites of
    Tier 1 across (demographic profile × tone) cells. Each Tier 2 record
    carries ``parent_ids = [<tier1_id>]`` so lineage survives any
    downstream debugging.
    Generator model: ``claude-sonnet-4-6`` (with ``claude-3-5-sonnet-20241022``
    fallback on 404).

  Tier 3 — NOT in this seed. Reserved for the follow-on full-build script.

OBJECT TRACEABILITY

  Every record carries:
    id                       — deterministic sha256(canonical_input)[:32]
    schema_version           — "native_nl.v1"
    trace_id                 — UUID4 stamped per script invocation
    tier                     — "tier1" or "tier2"
    parent_ids               — empty for tier1, [tier1_id] for tier2
    source                   — "english_generator.deterministic" / "claude_api"
    source_template_id       — tier1 template ID, null for tier2
    generator_model          — "deterministic" / "claude-sonnet-4-6" / ...
    generation_timestamp     — ISO 8601 UTC
    cas_expression / noetic / domain / drive / register
    prompt / reply
    demographic_profile / demographic_profile_code / tone / tone_code
    validator_pass / validator_reasons

USAGE

    # Full 5K seed (2500 tier1 + 2500 tier2 with API)
    python cas-synthetic/scripts/generate_native_nl_sdg_v1.py

    # Tier-1-only run (no API, no spend)
    python cas-synthetic/scripts/generate_native_nl_sdg_v1.py --tier1-only

    # Smoke (10 + 10 records, dry-run on Tier 2)
    python cas-synthetic/scripts/generate_native_nl_sdg_v1.py \\
        --tier1-target 10 --tier2-target 10 --dry-run

ENVIRONMENT

    ``NC_ANTHROPIC_API_KEY`` in
    ``noetic-compass-scaffold/noetic-compass/.env`` (NC prefix; quotes
    stripped on read), or in the calling environment. If the key is
    missing or invalid, the script produces Tier 1 ONLY and documents
    the gap in the manifest. No spend occurs.

CONSTRAINTS

  - HARD COST CAP: $50 USD (Tier 2 only). Aborts mid-run on overshoot.
  - Concurrency: 5 parallel asyncio workers.
  - Retries: 5 with exponential backoff.
  - All file writes are confined to ``cas-synthetic/data/native_nl/``
    and ``cas-synthetic/scripts/``.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import importlib.util as _importlib_util
import json
import os
import random
import re
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Repository root + import shim for demographic_tonal_axes
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEMO_AXES_PATH = (
    _REPO_ROOT / "cas-synthetic" / "generator" / "demographic_tonal_axes.py"
)


def _load_demographic_tonal_axes():
    """Load demographic_tonal_axes by file path so we don't trigger the rest
    of the ``cas_synthetic.generator`` package's __init__."""
    mod_name = "demographic_tonal_axes_native_nl"
    spec = _importlib_util.spec_from_file_location(mod_name, _DEMO_AXES_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module spec for {_DEMO_AXES_PATH}")
    module = _importlib_util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


_dta = _load_demographic_tonal_axes()
PROFILES = _dta.PROFILES
TONES = _dta.TONES
profile_for = _dta.profile_for
tone_for = _dta.tone_for
stratified_sample = _dta.stratified_sample

try:
    from anthropic import AsyncAnthropic
    from anthropic import APIStatusError, APIConnectionError, RateLimitError
except ImportError:  # pragma: no cover
    AsyncAnthropic = None  # validated lazily before any API call
    APIStatusError = APIConnectionError = RateLimitError = Exception  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "native_nl.v1"
GENERATION_VERSION = "native_nl_v1"

PRIMARY_MODEL = "claude-sonnet-4-6"
FALLBACK_MODEL = "claude-3-5-sonnet-20241022"

PRICE_PER_M_INPUT = 3.00
PRICE_PER_M_OUTPUT = 15.00

HARD_COST_CAP_USD = 50.0
DEFAULT_CONCURRENCY = 5
MAX_RETRIES = 5
DEFAULT_TEMPERATURE = 0.85
MAX_OUTPUT_TOKENS = 220
COST_LOG_INTERVAL = 500

REPLY_MIN_CHARS = 10
REPLY_MAX_CHARS = 600

DEFAULT_TIER1_TARGET = 2_500
DEFAULT_TIER2_TARGET = 2_500
DEFAULT_TIER2_K_PER_PARENT = 5  # tier2 fanout per tier1 parent

ENV_FILE_DEFAULT = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / ".env"
)

DEFAULT_OUT = (
    _REPO_ROOT / "cas-synthetic" / "data" / "native_nl" / "v1_seed_5k.jsonl"
)
DEFAULT_MANIFEST = (
    _REPO_ROOT / "cas-synthetic" / "data" / "native_nl" / "v1_seed_5k_manifest.json"
)

# ---------------------------------------------------------------------------
# Authoritative CAS axis tables — verbatim from CLAUDE.md
# ---------------------------------------------------------------------------

NOETICS: dict[str, tuple[str, str]] = {
    "^0": ("Idea", "All things in and outside the Mind."),
    "^1": ("Mind", "Various degrees of awareness that processes, stores, outputs, and intakes Ideas."),
    "^2": ("Positive", "An Idea the Mind has an affinity for and is attracted toward."),
    "^3": ("Negative", "An Idea the Mind is adverse to and repelled by."),
    "^4": ("Vibration", "The degree to which an Idea resonates with the Mind, its impression."),
    "^5": ("Female", "A Mind impregnated with an Idea, the Ideas a Mind is composed of."),
    "^6": ("Male", "An Idea impregnated with another Idea, the Ideas an Idea is composed of."),
    "^7": ("Rhythm", "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it."),
    "^8": ("Above/Cause", "An Idea that triggers a different Idea than itself to come to Mind."),
    "^9": ("Below/Effect", "The Idea brought to Mind by an Above/Cause trigger."),
}

DOMAINS: dict[str, str] = {
    "P": "Principled",
    "C": "Cognitive",
    "E": "Evaluative",
    "O": "Operational",
}

DRIVES: dict[str, str] = {
    "F1": "Unity",
    "F2": "Wisdom",
    "F3": "Vitality",
    "F4": "Connection",
    "F5": "Agency",
    "F6": "Structure",
    "F7": "Purpose",
}

REGISTERS: dict[str, str] = {
    "T": "Transcendent",
    "A": "Analytical",
    "f": "Affective",
    "E": "Embodied",
}

REGISTER_INSTRUCTIONS: dict[str, str] = {
    "T": (
        "transcendent — high-abstraction, purpose-orienting, integrative; "
        "felt sense of meaning or vision, NOT a felt-emotion line and NOT a "
        "step-by-step argument."
    ),
    "A": (
        "analytical — explicit, sequential, logical reasoning; lay out a "
        "step or premise; do NOT lead with a feeling word."
    ),
    "f": (
        "affective — feeling-toned, value-laden; the sentence should carry "
        "an emotional valence; do NOT present a chain of reasoning."
    ),
    "E": (
        "embodied — sensorimotor, bodily, concrete; gut/body language, "
        "physical action vocabulary; do NOT abstract away from the body."
    ),
}

NOETIC_NUDGES: dict[str, str] = {
    "^0": "neutral content / 'an idea'.",
    "^1": "paying attention / making up your mind / using your head.",
    "^2": "drawn to / speaks to me / can't resist.",
    "^3": (
        "VISCERAL aversion (NOT analytical critique) — can't stomach it / "
        "rubs me the wrong way / wouldn't touch it with a ten-foot pole."
    ),
    "^4": "struck a chord / hit me hard / made an impression / resonated.",
    "^5": (
        "accumulated experience composing the Mind — shaped by years / "
        "made me who I am / part of what makes me me."
    ),
    "^6": (
        "compositional decomposition (NOT aversion) — unpacking, breaking it down, "
        "looking at what's underneath, pulling apart the argument."
    ),
    "^7": (
        "rhythmic repetition entraining the Mind — practice, every day, "
        "muscle memory, getting into a groove."
    ),
    "^8": (
        "ASSOCIATIVE TRIGGERING (NOT deductive reasoning) — that reminds me / "
        "one thing leads to another / triggered a memory."
    ),
    "^9": (
        "the surfaced Idea — popped into my head / out of nowhere I thought of / "
        "it just clicked."
    ),
}


# ---------------------------------------------------------------------------
# Tier 1 — deterministic English generator
#
# Each (noetic, domain) pair has 3-5 colloquial phrasings. Drives provide a
# context tail. Registers shape the verb form. We bias toward the
# colloquialism map and avoid framework jargon.
# ---------------------------------------------------------------------------

# Subject seeds vary surface form so a 2500-record Tier 1 doesn't repeat
# verbatim. Domain-shaped because the user-prompt seed should match domain.
TIER1_TOPICS: tuple[str, ...] = (
    "a coworker repeatedly cutting corners on safety",
    "the spiritual side of a long career",
    "a habit you've kept for years",
    "an old song that came on the radio",
    "deciding whether to take a risky job offer",
    "the way your mentor shaped you",
    "a community ritual you grew up with",
    "letting someone down to keep a promise to yourself",
    "the smell of a particular meal",
    "watching someone you love struggle",
    "a public figure breaking a vow",
    "the muscle memory of a sport",
    "a rule you're not willing to break",
    "stepping into a leadership role you didn't ask for",
    "a piece of feedback that landed hard",
    "an unexpected memory while driving",
    "the discipline of daily practice",
    "facing a decision with no good options",
    "a sudden realization in the middle of a conversation",
    "the feeling of finally breaking a pattern",
    "training with a difficult teacher",
    "an idea that won't leave you alone",
    "a values clash with a close friend",
    "the texture of a workplace you used to belong to",
    "a piece of art that won't let you go",
    "an instruction that triggered another memory",
    "deciding what to teach the next generation",
    "an old wound that keeps showing up",
    "what 'home' actually means to you",
    "a pattern you're trying to unlearn",
    "the first time you got something really right",
    "a teaching that took years to land",
    "the weight of a quiet promise",
    "a kindness someone showed you that still surfaces",
    "the moment you knew this work was yours",
    "a story your family tells about you",
)

PROMPT_SEEDS: dict[str, tuple[str, ...]] = {
    "P": (
        "What's your honest take on {topic}?",
        "Where do you draw the line on {topic}?",
        "If someone asked what you stand for around {topic}, what would you say?",
        "Is there a principle you wouldn't bend on when it comes to {topic}?",
        "How do you decide what's right when {topic} comes up?",
    ),
    "C": (
        "Walk me through your thinking on {topic}.",
        "How do you make sense of {topic}?",
        "What model do you use to understand {topic}?",
        "Can you explain how you'd analyze {topic}?",
        "What's the structure you see in {topic}?",
    ),
    "E": (
        "How do you feel about {topic}?",
        "What's your reaction to {topic}?",
        "When {topic} comes up, what's the first thing that hits you?",
        "Can you describe the impression {topic} leaves on you?",
        "What does {topic} bring up for you?",
    ),
    "O": (
        "What would you actually do about {topic}?",
        "If you had to take action on {topic} this week, what would you start with?",
        "How would you put {topic} into practice?",
        "What's your routine around {topic}?",
        "Walk me through how you'd execute on {topic}.",
    ),
}

# Per-(noetic, register) reply templates. Each template carries:
#  - the colloquialism family (anti-drift compliant),
#  - {topic} placeholder, and
#  - {drive_tail} placeholder where the drive-context phrase lands.
# Templates are deliberately ordinary English; surface diversity is added
# in Tier 2.

NOETIC_REGISTER_TEMPLATES: dict[tuple[str, str], tuple[str, ...]] = {
    # ^0 Idea — neutral content
    ("^0", "T"): (
        "I'm holding {topic} as one open possibility among many — not committing yet, just letting it sit.",
        "Right now {topic} is a thought I've made room for; I'm not pinning it down.",
    ),
    ("^0", "A"): (
        "I want to map out the possible angles on {topic} before I narrow in.",
        "Let me list what {topic} could plausibly mean before I pick one.",
    ),
    ("^0", "f"): (
        "I'm sitting with {topic} as a feeling that hasn't shaped itself yet.",
        "There's an unresolved feeling around {topic} I'm not ready to name.",
    ),
    ("^0", "E"): (
        "I'm letting {topic} settle in my body before I move on it.",
        "I'm walking around with {topic} for now — not acting yet.",
    ),
    # ^1 Mind — paying attention / making up your mind
    ("^1", "T"): (
        "I'm paying close attention to what {topic} is really pointing at.",
        "I'm holding {topic} in my awareness and seeing what it asks of me.",
    ),
    ("^1", "A"): (
        "I'm focusing in on {topic} carefully — what's actually being claimed here?",
        "Let me direct attention to {topic} step by step.",
    ),
    ("^1", "f"): (
        "I'm noticing what {topic} stirs up the moment I turn toward it.",
        "When I let myself attend to {topic}, something rises right away.",
    ),
    ("^1", "E"): (
        "I'm zeroing in on {topic} — eyes up, hands ready.",
        "I'm pointed at {topic} and ready to watch what happens.",
    ),
    # ^2 Positive — drawn to / speaks to me
    ("^2", "T"): (
        "{topic} speaks to me at a level I trust — I'm drawn toward it.",
        "There's something about {topic} that pulls me in like it matters.",
    ),
    ("^2", "A"): (
        "Of the options here, {topic} is the one I find most compelling on the merits.",
        "I keep coming back to {topic} because it actually fits.",
    ),
    ("^2", "f"): (
        "I'm warm to {topic} — it just feels right.",
        "I can't help it — {topic} draws me in.",
    ),
    ("^2", "E"): (
        "I lean toward {topic} — physically, almost. My whole body says yes.",
        "I'm reaching for {topic} before I've even thought it through.",
    ),
    # ^3 Negative — VISCERAL aversion (NOT analytical critique)
    ("^3", "T"): (
        "{topic} sits wrong with me at a level I won't compromise on.",
        "I can't reconcile myself to {topic} — it goes against what I'm built on.",
    ),
    ("^3", "A"): (
        "I'm not going to sign off on {topic}. That's a hard line.",
        "I won't endorse {topic}. The answer there is no.",
    ),
    ("^3", "f"): (
        "{topic} rubs me the wrong way. I can't stomach it.",
        "I wouldn't touch {topic} with a ten-foot pole.",
    ),
    ("^3", "E"): (
        "Everything in my body recoils at {topic}.",
        "I get a knot in my gut every time {topic} comes up.",
    ),
    # ^4 Vibration — struck a chord / hit me hard
    ("^4", "T"): (
        "{topic} resonated with me in a way I didn't expect.",
        "Something about {topic} struck a chord deep down.",
    ),
    ("^4", "A"): (
        "{topic} registered as significant — high signal, not background.",
        "I'd flag {topic} as making a real impression on me.",
    ),
    ("^4", "f"): (
        "{topic} hit me hard.",
        "{topic} just landed — I'm still feeling it.",
    ),
    ("^4", "E"): (
        "{topic} hit me right in the chest.",
        "I felt {topic} viscerally — it shook me.",
    ),
    # ^5 Female — accumulated experience composing the Mind
    ("^5", "T"): (
        "{topic} is part of what makes me me — it's woven into who I am.",
        "I am the accumulation of moments like {topic}; that's the truth of it.",
    ),
    ("^5", "A"): (
        "My read on {topic} is shaped by years of cases just like it.",
        "{topic} is something I've absorbed — every prior version informs how I see it now.",
    ),
    ("^5", "f"): (
        "{topic} is part of who I am at this point.",
        "I can't separate myself from {topic} — it's lived in me too long.",
    ),
    ("^5", "E"): (
        "{topic} is in my bones now.",
        "{topic} lives in my body — every part of me remembers it.",
    ),
    # ^6 Male — compositional decomposition (NOT aversion)
    ("^6", "T"): (
        "I want to unpack {topic} and see what it's actually composed of.",
        "Let me break {topic} apart so I can see the pieces underneath.",
    ),
    ("^6", "A"): (
        "I'd pull {topic} apart and look at each component on its own.",
        "Walk me through {topic} piece by piece — where does it come from?",
    ),
    ("^6", "f"): (
        "I want to look under the hood of {topic} — see what's holding it together.",
        "I'm pulling {topic} apart in my head, piece by piece.",
    ),
    ("^6", "E"): (
        "Let me take {topic} apart with my hands and see what's inside.",
        "I want to literally pull {topic} apart and inspect it.",
    ),
    # ^7 Rhythm — practice / muscle memory / getting into a groove
    ("^7", "T"): (
        "{topic} has become part of my rhythm — repeated until it shaped me.",
        "I've practiced {topic} long enough that it's part of how I move.",
    ),
    ("^7", "A"): (
        "I run through {topic} on a regular cadence — every week, same way.",
        "Repetition matters here: I work {topic} the same way each time.",
    ),
    ("^7", "f"): (
        "{topic} is in my groove now — I just do it.",
        "I've done {topic} so many times I don't have to think about it anymore.",
    ),
    ("^7", "E"): (
        "{topic} is muscle memory at this point.",
        "My body knows {topic} — I just go through the motions.",
    ),
    # ^8 Above/Cause — ASSOCIATIVE TRIGGERING (NOT deductive reasoning)
    ("^8", "T"): (
        "{topic} reminds me of something else entirely — one thing leading to another.",
        "When I think of {topic}, it triggers a whole different memory.",
    ),
    ("^8", "A"): (
        "{topic} brings to mind a parallel case I keep returning to.",
        "Something about {topic} keeps flagging an associated example.",
    ),
    ("^8", "f"): (
        "{topic} just made me think of someone I haven't thought of in years.",
        "Hearing {topic} brought up a feeling I'd parked a long time ago.",
    ),
    ("^8", "E"): (
        "{topic} hit a smell-memory — I'm right back there.",
        "{topic} kicked off a body memory I wasn't expecting.",
    ),
    # ^9 Below/Effect — the surfaced Idea
    ("^9", "T"): (
        "It just clicked — {topic} surfaced on its own.",
        "{topic} popped into my head from somewhere deeper.",
    ),
    ("^9", "A"): (
        "Out of nowhere {topic} came up as the answer.",
        "{topic} arrived as the conclusion before I'd even worked it out.",
    ),
    ("^9", "f"): (
        "{topic} just popped into my head.",
        "Out of nowhere I thought of {topic}.",
    ),
    ("^9", "E"): (
        "{topic} surfaced in my body before I named it — gut first.",
        "I felt {topic} before I could put words on it — it just showed up.",
    ),
}


DRIVE_TAILS: dict[str, tuple[str, ...]] = {
    "F1": (" — it's about wholeness for me.", " — I want it to hold together.", ""),
    "F2": (" — I want to understand it properly.", " — wisdom-first.", ""),
    "F3": (" — it has to keep me alive in the work.", " — vitality matters.", ""),
    "F4": (" — for the people I'm close to.", " — connection-first.", ""),
    "F5": (" — I'm going to choose for myself.", " — I'm owning the call.", ""),
    "F6": (" — the structure has to hold.", " — I want clean shape on it.", ""),
    "F7": (" — it lines up with what I'm here for.", " — purpose-driven.", ""),
}


# ---------------------------------------------------------------------------
# Validator — surface filters reused from generate_paired_replies_v1.py
# ---------------------------------------------------------------------------

JARGON_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\bnoetic[s]?\b", re.IGNORECASE),
    re.compile(r"\bdomain[s]?\b", re.IGNORECASE),
    re.compile(r"\bregister[s]?\b", re.IGNORECASE),
    re.compile(r"\bdrive[s]?\b", re.IGNORECASE),
    re.compile(r"\bcas\b", re.IGNORECASE),
    re.compile(r"\bF[1-7]\b"),
    re.compile(r"\^[0-9]"),
    re.compile(r"\|[TAfE]\b"),
    re.compile(r"\boperator\b", re.IGNORECASE),
    re.compile(r"\bcompound state\b", re.IGNORECASE),
)

TEMPLATE_OPENERS: tuple[re.Pattern, ...] = (
    re.compile(r"^\s*reading this as\b", re.IGNORECASE),
    re.compile(r"^\s*this maps to\b", re.IGNORECASE),
    re.compile(r"^\s*this expresses\b", re.IGNORECASE),
    re.compile(r"^\s*i (?:detect|sense|perceive|interpret)\b", re.IGNORECASE),
)


def looks_like_english(text: str) -> bool:
    if not text:
        return False
    letters = sum(1 for ch in text if ch.isalpha())
    return letters >= max(8, int(0.5 * len(text)))


def validate_reply(text: str) -> tuple[bool, list[str]]:
    """Return (ok, reasons). reasons is empty when ok=True."""
    reasons: list[str] = []
    if not text:
        return False, ["empty"]
    s = text.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"', "`"):
        s = s[1:-1].strip()
    if len(s) < REPLY_MIN_CHARS:
        reasons.append("too_short")
    if len(s) > REPLY_MAX_CHARS:
        reasons.append("too_long")
    if not looks_like_english(s):
        reasons.append("low_letter_density")
    for pat in JARGON_PATTERNS:
        if pat.search(s):
            reasons.append(f"jargon:{pat.pattern}")
    for pat in TEMPLATE_OPENERS:
        if pat.search(s):
            reasons.append("template_opener")
    return (len(reasons) == 0), reasons


def clean_reply(text: str) -> str:
    s = text.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"', "`"):
        s = s[1:-1].strip()
    return s


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------

_UNIT_SEPARATOR = "\x1f"


def deterministic_id(*parts: str, prefix: str = "") -> str:
    """sha256-derived 32-hex-char ID. Stable for the same input parts.

    Inputs are concatenated with ``\\x1f`` (unit separator) before hashing.
    The ``prefix`` lets us tag tier1/tier2 IDs distinctively when desirable
    (we use a flat prefix-less ID by default to keep IDs uniform; the
    ``tier`` field carries the layer information).
    """
    canonical = _UNIT_SEPARATOR.join(parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if prefix:
        return f"{prefix}{digest[:32]}"
    return digest[:32]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_cas_expression(noetic: str, domain: str, drive: str, register: str) -> str:
    """v7.5-style register-specified compound: ``^n^D_{F_k}|R``."""
    return f"{noetic}^{domain}_{{{drive}}}|{register}"


# ---------------------------------------------------------------------------
# Tier 1 generation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Axes:
    noetic: str
    domain: str
    drive: str
    register: str
    topic: str

    def cas_expression(self) -> str:
        return build_cas_expression(self.noetic, self.domain, self.drive, self.register)


def axis_complete_iter() -> Iterable[tuple[str, str, str, str]]:
    """Yield every (noetic, domain, drive, register) tuple in canonical order.

    1,120 cells total. The Tier 1 generator iterates this until it has
    target records; with target=2500 we visit each cell ~2.2 times.
    """
    for n in NOETICS:
        for d in DOMAINS:
            for f in DRIVES:
                for r in REGISTERS:
                    yield (n, d, f, r)


def render_tier1(axes: Axes, rng: random.Random) -> tuple[str, str, str]:
    """Return (prompt, reply, template_id)."""
    seeds = PROMPT_SEEDS[axes.domain]
    seed = rng.choice(seeds)
    prompt = seed.format(topic=axes.topic)

    template_pool = NOETIC_REGISTER_TEMPLATES.get((axes.noetic, axes.register))
    if not template_pool:
        # Defensive fallback. Should never trigger; the table is exhaustive.
        template_pool = (
            f"On {axes.topic}, here is where I land: {axes.noetic} in the {axes.register} register.",
        )
    chosen_template = rng.choice(template_pool)
    drive_tail = rng.choice(DRIVE_TAILS.get(axes.drive, ("",)))
    reply_raw = chosen_template.format(topic=axes.topic) + drive_tail
    reply = reply_raw.strip()

    template_id = deterministic_id(
        axes.noetic, axes.domain, axes.drive, axes.register,
        chosen_template, prefix="tpl_",
    )
    return prompt, reply, template_id


def generate_tier1(target: int, seed: int, trace_id: str) -> list[dict]:
    """Generate ``target`` deterministic Tier 1 records."""
    rng = random.Random(seed)
    cells = list(axis_complete_iter())
    rng.shuffle(cells)

    records: list[dict] = []
    for i in range(target):
        n, d, f, r = cells[i % len(cells)]
        # Vary topic per record so the same cell visited twice produces
        # surface variation.
        topic = TIER1_TOPICS[(i + rng.randrange(0, 1000)) % len(TIER1_TOPICS)]
        axes = Axes(noetic=n, domain=d, drive=f, register=r, topic=topic)
        prompt, reply, template_id = render_tier1(axes, rng)

        ok, reasons = validate_reply(reply)
        cas_expr = axes.cas_expression()
        gen_ts = utc_now_iso()
        rec_id = deterministic_id(
            cas_expr, prompt, "tier1", "deterministic", gen_ts,
        )
        record = {
            "id": rec_id,
            "schema_version": SCHEMA_VERSION,
            "trace_id": trace_id,
            "tier": "tier1",
            "parent_ids": [],
            "source": "english_generator.deterministic",
            "source_template_id": template_id,
            "generator_model": "deterministic",
            "generation_timestamp": gen_ts,

            "cas_expression": cas_expr,
            "noetic": n,
            "domain": d,
            "drive": f,
            "register": r,

            "prompt": prompt,
            "reply": reply,

            "demographic_profile": "neutral",
            "demographic_profile_code": "P0",
            "tone": "neutral",
            "tone_code": "T1",

            "validator_pass": ok,
            "validator_reasons": list(reasons),
            "generation_version": GENERATION_VERSION,
        }
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------

class CostTracker:
    def __init__(self, hard_cap_usd: float):
        self.hard_cap_usd = hard_cap_usd
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0
        self._lock = asyncio.Lock()
        self._aborted = False

    @property
    def total_usd(self) -> float:
        return (
            self.input_tokens * PRICE_PER_M_INPUT / 1_000_000.0
            + self.output_tokens * PRICE_PER_M_OUTPUT / 1_000_000.0
        )

    async def add(self, in_tokens: int, out_tokens: int) -> bool:
        async with self._lock:
            self.input_tokens += in_tokens
            self.output_tokens += out_tokens
            self.api_calls += 1
            if self.total_usd > self.hard_cap_usd:
                self._aborted = True
                return False
            return True

    @property
    def aborted(self) -> bool:
        return self._aborted


# ---------------------------------------------------------------------------
# Tier 2 — Claude API rewrites
# ---------------------------------------------------------------------------

TIER2_SYSTEM_PROMPT = (
    "You are generating training data for a CAS-Native English generation "
    "head. Given a base reply expressing a CAS structural dynamic, REWRITE "
    "it in the voice of a specified demographic profile and tonal register. "
    "Preserve the structural dynamic — same Noetic family, same anti-drift "
    "discipline. Never mention any framework jargon."
)


def render_tier2_user_message(parent: dict, profile_code: str, tone_code: str) -> str:
    profile = profile_for(profile_code)
    tone = tone_for(tone_code)
    n_code = parent["noetic"]
    n_name, n_def = NOETICS[n_code]
    d_code = parent["domain"]
    f_code = parent["drive"]
    r_code = parent["register"]
    nudge = NOETIC_NUDGES[n_code]
    register_instr = REGISTER_INSTRUCTIONS[r_code]

    return (
        f"Base reply (preserve the structural dynamic, REWRITE the voice):\n"
        f"\"{parent['reply']}\"\n\n"
        f"User prompt context: \"{parent['prompt']}\"\n\n"
        f"Structural anchors (do NOT mention these in your output):\n"
        f"- Anti-drift cue for the Noetic: {nudge}\n"
        f"- Register requirement: {register_instr}\n\n"
        f"Voice spec:\n"
        f"- Demographic profile: {profile.name} — {profile.description}\n"
        f"- Tone: {tone.name} — {tone.description}\n\n"
        "Generate a 1-3 sentence English rewrite that:\n"
        "1. Preserves the structural dynamic of the base reply (same Noetic "
        "family, same anti-drift discipline). Do NOT mention CAS / Noetic / "
        "Domain / Drive / Register / framework / operator / |[TAfE] / ^N "
        "notation.\n"
        "2. Sounds like a real person in the given demographic and tone. Avoid "
        "'Reading this as...' / 'This maps to...' / 'I sense...' opener "
        "patterns.\n"
        "3. Tracks the profile's natural lexicon. Avoid the profile's "
        "avoid_lexicon.\n"
        "4. Keep total length UNDER 480 characters.\n\n"
        "CRITICAL: Output ONLY the reply text. No labels, no preamble, no "
        "closing remarks, no quote marks around it."
    )


async def call_claude(
    client: Any,
    user_message: str,
    *,
    model: str,
    cost_tracker: CostTracker,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[str | None, str, str | None]:
    """Call Claude with retries. Returns (text, model_used, error_reason)."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=temperature,
                system=TIER2_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
        except RateLimitError as exc:
            last_exc = exc
            wait = min(60.0, 2.0 ** attempt + random.random())
            await asyncio.sleep(wait)
            continue
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in (429, 529, 500, 502, 503, 504):
                last_exc = exc
                wait = min(60.0, 2.0 ** attempt + random.random())
                await asyncio.sleep(wait)
                continue
            if status == 404:
                raise
            return None, model, f"api_status_{status}"
        except APIConnectionError as exc:
            last_exc = exc
            wait = min(30.0, 2.0 ** attempt + random.random())
            await asyncio.sleep(wait)
            continue
        except Exception as exc:  # noqa: BLE001
            return None, model, f"unexpected:{type(exc).__name__}:{exc}"

        try:
            in_tokens = getattr(resp.usage, "input_tokens", 0) or 0
            out_tokens = getattr(resp.usage, "output_tokens", 0) or 0
        except Exception:  # noqa: BLE001
            in_tokens = 0
            out_tokens = 0
        ok = await cost_tracker.add(in_tokens, out_tokens)
        if not ok:
            return None, model, "cost_cap_exceeded"

        text_parts: list[str] = []
        for p in (resp.content or []):
            t = getattr(p, "text", None)
            if t:
                text_parts.append(t)
        text = "".join(text_parts)
        return text, model, None

    return None, model, f"retries_exhausted:{type(last_exc).__name__ if last_exc else 'unknown'}"


@dataclass
class Tier2Job:
    parent_id: str
    parent_record: dict
    profile_code: str
    tone_code: str
    user_message: str


def build_tier2_jobs(
    tier1_records: list[dict],
    target: int,
    seed: int,
    k_per_parent: int = DEFAULT_TIER2_K_PER_PARENT,
) -> list[Tier2Job]:
    """Pick deterministic Tier 1 parents and (profile, tone) pairs.

    The number of distinct parents needed is ceil(target / k_per_parent).
    For target=2500 with k=5 that's 500 distinct parents.
    """
    if not tier1_records:
        return []
    if k_per_parent < 1:
        raise ValueError(f"k_per_parent must be >= 1, got {k_per_parent}")

    rng = random.Random(seed)
    n_parents = (target + k_per_parent - 1) // k_per_parent
    n_parents = min(n_parents, len(tier1_records))

    # Stratify parent selection by (noetic, register) so the rewrites
    # cover the axis space, not just whatever Tier 1 happened to put first.
    by_cell: dict[tuple[str, str], list[dict]] = {}
    for r in tier1_records:
        key = (r["noetic"], r["register"])
        by_cell.setdefault(key, []).append(r)
    cells = list(by_cell.keys())
    rng.shuffle(cells)

    parents: list[dict] = []
    cell_idx = 0
    while len(parents) < n_parents and cells:
        cell = cells[cell_idx % len(cells)]
        pool = by_cell[cell]
        if pool:
            chosen = pool.pop(rng.randrange(len(pool)))
            parents.append(chosen)
        else:
            cells.remove(cell)
            if not cells:
                break
            continue
        cell_idx += 1

    jobs: list[Tier2Job] = []
    job_count = 0
    for parent in parents:
        if job_count >= target:
            break
        # Stratified (profile, tone) draws using an int seed derived from
        # the parent ID. Stable across reruns.
        parent_seed = int(parent["id"][:8], 16)
        pairs = stratified_sample(k=k_per_parent, seed=parent_seed)
        for profile_code, tone_code in pairs:
            if job_count >= target:
                break
            user_message = render_tier2_user_message(parent, profile_code, tone_code)
            jobs.append(
                Tier2Job(
                    parent_id=parent["id"],
                    parent_record=parent,
                    profile_code=profile_code,
                    tone_code=tone_code,
                    user_message=user_message,
                )
            )
            job_count += 1
    return jobs


# ---------------------------------------------------------------------------
# Tier 2 worker
# ---------------------------------------------------------------------------

class GenerationContext:
    """Mutable shared state for Tier 2 concurrent workers."""

    def __init__(
        self,
        client: Any,
        cost_tracker: CostTracker,
        trace_id: str,
        primary_model: str = PRIMARY_MODEL,
        fallback_model: str = FALLBACK_MODEL,
    ) -> None:
        self.client = client
        self.cost_tracker = cost_tracker
        self.trace_id = trace_id
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.current_model = primary_model
        self.failure_counter: Counter[str] = Counter()
        self.records: list[dict] = []
        self.records_lock = asyncio.Lock()
        self.last_logged_at = 0


async def generate_tier2_record(
    ctx: GenerationContext,
    job: Tier2Job,
) -> dict | None:
    if ctx.cost_tracker.aborted:
        return None

    text, model_used, err = await call_claude(
        ctx.client,
        job.user_message,
        model=ctx.current_model,
        cost_tracker=ctx.cost_tracker,
    )
    if text is None and err == "api_status_404" and ctx.current_model == ctx.primary_model:
        ctx.current_model = ctx.fallback_model
        text, model_used, err = await call_claude(
            ctx.client,
            job.user_message,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
        )
    if text is None:
        ctx.failure_counter[err or "unknown_api_error"] += 1
        return None

    cleaned = clean_reply(text)
    ok, reasons = validate_reply(cleaned)
    if not ok:
        # Single retry at lower temperature.
        text2, model_used2, err2 = await call_claude(
            ctx.client,
            job.user_message,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
            temperature=0.55,
        )
        if text2 is None:
            ctx.failure_counter[f"retry_api:{err2 or 'unknown'}"] += 1
            return None
        cleaned2 = clean_reply(text2)
        ok2, reasons2 = validate_reply(cleaned2)
        if not ok2:
            # Still record the failure but keep the cleaner of the two.
            ctx.failure_counter[
                f"validation:{':'.join(reasons[:1])}->{':'.join(reasons2[:1])}"
            ] += 1
            return None
        cleaned = cleaned2
        model_used = model_used2
        ok = ok2
        reasons = reasons2

    profile = profile_for(job.profile_code)
    tone = tone_for(job.tone_code)
    parent = job.parent_record
    gen_ts = utc_now_iso()
    cas_expr = parent["cas_expression"]
    rec_id = deterministic_id(
        cas_expr, parent["prompt"], "tier2", model_used, gen_ts,
        job.profile_code, job.tone_code,
    )
    record = {
        "id": rec_id,
        "schema_version": SCHEMA_VERSION,
        "trace_id": ctx.trace_id,
        "tier": "tier2",
        "parent_ids": [parent["id"]],
        "source": "claude_api",
        "source_template_id": parent.get("source_template_id"),
        "generator_model": model_used,
        "generation_timestamp": gen_ts,

        "cas_expression": cas_expr,
        "noetic": parent["noetic"],
        "domain": parent["domain"],
        "drive": parent["drive"],
        "register": parent["register"],

        "prompt": parent["prompt"],
        "reply": cleaned,

        "demographic_profile": profile.name,
        "demographic_profile_code": profile.code,
        "tone": tone.name,
        "tone_code": tone.code,

        "validator_pass": ok,
        "validator_reasons": list(reasons),
        "generation_version": GENERATION_VERSION,
    }
    return record


async def tier2_worker(
    ctx: GenerationContext,
    sem: asyncio.Semaphore,
    job: Tier2Job,
) -> None:
    if ctx.cost_tracker.aborted:
        return
    async with sem:
        if ctx.cost_tracker.aborted:
            return
        record = await generate_tier2_record(ctx, job)
        if record is not None:
            async with ctx.records_lock:
                ctx.records.append(record)
                if len(ctx.records) - ctx.last_logged_at >= COST_LOG_INTERVAL:
                    ctx.last_logged_at = len(ctx.records)
                    print(
                        f"[tier2 progress] successes={len(ctx.records)} "
                        f"api_calls={ctx.cost_tracker.api_calls} "
                        f"cost_estimate=${ctx.cost_tracker.total_usd:.2f} "
                        f"failures={sum(ctx.failure_counter.values())}",
                        flush=True,
                    )


# ---------------------------------------------------------------------------
# Env loader
# ---------------------------------------------------------------------------

def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v


def load_api_key(env_file: Path) -> str | None:
    key = os.environ.get("NC_ANTHROPIC_API_KEY")
    if key:
        return _strip_quotes(key)
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "NC_ANTHROPIC_API_KEY":
                return _strip_quotes(v)
    return None


# ---------------------------------------------------------------------------
# JSONL + manifest writers
# ---------------------------------------------------------------------------

def write_jsonl(out_path: Path, records: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        for rec in records:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")


def append_jsonl(out_path: Path, records: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fp:
        for rec in records:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")


def compute_distributions(records: list[dict]) -> dict[str, dict[str, int]]:
    keys = (
        "tier", "noetic", "domain", "drive", "register",
        "demographic_profile", "tone", "generator_model",
    )
    out: dict[str, Counter] = {k: Counter() for k in keys}
    for rec in records:
        for k in keys:
            out[k][rec.get(k, "?")] += 1
    return {k: dict(v) for k, v in out.items()}


def write_manifest(
    manifest_path: Path,
    *,
    records: list[dict],
    started_iso: str,
    completed_iso: str,
    cost: CostTracker,
    tier1_target: int,
    tier2_target: int,
    primary_model: str,
    final_model: str,
    failure_counter: Counter,
    api_key_status: str,
    trace_id: str,
    seed: int,
    notes: list[str],
    out_path: Path,
) -> dict:
    distributions = compute_distributions(records)
    by_tier = Counter(rec["tier"] for rec in records)
    validator_pass_count = sum(1 for rec in records if rec.get("validator_pass"))

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generation_version": GENERATION_VERSION,
        "trace_id": trace_id,
        "seed": seed,
        "tier1_target": tier1_target,
        "tier2_target": tier2_target,
        "tier1_records": int(by_tier.get("tier1", 0)),
        "tier2_records": int(by_tier.get("tier2", 0)),
        "total_records": len(records),
        "validator_pass_count": validator_pass_count,
        "validator_pass_rate": (
            validator_pass_count / max(1, len(records))
        ),
        "primary_model": primary_model,
        "final_model": final_model,
        "api_key_status": api_key_status,
        "distributions": distributions,
        "total_cost_usd": round(cost.total_usd, 4),
        "input_tokens": cost.input_tokens,
        "output_tokens": cost.output_tokens,
        "api_calls": cost.api_calls,
        "hard_cost_cap_usd": cost.hard_cap_usd,
        "cost_aborted": cost.aborted,
        "failure_counts": dict(failure_counter),
        "generation_started": started_iso,
        "generation_completed": completed_iso,
        "out_path": str(out_path),
        "round_trip_validator": "deferred",
        "notes": notes,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------

async def run_tier2(
    tier1_records: list[dict],
    target: int,
    seed: int,
    *,
    cost_cap_usd: float,
    concurrency: int,
    primary_model: str,
    fallback_model: str,
    api_key: str,
    trace_id: str,
    dry_run: bool,
) -> tuple[list[dict], CostTracker, Counter, str]:
    """Returns (records, cost_tracker, failure_counter, final_model_used)."""
    cost_tracker = CostTracker(cost_cap_usd)

    if target <= 0 or not tier1_records:
        return [], cost_tracker, Counter(), primary_model

    if dry_run:
        # Synthesize placeholder Tier 2 records without API calls.
        jobs = build_tier2_jobs(tier1_records, target, seed)
        records: list[dict] = []
        for job in jobs:
            profile = profile_for(job.profile_code)
            tone = tone_for(job.tone_code)
            parent = job.parent_record
            placeholder = (
                f"[dry-run] {parent['reply']} (rewritten as {profile.name} / "
                f"{tone.name})"
            )
            gen_ts = utc_now_iso()
            cas_expr = parent["cas_expression"]
            rec_id = deterministic_id(
                cas_expr, parent["prompt"], "tier2", "dry-run", gen_ts,
                job.profile_code, job.tone_code,
            )
            ok, reasons = validate_reply(placeholder)
            records.append({
                "id": rec_id,
                "schema_version": SCHEMA_VERSION,
                "trace_id": trace_id,
                "tier": "tier2",
                "parent_ids": [parent["id"]],
                "source": "claude_api",
                "source_template_id": parent.get("source_template_id"),
                "generator_model": "dry-run",
                "generation_timestamp": gen_ts,
                "cas_expression": cas_expr,
                "noetic": parent["noetic"],
                "domain": parent["domain"],
                "drive": parent["drive"],
                "register": parent["register"],
                "prompt": parent["prompt"],
                "reply": placeholder,
                "demographic_profile": profile.name,
                "demographic_profile_code": profile.code,
                "tone": tone.name,
                "tone_code": tone.code,
                "validator_pass": ok,
                "validator_reasons": list(reasons),
                "generation_version": GENERATION_VERSION,
            })
        return records, cost_tracker, Counter(), "dry-run"

    if AsyncAnthropic is None:
        raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")

    client = AsyncAnthropic(api_key=api_key)
    ctx = GenerationContext(
        client=client,
        cost_tracker=cost_tracker,
        trace_id=trace_id,
        primary_model=primary_model,
        fallback_model=fallback_model,
    )

    # Pre-flight probe — pick a working model.
    probe_text, _probe_model, probe_err = await call_claude(
        client, "Reply with the single word: ok",
        model=primary_model, cost_tracker=cost_tracker, temperature=0.0,
    )
    if probe_text is None and probe_err == "api_status_404":
        print(
            f"[preflight] primary model {primary_model} unavailable, "
            f"falling back to {fallback_model}",
            flush=True,
        )
        ctx.current_model = fallback_model
        probe_text, _probe_model, probe_err = await call_claude(
            client, "Reply with the single word: ok",
            model=fallback_model, cost_tracker=cost_tracker, temperature=0.0,
        )
    if probe_text is None:
        raise RuntimeError(f"preflight call failed: {probe_err}")
    print(f"[preflight] using model {ctx.current_model}; probe ok", flush=True)

    # Cost estimate guard.
    est_in_per = 700
    est_out_per = 90
    est_total = (
        target * est_in_per * PRICE_PER_M_INPUT / 1_000_000.0
        + target * est_out_per * PRICE_PER_M_OUTPUT / 1_000_000.0
    )
    print(
        f"[preflight] estimated tier2 cost for {target} records: "
        f"~${est_total:.2f} (cap=${cost_cap_usd:.2f})",
        flush=True,
    )
    if est_total > cost_cap_usd:
        raise RuntimeError(
            f"estimated cost ${est_total:.2f} exceeds cost cap "
            f"${cost_cap_usd:.2f}; reduce --tier2-target or raise --cost-cap"
        )

    jobs = build_tier2_jobs(tier1_records, target, seed)
    print(f"[tier2] {len(jobs)} jobs prepared", flush=True)

    sem = asyncio.Semaphore(concurrency)
    tasks = [
        asyncio.create_task(tier2_worker(ctx, sem, job)) for job in jobs
    ]
    await asyncio.gather(*tasks, return_exceptions=False)
    return ctx.records, cost_tracker, ctx.failure_counter, ctx.current_model


def run(
    *,
    tier1_target: int,
    tier2_target: int,
    out_path: Path,
    manifest_path: Path,
    seed: int,
    concurrency: int,
    cost_cap_usd: float,
    primary_model: str,
    fallback_model: str,
    env_file: Path,
    tier1_only: bool,
    dry_run: bool,
) -> int:
    started_iso = utc_now_iso()
    trace_id = str(uuid.uuid4())
    notes: list[str] = []

    print(
        f"[run] trace_id={trace_id} seed={seed} "
        f"tier1_target={tier1_target} tier2_target={tier2_target}",
        flush=True,
    )

    api_key_status = "unused"
    api_key: str | None = None
    if not tier1_only and not dry_run:
        api_key = load_api_key(env_file)
        if not api_key or not api_key.startswith("sk-ant-"):
            print(
                f"[warn] NC_ANTHROPIC_API_KEY missing or malformed in "
                f"{env_file} and environment; falling back to Tier 1 only",
                flush=True,
            )
            tier1_only = True
            api_key_status = "missing"
            notes.append(
                "API key missing or invalid; produced Tier 1 only. "
                "No spend occurred."
            )
        else:
            api_key_status = "present"

    if dry_run:
        api_key_status = "dry-run"

    print(f"[tier1] generating {tier1_target} deterministic records", flush=True)
    tier1_records = generate_tier1(tier1_target, seed, trace_id)
    print(
        f"[tier1] generated {len(tier1_records)} records "
        f"(validator_pass_rate="
        f"{sum(1 for r in tier1_records if r['validator_pass']) / max(1, len(tier1_records)):.3f})",
        flush=True,
    )

    write_jsonl(out_path, tier1_records)

    cost_tracker = CostTracker(cost_cap_usd)
    failure_counter: Counter = Counter()
    final_model = primary_model
    tier2_records: list[dict] = []

    if not tier1_only and tier2_target > 0:
        try:
            tier2_records, cost_tracker, failure_counter, final_model = (
                asyncio.run(
                    run_tier2(
                        tier1_records=tier1_records,
                        target=tier2_target,
                        seed=seed + 1,  # different stratification seed
                        cost_cap_usd=cost_cap_usd,
                        concurrency=concurrency,
                        primary_model=primary_model,
                        fallback_model=fallback_model,
                        api_key=api_key or "",
                        trace_id=trace_id,
                        dry_run=dry_run,
                    )
                )
            )
        except RuntimeError as exc:
            print(f"[tier2] aborted: {exc}", flush=True)
            notes.append(f"Tier 2 aborted: {exc}")
        if tier2_records:
            append_jsonl(out_path, tier2_records)

    all_records = tier1_records + tier2_records
    completed_iso = utc_now_iso()

    write_manifest(
        manifest_path,
        records=all_records,
        started_iso=started_iso,
        completed_iso=completed_iso,
        cost=cost_tracker,
        tier1_target=tier1_target,
        tier2_target=tier2_target,
        primary_model=primary_model,
        final_model=final_model,
        failure_counter=failure_counter,
        api_key_status=api_key_status,
        trace_id=trace_id,
        seed=seed,
        notes=notes,
        out_path=out_path,
    )
    print(
        f"[done] total={len(all_records)} "
        f"tier1={len(tier1_records)} tier2={len(tier2_records)} "
        f"cost=${cost_tracker.total_usd:.2f} "
        f"api_calls={cost_tracker.api_calls} "
        f"failures={sum(failure_counter.values())} "
        f"aborted={cost_tracker.aborted}",
        flush=True,
    )
    if failure_counter:
        print("[done] failure causes:", flush=True)
        for cause, count in failure_counter.most_common():
            print(f"   {count:>5d}  {cause}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tier1-target", type=int, default=DEFAULT_TIER1_TARGET)
    p.add_argument("--tier2-target", type=int, default=DEFAULT_TIER2_TARGET)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--seed", type=int, default=20260504)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--cost-cap", type=float, default=HARD_COST_CAP_USD)
    p.add_argument("--primary-model", default=PRIMARY_MODEL)
    p.add_argument("--fallback-model", default=FALLBACK_MODEL)
    p.add_argument("--env-file", type=Path, default=ENV_FILE_DEFAULT)
    p.add_argument(
        "--tier1-only", action="store_true",
        help="Skip Tier 2 (no API spend).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Synthesize Tier 2 placeholders without API calls.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        tier1_target=args.tier1_target,
        tier2_target=args.tier2_target,
        out_path=args.out,
        manifest_path=args.manifest,
        seed=args.seed,
        concurrency=args.concurrency,
        cost_cap_usd=args.cost_cap,
        primary_model=args.primary_model,
        fallback_model=args.fallback_model,
        env_file=args.env_file,
        tier1_only=args.tier1_only,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
