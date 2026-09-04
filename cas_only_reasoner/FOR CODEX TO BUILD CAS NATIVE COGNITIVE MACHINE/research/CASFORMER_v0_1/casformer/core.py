"""Differentiable CAS-Ohm attention and CJT-inspired Transformer blocks.

This module is an isolated research implementation.  It has no CNCM intent,
state-write, proof, commitment, memory-write, action, or permission authority.

The core split is deliberate:

* CAS-Ohm conductance controls path flow and relative allocation.
* A local relation-ID-selected operator transforms semantic content.
* A CJT gate uses reference-normalized available-flow magnitude, explicit
  Bias, and independently readable Drive/resistance components to select a
  bounded operating response.

The tensors are floating-point neural quantities.  They are not canonical
CNCM exact-decimal records and are not physical volts, amperes, or ohms.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import math
from typing import Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F


CASFORMER_VERSION = "0.1.0"
DIAGNOSTIC_FEATURE_NAMES = (
    "drive",
    "resistance_capability",
    "resistance_policy",
    "resistance_context",
    "resistance_resource",
)


class OperatingRegion(IntEnum):
    """Machine-readable CJT operating-region labels."""

    CUTOFF = 0
    ACTIVE = 1
    SATURATION = 2
    BREAKDOWN = 3


def _inverse_softplus(value: float) -> float:
    if value <= 0:
        raise ValueError("inverse softplus requires a positive value")
    return value + math.log(-math.expm1(-value))


def _logit(value: float) -> float:
    if not 0 < value < 1:
        raise ValueError("logit input must be strictly between zero and one")
    return math.log(value / (1.0 - value))


def _require_finite(name: str, value: Tensor) -> None:
    if not bool(torch.isfinite(value).all().item()):
        raise ValueError(f"{name} must contain only finite values")


def _stable_log1p_ratio(value: Tensor, reference: float) -> Tensor:
    """Compute log(1 + value/reference) without forming an overflowing ratio."""

    positive = value > 0
    safe_value = torch.where(
        positive, value, torch.full_like(value, reference)
    )
    log_reference = math.log(reference)
    result = torch.logaddexp(
        torch.log(safe_value), torch.full_like(value, log_reference)
    ) - log_reference
    return torch.where(positive, result, torch.zeros_like(result))


@dataclass(frozen=True)
class CASControl:
    """Explicit control plane for one CASformer layer.

    Edge tensors use shape ``[batch, heads, query, key]``.  ``bias`` uses
    shape ``[batch, query, d_model]``.  Hard topology and permission masks are
    separate from resistance because finite soft resistance cannot certify a
    closed path. ``breakdown_mask`` is optional and uses shape
    ``[batch, heads, query]``.
    """

    drive: Tensor
    resistance_capability: Tensor
    resistance_policy: Tensor
    resistance_context: Tensor
    resistance_resource: Tensor
    readiness: Tensor
    region_multiplier: Tensor
    topology_mask: Tensor
    permission_mask: Tensor
    relation_ids: Tensor
    bias: Tensor
    breakdown_mask: Tensor | None = None
    profile_id: str = "UNREGISTERED_NEURAL_PROXY"
    provenance: str = "UNREGISTERED"
    drive_provenance: str = "UNREGISTERED_DRIVE_SOURCE"
    resistance_provenance: str = "UNREGISTERED_RESISTANCE_SOURCE"
    control_tick: int = 0
    feedback_source_tick: int | None = None

    @property
    def resistance_components(self) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        return (
            self.resistance_capability,
            self.resistance_policy,
            self.resistance_context,
            self.resistance_resource,
        )

    @property
    def total_resistance(self) -> Tensor:
        return sum(self.resistance_components)

    @property
    def path_mask(self) -> Tensor:
        return self.topology_mask & self.permission_mask

    @property
    def candidate_path_mask(self) -> Tensor:
        """Paths admitted by controls before current representability is known."""

        mask = (
            self.path_mask
            & (self.drive > 0)
            & (self.readiness > 0)
            & (self.region_multiplier > 0)
        )
        if self.breakdown_mask is not None:
            mask = mask & ~self.breakdown_mask.unsqueeze(-1)
        return mask

    def validate(
        self,
        *,
        batch_size: int,
        num_heads: int,
        query_length: int,
        key_length: int,
        d_model: int,
        dtype: torch.dtype,
        device: torch.device,
        num_relations: int,
        minimum_total_resistance: float,
    ) -> None:
        typed_minimum = torch.as_tensor(
            minimum_total_resistance, dtype=dtype, device=device
        )
        if not bool(torch.isfinite(typed_minimum).item()) or not bool(
            (typed_minimum > 0).item()
        ):
            raise ValueError(
                "minimum_total_resistance must be representably positive "
                "in the input dtype"
            )
        edge_shape = (batch_size, num_heads, query_length, key_length)
        floating_edges = {
            "drive": self.drive,
            "resistance_capability": self.resistance_capability,
            "resistance_policy": self.resistance_policy,
            "resistance_context": self.resistance_context,
            "resistance_resource": self.resistance_resource,
            "readiness": self.readiness,
            "region_multiplier": self.region_multiplier,
        }
        for name, value in floating_edges.items():
            if tuple(value.shape) != edge_shape:
                raise ValueError(f"{name} must have shape {edge_shape}, got {tuple(value.shape)}")
            if value.dtype != dtype:
                raise ValueError(f"{name} must use input dtype {dtype}, got {value.dtype}")
            if value.device != device:
                raise ValueError(f"{name} must be on {device}, got {value.device}")
            _require_finite(name, value)
            if bool((value < 0).any().item()):
                raise ValueError(f"{name} must be nonnegative")

        for name, value in {
            "topology_mask": self.topology_mask,
            "permission_mask": self.permission_mask,
        }.items():
            if tuple(value.shape) != edge_shape or value.dtype != torch.bool:
                raise ValueError(f"{name} must be bool with shape {edge_shape}")
            if value.device != device:
                raise ValueError(f"{name} must be on the input device")

        if tuple(self.relation_ids.shape) != edge_shape:
            raise ValueError(f"relation_ids must have shape {edge_shape}")
        if self.relation_ids.device != device:
            raise ValueError("relation_ids must be on the input device")
        if self.relation_ids.dtype not in (torch.int32, torch.int64):
            raise ValueError("relation_ids must use an integer dtype")
        if bool(((self.relation_ids < 0) | (self.relation_ids >= num_relations)).any().item()):
            raise ValueError(f"relation_ids must be in [0, {num_relations})")

        bias_shape = (batch_size, query_length, d_model)
        if tuple(self.bias.shape) != bias_shape:
            raise ValueError(f"bias must have shape {bias_shape}, got {tuple(self.bias.shape)}")
        if self.bias.dtype != dtype or self.bias.device != device:
            raise ValueError("bias must share the input dtype and device")
        _require_finite("bias", self.bias)

        if self.breakdown_mask is not None:
            breakdown_shape = (batch_size, num_heads, query_length)
            if (
                tuple(self.breakdown_mask.shape) != breakdown_shape
                or self.breakdown_mask.dtype != torch.bool
                or self.breakdown_mask.device != device
            ):
                raise ValueError(
                    f"breakdown_mask must be bool on the input device with shape {breakdown_shape}"
                )

        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ValueError("profile_id must be a nonempty string")
        if not isinstance(self.provenance, str) or not self.provenance:
            raise ValueError("provenance must be a nonempty string")
        if not isinstance(self.drive_provenance, str) or not self.drive_provenance:
            raise ValueError("drive_provenance must be a nonempty string")
        if not isinstance(self.resistance_provenance, str) or not self.resistance_provenance:
            raise ValueError("resistance_provenance must be a nonempty string")
        if not isinstance(self.control_tick, int) or isinstance(self.control_tick, bool):
            raise ValueError("control_tick must be an integer")
        if self.control_tick < 0:
            raise ValueError("control_tick must be nonnegative")
        if self.feedback_source_tick is not None:
            if (
                not isinstance(self.feedback_source_tick, int)
                or isinstance(self.feedback_source_tick, bool)
                or self.feedback_source_tick < 0
            ):
                raise ValueError("feedback_source_tick must be a nonnegative integer")
            if self.feedback_source_tick >= self.control_tick:
                raise ValueError(
                    "feedback_source_tick must be earlier than control_tick; "
                    "same-tick verifier feedback is prohibited"
                )

        candidate_path = self.candidate_path_mask
        zero = torch.zeros_like(self.drive)
        effective_total = sum(
            torch.where(candidate_path, component, zero)
            for component in self.resistance_components
        )
        _require_finite("effective total_resistance", effective_total)
        if bool(
            (candidate_path & (effective_total < minimum_total_resistance)).any().item()
        ):
            raise ValueError(
                "effective-path total resistance must be at least "
                f"{minimum_total_resistance}; zero and negative resistance are prohibited"
            )

    @classmethod
    def uniform(
        cls,
        x: Tensor,
        *,
        num_heads: int,
        drive: float = 1.0,
        resistance_capability: float = 0.25,
        resistance_policy: float = 0.25,
        resistance_context: float = 0.25,
        resistance_resource: float = 0.25,
        relation_id: int = 0,
        bias: Tensor | None = None,
        causal: bool = False,
        profile_id: str = "UNREGISTERED_NEURAL_PROXY",
        provenance: str = "UNREGISTERED",
        drive_provenance: str = "UNREGISTERED_DRIVE_SOURCE",
        resistance_provenance: str = "UNREGISTERED_RESISTANCE_SOURCE",
        control_tick: int = 0,
        feedback_source_tick: int | None = None,
    ) -> "CASControl":
        """Create a fully explicit uniform control for examples and tests."""

        if x.ndim != 3:
            raise ValueError("x must have shape [batch, sequence, d_model]")
        batch, sequence, _ = x.shape
        edge_shape = (batch, num_heads, sequence, sequence)

        def full(value: float) -> Tensor:
            return torch.full(edge_shape, value, dtype=x.dtype, device=x.device)

        topology_mask = torch.ones(edge_shape, dtype=torch.bool, device=x.device)
        if causal:
            triangle = torch.ones(
                (sequence, sequence), dtype=torch.bool, device=x.device
            ).tril()
            topology_mask = topology_mask & triangle.view(1, 1, sequence, sequence)

        return cls(
            drive=full(drive),
            resistance_capability=full(resistance_capability),
            resistance_policy=full(resistance_policy),
            resistance_context=full(resistance_context),
            resistance_resource=full(resistance_resource),
            readiness=full(1.0),
            region_multiplier=full(1.0),
            topology_mask=topology_mask,
            permission_mask=torch.ones(edge_shape, dtype=torch.bool, device=x.device),
            relation_ids=torch.full(
                edge_shape, relation_id, dtype=torch.long, device=x.device
            ),
            bias=torch.zeros_like(x) if bias is None else bias,
            profile_id=profile_id,
            provenance=provenance,
            drive_provenance=drive_provenance,
            resistance_provenance=resistance_provenance,
            control_tick=control_tick,
            feedback_source_tick=feedback_source_tick,
        )


@dataclass(frozen=True)
class CASformerConfig:
    d_model: int
    num_heads: int
    num_relations: int = 4
    num_layers: int = 1
    d_ff: int | None = None
    dropout: float = 0.0
    attention_dropout: float = 0.0
    minimum_total_resistance: float = 0.1
    reference_resistance: float = 1.0
    reference_drive: float = 1.0
    initial_beta: float = 1.0
    beta_max: float = 4.0
    initial_cutoff: float = 0.25
    initial_saturation: float = 8.0
    linear_weight_mode: str = "standard"
    minimum_weight_resistance: float = 0.1

    def __post_init__(self) -> None:
        integer_fields = {
            "d_model": self.d_model,
            "num_heads": self.num_heads,
            "num_relations": self.num_relations,
            "num_layers": self.num_layers,
        }
        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in integer_fields.values()
        ):
            raise ValueError("model dimensions, relation count, and layer count must be integers")
        finite_fields = {
            "dropout": self.dropout,
            "attention_dropout": self.attention_dropout,
            "minimum_total_resistance": self.minimum_total_resistance,
            "reference_resistance": self.reference_resistance,
            "reference_drive": self.reference_drive,
            "initial_beta": self.initial_beta,
            "beta_max": self.beta_max,
            "initial_cutoff": self.initial_cutoff,
            "initial_saturation": self.initial_saturation,
            "minimum_weight_resistance": self.minimum_weight_resistance,
        }
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in finite_fields.values()
        ):
            raise ValueError("all scalar configuration values must be finite numbers")
        if self.d_model <= 0 or self.num_heads <= 0:
            raise ValueError("d_model and num_heads must be positive")
        if self.d_model % self.num_heads != 0:
            raise ValueError("d_model must be divisible by num_heads")
        if self.num_relations <= 0 or self.num_layers <= 0:
            raise ValueError("num_relations and num_layers must be positive")
        if self.d_ff is not None and (
            not isinstance(self.d_ff, int)
            or isinstance(self.d_ff, bool)
            or self.d_ff <= 0
        ):
            raise ValueError("d_ff must be a positive integer when supplied")
        if self.dropout != 0 or self.attention_dropout != 0:
            raise ValueError("CASformer v0.1 requires dropout and attention_dropout to be zero")
        if self.minimum_total_resistance <= 0:
            raise ValueError("minimum_total_resistance must be positive")
        if self.reference_resistance <= 0 or self.reference_drive <= 0:
            raise ValueError("reference resistance and drive must be positive")
        if not 0 < self.initial_beta < self.beta_max:
            raise ValueError("initial_beta must be strictly between zero and beta_max")
        if self.initial_cutoff <= 0 or self.initial_saturation <= self.initial_cutoff:
            raise ValueError("initial_saturation must be greater than a positive cutoff")
        if self.linear_weight_mode not in {"standard", "differential_conductance"}:
            raise ValueError(
                "linear_weight_mode must be 'standard' or 'differential_conductance'"
            )
        if self.minimum_weight_resistance <= 0:
            raise ValueError("minimum_weight_resistance must be positive")

    @property
    def head_dim(self) -> int:
        return self.d_model // self.num_heads

    @property
    def feed_forward_dim(self) -> int:
        return self.d_ff if self.d_ff is not None else 4 * self.d_model


@dataclass(frozen=True)
class OhmicAttentionTelemetry:
    semantic_scores: Tensor
    semantic_allocation: Tensor
    total_resistance: Tensor
    conductance: Tensor
    current: Tensor
    attention: Tensor
    total_current: Tensor
    diagnostic_features: Tensor
    effective_path_mask: Tensor


@dataclass(frozen=True)
class CASformerTelemetry:
    attention: OhmicAttentionTelemetry
    beta: Tensor
    cjt_preactivation: Tensor
    cjt_gate: Tensor
    cjt_candidate: Tensor
    cjt_effect: Tensor
    operating_region: Tensor


def _make_linear(
    config: CASformerConfig,
    in_features: int,
    out_features: int,
    *,
    bias: bool,
) -> nn.Module:
    if config.linear_weight_mode == "differential_conductance":
        return DifferentialConductanceLinear(
            in_features,
            out_features,
            minimum_resistance=config.minimum_weight_resistance,
            bias=bias,
        )
    return nn.Linear(in_features, out_features, bias=bias)


def _headwise_masked_linear(
    module: nn.Module,
    value: Tensor,
    blocked: Tensor,
    *,
    num_heads: int,
) -> Tensor:
    """Project each output-head slice without evaluating blocked queries."""

    weight = getattr(module, "weight", None)
    if weight is None:
        weight = getattr(module, "effective_weight")
    if weight.shape[0] % num_heads != 0:
        raise ValueError("linear output width must be divisible by num_heads")
    outputs_per_head = weight.shape[0] // num_heads
    head_weight = weight.view(num_heads, outputs_per_head, weight.shape[1])
    expanded = value.unsqueeze(1).expand(-1, num_heads, -1, -1)
    safe_value = torch.where(blocked.unsqueeze(-1), torch.zeros_like(expanded), expanded)
    projected = torch.einsum("bhqd,hed->bhqe", safe_value, head_weight)
    module_bias = getattr(module, "bias", None)
    if module_bias is not None:
        head_bias = module_bias.view(num_heads, outputs_per_head)
        projected = projected + torch.where(
            blocked.unsqueeze(-1),
            torch.zeros_like(projected),
            head_bias.view(1, num_heads, 1, outputs_per_head),
        )
    return projected


class OhmicMultiheadAttention(nn.Module):
    """Self-attention whose positive routing coefficient is CAS conductance."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.config = config
        self.q_proj = _make_linear(config, config.d_model, config.d_model, bias=False)
        self.k_proj = _make_linear(config, config.d_model, config.d_model, bias=False)
        self.v_proj = _make_linear(config, config.d_model, config.d_model, bias=False)
        self.out_proj = _make_linear(config, config.d_model, config.d_model, bias=False)
        if config.linear_weight_mode == "standard":
            self.relation_operators = nn.Parameter(
                torch.empty(
                    config.num_relations,
                    config.num_heads,
                    config.head_dim,
                    config.head_dim,
                )
            )
            self.relation_operator_modules = None
        else:
            self.register_parameter("relation_operators", None)
            self.relation_operator_modules = nn.ModuleList(
                nn.ModuleList(
                    DifferentialConductanceLinear(
                        config.head_dim,
                        config.head_dim,
                        minimum_resistance=config.minimum_weight_resistance,
                        bias=False,
                    )
                    for _ in range(config.num_heads)
                )
                for _ in range(config.num_relations)
            )
        self.attention_dropout = nn.Dropout(config.attention_dropout)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for projection in (self.q_proj, self.k_proj, self.v_proj, self.out_proj):
            if isinstance(projection, nn.Linear):
                nn.init.xavier_uniform_(projection.weight)
        if self.relation_operators is not None:
            with torch.no_grad():
                self.relation_operators.zero_()
                identity = torch.eye(self.config.head_dim)
                for relation in range(self.config.num_relations):
                    for head in range(self.config.num_heads):
                        operator = identity.clone()
                        if self.config.head_dim > 1 and relation > 0:
                            shift = 1 + ((relation - 1) % (self.config.head_dim - 1))
                            operator = operator + (0.025 * relation) * torch.roll(
                                identity, shifts=shift, dims=1
                            )
                        self.relation_operators[relation, head].copy_(operator)

    def relation_operator(self, relation: int) -> Tensor:
        if self.relation_operators is not None:
            return self.relation_operators[relation]
        assert self.relation_operator_modules is not None
        return torch.stack(
            [
                module.effective_weight.transpose(0, 1)
                for module in self.relation_operator_modules[relation]
            ],
            dim=0,
        )

    def _split_heads(self, value: Tensor) -> Tensor:
        batch, sequence, _ = value.shape
        return (
            value.view(batch, sequence, self.config.num_heads, self.config.head_dim)
            .transpose(1, 2)
            .contiguous()
        )

    def merge_heads(self, value: Tensor) -> Tensor:
        batch, heads, sequence, head_dim = value.shape
        if heads != self.config.num_heads or head_dim != self.config.head_dim:
            raise ValueError("head tensor does not match the configured head geometry")
        return value.transpose(1, 2).contiguous().view(batch, sequence, self.config.d_model)

    def forward(
        self, x: Tensor, control: CASControl
    ) -> tuple[Tensor, OhmicAttentionTelemetry]:
        if x.ndim != 3:
            raise ValueError("x must have shape [batch, sequence, d_model]")
        batch, sequence, width = x.shape
        if width != self.config.d_model:
            raise ValueError(f"x last dimension must be {self.config.d_model}")
        if not x.is_floating_point():
            raise ValueError("x must be a floating-point tensor")
        _require_finite("x", x)
        for name, scalar in {
            "reference_drive": self.config.reference_drive,
            "reference_resistance": self.config.reference_resistance,
        }.items():
            typed_scalar = torch.as_tensor(scalar, dtype=x.dtype, device=x.device)
            if not bool(torch.isfinite(typed_scalar).item()) or not bool(
                (typed_scalar > 0).item()
            ):
                raise ValueError(
                    f"{name} must be representably positive in the input dtype"
                )

        control.validate(
            batch_size=batch,
            num_heads=self.config.num_heads,
            query_length=sequence,
            key_length=sequence,
            d_model=self.config.d_model,
            dtype=x.dtype,
            device=x.device,
            num_relations=self.config.num_relations,
            minimum_total_resistance=self.config.minimum_total_resistance,
        )

        q = self._split_heads(self.q_proj(x))
        k = self._split_heads(self.k_proj(x))
        value = self._split_heads(self.v_proj(x))
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.config.head_dim)
        _require_finite("semantic_scores", scores)
        _require_finite("projected_value", value)

        candidate_path = control.candidate_path_mask
        zero_edge = torch.zeros_like(scores)
        unit_edge = torch.ones_like(scores)
        total_resistance = sum(
            torch.where(candidate_path, component, zero_edge)
            for component in control.resistance_components
        )
        safe_total_resistance = torch.where(
            candidate_path,
            total_resistance,
            torch.full_like(total_resistance, self.config.reference_resistance),
        )
        conductance = torch.where(
            candidate_path,
            self.config.reference_resistance / safe_total_resistance,
            zero_edge,
        )
        if bool(
            (
                candidate_path
                & (~torch.isfinite(conductance) | (conductance <= 0))
            ).any().item()
        ):
            raise ValueError(
                "candidate-path relative conductance must be finite and "
                "representably positive"
            )

        safe_drive = torch.where(
            candidate_path,
            control.drive,
            torch.full_like(control.drive, self.config.reference_drive),
        )
        safe_readiness = torch.where(candidate_path, control.readiness, unit_edge)
        safe_region = torch.where(candidate_path, control.region_multiplier, unit_edge)
        route_log = (
            torch.log(safe_drive)
            - math.log(self.config.reference_drive)
            + torch.log(safe_readiness)
            + torch.log(safe_region)
            + math.log(self.config.reference_resistance)
            - torch.log(safe_total_resistance)
        )
        current = torch.where(
            candidate_path,
            torch.exp(route_log),
            zero_edge,
        )
        _require_finite("current", current)
        valid_path = candidate_path & (current > 0)
        current = torch.where(valid_path, current, zero_edge)
        total_resistance = torch.where(valid_path, total_resistance, zero_edge)
        conductance = torch.where(valid_path, conductance, zero_edge)
        safe_total_resistance = torch.where(
            valid_path,
            total_resistance,
            torch.full_like(total_resistance, self.config.reference_resistance),
        )
        masked_drive = torch.where(valid_path, control.drive, zero_edge)
        total_current = current.sum(dim=-1)
        _require_finite("total_current", total_current)

        negative_infinity = torch.full_like(scores, -torch.inf)
        semantic_logits = torch.where(valid_path, scores, negative_infinity)
        semantic_row_max = semantic_logits.amax(dim=-1, keepdim=True)
        safe_semantic_max = torch.where(
            torch.isfinite(semantic_row_max),
            semantic_row_max,
            torch.zeros_like(semantic_row_max),
        )
        semantic_numerator = torch.where(
            valid_path,
            torch.exp(semantic_logits - safe_semantic_max),
            torch.zeros_like(semantic_logits),
        )
        semantic_denominator = semantic_numerator.sum(dim=-1, keepdim=True)
        semantic_allocation = torch.where(
            semantic_denominator > 0,
            semantic_numerator
            / semantic_denominator.clamp_min(torch.finfo(x.dtype).tiny),
            torch.zeros_like(semantic_numerator),
        )

        current_logits = torch.where(valid_path, scores + route_log, negative_infinity)
        row_max = current_logits.amax(dim=-1, keepdim=True)
        safe_row_max = torch.where(torch.isfinite(row_max), row_max, torch.zeros_like(row_max))
        relative_conductance = torch.where(
            valid_path,
            torch.exp(current_logits - safe_row_max),
            torch.zeros_like(current_logits),
        )
        denominator = relative_conductance.sum(dim=-1, keepdim=True)
        attention = torch.where(
            denominator > 0,
            relative_conductance / denominator.clamp_min(torch.finfo(x.dtype).tiny),
            torch.zeros_like(relative_conductance),
        )
        routed_attention = self.attention_dropout(attention)

        head_output = torch.zeros_like(q)
        for relation in range(self.config.num_relations):
            relation_path = valid_path & (control.relation_ids == relation)
            relation_attention = torch.where(
                relation_path, routed_attention, torch.zeros_like(routed_attention)
            )
            if not bool((relation_attention > 0).any().item()):
                continue
            selected_value = torch.einsum(
                "bhqk,bhkd->bhqd", relation_attention, value
            )
            _require_finite(f"selected_value[{relation}]", selected_value)
            operator = self.relation_operator(relation)
            _require_finite(f"relation_operator[{relation}]", operator)
            relation_output = torch.einsum(
                "bhqd,hde->bhqe", selected_value, operator
            )
            _require_finite(f"relation_output[{relation}]", relation_output)
            head_output = head_output + relation_output
        _require_finite("relation_routed_output", head_output)

        edge_features = torch.stack(
            (
                _stable_log1p_ratio(masked_drive, self.config.reference_drive),
                *(
                    _stable_log1p_ratio(
                        torch.where(valid_path, component, zero_edge),
                        self.config.reference_resistance,
                    )
                    for component in control.resistance_components
                ),
            ),
            dim=-1,
        )
        diagnostic_features = torch.einsum("bhqk,bhqkf->bhqf", attention, edge_features)
        _require_finite("diagnostic_features", diagnostic_features)
        telemetry = OhmicAttentionTelemetry(
            semantic_scores=torch.where(valid_path, scores, torch.zeros_like(scores)),
            semantic_allocation=semantic_allocation,
            total_resistance=torch.where(
                valid_path, total_resistance, torch.zeros_like(total_resistance)
            ),
            conductance=conductance,
            current=current,
            attention=attention,
            total_current=total_current,
            diagnostic_features=diagnostic_features,
            effective_path_mask=valid_path,
        )
        return head_output, telemetry


class CJTRegionGate(nn.Module):
    """Bounded flow-region gate kept separate from CJT Cause/Effect beta."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.config = config
        self.raw_beta = nn.Parameter(
            torch.full(
                (config.num_heads,), _logit(config.initial_beta / config.beta_max)
            )
        )
        self.raw_cutoff = nn.Parameter(
            torch.full((config.num_heads,), _inverse_softplus(config.initial_cutoff))
        )
        initial_span = config.initial_saturation - config.initial_cutoff
        self.raw_span = nn.Parameter(
            torch.full((config.num_heads,), _inverse_softplus(initial_span))
        )
        self.bias_projection = _make_linear(
            config, config.d_model, config.num_heads, bias=False
        )
        self.diagnostic_projection = _make_linear(
            config,
            len(DIAGNOSTIC_FEATURE_NAMES),
            config.num_heads,
            bias=True,
        )
        if isinstance(self.bias_projection, nn.Linear):
            nn.init.xavier_uniform_(self.bias_projection.weight, gain=0.1)
        if isinstance(self.diagnostic_projection, nn.Linear):
            nn.init.xavier_uniform_(self.diagnostic_projection.weight, gain=0.1)
        assert self.diagnostic_projection.bias is not None
        nn.init.zeros_(self.diagnostic_projection.bias)

    @property
    def beta(self) -> Tensor:
        typed_maximum = torch.as_tensor(
            self.config.beta_max,
            dtype=self.raw_beta.dtype,
            device=self.raw_beta.device,
        )
        typed_initial = torch.as_tensor(
            self.config.initial_beta,
            dtype=self.raw_beta.dtype,
            device=self.raw_beta.device,
        )
        if not bool(torch.isfinite(typed_maximum).item()) or not bool(
            (typed_maximum > 0).item()
        ):
            raise ValueError("beta_max must be representably positive in the module dtype")
        if (
            not bool(torch.isfinite(typed_initial).item())
            or not bool((typed_initial > 0).item())
            or not bool((typed_initial < typed_maximum).item())
        ):
            raise ValueError(
                "initial_beta must be representably strictly between zero and "
                "beta_max in the module dtype"
            )
        lower = torch.nextafter(
            torch.zeros_like(typed_maximum), torch.full_like(typed_maximum, torch.inf)
        )
        upper = torch.nextafter(typed_maximum, torch.zeros_like(typed_maximum))
        if not bool((upper >= lower).item()):
            raise ValueError(
                "beta_max leaves no representable strictly interior beta in the "
                "module dtype"
            )
        fraction = torch.sigmoid(self.raw_beta)
        beta = (typed_maximum * fraction).clamp(min=lower, max=upper)
        _require_finite("cjt_beta", beta)
        if not bool(((beta > 0) & (beta < typed_maximum)).all().item()):
            raise ValueError("cjt_beta must remain strictly inside its runtime bounds")
        return beta

    @property
    def cutoff(self) -> Tensor:
        value = F.softplus(self.raw_cutoff)
        return value.clamp_min(torch.finfo(value.dtype).eps)

    @property
    def saturation(self) -> Tensor:
        cutoff = self.cutoff
        learned_span = F.softplus(self.raw_span)
        minimum_span = torch.finfo(learned_span.dtype).eps * torch.maximum(
            torch.ones_like(cutoff), cutoff.detach().abs()
        )
        return cutoff + torch.maximum(learned_span, minimum_span)

    def forward(
        self,
        total_current: Tensor,
        bias: Tensor,
        diagnostic_features: Tensor,
        breakdown_mask: Tensor | None = None,
    ) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        if (
            bias.ndim != 3
            or bias.shape[-1] != self.config.d_model
            or not bias.is_floating_point()
        ):
            raise ValueError(
                f"bias must be floating point with shape [batch, query, {self.config.d_model}]"
            )
        expected_current = (bias.shape[0], self.config.num_heads, bias.shape[1])
        if tuple(total_current.shape) != expected_current:
            raise ValueError(f"total_current must have shape {expected_current}")
        expected_diagnostics = expected_current + (len(DIAGNOSTIC_FEATURE_NAMES),)
        if tuple(diagnostic_features.shape) != expected_diagnostics:
            raise ValueError(f"diagnostic_features must have shape {expected_diagnostics}")
        for name, value in {
            "total_current": total_current,
            "bias": bias,
            "diagnostic_features": diagnostic_features,
        }.items():
            if not value.is_floating_point():
                raise ValueError(f"{name} must be floating point")
            if value.dtype != bias.dtype or value.device != bias.device:
                raise ValueError("CJT gate tensors must share a dtype and device")
            _require_finite(name, value)
        if bool((total_current < 0).any().item()):
            raise ValueError("total_current must be nonnegative")
        if breakdown_mask is not None and (
            tuple(breakdown_mask.shape) != expected_current
            or breakdown_mask.dtype != torch.bool
            or breakdown_mask.device != bias.device
        ):
            raise ValueError(
                f"breakdown_mask must be bool on the input device with shape {expected_current}"
            )

        beta = self.beta
        cutoff = self.cutoff.view(1, -1, 1)
        saturation = self.saturation.view(1, -1, 1)
        _require_finite("cjt_beta", beta)
        _require_finite("cjt_cutoff", cutoff)
        _require_finite("cjt_saturation", saturation)
        if not bool((saturation > cutoff).all().item()):
            raise ValueError("cjt_saturation must remain strictly above cjt_cutoff")
        diagnostic_weights = getattr(self.diagnostic_projection, "weight", None)
        if diagnostic_weights is None:
            diagnostic_weights = self.diagnostic_projection.effective_weight
        diagnostic_projection_bias = self.diagnostic_projection.bias
        assert diagnostic_projection_bias is not None
        blocked_query = total_current == 0
        if breakdown_mask is not None:
            blocked_query = blocked_query | breakdown_mask
        if not bool(blocked_query.any().item()):
            effective_current = total_current
            bias_signal = self.bias_projection(bias).transpose(1, 2)
            effective_diagnostics = diagnostic_features
            diagnostic_bias = diagnostic_projection_bias.view(1, -1, 1)
        else:
            effective_current = torch.where(
                blocked_query, torch.zeros_like(total_current), total_current
            )
            bias_signal = _headwise_masked_linear(
                self.bias_projection,
                bias,
                blocked_query,
                num_heads=self.config.num_heads,
            ).squeeze(-1)
            effective_diagnostics = torch.where(
                blocked_query.unsqueeze(-1),
                torch.zeros_like(diagnostic_features),
                diagnostic_features,
            )
            diagnostic_bias = torch.where(
                blocked_query,
                torch.zeros_like(total_current),
                diagnostic_projection_bias.view(1, -1, 1),
            )
        diagnostic_signal = torch.einsum(
            "bhqf,hf->bhq", effective_diagnostics, diagnostic_weights
        ) + diagnostic_bias
        preactivation = effective_current + bias_signal + diagnostic_signal
        _require_finite("cjt_preactivation", preactivation)

        normalized_region = (preactivation - cutoff) / (saturation - cutoff)
        bounded_region = normalized_region.clamp(min=0.0, max=1.0)
        gate = bounded_region.square() * (3.0 - 2.0 * bounded_region)
        has_flow = effective_current > 0
        gate = torch.where(has_flow, gate, torch.zeros_like(gate))

        region = torch.full(
            total_current.shape,
            int(OperatingRegion.CUTOFF),
            dtype=torch.int64,
            device=total_current.device,
        )
        region = torch.where(
            has_flow & (preactivation > cutoff),
            torch.full_like(region, int(OperatingRegion.ACTIVE)),
            region,
        )
        region = torch.where(
            has_flow & (preactivation >= saturation),
            torch.full_like(region, int(OperatingRegion.SATURATION)),
            region,
        )

        if breakdown_mask is not None:
            gate = torch.where(breakdown_mask, torch.zeros_like(gate), gate)
            region = torch.where(
                breakdown_mask,
                torch.full_like(region, int(OperatingRegion.BREAKDOWN)),
                region,
            )

        return gate, preactivation, region, beta


class CASformerBlock(nn.Module):
    """Pre-LayerNorm Transformer block with an Ohmic attention/CJT socket."""

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.config = config
        self.input_norm = nn.LayerNorm(config.d_model)
        self.attention = OhmicMultiheadAttention(config)
        self.cjt_gate = CJTRegionGate(config)
        self.cjt_effect_bias = _make_linear(
            config, config.d_model, config.d_model, bias=False
        )
        if isinstance(self.cjt_effect_bias, nn.Linear):
            nn.init.xavier_uniform_(self.cjt_effect_bias.weight, gain=0.1)
        self.output_dropout = nn.Dropout(config.dropout)
        self.feed_forward_norm = nn.LayerNorm(config.d_model)
        self.feed_forward = nn.Sequential(
            _make_linear(
                config, config.d_model, config.feed_forward_dim, bias=True
            ),
            nn.GELU(),
            nn.Dropout(config.dropout),
            _make_linear(
                config, config.feed_forward_dim, config.d_model, bias=True
            ),
            nn.Dropout(config.dropout),
        )

    def forward(
        self, x: Tensor, control: CASControl
    ) -> tuple[Tensor, CASformerTelemetry]:
        normalized = self.input_norm(x)
        head_output, attention_telemetry = self.attention(normalized, control)
        gate, preactivation, region, beta = self.cjt_gate(
            attention_telemetry.total_current,
            control.bias,
            attention_telemetry.diagnostic_features,
            control.breakdown_mask,
        )
        zero_effect = gate == 0
        if not bool(zero_effect.any().item()):
            bias_heads = self.attention._split_heads(self.cjt_effect_bias(control.bias))
        else:
            bias_heads = _headwise_masked_linear(
                self.cjt_effect_bias,
                control.bias,
                zero_effect,
                num_heads=self.config.num_heads,
            )
        beta_heads = beta.view(1, self.config.num_heads, 1, 1)
        cjt_effect = torch.tanh(
            bias_heads + beta_heads * gate.unsqueeze(-1) * head_output
        ) - torch.tanh(bias_heads)
        _require_finite("cjt_effect", cjt_effect)
        merged = self.attention.merge_heads(cjt_effect)
        projected_effect = self.attention.out_proj(merged)
        _require_finite("projected_cjt_effect", projected_effect)
        x = x + self.output_dropout(projected_effect)
        _require_finite("attention_residual", x)
        feed_forward_effect = self.feed_forward(self.feed_forward_norm(x))
        _require_finite("feed_forward_effect", feed_forward_effect)
        x = x + feed_forward_effect
        _require_finite("block_output", x)
        telemetry = CASformerTelemetry(
            attention=attention_telemetry,
            beta=beta,
            cjt_preactivation=preactivation,
            cjt_gate=gate,
            cjt_candidate=head_output,
            cjt_effect=cjt_effect,
            operating_region=region,
        )
        return x, telemetry


class CASformerEncoder(nn.Module):
    """A stack of independent CASformer blocks.

    Position information is intentionally caller-supplied.  Without position
    features, this encoder remains permutation equivariant like a graph
    Transformer.  One ``CASControl`` may be reused across layers, or a distinct
    control may be supplied for every layer.
    """

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.config = config
        self.layers = nn.ModuleList(
            CASformerBlock(config) for _ in range(config.num_layers)
        )
        self.final_norm = nn.LayerNorm(config.d_model)

    def forward(
        self, x: Tensor, controls: CASControl | Sequence[CASControl]
    ) -> tuple[Tensor, tuple[CASformerTelemetry, ...]]:
        if isinstance(controls, CASControl):
            layer_controls = (controls,) * len(self.layers)
        else:
            layer_controls = tuple(controls)
            if len(layer_controls) != len(self.layers):
                raise ValueError(
                    f"expected {len(self.layers)} controls, got {len(layer_controls)}"
                )

        telemetry: list[CASformerTelemetry] = []
        for layer, control in zip(self.layers, layer_controls, strict=True):
            x, layer_telemetry = layer(x, control)
            telemetry.append(layer_telemetry)
        return self.final_norm(x), tuple(telemetry)


class CASformerLanguageModel(nn.Module):
    """Small decoder-style language-model wrapper around ``CASformerEncoder``.

    The model is a randomly initialized executable v0.1 research starting
    point.  It is not a complete reasoning transistor, a pretrained language
    cortex, or evidence of language ability.  Callers must supply causal
    topology masks through every layer control.
    """

    def __init__(
        self,
        config: CASformerConfig,
        *,
        vocab_size: int,
        max_sequence_length: int,
        tie_embeddings: bool = True,
    ) -> None:
        super().__init__()
        if vocab_size <= 1 or max_sequence_length <= 0:
            raise ValueError("vocab_size must exceed one and max_sequence_length must be positive")
        self.config = config
        self.vocab_size = vocab_size
        self.max_sequence_length = max_sequence_length
        self.token_embedding = nn.Embedding(vocab_size, config.d_model)
        self.position_embedding = nn.Embedding(max_sequence_length, config.d_model)
        self.encoder = CASformerEncoder(config)
        if config.linear_weight_mode == "differential_conductance":
            if tie_embeddings:
                raise ValueError(
                    "tie_embeddings must be false with differential_conductance weights"
                )
            self.lm_head = DifferentialConductanceLinear(
                config.d_model,
                vocab_size,
                minimum_resistance=config.minimum_weight_resistance,
                bias=False,
            )
        else:
            self.lm_head = nn.Linear(config.d_model, vocab_size, bias=False)
        if tie_embeddings and isinstance(self.lm_head, nn.Linear):
            self.lm_head.weight = self.token_embedding.weight

    def forward(
        self,
        input_ids: Tensor,
        controls: CASControl | Sequence[CASControl],
    ) -> tuple[Tensor, tuple[CASformerTelemetry, ...]]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        if input_ids.dtype not in (torch.int32, torch.int64):
            raise ValueError("input_ids must use an integer dtype")
        if input_ids.shape[1] > self.max_sequence_length:
            raise ValueError("input sequence exceeds max_sequence_length")
        if bool(((input_ids < 0) | (input_ids >= self.vocab_size)).any().item()):
            raise ValueError("input_ids contain an out-of-range token")
        control_sequence = (
            (controls,) if isinstance(controls, CASControl) else tuple(controls)
        )
        future = torch.ones(
            (input_ids.shape[1], input_ids.shape[1]),
            dtype=torch.bool,
            device=input_ids.device,
        ).triu(diagonal=1)
        for control in control_sequence:
            if bool((control.topology_mask & future.view(1, 1, *future.shape)).any().item()):
                raise ValueError(
                    "CASformerLanguageModel requires a causal topology_mask in every layer"
                )
        positions = torch.arange(input_ids.shape[1], device=input_ids.device)
        hidden = self.token_embedding(input_ids) + self.position_embedding(positions)[None, :, :]
        hidden, telemetry = self.encoder(hidden, controls)
        return self.lm_head(hidden), telemetry


class DifferentialConductanceLinear(nn.Module):
    """Signed linear map made from two strictly positive conductance paths."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        *,
        minimum_resistance: float = 0.1,
        bias: bool = True,
    ) -> None:
        super().__init__()
        if in_features <= 0 or out_features <= 0:
            raise ValueError("in_features and out_features must be positive")
        if minimum_resistance <= 0:
            raise ValueError("minimum_resistance must be positive")
        if not math.isfinite(minimum_resistance):
            raise ValueError("minimum_resistance must be finite")
        self.in_features = in_features
        self.out_features = out_features
        self.minimum_resistance = minimum_resistance
        self.raw_positive_resistance = nn.Parameter(
            torch.empty(out_features, in_features)
        )
        self.raw_negative_resistance = nn.Parameter(
            torch.empty(out_features, in_features)
        )
        self.bias = nn.Parameter(torch.empty(out_features)) if bias else None
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.normal_(self.raw_positive_resistance, mean=1.0, std=0.1)
        nn.init.normal_(self.raw_negative_resistance, mean=1.0, std=0.1)
        if self.bias is not None:
            bound = 1 / math.sqrt(self.in_features)
            nn.init.uniform_(self.bias, -bound, bound)

    def _runtime_resistance_floor(self) -> tuple[Tensor, Tensor]:
        floor = torch.as_tensor(
            self.minimum_resistance,
            dtype=self.raw_positive_resistance.dtype,
            device=self.raw_positive_resistance.device,
        )
        if not bool(torch.isfinite(floor).item()) or not bool((floor > 0).item()):
            raise ValueError(
                "minimum_resistance must be representably positive in the module dtype"
            )
        next_floor = torch.nextafter(floor, torch.full_like(floor, torch.inf))
        if not bool(torch.isfinite(next_floor).item()):
            raise ValueError(
                "minimum_resistance leaves no finite larger value in the module dtype"
            )
        smallest_conductance = next_floor.reciprocal()
        if not bool(torch.isfinite(smallest_conductance).item()) or not bool(
            (smallest_conductance > 0).item()
        ):
            raise ValueError(
                "minimum_resistance is too small for a finite positive "
                "conductance in the module dtype"
            )
        return floor, next_floor - floor

    def _rail_resistance(self, raw_resistance: Tensor, *, name: str) -> Tensor:
        floor, minimum_offset = self._runtime_resistance_floor()
        offset = torch.maximum(F.softplus(raw_resistance), minimum_offset)
        resistance = floor + offset
        if not bool(torch.isfinite(resistance).all().item()):
            raise ValueError(f"{name} resistance must remain finite")
        return resistance

    @property
    def positive_resistance(self) -> Tensor:
        return self._rail_resistance(
            self.raw_positive_resistance, name="positive rail"
        )

    @property
    def negative_resistance(self) -> Tensor:
        return self._rail_resistance(
            self.raw_negative_resistance, name="negative rail"
        )

    @property
    def effective_weight(self) -> Tensor:
        return self.positive_resistance.reciprocal() - self.negative_resistance.reciprocal()

    @property
    def positive_conductance(self) -> Tensor:
        return self.positive_resistance.reciprocal()

    @property
    def negative_conductance(self) -> Tensor:
        return self.negative_resistance.reciprocal()

    def gauge_ratio(self, *, floor: float = 1e-12) -> Tensor:
        """Report common rail magnitude relative to useful signed magnitude."""

        if floor <= 0:
            raise ValueError("floor must be positive")
        common = (self.positive_conductance + self.negative_conductance).mean()
        useful = self.effective_weight.abs().mean().clamp_min(floor)
        return common / useful

    def common_mode_penalty(self) -> Tensor:
        """Penalty available to stop both conductance rails growing together."""

        return (self.positive_conductance + self.negative_conductance).mean()

    def forward(self, value: Tensor) -> Tensor:
        return F.linear(value, self.effective_weight, self.bias)
