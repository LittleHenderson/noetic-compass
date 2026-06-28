from __future__ import annotations

import pytest

from api.services.cas_harness_scale_planner import build_cas_harness_scale_plan


def _assert_assignments_cover_layers(plan) -> None:
    assignments = plan.worker_assignments
    assert assignments[0].layer_start == 1
    assert assignments[-1].layer_end == plan.num_layers
    assert sum(assignment.assigned_layers for assignment in assignments) == plan.num_layers
    for previous, current in zip(assignments, assignments[1:]):
        assert previous.layer_end + 1 == current.layer_start


def test_one_b_model_uses_single_worker_full_internal_plan() -> None:
    plan = build_cas_harness_scale_plan(
        {
            "model_id": "open-weights/one-b",
            "parameter_count_b": 1,
            "num_layers": 24,
            "precision": "bf16",
            "available_gpu_memory_gb": 24,
        }
    )

    assert plan.scale_tier == "single_worker"
    assert plan.recommended_worker_count == 1
    assert plan.target_mode == "FULL_INTERNAL"
    assert plan.memory_estimate.fits_available_gpu_memory is True
    _assert_assignments_cover_layers(plan)


def test_twenty_b_model_is_small_distributed_optional_by_layers() -> None:
    plan = build_cas_harness_scale_plan(
        {
            "model_id": "open-weights/twenty-b",
            "parameter_count_b": 20,
            "num_layers": 48,
            "precision": "fp16",
        }
    )

    assert plan.scale_tier == "small_distributed_optional"
    assert plan.recommended_worker_count == 2
    assert all("layer" in assignment.role for assignment in plan.worker_assignments)
    assert "parameter_start_b" not in plan.to_dict()["worker_assignments"][0]
    _assert_assignments_cover_layers(plan)


def test_hundred_b_model_uses_enterprise_distributed_plan() -> None:
    plan = build_cas_harness_scale_plan(
        {
            "model_id": "open-weights/hundred-b",
            "parameter_count_b": 100,
            "num_layers": 96,
            "precision": "bf16",
            "quantization": "int4",
            "available_gpu_memory_gb": 80,
        }
    )

    assert plan.scale_tier == "enterprise_distributed"
    assert plan.recommended_worker_count >= 8
    assert plan.memory_estimate.quantization == "int4"
    assert plan.memory_estimate.bytes_per_parameter == 0.5
    assert plan.memory_estimate.fits_available_gpu_memory is True
    _assert_assignments_cover_layers(plan)


def test_three_hundred_b_model_is_supported_enterprise_ceiling() -> None:
    plan = build_cas_harness_scale_plan(
        {
            "model_id": "open-weights/three-hundred-b",
            "parameter_count_b": 300,
            "num_layers": 160,
            "precision": "bf16",
        }
    )

    assert plan.scale_tier == "enterprise_distributed"
    assert plan.recommended_worker_count >= 16
    assert plan.num_layers == 160
    _assert_assignments_cover_layers(plan)


def test_missing_layers_falls_back_to_estimated_layer_count() -> None:
    plan = build_cas_harness_scale_plan(
        {
            "model_id": "open-weights/layers-missing",
            "parameter_count_b": 45,
            "precision": "bf16",
        }
    )

    assert plan.layer_count_source == "estimated"
    assert plan.num_layers > 0
    assert any("Layer count was estimated" in limitation for limitation in plan.limitations)
    _assert_assignments_cover_layers(plan)


@pytest.mark.parametrize("target_mode", ["OUTPUT_ONLY", "black-box", "api only"])
def test_output_only_or_black_box_target_modes_are_rejected(target_mode: str) -> None:
    with pytest.raises(ValueError, match="open-weight"):
        build_cas_harness_scale_plan(
            {
                "model_id": "open-weights/not-supported",
                "parameter_count_b": 7,
                "num_layers": 32,
                "precision": "bf16",
                "target_mode": target_mode,
            }
        )


def test_plan_represents_open_weight_internal_audits_only() -> None:
    with pytest.raises(ValueError, match="open-weight"):
        build_cas_harness_scale_plan(
            {
                "model_id": "open-weights/not-supported",
                "parameter_count_b": 7,
                "num_layers": 32,
                "audit_mode": "black_box",
            }
        )

    plan = build_cas_harness_scale_plan(
        {
            "model_id": "open-weights/seven-b",
            "parameter_count_b": 7,
            "num_layers": 32,
            "target_mode": "FULL_INTERNAL",
        }
    )
    serialized = str(plan.to_dict()).lower()

    assert "black-box" not in serialized
    assert "black_box" not in serialized
    assert "output-only" not in serialized
    assert "output_only" not in serialized
    assert "1 harness per 1b parameters" not in serialized
    assert "parameter chunk" not in serialized
