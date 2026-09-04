"""Proposal-only neural CJTs built from the frozen CASformer v0.1 engine.

The CASformer residual/FFN output is deliberately discarded.  A Neural CJT
candidate is derived only from ``telemetry.cjt_effect``, which is already
hard-gated by admitted flow and the operating region.  The module proposes an
Effect and a Bias delta; it has no publication or state-write authority.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from casformer import (
    CASControl,
    CASformerBlock,
    CASformerConfig,
    CASformerTelemetry,
    DifferentialConductanceLinear,
)

from .contracts import verify_declared_digest
from .types import BUILTIN_OPERATION_IDENTITIES, OntologyStatus, OperationContract


DECOMPOSE = "^6"
ATTRACT = "^2"
AVERT = "^3"
TRIGGER = "^8"


class NeuralCJTError(ValueError):
    """A neural CJT registration or call violated its proposal contract."""


OperationAdmission = OntologyStatus


@dataclass(frozen=True)
class OperationRegistration:
    operation_id: str
    name: str
    relation_index: int
    admission: OntologyStatus
    contract_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.operation_id, str) or not self.operation_id:
            raise NeuralCJTError("operation_id must be a nonempty string")
        if "." in self.operation_id:
            raise NeuralCJTError("operation_id cannot contain '.'")
        if not isinstance(self.name, str) or not self.name:
            raise NeuralCJTError("operation name must be a nonempty string")
        if (
            not isinstance(self.relation_index, int)
            or isinstance(self.relation_index, bool)
            or self.relation_index < 0
        ):
            raise NeuralCJTError("relation_index must be a nonnegative integer")
        try:
            admission = OntologyStatus(self.admission)
        except (TypeError, ValueError) as exc:
            raise NeuralCJTError("operation admission status is invalid") from exc
        object.__setattr__(self, "admission", admission)
        if not isinstance(self.contract_id, str) or not self.contract_id:
            raise NeuralCJTError("contract_id must be a nonempty string")


OPERATION_REGISTRATIONS: tuple[OperationRegistration, ...] = (
    OperationRegistration(
        operation_id=DECOMPOSE,
        name="decompose",
        relation_index=0,
        admission=OntologyStatus.CANONICAL_ADMITTED,
        contract_id="cas.cjt.operation.^6.decompose/0.2",
    ),
    OperationRegistration(
        operation_id=ATTRACT,
        name="experimental_attract",
        relation_index=1,
        admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        contract_id="cas.cjt.operation.^2.attract.experimental/0.2",
    ),
    OperationRegistration(
        operation_id=AVERT,
        name="experimental_avert",
        relation_index=2,
        admission=OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS,
        contract_id="cas.cjt.operation.^3.avert.experimental/0.2",
    ),
    OperationRegistration(
        operation_id=TRIGGER,
        name="experimental_trigger",
        relation_index=3,
        admission=OntologyStatus.EXPERIMENTAL_CONFLICTED_SEMANTICS,
        contract_id="cas.cjt.operation.^8.trigger.experimental/0.2",
    ),
)


def _linear(config: CASformerConfig, in_features: int, out_features: int) -> nn.Module:
    if config.linear_weight_mode == "differential_conductance":
        return DifferentialConductanceLinear(
            in_features,
            out_features,
            minimum_resistance=config.minimum_weight_resistance,
            bias=False,
        )
    return nn.Linear(in_features, out_features, bias=False)


class _DecomposeTransform(nn.Module):
    """Two learned views merged into one typed ^6 candidate channel."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.left = _linear(config, config.d_model, config.d_model)
        self.right = _linear(config, config.d_model, config.d_model)
        self.merge = _linear(config, 2 * config.d_model, config.d_model)

    def forward(self, value: Tensor) -> Tensor:
        parts = torch.cat((torch.tanh(self.left(value)), torch.tanh(self.right(value))), dim=-1)
        return self.merge(parts)


class _AttractTransform(nn.Module):
    """Experimental learned preference channel; not canonical ^2 semantics."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.direction = _linear(config, config.d_model, config.d_model)
        self.gate = _linear(config, config.d_model, config.d_model)

    def forward(self, value: Tensor) -> Tensor:
        return torch.tanh(self.direction(value)) * torch.sigmoid(self.gate(value))


class _AvertTransform(nn.Module):
    """Experimental learned rejection channel; not canonical ^3 semantics."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.direction = _linear(config, config.d_model, config.d_model)
        self.gate = _linear(config, config.d_model, config.d_model)

    def forward(self, value: Tensor) -> Tensor:
        return -torch.tanh(self.direction(value)) * torch.sigmoid(self.gate(value))


class _TriggerTransform(nn.Module):
    """Experimental learned association channel; not deduction authority."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.source = _linear(config, config.d_model, config.d_model)
        self.response = _linear(config, config.d_model, config.d_model)

    def forward(self, value: Tensor) -> Tensor:
        return self.response(F.gelu(self.source(value)))


class RegisteredOperationBank(nn.Module):
    """Versioned operation identities backed by distinct neural modules.

    The four built-ins keep their frozen behavior.  A caller may add an
    experimental operation with :meth:`register_operation`, but the new module
    cannot execute until :meth:`bind_contract` accepts its exact typed
    OperationContract.
    """

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        if config.num_relations < len(OPERATION_REGISTRATIONS):
            raise NeuralCJTError(
                f"num_relations must be at least {len(OPERATION_REGISTRATIONS)}"
            )
        self.config = config
        self.modules_by_operation = nn.ModuleDict(
            {
                DECOMPOSE: _DecomposeTransform(config),
                ATTRACT: _AttractTransform(config),
                AVERT: _AvertTransform(config),
                TRIGGER: _TriggerTransform(config),
            }
        )
        self._registrations = {
            registration.operation_id: registration
            for registration in OPERATION_REGISTRATIONS
        }
        self._extension_ids: set[str] = set()
        self._bound_contract_digests: dict[str, str] = {}
        for registration in OPERATION_REGISTRATIONS:
            expected = BUILTIN_OPERATION_IDENTITIES[registration.operation_id]
            if (registration.name, registration.admission) != expected:
                raise NeuralCJTError(
                    f"registration {registration.operation_id} conflicts with the typed ontology"
                )

    def register_operation(
        self,
        registration: OperationRegistration,
        module: nn.Module,
    ) -> OperationRegistration:
        """Inject one new experimental module in an initially unbound state."""

        if not isinstance(registration, OperationRegistration):
            raise NeuralCJTError("registration must be an OperationRegistration")
        if not isinstance(module, nn.Module):
            raise NeuralCJTError("operation module must be a torch.nn.Module")
        if registration.operation_id in self._registrations:
            raise NeuralCJTError(
                f"operation is already registered: {registration.operation_id}"
            )
        if registration.operation_id in BUILTIN_OPERATION_IDENTITIES:
            raise NeuralCJTError("frozen built-in operation identities cannot be replaced")
        if registration.admission is OntologyStatus.CANONICAL_ADMITTED:
            raise NeuralCJTError("only the frozen ^6 operation may be canonical-admitted")
        if not registration.name.startswith("experimental_"):
            raise NeuralCJTError("extension operation names must start with 'experimental_'")
        if registration.relation_index >= self.config.num_relations:
            raise NeuralCJTError(
                "extension relation_index exceeds the configured relation channels"
            )
        if any(
            existing.relation_index == registration.relation_index
            for existing in self._registrations.values()
        ):
            raise NeuralCJTError("relation_index is already assigned to another operation")
        if any(
            existing.contract_id == registration.contract_id
            for existing in self._registrations.values()
        ):
            raise NeuralCJTError("contract_id is already assigned to another operation")
        if any(existing is module for existing in self.modules_by_operation.values()):
            raise NeuralCJTError("each operation requires a distinct neural module instance")
        self.modules_by_operation[registration.operation_id] = module
        self._registrations[registration.operation_id] = registration
        self._extension_ids.add(registration.operation_id)
        return registration

    # A descriptive alias for callers that treat additions as plugins.
    register_extension = register_operation

    def registration(self, operation_id: str) -> OperationRegistration:
        try:
            return self._registrations[operation_id]
        except KeyError as error:
            raise NeuralCJTError(f"unregistered CJT operation: {operation_id}") from error

    def executable_registration(self, operation_id: str) -> OperationRegistration:
        """Resolve an operation only if every required authority binding exists."""

        registration = self.registration(operation_id)
        if (
            operation_id in self._extension_ids
            and operation_id not in self._bound_contract_digests
        ):
            raise NeuralCJTError(
                f"extension operation is not contract-bound: {operation_id}"
            )
        return registration

    def bound_contract_digest(self, operation_id: str) -> str | None:
        self.registration(operation_id)
        return self._bound_contract_digests.get(operation_id)

    def forward(self, operation_id: str, value: Tensor) -> Tensor:
        registration = self.executable_registration(operation_id)
        if not isinstance(value, Tensor):
            raise NeuralCJTError("operation input must be a torch.Tensor")
        result = self.modules_by_operation[registration.operation_id](value)
        if registration.operation_id in self._extension_ids:
            if not isinstance(result, Tensor):
                raise NeuralCJTError("extension operation must return a torch.Tensor")
            if (
                result.shape != value.shape
                or result.dtype != value.dtype
                or result.device != value.device
            ):
                raise NeuralCJTError(
                    "extension operation must preserve tensor shape, dtype, and device"
                )
            if not bool(torch.isfinite(result).all().item()):
                raise NeuralCJTError("extension operation returned non-finite values")
        return result

    def bind_contract(self, contract: OperationContract) -> OperationRegistration:
        """Bind a strict operation contract to its one registered neural module."""

        if not isinstance(contract, OperationContract):
            raise NeuralCJTError("contract must be an OperationContract")
        registration = self.registration(contract.operation_id)
        if (
            contract.contract_id != registration.contract_id
            or contract.operation_name != registration.name
            or contract.ontology_status is not registration.admission
        ):
            raise NeuralCJTError("operation contract does not match the neural registration")
        if not verify_declared_digest(contract, "contract_digest"):
            raise NeuralCJTError("operation contract digest is invalid")
        existing_digest = self._bound_contract_digests.get(contract.operation_id)
        if existing_digest is not None and existing_digest != contract.contract_digest:
            raise NeuralCJTError("operation is already bound to a different contract digest")
        self._bound_contract_digests[contract.operation_id] = contract.contract_digest
        return registration

    def linear_modules(self) -> tuple[nn.Module, ...]:
        return tuple(
            module
            for operation in self.modules_by_operation.values()
            for module in operation.modules()
            if isinstance(module, (nn.Linear, DifferentialConductanceLinear))
        )


@dataclass(frozen=True)
class NeuralCJTProposal:
    """Non-authoritative tensors emitted by one Neural CJT execution."""

    operation: OperationRegistration
    candidate_effect: Tensor
    proposed_bias_delta: Tensor
    execution_mask: Tensor
    telemetry: CASformerTelemetry


class NeuralCJT(nn.Module):
    """Trainable proposal-only reasoning transistor.

    The wrapper reuses CASformer's Q/K/V projections, CAS-Ohm attention,
    relation operator, CJT region gate, beta, and positive-rail option.  It
    never treats the residual stream returned by ``CASformerBlock`` as an
    Effect.
    """

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.config = config
        self.engine = CASformerBlock(config)
        self.operations = RegisteredOperationBank(config)
        self.bias_update_head = _linear(config, config.d_model, config.d_model)

    def _validate_operation_binding(
        self,
        control: CASControl,
        registration: OperationRegistration,
    ) -> None:
        candidate = control.candidate_path_mask
        mismatched = candidate & (control.relation_ids != registration.relation_index)
        if bool(mismatched.any().item()):
            raise NeuralCJTError(
                "candidate route relation_ids do not match the registered operation"
            )

    def forward(
        self,
        x: Tensor,
        control: CASControl,
        *,
        operation_id: str,
    ) -> NeuralCJTProposal:
        registration = self.operations.executable_registration(operation_id)
        self._validate_operation_binding(control, registration)

        # CASformerBlock computes its residual/FFN output for compatibility,
        # but that tensor is intentionally discarded.  Only the hard-gated
        # telemetry Effect is allowed to seed a CJT proposal.
        _, telemetry = self.engine(x, control)
        gated_heads = telemetry.cjt_effect
        merged_effect = self.engine.attention.merge_heads(gated_heads)
        projected_effect = self.engine.attention.out_proj(merged_effect)
        transformed = self.operations(operation_id, projected_effect)

        execution_mask = (telemetry.cjt_gate > 0).any(dim=1)
        candidate_effect = torch.where(
            execution_mask.unsqueeze(-1),
            transformed,
            torch.zeros_like(transformed),
        )
        raw_bias_delta = self.bias_update_head(candidate_effect)
        proposed_bias_delta = torch.where(
            execution_mask.unsqueeze(-1),
            raw_bias_delta,
            torch.zeros_like(raw_bias_delta),
        )
        if not bool(torch.isfinite(candidate_effect).all().item()):
            raise NeuralCJTError("candidate Effect became non-finite")
        if not bool(torch.isfinite(proposed_bias_delta).all().item()):
            raise NeuralCJTError("proposed Bias delta became non-finite")
        return NeuralCJTProposal(
            operation=registration,
            candidate_effect=candidate_effect,
            proposed_bias_delta=proposed_bias_delta,
            execution_mask=execution_mask,
            telemetry=telemetry,
        )


__all__ = [
    "ATTRACT",
    "AVERT",
    "DECOMPOSE",
    "TRIGGER",
    "NeuralCJT",
    "NeuralCJTError",
    "NeuralCJTProposal",
    "OPERATION_REGISTRATIONS",
    "OperationAdmission",
    "OperationRegistration",
    "RegisteredOperationBank",
]
