"""Tests for the post-generation identifier repair module.

The repair mechanism (cas-native/inference/identifier_repair.py) is the
fast-path fix for the residual content-fidelity gap after the
cas_prefix_mask architectural fix: the model learns operator aliases
and register words via continuous semantic learning, but cannot copy
arbitrary symbolic identifiers verbatim. Repair extracts identifiers
from source CAS and substitutes them positionally into gen English.
"""

from __future__ import annotations

import pytest

from cas_native.inference.identifier_repair import (
    extract_source_identifiers,
    find_omega_slots,
    find_coefficient_slots,
    find_variable_slots,
    repair_identifiers,
    score_identifier_recovery,
)


# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------

def test_extract_omega_names_in_order_with_repeats() -> None:
    cas = "Θ(Ω_decision_60) = 1*^3^P|T + 2*^6^P → Ω_decision_60 + 0.1*Λ·Ω_engagement_side"
    src = extract_source_identifiers(cas)
    assert src.omega_names_in_order == [
        "decision_60", "decision_60", "engagement_side"
    ]
    assert src.omega_unique_in_order == ["decision_60", "engagement_side"]


def test_extract_coefficients_canonicalized() -> None:
    cas = "Θ(Ω_x) = 1.0*^3^P|T + 2*^6^P → Ω_x + 0.10*Λ·Ω_y"
    src = extract_source_identifiers(cas)
    # 1.0 -> "1", 2 stays "2", 0.10 -> "0.1"
    assert src.coefficients_in_order == ["1", "2", "0.1"]


def test_extract_variable_names_in_order() -> None:
    cas = (
        "let stageA0_3_0234 = ^0^P; "
        "let stageD3_3_0234 = ^9^P_{F3}; "
        "stageA0_3_0234 -> stageD3_3_0234"
    )
    src = extract_source_identifiers(cas)
    assert src.variable_names_in_order == ["stageA0_3_0234", "stageD3_3_0234"]


def test_extract_handles_omega_ascii_form() -> None:
    cas = "Theta(Omega_judgment) = 1*^1^E|E + 2*^1^E|f -> Omega_judgment"
    src = extract_source_identifiers(cas)
    assert src.omega_unique_in_order == ["judgment"]


# ---------------------------------------------------------------------------
# Output-side slot detection
# ---------------------------------------------------------------------------

def test_find_omega_slots_in_recipe_english() -> None:
    text = (
        "To produce the outcome called rehearsal_67, combine 1 of breaking "
        "down with 2 of paying attention. Together these inputs yield the "
        "named outcome rehearsal_67."
    )
    slots = find_omega_slots(text)
    assert len(slots) == 2
    assert slots[0].text == "rehearsal_67"
    assert slots[1].text == "rehearsal_67"


def test_find_coefficient_slots_basic() -> None:
    text = "combine 1 of breaking down an idea with 0.7 of something that just clicked"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["1", "0.7"]


def test_find_coefficient_slots_excludes_in_word_numbers() -> None:
    text = "outcome called rehearsal_67, combine 1.5 of something"
    slots = find_coefficient_slots(text)
    # 67 inside rehearsal_67 must NOT be picked up — it's not "X of"
    assert [s.text for s in slots] == ["1.5"]


def test_find_coefficient_slots_unit_form() -> None:
    text = "combine 1 unit of something that just clicked"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["1"]


def test_find_coefficient_slots_units_plural_form() -> None:
    text = "combine 2 units of breaking down"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["2"]


def test_find_coefficient_slots_times_form() -> None:
    text = "add 1.5 times something that struck a chord"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["1.5"]


def test_find_coefficient_slots_part_form() -> None:
    text = "with 0.5 part of a side effect"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["0.5"]


def test_find_coefficient_slots_contribution_form() -> None:
    """v1 PREFIX128 5ep emitted 'a 0.7 contribution from ...' — observed
    surface form for side products / additional terms."""
    text = "and a 0.7 contribution from something that just clicked"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["0.7"]


def test_find_coefficient_slots_contribution_of_form() -> None:
    text = "with 0.1 contribution of a side effect"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["0.1"]


def test_find_coefficient_slots_mixed_qualifiers() -> None:
    """A single recipe gen often mixes qualifier forms across slots."""
    text = (
        "To produce X, combine 1 unit of A with 1.5 times B, "
        "and add 0.1 of side effect."
    )
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["1", "1.5", "0.1"]


def test_find_coefficient_slots_does_not_match_decimals_inside_numbers() -> None:
    """Pre-bug regression: '1' inside '1.2' must not appear as a slot."""
    text = "combine 1.2 of something"
    slots = find_coefficient_slots(text)
    assert [s.text for s in slots] == ["1.2"]


def test_find_variable_slots_basic() -> None:
    text = (
        "Let stageA0_3_0234 name a foundational thought, "
        "stageD3_3_0234 name something that popped into mind"
    )
    slots = find_variable_slots(text)
    names = [s.text for s in slots]
    assert "stageA0_3_0234" in names
    assert "stageD3_3_0234" in names


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------

def test_repair_omega_in_recipe() -> None:
    cas = "Θ(Ω_decision_60) = 1*^3^P|T → Ω_decision_60 + 0.1*Λ·Ω_engagement_side"
    gen = (
        "To produce the outcome called rehearsal_67, take 1 of something that "
        "rubs you the wrong way, with an additional 0.1 of an effect feeding "
        "into outcome called engagement_72."
    )
    repaired, log = repair_identifiers(source_cas=cas, english=gen)
    assert "decision_60" in repaired
    assert "engagement_side" in repaired
    assert "rehearsal_67" not in repaired
    assert "engagement_72" not in repaired
    assert ("rehearsal_67", "decision_60") in log.omega_substitutions
    assert ("engagement_72", "engagement_side") in log.omega_substitutions


def test_repair_coefficients_when_wrong() -> None:
    cas = "Θ(Ω_x) = 1.5*^3^P + 2*^6^P → Ω_x + 0.1*Λ·Ω_y"
    gen = (
        "To produce the outcome called x, combine 0.5 of something with "
        "1.2 of something else, with an extra 0.05 of side effect feeding "
        "into outcome called y."
    )
    repaired, log = repair_identifiers(source_cas=cas, english=gen)
    # First gen coef 0.5 -> source 1.5; second 1.2 -> 2; third 0.05 -> 0.1
    assert "1.5 of" in repaired
    assert "2 of" in repaired
    assert "0.1 of" in repaired
    assert ("0.5", "1.5") in log.coefficient_substitutions
    assert ("1.2", "2") in log.coefficient_substitutions


def test_repair_no_op_when_identifiers_already_correct() -> None:
    cas = "Θ(Ω_alignment) = 1*^4^P|A → Ω_alignment"
    gen = "To produce the outcome called alignment, combine 1 of struck a chord."
    repaired, log = repair_identifiers(source_cas=cas, english=gen)
    assert repaired == gen
    assert log.total == 0


def test_repair_does_not_invent_slots() -> None:
    """If gen has fewer Ω slots than source, repair must not invent new
    slots. It only substitutes within existing slots."""
    cas = "Θ(Ω_main) = 1*^3 → Ω_main + 0.1*Λ·Ω_side"
    gen = "To produce the outcome called wrong_name, combine 1 of something."
    # Gen has 1 Ω slot, source has 2 unique Ω names. Only the first
    # (wrong_name -> main) is repaired. "side" is not inserted.
    repaired, log = repair_identifiers(source_cas=cas, english=gen)
    assert "main" in repaired
    assert "side" not in repaired
    assert len(log.omega_substitutions) == 1


def test_repair_handles_let_variable_names() -> None:
    cas = "let vsrc_0460 = ^2^P; let vtgt_0460 = ^8^O; vsrc_0460 -> vtgt_0460"
    gen = (
        'Let "var_a" name something you are drawn toward in a principled realm. '
        'Let "var_b" name a named outcome.'
    )
    repaired, log = repair_identifiers(source_cas=cas, english=gen)
    assert "vsrc_0460" in repaired
    assert "vtgt_0460" in repaired
    assert "var_a" not in repaired
    assert "var_b" not in repaired


# ---------------------------------------------------------------------------
# Identifier recovery scoring
# ---------------------------------------------------------------------------

def test_recovery_score_full_recovery_after_repair() -> None:
    cas = "Θ(Ω_decision_60) = 1*^3^P|T + 2*^6^P → Ω_decision_60 + 0.1*Λ·Ω_engagement_side"
    pre_gen = (
        "To produce the outcome called rehearsal_67, combine 0.5 of stuff "
        "with 1.2 of more, plus 0.05 of a side effect feeding into outcome "
        "called engagement_72."
    )
    pre_score = score_identifier_recovery(source_cas=cas, english=pre_gen)
    assert pre_score.omega_recovered == 0
    assert pre_score.omega_total == 2
    assert pre_score.coefficient_recovered == 0
    assert pre_score.coefficient_total == 3

    repaired, _ = repair_identifiers(source_cas=cas, english=pre_gen)
    post_score = score_identifier_recovery(source_cas=cas, english=repaired)
    assert post_score.omega_rate == 1.0
    assert post_score.coefficient_rate == 1.0


def test_recovery_score_canonical_coefficient_match() -> None:
    """A source coef of "1" should match either "1" or "1.0" in gen."""
    cas = "Θ(Ω_x) = 1*^3^P → Ω_x"
    gen = "To produce the outcome called x, combine 1.0 of something."
    score = score_identifier_recovery(source_cas=cas, english=gen)
    assert score.coefficient_recovered == 1
    assert score.coefficient_total == 1


def test_recovery_score_handles_state_literal_only() -> None:
    """Records with no Ω/coef/variable identifiers should score as
    fully recovered (totals are 0, rates default to 1.0)."""
    cas = "^7^C_{F2}|T"
    gen = "Practice and muscle memory in cognitive thinking."
    score = score_identifier_recovery(source_cas=cas, english=gen)
    assert score.omega_total == 0
    assert score.coefficient_total == 0
    assert score.variable_total == 0
    assert score.omega_rate == 1.0


# ---------------------------------------------------------------------------
# Integration: end-to-end on a real-shape recipe
# ---------------------------------------------------------------------------

def test_end_to_end_recipe_repair_v1_prefix128_5ep_record4() -> None:
    """Reproduce the EXACT v1 PREFIX128 5ep record 4 failure where the
    model produced 'combine 1 unit of ... and add 1.5 times ...' but
    the original slot detector only knew 'X of'. After broadening the
    qualifier patterns, repair should fire on all three coefficient
    slots."""
    source = (
        "Θ(Ω_decision_60) = 1*^3^P|T + 2*^6^P → Ω_decision_60 "
        "+ 0.1*Λ·Ω_engagement_side"
    )
    bad_gen = (
        "To produce the outcome called remembering_68, combine 1 unit of "
        "something that just clicked in operational thinking expressed in "
        "a transcendent way, and add 1.5 times something that struck a "
        "chord in a foundational way, with 0.7 of a side effect."
    )
    repaired, log = repair_identifiers(source_cas=source, english=bad_gen)
    # Ω: remembering_68 -> decision_60
    assert "decision_60" in repaired
    assert "remembering_68" not in repaired
    # Coef slot 1: "1" matches source "1" — no change.
    # Coef slot 2: "1.5" -> source "2".
    # Coef slot 3: "0.7" -> source "0.1".
    assert "2 times" in repaired
    assert "0.1 of" in repaired
    assert "1.5 times" not in repaired
    assert "0.7 of" not in repaired
    assert ("1.5", "2") in log.coefficient_substitutions
    assert ("0.7", "0.1") in log.coefficient_substitutions


def test_end_to_end_recipe_repair_matches_target() -> None:
    """Reproduce the v1 PREFIX128 5ep record 4 failure pattern: model
    produces a recipe-shape output with hallucinated Ω + coefs. Repair
    should restore the source identifiers."""
    source = "Θ(Ω_decision_60) = 1*^3^P|T + 2*^6^P → Ω_decision_60 + 0.1*Λ·Ω_engagement_side"
    bad_gen = (
        "To produce the outcome called rehearsal_67, combine 1 of breaking "
        "down an idea in operational behavior with 0.7 of something that just "
        "clicked in a foundational way, expressed in an embodied way."
    )
    repaired, log = repair_identifiers(source_cas=source, english=bad_gen)
    # Ω repair: rehearsal_67 -> decision_60 (engagement_side missing in gen,
    # so it's not inserted — repair never invents slots)
    assert "decision_60" in repaired
    assert "rehearsal_67" not in repaired
    # Coefficient repair: gen had "1" and "0.7"; source has "1", "2", "0.1".
    # Slot 1: "1" matches source "1" — no change.
    # Slot 2: "0.7" -> source "2".
    # Source "0.1" not inserted (only 2 gen slots).
    assert "2 of" in repaired
    assert "0.7 of" not in repaired
    # Operator-alias mismatches ("breaking down an idea" wrong, etc.) are
    # NOT touched — repair scope is symbolic identifiers only.
    assert "breaking down an idea" in repaired
