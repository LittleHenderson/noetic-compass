"""Tests for the CAS-notation recognizer."""

from __future__ import annotations

from cas_native.tokenizer.cas_notation import (
    KIND_ARROW,
    KIND_COMPOUND_STATE,
    KIND_DOMAIN,
    KIND_DRIVE,
    KIND_NOETIC,
    KIND_OMEGA,
    KIND_RECIPE_OPENER,
    KIND_REGISTER,
    KIND_REGISTER_SET,
    KIND_SET_RELATION,
    find_all_cas_notation,
    match_cas_notation,
)
from cas_native.tokenizer.structured_token import (
    DOMAIN_LABELS,
    REGISTER_LABELS,
)


def test_match_full_compound_state():
    match = match_cas_notation("^2^P_{F4}|f")
    assert match is not None
    assert match.kind == KIND_COMPOUND_STATE
    assert match.matched_text == "^2^P_{F4}|f"
    sig = match.signature
    assert sig.noetic[2] == 1.0
    assert sig.domain[DOMAIN_LABELS.index("P")] == 1.0
    assert sig.drive[3] == 1.0  # F4 is index 3 (one-based 4)
    assert sig.register[REGISTER_LABELS.index("f")] == 1.0


def test_match_noetic_only():
    match = match_cas_notation("^3")
    assert match is not None
    assert match.kind == KIND_COMPOUND_STATE or match.kind == KIND_NOETIC
    # Either the bare-noetic or compound (with no domain etc.) is acceptable
    # as long as the noetic axis fires.
    assert match.signature.noetic[3] == 1.0


def test_match_domain_alone():
    match = match_cas_notation("^P")
    assert match is not None
    assert match.kind == KIND_DOMAIN
    assert match.signature.domain[DOMAIN_LABELS.index("P")] == 1.0


def test_match_drive():
    match = match_cas_notation("F7")
    assert match is not None
    assert match.kind == KIND_DRIVE
    assert match.signature.drive[6] == 1.0  # F7 → index 6


def test_match_register():
    match = match_cas_notation("|A")
    assert match is not None
    assert match.kind == KIND_REGISTER
    assert match.signature.register[REGISTER_LABELS.index("A")] == 1.0


def test_match_register_set_v77():
    match = match_cas_notation("|⟨T,A,f⟩")
    assert match is not None
    assert match.kind == KIND_REGISTER_SET
    sig = match.signature
    assert sig.register[REGISTER_LABELS.index("T")] == 1.0
    assert sig.register[REGISTER_LABELS.index("A")] == 1.0
    assert sig.register[REGISTER_LABELS.index("f")] == 1.0
    assert sig.register[REGISTER_LABELS.index("E")] == 0.0
    assert "register_set" in sig.role_tags


def test_match_omega_target():
    match = match_cas_notation("Ω_attunement")
    assert match is not None
    assert match.kind == KIND_OMEGA
    assert "omega_target" in match.signature.role_tags


def test_match_recipe_opener():
    match = match_cas_notation("Θ(")
    assert match is not None
    assert match.kind == KIND_RECIPE_OPENER
    assert "recipe_opener" in match.signature.role_tags


def test_match_unicode_arrow():
    match = match_cas_notation("→")
    assert match is not None
    assert match.kind == KIND_ARROW


def test_match_set_relation():
    for symbol in ("∈", "⊂", "∪", "∩"):
        match = match_cas_notation(symbol)
        assert match is not None, f"failed to match {symbol!r}"
        assert match.kind == KIND_SET_RELATION
        assert f"set_relation:{symbol}" in match.signature.role_tags


def test_match_returns_none_on_natural_language():
    assert match_cas_notation("hello") is None


def test_match_anchored_at_start_only():
    """Match must anchor at the start position; later matches don't count."""
    text = "abc^2"
    assert match_cas_notation(text, start=0) is None
    assert match_cas_notation(text, start=3) is not None


def test_find_all_cas_notation_recovers_recipe_form():
    text = "Θ(Ω_focus) = 0.40*^3^P_{F2}|A + 0.60*^7^O_{F5}|E → Ω_focus"
    matches = find_all_cas_notation(text)
    kinds = [m.kind for m in matches]
    assert KIND_RECIPE_OPENER in kinds
    assert kinds.count(KIND_OMEGA) >= 2
    assert KIND_ARROW in kinds
    assert kinds.count(KIND_COMPOUND_STATE) >= 2


def test_compound_state_match_is_longest_first():
    """Given '^2^P_{F4}|f' the recognizer must NOT split into '^2' + '^P' + ..."""
    match = match_cas_notation("^2^P_{F4}|f")
    assert match is not None
    assert match.matched_text == "^2^P_{F4}|f"
