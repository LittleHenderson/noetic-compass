"""Record-level demographic + tonal rewriter for Level 3 CAS records.

Path A (rule-based, stdlib only). Given a Level 3 conversational record
and a (profile, tone) pair, return a NEW record where:

- ``user_prompt`` has been rewritten in the profile's voice and tone's
  register.
- Every label-bearing field is preserved unchanged. The rewriter only
  touches ``user_prompt`` plus a ``demographic_tonal`` annotation in
  ``provenance``.
- Top-level metadata fields ``demographic_profile``, ``tonal_register``,
  and ``expansion_method`` are added so downstream loaders can stratify.

Path B (Claude API rewrite) is documented as a fallback in the spec
doc and is NOT implemented here. The runbook in
``docs/working/sdg_demographic_tonal_spec_2026_05_04.md`` enumerates
when to escalate.

Public surface:

    SACRED_FIELDS                       — fields the rewriter MUST NOT modify
    rewrite_record(...)                  — record + (profile, tone) -> new record
    rewrite_user_prompt(...)             — bare-string variant for ad hoc use

The rewriter is deterministic given a seed derived from
``(record_id, profile_code, tone_code)``: rerunning the expansion from
the same source corpus produces byte-identical outputs.
"""

from __future__ import annotations

import copy
import hashlib
import random
import re
from dataclasses import dataclass
from typing import Any, Sequence

from .demographic_tonal_axes import (
    DemographicProfile,
    TonalRegister,
    profile_for,
    tone_for,
)


# ---------------------------------------------------------------------------
# Label-preservation contract
# ---------------------------------------------------------------------------
#
# These are the fields the rewriter is forbidden from modifying. Any
# downstream training pipeline assumes they remain bit-identical to the
# canonical source. ``user_prompt`` and the new metadata keys are the
# ONLY allowed differences between a canonical record and its variant.
#
# This list is intentionally broad: it includes every label, every soft
# target, every CAS-structure-bearing field, and the bucket / expression
# family. ``provenance`` is deep-copied through and only one new
# ``demographic_tonal`` sub-key is added.
SACRED_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "source_level2_id",
        "bucket",
        "cas_expression",
        "natural_language_mapping",
        "assistant_response",
        "follow_up_question",
        "soft_operator_targets",
        "soft_domain_targets",
        # The fuller v77 schema (referenced in the task brief)
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
# NOTE: ``tags`` is intentionally NOT sacred — the rewriter appends
# demographic_tonal / profile / tone tags so downstream filters can
# stratify. Any pre-existing tags survive (the appender uses
# dict.fromkeys to preserve order and dedupe). The label-bearing
# content of a record lives in the slot fields above, not in tags.


_EXPANSION_METHOD = "rule_based_v1"
_TARGET_PROMPT_RE = re.compile(
    r"\b(families?:[^?.]+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Profile-flavored sentence frames
# ---------------------------------------------------------------------------
#
# Each frame is a template the rewriter wraps around the existing CAS
# slot description. ``{slot_block}`` is the structural payload (the
# part that must be preserved so the model can still recover the CAS
# expression). ``{lexicon}`` lets the template pull a profile-specific
# token. ``{closer}`` is the target ask ("What's the notation?", etc.).
#
# Frames are listed multiple-per-profile so the rewriter can rotate.
# All frames preserve the slot block verbatim — that block is what
# carries the recoverability signal the model trains on.
_PROFILE_FRAMES: dict[str, tuple[str, ...]] = {
    "P1": (
        "Quick one — I'm trying to {lexicon} this CAS read. "
        "The structure is: {slot_block}. {closer}",
        "Need to ship a CAS notation for: {slot_block}. {closer}",
        "On a tight scope here: {slot_block}. {closer}",
    ),
    "P2": (
        "One might consider the following CAS structure: {slot_block}. "
        "{closer}",
        "Broadly speaking, the structure under analysis is: {slot_block}. "
        "{closer}",
        "Consider that the formal slots are: {slot_block}. {closer}",
    ),
    "P3": (
        "In my experience this presents as: {slot_block}. {closer}",
        "The intake is straightforward: {slot_block}. {closer}",
        "Clinically, the read is: {slot_block}. {closer}",
    ),
    "P4": (
        "Kindly please, I would like to know — the structure is "
        "in the case of: {slot_block}. {closer}",
        "Maybe is possible you can help — actually the same has "
        "this structure: {slot_block}. {closer}",
        "Perhaps you can explain — if I may, the slots are: "
        "{slot_block}. {closer}",
    ),
    "P5": (
        "Okay so this thing kinda goes like: {slot_block}. {closer}",
        "I dunno, the whole shape is sorta: {slot_block}. {closer}",
        "Honestly I'm just trying to figure this out — it's like: "
        "{slot_block}. {closer}",
    ),
    "P6": (
        "Before I accept the framing — what's the CAS read of: "
        "{slot_block}? {closer}",
        "Conditional on the slots being right, the structure is: "
        "{slot_block}. {closer}",
        "I'd want to see how this resolves: {slot_block}. {closer}",
    ),
    "P7": (
        "Sorry, this might be a dumb question, but I'm trying to figure "
        "out: {slot_block}. {closer}",
        "I'm new to CAS — is it okay if I ask about: {slot_block}? {closer}",
        "I hope this isn't off-base, but the structure I'm staring at "
        "is: {slot_block}. {closer}",
    ),
    "P8": (
        "Look — {slot_block}. {closer}",
        "Right, the read is: {slot_block}. {closer}",
        "Cut to it: {slot_block}. {closer}",
    ),
}


# Profile-specific closers (the "ask" at the end of the prompt). The
# closer is what the model is trained to answer; it MUST stay clearly
# expression-asking so the assistant_response remains a valid target.
_PROFILE_CLOSERS: dict[str, tuple[str, ...]] = {
    "P1": (
        "What's the notation?",
        "Give me the spec.",
        "What CAS expression maps to that?",
    ),
    "P2": (
        "What is the precise notation?",
        "How would one render this in CAS?",
        "Could you supply the formal CAS expression?",
    ),
    "P3": (
        "What's the CAS notation?",
        "What expression should I record?",
        "Give me the precise CAS read.",
    ),
    "P4": (
        "Please, what is the notation?",
        "Maybe you can give the exact expression?",
        "Kindly, what is the CAS expression?",
    ),
    "P5": (
        "Like, what's the actual notation?",
        "How do I write that in CAS?",
        "What's the CAS thing for it?",
    ),
    "P6": (
        "What notation does that resolve to?",
        "Show me the CAS expression.",
        "What's the precise CAS read?",
    ),
    "P7": (
        "What would the notation be? I just want to make sure.",
        "Could you maybe tell me the CAS expression?",
        "What's the right CAS notation here, if it's not too much trouble?",
    ),
    "P8": (
        "Notation?",
        "Give me the expression.",
        "What's it map to?",
    ),
}


# Tone interjections layered on top of profile output. Hedge tokens are
# inserted with probability ``hedge_density``.
_HEDGE_TOKENS: tuple[str, ...] = (
    "I think", "maybe", "I'm not totally sure but", "kind of",
    "sort of", "if I'm reading this right",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RewriteResult:
    """Result of a single rewrite call."""

    user_prompt: str
    profile_code: str
    tone_code: str
    expansion_method: str
    seed: int


def rewrite_record(
    record: dict[str, Any],
    *,
    profile_code: str,
    tone_code: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Return a new Level 3 record with a (profile, tone)-flavored prompt.

    The returned dict is a deep copy of ``record`` with:

    - ``user_prompt`` rewritten in the profile/tone voice.
    - ``demographic_profile`` set to ``profile_code`` (top-level).
    - ``tonal_register`` set to ``tone_code`` (top-level).
    - ``expansion_method`` set to ``"rule_based_v1"`` (top-level).
    - ``provenance.demographic_tonal`` populated with the same metadata
      plus the seed used (for full reproducibility).

    Every other field — every label, every CAS slot, every soft target,
    the cas_expression, the assistant_response, the follow_up_question,
    natural_language_mapping, tags, and provenance keys other than
    ``demographic_tonal`` — is preserved unchanged.

    Raises
    ------
    KeyError
        If ``profile_code`` or ``tone_code`` is not a valid axis code.
    ValueError
        If ``record`` lacks a ``user_prompt`` field.
    """
    if "user_prompt" not in record:
        raise ValueError(
            "rewrite_record requires record['user_prompt']; "
            f"got keys: {sorted(record)}"
        )

    profile = profile_for(profile_code)
    tone = tone_for(tone_code)

    # Derive a stable seed from (record id, profile, tone). Caller may
    # override for testing.
    if seed is None:
        seed = _derive_seed(record, profile_code, tone_code)
    rng = random.Random(seed)

    new_prompt = _rewrite_prompt(
        record["user_prompt"], profile=profile, tone=tone, rng=rng
    )

    new_record = copy.deepcopy(record)
    new_record["user_prompt"] = new_prompt
    new_record["demographic_profile"] = profile_code
    new_record["tonal_register"] = tone_code
    new_record["expansion_method"] = _EXPANSION_METHOD

    provenance = new_record.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    provenance["demographic_tonal"] = {
        "profile_code": profile_code,
        "profile_name": profile.name,
        "tone_code": tone_code,
        "tone_name": tone.name,
        "expansion_method": _EXPANSION_METHOD,
        "seed": seed,
    }
    new_record["provenance"] = provenance

    # Tag the variant for downstream filtering.
    tags = new_record.get("tags")
    if isinstance(tags, list):
        extra = [
            "demographic_tonal",
            f"profile_{profile_code}",
            f"tone_{tone_code}",
        ]
        new_record["tags"] = list(dict.fromkeys(list(tags) + extra))

    return new_record


def rewrite_user_prompt(
    user_prompt: str,
    *,
    profile_code: str,
    tone_code: str,
    seed: int = 0,
) -> str:
    """Rewrite a single user_prompt string. Stdlib-only convenience."""
    profile = profile_for(profile_code)
    tone = tone_for(tone_code)
    return _rewrite_prompt(
        user_prompt, profile=profile, tone=tone, rng=random.Random(seed)
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_seed(
    record: dict[str, Any], profile_code: str, tone_code: str
) -> int:
    """Stable seed from (record id, profile, tone) for deterministic rewrites."""
    record_id = str(record.get("id") or record.get("source_level2_id") or "")
    h = hashlib.sha1(
        f"{record_id}|{profile_code}|{tone_code}".encode("utf-8")
    ).hexdigest()
    return int(h[:12], 16)


def _extract_slot_block(user_prompt: str) -> tuple[str, str, str]:
    """Split the canonical prompt into (lead, slot_block, tail).

    Canonical Level 3 prompts have a recoverable structure such as

        "I am learning CAS. The target structure is families: state
         expression; states: Noetic ^2; domain O (operational); ...
         What is the precise notation?"

    The slot block ("families: ...; ...; operators: ...") is what the
    model trains on. We must preserve it verbatim. Lead and tail are
    discarded and replaced by profile/tone-flavored framing.

    If no recoverable slot block is found (unusual but possible for
    some legacy records), ``slot_block`` falls back to the full prompt
    minus any trailing question, and the rewriter wraps it in profile
    framing as best-effort.
    """
    text = user_prompt.strip()

    match = _TARGET_PROMPT_RE.search(text)
    if match:
        slot_start = match.start()
        # Slot block runs to the next sentence-final question or end-of-string.
        # Heuristic: cut at the last "? " before a wh-word, or at the end.
        slot_block = text[slot_start:].rstrip()

        # Strip a trailing question if present (we substitute our own closer).
        # Look for the last sentence boundary that ends with "?".
        question_match = re.search(r"\.[^.?!]*\?\s*$", slot_block)
        if question_match:
            slot_block = slot_block[: question_match.start()].rstrip(" .")
        else:
            # Strip trailing period.
            slot_block = slot_block.rstrip(" .?")
        return text[:slot_start].rstrip(), slot_block, ""

    # No "families:" anchor; treat the whole thing as the slot block.
    cleaned = text.rstrip(" .?")
    return "", cleaned, ""


def _rewrite_prompt(
    user_prompt: str,
    *,
    profile: DemographicProfile,
    tone: TonalRegister,
    rng: random.Random,
) -> str:
    """Compose a profile-flavored, tone-shaped prompt around the slot block."""
    _, slot_block, _ = _extract_slot_block(user_prompt)

    frames = _PROFILE_FRAMES[profile.code]
    frame = rng.choice(frames)
    closer = rng.choice(_PROFILE_CLOSERS[profile.code])
    lexicon_token = rng.choice(profile.typical_lexicon)

    body = frame.format(
        slot_block=slot_block,
        closer=closer,
        lexicon=lexicon_token,
    )

    body = _strip_avoid_lexicon(body, profile.avoid_lexicon)
    body = _apply_tone(body, tone, rng=rng)
    return body


def _strip_avoid_lexicon(
    text: str, avoid_lexicon: Sequence[str]
) -> str:
    """Remove any avoid-lexicon tokens that snuck in from generic templates.

    Avoid lexicon is a profile-level negative constraint: the rewriter
    should not put words in a profile's mouth that the profile would
    not say. Most templates already steer clear, but the closer / frame
    rotation is small enough that the safety net is cheap.
    """
    if not avoid_lexicon:
        return text
    out = text
    for token in avoid_lexicon:
        if not token:
            continue
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        out = pattern.sub("", out)
    # Collapse whitespace cosmetic damage.
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _apply_tone(
    text: str, tone: TonalRegister, *, rng: random.Random
) -> str:
    """Layer tone onto a profile-shaped prompt.

    Tone modifies the SAME content; it does not re-author the slot
    block. We layer tone by:

    1. Optionally prefixing a ``sentence_starter``.
    2. Optionally suffixing a ``sentence_ender``.
    3. Inserting hedge tokens with probability ``hedge_density``.
    """
    out = text

    # Prefix.
    if tone.sentence_starters:
        starter = rng.choice(tone.sentence_starters)
        if starter:
            out = f"{starter} {out}"

    # Suffix.
    if tone.sentence_enders:
        ender = rng.choice(tone.sentence_enders)
        if ender:
            # If the body already ends in punctuation, replace it.
            out = out.rstrip(" .?!")
            out = f"{out}{ender}" if ender.startswith(
                (".", "!", "?", " ", ",")
            ) else f"{out} {ender}"

    # Hedge insertion (saturation up to ``hedge_density``).
    if tone.hedge_density > 0:
        insertions = int(round(tone.hedge_density * 3))
        for _ in range(insertions):
            if rng.random() < tone.hedge_density:
                hedge = rng.choice(_HEDGE_TOKENS)
                # Insert near a sentence boundary if available.
                parts = out.split(". ")
                if len(parts) > 1:
                    idx = rng.randrange(len(parts) - 1)
                    parts[idx] = f"{parts[idx]} ({hedge})"
                    out = ". ".join(parts)
                else:
                    # Single-sentence body — append parenthetical.
                    out = f"{out.rstrip()} ({hedge})"

    # Final whitespace cleanup.
    out = re.sub(r"\s+", " ", out).strip()
    # Ensure terminal punctuation if absent.
    if out and out[-1] not in ".!?":
        out = f"{out}."
    return out


__all__ = [
    "SACRED_FIELDS",
    "RewriteResult",
    "rewrite_record",
    "rewrite_user_prompt",
]
