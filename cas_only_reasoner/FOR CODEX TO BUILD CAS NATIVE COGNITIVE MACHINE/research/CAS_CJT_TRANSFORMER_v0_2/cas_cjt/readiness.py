"""Independent Desire, Wisdom, and Power readiness for Neural CJTs.

The three axes stay visible.  A learned or authored score can only scale a
route that its corresponding hard status already admits; it can never turn an
``INSUFFICIENT`` or ``UNKNOWN`` prerequisite into an executable route.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor

from .types import PPM_SCALE, ReadinessState, ReadinessStatus


class ReadinessError(ValueError):
    """A D/W/P tensor profile violated its runtime contract."""


def _check_score(name: str, value: Tensor, reference: Tensor) -> None:
    if not isinstance(value, Tensor) or not value.is_floating_point():
        raise ReadinessError(f"{name} must be a floating-point tensor")
    if value.shape != reference.shape:
        raise ReadinessError(
            f"{name} must have shape {tuple(reference.shape)}, got {tuple(value.shape)}"
        )
    if value.dtype != reference.dtype or value.device != reference.device:
        raise ReadinessError(f"{name} must share the reference dtype and device")
    if not bool(torch.isfinite(value).all().item()):
        raise ReadinessError(f"{name} must contain only finite values")
    if bool(((value < 0) | (value > 1)).any().item()):
        raise ReadinessError(f"{name} must stay in the closed interval [0, 1]")


def _check_gate(name: str, value: Tensor, reference: Tensor) -> None:
    if (
        not isinstance(value, Tensor)
        or value.dtype != torch.bool
        or value.shape != reference.shape
        or value.device != reference.device
    ):
        raise ReadinessError(
            f"{name} must be bool on the reference device with shape "
            f"{tuple(reference.shape)}"
        )


@dataclass(frozen=True)
class DWPProfile:
    """Materialized per-route D/W/P state.

    Scores are differentiable soft strengths.  Gates are separately authored
    or verifier-derived hard facts.  The aggregate is intentionally exposed in
    addition to, not instead of, its three source axes.
    """

    desire: Tensor
    wisdom: Tensor
    power: Tensor
    desire_gate: Tensor
    wisdom_gate: Tensor
    power_gate: Tensor
    profile_id: str = "PROTOTYPE_DWP_PRODUCT/0.1"
    desire_reason: str = "DESIRE_SUFFICIENT"
    wisdom_reason: str = "WISDOM_SUFFICIENT"
    power_reason: str = "POWER_SUFFICIENT"

    def validate(self, reference: Tensor | None = None) -> None:
        if reference is None:
            reference = self.desire
        if not isinstance(reference, Tensor) or not reference.is_floating_point():
            raise ReadinessError("reference must be a floating-point tensor")
        for name, value in (
            ("desire", self.desire),
            ("wisdom", self.wisdom),
            ("power", self.power),
        ):
            _check_score(name, value, reference)
        for name, value in (
            ("desire_gate", self.desire_gate),
            ("wisdom_gate", self.wisdom_gate),
            ("power_gate", self.power_gate),
        ):
            _check_gate(name, value, reference)
        for name, value in (
            ("profile_id", self.profile_id),
            ("desire_reason", self.desire_reason),
            ("wisdom_reason", self.wisdom_reason),
            ("power_reason", self.power_reason),
        ):
            if not isinstance(value, str) or not value:
                raise ReadinessError(f"{name} must be a nonempty string")

    @property
    def hard_mask(self) -> Tensor:
        self.validate()
        return self.desire_gate & self.wisdom_gate & self.power_gate

    @property
    def soft_strength(self) -> Tensor:
        """Return the transparent multiplicative readiness factor."""

        self.validate()
        return self.desire * self.wisdom * self.power

    @property
    def effective_readiness(self) -> Tensor:
        """Return a soft strength only where all three hard axes admit work."""

        strength = self.soft_strength
        return torch.where(self.hard_mask, strength, torch.zeros_like(strength))

    def failed_axes(self) -> dict[str, Tensor]:
        """Keep each failed prerequisite independently diagnosable."""

        self.validate()
        return {
            "DESIRE": ~self.desire_gate,
            "WISDOM": ~self.wisdom_gate,
            "POWER": ~self.power_gate,
        }

    @classmethod
    def uniform(
        cls,
        reference: Tensor,
        *,
        desire: float = 1.0,
        wisdom: float = 1.0,
        power: float = 1.0,
        desire_open: bool = True,
        wisdom_open: bool = True,
        power_open: bool = True,
        desire_reason: str = "DESIRE_SUFFICIENT",
        wisdom_reason: str = "WISDOM_SUFFICIENT",
        power_reason: str = "POWER_SUFFICIENT",
    ) -> "DWPProfile":
        if not isinstance(reference, Tensor) or not reference.is_floating_point():
            raise ReadinessError("reference must be a floating-point tensor")

        def score(value: float) -> Tensor:
            return torch.full_like(reference, value)

        def gate(value: bool) -> Tensor:
            return torch.full(
                reference.shape,
                value,
                dtype=torch.bool,
                device=reference.device,
            )

        profile = cls(
            desire=score(desire),
            wisdom=score(wisdom),
            power=score(power),
            desire_gate=gate(desire_open),
            wisdom_gate=gate(wisdom_open),
            power_gate=gate(power_open),
            desire_reason=desire_reason,
            wisdom_reason=wisdom_reason,
            power_reason=power_reason,
        )
        profile.validate(reference)
        return profile

    @classmethod
    def from_state(
        cls,
        state: ReadinessState,
        reference: Tensor | None = None,
        *,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> "DWPProfile":
        """Materialize a strict wire ``ReadinessState`` as neural tensors.

        The wire status controls each hard gate.  A high score with an
        ``INSUFFICIENT`` or ``UNKNOWN`` status therefore remains closed.  The
        score conversion is exact at the wire boundary before the requested
        floating dtype is applied.
        """

        if not isinstance(state, ReadinessState):
            raise ReadinessError("state must be a ReadinessState")
        if reference is not None:
            if not isinstance(reference, Tensor) or not reference.is_floating_point():
                raise ReadinessError("reference must be a floating-point tensor")
            if device is not None or dtype is not None:
                raise ReadinessError(
                    "device and dtype must be omitted when reference is supplied"
                )
            shape = reference.shape
            resolved_device = reference.device
            resolved_dtype = reference.dtype
        else:
            shape = torch.Size([])
            resolved_device = torch.device("cpu") if device is None else torch.device(device)
            resolved_dtype = torch.get_default_dtype() if dtype is None else dtype
            if not resolved_dtype.is_floating_point:
                raise ReadinessError("dtype must be floating point")

        def score(axis: object) -> Tensor:
            score_ppm = getattr(axis, "score_ppm")
            return torch.full(
                shape,
                score_ppm / PPM_SCALE,
                device=resolved_device,
                dtype=resolved_dtype,
            )

        def gate(axis: object) -> Tensor:
            status = getattr(axis, "status")
            return torch.full(
                shape,
                status is ReadinessStatus.SUFFICIENT,
                device=resolved_device,
                dtype=torch.bool,
            )

        def reason(axis: object) -> str:
            reason_codes = getattr(axis, "reason_codes")
            return "|".join(reason_codes)

        profile = cls(
            desire=score(state.desire),
            wisdom=score(state.wisdom),
            power=score(state.power),
            desire_gate=gate(state.desire),
            wisdom_gate=gate(state.wisdom),
            power_gate=gate(state.power),
            profile_id=state.profile_id,
            desire_reason=reason(state.desire),
            wisdom_reason=reason(state.wisdom),
            power_reason=reason(state.power),
        )
        profile.validate(reference if reference is not None else profile.desire)
        return profile


__all__ = ["DWPProfile", "ReadinessError"]
