"""One bounded host actuator; native state and return authority stay upstream.

This trusted-host adapter counts calls it actually invokes and observes the
resulting native events. Calls, transition events, reserved work and actual
primitive work are different quantities. No ASOM/calibration claim is made.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import inspect
import sys
import time

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_profile import load_compound_profile
from cncm.model import TerminalStatus


PROFILE = "cas.closed-loop.native-stage/0.1"
UNIT = "native_host_step_invocation"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ADVANCE_CODE = CompoundMachine.advance.__code__
RETURN_IDENTITY_FIELDS = (
    "episode/run", "branch", "source_snapshot", "root_goal", "root_call_occurrence",
    "immediate_parent_call", "frame_or_continuation", "saved_resume_stage",
    "inputs_digest", "source_profile", "bias_version_at_suspension",
)


class GrantRefused(ValueError):
    """No native call was made for this request."""


class NativeStepFailed(RuntimeError):
    """Native execution failed; the receipt retains observations, not a verdict."""

    def __init__(self, receipt):
        super().__init__("NATIVE_STEP_FAILED")
        self.receipt = receipt


class InvalidNativeObservation(RuntimeError):
    """No verified after-state or usable measurement exists for this window."""

    def __init__(self, reason, native_fault=None):
        super().__init__(reason)
        self.validation_error = reason
        self.native_error_type = type(native_fault).__name__ if native_fault else None
        self.measurement_status = "INVALID"


def verify_receipt(receipt):
    return (type(receipt) is dict and receipt.get("receipt_digest") ==
            digest({k: v for k, v in receipt.items() if k != "receipt_digest"}))


@dataclass(frozen=True, slots=True)
class StepGrant:
    run_id: str
    state_hash: str
    logical_tick: int
    calls: int
    allow_acquisition: bool
    actuator_enabled: bool = True
    admission_digest: str = ""

    def __post_init__(self):
        if type(self.run_id) is not str or not self.run_id or len(self.run_id) > 128:
            raise GrantRefused("RUN_ID_INVALID")
        if type(self.state_hash) is not str or _SHA.fullmatch(self.state_hash) is None:
            raise GrantRefused("STATE_HASH_INVALID")
        if type(self.logical_tick) is not int or self.logical_tick < 0:
            raise GrantRefused("TICK_INVALID")
        if type(self.calls) is not int or self.calls not in (0, 1):
            raise GrantRefused("ONE_HOST_CALL_MAXIMUM")
        if type(self.allow_acquisition) is not bool or type(self.actuator_enabled) is not bool:
            raise GrantRefused("ACTUATOR_FLAGS_INVALID")
        if type(self.admission_digest) is not str or _SHA.fullmatch(self.admission_digest) is None:
            raise GrantRefused("ADMISSION_DIGEST_INVALID")


def _require_machine(machine):
    if type(machine) is not CompoundMachine:
        raise GrantRefused("EXACT_COMPOUND_MACHINE_REQUIRED")


def admission_for(machine):
    """Bind actual dependency bytes, native profile, and the caller's problem."""
    _require_machine(machine)
    here = Path(__file__).resolve().parent
    manifest = json.loads((here / "SOURCE_BINDINGS.json").read_text())
    runtime = (here / "_runtime").resolve()
    module = sys.modules[CompoundMachine.__module__]
    if Path(module.__file__).resolve() != runtime / "cncm/compound_engine.py":
        raise GrantRefused("UNADMITTED_RUNTIME_LOCATION")
    for row in manifest["files"]:
        raw = (runtime / row["destination"]).read_bytes()
        if len(raw) != row["bytes"] or sha256(raw).hexdigest() != row["sha256"]:
            raise GrantRefused("SOURCE_MANIFEST_MISMATCH")
    profile = load_compound_profile()
    if machine.profile != profile:
        raise GrantRefused("UNADMITTED_SOURCE_PROFILE")
    return {"source_manifest_digest": digest(manifest),
            "profile_digest": profile.profile_digest,
            "problem_hash": machine.problem.input_hash}


def grant_for(machine, *, calls, allow_acquisition, actuator_enabled=True):
    """Bind a proposal to the current snapshot. This does not execute work."""
    _require_machine(machine)
    state = machine.state
    return StepGrant(state.run_id, state.state_hash, state.logical_tick, calls,
                     allow_acquisition, actuator_enabled, digest(admission_for(machine)))


def runtime_location(machine):
    """Read exact native identities; do not choose or execute a return target.

    This is the runtime half of the later atlas binding. No fabricated atlas
    node or profile is supplied. The existing native frame owns its return.
    """
    _require_machine(machine)
    state = machine.state
    root = state.compound_call
    def identity(frame):
        suspension = None
        if frame is not None:
            for event in machine.coordinator.trace.events:
                for intent in event.proposed_intents:
                    if (intent.intent_id in event.authorized_intent_ids
                            and intent.intent_type.value in (
                                "PUSH_COMPOUND_ACQUISITION", "PUSH_PRIMITIVE_ACQUISITION")
                            and intent.mutation_dict().get("frame", {}).get("frame_id") == frame.frame_id):
                        suspension = event.pre_state_hash
        return {
            "episode/run": state.run_id,
            "branch": "branch-main",  # CompoundCoordinator's explicit single-branch profile.
            "source_snapshot": suspension if frame is not None else state.state_hash,
            "root_goal": machine.problem.reasoning.goal_id,
            "root_call_occurrence": root.call_id if root else None,
            "immediate_parent_call": ({"call_id": frame.call_id,
                                       "call_digest": frame.parent_call_digest} if frame else None),
            "frame_or_continuation": frame.to_dict() if frame else None,
            "saved_resume_stage": frame.resume_stage if frame else None,
            "inputs_digest": root.inputs_digest if root else None,
            "source_profile": machine.profile.profile_digest,
            "bias_version_at_suspension": suspension,
        }
    identities = [identity(frame) for frame in state.rpm_stack]
    body = {
        "schema": "cas.closed-loop.runtime-location/0.1",
        "run_id": state.run_id,
        "source_profile": machine.profile.profile_digest,
        "state_hash": state.state_hash,
        "logical_tick": state.logical_tick,
        "problem_hash": machine.problem.input_hash,
        "root_goal": machine.problem.reasoning.goal_id,
        "root_call": root.to_dict() if root is not None else None,
        "frames": [frame.to_dict() for frame in state.rpm_stack],
        "return_identity": identities[-1] if identities else identity(None),
        "frame_identities": identities,
        "bias_version_basis": "SEALED_PRE_STATE_HASH_INCLUDES_BIAS_NOT_A_SEPARATE_BIAS_COUNTER",
        "current_native_budget": state.native_budget.to_dict(),
        "atlas_binding": None,
        "profile_coordinates": None,
        "authority": "READ_ONLY_LOCATION_NOT_A_RESUME_TOKEN",
    }
    return {**body, "location_digest": digest(body)}


def execute_grant(machine, grant):
    """Invoke at most one existing host step; never write native state directly.

    A call may produce several native events. That is why the allocation unit
    is a host invocation, not an instruction or transition event. Upstream
    coordinator budgets, checks, failure handling and commitment remain active.
    Returned dictionaries are observations; they cannot authorize replay/resume.
    """
    _require_machine(machine)
    if type(grant) is not StepGrant:
        raise GrantRefused("TYPED_GRANT_REQUIRED")
    began = time.monotonic_ns()
    started_utc = datetime.now(timezone.utc).isoformat()
    before = machine.state
    admission = admission_for(machine)
    if grant.admission_digest != digest(admission):
        raise GrantRefused("STALE_OR_FOREIGN_ADMISSION")
    if (grant.run_id, grant.state_hash, grant.logical_tick) != (
            before.run_id, before.state_hash, before.logical_tick):
        raise GrantRefused("STALE_OR_FOREIGN_GRANT")
    if before.halt_status is not TerminalStatus.RUNNING:
        raise GrantRefused("EPISODE_NOT_RUNNING")
    location_before = runtime_location(machine)
    old_events = tuple(machine.coordinator.trace.events)
    invoked = 0
    attempted = 0
    native_ns = 0
    fault = None
    if grant.calls and grant.actuator_enabled:
        call_started = time.monotonic_ns()
        if sys.getprofile() is not None:
            raise GrantRefused("HOST_ENTRY_METER_REQUIRES_FREE_PROFILE_HOOK")
        def entry_meter(frame, event, arg):
            nonlocal invoked
            if (event == "call" and frame.f_code is _ADVANCE_CODE
                    and frame.f_locals.get("self") is machine):
                invoked += 1
        try:
            advance = machine.advance
            inspect.signature(advance).bind(allow_acquisition=grant.allow_acquisition)
            attempted += 1
            sys.setprofile(entry_meter)
            advance(allow_acquisition=grant.allow_acquisition)
        except Exception as error:
            fault = error
        finally:
            sys.setprofile(None)
            native_ns = time.monotonic_ns() - call_started
    after = machine.state
    all_events = machine.coordinator.trace.events
    if all_events[:len(old_events)] != old_events:
        raise InvalidNativeObservation("NATIVE_TRACE_PREFIX_CHANGED", fault) from fault
    events = all_events[len(old_events):]
    previous_hash = before.state_hash
    previous_event_hash = old_events[-1].event_hash if old_events else ""
    previous_event_id = old_events[-1].event_id if old_events else None
    previous_tick = before.logical_tick
    for event in events:
        if (event.run_id != before.run_id or not event.sealed
                or event.event_hash != event.computed_hash()
                or event.pre_state_hash != previous_hash
                or event.previous_event_hash != previous_event_hash
                or event.parent_event_id != previous_event_id
                or event.logical_tick != previous_tick + 1):
            raise InvalidNativeObservation("NATIVE_EVENT_CHAIN_INVALID", fault) from fault
        previous_hash = event.post_state_hash
        previous_event_hash, previous_event_id, previous_tick = event.event_hash, event.event_id, event.logical_tick
    if (previous_hash != after.state_hash or after.state_hash != after.computed_hash()
            or after.trace_head != previous_event_hash or after.logical_tick != previous_tick):
        raise InvalidNativeObservation("NATIVE_STATE_NOT_BOUND_TO_OBSERVED_EVENTS", fault) from fault
    instructions = (before.native_budget.instructions_remaining
                    - after.native_budget.instructions_remaining)
    checkers = (before.native_budget.checker_calls_remaining
                - after.native_budget.checker_calls_remaining)
    if instructions < 0 or checkers < 0:
        raise InvalidNativeObservation("NATIVE_BUDGET_INCREASED_WITHIN_STEP", fault) from fault
    location_after = runtime_location(machine)
    elapsed_ns = time.monotonic_ns() - began
    receipt = {
        "schema": "cas.closed-loop.native-step-receipt/0.1",
        "profile": PROFILE,
        "admission": admission,
        "window": {"started_utc": started_utc, "elapsed_ns": elapsed_ns,
                   "native_call_ns": native_ns, "wrapper_observation_ns": elapsed_ns - native_ns},
        "unit": UNIT,
        "I_predicted": None,
        "I_allocated": grant.calls,
        "I_executed": invoked,
        "I_attempted": attempted,
        "entry_meter": "CPYTHON_CALL_EVENT_FOR_PINNED_COMPOUND_ADVANCE_CODE",
        "actuator_enabled": grant.actuator_enabled,
        "allow_acquisition": grant.allow_acquisition,
        "before": location_before,
        "after": location_after,
        "native_event_count": len(events),
        "native_event_refs": [{"event_id": e.event_id, "event_hash": e.event_hash,
                               "run_id": e.run_id, "logical_tick": e.logical_tick,
                               "pre_state_hash": e.pre_state_hash,
                               "post_state_hash": e.post_state_hash} for e in events],
        "charged_native_policy_units": {"instructions": instructions, "checker_calls": checkers},
        "actual_primitive_work": None,
        "actual_primitive_work_status": "NOT_JOINED_USE_EXISTING_EVENT_BOUND_CATALOG",
        "native_halt_status": after.halt_status.value,
        "native_commitment_status": after.commitment_state.decision_status,
        "diagnostic_availability": "UNASSESSED",
        "asom": None,
        "semantic_verdict": "NOT_INFERRED_BY_ADAPTER",
        "execution_status": "INVALID_NATIVE_ERROR" if fault else "OBSERVED",
        "observation_validation": "VALID_EVENT_CHAIN_STATE_AND_BUDGET",
        "error_type": type(fault).__name__ if fault else None,
        "limits": "Host invocation count is not total compute, calibrated attention or proof of task success.",
    }
    receipt["receipt_digest"] = digest(receipt)
    if fault is not None:
        raise NativeStepFailed(receipt) from fault
    return receipt
