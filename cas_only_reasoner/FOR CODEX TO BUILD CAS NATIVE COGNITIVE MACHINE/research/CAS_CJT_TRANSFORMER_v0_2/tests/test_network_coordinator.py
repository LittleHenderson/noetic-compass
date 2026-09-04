from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, replace
import hashlib
import json
from pathlib import Path

import pytest
import torch
from torch import nn

from cas_cjt.artifacts import encode_tensor
from cas_cjt.checkpoint import checkpoint_entry_digests, encode_module_checkpoint
from cas_cjt.contracts import canonical_digest, canonical_json
from cas_cjt.learning import (
    QUALIFICATION_RECEIPT_SCHEMA_VERSION,
    LearningPolicy,
    QualificationReceipt,
)
from cas_cjt.memory import propose_memory_write
from cas_cjt.network_coordinator import (
    NetworkAtomicCoordinator,
    NetworkBatchRejected,
    NetworkCommitBatch,
    NetworkStateEnvelope,
)
from cas_cjt.persistence import ModelVersionWrite, PersistenceError, SQLiteAtomicStore
from cas_cjt.semantic import (
    DecoderContract,
    DeterministicSemanticDecoder,
    make_bound_evidence,
)
from cas_cjt.proposals import state_update_intents_for_successor
from cas_cjt.state import (
    advance_bias,
    cause_from_committed_effect,
    content_id,
    make_cause,
    make_initial_bias,
    make_operation_contract,
)
from cas_cjt.trace import MANDATORY_PHASES
from cas_cjt.types import (
    AuthorityCapability,
    BiasState,
    CandidateEffect,
    CauseKind,
    CausePacket,
    MemoryKind,
    MemoryWriteIntent,
    ModelUpdateIntent,
    ModelUpdateKind,
    OperatingRegion,
    PhaseRecord,
    SemanticOutcome,
    StateUpdateIntent,
    TensorArtifactRef,
    TickPhase,
    VerifierDisposition,
)
from cas_cjt.verifier import IndependentVerifier


ZERO_DIGEST = "0" * 64
SOFTWARE_DIGEST = "b" * 64
COORDINATOR_ID = "prototype-atomic-coordinator"
AUTHORITY_ID = "cas.network-atomic-authority/0.2"
MODEL_ID = "three-cjt-model"
MODEL_MANIFEST_CONTEXT = {
    "network": {
        "nodes": ["cjt-a", "cjt-b", "cjt-c"],
        "edges": [],
    },
    "config": {"fixture_model": "ThreeCJTModel", "input_width": 2},
    "decoder_labels": ["NO_EFFECT", "PARTS_FOUND"],
}


class ThreeCJTModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.cjt_a = nn.Linear(2, 2, bias=False)
        self.cjt_b = nn.Linear(2, 2, bias=False)
        self.cjt_c = nn.Linear(2, 2, bias=False)
        with torch.no_grad():
            self.cjt_a.weight.copy_(torch.tensor([[1.0, 2.0], [3.0, 4.0]]))
            self.cjt_b.weight.copy_(torch.tensor([[5.0, 6.0], [7.0, 8.0]]))
            self.cjt_c.weight.copy_(torch.tensor([[9.0, 10.0], [11.0, 12.0]]))


def _sealed(value, field_name: str):
    return replace(
        value,
        **{field_name: canonical_digest(value.to_dict(), omit_keys=(field_name,))},
    )


def _successor_bias(old: BiasState, **changes) -> BiasState:
    draft = replace(
        old,
        version=old.version + 1,
        previous_digest=old.state_digest,
        state_digest=ZERO_DIGEST,
        **changes,
    )
    return _sealed(draft, "state_digest")


def _reidentify_candidate(
    candidate: CandidateEffect, **changes
) -> CandidateEffect:
    draft = replace(
        candidate,
        candidate_effect_id="pending",
        candidate_digest=ZERO_DIGEST,
        **changes,
    )
    identity = {
        "tick": draft.tick,
        "parent_cause_id": draft.parent_cause_id,
        "producer_cjt_id": draft.producer_cjt_id,
        "operation_contract_digest": draft.operation_contract_digest,
        "bias_digest": draft.bias_digest,
        "model_digest": draft.model_digest,
        "content": draft.content,
        "content_ref": None if draft.content_ref is None else draft.content_ref.to_dict(),
    }
    return _sealed(
        replace(
            draft,
            candidate_effect_id=content_id("candidate-effect", identity),
        ),
        "candidate_digest",
    )


def _reidentify_receipt(receipt, **changes):
    draft = replace(
        receipt,
        receipt_id="pending",
        receipt_digest=ZERO_DIGEST,
        **changes,
    )
    identity_digest = canonical_digest(
        {
            "tick": draft.tick,
            "verifier_id": draft.verifier_id,
            "verifier_version": draft.verifier_version,
            "verifier_digest": draft.verifier_digest,
            "cause_id": draft.cause_id,
            "candidate_effect_id": draft.candidate_effect_id,
            "candidate_effect_digest": draft.candidate_effect_digest,
            "bias_digest": draft.bias_digest,
            "contract_digest": draft.operation_contract_digest,
            "outcome": draft.semantic_outcome.value,
            "disposition": draft.disposition.value,
            "reason_codes": list(draft.reason_codes),
            "evidence_refs": list(draft.evidence_refs),
        }
    )
    return _sealed(
        replace(
            draft,
            receipt_id=f"verifier-receipt-{identity_digest}",
        ),
        "receipt_digest",
    )


def _rebind_receipt_phases(
    records: tuple[PhaseRecord, ...],
    receipt,
) -> tuple[PhaseRecord, ...]:
    result = records
    verify = next(item for item in result if item.phase is TickPhase.VERIFY)
    result = _replace_phase(
        result,
        TickPhase.VERIFY,
        outputs={
            **dict(verify.outputs),
            "verifier_receipt_ids": (receipt.receipt_id,),
            "semantic_outcomes": (receipt.semantic_outcome.value,),
            "dispositions": (receipt.disposition.value,),
        },
    )
    diagnose = next(item for item in result if item.phase is TickPhase.DIAGNOSE)
    result = _replace_phase(
        result,
        TickPhase.DIAGNOSE,
        inputs={
            **dict(diagnose.inputs),
            "semantic_outcomes": (receipt.semantic_outcome.value,),
        },
        outputs={
            **dict(diagnose.outputs),
            "reason_codes": tuple(receipt.reason_codes),
            "repair_required": receipt.repair_required,
        },
    )
    emit = next(item for item in result if item.phase is TickPhase.EMIT)
    return _replace_phase(
        result,
        TickPhase.EMIT,
        inputs={"verifier_receipt_ids": (receipt.receipt_id,)},
        outputs={
            **dict(emit.outputs),
            "publication_requested": (
                receipt.disposition is VerifierDisposition.ACCEPT
            ),
        },
    )


def _bind_candidate_to_phases(
    candidate: CandidateEffect,
    records: tuple[PhaseRecord, ...],
) -> CandidateEffect:
    binding_digest = next(
        item.diagnostics["control_binding_digest"]
        for item in records
        if item.phase is TickPhase.OBSERVE
    )
    decoder = next(
        item for item in candidate.provenance if item.startswith("decoder:")
    )
    provenance = (
        f"cause:{candidate.parent_cause_id}",
        f"bias:{candidate.bias_digest}",
        f"model:{candidate.model_digest}",
        decoder,
        f"control-binding:{binding_digest}",
    )
    return _reidentify_candidate(candidate, provenance=provenance)


@dataclass
class Fixture:
    store: SQLiteAtomicStore
    coordinator: NetworkAtomicCoordinator
    model: ThreeCJTModel
    checkpoint: object
    state: NetworkStateEnvelope
    cause: object
    contract: object
    decoder_contract: DecoderContract
    decoder: DeterministicSemanticDecoder
    candidate: CandidateEffect
    receipt: object
    evidence_descriptor: dict
    effect_artifact: object


def _phases(
    *,
    tick: int,
    before: NetworkStateEnvelope,
    after: NetworkStateEnvelope,
    cause_id: str,
    candidate_ids: tuple[str, ...] = (),
    receipt_ids: tuple[str, ...] = (),
    operation_ids: tuple[str, ...] = (),
    operation_contract_ids: tuple[str, ...] = (),
    state_intent_ids: tuple[str, ...] = (),
    model_intent_ids: tuple[str, ...] = (),
    memory_intent_ids: tuple[str, ...] = (),
    reason_codes: tuple[str, ...] = (),
    artifact_ids: tuple[str, ...] = (),
    memory_read_refs: tuple[str, ...] = (),
    zero_flow: bool = False,
    control_cjt_id: str = "cjt-a",
) -> tuple[PhaseRecord, ...]:
    cjt_ids = tuple(item.cjt_id for item in before.biases)
    bias_ids = tuple(item.bias_id for item in before.biases)
    bias_digests = tuple(item.state_digest for item in before.biases)
    control_bias = before.by_cjt_id[control_cjt_id]
    ceiling = control_bias.governance.compute_ceiling_units
    scheduled = () if zero_flow else (control_cjt_id,)
    semantic_outcomes = () if not receipt_ids else tuple("INTENDED" for _ in receipt_ids)
    dispositions = () if not receipt_ids else tuple("ACCEPT" for _ in receipt_ids)
    evidence_ids = () if not receipt_ids else tuple("oracle-evidence" for _ in receipt_ids)
    active = not zero_flow
    raw_value = 0 if zero_flow else 1_000_000
    total_value = 0 if zero_flow else 3_000_000
    quantum_value = 0 if zero_flow else 3
    reasoning_used = 0 if zero_flow else 1
    route_mask = [[[active, active, active]]]
    hard_route_mask = [[[True, True, True]]]
    route_settings = {
        "drive_units": raw_value,
        "resistance_capability_units": 250_000,
        "resistance_context_units": 250_000,
        "resistance_resource_units": 250_000,
        "resistance_memory_units": 250_000,
        "unit_scale": 1_000_000,
        "causal": False,
        "topology_open": True,
        "permission_open": True,
        "budget_open": True,
        "force_breakdown": False,
    }
    native_compute = {
        "contract_type": "NATIVE_COMPUTE_INPUTS",
        "schema_version": "cas.neural-cjt.native-compute-inputs/0.2",
        "drive_units": [[[raw_value, raw_value, raw_value]]],
        "resistance_units": [[[1_000_000, 1_000_000, 1_000_000]]],
        "canonical_route_ids": ["route-a", "route-b", "route-c"],
        "flow_scale_units": 1_000_000,
    }
    compute_policy = {
        "contract_type": "NATIVE_COMPUTE_POLICY",
        "schema_version": "cas.neural-cjt.native-compute-policy/0.2",
        "policy_id": "cas.cjt.compute/0.2",
        "flow_units_per_quantum": 1_000_000,
        "max_routes": ceiling,
        "max_reasoning_steps": ceiling,
        "max_branches": min(4, ceiling),
        "max_memory_reads": min(4, ceiling),
        "max_diagnostic_probes": min(4, ceiling),
    }
    compute_plan = {
        "contract_type": "PREDECLARED_COMPUTE_PLAN",
        "schema_version": "cas.neural-cjt.predeclared-compute-plan/0.2",
        "policy_id": "cas.cjt.compute/0.2",
        "canonical_route_ids": ["route-a", "route-b", "route-c"],
        "source_raw_flow_units": [[[raw_value, raw_value, raw_value]]],
        "source_total_flow_units": [[total_value]],
        "scheduled_route_mask": route_mask,
        "route_quanta": [[quantum_value]],
        "reasoning_step_quanta": [[quantum_value]],
        "branch_quanta": [[quantum_value]],
        "memory_read_quanta": [[quantum_value]],
        "diagnostic_probe_quanta": [[quantum_value]],
    }
    control_binding_manifest = {
        "schema_version": "cas.neural-cjt.control-binding/0.2",
        "cause_id": cause_id,
        "cause_artifact_id": None,
        "cause_artifact_digest": None,
        "bias_id": control_bias.bias_id,
        "bias_version": control_bias.version,
        "bias_digest": control_bias.state_digest,
        "recurrent_bias_artifact_id": None,
        "recurrent_bias_digest": None,
        "model_digest": before.model_digest,
        "declared_beta_microunits": control_bias.theta.beta_microunits,
        "live_beta_by_head_microunits": [
            control_bias.theta.beta_microunits
        ],
        "readiness_profile_id": control_bias.rpm.readiness.profile_id,
        "operating_region": control_bias.operating.region.value,
        "governance_permissions": list(
            control_bias.governance.hard_permissions
        ),
        "route_settings": route_settings,
        "native_compute": native_compute,
        "compute_policy": compute_policy,
        "hard_masks": {
            "topology_mask": hard_route_mask,
            "permission_mask": [[[True, True, True]]],
            "quarantine_mask": [[[False, False, False]]],
            "budget_mask": [[[True, True, True]]],
            "readiness_hard_mask": [[[True, True, True]]],
        },
        "compute_plan": compute_plan,
        "memory_read_requests": list(memory_read_refs),
        "memory_reads": [
            {"memory_record_id": item} for item in memory_read_refs
        ],
    }
    control_binding_digest = canonical_digest(control_binding_manifest)
    observations = {
        "routes_executed": [[quantum_value]],
        "reasoning_steps_used": [[reasoning_used]],
        "branches_opened": [[0]],
        "memory_reads_used": [[min(quantum_value, len(memory_read_refs))]],
        "diagnostic_probes_used": [[0]],
    }
    effective_reasons = (
        reason_codes
        if reason_codes
        else (("EXACT_SEMANTIC_MATCH",) if receipt_ids else ())
    )
    eligible_cjt_ids = tuple(
        bias.cjt_id
        for bias in sorted(before.biases, key=lambda item: item.cjt_id)
        if bias.stable.registered_operation_id in set(operation_ids)
    )
    eligible_contract_ids = tuple(
        make_operation_contract(before.by_cjt_id[cjt_id].stable.registered_operation_id).contract_id
        for cjt_id in eligible_cjt_ids
    )
    records = {
        TickPhase.READ: (
            {
                "cause_id": cause_id,
                "state_digest": before.state_digest,
                "model_digest": before.model_digest,
            },
            {
                "bias_ids": bias_ids,
                "bias_digests": bias_digests,
                "memory_read_refs": memory_read_refs,
            },
        ),
        TickPhase.CANDIDATE: (
            {"candidate_operation_ids": operation_ids},
            {
                "candidate_cjt_ids": eligible_cjt_ids,
                "operation_contract_ids": eligible_contract_ids,
            },
        ),
        TickPhase.READINESS: (
            {"profile_ids": (control_bias.rpm.readiness.profile_id,)},
            {
                "desire": control_bias.rpm.readiness.desire.to_dict(),
                "wisdom": control_bias.rpm.readiness.wisdom.to_dict(),
                "power": control_bias.rpm.readiness.power.to_dict(),
                "hard_open": control_bias.rpm.readiness.hard_open,
            },
        ),
        TickPhase.ROUTE: (
            {
                "control_cjt_id": control_cjt_id,
                "topology_mask": hard_route_mask,
                "permission_mask": [[[True, True, True]]],
                "quarantine_mask": [[[False, False, False]]],
                "budget_mask": [[[True, True, True]]],
                "readiness_hard_mask": [[[True, True, True]]],
                "route_settings": route_settings,
                "native_compute": native_compute,
                "compute_policy": compute_policy,
                "control_binding_manifest": control_binding_manifest,
            },
            {
                "compute_plan": compute_plan,
                "effective_path_mask": route_mask,
                "conducting_query_mask": [[active]],
                "current_microunits": [[[raw_value, raw_value, raw_value]]],
                "total_current_microunits": [[total_value]],
                "flow_allocation_ppm": [
                    [[0, 0, 0]] if zero_flow else [[333_334, 333_333, 333_333]]
                ],
            },
        ),
        TickPhase.EXECUTE: (
            {"scheduled_cjt_ids": scheduled, "operation_ids": operation_ids},
            {
                "executed_cjt_ids": () if zero_flow else scheduled,
                "compute_units_used": reasoning_used,
            },
        ),
        TickPhase.OBSERVE: (
            {"executed_cjt_ids": () if zero_flow else scheduled},
            {
                "candidate_effect_ids": candidate_ids,
                "operating_regions": tuple("ACTIVE" for _ in candidate_ids),
                "artifact_ids": artifact_ids,
                "compute_observations": observations,
            },
        ),
        TickPhase.VERIFY: (
            {"candidate_effect_ids": candidate_ids, "evidence_ids": evidence_ids},
            {
                "verifier_receipt_ids": receipt_ids,
                "semantic_outcomes": semantic_outcomes,
                "dispositions": dispositions,
            },
        ),
        TickPhase.DIAGNOSE: (
            {
                "operating_regions": tuple("ACTIVE" for _ in candidate_ids),
                "semantic_outcomes": semantic_outcomes,
            },
            {"reason_codes": effective_reasons, "repair_required": False},
        ),
        TickPhase.EMIT: (
            {"verifier_receipt_ids": receipt_ids},
            {
                "state_intent_ids": state_intent_ids,
                "model_intent_ids": model_intent_ids,
                "memory_intent_ids": memory_intent_ids,
                "repair_ids": (),
                "repair_outcome_ids": (),
                "publication_requested": bool(candidate_ids),
            },
        ),
        TickPhase.COMMIT: (
            {
                "pre_state_digest": before.state_digest,
                "pre_model_digest": before.model_digest,
            },
            {
                "proposed_post_state_digest": after.state_digest,
                "proposed_post_model_digest": after.model_digest,
            },
        ),
        TickPhase.TRACE: (
            {"previous_trace_digest": None},
            {"seal_requested": True, "phase_count": 11},
        ),
    }
    return tuple(
        PhaseRecord(
            phase=TickPhase(name),
            tick=tick,
            inputs=records[TickPhase(name)][0],
            outputs=records[TickPhase(name)][1],
            diagnostics=(
                {
                    "control_binding_digest": control_binding_digest,
                    "declared_beta_microunits": (
                        control_bias.theta.beta_microunits
                    ),
                    "live_beta_by_head_microunits": [
                        control_bias.theta.beta_microunits
                    ],
                }
                if TickPhase(name) is TickPhase.OBSERVE
                else {}
            ),
            compute_units=(
                reasoning_used if TickPhase(name) is TickPhase.EXECUTE else 0
            ),
        )
        for name in MANDATORY_PHASES
    )


def _open(
    tmp_path: Path,
    *,
    denied_hard_permission: str | None = None,
    denied_learning_permission: str | None = None,
    denied_topology_permission: str | None = None,
    permitted_topology_edges: tuple[tuple[str, str], ...] = (),
) -> Fixture:
    model = ThreeCJTModel()
    checkpoint = encode_module_checkpoint(model)
    biases = tuple(
        make_initial_bias(
            cjt_id=cjt_id,
            operation_id="^6",
            model_id=MODEL_ID,
            model_digest=checkpoint.model_digest,
            checkpoint_ref=checkpoint.reference,
        )
        for cjt_id in ("cjt-a", "cjt-b", "cjt-c")
    )
    if (
        denied_hard_permission is not None
        or denied_learning_permission is not None
        or denied_topology_permission is not None
    ):
        adjusted = []
        for bias in biases:
            if bias.cjt_id != "cjt-a":
                adjusted.append(bias)
                continue
            governance = replace(
                bias.governance,
                hard_permissions=tuple(
                    item
                    for item in bias.governance.hard_permissions
                    if item != denied_hard_permission
                ),
                learning_permissions=tuple(
                    item
                    for item in bias.governance.learning_permissions
                    if item != denied_learning_permission
                ),
                topology_permissions=tuple(
                    item
                    for item in bias.governance.topology_permissions
                    if item != denied_topology_permission
                ),
            )
            adjusted.append(
                _sealed(
                    replace(
                        bias,
                        governance=governance,
                        state_digest=ZERO_DIGEST,
                    ),
                    "state_digest",
                )
            )
        biases = tuple(adjusted)
    state = NetworkStateEnvelope.create(
        biases,
        model_id=MODEL_ID,
        model_version=0,
        model_digest=checkpoint.model_digest,
        model_artifact_ref=checkpoint.reference,
    )
    initial_model = ModelVersionWrite(
        model_digest=checkpoint.model_digest,
        parent_model_digest=None,
        artifact_id=checkpoint.artifact.artifact_id,
        payload={
            "schema_version": "cas.neural-cjt.model-version/0.2",
            "model_id": MODEL_ID,
            "model_version": 0,
            "model_digest": checkpoint.model_digest,
            "model_artifact_ref": checkpoint.reference.to_dict(),
            **MODEL_MANIFEST_CONTEXT,
        },
    )
    store = SQLiteAtomicStore(tmp_path / "network.sqlite3")
    store.initialize(
        state_digest=state.state_digest,
        state_version=state.state_version,
        state_payload=state,
        model_digest=checkpoint.model_digest,
        initial_artifacts=(checkpoint.artifact,),
        initial_model_version=initial_model,
    )

    contract = make_operation_contract("^6")
    decoder_contract = DecoderContract(
        decoder_id="decoder-^6-v1",
        version=1,
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        labels=("NO_EFFECT", "PARTS_FOUND"),
    )
    decoder = DeterministicSemanticDecoder(decoder_contract)
    logits = torch.tensor([[0.0, 4.0]], dtype=torch.float32)
    effect_mapping, effect_artifact = encode_tensor(logits, kind="candidate-effect")
    effect_ref = TensorArtifactRef(**effect_mapping)
    bias = state.by_cjt_id["cjt-a"]
    cause = make_cause(
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"question": "what are the parts"},
        goal_context={"goal_id": "network-test"},
        candidate_operation_ids=("^6",),
    )
    control_binding_digest = next(
        item.diagnostics["control_binding_digest"]
        for item in _phases(
            tick=1,
            before=state,
            after=state,
            cause_id=cause.cause_id,
            operation_ids=("^6",),
        )
        if item.phase is TickPhase.OBSERVE
    )
    candidate_identity = {
        "tick": 1,
        "parent_cause_id": cause.cause_id,
        "producer_cjt_id": bias.cjt_id,
        "operation_contract_digest": contract.contract_digest,
        "bias_digest": bias.state_digest,
        "model_digest": state.model_digest,
        "content": decoder.decode(logits),
        "content_ref": effect_ref.to_dict(),
    }
    candidate = CandidateEffect(
        candidate_effect_id=content_id("candidate-effect", candidate_identity),
        tick=1,
        parent_cause_id=cause.cause_id,
        producer_cjt_id=bias.cjt_id,
        operation_id="^6",
        operation_contract_id=contract.contract_id,
        operation_contract_digest=contract.contract_digest,
        bias_id=bias.bias_id,
        bias_version=bias.version,
        bias_digest=bias.state_digest,
        model_digest=state.model_digest,
        content=decoder.decode(logits),
        content_ref=effect_ref,
        uncertainty_ppm=0,
        provenance=(
            f"cause:{cause.cause_id}",
            f"bias:{bias.state_digest}",
            f"model:{state.model_digest}",
            f"decoder:{decoder_contract.decoder_digest}",
            f"control-binding:{control_binding_digest}",
        ),
        candidate_digest=ZERO_DIGEST,
    )
    candidate = _sealed(candidate, "candidate_digest")
    evidence, descriptor = make_bound_evidence(
        evidence_id="oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    receipt = IndependentVerifier(contract.verifier_id).evaluate(
        cause,
        candidate,
        contract,
        evidence,
        bias=bias,
    ).receipt
    group = bias.theta.parameter_group_ids[0]
    coordinator = NetworkAtomicCoordinator(
        store,
        coordinator_id=COORDINATOR_ID,
        authority_contract_id=AUTHORITY_ID,
        runtime_id="network-runtime",
        software_digest=SOFTWARE_DIGEST,
        num_attention_heads=1,
        model_manifest_context=MODEL_MANIFEST_CONTEXT,
        operation_contracts={contract.contract_id: contract},
        decoder_contracts={
            cjt_id: decoder_contract for cjt_id in ("cjt-a", "cjt-b", "cjt-c")
        },
        permitted_topology_edges=permitted_topology_edges,
        trusted_evidence_sources=("trusted-oracle",),
        candidate_validator=decoder.validate_candidate,
        parameter_scope_prefixes={group: ("cjt_a.",)},
    )
    return Fixture(
        store=store,
        coordinator=coordinator,
        model=model,
        checkpoint=checkpoint,
        state=state,
        cause=cause,
        contract=contract,
        decoder_contract=decoder_contract,
        decoder=decoder,
        candidate=candidate,
        receipt=receipt,
        evidence_descriptor=descriptor,
        effect_artifact=effect_artifact,
    )


def _batch(fixture: Fixture, **changes) -> NetworkCommitBatch:
    old_bias = fixture.state.by_cjt_id[fixture.candidate.producer_cjt_id]
    accepted_bias = advance_bias(
        old_bias,
        tick=fixture.cause.tick,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=fixture.receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=fixture.candidate.candidate_effect_id,
    )
    after = fixture.state.successor(
        biases=(
            accepted_bias if item.bias_id == old_bias.bias_id else item
            for item in fixture.state.biases
        )
    )
    default_state_intents = state_update_intents_for_successor(
        old_bias,
        accepted_bias,
        tick=fixture.cause.tick,
        receipt=fixture.receipt,
        issuer_id=fixture.candidate.producer_cjt_id,
    )
    if "state_after" in changes and "state_intents" not in changes:
        default_state_intents = ()
    default_phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        candidate_ids=(fixture.candidate.candidate_effect_id,),
        receipt_ids=(fixture.receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        state_intent_ids=tuple(item.intent_id for item in default_state_intents),
        artifact_ids=(fixture.candidate.content_ref.artifact_id,),
    )
    phase_by_name = {item.phase: item for item in default_phases}
    values = dict(
        batch_id="network-batch-1",
        tick=1,
        base_trace_digest=None,
        state_before=fixture.state,
        state_after=after,
        cause=fixture.cause,
        candidate_effects=(fixture.candidate,),
        verifier_receipts=(fixture.receipt,),
        state_intents=default_state_intents,
        model_intents=(),
        memory_intents=(),
        repair_frames=(),
        phase_records=default_phases,
        runtime_id="network-runtime",
        software_digest=SOFTWARE_DIGEST,
        cjt_ids=tuple(item.cjt_id for item in fixture.state.biases),
        artifacts=(fixture.effect_artifact,),
        semantic_evidence=(fixture.evidence_descriptor,),
        decoder_contract=fixture.decoder_contract,
        compute_plan=phase_by_name[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=phase_by_name[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )
    values.update(changes)
    return NetworkCommitBatch(**values)


def test_three_cjt_effect_commit_is_replayable_and_restart_safe(tmp_path: Path) -> None:
    fixture = _open(tmp_path)
    batch = _batch(fixture)
    receipt = fixture.coordinator.commit(batch)

    assert receipt.published_effect_ids
    assert fixture.store.head.state_digest == batch.state_after.state_digest
    transition = fixture.store.reconstruct_transition()
    assert transition["transition_batches"][0]["batch_id"] == batch.batch_id
    assert transition["causes"][0] == fixture.cause.to_dict()
    assert transition["candidate_effects"][0] == fixture.candidate.to_dict()
    assert transition["verifier_receipts"][0] == fixture.receipt.to_dict()
    assert transition["trace"]["semantic_evidence"] == [fixture.evidence_descriptor]
    assert transition["trace"]["decoder_contract"] == fixture.decoder_contract.to_dict()
    assert fixture.store.verify_integrity()

    path = fixture.store.path
    fixture.store.close()
    reopened = SQLiteAtomicStore(path)
    coordinator = NetworkAtomicCoordinator(
        reopened,
        coordinator_id=COORDINATOR_ID,
        authority_contract_id=AUTHORITY_ID,
        runtime_id="network-runtime",
        software_digest=SOFTWARE_DIGEST,
        num_attention_heads=1,
        model_manifest_context=MODEL_MANIFEST_CONTEXT,
        operation_contracts={fixture.contract.contract_id: fixture.contract},
        decoder_contracts={
            cjt_id: fixture.decoder_contract
            for cjt_id in ("cjt-a", "cjt-b", "cjt-c")
        },
    )
    recovery = coordinator.restore_and_verify()
    restored = NetworkStateEnvelope.from_dict(recovery.state)
    assert len(restored.biases) == 3
    assert all(item.theta.model_digest == restored.model_digest for item in restored.biases)


def _replace_phase(
    records: tuple[PhaseRecord, ...],
    phase: TickPhase,
    *,
    inputs: dict | None = None,
    outputs: dict | None = None,
    compute_units: int | None = None,
) -> tuple[PhaseRecord, ...]:
    return tuple(
        replace(
            record,
            inputs=record.inputs if inputs is None else inputs,
            outputs=record.outputs if outputs is None else outputs,
            compute_units=(
                record.compute_units if compute_units is None else compute_units
            ),
        )
        if record.phase is phase
        else record
        for record in records
    )


def _assert_rejected_atomically(
    fixture: Fixture,
    batch: NetworkCommitBatch,
    reason: str,
) -> None:
    before_head = fixture.store.head
    before_traces = fixture.store.trace_events()
    before_audits = fixture.store.rejection_audits()
    authoritative_tables = (
        "published_effects",
        "memory_records",
        "repair_frames",
        "repair_outcomes",
        "transition_batches",
        "candidate_effects",
        "verifier_receipts",
        "qualification_receipts",
        "state_intents",
        "model_intents",
        "memory_intents",
        "commit_receipts",
    )
    before_counts = {
        table: fixture.store._connection.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        ).fetchone()["count"]
        for table in authoritative_tables
    }

    with pytest.raises(NetworkBatchRejected, match=reason):
        fixture.coordinator.commit(batch)

    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == before_traces
    assert {
        table: fixture.store._connection.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        ).fetchone()["count"]
        for table in authoritative_tables
    } == before_counts
    audits = fixture.store.rejection_audits()
    assert len(audits) == len(before_audits) + 1
    assert audits[-1]["visibility"] == "NON_AUTHORITATIVE"
    assert audits[-1]["state_advanced"] is False
    assert audits[-1]["reason_codes"] == [reason]
    assert fixture.store.verify_integrity()


def _reseal_qualification(
    receipt: QualificationReceipt,
    **changes,
) -> QualificationReceipt:
    draft = replace(
        receipt,
        qualification_receipt_id="pending",
        receipt_digest=ZERO_DIGEST,
        **changes,
    )
    wire = draft.to_dict()
    body = {
        key: value
        for key, value in wire.items()
        if key not in {"schema_version", "qualification_receipt_id", "receipt_digest"}
    }
    identity = content_id("qualification", body)
    digest = canonical_digest(
        {
            "schema_version": QUALIFICATION_RECEIPT_SCHEMA_VERSION,
            "qualification_receipt_id": identity,
            **body,
        }
    )
    return replace(
        draft,
        qualification_receipt_id=identity,
        receipt_digest=digest,
    )


def test_unrequested_memory_read_claim_is_rejected_without_moving_head(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    original = _batch(fixture, batch_id="unrequested-memory-read")
    observations = dict(original.compute_observations)
    observations["memory_reads_used"] = [[1]]
    phases = _replace_phase(
        original.phase_records,
        TickPhase.READ,
        outputs={
            **dict(
                next(
                    item for item in original.phase_records if item.phase is TickPhase.READ
                ).outputs
            ),
            "memory_read_refs": ("memory-not-requested",),
        },
    )
    observe = next(item for item in phases if item.phase is TickPhase.OBSERVE)
    phases = _replace_phase(
        phases,
        TickPhase.OBSERVE,
        outputs={**dict(observe.outputs), "compute_observations": observations},
    )
    poisoned = replace(
        original,
        memory_read_refs=("memory-not-requested",),
        compute_observations=observations,
        phase_records=phases,
    )

    with pytest.raises(NetworkBatchRejected, match="MEMORY_RECORD_NOT_RETAINED"):
        fixture.coordinator.commit(poisoned)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()
    assert fixture.store.verify_integrity()


def test_requested_but_unretained_memory_record_is_rejected_atomically(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    missing_id = "memory-never-retained"
    cause = make_cause(
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"question": "what are the parts"},
        goal_context={"goal_id": "network-test"},
        candidate_operation_ids=("^6",),
        memory_refs=(missing_id,),
    )
    candidate = _reidentify_candidate(
        fixture.candidate,
        parent_cause_id=cause.cause_id,
    )
    candidate = _bind_candidate_to_phases(
        candidate,
        _phases(
            tick=1,
            before=fixture.state,
            after=fixture.state,
            cause_id=cause.cause_id,
            operation_ids=("^6",),
            memory_read_refs=(missing_id,),
        ),
    )
    evidence, descriptor = make_bound_evidence(
        evidence_id="oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    receipt = IndependentVerifier(fixture.contract.verifier_id).evaluate(
        cause,
        candidate,
        fixture.contract,
        evidence,
        bias=fixture.state.by_cjt_id["cjt-a"],
    ).receipt
    after = fixture.state.successor()
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=cause.cause_id,
        candidate_ids=(candidate.candidate_effect_id,),
        receipt_ids=(receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        artifact_ids=(candidate.content_ref.artifact_id,),
        memory_read_refs=(missing_id,),
    )
    by_phase = {item.phase: item for item in phases}
    poisoned = _batch(
        fixture,
        batch_id="unretained-memory-read",
        state_after=after,
        cause=cause,
        candidate_effects=(candidate,),
        verifier_receipts=(receipt,),
        semantic_evidence=(descriptor,),
        memory_read_refs=(missing_id,),
        phase_records=phases,
        compute_plan=by_phase[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=by_phase[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )

    with pytest.raises(NetworkBatchRejected, match="MEMORY_RECORD_NOT_RETAINED"):
        fixture.coordinator.commit(poisoned)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()
    assert fixture.store.verify_integrity()


def test_huge_observation_under_zero_compute_ceiling_is_rejected_atomically(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    after = fixture.state.successor()
    cause = make_cause(
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"question": "closed route"},
        goal_context={"goal_id": "compute-poison"},
        candidate_operation_ids=("^6",),
    )
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=cause.cause_id,
        operation_ids=("^6",),
        reason_codes=("ZERO_FLOW",),
        zero_flow=True,
    )
    observations = dict(
        next(item for item in phases if item.phase is TickPhase.OBSERVE).outputs[
            "compute_observations"
        ]
    )
    observations["reasoning_steps_used"] = [[999_999_999]]
    execute = next(item for item in phases if item.phase is TickPhase.EXECUTE)
    phases = _replace_phase(
        phases,
        TickPhase.EXECUTE,
        outputs={**dict(execute.outputs), "compute_units_used": 999_999_999},
        compute_units=999_999_999,
    )
    observe = next(item for item in phases if item.phase is TickPhase.OBSERVE)
    phases = _replace_phase(
        phases,
        TickPhase.OBSERVE,
        outputs={**dict(observe.outputs), "compute_observations": observations},
    )
    by_phase = {item.phase: item for item in phases}
    poisoned = _batch(
        fixture,
        batch_id="zero-ceiling-huge-observation",
        state_after=after,
        cause=cause,
        candidate_effects=(),
        verifier_receipts=(),
        artifacts=(),
        semantic_evidence=(),
        decoder_contract=None,
        audit_only=True,
        audit_reason_codes=("ZERO_FLOW",),
        phase_records=phases,
        compute_plan=by_phase[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=observations,
    )

    with pytest.raises(NetworkBatchRejected, match="COMPUTE_CEILING_EXCEEDED"):
        fixture.coordinator.commit(poisoned)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()
    assert fixture.store.verify_integrity()


@pytest.mark.parametrize("poison", ("profile", "axis", "hard_open"))
def test_forged_readiness_evidence_is_rejected(
    tmp_path: Path, poison: str
) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    original = _batch(fixture, batch_id=f"forged-readiness-{poison}")
    readiness = next(
        item for item in original.phase_records if item.phase is TickPhase.READINESS
    )
    inputs = dict(readiness.inputs)
    outputs = dict(readiness.outputs)
    if poison == "profile":
        inputs["profile_ids"] = ("forged-profile",)
    elif poison == "axis":
        outputs["desire"] = {**dict(outputs["desire"]), "score_ppm": 0}
    else:
        outputs["hard_open"] = False
    poisoned = replace(
        original,
        phase_records=_replace_phase(
            original.phase_records,
            TickPhase.READINESS,
            inputs=inputs,
            outputs=outputs,
        ),
    )

    with pytest.raises(
        NetworkBatchRejected, match="READINESS_PHASE_NETWORK_BINDING_INVALID"
    ):
        fixture.coordinator.commit(poisoned)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()


def test_unknown_executed_cjt_and_unexecuted_conducting_producer_are_rejected(
    tmp_path: Path,
) -> None:
    for poison in ("ghost", "wrong-known-cjt"):
        case_path = tmp_path / poison
        case_path.mkdir()
        fixture = _open(case_path)
        before_head = fixture.store.head
        original = _batch(fixture, batch_id=f"execute-poison-{poison}")
        execute = next(
            item for item in original.phase_records if item.phase is TickPhase.EXECUTE
        )
        selected = ("ghost-cjt",) if poison == "ghost" else ("cjt-b",)
        phases = _replace_phase(
            original.phase_records,
            TickPhase.EXECUTE,
            inputs={**dict(execute.inputs), "scheduled_cjt_ids": selected},
            outputs={**dict(execute.outputs), "executed_cjt_ids": selected},
        )
        observe = next(item for item in phases if item.phase is TickPhase.OBSERVE)
        phases = _replace_phase(
            phases,
            TickPhase.OBSERVE,
            inputs={"executed_cjt_ids": selected},
            outputs=dict(observe.outputs),
        )
        poisoned = replace(original, phase_records=phases)
        expected = "EXECUTE_PHASE_BINDING_INVALID"
        with pytest.raises(NetworkBatchRejected, match=expected):
            fixture.coordinator.commit(poisoned)
        assert fixture.store.head == before_head
        assert fixture.store.trace_events() == ()


def test_forged_diagnosis_reason_is_rejected_without_moving_head(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    original = _batch(fixture, batch_id="forged-diagnosis")
    diagnose = next(
        item for item in original.phase_records if item.phase is TickPhase.DIAGNOSE
    )
    poisoned = replace(
        original,
        phase_records=_replace_phase(
            original.phase_records,
            TickPhase.DIAGNOSE,
            outputs={**dict(diagnose.outputs), "reason_codes": ("FORGED",)},
        ),
    )

    with pytest.raises(NetworkBatchRejected, match="DIAGNOSE_PHASE_BINDING_INVALID"):
        fixture.coordinator.commit(poisoned)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()


@pytest.mark.parametrize("poisoned_region", ("CUTOFF", "BREAKDOWN"))
def test_accept_receipt_cannot_be_replayed_under_a_fail_closed_region(
    tmp_path: Path, poisoned_region: str
) -> None:
    fixture = _open(tmp_path)
    original = _batch(fixture, batch_id=f"poisoned-region-{poisoned_region.lower()}")
    poisoned_phases = []
    for record in original.phase_records:
        if record.phase is TickPhase.OBSERVE:
            poisoned_phases.append(
                replace(
                    record,
                    outputs={
                        **dict(record.outputs),
                        "operating_regions": (poisoned_region,),
                    },
                )
            )
        elif record.phase is TickPhase.DIAGNOSE:
            poisoned_phases.append(
                replace(
                    record,
                    inputs={
                        **dict(record.inputs),
                        "operating_regions": (poisoned_region,),
                    },
                )
            )
        else:
            poisoned_phases.append(record)
    batch = replace(original, phase_records=tuple(poisoned_phases))
    before = fixture.store.head

    with pytest.raises(
        NetworkBatchRejected, match="OPERATING_REGION_RECEIPT_MISMATCH"
    ):
        fixture.coordinator.commit(batch)

    assert fixture.store.head == before
    assert fixture.store.trace_events() == ()
    assert fixture.store.rejection_audits()[-1]["reason_codes"] == [
        "OPERATING_REGION_RECEIPT_MISMATCH"
    ]
    assert fixture.store.verify_integrity()


def test_poisoned_mixed_memory_batch_writes_nothing_authoritative(tmp_path: Path) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    valid = propose_memory_write(
        tick=1,
        issuer_id="cjt-a",
        bias=fixture.state.by_cjt_id["cjt-a"],
        receipt=fixture.receipt,
        cause=fixture.cause,
        candidate=fixture.candidate,
    )
    target = fixture.state.by_cjt_id["cjt-b"]
    poison = MemoryWriteIntent(
        intent_id="poison-memory-intent",
        tick=1,
        issuer_id="cjt-b",
        authority_capability=AuthorityCapability.PROPOSE_MEMORY_WRITE.value,
        target_bias_id=target.bias_id,
        expected_bias_version=target.version,
        expected_bias_digest=target.state_digest,
        memory_record_id="poison-memory-record",
        memory_kind=MemoryKind.EPISODIC,
        content={"fact": "tries to borrow another CJT receipt"},
        content_ref=None,
        confidence_ppm=1_000_000,
        provenance=("adversarial-test",),
        evidence_refs=("adversarial-test",),
        verifier_receipt_id=fixture.receipt.receipt_id,
        intent_digest=ZERO_DIGEST,
    )
    poison = _sealed(poison, "intent_digest")
    original = _batch(fixture, batch_id="poisoned-memory-mix")
    emit = next(
        item for item in original.phase_records if item.phase is TickPhase.EMIT
    )
    batch = replace(
        original,
        memory_intents=(valid, poison),
        phase_records=_replace_phase(
            original.phase_records,
            TickPhase.EMIT,
            outputs={
                **dict(emit.outputs),
                "memory_intent_ids": (valid.intent_id, poison.intent_id),
            },
        ),
    )

    with pytest.raises(NetworkBatchRejected, match="MEMORY_INTENT_NOT_ACCEPTED"):
        fixture.coordinator.commit(batch)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()
    assert len(fixture.store.rejection_audits()) == 1
    with pytest.raises(PersistenceError):
        fixture.store.immutable_document("memory_records", valid.memory_record_id)
    assert fixture.store.verify_integrity()


def test_authored_semantics_cannot_ride_an_unrelated_zero_tensor(tmp_path: Path) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    mapping, zero_artifact = encode_tensor(
        torch.zeros((1, 2), dtype=torch.float32), kind="candidate-effect"
    )
    forged = _reidentify_candidate(
        fixture.candidate,
        content_ref=TensorArtifactRef(**mapping),
    )
    evidence, descriptor = make_bound_evidence(
        evidence_id="oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    receipt = IndependentVerifier(fixture.contract.verifier_id).evaluate(
        fixture.cause,
        forged,
        fixture.contract,
        evidence,
        bias=fixture.state.by_cjt_id["cjt-a"],
    ).receipt
    assert receipt.disposition.value == "ACCEPT"
    old = fixture.state.by_cjt_id["cjt-a"]
    accepted = advance_bias(
        old,
        tick=1,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=forged.candidate_effect_id,
    )
    after = fixture.state.successor(
        biases=(
            accepted if item.bias_id == old.bias_id else item
            for item in fixture.state.biases
        )
    )
    intents = state_update_intents_for_successor(
        old,
        accepted,
        tick=1,
        receipt=receipt,
        issuer_id="cjt-a",
    )
    batch = _batch(
        fixture,
        batch_id="forged-semantic-tensor",
        state_after=after,
        state_intents=intents,
        candidate_effects=(forged,),
        verifier_receipts=(receipt,),
        semantic_evidence=(descriptor,),
        artifacts=(zero_artifact,),
        phase_records=_phases(
            tick=1,
            before=fixture.state,
            after=after,
            cause_id=fixture.cause.cause_id,
            candidate_ids=(forged.candidate_effect_id,),
            receipt_ids=(receipt.receipt_id,),
            operation_ids=("^6",),
            operation_contract_ids=(fixture.contract.contract_id,),
            state_intent_ids=tuple(item.intent_id for item in intents),
            artifact_ids=(forged.content_ref.artifact_id,),
        ),
    )

    with pytest.raises(
        NetworkBatchRejected, match="CANDIDATE_CONTENT_NOT_DERIVED_FROM_ARTIFACT"
    ):
        fixture.coordinator.commit(batch)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()
    assert fixture.store.rejection_audits()[0]["reason_codes"] == [
        "CANDIDATE_CONTENT_NOT_DERIVED_FROM_ARTIFACT"
    ]


def test_zero_flow_audit_advances_only_global_envelope_and_seals_phases(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    after = fixture.state.successor()
    audit_cause = make_cause(
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"question": "zero flow"},
        goal_context={"goal_id": "audit"},
        candidate_operation_ids=("^6",),
    )
    candidate = _reidentify_candidate(
        fixture.candidate,
        parent_cause_id=audit_cause.cause_id,
    )
    candidate = _bind_candidate_to_phases(
        candidate,
        _phases(
            tick=1,
            before=fixture.state,
            after=after,
            cause_id=audit_cause.cause_id,
            operation_ids=("^6",),
            zero_flow=True,
        ),
    )
    evidence, descriptor = make_bound_evidence(
        evidence_id="oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    cutoff_receipt = IndependentVerifier(fixture.contract.verifier_id).evaluate(
        audit_cause,
        candidate,
        fixture.contract,
        evidence,
        bias=fixture.state.by_cjt_id["cjt-a"],
        operating_region=OperatingRegion.CUTOFF,
    ).receipt
    audit_phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=audit_cause.cause_id,
        candidate_ids=(candidate.candidate_effect_id,),
        receipt_ids=(cutoff_receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        artifact_ids=(candidate.content_ref.artifact_id,),
        reason_codes=("ZERO_FLOW",),
        zero_flow=True,
    )
    audit_phases = _rebind_receipt_phases(audit_phases, cutoff_receipt)
    observe = next(
        item for item in audit_phases if item.phase is TickPhase.OBSERVE
    )
    audit_phases = _replace_phase(
        audit_phases,
        TickPhase.OBSERVE,
        outputs={**dict(observe.outputs), "operating_regions": ("CUTOFF",)},
    )
    diagnose = next(
        item for item in audit_phases if item.phase is TickPhase.DIAGNOSE
    )
    audit_phases = _replace_phase(
        audit_phases,
        TickPhase.DIAGNOSE,
        inputs={**dict(diagnose.inputs), "operating_regions": ("CUTOFF",)},
    )
    audit_phase_by_name = {item.phase: item for item in audit_phases}
    batch = _batch(
        fixture,
        batch_id="zero-flow-audit",
        state_after=after,
        cause=audit_cause,
        candidate_effects=(candidate,),
        verifier_receipts=(cutoff_receipt,),
        artifacts=(fixture.effect_artifact,),
        semantic_evidence=(descriptor,),
        decoder_contract=fixture.decoder_contract,
        audit_only=True,
        audit_reason_codes=("ZERO_FLOW",),
        phase_records=audit_phases,
        compute_plan=audit_phase_by_name[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=audit_phase_by_name[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )
    receipt = fixture.coordinator.commit(batch)

    assert fixture.store.head.state_version == fixture.state.state_version + 1
    assert fixture.store.head.model_digest == fixture.state.model_digest
    restored = NetworkStateEnvelope.from_dict(fixture.store.load_state())
    assert restored.biases == fixture.state.biases
    assert restored.model_artifact_ref == fixture.state.model_artifact_ref
    transition = fixture.store.reconstruct_transition()
    assert len(transition["trace"]["phases"]) == 11
    assert transition["trace"]["audit_transition"]["bias_and_model_bytes_unchanged"]
    assert transition["state_intents"][0]["contract_type"] == "AUDIT_TRANSITION_INTENT"
    assert receipt.accepted_intent_ids == (
        transition["state_intents"][0]["intent_id"],
    )
    assert fixture.store.verify_integrity()


def _qualification(candidate_digest: str, changed: tuple[str, ...]) -> QualificationReceipt:
    policy = LearningPolicy()
    changed = tuple(sorted(changed))
    reasons = (
        "TARGET_IMPROVED",
        "RETENTION_PASSED",
        "REGRESSION_PASSED",
    )
    body = {
        "policy_id": policy.policy_id,
        "independent": True,
        "candidate_model_digest": candidate_digest,
        "disposition": "QUALIFIED",
        "changed_parameter_names": list(changed),
        "allowed_parameter_names": list(changed),
        "gradient_norm_microunits": 1,
        "max_gradient_norm_microunits": 1_000_000,
        "baseline_metrics_microunits": {
            "retention_loss": 1_000_000,
            "target_loss": 2_000_000,
        },
        "candidate_metrics_microunits": {
            "retention_loss": 1_000_000,
            "target_loss": 1_000_000,
        },
        "target_improved": True,
        "retention_passed": True,
        "regression_passed": True,
        "qualified": True,
        "reason_codes": list(reasons),
    }
    receipt_id = content_id("qualification", body)
    receipt_digest = canonical_digest(
        {
            "schema_version": QUALIFICATION_RECEIPT_SCHEMA_VERSION,
            "qualification_receipt_id": receipt_id,
            **body,
        }
    )
    return QualificationReceipt(
        qualification_receipt_id=receipt_id,
        policy_id=policy.policy_id,
        independent=True,
        candidate_model_digest=candidate_digest,
        disposition="QUALIFIED",
        changed_parameter_names=changed,
        allowed_parameter_names=changed,
        gradient_norm_microunits=1,
        max_gradient_norm_microunits=1_000_000,
        baseline_metrics_microunits=body["baseline_metrics_microunits"],
        candidate_metrics_microunits=body["candidate_metrics_microunits"],
        target_improved=True,
        retention_passed=True,
        regression_passed=True,
        qualified=True,
        reason_codes=reasons,
        receipt_digest=receipt_digest,
    )


def _model_update_batch(
    fixture: Fixture,
    *,
    changed_module: str,
    batch_id: str,
) -> tuple[NetworkCommitBatch, object]:
    candidate_model = ThreeCJTModel()
    with torch.no_grad():
        getattr(candidate_model, changed_module).weight.add_(1.0)
    candidate_checkpoint = encode_module_checkpoint(candidate_model)
    gradient_mapping, gradient_artifact = encode_tensor(
        torch.ones(1, dtype=torch.float32), kind="candidate-gradient"
    )
    gradient_reference = TensorArtifactRef(**gradient_mapping)
    changed_name = f"{changed_module}.weight"
    qualification = _qualification(candidate_checkpoint.model_digest, (changed_name,))
    initiator = fixture.state.by_cjt_id["cjt-a"]
    group_ids = (initiator.theta.parameter_group_ids[0],)
    model_intent_id = content_id(
        "intent-model",
        {
            "tick": 1,
            "model_id": MODEL_ID,
            "expected_model_digest": fixture.state.model_digest,
            "update_kind": ModelUpdateKind.GRADIENT_DELTA.value,
            "candidate_model_digest": candidate_checkpoint.model_digest,
            "gradient_digest": gradient_artifact.sha256,
            "parameter_names": [changed_name],
            "parameter_group_ids": list(group_ids),
            "plasticity_ppm": 1_000_000,
            "verifier_receipt_id": fixture.receipt.receipt_id,
            "qualification_receipt_id": qualification.qualification_receipt_id,
        },
    )
    model_intent = ModelUpdateIntent(
        intent_id=model_intent_id,
        tick=1,
        issuer_id="cjt-a",
        authority_capability=AuthorityCapability.PROPOSE_MODEL_UPDATE.value,
        model_id=MODEL_ID,
        expected_model_version=fixture.state.model_version,
        expected_model_digest=fixture.state.model_digest,
        update_kind=ModelUpdateKind.GRADIENT_DELTA,
        parameter_group_ids=group_ids,
        candidate_artifact=candidate_checkpoint.reference,
        gradient_artifact=gradient_reference,
        plasticity_ppm=1_000_000,
        verifier_receipt_id=fixture.receipt.receipt_id,
        qualification_receipt_id=qualification.qualification_receipt_id,
        reason_codes=(
            "VERIFIED_EXPERIENCE",
            "SELECTIVE_PLASTICITY",
            "QUALIFIED",
        ),
        intent_digest=ZERO_DIGEST,
    )
    model_intent = _sealed(model_intent, "intent_digest")
    accepted_initiator = advance_bias(
        initiator,
        tick=fixture.cause.tick,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=fixture.receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=fixture.candidate.candidate_effect_id,
    )
    updated_biases = []
    for bias in fixture.state.biases:
        theta = replace(
            bias.theta,
            model_version=bias.theta.model_version + 1,
            model_digest=candidate_checkpoint.model_digest,
            parameter_artifacts=(candidate_checkpoint.reference,),
        )
        if bias.bias_id == initiator.bias_id:
            updated_biases.append(
                _sealed(
                    replace(
                        accepted_initiator,
                        theta=theta,
                        state_digest=ZERO_DIGEST,
                    ),
                    "state_digest",
                )
            )
        else:
            updated_biases.append(_successor_bias(bias, theta=theta))
    after = fixture.state.successor(
        biases=updated_biases,
        model_version=fixture.state.model_version + 1,
        model_digest=candidate_checkpoint.model_digest,
        model_artifact_ref=candidate_checkpoint.reference,
    )
    state_intents = state_update_intents_for_successor(
        initiator,
        after.by_bias_id[initiator.bias_id],
        tick=1,
        receipt=fixture.receipt,
        issuer_id="cjt-a",
    )
    model_version = ModelVersionWrite(
        model_digest=candidate_checkpoint.model_digest,
        parent_model_digest=fixture.state.model_digest,
        artifact_id=candidate_checkpoint.artifact.artifact_id,
        payload={
            "schema_version": "cas.neural-cjt.model-version/0.2",
            "model_id": MODEL_ID,
            "model_version": fixture.state.model_version + 1,
            "model_digest": candidate_checkpoint.model_digest,
            "model_artifact_ref": candidate_checkpoint.reference.to_dict(),
            **MODEL_MANIFEST_CONTEXT,
            "parent_model_digest": fixture.state.model_digest,
            "learning_tick": 1,
            "initiating_cjt_id": "cjt-a",
            "qualification_receipt_id": qualification.qualification_receipt_id,
            "changed_parameter_names": [changed_name],
        },
    )
    batch = _batch(
        fixture,
        batch_id=batch_id,
        state_after=after,
        state_intents=state_intents,
        model_intents=(model_intent,),
        qualification_receipts=(qualification,),
        artifacts=(
            fixture.effect_artifact,
            candidate_checkpoint.artifact,
            gradient_artifact,
        ),
        model_version=model_version,
        phase_records=_phases(
            tick=1,
            before=fixture.state,
            after=after,
            cause_id=fixture.cause.cause_id,
            candidate_ids=(fixture.candidate.candidate_effect_id,),
            receipt_ids=(fixture.receipt.receipt_id,),
            operation_ids=("^6",),
            operation_contract_ids=(fixture.contract.contract_id,),
            state_intent_ids=tuple(item.intent_id for item in state_intents),
            model_intent_ids=(model_intent.intent_id,),
            artifact_ids=(fixture.candidate.content_ref.artifact_id,),
        ),
    )
    return batch, candidate_checkpoint


def test_qualified_model_update_propagates_only_shared_theta_pointer(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    batch, candidate_checkpoint = _model_update_batch(
        fixture, changed_module="cjt_a", batch_id="allowed-model-update"
    )
    fixture.coordinator.commit(batch)

    after = NetworkStateEnvelope.from_dict(fixture.store.load_state())
    assert all(
        bias.theta.model_digest == candidate_checkpoint.model_digest
        and bias.theta.model_version == 1
        and candidate_checkpoint.reference in bias.theta.parameter_artifacts
        for bias in after.biases
    )
    for cjt_id in ("cjt-b", "cjt-c"):
        old = fixture.state.by_cjt_id[cjt_id]
        new = after.by_cjt_id[cjt_id]
        assert new.stable == old.stable
        assert new.memory == old.memory
        assert new.rpm == old.rpm
        assert new.operating == old.operating
        assert new.governance == old.governance
        assert replace(
            new.theta,
            model_version=old.theta.model_version,
            model_digest=old.theta.model_digest,
            parameter_artifacts=old.theta.parameter_artifacts,
        ) == old.theta
    before_entries = checkpoint_entry_digests(
        fixture.checkpoint.reference, fixture.checkpoint.artifact
    )
    after_entries = checkpoint_entry_digests(
        candidate_checkpoint.reference, candidate_checkpoint.artifact
    )
    assert {
        name for name in before_entries if before_entries[name] != after_entries[name]
    } == {"cjt_a.weight"}
    assert fixture.store.verify_integrity()


def test_resealed_model_manifest_cannot_skip_versions(tmp_path: Path) -> None:
    fixture = _open(tmp_path)
    batch, candidate_checkpoint = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id="model-version-jump-poison",
    )
    receipt = fixture.coordinator.commit(batch)
    row = fixture.store._connection.execute(  # noqa: SLF001 - adversarial mutation
        "SELECT payload_json FROM model_versions WHERE model_digest = ?",
        (candidate_checkpoint.model_digest,),
    ).fetchone()
    payload = json.loads(row["payload_json"])
    payload["model_version"] = 7
    payload_json = canonical_json(payload)
    checksum = hashlib.sha256(payload_json.encode("ascii")).hexdigest()
    fixture.store._connection.execute(  # noqa: SLF001
        "DROP TRIGGER model_versions_immutable_update"
    )
    fixture.store._connection.execute(  # noqa: SLF001
        "UPDATE model_versions SET payload_sha256 = ?, payload_json = ? "
        "WHERE model_digest = ?",
        (checksum, payload_json, candidate_checkpoint.model_digest),
    )
    with pytest.raises(PersistenceError, match="model versions are not contiguous"):
        fixture.store.reconstruct_transition(receipt.trace_id)
    assert fixture.store.verify_integrity() is False


def test_learning_model_intent_must_be_gradient_delta(tmp_path: Path) -> None:
    fixture = _open(tmp_path)
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id="forged-model-update-kind",
    )
    original = batch.model_intents[0]
    assert original.gradient_artifact is not None
    identity = {
        "tick": original.tick,
        "model_id": original.model_id,
        "expected_model_digest": original.expected_model_digest,
        "update_kind": ModelUpdateKind.CHECKPOINT_REPLACEMENT.value,
        "candidate_model_digest": original.candidate_artifact.sha256,
        "gradient_digest": original.gradient_artifact.sha256,
        "parameter_names": list(
            batch.model_version.payload["changed_parameter_names"]
        ),
        "parameter_group_ids": list(original.parameter_group_ids),
        "plasticity_ppm": original.plasticity_ppm,
        "verifier_receipt_id": original.verifier_receipt_id,
        "qualification_receipt_id": original.qualification_receipt_id,
    }
    forged = _sealed(
        replace(
            original,
            intent_id=content_id("intent-model", identity),
            update_kind=ModelUpdateKind.CHECKPOINT_REPLACEMENT,
            intent_digest=ZERO_DIGEST,
        ),
        "intent_digest",
    )
    emit = next(
        item for item in batch.phase_records if item.phase is TickPhase.EMIT
    )
    phases = _replace_phase(
        batch.phase_records,
        TickPhase.EMIT,
        outputs={
            **dict(emit.outputs),
            "model_intent_ids": (forged.intent_id,),
        },
    )
    _assert_rejected_atomically(
        fixture,
        replace(batch, model_intents=(forged,), phase_records=phases),
        "MODEL_INTENT_UPDATE_KIND_INVALID",
    )


def test_checkpoint_scope_escape_rejects_cross_cjt_bytes_and_keeps_head(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    before_head = fixture.store.head
    batch, _ = _model_update_batch(
        fixture, changed_module="cjt_b", batch_id="cross-cjt-model-poison"
    )

    with pytest.raises(NetworkBatchRejected, match="CHECKPOINT_PARAMETER_SCOPE_ESCAPE"):
        fixture.coordinator.commit(batch)
    assert fixture.store.head == before_head
    assert fixture.store.trace_events() == ()
    assert fixture.store.rejection_audits()[0]["reason_codes"] == [
        "CHECKPOINT_PARAMETER_SCOPE_ESCAPE"
    ]
    assert fixture.store.verify_integrity()


@pytest.mark.parametrize("namespace", ("bias", "cjt"))
def test_network_envelope_rejects_duplicate_identity_namespaces(
    tmp_path: Path,
    namespace: str,
) -> None:
    fixture = _open(tmp_path)
    first, second, third = fixture.state.biases
    changes = (
        {"bias_id": first.bias_id}
        if namespace == "bias"
        else {
            "cjt_id": first.cjt_id,
            "stable": replace(second.stable, cjt_id=first.cjt_id),
        }
    )
    duplicate = _sealed(
        replace(second, **changes, state_digest=ZERO_DIGEST),
        "state_digest",
    )
    with pytest.raises(ValueError, match="Bias IDs and CJT IDs must each be unique"):
        NetworkStateEnvelope.create(
            (first, duplicate, third),
            model_id=fixture.state.model_id,
            model_version=fixture.state.model_version,
            model_digest=fixture.state.model_digest,
            model_artifact_ref=fixture.state.model_artifact_ref,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("runtime_id", "forged-runtime"),
        ("software_digest", "c" * 64),
    ),
)
def test_runtime_identity_is_bound_to_trusted_constructor_values(
    tmp_path: Path,
    field_name: str,
    value: str,
) -> None:
    fixture = _open(tmp_path)
    batch = replace(
        _batch(fixture, batch_id=f"forged-{field_name}"),
        **{field_name: value},
    )
    _assert_rejected_atomically(fixture, batch, "RUNTIME_IDENTITY_NOT_ADMITTED")


def test_resealed_candidate_with_stale_content_derived_id_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    forged = _sealed(
        replace(
            fixture.candidate,
            content={
                **dict(fixture.candidate.content),
                "symbol": "NO_EFFECT",
            },
            candidate_digest=ZERO_DIGEST,
        ),
        "candidate_digest",
    )
    batch = replace(
        _batch(fixture, batch_id="stale-candidate-id"),
        candidate_effects=(forged,),
    )
    _assert_rejected_atomically(fixture, batch, "CANDIDATE_EFFECT_IDENTITY_INVALID")


def test_resealed_candidate_cannot_add_false_provenance(tmp_path: Path) -> None:
    fixture = _open(tmp_path)
    forged_candidate = _sealed(
        replace(
            fixture.candidate,
            provenance=(*fixture.candidate.provenance, "human-approved:forged"),
            candidate_digest=ZERO_DIGEST,
        ),
        "candidate_digest",
    )
    evidence, descriptor = make_bound_evidence(
        evidence_id="oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    forged_receipt = IndependentVerifier(fixture.contract.verifier_id).evaluate(
        fixture.cause,
        forged_candidate,
        fixture.contract,
        evidence,
        bias=fixture.state.by_cjt_id["cjt-a"],
    ).receipt
    old_bias = fixture.state.by_cjt_id["cjt-a"]
    accepted_bias = advance_bias(
        old_bias,
        tick=1,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=forged_receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=forged_candidate.candidate_effect_id,
    )
    after = fixture.state.successor(
        biases=(
            accepted_bias if bias.bias_id == old_bias.bias_id else bias
            for bias in fixture.state.biases
        )
    )
    state_intents = state_update_intents_for_successor(
        old_bias,
        accepted_bias,
        tick=1,
        receipt=forged_receipt,
        issuer_id="cjt-a",
    )
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        candidate_ids=(forged_candidate.candidate_effect_id,),
        receipt_ids=(forged_receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        state_intent_ids=tuple(item.intent_id for item in state_intents),
        artifact_ids=(forged_candidate.content_ref.artifact_id,),
        reason_codes=tuple(forged_receipt.reason_codes),
    )
    phase_map = {item.phase: item for item in phases}
    poisoned = _batch(
        fixture,
        batch_id="false-candidate-provenance",
        state_after=after,
        candidate_effects=(forged_candidate,),
        verifier_receipts=(forged_receipt,),
        state_intents=state_intents,
        phase_records=phases,
        semantic_evidence=(descriptor,),
        compute_plan=phase_map[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=phase_map[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )
    _assert_rejected_atomically(
        fixture,
        poisoned,
        "CANDIDATE_PROVENANCE_INVALID",
    )


def test_resealed_receipt_with_stale_content_derived_id_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    forged = _sealed(
        replace(
            fixture.receipt,
            reason_codes=("FORGED_REASON",),
            receipt_digest=ZERO_DIGEST,
        ),
        "receipt_digest",
    )
    original = _batch(fixture, batch_id="stale-receipt-id")
    batch = replace(
        original,
        verifier_receipts=(forged,),
        phase_records=_rebind_receipt_phases(original.phase_records, forged),
    )
    _assert_rejected_atomically(fixture, batch, "VERIFIER_RECEIPT_IDENTITY_INVALID")


def test_resealed_receipt_with_untrusted_verifier_configuration_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    forged = _reidentify_receipt(fixture.receipt, verifier_version=2)
    original = _batch(fixture, batch_id="forged-verifier-version")
    batch = replace(
        original,
        verifier_receipts=(forged,),
        phase_records=_rebind_receipt_phases(original.phase_records, forged),
    )
    _assert_rejected_atomically(fixture, batch, "VERIFIER_RECEIPT_BINDING_INVALID")


def test_resealed_semantic_claim_must_equal_exact_verifier_replay(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    forged = _reidentify_receipt(
        fixture.receipt,
        reason_codes=("FORGED_SEMANTIC_JUSTIFICATION",),
    )
    original = _batch(fixture, batch_id="forged-semantic-outcome")
    batch = replace(
        original,
        verifier_receipts=(forged,),
        phase_records=_rebind_receipt_phases(original.phase_records, forged),
    )
    _assert_rejected_atomically(fixture, batch, "VERIFIER_RECEIPT_NOT_EXACT_REPLAY")


def test_self_digested_but_unadmitted_decoder_contract_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    unrelated = DecoderContract(
        decoder_id="unrelated-decoder-^6-v1",
        version=1,
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        labels=("NO_EFFECT", "PARTS_FOUND"),
    )
    batch = replace(
        _batch(fixture, batch_id="unadmitted-decoder"),
        decoder_contract=unrelated,
    )
    _assert_rejected_atomically(
        fixture,
        batch,
        "SEMANTIC_DECODER_CONTRACT_NOT_ADMITTED",
    )


@pytest.mark.parametrize(
    ("denied_permission", "reason"),
    (
        ("execute", "ROUTE_SETTINGS_HARD_MASK_BINDING_INVALID"),
        ("write_bias", "BIAS_STATE_WRITE_NOT_PERMITTED"),
        ("publish_effect", "EFFECT_PUBLICATION_NOT_PERMITTED"),
    ),
)
def test_durable_hard_permissions_cannot_be_bypassed(
    tmp_path: Path,
    denied_permission: str,
    reason: str,
) -> None:
    fixture = _open(tmp_path, denied_hard_permission=denied_permission)
    _assert_rejected_atomically(
        fixture,
        _batch(fixture, batch_id=f"missing-{denied_permission}"),
        reason,
    )


def test_memory_write_requires_durable_write_memory_permission(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path, denied_hard_permission="write_memory")
    intent = propose_memory_write(
        tick=1,
        issuer_id="cjt-a",
        bias=fixture.state.by_cjt_id["cjt-a"],
        receipt=fixture.receipt,
        cause=fixture.cause,
        candidate=fixture.candidate,
    )
    original = _batch(fixture, batch_id="missing-write-memory")
    emit = next(
        item for item in original.phase_records if item.phase is TickPhase.EMIT
    )
    phases = _replace_phase(
        original.phase_records,
        TickPhase.EMIT,
        outputs={
            **dict(emit.outputs),
            "memory_intent_ids": (intent.intent_id,),
        },
    )
    batch = replace(
        original,
        memory_intents=(intent,),
        phase_records=phases,
    )
    _assert_rejected_atomically(fixture, batch, "MEMORY_WRITE_NOT_PERMITTED")


def test_canonical_accept_requires_persistent_bias_transition(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    after = fixture.state.successor()
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        candidate_ids=(fixture.candidate.candidate_effect_id,),
        receipt_ids=(fixture.receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        artifact_ids=(fixture.candidate.content_ref.artifact_id,),
    )
    batch = _batch(
        fixture,
        batch_id="accept-without-bias-transition",
        state_after=after,
        state_intents=(),
        phase_records=phases,
    )
    _assert_rejected_atomically(
        fixture,
        batch,
        "BIAS_SUCCESSOR_NOT_EXACT_ADVANCE",
    )


def test_orphan_rpm_open_delta_is_rejected_without_authoritative_writes(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    old = fixture.state.by_cjt_id["cjt-a"]
    forged = advance_bias(
        old,
        tick=1,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=fixture.receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=fixture.candidate.candidate_effect_id,
        open_repair_id="repair-never-created",
        open_repair_return_address=(
            f"cjt:{old.cjt_id}:cause:{fixture.cause.cause_id}"
        ),
    )
    after = fixture.state.successor(
        biases=(
            forged if item.bias_id == old.bias_id else item
            for item in fixture.state.biases
        )
    )
    intents = state_update_intents_for_successor(
        old,
        forged,
        tick=1,
        receipt=fixture.receipt,
        issuer_id="cjt-a",
    )
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        candidate_ids=(fixture.candidate.candidate_effect_id,),
        receipt_ids=(fixture.receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        state_intent_ids=tuple(item.intent_id for item in intents),
        artifact_ids=(fixture.candidate.content_ref.artifact_id,),
    )
    batch = _batch(
        fixture,
        batch_id="orphan-rpm-open",
        state_after=after,
        state_intents=intents,
        phase_records=phases,
    )
    _assert_rejected_atomically(fixture, batch, "REPAIR_OPEN_DELTA_NOT_EXACT")


def test_audit_transition_requires_a_replayed_candidate_and_receipt(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    after = fixture.state.successor()
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        operation_ids=("^6",),
        reason_codes=("ZERO_FLOW",),
        zero_flow=True,
    )
    by_phase = {item.phase: item for item in phases}
    batch = _batch(
        fixture,
        batch_id="evidence-free-audit",
        state_after=after,
        candidate_effects=(),
        verifier_receipts=(),
        state_intents=(),
        artifacts=(),
        semantic_evidence=(),
        decoder_contract=None,
        audit_only=True,
        audit_reason_codes=("ZERO_FLOW",),
        phase_records=phases,
        compute_plan=by_phase[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=by_phase[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )
    _assert_rejected_atomically(fixture, batch, "AUDIT_REQUIRES_VERIFIED_CANDIDATE")


@pytest.mark.parametrize(
    ("poison", "reason"),
    (
        ("extra_diagnostic", "PHASE_CONTRACT_INVALID"),
        ("wrong_head_count", "CONTROL_BINDING_MANIFEST_INVALID"),
        ("unbound_manifest", "CONTROL_BINDING_MANIFEST_INVALID"),
    ),
)
def test_control_observation_and_candidate_cross_links_are_exact(
    tmp_path: Path,
    poison: str,
    reason: str,
) -> None:
    fixture = _open(tmp_path)
    original = _batch(fixture, batch_id=f"control-binding-{poison}")
    route = next(
        item for item in original.phase_records if item.phase is TickPhase.ROUTE
    )
    observe = next(
        item for item in original.phase_records if item.phase is TickPhase.OBSERVE
    )
    if poison == "extra_diagnostic":
        phases = _replace_phase(
            original.phase_records,
            TickPhase.OBSERVE,
            outputs=dict(observe.outputs),
        )
        phases = tuple(
            replace(
                item,
                diagnostics={**dict(item.diagnostics), "forged_claim": "present"},
            )
            if item.phase is TickPhase.OBSERVE
            else item
            for item in phases
        )
    else:
        manifest = dict(route.inputs["control_binding_manifest"])
        if poison == "wrong_head_count":
            manifest["live_beta_by_head_microunits"] = [
                fixture.state.by_cjt_id["cjt-a"].theta.beta_microunits,
                fixture.state.by_cjt_id["cjt-a"].theta.beta_microunits,
            ]
        else:
            manifest["route_settings"] = {"fixture": True, "forged": True}
        phases = _replace_phase(
            original.phase_records,
            TickPhase.ROUTE,
            inputs={**dict(route.inputs), "control_binding_manifest": manifest},
        )
        diagnostics = {
            "control_binding_digest": canonical_digest(manifest),
            "declared_beta_microunits": manifest["declared_beta_microunits"],
            "live_beta_by_head_microunits": manifest[
                "live_beta_by_head_microunits"
            ],
        }
        phases = tuple(
            replace(item, diagnostics=diagnostics)
            if item.phase is TickPhase.OBSERVE
            else item
            for item in phases
        )
    batch = replace(original, phase_records=phases)
    _assert_rejected_atomically(fixture, batch, reason)


def test_candidate_phase_must_equal_independently_derived_eligible_set(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    original = _batch(fixture, batch_id="ghost-candidate-phase")
    candidate_phase = next(
        item for item in original.phase_records if item.phase is TickPhase.CANDIDATE
    )
    phases = _replace_phase(
        original.phase_records,
        TickPhase.CANDIDATE,
        outputs={
            **dict(candidate_phase.outputs),
            "candidate_cjt_ids": (
                *candidate_phase.outputs["candidate_cjt_ids"],
                "ghost-cjt",
            ),
            "operation_contract_ids": (
                *candidate_phase.outputs["operation_contract_ids"],
                fixture.contract.contract_id,
            ),
        },
    )
    _assert_rejected_atomically(
        fixture,
        replace(original, phase_records=phases),
        "CANDIDATE_PHASE_BINDING_INVALID",
    )


def test_unrequested_canonical_operation_cannot_rebound_from_experimental_cause(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    cause = make_cause(
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"question": "request only attract"},
        goal_context={"goal_id": "unrequested-operation"},
        candidate_operation_ids=("^2",),
    )
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=fixture.state.successor(),
        cause_id=cause.cause_id,
        candidate_ids=(fixture.candidate.candidate_effect_id,),
        receipt_ids=(fixture.receipt.receipt_id,),
        operation_ids=("^2",),
        artifact_ids=(fixture.candidate.content_ref.artifact_id,),
    )
    batch = _batch(
        fixture,
        batch_id="unrequested-six-rebound",
        cause=cause,
        phase_records=phases,
    )
    _assert_rejected_atomically(
        fixture,
        batch,
        "CANDIDATE_PHASE_BINDING_INVALID",
    )


def test_durable_local_topology_denial_excludes_control_cjt(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path, denied_topology_permission="local")
    after = fixture.state.successor()
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        operation_ids=("^6",),
        reason_codes=("ZERO_FLOW",),
        zero_flow=True,
    )
    candidate_phase = next(
        item for item in phases if item.phase is TickPhase.CANDIDATE
    )
    phases = _replace_phase(
        phases,
        TickPhase.CANDIDATE,
        outputs={
            **dict(candidate_phase.outputs),
            "candidate_cjt_ids": ("cjt-b", "cjt-c"),
            "operation_contract_ids": (
                fixture.contract.contract_id,
                fixture.contract.contract_id,
            ),
        },
    )
    by_phase = {item.phase: item for item in phases}
    batch = _batch(
        fixture,
        batch_id="local-topology-denied",
        state_after=after,
        candidate_effects=(),
        verifier_receipts=(),
        state_intents=(),
        artifacts=(),
        semantic_evidence=(),
        decoder_contract=None,
        audit_only=True,
        audit_reason_codes=("ZERO_FLOW",),
        phase_records=phases,
        compute_plan=by_phase[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=by_phase[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )
    _assert_rejected_atomically(fixture, batch, "ROUTE_CONTROL_CJT_INVALID")


def test_committed_effect_cannot_route_across_an_untrusted_topology_edge(
    tmp_path: Path,
) -> None:
    fixture = _open(
        tmp_path,
        permitted_topology_edges=(("cjt-a", "cjt-b"),),
    )
    first_receipt = fixture.coordinator.commit(
        _batch(fixture, batch_id="topology-parent")
    )
    state = NetworkStateEnvelope.from_dict(fixture.store.load_state())
    cause = cause_from_committed_effect(
        fixture.store,
        first_receipt.published_effect_ids[0],
        tick=2,
        candidate_operation_ids=("^6",),
        goal_context={"goal_id": "topology-cascade"},
    )
    bias = state.by_cjt_id["cjt-c"]
    content_ref = fixture.candidate.content_ref
    identity = {
        "tick": 2,
        "parent_cause_id": cause.cause_id,
        "producer_cjt_id": bias.cjt_id,
        "operation_contract_digest": fixture.contract.contract_digest,
        "bias_digest": bias.state_digest,
        "model_digest": state.model_digest,
        "content": fixture.candidate.content,
        "content_ref": content_ref.to_dict(),
    }
    candidate = _sealed(
        CandidateEffect(
            candidate_effect_id=content_id("candidate-effect", identity),
            tick=2,
            parent_cause_id=cause.cause_id,
            producer_cjt_id=bias.cjt_id,
            operation_id="^6",
            operation_contract_id=fixture.contract.contract_id,
            operation_contract_digest=fixture.contract.contract_digest,
            bias_id=bias.bias_id,
            bias_version=bias.version,
            bias_digest=bias.state_digest,
            model_digest=state.model_digest,
            content=fixture.candidate.content,
            content_ref=content_ref,
            uncertainty_ppm=0,
            provenance=(
                f"cause:{cause.cause_id}",
                f"bias:{bias.state_digest}",
                f"model:{state.model_digest}",
                f"decoder:{fixture.decoder_contract.decoder_digest}",
            ),
            candidate_digest=ZERO_DIGEST,
        ),
        "candidate_digest",
    )
    evidence, descriptor = make_bound_evidence(
        evidence_id="topology-oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    receipt = IndependentVerifier(fixture.contract.verifier_id).evaluate(
        cause,
        candidate,
        fixture.contract,
        evidence,
        bias=bias,
    ).receipt
    next_bias = advance_bias(
        bias,
        tick=2,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=receipt.receipt_id,
        cause_id=cause.cause_id,
        effect_id=candidate.candidate_effect_id,
    )
    after = state.successor(
        biases=(
            next_bias if item.bias_id == bias.bias_id else item
            for item in state.biases
        )
    )
    intents = state_update_intents_for_successor(
        bias,
        next_bias,
        tick=2,
        receipt=receipt,
        issuer_id="cjt-c",
    )
    phases = _phases(
        tick=2,
        before=state,
        after=after,
        cause_id=cause.cause_id,
        candidate_ids=(candidate.candidate_effect_id,),
        receipt_ids=(receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        state_intent_ids=tuple(item.intent_id for item in intents),
        artifact_ids=(content_ref.artifact_id,),
        control_cjt_id="cjt-c",
    )
    candidate_phase = next(
        item for item in phases if item.phase is TickPhase.CANDIDATE
    )
    phases = _replace_phase(
        phases,
        TickPhase.CANDIDATE,
        outputs={
            **dict(candidate_phase.outputs),
            "candidate_cjt_ids": ("cjt-b",),
            "operation_contract_ids": (fixture.contract.contract_id,),
        },
    )
    by_phase = {item.phase: item for item in phases}
    cascade_fixture = replace(
        fixture,
        state=state,
        cause=cause,
        candidate=candidate,
        receipt=receipt,
        evidence_descriptor=descriptor,
    )
    batch = _batch(
        cascade_fixture,
        batch_id="wrong-topology-edge",
        tick=2,
        base_trace_digest=fixture.store.head.trace_digest,
        state_after=after,
        state_intents=intents,
        phase_records=phases,
        compute_plan=by_phase[TickPhase.ROUTE].outputs["compute_plan"],
        compute_observations=by_phase[TickPhase.OBSERVE].outputs[
            "compute_observations"
        ],
    )
    _assert_rejected_atomically(
        cascade_fixture,
        batch,
        "CANDIDATE_PHASE_BINDING_INVALID",
    )


@pytest.mark.parametrize("kind", ("effect", "rpm", "ordinary_origin"))
def test_cause_authority_fields_require_exact_retained_provenance(
    tmp_path: Path,
    kind: str,
) -> None:
    fixture = _open(tmp_path)
    if kind == "effect":
        cause = make_cause(
            tick=1,
            cause_kind=CauseKind.EFFECT,
            content={"published_effect_id": "effect-never-committed"},
            goal_context={"goal_id": "fake-effect"},
            candidate_operation_ids=("^6",),
            parent_effect_id="effect-never-committed",
            originating_cjt_id="cjt-a",
        )
        reason = "EFFECT_CAUSE_PROVENANCE_INVALID"
    elif kind == "rpm":
        cause = make_cause(
            tick=1,
            cause_kind=CauseKind.RPM_SUBGOAL,
            content={"repair_id": "repair-never-opened"},
            goal_context={"goal_id": "fake-repair"},
            candidate_operation_ids=("^6",),
            originating_cjt_id="cjt-a",
        )
        reason = "RPM_SUBGOAL_PROVENANCE_INVALID"
    else:
        cause = make_cause(
            tick=1,
            cause_kind=CauseKind.PROPOSITION,
            content={"question": "forged origin"},
            goal_context={"goal_id": "ordinary-origin"},
            candidate_operation_ids=("^6",),
            originating_cjt_id="cjt-a",
        )
        reason = "CAUSE_PROVENANCE_FIELDS_NOT_ADMITTED"
    batch = replace(
        _batch(fixture, batch_id=f"cause-provenance-{kind}"),
        cause=cause,
    )
    _assert_rejected_atomically(fixture, batch, reason)


def _batch_with_nonadmitted_cause(
    fixture: Fixture,
    cause: CausePacket,
    *,
    batch_id: str,
) -> NetworkCommitBatch:
    preview = _phases(
        tick=1,
        before=fixture.state,
        after=fixture.state,
        cause_id=cause.cause_id,
        operation_ids=("^6",),
    )
    candidate = _bind_candidate_to_phases(
        _reidentify_candidate(
            fixture.candidate,
            parent_cause_id=cause.cause_id,
        ),
        preview,
    )
    evidence, descriptor = make_bound_evidence(
        evidence_id="oracle-evidence",
        source_id="trusted-oracle",
        port_id="AUTHORED_TARGET",
        operation_id="^6",
        effect_kind="DECOMPOSITION_SIGNAL",
        expected_symbol="PARTS_FOUND",
    )
    receipt = IndependentVerifier(fixture.contract.verifier_id).evaluate(
        cause,
        candidate,
        fixture.contract,
        evidence,
        bias=fixture.state.by_cjt_id["cjt-a"],
    ).receipt
    after = fixture.state.successor()
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=cause.cause_id,
        candidate_ids=(candidate.candidate_effect_id,),
        receipt_ids=(receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        artifact_ids=(candidate.content_ref.artifact_id,),
    )
    phases = _rebind_receipt_phases(phases, receipt)
    return _batch(
        fixture,
        batch_id=batch_id,
        state_after=after,
        cause=cause,
        candidate_effects=(candidate,),
        verifier_receipts=(receipt,),
        state_intents=(),
        semantic_evidence=(descriptor,),
        phase_records=phases,
    )


def test_nonadmitted_cause_kind_is_rejected_by_trusted_contract(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    cause = make_cause(
        tick=1,
        cause_kind=CauseKind.EVENT,
        content={"event": "not admitted to decompose"},
        goal_context={"goal_id": "cause-kind"},
        candidate_operation_ids=("^6",),
    )
    _assert_rejected_atomically(
        fixture,
        _batch_with_nonadmitted_cause(
            fixture,
            cause,
            batch_id="wrong-cause-kind",
        ),
        "CAUSE_KIND_NOT_ACCEPTED",
    )


def test_nonadmitted_cause_schema_is_rejected_by_trusted_contract(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)

    class FutureCause(CausePacket):
        SCHEMA_VERSION = "cas.neural-cjt.cause/9.9"

    cause = FutureCause(
        **{
            item.name: getattr(fixture.cause, item.name)
            for item in dataclass_fields(CausePacket)
        }
    )
    _assert_rejected_atomically(
        fixture,
        _batch_with_nonadmitted_cause(
            fixture,
            cause,
            batch_id="wrong-cause-schema",
        ),
        "CAUSE_SCHEMA_NOT_ACCEPTED",
    )


@pytest.mark.parametrize(
    ("poison", "reason"),
    (
        ("issuer", "MODEL_INTENT_NOT_ACCEPTED"),
        ("plasticity", "MODEL_PLASTICITY_NOT_EXACT"),
    ),
)
def test_model_intent_authority_fields_are_exact(
    tmp_path: Path,
    poison: str,
    reason: str,
) -> None:
    fixture = _open(tmp_path)
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id=f"model-authority-{poison}",
    )
    original = batch.model_intents[0]
    changes = (
        {"issuer_id": "forged-writeback-controller"}
        if poison == "issuer"
        else {"plasticity_ppm": 999_999}
    )
    forged = _sealed(
        replace(original, **changes, intent_digest=ZERO_DIGEST),
        "intent_digest",
    )
    _assert_rejected_atomically(
        fixture,
        replace(batch, model_intents=(forged,)),
        reason,
    )


def test_model_update_requires_learn_and_named_group_permissions(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path, denied_learning_permission="learn")
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id="missing-learn-permission",
    )
    _assert_rejected_atomically(
        fixture,
        batch,
        "MODEL_PARAMETER_GROUP_NOT_ADMITTED",
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("target_improved", False),
        ("retention_passed", False),
        ("qualified", False),
    ),
)
def test_resealed_qualification_decisions_are_recomputed_from_exact_metrics(
    tmp_path: Path,
    field_name: str,
    value: bool,
) -> None:
    fixture = _open(tmp_path)
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id=f"qualification-{field_name}",
    )
    qualification = _reseal_qualification(
        batch.qualification_receipts[0],
        **{field_name: value},
    )
    intent = _sealed(
        replace(
            batch.model_intents[0],
            qualification_receipt_id=qualification.qualification_receipt_id,
            intent_digest=ZERO_DIGEST,
        ),
        "intent_digest",
    )
    poisoned = replace(
        batch,
        model_intents=(intent,),
        qualification_receipts=(qualification,),
    )
    _assert_rejected_atomically(
        fixture,
        poisoned,
        "QUALIFICATION_RECEIPT_NOT_ADMITTED",
    )


@pytest.mark.parametrize("poison", ("empty", "extra"))
def test_promoted_model_manifest_must_match_exact_runtime_contract(
    tmp_path: Path,
    poison: str,
) -> None:
    fixture = _open(tmp_path)
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id=f"model-manifest-{poison}",
    )
    payload = (
        {}
        if poison == "empty"
        else {**dict(batch.model_version.payload), "untrusted_extension": True}
    )
    poisoned = replace(
        batch,
        model_version=replace(batch.model_version, payload=payload),
    )
    _assert_rejected_atomically(
        fixture,
        poisoned,
        "MODEL_VERSION_MANIFEST_INVALID",
    )


def test_resealed_semantic_evidence_rejects_unadmitted_claim_fields(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    forged = {
        **fixture.evidence_descriptor,
        "externally_attested": True,
    }
    forged["evidence_digest"] = canonical_digest(
        forged,
        omit_keys=("evidence_digest",),
    )
    batch = replace(
        _batch(fixture, batch_id="semantic-evidence-extra-claim"),
        semantic_evidence=(forged,),
    )
    _assert_rejected_atomically(
        fixture,
        batch,
        "SEMANTIC_EVIDENCE_FIELDS_NOT_EXACT",
    )


def test_state_intent_rationale_is_factory_exact(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    batch = _batch(fixture, batch_id="forged-state-rationale")
    first, *rest = batch.state_intents
    forged = _sealed(
        replace(
            first,
            reason_codes=("FALSE_AUTHORITY_RATIONALE",),
            intent_digest=ZERO_DIGEST,
        ),
        "intent_digest",
    )
    poisoned = replace(batch, state_intents=(forged, *rest))
    _assert_rejected_atomically(
        fixture,
        poisoned,
        "STATE_INTENT_REASON_CODES_INVALID",
    )


def test_model_intent_rationale_is_factory_exact(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id="forged-model-rationale",
    )
    forged = _sealed(
        replace(
            batch.model_intents[0],
            reason_codes=("FALSE_AUTHORITY_RATIONALE",),
            intent_digest=ZERO_DIGEST,
        ),
        "intent_digest",
    )
    _assert_rejected_atomically(
        fixture,
        replace(batch, model_intents=(forged,)),
        "MODEL_INTENT_REASON_CODES_INVALID",
    )


@pytest.mark.parametrize("root", ("memory", "rpm", "operating"))
def test_bias_successor_metadata_is_exactly_reconstructed(
    tmp_path: Path,
    root: str,
) -> None:
    fixture = _open(tmp_path)
    old = fixture.state.by_cjt_id["cjt-a"]
    accepted = advance_bias(
        old,
        tick=1,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=fixture.receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=fixture.candidate.candidate_effect_id,
    )
    if root == "memory":
        root_change = {
            "memory": replace(
                accepted.memory,
                recent_cause_ids=(
                    *accepted.memory.recent_cause_ids,
                    "forged-cause-history",
                ),
            )
        }
    elif root == "rpm":
        root_change = {
            "rpm": replace(
                accepted.rpm,
                unmet_prerequisites=("forged-prerequisite",),
            )
        }
    else:
        root_change = {
            "operating": replace(
                accepted.operating,
                response_model_status="FORGED_RESPONSE_MODEL",
            )
        }
    poisoned_bias = _sealed(
        replace(accepted, **root_change, state_digest=ZERO_DIGEST),
        "state_digest",
    )
    after = fixture.state.successor(
        biases=(
            poisoned_bias if item.bias_id == old.bias_id else item
            for item in fixture.state.biases
        )
    )
    intents = state_update_intents_for_successor(
        old,
        poisoned_bias,
        tick=1,
        receipt=fixture.receipt,
        issuer_id="cjt-a",
    )
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        candidate_ids=(fixture.candidate.candidate_effect_id,),
        receipt_ids=(fixture.receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        state_intent_ids=tuple(item.intent_id for item in intents),
        artifact_ids=(fixture.candidate.content_ref.artifact_id,),
    )
    batch = _batch(
        fixture,
        batch_id=f"forged-bias-{root}",
        state_after=after,
        state_intents=intents,
        phase_records=phases,
    )
    _assert_rejected_atomically(
        fixture,
        batch,
        "BIAS_SUCCESSOR_NOT_EXACT_ADVANCE",
    )


def test_recurrent_state_reference_must_be_a_valid_shape_bound_runtime_artifact(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    old = fixture.state.by_cjt_id["cjt-a"]
    accepted = advance_bias(
        old,
        tick=1,
        region=OperatingRegion.ACTIVE,
        semantic_outcome=SemanticOutcome.INTENDED,
        verifier_receipt_id=fixture.receipt.receipt_id,
        cause_id=fixture.cause.cause_id,
        effect_id=fixture.candidate.candidate_effect_id,
        recurrent_state_ref=fixture.candidate.content_ref,
    )
    after = fixture.state.successor(
        biases=(
            accepted if item.bias_id == old.bias_id else item
            for item in fixture.state.biases
        )
    )
    intents = state_update_intents_for_successor(
        old,
        accepted,
        tick=1,
        receipt=fixture.receipt,
        issuer_id="cjt-a",
    )
    phases = _phases(
        tick=1,
        before=fixture.state,
        after=after,
        cause_id=fixture.cause.cause_id,
        candidate_ids=(fixture.candidate.candidate_effect_id,),
        receipt_ids=(fixture.receipt.receipt_id,),
        operation_ids=("^6",),
        operation_contract_ids=(fixture.contract.contract_id,),
        state_intent_ids=tuple(item.intent_id for item in intents),
        artifact_ids=(fixture.candidate.content_ref.artifact_id,),
    )
    _assert_rejected_atomically(
        fixture,
        _batch(
            fixture,
            batch_id="wrong-recurrent-artifact-kind",
            state_after=after,
            state_intents=intents,
            phase_records=phases,
        ),
        "RECURRENT_STATE_ARTIFACT_NOT_ADMITTED",
    )


def test_reidentified_state_intent_is_rejected_even_after_resealing_phase_refs(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    batch = _batch(fixture, batch_id="reidentified-state-intent")
    first, *rest = batch.state_intents
    forged = _sealed(
        replace(
            first,
            intent_id="forged-state-intent-id",
            intent_digest=ZERO_DIGEST,
        ),
        "intent_digest",
    )
    intents = (forged, *rest)
    emit = next(item for item in batch.phase_records if item.phase is TickPhase.EMIT)
    phases = _replace_phase(
        batch.phase_records,
        TickPhase.EMIT,
        outputs={
            **dict(emit.outputs),
            "state_intent_ids": tuple(item.intent_id for item in intents),
        },
    )
    _assert_rejected_atomically(
        fixture,
        replace(batch, state_intents=intents, phase_records=phases),
        "STATE_INTENT_IDENTITY_INVALID",
    )


def test_reidentified_model_intent_is_rejected_even_after_resealing_phase_refs(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    batch, _ = _model_update_batch(
        fixture,
        changed_module="cjt_a",
        batch_id="reidentified-model-intent",
    )
    forged = _sealed(
        replace(
            batch.model_intents[0],
            intent_id="forged-model-intent-id",
            intent_digest=ZERO_DIGEST,
        ),
        "intent_digest",
    )
    emit = next(item for item in batch.phase_records if item.phase is TickPhase.EMIT)
    phases = _replace_phase(
        batch.phase_records,
        TickPhase.EMIT,
        outputs={
            **dict(emit.outputs),
            "model_intent_ids": (forged.intent_id,),
        },
    )
    _assert_rejected_atomically(
        fixture,
        replace(batch, model_intents=(forged,), phase_records=phases),
        "MODEL_INTENT_IDENTITY_INVALID",
    )


def test_coordinator_rejects_resealed_nonfrozen_operation_contract(
    tmp_path: Path,
) -> None:
    fixture = _open(tmp_path)
    forged = _sealed(
        replace(
            fixture.contract,
            neural_transform_id="untrusted.transform.v9",
            contract_digest=ZERO_DIGEST,
        ),
        "contract_digest",
    )
    with pytest.raises(
        ValueError,
        match="does not equal the frozen runtime 0.2 contract",
    ):
        NetworkAtomicCoordinator(
            fixture.store,
            coordinator_id=COORDINATOR_ID,
            authority_contract_id=AUTHORITY_ID,
            runtime_id="network-runtime",
            software_digest=SOFTWARE_DIGEST,
            num_attention_heads=1,
            model_manifest_context=MODEL_MANIFEST_CONTEXT,
            operation_contracts={forged.contract_id: forged},
            decoder_contracts={
                cjt_id: fixture.decoder_contract
                for cjt_id in ("cjt-a", "cjt-b", "cjt-c")
            },
            trusted_evidence_sources=("trusted-oracle",),
            candidate_validator=fixture.decoder.validate_candidate,
        )
