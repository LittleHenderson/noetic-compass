"""Explicit twins and baselines used to prevent CASformer overclaiming."""

from __future__ import annotations

import math

import torch
from torch import Tensor, nn


def _validate_simplex(allocation: Tensor) -> None:
    if allocation.ndim != 1 or not allocation.is_floating_point():
        raise ValueError("allocation must be a floating-point vector")
    if not bool(torch.isfinite(allocation).all().item()):
        raise ValueError("allocation must be finite")
    if bool((allocation < 0).any().item()):
        raise ValueError("allocation must be nonnegative")
    unit = torch.ones((), dtype=allocation.dtype, device=allocation.device)
    if not bool(torch.isclose(allocation.sum(), unit, atol=1e-7, rtol=1e-6).item()):
        raise ValueError("allocation must sum to one")


def safe_masked_softmax(logits: Tensor, mask: Tensor) -> Tensor:
    """Masked softmax that returns finite exact zeros for an all-closed row."""

    if logits.shape != mask.shape or mask.dtype != torch.bool:
        raise ValueError("mask must be bool and have the same shape as logits")
    masked = torch.where(mask, logits, torch.full_like(logits, -torch.inf))
    row_max = masked.amax(dim=-1, keepdim=True)
    safe_max = torch.where(torch.isfinite(row_max), row_max, torch.zeros_like(row_max))
    numerator = torch.where(mask, torch.exp(masked - safe_max), torch.zeros_like(masked))
    denominator = numerator.sum(dim=-1, keepdim=True)
    return torch.where(
        denominator > 0,
        numerator / denominator.clamp_min(torch.finfo(logits.dtype).tiny),
        torch.zeros_like(numerator),
    )


def compiled_ohmic_attention(
    semantic_scores: Tensor,
    drive: Tensor,
    total_resistance: Tensor,
    readiness: Tensor,
    region_multiplier: Tensor,
    path_mask: Tensor,
    *,
    reference_drive: float = 1.0,
    reference_resistance: float = 1.0,
) -> tuple[Tensor, Tensor, Tensor]:
    """Compile CAS routing to an ordinary logit bias.

    Exact agreement with the main router is expected when ``path_mask`` is the
    same candidate mask used by that router, including any breakdown override.
    This function also closes flows that underflow to zero, producing the same
    final effective mask behavior. This proves the scalar routing path is a
    parameterization, not unique neural expressiveness.
    """

    if (
        not isinstance(reference_drive, (int, float))
        or isinstance(reference_drive, bool)
        or not math.isfinite(reference_drive)
        or not isinstance(reference_resistance, (int, float))
        or isinstance(reference_resistance, bool)
        or not math.isfinite(reference_resistance)
        or not 0 < reference_drive
        or not 0 < reference_resistance
    ):
        raise ValueError("reference values must be positive")
    for name, value in {
        "reference_drive": reference_drive,
        "reference_resistance": reference_resistance,
    }.items():
        typed_value = torch.as_tensor(
            value, dtype=semantic_scores.dtype, device=semantic_scores.device
        )
        if not bool(torch.isfinite(typed_value).item()) or not bool(
            (typed_value > 0).item()
        ):
            raise ValueError(f"{name} must be representably positive in the tensor dtype")
    tensors = (drive, total_resistance, readiness, region_multiplier)
    if any(value.shape != semantic_scores.shape for value in tensors):
        raise ValueError("all edge tensors must share semantic_scores shape")
    if path_mask.shape != semantic_scores.shape or path_mask.dtype != torch.bool:
        raise ValueError("path_mask must be bool and share semantic_scores shape")
    valid = (
        path_mask
        & (drive > 0)
        & (readiness > 0)
        & (region_multiplier > 0)
    )
    zero = torch.zeros_like(semantic_scores)
    unit = torch.ones_like(semantic_scores)
    safe_resistance = torch.where(valid, total_resistance, unit)
    if not bool(torch.isfinite(safe_resistance).all().item()) or bool(
        (valid & (safe_resistance <= 0)).any().item()
    ):
        raise ValueError("effective-path total_resistance must be finite and positive")
    reported_conductance = reference_resistance / safe_resistance
    if bool(
        (valid & (~torch.isfinite(reported_conductance) | (reported_conductance <= 0)))
        .any()
        .item()
    ):
        raise ValueError(
            "candidate-path relative conductance must be finite and representably positive"
        )
    safe_drive = torch.where(
        valid,
        drive,
        torch.full_like(drive, reference_drive),
    )
    safe_readiness = torch.where(valid, readiness, unit)
    safe_region = torch.where(valid, region_multiplier, unit)
    route_log = (
        torch.log(safe_drive)
        - math.log(reference_drive)
        + torch.log(safe_readiness)
        + torch.log(safe_region)
        + math.log(reference_resistance)
        - torch.log(safe_resistance)
    )
    current = torch.where(
        valid,
        torch.exp(route_log),
        zero,
    )
    if not bool(torch.isfinite(current).all().item()):
        raise ValueError("effective-path current must be finite")
    valid = valid & (current > 0)
    current = torch.where(valid, current, zero)
    compiled_logits = semantic_scores + route_log
    attention = safe_masked_softmax(compiled_logits, valid)
    total_current = current.sum(dim=-1)
    if not bool(torch.isfinite(total_current).all().item()):
        raise ValueError("total_current must be finite")
    return attention, current, total_current


def additive_weight_path(
    x: Tensor, base_weight: Tensor, deltas: Tensor, allocation: Tensor
) -> Tensor:
    """The retired additive effective-weight formulation."""

    _validate_simplex(allocation)
    effective = base_weight + torch.einsum("j,joi->oi", allocation, deltas)
    return torch.einsum("...i,oi->...o", x, effective)


def additive_output_mixture(
    x: Tensor, base_weight: Tensor, deltas: Tensor, allocation: Tensor
) -> Tensor:
    """The exact output-mixture twin of :func:`additive_weight_path`."""

    _validate_simplex(allocation)
    experts = torch.einsum("...i,joi->...jo", x, base_weight.unsqueeze(0) + deltas)
    return torch.einsum("j,...jo->...o", allocation, experts)


class GenericFullStateController(nn.Module):
    """Fair generic controller for later matched learning experiments.

    It receives the same independently sourced Drive and resistance values as
    a CAS diagnostic head.  The class is supplied so later experiments cannot
    compare CAS against a weaker ratio-only straw baseline.
    """

    def __init__(self, input_features: int, hidden_features: int, outputs: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_features, hidden_features),
            nn.GELU(),
            nn.Linear(hidden_features, outputs),
        )

    def forward(self, features: Tensor) -> Tensor:
        return self.network(features)
