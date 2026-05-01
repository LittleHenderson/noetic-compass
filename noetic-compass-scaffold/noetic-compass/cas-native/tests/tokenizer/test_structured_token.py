"""Schema tests for ``StructuredToken`` and ``CASSignature``."""

from __future__ import annotations

import pytest

from cas_native.tokenizer.structured_token import (
    DOMAIN_AXIS_LEN,
    DRIVE_AXIS_LEN,
    NOETIC_AXIS_LEN,
    REGISTER_AXIS_LEN,
    SCHEMA_VERSION,
    CASSignature,
    StructuredToken,
    TokenSource,
)


def _ones(n: int) -> tuple[float, ...]:
    return tuple(1.0 for _ in range(n))


def test_neutral_signature_is_neutral():
    sig = CASSignature.neutral()
    assert sig.is_neutral()
    assert sig.validate() == []


def test_signature_axis_lengths_are_canonical():
    sig = CASSignature.neutral()
    assert len(sig.noetic) == NOETIC_AXIS_LEN == 10
    assert len(sig.domain) == DOMAIN_AXIS_LEN == 4
    assert len(sig.drive) == DRIVE_AXIS_LEN == 7
    assert len(sig.register) == REGISTER_AXIS_LEN == 4


def test_signature_validate_flags_axis_length_mismatch():
    sig = CASSignature(noetic=(0.0, 0.0))  # too short
    errors = sig.validate()
    assert any("noetic axis must be length 10" in e for e in errors)


def test_signature_validate_flags_out_of_range_value():
    bad_noetic = (0.0,) * 9 + (1.5,)  # 1.5 > 1.0
    sig = CASSignature(noetic=bad_noetic)
    errors = sig.validate()
    assert any("outside [-1.0, +1.0]" in e for e in errors)


def test_signature_negative_drive_value_is_legal():
    """Negative drive values represent depletion (e.g., 'tired' depletes F3)."""
    sig = CASSignature(drive=(0.0, 0.0, -0.7, 0.0, 0.0, 0.0, 0.0))
    assert sig.validate() == []


def test_signature_round_trip_via_dict():
    sig = CASSignature(
        noetic=(0.0,) * 2 + (0.85,) + (0.0,) * 7,  # ^2 affinity 0.85
        register=(0.0, 0.5, 0.0, 0.0),  # |A 0.5
        role_tags=("affinity_marker",),
    )
    payload = sig.to_dict()
    restored = CASSignature.from_dict(payload)
    assert restored == sig


def test_token_validate_accepts_well_formed_token():
    token = StructuredToken(
        surface_text="drawn",
        surface_span=(0, 5),
        cas_signature=CASSignature.neutral(),
        confidence=0.7,
        source=TokenSource.LEXICON,
    )
    assert token.validate() == []


def test_token_validate_flags_inverted_span():
    token = StructuredToken(
        surface_text="oops",
        surface_span=(5, 2),  # end < start
        cas_signature=CASSignature.neutral(),
    )
    errors = token.validate()
    assert any("surface_span invalid" in e for e in errors)


def test_token_validate_flags_confidence_out_of_range():
    token = StructuredToken(
        surface_text="x",
        surface_span=(0, 1),
        cas_signature=CASSignature.neutral(),
        confidence=1.5,
    )
    errors = token.validate()
    assert any("confidence=1.5" in e for e in errors)


def test_token_round_trip_preserves_all_fields():
    token = StructuredToken(
        surface_text="resonates",
        surface_span=(10, 19),
        cas_signature=CASSignature(
            noetic=(0.0,) * 4 + (0.9,) + (0.0,) * 5,
            role_tags=("resonance_marker",),
        ),
        confidence=0.9,
        source=TokenSource.LEXICON,
        vocab_id=42,
    )
    payload = token.to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["surface_span"] == [10, 19]
    restored = StructuredToken.from_dict(payload)
    assert restored == token


def test_token_source_enum_values_are_stable():
    assert TokenSource.LEXICON.value == "lexicon"
    assert TokenSource.LEARNED.value == "learned"
    assert TokenSource.CAS_NOTATION.value == "cas_notation"
    assert TokenSource.FALLBACK.value == "fallback"


def test_signature_with_role_tags_is_not_neutral():
    sig = CASSignature(role_tags=("confidence_hedge",))
    assert not sig.is_neutral()
