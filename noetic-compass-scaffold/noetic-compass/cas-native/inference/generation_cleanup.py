"""Generic generation-cleanup pass — token-corruption and repetition.

Classified as **HYGIENE**, not semantic repair. Per the postprocessor
policy line (user, 2026-05-10):

    The model remains the generator. Deterministic postprocessors
    may repair logged, source-preserving, mechanically unambiguous
    surface defects. They may not invent content, choose meanings,
    or replace the model's semantic work.

This pass clears the policy line by addressing only token-level
corruption — closer to spellcheck/tokenization cleanup than to CAS
rendering. It does NOT invent content, choose meanings, or replace
semantic work. The model's verbatim output is always preserved on
``raw_text``; only ``final_text`` gets cleaned.

Per user audit d5e0864 (post meta-logic Phase 1.5): "the easiest path
to hit 18/24 is probably record 3's repetition issue." Record 3's
raw model output:

  "Amemory memory triggered a memory or association triggered
   a connection in a principled foundation, expressed through an
   embodied way of sensing and moving."

Two distinct corruption patterns visible:
  1. ``Amemory memory`` — leading single-letter article fused into
     the next token ("A" + "memory" -> "Amemory"), followed by an
     adjacent duplicate "memory" copy.
  2. ``triggered ... triggered`` — verb echoed across the clause.
     This pattern is harder to detect deterministically without
     understanding semantic intent, so this pass leaves it alone
     (the existing ``repeated_phrase_count`` quality gate flags it;
     future work may re-roll generation when flagged).

This module is a deterministic, model-free repair layer that runs
LATE in postprocessing (after rpm_repair / meta_logic_repair). It
fixes only what's symbolically certain:
  - adjacent duplicate words ("memory memory" -> "memory"), with
    case-insensitive match and case-of-first preservation
  - merged-prefix tokens for a tight whitelist of CAS content
    words ("Amemory" -> "A memory"; whitelist prevents over-
    aggressive splits like "Anywhere" -> "An ywhere")

The whitelist matters: the word-split heuristic is dangerous if
applied to generic English. We restrict it to Noetic-colloquialism
content words that appear in the CAS rendering vocabulary — this
keeps the repair surgical to the failure modes the model
demonstrably produces.

**Regression signal (guardrail 5):** if cleanup fires on more than a
small fraction of records in a future eval, that's a model-quality
regression, not something to hide. The eval harness reports the
cleanup count per pack, and ``apply_generation_cleanup=False`` is
plumbed through ``postprocess()`` so diagnostic evals can flip the
pass off and grade against raw model output.

Always logged in :class:`GenerationCleanupLog` so audits can see
exactly which substitutions fired.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Adjacent duplicate words
# ---------------------------------------------------------------------------

# `\b(\w+)\s+\1\b` matches a word at a word boundary, then whitespace,
# then the same word at a word boundary. Case-insensitive so we catch
# "Memory memory" / "memory memory" / "Memory Memory".
_ADJACENT_DUP_RX = re.compile(r"\b(\w{2,})\s+\1\b", re.IGNORECASE)


def _collapse_adjacent_duplicates(
    text: str, log: "GenerationCleanupLog",
) -> str:
    """Collapse "Word word" adjacent duplicates to one occurrence,
    preserving the case of the first instance. Words shorter than 2
    chars are excluded so we don't collapse legitimate "I I" or
    "a a" (rare but possible in degenerate output)."""
    def _sub(m: re.Match) -> str:
        word = m.group(1)
        log.adjacent_duplicate_substitutions.append(
            AdjacentDuplicateSub(word=word, span=(m.start(), m.end()))
        )
        # Keep the first occurrence verbatim; drop the second.
        return word
    return _ADJACENT_DUP_RX.sub(_sub, text)


# ---------------------------------------------------------------------------
# Merged-prefix split (whitelist-gated)
# ---------------------------------------------------------------------------

# Whitelist of CAS Noetic-colloquialism content words that the model
# is observed to produce. Anything outside this list is left alone —
# we don't risk splitting "Anywhere" -> "An ywhere" or "Athletic" ->
# "A thletic" by being too aggressive.
_PREFIX_SPLIT_WHITELIST: tuple[str, ...] = (
    "memory", "thought", "idea", "connection", "association",
    "rhythm", "attention", "judgment", "foundation", "impression",
    "thinking", "feeling", "feedback",
)

# Article prefixes the model fuses with the next token. Match each
# prefix + a whitelisted word as a single non-broken sequence.
_PREFIX_FUSE_PATTERN = re.compile(
    r"\b(A|An|The|I)("
    + "|".join(_PREFIX_SPLIT_WHITELIST)
    + r")\b",
    re.IGNORECASE,
)


def _split_merged_prefixes(
    text: str, log: "GenerationCleanupLog",
) -> str:
    """Split fused article-prefix tokens. Only words in the
    Noetic-colloquialism whitelist are eligible to split; this
    keeps the repair surgical to observed failure modes."""
    def _sub(m: re.Match) -> str:
        prefix = m.group(1)
        word = m.group(2)
        original = m.group(0)
        # Preserve case of the prefix; lowercase the content word
        # IF the prefix was capitalized AND the content word was
        # in original lowercase (since the fused form preserved the
        # capitalization of just the leading character).
        new = f"{prefix} {word.lower()}"
        log.merged_prefix_substitutions.append(
            MergedPrefixSub(found=original, new=new)
        )
        return new
    return _PREFIX_FUSE_PATTERN.sub(_sub, text)


# ---------------------------------------------------------------------------
# Log dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdjacentDuplicateSub:
    """One adjacent-duplicate collapse."""
    word: str
    span: tuple[int, int]


@dataclass(frozen=True)
class MergedPrefixSub:
    """One merged-prefix split."""
    found: str
    new: str


@dataclass
class GenerationCleanupLog:
    """Audit-friendly summary of one generation-cleanup pass."""
    adjacent_duplicate_substitutions: list[AdjacentDuplicateSub] = field(
        default_factory=list
    )
    merged_prefix_substitutions: list[MergedPrefixSub] = field(
        default_factory=list
    )

    @property
    def n_substitutions(self) -> int:
        return (
            len(self.adjacent_duplicate_substitutions)
            + len(self.merged_prefix_substitutions)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "n_substitutions": self.n_substitutions,
            "n_adjacent_duplicates": len(
                self.adjacent_duplicate_substitutions
            ),
            "adjacent_duplicate_substitutions": [
                {"word": s.word, "span_start": s.span[0], "span_end": s.span[1]}
                for s in self.adjacent_duplicate_substitutions
            ],
            "n_merged_prefix_splits": len(self.merged_prefix_substitutions),
            "merged_prefix_substitutions": [
                {"found": s.found, "new": s.new}
                for s in self.merged_prefix_substitutions
            ],
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def cleanup_generation(text: str) -> tuple[str, GenerationCleanupLog]:
    """Run all generic cleanup passes on ``text``. Returns
    ``(cleaned_text, log)``. Order matters: split merged prefixes
    FIRST so a fused "Amemory memory" becomes "A memory memory"
    which then gets collapsed by the adjacent-duplicate pass to
    "A memory"."""
    log = GenerationCleanupLog()
    if not text:
        return text, log
    text = _split_merged_prefixes(text, log)
    text = _collapse_adjacent_duplicates(text, log)
    return text, log


__all__ = [
    "AdjacentDuplicateSub",
    "GenerationCleanupLog",
    "MergedPrefixSub",
    "cleanup_generation",
]
