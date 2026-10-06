from __future__ import annotations

import inspect

import pytest

from api.services import cas_harness_fleet_executor as fleet_executor
from api.services.cas_harness_distributed_audits import (
    create_distributed_audit,
    dispatch_distributed_audit,
    reset_distributed_audits_for_tests,
)
from api.services.cas_harness_fleet_executor import (
    FleetExecutorStateError,
    HarnessV2ConfiguredFleetInventory,
    enumerate_harness_v2_configured_fleet,
    lease_next_job,
    load_harness_v2_fleet_job_snapshot_current,
    load_harness_v2_fleet_job_snapshot_for_issuance,
    prepare_fleet_for_audit,
    register_worker,
    reset_fleet_executor_for_tests,
)
from api.services.cas_harness_model_provenance import (
    ModelProvenanceManifest,
    WeightFileRef,
)
from api.services.cas_harness_scale_planner import ScalePlanRequest
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot


TENANT_ID = "tenant-harness-v2"
MODEL_ID = "customer/open-weight-20b"
MODEL_REVISION = "a" * 40
MODEL_ARTIFACT_MANIFEST_PATH = "/workspace/model-artifacts.json"
MODEL_ARTIFACT_MANIFEST_SHA256 = "b" * 64


def setup_function() -> None:
    reset_fleet_executor_for_tests()
    reset_distributed_audits_for_tests()


def _prepared_fleet():
    audit = create_distributed_audit(
        ScalePlanRequest(
            model_id=MODEL_ID,
            parameter_count_b=20,
            num_layers=8,
            precision="bf16",
            available_gpu_memory_gb=80,
            minimum_worker_count=2,
        ),
        data_capture_acknowledged=True,
        provenance=ModelProvenanceManifest(
            model_id=MODEL_ID,
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
        ),
    )
    dispatched = dispatch_distributed_audit(audit.audit_id)
    assert dispatched is not None
    run = prepare_fleet_for_audit(
        audit.audit_id,
        model_revision=MODEL_REVISION,
        model_artifact_manifest_path=MODEL_ARTIFACT_MANIFEST_PATH,
        model_artifact_manifest_sha256=MODEL_ARTIFACT_MANIFEST_SHA256,
        require_scoped_workers=True,
    )
    assert run is not None and run.jobs
    return dispatched, run


def _register_first_worker(audit) -> None:
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


def test_issuance_snapshot_is_server_derived_preterminal_and_has_no_lease_secret() -> None:
    audit, run = _prepared_fleet()
    _register_first_worker(audit)
    leased = lease_next_job(
        audit_id=audit.audit_id,
        worker_id=audit.worker_evidence[0].worker_id,
        require_scoped_worker=True,
    )
    assert leased is not None and leased.lease_token and leased.lease_token_hash

    snapshot = load_harness_v2_fleet_job_snapshot_for_issuance(
        tenant_id=TENANT_ID,
        audit_id=audit.audit_id,
        fleet_id=audit.audit_id,
        job_id=leased.job_id,
    )
    inventory = enumerate_harness_v2_configured_fleet(
        tenant_id=TENANT_ID,
        audit_id=audit.audit_id,
        fleet_id=audit.audit_id,
    )

    assert type(snapshot) is FleetJobSnapshot
    assert snapshot.execution_mapping()["job_id"] == leased.job_id
    assert snapshot.execution_mapping()["lease_model"] == {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_artifact_manifest_path": MODEL_ARTIFACT_MANIFEST_PATH,
        "model_artifact_manifest_sha256": MODEL_ARTIFACT_MANIFEST_SHA256,
        "execution_mode": "external_probe_command",
    }
    assert type(inventory) is HarnessV2ConfiguredFleetInventory
    assert inventory.job_ids == tuple(sorted(job.job_id for job in run.jobs))
    assert inventory.state_authority == "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
    assert (
        inventory.tenant_scope_authority
        == "AUTHENTICATED_SCOPE_REQUIRED_NOT_RETAINED_BY_FLEET_EXECUTOR"
    )
    rendered = repr((snapshot, inventory))
    assert leased.lease_token not in rendered
    assert leased.lease_token_hash not in rendered
    assert "lease_token" not in inspect.signature(
        load_harness_v2_fleet_job_snapshot_for_issuance
    ).parameters
    assert "lease_token" not in inspect.signature(
        enumerate_harness_v2_configured_fleet
    ).parameters


@pytest.mark.parametrize("terminal_status", ["completed", "failed"])
def test_issuance_snapshot_rejects_terminal_job_reuse(terminal_status: str) -> None:
    audit, run = _prepared_fleet()
    run.jobs[0].status = terminal_status

    with pytest.raises(FleetExecutorStateError, match="preterminal"):
        load_harness_v2_fleet_job_snapshot_for_issuance(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
            job_id=run.jobs[0].job_id,
        )


def test_issuance_snapshot_rejects_terminal_run_even_if_job_status_drifted() -> None:
    audit, run = _prepared_fleet()
    run.status = "COMPLETE"
    run.jobs[0].status = "queued"

    with pytest.raises(FleetExecutorStateError, match="preterminal"):
        load_harness_v2_fleet_job_snapshot_for_issuance(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
            job_id=run.jobs[0].job_id,
        )


@pytest.mark.parametrize(
    ("run_status", "job_status"),
    (("COMPLETE", "completed"), ("FAILED", "failed")),
)
def test_current_snapshot_permits_terminal_state_without_changing_exact_mapping(
    run_status: str,
    job_status: str,
) -> None:
    audit, run = _prepared_fleet()
    job = run.jobs[0]
    issuance_snapshot = load_harness_v2_fleet_job_snapshot_for_issuance(
        tenant_id=TENANT_ID,
        audit_id=audit.audit_id,
        fleet_id=audit.audit_id,
        job_id=job.job_id,
    )
    job.status = job_status
    run.status = run_status
    job.lease_token = "terminal-lease-secret-must-not-escape"
    job.lease_token_hash = "terminal-lease-hash-must-not-escape"

    current_snapshot = load_harness_v2_fleet_job_snapshot_current(
        tenant_id=TENANT_ID,
        audit_id=audit.audit_id,
        fleet_id=audit.audit_id,
        job_id=job.job_id,
    )

    assert current_snapshot == issuance_snapshot
    assert current_snapshot.execution_mapping() == issuance_snapshot.execution_mapping()
    rendered = repr(current_snapshot)
    assert job.lease_token not in rendered
    assert job.lease_token_hash not in rendered
    with pytest.raises(FleetExecutorStateError, match="preterminal"):
        load_harness_v2_fleet_job_snapshot_for_issuance(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
            job_id=job.job_id,
        )


def test_current_snapshot_retains_exact_unique_job_validation() -> None:
    audit, run = _prepared_fleet()
    with pytest.raises(FleetExecutorStateError, match="exactly once for replay"):
        load_harness_v2_fleet_job_snapshot_current(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
            job_id="fleet-job-not-configured",
        )

    run.jobs.append(run.jobs[0])
    with pytest.raises(FleetExecutorStateError, match="duplicate job_id"):
        load_harness_v2_fleet_job_snapshot_current(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
            job_id=run.jobs[0].job_id,
        )


@pytest.mark.parametrize(
    ("drift", "message"),
    (
        ("fleet_scope", "fleet_id must exactly equal"),
        ("job_scope", "crossed its audit/fleet scope"),
        ("execution_mapping", "assignment plan"),
    ),
)
def test_current_snapshot_retains_scope_and_mapping_validation(
    drift: str,
    message: str,
) -> None:
    audit, run = _prepared_fleet()
    job = run.jobs[0]
    fleet_id = audit.audit_id
    if drift == "fleet_scope":
        fleet_id = "another-fleet"
    elif drift == "job_scope":
        job.audit_id = "another-audit"
    else:
        job.layer_end += 1

    with pytest.raises(FleetExecutorStateError, match=message):
        load_harness_v2_fleet_job_snapshot_current(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=fleet_id,
            job_id=job.job_id,
        )


def test_configured_inventory_includes_terminal_jobs_but_redacts_runtime_state() -> None:
    audit, run = _prepared_fleet()
    terminal = run.jobs[0]
    terminal.status = "completed"
    terminal.lease_token = "lease-secret-must-not-escape"
    terminal.lease_token_hash = "lease-hash-must-not-escape"
    terminal.evidence_packet_fragment_payload = {"private": "fragment-payload"}
    terminal.error_message = "worker-private-error"

    inventory = enumerate_harness_v2_configured_fleet(
        tenant_id=TENANT_ID,
        audit_id=audit.audit_id,
        fleet_id=audit.audit_id,
    )
    rendered = repr(inventory)
    assert terminal.job_id in inventory.job_ids
    assert "lease-secret-must-not-escape" not in rendered
    assert "lease-hash-must-not-escape" not in rendered
    assert "fragment-payload" not in rendered
    assert "worker-private-error" not in rendered
    assert "completed" not in rendered


def test_loader_rejects_missing_and_duplicate_job_identity() -> None:
    audit, run = _prepared_fleet()
    with pytest.raises(FleetExecutorStateError, match="exactly once"):
        load_harness_v2_fleet_job_snapshot_for_issuance(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
            job_id="fleet-job-not-configured",
        )

    run.jobs.append(run.jobs[0])
    with pytest.raises(FleetExecutorStateError, match="duplicate job_id"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


def test_inventory_rejects_a_missing_run_or_empty_job_inventory() -> None:
    with pytest.raises(FleetExecutorStateError, match="unavailable in process-local state"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id="audit-not-configured",
            fleet_id="audit-not-configured",
        )

    audit, run = _prepared_fleet()
    run.jobs.clear()
    with pytest.raises(FleetExecutorStateError, match="no job inventory"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


def test_inventory_rejects_cross_audit_or_fleet_scope() -> None:
    audit, run = _prepared_fleet()
    with pytest.raises(FleetExecutorStateError, match="fleet_id must exactly equal"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id="another-fleet",
        )

    run.jobs[0].audit_id = "another-audit"
    with pytest.raises(FleetExecutorStateError, match="crossed its audit/fleet scope"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


def test_inventory_rejects_missing_partial_or_invalid_model_identity() -> None:
    audit, run = _prepared_fleet()
    run.jobs[0].model_revision = None
    with pytest.raises(FleetExecutorStateError, match="model identity"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


def test_inventory_rejects_cross_job_model_identity_drift() -> None:
    audit, run = _prepared_fleet()
    assert len(run.jobs) >= 2
    run.jobs[1].model_artifact_manifest_sha256 = "d" * 64

    with pytest.raises(FleetExecutorStateError, match="drifted model identity"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


def test_inventory_rejects_model_revision_drift_from_audit_provenance() -> None:
    audit, run = _prepared_fleet()
    for job in run.jobs:
        job.model_revision = "d" * 40

    with pytest.raises(FleetExecutorStateError, match="audit provenance"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


def test_inventory_rejects_model_id_or_assignment_drift() -> None:
    audit, run = _prepared_fleet()
    for job in run.jobs:
        job.model_id = "customer/substituted-model"
    with pytest.raises(FleetExecutorStateError, match="audit plan"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )

    for job in run.jobs:
        job.model_id = MODEL_ID
    run.jobs[0].layer_end += 1
    with pytest.raises(FleetExecutorStateError, match="assignment plan"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=TENANT_ID,
            audit_id=audit.audit_id,
            fleet_id=audit.audit_id,
        )


@pytest.mark.parametrize(
    ("tenant_id", "audit_id", "fleet_id"),
    [
        (" tenant-harness-v2", "audit", "audit"),
        ("tenant-harness-v2", "", ""),
        ("tenant-harness-v2", "audit\n", "audit\n"),
    ],
)
def test_inventory_rejects_nonexact_scope_text(
    tenant_id: str,
    audit_id: str,
    fleet_id: str,
) -> None:
    with pytest.raises(FleetExecutorStateError, match="exact non-empty bounded text"):
        enumerate_harness_v2_configured_fleet(
            tenant_id=tenant_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
        )
