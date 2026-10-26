"""Focused AWS tests for the adapter; no model or protected fixtures."""
from dataclasses import replace

import pytest

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import create_problem
from cncm.compound_profile import CompoundProfile, SOURCE_FILES, authority_policy, load_compound_profile
from research.cas_closed_loop_1.native_step_adapter import (
    GrantRefused, NativeStepFailed, InvalidNativeObservation, RETURN_IDENTITY_FIELDS,
    execute_grant, grant_for, runtime_location, verify_receipt, primitive_work_for_events,
)


@pytest.fixture
def machine():
    profile = load_compound_profile()
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
    assert receipt["actual_primitive_work"]["provenance"].startswith("NATIVE_EXECUTOR_REPORTS")
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
    assert receipt["observation_validation"] == "VALID_EVENT_CHAIN_STATE_AND_BUDGET"
    assert verify_receipt(receipt)
    assert receipt["actual_primitive_work"]["complete_totals"] is None
    assert receipt["actual_primitive_work"]["fault_work_status"] == "UNRECORDED_PRE_FAULT_WORK_UNKNOWN"
    assert receipt["semantic_verdict"] == "NOT_INFERRED_BY_ADAPTER"


def test_runtime_location_is_detached_and_has_no_coordinate_return_authority(machine):
    location = runtime_location(machine)
    assert location["profile_coordinates"] is None and location["atlas_binding"] is None
    assert location["authority"] == "READ_ONLY_LOCATION_NOT_A_RESUME_TOKEN"
    original = machine.state
    location["current_native_budget"].clear()
    location["frames"].append({"return_address": "nearest-flower"})
    assert machine.state == original


def test_all_eleven_identity_fields_and_suspended_snapshot_are_retained(machine):
    from cncm.model import TerminalStatus
    captured = {}
    measured = 0
    while machine.state.halt_status is TerminalStatus.RUNNING:
        location = runtime_location(machine)
        assert set(location["return_identity"]) == set(RETURN_IDENTITY_FIELDS)
        assert len(RETURN_IDENTITY_FIELDS) == 11
        for identity in location["frame_identities"]:
            frame_id = identity["frame_or_continuation"]["frame_id"]
            assert identity["source_snapshot"] is not None
            assert identity["bias_version_at_suspension"] == identity["source_snapshot"]
            if frame_id in captured:
                assert identity == captured[frame_id]
            captured[frame_id] = identity
        receipt = execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True))
        measured += receipt["actual_primitive_work"]["measured_totals"]["primitive_instructions"]
    assert len(captured) == 2
    assert measured > 0


def test_signature_failure_is_not_counted_as_entry(machine, monkeypatch):
    monkeypatch.setattr(CompoundMachine, "advance", lambda self: None)
    with pytest.raises(NativeStepFailed) as caught:
        execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True))
    receipt = caught.value.receipt
    assert receipt["I_attempted"] == receipt["I_executed"] == 0
    assert receipt["native_event_count"] == 0
    assert verify_receipt(receipt)


def test_receipt_content_digest_detects_alteration(machine):
    receipt = execute_grant(machine, grant_for(machine, calls=0, allow_acquisition=True))
    assert verify_receipt(receipt)
    receipt["I_executed"] = 1
    assert not verify_receipt(receipt)


def test_corrupt_post_fault_state_is_not_published_as_verified(machine, monkeypatch):
    original = CompoundMachine.advance
    def corrupt_then_fail(self, **kwargs):
        original(self, **kwargs)
        object.__setattr__(self.state, "state_hash", "0" * 64)
        raise RuntimeError("fault after corruption")
    monkeypatch.setattr(CompoundMachine, "advance", corrupt_then_fail)
    with pytest.raises(InvalidNativeObservation) as caught:
        execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True))
    assert caught.value.native_error_type == "RuntimeError"
    assert caught.value.measurement_status == "INVALID"
    assert not hasattr(caught.value, "receipt")


def test_simulated_profile_is_not_admitted():
    profile = CompoundProfile(tuple((name, 1, digest({"simulated_source": name}))
                                    for name in SOURCE_FILES), digest(authority_policy()))
    machine = CompoundMachine(profile, trusted_ingress=())
    machine.start(create_problem({"a": "2", "b": "3", "c": "5", "d": "7", "e": "35"}))
    with pytest.raises(GrantRefused, match="UNADMITTED_SOURCE_PROFILE"):
        grant_for(machine, calls=1, allow_acquisition=True)


def test_wrong_problem_admission_is_refused(machine):
    grant = replace(grant_for(machine, calls=1, allow_acquisition=True), admission_digest="0" * 64)
    with pytest.raises(GrantRefused, match="STALE_OR_FOREIGN_ADMISSION"):
        execute_grant(machine, grant)


def test_foreign_loaded_dependency_is_refused(machine, monkeypatch):
    import cncm.compound_kernel as kernel
    monkeypatch.setattr(kernel, "__file__", "foreign/cncm/compound_kernel.py")
    with pytest.raises(GrantRefused, match="UNADMITTED_DEPENDENCY_LOCATION"):
        grant_for(machine, calls=1, allow_acquisition=True)


def test_corrupt_existing_event_is_refused_even_for_zero_grant(machine):
    machine.advance()
    grant = grant_for(machine, calls=0, allow_acquisition=True)
    object.__setattr__(machine.coordinator.trace.events[0], "event_hash", "0" * 64)
    with pytest.raises(InvalidNativeObservation, match="EXISTING_NATIVE_HISTORY_INVALID"):
        execute_grant(machine, grant)


@pytest.mark.parametrize("enabled,calls", [(False, 1), (True, 0)])
def test_unexecuted_window_has_zero_measured_primitive_work(machine, enabled, calls):
    receipt = execute_grant(machine, grant_for(machine, calls=calls, allow_acquisition=True,
                                              actuator_enabled=enabled))
    work = receipt["actual_primitive_work"]
    assert work["status"] == "JOINED"
    assert work["complete_totals"] == {"primitive_instructions": 0, "original_checks": 0, "linear_checks": 0}
    assert work["events"] == []


def test_work_join_refuses_duplicate_and_changed_event(machine):
    machine.advance()
    event = machine.coordinator.trace.events[0]
    with pytest.raises(InvalidNativeObservation, match="WORK_EVENT_IDENTITY_INVALID"):
        primitive_work_for_events(machine, [event, event])
    with pytest.raises(InvalidNativeObservation, match="WORK_EVENT_IDENTITY_INVALID"):
        primitive_work_for_events(machine, [replace(event, event_hash="0" * 64)])
