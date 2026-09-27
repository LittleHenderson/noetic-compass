"""The return-address addendum's ten adapter-level cases, made executable.

Each test names the RETURN_ADDRESS_TEST_MAP.json row it answers
(`new_adapter_case_needed`) and the acceptance ids that row serves. The
addresses come from the leased adapter (native_step_adapter.py); the native
runtime is unmodified. Nothing here resumes, dispatches or commits.
"""
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundIntentType as C, create_problem
from cncm.compound_profile import load_compound_profile
from cncm.compound_recovery import recover_compound_journal
from cncm.model import ContractError, TerminalStatus
from cncm.rpa_compound_adapter import compound_atlas_from_journal
from cncm.rpa_model import AtlasSnapshot
from research.cas_closed_loop_1.control import controlled_step
from research.cas_closed_loop_1.native_step_adapter import (
    AtlasAddressRefused as AddressRefused, atlas_address_chain as address_chain,
    atlas_address_for_frame as address_for_frame, check_atlas_address as check_address,
    resolve_atlas_address as resolve_address, runtime_location)

HERE = Path(__file__).resolve().parent          # research/cas_closed_loop_1
RUNTIME = HERE / "_runtime"
REPO_ROOT = HERE.parents[1]
INPUTS = {"a": "2", "b": "3", "c": "5", "d": "7", "e": "35"}


def fresh():
    machine = CompoundMachine(load_compound_profile(), trusted_ingress=())
    machine.start(create_problem(INPUTS))
    return machine


def step_until(machine, predicate, limit=32):
    for _ in range(limit):
        if predicate(machine):
            return machine
        controlled_step(machine)
    raise AssertionError("condition not reached")


def two_frames(machine):
    return len(machine.state.rpm_stack) == 2


def concluded(machine):
    return machine.state.halt_status is not TerminalStatus.RUNNING


def view_of(machine):
    journal = machine.journal()
    return compound_atlas_from_journal(journal, trusted_genesis=machine.problem, trusted_ingress=(),
                                       expected_journal_digest=journal["journal_digest"], profile=machine.profile), journal


def resigned(address, **changes):
    """Tampered copy with a valid content digest, so refusals are semantic, not digest checks."""
    body = {key: value for key, value in deepcopy(address).items() if key != "address_digest"}
    for path, value in changes.items():
        target, *rest = path.split(".")
        if rest:
            body[target][rest[0]] = value
        else:
            body[target] = value
    return {**body, "address_digest": digest(body)}


@pytest.fixture
def suspended():
    """Public witness driven to two live acquisition frames (compound, then primitive)."""
    machine = step_until(fresh(), two_frames)
    return machine


# Row 1 (AT15, AT20): bind each waiting frame to its own snapshot/node address; return in dependency order.
def test_row1_two_nested_frames_bind_distinct_snapshot_addresses_and_return_to_exact_callers(suspended):
    machine = suspended
    outer, inner = machine.state.rpm_stack
    a_outer, a_inner = address_for_frame(machine, outer), address_for_frame(machine, inner)
    assert a_outer["continuation"]["depth"] == 1 and a_inner["continuation"]["depth"] == 2
    assert a_outer["continuation"]["resume_stage"] == "COMPOUND_APPLY" and a_inner["continuation"]["resume_stage"] == "COMPOUND_CONSTRUCT"
    assert a_outer["snapshot_node_id"] != a_inner["snapshot_node_id"]
    assert a_outer["frame_node_id"] != a_inner["frame_node_id"] and a_outer["address_digest"] != a_inner["address_digest"]
    assert a_outer["suspension"]["logical_tick"] < a_inner["suspension"]["logical_tick"]
    assert a_outer["root_call_occurrence"] == a_inner["root_call_occurrence"] == machine.state.compound_call.call_id
    view, _ = view_of(machine)
    assert resolve_address(view, a_outer)["status"] == "RESOLVED_LIVE_FRAME"
    assert resolve_address(view, a_inner)["status"] == "RESOLVED_LIVE_FRAME"
    step_until(machine, concluded)
    returns = [(intent.intent_type.value, intent.mutation_dict()["frame_id"]) for event in machine.coordinator.trace.events
               for intent in event.proposed_intents if intent.intent_id in event.authorized_intent_ids
               and intent.intent_type in (C.RETURN_PRIMITIVE, C.RETURN_COMPOUND)]
    assert returns == [("RETURN_PRIMITIVE", inner.frame_id), ("RETURN_COMPOUND", outer.frame_id)]
    assert machine.state.compound_call.status == "COMPLETE" and machine.state.compound_call.output == "3"
    final_view, _ = view_of(machine)
    assert resolve_address(final_view, a_outer)["status"] == "RESOLVED_HISTORICAL_FRAME_NOT_LIVE"
    assert resolve_address(final_view, a_inner)["status"] == "RESOLVED_HISTORICAL_FRAME_NOT_LIVE"


# Row 2 (AT16, AT17, AT19, AT27): a wrong atlas address cannot choose another native continuation.
def test_row2_wrong_address_cannot_select_another_continuation(suspended):
    machine = suspended
    outer, inner = machine.state.rpm_stack
    a_outer, a_inner = address_for_frame(machine, outer), address_for_frame(machine, inner)
    view, journal = view_of(machine)
    crossed = resigned(a_outer, continuation=a_inner["continuation"], frame_node_id=a_inner["frame_node_id"])
    with pytest.raises(AddressRefused, match="SUSPENSION_EVENT_FRAME_MISMATCH"):
        resolve_address(view, crossed)
    foreign_run = resigned(a_inner, run_id="compound-run-0000000000000000")
    with pytest.raises(AddressRefused, match="SUSPENSION_EVENT_MISMATCH"):
        resolve_address(view, foreign_run)
    import research.cas_closed_loop_1.native_step_adapter as module
    public = [name for name in dir(module) if not name.startswith("_")]
    assert not any(name.lower().startswith(("resume", "dispatch", "commit")) for name in public)
    assert machine.journal() == journal and len(machine.state.rpm_stack) == 2


# Row 3 (AT16, AT17, AT19, AT27): a repeated view event cannot dispatch a new native request.
def test_row3_repeated_resolution_dispatches_nothing(suspended):
    machine = suspended
    view, journal = view_of(machine)
    address = address_for_frame(machine, machine.state.rpm_stack[-1])
    before = (machine.state.state_hash, len(machine.coordinator.trace.events), machine.state.native_budget.to_dict())
    for _ in range(5):
        assert resolve_address(view, address)["status"] == "RESOLVED_LIVE_FRAME"
        assert address_chain(machine)["frames"][-1] == address
    assert (machine.state.state_hash, len(machine.coordinator.trace.events), machine.state.native_budget.to_dict()) == before
    assert machine.journal() == journal


# Row 4 (AT10, AT21, AT22): preserve the root/parent address chain across restart (fresh process).
def test_row4_address_chain_survives_fresh_process_recovery(suspended, tmp_path):
    machine = suspended
    chain = address_chain(machine)
    journal = machine.journal()
    (tmp_path / "journal.json").write_text(json.dumps(journal), encoding="utf-8")
    (tmp_path / "genesis.json").write_text(json.dumps(machine.problem.to_dict()), encoding="utf-8")
    code = """
import json, sys
runtime, root, work, expected = sys.argv[1:5]
sys.path.insert(0, runtime); sys.path.insert(0, root)
from cncm.compound_model import CompoundProblem
from cncm.compound_profile import load_compound_profile
from cncm.compound_recovery import recover_compound_journal
from research.cas_closed_loop_1.native_step_adapter import atlas_address_chain as address_chain
journal = json.load(open(work + '/journal.json'))
genesis = CompoundProblem.from_dict(json.load(open(work + '/genesis.json')))
machine = recover_compound_journal(journal, trusted_genesis=genesis, trusted_ingress=(), expected_journal_digest=expected, profile=load_compound_profile())
print(json.dumps(address_chain(machine)))
"""
    result = subprocess.run([sys.executable, "-c", code, str(RUNTIME), str(REPO_ROOT), str(tmp_path), journal["journal_digest"]],
                            capture_output=True, text=True, timeout=120, env={"PYTHONDONTWRITEBYTECODE": "1"})
    assert result.returncode == 0, result.stderr[-2000:]
    recovered = json.loads(result.stdout)
    assert recovered == chain
    assert [row["address_digest"] for row in recovered["frames"]] == [row["address_digest"] for row in chain["frames"]]
    assert recovered["root_call_occurrence"] == chain["root_call_occurrence"] and len(recovered["frames"]) == 2


# Row 5 (AT10, AT21, AT22): do not reconstruct budget from the suspended snapshot.
def test_row5_address_carries_no_budget_and_resume_uses_the_live_ledger(suspended):
    machine = suspended
    outer = machine.state.rpm_stack[0]
    address = address_for_frame(machine, outer)
    assert not {key for key in address if "budget" in key or "remaining" in key}
    entry = outer.entry_instruction_budget  # historical evidence recorded at suspension
    step_until(machine, concluded)
    assert machine.state.native_budget.instructions_remaining < entry
    assert address["continuation"]["entry_instruction_budget"] == entry  # history retained, not spend authority


# Row 6 (AT24, AT25, AT26): equal or missing profiles cannot merge two call occurrences.
def test_row6_equal_or_missing_profiles_never_merge_callers(suspended):
    machine = suspended
    # Determinism, recorded: a second machine started from byte-identical inputs reaches the
    # identical run_id, state hashes and frame identities. That is the same episode identity
    # (content-bound), not a second caller, so its addresses coincide by construction.
    twin = step_until(fresh(), two_frames)
    assert twin.state.run_id == machine.state.run_id
    assert address_for_frame(twin, twin.state.rpm_stack[0]) == address_for_frame(machine, machine.state.rpm_stack[0])
    # A different occurrence with the same source profile and root goal: different inputs.
    other = CompoundMachine(load_compound_profile(), trusted_ingress=())
    other.start(create_problem({**INPUTS, "e": "41"}))
    step_until(other, two_frames)
    a, b = address_for_frame(machine, machine.state.rpm_stack[0]), address_for_frame(other, other.state.rpm_stack[0])
    assert a["profile_coordinates"] is None and b["profile_coordinates"] is None
    assert a["source_profile"] == b["source_profile"] and a["root_goal"] == b["root_goal"]
    assert a["run_id"] != b["run_id"] and a["address_digest"] != b["address_digest"]
    assert a["snapshot_node_id"] != b["snapshot_node_id"] and a["frame_node_id"] != b["frame_node_id"]
    view_a, _ = view_of(machine)
    with pytest.raises(AddressRefused, match="SUSPENSION_EVENT_NOT_IN_VIEW"):
        resolve_address(view_a, b)
    with pytest.raises(AddressRefused, match="FRAME_NOT_LIVE"):
        address_for_frame(machine, other.state.rpm_stack[0])
    with pytest.raises(AddressRefused, match="PROFILE_COORDINATES_HAVE_NO_ADDRESS_ROLE"):
        check_address(resigned(a, profile_coordinates=["1/40"] * 40))


# Row 7 (AT24, AT25, AT26): layout, focus and recentering leave return-address resolution unchanged.
def test_row7_focus_and_hypothesis_changes_leave_resolution_unchanged(suspended):
    machine = suspended
    address = address_for_frame(machine, machine.state.rpm_stack[-1])
    view, journal = view_of(machine)
    baseline = resolve_address(view, address)
    snapshot = AtlasSnapshot.from_dict(view["atlas"])
    other_focus = next(node.node_id for node in snapshot.nodes if node.node_id.startswith("parameter-"))
    refocused = {**view, "atlas": snapshot.focus(other_focus).to_dict()}
    assert refocused["atlas"]["focus_node_id"] == other_focus != view["atlas"]["focus_node_id"]
    moved = resolve_address(refocused, address)
    assert {k: v for k, v in moved.items() if k != "view_focus_node_id"} == {k: v for k, v in baseline.items() if k != "view_focus_node_id"}
    flat = {**view, "atlas": snapshot.flat_graph()}
    assert resolve_address(flat, address)["snapshot_node_id"] == baseline["snapshot_node_id"]
    assert machine.journal() == journal


# Row 8 (AT10, AT21, AT27): the adapter preserves one event/address association.
def test_row8_one_suspension_event_per_address(suspended):
    machine = suspended
    inner = machine.state.rpm_stack[-1]
    first, second = address_for_frame(machine, inner), address_for_frame(machine, inner)
    assert first == second
    view, _ = view_of(machine)
    other_event = next(row["event"] for row in view["timeline"] if row["event"]["event_hash"] != first["suspension"]["event_hash"])
    swapped = resigned(first, **{"suspension.event_hash": other_event["event_hash"]})
    with pytest.raises(AddressRefused, match="SUSPENSION_EVENT_MISMATCH"):
        resolve_address(view, swapped)
    from research.cas_closed_loop_1.native_step_adapter import _suspension_event
    assert _suspension_event(machine.result(), inner).event_hash == first["suspension"]["event_hash"]


# Row 9 (AT24, AT27): no successful adapter view from a tampered replay.
def test_row9_tampered_view_or_journal_cannot_resolve(suspended):
    machine = suspended
    address = address_for_frame(machine, machine.state.rpm_stack[0])
    view, journal = view_of(machine)
    altered = deepcopy(view)
    for node in altered["atlas"]["nodes"]:
        if node["node_id"] == address["snapshot_node_id"]:
            node["fields"] = [[k, ("0" * 64 if k == "state_hash" else v)] for k, v in node["fields"]]
    with pytest.raises(AddressRefused, match="SNAPSHOT_NODE_MISMATCH"):
        resolve_address(altered, address)
    dropped = deepcopy(view)
    dropped["atlas"]["nodes"] = [node for node in dropped["atlas"]["nodes"] if node["node_id"] != address["waiting_state_node_id"]]
    with pytest.raises(AddressRefused, match="WAITING_NODE_NOT_FOUND"):
        resolve_address(dropped, address)
    truncated = deepcopy(journal)
    truncated["episodes"][0]["trace"] = truncated["episodes"][0]["trace"][:-1]
    with pytest.raises(ContractError):
        recover_compound_journal(truncated, trusted_genesis=machine.problem, trusted_ingress=(),
                                 expected_journal_digest=journal["journal_digest"], profile=machine.profile)
    with pytest.raises(AddressRefused, match="ADDRESS_DIGEST_MISMATCH"):
        check_address({**address, "snapshot_node_id": "state-" + "0" * 64})


# Row 10 (AT25, AT27): use the exact matching frame/snapshot; no nearest-node fallback.
def test_row10_near_miss_snapshot_hash_is_refused_not_nearest(suspended):
    machine = suspended
    address = address_for_frame(machine, machine.state.rpm_stack[0])
    view, _ = view_of(machine)
    real = address["suspension"]["pre_state_hash"]
    near = real[:-1] + ("0" if real[-1] != "0" else "1")
    assert sum(x != y for x, y in zip(real, near)) == 1
    near_miss = resigned(address, **{"suspension.pre_state_hash": near}, snapshot_node_id="state-" + near,
                         atlas_context={**address["atlas_context"], "observation_id": "observation-" + near})
    assert any(node["node_id"] == "state-" + real for node in view["atlas"]["nodes"])
    with pytest.raises(AddressRefused, match="SUSPENSION_EVENT_MISMATCH|SNAPSHOT_NODE_NOT_FOUND"):
        resolve_address(view, near_miss)
    outer = machine.state.rpm_stack[0]
    step_until(machine, concluded)  # after the exact return the frame is no longer live
    with pytest.raises(AddressRefused, match="FRAME_NOT_LIVE"):
        address_for_frame(machine, outer)


# Wiring (T05/T07, addendum section 3): runtime_location carries the same addresses, or null with no frame.
def test_runtime_location_atlas_binding_is_the_address_chain_or_null(suspended):
    machine = suspended
    location = runtime_location(machine)
    assert location["atlas_binding"]["frames"] == address_chain(machine)["frames"]
    assert [row["frame_node_id"] for row in location["atlas_binding"]["frames"]] == ["frame-" + f["frame_id"] for f in location["frames"]]
    assert location["atlas_binding"]["authority"] == "READ_ONLY_ADDRESS_NOT_A_RESUME_TOKEN"
    assert location["profile_coordinates"] is None
    step_until(machine, concluded)
    after = runtime_location(machine)
    assert after["frames"] == [] and after["return_identity"] is None and after["atlas_binding"] is None
