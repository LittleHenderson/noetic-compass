from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from copy import deepcopy

import pytest

from cas_cjt.contracts import (
    ContractSchemaError,
    assert_no_json_floats,
    canonical_digest,
    canonical_json,
    is_valid_contract,
    load_contract_schema,
    validate_contract,
    verify_declared_digest,
)
from cas_cjt.phase_contract import REQUIRED_PHASE_FIELDS
from cas_cjt.types import (
    AuthorityCapability,
    BiasState,
    CandidateEffect,
    CauseKind,
    CausePacket,
    CommitDisposition,
    CommitReceipt,
    ContractTypeError,
    Governance,
    LocalMemory,
    MANDATORY_TICK_ORDER,
    MemoryKind,
    MemoryWriteIntent,
    ModelUpdateIntent,
    ModelUpdateKind,
    OntologyStatus,
    OperatingRecord,
    OperatingRegion,
    OperationContract,
    PhaseRecord,
    PublishedEffect,
    RPMState,
    ReadinessAxis,
    ReadinessAxisName,
    ReadinessState,
    ReadinessStatus,
    RepairFrame,
    RepairOutcome,
    RepairStatus,
    SemanticOutcome,
    StableSubstrate,
    StateUpdateIntent,
    TensorArtifactRef,
    ThetaRef,
    TickPhase,
    TickTrace,
    VerifierDisposition,
    VerifierReceipt,
)


H0 = "0" * 64
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64


def artifact(identifier: str = "tensor-1", *, digest: str = H1) -> TensorArtifactRef:
    return TensorArtifactRef(
        artifact_id=identifier,
        sha256=digest,
        dtype="float32",
        shape=(2, 3),
        encoding="raw-contiguous-v1",
        byte_length=24,
    )


def axis(
    name: ReadinessAxisName,
    *,
    status: ReadinessStatus = ReadinessStatus.SUFFICIENT,
    score: int = 800_000,
) -> ReadinessAxis:
    return ReadinessAxis(
        axis=name,
        status=status,
        score_ppm=score,
        threshold_ppm=500_000,
        reason_codes=(f"{name.value}_AUTHORED",),
        evidence_refs=(f"evidence-{name.value.lower()}",),
        provenance=("prototype-dwp-profile/0.1",),
    )


def readiness(*, wisdom_status: ReadinessStatus = ReadinessStatus.SUFFICIENT) -> ReadinessState:
    return ReadinessState(
        profile_id="PROTOTYPE_DWP_PRODUCT/0.1",
        desire=axis(ReadinessAxisName.DESIRE),
        wisdom=axis(ReadinessAxisName.WISDOM, status=wisdom_status),
        power=axis(ReadinessAxisName.POWER, score=700_000),
    )


def bias() -> BiasState:
    tensor = artifact()
    return BiasState(
        bias_id="bias-cjt-1",
        cjt_id="cjt-1",
        version=0,
        previous_digest=None,
        stable=StableSubstrate(
            cjt_id="cjt-1",
            formation_version=1,
            registered_operation_id="^6",
            specialization_tags=("toy-decomposition",),
            lineage_refs=("genesis",),
            configuration_digest=H1,
        ),
        memory=LocalMemory(
            recurrent_state_ref=tensor,
            recent_cause_ids=("cause-0",),
            recent_candidate_effect_ids=(),
            verifier_receipt_ids=(),
            repair_frame_ids=(),
            retrieved_memory_refs=("memory-0",),
            provenance_refs=("fixture-v1",),
        ),
        rpm=RPMState(
            readiness=readiness(),
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
            model_digest=H2,
            parameter_artifacts=(tensor,),
            parameter_group_ids=("operator.^6",),
            beta_microunits=1_000_000,
            operating_profile_id="cjt-region/0.2",
            adapter_ids=("casformer-v0.1",),
        ),
        governance=Governance(
            hard_permissions=("EXECUTE",),
            topology_permissions=("cjt-1->cjt-2",),
            learning_permissions=("operator.^6",),
            compute_ceiling_units=32,
            quarantined=False,
            state_write_authorities=("prototype-coordinator",),
            memory_write_authorities=("prototype-coordinator",),
            effect_publication_authorities=("prototype-coordinator",),
            owner_restrictions=("NO_EXTERNAL_ACTION",),
        ),
        state_digest=H3,
    )


def cause(*, kind: CauseKind = CauseKind.PROPOSITION, parent: str | None = None) -> CausePacket:
    return CausePacket(
        cause_id="cause-1",
        tick=1,
        cause_kind=kind,
        content={"predicate": "has_parts", "arguments": ["whole"]},
        source="fixture",
        provenance=("fixture:typed-cause",),
        time_label="logical-tick-1",
        uncertainty_ppm=20_000,
        goal_context={"goal_id": "goal-1"},
        entity_bindings=("whole",),
        relation_bindings=("has_parts",),
        candidate_operation_ids=("^6",),
        memory_refs=("memory-0",),
        originating_cjt_id=None,
        originating_modality="typed-fixture",
        parent_effect_id=parent,
        content_ref=artifact("cause-vector"),
    )


def operation(
    operation_id: str = "^6",
    name: str = "decompose",
    status: OntologyStatus = OntologyStatus.CANONICAL_ADMITTED,
) -> OperationContract:
    return OperationContract(
        contract_id=f"operation-{operation_id}-v1",
        contract_version=1,
        operation_id=operation_id,
        operation_name=name,
        ontology_status=status,
        accepted_cause_kinds=(CauseKind.PROPOSITION, CauseKind.EFFECT),
        accepted_schema_versions=(CausePacket.SCHEMA_VERSION,),
        permitted_evidence_ports=("typed-content",),
        neural_transform_id="relation-operator-bank",
        effect_schema_id=CandidateEffect.SCHEMA_VERSION,
        memory_interface=("READ_LOCAL", "PROPOSE_WRITE"),
        readiness_profile_id="PROTOTYPE_DWP_PRODUCT/0.1",
        legal_actions=("PROPOSE_EFFECT",),
        legal_bias_paths=("/memory/recent_candidate_effect_ids", "/operating"),
        temporal_transition_law="NEXT_TICK_ONLY",
        verifier_id="fixture-semantic-verifier",
        verifier_version=1,
        verifier_digest=H1,
        plasticity_groups=("operator.^6",),
        governance_requirements=("EXECUTE",),
        contract_digest=H2,
    )


def candidate() -> CandidateEffect:
    return CandidateEffect(
        candidate_effect_id="candidate-1",
        tick=1,
        parent_cause_id="cause-1",
        producer_cjt_id="cjt-1",
        operation_id="^6",
        operation_contract_id="operation-^6-v1",
        operation_contract_digest=H2,
        bias_id="bias-cjt-1",
        bias_version=0,
        bias_digest=H3,
        model_digest=H2,
        content={"parts": ["part-a", "part-b"]},
        content_ref=artifact("effect-vector"),
        uncertainty_ppm=30_000,
        provenance=("neural-cjt:cjt-1",),
        candidate_digest=H4,
    )


def verifier(*, disposition: VerifierDisposition = VerifierDisposition.ACCEPT) -> VerifierReceipt:
    accepted = disposition is VerifierDisposition.ACCEPT
    return VerifierReceipt(
        receipt_id="verifier-1",
        tick=1,
        verifier_id="fixture-semantic-verifier",
        verifier_version=1,
        verifier_digest=H2,
        independent=True,
        cause_id="cause-1",
        candidate_effect_id="candidate-1",
        candidate_effect_digest=H4,
        bias_id="bias-cjt-1",
        bias_version=0,
        bias_digest=H3,
        operation_contract_id="operation-^6-v1",
        operation_contract_digest=H2,
        model_digest=H2,
        semantic_outcome=SemanticOutcome.INTENDED if accepted else SemanticOutcome.OFF_AXIS,
        disposition=disposition,
        reason_codes=("FIXTURE_MATCH" if accepted else "OFF_AXIS",),
        evidence_refs=("fixture:oracle",),
        repair_required=disposition is VerifierDisposition.REPAIR,
        receipt_digest=H1,
    )


def phases() -> tuple[PhaseRecord, ...]:
    records = []
    for phase in MANDATORY_TICK_ORDER:
        contract = REQUIRED_PHASE_FIELDS[phase]
        inputs = {key: None for key in contract["inputs"]}
        outputs = {key: None for key in contract["outputs"]}
        diagnostics = {key: None for key in contract["diagnostics"]}
        compute_units = 1 if phase is TickPhase.EXECUTE else 0
        if phase is TickPhase.EXECUTE:
            outputs["compute_units_used"] = compute_units
        records.append(
            PhaseRecord(
                phase=phase,
                tick=1,
                inputs=inputs,
                outputs=outputs,
                diagnostics=diagnostics,
                compute_units=compute_units,
            )
        )
    return tuple(records)


def all_valid_contracts() -> tuple[object, ...]:
    tensor = artifact()
    cause_value = cause()
    readiness_value = readiness()
    bias_value = bias()
    candidate_value = candidate()
    operation_value = operation()
    verifier_value = verifier()
    repair = RepairFrame(
        repair_id="repair-1",
        opened_tick=1,
        eligible_tick=2,
        parent_cause_id="cause-1",
        rejected_candidate_effect_id="candidate-1",
        verifier_receipt_id="verifier-1",
        suspended_bias_id="bias-cjt-1",
        suspended_bias_version=0,
        prerequisite_axis=ReadinessAxisName.WISDOM,
        subgoal_cause_id="cause-repair-1",
        return_address="runtime:cjt-1:tick-2",
        depth=1,
        max_depth=3,
        branch_count=1,
        max_branches=2,
        budget_units=8,
        consumed_units=0,
        cycle_key="goal-1|wisdom",
        status=RepairStatus.OPEN,
        result_effect_id=None,
        frame_digest=H1,
    )
    repair_outcome = RepairOutcome(
        outcome_id="repair-outcome-1",
        repair_id=repair.repair_id,
        tick=3,
        status=RepairStatus.RETURNED,
        frame_digest=repair.frame_digest,
        result_effect_id="published-repair-1",
        result_effect_digest=H2,
        result_effect_commit_receipt_id="commit-repair-1",
        resumed_cause_id="cause-resumed-1",
        resumed_candidate_effect_id="candidate-resumed-1",
        verifier_receipt_id="verifier-resumed-1",
        target_bias_id="bias-cjt-1",
        target_bias_version=1,
        target_bias_digest=H3,
        outcome_digest=H4,
    )
    state_intent = StateUpdateIntent(
        intent_id="state-intent-1",
        tick=1,
        issuer_id="cjt-1",
        authority_capability=AuthorityCapability.PROPOSE_STATE_UPDATE.value,
        target_bias_id="bias-cjt-1",
        expected_bias_version=0,
        expected_bias_digest=H3,
        target_path="/operating/semantic_outcome",
        replacement={"value": "INTENDED"},
        verifier_receipt_id="verifier-1",
        reason_codes=("VERIFIED",),
        intent_digest=H1,
    )
    model_intent = ModelUpdateIntent(
        intent_id="model-intent-1",
        tick=1,
        issuer_id="learning-controller",
        authority_capability=AuthorityCapability.PROPOSE_MODEL_UPDATE.value,
        model_id="model-1",
        expected_model_version=0,
        expected_model_digest=H2,
        update_kind=ModelUpdateKind.GRADIENT_DELTA,
        parameter_group_ids=("operator.^6",),
        candidate_artifact=artifact("candidate-model", digest=H3),
        gradient_artifact=artifact("gradient", digest=H4),
        plasticity_ppm=600_000,
        verifier_receipt_id="verifier-1",
        qualification_receipt_id="qualification-1",
        reason_codes=("LOSS_IMPROVED",),
        intent_digest=H1,
    )
    memory_intent = MemoryWriteIntent(
        intent_id="memory-intent-1",
        tick=1,
        issuer_id="cjt-1",
        authority_capability=AuthorityCapability.PROPOSE_MEMORY_WRITE.value,
        target_bias_id="bias-cjt-1",
        expected_bias_version=0,
        expected_bias_digest=H3,
        memory_record_id="memory-1",
        memory_kind=MemoryKind.EPISODIC,
        content={"cause_id": "cause-1", "effect_id": "candidate-1"},
        content_ref=None,
        confidence_ppm=900_000,
        provenance=("verifier-1",),
        evidence_refs=("fixture:oracle",),
        verifier_receipt_id="verifier-1",
        intent_digest=H1,
    )
    commit = CommitReceipt(
        receipt_id="commit-1",
        tick=1,
        batch_id="batch-1",
        coordinator_id="prototype-coordinator",
        authority_contract_id="prototype-authority/0.2",
        authorized=True,
        disposition=CommitDisposition.COMMITTED,
        pre_state_digest=H3,
        post_state_digest=H4,
        pre_model_digest=H2,
        post_model_digest=H2,
        accepted_intent_ids=("state-intent-1",),
        rejected_intent_ids=(),
        published_effect_ids=("published-1",),
        opened_repair_ids=(),
        reason_codes=("ATOMIC_COMMIT",),
        atomic=True,
        rollback_of_receipt_id=None,
        persisted_snapshot_id="snapshot-1",
        trace_id="trace-1",
        receipt_digest=H1,
    )
    published = PublishedEffect(
        published_effect_id="published-1",
        candidate_effect_id="candidate-1",
        tick=1,
        producer_cjt_id="cjt-1",
        content={"parts": ["part-a", "part-b"]},
        content_ref=tensor,
        verifier_receipt_id="verifier-1",
        commit_receipt_id="commit-1",
        provenance=("candidate-1", "verifier-1", "commit-1"),
        publication_digest=H2,
    )
    trace = TickTrace(
        trace_id="trace-1",
        tick=1,
        runtime_id="prototype-runtime",
        software_digest=H0,
        cause_id="cause-1",
        cjt_ids=("cjt-1",),
        pre_state_digest=H3,
        post_state_digest=H4,
        pre_model_digest=H2,
        post_model_digest=H2,
        phases=phases(),
        candidate_effect_ids=("candidate-1",),
        published_effect_ids=("published-1",),
        verifier_receipt_ids=("verifier-1",),
        commit_receipt_id="commit-1",
        memory_read_refs=("memory-0",),
        memory_write_refs=("memory-1",),
        accepted_intent_ids=("state-intent-1",),
        rejected_intent_ids=(),
        previous_trace_digest=None,
        sealed=True,
        trace_digest=H1,
    )
    return (
        tensor,
        cause_value,
        readiness_value.desire,
        readiness_value,
        bias_value.stable,
        bias_value.memory,
        bias_value.rpm,
        bias_value.operating,
        bias_value.theta,
        bias_value.governance,
        bias_value,
        candidate_value,
        published,
        operation_value,
        verifier_value,
        repair,
        repair_outcome,
        state_intent,
        model_intent,
        memory_intent,
        commit,
        phases()[0],
        trace,
    )


def test_schema_is_valid_draft_2020_12() -> None:
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(load_contract_schema())


@pytest.mark.parametrize("value", all_valid_contracts())
def test_every_public_contract_has_a_strict_valid_wire_shape(value: object) -> None:
    wire = validate_contract(value)  # type: ignore[arg-type]
    assert wire["contract_type"] == value.contract_type  # type: ignore[attr-defined]
    assert is_valid_contract(wire)
    assert ".0" not in canonical_json(wire)


def test_frozen_types_are_deeply_immutable() -> None:
    value = cause()
    with pytest.raises(FrozenInstanceError):
        value.tick = 2  # type: ignore[misc]
    with pytest.raises(TypeError):
        value.content["predicate"] = "changed"  # type: ignore[index]
    assert isinstance(value.content["arguments"], tuple)


@pytest.mark.parametrize("bad", [0.25, {"nested": [1, 2.0]}, {"x": float("nan")}])
def test_authoritative_json_rejects_all_float_values(bad: object) -> None:
    with pytest.raises(ContractTypeError, match="float"):
        assert_no_json_floats(bad)
    with pytest.raises(ContractTypeError, match="float"):
        CausePacket(
            cause_id="bad",
            tick=0,
            cause_kind=CauseKind.IDEA,
            content={"bad": bad},
            source="fixture",
            provenance=("fixture",),
            time_label="t0",
            uncertainty_ppm=0,
            goal_context={"goal": "g"},
        )


def test_cause_requires_structured_content_provenance_and_effect_parent() -> None:
    with pytest.raises(ContractTypeError, match="content must not be empty"):
        CausePacket(
            cause_id="bad",
            tick=0,
            cause_kind=CauseKind.IDEA,
            content={},
            source="fixture",
            provenance=("fixture",),
            time_label="t0",
            uncertainty_ppm=0,
            goal_context={"goal": "g"},
        )
    with pytest.raises(ContractTypeError, match="parent_effect_id"):
        cause(kind=CauseKind.EFFECT)
    assert cause(kind=CauseKind.EFFECT, parent="published-0").parent_effect_id == "published-0"


def test_readiness_axes_are_independent_hard_gates() -> None:
    open_state = readiness()
    assert open_state.all_sufficient
    assert open_state.hard_open
    assert open_state.readiness_ppm == 700_000
    closed = readiness(wisdom_status=ReadinessStatus.UNKNOWN)
    assert not closed.all_sufficient
    assert not closed.hard_open
    assert closed.first_unmet is ReadinessAxisName.WISDOM
    assert closed.readiness_ppm == 0
    with pytest.raises(ContractTypeError, match="axis WISDOM"):
        ReadinessState(
            profile_id="prototype",
            desire=axis(ReadinessAxisName.DESIRE),
            wisdom=axis(ReadinessAxisName.DESIRE),
            power=axis(ReadinessAxisName.POWER),
        )


def test_bias_contains_exactly_six_typed_parts_and_binds_cjt() -> None:
    value = bias()
    wire = validate_contract(value)
    assert set(wire) == {
        "contract_type", "schema_version", "bias_id", "cjt_id", "version",
        "previous_digest", "stable", "memory", "rpm", "operating", "theta",
        "governance", "state_digest",
    }
    bad = deepcopy(wire)
    bad["surprise"] = True
    with pytest.raises(ContractSchemaError):
        validate_contract(bad)
    with pytest.raises(ContractTypeError, match="stable.cjt_id"):
        BiasState(
            bias_id=value.bias_id,
            cjt_id="other-cjt",
            version=value.version,
            previous_digest=value.previous_digest,
            stable=value.stable,
            memory=value.memory,
            rpm=value.rpm,
            operating=value.operating,
            theta=value.theta,
            governance=value.governance,
            state_digest=value.state_digest,
        )


@pytest.mark.parametrize(
    ("operation_id", "name", "status"),
    [
        ("^6", "decompose", OntologyStatus.CANONICAL_ADMITTED),
        ("^2", "experimental_attract", OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS),
        ("^3", "experimental_avert", OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS),
        ("^8", "experimental_trigger", OntologyStatus.EXPERIMENTAL_CONFLICTED_SEMANTICS),
    ],
)
def test_operation_identity_preserves_canonical_boundary(
    operation_id: str, name: str, status: OntologyStatus
) -> None:
    assert validate_contract(operation(operation_id, name, status))["ontology_status"] == status.value


def test_open_or_conflicted_operation_cannot_claim_canonical_status() -> None:
    with pytest.raises(ContractTypeError, match="must be named"):
        operation("^8", "experimental_trigger", OntologyStatus.CANONICAL_ADMITTED)
    forged = operation("^6", "decompose", OntologyStatus.CANONICAL_ADMITTED).to_dict()
    forged["operation_id"] = "^2"
    with pytest.raises(ContractSchemaError):
        validate_contract(forged)


def test_operation_contract_requires_a_positive_verifier_version() -> None:
    contract = operation()
    assert validate_contract(contract)["verifier_version"] == 1

    missing = contract.to_dict()
    missing.pop("verifier_version")
    with pytest.raises(ContractSchemaError):
        validate_contract(missing)

    values = contract.to_dict()
    values.pop("contract_type")
    values.pop("schema_version")
    values["verifier_version"] = 0
    with pytest.raises(ContractTypeError, match="verifier_version"):
        OperationContract(**values)


def test_candidate_and_publication_are_distinct_authority_states() -> None:
    with pytest.raises(ContractTypeError, match="never be authoritative"):
        replace(candidate(), authoritative=True)
    raw = candidate().to_dict()
    raw["authoritative"] = True
    with pytest.raises(ContractSchemaError):
        validate_contract(raw)


def test_verifier_cannot_self_verify_or_accept_unassessed_effect() -> None:
    values = verifier().to_dict()
    values.pop("contract_type")
    values.pop("schema_version")
    values["independent"] = False
    with pytest.raises(ContractTypeError, match="self-verify"):
        VerifierReceipt(**values)
    values["independent"] = True
    values["semantic_outcome"] = SemanticOutcome.UNASSESSED
    with pytest.raises(ContractTypeError, match="ACCEPT requires"):
        VerifierReceipt(**values)


def test_verifier_receipt_requires_a_configuration_digest() -> None:
    receipt = verifier()
    assert validate_contract(receipt)["verifier_digest"] == H2

    missing = receipt.to_dict()
    missing.pop("verifier_digest")
    with pytest.raises(ContractSchemaError):
        validate_contract(missing)

    values = receipt.to_dict()
    values.pop("contract_type")
    values.pop("schema_version")
    values["verifier_digest"] = "not-a-sha256"
    with pytest.raises(ContractTypeError, match="verifier_digest"):
        VerifierReceipt(**values)


def test_repair_is_next_tick_bounded_and_return_requires_effect() -> None:
    valid = next(item for item in all_valid_contracts() if isinstance(item, RepairFrame))
    data = valid.to_dict()
    data.pop("contract_type")
    data.pop("schema_version")
    data["eligible_tick"] = data["opened_tick"] + 2
    with pytest.raises(ContractTypeError, match="next tick"):
        RepairFrame(**data)
    data["eligible_tick"] = data["opened_tick"] + 1
    data["status"] = RepairStatus.RETURNED
    with pytest.raises(ContractTypeError, match="immutable OPEN"):
        RepairFrame(**data)

    outcome = next(
        item for item in all_valid_contracts() if isinstance(item, RepairOutcome)
    )
    outcome_data = outcome.to_dict()
    outcome_data.pop("contract_type")
    outcome_data.pop("schema_version")
    outcome_data["status"] = RepairStatus.OPEN
    with pytest.raises(ContractTypeError, match="RETURNED"):
        RepairOutcome(**outcome_data)


def test_intent_capabilities_and_mutable_paths_are_type_specific() -> None:
    valid = next(item for item in all_valid_contracts() if isinstance(item, StateUpdateIntent))
    data = valid.to_dict()
    data.pop("contract_type")
    data.pop("schema_version")
    data["authority_capability"] = AuthorityCapability.PROPOSE_MODEL_UPDATE.value
    with pytest.raises(ContractTypeError, match="PROPOSE_STATE_UPDATE"):
        StateUpdateIntent(**data)
    data["authority_capability"] = AuthorityCapability.PROPOSE_STATE_UPDATE.value
    data["target_path"] = "/governance/state_write_authorities"
    with pytest.raises(ContractTypeError, match="protected"):
        StateUpdateIntent(**data)


def test_gradient_update_requires_external_tensor_artifact() -> None:
    valid = next(item for item in all_valid_contracts() if isinstance(item, ModelUpdateIntent))
    data = valid.to_dict()
    data.pop("contract_type")
    data.pop("schema_version")
    data["candidate_artifact"] = artifact("candidate-model")
    data["gradient_artifact"] = None
    with pytest.raises(ContractTypeError, match="requires gradient_artifact"):
        ModelUpdateIntent(**data)


def test_effect_only_commit_is_valid_and_rejection_is_atomic() -> None:
    valid = next(item for item in all_valid_contracts() if isinstance(item, CommitReceipt))
    data = valid.to_dict()
    data.pop("contract_type")
    data.pop("schema_version")
    data["accepted_intent_ids"] = ()
    assert validate_contract(CommitReceipt(**data))["published_effect_ids"] == ["published-1"]

    data.update(
        disposition=CommitDisposition.REJECTED,
        authorized=False,
        post_state_digest=data["pre_state_digest"],
        post_model_digest=data["pre_model_digest"],
        accepted_intent_ids=(),
        published_effect_ids=(),
        opened_repair_ids=(),
        rejected_intent_ids=("bad-intent",),
        persisted_snapshot_id=None,
    )
    assert validate_contract(CommitReceipt(**data))["disposition"] == "REJECTED"
    data["post_state_digest"] = H4
    with pytest.raises(ContractTypeError, match="state unchanged"):
        CommitReceipt(**data)


def test_tick_trace_requires_exact_eleven_phase_order_and_no_extras() -> None:
    valid = next(item for item in all_valid_contracts() if isinstance(item, TickTrace))
    assert tuple(record.phase for record in valid.phases) == tuple(TickPhase)
    data = valid.to_dict()
    data.pop("contract_type")
    data.pop("schema_version")
    swapped = list(valid.phases)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    data["phases"] = tuple(swapped)
    with pytest.raises(ContractTypeError, match="mandatory 11-phase order"):
        TickTrace(**data)
    raw = valid.to_dict()
    raw["unexpected"] = "forbidden"
    with pytest.raises(ContractSchemaError):
        validate_contract(raw)


@pytest.mark.parametrize("phase", tuple(TickPhase))
def test_phase_schema_rejects_missing_and_extra_claims_for_every_phase(
    phase: TickPhase,
) -> None:
    valid = next(record for record in phases() if record.phase is phase).to_dict()

    missing = deepcopy(valid)
    field_name = next(iter(missing["inputs"]))
    del missing["inputs"][field_name]
    with pytest.raises(ContractSchemaError):
        validate_contract(missing)

    extra = deepcopy(valid)
    extra["inputs"]["false_claim"] = True
    with pytest.raises(ContractSchemaError):
        validate_contract(extra)


def test_network_tick_trace_requires_the_complete_extension() -> None:
    valid = next(item for item in all_valid_contracts() if isinstance(item, TickTrace))
    raw = valid.to_dict()
    raw["network_request_digest"] = H1
    with pytest.raises(ContractSchemaError):
        validate_contract(raw)


def test_canonical_digest_is_stable_and_declared_digest_is_recomputable() -> None:
    left = {"b": [2, 3], "a": {"x": 1}}
    right = {"a": {"x": 1}, "b": [2, 3]}
    assert canonical_json(left) == canonical_json(right)
    assert canonical_digest(left) == canonical_digest(right)
    envelope = {"payload": left, "digest": H0}
    envelope["digest"] = canonical_digest(envelope, omit_keys=("digest",))
    assert verify_declared_digest(envelope, "digest")
    envelope["payload"]["a"]["x"] = 2
    assert not verify_declared_digest(envelope, "digest")


def test_schema_rejects_missing_fields_wrong_versions_and_floats() -> None:
    wire = cause().to_dict()
    del wire["provenance"]
    with pytest.raises(ContractSchemaError):
        validate_contract(wire)
    wire = cause().to_dict()
    wire["schema_version"] = "cas.neural-cjt.cause/999"
    with pytest.raises(ContractSchemaError):
        validate_contract(wire)
    wire = cause().to_dict()
    wire["uncertainty_ppm"] = 0.5
    with pytest.raises(ContractTypeError, match="float"):
        validate_contract(wire)


def test_tensor_reference_accepts_raw_codec_but_rejects_empty_payload() -> None:
    assert artifact().encoding == "raw-contiguous-v1"
    with pytest.raises(ContractTypeError, match="byte_length"):
        TensorArtifactRef(
            artifact_id="empty",
            sha256=H0,
            dtype="float32",
            shape=(0,),
            encoding="raw-contiguous-v1",
            byte_length=0,
        )
