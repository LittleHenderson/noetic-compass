"""Unit tests for the frontier cost-acknowledgment gate (frontier run-gate 4).

These exercise the honesty contract at the service layer, mirroring the
provenance (5), architecture (6), probe (7), and compute (3) gates'
declared-vs-verified split -- with one defining constraint: this gate **never
quotes a price**. The planner models no wall-clock duration, throughput, or
dollar rate, so inventing a cost figure would violate the honesty contract. What
the gate *can* do is surface the real committed magnitude the planner already
computes (``recommended_worker_count``, ``estimated_total_runtime_gb``) plus the
real fleet the gate-(3) envelope declared, and require the caller to acknowledge
that caller-owned, unquoted cost for an ``EXPERIMENTAL_NOT_VALIDATED`` result.

* ``acknowledged`` -> ``COST_ACKNOWLEDGED``: enough to create a run, never on its
  own a verdict. ``cost_metered`` stays ``False`` -- real accelerator-hours are
  metered fleet-side, never at the API tier.
* not ``acknowledged`` at the frontier -> ``COST_NOT_ACKNOWLEDGED`` with a reason
  that surfaces the real magnitude and points at the acknowledgement flag or a
  below-frontier model; the validator raises ``ValueError`` (-> HTTP 422).
* ``COST_METERED`` is reserved for the fleet, the only place real compute runs, so
  it is never produced here.

The magnitudes are anchored to the planner's own arithmetic: a 1000B bf16 model
needs ``2000 GB`` weights + ``18%`` overhead = ``2360 GB`` runtime, and the
planner recommends ``84`` workers for it -- numbers this gate surfaces but never
invents.
"""

from __future__ import annotations

import dataclasses

import pytest

from api.services.cas_harness_compute_feasibility import (
    ComputeEnvelopeDeclaration,
    ComputeFeasibilitySummary,
    summarize_compute_feasibility,
)
from api.services.cas_harness_cost_acknowledgment import (
    CostExposureSummary,
    frontier_cost_requirement_notice,
    summarize_cost_exposure,
    validate_frontier_cost_acknowledgment,
)
from api.services.cas_harness_scale_planner import (
    ScalePlan,
    ScalePlanRequest,
    build_scale_plan,
)


def _frontier_plan(
    *, parameter_count_b: float = 1000.0, precision: str = "bf16"
) -> ScalePlan:
    return build_scale_plan(
        ScalePlanRequest(
            model_id="frontier-cost-x",
            parameter_count_b=parameter_count_b,
            precision=precision,  # type: ignore[arg-type]
            accept_experimental_frontier=True,
        )
    )


def _compute_summary(plan: ScalePlan, **overrides: object) -> ComputeFeasibilitySummary:
    base: dict[str, object] = {
        "accelerator_count": 64,
        "accelerator_memory_gb": 80.0,
        "accelerator_type": "H100-80GB",
    }
    base.update(overrides)
    envelope = ComputeEnvelopeDeclaration(**base)  # type: ignore[arg-type]
    return summarize_compute_feasibility(plan=plan, envelope=envelope)


# ---------------------------------------------------------------------------
# acknowledged -> ACKNOWLEDGED (never METERED at the API tier)
# ---------------------------------------------------------------------------


def test_acknowledged_is_acknowledged_not_metered() -> None:
    plan = _frontier_plan()
    summary = summarize_cost_exposure(
        plan=plan, compute=_compute_summary(plan), acknowledged=True
    )

    assert summary.status == "COST_ACKNOWLEDGED"
    assert summary.accepted is True
    assert summary.acknowledged is True
    # Real cost can only be known by metering a running fleet -- never at this tier.
    assert summary.cost_metered is False
    assert summary.reasons == ()


def test_acknowledged_surfaces_real_magnitudes_not_invented_ones() -> None:
    plan = _frontier_plan()
    summary = summarize_cost_exposure(
        plan=plan, compute=_compute_summary(plan), acknowledged=True
    )

    # Every magnitude is one the planner / gate (3) already computed.
    assert summary.recommended_worker_count == plan.recommended_worker_count
    assert (
        summary.estimated_total_runtime_gb
        == plan.memory_estimate.estimated_total_runtime_gb
    )
    assert summary.declared_accelerator_count == 64
    assert summary.declared_accelerator_memory_gb == 80.0
    assert summary.effective_accelerator_count == 64


def test_acknowledged_without_compute_envelope_still_surfaces_plan_magnitudes() -> None:
    # Below frontier a volunteered acknowledgement may arrive with no envelope; the
    # plan magnitudes are still real, the fleet ones are honestly null.
    plan = _frontier_plan()
    summary = summarize_cost_exposure(plan=plan, compute=None, acknowledged=True)

    assert summary.status == "COST_ACKNOWLEDGED"
    assert summary.recommended_worker_count == plan.recommended_worker_count
    assert summary.declared_accelerator_count is None
    assert summary.declared_accelerator_memory_gb is None
    assert summary.effective_accelerator_count is None


# ---------------------------------------------------------------------------
# not acknowledged -> NOT_ACKNOWLEDGED (the 422 case)
# ---------------------------------------------------------------------------


def test_not_acknowledged_is_refused_and_names_the_real_magnitude() -> None:
    plan = _frontier_plan()
    summary = summarize_cost_exposure(
        plan=plan, compute=_compute_summary(plan), acknowledged=False
    )

    assert summary.status == "COST_NOT_ACKNOWLEDGED"
    assert summary.accepted is False
    assert summary.acknowledged is False
    joined = " ".join(summary.reasons)
    # The refusal surfaces the real committed magnitude (not an invented dollar figure)
    assert str(plan.recommended_worker_count) in joined
    assert str(plan.memory_estimate.estimated_total_runtime_gb) in joined
    # ... names the remedy flag, and the below-frontier alternative.
    assert "accept_frontier_compute_cost" in joined
    assert "below-frontier" in joined


def test_refusal_never_quotes_a_price() -> None:
    plan = _frontier_plan()
    summary = summarize_cost_exposure(
        plan=plan, compute=_compute_summary(plan), acknowledged=False
    )
    joined = " ".join(summary.reasons).lower()
    # The honesty constraint: no invented currency / time figure in the refusal.
    assert "does not estimate, quote, bill, or cap" in joined
    assert "$" not in joined
    assert "per hour" not in joined


# ---------------------------------------------------------------------------
# notice / to_dict / immutability
# ---------------------------------------------------------------------------


def test_notice_is_honest_about_unquoted_caller_owned_cost() -> None:
    notice = frontier_cost_requirement_notice()
    assert "does NOT" in notice
    assert "caller's" in notice
    assert "never at the API tier" in notice
    # It must not pretend to price the run.
    assert "$" not in notice


def test_to_dict_round_trip_shape() -> None:
    plan = _frontier_plan()
    summary = summarize_cost_exposure(
        plan=plan, compute=_compute_summary(plan), acknowledged=False
    )
    payload = summary.to_dict()

    assert set(payload) == {
        "status",
        "acknowledged",
        "cost_metered",
        "recommended_worker_count",
        "estimated_total_runtime_gb",
        "declared_accelerator_count",
        "declared_accelerator_memory_gb",
        "effective_accelerator_count",
        "notice",
        "reasons",
    }
    assert payload["status"] == "COST_NOT_ACKNOWLEDGED"
    assert payload["cost_metered"] is False
    assert isinstance(payload["reasons"], list)
    assert payload["reasons"]  # non-empty for a refusal


def test_summary_is_frozen() -> None:
    plan = _frontier_plan()
    summary = summarize_cost_exposure(plan=plan, compute=None, acknowledged=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.status = "COST_METERED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# validate_frontier_cost_acknowledgment -- raises on NOT_ACKNOWLEDGED
# ---------------------------------------------------------------------------


def test_validate_returns_summary_when_acknowledged() -> None:
    plan = _frontier_plan()
    summary = validate_frontier_cost_acknowledgment(
        plan=plan, compute=_compute_summary(plan), acknowledged=True
    )
    assert isinstance(summary, CostExposureSummary)
    assert summary.status == "COST_ACKNOWLEDGED"


def test_validate_raises_when_not_acknowledged() -> None:
    plan = _frontier_plan()
    with pytest.raises(ValueError) as excinfo:
        validate_frontier_cost_acknowledgment(
            plan=plan, compute=_compute_summary(plan), acknowledged=False
        )
    message = str(excinfo.value)
    assert "frontier compute cost not acknowledged" in message
    assert "accept_frontier_compute_cost" in message
