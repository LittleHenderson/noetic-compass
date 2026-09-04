"""CAS-Ohm candidate routing and bounded compute planning.

This module keeps four ideas separate:

* hard eligibility decides which routes may exist;
* current records the differentiable unnormalised reference-relative flow;
* flow allocation records ``current / total_current``;
* semantic attention records the ordinary score plus ``log(current)`` twin.

An all-closed row stays exactly zero.  It never receives a uniform fallback.
The compute plan is frozen from separately supplied, exact scaled-integer
native controls.  Neural current is a post-plan observation and cannot enlarge
that plan after execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import torch
from torch import Tensor

from .readiness import DWPProfile


class RoutingError(ValueError):
    """A route tensor or compute record violated its closed contract."""


REALIZED_FLOW_SCALE = 1_000_000


def bounded_mean_flow_ppm(values: Sequence[int]) -> int:
    """Return the exact round-to-even mean of integer flow microunits."""

    typed = tuple(values)
    if not typed:
        return 0
    if any(
        not isinstance(item, int) or isinstance(item, bool) or item < 0
        for item in typed
    ):
        raise RoutingError("realized flow units must be nonnegative integers")
    quotient, remainder = divmod(sum(typed), len(typed))
    if remainder * 2 > len(typed) or (
        remainder * 2 == len(typed) and quotient % 2 == 1
    ):
        quotient += 1
    return min(REALIZED_FLOW_SCALE, quotient)


def largest_remainder_flow_ppm(
    current_units: Sequence[int],
    canonical_route_ids: Sequence[str],
) -> tuple[int, ...]:
    """Allocate one exact ppm whole by largest remainder and route-ID tie-break."""

    currents = tuple(current_units)
    route_ids = tuple(canonical_route_ids)
    if (
        not currents
        or len(currents) != len(route_ids)
        or len(set(route_ids)) != len(route_ids)
        or any(not isinstance(item, str) or not item for item in route_ids)
        or any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0
            for item in currents
        )
    ):
        raise RoutingError("realized route flow inputs are invalid")
    total = sum(currents)
    if total == 0:
        return tuple(0 for _ in currents)
    floors: list[int] = []
    remainders: list[int] = []
    for current in currents:
        floor, remainder = divmod(current * REALIZED_FLOW_SCALE, total)
        floors.append(floor)
        remainders.append(remainder)
    remaining = REALIZED_FLOW_SCALE - sum(floors)
    order = sorted(
        range(len(currents)),
        key=lambda index: (-remainders[index], route_ids[index]),
    )
    for index in order[:remaining]:
        floors[index] += 1
    return tuple(floors)


def allocate_global_charge(
    capacities: Sequence[int],
    conducting_rows: Sequence[bool],
    count: int,
) -> tuple[int, ...]:
    """Charge global events once to the first conducting rows with capacity."""

    typed_capacities = tuple(capacities)
    typed_conducting = tuple(conducting_rows)
    if (
        len(typed_capacities) != len(typed_conducting)
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        or any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0
            for item in typed_capacities
        )
        or any(not isinstance(item, bool) for item in typed_conducting)
    ):
        raise RoutingError("global compute charge inputs are invalid")
    remaining = count
    result: list[int] = []
    for capacity, conducting in zip(
        typed_capacities, typed_conducting, strict=True
    ):
        charge = min(capacity, remaining) if conducting else 0
        result.append(charge)
        remaining -= charge
    if remaining:
        raise RoutingError("global compute charge exceeds conducting capacity")
    return tuple(result)


def global_memory_read_limit(
    memory_read_quanta: Sequence[int],
    conducting_mask: Sequence[bool],
    *,
    global_ceiling: int,
) -> int:
    """Return one exact physical-record read cap for runtime and audit replay."""

    quanta = tuple(memory_read_quanta)
    conducting = tuple(conducting_mask)
    if len(quanta) != len(conducting):
        raise RoutingError("memory read quanta and conducting mask shapes differ")
    if (
        not isinstance(global_ceiling, int)
        or isinstance(global_ceiling, bool)
        or global_ceiling < 0
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in quanta
        )
        or any(not isinstance(value, bool) for value in conducting)
    ):
        raise RoutingError("memory read limits must be nonnegative exact integers")
    admitted = sum(
        value
        for value, has_flow in zip(quanta, conducting, strict=True)
        if has_flow
    )
    return min(admitted, global_ceiling)


def quantize_realized_current(current: Tensor) -> Tensor:
    """Ceil positive neural current into support-preserving integer microunits."""

    if not isinstance(current, Tensor) or not current.is_floating_point():
        raise RoutingError("realized current must be a floating-point tensor")
    _finite("realized current", current)
    if bool((current < 0).any().item()):
        raise RoutingError("realized current must be nonnegative")
    scaled = torch.ceil(
        current.detach().to(device="cpu", dtype=torch.float64)
        * REALIZED_FLOW_SCALE
    )
    if bool((scaled > torch.iinfo(torch.int64).max).any().item()):
        raise RoutingError("realized current exceeds int64")
    return scaled.to(dtype=torch.int64)


def realized_flow_tensors(
    current: Tensor,
    effective_mask: Tensor,
    canonical_route_ids: Sequence[str],
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    """Return exact mask/current/total/allocation authority evidence."""

    if (
        not isinstance(effective_mask, Tensor)
        or effective_mask.dtype != torch.bool
        or effective_mask.shape != current.shape
    ):
        raise RoutingError("effective mask must match realized current")
    units = quantize_realized_current(current)
    mask = effective_mask.detach().to(device="cpu")
    if not torch.equal(mask, units > 0):
        raise RoutingError("effective mask does not equal positive realized-current support")
    width = units.shape[-1]
    route_ids = tuple(canonical_route_ids)
    if len(route_ids) != width:
        raise RoutingError("canonical route IDs must match realized current")
    flat_units = units.reshape(-1, width).tolist()
    maximum = torch.iinfo(torch.int64).max
    row_totals = [sum(int(item) for item in row) for row in flat_units]
    if any(total > maximum for total in row_totals):
        raise RoutingError("realized total current exceeds int64")
    allocations = [
        largest_remainder_flow_ppm(row, route_ids) for row in flat_units
    ]
    totals = torch.tensor(row_totals, dtype=torch.int64).reshape(units.shape[:-1])
    allocation = torch.tensor(allocations, dtype=torch.int64).reshape(units.shape)
    return units, totals, allocation, totals > 0


def allocate_global_charge_tensor(
    capacities: Tensor,
    conducting_rows: Tensor,
    count: int,
) -> Tensor:
    """Tensor wrapper for :func:`allocate_global_charge`."""

    if (
        not isinstance(capacities, Tensor)
        or capacities.dtype != torch.int64
        or not isinstance(conducting_rows, Tensor)
        or conducting_rows.dtype != torch.bool
        or capacities.shape != conducting_rows.shape
    ):
        raise RoutingError("global charge tensors must have one matching row shape")
    values = allocate_global_charge(
        capacities.detach().to(device="cpu").reshape(-1).tolist(),
        conducting_rows.detach().to(device="cpu").reshape(-1).tolist(),
        count,
    )
    return torch.tensor(
        values,
        dtype=torch.int64,
        device=capacities.device,
    ).reshape(capacities.shape)


def _finite(name: str, value: Tensor) -> None:
    if not bool(torch.isfinite(value).all().item()):
        raise RoutingError(f"{name} must contain only finite values")


def _same_float_tensor(name: str, value: Tensor, reference: Tensor) -> None:
    if not isinstance(value, Tensor) or not value.is_floating_point():
        raise RoutingError(f"{name} must be a floating-point tensor")
    if value.shape != reference.shape:
        raise RoutingError(
            f"{name} must have shape {tuple(reference.shape)}, got {tuple(value.shape)}"
        )
    if value.dtype != reference.dtype or value.device != reference.device:
        raise RoutingError(f"{name} must share the reference dtype and device")
    _finite(name, value)


def _same_bool_tensor(name: str, value: Tensor, reference: Tensor) -> None:
    if (
        not isinstance(value, Tensor)
        or value.dtype != torch.bool
        or value.shape != reference.shape
        or value.device != reference.device
    ):
        raise RoutingError(
            f"{name} must be bool on the reference device with shape "
            f"{tuple(reference.shape)}"
        )


def _masked_attention(
    semantic_scores: Tensor,
    current: Tensor,
    effective_mask: Tensor,
) -> Tensor:
    """Stable softmax of ``semantic_scores + log(current)`` with zero fallback."""

    negative_infinity = torch.full_like(semantic_scores, -torch.inf)
    safe_current = torch.where(effective_mask, current, torch.ones_like(current))
    logits = torch.where(
        effective_mask,
        semantic_scores + torch.log(safe_current),
        negative_infinity,
    )
    row_max = logits.amax(dim=-1, keepdim=True)
    safe_max = torch.where(torch.isfinite(row_max), row_max, torch.zeros_like(row_max))
    numerator = torch.where(
        effective_mask,
        torch.exp(logits - safe_max),
        torch.zeros_like(logits),
    )
    denominator = numerator.sum(dim=-1, keepdim=True)
    return torch.where(
        denominator > 0,
        numerator / denominator.clamp_min(torch.finfo(semantic_scores.dtype).tiny),
        torch.zeros_like(numerator),
    )


def compiled_attention_twin(
    semantic_scores: Tensor,
    current: Tensor,
    effective_mask: Tensor,
) -> Tensor:
    """Ordinary additive-logit form exactly equivalent to scalar Ohmic routing."""

    compiling = bool(
        hasattr(torch, "compiler") and torch.compiler.is_compiling()
    )
    if not compiling:
        if not isinstance(semantic_scores, Tensor) or not semantic_scores.is_floating_point():
            raise RoutingError("semantic_scores must be a floating-point tensor")
        _same_float_tensor("current", current, semantic_scores)
        _same_bool_tensor("effective_mask", effective_mask, semantic_scores)
        if bool((current < 0).any().item()):
            raise RoutingError("current must be nonnegative")
        if bool((effective_mask & (current <= 0)).any().item()):
            raise RoutingError(
                "every effective route must have representably positive current"
            )
    return _masked_attention(semantic_scores, current, effective_mask)


@dataclass(frozen=True)
class NativeComputeInputs:
    """Exact pre-schedule controls, kept separate from neural tensors.

    ``drive_units`` and ``resistance_units`` are authored scaled integers.
    They are never reconstructed by rounding neural floating-point values.
    Canonical route IDs provide a stable final tie-break.
    """

    drive_units: Tensor
    resistance_units: Tensor
    canonical_route_ids: tuple[str, ...]
    flow_scale_units: int = 1_000_000

    def validate(self, reference: Tensor) -> None:
        for name, value in (
            ("drive_units", self.drive_units),
            ("resistance_units", self.resistance_units),
        ):
            if (
                not isinstance(value, Tensor)
                or value.dtype != torch.int64
                or value.shape != reference.shape
                or value.device != reference.device
            ):
                raise RoutingError(
                    f"{name} must be int64 on the route device with shape "
                    f"{tuple(reference.shape)}"
                )
            if bool((value < 0).any().item()):
                raise RoutingError(f"{name} must be nonnegative")
        route_ids = tuple(self.canonical_route_ids)
        if len(route_ids) != reference.shape[-1]:
            raise RoutingError("canonical_route_ids must match the route axis")
        if any(not isinstance(item, str) or not item for item in route_ids):
            raise RoutingError("canonical_route_ids must be nonempty strings")
        if len(set(route_ids)) != len(route_ids):
            raise RoutingError("canonical_route_ids must be unique")
        if (
            not isinstance(self.flow_scale_units, int)
            or isinstance(self.flow_scale_units, bool)
            or self.flow_scale_units <= 0
        ):
            raise RoutingError("flow_scale_units must be a positive integer")

    def raw_flow_units(self, admitted_mask: Tensor) -> Tensor:
        """Evaluate ``floor(scale * drive / resistance)`` with Python integers."""

        self.validate(admitted_mask)
        _same_bool_tensor("admitted_mask", admitted_mask, self.drive_units)
        width = self.drive_units.shape[-1]
        flat_drive = self.drive_units.detach().cpu().reshape(-1, width).tolist()
        flat_resistance = (
            self.resistance_units.detach().cpu().reshape(-1, width).tolist()
        )
        flat_mask = admitted_mask.detach().cpu().reshape(-1, width).tolist()
        maximum = torch.iinfo(torch.int64).max
        rows: list[list[int]] = []
        for drive_row, resistance_row, mask_row in zip(
            flat_drive, flat_resistance, flat_mask, strict=True
        ):
            row: list[int] = []
            for drive, resistance, admitted in zip(
                drive_row, resistance_row, mask_row, strict=True
            ):
                if not admitted or drive == 0:
                    row.append(0)
                    continue
                if resistance <= 0:
                    raise RoutingError(
                        "an admitted native route with positive drive requires positive resistance"
                    )
                raw = (self.flow_scale_units * drive) // resistance
                if raw > maximum:
                    raise RoutingError("native raw flow exceeds int64")
                row.append(raw)
            rows.append(row)
        return torch.tensor(
            rows,
            dtype=torch.int64,
            device=self.drive_units.device,
        ).reshape(self.drive_units.shape)

    def to_authoritative_dict(self) -> dict[str, Any]:
        """Expose the exact authored snapshot without JSON floating point."""

        # The drive tensor is a sufficient shape/device reference here.
        self.validate(self.drive_units)
        return {
            "contract_type": "NATIVE_COMPUTE_INPUTS",
            "schema_version": "cas.neural-cjt.native-compute-inputs/0.2",
            "drive_units": self.drive_units.detach().cpu().tolist(),
            "resistance_units": self.resistance_units.detach().cpu().tolist(),
            "canonical_route_ids": list(self.canonical_route_ids),
            "flow_scale_units": self.flow_scale_units,
        }


@dataclass(frozen=True)
class RouteInputs:
    semantic_scores: Tensor
    drive: Tensor
    resistance_capability: Tensor
    resistance_context: Tensor
    resistance_resource: Tensor
    resistance_memory: Tensor
    prior_region_multiplier: Tensor
    topology_mask: Tensor
    permission_mask: Tensor
    quarantine_mask: Tensor
    budget_mask: Tensor
    readiness: DWPProfile
    native_compute: NativeComputeInputs
    reference_drive: float = 1.0
    reference_resistance: float = 1.0
    minimum_total_resistance: float = 0.1

    @property
    def resistance_components(self) -> tuple[Tensor, ...]:
        return (
            self.resistance_capability,
            self.resistance_context,
            self.resistance_resource,
            self.resistance_memory,
        )

    def validate(self) -> None:
        scores = self.semantic_scores
        if (
            not isinstance(scores, Tensor)
            or not scores.is_floating_point()
            or scores.ndim < 1
        ):
            raise RoutingError("semantic_scores must be a floating tensor with a route axis")
        _finite("semantic_scores", scores)
        for name, value in (
            ("drive", self.drive),
            ("resistance_capability", self.resistance_capability),
            ("resistance_context", self.resistance_context),
            ("resistance_resource", self.resistance_resource),
            ("resistance_memory", self.resistance_memory),
            ("prior_region_multiplier", self.prior_region_multiplier),
        ):
            _same_float_tensor(name, value, scores)
            if bool((value < 0).any().item()):
                raise RoutingError(f"{name} must be nonnegative")
        for name, value in (
            ("topology_mask", self.topology_mask),
            ("permission_mask", self.permission_mask),
            ("quarantine_mask", self.quarantine_mask),
            ("budget_mask", self.budget_mask),
        ):
            _same_bool_tensor(name, value, scores)
        self.readiness.validate(scores)
        if not isinstance(self.native_compute, NativeComputeInputs):
            raise RoutingError("native_compute must be NativeComputeInputs")
        self.native_compute.validate(scores)
        for name, value in (
            ("reference_drive", self.reference_drive),
            ("reference_resistance", self.reference_resistance),
            ("minimum_total_resistance", self.minimum_total_resistance),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise RoutingError(f"{name} must be a finite positive number")
            typed = torch.as_tensor(value, dtype=scores.dtype, device=scores.device)
            if not math.isfinite(float(value)) or not bool(
                (torch.isfinite(typed) & (typed > 0)).item()
            ):
                raise RoutingError(
                    f"{name} must be finite and representably positive in the route dtype"
                )


@dataclass(frozen=True)
class ComputePolicy:
    """Deterministic exact-integer conversion from native flow to ceilings."""

    policy_id: str = "cas.cjt.compute/0.2"
    flow_units_per_quantum: int = 1_000_000
    max_routes: int = 8
    max_reasoning_steps: int = 8
    max_branches: int = 4
    max_memory_reads: int = 4
    max_diagnostic_probes: int = 4

    def validate(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise RoutingError("compute policy_id must be a nonempty string")
        if (
            not isinstance(self.flow_units_per_quantum, int)
            or isinstance(self.flow_units_per_quantum, bool)
            or self.flow_units_per_quantum <= 0
        ):
            raise RoutingError("flow_units_per_quantum must be a positive integer")
        for name in (
            "max_routes",
            "max_reasoning_steps",
            "max_branches",
            "max_memory_reads",
            "max_diagnostic_probes",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise RoutingError(f"{name} must be a nonnegative integer")

    def to_authoritative_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_type": "NATIVE_COMPUTE_POLICY",
            "schema_version": "cas.neural-cjt.native-compute-policy/0.2",
            "policy_id": self.policy_id,
            "flow_units_per_quantum": self.flow_units_per_quantum,
            "max_routes": self.max_routes,
            "max_reasoning_steps": self.max_reasoning_steps,
            "max_branches": self.max_branches,
            "max_memory_reads": self.max_memory_reads,
            "max_diagnostic_probes": self.max_diagnostic_probes,
        }

    def bind(
        self,
        native: NativeComputeInputs,
        admitted_mask: Tensor,
    ) -> "PredeclaredComputePlan":
        self.validate()
        if not isinstance(native, NativeComputeInputs):
            raise RoutingError("native must be NativeComputeInputs")
        raw = native.raw_flow_units(admitted_mask)
        width = raw.shape[-1]
        flat_raw = raw.detach().cpu().reshape(-1, width).tolist()
        maximum = torch.iinfo(torch.int64).max
        totals: list[int] = []
        quanta: list[int] = []
        route_counts: list[int] = []
        scheduled: list[list[bool]] = []
        for row in flat_raw:
            total = sum(row)
            if total > maximum:
                raise RoutingError("native total flow exceeds int64")
            total_quanta = (
                0
                if total == 0
                else (total + self.flow_units_per_quantum - 1)
                // self.flow_units_per_quantum
            )
            positive_count = sum(value > 0 for value in row)
            route_count = min(total_quanta, positive_count, self.max_routes)
            order = sorted(
                range(width),
                key=lambda index: (-row[index], native.canonical_route_ids[index]),
            )
            chosen = {
                index for index in order if row[index] > 0
            }
            chosen = set(list(index for index in order if index in chosen)[:route_count])
            totals.append(total)
            quanta.append(total_quanta)
            route_counts.append(route_count)
            scheduled.append([index in chosen for index in range(width)])

        prefix_shape = raw.shape[:-1]
        device = raw.device
        total_tensor = torch.tensor(totals, dtype=torch.int64, device=device).reshape(
            prefix_shape
        )
        quantum_tensor = torch.tensor(quanta, dtype=torch.int64, device=device).reshape(
            prefix_shape
        )
        route_tensor = torch.tensor(
            route_counts, dtype=torch.int64, device=device
        ).reshape(prefix_shape)
        scheduled_tensor = torch.tensor(
            scheduled, dtype=torch.bool, device=device
        ).reshape(raw.shape)

        def bounded(cap: int) -> Tensor:
            return quantum_tensor.clamp(min=0, max=cap)

        plan = PredeclaredComputePlan(
            policy_id=self.policy_id,
            canonical_route_ids=native.canonical_route_ids,
            source_raw_flow_units=raw,
            source_total_flow_units=total_tensor,
            scheduled_route_mask=scheduled_tensor,
            route_quanta=route_tensor,
            reasoning_step_quanta=bounded(self.max_reasoning_steps),
            branch_quanta=bounded(self.max_branches),
            memory_read_quanta=bounded(self.max_memory_reads),
            diagnostic_probe_quanta=bounded(self.max_diagnostic_probes),
        )
        plan.validate()
        return plan


@dataclass(frozen=True)
class PredeclaredComputePlan:
    policy_id: str
    canonical_route_ids: tuple[str, ...]
    source_raw_flow_units: Tensor
    source_total_flow_units: Tensor
    scheduled_route_mask: Tensor
    route_quanta: Tensor
    reasoning_step_quanta: Tensor
    branch_quanta: Tensor
    memory_read_quanta: Tensor
    diagnostic_probe_quanta: Tensor

    @property
    def integer_fields(self) -> tuple[tuple[str, Tensor], ...]:
        return (
            ("route_quanta", self.route_quanta),
            ("reasoning_step_quanta", self.reasoning_step_quanta),
            ("branch_quanta", self.branch_quanta),
            ("memory_read_quanta", self.memory_read_quanta),
            ("diagnostic_probe_quanta", self.diagnostic_probe_quanta),
        )

    def validate(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise RoutingError("compute plan policy_id must be a nonempty string")
        if (
            not isinstance(self.source_raw_flow_units, Tensor)
            or self.source_raw_flow_units.dtype != torch.int64
            or self.source_raw_flow_units.ndim < 1
            or bool((self.source_raw_flow_units < 0).any().item())
        ):
            raise RoutingError("source_raw_flow_units must be nonnegative int64")
        expected_shape = self.source_raw_flow_units.shape[:-1]
        if (
            not isinstance(self.source_total_flow_units, Tensor)
            or self.source_total_flow_units.dtype != torch.int64
            or self.source_total_flow_units.shape != expected_shape
            or self.source_total_flow_units.device != self.source_raw_flow_units.device
            or bool((self.source_total_flow_units < 0).any().item())
        ):
            raise RoutingError(
                "source_total_flow_units must be nonnegative int64 over route rows"
            )
        exact_totals = self.source_raw_flow_units.sum(dim=-1)
        if not torch.equal(exact_totals, self.source_total_flow_units):
            raise RoutingError("source_total_flow_units does not match raw route flow")
        if (
            not isinstance(self.scheduled_route_mask, Tensor)
            or self.scheduled_route_mask.dtype != torch.bool
            or self.scheduled_route_mask.shape != self.source_raw_flow_units.shape
            or self.scheduled_route_mask.device != self.source_raw_flow_units.device
        ):
            raise RoutingError("scheduled_route_mask must match source route flow")
        route_ids = tuple(self.canonical_route_ids)
        if (
            len(route_ids) != self.source_raw_flow_units.shape[-1]
            or len(set(route_ids)) != len(route_ids)
            or any(not isinstance(item, str) or not item for item in route_ids)
        ):
            raise RoutingError("canonical_route_ids are invalid")
        if bool(
            (self.scheduled_route_mask & (self.source_raw_flow_units == 0)).any().item()
        ):
            raise RoutingError("a zero-native-flow route cannot be scheduled")
        for name, value in self.integer_fields:
            if (
                not isinstance(value, Tensor)
                or value.dtype != torch.int64
                or value.shape != expected_shape
                or value.device != self.source_total_flow_units.device
                or bool((value < 0).any().item())
            ):
                raise RoutingError(
                    f"{name} must be a nonnegative int64 tensor matching native rows"
                )
        if not torch.equal(
            self.scheduled_route_mask.sum(dim=-1, dtype=torch.int64),
            self.route_quanta,
        ):
            raise RoutingError("route_quanta must match scheduled_route_mask")
        no_flow = self.source_total_flow_units == 0
        if any(bool((value[no_flow] != 0).any().item()) for _, value in self.integer_fields):
            raise RoutingError("a zero-flow row cannot receive compute")

    def to_authoritative_dict(self) -> dict[str, Any]:
        """Return a no-float snapshot suitable for hashing and sealed traces."""

        self.validate()

        def values(tensor: Tensor) -> Any:
            return tensor.detach().cpu().tolist()

        return {
            "contract_type": "PREDECLARED_COMPUTE_PLAN",
            "schema_version": "cas.neural-cjt.predeclared-compute-plan/0.2",
            "policy_id": self.policy_id,
            "canonical_route_ids": list(self.canonical_route_ids),
            "source_raw_flow_units": values(self.source_raw_flow_units),
            "source_total_flow_units": values(self.source_total_flow_units),
            "scheduled_route_mask": values(self.scheduled_route_mask),
            "route_quanta": values(self.route_quanta),
            "reasoning_step_quanta": values(self.reasoning_step_quanta),
            "branch_quanta": values(self.branch_quanta),
            "memory_read_quanta": values(self.memory_read_quanta),
            "diagnostic_probe_quanta": values(self.diagnostic_probe_quanta),
        }


@dataclass(frozen=True)
class PostExecutionObservation:
    """Measured consumption.  It cannot retroactively grant more compute."""

    routes_executed: Tensor
    reasoning_steps_used: Tensor
    branches_opened: Tensor
    memory_reads_used: Tensor
    diagnostic_probes_used: Tensor

    @property
    def fields(self) -> tuple[tuple[str, Tensor], ...]:
        return (
            ("routes_executed", self.routes_executed),
            ("reasoning_steps_used", self.reasoning_steps_used),
            ("branches_opened", self.branches_opened),
            ("memory_reads_used", self.memory_reads_used),
            ("diagnostic_probes_used", self.diagnostic_probes_used),
        )

    def validate_against(self, plan: PredeclaredComputePlan) -> None:
        plan.validate()
        ceilings = dict(plan.integer_fields)
        mapping = {
            "routes_executed": "route_quanta",
            "reasoning_steps_used": "reasoning_step_quanta",
            "branches_opened": "branch_quanta",
            "memory_reads_used": "memory_read_quanta",
            "diagnostic_probes_used": "diagnostic_probe_quanta",
        }
        for name, value in self.fields:
            if (
                not isinstance(value, Tensor)
                or value.dtype != torch.int64
                or value.shape != plan.source_total_flow_units.shape
                or value.device != plan.source_total_flow_units.device
                or bool((value < 0).any().item())
            ):
                raise RoutingError(
                    f"{name} must be a nonnegative int64 tensor matching the plan"
                )
            if bool((value > ceilings[mapping[name]]).any().item()):
                raise RoutingError(f"{name} exceeds its predeclared compute ceiling")


@dataclass(frozen=True)
class CASOhmRoutingResult:
    candidate_mask: Tensor
    effective_mask: Tensor
    total_resistance: Tensor
    conductance: Tensor
    current: Tensor
    flow_allocation: Tensor
    attention_allocation: Tensor
    total_current: Tensor
    compute_plan: PredeclaredComputePlan


class CASOhmRouter:
    """Parameter-free CAS-Ohm route evaluator."""

    def __init__(self, compute_policy: ComputePolicy | None = None) -> None:
        self.compute_policy = ComputePolicy() if compute_policy is None else compute_policy
        self.compute_policy.validate()

    def route(self, inputs: RouteInputs) -> CASOhmRoutingResult:
        inputs.validate()
        scores = inputs.semantic_scores
        zero = torch.zeros_like(scores)
        one = torch.ones_like(scores)
        readiness_strength = inputs.readiness.effective_readiness
        hard_admitted = (
            inputs.topology_mask
            & inputs.permission_mask
            & ~inputs.quarantine_mask
            & inputs.budget_mask
            & inputs.readiness.hard_mask
        )
        # This plan is computed before neural execution from the separate
        # exact/native control snapshot.  Nothing below can expand it.
        plan = self.compute_policy.bind(inputs.native_compute, hard_admitted)
        candidate = (
            hard_admitted
            & plan.scheduled_route_mask
            & (inputs.drive > 0)
            & (readiness_strength > 0)
            & (inputs.prior_region_multiplier > 0)
        )

        total_resistance = sum(
            torch.where(candidate, component, zero)
            for component in inputs.resistance_components
        )
        _finite("candidate total resistance", total_resistance)
        typed_minimum = torch.as_tensor(
            inputs.minimum_total_resistance,
            dtype=scores.dtype,
            device=scores.device,
        )
        if bool((candidate & (total_resistance < typed_minimum)).any().item()):
            raise RoutingError(
                "candidate total resistance is below minimum_total_resistance"
            )
        safe_resistance = torch.where(
            candidate,
            total_resistance,
            torch.full_like(total_resistance, inputs.reference_resistance),
        )
        conductance = torch.where(
            candidate,
            inputs.reference_resistance / safe_resistance,
            zero,
        )
        if bool(
            (
                candidate
                & (~torch.isfinite(conductance) | (conductance <= 0))
            ).any().item()
        ):
            raise RoutingError(
                "candidate conductance must be finite and representably positive"
            )

        safe_drive = torch.where(
            candidate,
            inputs.drive,
            torch.full_like(inputs.drive, inputs.reference_drive),
        )
        safe_readiness = torch.where(candidate, readiness_strength, one)
        safe_region = torch.where(candidate, inputs.prior_region_multiplier, one)
        route_log = (
            torch.log(safe_drive)
            - math.log(inputs.reference_drive)
            + torch.log(safe_readiness)
            + torch.log(safe_region)
            + math.log(inputs.reference_resistance)
            - torch.log(safe_resistance)
        )
        current = torch.where(candidate, torch.exp(route_log), zero)
        _finite("route current", current)
        effective = candidate & (current > 0)
        current = torch.where(effective, current, zero)
        total_resistance = torch.where(effective, total_resistance, zero)
        conductance = torch.where(effective, conductance, zero)
        total_current = current.sum(dim=-1)
        _finite("total current", total_current)

        safe_total = torch.where(
            total_current > 0,
            total_current,
            torch.ones_like(total_current),
        )
        flow_allocation = torch.where(
            effective,
            current / safe_total.unsqueeze(-1),
            zero,
        )
        attention = _masked_attention(scores, current, effective)
        return CASOhmRoutingResult(
            candidate_mask=candidate,
            effective_mask=effective,
            total_resistance=total_resistance,
            conductance=conductance,
            current=current,
            flow_allocation=flow_allocation,
            attention_allocation=attention,
            total_current=total_current,
            compute_plan=plan,
        )


__all__ = [
    "CASOhmRouter",
    "CASOhmRoutingResult",
    "ComputePolicy",
    "NativeComputeInputs",
    "PostExecutionObservation",
    "PredeclaredComputePlan",
    "REALIZED_FLOW_SCALE",
    "RouteInputs",
    "RoutingError",
    "allocate_global_charge",
    "allocate_global_charge_tensor",
    "bounded_mean_flow_ppm",
    "compiled_attention_twin",
    "global_memory_read_limit",
    "largest_remainder_flow_ppm",
    "quantize_realized_current",
    "realized_flow_tensors",
]
