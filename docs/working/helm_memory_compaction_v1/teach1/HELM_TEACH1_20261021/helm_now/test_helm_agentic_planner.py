"""test_helm_agentic_planner.py -- the chat's tool planner (helm_agentic_executor.DynamicGoalPlanner) orders steps
right. Plans only: no step is executed, no file is written.

Cases A-E and TEST 8 are copied from helm_agentic_executor.run_agentic_autonomy_verification (which also runs
tools, so it is not a pytest). Case F is the defect found by HELM UI v0 (2026-10-19): two 'Before X, Y.' sentences
lost an action (git, and the second sentence's X).
Run:  python -m pytest test_helm_agentic_planner.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pytest  # noqa: E402

import helm_agentic_executor as ax  # noqa: E402


@pytest.fixture(scope="module")
def planner():
    return ax.AgenticExecutionEngine(workspace_root=HERE).planner


def tools(planner, goal):
    return [s.tool_name for s in planner.decompose_goal(goal).topological_sort()]


def test_case_a_write_verify_commit(planner):
    assert tools(planner, "Write the code math_utils.py, verify it with tests, then commit to git.") == \
        ["synthesize_code", "execute_command", "git_action"]


def test_case_b_verify_before_writing(planner):
    steps = planner.decompose_goal("Before writing any code, run the verification on auth.py, then write the code.").topological_sort()
    assert [s.tool_name for s in steps] == ["execute_command", "synthesize_code"]
    assert steps[1].dependencies == [steps[0].step_id]


def test_case_c_first_git_then_write(planner):
    goal = "First check git to see what changed and recover the last known good state, then write the code."
    assert tools(planner, goal) == ["git_action", "synthesize_code"]


def test_case_d_git_log_and_diff(planner):
    assert tools(planner, "Git log and diff.") == ["git_action"]


def test_case_e_parallel_then_join(planner):
    steps = planner.decompose_goal("Inspect README.md and check git status in parallel, then design the system.").topological_sort()
    assert len(steps) == 3 and steps[2].tool_name == "systems_design_spec"
    assert set(steps[2].dependencies) == {steps[0].step_id, steps[1].step_id}


def test_case_8_dynamic_order(planner):
    t = tools(planner, "Synthesize python code math_utils.py, verify syntax, run test suite, and check git status.")
    assert t.index("synthesize_code") < t.index("execute_command") < t.index("git_action")


def test_case_f_two_before_sentences_keep_every_action(planner):
    goal = "Before you commit to git, verify the tests pass. Before you verify the tests, write the code for auth.py."
    steps = planner.decompose_goal(goal).topological_sort()
    assert [s.tool_name for s in steps] == ["synthesize_code", "execute_command", "git_action"]
    assert steps[0].params["path"].endswith("auth.py")
    assert steps[2].params["action"] == "commit"


def test_before_x_keeps_x_when_y_is_a_write(planner):
    # the old check dropped X whenever Y was a write, whatever X was
    assert tools(planner, "Before committing to git, write the code for auth.py.") == ["synthesize_code", "git_action"]
