"""Native free-form English surface generation from CAS expressions.

Phase 3 of the SDG pipeline. Whereas Lever 3 (sibling track) takes an
existing training-surface prompt and rewrites it via the Claude API,
this module generates a colloquial English prompt directly from a CAS
expression using only stdlib + the ``colloquialism_lexicon``. The
public surface is intentionally narrow:

    generate_free_form(cas_expression, *, seed=None, style="neutral") -> str
    expand_record(record, *, k, seed) -> list[dict]

``generate_free_form`` is the deterministic-given-seed primitive. Same
``cas_expression`` + same ``seed`` always returns byte-identical
output. Different seeds yield different surfaces.

``expand_record`` is the record-level API used by the driver script.
It produces K free-form variants of a Level 3 record, preserving every
sacred field (CAS expression, all 12 prediction labels, soft targets,
provenance) and only mutating ``user_prompt`` plus a small bag of
metadata fields (``expansion_method``, ``seed_used`` etc.).

Compositional rules implemented per Phase 3 spec:

1. simple state    -> "Working through this carefully, ... drawn to it."
2. copresence (+)  -> "When I think it through ... AND there's this
                       practiced rhythm I've built up over the years."
3. integration (×) -> "When I sit with how something feels ... I find
                       myself arriving at a clear sense of ..."
4. recipe          -> "What goes into producing X is roughly: 0.7 parts
                       of analytical decomposition plus 1.4 parts of ..."
5. meta-logic      -> "Looking at the cluster of cognitive moves here,
                       what they have in common is ..."

Anti-drift guarantees enforced by lexicon partition:

- ``^3`` Negative phrases come from ``NOETIC_LEXICON["3"]`` only, which
  contains zero ``audit/scrutinise/critique/dissect`` vocabulary.
- ``^8`` Above/Cause phrases come from ``NOETIC_LEXICON["8"]`` only,
  which contains zero deductive vocabulary
  (``therefore/thus/q.e.d./hence/ergo/consequently/deduce/it follows
  that``).
- ``^4`` Vibration phrases retain the etymological cognate (resonance,
  struck-a-chord) by construction.
"""

from __future__ import annotations

import copy
import hashlib
import random
import re
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .colloquialism_lexicon import (
    COPRESENCE_CONJUNCTIONS,
    DOMAIN_FLAVOR,
    DOMAIN_NAMES,
    DRIVE_FLAVOR,
    DRIVE_NAMES,
    INTEGRATION_OPENERS,
    INTEGRATION_RESULT_PHRASES,
    META_LOGIC_OPENERS,
    META_LOGIC_RELATION_PHRASES,
    NOETIC_LEXICON,
    NOETIC_NAMES,
    OMEGA_NAMES,
    RECIPE_INGREDIENT_CONJUNCTIONS,
    RECIPE_LEAKAGE_PHRASES,
    RECIPE_OPENERS,
    REGISTER_FRAMES,
    REGISTER_NAMES,
    SENTENCE_CONNECTIVES,
    normalise_omega_name,
)
from .compositional_rules import (
    SimpleState,
    StructuralPlan,
    parse_cas_expression,
)


# ---------------------------------------------------------------------------
# Sacred fields contract (mirrors demographic_tonal_rewrite.SACRED_FIELDS)
# ---------------------------------------------------------------------------
#
# Phase 3 expansion preserves these fields byte-identically between
# canonical and variant. Any breakage of this contract is a CI failure.

SACRED_FIELDS: frozenset[str] = frozenset(
    {
        # NOTE: ``id`` is intentionally NOT sacred — the driver re-keys
        # variants so concatenated corpora don't collide. ``source_level2_id``
        # IS sacred (it is the join key back to the canonical Level 2 record).
        "source_level2_id",
        "bucket",
        "cas_expression",
        "natural_language_mapping",
        "assistant_response",
        "follow_up_question",
        "soft_operator_targets",
        "soft_domain_targets",
        # The fuller v77 schema (when present in the source).
        "turn_type",
        "expression_family",
        "transition_kind",
        "noetic",
        "domain",
        "drive",
        "register_mode",
        "registers",
        "authority",
        "has_omega",
        "has_meta_logic",
        "meta_relations",
        "prior_cas_state",
    }
)


_EXPANSION_METHOD: str = "free_form_v1"


# ---------------------------------------------------------------------------
# Forbidden-vocabulary guards
# ---------------------------------------------------------------------------
#
# These regular expressions encode the CLAUDE.md anti-drift annotations
# at the SURFACE level: even if a future lexicon edit accidentally
# introduces forbidden vocabulary, this guard logs a deterministic
# warning and rolls the dice for an alternate phrase.

_NEG_FORBIDDEN_RE = re.compile(
    r"\b(audit|audits|audited|auditing|scrutini[sz]e|scrutini[sz]ed|"
    r"scrutini[sz]ing|critique|critiqued|critiquing|fact[- ]check|"
    r"find flaws|nitpick|nitpicking|tear apart|pick apart|dissect|"
    r"dissecting)\b",
    re.IGNORECASE,
)

_AC_FORBIDDEN_RE = re.compile(
    r"\b(therefore|thus|hence|q\.?e\.?d\.?|ergo|consequently|"
    r"it follows that|deduce|deduction|deduced|deducing)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Generator core
# ---------------------------------------------------------------------------


@dataclass
class GenerationContext:
    rng: random.Random
    style: str

    def pick(self, options: Sequence[str]) -> str:
        if not options:
            return ""
        return options[self.rng.randrange(len(options))]


def _seed_for(cas_expression: str, seed: Optional[int]) -> int:
    """Derive a stable per-call seed from ``cas_expression`` and ``seed``."""
    base = hashlib.sha1(
        f"{seed}|{cas_expression}".encode("utf-8")
    ).hexdigest()
    return int(base[:12], 16)


def _phrases_for_state(state: SimpleState) -> tuple[str, ...]:
    """Return the lexicon bucket appropriate to a state's register.

    Ranking:
    1. explicit ``register`` slot -> matching modifier list
    2. ``register_set`` (|⟨...⟩) -> first matching register's modifier
    3. unspecified -> ``base``
    """
    bucket = NOETIC_LEXICON.get(state.noetic)
    if bucket is None:
        return ()

    if state.register is not None:
        key = _register_to_key(state.register)
        phrases = bucket.get(key)
        if phrases:
            return phrases
    if state.register_set:
        for r in state.register_set:
            key = _register_to_key(r)
            phrases = bucket.get(key)
            if phrases:
                return phrases
    return bucket.get("base", ())


def _register_to_key(register: str) -> str:
    return {
        "T": "transcendent_modifier",
        "A": "analytical_modifier",
        "f": "felt_modifier",
        "E": "embodied_modifier",
    }.get(register, "base")


def _safe_pick(
    ctx: GenerationContext,
    options: Sequence[str],
    *,
    forbidden: Optional[re.Pattern[str]] = None,
    fallback: Optional[Sequence[str]] = None,
) -> str:
    """Pick a phrase, retrying if it triggers ``forbidden``.

    Used to enforce anti-drift at runtime even when the source lexicon
    has been carefully partitioned. If every option triggers the
    forbidden regex, falls back to the first non-empty option from
    ``fallback`` (or ``options`` if no fallback supplied).
    """
    if not options:
        if fallback:
            return fallback[0]
        return ""
    indices = list(range(len(options)))
    ctx.rng.shuffle(indices)
    if forbidden is None:
        return options[indices[0]]
    for idx in indices:
        candidate = options[idx]
        if not forbidden.search(candidate):
            return candidate
    # Every option tripped the guard; fall back.
    if fallback:
        return fallback[0]
    return options[0]


def _domain_marker(ctx: GenerationContext, domain: Optional[str]) -> str:
    if domain is None:
        return ""
    options = DOMAIN_FLAVOR.get(domain, ())
    return ctx.pick(options)


def _drive_marker(ctx: GenerationContext, drive: Optional[str]) -> str:
    if drive is None:
        return ""
    options = DRIVE_FLAVOR.get(drive, ())
    return ctx.pick(options)


def _register_frame(ctx: GenerationContext, register: Optional[str]) -> str:
    if register is None:
        return ""
    options = REGISTER_FRAMES.get(register, ())
    return ctx.pick(options)


# ---------------------------------------------------------------------------
# Shape-specific renderers
# ---------------------------------------------------------------------------


# Grammar-aware sentence frames for simple states. The renderer picks a
# frame whose verb agrees with the lexical shape of the chosen phrase.
# ``_select_frame`` introspects the phrase to decide which frame to use.

# Phrases that already start with a finite present-tense verb in the
# first-person singular ("popped into my head", "rubs me wrong",
# "hit me hard") read naturally inside the "what + finite verb"
# template family.
_FRAMES_DECLARATIVE: tuple[str, ...] = (
    "what I notice is that {phrase}",
    "what's going on is that {phrase}",
    "the read I have is that {phrase}",
    "where I land is that {phrase}",
    "the way I'd describe it: {phrase}",
)

# Phrases that read naturally as objects of "I find myself ___":
# gerund / participle ("drawing", "noticing it"), or short verb
# phrases ("drawn to it", "leaning into it").
_FRAMES_FIND_MYSELF: tuple[str, ...] = (
    "I find myself {phrase}",
    "I keep {phrase}",
    "I'm {phrase}",
    "honestly, I'm {phrase}",
)

# Phrases that read as standalone clauses ("it just clicked",
# "it sits well", "it just popped into my head"). The renderer
# prepends a connective rather than wedging it into a verb frame.
_FRAMES_STANDALONE: tuple[str, ...] = (
    "{phrase}",
    "honestly, {phrase}",
    "if I'm being plain, {phrase}",
)


def _select_frame(ctx: GenerationContext, phrase: str) -> str:
    """Pick a sentence frame appropriate to a phrase's grammar."""
    p = phrase.strip().lower()
    # Standalone clauses already make a sentence on their own.
    if p.startswith(("it ", "the thought ", "the answer ", "the conclusion ", "the gesture ", "the body ", "an idea ", "what arrived ", "what landed ", "what came ", "what dropped ", "what showed ")):
        return ctx.pick(_FRAMES_STANDALONE)
    # First-person verb-phrase fragments like "I bristle at it",
    # "I have to push back", "I keep arriving at no" — already a
    # sentence skeleton.
    if p.startswith("i "):
        return ctx.pick(_FRAMES_STANDALONE)
    # Phrases that start with a finite verb in 3rd person singular
    # ("rubs me wrong", "speaks to me", "hit me hard", "popped...").
    finite_3sg = (
        "rubs", "speaks", "hit", "hits", "made", "makes", "brought",
        "called", "linked", "summoned", "popped", "set off", "set me",
        "got me", "kicked", "started", "stirred", "moved", "registered",
        "landed", "really", "rings", "echoes", "lingers", "still",
        "violates", "cuts", "feels", "stands", "is wrong", "leaves",
        "reminds", "puts", "turns", "find", "have to", "doesn't",
        "the impression", "the affect", "the emotion", "the gut",
        "shoulders", "stomach", "jaw", "my body", "my hands", "feet",
        "chest", "vibrated", "physically", "shook", "rang",
        "every", "decades", "what", "the layers", "all", "everything",
        "years", "my professional", "the body of",
        "the framework", "the analytical", "the explicit", "the chain",
        "the formal", "the structured", "the body has", "the body",
    )
    if p.startswith(finite_3sg):
        return ctx.pick(_FRAMES_DECLARATIVE)
    # Default: fits inside "I find myself ___" or "I keep ___".
    return ctx.pick(_FRAMES_FIND_MYSELF)


def _render_simple(ctx: GenerationContext, state: SimpleState) -> str:
    options = _phrases_for_state(state)

    forbidden: Optional[re.Pattern[str]] = None
    if state.noetic == "3":
        forbidden = _NEG_FORBIDDEN_RE
    elif state.noetic == "8":
        forbidden = _AC_FORBIDDEN_RE

    fallback = NOETIC_LEXICON[state.noetic]["base"]
    phrase = _safe_pick(ctx, options, forbidden=forbidden, fallback=fallback)

    domain_flavor = _domain_marker(ctx, state.domain)
    drive_flavor = _drive_marker(ctx, state.drive)
    register_frame = _register_frame(ctx, state.register)

    frame = _select_frame(ctx, phrase)
    body = frame.format(phrase=phrase)

    parts: list[str] = []
    if register_frame:
        parts.append(register_frame)
    if domain_flavor:
        parts.append(f"on the {_strip_leading_article(domain_flavor)} side of things,")

    parts.append(body)

    if drive_flavor:
        parts.append(f"— {_strip_leading_article(drive_flavor)}")

    sentence = " ".join(p.strip() for p in parts if p.strip())
    sentence = _normalise_punctuation(sentence)
    return sentence


_LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)


def _strip_leading_article(text: str) -> str:
    """Drop a leading 'the'/'a'/'an' so flavor markers slot cleanly into
    'on the X side of things' without producing 'the the X'.
    """
    return _LEADING_ARTICLE_RE.sub("", text, count=1)


def _render_copresence(ctx: GenerationContext, plan: StructuralPlan) -> str:
    if not plan.substates:
        return ""

    rendered_parts: list[str] = []
    for i, state in enumerate(plan.substates):
        clause = _render_simple(ctx, state)
        if i == 0:
            rendered_parts.append(clause)
        else:
            connector = ctx.pick(COPRESENCE_CONJUNCTIONS)
            # Strip the leading register frame from continuation clauses
            # to keep the sentence readable.
            clause_continuation = _strip_leading_frame(clause)
            rendered_parts.append(f", {connector} {clause_continuation}")

    return _normalise_punctuation(" ".join(rendered_parts))


def _render_integration(ctx: GenerationContext, plan: StructuralPlan) -> str:
    if not plan.substates:
        return ""

    opener = ctx.pick(INTEGRATION_OPENERS)
    contributions: list[str] = []
    for state in plan.substates:
        phrases = _phrases_for_state(state)
        forbidden = None
        if state.noetic == "3":
            forbidden = _NEG_FORBIDDEN_RE
        elif state.noetic == "8":
            forbidden = _AC_FORBIDDEN_RE
        fallback = NOETIC_LEXICON[state.noetic]["base"]
        snippet = _safe_pick(ctx, phrases, forbidden=forbidden, fallback=fallback)
        contributions.append(snippet)

    if len(contributions) == 1:
        body = contributions[0]
    elif len(contributions) == 2:
        body = f"{contributions[0]} and {contributions[1]}"
    else:
        body = ", ".join(contributions[:-1]) + f", and {contributions[-1]}"

    omega = normalise_omega_name(plan.omega_name or "Omega_default")
    omega_gloss = OMEGA_NAMES.get(omega, OMEGA_NAMES["Omega_default"])
    if not omega_gloss:
        omega_gloss = "a unified emergent state"

    result_template = ctx.pick(INTEGRATION_RESULT_PHRASES)
    if "{result}" in result_template:
        result_clause = result_template.format(result=omega_gloss)
    else:
        result_clause = f"{result_template} {omega_gloss}"

    sentence = f"{opener} when I let {body} all enter the same place, {result_clause}."
    return _normalise_punctuation(sentence)


def _render_recipe(ctx: GenerationContext, plan: StructuralPlan) -> str:
    target_raw = normalise_omega_name(plan.omega_name or "Omega_default")
    target_gloss = OMEGA_NAMES.get(target_raw, OMEGA_NAMES["Omega_default"])
    opener_template = ctx.pick(RECIPE_OPENERS)
    opener = opener_template.format(target=target_gloss)

    if not plan.recipe_ingredients:
        return _normalise_punctuation(
            f"{opener} a layered combination of cognitive moves."
        )

    pieces: list[str] = []
    for coef, state in plan.recipe_ingredients:
        phrases = _phrases_for_state(state)
        forbidden = None
        if state.noetic == "3":
            forbidden = _NEG_FORBIDDEN_RE
        elif state.noetic == "8":
            forbidden = _AC_FORBIDDEN_RE
        fallback = NOETIC_LEXICON[state.noetic]["base"]
        snippet = _safe_pick(ctx, phrases, forbidden=forbidden, fallback=fallback)
        domain_marker = _domain_marker(ctx, state.domain)
        if domain_marker:
            phrase = f"{coef:g} parts of {snippet} ({domain_marker})"
        else:
            phrase = f"{coef:g} parts of {snippet}"
        pieces.append(phrase)

    conj = ctx.pick(RECIPE_INGREDIENT_CONJUNCTIONS)
    if len(pieces) == 1:
        body = pieces[0]
    elif len(pieces) == 2:
        body = f"{pieces[0]} {conj} {pieces[1]}"
    else:
        body = ", ".join(pieces[:-1]) + f", {conj} {pieces[-1]}"

    sentence = f"{opener} {body}"

    if plan.leakage:
        leakage_key = normalise_omega_name(plan.leakage)
        leakage_gloss = OMEGA_NAMES.get(leakage_key, "an unintended side product")
        leakage_template = ctx.pick(RECIPE_LEAKAGE_PHRASES)
        leakage_clause = leakage_template.format(leakage=leakage_gloss)
        sentence = f"{sentence}, {leakage_clause}"

    sentence = sentence + "."
    return _normalise_punctuation(sentence)


def _render_meta_logic(ctx: GenerationContext, plan: StructuralPlan) -> str:
    opener = ctx.pick(META_LOGIC_OPENERS)
    primary_relation = (
        plan.meta_relations[0] if plan.meta_relations else "family"
    )
    relation_phrases = META_LOGIC_RELATION_PHRASES.get(
        primary_relation, ()
    )
    relation_phrase = ctx.pick(relation_phrases) if relation_phrases else "the structural family is"

    glosses: list[str] = []
    seen_keys: set[tuple[Optional[str], str]] = set()
    for state in plan.substates:
        key = (state.domain, state.noetic)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        name = NOETIC_NAMES.get(state.noetic, "Idea")
        if state.domain:
            domain = DOMAIN_NAMES.get(state.domain, "")
            article = _indefinite_article(domain)
            glosses.append(f"{article} {domain} {name} move")
        else:
            article = _indefinite_article(name)
            glosses.append(f"{article} {name} move")
        if len(glosses) >= 6:
            break

    if not glosses:
        glosses.append("the cognitive moves at play")

    if len(glosses) == 1:
        listing = glosses[0]
    elif len(glosses) == 2:
        listing = f"{glosses[0]} and {glosses[1]}"
    else:
        listing = ", ".join(glosses[:-1]) + f", and {glosses[-1]}"

    sentence = f"{opener} {relation_phrase} {listing}."
    return _normalise_punctuation(sentence)


def _indefinite_article(word: str) -> str:
    """Return 'a' or 'an' depending on the first sound of ``word``."""
    if not word:
        return "a"
    return "an" if word[0].lower() in "aeiou" else "a"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_LEADING_FRAME_RE = re.compile(
    r"^(?:At the level of meaning|Looking at the whole arc|In the bigger picture|"
    r"Where it really matters|From where I stand on this|Stepping back to the deepest read|"
    r"From the meaning of it|When I take in the larger sense|"
    r"Working through this carefully|When I think it through|Step by step|"
    r"Reasoning it out|Laying out the logic|Walking the chain of thought|"
    r"When I sit and reason about it|On reflection|"
    r"Feeling into it|Sitting with how it feels|Honestly|On the gut level|"
    r"Where the feeling sits|When I check the feeling|From the gut|"
    r"Where the affect lands|"
    r"In the body|Where my hands meet it|When I actually do it|In the doing|"
    r"Where I physically engage with it|On the floor, in practice|"
    r"When my body is on the line|Out in the actual movement),?\s*",
    re.IGNORECASE,
)


def _strip_leading_frame(text: str) -> str:
    """Remove a register-frame opener from a continuation clause."""
    return _LEADING_FRAME_RE.sub("", text, count=1).lstrip()


_PUNCT_RE = re.compile(r"\s+([.,;:!?])")
_DUP_SPACE_RE = re.compile(r"\s{2,}")
_DUP_DASH_RE = re.compile(r"—\s*—+")


def _normalise_punctuation(text: str) -> str:
    text = _PUNCT_RE.sub(r"\1", text)
    text = _DUP_DASH_RE.sub("—", text)
    text = _DUP_SPACE_RE.sub(" ", text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text = text + "."
    return text


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def generate_free_form(
    cas_expression: str,
    *,
    seed: Optional[int] = None,
    style: str = "neutral",
) -> str:
    """Generate a free-form English prompt expressing ``cas_expression``.

    Parameters
    ----------
    cas_expression:
        A CAS expression string. Supported shapes: simple state (e.g.
        ``^3^E_{F2}|A``), co-presence (``+`` joined), integration
        (``×`` with ``=``), recipe (``Theta(Omega_*) = ... -> ...``),
        meta-logic (``StateCluster{...} ∩ ...``).
    seed:
        Optional integer seed for deterministic surface selection.
        ``None`` means use a global random; in that case the function
        is non-deterministic.
    style:
        Reserved for future integration with the demographic +
        tonal axes module. Currently only ``"neutral"`` is honoured.

    Returns
    -------
    str
        A colloquial English sentence (or short paragraph) describing
        the underlying CAS structure. The output never names CAS
        primitives by their formal symbols.
    """
    plan = parse_cas_expression(cas_expression)
    rng_seed = _seed_for(cas_expression, seed if seed is not None else 0)
    if seed is None:
        rng = random.Random()
    else:
        rng = random.Random(rng_seed)

    ctx = GenerationContext(rng=rng, style=style)

    if plan.shape == "simple" and plan.substates:
        return _render_simple(ctx, plan.substates[0])
    if plan.shape == "copresence":
        return _render_copresence(ctx, plan)
    if plan.shape == "integration":
        return _render_integration(ctx, plan)
    if plan.shape == "recipe":
        return _render_recipe(ctx, plan)
    if plan.shape == "meta_logic":
        return _render_meta_logic(ctx, plan)

    # Fallback: emit a generic sentence that still preserves the
    # CAS-isn't-mentioned guarantee.
    if plan.substates:
        return _render_simple(ctx, plan.substates[0])
    return _normalise_punctuation(
        "Something is going on cognitively that's hard to put a label on"
    )


# ---------------------------------------------------------------------------
# Record-level expansion helpers (used by the driver script)
# ---------------------------------------------------------------------------


def _per_record_seed(record_id: str, variant_index: int, global_seed: int) -> int:
    digest = hashlib.sha1(
        f"{global_seed}|{record_id}|{variant_index}".encode("utf-8")
    ).hexdigest()
    return int(digest[:12], 16)


def expand_record(
    record: dict[str, Any],
    *,
    k: int = 3,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Return ``k`` free-form variants of a Level 3 conversational record.

    Each variant has the same labels (turn_type, expression_family,
    transition_kind, noetic, domain, drive, register_mode, registers,
    authority, has_omega, has_meta_logic, meta_relations) — only
    ``user_prompt`` changes. Metadata fields ``expansion_method``,
    ``seed_used``, and a ``free_form`` block in ``provenance`` are
    added.

    Determinism: ``record["id"]`` (or ``source_level2_id``) plus the
    global ``seed`` plus the variant index seeds an RNG that the
    surface generator consumes.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    cas_expression = record.get("cas_expression", "")
    record_id = str(record.get("id") or record.get("source_level2_id") or "")
    variants: list[dict[str, Any]] = []

    for variant_idx in range(k):
        per_seed = _per_record_seed(record_id, variant_idx, seed)
        new_prompt = generate_free_form(cas_expression, seed=per_seed)
        variant = copy.deepcopy(record)
        variant["user_prompt"] = new_prompt
        variant["expansion_method"] = _EXPANSION_METHOD
        variant["seed_used"] = per_seed
        # Preserve and extend the provenance block.
        prov = variant.get("provenance")
        if not isinstance(prov, dict):
            prov = {}
        prov_free_form = {
            "expansion_method": _EXPANSION_METHOD,
            "global_seed": seed,
            "per_record_seed": per_seed,
            "variant_index": variant_idx,
            "source_record_id": record_id,
            "cas_expression_at_expansion": cas_expression,
        }
        prov["free_form"] = prov_free_form
        variant["provenance"] = prov
        # Append free_form-specific tags.
        tags = list(variant.get("tags", []))
        for tag in ("phase3", "free_form_v1", _EXPANSION_METHOD):
            if tag not in tags:
                tags.append(tag)
        variant["tags"] = tags
        # Re-key the variant id so concatenated corpora don't collide.
        variant_id_seed = hashlib.sha1(
            f"{record_id}|{variant_idx}|{seed}|free_form".encode("utf-8")
        ).hexdigest()[:12]
        variant["id"] = f"l3conv-ff-{variant_id_seed}"
        variants.append(variant)

    return variants


__all__ = [
    "SACRED_FIELDS",
    "generate_free_form",
    "expand_record",
]
