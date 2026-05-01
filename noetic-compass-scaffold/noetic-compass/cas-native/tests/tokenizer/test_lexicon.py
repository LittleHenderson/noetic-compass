"""Tests for the CAS lexicon schema, loader, and lookup."""

from __future__ import annotations

import json

import pytest

from cas_native.tokenizer.lexicon import (
    CASLexicon,
    LexiconEntry,
    load_seed_lexicon,
    seed_lexicon_path,
)
from cas_native.tokenizer.structured_token import (
    DOMAIN_LABELS,
    REGISTER_LABELS,
    CASSignature,
)


def _noetic_sig(idx: int, val: float = 0.9) -> CASSignature:
    n = [0.0] * 10
    n[idx] = val
    return CASSignature(noetic=tuple(n))


def test_seed_lexicon_loads_and_has_minimum_size():
    lex = load_seed_lexicon()
    assert lex.size >= 80, f"seed lexicon too small: {lex.size}"


def test_seed_lexicon_jsonl_is_one_entry_per_line():
    path = seed_lexicon_path()
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    for line in lines:
        json.loads(line)
    assert len(lines) >= 80


def test_seed_lexicon_anti_drift_visceral_negatives():
    """^3 entries must be visceral; analytical-critique words go to ^6."""
    lex = load_seed_lexicon()

    can_t_stomach = lex.lookup_multiword_at("can't stomach this", 0)
    assert can_t_stomach is not None
    assert can_t_stomach.entry.signature.noetic[3] >= 0.9

    audit = lex.lookup_single_word("audit")
    assert audit is not None
    assert audit.signature.noetic[6] >= 0.8
    assert audit.signature.noetic[3] == 0.0, "audit must NOT fire ^3 — anti-drift"

    scrutinize = lex.lookup_single_word("scrutinize")
    assert scrutinize is not None
    assert scrutinize.signature.noetic[6] >= 0.8
    assert scrutinize.signature.noetic[3] == 0.0


def test_seed_lexicon_anti_drift_associative_triggers():
    """^8 entries must be associative; deductive reasoning is NOT ^8."""
    lex = load_seed_lexicon()
    reminds = lex.lookup_multiword_at("that reminds me of yesterday", 0)
    assert reminds is not None
    assert reminds.entry.signature.noetic[8] >= 0.85
    triggered = lex.lookup_single_word("triggered")
    assert triggered is not None
    assert triggered.signature.noetic[8] >= 0.85


def test_seed_lexicon_etymological_cognate_for_vibration():
    lex = load_seed_lexicon()
    struck = lex.lookup_multiword_at("really struck a chord with me", 7)
    assert struck is not None
    assert struck.entry.signature.noetic[4] >= 0.9


def test_demographic_register_variants_share_axis():
    """Different demographic surfaces collapse to identical CAS axes."""
    lex = load_seed_lexicon()
    base = lex.lookup_single_word("exhausted")
    working = lex.lookup_multiword_at("hella tired today", 0)
    child = lex.lookup_multiword_at("super sleepy now", 0)
    academic = lex.lookup_multiword_at("profoundly fatigued by", 0)
    assert base is not None
    assert working is not None and "working_class" in working.entry.register_variants
    assert child is not None and "child" in child.entry.register_variants
    assert academic is not None and "academic" in academic.entry.register_variants
    for sig in (
        base.signature,
        working.entry.signature,
        child.entry.signature,
        academic.entry.signature,
    ):
        assert sig.drive[2] < 0.0, "all variants must depress F3 vitality"


def test_lexicon_validate_rejects_zero_confidence_entry():
    bad = LexiconEntry(
        surface="x", signature=CASSignature.neutral(), confidence=0.0
    )
    errors = bad.validate()
    assert any("confidence=0.0 outside" in e for e in errors)


def test_lexicon_validate_rejects_inconsistent_multiword_flag():
    bad = LexiconEntry(
        surface="not multi",
        signature=CASSignature.neutral(),
        confidence=0.7,
        is_multiword=False,
    )
    errors = bad.validate()
    assert any("multiword" in e.lower() for e in errors)


def test_context_required_rejects_match_without_context():
    """Context regex anchored against the ␟ separator must reject when
    the linking verb appears only AFTER the candidate, not before."""
    entry = LexiconEntry(
        surface="kind of",
        signature=CASSignature(role_tags=("confidence_hedge",)),
        confidence=0.8,
        is_multiword=True,
        context_required=r"\b(am|is|feel|seem)\b[^␟]*␟",
    )
    lex = CASLexicon([entry])
    # "what kind of cookie is this" — "is" comes AFTER "kind of", regex
    # requires it BEFORE the ␟ separator. Match must fail.
    no_ctx = lex.lookup_multiword_at("what kind of cookie is this", 5)
    assert no_ctx is None


def test_context_required_accepts_match_with_context():
    entry = LexiconEntry(
        surface="kind of",
        signature=CASSignature(role_tags=("confidence_hedge",)),
        confidence=0.8,
        is_multiword=True,
        context_required=r"\b(am|is|feel|feels)\b[^␟]*␟",
    )
    lex = CASLexicon([entry])
    text = "I feel kind of tired"
    pos = text.index("kind of")
    match = lex.lookup_multiword_at(text, pos)
    assert match is not None
    assert match.entry.surface == "kind of"


def test_lookup_multiword_returns_none_at_eof():
    lex = load_seed_lexicon()
    text = "hello"
    assert lex.lookup_multiword_at(text, len(text)) is None


def test_jsonl_round_trip(tmp_path):
    entries = [
        LexiconEntry(
            surface="drawn to",
            signature=_noetic_sig(2, 0.95),
            confidence=0.95,
            is_multiword=True,
            notes="round-trip test entry",
        ),
        LexiconEntry(
            surface="audit", signature=_noetic_sig(6, 0.85), confidence=0.85,
        ),
    ]
    lex = CASLexicon(entries)
    path = tmp_path / "round_trip.jsonl"
    lex.to_jsonl(path)
    restored = CASLexicon.from_jsonl(path)
    assert restored.size == 2
    assert restored.lookup_single_word("audit") is not None


def test_lookup_is_case_insensitive():
    lex = load_seed_lexicon()
    assert lex.lookup_single_word("audit") is not None
    assert lex.lookup_single_word("AUDIT") is not None
    assert lex.lookup_single_word("Audit") is not None
