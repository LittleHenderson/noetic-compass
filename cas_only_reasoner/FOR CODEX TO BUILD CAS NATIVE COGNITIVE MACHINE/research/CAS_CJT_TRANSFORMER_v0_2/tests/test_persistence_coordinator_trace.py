from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
import torch

from cas_cjt.artifacts import ArtifactError, decode_tensor, encode_tensor, make_model_artifact
from cas_cjt.contracts import canonical_digest, canonical_json, verify_declared_digest
from cas_cjt.coordinator import (
    AtomicCoordinator,
    BatchRejected,
    CommitBatch,
    PROPOSE_MEMORY_WRITE,
    PROPOSE_STATE_UPDATE,
    RollbackRequest,
)
from cas_cjt.memory import retrieve_memory
from cas_cjt.state import content_id, make_cause
from cas_cjt.persistence import (
    IdempotencyConflict,
    InjectedFailure,
    ModelVersionWrite,
    PersistenceError,
    SQLiteAtomicStore,
    StaleHeadError,
)
from cas_cjt.repair import open_repair
from cas_cjt.trace import (
    MANDATORY_PHASES,
    reconstruct_trace,
    seal_trace,
    verify_public_trace,
    verify_public_rejection_audit,
    verify_rejection_audit,
    verify_rejection_audit_chain,
    verify_trace,
    verify_trace_chain,
)
from cas_cjt.types import (
    BiasState,
    CandidateEffect,
    CauseKind,
    CausePacket,
    CommitReceipt,
    Governance,
    LocalMemory,
    MemoryKind,
    MemoryWriteIntent,
    ModelUpdateIntent,
    ModelUpdateKind,
    OperatingRecord,
    OperatingRegion,
    PhaseRecord,
    RPMState,
    ReadinessAxis,
    ReadinessAxisName,
    ReadinessState,
    ReadinessStatus,
    SemanticOutcome,
    StableSubstrate,
    StateUpdateIntent,
    TensorArtifactRef,
    ThetaRef,
    TickPhase,
    VerifierDisposition,
    VerifierReceipt,
)


H0 = "0" * 64
H1 = "1" * 64
OPERATION_DIGEST = "a" * 64
SOFTWARE_DIGEST = "b" * 64


def _sealed(value, field_name: str):
    return replace(
        value,
        **{field_name: canonical_digest(value, omit_keys=(field_name,))},
    )


def _ref(tensor: torch.Tensor):
    mapping, artifact = encode_tensor(tensor)
    return TensorArtifactRef(**mapping), artifact


def _axis(axis: ReadinessAxisName) -> ReadinessAxis:
    return ReadinessAxis(
        axis=axis,
        status=ReadinessStatus.SUFFICIENT,
        score_ppm=900_000,
        threshold_ppm=500_000,
        reason_codes=(f"{axis.value}_READY",),
        evidence_refs=(f"fixture:{axis.value.lower()}",),
        provenance=("fixture:dwp",),
    )


def _phases(tick: int, *, private_value: int | None = None) -> tuple[PhaseRecord, ...]:
    fields = {
        "READ": (("cause_id", "state_digest", "model_digest"), ("bias_ids", "bias_digests", "memory_read_refs"), ()),
        "CANDIDATE": (("candidate_operation_ids",), ("candidate_cjt_ids", "operation_contract_ids"), ()),
        "READINESS": (("profile_ids",), ("desire", "wisdom", "power", "hard_open"), ()),
        "ROUTE": (("control_cjt_id", "topology_mask", "permission_mask", "quarantine_mask", "budget_mask", "readiness_hard_mask", "route_settings", "native_compute", "compute_policy", "control_binding_manifest"), ("compute_plan", "effective_path_mask", "conducting_query_mask", "current_microunits", "total_current_microunits", "flow_allocation_ppm"), ()),
        "EXECUTE": (("scheduled_cjt_ids", "operation_ids"), ("executed_cjt_ids", "compute_units_used"), ()),
        "OBSERVE": (("executed_cjt_ids",), ("candidate_effect_ids", "operating_regions", "artifact_ids", "compute_observations"), ("control_binding_digest", "declared_beta_microunits", "live_beta_by_head_microunits")),
        "VERIFY": (("candidate_effect_ids", "evidence_ids"), ("verifier_receipt_ids", "semantic_outcomes", "dispositions"), ()),
        "DIAGNOSE": (("operating_regions", "semantic_outcomes"), ("reason_codes", "repair_required"), ()),
        "EMIT": (("verifier_receipt_ids",), ("state_intent_ids", "model_intent_ids", "memory_intent_ids", "repair_ids", "repair_outcome_ids", "publication_requested"), ()),
        "COMMIT": (("pre_state_digest", "pre_model_digest"), ("proposed_post_state_digest", "proposed_post_model_digest"), ()),
        "TRACE": (("previous_trace_digest",), ("seal_requested", "phase_count"), ()),
    }
    result = []
    for name in MANDATORY_PHASES:
        input_keys, output_keys, diagnostic_keys = fields[name]
        inputs = {key: None for key in input_keys}
        outputs = {key: None for key in output_keys}
        diagnostics = {key: None for key in diagnostic_keys}
        compute_units = 1 if name == "EXECUTE" else 0
        if name == "EXECUTE":
            outputs["compute_units_used"] = compute_units
        if private_value is not None and name == "EXECUTE":
            outputs["compute_units_used"] = {
                "raw_values": [private_value, private_value + 1]
            }
        if private_value is not None and name == "ROUTE":
            inputs["route_settings"] = {
                "drive_microunits": [987_321],
                "resistance_microunits": [7_654_321],
                "closed_route_mask": [False],
            }
            inputs["native_compute"] = {
                "authored_drive_microunits": [987_321],
                "authored_resistance_microunits": [7_654_321],
            }
        result.append(
            PhaseRecord(
                phase=TickPhase(name),
                tick=tick,
                inputs=inputs,
                outputs=outputs,
                diagnostics=diagnostics,
                compute_units=compute_units,
            )
        )
    return tuple(result)


@dataclass
class Fixture:
    bias0: BiasState
    bias1: BiasState
    model_artifact: object
    state_artifact: object
    effect_artifact: object
    candidate: CandidateEffect
    verifier: VerifierReceipt
    cause: CausePacket
    initial_model: ModelVersionWrite


def _fixture() -> Fixture:
    state_ref, state_artifact = _ref(torch.tensor([[1.0, 2.0]], dtype=torch.float32))
    effect_ref, effect_artifact = _ref(torch.tensor([[3.0, 4.0]], dtype=torch.float32))
    model_artifact = make_model_artifact(
        b"deterministic-model-v0",
        format_name="raw-test-checkpoint-v1",
        metadata={"model_id": "model-1", "model_version": 0},
    )
    readiness = ReadinessState(
        profile_id="PROTOTYPE_DWP_PRODUCT/0.1",
        desire=_axis(ReadinessAxisName.DESIRE),
        wisdom=_axis(ReadinessAxisName.WISDOM),
        power=_axis(ReadinessAxisName.POWER),
    )
    bias0 = BiasState(
        bias_id="bias-cjt-1",
        cjt_id="cjt-1",
        version=0,
        previous_digest=None,
        stable=StableSubstrate(
            cjt_id="cjt-1",
            formation_version=1,
            registered_operation_id="^6",
            specialization_tags=("decomposition",),
            lineage_refs=("fixture:genesis",),
            configuration_digest=H1,
        ),
        memory=LocalMemory(
            recurrent_state_ref=state_ref,
            recent_cause_ids=(),
            recent_candidate_effect_ids=(),
            verifier_receipt_ids=(),
            repair_frame_ids=(),
            retrieved_memory_refs=(),
            provenance_refs=("fixture:state",),
        ),
        rpm=RPMState(
            readiness=readiness,
            unmet_prerequisites=(),
            open_repair_ids=(),
            suspended_parent_cause_id=None,
            return_addresses=(),
            repair_history=(),
        ),
        operating=OperatingRecord(
            region=OperatingRegion.ACTIVE,
            stability_status="STABLE",
            response_model_status="PROFILE_BOUND",
            semantic_outcome=SemanticOutcome.UNASSESSED,
            previous_committed_verifier_receipt_id=None,
            last_tick=0,
        ),
        theta=ThetaRef(
            model_id="model-1",
            model_version=0,
            model_digest=model_artifact.sha256,
            parameter_artifacts=(state_ref,),
            parameter_group_ids=("operator.^6",),
            beta_microunits=1_000_000,
            operating_profile_id="cjt-region/0.2",
            adapter_ids=("casformer-v0.1",),
        ),
        governance=Governance(
            hard_permissions=("EXECUTE",),
            topology_permissions=("cjt-1",),
            learning_permissions=("learn", "operator.^6"),
            compute_ceiling_units=64,
            quarantined=False,
            state_write_authorities=("prototype-coordinator",),
            memory_write_authorities=("prototype-coordinator",),
            effect_publication_authorities=("prototype-coordinator",),
            owner_restrictions=("NO_EXTERNAL_ACTION",),
        ),
        state_digest=H0,
    )
    bias0 = _sealed(bias0, "state_digest")
    bias1 = replace(
        bias0,
        version=1,
        previous_digest=bias0.state_digest,
        state_digest=H0,
    )
    bias1 = _sealed(bias1, "state_digest")
    cause = make_cause(
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"predicate": "has_parts", "arguments": ["whole"]},
        source="fixture",
        provenance=("fixture:cause",),
        uncertainty_ppm=10_000,
        goal_context={"goal_id": "goal-1"},
        candidate_operation_ids=("^6",),
    )
    candidate_identity = {
        "tick": 1,
        "parent_cause_id": cause.cause_id,
        "producer_cjt_id": "cjt-1",
        "operation_contract_digest": OPERATION_DIGEST,
        "bias_digest": bias0.state_digest,
        "model_digest": model_artifact.sha256,
        "content": {"parts": ["part-a", "part-b"]},
        "content_ref": effect_ref.to_dict(),
    }
    candidate = CandidateEffect(
        candidate_effect_id=content_id("candidate-effect", candidate_identity),
        tick=1,
        parent_cause_id=cause.cause_id,
        producer_cjt_id="cjt-1",
        operation_id="^6",
        operation_contract_id="operation-^6-v1",
        operation_contract_digest=OPERATION_DIGEST,
        bias_id=bias0.bias_id,
        bias_version=bias0.version,
        bias_digest=bias0.state_digest,
        model_digest=model_artifact.sha256,
        content={"parts": ["part-a", "part-b"]},
        content_ref=effect_ref,
        uncertainty_ppm=20_000,
        provenance=("neural-cjt:cjt-1",),
        candidate_digest=H0,
    )
    candidate = _sealed(candidate, "candidate_digest")
    receipt_identity = canonical_digest(
        {
            "tick": 1,
            "verifier_id": "semantic-verifier",
            "verifier_version": 1,
            "verifier_digest": SOFTWARE_DIGEST,
            "cause_id": cause.cause_id,
            "candidate_effect_id": candidate.candidate_effect_id,
            "candidate_effect_digest": candidate.candidate_digest,
            "bias_digest": bias0.state_digest,
            "contract_digest": OPERATION_DIGEST,
            "outcome": SemanticOutcome.INTENDED.value,
            "disposition": VerifierDisposition.ACCEPT.value,
            "reason_codes": ["SEMANTIC_MATCH"],
            "evidence_refs": ["fixture:oracle"],
        }
    )
    verifier = VerifierReceipt(
        receipt_id=f"verifier-receipt-{receipt_identity}",
        tick=1,
        verifier_id="semantic-verifier",
        verifier_version=1,
        verifier_digest=SOFTWARE_DIGEST,
        independent=True,
        cause_id=cause.cause_id,
        candidate_effect_id=candidate.candidate_effect_id,
        candidate_effect_digest=candidate.candidate_digest,
        bias_id=bias0.bias_id,
        bias_version=bias0.version,
        bias_digest=bias0.state_digest,
        operation_contract_id=candidate.operation_contract_id,
        operation_contract_digest=OPERATION_DIGEST,
        model_digest=model_artifact.sha256,
        semantic_outcome=SemanticOutcome.INTENDED,
        disposition=VerifierDisposition.ACCEPT,
        reason_codes=("SEMANTIC_MATCH",),
        evidence_refs=("fixture:oracle",),
        repair_required=False,
        receipt_digest=H0,
    )
    verifier = _sealed(verifier, "receipt_digest")
    initial_model = ModelVersionWrite(
        model_digest=model_artifact.sha256,
        parent_model_digest=None,
        artifact_id=model_artifact.artifact_id,
        payload={
            "schema_version": "cas.neural-cjt.model-version/0.2",
            "model_id": "model-1",
            "model_version": 0,
            "model_digest": model_artifact.sha256,
            "model_artifact_ref": {
                "artifact_id": model_artifact.artifact_id,
                "sha256": model_artifact.sha256,
            },
            "parent_model_digest": None,
        },
    )
    return Fixture(
        bias0=bias0,
        bias1=bias1,
        model_artifact=model_artifact,
        state_artifact=state_artifact,
        effect_artifact=effect_artifact,
        candidate=candidate,
        verifier=verifier,
        cause=cause,
        initial_model=initial_model,
    )


def _open(tmp_path: Path, fixture: Fixture):
    store = SQLiteAtomicStore(tmp_path / "neural-cjt.sqlite3")
    store.initialize(
        state_digest=fixture.bias0.state_digest,
        state_version=0,
        state_payload=fixture.bias0,
        model_digest=fixture.model_artifact.sha256,
        initial_artifacts=(fixture.state_artifact, fixture.model_artifact),
        initial_model_version=fixture.initial_model,
    )
    coordinator = AtomicCoordinator(
        store,
        coordinator_id="prototype-coordinator",
        authority_contract_id="prototype-authority/0.2",
        operation_contract_digests={"operation-^6-v1": OPERATION_DIGEST},
        trusted_runtime_id="prototype-runtime",
        trusted_software_digest=SOFTWARE_DIGEST,
        trusted_cjt_ids=("cjt-1",),
    )
    return store, coordinator


def _batch(fixture: Fixture, **changes) -> CommitBatch:
    values = dict(
        batch_id="batch-1",
        tick=1,
        base_snapshot_hash=fixture.bias0.state_digest,
        base_trace_digest=None,
        cause=fixture.cause,
        bias_before=fixture.bias0,
        bias_after=fixture.bias1,
        candidate_effects=(fixture.candidate,),
        verifier_receipts=(fixture.verifier,),
        state_intents=(),
        model_intents=(),
        memory_intents=(),
        repair_frames=(),
        phase_records=_phases(1, private_value=73),
        runtime_id="prototype-runtime",
        software_digest=SOFTWARE_DIGEST,
        cjt_ids=("cjt-1",),
        artifacts=(fixture.effect_artifact,),
        memory_read_refs=(),
        compute_plan={"budget_units": 11},
        compute_observations={"used_units": 11},
        sensitive_trace_fields=("raw_values",),
    )
    values.update(changes)
    return CommitBatch(**values)


def _rollback_commit(
    coordinator: AtomicCoordinator,
    target: CommitReceipt,
    *,
    tick: int,
    suffix: str,
) -> CommitReceipt:
    rollback_cause = make_cause(
        tick=tick,
        cause_kind=CauseKind.PROPOSITION,
        content={
            "mode": "COMPENSATING_ROLLBACK",
            "rollback_of_receipt_id": target.receipt_id,
            "reason_codes": ["SEMANTIC_REGRESSION"],
        },
        goal_context={"kind": "COMPENSATING_ROLLBACK"},
        source="prototype:atomic-coordinator",
        provenance=(f"commit-receipt:{target.receipt_id}",),
        candidate_operation_ids=(),
    )
    return coordinator.rollback(
        RollbackRequest(
            batch_id=f"rollback-batch-{suffix}",
            tick=tick,
            rollback_of_receipt_id=target.receipt_id,
            issuer_id="prototype-coordinator",
            authority_capability=PROPOSE_STATE_UPDATE,
            cause_id=rollback_cause.cause_id,
            runtime_id="prototype-runtime",
            software_digest=SOFTWARE_DIGEST,
            cjt_ids=("cjt-1",),
            reason_codes=("SEMANTIC_REGRESSION",),
        )
    )


def test_tensor_artifact_round_trip_typed_ref_and_tamper_detection() -> None:
    original = torch.tensor([[1.25, -2.5], [3.0, 4.5]], dtype=torch.float32)
    mapping, artifact = encode_tensor(original)
    typed = TensorArtifactRef(**mapping)
    restored = decode_tensor(typed, artifact)
    assert torch.equal(restored, original)
    public = artifact.public_descriptor()
    assert public["redacted"] is True
    assert "payload" not in public
    with pytest.raises(ArtifactError, match="digest mismatch"):
        decode_tensor(typed, replace(artifact, payload=artifact.payload + b"x"))
    with pytest.raises(ArtifactError, match="empty tensors"):
        encode_tensor(torch.empty(0))


def test_atomic_commit_idempotency_restart_and_public_redaction(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    batch = _batch(fixture)
    receipt = coordinator.commit(batch)
    assert receipt.disposition.value == "COMMITTED"
    assert receipt.published_effect_ids
    assert coordinator.commit(batch) == receipt
    assert len(store.trace_events()) == 1
    assert store.head.state_digest == fixture.bias1.state_digest
    assert store.load_artifact(fixture.model_artifact.artifact_id).payload == b"deterministic-model-v0"
    effect = store.immutable_document("published_effects", receipt.published_effect_ids[0])
    assert effect["authoritative"] is True
    assert effect["verifier_receipt_id"] == fixture.verifier.receipt_id
    public_trace = store.trace_events(public=True)[0]
    assert verify_public_trace(public_trace)
    serialized = json.dumps(public_trace, sort_keys=True)
    private_serialized = json.dumps(store.trace_events()[0], sort_keys=True)
    assert '"raw_values": [73, 74]' not in serialized
    assert '"drive_microunits": [987321]' in private_serialized
    assert '"resistance_microunits": [7654321]' in private_serialized
    assert '"drive_microunits": [987321]' not in serialized
    assert '"resistance_microunits": [7654321]' not in serialized
    assert '"route_settings": {"redacted": true' in serialized
    assert '"native_compute": {"redacted": true' in serialized
    assert '"redacted": true' in serialized
    transition = store.reconstruct_transition()
    assert transition["causes"][0]["cause_id"] == fixture.cause.cause_id
    assert transition["candidate_effects"][0]["candidate_effect_id"] == fixture.candidate.candidate_effect_id
    assert transition["verifier_receipts"][0]["receipt_id"] == fixture.verifier.receipt_id
    assert transition["transition_batches"][0]["batch_id"] == batch.batch_id
    assert transition["pre_state"]["state_digest"] == fixture.bias0.state_digest
    assert transition["post_state"]["state_digest"] == fixture.bias1.state_digest
    assert {item["artifact_id"] for item in transition["artifacts"]} >= {
        fixture.effect_artifact.artifact_id,
        fixture.state_artifact.artifact_id,
    }
    assert store.verify_integrity()
    database = store.path
    store.close()

    reopened = SQLiteAtomicStore(database)
    recovered = AtomicCoordinator(
        reopened,
        coordinator_id="prototype-coordinator",
        authority_contract_id="prototype-authority/0.2",
        operation_contract_digests={"operation-^6-v1": OPERATION_DIGEST},
        trusted_runtime_id="prototype-runtime",
        trusted_software_digest=SOFTWARE_DIGEST,
        trusted_cjt_ids=("cjt-1",),
    ).restore_and_verify()
    assert recovered.head.state_digest == fixture.bias1.state_digest
    assert recovered.state["version"] == 1
    assert reopened.reconstruct_transition()["trace"]["trace_id"] == receipt.trace_id
    reopened.close()

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from cas_cjt.persistence import SQLiteAtomicStore; "
                "s=SQLiteAtomicStore(r'" + str(database) + "'); "
                "print(s.verify_integrity(), s.head.state_version); s.close()"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    assert probe.stdout.strip() == "True 1"


@pytest.mark.parametrize(
    "fault_at",
    [
        "after_artifacts",
        "after_state",
        "after_trace",
        "after_receipt",
        "after_head_update",
        "before_commit",
    ],
)
def test_every_fault_point_rolls_back_the_whole_batch(tmp_path: Path, fault_at: str) -> None:
    fixture = _fixture()
    scoped = tmp_path / fault_at
    scoped.mkdir()
    store, coordinator = _open(scoped, fixture)
    initial = store.head
    with pytest.raises(InjectedFailure, match=fault_at):
        coordinator.commit(_batch(fixture), fault_at=fault_at)
    assert store.head == initial
    assert store.trace_events() == ()
    assert store.rejection_audits() == ()
    assert store.receipt_for_batch("batch-1") is None
    assert not store.has_artifact(fixture.effect_artifact.artifact_id)
    with pytest.raises(PersistenceError):
        store.immutable_document("published_effects", "effect-missing")
    assert store.verify_integrity()
    store.close()


def test_stale_and_mixed_invalid_batches_write_nothing(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    receipt = coordinator.commit(_batch(fixture))
    initial_event_count = len(store.trace_events())
    with pytest.raises(StaleHeadError):
        coordinator.commit(_batch(fixture, batch_id="stale-batch"))
    assert len(store.trace_events()) == initial_event_count
    assert store.head.commit_receipt_id == receipt.receipt_id
    stale_audit = store.rejection_audits()[0]
    assert stale_audit["reason_codes"] == ["STALE_ACTIVE_HEAD"]
    assert stale_audit["pre_state_digest"] == stale_audit["post_state_digest"]
    store.close()

    second_path = tmp_path / "mixed"
    second_path.mkdir()
    store, coordinator = _open(second_path, fixture)
    valid = MemoryWriteIntent(
        intent_id="memory-good",
        tick=1,
        issuer_id="cjt-1",
        authority_capability=PROPOSE_MEMORY_WRITE,
        target_bias_id=fixture.bias0.bias_id,
        expected_bias_version=0,
        expected_bias_digest=fixture.bias0.state_digest,
        memory_record_id="memory-good",
        memory_kind=MemoryKind.EPISODIC,
        content={"cause_id": fixture.cause.cause_id},
        content_ref=None,
        confidence_ppm=900_000,
        provenance=(fixture.verifier.receipt_id,),
        evidence_refs=("fixture:oracle",),
        verifier_receipt_id=fixture.verifier.receipt_id,
        intent_digest=H0,
    )
    valid = _sealed(valid, "intent_digest")
    invalid = valid.to_dict()
    invalid["intent_id"] = "memory-bad"
    invalid["memory_record_id"] = "memory-bad"
    invalid["expected_bias_digest"] = "9" * 64
    invalid["intent_digest"] = canonical_digest(invalid, omit_keys=("intent_digest",))
    with pytest.raises(BatchRejected, match="MEMORY_INTENT_HEAD_BINDING_INVALID"):
        coordinator.commit(
            _batch(fixture, memory_intents=(valid, invalid), batch_id="mixed-batch")
        )
    assert store.head.state_digest == fixture.bias0.state_digest
    assert store.trace_events() == ()
    assert store.receipt_for_batch("mixed-batch") is None
    audit = store.rejection_audits()[0]
    assert audit["accepted_intent_ids"] == []
    assert audit["rejected_intent_ids"] == ["memory-good", "memory-bad"]
    assert audit["state_advanced"] is False
    assert audit["pre_state_digest"] == audit["post_state_digest"]
    assert not store.has_artifact(fixture.effect_artifact.artifact_id)
    with pytest.raises(PersistenceError):
        store.immutable_document("memory_records", "memory-good")
    store.close()


def test_batch_id_collision_and_immutable_history_are_rejected(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    coordinator.commit(_batch(fixture))
    with pytest.raises(IdempotencyConflict):
        coordinator.commit(_batch(fixture, runtime_id="different-runtime"))
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        store._connection.execute(  # noqa: SLF001 - proves the database trigger itself
            "UPDATE state_versions SET state_version = 99 WHERE state_digest = ?",
            (fixture.bias0.state_digest,),
        )
    assert store.verify_integrity()
    store.close()


def test_rejection_audit_is_idempotent_redacted_and_tamper_evident(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    bad = _batch(fixture, effect_publication_capability="WRITE_EFFECT_DIRECTLY")
    for _ in range(2):
        with pytest.raises(BatchRejected, match="EFFECT_PUBLICATION_CAPABILITY_INVALID"):
            coordinator.commit(bad)
    audits = store.rejection_audits()
    assert len(audits) == 1
    assert verify_rejection_audit_chain(audits)
    assert store.head.state_digest == fixture.bias0.state_digest
    assert store.head.trace_digest is None
    assert store.trace_events() == ()
    public = store.rejection_audits(public=True)[0]
    assert verify_public_rejection_audit(public)
    assert '"raw_values": [73, 74]' not in json.dumps(public, sort_keys=True)
    tampered = dict(audits[0])
    tampered["reason_codes"] = ["FORGED"]
    assert not verify_rejection_audit(tampered)
    assert store.verify_integrity()
    store.close()


def test_compensating_rollback_is_a_new_commit_and_survives_restart(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    original = coordinator.commit(_batch(fixture))
    rollback_cause = make_cause(
        tick=2,
        cause_kind=CauseKind.PROPOSITION,
        content={
            "mode": "COMPENSATING_ROLLBACK",
            "rollback_of_receipt_id": original.receipt_id,
            "reason_codes": ["SEMANTIC_REGRESSION"],
        },
        goal_context={"kind": "COMPENSATING_ROLLBACK"},
        source="prototype:atomic-coordinator",
        provenance=(f"commit-receipt:{original.receipt_id}",),
        candidate_operation_ids=(),
    )
    rollback_request = RollbackRequest(
        batch_id="rollback-batch-1",
        tick=2,
        rollback_of_receipt_id=original.receipt_id,
        issuer_id="prototype-coordinator",
        authority_capability=PROPOSE_STATE_UPDATE,
        cause_id=rollback_cause.cause_id,
        runtime_id="prototype-runtime",
        software_digest=SOFTWARE_DIGEST,
        cjt_ids=("cjt-1",),
        reason_codes=("SEMANTIC_REGRESSION",),
    )
    rolled_back = coordinator.rollback(rollback_request)
    assert rolled_back.disposition.value == "ROLLED_BACK"
    assert rolled_back.rollback_of_receipt_id == original.receipt_id
    assert coordinator.rollback(rollback_request) == rolled_back
    head = store.head
    restored = store.load_state()
    assert head.state_version == 2
    assert head.state_digest != fixture.bias0.state_digest
    assert restored["previous_digest"] == fixture.bias1.state_digest
    assert restored["stable"] == fixture.bias0.to_dict()["stable"]
    assert restored["memory"] == fixture.bias0.to_dict()["memory"]
    assert len(store.trace_events()) == 2
    assert verify_trace_chain(store.trace_events())
    projection = reconstruct_trace(store.trace_events())
    assert projection[-1]["post_state_digest"] == head.state_digest
    assert store.verify_integrity()
    database = store.path
    store.close()
    with SQLiteAtomicStore(database) as reopened:
        assert reopened.verify_integrity()
        assert reopened.head.state_version == 2


def test_integrity_semantically_reconstructs_every_older_trace(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    original = coordinator.commit(_batch(fixture))
    _rollback_commit(coordinator, original, tick=2, suffix="older-trace")

    row = store._connection.execute(  # noqa: SLF001 - adversarial row mutation
        "SELECT record_id, payload_json FROM transition_batches "
        "WHERE commit_receipt_id = ?",
        (original.receipt_id,),
    ).fetchone()
    payload = json.loads(row["payload_json"])
    payload["runtime_id"] = "tampered-runtime"
    payload_json = canonical_json(payload)
    checksum = hashlib.sha256(payload_json.encode("ascii")).hexdigest()
    store._connection.execute(  # noqa: SLF001
        "DROP TRIGGER transition_batches_immutable_update"
    )
    store._connection.execute(  # noqa: SLF001
        "UPDATE transition_batches SET payload_sha256 = ?, payload_json = ? "
        "WHERE record_id = ?",
        (checksum, payload_json, row["record_id"]),
    )
    with pytest.raises(PersistenceError, match="request digest/batch binding"):
        store.reconstruct_transition(original.trace_id)
    assert store.verify_integrity() is False
    store.close()


def test_selected_reconstruction_binds_trace_payload_to_trace_row(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    receipt = coordinator.commit(_batch(fixture))
    replacement_digest = "a" * 64
    store._connection.execute("PRAGMA foreign_keys = OFF")  # noqa: SLF001
    store._connection.execute(  # noqa: SLF001
        "DROP TRIGGER trace_events_immutable_update"
    )
    store._connection.execute(  # noqa: SLF001
        "DROP TRIGGER commit_receipts_immutable_update"
    )
    store._connection.execute(  # noqa: SLF001
        "UPDATE trace_events SET trace_digest = ? WHERE trace_id = ?",
        (replacement_digest, receipt.trace_id),
    )
    store._connection.execute(  # noqa: SLF001
        "UPDATE commit_receipts SET trace_digest = ? WHERE receipt_id = ?",
        (replacement_digest, receipt.receipt_id),
    )
    with pytest.raises(PersistenceError, match="trace event failed verification"):
        store.reconstruct_transition(receipt.trace_id)
    assert store.verify_integrity() is False
    store.close()


def test_double_rollback_reconstruction_closes_transitive_origins(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    original = coordinator.commit(_batch(fixture))
    first = _rollback_commit(coordinator, original, tick=2, suffix="first")
    second = _rollback_commit(coordinator, first, tick=3, suffix="second")

    transition = store.reconstruct_transition(second.trace_id)
    prior_ids = {
        item["receipt_id"]
        for item in transition["prior_dependencies"]["commit_receipts"]
    }
    assert prior_ids == {original.receipt_id, first.receipt_id}
    assert store.verify_integrity()
    store.close()


def test_single_bias_coordinator_fails_closed_on_repair_frames(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    receipt_identity = canonical_digest(
        {
            "tick": 1,
            "verifier_id": "semantic-verifier",
            "verifier_version": 1,
            "verifier_digest": SOFTWARE_DIGEST,
            "cause_id": fixture.cause.cause_id,
            "candidate_effect_id": fixture.candidate.candidate_effect_id,
            "candidate_effect_digest": fixture.candidate.candidate_digest,
            "bias_digest": fixture.bias0.state_digest,
            "contract_digest": OPERATION_DIGEST,
            "outcome": SemanticOutcome.OPPOSITE.value,
            "disposition": VerifierDisposition.REPAIR.value,
            "reason_codes": ["EXACT_OPPOSITE_MATCH"],
            "evidence_refs": ["fixture:oracle"],
        }
    )
    verifier = VerifierReceipt(
        receipt_id=f"verifier-receipt-{receipt_identity}",
        tick=1,
        verifier_id="semantic-verifier",
        verifier_version=1,
        verifier_digest=SOFTWARE_DIGEST,
        independent=True,
        cause_id=fixture.cause.cause_id,
        candidate_effect_id=fixture.candidate.candidate_effect_id,
        candidate_effect_digest=fixture.candidate.candidate_digest,
        bias_id=fixture.bias0.bias_id,
        bias_version=fixture.bias0.version,
        bias_digest=fixture.bias0.state_digest,
        operation_contract_id=fixture.candidate.operation_contract_id,
        operation_contract_digest=OPERATION_DIGEST,
        model_digest=fixture.model_artifact.sha256,
        semantic_outcome=SemanticOutcome.OPPOSITE,
        disposition=VerifierDisposition.REPAIR,
        reason_codes=("EXACT_OPPOSITE_MATCH",),
        evidence_refs=("fixture:oracle",),
        repair_required=True,
        receipt_digest=H0,
    )
    verifier = _sealed(verifier, "receipt_digest")
    frame, _ = open_repair(
        cause=fixture.cause,
        candidate=fixture.candidate,
        receipt=verifier,
        bias=fixture.bias0,
    )
    forged = _sealed(replace(frame, cycle_key="f" * 64, frame_digest=H0), "frame_digest")
    before = store.head
    with pytest.raises(BatchRejected, match="REPAIR_REQUIRES_NETWORK_COORDINATOR"):
        coordinator.commit(
            _batch(
                fixture,
                verifier_receipts=(verifier,),
                repair_frames=(forged,),
            )
        )
    assert store.head == before
    assert store.trace_events() == ()
    store.close()


@pytest.mark.parametrize(
    ("case", "target_path"),
    (
        ("memory_root", "/memory"),
        ("memory_repair_frames", "/memory/repair_frame_ids"),
        ("memory_provenance", "/memory/provenance_refs"),
        ("rpm_root", "/rpm"),
        ("rpm_open", "/rpm/open_repair_ids"),
        ("rpm_suspended_parent", "/rpm/suspended_parent_cause_id"),
        ("rpm_return_address", "/rpm/return_addresses"),
        ("rpm_history", "/rpm/repair_history"),
        ("rpm_readiness", "/rpm/readiness"),
        ("operating_root", "/operating"),
        ("operating_outcome", "/operating/semantic_outcome"),
        ("operating_tick", "/operating/last_tick"),
        ("theta_root", "/theta"),
        ("theta_beta", "/theta/beta_microunits"),
        ("theta_profile", "/theta/operating_profile_id"),
    ),
)
def test_single_bias_coordinator_rejects_every_state_update_before_write(
    tmp_path: Path,
    case: str,
    target_path: str,
) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    repair_id = "repair-ghost"
    replacements = {
        "memory_root": {
            **fixture.bias0.memory.to_dict(),
            "repair_frame_ids": [repair_id],
            "provenance_refs": ["forged:human-approved"],
        },
        "memory_repair_frames": [repair_id],
        "memory_provenance": ["forged:human-approved"],
        "rpm_root": {
            **fixture.bias0.rpm.to_dict(),
            "open_repair_ids": [repair_id],
            "suspended_parent_cause_id": fixture.cause.cause_id,
            "return_addresses": [
                f"cjt:{fixture.bias0.cjt_id}:cause:{fixture.cause.cause_id}"
            ],
            "repair_history": [repair_id],
        },
        "rpm_open": [repair_id],
        "rpm_suspended_parent": fixture.cause.cause_id,
        "rpm_return_address": [
            f"cjt:{fixture.bias0.cjt_id}:cause:{fixture.cause.cause_id}"
        ],
        "rpm_history": [repair_id],
        "rpm_readiness": {
            **fixture.bias0.rpm.readiness.to_dict(),
            "profile_id": "forged-readiness-profile/9.9",
        },
        "operating_root": {
            **fixture.bias0.operating.to_dict(),
            "semantic_outcome": SemanticOutcome.OPPOSITE.value,
            "last_tick": 77,
        },
        "operating_outcome": SemanticOutcome.OPPOSITE.value,
        "operating_tick": 77,
        "theta_root": {
            **fixture.bias0.theta.to_dict(),
            "beta_microunits": 999_999,
            "operating_profile_id": "forged-operating-profile/9.9",
        },
        "theta_beta": 999_999,
        "theta_profile": "forged-operating-profile/9.9",
    }
    replacement = replacements[case]

    after = fixture.bias1.to_dict()
    cursor = after
    pointer_parts = target_path.removeprefix("/").split("/")
    for part in pointer_parts[:-1]:
        cursor = cursor[part]
    cursor[pointer_parts[-1]] = replacement
    after["state_digest"] = canonical_digest(after, omit_keys=("state_digest",))

    intent = {
        "contract_type": StateUpdateIntent.CONTRACT_TYPE,
        "schema_version": StateUpdateIntent.SCHEMA_VERSION,
        "intent_id": f"state-forgery-{case}",
        "tick": 1,
        "issuer_id": "cjt-1",
        "authority_capability": PROPOSE_STATE_UPDATE,
        "target_bias_id": fixture.bias0.bias_id,
        "expected_bias_version": fixture.bias0.version,
        "expected_bias_digest": fixture.bias0.state_digest,
        "target_path": target_path,
        "replacement": replacement,
        "verifier_receipt_id": fixture.verifier.receipt_id,
        "reason_codes": ["FORGED_STATE_PROJECTION"],
        "intent_digest": H0,
    }
    intent["intent_digest"] = canonical_digest(intent, omit_keys=("intent_digest",))

    head_before = store.head
    with pytest.raises(BatchRejected, match="STATE_UPDATE_REQUIRES_NETWORK_COORDINATOR"):
        coordinator.commit(
            _batch(fixture, bias_after=after, state_intents=(intent,))
        )
    assert store.head == head_before
    assert store.trace_events() == ()
    for table in (
        "commit_receipts",
        "transition_batches",
        "candidate_effects",
        "verifier_receipts",
        "state_intents",
        "repair_frames",
        "published_effects",
    ):
        assert store._connection.execute(  # noqa: SLF001 - no-write boundary assertion
            f"SELECT count(*) FROM {table}"
        ).fetchone()[0] == 0
    audits = store.rejection_audits()
    assert len(audits) == 1
    assert audits[0]["reason_codes"] == ["STATE_UPDATE_REQUIRES_NETWORK_COORDINATOR"]
    assert store.verify_integrity()
    store.close()


def test_memory_write_restarts_and_reads_through_bounded_candidate_interface(
    tmp_path: Path,
) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    intent = MemoryWriteIntent(
        intent_id="memory-intent-1",
        tick=1,
        issuer_id="cjt-1",
        authority_capability=PROPOSE_MEMORY_WRITE,
        target_bias_id=fixture.bias0.bias_id,
        expected_bias_version=fixture.bias0.version,
        expected_bias_digest=fixture.bias0.state_digest,
        memory_record_id="memory-record-1",
        memory_kind=MemoryKind.EPISODIC,
        content={"cause_id": fixture.cause.cause_id, "lesson": "verified"},
        content_ref=None,
        confidence_ppm=910_000,
        provenance=(fixture.verifier.receipt_id,),
        evidence_refs=("fixture:oracle",),
        verifier_receipt_id=fixture.verifier.receipt_id,
        intent_digest=H0,
    )
    intent = _sealed(intent, "intent_digest")
    receipt = coordinator.commit(_batch(fixture, memory_intents=(intent,)))
    record = store.immutable_document("memory_records", intent.memory_record_id)
    assert record["source_intent_id"] == intent.intent_id
    assert verify_declared_digest(record, "record_digest")
    assert store.immutable_document("memory_intents", intent.intent_id)["intent_digest"] == intent.intent_digest
    database = store.path
    store.close()
    with SQLiteAtomicStore(database) as reopened:
        candidate_memories = retrieve_memory(
            reopened,
            (intent.memory_record_id, "not-permitted"),
            permitted_ids=(intent.memory_record_id,),
            max_reads=1,
        )
        assert candidate_memories == (
            {
                "memory_record_id": intent.memory_record_id,
                "memory_kind": "EPISODIC",
                "content": {"cause_id": fixture.cause.cause_id, "lesson": "verified"},
                "content_ref": None,
                "confidence_ppm": 910_000,
                "provenance": [fixture.verifier.receipt_id],
                "candidate_only": True,
            },
        )
        transition = reopened.reconstruct_transition(receipt.trace_id)
        assert transition["memory_intents"][0]["intent_id"] == intent.intent_id
        assert transition["memory_records"][0]["memory_record_id"] == intent.memory_record_id
        assert reopened.verify_integrity()


def _model_update_batch(fixture: Fixture) -> tuple[CommitBatch, object]:
    new_reference, new_artifact = _ref(
        torch.tensor([9.0, 8.0, 7.0], dtype=torch.float32)
    )
    next_theta = replace(
        fixture.bias0.theta,
        model_version=1,
        model_digest=new_artifact.sha256,
        parameter_artifacts=(new_reference,),
    )
    next_bias = replace(
        fixture.bias0,
        version=1,
        previous_digest=fixture.bias0.state_digest,
        theta=next_theta,
        state_digest=H0,
    )
    next_bias = _sealed(next_bias, "state_digest")
    state_intent = StateUpdateIntent(
        intent_id="state-intent-model-1",
        tick=1,
        issuer_id="cjt-1",
        authority_capability=PROPOSE_STATE_UPDATE,
        target_bias_id=fixture.bias0.bias_id,
        expected_bias_version=0,
        expected_bias_digest=fixture.bias0.state_digest,
        target_path="/theta",
        replacement=next_theta.to_dict(),
        verifier_receipt_id=fixture.verifier.receipt_id,
        reason_codes=("QUALIFIED_MODEL",),
        intent_digest=H0,
    )
    state_intent = _sealed(state_intent, "intent_digest")
    qualification_body = {
        "schema_version": "cas.neural-cjt.qualification-receipt/0.2",
        "qualification_receipt_id": "qualification-1",
        "policy_id": "fixture-learning-policy/0.2",
        "independent": True,
        "candidate_model_digest": new_artifact.sha256,
        "disposition": "QUALIFIED",
        "baseline_metrics_microunits": {"target_loss": 500_000},
        "candidate_metrics_microunits": {"target_loss": 400_000},
        "target_improved": True,
        "retention_passed": True,
        "regression_passed": True,
        "qualified": True,
        "reason_codes": ["TARGET_IMPROVED", "RETENTION_PASSED", "REGRESSION_PASSED"],
    }
    qualification = {
        **qualification_body,
        "receipt_digest": canonical_digest(qualification_body),
    }
    model_intent = ModelUpdateIntent(
        intent_id="model-intent-1",
        tick=1,
        issuer_id="prototype-write-back-controller",
        authority_capability="PROPOSE_MODEL_UPDATE",
        model_id="model-1",
        expected_model_version=0,
        expected_model_digest=fixture.bias0.theta.model_digest,
        update_kind=ModelUpdateKind.CHECKPOINT_REPLACEMENT,
        parameter_group_ids=("operator.^6",),
        candidate_artifact=new_reference,
        gradient_artifact=None,
        plasticity_ppm=500_000,
        verifier_receipt_id=fixture.verifier.receipt_id,
        qualification_receipt_id="qualification-1",
        reason_codes=("QUALIFIED",),
        intent_digest=H0,
    )
    model_intent = _sealed(model_intent, "intent_digest")
    model_version = ModelVersionWrite(
        model_digest=new_artifact.sha256,
        parent_model_digest=fixture.bias0.theta.model_digest,
        artifact_id=new_artifact.artifact_id,
        payload={
            "schema_version": "cas.neural-cjt.model-version/0.2",
            "model_id": "model-1",
            "model_version": 1,
            "model_digest": new_artifact.sha256,
            "model_artifact_ref": {
                "artifact_id": new_artifact.artifact_id,
                "sha256": new_artifact.sha256,
            },
            "parent_model_digest": fixture.bias0.theta.model_digest,
            "qualification_receipt_id": "qualification-1",
        },
    )
    return (
        _batch(
            fixture,
            bias_after=next_bias,
            state_intents=(state_intent,),
            model_intents=(model_intent,),
            qualification_receipts=(qualification,),
            model_version=model_version,
            artifacts=(fixture.effect_artifact, new_artifact),
        ),
        new_artifact,
    )


def test_single_bias_coordinator_rejects_model_updates_before_write(tmp_path: Path) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    batch, new_artifact = _model_update_batch(fixture)
    head_before = store.head
    with pytest.raises(BatchRejected, match="MODEL_UPDATE_REQUIRES_NETWORK_COORDINATOR"):
        coordinator.commit(batch)
    assert store.head == head_before
    assert not store.has_artifact(new_artifact.artifact_id)
    assert store.trace_events() == ()
    assert store._connection.execute(  # noqa: SLF001 - no-write boundary assertion
        "SELECT count(*) FROM model_intents"
    ).fetchone()[0] == 0
    assert store._connection.execute(  # noqa: SLF001
        "SELECT count(*) FROM qualification_receipts"
    ).fetchone()[0] == 0
    assert store._connection.execute(  # noqa: SLF001
        "SELECT count(*) FROM model_versions"
    ).fetchone()[0] == 1
    audits = store.rejection_audits()
    assert len(audits) == 1
    assert audits[0]["reason_codes"] == ["MODEL_UPDATE_REQUIRES_NETWORK_COORDINATOR"]
    assert store.verify_integrity()
    store.close()


def test_single_bias_coordinator_rejects_resealed_qualification_arithmetic(
    tmp_path: Path,
) -> None:
    fixture = _fixture()
    store, coordinator = _open(tmp_path, fixture)
    batch, new_artifact = _model_update_batch(fixture)
    qualification = dict(batch.qualification_receipts[0])
    qualification["candidate_metrics_microunits"] = {"target_loss": 900_000}
    qualification["receipt_digest"] = canonical_digest(
        qualification,
        omit_keys=("receipt_digest",),
    )
    poisoned = replace(
        batch,
        batch_id="batch-forged-qualification",
        qualification_receipts=(qualification,),
    )

    head_before = store.head
    with pytest.raises(BatchRejected, match="MODEL_UPDATE_REQUIRES_NETWORK_COORDINATOR"):
        coordinator.commit(poisoned)
    assert store.head == head_before
    assert not store.has_artifact(new_artifact.artifact_id)
    assert store.trace_events() == ()
    assert store._connection.execute(  # noqa: SLF001 - no-write boundary assertion
        "SELECT count(*) FROM model_intents"
    ).fetchone()[0] == 0
    assert store._connection.execute(  # noqa: SLF001
        "SELECT count(*) FROM qualification_receipts"
    ).fetchone()[0] == 0
    assert store.verify_integrity()
    store.close()


def test_trace_tamper_and_chain_discontinuity_are_detected() -> None:
    phases1 = _phases(1)
    first = seal_trace(
        {
            "tick": 1,
            "runtime_id": "runtime",
            "software_digest": SOFTWARE_DIGEST,
            "cause_id": "cause-1",
            "cjt_ids": ["cjt-1"],
            "pre_state_digest": "1" * 64,
            "post_state_digest": "2" * 64,
            "pre_model_digest": "3" * 64,
            "post_model_digest": "3" * 64,
            "phases": phases1,
            "candidate_effect_ids": [],
            "published_effect_ids": [],
            "verifier_receipt_ids": [],
            "commit_receipt_id": "commit-1",
            "memory_read_refs": [],
            "memory_write_refs": [],
            "accepted_intent_ids": ["intent-1"],
            "rejected_intent_ids": [],
            "sealed": True,
        },
        previous_trace_digest=None,
    )
    second = seal_trace(
        {
            "tick": 2,
            "runtime_id": "runtime",
            "software_digest": SOFTWARE_DIGEST,
            "cause_id": "cause-2",
            "cjt_ids": ["cjt-1"],
            "pre_state_digest": "2" * 64,
            "post_state_digest": "4" * 64,
            "pre_model_digest": "3" * 64,
            "post_model_digest": "3" * 64,
            "phases": _phases(2),
            "candidate_effect_ids": [],
            "published_effect_ids": [],
            "verifier_receipt_ids": [],
            "commit_receipt_id": "commit-2",
            "memory_read_refs": [],
            "memory_write_refs": [],
            "accepted_intent_ids": ["intent-2"],
            "rejected_intent_ids": [],
            "sealed": True,
        },
        previous_trace_digest=first.trace_digest,
    )
    assert verify_trace(first.payload)
    assert verify_trace_chain((first.payload, second.payload))
    tampered = dict(second.payload)
    tampered["cause_id"] = "changed"
    assert not verify_trace(tampered)
    disconnected = dict(second.payload)
    disconnected["pre_state_digest"] = "8" * 64
    disconnected = seal_trace(
        {
            key: value
            for key, value in disconnected.items()
            if key not in {"trace_id", "trace_digest", "previous_trace_digest", "contract_type", "schema_version"}
        },
        previous_trace_digest=first.trace_digest,
    )
    assert not verify_trace_chain((first.payload, disconnected.payload))


def test_initialize_refuses_unretained_model_digest(tmp_path: Path) -> None:
    fixture = _fixture()
    with SQLiteAtomicStore(tmp_path / "bad-bootstrap.sqlite3") as store:
        with pytest.raises(PersistenceError, match="initial_model_version"):
            store.initialize(
                state_digest=fixture.bias0.state_digest,
                state_version=0,
                state_payload=fixture.bias0,
                model_digest=fixture.model_artifact.sha256,
            )
