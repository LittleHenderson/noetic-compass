"""Read-only atlas projections of real replayed native transitions.

Most cases explicitly use simulated source identities, as labeled by the imported
fixture. The retained acceptance test instead uses the current actual source
profile. Traversal parity measures information preservation, not human benefit.
"""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from cncm.canonical import digest
from cncm.engine import CognitiveMachine
from cncm.model import ContractError, IntentType, Provenance, TerminalStatus
from cncm.native_engine import NativeMachine
from cncm.native_kernel import native_intent
from cncm.native_model import CAPABILITY, NativeBudget, NativeIntentType, NativeProblem
from cncm.native_profile import load_native_profile
from cncm.native_recovery import _decode_intent
from cncm.rpa_model import AtlasSnapshot, LinkType, NodeStatus
from cncm.rpa_native_adapter import native_atlas_from_journal, VIEW_SCHEMA
from cncm.procedural_substrate import make_candidate
from tests.test_native_kernel import native_problem, simulated_profile


ROOT = Path(__file__).resolve().parents[1]


def at_stage(stage, *, budget=None, ticks=128):
    packet = native_problem(budget=budget)
    packet = replace(packet, reasoning=replace(packet.reasoning,
        budgets=replace(packet.reasoning.budgets, max_ticks=ticks)))
    machine = NativeMachine(simulated_profile())
    machine.start(packet)
    for _ in range(stage):
        machine.advance()
    return machine


def project(machine):
    journal = machine.journal()
    return native_atlas_from_journal(journal, trusted_genesis=machine._episodes[0].problem,
        expected_journal_digest=journal["journal_digest"], profile=machine.profile)


def nodes(view):
    return AtlasSnapshot.from_dict(view["atlas"]).node_map()


def fields(view, node_id):
    return dict(nodes(view)[node_id].fields)


def new_problem(packet, *, c="29", name="adapter-reuse"):
    return replace(packet, reasoning=replace(packet.reasoning, problem_id=name),
        call=replace(packet.call, inputs=(("a", "3"), ("b", "5"), ("c", c))))


def send(machine, kind, mutation):
    intent = native_intent(machine.coordinator, kind, mutation)
    return machine.coordinator.execute(enabled_components=(intent.issuer_subsystem,),
        scheduled_components=(intent.issuer_subsystem,), intents=(intent,))


@pytest.mark.parametrize("stage,action", [
    (0, "REQUEST_PROCEDURE_CALL"), (1, "PUSH_ACQUISITION"),
    (2, "SELECT_PROCEDURE"), (3, "INSTALL_PROCEDURE"),
    (4, "RETURN_ACQUISITION"), (5, "APPLY_PROCEDURE"),
    (6, "ORDINARY_REASONING_AND_COMMITMENT_GATES"),
])
def test_stage_hints_are_proposals_and_projection_never_advances_source(stage, action):
    machine = at_stage(stage)
    before = machine.journal()
    coordinator = machine.coordinator
    view = project(machine)
    assert set(view) == {"schema_version", "atlas", "native", "timeline", "next_actions"}
    assert view["schema_version"] == VIEW_SCHEMA
    assert view["native"]["current_state_hash"] == machine.state.state_hash
    assert view["native"]["journal_digest"] == before["journal_digest"]
    assert view["next_actions"] == [{"action": action, "readiness": "necessary_conditions_present",
                                      "blockers": [], "authority": "PROPOSAL_ONLY"}]
    atlas = AtlasSnapshot.from_dict(view["atlas"])
    assert all(node.profile40 is None and node.profile_basis is None for node in atlas.nodes)
    assert atlas.node_map()[atlas.hypothesis_branch_id].status is NodeStatus.HYPOTHETICAL
    assert all(link.transition_status == "candidate" for link in atlas.links
               if link.target_id == atlas.hypothesis_branch_id)
    assert machine.coordinator is coordinator and machine.journal() == before


def test_suspended_caller_frame_missing_head_and_budget_are_exact():
    machine = at_stage(2)
    view = project(machine)
    call = fields(view, "current-call")
    frame = machine.state.rpm_stack[-1]
    assert call["call_id"] == frame.call_id == machine.problem.call.call_id
    assert call["goal_id"] == frame.parent_goal_id == machine.problem.call.goal_id
    assert call["branch_id"] == frame.branch_id == "branch-main"
    assert call["stage"] == "SUSPENDED"
    assert fields(view, "current-procedure")["active_head"] == "ABSENT"
    assert json.loads(fields(view, "current-continuation")["stack"]) == [frame.to_dict()]
    assert fields(view, "current-continuation")["active_goal"] == frame.goal_id
    assert fields(view, "current-budget") == {
        "procedure_instructions": "512", "checker_calls": "128", "ordinary_ticks": "126",
        "units": "conservative policy allocations",
    }
    bound = fields(view, "bound-call-inputs")
    assert json.loads(bound["inputs"]) == machine.problem.call.inputs_dict()
    assert bound["inputs_digest"] == frame.inputs_digest
    assert bound["source_profile_digest"] == machine.profile.profile_digest


def test_terminal_unresolved_frame_blocks_new_episode_hint():
    machine = at_stage(2, ticks=3)
    machine.advance()
    assert machine.state.rpm_stack and machine.state.halt_status is TerminalStatus.BUDGET_EXHAUSTED
    hint = project(machine)["next_actions"][0]
    assert hint["action"] == "START_NEW_EPISODE" and hint["readiness"] == "blocked"
    assert hint["authority"] == "PROPOSAL_ONLY"
    assert "Unresolved acquisition frame" in hint["blockers"][0]


def test_maximum_length_native_call_id_gets_a_bounded_view_identity():
    packet = native_problem()
    original = packet.call.call_id
    long_id = "c" + "x" * 127
    def rename(value):
        if type(value) is dict:
            return {key: rename(item) for key, item in value.items()}
        if type(value) is list:
            return [rename(item) for item in value]
        return long_id if value == original else value
    packet = NativeProblem.from_dict(rename(packet.to_dict()))
    machine = NativeMachine(simulated_profile())
    machine.start(packet)
    view = project(machine)
    mapping = nodes(view)
    assert fields(view, "current-call")["call_id"] == long_id
    assert fields(view, "bound-call-inputs")["call_id"] == long_id
    assert mapping["current-call"].idea_id == mapping["bound-call-inputs"].idea_id
    assert len(mapping["current-call"].idea_id) <= 128


@pytest.mark.parametrize("budget,expected_count", [(NativeBudget(143, 24), 1),
    (NativeBudget(144, 23), 1), (NativeBudget(0, 0), 2)])
def test_selection_hint_reports_insufficient_necessary_budget_without_running_selection(budget, expected_count):
    machine = at_stage(2, budget=budget)
    before = machine.journal()
    view = project(machine)
    hint = view["next_actions"][0]
    assert hint["action"] == "SELECT_PROCEDURE" and hint["readiness"] == "blocked"
    assert len(hint["blockers"]) == expected_count
    assert hint["authority"] == "PROPOSAL_ONLY"
    assert machine.journal() == before
    assert machine.state.native_budget == budget
    assert machine.coordinator.selected_artifact(machine.problem.call.call_id) is None


def test_selection_hint_reserves_the_last_tick_for_halt():
    machine = at_stage(2, ticks=3)
    view = project(machine)
    assert view["next_actions"][0]["readiness"] == "blocked"
    assert "Last tick is reserved for halt." in view["next_actions"][0]["blockers"]
    assert machine.state.halt_status is TerminalStatus.RUNNING


def test_current_checked_output_is_separate_from_ordinary_commitment():
    machine = at_stage(6)
    before = project(machine)
    assert before["native"]["output"] == "7"
    assert fields(before, "current-result")["call_stage"] == "COMPLETE"
    assert fields(before, "current-result")["committed_conclusion"] == "NONE"
    assert before["native"]["terminal_status"] == "RUNNING"
    machine.run()
    after = project(machine)
    assert after["native"]["terminal_status"] == "CONCLUDED"
    assert json.loads(fields(after, "current-result")["committed_conclusion"]) == machine.state.commitment_state.conclusion.to_dict()
    assert sum(row["work"]["instructions_allocated"] for row in after["timeline"]) == 210
    assert sum(row["work"]["checker_calls_allocated"] for row in after["timeline"]) == 35
    assert all(row["work"]["basis"] == "conservative_policy_units" for row in after["timeline"])


def test_committed_before_final_halt_hint_does_not_repeat_commitment():
    completed = at_stage(6)
    completed.run()
    trace = completed.journal()["episodes"][0]["trace"]
    assert len(trace) == 14 and trace[-1]["proposed_intents"][0]["intent_type"] == "HALT"
    partial = NativeMachine(completed.profile)
    partial.start(completed.problem)
    for event in trace[:-1]:
        result = partial.coordinator.execute(enabled_components=event["enabled_components"],
            scheduled_components=event["scheduled_components"],
            intents=tuple(_decode_intent(row) for row in event["proposed_intents"]))
        assert result.trace_event.to_dict() == event
    assert partial.state.commitment_state.decision_status == "COMMITTED"
    assert partial.state.halt_status is TerminalStatus.RUNNING
    before = partial.journal()
    view = project(partial)
    assert view["next_actions"] == [{"action": "HALT", "readiness": "necessary_conditions_present",
        "blockers": [], "authority": "PROPOSAL_ONLY"}]
    assert partial.journal() == before


def test_linked_reuse_and_rollback_display_history_without_old_output_becoming_current():
    machine = at_stage(6)
    packet = machine.problem
    machine.run()
    first = machine.state
    reused = machine.run(new_problem(packet), allow_acquisition=False)
    assert reused.output == "8"
    view = project(machine)
    assert view["native"]["output"] == "8"
    assert sum(row["work"]["instructions_allocated"] for row in view["timeline"]) == 216
    atlas = AtlasSnapshot.from_dict(view["atlas"])
    starts = [link for link in atlas.links if link.action_id == "START_NEW_EPISODE"
              and link.transition_status == "observed"]
    assert len(starts) == 1 and starts[0].source_id == "native-state-" + first.state_hash
    machine.start(new_problem(packet, c="32", name="adapter-rollback"))
    machine.rollback(CAPABILITY)
    machine.run(allow_acquisition=False)
    after = project(machine)
    assert after["native"]["output"] is None
    assert fields(after, "current-result")["output"] == "NONE"
    assert fields(after, "current-procedure")["active_head"] == "ABSENT"
    assert fields(after, "current-procedure")["retained_artifact_count"] == "1"
    record_nodes = [dict(node.fields) for node in nodes(after).values()
                    if "record_kind" in dict(node.fields)]
    assert any(row["record_kind"] == "ROLLBACK" for row in record_nodes)
    assert len([row for row in record_nodes if row["record_kind"] == "EXECUTION"]) == 2
    assert any("ROLLBACK_PROCEDURE" in row["intent_types"] for row in after["timeline"])


def test_failed_installation_retains_charged_work_and_failure_return_hint():
    machine = at_stage(2)
    outcome = send(machine, NativeIntentType.INSTALL_PROCEDURE, {
        "call_id": machine.problem.call.call_id,
        "artifact": make_candidate(combine="ADD_EXACT").to_dict(), "qualification_digest": None,
    })
    assert outcome.rejected_intents and not outcome.authorized_intents
    before = machine.journal()
    view = project(machine)
    row = view["timeline"][-1]
    assert row["outcome"] == "REJECTED"
    assert row["work"] == {"instructions_allocated": 60, "checker_calls_allocated": 10,
                            "basis": "conservative_policy_units"}
    assert fields(view, "current-budget")["procedure_instructions"] == "452"
    assert fields(view, "current-budget")["checker_calls"] == "118"
    assert fields(view, "current-procedure")["active_head"] == "ABSENT"
    assert view["next_actions"][0]["action"] == "RETURN_ACQUISITION"
    assert machine.journal() == before


def test_coalesced_valid_write_is_not_mislabeled_as_wholly_rejected():
    machine = at_stage(6)
    c, packet = machine.coordinator, machine.problem.reasoning
    record = c._decompose_query(machine.state, machine.state.branch_table[0])
    proposals = tuple(CognitiveMachine._intent(c, intent_type=IntentType.RECORD_DECOMPOSITION,
        issuer="reasoning_engine", capability="decompose", scope="branch:branch-main",
        branch_id="branch-main", goal_id=packet.goal_id, mutation={"decomposition": record.to_dict()},
        provenance=(Provenance("test", label),)) for label in ("a", "b"))
    result = c.execute(enabled_components=("reasoning_engine",), scheduled_components=("reasoning_engine",),
                       intents=proposals)
    assert len(result.authorized_intents) == len(result.rejected_intents) == 1
    assert len(machine.state.branch_table[0].decompositions) == 1
    view = project(machine)
    row = view["timeline"][-1]
    assert row["outcome"] in {"MIXED", "PARTIALLY_ACCEPTED"}
    assert row["authorized_intent_ids"] == list(result.trace_event.authorized_intent_ids)
    assert row["rejected_intent_ids"] == [item.intent_id for item in result.rejected_intents]


def test_focus_and_hypothesis_changes_preserve_present_and_source_evidence():
    machine = at_stage(2)
    journal = machine.journal()
    view = project(machine)
    atlas = AtlasSnapshot.from_dict(view["atlas"])
    original_digest = atlas.snapshot_digest
    focused = atlas.focus("current-continuation").with_hypothesis(None)
    assert focused.focus_node_id == "current-continuation"
    assert focused.current_state_id == atlas.current_state_id
    assert focused.nodes == atlas.nodes and focused.links == atlas.links
    assert focused.node_map()[focused.current_state_id] == atlas.node_map()[atlas.current_state_id]
    assert atlas.snapshot_digest == original_digest
    assert machine.journal() == journal
    assert project(machine)["native"] == view["native"]


@pytest.mark.parametrize("case", ["unsealed_change", "resealed_output", "resealed_proof", "wrong_source", "wrong_genesis", "truncated"])
def test_adapter_refuses_corrupted_and_resealed_evidence(case):
    machine = at_stage(6)
    journal = machine.journal()
    anchor = journal["journal_digest"]
    genesis = machine.problem
    if case == "wrong_genesis":
        genesis = new_problem(genesis)
    elif case == "wrong_source":
        journal["source_profile"]["source_files"][0]["sha256"] = "f" * 64
    elif case == "truncated":
        journal["episodes"][0]["trace"].pop()
        journal["episodes"][0]["proposal_batches"].pop()
    else:
        state = journal["episodes"][0]["final_state"]
        if case == "resealed_proof":
            proof = state["branch_table"][0]["proof_steps"][0]
            proof["execution_digest"] = "a" * 64
            proof["step_id"] = "native-proof-" + digest({key: value for key, value in proof.items() if key != "step_id"})
        else:
            state["native_calls"][0]["output"] = "999"
        state["state_hash"] = digest({key: value for key, value in state.items() if key not in {"state_hash", "trace_head"}})
    if case not in {"unsealed_change", "truncated", "wrong_genesis"}:
        journal["journal_digest"] = digest({key: value for key, value in journal.items() if key != "journal_digest"})
        anchor = journal["journal_digest"]
    with pytest.raises(ContractError):
        native_atlas_from_journal(journal, trusted_genesis=genesis,
            expected_journal_digest=anchor, profile=machine.profile)


def flat_breadth_first(wire, *, max_nodes, max_depth, allowed):
    """Plain directed-edge baseline with the same declared edge-ID tie order."""
    frontier = [wire["focus_node_id"]]
    visited = list(frontier)
    edges = sorted(wire["links"], key=lambda row: row["link_id"])
    for _ in range(max_depth):
        next_frontier = []
        for source in frontier:
            for edge in edges:
                if edge["source_id"] != source or edge["relation"] not in allowed:
                    continue
                target = edge["target_id"]
                if target not in visited and len(visited) < max_nodes:
                    visited.append(target)
                    next_frontier.append(target)
        frontier = next_frontier
    return tuple(visited)


@pytest.mark.parametrize("budget", [1, 3, 8, 100])
@pytest.mark.parametrize("depth", [0, 1, 3])
def test_typed_and_plain_graph_keep_same_information_and_traversal_budget(budget, depth):
    machine = at_stage(6)
    atlas = AtlasSnapshot.from_dict(project(machine)["atlas"])
    flat = atlas.flat_graph()
    assert flat == atlas.to_dict()
    relations = (LinkType.CONTAINS_PART, LinkType.REFINES_STATE)
    typed = atlas.expand(max_nodes=budget, max_depth=depth, relations=relations)
    plain = flat_breadth_first(flat, max_nodes=budget, max_depth=depth,
                              allowed={kind.value for kind in relations})
    assert typed.visited_node_ids == plain
    assert len(plain) <= budget
    assert plain[0] == atlas.current_state_id  # The root consumes one node.
    assert machine.state.native_budget == NativeBudget(302, 93)


def test_retained_actual_source_acceptance_chain_projects_without_promoting_old_results():
    folder = ROOT / "records/native_procedure_001/acceptance_002"
    anchor = json.loads((folder / "final_anchor.json").read_text(encoding="utf-8"))
    genesis = NativeProblem.from_dict(json.loads((folder / "genesis.json").read_text(encoding="utf-8")))
    raw = (folder / "final_journal.json").read_bytes()
    before = digest(raw.hex())
    profile = load_native_profile()
    assert profile.profile_digest == anchor["source_profile_digest"] == "c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607"
    view = native_atlas_from_journal(raw, trusted_genesis=genesis,
        expected_journal_digest=anchor["journal_digest"])
    assert view["native"]["terminal_status"] == "NEEDS_CAPABILITY"
    assert view["native"]["output"] is None
    assert fields(view, "current-procedure")["active_head"] == "ABSENT"
    assert len({row["run_id"] for row in view["timeline"]}) == 3
    assert sum(row["work"]["instructions_allocated"] for row in view["timeline"]) == 216
    assert sum(row["work"]["checker_calls_allocated"] for row in view["timeline"]) == 36
    assert digest((folder / "final_journal.json").read_bytes().hex()) == before
