"""CCB-T1: typed tool intents, authority, faults (the G7 gate)."""

import pytest

from conftest import load_problem
from toolboard.faults import (branch_case, budget_case, hostile_result_case,
                              injected_failure_case, permission_case)
from toolboard.intent import execute, validate
from toolboard.toolboard import CCB_T1
from toolboard.tools import (AmbiguousToolNeed, ContraToolResult,
                             ToolBudgetExhausted, ToolFailure,
                             ToolPermissionDenied, ToolUnknown,
                             default_registry)


def test_calculator_is_exact():
    registry = default_registry()
    result = registry.tools["calculator"].call(
        {"pred": "sum", "args": ["x", "y"]},
        [{"pred": "value", "args": ["x", "2/3"]},
         {"pred": "value", "args": ["y", "3/4"]}])
    assert {"pred": "sum", "args": ["x", "y", "17/12"]} in result["add_facts"]
    assert {"pred": "gt", "args": ["17/12", "1"]} in result["add_facts"]


def test_tool_intent_requires_committed_sealed_path():
    intent = {"tool": "calculator", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": False,
                             "sealed_trace": False, "branch_id": None}}
    reasons = validate(intent, default_registry(), 0, 5.0, [])
    assert any("committed" in r for r in reasons)
    assert any("sealed" in r for r in reasons)


def test_no_branch_may_call_tools():
    case = branch_case()
    reasons = validate(case["intent"], case["registry"], 0, 5.0, [])
    assert any("branch" in r for r in reasons)


def test_permission_denial_typed():
    case = permission_case()
    with pytest.raises(ToolPermissionDenied):
        execute(case["intent"], case["registry"], case["authority"],
                5.0, [])


def test_budget_exhaustion_typed():
    case = budget_case()
    with pytest.raises(ToolBudgetExhausted):
        execute(case["intent"], case["registry"], 0, case["budget"], [])


def test_injected_failure_typed_no_partial_state():
    case = injected_failure_case()
    with pytest.raises(ToolFailure):
        execute(case["intent"], case["registry"], 0, 5.0, [])


def test_hostile_contradictory_result_flagged():
    case = hostile_result_case()
    with pytest.raises(ContraToolResult):
        execute(case["intent"], case["registry"], 0, 5.0, case["facts"])


def test_unknown_tool_typed():
    intent = {"tool": "nope", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": True,
                             "sealed_trace": True, "branch_id": None}}
    with pytest.raises(ToolUnknown):
        execute(intent, default_registry(), 0, 5.0, [])


def test_full_loop_needs_tool_then_concludes():
    board = CCB_T1(load_problem("tool_need_problem.json"),
                   registry=default_registry())
    result = board.run()
    assert result["terminal_status"] == "CONCLUDED"
    assert result["conclusion"] == {"pred": "greater_than_one", "args": []}
    assert len(board.tool_records) == 1
    record = board.tool_records[0]
    assert record["tool"] == "calculator"
    assert record["digest"]
    assert record["provenance"]["committed_outcome"] is True


def test_without_tools_the_same_problem_halts():
    from kernel.kernel import CAS_RRK
    packet = CAS_RRK(load_problem("tool_need_problem.json"),
                     run_id="no_tools", seed=0).run()
    assert packet["terminal_status"] == "NEEDS_INFORMATION"


def test_tool_record_provenance_and_determinism():
    problem = load_problem("tool_need_problem.json")
    a = CCB_T1(problem, registry=default_registry()).run()
    b = CCB_T1(load_problem("tool_need_problem.json"),
               registry=default_registry()).run()
    assert a["kernel_final_hash"] == b["kernel_final_hash"]
    assert a["tool_records"][0]["digest"] == b["tool_records"][0]["digest"]
    assert a["budget_remaining"] == b["budget_remaining"]
