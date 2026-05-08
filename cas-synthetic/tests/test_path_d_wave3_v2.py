"""Unit tests for the Path D Wave 3 v2 prompt builders + validators.

Five test groups:

1. **v2 prompt builders** — recipe + fractal preservation guidance is added
   when the seed surface form requires it; absent otherwise.
2. **english_to_cas v2** — prompt does NOT contain the source CAS, only the
   pre-generated English description.
3. **invalid_to_corrected repair vs narration** — repair prompt asks for the
   smallest possible edit with worked good/bad examples; narration prompt
   references the actual minimal change.
4. **Validators** — recipe coefficient + Ω preservation, fractal k-indices,
   anti-copy guard, Jaccard guard. Each exercised on a hand-built positive
   AND a hand-built negative case.
5. **Wave 2.5 iterate** — accept_writer fires on validator pass,
   reject_writer fires on validator fail, counts aggregate correctly.

No API calls. No paid resources used.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_path_d_wave3_v2.py"
)


def _load_module():
    name = "path_d_wave3_v2_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Group 1: v2 prompt builders — conditional recipe / fractal guidance
# ---------------------------------------------------------------------------


def test_cas_to_english_v2_includes_recipe_guidance_for_recipe_seed():
    m = _load_module()
    seed = {
        "expression": "Θ(Ω_decision_47) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_decision_47",
        "grammar_category": "recipe",
    }
    sys_p, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "RECIPE-SPECIFIC RULES" in user_p
    assert "MUST appear in your English output as a" in user_p
    assert "DO NOT confuse ^3 and ^6" in user_p
    assert "Ω_decision_47" not in sys_p  # source not leaked into system msg


def test_cas_to_english_v2_includes_fractal_guidance_for_fractal_seed():
    m = _load_module()
    seed = {
        "expression": "Φ⟨9:4:7⟩",
        "grammar_category": "fractal_sequence",
    }
    sys_p, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "FRACTAL-SPECIFIC RULES" in user_p
    assert "OPERATOR INDEX" in user_p
    assert "DO NOT say '9 domains'" in user_p


def test_cas_to_english_v2_omits_recipe_guidance_for_state_literal():
    m = _load_module()
    seed = {
        "expression": "^3^P|A",
        "grammar_category": "state_literal",
    }
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "RECIPE-SPECIFIC RULES" not in user_p
    assert "FRACTAL-SPECIFIC RULES" not in user_p


def test_cas_to_english_v2_includes_colloquialisms():
    m = _load_module()
    seed = {
        "expression": "^3^P|A",
        "grammar_category": "state_literal",
    }
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "Approved everyday English phrasings" in user_p
    assert "rubs the wrong way" in user_p


# Group 1b: NO-NOTATION block + per-slot guidance wiring (added 2026-05-08
# after the paid preflight found the model leaking CAS notation in 8 of 10
# cas_to_english categories. The earlier "do not echo notation" line was
# too soft. The new block names every forbidden token AND its plain-English
# replacement, and per-slot guidance gives a worked example per category.)


def test_cas_to_english_v2_includes_no_notation_block_for_every_category():
    m = _load_module()
    for cat in (
        "state_literal",
        "binary_composition",
        "cross_register_omega",
        "rpm_chain",
        "let_binding",
        "inversion",
        "diagram_export",
        "recipe",
        "fractal_sequence",
        "meta_logic_relation",
    ):
        seed = {"expression": "placeholder", "grammar_category": cat}
        _, user_p = m.build_cas_to_english_prompt_v2(seed)
        assert "NO-NOTATION RULE" in user_p, f"missing NO-NOTATION for {cat}"
        assert "FORBIDDEN — Ω" in user_p, f"missing Ω forbidden for {cat}"
        assert "FORBIDDEN — drive labels F1 F2" in user_p
        assert "FORBIDDEN — domain letters as labels" in user_p
        assert "FORBIDDEN — register labels T A f E" in user_p
        # Replacement table must be present so the model has a concrete map.
        assert "F7 → purpose" in user_p
        assert "C → cognitive" in user_p
        assert "T → transcendent" in user_p


def test_cas_to_english_v2_state_literal_guidance_wired():
    m = _load_module()
    seed = {"expression": "^7^E_{F3}|A", "grammar_category": "state_literal"}
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "STATE-LITERAL RULES" in user_p
    assert "BINARY-COMPOSITION RULES" not in user_p
    assert "CROSS-REGISTER OMEGA RULES" not in user_p


def test_cas_to_english_v2_binary_composition_guidance_wired():
    m = _load_module()
    seed = {"expression": "^3^O + ^7^P", "grammar_category": "binary_composition"}
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "BINARY-COMPOSITION RULES" in user_p
    assert "operator index 2" in user_p
    assert "STATE-LITERAL RULES" not in user_p


def test_cas_to_english_v2_cross_register_omega_guidance_wired():
    m = _load_module()
    seed = {
        "expression": "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_alignment",
        "grammar_category": "cross_register_omega",
    }
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "CROSS-REGISTER OMEGA RULES" in user_p
    # The worked example shows stem-only rendering, never Ω_ prefix.
    assert "the outcome called alignment" in user_p
    assert "two or three same-Noetic" in user_p
    assert "Do not invent a third mode" in user_p
    assert "|E means embodied" in user_p
    assert "Exact-register checklist" in user_p
    assert "must be embodied + felt" in user_p


def test_cas_to_english_v2_rpm_chain_guidance_wired():
    m = _load_module()
    seed = {
        "expression": "^0^P → ^1^C → ^2^E → ^7^O",
        "grammar_category": "rpm_chain",
    }
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "RPM-CHAIN RULES" in user_p


def test_cas_to_english_v2_let_binding_guidance_wired():
    m = _load_module()
    seed = {
        "expression": "let anchor_03 = ^1^P_{F2}|T",
        "grammar_category": "let_binding",
    }
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "LET-BINDING RULES" in user_p


def test_cas_to_english_v2_inversion_guidance_wired():
    m = _load_module()
    seed = {"expression": "^3^P_{F1}", "grammar_category": "inversion"}
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "INVERSION RULES" in user_p


def test_cas_to_english_v2_diagram_export_guidance_wired():
    m = _load_module()
    seed = {
        "expression": "NoeticCluster{^1, ^3, ^4}",
        "grammar_category": "diagram_export",
    }
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    assert "DIAGRAM-EXPORT RULES" in user_p
    assert "export let upsilon_0206" in user_p


def test_cas_to_english_v2_per_slot_guidance_is_mutually_exclusive():
    """Each category should receive at most one slot-specific guidance
    block (recipe / fractal can also fire shape-based, which is fine, but
    the new categories are category-only matched and should not collide
    with each other)."""
    m = _load_module()
    new_blocks = [
        "STATE-LITERAL RULES",
        "BINARY-COMPOSITION RULES",
        "CROSS-REGISTER OMEGA RULES",
        "RPM-CHAIN RULES",
        "LET-BINDING RULES",
        "INVERSION RULES",
        "DIAGRAM-EXPORT RULES",
    ]
    seed = {"expression": "^3^P|A", "grammar_category": "state_literal"}
    _, user_p = m.build_cas_to_english_prompt_v2(seed)
    fires = [b for b in new_blocks if b in user_p]
    assert fires == ["STATE-LITERAL RULES"]


# ---------------------------------------------------------------------------
# Group 2: english_to_cas v2 — no source CAS in prompt
# ---------------------------------------------------------------------------


def test_english_to_cas_v2_does_not_embed_source_cas():
    m = _load_module()
    sys_p, user_p = m.build_english_to_cas_prompt_v2(
        "A thought drawn toward foundations.",
        grammar_category="binary_composition",
    )
    # The source CAS is NOT supplied to this prompt — only the English
    # description.
    assert "^0^P|A" not in user_p
    assert "reference target" not in user_p.lower()
    assert "A thought drawn toward foundations." in user_p


def test_english_to_cas_v2_retry_includes_prior_error():
    m = _load_module()
    sys_p, user_p = m.build_english_to_cas_prompt_v2(
        "A pull toward an evaluative judgment.",
        grammar_category="state_literal",
        prior_attempt="^2^E|garbage",
        prior_error="parsing@8: bad register",
    )
    assert "previous attempt" in user_p
    assert "^2^E|garbage" in user_p
    assert "parsing@8: bad register" in user_p


# ---------------------------------------------------------------------------
# Group 3: invalid_to_corrected repair vs narration
# ---------------------------------------------------------------------------


def test_invalid_to_corrected_repair_prompt_demands_minimal_edit():
    m = _load_module()
    inv = {
        "expression": "^13^E|f + ^1^E|E",
        "compiler_error_message": "typecheck: operator index must be 0-9, got 13",
        "error_class": "admissibility",
    }
    sys_p, user_p = m.build_invalid_to_corrected_repair_prompt_v2(inv)
    assert "SMALLEST POSSIBLE EDIT" in sys_p
    assert "GOOD EXAMPLE" in user_p
    assert "BAD EXAMPLE" in user_p
    assert "^13^E|f + ^1^E|E" in user_p


def test_invalid_to_corrected_narration_references_specific_change():
    m = _load_module()
    inv = {
        "expression": "^13^E|f + ^1^E|E",
        "compiler_error_message": "typecheck: operator index must be 0-9, got 13",
        "error_class": "admissibility",
    }
    sys_p, user_p = m.build_invalid_to_corrected_narration_prompt_v2(
        inv, corrected_expression="^1^E|f + ^1^E|E"
    )
    # The narration prompt must reject the generic phrasing the audit
    # flagged.
    assert "Be specific" in user_p
    assert "DO NOT use generic language" in user_p
    assert "^1^E|f + ^1^E|E" in user_p


# ---------------------------------------------------------------------------
# Group 4: validators
# ---------------------------------------------------------------------------


def test_recipe_preservation_pass_with_coefficients_and_omega_stem():
    m = _load_module()
    r = m.validate_cas_to_english_recipe_preservation(
        source_cas="Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02",
        english_output=(
            "When 1.5 of unpacking in evaluative judgment combines with "
            "1.5 of unpacking principled foundations, the production "
            "yields the outcome called reasoning_02."
        ),
    )
    assert r.passed
    assert "1.5" in r.detail["coefficients_found"]
    assert "reasoning_02" in r.detail["omega_stems_found"]


def test_recipe_preservation_fail_when_coefficients_dropped():
    m = _load_module()
    r = m.validate_cas_to_english_recipe_preservation(
        source_cas="Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02",
        english_output=(
            "Breaking down evaluative judgment combines with breaking "
            "down principled foundations to produce reasoning_02."
        ),
    )
    assert not r.passed
    assert "missing coefficients" in (r.reason or "")


def test_recipe_preservation_fail_when_omega_stem_dropped():
    m = _load_module()
    r = m.validate_cas_to_english_recipe_preservation(
        source_cas="Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47",
        english_output=(
            "When 0.7 of analytical thought-emergence combines, the "
            "production yields a named decision target."
        ),
    )
    assert not r.passed
    # The stem 'decision_47' is missing from English; reason should
    # surface that.
    assert "decision_47" in (r.reason or "")


def test_recipe_preservation_fail_when_omega_prefix_leaks():
    """Anti-leak: echoing 'Ω_<stem>' in English is CAS notation leakage."""
    m = _load_module()
    r = m.validate_cas_to_english_recipe_preservation(
        source_cas="Θ(Ω_reasoning_02) = 1.5*^6^E → Ω_reasoning_02",
        english_output=(
            "1.5 of evaluative unpacking produces Ω_reasoning_02."
        ),
    )
    assert not r.passed
    assert "Ω_" in (r.reason or "")


def test_recipe_preservation_pass_with_quoted_stem_phrase():
    """Stem may surface inside a quoting / naming phrase."""
    m = _load_module()
    r = m.validate_cas_to_english_recipe_preservation(
        source_cas="Θ(Ω_reasoning_50) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_reasoning_50",
        english_output=(
            "When reasoning weighs 0.7 of analytical thought-emergence "
            "and 1.5 of analytical attention to a foundational principle, "
            "that produces \"the outcome called reasoning_50\"."
        ),
    )
    assert r.passed


def test_recipe_preservation_skip_for_non_recipe():
    m = _load_module()
    r = m.validate_cas_to_english_recipe_preservation(
        source_cas="^3^P|A + ^4^E|f",
        english_output="Aversion to a foundational principle plus an "
        "evaluative resonance.",
    )
    assert r.passed
    assert "skipped" in (r.reason or "").lower()


# ---------------------------------------------------------------------------
# Per-occurrence operator-alias check (Wave 2.5 catch-3 closure 2026-05-08)
# ---------------------------------------------------------------------------


def test_recipe_per_occurrence_pass_clean_recipe():
    """Pass case — every operand's alias surfaces near its coefficient."""
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas="Θ(Ω_decision_47) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_decision_47",
        english_output=(
            "To produce the outcome called decision_47, take 0.7 of "
            "a thought that popped into mind in cognitive thinking "
            "expressed in an analytical way, plus 1.5 of paying "
            "attention to a foundational principle expressed in an "
            "analytical way."
        ),
    )
    assert r.passed, r.reason


def test_recipe_per_occurrence_fail_noetic_3_to_5_swap():
    """Fail case — ^3^C_{F5} mis-rendered as ^5 alias (who-you-are).

    Mirrors seed_recipe_00407, the original target bug.
    """
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas=(
            "Θ(Ω_judgment_07) = 0.7*^7^O + 1.5*^5^C_{F4} + 2*^3^C_{F5} "
            "→ Ω_judgment_07"
        ),
        english_output=(
            "To produce the outcome called judgment_07, combine 0.7 of "
            "practice-makes-perfect operational behavior, plus 1.5 of "
            "who-you-are cognitive thinking shaped by the need for "
            "connection, plus 2 of who-you-are cognitive thinking "
            "shaped by the need for self-determination."
        ),
    )
    assert not r.passed
    assert "operator_misrender_at_coeff_2" in (r.reason or "")
    assert "^3" in (r.reason or "")


def test_recipe_per_occurrence_fail_noetic_2_to_6_swap():
    """Fail case — ^2^C_{F3}|A mis-rendered as ^6 alias (breaking down).

    Mirrors seed_recipe_00061.
    """
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas=(
            "Θ(Ω_withdrawal_61) = 0.7*^9^E + 2*^2^C_{F3}|A → Ω_withdrawal_61"
        ),
        english_output=(
            "Take 0.7 of something that popped into mind in evaluative "
            "judging, and add 2 of breaking down a thought about "
            "vitality and energy expressed in an analytical way — "
            "together these produce the outcome called withdrawal_61."
        ),
    )
    assert not r.passed
    assert "operator_misrender_at_coeff_2" in (r.reason or "")


def test_recipe_per_occurrence_fail_register_E_to_A_swap():
    """Fail case — |E source rendered with conflicting |A alias.

    Mirrors seed_recipe_00165.
    """
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas=(
            "Θ(Ω_rehearsal_65) = 2*^1^P_{F1}|E + 0.5*^0^C_{F2} → Ω_rehearsal_65"
        ),
        english_output=(
            "To produce the outcome called rehearsal_65, combine 2 of "
            "paying attention to a need for cohesion in foundational "
            "thinking, expressed in an analytical way, plus 0.5 of a "
            "thought about a need for insight in cognitive thinking, "
            "expressed in an analytical way."
        ),
    )
    assert not r.passed
    # Conflict-based register check should report |E source missing AND
    # conflicting |A alias near the coefficient.
    assert "register_misplaced_at_coeff_2" in (r.reason or "")
    assert "|E" in (r.reason or "")


def test_recipe_per_occurrence_pass_repeated_noetic_one_alias_per_coeff():
    """Edge case — recipe with three operands sharing the same noetic
    ^3 must accept when the ^3 alias appears at least once near each
    coefficient. Order tolerance via greedy backtracking.
    """
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas=(
            "Θ(Ω_collapse_03) = 0.5*^3^P + 0.7*^3^C + 1*^3^E → Ω_collapse_03"
        ),
        english_output=(
            "To produce the outcome called collapse_03, combine 0.5 of "
            "an aversion to a foundational principle, add 0.7 of an "
            "aversion in cognitive thinking, and add 1 of an aversion "
            "in evaluative judgment."
        ),
    )
    assert r.passed, r.reason


def test_recipe_per_occurrence_skip_for_non_recipe():
    """Pass-by-skip — non-recipe source emits no ``<coeff>*<state>`` pairs."""
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas="^3^P|A + ^4^E|f",
        english_output="Aversion to a foundational principle plus an "
        "evaluative resonance.",
    )
    assert r.passed
    assert "skipped" in (r.reason or "").lower()


def test_recipe_per_occurrence_fail_when_coefficient_anchor_missing():
    """Fail case — coefficient ``1`` rendered as ``a full measure``;
    digit anchor not found, so the per-occurrence check cannot resolve
    the operand and reports anchor-not-found.

    Mirrors seed_recipe_00361. The original recipe-preservation
    validator misses this because ``1 in english_output`` substring-
    matches inside ``rehearsal_61``.
    """
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas=(
            "Θ(Ω_rehearsal_61) = 1*^8^C|E + 0.5*^4^E_{F1} + 0.5*^7^P "
            "→ Ω_rehearsal_61"
        ),
        english_output=(
            "To produce the outcome called rehearsal_61, combine a full "
            "measure of what triggered a memory in cognitive thinking "
            "and mental reasoning, add 0.5 of what struck a chord in "
            "evaluative judgment tied to the need for unity, and add "
            "0.5 of practice making perfect in foundational thinking."
        ),
    )
    assert not r.passed
    assert "anchor not found" in (r.reason or "").lower()


def test_recipe_per_occurrence_pass_register_absent_no_conflict():
    """Pass case — register descriptor omitted from English window.

    Pure-absence is tolerated by design. The conflict-based register
    check only fails when a DIFFERENT register's alias is in the
    window. If the operand has |T but no transcendent / strategic /
    big-picture alias surfaces, AND no conflicting register alias
    surfaces, the validator passes.
    """
    m = _load_module()
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas="Θ(Ω_outcome) = 1*^2^P|T + 0.5*^9^O → Ω_outcome",
        english_output=(
            "To produce the outcome called outcome, take 1 of being "
            "drawn toward a foundational principle, and add 0.5 of "
            "something that popped into mind operationally."
        ),
    )
    assert r.passed, r.reason


def test_recipe_per_occurrence_order_tolerant_duplicate_coeffs():
    """Edge case — two operands share the same coefficient string and
    appear in PERMUTED order in the English. Greedy backtracking must
    find a satisfying assignment.
    """
    m = _load_module()
    # Source order: ^2^C then ^6^P. English order: ^6 first, ^2 second.
    r = m.validate_cas_to_english_recipe_per_occurrence(
        source_cas="Θ(Ω_demo) = 0.5*^2^C + 0.5*^6^P → Ω_demo",
        english_output=(
            "Combine 0.5 of breaking down a foundational principle "
            "and 0.5 of being drawn toward something cognitive."
        ),
    )
    assert r.passed, r.reason


def test_fractal_k_indices_pass_with_operator_names():
    m = _load_module()
    r = m.validate_cas_to_english_fractal_k_indices(
        source_cas="Φ⟨9:4:7⟩",
        english_output=(
            "An idea popped into mind, then struck a chord, then turned "
            "into muscle memory."
        ),
    )
    assert r.passed
    assert r.detail["k_values"] == [9, 4, 7]


def test_render_fractal_sequence_deterministic_preserves_k_values():
    m = _load_module()
    out = m.render_fractal_sequence_deterministic("Phi<2:6:8>")
    assert "being drawn to something" in out
    assert "breaking it down" in out
    assert "triggered a memory" in out
    r = m.validate_cas_to_english_fractal_k_indices(
        source_cas="Phi<2:6:8>",
        english_output=out,
    )
    assert r.passed, r.reason


def test_render_fractal_sequence_deterministic_accepts_k9_phrase():
    m = _load_module()
    out = m.render_fractal_sequence_deterministic("Phi<1:9:2>")
    assert "something that just clicked" in out
    r = m.validate_cas_to_english_fractal_k_indices(
        source_cas="Phi<1:9:2>",
        english_output=out,
    )
    assert r.passed, r.reason


def test_wave2_5_iterate_uses_deterministic_renderer_for_fractals():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    counts = m.wave2_5_iterate(
        [{
            "seed_id": "seed_fractal_sequence_x",
            "expression": "Phi<2:6>",
            "grammar_category": "fractal_sequence",
        }],
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert accepted[0].model_used == "deterministic_fractal_renderer"
    assert accepted[0].estimated_cost_usd == 0.0
    assert "being drawn to something" in accepted[0].english_description
    assert "breaking it down" in accepted[0].english_description


def test_render_cross_register_omega_deterministic_preserves_exact_registers():
    m = _load_module()
    out = m.render_cross_register_omega_deterministic(
        "(^4^C|E × ^4^C|f) = ^4^C|Ω_calm"
    )
    assert "embodied sensorimotor awareness" in out
    assert "felt emotion" in out
    assert "analytical reasoning" not in out
    assert "calm" in out
    results = m.run_validators_for_cas_to_english(
        seed={
            "expression": "(^4^C|E × ^4^C|f) = ^4^C|Ω_calm",
            "grammar_category": "cross_register_omega",
        },
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_wave2_5_iterate_uses_deterministic_renderer_for_cross_register_omega():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    counts = m.wave2_5_iterate(
        [{
            "seed_id": "seed_cross_register_omega_x",
            "expression": "(^6^P|f × ^6^P|A) = ^6^P|Ω_integration",
            "grammar_category": "cross_register_omega",
        }],
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert accepted[0].model_used == "deterministic_cross_register_omega_renderer"
    assert accepted[0].estimated_cost_usd == 0.0
    assert "felt emotion and analytical reasoning" in accepted[0].english_description


def test_render_rpm_chain_deterministic_preserves_stage_domains():
    m = _load_module()
    src = (
        "let stageA0_2_0109 = ^0^P; let stageD2_2_0109 = ^8^P_{F2}; "
        "let stageW2_2_0109 = ^8^C_{F2}; let stageP2_2_0109 = ^8^E_{F2}; "
        "stageW2_2_0109 -> stageP2_2_0109"
    )
    out = m.render_rpm_chain_deterministic(src)
    assert "stageA0_2_0109 names a thought in a foundational frame" in out
    assert "stageD2_2_0109 names something that triggered a memory in a foundational frame" in out
    assert "stageW2_2_0109 names something that triggered a memory in cognitive thinking" in out
    assert "stageP2_2_0109 names something that triggered a memory in evaluative judgment" in out
    assert "stageW2_2_0109 leads to stageP2_2_0109" in out
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "rpm_chain"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_wave2_5_iterate_uses_deterministic_renderer_for_rpm_chain():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    counts = m.wave2_5_iterate(
        [{
            "seed_id": "seed_rpm_chain_x",
            "expression": (
                "let stageA0_6_0002 = ^0^P; "
                "let stageD6_6_0002 = ^3^P_{F6}; "
                "let stageW6_6_0002 = ^3^C_{F6}; "
                "let stageP6_6_0002 = ^3^E_{F6}; "
                "stageD6_6_0002 -> stageW6_6_0002"
            ),
            "grammar_category": "rpm_chain",
        }],
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert accepted[0].model_used == "deterministic_rpm_chain_renderer"
    assert accepted[0].estimated_cost_usd == 0.0
    assert "stageD6_6_0002 names an aversion in a foundational frame" in accepted[0].english_description
    assert "stageW6_6_0002 names an aversion in cognitive thinking" in accepted[0].english_description


def test_render_meta_logic_relation_deterministic_avoids_jargon():
    m = _load_module()
    src = "NoeticCluster{^3, ^5, ^7, ^8, ^9}"
    out = m.render_meta_logic_relation_deterministic(src)
    assert "cognitive operations" not in out.lower()
    assert "noetic" not in out.lower()
    assert "an aversion" in out
    assert "identity shaped by experience" in out
    assert "muscle memory" in out
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "meta_logic_relation"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_render_meta_logic_coordinate_does_not_make_drive_an_outcome():
    m = _load_module()
    src = "Coordinate{^3, O, F2, T}"
    out = m.render_meta_logic_relation_deterministic(src)
    assert "outcome called wisdom" not in out
    assert "wisdom as the guiding need" in out
    assert "operational behavior" in out
    assert "big-picture perspective" in out
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "meta_logic_relation"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_wave2_5_iterate_uses_deterministic_renderer_for_meta_logic():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    counts = m.wave2_5_iterate(
        [{
            "seed_id": "seed_meta_logic_relation_x",
            "expression": "PartitionOf(Noetics, NoeticCluster{^0, ^2}, NoeticCluster{^3})",
            "grammar_category": "meta_logic_relation",
        }],
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert accepted[0].model_used == "deterministic_meta_logic_renderer"
    assert accepted[0].estimated_cost_usd == 0.0
    assert "partition" in accepted[0].english_description.lower()


def test_render_inversion_deterministic_preserves_direct_arrow_domains():
    m = _load_module()
    src = "^5^C -> ^5^E"
    out = m.render_inversion_deterministic(src)
    assert "cognitive thinking leads to" in out
    assert "evaluative judgment" in out
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "inversion"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_render_inversion_deterministic_delegates_let_chain():
    m = _load_module()
    src = (
        "let stageA0_axisA_7 = ^0^P; "
        "let stageP7_axisA_7 = ^8^E_{F7}; "
        "stageA0_axisA_7 -> stageP7_axisA_7"
    )
    out = m.render_inversion_deterministic(src)
    assert "stageA0_axisA_7 names a thought in a foundational frame" in out
    assert "stageP7_axisA_7 names something that triggered a memory in evaluative judgment" in out
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "inversion"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_wave2_5_iterate_uses_deterministic_renderer_for_inversion():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    counts = m.wave2_5_iterate(
        [{
            "seed_id": "seed_inversion_x",
            "expression": "^2^C_{F2} + ^3^C_{F6}",
            "grammar_category": "inversion",
        }],
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert accepted[0].model_used == "deterministic_inversion_renderer"
    assert accepted[0].estimated_cost_usd == 0.0


def test_simple_lanes_render_deterministically_and_validate():
    m = _load_module()
    examples = [
        ("state_literal", "^9^O_{F3}|E", m.render_state_literal_deterministic),
        ("binary_composition", "^8^P -> ^1^O", m.render_binary_composition_deterministic),
        ("let_binding", "let trace_0055 = ^9^O_{F3}|E", m.render_let_binding_deterministic),
    ]
    for category, source, renderer in examples:
        out = renderer(source)
        results = m.run_validators_for_cas_to_english(
            seed={"expression": source, "grammar_category": category},
            english_output=out,
        )
        assert all(r.passed for r in results), [
            category,
            out,
            [(r.name, r.reason) for r in results],
        ]
    assert not m.render_state_literal_deterministic("^5^E|E").startswith(
        "A group containing"
    )
    assert "fuse" in m.render_binary_composition_deterministic("^9^C × ^7^C")


def test_wave2_5_iterate_uses_deterministic_renderer_for_simple_lanes():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    seeds = [
        {
            "seed_id": "seed_state_literal_x",
            "expression": "^9^O_{F3}|E",
            "grammar_category": "state_literal",
        },
        {
            "seed_id": "seed_binary_composition_x",
            "expression": "^8^P -> ^1^O",
            "grammar_category": "binary_composition",
        },
        {
            "seed_id": "seed_let_binding_x",
            "expression": "let trace_0055 = ^9^O_{F3}|E",
            "grammar_category": "let_binding",
        },
    ]
    counts = m.wave2_5_iterate(
        seeds,
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 3, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert [r.model_used for r in accepted] == [
        "deterministic_state_literal_renderer",
        "deterministic_binary_composition_renderer",
        "deterministic_let_binding_renderer",
    ]
    assert all(r.estimated_cost_usd == 0.0 for r in accepted)


def test_render_recipe_deterministic_disambiguates_embodied_register():
    m = _load_module()
    src = (
        "Θ(Ω_rehearsal_65) = 2*^1^P_{F1}|E + "
        "0.5*^0^C_{F2} → Ω_rehearsal_65"
    )
    out = m.render_recipe_deterministic(src)
    assert "2 of paying attention in a foundational frame" in out
    assert "expressed through embodied awareness" in out
    assert "evaluative judgment" not in out.split("0.5", 1)[0]
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "recipe"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_render_diagram_export_deterministic_preserves_exported_state_domain():
    m = _load_module()
    src = "export let tau_0441 = ^0^O_{F4}"
    out = m.render_diagram_export_deterministic(src)
    assert "Export tau_0441" in out
    assert "operational behavior" in out
    assert "connection as the guiding need" in out
    results = m.run_validators_for_cas_to_english(
        seed={"expression": src, "grammar_category": "diagram_export"},
        english_output=out,
    )
    assert all(r.passed for r in results), [
        (r.name, r.reason) for r in results
    ]


def test_wave2_5_iterate_uses_deterministic_renderer_for_recipe_and_diagram():
    m = _load_module()
    accepted = []
    rejected = []
    calls = []

    def model_callable(system, user):
        calls.append((system, user))
        return "this model should not be called", 10, 10

    seeds = [
        {
            "seed_id": "seed_recipe_x",
            "expression": "Θ(Ω_demo) = 1*^4^O + 1*^7^O → Ω_demo",
            "grammar_category": "recipe",
        },
        {
            "seed_id": "seed_diagram_export_x",
            "expression": "export let node_0001 = Theta(Omega_demo) = 1*^4^O + 1*^7^O -> Omega_demo",
            "grammar_category": "diagram_export",
        },
    ]
    counts = m.wave2_5_iterate(
        seeds,
        model_callable=model_callable,
        model_name="paid-model",
        cost_per_in_token=1.0,
        cost_per_out_token=1.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 2, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert [r.model_used for r in accepted] == [
        "deterministic_recipe_renderer",
        "deterministic_diagram_export_renderer",
    ]


def test_fractal_k_indices_fail_on_count_misread():
    m = _load_module()
    r = m.validate_cas_to_english_fractal_k_indices(
        source_cas="Φ⟨2:9:6:7:8:9:2:5⟩",
        english_output=(
            "A sequence of 8 stages moving through the operations 2, 9, "
            "6, 7, 8, 9, 2, 5."
        ),
    )
    assert not r.passed
    # Both the count-misread and the missing-operator-rendering should
    # flag.
    assert ("count-misread" in (r.reason or "")
            or "k-values not rendered" in (r.reason or ""))


def test_fractal_k_indices_skip_for_non_fractal():
    m = _load_module()
    r = m.validate_cas_to_english_fractal_k_indices(
        source_cas="^3^P|A",
        english_output="Principled aversion.",
    )
    assert r.passed


def test_diagram_export_statecluster_requires_member_coverage():
    m = _load_module()
    r = m.validate_cas_to_english_diagram_export(
        source_cas="StateCluster{^4^O, ^0^E, ^8^P}",
        english_output=(
            "A cognitive state composed of three linked elements, "
            "but without their actual operator meanings."
        ),
    )
    assert not r.passed
    assert "missing member noetics" in (r.reason or "")


def test_diagram_export_rejects_wrong_cluster_cardinality():
    m = _load_module()
    r = m.validate_cas_to_english_diagram_export(
        source_cas="StateCluster{^4^O, ^0^E, ^8^P}",
        english_output=(
            "A cognitive state clustering together four distinct elements: "
            "something that struck a chord, a thought, a triggered memory, "
            "and an operational behavior."
        ),
    )
    assert not r.passed
    assert "wrong explicit cluster cardinality" in (r.reason or "")


def test_diagram_export_accepts_correct_cluster_cardinality():
    m = _load_module()
    r = m.validate_cas_to_english_diagram_export(
        source_cas="StateCluster{^4^O, ^0^E, ^8^P}",
        english_output=(
            "A cluster of three elements: something that struck a chord, "
            "a thought, and something that triggered a memory."
        ),
    )
    assert r.passed, r.reason


def test_anti_copy_pass_when_independent_generation():
    m = _load_module()
    r = m.validate_anti_copy_english_to_cas(
        prompt_text="Translate to CAS: a thought drawn toward foundations.",
        generated_cas="^0 ∘ ^2^P",
    )
    assert r.passed


def test_anti_copy_fail_on_verbatim_substring():
    m = _load_module()
    r = m.validate_anti_copy_english_to_cas(
        prompt_text=(
            "reference target: ^0^P|A + ^0^P|T (do not paste verbatim)"
        ),
        generated_cas="^0^P|A + ^0^P|T",
    )
    assert not r.passed
    assert "copy detected" in (r.reason or "")


# ---------------------------------------------------------------------------
# Group 4b: english_to_cas structural-match validator (fix 2)
# ---------------------------------------------------------------------------


def test_structural_match_pass_when_identical():
    m = _load_module()
    src = "Θ(Ω_x) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_x"
    r = m.validate_english_to_cas_structural_match(
        source_cas=src,
        generated_cas=src,
    )
    assert r.passed, r.reason


def test_structural_match_pass_when_reordered():
    """Multiset equality, not sequence equality — A + B == B + A."""
    m = _load_module()
    r = m.validate_english_to_cas_structural_match(
        source_cas="^3^P|A + ^4^E|f",
        generated_cas="^4^E|f + ^3^P|A",
    )
    assert r.passed, r.reason


def test_structural_match_fail_on_state_literal_drift():
    m = _load_module()
    r = m.validate_english_to_cas_structural_match(
        source_cas="^3^P|A + ^4^E|f",
        generated_cas="^3^P|A",  # missing one literal
    )
    assert not r.passed
    assert "state_literal_drift" in (r.reason or "")


def test_structural_match_fail_on_coefficient_mismatch():
    m = _load_module()
    r = m.validate_english_to_cas_structural_match(
        source_cas="Θ(Ω_x) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_x",
        generated_cas="Θ(Ω_x) = 0.5*^9^C|A + 1.5*^1^P|A → Ω_x",
    )
    assert not r.passed
    assert "coefficient_mismatch" in (r.reason or "")


def test_structural_match_fail_on_omega_rename():
    m = _load_module()
    r = m.validate_english_to_cas_structural_match(
        source_cas="Θ(Ω_alpha) = 1*^5^P → Ω_alpha",
        generated_cas="Θ(Ω_beta) = 1*^5^P → Ω_beta",
    )
    assert not r.passed
    assert "omega_target_mismatch" in (r.reason or "")


def test_structural_match_fail_on_operator_jaccard():
    m = _load_module()
    r = m.validate_english_to_cas_structural_match(
        # Source has +, ×, =, → (4 ops). Generated has only + (1 op).
        # Jaccard = 1/4 = 0.25, below default threshold 0.7.
        source_cas="(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω",
        generated_cas="^3^P|A + ^3^P|f + ^3^P|T",
    )
    # Note: state-literal multisets also differ (^3^P|Ω vs absence). Both
    # divergence dimensions should be reported.
    assert not r.passed


def test_structural_match_pass_with_drive_and_register_preserved():
    m = _load_module()
    r = m.validate_english_to_cas_structural_match(
        source_cas="^9^P_{F8}|A + ^9^C_{F7}|f",
        generated_cas="^9^P_{F8}|A + ^9^C_{F7}|f",
    )
    assert r.passed, r.reason


def test_run_validators_for_english_to_cas_includes_structural_match_when_source_provided():
    m = _load_module()
    results = m.run_validators_for_english_to_cas(
        prompt_text="An English description...",
        generated_cas="^3^P|A + ^4^E|f",
        source_cas="^3^P|A + ^4^E|f",
    )
    names = [r.name for r in results]
    assert "english_to_cas_structural_match" in names
    assert all(r.passed for r in results)


def test_run_validators_for_english_to_cas_skips_structural_match_without_source():
    m = _load_module()
    results = m.run_validators_for_english_to_cas(
        prompt_text="An English description...",
        generated_cas="^3^P|A + ^4^E|f",
    )
    names = [r.name for r in results]
    assert "english_to_cas_structural_match" not in names


# ---------------------------------------------------------------------------
# Group 4c: jaccard validator (existing)
# ---------------------------------------------------------------------------


def test_jaccard_pass_for_minimal_edit():
    m = _load_module()
    r = m.validate_invalid_to_corrected_jaccard(
        invalid_expression="^13^E|f + ^1^E|E",
        corrected_expression="^1^E|f + ^1^E|E",
    )
    assert r.passed
    assert r.detail["jaccard"] >= 0.6


def test_jaccard_fail_for_whole_rewrite():
    m = _load_module()
    r = m.validate_invalid_to_corrected_jaccard(
        invalid_expression="^13^E|f + ^1^E|E",
        corrected_expression="^2^P + ^4^C|T → Ω_demo",
    )
    assert not r.passed
    assert r.detail["jaccard"] < 0.6


def test_jaccard_threshold_is_configurable():
    m = _load_module()
    # A high-overlap legitimate edit should pass at threshold 0.6 but fail
    # at threshold 0.99.
    r_loose = m.validate_invalid_to_corrected_jaccard(
        invalid_expression="^3^P|A + ^4^P|f",
        corrected_expression="^3^P|A + ^4^E|f",
        threshold=0.6,
    )
    r_strict = m.validate_invalid_to_corrected_jaccard(
        invalid_expression="^3^P|A + ^4^P|f",
        corrected_expression="^3^P|A + ^4^E|f",
        threshold=0.99,
    )
    assert r_loose.passed
    assert not r_strict.passed


# ---------------------------------------------------------------------------
# Group 5: wave2_5_iterate accept/reject path
# ---------------------------------------------------------------------------


def test_wave2_5_iterate_accepts_when_validators_pass():
    m = _load_module()
    seeds = [
        {
            "seed_id": "seed_x",
            "expression": "^3^P|A",
            "grammar_category": "state_literal",
        },
    ]
    accepted: list[Any] = []
    rejected: list[Any] = []

    def good_model(system: str, user: str) -> tuple[str, int, int]:
        # ^3^P|A — Negative noetic, Principled domain, Analytical register.
        # All three must surface to satisfy the state_literal validator.
        return (
            "An analytical aversion to a foundational principle, reasoned "
            "through carefully.",
            100,
            20,
        )

    counts = m.wave2_5_iterate(
        seeds,
        model_callable=good_model,
        model_name="test-model",
        cost_per_in_token=0.0,
        cost_per_out_token=0.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}, (
        f"unexpected rejections: {rejected}"
    )
    assert len(accepted) == 1
    assert accepted[0].seed_id == "seed_x"


def test_wave2_5_iterate_uses_deterministic_recipe_instead_of_bad_model():
    m = _load_module()
    seeds = [
        {
            "seed_id": "seed_recipe_x",
            "expression": "Θ(Ω_test_01) = 0.7*^9^C|A → Ω_test_01",
            "grammar_category": "recipe",
        },
    ]
    accepted: list[Any] = []
    rejected: list[dict[str, Any]] = []
    calls: list[tuple[str, str]] = []

    def bad_model(system: str, user: str) -> tuple[str, int, int]:
        calls.append((system, user))
        # Drops both the 0.7 coefficient and the test_01 named-stem.
        return ("A thought becomes reasoning.", 100, 10)

    counts = m.wave2_5_iterate(
        seeds,
        model_callable=bad_model,
        model_name="test-model",
        cost_per_in_token=0.0,
        cost_per_out_token=0.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
    assert calls == []
    assert rejected == []
    assert accepted[0].model_used == "deterministic_recipe_renderer"
    assert accepted[0].estimated_cost_usd == 0.0
    assert "0.7" in accepted[0].english_description
    assert "test_01" in accepted[0].english_description


def test_fractal_validator_rejects_count_misread_prose():
    m = _load_module()
    r = m.validate_cas_to_english_fractal_k_indices(
        source_cas="Φ⟨9:4:7⟩",
        english_output="A sequence of 3 stages with operations 9, 4, and 7.",
    )
    assert not r.passed
    assert ("count-misread" in (r.reason or "")
            or "k-values not rendered" in (r.reason or ""))


def test_wave2_5_iterate_records_carry_full_traceability():
    m = _load_module()
    seeds = [
        {
            "seed_id": "seed_x",
            "expression": "^3^P|A",
            "grammar_category": "state_literal",
        },
    ]
    accepted: list[Any] = []
    rejected: list[Any] = []

    def model(system: str, user: str) -> tuple[str, int, int]:
        # ^3^P|A — must satisfy noetic + domain + register coverage now.
        return (
            "An analytical aversion to a foundational principle, reasoned "
            "through carefully.",
            100,
            20,
        )

    m.wave2_5_iterate(
        seeds,
        model_callable=model,
        model_name="test-model",
        cost_per_in_token=0.0,
        cost_per_out_token=0.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert len(accepted) == 1
    rec = accepted[0].to_record()
    # Per feedback_traceability_is_the_whole_purpose.md: every record must
    # walk back to its origin.
    for required_field in (
        "seed_id",
        "source_cas",
        "grammar_category",
        "english_description",
        "prompt_template_version",
        "validators_run",
        "validators_passed",
        "validators_failed_reasons",
        "model_used",
        "raw_response",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "generated_at",
    ):
        assert required_field in rec, f"missing traceability field: {required_field}"
    assert rec["prompt_template_version"] == m.WAVE_2_5_TEMPLATE_VERSION


# ---------------------------------------------------------------------------
# Group 6: parse helper + tokenize helper round-trip
# ---------------------------------------------------------------------------


def test_parse_cas_strips_fences_and_labels():
    m = _load_module()
    assert m.parse_cas_from_response("```cas\n^3^P|A\n```") == "^3^P|A"
    assert m.parse_cas_from_response("CAS: ^2^C × ^5^P") == "^2^C × ^5^P"


# ---------------------------------------------------------------------------
# Group 7: validate_no_cas_jargon_leakage (global Wave 2.5 guard)
#
# Added 2026-05-08 in response to the paid-preflight validator-coverage gap
# where 179 records were accepted despite leaking Ω_<name>, state literals,
# F[1-7] drives, "domain X" CAS-jargon, etc.
# ---------------------------------------------------------------------------


def test_jargon_leakage_pass_on_clean_english():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Paying attention to a foundational principle leads to it "
            "striking a chord with you."
        ),
    )
    assert r.passed, r.reason


def test_jargon_leakage_fail_on_omega_underscore_name():
    """User example: 'pulls you toward Ω_patience.' must reject."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "When you're drawn to thinking clearly, drawn to staying "
            "focused, and drawn to acting with care, that combination "
            "pulls you toward Ω_patience."
        ),
    )
    assert not r.passed
    assert "omega_symbol" in (r.reason or "")


def test_jargon_leakage_fail_on_omega_with_digit_stem():
    """Catches Ω_4 (digit stem), which a [A-Za-z]-only regex would miss."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "You become aware of something, and that awareness strikes a "
            "chord with outcome Ω_4."
        ),
    )
    assert not r.passed
    assert "omega_symbol" in (r.reason or "")


def test_jargon_leakage_fail_on_state_literal_prefix():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Something rubs the wrong way (^3^P|A) about a foundational "
            "principle."
        ),
    )
    assert not r.passed
    assert "state_literal_prefix" in (r.reason or "")


def test_jargon_leakage_fail_on_drive_reference_standalone():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "A thought comes to mind. That triggers a memory involving "
            "F2, which then reminds you of something about F2."
        ),
    )
    assert not r.passed
    assert "drive_reference" in (r.reason or "")


def test_jargon_leakage_pass_on_compound_identifier_with_F_digit():
    """Word boundary requirement: 'F1A2' or 'F1' inside a longer token
    should NOT match — only the standalone digit form is a leak."""
    m = _load_module()
    # F1A2 is a synthetic identifier — used in unit fixtures but not a
    # real drive reference. Word boundaries must protect this.
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "The ticket reference F1A2B5 is being escalated to the "
            "infrastructure team."
        ),
    )
    assert r.passed, r.reason


def test_jargon_leakage_fail_on_noetic_keyword():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Three noetics combine to produce a unified outcome."
        ),
    )
    assert not r.passed
    assert "noetic_keyword" in (r.reason or "")


def test_jargon_leakage_fail_on_operator_slot_language():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "The set gathers a thought, breaking down, and operator slot 8."
        ),
    )
    assert not r.passed
    assert "operator_jargon" in (r.reason or "")


def test_jargon_leakage_fail_on_cognitive_operation_language():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output="A cognitive operation CO-9 combines with lambda.",
    )
    assert not r.passed
    assert "operator_jargon" in (r.reason or "")


def test_jargon_leakage_fail_on_rpm_keyword():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output="The RPM chain unfolds in four stages.",
    )
    assert not r.passed
    assert "rpm_keyword" in (r.reason or "")


def test_jargon_leakage_fail_on_register_letter_after_word():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Who you are—shaped by experience—is examined through the "
            "lens of domain P, register F6."
        ),
    )
    assert not r.passed
    assert "register_jargon_contextual" in (r.reason or "")


def test_jargon_leakage_fail_on_named_register_phrase():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "An aversion in the analytical register combined with one "
            "in the affective register."
        ),
    )
    assert not r.passed
    assert "register_jargon_named" in (r.reason or "")


def test_jargon_leakage_fail_on_plural_registers_in_jargon_context():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Something resonates with you across two distinct registers."
        ),
    )
    assert not r.passed
    assert "register_jargon_plural" in (r.reason or "")


def test_jargon_leakage_fail_on_domain_followed_by_letter():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Who you are, shaped by domain P, combined with who you are, "
            "shaped by domain E."
        ),
    )
    assert not r.passed
    assert "domain_jargon" in (r.reason or "")


def test_jargon_leakage_fail_on_letter_dash_domain():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output="A resonance struck a chord with the C-domain function.",
    )
    assert not r.passed
    assert "domain_jargon" in (r.reason or "")


def test_jargon_leakage_fail_on_F_prefixed_domain_phrase():
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output="A thought shaped by experiences that hits hard in the F4 domain.",
    )
    assert not r.passed
    assert "domain_jargon" in (r.reason or "")


def test_jargon_leakage_pass_on_plain_english_domain_of_mathematics():
    """Critical false-positive test: 'the domain of mathematics' must NOT
    flag, even though it contains the bare word 'domain'."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "The domain of mathematics has long fascinated philosophers; "
            "in the domain of biology, the same questions take a different "
            "form. We move from one domain to another easily."
        ),
    )
    assert r.passed, r.reason


def test_jargon_leakage_fail_on_cas_axis_domain_wording():
    """Wave 2.5 calibration showed 'operational domain' style leaks."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "A pull toward it, expressed through felt emotion, in the "
            "operational domain."
        ),
    )
    assert not r.passed
    assert "domain_axis_word" in (r.reason or "")


def test_jargon_leakage_fail_on_bare_drive_axis_word():
    """Accepted RPM samples used 'structure-and-order drive' as CAS jargon."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "Let x name who one is shaped by in the structure-and-order drive."
        ),
    )
    assert not r.passed
    assert "drive_axis_word" in (r.reason or "")


def test_jargon_leakage_fail_on_bare_register_axis_word():
    """Bare register labels are not allowed in generated training prose."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "The same pattern appears across analytical and embodied registers."
        ),
    )
    assert not r.passed
    assert "register_axis_word" in (r.reason or "")


def test_jargon_leakage_pass_on_registered_nurse_phrase():
    """Critical false-positive test: word 'registered' must NOT trigger
    the bare 'register' jargon detector."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "She is a registered nurse who registered to vote last year."
        ),
    )
    assert r.passed, r.reason


def test_jargon_leakage_pass_on_cash_register():
    """Plain English use of 'register' as a noun (cash register) must pass."""
    m = _load_module()
    r = m.validate_no_cas_jargon_leakage(
        english_output=(
            "She placed the change in the cash register and walked out."
        ),
    )
    assert r.passed, r.reason


def test_jargon_leakage_user_verbatim_example():
    """The user's exact verbatim concrete example must reject."""
    m = _load_module()
    seed = {
        "seed_id": "verbatim_user_example",
        "expression": "(^2|T × ^2|f × ^2|E) = ^2|Ω_patience",
        "grammar_category": "cross_register_omega",
    }
    english = (
        "When you're drawn to thinking clearly, drawn to staying focused, "
        "and drawn to acting with care, that combination pulls you toward "
        "Ω_patience."
    )
    results = m.run_validators_for_cas_to_english(
        seed=seed, english_output=english
    )
    assert any(not r.passed for r in results), (
        f"user verbatim example must be rejected; results={[r.name for r in results]}"
    )
    # Specifically: the global jargon validator must catch the Ω_patience.
    jargon = [r for r in results if r.name == "no_cas_jargon_leakage"]
    assert jargon and not jargon[0].passed
    assert "omega_symbol" in (jargon[0].reason or "")


# ---------------------------------------------------------------------------
# Group 8: slot-specific structural-preservation validators
# ---------------------------------------------------------------------------


def test_state_literal_pass_with_full_components():
    m = _load_module()
    r = m.validate_cas_to_english_state_literal_preservation(
        source_cas="^3^P|A",
        english_output=(
            "An analytical aversion to a foundational principle, reasoned "
            "through carefully."
        ),
    )
    assert r.passed, r.reason


def test_state_literal_fail_on_missing_register():
    m = _load_module()
    r = m.validate_cas_to_english_state_literal_preservation(
        source_cas="^3^P|A",
        english_output="A principled aversion.",  # no analytical signal
    )
    assert not r.passed
    assert "register" in (r.reason or "")


def test_state_literal_fail_on_missing_drive():
    m = _load_module()
    r = m.validate_cas_to_english_state_literal_preservation(
        source_cas="^8^C_{F2}",
        english_output=(
            "One thing led to another, and that triggered a memory tied "
            "to how you process information."
        ),
    )
    # No drive (F2 -> wisdom/insight) word and the C-domain ("cognitive"
    # / "thought") only loosely surfaces. The validator should fail.
    assert not r.passed


def test_binary_composition_pass_with_both_operands():
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="^2^P + ^4^P",
        english_output=(
            "Drawn toward a foundational principle and struck a chord "
            "with another foundational principle, together."
        ),
    )
    assert r.passed, r.reason


def test_binary_composition_accepts_hyphenated_negative_alias():
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="^3^O × ^6^O",
        english_output=(
            "A pushed-away-from response in the operational arena fused "
            "with breaking down an idea in the operational arena."
        ),
    )
    assert r.passed, r.reason


def test_noetic_aliases_cover_wave2_5_calibration_phrases():
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="^4^P + ^6^P",
        english_output=(
            "A resonant foundational impression combines with an effort "
            "to break down a foundational principle."
        ),
    )
    assert r.passed, r.reason


def test_noetic_aliases_cover_wave2_5_cross_register_phrases():
    m = _load_module()
    r = m.validate_cas_to_english_cross_register_omega(
        source_cas="(^8^C|E × ^8^C|T) = ^8^C|Ω_coherence",
        english_output=(
            "When something triggers a memory in the cognitive realm, "
            "expressed through embodied sensorimotor attention and "
            "transcendent strategic understanding, those two modes fuse "
            "into the outcome called coherence."
        ),
    )
    assert r.passed, r.reason


def test_binary_composition_fail_on_missing_operand():
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="^1^P + ^4^P",
        english_output="Paying attention to something.",
    )
    assert not r.passed
    assert "missing operand components" in (r.reason or "")


def test_cross_register_omega_fail_on_missing_emergent_stem():
    m = _load_module()
    r = m.validate_cas_to_english_cross_register_omega(
        source_cas="(^3^P|A × ^3^P|f) = ^3^P|Ω_alignment",
        english_output=(
            "An analytical aversion to a foundational principle, combined "
            "with a felt aversion to a foundational principle, produces "
            "a unified outcome."
        ),
    )
    assert not r.passed
    assert "alignment" in (r.reason or "")


def test_cross_register_omega_pass_with_stem_and_register_descriptions():
    m = _load_module()
    r = m.validate_cas_to_english_cross_register_omega(
        source_cas="(^3^P|A × ^3^P|f) = ^3^P|Ω_alignment",
        english_output=(
            "An analytical, reasoned aversion to a foundational principle "
            "combined with a felt, affective aversion to that same "
            "foundational principle yields the alignment outcome."
        ),
    )
    assert r.passed, r.reason


def test_cross_register_omega_rejects_invented_third_mode():
    m = _load_module()
    r = m.validate_cas_to_english_cross_register_omega(
        source_cas="(^6^P|f × ^6^P|A) = ^6^P|Ω_integration",
        english_output=(
            "A principled effort to break down an idea expressed through "
            "analytical reasoning, felt emotion, and embodied awareness — "
            "all three modes fusing into the outcome called integration."
        ),
    )
    assert not r.passed
    assert "unexpected register descriptions" in (r.reason or "")
    assert "register count mismatch" in (r.reason or "")


def test_cross_register_omega_accepts_big_picture_t_alias():
    m = _load_module()
    r = m.validate_cas_to_english_cross_register_omega(
        source_cas="(^4^P|T × ^4^P|A) = ^4^P|Ω_presence",
        english_output=(
            "A foundational response that strikes a chord, expressed "
            "through big-picture strategic conviction and analytical "
            "reasoning, with those two modes fusing into the outcome "
            "called presence."
        ),
    )
    assert r.passed, r.reason


def test_cross_register_omega_accepts_no_domain_register_forms():
    m = _load_module()
    r = m.validate_cas_to_english_cross_register_omega(
        source_cas="(^4|f × ^4|T) = ^4|Ω_refusal",
        english_output=(
            "When something strikes a chord in an affective, felt way "
            "and also in a transcendent strategic way, those two modes "
            "of resonance fuse into the outcome called refusal."
        ),
    )
    assert r.passed, r.reason


def test_rpm_chain_fail_on_missing_flow_connectives():
    m = _load_module()
    r = m.validate_cas_to_english_rpm_chain(
        source_cas="^0^P -> ^9^P_{F7} -> ^9^C_{F7} -> ^9^E_{F7}",
        # Only one flow connective for three arrows.
        english_output=(
            "An idea, an effect, an effect, and an effect together."
        ),
    )
    assert not r.passed


def test_rpm_chain_pass_with_chain_flow_words():
    m = _load_module()
    r = m.validate_cas_to_english_rpm_chain(
        source_cas="^1^P -> ^4^P -> ^7^P",
        english_output=(
            "Paying attention to a foundational principle leads to it "
            "striking a chord, which then becomes muscle memory through "
            "practice."
        ),
    )
    assert r.passed, r.reason


def test_rpm_chain_accepts_transforms_into_flow_marker():
    m = _load_module()
    r = m.validate_cas_to_english_rpm_chain(
        source_cas="^1^P -> ^1^C",
        english_output=(
            "Paying attention to a principled foundation transforms into "
            "using your head in a cognitive frame."
        ),
    )
    assert r.passed, r.reason


def test_rpm_chain_accepts_produces_as_flow_marker():
    m = _load_module()
    r = m.validate_cas_to_english_rpm_chain(
        source_cas="^4^P -> ^6^P",
        english_output=(
            "A resonant foundational impression produces an effort to "
            "break down a foundational principle."
        ),
    )
    assert r.passed, r.reason


def test_rpm_chain_skips_recipe_arrows():
    m = _load_module()
    r = m.validate_cas_to_english_rpm_chain(
        source_cas="Θ(Ω_decision_58) = 0.5*^3^E + 0.5*^5^E → Ω_decision_58",
        english_output=(
            "To produce decision_58, combine 0.5 of an aversion with "
            "0.5 of what experience has shaped."
        ),
    )
    assert r.passed, r.reason
    assert "recipe shape" in (r.reason or "")


def test_run_validators_do_not_apply_rpm_chain_to_recipe_shape():
    m = _load_module()
    results = m.run_validators_for_cas_to_english(
        seed={
            "expression": "Θ(Ω_decision_58) = 0.5*^3^E + 0.5*^5^E → Ω_decision_58",
            "grammar_category": "recipe",
        },
        english_output=(
            "To produce the outcome called decision_58, combine 0.5 of "
            "an aversion in evaluative judgment with 0.5 of who one is "
            "in evaluative judgment."
        ),
    )
    assert "cas_to_english_rpm_chain" not in [r.name for r in results]


def test_run_validators_do_not_apply_cross_register_omega_to_recipe_shape():
    m = _load_module()
    results = m.run_validators_for_cas_to_english(
        seed={
            "expression": "Θ(Ω_rehearsal_90) = 0.5*^6^C_{F4}|T + 0.5*^6^P → Ω_rehearsal_90",
            "grammar_category": "recipe",
        },
        english_output=(
            "To build the outcome called rehearsal_90, combine 0.5 of "
            "breaking down an idea about connection expressed in a "
            "big-picture way with 0.5 of a foundational principle."
        ),
    )
    assert "cas_to_english_cross_register_omega" not in [
        r.name for r in results
    ]


def test_let_binding_fail_on_missing_variable_name():
    m = _load_module()
    r = m.validate_cas_to_english_let_binding(
        source_cas="let attraction_0019 = ^5^O_{F5}|T",
        english_output=(
            "We bind a variable to a state shaped by experiences."
        ),
    )
    assert not r.passed
    assert "missing let-binding names" in (r.reason or "")


def test_let_binding_pass_with_name_and_operand():
    m = _load_module()
    r = m.validate_cas_to_english_let_binding(
        source_cas="let trace_0025 = ^6^P",
        english_output=(
            "We define a named reference called trace_0025 that captures "
            "the act of unpacking a foundational principle."
        ),
    )
    assert r.passed, r.reason


def test_inversion_pass_with_full_state_components():
    m = _load_module()
    r = m.validate_cas_to_english_inversion(
        source_cas="^1^P -> ^1^C",
        english_output=(
            "Paying attention to a foundational principle leads to "
            "becoming aware of it as a thought."
        ),
    )
    assert r.passed, r.reason


def test_inversion_accepts_push_away_negative_alias():
    m = _load_module()
    r = m.validate_cas_to_english_inversion(
        source_cas="^2^C + ^3^C",
        english_output=(
            "A pull toward something expressed in cognitive thinking added "
            "to a push away from something expressed in cognitive thinking."
        ),
    )
    assert r.passed, r.reason


def test_diagram_export_fail_on_missing_member_noetics():
    m = _load_module()
    r = m.validate_cas_to_english_diagram_export(
        source_cas="NoeticCluster{^0, ^2, ^7, ^8}",
        # No noetic alias for any of {0, 2, 7, 8}.
        english_output="A grouping of cognitive operations.",
    )
    assert not r.passed


def test_diagram_export_pass_with_cluster_word_and_member_aliases():
    m = _load_module()
    r = m.validate_cas_to_english_diagram_export(
        source_cas="NoeticCluster{^0, ^2}",
        english_output=(
            "A cluster of two thoughts—one foundational and abstract, "
            "the other drawn toward it—held together as a single unit."
        ),
    )
    assert r.passed, r.reason


# ---------------------------------------------------------------------------
# Group 9: run_validators_for_cas_to_english wiring
# ---------------------------------------------------------------------------


def test_run_validators_always_includes_jargon_check():
    m = _load_module()
    seed = {
        "seed_id": "x",
        "expression": "^3^P|A",
        "grammar_category": "state_literal",
    }
    results = m.run_validators_for_cas_to_english(
        seed=seed, english_output="A clean reply with no leakage."
    )
    names = [r.name for r in results]
    assert "no_cas_jargon_leakage" in names


def test_run_validators_user_verbatim_example_rejects_via_jargon():
    """The user's concrete reported leak — Ω_patience — is rejected by
    the global jargon validator regardless of category."""
    m = _load_module()
    seed = {
        "seed_id": "verbatim",
        "expression": "(^2|T × ^2|f × ^2|E) = ^2|Ω_patience",
        "grammar_category": "cross_register_omega",
    }
    english = (
        "When you're drawn to thinking clearly, drawn to staying focused, "
        "and drawn to acting with care, that combination pulls you toward "
        "Ω_patience."
    )
    results = m.run_validators_for_cas_to_english(
        seed=seed, english_output=english
    )
    failed = [r for r in results if not r.passed]
    assert failed, "verbatim example must be rejected"
    fail_names = {r.name for r in failed}
    assert "no_cas_jargon_leakage" in fail_names


def test_tokenize_for_jaccard_separates_operators():
    m = _load_module()
    toks = m._tokenize_for_jaccard("^3^P|A + ^4^P|f")
    assert "+" in toks
    assert "^3^P|A" in toks
    assert "^4^P|f" in toks


# ---------------------------------------------------------------------------
# Group 10: validate_no_phantom_outcome_framing
#
# The Wave 2.5 stratified audit (2026-05-08) found inversion + rpm_chain +
# diagram_export + binary_composition + recipe records that rendered DRIVE
# subscripts (``_{Fk}``) as if they were named OUTCOME targets (``Ω_<stem>``).
# This validator closes that gap. It is a structural safety check, NOT a
# category-specific content-preservation check.
# ---------------------------------------------------------------------------


def test_phantom_outcome_audit_seed_inversion_00038():
    """Concrete audit-cited record: ^2^O_{F2} + ^3^O_{F6} rendered with
    'outcome called wisdom' / 'outcome called structure' (F2/F6 are drives,
    wisdom/structure are drive aliases). Source has no Ω_ token."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="^2^O_{F2} + ^3^O_{F6}",
        english=(
            "A positive pull toward the outcome called wisdom, combined "
            "with a negative push away from the outcome called structure."
        ),
    )
    assert not r.passed
    assert "outcome_called_or_named" in r.detail["triggers"]
    assert any(
        "wisdom" in p.lower() or "structure" in p.lower()
        for p in r.detail["phantom_phrases"]
    )


def test_phantom_outcome_audit_seed_inversion_00042():
    """Audit-cited: ^2^O_{F3} + ^3^O_{F5} -> 'outcome named vitality' /
    'outcome named agency'."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="^2^O_{F3} + ^3^O_{F5}",
        english=(
            "A cognitive state drawn toward the outcome named vitality, "
            "combined with a cognitive state pushed away from the "
            "outcome named agency."
        ),
    )
    assert not r.passed
    assert "outcome_called_or_named" in r.detail["triggers"]


def test_phantom_outcome_audit_seed_rpm_chain_00350():
    """Audit-cited: ``^6^P_{F2}`` rendered as 'in the realm of wisdom'.
    F2 drive surfaces as a realm-style outcome."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="let stageD2_2_0349 = ^6^P_{F2}",
        english=(
            "Let stageD2_2_0349 name breaking down an idea in the realm "
            "of wisdom."
        ),
    )
    assert not r.passed
    assert "realm_of_axis_word" in r.detail["triggers"]


def test_phantom_outcome_passes_when_no_outcome_framing_present():
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="^3^P_{F1}|A",
        english=(
            "A principled aversion driven by a need for unity, expressed "
            "through analytical reasoning."
        ),
    )
    assert r.passed, r.reason


def test_phantom_outcome_passes_with_matching_omega_stem():
    """When source has Ω_<stem> and English uses 'outcome called <stem>'
    referencing that exact stem, the framing is legitimate."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="Θ(Ω_patience) = 0.7*^9^P + 0.3*^1^P → Ω_patience",
        english="The recipe yields the outcome called patience.",
    )
    assert r.passed, r.reason


def test_phantom_outcome_passes_with_ascii_omega_spelling():
    """diagram_export records use the ASCII pre-compile spelling
    ``Theta(Omega_decision)`` and ``Omega_X`` rather than ``Θ(Ω_X)``.
    The validator must accept that spelling as a legitimate source Ω."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas=(
            "export let epsilon_0343 = Theta(Omega_decision) = 1*^0^C + "
            "1*^1^C -> Omega_decision"
        ),
        english=(
            "Export 'epsilon_0343' as a recipe for the outcome called "
            "decision: together these produce the named outcome decision."
        ),
    )
    assert r.passed, r.reason


def test_phantom_outcome_fails_when_omega_stem_mismatched():
    """Source has Ω_alignment but English claims 'outcome called wisdom'.
    The captured stem doesn't match any source Ω target — reject."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="Θ(Ω_alignment) = 0.5*^2^P → Ω_alignment",
        english="A pull toward the outcome called wisdom.",
    )
    assert not r.passed, r.reason


def test_phantom_outcome_passes_for_plain_outcome_of_game():
    """Plain English 'the outcome of the game' must pass — 'of' follows
    'outcome' so this is a prepositional phrase, not phantom framing."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="^3^P",
        english="The outcome of the game was uncertain.",
    )
    assert r.passed, r.reason


def test_phantom_outcome_passes_for_realm_of_mathematics():
    """Plain English 'in the realm of mathematics' must pass — mathematics
    is not a CAS axis word."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="^6^C",
        english="A new theorem in the realm of mathematics.",
    )
    assert r.passed, r.reason


def test_phantom_outcome_passes_for_realm_of_art():
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="^2^P",
        english="A masterpiece in the realm of art.",
    )
    assert r.passed, r.reason


def test_phantom_outcome_fails_for_outcome_called_drive_alias_no_omega():
    """When source has no Ω_ AND English says 'outcome called wisdom',
    that's drive→outcome confusion — reject regardless of which drive
    alias was used."""
    m = _load_module()
    for alias in ("wisdom", "vitality", "agency", "structure", "unity",
                  "connection", "purpose"):
        r = m.validate_no_phantom_outcome_framing(
            source_cas="^2^O_{F2}",
            english=f"A pull toward the outcome called {alias}.",
        )
        assert not r.passed, f"alias={alias} should fail: {r.reason}"


def test_phantom_outcome_named_outcome_X_pattern_caught():
    """The 'named outcome X' construction (used in seed_diagram_export_00442
    audit case where ^0^O_{F4} was rendered as 'an outcome named connection')
    must trigger rejection."""
    m = _load_module()
    r = m.validate_no_phantom_outcome_framing(
        source_cas="export let tau_0441 = ^0^O_{F4}",
        english=(
            "Export tau_0441 as a thought paired with an outcome named "
            "connection or belonging."
        ),
    )
    assert not r.passed, r.reason
    assert "outcome_called_or_named" in r.detail["triggers"]


def test_phantom_outcome_runs_in_pipeline_for_every_category():
    """The phantom-outcome validator must always fire from
    run_validators_for_cas_to_english, regardless of grammar_category."""
    m = _load_module()
    seed = {
        "seed_id": "audit_38",
        "expression": "^2^O_{F2} + ^3^O_{F6}",
        "grammar_category": "inversion",
    }
    results = m.run_validators_for_cas_to_english(
        seed=seed,
        english_output=(
            "A positive pull toward the outcome called wisdom, combined "
            "with a negative push away from the outcome called structure."
        ),
    )
    names = [r.name for r in results]
    assert "no_phantom_outcome_framing" in names
    failed_names = {r.name for r in results if not r.passed}
    assert "no_phantom_outcome_framing" in failed_names


def test_phantom_outcome_runs_for_state_literal_category_too():
    """state_literal category must also receive the phantom-outcome
    check — it is a global safety gate, not category-specific."""
    m = _load_module()
    seed = {
        "seed_id": "sl",
        "expression": "^3^P|A",
        "grammar_category": "state_literal",
    }
    results = m.run_validators_for_cas_to_english(
        seed=seed,
        english_output="A principled aversion expressed analytically.",
    )
    names = [r.name for r in results]
    assert "no_phantom_outcome_framing" in names


# ---------------------------------------------------------------------------
# Group 10: CO-N composition handling in binary_composition
#
# Added 2026-05-08 after a Wave 2.5 audit found that ``CO-N ∘ CO-M`` source
# expressions slipped past the state-literal-only validator. Audit case:
# seed_binary_composition_00498 had source ``CO-9 ∘ CO-7`` and English
# rendering ``something that struck a chord ... something that hit hard``
# — both ^4 (Vibration) aliases, none of ^9 (Below/Effect) or ^7 (Rhythm).
# ---------------------------------------------------------------------------


def test_extract_co_n_operators_finds_indices():
    m = _load_module()
    assert m._extract_co_n_operators("CO-9 ∘ CO-7") == [9, 7]
    assert m._extract_co_n_operators("CO-3 ∘ CO-3") == [3, 3]
    assert m._extract_co_n_operators("^3^P|A") == []


def test_co_n_binary_composition_pass_with_correct_aliases():
    """CO-9 ∘ CO-7 rendered with ^9 + ^7 aliases passes."""
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="CO-9 ∘ CO-7",
        english_output=(
            "Something that just clicked combined with muscle memory."
        ),
    )
    assert r.passed, r.reason


def test_co_n_binary_composition_fail_audit_case_misrender():
    """Audit case: CO-9 ∘ CO-7 rendered with ^4 aliases (struck a chord /
    hit hard) — must fail with operator_misrender_in_co_n_composition."""
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="CO-9 ∘ CO-7",
        english_output=(
            "A composition where something that struck a chord in the "
            "operational arena is then integrated with something that "
            "hit hard in the evaluative arena."
        ),
    )
    assert not r.passed
    assert "operator_misrender_in_co_n_composition" in (r.reason or "")
    # Both source operators (9, 7) should be reported missing.
    assert 9 in r.detail.get("co_n_missing", [])
    assert 7 in r.detail.get("co_n_missing", [])
    # The intruder ^4 should surface in detail.
    assert 4 in r.detail.get("co_n_intruder_operators", [])


def test_co_n_binary_composition_fail_silent_drop():
    """If the source operator's aliases are simply absent (not replaced by
    a wrong one), still fail — but with the simpler 'missing' diagnostic
    rather than the misrender flag."""
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="CO-2 ∘ CO-7",
        english_output="A composition of two things that go together.",
    )
    assert not r.passed
    assert "missing CO-N operator aliases" in (r.reason or "")


def test_co_n_binary_composition_repeated_operator():
    """CO-3 ∘ CO-3 needs a ^3 alias — exists for both occurrences via
    one rendering."""
    m = _load_module()
    r = m.validate_cas_to_english_binary_composition(
        source_cas="CO-3 ∘ CO-3",
        english_output=(
            "Two aversions composed together, both rubbing the wrong way."
        ),
    )
    assert r.passed, r.reason


def test_co_n_and_caret_n_mixed_source_both_checked():
    """Edge case: source mixes ``CO-N`` and ``^N^D``. Both shapes should
    be checked; failures from either branch surface together."""
    m = _load_module()
    # ^3^P needs a ^3 alias AND a P-domain word; CO-7 needs a ^7 alias.
    # English provides ^3 + P + ^7 — should pass.
    r_pass = m.validate_cas_to_english_binary_composition(
        source_cas="^3^P + CO-7",
        english_output=(
            "An aversion to a foundational principle paired with practiced "
            "muscle memory."
        ),
    )
    assert r_pass.passed, r_pass.reason
    # And a fail case where CO-7 alias is missing.
    r_fail = m.validate_cas_to_english_binary_composition(
        source_cas="^3^P + CO-7",
        english_output=(
            "An aversion to a foundational principle paired with another "
            "behavior."
        ),
    )
    assert not r_fail.passed


def test_run_validators_dispatches_co_n_composition_with_or_without_category():
    """The wiring should invoke the binary_composition validator on a
    CO-N ∘ CO-M source even when grammar_category is missing or wrong."""
    m = _load_module()
    seed = {
        "expression": "CO-9 ∘ CO-7",
        # No grammar_category — exercises the shape-based trigger.
    }
    results = m.run_validators_for_cas_to_english(
        seed=seed,
        english_output=(
            "Something that struck a chord plus something that hit hard."
        ),
    )
    names = [r.name for r in results]
    assert "cas_to_english_binary_composition" in names
    bc = next(r for r in results if r.name == "cas_to_english_binary_composition")
    assert not bc.passed
    assert "operator_misrender_in_co_n_composition" in (bc.reason or "")


# ---------------------------------------------------------------------------
# Group 11: per-stage noetic preservation in rpm_chain
#
# Audit case: seed_rpm_chain_00110 had four ^8 stages but only stageD2
# rendered the ^8 alias ('triggered'); stageW2/P2 dropped the alias and
# said 'cognitive judgment' / 'evaluative judgment'. seed_rpm_chain_00350
# had the same shape with ^6.
# ---------------------------------------------------------------------------


def test_per_stage_noetic_pass_when_each_stage_has_alias():
    m = _load_module()
    src = (
        "let stageA = ^0^P; let stageB = ^8^P_{F2}; "
        "let stageC = ^8^C_{F2}; let stageD = ^8^E_{F2}; "
        "stageA -> stageB"
    )
    eng = (
        "Let stageA name a foundational thought, stageB name something "
        "triggered in the cognitive realm, stageC name a triggered "
        "memory in the cognitive realm, stageD name a triggered "
        "association in the evaluative realm. stageA leads to stageB."
    )
    failed, ok = m._check_per_stage_noetic_preservation(
        source_cas=src, english_output=eng
    )
    assert failed == []
    # Four stages all OK.
    assert {s["name"] for s in ok} == {"stageA", "stageB", "stageC", "stageD"}


def test_per_stage_noetic_fail_audit_case_seed_rpm_chain_00110():
    """The exact audit example: stages 2-4 of a 4-stage ^8 chain drop
    the ^8 alias. Per-stage check should flag stageW2 + stageP2."""
    m = _load_module()
    src = (
        "let stageA0_2_0109 = ^0^P; let stageD2_2_0109 = ^8^P_{F2}; "
        "let stageW2_2_0109 = ^8^C_{F2}; let stageP2_2_0109 = ^8^E_{F2}; "
        "stageW2_2_0109 -> stageP2_2_0109"
    )
    eng = (
        "Let stageA0_2_0109 name a foundational thought, stageD2_2_0109 "
        "name something triggered in the realm of wisdom and insight, "
        "stageW2_2_0109 name a cognitive judgment in the realm of wisdom "
        "and insight, and stageP2_2_0109 name an evaluative judgment in "
        "the realm of wisdom and insight. stageW2_2_0109 leads to "
        "stageP2_2_0109."
    )
    failed, _ok = m._check_per_stage_noetic_preservation(
        source_cas=src, english_output=eng
    )
    failed_names = {f["name"] for f in failed}
    assert "stageW2_2_0109" in failed_names
    assert "stageP2_2_0109" in failed_names
    # And the rpm_chain validator surfaces the same diagnostic.
    r = m.validate_cas_to_english_rpm_chain(
        source_cas=src, english_output=eng
    )
    assert not r.passed
    assert "stage_noetic_dropped" in (r.reason or "")


def test_per_stage_noetic_pass_with_anaphor_continues():
    """Anaphor exception: 'continues the same' / 'this same' permits a
    stage clause to inherit the alias without restating it."""
    m = _load_module()
    src = (
        "let stageA = ^0^P; let stageB = ^6^P_{F2}; "
        "let stageC = ^6^C_{F2}; let stageD = ^6^E_{F2}; "
        "stageA -> stageB"
    )
    eng = (
        "Let stageA name a foundational thought, stageB name breaking "
        "down a principled idea, stageC continues the same operation in "
        "the cognitive realm, and stageD repeats it again in the "
        "evaluative realm. stageA then leads to stageB."
    )
    failed, ok = m._check_per_stage_noetic_preservation(
        source_cas=src, english_output=eng
    )
    assert failed == []
    # stageC and stageD pass via anaphor.
    anaphor_names = {s["name"] for s in ok if s["anaphor"]}
    assert "stageC" in anaphor_names
    assert "stageD" in anaphor_names


def test_per_stage_domain_fail_on_stage_domain_swap():
    """Human review caught stage-level domain swaps that document-level
    coverage missed: a ^5^P stage narrated as evaluative/cognitive still
    mentions the noetic, but the bound domain is wrong."""
    m = _load_module()
    src = (
        "let stageA0_7_0128 = ^0^P; let stageD7_7_0128 = ^5^P_{F7}; "
        "let stageW7_7_0128 = ^5^C_{F7}; let stageP7_7_0128 = ^5^E_{F7}; "
        "stageD7_7_0128 -> stageW7_7_0128"
    )
    eng = (
        "Let stageA0_7_0128 name a foundational thought, "
        "stageD7_7_0128 name who one is shaped by a need for purpose "
        "and meaning in the evaluative arena, stageW7_7_0128 name "
        "cognitive thinking shaped by a need for purpose and meaning in "
        "the evaluative arena, and stageP7_7_0128 name evaluative "
        "judgment shaped by a need for purpose and meaning in the "
        "evaluative arena. stageD7_7_0128 leads to stageW7_7_0128."
    )
    failed, _ok = m._check_per_stage_domain_preservation(
        source_cas=src, english_output=eng
    )
    failed_names = {f["name"] for f in failed}
    assert "stageD7_7_0128" in failed_names
    assert "stageW7_7_0128" in failed_names
    r = m.validate_cas_to_english_rpm_chain(
        source_cas=src, english_output=eng
    )
    assert not r.passed
    assert "stage_domain_drift" in (r.reason or "")


def test_per_stage_domain_pass_when_each_stage_domain_matches():
    m = _load_module()
    src = (
        "let stageA0_7_0128 = ^0^P; let stageD7_7_0128 = ^5^P_{F7}; "
        "let stageW7_7_0128 = ^5^C_{F7}; let stageP7_7_0128 = ^5^E_{F7}; "
        "stageD7_7_0128 -> stageW7_7_0128"
    )
    eng = (
        "Let stageA0_7_0128 name a foundational thought, "
        "stageD7_7_0128 name who one is shaped by purpose in a "
        "foundational frame, stageW7_7_0128 name who one is shaped by "
        "purpose in cognitive thinking, and stageP7_7_0128 name who one "
        "is shaped by purpose in evaluative judgment. stageD7_7_0128 "
        "leads to stageW7_7_0128."
    )
    failed, ok = m._check_per_stage_domain_preservation(
        source_cas=src, english_output=eng
    )
    assert failed == []
    assert {s["name"] for s in ok} == {
        "stageA0_7_0128",
        "stageD7_7_0128",
        "stageW7_7_0128",
        "stageP7_7_0128",
    }


def test_per_stage_clause_window_handles_underscored_digit_names():
    """Stage names like 'stageW2_2_0109' contain digits and underscores;
    clause extraction must match them correctly."""
    m = _load_module()
    eng = (
        "alpha, stageW2_2_0109 name a triggered memory in the cognitive "
        "realm, beta."
    )
    clause = m._stage_clause_window(
        english_output=eng, stage_name="stageW2_2_0109"
    )
    assert clause is not None
    assert "stageW2_2_0109" in clause
    assert "triggered" in clause


def test_per_stage_clause_window_returns_none_for_missing_stage():
    m = _load_module()
    clause = m._stage_clause_window(
        english_output="No stage names here.", stage_name="stageZ_0099"
    )
    assert clause is None


def test_rpm_chain_pass_when_audit_case_fixed():
    """Sanity: if the audit case is rewritten so stageW2/P2 also surface
    'triggered' (or use anaphor), the rpm_chain validator passes."""
    m = _load_module()
    src = (
        "let stageA0_2_0109 = ^0^P; let stageD2_2_0109 = ^8^P_{F2}; "
        "let stageW2_2_0109 = ^8^C_{F2}; let stageP2_2_0109 = ^8^E_{F2}; "
        "stageW2_2_0109 -> stageP2_2_0109"
    )
    eng = (
        "Let stageA0_2_0109 name a foundational thought, stageD2_2_0109 "
        "name something triggered in a foundational frame and in the realm "
        "of wisdom, stageW2_2_0109 "
        "name a triggered cognitive shift in the realm of wisdom, and "
        "stageP2_2_0109 name an evaluative judgment that triggered "
        "follow-on action in the realm of wisdom. stageW2_2_0109 leads "
        "to stageP2_2_0109."
    )
    r = m.validate_cas_to_english_rpm_chain(
        source_cas=src, english_output=eng
    )
    assert r.passed, r.reason
