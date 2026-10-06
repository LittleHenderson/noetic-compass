from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json

import pytest

from api.services.cas_harness_distributed_audits import (
    create_distributed_audit,
    dispatch_distributed_audit,
    reset_distributed_audits_for_tests,
)
from api.services.cas_harness_fleet_executor import (
    ActiveFleetJobLease,
    FleetExecutorStateError,
    build_evidence_fragment_ref,
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
    validate_active_fleet_job_lease,
)
from api.services.cas_harness_scale_planner import ScalePlanRequest
from api.services.cas_harness_model_provenance import (
    ModelProvenanceManifest,
    WeightFileRef,
)


MODEL_REVISION = "a" * 40
MODEL_ARTIFACT_MANIFEST_PATH = "/workspace/model-artifacts.json"
MODEL_ARTIFACT_MANIFEST_SHA256 = "b" * 64


def setup_function() -> None:
    reset_fleet_executor_for_tests()
    reset_distributed_audits_for_tests()


def _create_dispatched_audit(
    *,
    parameter_count_b: int = 20,
    num_layers: int = 8,
    minimum_worker_count: int | None = None,
    with_provenance: bool = False,
):
    audit = create_distributed_audit(
        ScalePlanRequest(
            model_id=f"customer/open-weight-{parameter_count_b}b",
            parameter_count_b=parameter_count_b,
            num_layers=num_layers,
            precision="int4" if parameter_count_b == 300 else "bf16",
            available_gpu_memory_gb=80,
            minimum_worker_count=minimum_worker_count,
        ),
        # A fleet run is a real distributed run, so it acknowledges the audit's data
        # capture (universal run-gate 8) -- the harvest happens at every size.
        data_capture_acknowledged=True,
        provenance=(
            ModelProvenanceManifest(
                model_id=f"customer/open-weight-{parameter_count_b}b",
                source_uri="https://models.example.test/open-weight",
                license_id="apache-2.0",
                revision=MODEL_REVISION,
                weight_files=(
                    WeightFileRef(
                        path="model.safetensors",
                        sha256="c" * 64,
                        size_bytes=1,
                    ),
                ),
            )
            if with_provenance
            else None
        ),
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


def _fragment_ref_for_job(
    job,
    *,
    model_id: str,
    produced_outputs: list[str] | None = None,
    evidence_payload: dict | None = None,
    execution_mode: str | None = None,
) -> str:
    produced = produced_outputs or list(job.expected_outputs)
    return build_evidence_fragment_ref(
        audit_id=job.audit_id,
        job_id=job.job_id,
        worker_id=job.assigned_worker_id,
        model_id=model_id,
        layer_start=job.layer_start,
        layer_end=job.layer_end,
        shard_id=job.shard_id,
        expected_outputs=job.expected_outputs,
        produced_outputs=produced,
        evidence_packet_fragment_payload=evidence_payload,
        execution_mode=execution_mode,
    )


def _real_model_attestation(job, *, model_id: str) -> dict:
    artifacts = [
        {"path": "config.json", "sha256": "d" * 64, "byte_count": 1}
    ]
    artifact_set_sha256 = hashlib.sha256(
        json.dumps(
            artifacts,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "status": "real_model_forward_completed",
        "audit_id": job.audit_id,
        "job_id": job.job_id,
        "worker_id": job.assigned_worker_id,
        "model_id": model_id,
        "model_revision": MODEL_REVISION,
        "shard_id": job.shard_id,
        "layer_start": job.layer_start,
        "layer_end": job.layer_end,
        "model_info": {
            "artifact_identity": {
                "manifest_path": MODEL_ARTIFACT_MANIFEST_PATH,
                "manifest_sha256": MODEL_ARTIFACT_MANIFEST_SHA256,
                "artifact_count": len(artifacts),
                "artifact_set_sha256": artifact_set_sha256,
                "artifacts": artifacts,
                "all_artifacts_hash_verified": True,
                "post_load_reverified": True,
                "local_files_only": True,
                "trust_remote_code": False,
                "use_safetensors": True,
            }
        },
    }


def _lease_and_complete(audit_id: str, worker_id: str, *, model_id: str):
    job = lease_next_job(audit_id=audit_id, worker_id=worker_id)
    assert job is not None
    produced_outputs = list(job.expected_outputs)
    evidence_payload = (
        _real_model_attestation(job, model_id=model_id)
        if job.execution_mode == "external_probe_command"
        else None
    )
    execution_mode = (
        "external_probe_command"
        if job.execution_mode == "external_probe_command"
        else None
    )
    run = submit_job_receipt(
        audit_id=audit_id,
        job_id=job.job_id,
        worker_id=worker_id,
        lease_token=job.lease_token or "",
        produced_outputs=produced_outputs,
        evidence_packet_fragment_ref=_fragment_ref_for_job(
            job,
            model_id=model_id,
            produced_outputs=produced_outputs,
            evidence_payload=evidence_payload,
            execution_mode=execution_mode,
        ),
        evidence_packet_fragment_payload=evidence_payload,
        execution_mode=execution_mode,
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


def test_dark_v2_active_lease_snapshot_is_exact_redacted_and_fail_closed():
    audit = _create_dispatched_audit(with_provenance=True)
    assignment = audit.worker_evidence[0]
    register_worker(
        worker_id=assignment.worker_id,
        audit_id=audit.audit_id,
        model_id=audit.plan.model_id,
        worker_url=f"https://{assignment.worker_id}.workers.internal",
        gpu_type="H100-80GB",
        capacity=1,
        supported_methods=list(assignment.assigned_methods),
    )
    prepare_fleet_for_audit(
        audit.audit_id,
        model_revision=MODEL_REVISION,
        model_artifact_manifest_path=MODEL_ARTIFACT_MANIFEST_PATH,
        model_artifact_manifest_sha256=MODEL_ARTIFACT_MANIFEST_SHA256,
        require_scoped_workers=True,
    )
    job = lease_next_job(
        audit_id=audit.audit_id,
        worker_id=assignment.worker_id,
        require_scoped_worker=True,
    )
    assert job is not None and job.lease_token and job.lease_expires_at
    token = job.lease_token
    observed = validate_active_fleet_job_lease(
        audit_id=audit.audit_id,
        job_id=job.job_id,
        worker_id=assignment.worker_id,
        lease_token=token,
    )
    assert isinstance(observed, ActiveFleetJobLease)
    assert observed.snapshot.execution_mapping()["job_id"] == job.job_id
    assert observed.lease_generation_id.startswith("flg_")
    assert observed.lease_token_sha256 == hashlib.sha256(token.encode()).hexdigest()
    assert token not in repr(observed)
    assert observed.state_authority == "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
    assert observed.trusted_time == "NOT_ESTABLISHED"

    with pytest.raises(FleetExecutorStateError, match="does not match"):
        validate_active_fleet_job_lease(
            audit_id=audit.audit_id,
            job_id=job.job_id,
            worker_id=assignment.worker_id,
            lease_token="wrong-secret",
        )
    with pytest.raises(FleetExecutorStateError, match="expired"):
        validate_active_fleet_job_lease(
            audit_id=audit.audit_id,
            job_id=job.job_id,
            worker_id=assignment.worker_id,
            lease_token=token,
            now=datetime.fromisoformat(job.lease_expires_at) + timedelta(seconds=1),
        )


def test_duplicate_worker_registration_is_rejected():
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

    with pytest.raises(FleetExecutorStateError, match="already registered"):
        register_worker(
            worker_id="probe-worker-001",
            model_id="customer/open-weight-300b",
            worker_url="https://probe-worker-001-replacement.workers.internal",
            gpu_type="H100-80GB",
            capacity=2,
            supported_methods=["foundation_probe"],
        )


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


def test_fleet_run_dict_does_not_expose_lease_token_outside_lease_response():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    leased = lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)
    assert leased is not None
    assert leased.lease_token
    assert leased.to_dict()["lease_token"] is None
    assert leased.to_dict(include_lease_token=True)["lease_token"] == leased.lease_token

    saved = get_fleet_run(audit.audit_id)
    assert saved is not None
    assert all(job["lease_token"] is None for job in saved.to_dict()["jobs"])


def test_lease_token_is_not_derivable_from_public_lease_fields():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    lease_seconds = 900
    leased = lease_next_job(
        audit_id=audit.audit_id,
        worker_id=assignment.worker_id,
        lease_seconds=lease_seconds,
    )
    assert leased is not None
    assert leased.lease_token is not None
    assert leased.lease_expires_at is not None
    inferred_leased_at = datetime.fromisoformat(leased.lease_expires_at) - timedelta(
        seconds=lease_seconds
    )
    public_derivation = hashlib.sha256(
        json.dumps(
            {
                "audit_id": leased.audit_id,
                "job_id": leased.job_id,
                "worker_id": leased.assigned_worker_id,
                "leased_at": inferred_leased_at.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    assert len(leased.lease_token) == 64
    assert leased.lease_token != public_derivation


def test_unregistered_worker_cannot_lease_a_job():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    with pytest.raises(FleetExecutorStateError, match="Worker must register before leasing jobs"):
        lease_next_job(audit_id=audit.audit_id, worker_id=audit.worker_evidence[0].worker_id)


def test_wrong_model_worker_cannot_lease_assigned_job():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id="customer/wrong-open-weight-1b")
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None
    assert run.verifier_gate_status == "waiting_for_workers"

    with pytest.raises(FleetExecutorStateError, match="model_id does not match"):
        lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)


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


def test_stale_heartbeat_blocks_gate_without_explicit_stale_scan():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    worker = list_workers()[0]
    worker.last_heartbeat_at = (datetime.now(UTC) - timedelta(seconds=180)).isoformat()
    saved = get_fleet_run(audit.audit_id)

    assert saved is not None
    assert saved.verifier_gate_status == "waiting_for_workers"
    assert saved.to_dict()["stale_workers"] == [assignment.worker_id]
    with pytest.raises(FleetExecutorStateError, match="heartbeat is not active"):
        lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)


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


def test_stale_worker_cannot_submit_receipt_with_unexpired_lease():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None
    leased = lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)
    assert leased is not None

    worker = list_workers()[0]
    worker.last_heartbeat_at = (datetime.now(UTC) - timedelta(seconds=180)).isoformat()

    with pytest.raises(FleetExecutorStateError, match="heartbeat is not active"):
        submit_job_receipt(
            audit_id=audit.audit_id,
            job_id=leased.job_id,
            worker_id=assignment.worker_id,
            lease_token=leased.lease_token or "",
            produced_outputs=list(leased.expected_outputs),
            evidence_packet_fragment_ref=f"packet-fragment://{leased.job_id}",
        )

    saved = get_fleet_run(audit.audit_id)
    assert saved is not None
    assert saved.verifier_gate_status == "waiting_for_workers"
    assert saved.to_dict()["stale_workers"] == [assignment.worker_id]


def test_stale_then_heartbeat_cannot_submit_old_lease():
    audit = _create_dispatched_audit(parameter_count_b=1, num_layers=1)
    assignment = audit.worker_evidence[0]
    _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None
    leased = lease_next_job(audit_id=audit.audit_id, worker_id=assignment.worker_id)
    assert leased is not None
    old_lease_token = leased.lease_token or ""

    worker = list_workers()[0]
    worker.last_heartbeat_at = (datetime.now(UTC) - timedelta(seconds=20)).isoformat()
    stale = mark_stale_workers(max_heartbeat_age_seconds=1)
    assert [worker.worker_id for worker in stale] == [assignment.worker_id]
    refreshed = heartbeat_worker(assignment.worker_id)
    assert refreshed is not None
    assert refreshed.status == "active"

    produced_outputs = list(leased.expected_outputs)
    with pytest.raises(FleetExecutorStateError, match="active lease|lease_token"):
        submit_job_receipt(
            audit_id=audit.audit_id,
            job_id=leased.job_id,
            worker_id=assignment.worker_id,
            lease_token=old_lease_token,
            produced_outputs=produced_outputs,
            evidence_packet_fragment_ref=_fragment_ref_for_job(
                leased,
                model_id=audit.plan.model_id,
                produced_outputs=produced_outputs,
            ),
        )


def test_merge_is_blocked_until_every_assigned_job_has_a_receipt():
    audit = _create_dispatched_audit(parameter_count_b=20, num_layers=8, minimum_worker_count=3)
    for assignment in audit.worker_evidence:
        _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(audit.audit_id)
    assert run is not None

    for assignment in audit.worker_evidence[:-1]:
        _lease_and_complete(audit.audit_id, assignment.worker_id, model_id=audit.plan.model_id)

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
        with_provenance=True,
    )
    assert len(audit.worker_evidence) == 300

    for assignment in audit.worker_evidence:
        _register_assignment_worker(assignment, model_id=audit.plan.model_id)
    run = prepare_fleet_for_audit(
        audit.audit_id,
        model_revision=MODEL_REVISION,
        model_artifact_manifest_path=MODEL_ARTIFACT_MANIFEST_PATH,
        model_artifact_manifest_sha256=MODEL_ARTIFACT_MANIFEST_SHA256,
    )
    assert run is not None
    assert len(run.jobs) == 300

    for assignment in audit.worker_evidence[:-1]:
        _lease_and_complete(audit.audit_id, assignment.worker_id, model_id=audit.plan.model_id)

    with pytest.raises(FleetExecutorStateError, match="every assigned job returns a receipt"):
        merge_fleet_evidence(audit.audit_id)

    partial = get_fleet_run(audit.audit_id)
    assert partial is not None
    assert partial.verifier_gate_status == "waiting_for_receipts"
    assert partial.to_dict()["completed_fragments"] == 299

    _lease_and_complete(audit.audit_id, audit.worker_evidence[-1].worker_id, model_id=audit.plan.model_id)
    merged = merge_fleet_evidence(audit.audit_id)

    assert merged is not None
    assert merged.status == "COMPLETE"
    assert merged.verifier_gate_status == "ready_for_verifier"
    assert merged.to_dict()["completed_fragments"] == 300
    assert merged.to_dict()["total_jobs"] == 300
    assert merged.merged_packet_trace_id == f"{audit.audit_id}-distributed-merge"
    assert "verifier decision layer" in merged.merge_reason
