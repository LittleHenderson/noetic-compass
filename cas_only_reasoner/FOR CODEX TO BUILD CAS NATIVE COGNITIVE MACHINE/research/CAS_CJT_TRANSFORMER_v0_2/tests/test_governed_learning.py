from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch


CASFORMER_ROOT = Path(__file__).resolve().parents[2] / "CASFORMER_v0_1"
sys.path.insert(0, str(CASFORMER_ROOT))

from casformer import CASformerConfig

import cas_cjt
from cas_cjt.checkpoint import changed_parameter_names, encode_module_checkpoint
from cas_cjt.contracts import canonical_digest
from cas_cjt.learning import (
    GovernedLearner,
    LearningError,
    LearningPolicy,
    QualificationFailed,
    validate_qualification_receipt,
)
from cas_cjt.network import CJTNodeSpec
from cas_cjt.runtime import NeuralCJTRuntime
from cas_cjt.state import content_id


_QUALIFICATION_BODY_KEYS = (
    "policy_id",
    "independent",
    "candidate_model_digest",
    "disposition",
    "changed_parameter_names",
    "allowed_parameter_names",
    "gradient_norm_microunits",
    "max_gradient_norm_microunits",
    "baseline_metrics_microunits",
    "candidate_metrics_microunits",
    "target_improved",
    "retention_passed",
    "regression_passed",
    "qualified",
    "reason_codes",
)


def _config() -> CASformerConfig:
    return CASformerConfig(
        d_model=4,
        num_heads=2,
        num_relations=4,
        num_layers=1,
        dropout=0.0,
        attention_dropout=0.0,
        initial_cutoff=0.01,
        initial_saturation=100.0,
    )


def _prepared(tmp_path: Path):
    runtime = NeuralCJTRuntime.create(
        tmp_path / "learning.db",
        config=_config(),
        node_specs=tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C")),
        topology=(),
        seed=7,
        labels=("L0", "L1", "L2", "L3"),
    )
    cause, artifact = runtime.make_input_cause(
        torch.tensor([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]]),
        tick=1,
        content={"experience": "fixture"},
        goal_context={"goal": "learn"},
    )
    prepared = runtime._prepare_inference(
        cause=cause,
        cjt_id="A",
        expected_symbol="L1",
        opposite_symbol=None,
        settings=None,
        supplied_artifacts=(artifact,),
        resume_repair_id=None,
        write_memory=False,
    )
    return runtime, prepared


def _loss_and_score(names: tuple[str, ...], *, scale: float = 1.0):
    def loss(model: torch.nn.Module) -> torch.Tensor:
        parameters = dict(model.named_parameters())
        return scale * sum(((parameters[name] - 0.125) ** 2).mean() for name in names)

    def score(model: torch.nn.Module) -> dict[str, float]:
        return {
            "target_loss": float(loss(model).detach().item()),
            "retention_loss": 0.0,
        }

    return loss, score


def _qualification_wire(
    policy: LearningPolicy | None = None,
    *,
    regression_passed: bool = True,
) -> dict[str, object]:
    admitted = LearningPolicy() if policy is None else policy
    target_improved = True
    retention_passed = True
    qualified = target_improved and retention_passed and regression_passed
    body: dict[str, object] = {
        "policy_id": admitted.policy_id,
        "independent": True,
        "candidate_model_digest": "a" * 64,
        "disposition": "QUALIFIED" if qualified else "REFUSED",
        "changed_parameter_names": ["operation.weight"],
        "allowed_parameter_names": ["operation.weight"],
        "gradient_norm_microunits": 250_000,
        "max_gradient_norm_microunits": int(
            round(admitted.max_gradient_norm * 1_000_000)
        ),
        "baseline_metrics_microunits": {
            "retention_loss": 100_000,
            "target_loss": 2_000_000,
        },
        "candidate_metrics_microunits": {
            "retention_loss": 100_001,
            "target_loss": 1_000_000,
        },
        "target_improved": target_improved,
        "retention_passed": retention_passed,
        "regression_passed": regression_passed,
        "qualified": qualified,
        "reason_codes": [
            "TARGET_IMPROVED",
            "RETENTION_PASSED",
            "REGRESSION_PASSED" if regression_passed else "REGRESSION_FAILED",
        ],
    }
    receipt_id = content_id("qualification", body)
    wire = {
        "schema_version": "cas.neural-cjt.qualification-receipt/0.2",
        "qualification_receipt_id": receipt_id,
        **body,
        "receipt_digest": "0" * 64,
    }
    wire["receipt_digest"] = canonical_digest(
        wire,
        omit_keys=("receipt_digest",),
    )
    return wire


def _reseal_qualification(
    wire: dict[str, object],
    *,
    refresh_identity: bool = True,
) -> dict[str, object]:
    if refresh_identity:
        body = {name: wire[name] for name in _QUALIFICATION_BODY_KEYS}
        wire["qualification_receipt_id"] = content_id("qualification", body)
    wire["receipt_digest"] = canonical_digest(
        wire,
        omit_keys=("receipt_digest",),
    )
    return wire


def test_qualification_validator_accepts_exact_receipt_and_external_regression_result() -> None:
    policy = LearningPolicy()
    qualified = _qualification_wire(policy)
    assert validate_qualification_receipt(qualified, policy=policy) == qualified

    # The validator binds this supplied failure into a coherent refusal.  It
    # does not claim that it independently ran the external regression suite.
    refused = _qualification_wire(policy, regression_passed=False)
    assert validate_qualification_receipt(refused, policy=policy) == refused
    assert refused["qualified"] is False


def test_qualification_validator_is_a_public_package_export() -> None:
    assert cas_cjt.validate_qualification_receipt is validate_qualification_receipt


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("max_gradient_norm_microunits", 999_999, "admitted policy"),
        ("gradient_norm_microunits", True, "nonnegative integer"),
        ("gradient_norm_microunits", 1_000_001, "exceeds"),
        ("regression_passed", 1, "must be a boolean"),
        ("candidate_model_digest", "not-a-digest", "SHA-256"),
        ("policy_id", "attacker-policy/9.9", "does not match"),
    ),
)
def test_qualification_validator_rejects_resealed_type_policy_and_range_tampering(
    field: str,
    value: object,
    message: str,
) -> None:
    policy = LearningPolicy()
    wire = _qualification_wire(policy)
    wire[field] = value
    _reseal_qualification(wire)
    with pytest.raises(LearningError, match=message):
        validate_qualification_receipt(wire, policy=policy)


def test_qualification_validator_recomputes_target_and_retention_arithmetic() -> None:
    policy = LearningPolicy()
    forged_target = _qualification_wire(policy)
    forged_target["candidate_metrics_microunits"] = {
        "retention_loss": 100_001,
        "target_loss": 3_000_000,
    }
    _reseal_qualification(forged_target)
    with pytest.raises(LearningError, match="target_improved"):
        validate_qualification_receipt(forged_target, policy=policy)

    forged_retention = _qualification_wire(policy)
    forged_retention["candidate_metrics_microunits"] = {
        "retention_loss": 106_000,
        "target_loss": 1_000_000,
    }
    _reseal_qualification(forged_retention)
    with pytest.raises(LearningError, match="retention_passed"):
        validate_qualification_receipt(forged_retention, policy=policy)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("qualified", False, "decision conjunction"),
        ("disposition", "PASS", "disposition"),
        (
            "reason_codes",
            ["TARGET_NOT_IMPROVED", "RETENTION_PASSED", "REGRESSION_PASSED"],
            "reason_codes",
        ),
    ),
)
def test_qualification_validator_rejects_resealed_semantic_decision_tampering(
    field: str,
    value: object,
    message: str,
) -> None:
    policy = LearningPolicy()
    wire = _qualification_wire(policy)
    wire[field] = value
    _reseal_qualification(wire)
    with pytest.raises(LearningError, match=message):
        validate_qualification_receipt(wire, policy=policy)


def test_qualification_validator_rejects_digest_identity_and_exact_key_tampering() -> None:
    policy = LearningPolicy()
    bad_digest = _qualification_wire(policy)
    bad_digest["receipt_digest"] = "0" * 64
    with pytest.raises(LearningError, match="receipt_digest"):
        validate_qualification_receipt(bad_digest, policy=policy)

    stale_identity = _qualification_wire(policy)
    stale_identity["candidate_metrics_microunits"] = {
        "retention_loss": 100_001,
        "target_loss": 999_999,
    }
    _reseal_qualification(stale_identity, refresh_identity=False)
    with pytest.raises(LearningError, match="content-derived"):
        validate_qualification_receipt(stale_identity, policy=policy)

    extra_key = _qualification_wire(policy)
    extra_key["attacker_note"] = "resealed"
    _reseal_qualification(extra_key)
    with pytest.raises(LearningError, match="keys are not exact"):
        validate_qualification_receipt(extra_key, policy=policy)


def test_qualification_validator_requires_exact_metric_keys_even_when_resealed() -> None:
    policy = LearningPolicy()
    wire = _qualification_wire(policy)
    baseline = dict(wire["baseline_metrics_microunits"])
    candidate = dict(wire["candidate_metrics_microunits"])
    baseline["unbound_metric"] = 0
    candidate["unbound_metric"] = 0
    wire["baseline_metrics_microunits"] = baseline
    wire["candidate_metrics_microunits"] = candidate
    _reseal_qualification(wire)
    with pytest.raises(LearningError, match="exactly match"):
        validate_qualification_receipt(wire, policy=policy)


def test_staged_learning_clips_large_gradient_and_never_mutates_active_model(
    tmp_path: Path,
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    loss, score = _loss_and_score(allowed, scale=1_000_000.0)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload
    learner = GovernedLearner(
        LearningPolicy(max_gradient_norm=0.01, learning_rate=0.05)
    )
    proposal = learner.propose(
        active_model=runtime.network,
        bias=prepared.bias,
        operation_contract=prepared.contract,
        verifier_receipt=prepared.verifier_receipt,
        tick=1,
        loss_fn=loss,
        score_fn=score,
        allowed_parameter_names=allowed,
        parameter_group_ids=("cjt:A:operation:^6",),
        flow_ppm=1_000_000,
        regression_passed=True,
    )
    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert changed_parameter_names(runtime.network, proposal.staged_model) == (
        proposal.changed_parameter_names
    )
    assert set(proposal.changed_parameter_names) <= set(allowed)
    assert proposal.qualification.gradient_norm_microunits <= 10_000
    assert proposal.qualification.qualified
    runtime.close()


def test_default_contract_plasticity_roles_are_scoped_to_the_bias_cjt(
    tmp_path: Path,
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A", include_bias_head=True)
    loss, score = _loss_and_score(allowed)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload

    proposal = GovernedLearner().propose(
        active_model=runtime.network,
        bias=prepared.bias,
        operation_contract=prepared.contract,
        verifier_receipt=prepared.verifier_receipt,
        tick=1,
        loss_fn=loss,
        score_fn=score,
        allowed_parameter_names=allowed,
        flow_ppm=1_000_000,
        regression_passed=True,
    )

    assert proposal.intent.parameter_group_ids == (
        "cjt:A:operation:^6",
        "cjt:A:bias_update_head",
    )
    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert runtime.store.head.state_version == 0
    runtime.close()


@pytest.mark.parametrize(
    ("group_id", "message"),
    (
        ("cjt:A:operation:^2", "operation contract"),
        ("cjt:B:operation:^6", "scoped to the Bias CJT"),
    ),
)
def test_explicit_plasticity_groups_reject_foreign_roles_and_scopes(
    tmp_path: Path,
    group_id: str,
    message: str,
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    loss, score = _loss_and_score(allowed)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload

    with pytest.raises(LearningError, match=message):
        GovernedLearner().propose(
            active_model=runtime.network,
            bias=prepared.bias,
            operation_contract=prepared.contract,
            verifier_receipt=prepared.verifier_receipt,
            tick=1,
            loss_fn=loss,
            score_fn=score,
            allowed_parameter_names=allowed,
            parameter_group_ids=(group_id,),
            flow_ppm=1_000_000,
            regression_passed=True,
        )

    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert runtime.store.head.state_version == 0
    runtime.close()


def test_score_callbacks_cannot_mutate_active_or_staged_authority_models(
    tmp_path: Path,
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    base_loss, base_score = _loss_and_score(allowed)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload
    leaked: dict[str, torch.nn.Module] = {}
    scored_models: list[torch.nn.Module] = []

    def retaining_loss(model: torch.nn.Module) -> torch.Tensor:
        leaked["working"] = model
        return base_loss(model)

    def mutating_score(model: torch.nn.Module) -> dict[str, float]:
        metrics = base_score(model)
        scored_models.append(model)
        if len(scored_models) == 2:
            with torch.no_grad():
                dict(model.named_parameters())[allowed[0]].add_(1_000.0)
                dict(leaked["working"].named_parameters())[allowed[0]].add_(2_000.0)
                dict(runtime.network.named_parameters())[allowed[0]].add_(3_000.0)
        return metrics

    proposal = GovernedLearner().propose(
        active_model=runtime.network,
        bias=prepared.bias,
        operation_contract=prepared.contract,
        verifier_receipt=prepared.verifier_receipt,
        tick=1,
        loss_fn=retaining_loss,
        score_fn=mutating_score,
        allowed_parameter_names=allowed,
        parameter_group_ids=("cjt:A:operation:^6",),
        flow_ppm=1_000_000,
        regression_passed=True,
    )

    assert len(scored_models) == 2
    assert all(model is not runtime.network for model in scored_models)
    assert all(model is not proposal.staged_model for model in scored_models)
    assert proposal.checkpoint.artifact.payload == encode_module_checkpoint(
        proposal.staged_model
    ).artifact.payload
    active_parameters = dict(runtime.network.named_parameters())
    staged_parameters = dict(proposal.staged_model.named_parameters())
    delta = torch.cat(
        [
            (staged_parameters[name] - active_parameters[name]).detach().reshape(-1)
            for name in proposal.changed_parameter_names
        ]
    )
    assert float(torch.linalg.vector_norm(delta).item()) <= 0.051
    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert runtime.store.head.state_version == 0
    runtime.close()


@pytest.mark.parametrize("failure_point", ("baseline_score", "loss", "candidate_score"))
def test_throwing_callbacks_restore_active_state_in_finally(
    tmp_path: Path,
    failure_point: str,
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    base_loss, base_score = _loss_and_score(allowed)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload
    training_before = tuple(
        (name, module.training) for name, module in runtime.network.named_modules()
    )
    requires_grad_before = tuple(
        (name, parameter.requires_grad)
        for name, parameter in runtime.network.named_parameters()
    )
    gradients_before = tuple(
        (name, parameter.grad)
        for name, parameter in runtime.network.named_parameters()
    )

    def corrupt_active_and_throw() -> None:
        runtime.network.eval()
        parameter = dict(runtime.network.named_parameters())[allowed[0]]
        with torch.no_grad():
            parameter.add_(4_000.0)
        parameter.requires_grad_(False)
        parameter.grad = torch.ones_like(parameter)
        raise RuntimeError(f"{failure_point} exploded")

    score_calls = 0

    def score(model: torch.nn.Module) -> dict[str, float]:
        nonlocal score_calls
        score_calls += 1
        if failure_point == "baseline_score" or (
            failure_point == "candidate_score" and score_calls == 2
        ):
            corrupt_active_and_throw()
        return base_score(model)

    def loss(model: torch.nn.Module) -> torch.Tensor:
        if failure_point == "loss":
            corrupt_active_and_throw()
        return base_loss(model)

    with pytest.raises(RuntimeError, match=f"{failure_point} exploded"):
        GovernedLearner().propose(
            active_model=runtime.network,
            bias=prepared.bias,
            operation_contract=prepared.contract,
            verifier_receipt=prepared.verifier_receipt,
            tick=1,
            loss_fn=loss,
            score_fn=score,
            allowed_parameter_names=allowed,
            parameter_group_ids=("cjt:A:operation:^6",),
            flow_ppm=1_000_000,
            regression_passed=True,
        )

    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert tuple(
        (name, module.training) for name, module in runtime.network.named_modules()
    ) == training_before
    assert tuple(
        (name, parameter.requires_grad)
        for name, parameter in runtime.network.named_parameters()
    ) == requires_grad_before
    assert tuple(
        (name, parameter.grad)
        for name, parameter in runtime.network.named_parameters()
    ) == gradients_before
    assert runtime.store.head.state_version == 0
    runtime.close()


def test_regression_declaration_defaults_fail_closed(tmp_path: Path) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    loss, score = _loss_and_score(allowed)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload

    with pytest.raises(QualificationFailed, match="REGRESSION_FAILED"):
        GovernedLearner().propose(
            active_model=runtime.network,
            bias=prepared.bias,
            operation_contract=prepared.contract,
            verifier_receipt=prepared.verifier_receipt,
            tick=1,
            loss_fn=loss,
            score_fn=score,
            allowed_parameter_names=allowed,
            parameter_group_ids=("cjt:A:operation:^6",),
            flow_ppm=1_000_000,
        )

    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert runtime.store.head.state_version == 0
    runtime.close()


@pytest.mark.parametrize("failure", ("nan", "retention", "regression", "zero_flow"))
def test_invalid_learning_proposals_leave_active_bytes_unchanged(
    tmp_path: Path, failure: str
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    loss, score = _loss_and_score(allowed)
    active_before = encode_module_checkpoint(runtime.network).artifact.payload
    learner = GovernedLearner()

    if failure == "nan":
        def bad_loss(model: torch.nn.Module) -> torch.Tensor:
            parameter = dict(model.named_parameters())[allowed[0]]
            return parameter.mean() * torch.tensor(float("nan"))

        expected_error = LearningError
        kwargs = {"loss_fn": bad_loss, "score_fn": score, "flow_ppm": 1_000_000}
    elif failure == "retention":
        baseline_digest = encode_module_checkpoint(runtime.network).model_digest

        def bad_score(model: torch.nn.Module) -> dict[str, float]:
            target = float(loss(model).detach().item())
            is_baseline = encode_module_checkpoint(model).model_digest == baseline_digest
            return {"target_loss": target, "retention_loss": 0.0 if is_baseline else 1.0}

        expected_error = QualificationFailed
        kwargs = {"loss_fn": loss, "score_fn": bad_score, "flow_ppm": 1_000_000}
    elif failure == "regression":
        expected_error = QualificationFailed
        kwargs = {
            "loss_fn": loss,
            "score_fn": score,
            "flow_ppm": 1_000_000,
            "regression_passed": False,
        }
    else:
        expected_error = LearningError
        kwargs = {"loss_fn": loss, "score_fn": score, "flow_ppm": 0}

    with pytest.raises(expected_error):
        learner.propose(
            active_model=runtime.network,
            bias=prepared.bias,
            operation_contract=prepared.contract,
            verifier_receipt=prepared.verifier_receipt,
            tick=1,
            allowed_parameter_names=allowed,
            parameter_group_ids=("cjt:A:operation:^6",),
            **kwargs,
        )
    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    assert runtime.store.head.state_version == 0
    runtime.close()


def test_bias_governance_can_deny_learning_before_gradient_execution(
    tmp_path: Path,
) -> None:
    runtime, prepared = _prepared(tmp_path)
    allowed = runtime.network.parameter_names_for_node("A")
    loss, score = _loss_and_score(allowed)
    denied = replace(
        prepared.bias,
        governance=replace(prepared.bias.governance, learning_permissions=()),
        state_digest="0" * 64,
    )
    denied = replace(
        denied,
        state_digest=canonical_digest(denied.to_dict(), omit_keys=("state_digest",)),
    )
    denied_receipt = replace(
        prepared.verifier_receipt,
        bias_digest=denied.state_digest,
        receipt_digest="0" * 64,
    )
    denied_receipt = replace(
        denied_receipt,
        receipt_digest=canonical_digest(
            denied_receipt.to_dict(), omit_keys=("receipt_digest",)
        ),
    )
    active_before = encode_module_checkpoint(runtime.network).artifact.payload
    with pytest.raises(LearningError, match="denies learning"):
        GovernedLearner().propose(
            active_model=runtime.network,
            bias=denied,
            operation_contract=prepared.contract,
            verifier_receipt=denied_receipt,
            tick=1,
            loss_fn=loss,
            score_fn=score,
            allowed_parameter_names=allowed,
            parameter_group_ids=("cjt:A:operation:^6",),
            flow_ppm=1_000_000,
        )
    assert encode_module_checkpoint(runtime.network).artifact.payload == active_before
    runtime.close()
