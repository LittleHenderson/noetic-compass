"""Tests for the Stage 20 Generation Readiness Gate."""

import pytest
import torch

from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.model.generation_readiness_gate import (
    ALLOW,
    BALANCED,
    CAVEAT,
    CONSTRAIN,
    HIGH_PRECISION,
    MAX_COVERAGE_TRIAGE,
    SUPPRESS,
    GenerationReadinessGate,
)


def _clean_meta(batch: int = 1) -> dict[str, torch.Tensor]:
    return {
        "lacunarity": torch.zeros(batch, 5),
        "gap_map": torch.full((batch, 40), 0.05),
        "domain_confidence": torch.full((batch, 4), 0.90),
    }


def test_gate_defaults_to_balanced_allow_for_clean_signals():
    gate = GenerationReadinessGate()

    result = gate(
        lacunarity_scores=torch.full((1, 3), 0.10),
        lacunarity_meta=_clean_meta(),
        inversion_flags=torch.zeros(1, 7),
        rpm_satisfaction=torch.tensor(0.95),
        verification={"accepted": True, "decision_tier": "high"},
    )

    assert result.mode == BALANCED
    assert result.generation_readiness == ALLOW
    assert result.risk_score == 0.0
    assert result.recommended_mode == BALANCED
    assert result.as_dict()["reasons"] == ["all_readiness_signals_within_mode_thresholds"]


def test_gate_constrains_or_suppresses_high_risk_signals():
    gate = GenerationReadinessGate()

    result = gate(
        lacunarity_scores=torch.tensor([[2.4, 2.8]]),
        lacunarity_meta={
            "lacunarity": torch.zeros(1, 5),
            "gap_map": torch.full((1, 40), 0.80),
            "domain_confidence": torch.tensor([[0.20, 0.60, 0.75, 0.80]]),
        },
        inversion_flags=torch.tensor([[0.9, 0.1, 0.8, 0.0, 0.0, 0.7, 0.0]]),
        rpm_satisfaction=torch.tensor(0.30),
        verification={"accepted": True, "decision_tier": "high"},
    )

    assert result.generation_readiness == SUPPRESS
    assert result.risk_score == 1.0
    assert result.recommended_mode == HIGH_PRECISION
    assert "high_lacunarity" in result.reasons
    assert "high_gap_probability" in result.reasons
    assert "low_domain_confidence" in result.reasons
    assert "inversion_flags_present" in result.reasons
    assert "low_rpm_satisfaction" in result.reasons


def test_verification_rejection_is_suppressed_outside_triage():
    gate = GenerationReadinessGate()

    result = gate(
        lacunarity_scores=torch.zeros(1, 1),
        lacunarity_meta=_clean_meta(),
        inversion_flags=torch.zeros(1, 7),
        rpm_satisfaction=torch.tensor(0.95),
        verification={
            "accepted": False,
            "suppression_reasons": ["factor_conflicted"],
        },
        mode=HIGH_PRECISION,
    )

    assert result.generation_readiness == SUPPRESS
    assert result.risk_score == 0.9
    assert "verification_stack_rejected" in result.reasons
    assert "verification:factor_conflicted" in result.reasons


def test_medium_confidence_acceptance_gets_caveat_in_balanced_mode():
    gate = GenerationReadinessGate()

    result = gate(
        lacunarity_scores=torch.zeros(1, 1),
        lacunarity_meta=_clean_meta(),
        inversion_flags=torch.zeros(1, 7),
        rpm_satisfaction=torch.tensor(0.95),
        verification={"accepted": True, "decision_tier": "medium"},
    )

    assert result.generation_readiness == CAVEAT
    assert result.risk_score == 0.25
    assert "verification_tier_medium" in result.reasons


def test_verification_rejection_constrains_in_triage_mode():
    gate = GenerationReadinessGate()

    result = gate(
        lacunarity_scores=torch.zeros(1, 1),
        lacunarity_meta=_clean_meta(),
        inversion_flags=torch.zeros(1, 7),
        rpm_satisfaction=torch.tensor(0.95),
        verification={"accepted": False, "suppression_reasons": ["trace_conflicted"]},
        mode=MAX_COVERAGE_TRIAGE,
    )

    assert result.generation_readiness == CONSTRAIN
    assert result.recommended_mode == HIGH_PRECISION
    assert "verification:trace_conflicted" in result.reasons


def test_unknown_mode_raises():
    gate = GenerationReadinessGate()
    with pytest.raises(ValueError, match="Unknown generation readiness mode"):
        gate(mode="FAST_AND_LOOSE")


def test_cas_native_model_helper_is_opt_in_and_does_not_mutate_outputs():
    model = CASNativeModel(
        CASNativeConfig(
            d_model=32,
            n_layers=2,
            n_heads=4,
            vocab_size=32,
            max_seq_len=32,
            fractal_depth=1,
            num_ethical_propositions=3,
        )
    )
    gate = GenerationReadinessGate()

    outputs = {
        "lacunarity_scores": torch.full((1, 4), 0.10),
        "lacunarity_meta": _clean_meta(),
        "inversion_flags": torch.zeros(1, 7),
        "rpm_satisfaction": torch.tensor(0.95),
    }
    before = outputs["lacunarity_scores"].clone()

    with pytest.raises(RuntimeError, match="generation readiness gate"):
        model.assess_generation_readiness(outputs)

    model.attach_generation_readiness_gate(gate)
    result = model.assess_generation_readiness(
        outputs,
        verification={"accepted": True, "decision_tier": "high"},
    )

    assert result["generation_readiness"] == ALLOW
    assert result["mode"] == BALANCED
    assert torch.equal(outputs["lacunarity_scores"], before)
