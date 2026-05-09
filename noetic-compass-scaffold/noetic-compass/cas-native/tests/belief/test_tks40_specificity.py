"""Tests for legacy TKS 40-element specificity mapping."""

from __future__ import annotations

import pytest

from cas_native.belief.tks40_specificity import (
    TKS40_ELEMENTS,
    compression_hint_for_cas,
    compression_prompt_fragment,
    lookup_cas_state,
    lookup_tks40,
)


def test_table_has_all_40_elements_and_unique_current_states():
    assert len(TKS40_ELEMENTS) == 40
    assert len({element.legacy_code for element in TKS40_ELEMENTS}) == 40
    assert len({element.cas_expression for element in TKS40_ELEMENTS}) == 40


def test_domain_bridge_maps_original_planes_to_current_domains():
    assert lookup_tks40("A1").cas_expression == "^1^P"
    assert lookup_tks40("B1").cas_expression == "^1^C"
    assert lookup_tks40("C1").cas_expression == "^1^E"
    assert lookup_tks40("D1").cas_expression == "^1^O"


def test_legacy_element_10_maps_to_current_idea_noetic_zero():
    assert lookup_tks40("A10").cas_expression == "^0^P"
    assert lookup_tks40("B10").cas_expression == "^0^C"
    assert lookup_tks40("C10").cas_expression == "^0^E"
    assert lookup_tks40("D10").cas_expression == "^0^O"


def test_lookup_cas_state_returns_specificity_hint():
    element = lookup_cas_state("^8^P")
    assert element.legacy_code == "A8"
    assert "inner meaning" in element.compression_hint
    assert "higher moral" in element.compression_hint


def test_compression_hint_for_cas_is_prompt_sized():
    hint = compression_hint_for_cas("^7^O")
    assert "movement" in hint
    assert len(hint) < 120


def test_compression_prompt_fragment_links_both_notations():
    fragment = compression_prompt_fragment("^4^C")
    assert "^4^C" in fragment
    assert "legacy B4" in fragment
    assert "thought resonance" in fragment


def test_unknown_legacy_code_raises_keyerror():
    with pytest.raises(KeyError, match="unknown TKS40"):
        lookup_tks40("Z99")


def test_unknown_cas_state_raises_keyerror():
    with pytest.raises(KeyError, match="unknown mapped CAS state"):
        lookup_cas_state("^9^X")
