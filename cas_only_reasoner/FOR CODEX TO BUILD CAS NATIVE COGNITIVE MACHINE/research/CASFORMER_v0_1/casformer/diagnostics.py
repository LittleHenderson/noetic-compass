"""Non-authoritative CAS-Ohm neural diagnostics for CASformer v0.1."""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import Tensor


def _validate_finite_nonnegative(name: str, value: Tensor) -> None:
    if not value.is_floating_point():
        raise ValueError(f"{name} must be floating point")
    if not bool(torch.isfinite(value).all().item()):
        raise ValueError(f"{name} must be finite")
    if bool((value < 0).any().item()):
        raise ValueError(f"{name} must be nonnegative")


def capability_resistance(
    capability: Tensor, *, minimum: float = 0.1, maximum: float = 10.0
) -> Tensor:
    """Map a calibrated 0-10 capability rating to positive resistance."""

    if (
        not math.isfinite(minimum)
        or not math.isfinite(maximum)
        or not 0 < minimum <= maximum
    ):
        raise ValueError("finite resistance bounds must satisfy 0 < minimum <= maximum")
    _validate_finite_nonnegative("capability", capability)
    if bool((capability > 10).any().item()):
        raise ValueError("capability must be in the calibrated range [0, 10]")
    return minimum + (maximum - minimum) * (1 - capability / 10)


@dataclass(frozen=True)
class IQReading:
    raw_current: Tensor
    normalized_current: Tensor
    overload_ratio: Tensor


def quantize_current(total_current: Tensor, *, full_scale: float) -> IQReading:
    """Return the guide's clipped 0-10 display value without discarding raw flow."""

    if not math.isfinite(full_scale) or full_scale <= 0:
        raise ValueError("full_scale must be finite and positive")
    _validate_finite_nonnegative("total_current", total_current)
    overload_ratio = total_current / full_scale
    normalized = torch.clamp(10 * overload_ratio, min=0, max=10)
    return IQReading(total_current, normalized, overload_ratio)


@dataclass(frozen=True)
class FlowAudit:
    predicted_current: Tensor
    observed_current: Tensor
    residual: Tensor
    relative_error: Tensor
    hidden_resistance: Tensor
    hidden_resistance_observable: Tensor


def audit_flow(
    drive: Tensor,
    known_resistance: Tensor,
    observed_current: Tensor,
    *,
    residual_floor: float = 1e-12,
) -> FlowAudit:
    """Compare predicted and observed flow without treating residual sign as a cause."""

    if not math.isfinite(residual_floor) or residual_floor <= 0:
        raise ValueError("residual_floor must be finite and positive")
    for name, value in {
        "drive": drive,
        "known_resistance": known_resistance,
        "observed_current": observed_current,
    }.items():
        _validate_finite_nonnegative(name, value)
    if drive.shape != known_resistance.shape or drive.shape != observed_current.shape:
        raise ValueError("drive, known_resistance, and observed_current must share a shape")
    if bool((known_resistance <= 0).any().item()):
        raise ValueError("known_resistance must be strictly positive")

    predicted = drive / known_resistance
    residual = observed_current - predicted
    relative_error = residual.abs() / predicted.clamp_min(residual_floor)
    observable = observed_current > 0
    safe_observed = torch.where(observable, observed_current, torch.ones_like(observed_current))
    hidden = drive / safe_observed - known_resistance
    hidden = torch.where(observable, hidden, torch.full_like(hidden, torch.nan))
    return FlowAudit(
        predicted_current=predicted,
        observed_current=observed_current,
        residual=residual,
        relative_error=relative_error,
        hidden_resistance=hidden,
        hidden_resistance_observable=observable,
    )
