"""Tests for the pre-tokenizer."""

from __future__ import annotations

from cas_native.tokenizer.pretokenizer import (
    KIND_CAS_CANDIDATE,
    KIND_PUNCT,
    KIND_WHITESPACE,
    KIND_WORD,
    pretokenize,
    reassemble,
)


def test_pretokenize_round_trips_input():
    text = "I feel kind of nervous about doing this thing."
    spans = pretokenize(text)
    assert reassemble(spans) == text


def test_pretokenize_preserves_offsets():
    text = "drawn to it"
    spans = pretokenize(text)
    for span in spans:
        assert text[span.start : span.end] == span.text


def test_pretokenize_keeps_apostrophes_inside_words():
    text = "I can't stomach it"
    spans = pretokenize(text)
    word_texts = [s.text for s in spans if s.kind == KIND_WORD]
    assert "can't" in word_texts


def test_pretokenize_separates_punctuation():
    text = "Hello, world!"
    spans = pretokenize(text)
    kinds = [s.kind for s in spans]
    assert KIND_PUNCT in kinds
    assert any(s.text == "," for s in spans)
    assert any(s.text == "!" for s in spans)


def test_pretokenize_flags_cas_candidate_for_caret_form():
    text = "the state is ^2^P"
    spans = pretokenize(text)
    cas_spans = [s for s in spans if s.kind == KIND_CAS_CANDIDATE]
    assert len(cas_spans) == 1
    assert cas_spans[0].text == "^2^P"


def test_pretokenize_flags_cas_candidate_for_register_form():
    text = "register |f"
    spans = pretokenize(text)
    cas_spans = [s for s in spans if s.kind == KIND_CAS_CANDIDATE]
    assert len(cas_spans) == 1
    assert cas_spans[0].text == "|f"


def test_pretokenize_flags_omega_target():
    text = "target Ω_focus emerges"
    spans = pretokenize(text)
    cas_spans = [s for s in spans if s.kind == KIND_CAS_CANDIDATE]
    assert any("Ω_focus" in s.text for s in cas_spans)


def test_pretokenize_handles_unicode_arrow():
    text = "A → B"
    spans = pretokenize(text)
    assert any(s.kind == KIND_CAS_CANDIDATE and "→" in s.text for s in spans)


def test_pretokenize_emits_whitespace_spans():
    text = "a b"
    spans = pretokenize(text)
    ws_spans = [s for s in spans if s.kind == KIND_WHITESPACE]
    assert len(ws_spans) == 1
    assert ws_spans[0].text == " "


def test_pretokenize_groups_run_of_whitespace():
    text = "a   b"
    spans = pretokenize(text)
    ws_spans = [s for s in spans if s.kind == KIND_WHITESPACE]
    assert len(ws_spans) == 1
    assert ws_spans[0].text == "   "


def test_pretokenize_handles_empty_input():
    assert pretokenize("") == []


def test_pretokenize_makes_progress_on_unrecognized_chars():
    """A leading CAS candidate char with no body must still advance."""
    text = "^"
    spans = pretokenize(text)
    assert reassemble(spans) == text
    assert len(spans) == 1
