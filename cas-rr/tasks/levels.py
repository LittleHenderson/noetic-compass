"""The capability ladder: L0-L6 with quantified difficulty.

Each level adds a measured difficulty axis:

    D = proof depth (rule applications needed)
    B = branching factor (candidates compared)
    C = constraint load (conditions per plan / premises per rule)
    N = negation load (falsification and contradiction handling)
    U = uncertainty load (missing information -> typed refusal)
    M = memory dependence (result changes only via memory)
    R = recursion depth (nested subgoals)

L6 entries are FRONTIER probes: the machine is expected to refuse them
honestly (NEEDS_INFORMATION) because the operators do not exist yet.
A refusal is scored as the correct behavior, not a failure - refusing is
exactly what the design promises (spec Ch. 12).
"""

from cas_rr.foundations import GoalFrame
from cas_rr.runtime import Problem
from tasks.battery import (
    A, R,
    task_constraint, task_fault, task_memory, task_missing_info,
    task_recursive_nested, task_recursive_plan,
)


def task_l0_recall():
    facts = [A("color", "sky", "blue")]
    goal = GoalFrame(goal_id="g_l0", foundation_ref="TF2b",
                     desired_outcome=A("color", "sky", "blue"), kind="question")
    return Problem("L0_recall", "Direct fact lookup - no rule needed.",
                   facts, [],
                   [A("color", "sky", "blue"), A("color", "sky", "red")], goal)


def task_l1_modus_ponens():
    facts = [A("human", "socrates")]
    rules = [R("r_mp", [A("human", "?X")], A("mortal", "?X"))]
    goal = GoalFrame(goal_id="g_l1", foundation_ref="TF2b",
                     desired_outcome=A("mortal", "socrates"), kind="question")
    return Problem("L1_modus_ponens", "Single rule, single premise.",
                   facts, rules,
                   [A("mortal", "socrates"), A("mortal", "zeus")], goal)


def task_l2_chain():
    facts = [A("precedes", "a", "b"), A("precedes", "b", "c"),
             A("precedes", "c", "d")]
    rules = [R("r_trans",
               [A("precedes", "?X", "?Y"), A("precedes", "?Y", "?Z")],
               A("precedes", "?X", "?Z"))]
    goal = GoalFrame(goal_id="g_l2", foundation_ref="TF2b",
                     desired_outcome=A("precedes", "a", "d"), kind="question")
    return Problem("L2_chain4", "Depth-3 chained deduction.",
                   facts, rules,
                   [A("precedes", "a", "d"), A("precedes", "d", "a")], goal)


def task_l6_arithmetic_supported():
    facts = [A("height", "ada", "5"), A("height", "bo", "3"), A("gt", "5", "3")]
    rules = [R("r_taller",
               [A("height", "?X", "?Hx"), A("height", "?Y", "?Hy"),
                A("gt", "?Hx", "?Hy")],
               A("taller", "?X", "?Y"))]
    goal = GoalFrame(goal_id="g_l6a", foundation_ref="TF2b",
                     desired_outcome=A("taller", "ada", "bo"), kind="question")
    return Problem("L6a_arithmetic_encoded",
                   "Numeric comparison supplied as data.",
                   facts, rules,
                   [A("taller", "ada", "bo"), A("taller", "bo", "ada")], goal)


def task_l6_arithmetic_unsupported():
    facts = [A("height", "ada", "5"), A("height", "bo", "3")]
    rules = [R("r_taller",
               [A("height", "?X", "?Hx"), A("height", "?Y", "?Hy"),
                A("gt", "?Hx", "?Hy")],
               A("taller", "?X", "?Y"))]
    goal = GoalFrame(goal_id="g_l6b", foundation_ref="TF2b",
                     desired_outcome=A("taller", "ada", "bo"), kind="question")
    return Problem("L6b_arithmetic_unencoded",
                   "Numeric comparison NOT supplied - must refuse to compute.",
                   facts, rules,
                   [A("taller", "ada", "bo"), A("taller", "bo", "ada")], goal)


def task_l6_induction():
    facts = [A("swan", "a"), A("white", "a"),
             A("swan", "b"), A("white", "b")]
    goal = GoalFrame(goal_id="g_l6c", foundation_ref="TF2b",
                     desired_outcome=A("all_swans_white"), kind="question")
    return Problem("L6c_induction",
                   "Generalize from examples - no such operator exists.",
                   facts, [],
                   [A("all_swans_white"), A("not_all_swans_white")], goal)


def task_l6_probabilistic():
    facts = [A("vote", "P1"), A("vote", "P2")]
    rules = [R("r_wins", [A("more_votes", "?P")], A("wins", "?P"))]
    goal = GoalFrame(goal_id="g_l6d", foundation_ref="TF5b",
                     desired_outcome=A("wins", "?P"), kind="question")
    return Problem("L6d_probabilistic",
                   "Majority judgment without counting machinery.",
                   facts, rules, [A("wins", "P1"), A("wins", "P2")], goal)


def task_l6_hypothetical():
    facts = [A("rain", "today")]
    goal = GoalFrame(goal_id="g_l6e", foundation_ref="TF2b",
                     desired_outcome=A("implies", "rain", "wet"), kind="question")
    return Problem("L6e_hypothetical",
                   "Conditional proof - assumption handling does not exist.",
                   facts, [],
                   [A("implies", "rain", "wet"), A("implies", "wet", "rain")],
                   goal)


LADDER = [
    dict(level="L0", name="fact recall", builder=task_l0_recall,
         expected_status="CONCLUDED", expected_output="color(sky,blue)",
         note="D=0 B=2: direct memory match, no rule"),
    dict(level="L1", name="modus ponens", builder=task_l1_modus_ponens,
         expected_status="CONCLUDED", expected_output="mortal(socrates)",
         note="D=1 C=1 B=2: single rule, single premise"),
    dict(level="L2", name="chained deduction", builder=task_l2_chain,
         expected_status="CONCLUDED", expected_output="precedes(a,d)",
         note="D=3 B=2: three-link chain, two rule applications"),
    dict(level="L3", name="constraint satisfaction", builder=task_constraint,
         expected_status="CONCLUDED", expected_output="viable(P1)",
         note="C=5 B=3 N=2: five conditions, two falsified plans"),
    dict(level="L4", name="fault diagnosis", builder=task_fault,
         expected_status="CONCLUDED", expected_output="first_bad(S3)",
         note="B=5 N=4 U=1: test-point walk-down"),
    dict(level="L4", name="honest refusal", builder=task_missing_info,
         expected_status="NEEDS_INFORMATION", expected_output=None,
         note="U=1 M=1: typed lacunae instead of invention"),
    dict(level="L5", name="recursive planning (depth 1)",
         builder=task_recursive_plan, constitution="plan",
         expected_status="CONCLUDED", expected_output="executable(P_launch)",
         note="R=1 C=2: KNOWLEDGE then CAPABILITY subgoals"),
    dict(level="L5", name="recursive planning (depth 2)",
         builder=task_recursive_nested, constitution="plan",
         expected_status="CONCLUDED", expected_output="executable(P_launch)",
         note="R=2: the capability subgoal descends into its own knowledge subgoal"),
    dict(level="L5", name="memory-dependent reasoning", builder=task_memory,
         protocol="memory",
         expected_status="CONCLUDED", expected_output="is(b,y)",
         note="M=1: NEEDS_INFORMATION before the memory, CONCLUDED after"),
    # ------------------------------------------------------------- FRONTIER
    dict(level="L6", name="arithmetic (comparison as data)",
         builder=task_l6_arithmetic_supported,
         expected_status="CONCLUDED", expected_output="taller(ada,bo)",
         note="frontier: numeric reasoning works only when the comparison is encoded"),
    dict(level="L6", name="arithmetic (unencoded)", builder=task_l6_arithmetic_unsupported,
         expected_status="NEEDS_INFORMATION", expected_output=None,
         note="frontier: refuses to compute 5>3 by itself"),
    dict(level="L6", name="induction", builder=task_l6_induction,
         expected_status="NEEDS_INFORMATION", expected_output=None,
         note="frontier: no generalization operator"),
    dict(level="L6", name="probabilistic reasoning", builder=task_l6_probabilistic,
         expected_status="NEEDS_INFORMATION", expected_output=None,
         note="frontier: no counting/majority machinery"),
    dict(level="L6", name="hypothetical reasoning", builder=task_l6_hypothetical,
         expected_status="NEEDS_INFORMATION", expected_output=None,
         note="frontier: no conditional proof"),
]
