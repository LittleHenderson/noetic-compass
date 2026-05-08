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


def test_wave2_5_iterate_rejects_recipe_with_dropped_coefficients():
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

    def bad_model(system: str, user: str) -> tuple[str, int, int]:
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
    assert counts == {"accepted": 0, "rejected": 1, "errored": 0}
    assert "missing coefficients" in rejected[0]["reason"] or \
           "missing named Ω target stems" in rejected[0]["reason"]


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
