"""Factories and immutable state transitions for the Neural CJT prototype.

The wire types deliberately require callers to supply their own digests.  This
module is the single construction path used by the runtime.  It computes every
content identity from canonical, no-float JSON and can rebuild a BiasState from
the bytes persisted by :mod:`cas_cjt.persistence` after a process restart.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Protocol, Sequence

from .contracts import canonical_digest, verify_declared_digest
from .types import (
    BiasState,
    CauseKind,
    CausePacket,
    Governance,
    LocalMemory,
    OntologyStatus,
    OperatingRecord,
    OperatingRegion,
    OperationContract,
    RPMState,
    ReadinessAxis,
    ReadinessAxisName,
    ReadinessState,
    ReadinessStatus,
    SemanticOutcome,
    StableSubstrate,
    TensorArtifactRef,
    ThetaRef,
)


ZERO_DIGEST = "0" * 64
RUNTIME_STATE_SCHEMA = "cas.neural-cjt.runtime-state/0.2"
READINESS_PROFILE_ID = "PROTOTYPE_DWP_PRODUCT/0.1"


class StateContractError(ValueError):
    """A persisted or proposed state failed a local integrity rule."""


def content_id(prefix: str, value: Any, *, length: int = 24) -> str:
    """Return a readable content-derived identifier."""

    if not isinstance(prefix, str) or not prefix:
        raise StateContractError("identifier prefix must be a nonempty string")
    if not isinstance(length, int) or isinstance(length, bool) or not 8 <= length <= 64:
        raise StateContractError("identifier digest length must be between 8 and 64")
    return f"{prefix}-{canonical_digest(value)[:length]}"


def tensor_ref_from_mapping(value: Mapping[str, Any]) -> TensorArtifactRef:
    """Construct the strict public tensor reference returned by encode_tensor."""

    return TensorArtifactRef(
        artifact_id=str(value["artifact_id"]),
        sha256=str(value["sha256"]),
        dtype=str(value["dtype"]),
        shape=tuple(value["shape"]),
        encoding=str(value["encoding"]),
        byte_length=int(value["byte_length"]),
    )


def make_readiness(
    *,
    desire_ppm: int = 1_000_000,
    wisdom_ppm: int = 1_000_000,
    power_ppm: int = 1_000_000,
    threshold_ppm: int = 500_000,
    insufficient_axes: Sequence[ReadinessAxisName | str] = (),
    evidence_refs: Sequence[str] = ("evidence:prototype-authored-readiness",),
) -> ReadinessState:
    """Build three separately inspectable readiness axes."""

    blocked = {ReadinessAxisName(item) for item in insufficient_axes}

    def axis(axis_name: ReadinessAxisName, score: int) -> ReadinessAxis:
        sufficient = axis_name not in blocked and score >= threshold_ppm
        return ReadinessAxis(
            axis=axis_name,
            status=(
                ReadinessStatus.SUFFICIENT
                if sufficient
                else ReadinessStatus.INSUFFICIENT
            ),
            score_ppm=score,
            threshold_ppm=threshold_ppm,
            reason_codes=(
                f"{axis_name.value}_SUFFICIENT"
                if sufficient
                else f"{axis_name.value}_INSUFFICIENT",
            ),
            evidence_refs=tuple(evidence_refs),
            provenance=("prototype:explicit-readiness-input",),
        )

    return ReadinessState(
        profile_id=READINESS_PROFILE_ID,
        desire=axis(ReadinessAxisName.DESIRE, desire_ppm),
        wisdom=axis(ReadinessAxisName.WISDOM, wisdom_ppm),
        power=axis(ReadinessAxisName.POWER, power_ppm),
    )


_OPERATION_DETAILS: dict[
    str, tuple[str, OntologyStatus, str, str, tuple[CauseKind, ...], str]
] = {
    "^6": (
        "decompose",
        OntologyStatus.CANONICAL_ADMITTED,
        "cas.op.decompose.v1",
        "cas.cjt.operation.^6.decompose/0.2",
        (
            CauseKind.IDEA,
            CauseKind.PROPOSITION,
            CauseKind.EFFECT,
            CauseKind.RPM_SUBGOAL,
            CauseKind.TRAINING_EXPERIENCE,
        ),
        "DECOMPOSITION_SIGNAL",
    ),
    "^2": (
        "experimental_attract",
        OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        "prototype.op.attract.v1",
        "cas.cjt.operation.^2.attract.experimental/0.2",
        (CauseKind.IDEA, CauseKind.EFFECT),
        "ATTRACTION_SIGNAL",
    ),
    "^3": (
        "experimental_avert",
        OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        "prototype.op.avert.v1",
        "cas.cjt.operation.^3.avert.experimental/0.2",
        (CauseKind.IDEA, CauseKind.EFFECT),
        "AVERSION_SIGNAL",
    ),
    "^8": (
        "experimental_trigger",
        OntologyStatus.EXPERIMENTAL_CONFLICTED_SEMANTICS,
        "prototype.op.trigger.v1",
        "cas.cjt.operation.^8.trigger.experimental/0.2",
        (CauseKind.EVENT, CauseKind.EFFECT),
        "ASSOCIATION_SIGNAL",
    ),
}


def make_operation_contract(operation_id: str) -> OperationContract:
    """Create one of the four frozen prototype operation contracts."""

    try:
        name, status, transform_id, contract_id, accepted_kinds, effect_kind = (
            _OPERATION_DETAILS[operation_id]
        )
    except KeyError as exc:
        raise StateContractError(f"unknown operation identity: {operation_id}") from exc
    verifier_descriptor = {
        "verifier_id": "independent-effect-verifier",
        "verifier_version": 1,
        "policy_id": "cas.neural-cjt.exact-semantic-verifier/0.2",
    }
    placeholder = OperationContract(
        contract_id=contract_id,
        contract_version=1,
        operation_id=operation_id,
        operation_name=name,
        ontology_status=status,
        accepted_cause_kinds=accepted_kinds,
        accepted_schema_versions=(CausePacket.SCHEMA_VERSION,),
        permitted_evidence_ports=("AUTHORED_TARGET", "MEMORY", "PROVENANCE"),
        neural_transform_id=transform_id,
        effect_schema_id=f"{CandidateEffectSchema.ID}:{effect_kind}",
        memory_interface=("READ_REFERENCES", "PROPOSE_WRITE"),
        readiness_profile_id=READINESS_PROFILE_ID,
        legal_actions=("PROPOSE_EFFECT",),
        legal_bias_paths=("/memory", "/rpm", "/operating", "/theta"),
        temporal_transition_law="EFFECT_TO_CAUSE_ONLY_AFTER_COMMIT",
        verifier_id="independent-effect-verifier",
        verifier_version=1,
        verifier_digest=canonical_digest(verifier_descriptor),
        plasticity_groups=(f"operation:{operation_id}", "bias_update_head"),
        governance_requirements=(
            "execute",
            "publish_effect",
            "write_bias",
            "learn",
        ),
        contract_digest=ZERO_DIGEST,
    )
    return replace(
        placeholder,
        contract_digest=canonical_digest(
            placeholder.to_dict(), omit_keys=("contract_digest",)
        ),
    )


class CandidateEffectSchema:
    """Stable name for the prototype candidate Effect payload contract."""

    ID = "cas.neural-cjt.candidate-effect-content/0.2"


def make_cause(
    *,
    tick: int,
    content: Mapping[str, Any],
    goal_context: Mapping[str, Any],
    cause_kind: CauseKind = CauseKind.IDEA,
    source: str = "prototype:user-input",
    provenance: Sequence[str] = ("prototype:local-input",),
    uncertainty_ppm: int = 0,
    entity_bindings: Sequence[str] = (),
    relation_bindings: Sequence[str] = (),
    candidate_operation_ids: Sequence[str] = ("^6",),
    memory_refs: Sequence[str] = (),
    content_ref: TensorArtifactRef | None = None,
    parent_effect_id: str | None = None,
    originating_cjt_id: str | None = None,
    originating_modality: str | None = None,
) -> CausePacket:
    """Create a typed Cause whose identity binds its structured envelope."""

    identity = {
        "tick": tick,
        "cause_kind": cause_kind.value,
        "content": dict(content),
        "goal_context": dict(goal_context),
        "source": source,
        "provenance": list(provenance),
        "uncertainty_ppm": uncertainty_ppm,
        "entity_bindings": list(entity_bindings),
        "relation_bindings": list(relation_bindings),
        "candidate_operation_ids": list(candidate_operation_ids),
        "memory_refs": list(memory_refs),
        "content_ref": None if content_ref is None else content_ref.to_dict(),
        "parent_effect_id": parent_effect_id,
        "originating_cjt_id": originating_cjt_id,
        "originating_modality": originating_modality,
    }
    return CausePacket(
        cause_id=content_id("cause", identity),
        tick=tick,
        cause_kind=cause_kind,
        content=content,
        source=source,
        provenance=tuple(provenance),
        time_label=f"logical-tick:{tick}",
        uncertainty_ppm=uncertainty_ppm,
        goal_context=goal_context,
        entity_bindings=tuple(entity_bindings),
        relation_bindings=tuple(relation_bindings),
        candidate_operation_ids=tuple(candidate_operation_ids),
        memory_refs=tuple(memory_refs),
        originating_cjt_id=originating_cjt_id,
        originating_modality=originating_modality,
        parent_effect_id=parent_effect_id,
        content_ref=content_ref,
    )


def verify_cause_identity(cause: CausePacket) -> bool:
    """Verify that a Cause ID binds every semantic and provenance field."""

    if not isinstance(cause, CausePacket):
        return False
    identity = {
        "tick": cause.tick,
        "cause_kind": cause.cause_kind.value,
        "content": cause.content,
        "goal_context": cause.goal_context,
        "source": cause.source,
        "provenance": list(cause.provenance),
        "uncertainty_ppm": cause.uncertainty_ppm,
        "entity_bindings": list(cause.entity_bindings),
        "relation_bindings": list(cause.relation_bindings),
        "candidate_operation_ids": list(cause.candidate_operation_ids),
        "memory_refs": list(cause.memory_refs),
        "content_ref": None if cause.content_ref is None else cause.content_ref.to_dict(),
        "parent_effect_id": cause.parent_effect_id,
        "originating_cjt_id": cause.originating_cjt_id,
        "originating_modality": cause.originating_modality,
    }
    return cause.cause_id == content_id("cause", identity)


class _CommittedEffectStore(Protocol):
    def immutable_document(self, table: str, record_id: str) -> dict[str, Any]: ...

    def receipt_by_id(self, receipt_id: str) -> dict[str, Any]: ...

    def trace_events(self, *, public: bool = False) -> tuple[dict[str, Any], ...]: ...

    def has_artifact(self, artifact_id: str, sha256: str | None = None) -> bool: ...


def cause_from_committed_effect(
    store: _CommittedEffectStore,
    published_effect_id: str,
    *,
    tick: int,
    candidate_operation_ids: Sequence[str],
    goal_context: Mapping[str, Any],
) -> CausePacket:
    """The only normal cascade constructor: a committed Effect becomes Cause."""

    published_effect = store.immutable_document("published_effects", published_effect_id)
    if published_effect.get("contract_type") != "PUBLISHED_EFFECT":
        raise StateContractError("only a PublishedEffect may enter the cascade")
    if published_effect.get("authoritative") is not True:
        raise StateContractError("an uncommitted Effect cannot become a Cause")
    if not verify_declared_digest(published_effect, "publication_digest"):
        raise StateContractError("PublishedEffect digest mismatch")
    if published_effect.get("published_effect_id") != published_effect_id:
        raise StateContractError("PublishedEffect store identity mismatch")
    receipt = store.receipt_by_id(str(published_effect.get("commit_receipt_id")))
    if (
        receipt.get("disposition") != "COMMITTED"
        or published_effect_id not in receipt.get("published_effect_ids", [])
        or receipt.get("trace_id")
        not in {event.get("trace_id") for event in store.trace_events()}
    ):
        raise StateContractError("PublishedEffect is not bound to a durable commit and trace")
    ref_value = published_effect.get("content_ref")
    ref = None if ref_value is None else tensor_ref_from_mapping(ref_value)
    if ref is not None and not store.has_artifact(ref.artifact_id, ref.sha256):
        raise StateContractError("PublishedEffect tensor artifact is not retained")
    return make_cause(
        tick=tick,
        cause_kind=CauseKind.EFFECT,
        content={
            "published_effect_id": published_effect["published_effect_id"],
            "candidate_effect_id": published_effect["candidate_effect_id"],
            "semantic_content": published_effect["content"],
        },
        goal_context=goal_context,
        source="prototype:committed-effect-cascade",
        provenance=(
            f"published-effect:{published_effect['published_effect_id']}",
            f"commit-receipt:{published_effect['commit_receipt_id']}",
        ),
        candidate_operation_ids=tuple(candidate_operation_ids),
        content_ref=ref,
        parent_effect_id=str(published_effect["published_effect_id"]),
        originating_cjt_id=str(published_effect["producer_cjt_id"]),
    )


def make_initial_bias(
    *,
    cjt_id: str,
    operation_id: str,
    model_id: str,
    model_digest: str,
    checkpoint_ref: TensorArtifactRef,
    readiness: ReadinessState | None = None,
    compute_ceiling_units: int = 8,
    beta_microunits: int = 1_000_000,
) -> BiasState:
    """Build the complete six-compartment Bias at version zero."""

    contract = make_operation_contract(operation_id)
    readiness = make_readiness() if readiness is None else readiness
    operation_group = f"cjt:{cjt_id}:operation:{operation_id}"
    bias_group = f"cjt:{cjt_id}:bias_update_head"
    stable = StableSubstrate(
        cjt_id=cjt_id,
        formation_version=1,
        registered_operation_id=operation_id,
        specialization_tags=("neural-cjt", contract.operation_name),
        lineage_refs=("casformer-reference/0.1.0",),
        configuration_digest=canonical_digest(
            {
                "operation_contract_digest": contract.contract_digest,
                "readiness_profile_id": readiness.profile_id,
                "compute_ceiling_units": compute_ceiling_units,
            }
        ),
    )
    bias = BiasState(
        bias_id=f"bias:{cjt_id}",
        cjt_id=cjt_id,
        version=0,
        previous_digest=None,
        stable=stable,
        memory=LocalMemory(
            recurrent_state_ref=None,
            recent_cause_ids=(),
            recent_candidate_effect_ids=(),
            verifier_receipt_ids=(),
            repair_frame_ids=(),
            retrieved_memory_refs=(),
            provenance_refs=(),
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
            region=OperatingRegion.UNASSESSED,
            stability_status="UNASSESSED",
            response_model_status="PROTOTYPE",
            semantic_outcome=SemanticOutcome.UNASSESSED,
            previous_committed_verifier_receipt_id=None,
            last_tick=0,
        ),
        theta=ThetaRef(
            model_id=model_id,
            model_version=0,
            model_digest=model_digest,
            parameter_artifacts=(checkpoint_ref,),
            parameter_group_ids=(operation_group, bias_group),
            beta_microunits=beta_microunits,
            operating_profile_id="CASFORMER_CJT_REGIONS/0.1",
            adapter_ids=(),
        ),
        governance=Governance(
            hard_permissions=(
                "execute",
                "publish_effect",
                "read_memory",
                "write_bias",
                "write_memory",
            ),
            topology_permissions=("local", "cascade"),
            learning_permissions=("learn", operation_group, bias_group),
            compute_ceiling_units=compute_ceiling_units,
            quarantined=False,
            state_write_authorities=("prototype-atomic-coordinator",),
            memory_write_authorities=("prototype-atomic-coordinator",),
            effect_publication_authorities=("prototype-atomic-coordinator",),
            owner_restrictions=("NO_EXTERNAL_ACTION", "NO_CNCM_AUTHORITY"),
        ),
        state_digest=ZERO_DIGEST,
    )
    return replace(
        bias,
        state_digest=canonical_digest(bias.to_dict(), omit_keys=("state_digest",)),
    )


def advance_bias(
    bias: BiasState,
    *,
    tick: int,
    region: OperatingRegion,
    semantic_outcome: SemanticOutcome,
    verifier_receipt_id: str,
    cause_id: str | None = None,
    effect_id: str | None = None,
    recurrent_state_ref: TensorArtifactRef | None = None,
    open_repair_id: str | None = None,
    open_repair_return_address: str | None = None,
    close_repair_id: str | None = None,
    retrieved_memory_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
    theta: ThetaRef | None = None,
    record_memory: bool = True,
) -> BiasState:
    """Propose the next complete Bias revision without mutating its input."""

    recent_causes = list(bias.memory.recent_cause_ids)
    recent_effects = list(bias.memory.recent_candidate_effect_ids)
    receipts = list(bias.memory.verifier_receipt_ids)
    repairs = list(bias.memory.repair_frame_ids)
    retrieved = list(bias.memory.retrieved_memory_refs)
    provenance = list(bias.memory.provenance_refs)
    if record_memory and cause_id is not None and cause_id not in recent_causes:
        recent_causes.append(cause_id)
    if record_memory and effect_id is not None and effect_id not in recent_effects:
        recent_effects.append(effect_id)
    if record_memory and verifier_receipt_id not in receipts:
        receipts.append(verifier_receipt_id)
    if open_repair_id is not None and open_repair_id not in repairs:
        repairs.append(open_repair_id)
    if record_memory:
        for reference in retrieved_memory_refs:
            if reference not in retrieved:
                retrieved.append(reference)
        for reference in provenance_refs:
            if reference not in provenance:
                provenance.append(reference)

    open_repairs = list(bias.rpm.open_repair_ids)
    history = list(bias.rpm.repair_history)
    if open_repair_id is not None and (
        not isinstance(open_repair_return_address, str)
        or not open_repair_return_address
    ):
        raise StateContractError(
            "opening a repair requires its exact nonempty return address"
        )
    if open_repair_id is None and open_repair_return_address is not None:
        raise StateContractError("a repair return address requires an opened repair")
    if open_repair_id is not None and open_repair_id not in open_repairs:
        open_repairs.append(open_repair_id)
    if close_repair_id is not None:
        open_repairs = [item for item in open_repairs if item != close_repair_id]
        if close_repair_id not in history:
            history.append(close_repair_id)
    if len(open_repairs) > 1:
        raise StateContractError("v0.2 permits at most one open repair per Bias")

    next_bias = replace(
        bias,
        version=bias.version + 1,
        previous_digest=bias.state_digest,
        memory=replace(
            bias.memory,
            recurrent_state_ref=(
                recurrent_state_ref
                if recurrent_state_ref is not None
                else bias.memory.recurrent_state_ref
            ),
            recent_cause_ids=tuple(recent_causes[-16:]),
            recent_candidate_effect_ids=tuple(recent_effects[-16:]),
            verifier_receipt_ids=tuple(receipts[-16:]),
            repair_frame_ids=tuple(repairs[-16:]),
            retrieved_memory_refs=tuple(retrieved[-16:]),
            provenance_refs=tuple(provenance[-16:]),
        ),
        rpm=replace(
            bias.rpm,
            open_repair_ids=tuple(open_repairs),
            suspended_parent_cause_id=(
                cause_id
                if open_repair_id is not None
                else (
                    bias.rpm.suspended_parent_cause_id
                    if open_repairs
                    else None
                )
            ),
            return_addresses=(
                (open_repair_return_address,)
                if open_repair_id is not None
                else (bias.rpm.return_addresses if open_repairs else ())
            ),
            repair_history=tuple(history[-16:]),
        ),
        operating=replace(
            bias.operating,
            region=region,
            stability_status=("FAULT" if region is OperatingRegion.BREAKDOWN else "STABLE"),
            semantic_outcome=semantic_outcome,
            previous_committed_verifier_receipt_id=verifier_receipt_id,
            last_tick=tick,
        ),
        theta=bias.theta if theta is None else theta,
        state_digest=ZERO_DIGEST,
    )
    return replace(
        next_bias,
        state_digest=canonical_digest(next_bias.to_dict(), omit_keys=("state_digest",)),
    )


def _axis_from_dict(value: Mapping[str, Any]) -> ReadinessAxis:
    return ReadinessAxis(
        axis=value["axis"],
        status=value["status"],
        score_ppm=value["score_ppm"],
        threshold_ppm=value["threshold_ppm"],
        reason_codes=tuple(value["reason_codes"]),
        evidence_refs=tuple(value["evidence_refs"]),
        provenance=tuple(value["provenance"]),
    )


def bias_from_dict(value: Mapping[str, Any], *, verify_digest: bool = True) -> BiasState:
    """Rebuild and validate a persisted BiasState."""

    readiness_value = value["rpm"]["readiness"]
    readiness = ReadinessState(
        profile_id=readiness_value["profile_id"],
        desire=_axis_from_dict(readiness_value["desire"]),
        wisdom=_axis_from_dict(readiness_value["wisdom"]),
        power=_axis_from_dict(readiness_value["power"]),
    )
    recurrent = value["memory"]["recurrent_state_ref"]
    theta_artifacts = tuple(
        tensor_ref_from_mapping(item) for item in value["theta"]["parameter_artifacts"]
    )
    result = BiasState(
        bias_id=value["bias_id"],
        cjt_id=value["cjt_id"],
        version=value["version"],
        previous_digest=value["previous_digest"],
        stable=StableSubstrate(
            cjt_id=value["stable"]["cjt_id"],
            formation_version=value["stable"]["formation_version"],
            registered_operation_id=value["stable"]["registered_operation_id"],
            specialization_tags=tuple(value["stable"]["specialization_tags"]),
            lineage_refs=tuple(value["stable"]["lineage_refs"]),
            configuration_digest=value["stable"]["configuration_digest"],
        ),
        memory=LocalMemory(
            recurrent_state_ref=(
                None if recurrent is None else tensor_ref_from_mapping(recurrent)
            ),
            recent_cause_ids=tuple(value["memory"]["recent_cause_ids"]),
            recent_candidate_effect_ids=tuple(
                value["memory"]["recent_candidate_effect_ids"]
            ),
            verifier_receipt_ids=tuple(value["memory"]["verifier_receipt_ids"]),
            repair_frame_ids=tuple(value["memory"]["repair_frame_ids"]),
            retrieved_memory_refs=tuple(value["memory"]["retrieved_memory_refs"]),
            provenance_refs=tuple(value["memory"]["provenance_refs"]),
        ),
        rpm=RPMState(
            readiness=readiness,
            unmet_prerequisites=tuple(value["rpm"]["unmet_prerequisites"]),
            open_repair_ids=tuple(value["rpm"]["open_repair_ids"]),
            suspended_parent_cause_id=value["rpm"]["suspended_parent_cause_id"],
            return_addresses=tuple(value["rpm"]["return_addresses"]),
            repair_history=tuple(value["rpm"]["repair_history"]),
        ),
        operating=OperatingRecord(
            region=value["operating"]["region"],
            stability_status=value["operating"]["stability_status"],
            response_model_status=value["operating"]["response_model_status"],
            semantic_outcome=value["operating"]["semantic_outcome"],
            previous_committed_verifier_receipt_id=value["operating"][
                "previous_committed_verifier_receipt_id"
            ],
            last_tick=value["operating"]["last_tick"],
        ),
        theta=ThetaRef(
            model_id=value["theta"]["model_id"],
            model_version=value["theta"]["model_version"],
            model_digest=value["theta"]["model_digest"],
            parameter_artifacts=theta_artifacts,
            parameter_group_ids=tuple(value["theta"]["parameter_group_ids"]),
            beta_microunits=value["theta"]["beta_microunits"],
            operating_profile_id=value["theta"]["operating_profile_id"],
            adapter_ids=tuple(value["theta"]["adapter_ids"]),
        ),
        governance=Governance(
            hard_permissions=tuple(value["governance"]["hard_permissions"]),
            topology_permissions=tuple(value["governance"]["topology_permissions"]),
            learning_permissions=tuple(value["governance"]["learning_permissions"]),
            compute_ceiling_units=value["governance"]["compute_ceiling_units"],
            quarantined=value["governance"]["quarantined"],
            state_write_authorities=tuple(value["governance"]["state_write_authorities"]),
            memory_write_authorities=tuple(value["governance"]["memory_write_authorities"]),
            effect_publication_authorities=tuple(
                value["governance"]["effect_publication_authorities"]
            ),
            owner_restrictions=tuple(value["governance"]["owner_restrictions"]),
        ),
        state_digest=value["state_digest"],
    )
    if verify_digest and not verify_declared_digest(result, "state_digest"):
        raise StateContractError("persisted Bias state_digest mismatch")
    return result


def make_runtime_state(
    *,
    runtime_id: str,
    state_version: int,
    logical_tick: int,
    biases: Sequence[BiasState],
    model_digest: str,
    model_version: int = 0,
    open_repairs: Sequence[Mapping[str, Any]] = (),
    published_effect_ids: Sequence[str] = (),
    memory_record_ids: Sequence[str] = (),
    parent_state_digest: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Build the one authoritative runtime snapshot stored under one digest."""

    if len({bias.cjt_id for bias in biases}) != len(tuple(biases)):
        raise StateContractError("runtime state contains duplicate CJT identities")
    payload = {
        "schema_version": RUNTIME_STATE_SCHEMA,
        "runtime_id": runtime_id,
        "state_version": state_version,
        "logical_tick": logical_tick,
        "parent_state_digest": parent_state_digest,
        "active_model_digest": model_digest,
        "model_version": model_version,
        "biases": {
            bias.cjt_id: bias.to_dict() for bias in sorted(biases, key=lambda item: item.cjt_id)
        },
        "open_repairs": [dict(item) for item in open_repairs],
        "published_effect_ids": sorted(set(published_effect_ids)),
        "memory_record_ids": sorted(set(memory_record_ids)),
        "state_digest": ZERO_DIGEST,
    }
    digest = canonical_digest(payload, omit_keys=("state_digest",))
    payload["state_digest"] = digest
    return payload, digest


def load_runtime_biases(state: Mapping[str, Any]) -> dict[str, BiasState]:
    """Verify the runtime envelope and rebuild each complete Bias."""

    if state.get("schema_version") != RUNTIME_STATE_SCHEMA:
        raise StateContractError("runtime state schema mismatch")
    if not verify_declared_digest(state, "state_digest"):
        raise StateContractError("runtime state_digest mismatch")
    biases = state.get("biases")
    if not isinstance(biases, Mapping) or not biases:
        raise StateContractError("runtime state must contain Bias records")
    rebuilt = {key: bias_from_dict(value) for key, value in biases.items()}
    if any(key != bias.cjt_id for key, bias in rebuilt.items()):
        raise StateContractError("runtime Bias index does not match cjt_id")
    return rebuilt


__all__ = [
    "CandidateEffectSchema",
    "READINESS_PROFILE_ID",
    "RUNTIME_STATE_SCHEMA",
    "StateContractError",
    "ZERO_DIGEST",
    "advance_bias",
    "bias_from_dict",
    "cause_from_committed_effect",
    "content_id",
    "load_runtime_biases",
    "make_cause",
    "make_initial_bias",
    "make_operation_contract",
    "make_readiness",
    "make_runtime_state",
    "tensor_ref_from_mapping",
    "verify_cause_identity",
]
