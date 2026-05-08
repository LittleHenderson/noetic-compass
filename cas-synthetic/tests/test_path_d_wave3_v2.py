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
        return ("Principled aversion to a foundational idea.", 100, 20)

    counts = m.wave2_5_iterate(
        seeds,
        model_callable=good_model,
        model_name="test-model",
        cost_per_in_token=0.0,
        cost_per_out_token=0.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts == {"accepted": 1, "rejected": 0, "errored": 0}
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


def test_wave2_5_iterate_rejects_fractal_with_count_misread():
    m = _load_module()
    seeds = [
        {
            "seed_id": "seed_fractal_x",
            "expression": "Φ⟨9:4:7⟩",
            "grammar_category": "fractal_sequence",
        },
    ]
    accepted: list[Any] = []
    rejected: list[dict[str, Any]] = []

    def bad_model(system: str, user: str) -> tuple[str, int, int]:
        return ("A sequence of 3 stages with operations 9, 4, and 7.", 100, 10)

    counts = m.wave2_5_iterate(
        seeds,
        model_callable=bad_model,
        model_name="test-model",
        cost_per_in_token=0.0,
        cost_per_out_token=0.0,
        accept_writer=accepted.append,
        reject_writer=rejected.append,
    )
    assert counts["rejected"] == 1


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
        return ("Principled aversion to a foundational principle.", 100, 20)

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


def test_tokenize_for_jaccard_separates_operators():
    m = _load_module()
    toks = m._tokenize_for_jaccard("^3^P|A + ^4^P|f")
    assert "+" in toks
    assert "^3^P|A" in toks
    assert "^4^P|f" in toks
