from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.services.cas_harness_distributed_audits import (
    create_distributed_audit,
    dispatch_distributed_audit,
    reset_distributed_audits_for_tests,
)
from api.services.cas_harness_fleet_executor import (
    FleetExecutorStateError,
    get_fleet_run,
    heartbeat_worker,
    lease_next_job,
    list_workers,
    mark_stale_workers,
    merge_fleet_evidence,
    prepare_fleet_for_audit,
    register_worker,
    reset_fleet_executor_for_tests,
    submit_job_receipt,
)
from api.services.cas_harness_scale_planner import ScalePlanRequest


def setup_function() -> None:
    reset_fleet_executor_for_tests()
    reset_distributed_audits_for_tests()


def _create_dispatched_audit(
    *,
    parameter_count_b: int = 20,
    num_layers: int = 8,
    minimum_worker_count: int | None = None,
):
    audit = create_distributed_audit(
        ScalePlanRequest(
            model_id=f"customer/open-weight-{parameter_count_b}b",
            parameter_count_b=parameter_count_b,
            num_layers=num_layers,
            precision="int4" if parameter_count_b == 300 else "bf16",
            available_gpu_memory_gb=80,
            minimum_worker_count=minimum_worker_count,
        )
    )
    dispatched = dispatch_distributed_audit(audit.audit_id)
    assert dispatched is not None
    return dispatched


def _register_assignment_worker(assignment, *, model_id: str = "customer/open-weight-20b"):
    return register_worker(
        worker_id=assignment.worker_id,
        model_id=model_id,
        worker_url=f"https://{assignment.worker_id}.workers.internal",
        gpu_type="H100-80GB",
        capacity=1,
        supported_methods=list(assignment.assigned_methods),
    )


def _lease_and_complete(audit_id: str, worker_id: str):
    job = lease_next_job(audit_id=audit_id, worker_id=worker_id)
    assert job is not None
    run = submit_job_receipt(
        audit_id=audit_id,
        job_id=job.job_id,
        worker_id=worker_id,
        lease_token=job.lease_token or "",
        produced_outputs=list(job.expected_outputs),
        evidence_packet_fragment_ref=f"packet-fragment://{job.job_id}",
    )
    assert run is not None
    return job


def test_register_worker_records_capacity_and_heartbeat_contract():
    worker = register_worker(
        worker_id="probe-worker-001",
        model_id="customer/open-weight-300b",
        worker_url="https://probe-worker-001.workers.internal",
        gpu_type="H100-80GB",
        capacity=2,
        supported_methods=[
            "foundation_probe",
            "targeted_ablation",
            "matched_controls",
            "verification_stack",
        ],
    )

    assert worker.worker_id == "probe-worker-001"
    assert worker.status == "active"
    assert worker.gpu_type == "H100-80GB"
    assert worker.capacity == 2
    assert "targeted_ablation" in worker.supported_methods
    assert worker.registered_at
    assert worker.last_heartbeat_at


def test_prepare_fleet_and_lease_jobs_to_registered_workers():
    audit = _create_dispatched_audit(parameter_count_b=20, num_layers=8, minimum_worker_count=4)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)

    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None
    assert run.status == "PREPARED"
    assert len(run.jobs) == audit.plan.recommended_worker_count
    leased = lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)
    saved = get_fleet_run(audit.audit_id)

    assert leased is not None
    assert leased.status == "leased"
    assert leased.assigned_worker_id == assignment.worker_id
    assert leased.lease_token
    assert leased.layer_start <= leased.layer_end
    assert "worker_evidence_manifest" in leased.expected_outputs
    assert saved is not None
    assert saved.status == "LEASING"
    assert saved.to_dict()["leased_jobs"] == 1
    assert saved.to_dict()["completed_fragments"] == 0


def test_stale_heartbeat_detection_marks_workers_and_blocks_gate():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    worker = list_workers()[0]
    worker.last_heartbeat_at = (datetime.now(UTC) - timedelta(seconds=20)).isoformat()
    stale = mark_stale_workers(max_heartbeat_age_seconds=1)
    saved = get_fleet_run(audit.audit_id)

    assert [worker.worker_id for worker in stale] == [assignment.worker_id]
    assert stale[0].status == "stale"
    assert saved is not None
    assert saved.verifier_gate_status == "waiting_for_workers"
    assert saved.to_dict()["stale_workers"] == [assignment.worker_id]

    refreshed = heartbeat_worker(assignment.worker_id)
    assert refreshed is not None
    assert refreshed.status == "active"


def test_receipt_submission_requires_active_lease_and_evidence_packet_fragment_ref():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None
    job = run.jobs[0]

    with pytest.raises(FleetExecutorStateError, match="active lease"):
        submit_job_receipt(
            audit_id=audit.audit_id,
            job_id=job.job_id,
            worker_id=assignment.worker_id,
            lease_token="not-active",
            produced_outputs=list(job.expected_outputs),
            evidence_packet_fragment_ref=f"packet-fragment://{job.job_id}",
        )

    leased = lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)
    assert leased is not None
    with pytest.raises(FleetExecutorStateError, match="evidence_packet_fragment_ref"):
        submit_job_receipt(
            audit_id=audit.audit_id,
            job_id=leased.job_id,
            worker_id=assignment.worker_id,
            lease_token=leased.lease_token or "",
            produced_outputs=list(leased.expected_outputs),
        )


def test_merge_is_blocked_until_every_assigned_job_has_a_receipt():
    audit = _create_dispatched_audit(parameter_count_b=20, num_layers=8, minimum_worker_count=3)
    for assignment in audit.worker_evidence:
        _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    for assignment in audit.worker_evidence[:-1]:
        _lease_and_complete(audit.audit_id, assignment.worker_id)

    with pytest.raises(FleetExecutorStateError, match="every assigned job returns a receipt"):
        merge_fleet_evidence(audit.audit_id)

    saved = get_fleet_run(audit.audit_id)
    assert saved is not None
    assert saved.verifier_gate_status == "waiting_for_receipts"
    assert saved.to_dict()["completed_fragments"] == len(audit.worker_evidence) - 1


def test_300b_fleet_run_requires_all_300_worker_receipts_before_merge_completes():
    audit = _create_dispatched_audit(
        parameter_count_b=300,
        num_layers=160,
        minimum_worker_count=300,
    )
    assert len(audit.worker_evidence) == 300

    for assignment in audit.worker_evidence:
        _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None
    assert len(run.jobs) == 300

    for assignment in audit.worker_evidence[:-1]:
        _lease_and_complete(audit.audit_id, assignment.worker_id)

    with pytest.raises(FleetExecutorStateError, match="every assigned job returns a receipt"):
        merge_fleet_evidence(audit.audit_id)

    partial = get_fleet_run(audit.audit_id)
    assert partial is not None
    assert partial.verifier_gate_status == "waiting_for_receipts"
    assert partial.to_dict()["completed_fragments"] == 299

    _lease_and_complete(audit.audit_id, audit.worker_evidence[-1].worker_id)
    merged = merge_fleet_evidence(audit.audit_id)

    assert merged is not None
    assert merged.status == "COMPLETE"
    assert merged.verifier_gate_status == "ready_for_verifier"
    assert merged.to_dict()["completed_fragments"] == 300
    assert merged.to_dict()["total_jobs"] == 300
    assert merged.merged_packet_trace_id == f"{audit.audit_id}-distributed-merge"
    assert "verifier decision layer" in merged.merge_reason
