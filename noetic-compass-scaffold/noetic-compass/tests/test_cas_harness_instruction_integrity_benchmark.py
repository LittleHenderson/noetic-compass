from __future__ import annotations

from pathlib import Path

import pytest

from api.services.cas_harness_instruction_integrity_benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    InstructionIntegrityBenchmarkError,
    load_instruction_integrity_benchmark_suite,
    run_instruction_integrity_benchmark_suite,
)


SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"
BENCHMARK_FIXTURE = SCENARIOS / "instruction_integrity_benchmark_v0.json"
HELDOUT_FIXTURE = SCENARIOS / "instruction_integrity_heldout_v0.json"


def test_verified_development_benchmark_passes_shadow_gates():
    result = run_instruction_integrity_benchmark_suite(
        load_instruction_integrity_benchmark_suite(BENCHMARK_FIXTURE)
    )

    assert result["schema_version"] == BENCHMARK_SCHEMA_VERSION
    assert result["suite_id"] == "instruction_integrity_shadow_v0_20260610"
    assert result["evaluation_role"] == "development_benchmark"
    assert result["cases_run"] == 15
    assert result["passed"] == 15
    assert result["failed"] == 0
    assert result["metrics"]["case_counts_by_lane"] == {
        "clean": 4,
        "injected": 6,
        "control": 5,
    }
    assert result["metrics"]["injected_recall"] == 1.0
    assert result["metrics"]["benign_false_positive_rate"] == 0.0
    assert result["gates"]["overall_pass"] is True
    assert result["mode"] == "shadow"
    assert result["verdict_effect"] == "none_shadow_only"


def test_frozen_heldout_scaffold_passes_separately_identified_evaluation():
    result = run_instruction_integrity_benchmark_suite(
        load_instruction_integrity_benchmark_suite(HELDOUT_FIXTURE)
    )

    assert result["suite_id"] == "instruction_integrity_heldout_shadow_v0_20260729"
    assert result["evaluation_role"] == "held_out_evaluation"
    assert result["cases_run"] == 12
    assert result["passed"] == 12
    assert result["failed"] == 0
    assert result["metrics"]["case_counts_by_lane"] == {
        "clean": 2,
        "injected": 5,
        "control": 5,
    }
    assert result["metrics"]["injected_recall"] == 1.0
    assert result["metrics"]["benign_false_positive_rate"] == 0.0
    assert result["gates"]["overall_pass"] is True
    assert len(result["suite_sha256"]) == 64


def test_every_fixture_case_enforces_no_action_shadow_contract():
    for fixture in (BENCHMARK_FIXTURE, HELDOUT_FIXTURE):
        result = run_instruction_integrity_benchmark_suite(
            load_instruction_integrity_benchmark_suite(fixture)
        )
        assert all(row["shadow_contract_pass"] for row in result["case_results"])
        assert all(
            row["verdict_effect"] == "none_shadow_only"
            for row in result["case_results"]
        )


def test_benchmark_rejects_untrusted_fixture_shape():
    with pytest.raises(InstructionIntegrityBenchmarkError, match="schema_version"):
        run_instruction_integrity_benchmark_suite(
            {"schema_version": "future", "suite_id": "bad", "cases": []}
        )

    with pytest.raises(InstructionIntegrityBenchmarkError, match="non-empty array"):
        run_instruction_integrity_benchmark_suite(
            {
                "schema_version": BENCHMARK_SCHEMA_VERSION,
                "suite_id": "bad",
                "evaluation_role": "development_benchmark",
                "cases": [],
            }
        )

    with pytest.raises(InstructionIntegrityBenchmarkError, match="evaluation_role"):
        run_instruction_integrity_benchmark_suite(
            {
                "schema_version": BENCHMARK_SCHEMA_VERSION,
                "suite_id": "bad",
                "evaluation_role": "production_gate",
                "cases": [{}],
            }
        )
