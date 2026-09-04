"""Optional learned control-field adapter for CASformer research."""

from __future__ import annotations

import math

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from .core import CASControl, CASformerConfig


def _inverse_softplus(value: float) -> float:
    return value + math.log(-math.expm1(-value))


class _PairwisePositiveField(nn.Module):
    def __init__(
        self,
        d_model: int,
        num_heads: int,
        *,
        floor: float,
        initial_value: float,
    ) -> None:
        super().__init__()
        if not math.isfinite(floor) or not math.isfinite(initial_value):
            raise ValueError("floor and initial_value must be finite")
        if floor < 0 or initial_value <= floor:
            raise ValueError("initial_value must be greater than a nonnegative floor")
        self.floor = floor
        self.query = nn.Linear(d_model, num_heads)
        self.key = nn.Linear(d_model, num_heads)
        nn.init.normal_(self.query.weight, mean=0.0, std=0.01)
        nn.init.normal_(self.key.weight, mean=0.0, std=0.01)
        half_bias = 0.5 * _inverse_softplus(initial_value - floor)
        nn.init.constant_(self.query.bias, half_bias)
        nn.init.constant_(self.key.bias, half_bias)

    def forward(self, x: Tensor) -> Tensor:
        query = self.query(x).transpose(1, 2).unsqueeze(-1)
        key = self.key(x).transpose(1, 2).unsqueeze(-2)
        return self.floor + F.softplus(query + key)


class LearnedCASControlAdapter(nn.Module):
    """Predict positive Drive and soft resistance fields from hidden states.

    Policy resistance and both hard masks remain caller-owned.  Policy
    resistance is detached on purpose so gradient descent cannot weaken a
    policy boundary.  This adapter is a convenience for experiments; because
    it predicts Drive and resistance from one hidden state, it does not prove
    that those quantities are independently identified or calibrated.
    """

    def __init__(self, config: CASformerConfig) -> None:
        super().__init__()
        self.config = config
        component_floor = config.minimum_total_resistance / 3
        self.drive = _PairwisePositiveField(
            config.d_model,
            config.num_heads,
            floor=0.0,
            initial_value=config.reference_drive,
        )
        self.capability_resistance = _PairwisePositiveField(
            config.d_model,
            config.num_heads,
            floor=component_floor,
            initial_value=max(config.reference_resistance / 3, component_floor * 2),
        )
        self.context_resistance = _PairwisePositiveField(
            config.d_model,
            config.num_heads,
            floor=component_floor,
            initial_value=max(config.reference_resistance / 3, component_floor * 2),
        )
        self.resource_resistance = _PairwisePositiveField(
            config.d_model,
            config.num_heads,
            floor=component_floor,
            initial_value=max(config.reference_resistance / 3, component_floor * 2),
        )

    def forward(
        self,
        x: Tensor,
        *,
        bias: Tensor,
        policy_resistance: Tensor,
        readiness: Tensor,
        region_multiplier: Tensor,
        topology_mask: Tensor,
        permission_mask: Tensor,
        relation_ids: Tensor,
        breakdown_mask: Tensor | None = None,
        profile_id: str = "LEARNED_UNREGISTERED_NEURAL_PROXY",
        provenance: str = "LEARNED_CAS_CONTROL_ADAPTER",
        drive_provenance: str = "LEARNED_CAS_CONTROL_ADAPTER:DRIVE_CHANNEL",
        resistance_provenance: str = "LEARNED_CAS_CONTROL_ADAPTER:RESISTANCE_CHANNELS",
        control_tick: int = 0,
        feedback_source_tick: int | None = None,
    ) -> CASControl:
        if x.ndim != 3 or x.shape[-1] != self.config.d_model:
            raise ValueError(
                f"x must have shape [batch, sequence, {self.config.d_model}]"
            )
        return CASControl(
            drive=self.drive(x),
            resistance_capability=self.capability_resistance(x),
            resistance_policy=policy_resistance.detach(),
            resistance_context=self.context_resistance(x),
            resistance_resource=self.resource_resistance(x),
            readiness=readiness,
            region_multiplier=region_multiplier,
            topology_mask=topology_mask,
            permission_mask=permission_mask,
            relation_ids=relation_ids,
            bias=bias,
            breakdown_mask=breakdown_mask,
            profile_id=profile_id,
            provenance=provenance,
            drive_provenance=drive_provenance,
            resistance_provenance=resistance_provenance,
            control_tick=control_tick,
            feedback_source_tick=feedback_source_tick,
        )
