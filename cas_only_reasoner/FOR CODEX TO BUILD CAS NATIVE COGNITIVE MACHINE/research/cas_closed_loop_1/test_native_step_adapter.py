"""Focused AWS tests for the adapter; no model or protected fixtures."""
from dataclasses import replace

import pytest

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import create_problem
from cncm.compound_profile import CompoundProfile, SOURCE_FILES, authority_policy
from research.cas_closed_loop_1.native_step_adapter import (
    GrantRefused, NativeStepFailed, execute_grant, grant_for, runtime_location,
)


@pytest.fixture
def machine():
    # This fixture follows the existing native kernel unit-test profile. It is
    # a public adapter test, not the later actual-source demonstration.
    profile = CompoundProfile(tuple((name, 1, digest({"simulated_source": name}))
                                    for name in SOURCE_FILES), digest(authority_policy()))
    machine = CompoundMachine(profile, trusted_ingress=())
    machine.start(create_problem({"a": "2", "b": "3", "c": "5", "d": "7", "e": "35"}))
    return machine


def test_disabled_actuator_retains_allocation_without_execution(machine):
    before = machine.state
    receipt = execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True,
                                              actuator_enabled=False))
    assert receipt["I_allocated"] == 1 and receipt["I_executed"] == 0
    assert receipt["native_event_count"] == 0 and machine.state == before
    assert receipt["charged_native_policy_units"] == {"instructions": 0, "checker_calls": 0}
    assert receipt["asom"] is None and receipt["diagnostic_availability"] == "UNASSESSED"


def test_zero_grant_does_not_make_native_call(machine):
    receipt = execute_grant(machine, grant_for(machine, calls=0, allow_acquisition=True))
    assert receipt["I_executed"] == 0 and receipt["native_event_count"] == 0
    assert receipt["before"]["state_hash"] == receipt["after"]["state_hash"]


def test_granted_step_observes_native_events_and_stale_reuse_is_refused(machine):
    grant = grant_for(machine, calls=1, allow_acquisition=True)
    receipt = execute_grant(machine, grant)
    assert receipt["I_executed"] == 1 and receipt["native_event_count"] > 0
    assert receipt["native_event_refs"][-1]["post_state_hash"] == machine.state.state_hash
    state = machine.state
    with pytest.raises(GrantRefused, match="STALE_OR_FOREIGN_GRANT"):
        execute_grant(machine, grant)
    assert machine.state == state
    assert receipt["actual_primitive_work"] is None  # reservations are not measured instructions
    assert receipt["semantic_verdict"] == "NOT_INFERRED_BY_ADAPTER"


@pytest.mark.parametrize("calls", [True, -1, 2, 1.0])
def test_invalid_grant_never_reaches_executor(machine, calls):
    before = machine.state
    with pytest.raises(GrantRefused):
        grant_for(machine, calls=calls, allow_acquisition=True)
    assert machine.state == before


def test_foreign_episode_refused_before_work(machine):
    grant = replace(grant_for(machine, calls=1, allow_acquisition=True), run_id="foreign-run")
    before = machine.state
    with pytest.raises(GrantRefused, match="STALE_OR_FOREIGN_GRANT"):
        execute_grant(machine, grant)
    assert machine.state == before


def test_native_error_keeps_observed_events_and_never_reports_success(machine, monkeypatch):
    original = CompoundMachine.advance

    def fail_after_step(self, **kwargs):
        original(self, **kwargs)
        raise RuntimeError("synthetic post-step fault")

    monkeypatch.setattr(CompoundMachine, "advance", fail_after_step)
    with pytest.raises(NativeStepFailed) as caught:
        execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True))
    receipt = caught.value.receipt
    assert receipt["execution_status"] == "INVALID_NATIVE_ERROR"
    assert receipt["I_executed"] == 1 and receipt["native_event_count"] > 0
    assert receipt["after"]["state_hash"] == machine.state.state_hash
    assert receipt["charged_native_policy_units"]["instructions"] >= 0
    assert receipt["semantic_verdict"] == "NOT_INFERRED_BY_ADAPTER"


def test_runtime_location_is_detached_and_has_no_coordinate_return_authority(machine):
    location = runtime_location(machine)
    assert location["profile_coordinates"] is None and location["atlas_binding"] is None
    assert location["authority"] == "READ_ONLY_LOCATION_NOT_A_RESUME_TOKEN"
    original = machine.state
    location["current_native_budget"].clear()
    location["frames"].append({"return_address": "nearest-flower"})
    assert machine.state == original
