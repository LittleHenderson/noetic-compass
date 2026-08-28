"""The 16-row conformance table (spec/CONFORMANCE_PLAN_v0.1.md)."""

import copy

from kernel.kernel import CAS_RRK, DEFAULT_CONSTITUTION, build_initial_state
from kernel.fixtures import load_problem
from kernel.schemas import BranchFrame, Candidate, Proposition
from kernel.state_store import TransactionCoordinator, make_intent

PROB = load_problem("rpm_recursion")
PLAN = load_problem("candidate_planning")
CONTRA = load_problem("contradiction")
MISSING = load_problem("missing_information")


def _state(problem=PROB, constitution=None):
    return build_initial_state(problem, constitution or dict(DEFAULT_CONSTITUTION),
                               "run_t", 0)


def _validate(coordinator, state, intents):
    ok_list, rejected, reasons = [], [], []
    for intent in intents:
        ok, reason = coordinator.validate(intent, state)
        if ok:
            ok_list.append(intent)
        else:
            rejected.append(intent)
            reasons.append(reason)
    return ok_list, rejected, reasons


def test_01_scheduler_cannot_emit_decision_commit():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x1", "DecisionCommitIntent", "scheduler", 0)
    ok, reason = coord.validate(intent, _state())
    assert not ok and "unauthorized" in reason


def test_02_branch_cannot_write_durable_memory():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x2", "MemoryWriteIntent", "branch_manager", 0)
    ok, reason = coord.validate(intent, _state())
    assert not ok and "unauthorized" in reason


def test_03_branch_cannot_take_external_action():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x3", "ForkIntent", "branch_manager", 0,
                         branch_id="b_ext",
                         mutation={"external_action": "tool_call"})
    ok, reason = coord.validate(intent, _state())
    assert not ok and "external action" in reason


def test_04_rpm_return_without_parent_is_stack_fault():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x4", "ReturnGoalIntent", "rpm_stack", 0,
                         mutation={"parent_goal_id": "ghost",
                                   "resolved_goal": "g_launch",
                                   "result": {"action": "none"},
                                   "add_propositions": []})
    ok, reason = coord.validate(intent, _state())
    assert not ok and "STACK_FAULT" in reason


def test_05_conflicting_field_mutations_resolve_deterministically():
    coord = TransactionCoordinator(PROB)
    a = make_intent("a_recall", "DeriveIntent", "reasoning", 0,
                    mutation={"op": "RECALL", "scope": "working_memory"})
    b = make_intent("b_recall", "DeriveIntent", "reasoning", 0,
                    mutation={"op": "RECALL", "scope": "working_memory"})
    authorized, rejected, reasons = coord.resolve([a, b])
    assert [i["intent_id"] for i in authorized] == ["a_recall"]
    assert any("conflict" in r for r in reasons)


def test_06_commit_with_contradiction_rejected():
    state = _state(CONTRA)
    state.branch_table["b1"] = BranchFrame("b1", None, 0, [
        Candidate("c1", "b1", Proposition("P"), {"status": "SUPPORTED"})])
    coord = TransactionCoordinator(CONTRA)
    intent = make_intent("x6", "DecisionCommitIntent", "commitment_latch", 0,
                         branch_id="b1",
                         mutation={"branch_id": "b1", "candidate_id": "c1",
                                   "target": {"pred": "P", "args": []}})
    ok, reason = coord.validate(intent, state)
    assert not ok and "CONTRADICTED" in reason


def test_07_learning_referencing_discarded_branch_rejected():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x7", "MemoryWriteIntent", "write_back", 0,
                         provenance={"committed_outcome": True,
                                     "sealed_trace": True,
                                     "branch_id": "branch_99"})
    ok, reason = coord.validate(intent, _state())
    assert not ok and "discarded branch" in reason


def test_08_halt_before_trace_seal_rejected():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x8", "HaltIntent", "halting_controller", 0,
                         mutation={"status": "CONCLUDED"},
                         provenance={"phase": "PROPOSE"})
    ok, reason = coord.validate(intent, _state())
    assert not ok and "halt test phase" in reason


def test_09_trace_fabric_cannot_mutate():
    coord = TransactionCoordinator(PROB)
    intent = make_intent("x9", "DeriveIntent", "trace_fabric", 0,
                         mutation={"op": "RECALL"})
    ok, reason = coord.validate(intent, _state())
    assert not ok and "unauthorized" in reason


def test_10_deterministic_runs():
    a = CAS_RRK(PLAN).run()
    b = CAS_RRK(PLAN).run()
    assert a["trace_digest"] == b["trace_digest"]
    assert a["final_state_hash"] == b["final_state_hash"]
    assert a["terminal_status"] == b["terminal_status"] == "CONCLUDED"


def test_11_failed_branches_roll_back():
    rt = CAS_RRK(PLAN)
    packet = rt.run()
    kinds = [m.get("kind") for e in packet["trace"]
             for m in e["committed_mutations"]]
    assert "discard" in kinds
    table = rt.state.branch_table
    assert len(table) == 1
    committed = next(iter(table.values()))
    assert committed.status == "COMMITTED"
    assert committed.candidates[0].target == Proposition("viable", ("P1",))


def test_12_missing_premise_halts_needs_information():
    packet = CAS_RRK(MISSING).run()
    assert packet["terminal_status"] == "NEEDS_INFORMATION"
    assert packet["conclusion"] is None


def test_13_rpm_subgoal_succeeds_and_parent_resumes():
    rt = CAS_RRK(PROB)
    packet = rt.run()
    kinds = [m.get("kind") for e in packet["trace"]
             for m in e["committed_mutations"]]
    assert packet["terminal_status"] == "CONCLUDED"
    assert "push_rpm" in kinds and "return_rpm" in kinds
    assert rt.state.active_goal_id == "g_launch"


def test_14_rpm_subgoal_failure_propagates_typed():
    no_actions = copy.deepcopy(PROB)
    no_actions["available_actions"] = {}
    assert CAS_RRK(no_actions).run()["terminal_status"] == "NEEDS_INFORMATION"
    with_knowledge = copy.deepcopy(PROB)
    with_knowledge["available_actions"] = {}
    with_knowledge["propositions"].append(
        {"pred": "known", "args": ["market_knowledge"]})
    assert CAS_RRK(with_knowledge).run()["terminal_status"] == "NEEDS_CAPABILITY"


def test_15_budget_exhausted():
    constitution = dict(DEFAULT_CONSTITUTION, branch_budget=1)
    packet = CAS_RRK(PROB, constitution).run()
    assert packet["terminal_status"] == "BUDGET_EXHAUSTED"


def test_16_loop_limit_reached():
    constitution = dict(DEFAULT_CONSTITUTION, max_ticks=1)
    packet = CAS_RRK(PROB, constitution).run()
    assert packet["terminal_status"] == "LOOP_LIMIT_REACHED"
