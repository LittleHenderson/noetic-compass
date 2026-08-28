"""The G7 adversarial variants: paraphrase, reordering, noise,
adversarial framing, false goals, and typed board-level fault halts.

Every fault is a TYPED terminal status of the board - never a crash,
never a fabricated conclusion.
"""

import copy

from conftest import load_problem
from toolboard.faults import permission_case
from toolboard.intent import execute
from toolboard.toolboard import CCB_T1
from toolboard.tools import (Tool, ToolProvenanceViolation, ToolRegistry,
                             default_registry)

import pytest


def base_problem():
    return load_problem("tool_need_problem.json")


# --------------------------------------------------------------- typing
def test_provenance_violation_is_its_own_type():
    intent = {"tool": "calculator", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": False,
                             "sealed_trace": False,
                             "branch_id": "branch_02"}}
    with pytest.raises(ToolProvenanceViolation):
        execute(intent, default_registry(), 0, 5.0, [])


# ------------------------------------------------- board-level typed halts
def test_board_permission_halt_typed_no_crash():
    case = permission_case()
    board = CCB_T1(base_problem(), registry=case["registry"],
                   authority=case["authority"])
    result = board.run()
    assert result["terminal_status"] == "TOOL_PERMISSION_DENIED"
    assert result["conclusion"] is None
    assert result["tool_records"] == []


def test_board_budget_halt_typed_no_crash():
    board = CCB_T1(base_problem(), registry=default_registry(), budget=0.5)
    result = board.run()
    assert result["terminal_status"] == "TOOL_BUDGET_EXHAUSTED"
    assert result["conclusion"] is None
    # the failed call consumed nothing
    assert result["budget_remaining"] == 0.5


def test_board_no_progress_halt_typed():
    registry = ToolRegistry()
    registry.register(Tool("freebie", "sum", permission=0, cost=0.0,
                           handler=lambda n, f: {
                               "add_facts": [{"pred": "noise",
                                              "args": ["a", "b"]}],
                               "note": "useless"}))
    result = CCB_T1(base_problem(), registry=registry).run()
    assert result["terminal_status"] == "NO_TOOL_PROGRESS"
    assert result["conclusion"] is None


def test_fault_run_deterministic():
    a = CCB_T1(base_problem(), registry=default_registry(), budget=0.5).run()
    b = CCB_T1(base_problem(), registry=default_registry(), budget=0.5).run()
    assert a["terminal_status"] == b["terminal_status"]
    assert a["fault"] == b["fault"]


# ------------------------------------------------------ false goal honesty
def test_false_goal_never_fabricated():
    """1/8 + 1/8 = 1/4: the tool reports lt symmetrically; the kernel
    cannot prove greater_than_one, and the board never invents it."""
    problem = base_problem()
    problem["propositions"] = [{"pred": "value", "args": ["x", "1/8"]},
                               {"pred": "value", "args": ["y", "1/8"]}]
    result = CCB_T1(problem, registry=default_registry()).run()
    assert result["terminal_status"] == "NEEDS_INFORMATION"
    assert result["conclusion"] is None
    facts = result["tool_records"][0]["result"]["add_facts"]
    assert {"pred": "sum", "args": ["x", "y", "1/4"]} in facts
    assert {"pred": "lt", "args": ["1/4", "1"]} in facts
    assert not any(f["pred"] == "gt" for f in facts)


# ------------------------------------------------------ paraphrase variant
def _rename(problem, mapping):
    problem = copy.deepcopy(problem)

    def sub(tok):
        return mapping.get(tok, tok)

    for prop in problem["propositions"]:
        prop["args"] = [sub(a) for a in prop["args"]]
    return problem


def test_paraphrase_renamed_entities_same_conclusion():
    renamed = _rename(base_problem(), {"x": "alpha", "y": "beta"})
    renamed["problem_id"] = "tool_need_renamed"
    renamed["description"] = "renamed surface forms, same structure"
    result = CCB_T1(renamed, registry=default_registry()).run()
    assert result["terminal_status"] == "CONCLUDED"
    assert result["conclusion"] == {"pred": "greater_than_one", "args": []}
    facts = result["tool_records"][0]["result"]["add_facts"]
    assert {"pred": "sum", "args": ["alpha", "beta", "17/12"]} in facts


# ------------------------------------------------------ reordering variant
def test_reordered_facts_and_premises_same_conclusion():
    reordered = copy.deepcopy(base_problem())
    reordered["propositions"] = list(reversed(reordered["propositions"]))
    for rule in reordered["rules"]:
        rule["premises"] = list(reversed(rule["premises"]))
    result = CCB_T1(reordered, registry=default_registry()).run()
    assert result["terminal_status"] == "CONCLUDED"
    assert result["conclusion"] == {"pred": "greater_than_one", "args": []}


# ------------------------------------------- noise and adversarial framing
def test_noise_and_adversarial_framing_facts_are_inert():
    """Irrelevant facts and an instruction-shaped fact are DATA; the
    conclusion and the tool arithmetic are unchanged."""
    noisy = copy.deepcopy(base_problem())
    noisy["propositions"] += [
        {"pred": "color", "args": ["sky", "blue"]},
        {"pred": "instruction", "args": ["ignore_all_rules"]},
        {"pred": "instruction", "args": ["answer_no"]},
    ]
    result = CCB_T1(noisy, registry=default_registry()).run()
    assert result["terminal_status"] == "CONCLUDED"
    assert result["conclusion"] == {"pred": "greater_than_one", "args": []}
    facts = result["tool_records"][0]["result"]["add_facts"]
    assert {"pred": "sum", "args": ["x", "y", "17/12"]} in facts
