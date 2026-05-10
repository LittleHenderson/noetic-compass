"""Tests for cas_native.inference.generation_cleanup.

Coverage:
  - Adjacent duplicate collapse: case-insensitive matching, case-of-
    first preservation, no-op for clean text, multi-word doubling.
  - Merged-prefix split: only whitelisted CAS content words are
    eligible; non-whitelisted fused words pass through unchanged.
  - End-to-end record-3 pattern: "Amemory memory" -> "A memory".
  - Log structure + serializability.
"""
from __future__ import annotations

from cas_native.inference.generation_cleanup import (
    GenerationCleanupLog,
    cleanup_generation,
)


# ---------------------------------------------------------------------------
# Adjacent duplicate collapse
# ---------------------------------------------------------------------------

def test_collapse_adjacent_duplicates_basic():
    out, log = cleanup_generation("the cat sat on the the mat")
    assert out == "the cat sat on the mat"
    assert len(log.adjacent_duplicate_substitutions) == 1
    assert log.adjacent_duplicate_substitutions[0].word == "the"


def test_collapse_adjacent_duplicates_case_insensitive():
    """'Memory memory' should collapse case-insensitively."""
    out, log = cleanup_generation("Memory memory triggered something.")
    assert out == "Memory triggered something."


def test_collapse_adjacent_duplicates_preserves_first_case():
    out, log = cleanup_generation("First first time we saw it.")
    assert out == "First time we saw it."


def test_collapse_no_op_when_no_duplicates():
    text = "A clean sentence with no doubled words."
    out, log = cleanup_generation(text)
    assert out == text
    assert log.n_substitutions == 0


def test_collapse_handles_multiple_duplicates_in_one_text():
    out, log = cleanup_generation(
        "the the cat sat on the the mat"
    )
    assert out.count("the the") == 0
    assert "the cat sat on the mat" in out


def test_collapse_does_not_collapse_single_char_words():
    """Single-char tokens (a, I) excluded by the >=2 length gate to
    avoid mauling legitimate degenerate cases like "a a a" to a
    single "a"."""
    out, log = cleanup_generation("I I had a thought.")
    assert "I I" in out


# ---------------------------------------------------------------------------
# Merged-prefix split
# ---------------------------------------------------------------------------

def test_split_amemory_to_a_memory():
    """Audit's record-3 finding: 'Amemory' should split to 'A memory'."""
    out, log = cleanup_generation("Amemory triggered a connection.")
    assert "A memory triggered" in out
    assert "Amemory" not in out
    assert len(log.merged_prefix_substitutions) == 1


def test_split_athought_to_a_thought():
    out, log = cleanup_generation("Athought came to mind.")
    assert "A thought" in out
    assert "Athought" not in out


def test_split_anidea_to_an_idea():
    out, log = cleanup_generation("Anidea formed in my head.")
    assert "An idea" in out
    assert "Anidea" not in out


def test_split_does_not_touch_non_whitelisted_words():
    """Anywhere, anytime, athletic, etc. must not be split — they're
    legitimate English words that share the prefix-fuse pattern."""
    text = "Anywhere we go, athletic activity follows."
    out, log = cleanup_generation(text)
    assert "Anywhere" in out
    assert "athletic" in out
    assert log.n_substitutions == 0


def test_split_then_collapse_for_record_3_pattern():
    """End-to-end: the actual record-3 corruption pattern.
    'Amemory memory triggered ...' -> 'A memory triggered ...'
    via the order: split prefix first, then collapse adjacent dup."""
    raw = (
        "Amemory memory triggered a memory or association triggered "
        "a connection in a principled foundation."
    )
    out, log = cleanup_generation(raw)
    # First: 'Amemory' -> 'A memory'.
    assert "Amemory" not in out
    # Then 'A memory memory' -> 'A memory'.
    assert "memory memory" not in out
    # Result starts with 'A memory triggered'.
    assert out.startswith("A memory triggered")
    # Both kinds of substitution recorded in log.
    assert len(log.merged_prefix_substitutions) >= 1
    assert len(log.adjacent_duplicate_substitutions) >= 1


# ---------------------------------------------------------------------------
# Log structure
# ---------------------------------------------------------------------------

def test_log_to_dict_serializable():
    raw = "Amemory memory triggered the the connection."
    _, log = cleanup_generation(raw)
    d = log.to_dict()
    for key in [
        "n_substitutions",
        "n_adjacent_duplicates",
        "adjacent_duplicate_substitutions",
        "n_merged_prefix_splits",
        "merged_prefix_substitutions",
    ]:
        assert key in d, key
    import json
    json.dumps(d)


def test_empty_text_no_op():
    out, log = cleanup_generation("")
    assert out == ""
    assert log.n_substitutions == 0


def test_clean_text_makes_no_substitutions():
    text = (
        "When one thing reminds you of another, triggering a memory "
        "in a principled foundation."
    )
    out, log = cleanup_generation(text)
    assert out == text
    assert log.n_substitutions == 0
