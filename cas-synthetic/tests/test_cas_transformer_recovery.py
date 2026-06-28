"""Tests for CAS Transformer recovery parser and fidelity scorer."""

from __future__ import annotations

from dataclasses import replace

from cas_synthetic.generator.cas_transformer import CASTransformerTurnGenerator
from cas_synthetic.validation.cas_transformer_recovery import (
    CASSurfaceRecoveryParserV0,
    RecoveryFidelityScorer,
)


def test_recovery_parser_recovers_renderer_v0_turn_types():
    records = list(CASTransformerTurnGenerator(seed=7).iter_records(10))
    parser = CASSurfaceRecoveryParserV0()

    recovered_types = [
        node.turn_type
        for record in records
        for node in parser.parse_record(record)
    ]

    assert "OPEN" in recovered_types
    assert "ACK" in recovered_types
    assert "CLARIFY" in recovered_types
    assert "EMPATHIZE" in recovered_types
    assert "ANSWER" in recovered_types
    assert "PLAN" in recovered_types
    assert "REPAIR" in recovered_types
    assert "REFUSE" in recovered_types
    assert "REFUSE_CLAIM" in recovered_types


def test_recovery_fidelity_passes_generated_records():
    scorer = RecoveryFidelityScorer()
    records = list(CASTransformerTurnGenerator(seed=11).iter_records(20))
    results = [scorer.score_record(record) for record in records]

    assert all(result.passed for result in results)
    assert all(result.score == 1.0 for result in results)
    assert all(result.critical_exact for result in results)


def test_recovery_fidelity_detects_turn_type_mismatch():
    record = list(CASTransformerTurnGenerator(seed=3).iter_records(2))[1]
    bad_node = replace(record.trace[0], surface_span="Understood.")
    bad_record = replace(record, response="Understood.", trace=[bad_node])

    result = RecoveryFidelityScorer().score_record(bad_record)

    assert not result.passed
    assert not result.critical_exact
    assert result.component_scores["turn_type"] == 0.0
    assert any("turn_type" in failure for failure in result.failures)


def test_recovery_fidelity_detects_ast_expression_drift():
    record = next(CASTransformerTurnGenerator(seed=3).iter_records(1))
    bad_record = replace(record, cas_expression="^0^P_{F1}|A")

    result = RecoveryFidelityScorer().score_record(bad_record)

    assert not result.passed
    assert result.critical_exact
    assert result.component_scores["ast_equivalence"] == 0.0
    assert any("ast_equivalence" in failure for failure in result.failures)


def test_recovery_fidelity_detects_compiler_invalid_critical_failure():
    record = next(CASTransformerTurnGenerator(seed=3).iter_records(1))
    bad_record = replace(record, compiler={"valid": False})

    result = RecoveryFidelityScorer().score_record(bad_record)

    assert not result.passed
    assert not result.critical_exact
    assert any("compiler_valid" in failure for failure in result.failures)


def test_recovery_result_serializes_breakdown():
    record = next(CASTransformerTurnGenerator(seed=5).iter_records(1))
    result = RecoveryFidelityScorer().score_record(record)
    payload = result.to_dict()

    assert payload["score"] == 1.0
    assert payload["component_scores"]["turn_type"] == 1.0
    assert payload["critical_exact"] is True
    assert payload["passed"] is True
    assert payload["recovered_nodes"][0]["turn_type"] == "OPEN"

