from __future__ import annotations

import pytest

from api.services.cas_harness_scale_planner import (
    ScalePlanRequest,
    build_scale_plan,
    scale_validation_status,
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


def test_three_hundred_b_model_can_request_larger_tensor_shard_fleet():
    plan = build_scale_plan(
        ScalePlanRequest(
            model_id="customer/open-300b",
            parameter_count_b=300,
            num_layers=160,
            precision="int4",
            available_gpu_memory_gb=80,
            minimum_worker_count=300,
        )
    )

    assert plan.recommended_worker_count == 300
    assert len(plan.worker_assignments) == 300
    assert plan.worker_assignments[0].shard_id.startswith("layer-")
    assert plan.worker_assignments[0].layer_start == plan.worker_assignments[0].layer_end
    assert plan.worker_assignments[-1].layer_end == 159
    assert {assignment.layer_start for assignment in plan.worker_assignments} == set(range(160))


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


def test_models_up_to_300b_are_engineered_not_validated():
    # 20B-300B is the engineered (architecture-validated, not size-validated) band.
    plan = build_scale_plan(ScalePlanRequest(model_id="customer/open-100b", parameter_count_b=100))

    assert plan.validation_status == "ENGINEERED_NOT_VALIDATED"
    assert "architecture-validated, not size-validated" in plan.validation_notice


def test_at_or_below_20b_is_empirically_validated():
    plan = build_scale_plan(ScalePlanRequest(model_id="open-20b", parameter_count_b=20, num_layers=40))

    assert plan.validation_status == "EMPIRICALLY_VALIDATED"
    assert "empirically validated" in plan.validation_notice.lower()


def test_405b_without_frontier_ack_is_refused():
    # 300B-4T is the experimental frontier lane: a plan must not be produced unless
    # the caller explicitly accepts experimental-risk terms.
    with pytest.raises(ValueError, match="experimental frontier-scale lane"):
        build_scale_plan(ScalePlanRequest(model_id="frontier/open-405b", parameter_count_b=405))


def test_405b_with_frontier_ack_plans_experimental_not_validated_lane():
    plan = build_scale_plan(
        ScalePlanRequest(
            model_id="frontier/open-405b",
            parameter_count_b=405,
            accept_experimental_frontier=True,
        )
    )

    assert plan.scale_tier == "frontier_experimental_open_weight"
    assert plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED"
    # The honest frontier waiver must travel with the plan.
    notice = plan.validation_notice.lower()
    assert "experimental_not_validated" in notice
    assert "customer risk" in notice
    assert any("EXPERIMENTAL_NOT_VALIDATED" in item for item in plan.limitations)
    # A frontier plan still produces real layer/shard worker assignments.
    assert plan.recommended_worker_count >= 16
    assert plan.worker_assignments[0].layer_start == 0


def test_one_trillion_with_frontier_ack_is_experimental_not_validated():
    plan = build_scale_plan(
        ScalePlanRequest(
            model_id="frontier/open-1t",
            parameter_count_b=1000,
            accept_experimental_frontier=True,
        )
    )

    assert plan.scale_tier == "frontier_experimental_open_weight"
    assert plan.validation_status == "EXPERIMENTAL_NOT_VALIDATED"


def test_above_4t_is_hard_refused_even_with_frontier_ack():
    # >4T is refused outright; the experimental acknowledgement cannot unlock it.
    with pytest.raises(ValueError, match="up to 4T"):
        build_scale_plan(
            ScalePlanRequest(
                model_id="frontier/too-large",
                parameter_count_b=5000,
                accept_experimental_frontier=True,
            )
        )


def test_validation_ladder_is_the_single_source_of_truth():
    assert scale_validation_status(20) == "EMPIRICALLY_VALIDATED"
    assert scale_validation_status(20.0001) == "ENGINEERED_NOT_VALIDATED"
    assert scale_validation_status(300) == "ENGINEERED_NOT_VALIDATED"
    assert scale_validation_status(300.0001) == "EXPERIMENTAL_NOT_VALIDATED"
    assert scale_validation_status(4000) == "EXPERIMENTAL_NOT_VALIDATED"
