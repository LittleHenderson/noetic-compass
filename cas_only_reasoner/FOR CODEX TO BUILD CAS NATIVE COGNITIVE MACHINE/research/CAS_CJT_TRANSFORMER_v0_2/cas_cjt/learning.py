"""Governed staging-only gradient proposals for Neural CJTs.

An active model is never passed to ``optimizer.step``.  The learner clones it,
freezes out-of-scope parameters, computes a bounded candidate update, runs a
caller-supplied score callback, and returns an immutable proposal.  The caller
must still ask the sole-writer coordinator to publish the candidate checkpoint.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import math
from typing import Callable, Mapping, Sequence

import torch
from torch import Tensor, nn

from .artifacts import StoredArtifact, encode_tensor
from .checkpoint import (
    CheckpointBundle,
    changed_parameter_names,
    encode_module_checkpoint,
    load_module_checkpoint,
)
from .contracts import canonical_digest
from .state import ZERO_DIGEST, content_id, tensor_ref_from_mapping
from .types import (
    AuthorityCapability,
    BiasState,
    ModelUpdateIntent,
    ModelUpdateKind,
    OperationContract,
    VerifierDisposition,
    VerifierReceipt,
)


ScoreFunction = Callable[[nn.Module], Mapping[str, float]]
LossFunction = Callable[[nn.Module], Tensor]


class LearningError(ValueError):
    """A learning proposal failed a finite, scope, or governance check."""


class QualificationFailed(LearningError):
    """A candidate failed its target or retention check."""


QUALIFICATION_RECEIPT_SCHEMA_VERSION = "cas.neural-cjt.qualification-receipt/0.2"
_QUALIFICATION_RECEIPT_BODY_KEYS = (
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
_QUALIFICATION_RECEIPT_WIRE_KEYS = frozenset(
    (
        "schema_version",
        "qualification_receipt_id",
        *_QUALIFICATION_RECEIPT_BODY_KEYS,
        "receipt_digest",
    )
)


@dataclass(frozen=True, slots=True)
class LearningPolicy:
    learning_rate: float = 0.05
    max_gradient_norm: float = 1.0
    target_metric: str = "target_loss"
    minimum_improvement_ppm: int = 1
    retention_metric_names: tuple[str, ...] = ("retention_loss",)
    retention_tolerance_ppm: int = 5_000
    policy_id: str = "cas.neural-cjt.learning-policy/0.2"

    def validate(self) -> None:
        if (
            not isinstance(self.learning_rate, (int, float))
            or isinstance(self.learning_rate, bool)
            or not isinstance(self.max_gradient_norm, (int, float))
            or isinstance(self.max_gradient_norm, bool)
            or not math.isfinite(self.learning_rate)
            or not math.isfinite(self.max_gradient_norm)
            or self.learning_rate <= 0
            or self.max_gradient_norm <= 0
        ):
            raise LearningError("learning rate and gradient bound must be finite and positive")
        if (
            not isinstance(self.target_metric, str)
            or not self.target_metric
            or not isinstance(self.policy_id, str)
            or not self.policy_id
        ):
            raise LearningError("learning policy identifiers must be nonempty")
        if (
            not isinstance(self.minimum_improvement_ppm, int)
            or isinstance(self.minimum_improvement_ppm, bool)
            or not isinstance(self.retention_tolerance_ppm, int)
            or isinstance(self.retention_tolerance_ppm, bool)
            or self.minimum_improvement_ppm < 0
            or self.retention_tolerance_ppm < 0
        ):
            raise LearningError("qualification tolerances must be nonnegative")
        if not isinstance(self.retention_metric_names, tuple) or any(
            not isinstance(name, str) or not name
            for name in self.retention_metric_names
        ):
            raise LearningError("retention metric names must be nonempty strings")
        if len(set(self.retention_metric_names)) != len(self.retention_metric_names):
            raise LearningError("retention metric names must be unique")


@dataclass(frozen=True, slots=True)
class QualificationReceipt:
    qualification_receipt_id: str
    policy_id: str
    independent: bool
    candidate_model_digest: str
    disposition: str
    changed_parameter_names: tuple[str, ...]
    allowed_parameter_names: tuple[str, ...]
    gradient_norm_microunits: int
    max_gradient_norm_microunits: int
    baseline_metrics_microunits: Mapping[str, int]
    candidate_metrics_microunits: Mapping[str, int]
    target_improved: bool
    retention_passed: bool
    regression_passed: bool
    qualified: bool
    reason_codes: tuple[str, ...]
    receipt_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": QUALIFICATION_RECEIPT_SCHEMA_VERSION,
            "qualification_receipt_id": self.qualification_receipt_id,
            "policy_id": self.policy_id,
            "independent": self.independent,
            "candidate_model_digest": self.candidate_model_digest,
            "disposition": self.disposition,
            "changed_parameter_names": list(self.changed_parameter_names),
            "allowed_parameter_names": list(self.allowed_parameter_names),
            "gradient_norm_microunits": self.gradient_norm_microunits,
            "max_gradient_norm_microunits": self.max_gradient_norm_microunits,
            "baseline_metrics_microunits": dict(self.baseline_metrics_microunits),
            "candidate_metrics_microunits": dict(self.candidate_metrics_microunits),
            "target_improved": self.target_improved,
            "retention_passed": self.retention_passed,
            "regression_passed": self.regression_passed,
            "qualified": self.qualified,
            "reason_codes": list(self.reason_codes),
            "receipt_digest": self.receipt_digest,
        }


@dataclass(frozen=True)
class LearningProposal:
    staged_model: nn.Module
    checkpoint: CheckpointBundle
    gradient_artifact: StoredArtifact
    gradient_reference: object
    intent: ModelUpdateIntent
    qualification: QualificationReceipt
    changed_parameter_names: tuple[str, ...]
    plasticity_ppm: int

    @property
    def artifacts(self) -> tuple[StoredArtifact, ...]:
        return (self.checkpoint.artifact, self.gradient_artifact)


def _microunits(value: float, *, label: str) -> int:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise LearningError(f"metric {label} must be finite")
    scaled = int(round(float(value) * 1_000_000))
    if scaled < 0:
        raise LearningError(f"metric {label} must be nonnegative")
    return scaled


def _require_string_list(
    value: object,
    *,
    label: str,
    allow_empty: bool,
) -> list[str]:
    if not isinstance(value, list):
        raise LearningError(f"qualification {label} must be a JSON array")
    if (not allow_empty and not value) or any(
        not isinstance(item, str) or not item for item in value
    ):
        qualifier = "nonempty " if allow_empty else "one or more nonempty "
        raise LearningError(
            f"qualification {label} must contain {qualifier}strings"
        )
    if len(set(value)) != len(value):
        raise LearningError(f"qualification {label} must not contain duplicates")
    if value != sorted(value):
        raise LearningError(f"qualification {label} must be sorted")
    return list(value)


def _require_metric_map(
    value: object,
    *,
    label: str,
    expected_names: set[str],
) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != expected_names:
        raise LearningError(
            f"qualification {label} keys must exactly match the configured metrics"
        )
    result: dict[str, int] = {}
    for name in sorted(expected_names):
        metric = value[name]
        if not isinstance(metric, int) or isinstance(metric, bool) or metric < 0:
            raise LearningError(
                f"qualification {label}.{name} must be a nonnegative integer"
            )
        result[name] = metric
    return result


def validate_qualification_receipt(
    value: QualificationReceipt | Mapping[str, object],
    *,
    policy: LearningPolicy,
) -> dict[str, object]:
    """Validate one qualification receipt against an admitted learning policy.

    The check is deterministic and recomputes all locally derivable decisions.
    ``regression_passed`` and ``independent`` remain declarations from the
    external test producer; this function binds them into the receipt but does
    not prove that the producer was organizationally independent or that it ran
    a real regression suite.
    """

    policy.validate()
    raw = value.to_dict() if isinstance(value, QualificationReceipt) else value
    if not isinstance(raw, Mapping):
        raise LearningError("qualification receipt must be a JSON object")
    if set(raw) != _QUALIFICATION_RECEIPT_WIRE_KEYS:
        missing = sorted(_QUALIFICATION_RECEIPT_WIRE_KEYS - set(raw))
        extra = sorted(
            set(raw) - _QUALIFICATION_RECEIPT_WIRE_KEYS,
            key=lambda item: repr(item),
        )
        raise LearningError(
            f"qualification receipt keys are not exact; missing={missing}, extra={extra}"
        )
    wire = dict(raw)
    if wire["schema_version"] != QUALIFICATION_RECEIPT_SCHEMA_VERSION:
        raise LearningError("qualification receipt schema_version is not admitted")

    for name in ("qualification_receipt_id", "policy_id"):
        if not isinstance(wire[name], str) or not wire[name]:
            raise LearningError(f"qualification {name} must be a nonempty string")
    if wire["policy_id"] != policy.policy_id:
        raise LearningError("qualification policy_id does not match the admitted policy")

    for name in ("candidate_model_digest", "receipt_digest"):
        digest = wire[name]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise LearningError(f"qualification {name} must be a lowercase SHA-256 digest")

    if not isinstance(wire["independent"], bool) or wire["independent"] is not True:
        raise LearningError("qualification independent must be the boolean true declaration")
    for name in (
        "target_improved",
        "retention_passed",
        "regression_passed",
        "qualified",
    ):
        if not isinstance(wire[name], bool):
            raise LearningError(f"qualification {name} must be a boolean")

    changed = _require_string_list(
        wire["changed_parameter_names"],
        label="changed_parameter_names",
        allow_empty=False,
    )
    allowed = _require_string_list(
        wire["allowed_parameter_names"],
        label="allowed_parameter_names",
        allow_empty=False,
    )
    if not set(changed).issubset(allowed):
        raise LearningError("qualification changed parameters escape the allowed set")

    gradient_norm = wire["gradient_norm_microunits"]
    maximum_norm = wire["max_gradient_norm_microunits"]
    if (
        not isinstance(gradient_norm, int)
        or isinstance(gradient_norm, bool)
        or gradient_norm < 0
    ):
        raise LearningError(
            "qualification gradient_norm_microunits must be a nonnegative integer"
        )
    expected_maximum = _microunits(
        policy.max_gradient_norm,
        label="max_gradient_norm",
    )
    if expected_maximum <= 0:
        raise LearningError("configured max gradient norm is below one microunit")
    if (
        not isinstance(maximum_norm, int)
        or isinstance(maximum_norm, bool)
        or maximum_norm != expected_maximum
    ):
        raise LearningError(
            "qualification max_gradient_norm_microunits does not match the admitted policy"
        )
    if gradient_norm > maximum_norm:
        raise LearningError("qualification gradient norm exceeds the admitted maximum")

    expected_metrics = {policy.target_metric, *policy.retention_metric_names}
    before = _require_metric_map(
        wire["baseline_metrics_microunits"],
        label="baseline_metrics_microunits",
        expected_names=expected_metrics,
    )
    after = _require_metric_map(
        wire["candidate_metrics_microunits"],
        label="candidate_metrics_microunits",
        expected_names=expected_metrics,
    )
    target_improved = (
        before[policy.target_metric] - after[policy.target_metric]
        >= policy.minimum_improvement_ppm
    )
    retention_passed = all(
        after[name] <= before[name] + policy.retention_tolerance_ppm
        for name in policy.retention_metric_names
    )
    if wire["target_improved"] is not target_improved:
        raise LearningError("qualification target_improved does not match its metrics")
    if wire["retention_passed"] is not retention_passed:
        raise LearningError("qualification retention_passed does not match its metrics")

    regression_passed = wire["regression_passed"]
    qualified = target_improved and retention_passed and regression_passed
    if wire["qualified"] is not qualified:
        raise LearningError("qualification qualified is not the exact decision conjunction")
    expected_disposition = "QUALIFIED" if qualified else "REFUSED"
    if wire["disposition"] != expected_disposition:
        raise LearningError("qualification disposition does not match the decision")
    expected_reasons = [
        "TARGET_IMPROVED" if target_improved else "TARGET_NOT_IMPROVED",
        "RETENTION_PASSED" if retention_passed else "RETENTION_FAILED",
        "REGRESSION_PASSED" if regression_passed else "REGRESSION_FAILED",
    ]
    if wire["reason_codes"] != expected_reasons:
        raise LearningError("qualification reason_codes do not match the decision")

    body = {name: wire[name] for name in _QUALIFICATION_RECEIPT_BODY_KEYS}
    expected_id = content_id("qualification", body)
    if wire["qualification_receipt_id"] != expected_id:
        raise LearningError("qualification_receipt_id is not content-derived")
    expected_digest = canonical_digest(
        {
            "schema_version": QUALIFICATION_RECEIPT_SCHEMA_VERSION,
            "qualification_receipt_id": expected_id,
            **body,
        }
    )
    if wire["receipt_digest"] != expected_digest:
        raise LearningError("qualification receipt_digest is invalid")
    return wire


def _qualify(
    baseline: Mapping[str, float],
    candidate: Mapping[str, float],
    *,
    policy: LearningPolicy,
    regression_passed: bool,
    candidate_model_digest: str,
    changed_parameter_names: Sequence[str],
    allowed_parameter_names: Sequence[str],
    gradient_norm: float,
) -> QualificationReceipt:
    if not isinstance(regression_passed, bool):
        raise LearningError("regression_passed must be a boolean test result")
    if set(baseline) != set(candidate):
        raise LearningError("baseline and candidate score sets differ")
    expected_metrics = {policy.target_metric, *policy.retention_metric_names}
    if set(baseline) != expected_metrics:
        raise LearningError("score function metric keys do not exactly match the policy")
    before = {name: _microunits(value, label=name) for name, value in sorted(baseline.items())}
    after = {name: _microunits(value, label=name) for name, value in sorted(candidate.items())}
    target_improved = (
        before[policy.target_metric] - after[policy.target_metric]
        >= policy.minimum_improvement_ppm
    )
    retention_passed = all(
        after[name] <= before[name] + policy.retention_tolerance_ppm
        for name in policy.retention_metric_names
    )
    qualified = target_improved and retention_passed and regression_passed
    reasons = []
    reasons.append("TARGET_IMPROVED" if target_improved else "TARGET_NOT_IMPROVED")
    reasons.append("RETENTION_PASSED" if retention_passed else "RETENTION_FAILED")
    reasons.append("REGRESSION_PASSED" if regression_passed else "REGRESSION_FAILED")
    body = {
        "policy_id": policy.policy_id,
        "independent": True,
        "candidate_model_digest": candidate_model_digest,
        "disposition": "QUALIFIED" if qualified else "REFUSED",
        "changed_parameter_names": list(changed_parameter_names),
        "allowed_parameter_names": list(allowed_parameter_names),
        "gradient_norm_microunits": _microunits(gradient_norm, label="gradient_norm"),
        "max_gradient_norm_microunits": _microunits(
            policy.max_gradient_norm, label="max_gradient_norm"
        ),
        "baseline_metrics_microunits": before,
        "candidate_metrics_microunits": after,
        "target_improved": target_improved,
        "retention_passed": retention_passed,
        "regression_passed": regression_passed,
        "qualified": qualified,
        "reason_codes": reasons,
    }
    receipt_id = content_id("qualification", body)
    digest = canonical_digest(
        {
            "schema_version": QUALIFICATION_RECEIPT_SCHEMA_VERSION,
            "qualification_receipt_id": receipt_id,
            **body,
        }
    )
    receipt = QualificationReceipt(
        qualification_receipt_id=receipt_id,
        policy_id=policy.policy_id,
        independent=True,
        candidate_model_digest=candidate_model_digest,
        disposition="QUALIFIED" if qualified else "REFUSED",
        changed_parameter_names=tuple(changed_parameter_names),
        allowed_parameter_names=tuple(allowed_parameter_names),
        gradient_norm_microunits=body["gradient_norm_microunits"],
        max_gradient_norm_microunits=body["max_gradient_norm_microunits"],
        baseline_metrics_microunits=before,
        candidate_metrics_microunits=after,
        target_improved=target_improved,
        retention_passed=retention_passed,
        regression_passed=regression_passed,
        qualified=qualified,
        reason_codes=tuple(reasons),
        receipt_digest=digest,
    )
    validate_qualification_receipt(receipt, policy=policy)
    return receipt


def _gradient_vector(parameters: Sequence[tuple[str, nn.Parameter]]) -> Tensor:
    pieces: list[Tensor] = []
    for name, parameter in parameters:
        if parameter.grad is None:
            raise LearningError(f"allowed parameter {name} received no gradient")
        gradient = parameter.grad.detach()
        if not bool(torch.isfinite(gradient).all().item()):
            raise LearningError(f"gradient for {name} is non-finite")
        pieces.append(gradient.reshape(-1).to(device="cpu", dtype=torch.float32))
    if not pieces:
        raise LearningError("plasticity allowlist selected no parameters")
    return torch.cat(pieces)


@dataclass(frozen=True)
class _ActiveModelSnapshot:
    checkpoint: CheckpointBundle
    parameter_requires_grad: tuple[tuple[str, bool], ...]
    parameter_gradients: tuple[tuple[str, Tensor | None], ...]
    training_modes: tuple[tuple[str, bool], ...]


def _capture_active_model(module: nn.Module) -> _ActiveModelSnapshot:
    return _ActiveModelSnapshot(
        checkpoint=encode_module_checkpoint(module),
        parameter_requires_grad=tuple(
            (name, parameter.requires_grad)
            for name, parameter in module.named_parameters()
        ),
        parameter_gradients=tuple(
            (
                name,
                None if parameter.grad is None else parameter.grad.detach().clone(),
            )
            for name, parameter in module.named_parameters()
        ),
        training_modes=tuple(
            (name, child.training)
            for name, child in module.named_modules()
        ),
    )


def _restore_active_model(
    module: nn.Module,
    snapshot: _ActiveModelSnapshot,
) -> None:
    """Restore all mutable PyTorch state exposed to a callback closure."""

    try:
        load_module_checkpoint(
            module,
            snapshot.checkpoint.reference,
            snapshot.checkpoint.artifact,
        )
        parameters = dict(module.named_parameters())
        expected_parameter_names = {
            name for name, _ in snapshot.parameter_requires_grad
        }
        if set(parameters) != expected_parameter_names:
            raise LearningError("active model parameter layout changed during learning")
        for name, requires_grad in snapshot.parameter_requires_grad:
            parameters[name].requires_grad_(requires_grad)
        for name, gradient in snapshot.parameter_gradients:
            parameters[name].grad = (
                None
                if gradient is None
                else gradient.detach()
                .to(device=parameters[name].device, dtype=parameters[name].dtype)
                .clone()
            )

        modules = dict(module.named_modules())
        expected_module_names = {name for name, _ in snapshot.training_modes}
        if set(modules) != expected_module_names:
            raise LearningError("active model module layout changed during learning")
        for name, training in snapshot.training_modes:
            modules[name].training = training

        restored = encode_module_checkpoint(module)
        if restored.artifact.payload != snapshot.checkpoint.artifact.payload:
            raise LearningError("active model bytes could not be restored exactly")
    except LearningError:
        raise
    except Exception as exc:
        raise LearningError("active model could not be restored after learning") from exc


def _resolve_plasticity_groups(
    *,
    bias: BiasState,
    operation_contract: OperationContract,
    parameter_group_ids: Sequence[str] | None,
) -> tuple[str, ...]:
    """Turn contract role templates into concrete groups for one Bias."""

    roles = tuple(operation_contract.plasticity_groups)
    if len(set(roles)) != len(roles) or any(role.startswith("cjt:") for role in roles):
        raise LearningError(
            "operation contract plasticity groups must be unique unscoped roles"
        )
    scope = f"cjt:{bias.cjt_id}:"
    if parameter_group_ids is None:
        return tuple(f"{scope}{role}" for role in roles)
    if isinstance(parameter_group_ids, (str, bytes)):
        raise LearningError("parameter_group_ids must be a sequence of scoped groups")
    groups = tuple(parameter_group_ids)
    if (
        not groups
        or any(not isinstance(group, str) or not group for group in groups)
        or len(set(groups)) != len(groups)
    ):
        raise LearningError(
            "parameter_group_ids must contain unique nonempty scoped groups"
        )
    if any(not group.startswith(scope) or group == scope for group in groups):
        raise LearningError("plasticity parameter group is not scoped to the Bias CJT")
    requested_roles = {group[len(scope) :] for group in groups}
    if not requested_roles.issubset(set(roles)):
        raise LearningError(
            "plasticity parameter-group role is not admitted by the operation contract"
        )
    return groups


class GovernedLearner:
    """Create a qualified model update proposal on an isolated clone."""

    def __init__(self, policy: LearningPolicy | None = None) -> None:
        self.policy = LearningPolicy() if policy is None else policy
        self.policy.validate()

    def propose(
        self,
        *,
        active_model: nn.Module,
        bias: BiasState,
        operation_contract: OperationContract,
        verifier_receipt: VerifierReceipt,
        tick: int,
        loss_fn: LossFunction,
        score_fn: ScoreFunction,
        allowed_parameter_names: Sequence[str],
        parameter_group_ids: Sequence[str] | None = None,
        flow_ppm: int,
        regression_passed: bool = False,
        issuer_id: str = "prototype-write-back-controller",
    ) -> LearningProposal:
        if verifier_receipt.disposition is not VerifierDisposition.ACCEPT:
            raise LearningError("learning requires an accepted independent verifier receipt")
        if (
            verifier_receipt.bias_id != bias.bias_id
            or verifier_receipt.bias_digest != bias.state_digest
            or verifier_receipt.model_digest != bias.theta.model_digest
            or verifier_receipt.operation_contract_id != operation_contract.contract_id
        ):
            raise LearningError("learning receipt does not bind Bias/model/operation")
        if "learn" not in bias.governance.learning_permissions or bias.governance.quarantined:
            raise LearningError("Bias governance denies learning")
        if not 0 <= flow_ppm <= 1_000_000:
            raise LearningError("flow_ppm must be in [0, 1000000]")
        plasticity_ppm = min(bias.rpm.readiness.readiness_ppm, flow_ppm)
        if plasticity_ppm == 0:
            raise LearningError("zero flow or readiness grants zero plasticity")

        allowed = tuple(sorted(set(allowed_parameter_names)))
        groups = _resolve_plasticity_groups(
            bias=bias,
            operation_contract=operation_contract,
            parameter_group_ids=parameter_group_ids,
        )
        if not groups or not set(groups).issubset(set(bias.theta.parameter_group_ids)):
            raise LearningError("plasticity parameter groups are not admitted by Bias Theta")
        if not set(groups).issubset(set(bias.governance.learning_permissions)):
            raise LearningError("Bias governance denies a requested parameter group")
        active_snapshot = _capture_active_model(active_model)
        try:
            baseline_model = deepcopy(active_model)
            working_model = deepcopy(baseline_model)
            selected: list[tuple[str, nn.Parameter]] = []
            for name, parameter in working_model.named_parameters():
                permitted = name in allowed
                parameter.requires_grad_(permitted)
                if permitted:
                    selected.append((name, parameter))
            if {name for name, _ in selected} != set(allowed):
                missing = sorted(set(allowed) - {name for name, _ in selected})
                raise LearningError(f"unknown plasticity parameter names: {missing}")

            baseline_scores = dict(score_fn(deepcopy(baseline_model)))
            loss = loss_fn(working_model)
            if (
                not isinstance(loss, Tensor)
                or loss.numel() != 1
                or not loss.is_floating_point()
            ):
                raise LearningError("loss_fn must return one floating scalar Tensor")
            if not bool(torch.isfinite(loss).item()):
                raise LearningError("candidate learning loss is non-finite")
            loss.backward()
            gradient = _gradient_vector(selected)
            gradient_norm = float(torch.linalg.vector_norm(gradient).item())
            if not math.isfinite(gradient_norm):
                raise LearningError("gradient norm is non-finite")
            clip = min(
                1.0,
                self.policy.max_gradient_norm / max(gradient_norm, 1e-30),
            )
            scale = self.policy.learning_rate * (plasticity_ppm / 1_000_000) * clip
            with torch.no_grad():
                for _, parameter in selected:
                    assert parameter.grad is not None
                    parameter.add_(parameter.grad, alpha=-scale)

            # The loss callback saw only ``working_model``.  Seal a fresh
            # authority candidate so a later score callback cannot reach it
            # through a reference retained by the loss callback.
            staged_model = deepcopy(working_model)
            candidate_scores = dict(score_fn(deepcopy(staged_model)))
            changed = changed_parameter_names(baseline_model, staged_model)
            if not changed or not set(changed) <= set(allowed):
                raise LearningError(
                    "candidate update changed no parameters or escaped its allowlist"
                )
            # Encode only after scoring has completed against an isolated copy.
            checkpoint = encode_module_checkpoint(staged_model)
            qualification = _qualify(
                baseline_scores,
                candidate_scores,
                policy=self.policy,
                regression_passed=regression_passed,
                candidate_model_digest=checkpoint.model_digest,
                changed_parameter_names=changed,
                allowed_parameter_names=allowed,
                gradient_norm=gradient_norm * clip,
            )
            if not qualification.qualified:
                raise QualificationFailed(";".join(qualification.reason_codes))

            gradient_ref_mapping, gradient_artifact = encode_tensor(
                gradient,
                kind="candidate-gradient",
            )
            gradient_ref = tensor_ref_from_mapping(gradient_ref_mapping)
            identity = {
                "tick": tick,
                "model_id": bias.theta.model_id,
                "expected_model_digest": bias.theta.model_digest,
                "update_kind": ModelUpdateKind.GRADIENT_DELTA.value,
                "candidate_model_digest": checkpoint.model_digest,
                "gradient_digest": gradient_artifact.sha256,
                "parameter_names": list(changed),
                "parameter_group_ids": list(groups),
                "plasticity_ppm": plasticity_ppm,
                "verifier_receipt_id": verifier_receipt.receipt_id,
                "qualification_receipt_id": qualification.qualification_receipt_id,
            }
            intent = ModelUpdateIntent(
                intent_id=content_id("intent-model", identity),
                tick=tick,
                issuer_id=issuer_id,
                authority_capability=AuthorityCapability.PROPOSE_MODEL_UPDATE.value,
                model_id=bias.theta.model_id,
                expected_model_version=bias.theta.model_version,
                expected_model_digest=bias.theta.model_digest,
                update_kind=ModelUpdateKind.GRADIENT_DELTA,
                parameter_group_ids=groups,
                candidate_artifact=checkpoint.reference,
                gradient_artifact=gradient_ref,
                plasticity_ppm=plasticity_ppm,
                verifier_receipt_id=verifier_receipt.receipt_id,
                qualification_receipt_id=qualification.qualification_receipt_id,
                reason_codes=(
                    "VERIFIED_EXPERIENCE",
                    "SELECTIVE_PLASTICITY",
                    "QUALIFIED",
                ),
                intent_digest=ZERO_DIGEST,
            )
            intent = replace(
                intent,
                intent_digest=canonical_digest(
                    intent.to_dict(),
                    omit_keys=("intent_digest",),
                ),
            )
            return LearningProposal(
                staged_model=staged_model,
                checkpoint=checkpoint,
                gradient_artifact=gradient_artifact,
                gradient_reference=gradient_ref,
                intent=intent,
                qualification=qualification,
                changed_parameter_names=changed,
                plasticity_ppm=plasticity_ppm,
            )
        finally:
            _restore_active_model(active_model, active_snapshot)


__all__ = [
    "GovernedLearner",
    "LearningError",
    "LearningPolicy",
    "LearningProposal",
    "QualificationFailed",
    "QualificationReceipt",
    "validate_qualification_receipt",
]
