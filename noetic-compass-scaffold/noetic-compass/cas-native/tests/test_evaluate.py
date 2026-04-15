"""Semantic tests for the CAS-Native evaluator."""

import pytest
import torch

from cas_native.evaluation.evaluate import (
    CASEvaluator,
    build_drive_scores,
    build_pathway_scores,
    compute_domain_scores,
    compute_engine_assessment,
    compute_per_operator_scores,
    normalize_state_vector,
)


cas_engine = pytest.importorskip("cas_engine")


class _DummyModel(torch.nn.Module):
    def __init__(self, cognitive_state: torch.Tensor, rpm_satisfaction: float):
        super().__init__()
        self._dummy = torch.nn.Parameter(torch.zeros(1))
        self._cognitive_state = cognitive_state
        self._rpm_satisfaction = rpm_satisfaction

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None):
        batch, seq_len = input_ids.shape
        logits = torch.zeros(batch, seq_len, 8, device=input_ids.device)
        inversion_flags = torch.zeros(batch, 7, device=input_ids.device)
        topos_truth_values = torch.full((batch, 3, 3), 1.0 / 3.0, device=input_ids.device)
        return {
            "logits": logits,
            "cognitive_state": self._cognitive_state.to(input_ids.device),
            "rpm_satisfaction": torch.tensor(self._rpm_satisfaction, device=input_ids.device),
            "inversion_flags": inversion_flags,
            "topos_truth_values": topos_truth_values,
        }


class TestCASEvaluator:

    def test_compute_engine_assessment_matches_direct_rust_engine(self):
        """The evaluator helper should match a direct PyO3 CAS engine call."""
        state = torch.full((40,), 1.0 / 40.0)
        rpm_satisfaction = 0.62

        assessment = compute_engine_assessment(state, rpm_satisfaction)

        operator_scores = compute_per_operator_scores(state)
        operator_list = [operator_scores[f"CO-{i}"] for i in range(10)]
        domain_scores = compute_domain_scores(state)
        drive_scores = build_drive_scores(rpm_satisfaction)
        pathway_scores = build_pathway_scores(rpm_satisfaction)
        state_vector = cas_engine.CognitiveStateVector(normalize_state_vector(state))
        inversion_scan = cas_engine.InversionScanner.scan(
            operator_scores=operator_list,
            drive_scores=drive_scores,
            state_vector=state_vector,
            domain_averages=domain_scores,
            pathway_scores=pathway_scores,
        )
        social_proxy = 0.5 * inversion_scan["resistance_score"] + 0.5 * rpm_satisfaction
        direct = cas_engine.compute_nccs(
            operator_scores=operator_list,
            domain_averages=domain_scores,
            drive_scores=drive_scores,
            rpm_completeness=rpm_satisfaction,
            pathway_rpm_completeness=rpm_satisfaction,
            bias_flag_count=0,
            inversion_axis_scores=inversion_scan["axis_scores"],
            stealth_resistance=inversion_scan["stealth_resistance"],
            compound_severity=inversion_scan["compound_severity"],
            manipulation_resistance=social_proxy,
            overton_drift_resistance=social_proxy,
        )

        assert assessment["nccs"]["composite"] == pytest.approx(direct["composite"])
        assert assessment["nccs"]["certification"] == direct["certification"]

    def test_evaluator_batch_uses_rust_engine_outputs(self):
        """Batch evaluation should expose the same NCCS computed by the Rust engine."""
        cognitive_state = torch.full((1, 5, 40), 1.0 / 40.0)
        model = _DummyModel(cognitive_state=cognitive_state, rpm_satisfaction=0.55)
        evaluator = CASEvaluator(model)
        batch = {
            "input_ids": torch.ones(1, 5, dtype=torch.long),
            "attention_mask": torch.ones(1, 5, dtype=torch.long),
        }

        report = evaluator.evaluate_batch([batch])
        expected = compute_engine_assessment(cognitive_state[0].mean(dim=0), 0.55)

        assert report["nccs"]["mean"] == pytest.approx(expected["nccs"]["composite"])
        assert report["domain_coherence_index"] == pytest.approx(expected["dci"])
