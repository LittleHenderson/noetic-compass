"""Run-gate (4): cost-acknowledgment modality for the distributed CAS Harness probe.

Gates (5)/(6)/(7)/(3) established that the model can be audited and that the
declared hardware can physically hold it. This gate answers a different kind of
question -- not *can* it run, but *does the caller accept what running it costs?*

The honesty constraint shapes this gate more than any other. The scale planner
computes **real** resource magnitudes (``recommended_worker_count``, the model's
``estimated_total_runtime_gb``) and gate (3) validated a **real** fleet (an
accelerator count x per-card memory the caller declared). But **nothing** in the
system models wall-clock duration, throughput (tokens/sec), or dollars -- there is
no rate, no price book, no duration estimator anywhere in the planner. So this gate
**refuses to quote a price**: quoting one would mean inventing a duration/throughput/
$-rate model the honesty constraint forbids.

What it *can* do honestly is surface the real committed magnitude and require the
caller to explicitly accept that a frontier (``EXPERIMENTAL_NOT_VALIDATED``, >300B)
run will incur a substantial, **caller-owned** compute cost that CAS Harness does
**not** estimate, quote, bill, meter, or cap -- for a result CAS Harness has already
labelled experimental and unvalidated. That is the specific dishonest-by-omission
failure this gate prevents: a customer spending a fortune on frontier compute for a
result we told them was unproven, without ever having been asked to acknowledge the
spend.

It is **frontier-only** (stricter for bigger): below the frontier rung the committed
fleet is modest, so a volunteered acknowledgement is recorded for traceability but
its absence never blocks the run. A frontier run, by contrast, is refused without it.

Honesty contract, mirroring the other gates' declared-vs-verified split:
  * ``COST_METERED``        -- the fleet metered real accelerator-hours of actual
      consumption. Fleet-side only; **never produced at the API tier**, where no
      compute has run.
  * ``COST_ACKNOWLEDGED``   -- the caller accepted the uncosted commitment. Enough
      to *create* a run, never on its own a customer ACCEPT.
  * ``COST_NOT_ACKNOWLEDGED`` -- a frontier run with no acknowledgement -> a
      ``ValueError`` -> HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from api.services.cas_harness_compute_feasibility import ComputeFeasibilitySummary
from api.services.cas_harness_scale_planner import ScalePlan


CostAcknowledgmentStatus = Literal[
    "COST_METERED",
    "COST_ACKNOWLEDGED",
    "COST_NOT_ACKNOWLEDGED",
]


@dataclass(frozen=True)
class CostExposureSummary:
    """The honest cost-acknowledgment receipt carried out through the run record.

    Every quantity here is one the planner / gate (3) already computed -- the gate
    invents none. The fields CAS Harness *cannot* honestly produce (duration,
    throughput, dollars) are deliberately absent rather than guessed.
    """

    status: CostAcknowledgmentStatus
    acknowledged: bool
    # Always False at the API tier: real cost can only be known by running the
    # fleet and metering accelerator-hours, which the workers do, not this tier.
    # Mirrors the other gates' *_verified fields.
    cost_metered: bool
    # Real committed magnitude, surfaced from the plan (never invented):
    recommended_worker_count: int | None
    estimated_total_runtime_gb: float | None
    # Real declared fleet, surfaced from the gate-(3) envelope when present:
    declared_accelerator_count: int | None
    declared_accelerator_memory_gb: float | None
    effective_accelerator_count: int | None
    notice: str
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status != "COST_NOT_ACKNOWLEDGED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "acknowledged": self.acknowledged,
            "cost_metered": self.cost_metered,
            "recommended_worker_count": self.recommended_worker_count,
            "estimated_total_runtime_gb": self.estimated_total_runtime_gb,
            "declared_accelerator_count": self.declared_accelerator_count,
            "declared_accelerator_memory_gb": self.declared_accelerator_memory_gb,
            "effective_accelerator_count": self.effective_accelerator_count,
            "notice": self.notice,
            "reasons": list(self.reasons),
        }


def frontier_cost_requirement_notice() -> str:
    return (
        "A real frontier-scale (300B-4T, EXPERIMENTAL_NOT_VALIDATED) distributed CAS Harness "
        "run commits a large probe-worker fleet to load and hook a model of this size. CAS "
        "Harness does NOT estimate the run's wall-clock duration, throughput, or dollar cost, "
        "and does NOT bill, meter, or cap it -- the compute is entirely the caller's, on the "
        "caller's declared infrastructure, for a result CAS Harness has already labelled "
        "experimental and unvalidated. This gate requires the caller to explicitly acknowledge "
        "that caller-owned, unquoted cost; it never quotes a price, because the system models "
        "no duration or rate it could honestly quote. Real accelerator-hours are metered "
        "fleet-side, never at the API tier."
    )


def _magnitudes(
    plan: ScalePlan, compute: ComputeFeasibilitySummary | None
) -> dict[str, object]:
    return {
        "recommended_worker_count": plan.recommended_worker_count,
        "estimated_total_runtime_gb": plan.memory_estimate.estimated_total_runtime_gb,
        "declared_accelerator_count": (
            compute.declared_accelerator_count if compute is not None else None
        ),
        "declared_accelerator_memory_gb": (
            compute.declared_accelerator_memory_gb if compute is not None else None
        ),
        "effective_accelerator_count": (
            compute.effective_accelerator_count if compute is not None else None
        ),
    }


def summarize_cost_exposure(
    *,
    plan: ScalePlan,
    compute: ComputeFeasibilitySummary | None,
    acknowledged: bool,
) -> CostExposureSummary:
    """Resolve a cost acknowledgement to its honest tri-state summary.

    Acknowledged -> ``COST_ACKNOWLEDGED`` (never ``COST_METERED`` here; metering
    happens fleet-side). Not acknowledged -> ``COST_NOT_ACKNOWLEDGED`` with a reason
    that surfaces the real committed magnitude and the uncosted-by-design terms, and
    points the caller at either the acknowledgement flag or a below-frontier model.
    """

    magnitudes = _magnitudes(plan, compute)
    reasons: list[str] = []

    if not acknowledged:
        worker_count = magnitudes["recommended_worker_count"]
        runtime_gb = magnitudes["estimated_total_runtime_gb"]
        reasons.append(
            f"a real frontier-scale (EXPERIMENTAL_NOT_VALIDATED) run commits {worker_count} "
            f"probe workers to hold ~{runtime_gb} GB of model+activation memory across the "
            "declared fleet, at a compute cost CAS Harness does not estimate, quote, bill, or "
            "cap. Set accept_frontier_compute_cost=true to acknowledge that caller-owned, "
            "unquoted cost for an experimental result, or audit a below-frontier (<=300B) "
            "model where the committed fleet is modest."
        )

    status: CostAcknowledgmentStatus = (
        "COST_NOT_ACKNOWLEDGED" if reasons else "COST_ACKNOWLEDGED"
    )
    return CostExposureSummary(
        status=status,
        acknowledged=acknowledged,
        cost_metered=False,
        recommended_worker_count=magnitudes["recommended_worker_count"],  # type: ignore[arg-type]
        estimated_total_runtime_gb=magnitudes["estimated_total_runtime_gb"],  # type: ignore[arg-type]
        declared_accelerator_count=magnitudes["declared_accelerator_count"],  # type: ignore[arg-type]
        declared_accelerator_memory_gb=magnitudes["declared_accelerator_memory_gb"],  # type: ignore[arg-type]
        effective_accelerator_count=magnitudes["effective_accelerator_count"],  # type: ignore[arg-type]
        notice=frontier_cost_requirement_notice(),
        reasons=tuple(reasons),
    )


def validate_frontier_cost_acknowledgment(
    *,
    plan: ScalePlan,
    compute: ComputeFeasibilitySummary | None,
    acknowledged: bool,
) -> CostExposureSummary:
    """Raise ``ValueError`` (-> HTTP 422) unless a frontier run's cost is acknowledged.

    Frontier-only: enforced for ``EXPERIMENTAL_NOT_VALIDATED`` plans, because the
    committed fleet -- and therefore the caller-owned cost -- is substantial only at
    the frontier. Below that rung the commitment is modest and a volunteered
    acknowledgement is merely recorded, never required.
    """

    summary = summarize_cost_exposure(plan=plan, compute=compute, acknowledged=acknowledged)
    if not summary.accepted:
        raise ValueError(
            "distributed CAS Harness audit refused: frontier compute cost not acknowledged -- "
            + " ".join(summary.reasons)
        )
    return summary
