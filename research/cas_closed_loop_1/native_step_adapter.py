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
import threading
import time

from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundFrame
from cncm.compound_profile import load_compound_profile
from cncm.model import TerminalStatus
from cncm.rpa_compound_adapter import VIEW_SCHEMA, _catalog, work_from_catalog
from cncm.rpa_model import CONTEXT_SCHEMA


PROFILE = "cas.closed-loop.native-stage/0.1"
UNIT = "native_host_step_invocation"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ADVANCE = CompoundMachine.advance
_ADVANCE_CODE = _ADVANCE.__code__
RETURN_IDENTITY_FIELDS = (
    "episode/run", "branch", "source_snapshot", "root_goal", "root_call_occurrence",
    "immediate_parent_call", "frame_or_continuation", "saved_resume_stage",
    "inputs_digest", "source_profile", "bias_version_at_suspension",
)
ATLAS_ADDRESS_SCHEMA = "cas.closed-loop.atlas-address/0.1"
ATLAS_BINDING_SCHEMA = "cas.closed-loop.atlas-binding/0.1"
ATLAS_RESOLUTION_SCHEMA = "cas.closed-loop.atlas-address-resolution/0.1"
ATLAS_ADDRESS_AUTHORITY = "READ_ONLY_ADDRESS_NOT_A_RESUME_TOKEN"
ATLAS_ADDRESS_FIELDS = (
    "schema", "run_id", "branch", "source_profile", "root_goal", "root_call_occurrence",
    "suspension", "snapshot_node_id", "atlas_context", "waiting_state_node_id",
    "waiting_atlas_context", "frame_node_id", "continuation", "profile_coordinates", "authority",
)
_PUSH_INTENTS = ("PUSH_COMPOUND_ACQUISITION", "PUSH_PRIMITIVE_ACQUISITION")


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


class AtlasAddressRefused(ValueError):
    """An atlas address cannot be built or resolved; the reason is the message."""


def verify_receipt(receipt):
    return (type(receipt) is dict
            and type(receipt.get("I_allocated")) is int
            and type(receipt.get("I_executed")) is int
            and 0 <= receipt["I_executed"] <= receipt["I_allocated"] <= 1
            and receipt.get("receipt_digest") ==
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
        relative = row["destination"]
        name = None
        if relative.startswith("cncm/") and relative.endswith(".py"):
            name = relative[:-3].replace("/", ".").removesuffix(".__init__")
        elif relative == "compiler_ohm.py":
            name = "compiler_ohm"
        elif relative.startswith("pcba/") and relative.count("/") == 1 and relative.endswith(".py"):
            name = Path(relative).stem
        if name is not None:
            loaded = sys.modules.get(name)
            if loaded is not None and Path(loaded.__file__).resolve() != runtime / relative:
                raise GrantRefused("UNADMITTED_DEPENDENCY_LOCATION")
        raw = (runtime / row["destination"]).read_bytes()
        if len(raw) != row["bytes"] or sha256(raw).hexdigest() != row["sha256"]:
            raise GrantRefused("SOURCE_MANIFEST_MISMATCH")
    profile = load_compound_profile()
    if machine.profile != profile:
        raise GrantRefused("UNADMITTED_SOURCE_PROFILE")
    return {"source_manifest_digest": digest(manifest),
            "profile_digest": profile.profile_digest,
            "problem_hash": machine.problem.input_hash}


def primitive_work_for_events(machine, events):
    """Join native executor reports, never substitute grants or reservations.

    The upstream catalog joins run/tick/intent. Validate the native state and
    its whole trace before reading the state-owned records, then bind each result
    to a sealed event ID/hash in that validated trace. Missing report counters
    remain unknown; ordinary inference and wrapper work are outside this meter.
    """
    _require_machine(machine)
    try:
        observed = machine.result()
    except Exception as error:
        raise InvalidNativeObservation("WORK_STATE_HISTORY_INVALID", error) from error
    keys = ("primitive_instructions", "original_checks", "linear_checks")
    state = observed.final_state
    catalog = _catalog((*state.native_records, *state.semantic_records, *state.compound_records))
    reports = {row["report_digest"]: row["body"] for row in catalog["reports"]}
    actual_events = {(e.event_id, e.event_hash): e for e in observed.trace}
    totals = dict.fromkeys(keys, 0)
    rows, seen, unknown = [], set(), []
    for event in events:
        pair = (event.event_id, event.event_hash)
        if (pair in seen or pair not in actual_events or not event.sealed
                or event.event_hash != event.computed_hash()
                or event != actual_events[pair]):
            raise InvalidNativeObservation("WORK_EVENT_IDENTITY_INVALID")
        seen.add(pair)
        wire = event.to_dict()
        ids = {intent.intent_id for intent in event.proposed_intents}
        selected = [row for row in catalog["records"] if row["kind"] == "WORK_RESERVATION"
                    and row["body"].get("run_id") == event.run_id
                    and row["body"].get("tick") == event.logical_tick - 1
                    and row["body"].get("intent_id") in ids]
        refs = sorted(row["record_digest"] for row in selected)
        work = work_from_catalog(catalog, refs, wire)
        missing = []
        for row in selected:
            observed = [reports[ref["report_digest"]] for ref in row["report_refs"]]
            if not any("actual_work" in report or "cost" in report for report in observed):
                missing.append(row["record_digest"])
        unknown.extend(missing)
        for key in keys:
            totals[key] += work[key]
        rows.append({"event_id": event.event_id, "event_hash": event.event_hash,
                     "work_record_digests": refs, "work": work, "unmeasured_records": missing})
    return {"status": "JOINED_PARTIAL" if unknown else "JOINED",
            "measured_totals": totals, "unmeasured_records": unknown,
            "complete_totals": None if unknown else totals.copy(), "events": rows,
            "catalog_digest": catalog["catalog_digest"],
            "catalog_state_binding": {"run_id": state.run_id, "state_hash": state.state_hash,
                                      "trace_head": state.trace_head, "logical_tick": state.logical_tick},
            "provenance": "NATIVE_EXECUTOR_REPORTS_JOINED_BY_RUN_TICK_INTENT_AND_SEALED_EVENT",
            "scope": "Native primitive and original/linear check counters; excludes ordinary reasoning and orchestration."}


def grant_for(machine, *, calls, allow_acquisition, actuator_enabled=True):
    """Bind a proposal to the current snapshot. This does not execute work."""
    _require_machine(machine)
    try:
        machine.result()  # Native validation of the full existing chain and current state.
    except Exception as error:
        raise InvalidNativeObservation("EXISTING_NATIVE_HISTORY_INVALID", error) from error
    state = machine.state
    return StepGrant(state.run_id, state.state_hash, state.logical_tick, calls,
                     allow_acquisition, actuator_enabled, digest(admission_for(machine)))


def runtime_location(machine):
    """Read exact native identities; do not choose or execute a return target.

    This is the runtime half of the later atlas binding. No fabricated atlas
    node or profile is supplied. The existing native frame owns its return.
    """
    _require_machine(machine)
    try:
        observed = machine.result()
    except Exception as error:
        raise InvalidNativeObservation("EXISTING_NATIVE_HISTORY_INVALID", error) from error
    state = machine.state
    root = state.compound_call
    def identity(frame):
        matches = []
        for event in machine.coordinator.trace.events:
            for intent in event.proposed_intents:
                if (intent.intent_id in event.authorized_intent_ids
                        and intent.intent_type.value in (
                            "PUSH_COMPOUND_ACQUISITION", "PUSH_PRIMITIVE_ACQUISITION")
                        and intent.mutation_dict().get("frame", {}).get("frame_id") == frame.frame_id):
                    matches.append(event.pre_state_hash)
        if len(matches) != 1:
            raise InvalidNativeObservation("SUSPENSION_EVENT_NOT_UNIQUE")
        suspension = matches[0]
        return {
            "episode/run": state.run_id,
            "branch": "branch-main",  # CompoundCoordinator's explicit single-branch profile.
            "source_snapshot": suspension,
            "root_goal": machine.problem.reasoning.goal_id,
            "root_call_occurrence": root.call_id if root else None,
            "immediate_parent_call": ({"call_id": frame.call_id,
                                       "call_digest": frame.parent_call_digest}),
            "frame_or_continuation": frame.to_dict(),
            "saved_resume_stage": frame.resume_stage,
            "inputs_digest": root.inputs_digest if root else None,
            "source_profile": machine.profile.profile_digest,
            "bias_version_at_suspension": suspension,
        }
    identities = [identity(frame) for frame in state.rpm_stack]
    # Snapshot-bound atlas addresses for the same live frames, in the same order.
    # None when no frame exists: no suspension means no address, as no return identity.
    addresses = [_atlas_address(machine, observed, frame) for frame in state.rpm_stack]
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
        "return_identity": identities[-1] if identities else None,
        "frame_identities": identities,
        "bias_version_basis": "SEALED_PRE_STATE_HASH_INCLUDES_BIAS_NOT_A_SEPARATE_BIAS_COUNTER",
        "current_native_budget": state.native_budget.to_dict(),
        "atlas_binding": ({"schema": ATLAS_BINDING_SCHEMA, "frames": addresses,
                           "authority": ATLAS_ADDRESS_AUTHORITY} if addresses else None),
        "profile_coordinates": None,
        "authority": "READ_ONLY_LOCATION_NOT_A_RESUME_TOKEN",
    }
    return {**body, "location_digest": digest(body)}


# --- Snapshot-bound atlas addresses (return-address addendum RPA-RETURN-1) ---
# An exact address names episode, branch, source snapshot, root goal, call
# occurrence and saved continuation, reusing existing runtime identifiers and
# the atlas's snapshot-bound node scheme from the pinned rpa_compound_adapter:
# 'state-<hash>' with AtlasContext(run, VIEW_SCHEMA, 'observation-<hash>',
# 'logical-tick:<n>', n) and 'frame-<frame_id>' for live frames. The address
# is a lookup key. It grants nothing: nothing here resumes, dispatches,
# commits or advances; the existing CompoundCoordinator remains the writer.
# Profile coordinates and view focus are never inputs. There is no
# nearest-node fallback: exact match or a named refusal.


def _atlas_require(condition, reason):
    if not condition:
        raise AtlasAddressRefused(reason)


def _atlas_context(run_id, tick, state_hash):
    return {"context_id": run_id, "model_version": VIEW_SCHEMA, "observation_id": "observation-" + state_hash,
            "observation_time": "logical-tick:" + str(tick), "record_version": tick}


def _suspension_event(observed, frame):
    """The unique authorized push event whose proposed frame is exactly this frame."""
    matches = []
    for event in observed.trace:
        for intent in event.proposed_intents:
            if (intent.intent_id in event.authorized_intent_ids and intent.intent_type.value in _PUSH_INTENTS
                    and intent.mutation_dict().get("frame") == frame.to_dict()):
                matches.append(event)
    _atlas_require(len(matches) == 1, "SUSPENSION_EVENT_NOT_UNIQUE")
    event = matches[0]
    _atlas_require(event.sealed and event.event_hash == event.computed_hash(), "SUSPENSION_EVENT_UNSEALED")
    return event


def _atlas_address(machine, observed, frame):
    state = observed.final_state
    _atlas_require(type(frame) is CompoundFrame and any(row == frame for row in state.rpm_stack), "FRAME_NOT_LIVE")
    event = _suspension_event(observed, frame)
    root = state.compound_call
    body = {
        "schema": ATLAS_ADDRESS_SCHEMA,
        "run_id": state.run_id,
        "branch": "branch-main",
        "source_profile": machine.profile.profile_digest,
        "root_goal": machine.problem.reasoning.goal_id,
        "root_call_occurrence": root.call_id if root else None,
        "suspension": {"event_id": event.event_id, "event_hash": event.event_hash,
                       "logical_tick": event.logical_tick, "pre_state_hash": event.pre_state_hash,
                       "post_state_hash": event.post_state_hash},
        "snapshot_node_id": "state-" + event.pre_state_hash,
        "atlas_context": _atlas_context(state.run_id, event.logical_tick - 1, event.pre_state_hash),
        "waiting_state_node_id": "state-" + event.post_state_hash,
        "waiting_atlas_context": _atlas_context(state.run_id, event.logical_tick, event.post_state_hash),
        "frame_node_id": "frame-" + frame.frame_id,
        "continuation": {**frame.to_dict(), "frame_digest": digest(frame.to_dict())},
        "profile_coordinates": None,
        "authority": ATLAS_ADDRESS_AUTHORITY,
    }
    return {**body, "address_digest": digest(body)}


def _validated_result(machine):
    _require_machine(machine)
    try:
        return machine.result()  # native validation of the whole chain and current state
    except Exception as error:
        raise AtlasAddressRefused("NATIVE_HISTORY_INVALID") from error


def atlas_address_for_frame(machine, frame):
    """Exact, snapshot-bound address of one live acquisition frame."""
    return _atlas_address(machine, _validated_result(machine), frame)


def atlas_address_chain(machine):
    """Addresses for every live frame, innermost last, plus the root reference."""
    observed = _validated_result(machine)
    state = observed.final_state
    root = state.compound_call
    return {"schema": "cas.closed-loop.atlas-address-chain/0.1", "run_id": state.run_id,
            "state_hash": state.state_hash, "logical_tick": state.logical_tick,
            "root_goal": machine.problem.reasoning.goal_id,
            "root_call_occurrence": root.call_id if root else None,
            "frames": [_atlas_address(machine, observed, frame) for frame in state.rpm_stack],
            "authority": ATLAS_ADDRESS_AUTHORITY}


def check_atlas_address(address):
    _atlas_require(type(address) is dict and set(address) == set(ATLAS_ADDRESS_FIELDS) | {"address_digest"}, "ADDRESS_FIELDS_INVALID")
    _atlas_require(address["schema"] == ATLAS_ADDRESS_SCHEMA and address["authority"] == ATLAS_ADDRESS_AUTHORITY, "ADDRESS_SCHEMA_INVALID")
    body = {key: value for key, value in address.items() if key != "address_digest"}
    _atlas_require(address["address_digest"] == digest(body), "ADDRESS_DIGEST_MISMATCH")
    suspension = address["suspension"]
    _atlas_require(type(suspension) is dict and set(suspension) == {"event_id", "event_hash", "logical_tick", "pre_state_hash", "post_state_hash"}
                   and all(_SHA.fullmatch(suspension[key]) for key in ("event_hash", "pre_state_hash", "post_state_hash"))
                   and type(suspension["logical_tick"]) is int and suspension["logical_tick"] >= 1, "ADDRESS_SUSPENSION_INVALID")
    _atlas_require(address["snapshot_node_id"] == "state-" + suspension["pre_state_hash"]
                   and address["waiting_state_node_id"] == "state-" + suspension["post_state_hash"]
                   and address["frame_node_id"] == "frame-" + address["continuation"]["frame_id"], "ADDRESS_NODE_IDS_INCONSISTENT")
    _atlas_require(address["profile_coordinates"] is None, "PROFILE_COORDINATES_HAVE_NO_ADDRESS_ROLE")
    return address


def resolve_atlas_address(view, address):
    """Resolve an address against a rendered atlas view: exact match or a named refusal.

    Focus, hypothesis handle and layout of the view are ignored. The result
    grants nothing; it names nodes for inspection only.
    """
    check_atlas_address(address)
    _atlas_require(type(view) is dict and view.get("schema_version") == VIEW_SCHEMA, "ATLAS_VIEW_REQUIRED")
    suspension, continuation = address["suspension"], address["continuation"]
    frame = {key: value for key, value in continuation.items() if key != "frame_digest"}
    events = [row["event"] for row in view["timeline"] if row["event"]["event_hash"] == suspension["event_hash"]]
    _atlas_require(len(events) == 1, "SUSPENSION_EVENT_NOT_IN_VIEW")
    event = events[0]
    _atlas_require(event["event_id"] == suspension["event_id"] and event["logical_tick"] == suspension["logical_tick"]
                   and event["pre_state_hash"] == suspension["pre_state_hash"] and event["post_state_hash"] == suspension["post_state_hash"]
                   and event["run_id"] == address["run_id"], "SUSPENSION_EVENT_MISMATCH")
    pushed = [intent for intent in event["proposed_intents"] if intent["intent_id"] in event["authorized_intent_ids"]
              and intent["intent_type"] in _PUSH_INTENTS and intent["proposed_mutation"].get("frame") == frame]
    _atlas_require(len(pushed) == 1, "SUSPENSION_EVENT_FRAME_MISMATCH")
    nodes = {node["node_id"]: node for node in view["atlas"]["nodes"]}  # exact keys only; no nearest lookup
    snapshot = nodes.get(address["snapshot_node_id"])
    _atlas_require(snapshot is not None, "SNAPSHOT_NODE_NOT_FOUND")
    _atlas_require(snapshot["kind"] == "state" and snapshot["context"] == {"schema_version": CONTEXT_SCHEMA, **address["atlas_context"]}
                   and dict(snapshot["fields"]).get("state_hash") == suspension["pre_state_hash"], "SNAPSHOT_NODE_MISMATCH")
    waiting = nodes.get(address["waiting_state_node_id"])
    _atlas_require(waiting is not None, "WAITING_NODE_NOT_FOUND")
    _atlas_require(waiting["kind"] == "state" and waiting["context"] == {"schema_version": CONTEXT_SCHEMA, **address["waiting_atlas_context"]}
                   and dict(waiting["fields"]).get("state_hash") == suspension["post_state_hash"]
                   and suspension["event_hash"] in waiting["evidence_refs"], "WAITING_NODE_MISMATCH")
    live = any(row == frame for row in view["native"]["frames"])
    frame_node = nodes.get(address["frame_node_id"])
    if live:
        expected = [[key, value if type(value) is str else canonical_json(value)] for key, value in sorted(frame.items())]
        _atlas_require(frame_node is not None and [list(row) for row in frame_node["fields"]] == expected, "LIVE_FRAME_NODE_MISSING_OR_CHANGED")
        status = "RESOLVED_LIVE_FRAME"
    else:
        _atlas_require(frame_node is None, "STALE_FRAME_NODE_PRESENT")
        status = "RESOLVED_HISTORICAL_FRAME_NOT_LIVE"
    return {"schema": ATLAS_RESOLUTION_SCHEMA, "status": status, "address_digest": address["address_digest"],
            "snapshot_node_id": address["snapshot_node_id"], "waiting_state_node_id": address["waiting_state_node_id"],
            "frame_node_id": address["frame_node_id"] if live else None,
            "view_current_state_id": view["atlas"]["current_state_id"],
            "view_focus_node_id": view["atlas"]["focus_node_id"],
            "authority": "READ_ONLY_RESOLUTION_NO_RESUME_NO_DISPATCH"}


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
    entry_refused = False
    native_ns = 0
    fault = None
    if grant.calls and grant.actuator_enabled:
        advance = machine.advance
        if (not inspect.ismethod(advance) or advance.__self__ is not machine
                or advance.__func__ is not _ADVANCE or advance.__func__.__code__ is not _ADVANCE_CODE):
            raise GrantRefused("EXACT_NATIVE_DISPATCH_REQUIRED")
        call_started = time.monotonic_ns()
        if sys.getprofile() is not None or threading.getprofile() is not None:
            raise GrantRefused("HOST_ENTRY_METER_REQUIRES_FREE_PROFILE_HOOK")
        # Claim boundary: this meter counts entries into the pinned advance on
        # the window thread and on threads started inside the window, and it
        # invalidates the window on any foreign-thread Python activity or a
        # cleared hook. It is not isolation against arbitrary Python: code that
        # installs, replaces or clears interpreter hooks, or a thread that
        # already existed before the window, is outside the tested attacker
        # class (same-process, in-memory patching of native internals).
        window_thread = threading.get_ident()
        foreign_thread_seen = False
        hook_intact = False
        def entry_meter(frame, event, arg):
            nonlocal invoked, entry_refused, foreign_thread_seen
            if threading.get_ident() != window_thread:
                # The pinned native runtime is single-threaded. Any Python
                # activity on another thread inside the window invalidates it.
                foreign_thread_seen = True
            if (event == "call" and frame.f_code is _ADVANCE_CODE
                    and frame.f_locals.get("self") is machine):
                # The pinned native implementation does not re-enter advance.
                # An unexpected re-entry invalidates the whole measurement.
                if invoked >= grant.calls or threading.get_ident() != window_thread:
                    entry_refused = True
                    raise GrantRefused("HOST_ENTRY_ALLOCATION_EXCEEDED")
                invoked += 1
        try:
            attempted += 1
            sys.setprofile(entry_meter)
            threading.setprofile(entry_meter)  # threads started inside the window
            advance(allow_acquisition=grant.allow_acquisition)
        except Exception as error:
            fault = error
        finally:
            hook_intact = sys.getprofile() is entry_meter
            sys.setprofile(None)
            threading.setprofile(None)
            native_ns = time.monotonic_ns() - call_started
        if not hook_intact:
            # The hook was cleared or replaced inside the window (a callback
            # exception clears it; foreign code could too). Unmetered work may
            # have run, so never publish a usable count.
            entry_refused = True
        if foreign_thread_seen:
            entry_refused = True
    if entry_refused:
        # A callback exception clears CPython's profile hook. Code that catches
        # it could execute unmetered work, so never publish a usable count.
        raise InvalidNativeObservation("HOST_ENTRY_METER_INVALIDATED", fault) from fault
    if invoked > grant.calls:
        raise InvalidNativeObservation("HOST_ENTRY_ALLOCATION_EXCEEDED", fault) from fault
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
    actual_work = primitive_work_for_events(machine, events)
    if fault is not None:
        actual_work["status"] = "JOINED_PARTIAL_NATIVE_FAULT"
        actual_work["complete_totals"] = None
        actual_work["fault_work_status"] = "UNRECORDED_PRE_FAULT_WORK_UNKNOWN"
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
        "actual_primitive_work": actual_work,
        "actual_primitive_work_status": actual_work["status"],
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
