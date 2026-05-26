from __future__ import annotations

import pytest

from api.services.cas_harness_scale_planner import (
    ScalePlanRequest,
    build_scale_plan,
)


def test_one_b_model_uses_single_open_weight_worker():
    plan = build_scale_plan(
        ScalePlanRequest(model_id="EleutherAI/pythia-1b", parameter_count_b=1, num_layers=16)
    )

    assert plan.scale_tier == "single_worker_open_weight"
    assert plan.recommended_worker_count == 1
    assert plan.worker_assignments[0].layer_start == 0
    assert plan.worker_assignments[0].layer_end == 15
    assert "black-box" in " ".join(plan.limitations)


def test_twenty_b_model_is_small_distributed_and_layer_based():
    plan = build_scale_plan(
        ScalePlanRequest(model_id="open-20b", parameter_count_b=20, num_layers=40)
    )

    assert plan.scale_tier == "small_distributed_open_weight"
    assert plan.recommended_worker_count >= 2
    assert plan.worker_assignments[0].shard_id.startswith("layers-")
    assert all("1B" not in assignment.shard_id for assignment in plan.worker_assignments)


def test_hundred_b_model_gets_enterprise_layer_assignments():
    plan = build_scale_plan(
        ScalePlanRequest(
            model_id="customer/open-100b",
            parameter_count_b=100,
            num_layers=120,
            precision="bf16",
            available_gpu_memory_gb=80,
        )
    )

    assert plan.scale_tier == "enterprise_distributed_open_weight"
    assert plan.recommended_worker_count >= 9
    assert plan.worker_assignments[0].layer_start == 0
    assert plan.worker_assignments[-1].layer_end == 119
    assert "single orchestrated Evidence Packet across all workers" in plan.expected_capability
    assert "enterprise GPU scheduling" in " ".join(plan.limitations)


def test_three_hundred_b_model_caps_to_supported_enterprise_plan():
    plan = build_scale_plan(
        ScalePlanRequest(
            model_id="customer/open-300b",
            parameter_count_b=300,
            precision="int4",
            available_gpu_memory_gb=80,
        )
    )

    assert plan.scale_tier == "enterprise_distributed_open_weight"
    assert plan.num_layers == 160
    assert plan.recommended_worker_count >= 25
    assert plan.memory_estimate.total_weight_memory_gb == 150.0
    assert plan.memory_estimate.estimated_memory_per_worker_gb < 80


def test_missing_layers_falls_back_to_reasonable_layer_count():
    plan = build_scale_plan(ScalePlanRequest(model_id="open-70b", parameter_count_b=70))

    assert plan.num_layers == 80
    assert plan.worker_assignments[-1].layer_end == 79


def test_rejects_output_only_or_black_box_style_mode():
    with pytest.raises(ValueError, match="open-weight internal audit modes only"):
        build_scale_plan(
            ScalePlanRequest(
                model_id="closed-api",
                parameter_count_b=10,
                audit_depth="OUTPUT_ONLY",  # type: ignore[arg-type]
            )
        )


def test_rejects_models_above_current_300b_boundary():
    with pytest.raises(ValueError, match="up to 300B"):
        build_scale_plan(ScalePlanRequest(model_id="too-large", parameter_count_b=405))
