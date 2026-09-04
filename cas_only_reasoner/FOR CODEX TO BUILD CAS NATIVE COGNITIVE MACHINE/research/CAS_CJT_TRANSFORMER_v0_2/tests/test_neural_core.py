from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch


# The v0.2 package deliberately reuses, rather than copies, the frozen v0.1
# engine.  Source-tree tests make that sibling package importable explicitly.
CASFORMER_ROOT = Path(__file__).resolve().parents[2] / "CASFORMER_v0_1"
sys.path.insert(0, str(CASFORMER_ROOT))

from casformer import CASControl, CASformerConfig, DifferentialConductanceLinear

from cas_cjt.contracts import (
    assert_no_json_floats,
    canonical_digest,
    verify_declared_digest,
)
from cas_cjt.neural import (
    ATTRACT,
    AVERT,
    DECOMPOSE,
    TRIGGER,
    NeuralCJT,
    NeuralCJTError,
    OperationRegistration,
    RegisteredOperationBank,
)
from cas_cjt.readiness import DWPProfile
from cas_cjt.routing import (
    CASOhmRouter,
    ComputePolicy,
    NativeComputeInputs,
    PostExecutionObservation,
    RouteInputs,
    RoutingError,
    compiled_attention_twin,
    global_memory_read_limit,
    realized_flow_tensors,
)
from cas_cjt.state import make_operation_contract
from cas_cjt.types import (
    BiasState,
    CandidateEffect,
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
    VerifierDisposition,
)
from cas_cjt.verifier import IndependentVerifier, SemanticEvidence


H0 = "0" * 64
H1 = "1" * 64
H2 = "2" * 64


def _config(**changes: object) -> CASformerConfig:
    values: dict[str, object] = {
        "d_model": 8,
        "num_heads": 2,
        "num_relations": 4,
        "num_layers": 1,
        "dropout": 0.0,
        "attention_dropout": 0.0,
        "initial_beta": 1.0,
        "beta_max": 4.0,
        "initial_cutoff": 0.01,
        "initial_saturation": 100.0,
    }
    values.update(changes)
    return CASformerConfig(**values)


def _axis(
    name: ReadinessAxisName,
    score: int,
    status: ReadinessStatus = ReadinessStatus.SUFFICIENT,
) -> ReadinessAxis:
    return ReadinessAxis(
        axis=name,
        status=status,
        score_ppm=score,
        threshold_ppm=500_000,
        reason_codes=(f"{name.value}_{status.value}",),
        evidence_refs=(f"evidence-{name.value.lower()}",),
        provenance=("test-dwp",),
    )


def _readiness(
    *, wisdom_status: ReadinessStatus = ReadinessStatus.SUFFICIENT
) -> ReadinessState:
    return ReadinessState(
        profile_id="PROTOTYPE_DWP_PRODUCT/0.1",
        desire=_axis(ReadinessAxisName.DESIRE, 800_000),
        wisdom=_axis(ReadinessAxisName.WISDOM, 900_000, wisdom_status),
        power=_axis(ReadinessAxisName.POWER, 700_000),
    )


def _route_inputs(
    *,
    drive: torch.Tensor | None = None,
    scores: torch.Tensor | None = None,
    permission: torch.Tensor | None = None,
    native_drive: torch.Tensor | None = None,
    native_resistance: torch.Tensor | None = None,
    route_ids: tuple[str, ...] = ("route-a", "route-b", "route-c"),
    desire: float = 0.5,
    wisdom: float = 0.8,
    power: float = 0.75,
    region: torch.Tensor | None = None,
) -> RouteInputs:
    shape = (1, 1, 1, 3)
    dtype = torch.float64
    if drive is None:
        drive = torch.tensor([1.0, 2.0, 4.0], dtype=dtype).reshape(shape)
    if scores is None:
        scores = torch.tensor([0.0, 1.0, -1.0], dtype=dtype).reshape(shape)
    if permission is None:
        permission = torch.ones(shape, dtype=torch.bool)
    if native_drive is None:
        native_drive = torch.ones(shape, dtype=torch.int64)
    if native_resistance is None:
        native_resistance = torch.ones(shape, dtype=torch.int64)
    if region is None:
        region = torch.tensor([1.0, 0.5, 0.25], dtype=dtype).reshape(shape)
    quarter = torch.full(shape, 0.25, dtype=dtype)
    return RouteInputs(
        semantic_scores=scores,
        drive=drive,
        resistance_capability=quarter.clone(),
        resistance_context=quarter.clone(),
        resistance_resource=quarter.clone(),
        resistance_memory=quarter.clone(),
        prior_region_multiplier=region,
        topology_mask=torch.ones(shape, dtype=torch.bool),
        permission_mask=permission,
        quarantine_mask=torch.zeros(shape, dtype=torch.bool),
        budget_mask=torch.ones(shape, dtype=torch.bool),
        readiness=DWPProfile.uniform(
            drive,
            desire=desire,
            wisdom=wisdom,
            power=power,
        ),
        native_compute=NativeComputeInputs(
            drive_units=native_drive,
            resistance_units=native_resistance,
            canonical_route_ids=route_ids,
        ),
    )


def _artifact(identifier: str) -> TensorArtifactRef:
    return TensorArtifactRef(
        artifact_id=identifier,
        sha256=H1,
        dtype="float32",
        shape=(1, 8),
        encoding="raw-contiguous-v1",
        byte_length=32,
    )


def _cause() -> CausePacket:
    return CausePacket(
        cause_id="cause-1",
        tick=1,
        cause_kind=CauseKind.PROPOSITION,
        content={"whole": "w"},
        source="test",
        provenance=("test-cause",),
        time_label="tick-1",
        uncertainty_ppm=0,
        goal_context={"goal_id": "g"},
        candidate_operation_ids=(DECOMPOSE,),
    )


def _bias() -> BiasState:
    tensor = _artifact("theta-1")
    draft = BiasState(
        bias_id="bias-1",
        cjt_id="cjt-1",
        version=0,
        previous_digest=None,
        stable=StableSubstrate(
            cjt_id="cjt-1",
            formation_version=1,
            registered_operation_id=DECOMPOSE,
            specialization_tags=("decompose",),
            lineage_refs=("genesis",),
            configuration_digest=H1,
        ),
        memory=LocalMemory(
            recurrent_state_ref=None,
            recent_cause_ids=(),
            recent_candidate_effect_ids=(),
            verifier_receipt_ids=(),
            repair_frame_ids=(),
            retrieved_memory_refs=(),
            provenance_refs=("genesis",),
        ),
        rpm=RPMState(
            readiness=_readiness(),
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
            topology_permissions=("cjt-1",),
            learning_permissions=("operator.^6",),
            compute_ceiling_units=8,
            quarantined=False,
            state_write_authorities=("coordinator",),
            memory_write_authorities=("coordinator",),
            effect_publication_authorities=("coordinator",),
            owner_restrictions=("NO_EXTERNAL_ACTION",),
        ),
        state_digest=H0,
    )
    return replace(
        draft,
        state_digest=canonical_digest(draft, omit_keys=("state_digest",)),
    )


def _contract(verifier: IndependentVerifier) -> OperationContract:
    draft = OperationContract(
        contract_id="cas.cjt.operation.^6.decompose/0.2",
        contract_version=1,
        operation_id=DECOMPOSE,
        operation_name="decompose",
        ontology_status=OntologyStatus.CANONICAL_ADMITTED,
        accepted_cause_kinds=(CauseKind.PROPOSITION,),
        accepted_schema_versions=(CausePacket.SCHEMA_VERSION,),
        permitted_evidence_ports=("typed-content",),
        neural_transform_id="registered-operation-bank/0.2",
        effect_schema_id=CandidateEffect.SCHEMA_VERSION,
        memory_interface=("READ_LOCAL", "PROPOSE_WRITE"),
        readiness_profile_id="PROTOTYPE_DWP_PRODUCT/0.1",
        legal_actions=("PROPOSE_EFFECT",),
        legal_bias_paths=("/memory/recent_candidate_effect_ids", "/operating"),
        temporal_transition_law="NEXT_TICK_ONLY",
        verifier_id=verifier.verifier_id,
        verifier_version=verifier.verifier_version,
        verifier_digest=verifier.configuration_digest,
        plasticity_groups=("operator.^6",),
        governance_requirements=("EXECUTE",),
        contract_digest=H0,
    )
    return replace(
        draft,
        contract_digest=canonical_digest(draft, omit_keys=("contract_digest",)),
    )


def _candidate(
    bias: BiasState,
    contract: OperationContract,
    content: dict[str, object],
    *,
    identifier: str = "candidate-1",
) -> CandidateEffect:
    draft = CandidateEffect(
        candidate_effect_id=identifier,
        tick=1,
        parent_cause_id="cause-1",
        producer_cjt_id="cjt-1",
        operation_id=DECOMPOSE,
        operation_contract_id=contract.contract_id,
        operation_contract_digest=contract.contract_digest,
        bias_id=bias.bias_id,
        bias_version=bias.version,
        bias_digest=bias.state_digest,
        model_digest=bias.theta.model_digest,
        content=content,
        content_ref=None,
        uncertainty_ppm=0,
        provenance=("neural-cjt",),
        candidate_digest=H0,
    )
    return replace(
        draft,
        candidate_digest=canonical_digest(draft, omit_keys=("candidate_digest",)),
    )


def test_dwp_preserves_three_hard_axes_and_wire_reasons() -> None:
    state = _readiness(wisdom_status=ReadinessStatus.UNKNOWN)
    reference = torch.ones(2, 3, dtype=torch.float64)
    profile = DWPProfile.from_state(state, reference)

    assert torch.equal(profile.desire_gate, torch.ones_like(profile.desire_gate))
    assert torch.equal(profile.wisdom_gate, torch.zeros_like(profile.wisdom_gate))
    assert torch.equal(profile.power_gate, torch.ones_like(profile.power_gate))
    assert torch.equal(profile.effective_readiness, torch.zeros_like(reference))
    assert profile.wisdom_reason == "WISDOM_UNKNOWN"
    assert profile.profile_id == state.profile_id
    assert torch.allclose(profile.soft_strength, torch.full_like(reference, 0.504))


def test_router_preserves_current_flow_and_semantic_twin() -> None:
    result = CASOhmRouter().route(_route_inputs())
    expected = torch.full_like(result.current, 0.3)

    assert torch.allclose(result.current, expected)
    assert torch.allclose(result.total_current, torch.tensor([[[0.9]]], dtype=torch.float64))
    assert torch.allclose(
        result.flow_allocation.sum(dim=-1),
        torch.ones(1, 1, 1, dtype=torch.float64),
    )
    assert torch.allclose(
        result.attention_allocation,
        compiled_attention_twin(
            _route_inputs().semantic_scores, result.current, result.effective_mask
        ),
    )
    assert not torch.allclose(result.flow_allocation, result.attention_allocation)


def test_all_closed_routes_have_exact_zero_and_no_uniform_fallback() -> None:
    shape = (1, 1, 1, 3)
    zero_drive = torch.zeros(shape, dtype=torch.float64)
    inputs = _route_inputs(
        drive=zero_drive,
        native_drive=torch.zeros(shape, dtype=torch.int64),
    )
    result = CASOhmRouter().route(inputs)

    for value in (
        result.current,
        result.flow_allocation,
        result.attention_allocation,
        result.total_current,
    ):
        assert torch.equal(value, torch.zeros_like(value))
    assert not result.effective_mask.any()
    assert result.compute_plan.to_authoritative_dict()["reasoning_step_quanta"] == [[[0]]]


def test_native_plan_is_exact_deterministic_and_not_changed_by_neural_current() -> None:
    shape = (1, 1, 1, 3)
    policy = ComputePolicy(flow_units_per_quantum=2_000_000)
    router = CASOhmRouter(policy)
    route_ids = ("route-b", "route-a", "route-c")
    first = router.route(_route_inputs(route_ids=route_ids, desire=0.2))
    second = router.route(_route_inputs(route_ids=route_ids, desire=1.0))

    assert not torch.equal(first.total_current, second.total_current)
    assert first.compute_plan.to_authoritative_dict() == second.compute_plan.to_authoritative_dict()
    assert first.compute_plan.route_quanta.item() == 2
    assert first.compute_plan.scheduled_route_mask.flatten().tolist() == [True, True, False]
    assert_no_json_floats(first.compute_plan.to_authoritative_dict())

    larger_native = torch.full(shape, 4, dtype=torch.int64)
    larger = router.route(
        _route_inputs(
            route_ids=route_ids,
            native_drive=larger_native,
            desire=0.2,
        )
    )
    assert larger.compute_plan.reasoning_step_quanta.item() > first.compute_plan.reasoning_step_quanta.item()


def test_post_execution_observation_cannot_enlarge_predeclared_plan() -> None:
    plan = CASOhmRouter().route(_route_inputs()).compute_plan
    valid = PostExecutionObservation(
        routes_executed=plan.route_quanta.clone(),
        reasoning_steps_used=plan.reasoning_step_quanta.clone(),
        branches_opened=plan.branch_quanta.clone(),
        memory_reads_used=plan.memory_read_quanta.clone(),
        diagnostic_probes_used=plan.diagnostic_probe_quanta.clone(),
    )
    valid.validate_against(plan)
    poisoned = replace(
        valid, reasoning_steps_used=plan.reasoning_step_quanta + 1
    )
    with pytest.raises(RoutingError, match="exceeds"):
        poisoned.validate_against(plan)


def test_global_memory_read_limit_matches_runtime_and_replay_cap() -> None:
    assert global_memory_read_limit(
        (4, 4, 4), (True, False, True), global_ceiling=5
    ) == 5
    assert global_memory_read_limit(
        (4, 4), (False, False), global_ceiling=99
    ) == 0


def test_realized_flow_rejects_row_total_before_int64_overflow() -> None:
    current = torch.full((1, 1, 1, 2), 5_000_000_000_000.0, dtype=torch.float64)
    with pytest.raises(RoutingError, match="total current exceeds int64"):
        realized_flow_tensors(
            current,
            torch.ones_like(current, dtype=torch.bool),
            ("route-a", "route-b"),
        )


def test_closed_route_has_zero_control_and_score_gradients() -> None:
    drive = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float64).reshape(
        1, 1, 1, 3
    ).requires_grad_()
    scores = torch.tensor([0.2, 0.4, 0.6], dtype=torch.float64).reshape(
        1, 1, 1, 3
    ).requires_grad_()
    permission = torch.tensor([True, False, True]).reshape(1, 1, 1, 3)
    result = CASOhmRouter().route(
        _route_inputs(drive=drive, scores=scores, permission=permission)
    )
    (result.current.sum() + result.attention_allocation.square().sum()).backward()

    assert drive.grad is not None
    assert scores.grad is not None
    drive_grad = drive.grad.reshape(-1)
    score_grad = scores.grad.reshape(-1)
    assert drive_grad[1].item() == 0.0
    assert score_grad[1].item() == 0.0
    assert drive_grad[[0, 2]].abs().sum().item() > 0


def test_compiled_attention_twin_matches_eager_including_closed_row() -> None:
    scores = torch.tensor(
        [[[[-1.0, 0.5, 1.0], [0.0, 0.0, 0.0]]]], dtype=torch.float64
    )
    current = torch.tensor(
        [[[[0.2, 0.0, 0.8], [0.0, 0.0, 0.0]]]], dtype=torch.float64
    )
    mask = current > 0
    eager = compiled_attention_twin(scores, current, mask)
    compiled = torch.compile(
        compiled_attention_twin, backend="eager", fullgraph=True
    )(scores, current, mask)
    assert torch.equal(eager, compiled)
    assert torch.equal(compiled[..., 1, :], torch.zeros_like(compiled[..., 1, :]))


def test_operation_registry_marks_only_decompose_canonical_and_binds_contract() -> None:
    bank = RegisteredOperationBank(_config())
    statuses = {
        operation_id: bank.registration(operation_id).admission
        for operation_id in (DECOMPOSE, ATTRACT, AVERT, TRIGGER)
    }
    assert statuses[DECOMPOSE] is OntologyStatus.CANONICAL_ADMITTED
    assert statuses[ATTRACT] is OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS
    assert statuses[AVERT] is OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS
    assert statuses[TRIGGER] is OntologyStatus.EXPERIMENTAL_CONFLICTED_SEMANTICS
    assert len({id(module) for module in bank.modules_by_operation.values()}) == 4

    verifier = IndependentVerifier("semantic-verifier")
    contract = _contract(verifier)
    assert bank.bind_contract(contract).operation_id == DECOMPOSE
    with pytest.raises(NeuralCJTError, match="does not match"):
        bank.bind_contract(replace(contract, contract_id="wrong-contract"))


def _extension_contract() -> OperationContract:
    verifier = IndependentVerifier("extension-verifier")
    base = _contract(verifier)
    draft = replace(
        base,
        contract_id="cas.cjt.operation.^9.dummy.experimental/0.2",
        operation_id="^9",
        operation_name="experimental_dummy",
        ontology_status=OntologyStatus.EXPERIMENTAL_LOCAL,
        neural_transform_id="fixture.experimental-dummy/0.1",
        plasticity_groups=("operator.^9",),
        contract_digest=H0,
    )
    return replace(
        draft,
        contract_digest=canonical_digest(draft, omit_keys=("contract_digest",)),
    )


def test_fifth_operation_requires_registration_and_exact_contract_binding() -> None:
    class DummyFifthOperator(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.scale = torch.nn.Parameter(torch.tensor(2.0))
            self.calls = 0

        def forward(self, value: torch.Tensor) -> torch.Tensor:
            self.calls += 1
            return value * self.scale

    model = NeuralCJT(_config(num_relations=5))
    x = torch.randn(1, 3, 8)
    control = CASControl.uniform(x, num_heads=2, relation_id=4)

    with pytest.raises(NeuralCJTError, match="unregistered"):
        model(x, control, operation_id="^9")

    module = DummyFifthOperator()
    registration = OperationRegistration(
        operation_id="^9",
        name="experimental_dummy",
        relation_index=4,
        admission=OntologyStatus.EXPERIMENTAL_LOCAL,
        contract_id="cas.cjt.operation.^9.dummy.experimental/0.2",
    )
    model.operations.register_operation(registration, module)
    with pytest.raises(NeuralCJTError, match="not contract-bound"):
        model(x, control, operation_id="^9")
    assert module.calls == 0

    contract = _extension_contract()
    wrong = replace(
        contract,
        contract_id="wrong-extension-contract",
        contract_digest=H0,
    )
    wrong = replace(
        wrong,
        contract_digest=canonical_digest(wrong, omit_keys=("contract_digest",)),
    )
    with pytest.raises(NeuralCJTError, match="does not match"):
        model.operations.bind_contract(wrong)
    assert model.operations.bound_contract_digest("^9") is None
    assert module.calls == 0

    assert model.operations.bind_contract(contract) == registration
    assert (
        model.operations.bound_contract_digest("^9")
        == contract.contract_digest
    )
    proposal = model(x, control, operation_id="^9")
    assert proposal.operation == registration
    assert module.calls == 1
    assert proposal.candidate_effect.shape == x.shape
    assert torch.isfinite(proposal.candidate_effect).all()


def test_extension_registration_cannot_override_builtins_or_relation_channels() -> None:
    bank = RegisteredOperationBank(_config(num_relations=5))
    dummy = torch.nn.Identity()
    with pytest.raises(NeuralCJTError, match="already registered"):
        bank.register_extension(
            OperationRegistration(
                operation_id=DECOMPOSE,
                name="decompose",
                relation_index=0,
                admission=OntologyStatus.CANONICAL_ADMITTED,
                contract_id="cas.cjt.operation.^6.decompose/0.2",
            ),
            dummy,
        )
    with pytest.raises(NeuralCJTError, match="canonical"):
        bank.register_operation(
            OperationRegistration(
                operation_id="^9",
                name="experimental_false_canonical",
                relation_index=4,
                admission=OntologyStatus.CANONICAL_ADMITTED,
                contract_id="experimental.false-canonical/0.1",
            ),
            dummy,
        )
    with pytest.raises(NeuralCJTError, match="relation_index is already assigned"):
        bank.register_operation(
            OperationRegistration(
                operation_id="^9",
                name="experimental_collision",
                relation_index=3,
                admission=OntologyStatus.EXPERIMENTAL_LOCAL,
                contract_id="experimental.collision/0.1",
            ),
            dummy,
        )
    with pytest.raises(NeuralCJTError, match="unregistered"):
        bank("^10", torch.ones(1, 1, 8))


def test_neural_candidate_comes_only_from_gated_cjt_effect() -> None:
    torch.manual_seed(7)
    model = NeuralCJT(_config()).to(dtype=torch.float64)
    x = torch.randn(1, 3, 8, dtype=torch.float64, requires_grad=True)
    control = CASControl.uniform(x.detach(), num_heads=2, relation_id=0)
    proposal = model(x, control, operation_id=DECOMPOSE)
    merged = model.engine.attention.merge_heads(proposal.telemetry.cjt_effect)
    expected = model.operations(
        DECOMPOSE, model.engine.attention.out_proj(merged)
    )
    expected = torch.where(
        proposal.execution_mask.unsqueeze(-1), expected, torch.zeros_like(expected)
    )

    assert torch.allclose(proposal.candidate_effect, expected)
    assert proposal.candidate_effect.abs().sum().item() > 0
    proposal.candidate_effect.square().mean().backward()
    assert x.grad is not None and torch.isfinite(x.grad).all()


@pytest.mark.parametrize("failure", ("zero_flow", "breakdown"))
def test_neural_zero_flow_and_breakdown_fail_closed_with_zero_gradient(failure: str) -> None:
    torch.manual_seed(11)
    model = NeuralCJT(_config()).to(dtype=torch.float64)
    x = torch.randn(1, 3, 8, dtype=torch.float64, requires_grad=True)
    drive = 0.0 if failure == "zero_flow" else 1.0
    control = CASControl.uniform(x.detach(), num_heads=2, drive=drive, relation_id=0)
    if failure == "breakdown":
        control = replace(
            control,
            breakdown_mask=torch.ones(1, 2, 3, dtype=torch.bool),
        )
    residual, telemetry = model.engine(x, control)
    proposal = model(x, control, operation_id=DECOMPOSE)

    assert residual.abs().sum().item() > 0
    assert torch.equal(telemetry.cjt_effect, torch.zeros_like(telemetry.cjt_effect))
    assert torch.equal(
        proposal.candidate_effect, torch.zeros_like(proposal.candidate_effect)
    )
    assert torch.equal(
        proposal.proposed_bias_delta, torch.zeros_like(proposal.proposed_bias_delta)
    )
    proposal.candidate_effect.sum().backward()
    assert x.grad is not None
    assert torch.equal(x.grad, torch.zeros_like(x.grad))


def test_relation_contract_mismatch_fails_before_neural_execution() -> None:
    model = NeuralCJT(_config()).to(dtype=torch.float64)
    x = torch.randn(1, 2, 8, dtype=torch.float64)
    wrong = CASControl.uniform(x, num_heads=2, relation_id=1)
    with pytest.raises(NeuralCJTError, match="relation_ids"):
        model(x, wrong, operation_id=DECOMPOSE)


def test_positive_rail_mode_covers_engine_operations_and_bias_proposal() -> None:
    torch.manual_seed(13)
    cfg = _config(
        linear_weight_mode="differential_conductance",
        minimum_weight_resistance=0.2,
    )
    model = NeuralCJT(cfg).to(dtype=torch.float64)
    rails = [
        module
        for module in model.modules()
        if isinstance(module, DifferentialConductanceLinear)
    ]
    assert rails
    assert all(
        isinstance(module, DifferentialConductanceLinear)
        for module in model.operations.linear_modules()
    )
    assert isinstance(model.bias_update_head, DifferentialConductanceLinear)

    x = torch.randn(1, 3, 8, dtype=torch.float64, requires_grad=True)
    control = CASControl.uniform(x.detach(), num_heads=2, relation_id=0)
    proposal = model(x, control, operation_id=DECOMPOSE)
    rail_penalty = sum(module.common_mode_penalty() for module in rails)
    (
        proposal.candidate_effect.square().mean()
        + proposal.proposed_bias_delta.square().mean()
        + 1e-8 * rail_penalty
    ).backward()
    assert torch.isfinite(proposal.candidate_effect).all()
    for module in rails:
        assert torch.all(module.positive_resistance > cfg.minimum_weight_resistance)
        assert torch.all(module.negative_resistance > cfg.minimum_weight_resistance)
        assert module.raw_positive_resistance.grad is not None
        assert module.raw_negative_resistance.grad is not None
        assert torch.isfinite(module.raw_positive_resistance.grad).all()
        assert torch.isfinite(module.raw_negative_resistance.grad).all()


def test_verifier_keeps_operating_and_semantic_axes_independent() -> None:
    verifier = IndependentVerifier("semantic-verifier")
    bias = _bias()
    contract = _contract(verifier)
    cause = _cause()
    expected = {"parts": ["a", "b"]}
    opposite = {"parts": ["not-a", "not-b"]}
    evidence = SemanticEvidence(
        evidence_id="oracle-1",
        source_id="oracle",
        port_id="typed-content",
        expected_content=expected,
        opposite_content=opposite,
    )

    intended = verifier.evaluate(
        cause,
        _candidate(bias, contract, expected),
        contract,
        evidence,
        bias=bias,
        operating_region=OperatingRegion.SATURATION,
    )
    wrong = verifier.evaluate(
        cause,
        _candidate(bias, contract, opposite, identifier="candidate-opposite"),
        contract,
        evidence,
        bias=bias,
        operating_region=OperatingRegion.ACTIVE,
    )
    off_axis = verifier.evaluate(
        cause,
        _candidate(
            bias,
            contract,
            {"parts": ["unrelated"]},
            identifier="candidate-off-axis",
        ),
        contract,
        evidence,
        bias=bias,
        operating_region=OperatingRegion.ACTIVE,
    )

    assert intended.operating_region is OperatingRegion.SATURATION
    assert intended.semantic_outcome is SemanticOutcome.INTENDED
    assert intended.receipt.disposition is VerifierDisposition.ACCEPT
    assert intended.receipt.verifier_digest == verifier.configuration_digest
    assert wrong.operating_region is OperatingRegion.ACTIVE
    assert wrong.semantic_outcome is SemanticOutcome.OPPOSITE
    assert wrong.receipt.disposition is VerifierDisposition.REPAIR
    assert wrong.receipt.repair_required
    assert off_axis.semantic_outcome is SemanticOutcome.OFF_AXIS
    assert off_axis.receipt.disposition is VerifierDisposition.REPAIR
    assert off_axis.receipt.repair_required
    assert verify_declared_digest(intended.receipt, "receipt_digest")


def test_generated_operation_contract_binds_exact_verifier_configuration() -> None:
    verifier = IndependentVerifier("independent-effect-verifier")
    contract = make_operation_contract("^6")

    assert contract.verifier_id == verifier.verifier_id
    assert contract.verifier_version == verifier.verifier_version
    assert contract.verifier_digest == verifier.configuration_digest


def test_verifier_quarantines_a_contract_with_the_wrong_verifier_version() -> None:
    verifier = IndependentVerifier("semantic-verifier")
    bias = _bias()
    contract_draft = replace(_contract(verifier), verifier_version=2, contract_digest=H0)
    contract = replace(
        contract_draft,
        contract_digest=canonical_digest(
            contract_draft, omit_keys=("contract_digest",)
        ),
    )
    content = {"parts": ["a", "b"]}
    result = verifier.evaluate(
        _cause(),
        _candidate(bias, contract, content),
        contract,
        SemanticEvidence(
            evidence_id="oracle-version-mismatch",
            source_id="oracle",
            port_id="typed-content",
            expected_content=content,
        ),
        bias=bias,
    )

    assert result.receipt.disposition is VerifierDisposition.QUARANTINE
    assert "VERIFIER_VERSION_MISMATCH" in result.receipt.reason_codes


def test_verifier_abstains_without_evidence_and_quarantines_stale_binding() -> None:
    verifier = IndependentVerifier("semantic-verifier")
    bias = _bias()
    contract = _contract(verifier)
    candidate = _candidate(bias, contract, {"parts": ["a"]})
    unassessed = verifier.evaluate(
        _cause(), candidate, contract, None, bias=bias
    )
    assert unassessed.semantic_outcome is SemanticOutcome.UNASSESSED
    assert unassessed.receipt.disposition is VerifierDisposition.ABSTAIN

    stale_draft = replace(candidate, bias_version=1, candidate_digest=H0)
    stale = replace(
        stale_draft,
        candidate_digest=canonical_digest(
            stale_draft, omit_keys=("candidate_digest",)
        ),
    )
    rejected = verifier.evaluate(
        _cause(),
        stale,
        contract,
        SemanticEvidence(
            evidence_id="oracle-2",
            source_id="oracle",
            port_id="typed-content",
            expected_content={"parts": ["a"]},
        ),
        bias=bias,
    )
    assert rejected.receipt.disposition is VerifierDisposition.QUARANTINE
    assert "BIAS_VERSION_MISMATCH" in rejected.receipt.reason_codes
    assert rejected.receipt.semantic_outcome is SemanticOutcome.UNASSESSED


def test_candidate_producer_cannot_be_its_own_verifier() -> None:
    verifier = IndependentVerifier("cjt-1")
    bias = _bias()
    contract = _contract(verifier)
    candidate = _candidate(bias, contract, {"parts": ["a"]})
    result = verifier.evaluate(
        _cause(),
        candidate,
        contract,
        SemanticEvidence(
            evidence_id="oracle-3",
            source_id="oracle",
            port_id="typed-content",
            expected_content={"parts": ["a"]},
        ),
        bias=bias,
    )
    assert result.receipt.disposition is VerifierDisposition.QUARANTINE
    assert "SELF_VERIFICATION_PROHIBITED" in result.receipt.reason_codes
