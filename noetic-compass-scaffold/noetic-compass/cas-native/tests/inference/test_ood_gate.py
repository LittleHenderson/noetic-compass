"""Tests for the OOD routing gate (Step C of the v0 relevance-failure plan).

The K=9 classifier already detects out-of-distribution input. The gate's job
is to consult that detection and STOP shipping a CAS classification + native
generation when the detector says the input is out-of-distribution. Without
the gate, casual prompts like "what up?" / "this shit is wack" / "Bro I don't
know" produced confidently-wrong CAS classifications during the
2026-05-07 human-relevance audit
(``docs/working/path_B4_human_relevance_failure_2026_05_07.md``).

These tests assert:

* The four canonical failure prompts no longer route to ``CAS_PIPELINE``.
* A clean CAS prompt with high confidence DOES route to ``CAS_PIPELINE``.
* A CAS-detected prompt below the gate's confidence threshold routes to
  ``NEED_CONTEXT`` rather than ship a low-confidence classification.
* ``chat.py`` actually calls the gate from ``_predict_and_show`` (source-grep
  pin so future edits don't silently regress the routing).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cas_native.inference.ood_gate import (
    GateResult,
    OODGate,
    RouteDecision,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_OOD_NOTE = (
    "no CAS signal detected in free-form input; predicting on the "
    "raw text. The K=9 baseline tends to collapse to its prior on "
    "out-of-distribution colloquial English (documented modality "
    "limitation)."
)


def _ood_k9_result(**extra: object) -> dict[str, object]:
    """K=9 result shape that mimics the OOD-detected branch in chat.py.

    The detector wrote the sentinel into ``notes``; per-head confidences may
    or may not be present. The gate must trigger on the sentinel regardless
    of confidence.
    """
    base: dict[str, object] = {
        "notes": [_OOD_NOTE],
        "noetic": 2,
        "domain": "E",
        "drive": "F5",
        "registers": ["E"],
        # Confidences are typical-looking; the gate must NOT use them to
        # override the OOD-sentinel verdict.
        "noetic_confidence": 0.71,
        "domain_confidence": 0.65,
        "drive_confidence": 0.58,
    }
    base.update(extra)
    return base


def _confident_cas_k9_result(confidence: float = 0.85) -> dict[str, object]:
    """K=9 result for a clean, in-distribution CAS prompt with high confidence."""
    return {
        # No notes field, no OOD sentinel anywhere.
        "noetic": 3,
        "domain": "P",
        "drive": "F2",
        "registers": ["A"],
        "noetic_confidence": confidence,
        "domain_confidence": confidence,
        "drive_confidence": confidence,
        "register_confidence": confidence,
    }


def _chat_source() -> str:
    """Return chat.py source for source-grep tests."""
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    assert chat_path.exists(), f"chat.py not found at {chat_path}"
    return chat_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Required spec tests — the four canonical prompts must NOT ship CAS
# ---------------------------------------------------------------------------


def test_what_up_does_not_route_to_cas_pipeline():
    gate = OODGate()
    result = gate.route("what up?", _ood_k9_result())
    assert isinstance(result, GateResult)
    assert result.decision is not RouteDecision.CAS_PIPELINE
    # "what up?" is short + casual -> conversational fallback.
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK
    assert result.canned_response  # canned plain-English reply present
    assert "CAS" not in (result.canned_response or "") or "CAS structure" in (
        result.canned_response or ""
    )


def test_this_shit_is_wack_does_not_route_to_cas_pipeline():
    gate = OODGate()
    # The audit prompt verbatim was "This shit is wack as fuck."
    result = gate.route(
        "This shit is wack as fuck.", _ood_k9_result()
    )
    assert result.decision is not RouteDecision.CAS_PIPELINE
    # 6 words, multiple casual hits -> conversational fallback.
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK
    assert result.canned_response


def test_bro_i_dont_know_does_not_route_to_cas_pipeline():
    gate = OODGate()
    result = gate.route("Bro I don't know", _ood_k9_result())
    assert result.decision is not RouteDecision.CAS_PIPELINE
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK
    assert result.canned_response


# ---------------------------------------------------------------------------
# Required spec tests — valid CAS prompt regression + low-confidence branch
# ---------------------------------------------------------------------------


def test_valid_cas_prompt_routes_to_pipeline():
    """Regression: a confident, in-distribution CAS prompt must still flow."""
    gate = OODGate()
    prompt = (
        "I keep practicing the same scale every morning before I do anything else."
    )
    result = gate.route(prompt, _confident_cas_k9_result(confidence=0.85))
    assert result.decision is RouteDecision.CAS_PIPELINE
    assert result.canned_response is None


def test_low_confidence_routes_to_need_context():
    """K=9 ran (no OOD sentinel) but confidence is too low -> NEED_CONTEXT."""
    gate = OODGate(confidence_threshold=0.4)
    prompt = (
        "I noticed something unusual in my response to that situation today."
    )
    # All head confidences are below threshold.
    low_conf = {
        "noetic": 1,
        "domain": "C",
        "drive": "F4",
        "noetic_confidence": 0.21,
        "domain_confidence": 0.18,
        "drive_confidence": 0.30,
        "register_confidence": 0.25,
    }
    result = gate.route(prompt, low_conf)
    assert result.decision is RouteDecision.NEED_CONTEXT
    assert result.canned_response


# ---------------------------------------------------------------------------
# Source-grep wiring pins on chat.py
# ---------------------------------------------------------------------------


def test_chat_imports_ood_gate():
    """chat.py must import the gate; otherwise routing won't fire."""
    src = _chat_source()
    assert "from cas_native.inference.ood_gate import" in src, (
        "chat.py must import the OOD gate module"
    )
    assert "OODGate" in src
    assert "RouteDecision" in src


def test_predict_and_show_calls_ood_gate():
    """The typed-input prediction path must call OODGate.route(...)."""
    src = _chat_source()
    fn_start = src.index("def _predict_and_show(")
    # Read a generous slice — the function is ~150 lines after our edit.
    fn_body = src[fn_start: fn_start + 8000]
    assert ".route(" in fn_body, (
        "_predict_and_show must call <gate>.route(prompt, k9_result) before "
        "invoking the K=9 -> native pipeline"
    )
    assert "RouteDecision.CAS_PIPELINE" in fn_body, (
        "_predict_and_show must branch on RouteDecision.CAS_PIPELINE"
    )
    # The skip-native branch must short-circuit before native generation.
    # We assert the gate-check appears BEFORE the generate_reply call.
    gate_pos = fn_body.find(".route(")
    gen_pos = fn_body.find("generate_reply(")
    assert gate_pos != -1 and gen_pos != -1, (
        "expected both gate.route(...) and generate_reply(...) in the "
        "function body"
    )
    assert gate_pos < gen_pos, (
        "gate must be consulted BEFORE generate_reply is invoked"
    )


# ---------------------------------------------------------------------------
# Robustness coverage (small, kept tight to spec)
# ---------------------------------------------------------------------------


def test_long_non_casual_ood_prompt_routes_to_clarification():
    """Long free-form input with no casual hits but OOD-detected goes to
    CLARIFICATION rather than CONVERSATIONAL_FALLBACK."""
    gate = OODGate()
    long_prompt = (
        "Could you explain in detail the relationship between the proton's "
        "magnetic moment and the deeper foundations of quantum chromodynamics "
        "as it pertains to lattice simulations of low-energy hadron physics."
    )
    result = gate.route(long_prompt, _ood_k9_result())
    assert result.decision is RouteDecision.CLARIFICATION
    assert result.canned_response


def test_ood_sentinel_in_nested_field_still_triggers():
    """Defensive: sentinel may appear in note (singular), system_notes, etc."""
    gate = OODGate()
    for field in ("note", "ood_note", "system_notes"):
        result = gate.route(
            "yo",
            {field: _OOD_NOTE},
        )
        assert result.decision is not RouteDecision.CAS_PIPELINE, (
            f"sentinel in {field!r} must still trigger the gate"
        )


def test_threshold_is_configurable():
    gate = OODGate(confidence_threshold=0.9)
    # With threshold 0.9, even 0.85 confidence is too low.
    result = gate.route(
        "A reasonable prompt about practicing scales every morning.",
        _confident_cas_k9_result(confidence=0.85),
    )
    assert result.decision is RouteDecision.NEED_CONTEXT


def test_threshold_validation():
    with pytest.raises(ValueError):
        OODGate(confidence_threshold=-0.1)
    with pytest.raises(ValueError):
        OODGate(confidence_threshold=1.1)


def test_route_rejects_non_string_prompt():
    gate = OODGate()
    with pytest.raises(TypeError):
        gate.route(123, _ood_k9_result())  # type: ignore[arg-type]


def test_empty_prompt_falls_back_when_ood():
    gate = OODGate()
    result = gate.route("", _ood_k9_result())
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK


def test_no_confidence_data_does_not_block_pipeline():
    """If neither sentinel nor confidence info exists, route to pipeline.

    This preserves backward compatibility for predictors that do not yet
    expose per-head confidences in the result dict.
    """
    gate = OODGate()
    bare = {"noetic": 2, "domain": "P", "drive": "F2"}
    result = gate.route("an in-distribution-looking prompt", bare)
    assert result.decision is RouteDecision.CAS_PIPELINE


# ---------------------------------------------------------------------------
# CAS surface-token pre-filter (Step E calibration)
#
# Pre-calibration audit (b4_product_routing_eval) showed valid_cas_notation
# and fractal_composition at 100% fail because the gate consulted the OOD
# verdict blindly and blocked the pipeline for prompts that explicitly
# carried CAS notation. The pre-filter overrides the OOD verdict when the
# prompt contains unambiguous CAS surface tokens.
#
# Coverage requirements (from the Step E spec): seven categories, each
# tested with at least one prompt that should bypass and route to
# CAS_PIPELINE. The previous corpus / regex sketches forgot meta-logic
# constructors and Cognitive Fractal angle-bracket sequences; both are
# covered explicitly here.
# ---------------------------------------------------------------------------


def test_cas_surface_state_literal_bypasses_ood():
    """Category 1: state literal ``^N^D``. ``^3^P`` must bypass the OOD
    verdict and route to CAS_PIPELINE."""
    gate = OODGate()
    # OOD-detector says no signal, but prompt clearly contains ^3^P.
    result = gate.route("classify ^3^P_{F7}|A please", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE
    assert "cas_surface" in result.reason


def test_cas_surface_drive_subscript_bypasses_ood():
    """Category 2: drive subscripts ``F1``..``F7`` and ``_{F_k}``."""
    gate = OODGate()
    result = gate.route("does _{F2} entrain ^7?", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE
    assert "cas_surface" in result.reason


def test_cas_surface_single_register_bypasses_ood():
    """Category 3a: single register tag ``|A`` bypasses the OOD verdict."""
    gate = OODGate()
    result = gate.route("explain |A vs |f register", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_multi_register_unicode_bypasses_ood():
    """Category 3b: multi-register set notation ``|⟨A,f,T⟩`` bypasses."""
    gate = OODGate()
    result = gate.route("describe ^3^P|⟨A,f,T⟩ architecture", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_multi_register_ascii_bypasses_ood():
    """Category 3b ASCII fallback: ``|<A,f,T>`` bypasses the OOD verdict."""
    gate = OODGate()
    result = gate.route("register set notation: ^3^P|<A,f,T>", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_named_omega_bypasses_ood():
    """Category 4: named emergent ``Ω_focused_refusal`` / ``Omega_X``."""
    gate = OODGate()
    result_unicode = gate.route("define Ω_focused_refusal", _ood_k9_result())
    assert result_unicode.decision is RouteDecision.CAS_PIPELINE
    result_ascii = gate.route("define Omega_focused_refusal", _ood_k9_result())
    assert result_ascii.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_theta_recipe_bypasses_ood():
    """Category 5: production recipe ``Θ(Ω_X) = ...`` and ASCII
    ``Theta(Omega_X) = ...``. Both forms must bypass the OOD verdict.

    This is the v76_production failure-mode prompt from the audit fixture."""
    gate = OODGate()
    unicode_recipe = (
        "Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A "
        "+ 1.04*^1^P_{F1}|A → Ω_focused_refusal"
    )
    result_u = gate.route(unicode_recipe, _ood_k9_result())
    assert result_u.decision is RouteDecision.CAS_PIPELINE

    ascii_recipe = (
        "Theta(Omega_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A "
        "+ 1.04*^1^P_{F1}|A -> Omega_focused_refusal"
    )
    result_a = gate.route(ascii_recipe, _ood_k9_result())
    assert result_a.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_coefficient_state_bypasses_ood():
    """Category 5c: coefficient-times-state ``0.53*^7^P`` is a recipe
    fragment and must trigger the bypass even outside a full Θ wrapper."""
    gate = OODGate()
    result = gate.route("the term 0.53*^7^P|T is a recipe fragment", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_meta_logic_noetic_cluster_bypasses_ood():
    """Category 6: meta-logic / set constructor ``NoeticCluster{...}``
    bypasses the OOD verdict.

    This category was FORGOTTEN by the v0 corpus and earlier regex
    sketches; covered explicitly per Step E spec."""
    gate = OODGate()
    result = gate.route(
        "let cluster = NoeticCluster{^2, ^3, ^4}", _ood_k9_result()
    )
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_meta_logic_state_set_bypasses_ood():
    """Category 6: ``StateSet{...}`` constructor bypasses."""
    gate = OODGate()
    result = gate.route("StateSet{P0, P1, P2, P3} is a domain slice", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_meta_logic_relation_cluster_bypasses_ood():
    """Category 6: ``RelationCluster{...}`` constructor bypasses."""
    gate = OODGate()
    result = gate.route("RelationCluster{(^2, ^3), (^5, ^6)}", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_meta_logic_cover_of_validator_bypasses_ood():
    """Category 6: ``CoverOf(...)`` validator bypasses."""
    gate = OODGate()
    result = gate.route("verify CoverOf(NoeticCluster{...}, target)", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_meta_logic_partition_of_validator_bypasses_ood():
    """Category 6: ``PartitionOf(...)`` validator bypasses."""
    gate = OODGate()
    result = gate.route("PartitionOf(StateSet{...}, blocks)", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_let_binding_bypasses_ood():
    """Category 6: ``let X = ^3^P`` binding bypasses."""
    gate = OODGate()
    result = gate.route("let X = ^3^P_{F2}|A", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_membership_relation_bypasses_ood():
    """Category 6: membership relation with ∈ glyph + constructor bypasses.

    ``^3^P ∈ NoeticCluster{...}`` carries multiple CAS surface tokens; any
    one is sufficient. ∈ alone is in the operator-glyph regex."""
    gate = OODGate()
    result = gate.route("^3^P ∈ NoeticCluster{^2, ^3, ^4}", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_fractal_unicode_sequence_bypasses_ood():
    """Category 7a: Cognitive Fractal angle-bracket sequence ``⟨2:3:6⟩``.

    This category was FORGOTTEN by the v0 corpus; covered per Step E spec."""
    gate = OODGate()
    result = gate.route("the fractal ⟨2:3:6⟩ describes a path", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_fractal_ascii_sequence_bypasses_ood():
    """Category 7b: ASCII fallback ``<k1:k2:k3>`` of the fractal sequence."""
    gate = OODGate()
    result = gate.route("encoded as <2:3:6> in ASCII", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_fractal_dot_chain_bypasses_ood():
    """Category 7c: X.Y.Z fractal dot-chain ``^5.^7.^2`` bypasses."""
    gate = OODGate()
    result = gate.route("compute ^5.^7.^2 as a fractal", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_rpm_chain_bypasses_ood():
    """Category 6e: RPM capability-pathway chain ``A0 -> D2 -> W2 -> P2``."""
    gate = OODGate()
    result = gate.route("RPM-chain: A0 -> D2 -> W2 -> P2", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_chain_entails_relation_bypasses_ood():
    """Category 6: ``ChainEntails(...)`` relation bypasses."""
    gate = OODGate()
    result = gate.route("ChainEntails(^8^P_{F2}, ^9^P_{F2})", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


def test_cas_surface_compose_glyph_bypasses_ood():
    """Category 4: ∘ composition glyph bypasses."""
    gate = OODGate()
    result = gate.route("compose ^8 ∘ ^9 ∘ ^4", _ood_k9_result())
    assert result.decision is RouteDecision.CAS_PIPELINE


# ---------------------------------------------------------------------------
# Regression checks — casual prompts must STILL route to fallback / clarification
# ---------------------------------------------------------------------------
#
# The pre-filter must not flip casual prompts toward CAS_PIPELINE. These
# prompts contain no CAS surface tokens; pre-filter must return False and
# the existing OOD-sentinel logic must keep routing them to fallback /
# clarification.


def test_what_up_regression_still_fallback_with_prefilter():
    gate = OODGate()
    result = gate.route("what up", _ood_k9_result())
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK


def test_wack_regression_still_fallback_with_prefilter():
    gate = OODGate()
    result = gate.route("this shit is wack", _ood_k9_result())
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK


def test_bro_idk_regression_still_fallback_with_prefilter():
    gate = OODGate()
    result = gate.route("Bro I don't know", _ood_k9_result())
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK


def test_long_non_casual_ood_regression_still_clarification():
    """Long free-form English with no CAS surface tokens still goes to
    CLARIFICATION even with the pre-filter on."""
    gate = OODGate()
    long_prompt = (
        "Could you explain in detail the relationship between the proton's "
        "magnetic moment and the deeper foundations of quantum chromodynamics."
    )
    result = gate.route(long_prompt, _ood_k9_result())
    assert result.decision is RouteDecision.CLARIFICATION


# ---------------------------------------------------------------------------
# cas_surface_bypass=False — the pure OOD-only logic path
# ---------------------------------------------------------------------------


def test_cas_surface_bypass_disabled_consults_ood():
    """With ``cas_surface_bypass=False`` the gate ignores CAS surface tokens
    and consults the OOD signal as before. This is the regression-mode
    setting for tests that need to exercise OOD-only logic."""
    gate = OODGate(cas_surface_bypass=False)
    # The prompt contains ^3^P (would normally bypass) but the OOD note
    # is present. With bypass off, the OOD verdict wins.
    result = gate.route("classify ^3^P_{F7}|A", _ood_k9_result())
    assert result.decision is not RouteDecision.CAS_PIPELINE
    assert result.decision in (
        RouteDecision.CONVERSATIONAL_FALLBACK,
        RouteDecision.CLARIFICATION,
    )


def test_cas_surface_bypass_disabled_low_confidence_routes_to_need_context():
    """With bypass off, the confidence floor still applies."""
    gate = OODGate(cas_surface_bypass=False, confidence_threshold=0.4)
    low_conf = {
        "noetic": 1,
        "domain": "C",
        "noetic_confidence": 0.21,
        "domain_confidence": 0.18,
    }
    # CAS surface present but bypass disabled and confidence under threshold.
    result = gate.route("classify ^3^P_{F2}|A", low_conf)
    assert result.decision is RouteDecision.NEED_CONTEXT


# ---------------------------------------------------------------------------
# Direct unit tests on the static helper
# ---------------------------------------------------------------------------


def test_has_cas_surface_tokens_state_literal():
    assert OODGate._has_cas_surface_tokens("classify ^3^P here")
    assert OODGate._has_cas_surface_tokens("just ^7")


def test_has_cas_surface_tokens_named_omega():
    assert OODGate._has_cas_surface_tokens("Ω_cadence is the target")
    assert OODGate._has_cas_surface_tokens("Omega_presence is named")


def test_has_cas_surface_tokens_theta_recipe():
    assert OODGate._has_cas_surface_tokens("Θ(Ω_X) = ...")
    assert OODGate._has_cas_surface_tokens("Theta(Omega_X) = ...")


def test_has_cas_surface_tokens_meta_logic_constructors():
    # The seven set constructors and validators required by spec.
    assert OODGate._has_cas_surface_tokens("NoeticCluster{^1, ^2}")
    assert OODGate._has_cas_surface_tokens("StateSet{...}")
    assert OODGate._has_cas_surface_tokens("RelationCluster{(^2, ^3)}")
    assert OODGate._has_cas_surface_tokens("Tuple(^1, ^2)")
    assert OODGate._has_cas_surface_tokens("Coordinate(0, 1)")
    assert OODGate._has_cas_surface_tokens("Product(P, C)")
    assert OODGate._has_cas_surface_tokens("CoverOf(X, Y)")
    assert OODGate._has_cas_surface_tokens("PartitionOf(S, B)")


def test_has_cas_surface_tokens_fractal_sequences():
    assert OODGate._has_cas_surface_tokens("⟨2:3:6⟩")
    assert OODGate._has_cas_surface_tokens("⟨1:2:3:4:5⟩")
    assert OODGate._has_cas_surface_tokens("<2:3:6>")
    assert OODGate._has_cas_surface_tokens("compute ^5.^7.^2 chain")


def test_has_cas_surface_tokens_negative_cases():
    """Plain colloquial English must NOT trip the pre-filter."""
    assert not OODGate._has_cas_surface_tokens("what up")
    assert not OODGate._has_cas_surface_tokens("hey")
    assert not OODGate._has_cas_surface_tokens("Bro I don't know")
    assert not OODGate._has_cas_surface_tokens("this shit is wack")
    assert not OODGate._has_cas_surface_tokens("explain CAS simply")
    assert not OODGate._has_cas_surface_tokens(
        "I keep practicing the same scale every morning"
    )
    assert not OODGate._has_cas_surface_tokens(
        "Could you explain quantum chromodynamics."
    )
    assert not OODGate._has_cas_surface_tokens("")
    assert not OODGate._has_cas_surface_tokens("    ")


def test_has_cas_surface_tokens_avoids_false_positive_on_F8():
    """``F8`` is out-of-range (only F1-F7 exist) but still names a drive in
    casual context. Ensure F8 alone does NOT trigger the pre-filter — the
    drive-subscript pattern is bounded to F1..F7. The user-facing fixture
    item ``"is F8 a real drive"`` is in the invalid_cas bucket where either
    pipeline OR clarification is acceptable, so we choose conservative."""
    assert not OODGate._has_cas_surface_tokens("is F8 a real drive")
