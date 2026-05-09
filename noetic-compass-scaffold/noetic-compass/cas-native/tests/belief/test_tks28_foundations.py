"""Tests for legacy TKS 28 Foundations specificity mapping."""

from __future__ import annotations

import pytest

from cas_native.belief.tks28_foundations import (
    TKS28_FOUNDATIONS,
    foundation_hint_for_drive_register,
    foundation_prompt_fragment,
    lookup_drive_register,
    lookup_tks28,
)


def test_table_has_all_28_foundations_and_unique_drive_registers():
    assert len(TKS28_FOUNDATIONS) == 28
    assert len({entry.legacy_code for entry in TKS28_FOUNDATIONS}) == 28
    assert len({entry.cas_expression for entry in TKS28_FOUNDATIONS}) == 28


def test_world_bridge_maps_to_current_register_axis():
    assert lookup_tks28("1a").cas_expression == "F1|T"
    assert lookup_tks28("1b").cas_expression == "F1|A"
    assert lookup_tks28("1c").cas_expression == "F1|f"
    assert lookup_tks28("1d").cas_expression == "F1|E"


def test_foundation_positions_map_to_current_drives():
    assert lookup_tks28("2b").cas_expression == "F2|A"
    assert lookup_tks28("3d").cas_expression == "F3|E"
    assert lookup_tks28("4c").cas_expression == "F4|f"
    assert lookup_tks28("7a").cas_expression == "F7|T"


def test_lookup_drive_register_returns_specific_hint():
    entry = lookup_drive_register("F5|A")
    assert entry.legacy_code == "5b"
    assert "strategic thinking" in entry.compression_hint
    assert "ethical use" in entry.compression_hint


def test_foundation_hint_for_drive_register_is_prompt_sized():
    hint = foundation_hint_for_drive_register("F7|E")
    assert "procreation" in hint
    assert len(hint) < 120


def test_foundation_prompt_fragment_links_both_notations():
    fragment = foundation_prompt_fragment("F4|f")
    assert "F4|f" in fragment
    assert "legacy 4c" in fragment
    assert "emotional bonding" in fragment


def test_lookup_tks28_is_case_insensitive_for_legacy_codes():
    assert lookup_tks28("2B").cas_expression == "F2|A"


def test_unknown_legacy_code_raises_keyerror():
    with pytest.raises(KeyError, match="unknown TKS28"):
        lookup_tks28("9z")


def test_unknown_drive_register_raises_keyerror():
    with pytest.raises(KeyError, match="unknown mapped drive-register"):
        lookup_drive_register("F9|Q")
