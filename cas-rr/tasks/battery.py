"""The six-task native reasoning battery, plus negative variants.

1. Transitive inference (CONCLUDED + NEEDS_INFORMATION variant)
2. Constraint satisfaction (CONCLUDED + INADMISSIBLE variant)
3. Fault diagnosis via test-point walk-down (CONCLUDED + NEEDS_INFORMATION)
4. Missing-information reasoning (NEEDS_INFORMATION)
5. Recursive planning (CONCLUDED + NEEDS_CAPABILITY variant)
6. Memory-dependent reasoning (NEEDS_INFORMATION -> CONCLUDED via memory)
7. Contradiction surface (CONFLICT_UNRESOLVED)
"""

from __future__ import annotations

from dataclasses import replace

from cas_rr.foundations import GoalFrame
from cas_rr.runtime import Problem, default_constitution
from cas_rr.terms import Atom, Rule


def A(pred: str, *args: str) -> Atom:
    return Atom(pred, tuple(args))


def R(rule_id: str, premises, conclusion: Atom, note: str = "") -> Rule:
    return Rule(rule_id, tuple(premises), conclusion, "task_battery", note)


# --------------------------------------------------------------------------
# 1. Transitive inference
# --------------------------------------------------------------------------
def task_transitive():
    facts = [A("precedes", "a", "b"), A("precedes", "b", "c")]
    rules = [R("r_trans",
               [A("precedes", "?X", "?Y"), A("precedes", "?Y", "?Z")],
               A("precedes", "?X", "?Z"), "transitivity")]
    alternatives = [A("precedes", "a", "c"), A("precedes", "c", "a")]
    goal = GoalFrame(goal_id="g_trans", foundation_ref="TF2b",
                     desired_outcome=A("precedes", "a", "c"), kind="question")
    return Problem("transitive_01",
                   "A precedes B; B precedes C. What follows?",
                   facts, rules, alternatives, goal)


def task_transitive_negative():
    facts = [A("precedes", "a", "b"), A("precedes", "b", "c")]
    rules = [R("r_trans",
               [A("precedes", "?X", "?Y"), A("precedes", "?Y", "?Z")],
               A("precedes", "?X", "?Z"), "transitivity")]
    alternatives = [A("precedes", "c", "a"), A("precedes", "a", "c")]
    goal = GoalFrame(goal_id="g_trans_neg", foundation_ref="TF2b",
                     desired_outcome=A("precedes", "c", "a"), kind="question")
    return Problem("transitive_neg_01",
                   "A precedes B; B precedes C. Does C precede A?",
                   facts, rules, alternatives, goal)


# --------------------------------------------------------------------------
# 2. Constraint satisfaction
# --------------------------------------------------------------------------
def _constraint_facts():
    return [
        A("plan_has", "P1", "f1"), A("plan_has", "P1", "f2"),
        A("plan_has", "P1", "f3"), A("plan_has", "P1", "f4"),
        A("plan_has", "P1", "f5"),
        A("plan_has", "P2", "f1"), A("plan_has", "P2", "f2"),
        A("plan_has", "P2", "f4"), A("plan_has", "P2", "f5"),
        A("missing", "P2", "f3"),
        A("plan_has", "P3", "f1"),
        A("missing", "P3", "f2"), A("missing", "P3", "f3"),
        A("missing", "P3", "f4"), A("missing", "P3", "f5"),
    ]


def _constraint_rules():
    return [
        R("c1", [A("plan_has", "?P", "f1")], A("cond", "?P", "C1")),
        R("c2", [A("plan_has", "?P", "f2")], A("cond", "?P", "C2")),
        R("c3", [A("plan_has", "?P", "f3")], A("cond", "?P", "C3")),
        R("c4", [A("plan_has", "?P", "f4")], A("cond", "?P", "C4")),
        R("c5", [A("plan_has", "?P", "f5")], A("cond", "?P", "C5")),
        R("viable", [A("cond", "?P", "C1"), A("cond", "?P", "C2"),
                     A("cond", "?P", "C3"), A("cond", "?P", "C4"),
                     A("cond", "?P", "C5")], A("viable", "?P")),
        R("not_viable", [A("missing", "?P", "?F")], A("not_viable", "?P")),
    ]


def task_constraint():
    goal = GoalFrame(goal_id="g_plan", foundation_ref="TF5b",
                     desired_outcome=A("viable", "?P"), kind="plan")
    return Problem("constraint_01",
                   "Choose a plan satisfying all five conditions.",
                   _constraint_facts(), _constraint_rules(),
                   [A("viable", "P1"), A("viable", "P2"), A("viable", "P3")],
                   goal)


def task_inadmissible():
    facts = [
        A("plan_has", "P1", "f1"), A("plan_has", "P1", "f2"),
        A("plan_has", "P1", "f3"), A("plan_has", "P1", "f4"),
        A("plan_has", "P1", "f5"),
        A("plan_has", "P2", "f1"), A("plan_has", "P2", "f2"),
        A("plan_has", "P2", "f3"), A("plan_has", "P2", "f4"),
        A("plan_has", "P2", "f5"),
        A("violates_charter", "P1"), A("violates_charter", "P2"),
    ]
    rules = [
        R("viable", [A("plan_has", "?P", "f1"), A("plan_has", "?P", "f2"),
                     A("plan_has", "?P", "f3"), A("plan_has", "?P", "f4"),
                     A("plan_has", "?P", "f5")], A("viable", "?P")),
    ]
    goal = GoalFrame(goal_id="g_charter", foundation_ref="TF5b",
                     desired_outcome=A("viable", "?P"), kind="plan")
    return Problem("inadmissible_01",
                   "Both viable plans violate the charter.",
                   facts, rules, [A("viable", "P1"), A("viable", "P2")], goal)


# --------------------------------------------------------------------------
# 3. Fault diagnosis via test-point walk-down
# --------------------------------------------------------------------------
def _fault_facts():
    return [
        A("good", "tp0"), A("good", "tp1"), A("good", "tp2"),
        A("bad", "tp3"), A("bad", "tp4"), A("bad", "tp5"),
        A("upstream", "S1", "tp0"), A("upstream", "S2", "tp1"),
        A("upstream", "S3", "tp2"), A("upstream", "S4", "tp3"),
        A("upstream", "S5", "tp4"),
        A("output", "S1", "tp1"), A("output", "S2", "tp2"),
        A("output", "S3", "tp3"), A("output", "S4", "tp4"),
        A("output", "S5", "tp5"),
    ]


def task_fault():
    rules = [R("walk_down",
               [A("upstream", "?S", "?U"), A("output", "?S", "?O"),
                A("good", "?U"), A("bad", "?O")],
               A("first_bad", "?S"), "last good / first bad walk-down")]
    goal = GoalFrame(goal_id="g_fault", foundation_ref="TF2b",
                     desired_outcome=A("first_bad", "?S"), kind="question")
    return Problem("fault_01",
                   "Observed effect is wrong. Which stage first deviated?",
                   _fault_facts(), rules,
                   [A("first_bad", f"S{i}") for i in range(1, 6)], goal)


def task_fault_missing_reading():
    facts = [f for f in _fault_facts() if f != A("bad", "tp3")]
    rules = [R("walk_down",
               [A("upstream", "?S", "?U"), A("output", "?S", "?O"),
                A("good", "?U"), A("bad", "?O")],
               A("first_bad", "?S"), "last good / first bad walk-down")]
    goal = GoalFrame(goal_id="g_fault2", foundation_ref="TF2b",
                     desired_outcome=A("first_bad", "?S"), kind="question")
    return Problem("fault_missing_01",
                   "Diagnose with a missing test-point reading.",
                   facts, rules,
                   [A("first_bad", f"S{i}") for i in range(1, 6)], goal)


# --------------------------------------------------------------------------
# 4. Missing-information reasoning
# --------------------------------------------------------------------------
def task_missing_info():
    facts = [A("has", "a", "x")]
    rules = [R("r_is", [A("has", "?X", "?Y")], A("is", "?X", "?Y"))]
    goal = GoalFrame(goal_id="g_missing", foundation_ref="TF2b",
                     desired_outcome=A("is", "b", "y"), kind="question")
    return Problem("missing_info_01",
                   "Can the conclusion be established from the premises?",
                   facts, rules, [A("is", "b", "y"), A("is", "a", "x")], goal)


# --------------------------------------------------------------------------
# 5. Recursive planning
# --------------------------------------------------------------------------
def _plan_facts():
    return [
        A("plan_for", "P_launch", "G"),
        A("requires_knowledge", "P_launch", "market_knowledge"),
        A("requires_capability", "P_launch", "print_capacity"),
        A("defer_plan", "P_defer"),
        A("action_exists", "market_research"),
        A("action_available", "market_research"),
        A("action_exists", "restructure_resources"),
        A("action_available", "restructure_resources"),
    ]


def _plan_rules():
    return [
        R("r_exec",
          [A("plan_for", "?P", "?G"), A("requires_knowledge", "?P", "?K"),
           A("requires_capability", "?P", "?C"), A("known", "?K"),
           A("has_capability", "?C")],
          A("executable", "?P")),
        R("r_defer", [A("defer_plan", "?P")], A("executable", "?P")),
        R("r_action", [A("action_exists", "?A"), A("action_available", "?A")],
          A("action_executable", "?A")),
    ]


def _plan_effects():
    return {
        "executable(P_launch)": {"TF7b": 0.5, "TF6d": 0.3, "TF5b": 0.3},
        "executable(P_defer)": {"TF7b": -0.5},
    }


def _plan_constitution():
    acq = {
        "A_root": 1.0,
        **{f"D{m}": 0.9 for m in range(1, 8)},
        **{f"W{m}": 0.8 for m in range(1, 8)},
        **{f"P{m}": 0.8 for m in range(1, 8)},
    }
    acq["W7"] = 0.4
    acq["P7"] = 0.3
    return replace(default_constitution(), acquisition=acq)


def task_recursive_plan():
    goal = GoalFrame(
        goal_id="g_launch", foundation_ref="TF7b",
        desired_outcome=A("executable", "?P"), kind="plan",
        required_knowledge=("market_knowledge",),
        required_capability=("print_capacity",))
    return Problem(
        "recursive_plan_01",
        "Publish the volume: knowledge and capability are missing.",
        _plan_facts(), _plan_rules(),
        [A("executable", "P_launch"), A("executable", "P_defer")],
        goal,
        authored_effects=_plan_effects(),
        available_actions={"market_knowledge": "market_research",
                           "print_capacity": "restructure_resources"},
        world_actions={
            "market_research": {
                "add_facts": [A("known", "market_knowledge")],
                "acquisition": {"W7": 0.9},
            },
            "restructure_resources": {
                "add_facts": [A("has_capability", "print_capacity")],
                "acquisition": {"P7": 0.8},
            },
        })


def task_needs_capability():
    goal = GoalFrame(
        goal_id="g_nocap", foundation_ref="TF6d",
        desired_outcome=A("executable", "?P"), kind="plan",
        required_knowledge=("market_knowledge",),
        required_capability=("print_capacity",))
    facts = _plan_facts() + [A("known", "market_knowledge")]
    return Problem(
        "needs_capability_01",
        "Knowledge acquired; production capability absent and unobtainable.",
        facts, _plan_rules(),
        [A("executable", "P_launch"), A("executable", "P_defer")],
        goal,
        authored_effects=_plan_effects(),
        available_actions={"market_knowledge": "market_research"},
        world_actions={
            "market_research": {
                "add_facts": [A("known", "market_knowledge")],
                "acquisition": {"W7": 0.9},
            },
        })


def task_recursive_nested():
    """Depth-2 recursion: the capability action itself needs knowledge.

    P_launch needs market_knowledge (research1) and print_capacity
    (build1); but build1 has its own prerequisite market2 (research2).
    The machine must descend capability -> knowledge and climb back out.
    """
    goal = GoalFrame(
        goal_id="g_nested", foundation_ref="TF7b",
        desired_outcome=A("executable", "?P"), kind="plan",
        required_knowledge=("market_knowledge",),
        required_capability=("print_capacity",))
    facts = [
        A("plan_for", "P_launch", "G"),
        A("requires_knowledge", "P_launch", "market_knowledge"),
        A("requires_capability", "P_launch", "print_capacity"),
        A("defer_plan", "P_defer"),
        A("action_exists", "research1"),
        A("action_available", "research1"),
        A("action_exists", "build1"),
        A("action_available", "build1"),
        A("action_exists", "research2"),
        A("action_available", "research2"),
    ]
    return Problem(
        "recursive_nested_01",
        "Launch, whose production step needs its own market research.",
        facts, _plan_rules(),
        [A("executable", "P_launch"), A("executable", "P_defer")],
        goal,
        authored_effects=_plan_effects(),
        available_actions={
            "market_knowledge": "research1",
            "print_capacity": "build1",
            "market2": "research2",
        },
        world_actions={
            "research1": {
                "add_facts": [A("known", "market_knowledge")],
                "acquisition": {"W7": 0.9},
            },
            "build1": {
                "add_facts": [A("has_capability", "print_capacity")],
                "acquisition": {"P7": 0.8},
            },
            "research2": {
                "add_facts": [A("known", "market2")],
            },
        },
        action_prerequisites={
            "build1": {"knowledge": ["market2"], "capability": []},
        })


# --------------------------------------------------------------------------
# 6. Memory-dependent reasoning
# --------------------------------------------------------------------------
def task_memory():
    facts = [A("has", "a", "x")]
    rules = [R("r_is", [A("has", "?X", "?Y")], A("is", "?X", "?Y"))]
    goal = GoalFrame(goal_id="g_mem", foundation_ref="TF2b",
                     desired_outcome=A("is", "b", "y"), kind="question")
    return Problem("memory_01",
                   "Is b y? (depends on remembered experience)",
                   facts, rules, [A("is", "b", "y"), A("is", "a", "x")], goal)


# --------------------------------------------------------------------------
# 7. Contradiction surface
# --------------------------------------------------------------------------
def task_contradiction():
    facts = [A("plan_has", "P1", "f1"), A("missing", "P1", "f1")]
    rules = [
        R("viable", [A("plan_has", "?P", "f1")], A("viable", "?P")),
        R("not_viable", [A("missing", "?P", "?F")], A("not_viable", "?P")),
    ]
    goal = GoalFrame(goal_id="g_conflict", foundation_ref="TF5b",
                     desired_outcome=A("viable", "?P"), kind="plan")
    return Problem("contradiction_01",
                   "Evidence supports and refutes the same plan.",
                   facts, rules, [A("viable", "P1")], goal)


BATTERY = {
    "transitive": task_transitive,
    "transitive_negative": task_transitive_negative,
    "constraint": task_constraint,
    "inadmissible": task_inadmissible,
    "fault": task_fault,
    "fault_missing_reading": task_fault_missing_reading,
    "missing_info": task_missing_info,
    "recursive_plan": task_recursive_plan,
    "recursive_nested": task_recursive_nested,
    "needs_capability": task_needs_capability,
    "memory": task_memory,
    "contradiction": task_contradiction,
}

# Tasks whose constitutions differ from the default.
CONSTITUTIONS = {
    "recursive_plan": _plan_constitution,
    "recursive_nested": _plan_constitution,
    "needs_capability": _plan_constitution,
}


def constitution_for(name):
    factory = CONSTITUTIONS.get(name) or default_constitution
    return factory()
