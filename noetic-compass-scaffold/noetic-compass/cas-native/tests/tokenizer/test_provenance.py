"""Tests for the per-eval token-source provenance helper."""

from __future__ import annotations

import pytest

from cas_native.tokenizer import (
    SIGNAL_BEARING_LABELS,
    SOURCE_LABELS,
    TokenSource,
    summarize_token_provenance,
    tokenize,
)
from cas_native.tokenizer.structured_token import CASSignature, StructuredToken


def _token(surface: str, source: TokenSource, span_start: int = 0) -> StructuredToken:
    return StructuredToken(
        surface_text=surface,
        surface_span=(span_start, span_start + len(surface)),
        cas_signature=CASSignature.neutral(),
        confidence=0.0 if source == TokenSource.FALLBACK else 0.9,
        source=source,
    )


def test_summary_returns_canonical_shape():
    summary = summarize_token_provenance([])

    assert summary["n_records"] == 0
    assert summary["total_tokens"] == 0
    assert summary["total_signal_bearing"] == 0
    assert summary["overall_signal_fraction"] == 0.0
    assert set(summary["by_source"].keys()) == set(SOURCE_LABELS)
    assert summary["by_bucket"] == {}


def test_signal_fraction_counts_lexicon_and_cas_notation_only():
    sequence = [
        _token("drawn to", TokenSource.LEXICON),
        _token("^2^P_{F4}|f", TokenSource.CAS_NOTATION, span_start=10),
        _token("xyzzy", TokenSource.FALLBACK, span_start=22),
        _token("foo", TokenSource.FALLBACK, span_start=28),
    ]
    summary = summarize_token_provenance([sequence])

    assert summary["total_tokens"] == 4
    assert summary["total_signal_bearing"] == 2
    assert summary["overall_signal_fraction"] == 0.5
    assert summary["by_source"]["LEXICON"] == 1
    assert summary["by_source"]["CAS_NOTATION"] == 1
    assert summary["by_source"]["FALLBACK"] == 2
    assert summary["by_source_fraction"]["LEXICON"] == 0.25
    assert summary["by_source_fraction"]["FALLBACK"] == 0.5


def test_signal_bearing_label_set_matches_helper_logic():
    """Drift guard: only LEXICON and CAS_NOTATION carry per-token cas_signature."""

    assert SIGNAL_BEARING_LABELS == frozenset({"LEXICON", "CAS_NOTATION"})


def test_per_bucket_grouping_uses_record_bucket_field():
    seq_a = [_token("audit", TokenSource.LEXICON)]
    seq_b = [
        _token("xx", TokenSource.FALLBACK),
        _token("yy", TokenSource.FALLBACK, span_start=3),
    ]
    records = [{"bucket": "v74_baseline"}, {"bucket": "v77_omega"}]
    summary = summarize_token_provenance([seq_a, seq_b], records=records)

    assert set(summary["by_bucket"].keys()) == {"v74_baseline", "v77_omega"}
    assert summary["by_bucket"]["v74_baseline"]["n_records"] == 1
    assert summary["by_bucket"]["v74_baseline"]["total_tokens"] == 1
    assert summary["by_bucket"]["v74_baseline"]["signal_fraction"] == 1.0
    assert summary["by_bucket"]["v77_omega"]["n_records"] == 1
    assert summary["by_bucket"]["v77_omega"]["total_tokens"] == 2
    assert summary["by_bucket"]["v77_omega"]["signal_fraction"] == 0.0


def test_records_without_bucket_field_group_under_unknown():
    seq = [_token("a", TokenSource.FALLBACK)]
    summary = summarize_token_provenance([seq], records=[{}])
    assert "unknown" in summary["by_bucket"]


def test_no_records_groups_all_under_unknown():
    seq = [_token("a", TokenSource.FALLBACK)]
    summary = summarize_token_provenance([seq])
    assert "unknown" in summary["by_bucket"]
    assert summary["by_bucket"]["unknown"]["n_records"] == 1


def test_records_length_mismatch_raises():
    with pytest.raises(ValueError, match="length"):
        summarize_token_provenance(
            [[_token("a", TokenSource.FALLBACK)]], records=[{}, {}]
        )


def test_real_tokenize_pipeline_produces_signal_bearing_lexicon_token():
    """End-to-end: a known lexicon hit raises the signal fraction above zero."""

    sequences = [tokenize("I feel drawn to this idea")]
    summary = summarize_token_provenance(sequences)

    assert summary["overall_signal_fraction"] > 0.0
    assert summary["by_source"]["LEXICON"] >= 1


def test_real_tokenize_pipeline_cas_notation_counts():
    sequences = [tokenize("the state ^2^P_{F4}|f matters")]
    summary = summarize_token_provenance(sequences)

    assert summary["by_source"]["CAS_NOTATION"] >= 1
