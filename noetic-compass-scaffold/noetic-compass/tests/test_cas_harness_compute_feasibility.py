"""Unit tests for the frontier compute-feasibility gate (frontier run-gate 3).

These exercise the honesty contract at the service layer, mirroring the
provenance (5), architecture (6), and probe (7) gates' declared-vs-verified split:

* A missing envelope, a non-positive accelerator count or memory, an aggregate
  that cannot cover the plan's runtime memory, or a per-accelerator size so small
  that even a fully fanned-out fleet (capped at ``MAX_WORKER_FANOUT``) cannot hold
  the model is ``COMPUTE_FEASIBILITY_INSUFFICIENT`` and the frontier validator
  raises (callers turn that into HTTP 422).
* A declared envelope whose capped, usable aggregate memory covers the plan's
  ``estimated_total_runtime_gb`` is ``COMPUTE_FEASIBILITY_DECLARED`` -- enough to
  create a run, never a verdict.
* ``COMPUTE_FEASIBILITY_VERIFIED`` is reserved for the fleet, the only place the
  model is actually sharded onto real accelerators, so it is never produced here.

The numbers are anchored to the planner's own arithmetic
(``cas_harness_scale_planner``): a 1000B bf16 model needs ``2000 GB`` of weights +
``18%`` activation overhead = ``2360 GB`` runtime; an 80 GB accelerator offers
``80 x 0.62 = 49.6 GB`` usable, so ``ceil(2360 / 49.6) = 48`` accelerators are
required. The same shared ``USABLE_MEMORY_FRACTION`` and ``MAX_WORKER_FANOUT`` the
planner uses to (silently) clamp worker fan-out are what this gate uses to refuse
honestly.
"""

from __future__ import annotations

import pytest

from api.services.cas_harness_compute_feasibility import (
    ComputeEnvelopeDeclaration,
    ComputeFeasibilitySummary,
    summarize_compute_feasibility,
    validate_frontier_compute_feasibility,
)
from api.services.cas_harness_scale_planner import (
    MAX_WORKER_FANOUT,
    USABLE_MEMORY_FRACTION,
    ScalePlan,
    ScalePlanRequest,
    build_scale_plan,
)


def _frontier_plan(
    *, parameter_count_b: float = 1000.0, precision: str = "bf16"
) -> ScalePlan:
    """A frontier-lane plan whose memory_estimate drives the gate's arithmetic."""

    return build_scale_plan(
        ScalePlanRequest(
            model_id="frontier-probe-x",
            parameter_count_b=parameter_count_b,
            precision=precision,  # type: ignore[arg-type]
            accept_experimental_frontier=True,
        )
    )


def _envelope(**overrides: object) -> ComputeEnvelopeDeclaration:
    """A sufficient compute envelope for a 1000B bf16 plan (64 x 80 GB)."""

    base: dict[str, object] = {
        "accelerator_count": 64,
        "accelerator_memory_gb": 80.0,
        "accelerator_type": "H100-80GB",
    }
    base.update(overrides)
    return ComputeEnvelopeDeclaration(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Missing / malformed / insufficient -> INSUFFICIENT
# ---------------------------------------------------------------------------


def test_missing_envelope_is_insufficient():
    summary = summarize_compute_feasibility(plan=_frontier_plan(), envelope=None)

    assert summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert summary.accepted is False
    assert summary.memory_sufficient is None
    assert summary.fit_verified is False
    assert summary.reasons  # an honest reason is always attached


@pytest.mark.parametrize("bad_count", [0, -1, -512])
def test_non_positive_accelerator_count_is_insufficient(bad_count):
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_count=bad_count)
    )

    assert summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert summary.declared_accelerator_count == bad_count
    assert any("accelerator_count must be positive" in r for r in summary.reasons)


@pytest.mark.parametrize("bad_memory", [0.0, -1.0, -80.0])
def test_non_positive_accelerator_memory_is_insufficient(bad_memory):
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_memory_gb=bad_memory)
    )

    assert summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert summary.declared_accelerator_memory_gb == bad_memory
    assert any("accelerator_memory_gb must be positive" in r for r in summary.reasons)


def test_too_few_accelerators_is_insufficient():
    # 16 x 80 GB -> 16 x 49.6 = 793.6 GB usable aggregate; the model needs 2360 GB.
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_count=16)
    )

    assert summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert summary.memory_sufficient is False
    assert summary.needed_runtime_gb == 2360.0
    assert summary.accelerators_required == 48
    assert summary.effective_accelerator_count == 16
    # The reason names the shortfall and the count the caller actually needs.
    assert any("Declare at least 48 accelerators" in r for r in summary.reasons)


def test_one_accelerator_short_is_insufficient():
    # 47 x 80 GB is exactly one short of the 48 required.
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_count=47)
    )

    assert summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert summary.accelerators_required == 48
    assert summary.memory_sufficient is False


def test_per_accelerator_too_small_for_fanout_cap_is_insufficient():
    # 4 GB cards -> 2.48 GB usable each; the model needs ceil(2360 / 2.48) = 952
    # accelerators, more than the MAX_WORKER_FANOUT cap. Even an unbounded count of
    # these cards cannot help: the planner clamps fan-out and under-resources every
    # shard. This is a distinct, honest refusal from "declare more accelerators".
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(),
        envelope=_envelope(accelerator_count=1_000_000, accelerator_memory_gb=4.0),
    )

    assert summary.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert summary.accelerators_required == 952
    assert summary.accelerators_required > MAX_WORKER_FANOUT
    assert summary.effective_accelerator_count == MAX_WORKER_FANOUT
    assert summary.fanout_capped is True
    assert any(f"{MAX_WORKER_FANOUT}-worker fan-out cap" in r for r in summary.reasons)
    assert any("Declare larger accelerators" in r for r in summary.reasons)


# ---------------------------------------------------------------------------
# Sufficient envelopes -> DECLARED (never VERIFIED at this tier)
# ---------------------------------------------------------------------------


def test_sufficient_envelope_is_declared_not_verified():
    summary = summarize_compute_feasibility(plan=_frontier_plan(), envelope=_envelope())

    assert summary.status == "COMPUTE_FEASIBILITY_DECLARED"
    assert summary.accepted is True
    assert summary.memory_sufficient is True
    assert summary.needed_runtime_gb == 2360.0
    assert summary.accelerators_required == 48
    assert summary.effective_accelerator_count == 64
    assert summary.available_aggregate_gb == pytest.approx(3174.4)
    assert summary.memory_headroom_gb == pytest.approx(814.4)
    assert summary.reasons == ()
    # Fleet-side load is the only place VERIFIED can be claimed.
    assert summary.status != "COMPUTE_FEASIBILITY_VERIFIED"
    assert summary.fit_verified is False


def test_exact_boundary_envelope_is_declared():
    # 48 accelerators is the minimum that fits; effective == required.
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_count=48)
    )

    assert summary.status == "COMPUTE_FEASIBILITY_DECLARED"
    assert summary.effective_accelerator_count == 48
    assert summary.accelerators_required == 48
    assert summary.memory_sufficient is True


def test_summary_records_the_shared_planner_constants():
    # The summary is self-describing: it carries the exact fraction and cap it used,
    # so a consumer can see the gate and planner cannot have drifted.
    summary = summarize_compute_feasibility(plan=_frontier_plan(), envelope=_envelope())

    assert summary.usable_memory_fraction == USABLE_MEMORY_FRACTION
    assert summary.fanout_cap == MAX_WORKER_FANOUT
    assert summary.per_accelerator_usable_gb == pytest.approx(80.0 * USABLE_MEMORY_FRACTION)


def test_fanout_capped_but_sufficient_notes_the_cap():
    # 600 accelerators declared, but the planner only ever uses 512. The model still
    # fits in 48, so the run is feasible -- but the gate is honest that only 512 of
    # the declared 600 will be used.
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_count=600)
    )

    assert summary.status == "COMPUTE_FEASIBILITY_DECLARED"
    assert summary.fanout_capped is True
    assert summary.effective_accelerator_count == MAX_WORKER_FANOUT
    assert f"only {MAX_WORKER_FANOUT} are used" in summary.notice


def test_precision_flips_feasibility_on_identical_hardware():
    # Same 16 x 80 GB fleet: too small for bf16 (needs 48), but fine for int4 (the
    # model's resident memory halves, so only 12 accelerators are required). The gate
    # reads the precision straight from the plan's memory estimate -- no invented math.
    hardware = _envelope(accelerator_count=16)

    bf16 = summarize_compute_feasibility(
        plan=_frontier_plan(precision="bf16"), envelope=hardware
    )
    int4 = summarize_compute_feasibility(
        plan=_frontier_plan(precision="int4"), envelope=hardware
    )

    assert bf16.status == "COMPUTE_FEASIBILITY_INSUFFICIENT"
    assert bf16.accelerators_required == 48
    assert int4.status == "COMPUTE_FEASIBILITY_DECLARED"
    assert int4.needed_runtime_gb == 590.0
    assert int4.accelerators_required == 12


def test_accelerator_type_is_recorded_when_present():
    summary = summarize_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope(accelerator_type="MI300X-192GB")
    )

    assert summary.accelerator_type == "MI300X-192GB"
    assert "MI300X-192GB" in summary.notice


def test_needed_runtime_matches_plan_memory_estimate():
    plan = _frontier_plan()
    summary = summarize_compute_feasibility(plan=plan, envelope=_envelope())

    assert summary.needed_runtime_gb == plan.memory_estimate.estimated_total_runtime_gb


def test_notice_is_honest_about_declared_not_validated():
    # A frontier run is EXPERIMENTAL_NOT_VALIDATED by definition; the gate must
    # certify physical fit WITHOUT implying the run will succeed or cost a given amount.
    summary = summarize_compute_feasibility(plan=_frontier_plan(), envelope=_envelope())

    assert "EXPERIMENTAL_NOT_VALIDATED" in summary.notice
    assert "NOT" in summary.notice


def test_summary_to_dict_round_trips_keys():
    summary = summarize_compute_feasibility(plan=_frontier_plan(), envelope=_envelope())
    data = summary.to_dict()

    assert data["status"] == "COMPUTE_FEASIBILITY_DECLARED"
    assert data["needed_runtime_gb"] == 2360.0
    assert data["accelerators_required"] == 48
    assert data["effective_accelerator_count"] == 64
    assert data["usable_memory_fraction"] == USABLE_MEMORY_FRACTION
    assert data["fanout_cap"] == MAX_WORKER_FANOUT
    assert data["fit_verified"] is False
    assert isinstance(data["reasons"], list)


def test_summary_is_a_frozen_dataclass():
    summary = summarize_compute_feasibility(plan=_frontier_plan(), envelope=_envelope())

    assert isinstance(summary, ComputeFeasibilitySummary)
    with pytest.raises(Exception):
        summary.status = "COMPUTE_FEASIBILITY_VERIFIED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Frontier validator: raises on INSUFFICIENT, returns on sufficient
# ---------------------------------------------------------------------------


def test_validate_frontier_compute_raises_without_envelope():
    with pytest.raises(ValueError) as exc:
        validate_frontier_compute_feasibility(plan=_frontier_plan(), envelope=None)

    assert "frontier-scale run refused" in str(exc.value)
    assert "insufficient compute envelope" in str(exc.value)


def test_validate_frontier_compute_raises_for_too_few_accelerators():
    with pytest.raises(ValueError) as exc:
        validate_frontier_compute_feasibility(
            plan=_frontier_plan(), envelope=_envelope(accelerator_count=16)
        )

    assert "frontier-scale run refused" in str(exc.value)
    assert "Declare at least 48 accelerators" in str(exc.value)


def test_validate_frontier_compute_returns_summary_for_sufficient_envelope():
    summary = validate_frontier_compute_feasibility(
        plan=_frontier_plan(), envelope=_envelope()
    )

    assert summary.status == "COMPUTE_FEASIBILITY_DECLARED"
    assert summary.memory_sufficient is True
