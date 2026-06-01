"""Compute-feasibility gate for frontier-scale runs (frontier run-gate 3).

Gates (5), (6), and (7) confirmed the *model* is auditable: provenance is
declared, the architecture adapter exists, and the CAS probe is loadable. This
gate answers a blunter, physical question: can the declared hardware actually
*hold* the model long enough to run the audit, or would the planner hand back a
plan that merely *looks* schedulable?

Anchored to the planner's own arithmetic (``cas_harness_scale_planner``), not an
aspirational one. Two planner facts make a silent infeasibility possible:

* the planner provisions only a fraction of each accelerator's memory for weights
  and activations (``USABLE_MEMORY_FRACTION`` -- the rest is left for the runtime,
  fragmentation, KV cache, and CAS capture buffers); and
* it clamps the probe-worker fan-out to ``MAX_WORKER_FANOUT`` no matter how large
  the model is.

So a frontier model can be handed a plan with the worker count pinned at the cap
while each worker is quietly asked to hold more than one accelerator can fit. The
plan looks complete; the run would thrash or OOM on every shard. This gate makes
that refusal explicit and honest *before* a run is created.

The check is pure physics from numbers we already own. The model's runtime memory
need is the planner's own ``estimated_total_runtime_gb`` (weights + activation
overhead). The fleet can bring at most ``min(MAX_WORKER_FANOUT, accelerator_count)``
accelerators to bear, each contributing ``accelerator_memory_gb x
USABLE_MEMORY_FRACTION`` usable GB. If that aggregate cannot cover the runtime
need, the declared envelope is refused. No invented duration, throughput, or
dollar model -- that would be a dishonest gate; this one only compares memory we
can actually account for.

Honesty contract (mirrors gates 5, 6, and 7 -- declared vs verified):

* ``COMPUTE_FEASIBILITY_VERIFIED`` -- the fleet actually sharded the model onto
  real accelerators and confirmed the resident set fits. Fleet-side only; never
  produced at the API tier.
* ``COMPUTE_FEASIBILITY_DECLARED`` -- the declared envelope is numerically
  sufficient under the planner's memory model: capped accelerator count x
  per-accelerator usable memory covers the estimated runtime need. Enough to
  *create* a run; the real fit is confirmed fleet-side.
* ``COMPUTE_FEASIBILITY_INSUFFICIENT`` -- missing envelope at frontier /
  non-positive fields / aggregate usable memory below the runtime need / a
  per-accelerator size so small that even a fully fanned-out fleet (capped at
  ``MAX_WORKER_FANOUT``) cannot hold the model. Refuses the run (HTTP 422).

Scope (kept deliberately narrow, so the gate stays honest): it certifies the
declared hardware is *numerically able to hold the model's resident memory* under
the planner's own fractions and fan-out cap. It does **not** certify the run will
finish, hit a latency target, or cost a given amount -- a frontier run is
``EXPERIMENTAL_NOT_VALIDATED`` by definition, and runtime/throughput/cost at that
scale are projections, not measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Literal

from api.services.cas_harness_scale_planner import (
    MAX_WORKER_FANOUT,
    USABLE_MEMORY_FRACTION,
    ScalePlan,
)

ComputeFeasibilityStatus = Literal[
    "COMPUTE_FEASIBILITY_VERIFIED",
    "COMPUTE_FEASIBILITY_DECLARED",
    "COMPUTE_FEASIBILITY_INSUFFICIENT",
]


@dataclass(frozen=True)
class ComputeEnvelopeDeclaration:
    """Caller-supplied statement of the hardware the run would execute on.

    Intentionally minimal: the only numbers the gate can honestly reason about
    are how many accelerators are available and how much memory each one has.
    ``accelerator_type`` is a free-form label (e.g. ``"H100-80GB"``) carried for
    traceability only -- the gate never infers memory from the name, because a
    name lookup the gate cannot verify would smuggle in an unproven assumption.
    """

    accelerator_count: int
    accelerator_memory_gb: float
    accelerator_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "accelerator_count": self.accelerator_count,
            "accelerator_memory_gb": self.accelerator_memory_gb,
            "accelerator_type": self.accelerator_type,
        }


@dataclass(frozen=True)
class ComputeFeasibilitySummary:
    """Honest rollup of the compute-feasibility check, mirroring the gate-7 shape."""

    status: ComputeFeasibilityStatus
    accelerator_type: str | None
    declared_accelerator_count: int | None
    declared_accelerator_memory_gb: float | None
    usable_memory_fraction: float
    fanout_cap: int
    per_accelerator_usable_gb: float | None
    effective_accelerator_count: int | None
    fanout_capped: bool
    needed_runtime_gb: float
    available_aggregate_gb: float | None
    memory_headroom_gb: float | None
    accelerators_required: int | None
    memory_sufficient: bool | None
    fit_verified: bool
    notice: str
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        """True when the declared envelope is good enough to *create* a run."""

        return self.status != "COMPUTE_FEASIBILITY_INSUFFICIENT"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "accelerator_type": self.accelerator_type,
            "declared_accelerator_count": self.declared_accelerator_count,
            "declared_accelerator_memory_gb": self.declared_accelerator_memory_gb,
            "usable_memory_fraction": self.usable_memory_fraction,
            "fanout_cap": self.fanout_cap,
            "per_accelerator_usable_gb": self.per_accelerator_usable_gb,
            "effective_accelerator_count": self.effective_accelerator_count,
            "fanout_capped": self.fanout_capped,
            "needed_runtime_gb": self.needed_runtime_gb,
            "available_aggregate_gb": self.available_aggregate_gb,
            "memory_headroom_gb": self.memory_headroom_gb,
            "accelerators_required": self.accelerators_required,
            "memory_sufficient": self.memory_sufficient,
            "fit_verified": self.fit_verified,
            "notice": self.notice,
            "reasons": list(self.reasons),
        }


def frontier_compute_requirement_notice() -> str:
    return (
        "A frontier-scale (300B-4T) run requires a declared compute envelope the fleet can "
        "physically hold the model in: enough accelerators that the count -- capped at the "
        f"planner's {MAX_WORKER_FANOUT}-worker fan-out -- times per-accelerator memory times the "
        f"{USABLE_MEMORY_FRACTION} usable fraction covers the plan's estimated runtime memory. The "
        "planner silently clamps worker fan-out, so a too-small envelope would produce a plan that "
        "looks schedulable while under-resourcing every shard. Compute feasibility is run-gate (3)."
    )


def summarize_compute_feasibility(
    *,
    plan: ScalePlan,
    envelope: ComputeEnvelopeDeclaration | None,
) -> ComputeFeasibilitySummary:
    """Check a declared compute envelope against the plan's own memory math.

    Returns ``COMPUTE_FEASIBILITY_DECLARED`` when the declared fleet (capped at
    ``MAX_WORKER_FANOUT``) provides enough aggregate usable memory to hold the
    plan's ``estimated_total_runtime_gb``; ``COMPUTE_FEASIBILITY_INSUFFICIENT``
    otherwise. ``COMPUTE_FEASIBILITY_VERIFIED`` is reserved for the fleet, the only
    place the model is actually sharded onto real accelerators.
    """

    needed_runtime_gb = round(plan.memory_estimate.estimated_total_runtime_gb, 2)

    accelerator_type: str | None = None
    declared_count: int | None = None
    declared_mem: float | None = None
    per_accelerator_usable_gb: float | None = None
    effective_count: int | None = None
    available_aggregate_gb: float | None = None
    memory_headroom_gb: float | None = None
    accelerators_required: int | None = None
    memory_sufficient: bool | None = None
    fanout_capped = False
    reasons: list[str] = []

    if envelope is None:
        reasons.append("no compute envelope declared")
    else:
        accelerator_type = (envelope.accelerator_type or "").strip() or None
        declared_count = envelope.accelerator_count
        declared_mem = envelope.accelerator_memory_gb

        if declared_count is None or declared_count <= 0:
            reasons.append(f"accelerator_count must be positive (declared: {declared_count})")
        if declared_mem is None or declared_mem <= 0:
            reasons.append(
                f"accelerator_memory_gb must be positive (declared: {declared_mem})"
            )

        # Only do the memory arithmetic once the fields are usable. The integer
        # comparison effective_count >= accelerators_required is exact and avoids
        # any float-rounding ambiguity at the feasibility boundary.
        if not reasons:
            usable_exact = declared_mem * USABLE_MEMORY_FRACTION
            per_accelerator_usable_gb = round(usable_exact, 2)
            accelerators_required = ceil(needed_runtime_gb / usable_exact)
            effective_count = min(MAX_WORKER_FANOUT, declared_count)
            fanout_capped = declared_count > MAX_WORKER_FANOUT
            available_aggregate_gb = round(effective_count * usable_exact, 2)
            memory_headroom_gb = round(available_aggregate_gb - needed_runtime_gb, 2)
            memory_sufficient = effective_count >= accelerators_required

            if not memory_sufficient:
                if accelerators_required > MAX_WORKER_FANOUT:
                    reasons.append(
                        f"each declared accelerator provides only {per_accelerator_usable_gb} GB "
                        f"usable ({declared_mem} GB x {USABLE_MEMORY_FRACTION}); the model needs "
                        f"{needed_runtime_gb} GB, which would require {accelerators_required} "
                        f"accelerators -- more than the planner's {MAX_WORKER_FANOUT}-worker "
                        f"fan-out cap. The planner would silently clamp to {MAX_WORKER_FANOUT} "
                        "workers and under-resource every shard. Declare larger accelerators."
                    )
                else:
                    reasons.append(
                        f"the declared fleet ({effective_count} accelerators x "
                        f"{per_accelerator_usable_gb} GB usable) provides {available_aggregate_gb} "
                        f"GB; the model needs {needed_runtime_gb} GB. Declare at least "
                        f"{accelerators_required} accelerators of this size."
                    )

    if reasons:
        return ComputeFeasibilitySummary(
            status="COMPUTE_FEASIBILITY_INSUFFICIENT",
            accelerator_type=accelerator_type,
            declared_accelerator_count=declared_count,
            declared_accelerator_memory_gb=declared_mem,
            usable_memory_fraction=USABLE_MEMORY_FRACTION,
            fanout_cap=MAX_WORKER_FANOUT,
            per_accelerator_usable_gb=per_accelerator_usable_gb,
            effective_accelerator_count=effective_count,
            fanout_capped=fanout_capped,
            needed_runtime_gb=needed_runtime_gb,
            available_aggregate_gb=available_aggregate_gb,
            memory_headroom_gb=memory_headroom_gb,
            accelerators_required=accelerators_required,
            memory_sufficient=memory_sufficient,
            fit_verified=False,
            notice=(
                "Declared compute envelope is insufficient: "
                + "; ".join(reasons)
                + ". "
                + frontier_compute_requirement_notice()
            ),
            reasons=tuple(reasons),
        )

    fanout_note = (
        f" Note: {declared_count} accelerators were declared but the planner fans out to at most "
        f"{MAX_WORKER_FANOUT} workers, so only {effective_count} are used."
        if fanout_capped
        else ""
    )
    notice = (
        "Declared compute envelope can hold the model under the planner's memory model: "
        f"{declared_count} x {declared_mem} GB accelerators"
        + (f" ({accelerator_type})" if accelerator_type else "")
        + f", {per_accelerator_usable_gb} GB usable each (x {USABLE_MEMORY_FRACTION}); "
        f"{available_aggregate_gb} GB aggregate across {effective_count} workers >= "
        f"{needed_runtime_gb} GB runtime need (headroom {memory_headroom_gb} GB; minimum "
        f"{accelerators_required} accelerators required)."
        + fanout_note
        + " This is a DECLARED envelope -- the model has NOT been sharded onto real hardware; the "
        "actual fit is confirmed fleet-side (only then can the status become "
        "COMPUTE_FEASIBILITY_VERIFIED). The gate certifies the declared hardware is numerically "
        "sufficient under the planner's own memory model, NOT that the run will finish, hit a "
        "latency target, or cost a given amount (a frontier run is EXPERIMENTAL_NOT_VALIDATED by "
        "definition)."
    )

    return ComputeFeasibilitySummary(
        status="COMPUTE_FEASIBILITY_DECLARED",
        accelerator_type=accelerator_type,
        declared_accelerator_count=declared_count,
        declared_accelerator_memory_gb=declared_mem,
        usable_memory_fraction=USABLE_MEMORY_FRACTION,
        fanout_cap=MAX_WORKER_FANOUT,
        per_accelerator_usable_gb=per_accelerator_usable_gb,
        effective_accelerator_count=effective_count,
        fanout_capped=fanout_capped,
        needed_runtime_gb=needed_runtime_gb,
        available_aggregate_gb=available_aggregate_gb,
        memory_headroom_gb=memory_headroom_gb,
        accelerators_required=accelerators_required,
        memory_sufficient=memory_sufficient,
        fit_verified=False,
        notice=notice,
        reasons=(),
    )


def validate_frontier_compute_feasibility(
    *,
    plan: ScalePlan,
    envelope: ComputeEnvelopeDeclaration | None,
) -> ComputeFeasibilitySummary:
    """Frontier run-gate: raise ``ValueError`` unless the envelope can hold the model.

    Acceptable means COMPUTE_FEASIBILITY_DECLARED (or VERIFIED) -- a declared
    envelope whose capped, usable aggregate memory covers the plan's runtime need
    is enough to *create* a frontier run. COMPUTE_FEASIBILITY_INSUFFICIENT (missing
    / non-positive fields / aggregate too small / per-accelerator too small for the
    fan-out cap) refuses it. Callers convert this ValueError to HTTP 422.
    """

    summary = summarize_compute_feasibility(plan=plan, envelope=envelope)
    if summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT":
        raise ValueError(
            "frontier-scale run refused: insufficient compute envelope -- "
            + "; ".join(summary.reasons)
            + ". "
            + frontier_compute_requirement_notice()
        )
    return summary
