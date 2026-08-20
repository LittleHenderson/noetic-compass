"""Schema checks for future distributed open-weight probe workers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.distributed import (
    DistributedAuditPlan,
    OrchestratorMergeSummary,
    ProbeWorkerAssignment,
    WorkerCapability,
    WorkerEvidenceSummary,
)


METHODS = ["foundation_probe", "mode7_attribution"]
OUTPUTS = ["activation_summary", "worker_evidence_packet"]
MODEL_ID = "open-cas/example-distributed"


def assignment(
    assignment_id: str,
    layer_start: int,
    layer_end: int,
    *,
    model_scale: str = "70B",
    worker_status: str = "assigned",
) -> ProbeWorkerAssignment:
    return ProbeWorkerAssignment(
        assignment_id=assignment_id,
        worker_id=f"worker-{assignment_id}",
        model_id=MODEL_ID,
        model_scale=model_scale,
        model_weight_ref="hf://open-cas/example-70b",
        model_weight_hash="sha256:abc123",
        layer_start=layer_start,
        layer_end=layer_end,
        shard_id=f"layers-{layer_start:03d}-{layer_end:03d}",
        assigned_methods=METHODS,
        expected_outputs=OUTPUTS,
        worker_status=worker_status,
    )


def test_distributed_audit_plan_accepts_contiguous_layer_shards():
    plan = DistributedAuditPlan(
        plan_id="audit-300b-contiguous",
        model_id=MODEL_ID,
        model_scale="300B",
        model_weight_ref="hf://open-cas/example-70b",
        model_weight_hash="sha256:abc123",
        total_layers=96,
        expected_outputs=OUTPUTS,
        assignments=[
            assignment("a", 0, 23, model_scale="300B"),
            assignment("b", 24, 47, model_scale="300B"),
            assignment("c", 48, 71, model_scale="300B"),
            assignment("d", 72, 95, model_scale="300B"),
        ],
    )

    assert plan.weight_access == "open_weight"
    assert plan.merge_strategy == "contiguous_layer_shards"
    assert [(a.layer_start, a.layer_end) for a in plan.assignments] == [
        (0, 23),
        (24, 47),
        (48, 71),
        (72, 95),
    ]


@pytest.mark.parametrize("model_scale", ["20B", "70B", "100B", "300B"])
def test_protocol_supports_required_large_open_weight_model_scales(model_scale: str):
    capability = WorkerCapability(
        worker_id=f"worker-{model_scale}",
        supported_model_scales=["20B", "70B", "100B", "300B"],
        supported_methods=METHODS,
        supported_outputs=OUTPUTS,
        max_layers_per_assignment=32,
        max_shards=8,
    )
    plan = DistributedAuditPlan(
        plan_id=f"audit-{model_scale}",
        model_id=MODEL_ID,
        model_scale=model_scale,
        total_layers=4,
        expected_outputs=OUTPUTS,
        assignments=[
            assignment("left", 0, 1, model_scale=model_scale),
            assignment("right", 2, 3, model_scale=model_scale),
        ],
    )

    assert model_scale in capability.supported_model_scales
    assert plan.model_scale == model_scale


def test_distributed_audit_plan_rejects_non_contiguous_ranges():
    with pytest.raises(ValidationError, match="contiguously"):
        DistributedAuditPlan(
            plan_id="audit-gap",
            model_id=MODEL_ID,
            model_scale="70B",
            total_layers=6,
            expected_outputs=OUTPUTS,
            assignments=[
                assignment("first", 0, 1),
                assignment("gap", 3, 5),
            ],
        )


def test_probe_worker_assignment_rejects_invalid_layer_range():
    with pytest.raises(ValidationError, match="layer_end"):
        assignment("bad-range", 8, 7)


def test_probe_worker_assignment_rejects_invalid_worker_status():
    with pytest.raises(ValidationError):
        assignment("bad-status", 0, 3, worker_status="done")


def test_probe_worker_assignment_rejects_parameter_count_chunks():
    payload = assignment("param-chunk", 0, 3).model_dump()
    payload["parameter_start"] = 0
    payload["parameter_end"] = 1_000_000

    with pytest.raises(ValidationError):
        ProbeWorkerAssignment(**payload)


def test_protocol_rejects_black_box_output_only_mode():
    payload = assignment("black-box", 0, 3).model_dump()
    payload["weight_access"] = "black_box_output_only"

    with pytest.raises(ValidationError):
        ProbeWorkerAssignment(**payload)


def test_worker_evidence_summary_and_complete_merge_round_trip():
    summaries = [
        WorkerEvidenceSummary(
            plan_id="audit-merge",
            assignment_id="left",
            worker_id="worker-left",
            model_id=MODEL_ID,
            model_scale="70B",
            model_weight_hash="sha256:abc123",
            layer_start=0,
            layer_end=1,
            shard_id="layers-000-001",
            assigned_methods=METHODS,
            expected_outputs=OUTPUTS,
            produced_outputs=OUTPUTS,
            worker_status="completed",
            evidence_packet_ref="packet://left",
        ),
        WorkerEvidenceSummary(
            plan_id="audit-merge",
            assignment_id="right",
            worker_id="worker-right",
            model_id=MODEL_ID,
            model_scale="70B",
            model_weight_hash="sha256:abc123",
            layer_start=2,
            layer_end=3,
            shard_id="layers-002-003",
            assigned_methods=METHODS,
            expected_outputs=OUTPUTS,
            produced_outputs=OUTPUTS,
            worker_status="completed",
            evidence_packet_ref="packet://right",
        ),
    ]

    merge = OrchestratorMergeSummary(
        plan_id="audit-merge",
        model_id=MODEL_ID,
        model_scale="70B",
        model_weight_hash="sha256:abc123",
        total_layers=4,
        merge_status="complete",
        expected_outputs=OUTPUTS,
        merged_shards=["layers-000-001", "layers-002-003"],
        worker_summaries=summaries,
    )

    restored = OrchestratorMergeSummary.model_validate_json(merge.model_dump_json())
    assert restored.merge_status == "complete"
    assert [summary.shard_id for summary in restored.worker_summaries] == [
        "layers-000-001",
        "layers-002-003",
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"error_message": "failed despite completed"},
        {"missing_outputs": [OUTPUTS[0]]},
        {"produced_outputs": [OUTPUTS[0]]},
        {"produced_outputs": [OUTPUTS[0], OUTPUTS[0]]},
    ],
)
def test_completed_worker_rejects_error_missing_or_inexact_outputs(overrides):
    payload = {
        "plan_id": "audit-merge",
        "assignment_id": "left",
        "worker_id": "worker-left",
        "model_id": MODEL_ID,
        "model_scale": "70B",
        "model_weight_hash": "sha256:abc123",
        "layer_start": 0,
        "layer_end": 1,
        "shard_id": "layers-000-001",
        "assigned_methods": METHODS,
        "expected_outputs": OUTPUTS,
        "produced_outputs": OUTPUTS,
        "worker_status": "completed",
    }
    payload.update(overrides)

    with pytest.raises(ValidationError):
        WorkerEvidenceSummary(**payload)


@pytest.mark.parametrize(
    "merge_overrides",
    [
        {"missing_layers": [3]},
        {"missing_outputs": [OUTPUTS[0]]},
        {"merged_shards": []},
        {"plan_id": "wrong-plan"},
        {"model_weight_hash": "sha256:different"},
        {"expected_outputs": [OUTPUTS[0]]},
    ],
)
def test_complete_merge_rejects_missing_or_identity_contract_mismatch(merge_overrides):
    summary = WorkerEvidenceSummary(
        plan_id="audit-merge",
        assignment_id="only",
        worker_id="worker-only",
        model_id=MODEL_ID,
        model_scale="70B",
        model_weight_hash="sha256:abc123",
        layer_start=0,
        layer_end=3,
        shard_id="layers-000-003",
        assigned_methods=METHODS,
        expected_outputs=OUTPUTS,
        produced_outputs=OUTPUTS,
        worker_status="completed",
    )
    payload = {
        "plan_id": "audit-merge",
        "model_id": MODEL_ID,
        "model_scale": "70B",
        "model_weight_hash": "sha256:abc123",
        "total_layers": 4,
        "merge_status": "complete",
        "expected_outputs": OUTPUTS,
        "merged_shards": ["layers-000-003"],
        "worker_summaries": [summary],
    }
    payload.update(merge_overrides)

    with pytest.raises(ValidationError):
        OrchestratorMergeSummary(**payload)
