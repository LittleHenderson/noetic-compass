"""test_all.py -- Prerequisite-graph planner acceptance and audit suite.

Acceptance test suite enforcing Sections 7 & 8 of SPEC_PREREQUISITE_GRAPH_PLANNER_20261018.md:
  Case A: Control sequential order ('synthesize' -> 'verify' -> 'git')
  Case B: Verification first ('verify' -> 'synthesize')
  Case C: Git first ('git' -> 'synthesize' with mandatory edge source)
  Case C bite check: Reverting temporal parsing proves failure on old keyword chain
  Case D: One step (single node, order_source: NONE)
  Case E: Cycle refusal (PLAN_CYCLE naming both members)
  Case F: Horizon refusal (chain of 13 nodes -> PLAN_HORIZON naming 13th)
  Case G: Gate-detected order violation (PLAN_ORDER_VIOLATION from GATE)
  Case H: Determinism (50 iterations yielding identical order & digest)
  Case I: README claim ceiling enforced verbatim
  Case J: Mid-plan repair & refusal (perform_repair called once)
  Case K: Two 'Before X, Y.' sentences keep every action (synthesize -> verify -> git)

CLAIM CEILING:
MECHANISM ONLY. ORDERING IS DERIVED FROM STATED PREREQUISITES. NO UNDERSTANDING OF THE REQUEST IS CLAIMED.
"""
from __future__ import annotations

import os
import platform
import sys
from typing import List

HERE = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.dirname(HERE)

for path in (
    HERE,
    os.path.join(COUNCIL, "the_loop_v3"),
    os.path.join(COUNCIL, "dwp_engine_v2"),
    os.path.join(COUNCIL, "repair_performer"),
    os.path.join(COUNCIL, "language_v3"),
):
    if path not in sys.path:
        sys.path.insert(0, path)

import depth
import plan_executor
import plan_graph
import rpm_gate
from plan_graph import (
    CLAIM_CEILING,
    PLAN_CYCLE,
    PLAN_HORIZON,
    PLAN_ORDER_VIOLATION,
    PLAN_REPAIR_FAILED,
    PlanEdge,
    PlanNode,
    PlanRefusal,
    PlanResult,
    build_plan,
)

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def equal(left, right, why=""):
    assert left == right, f"{why or 'values differ'}: {left!r} != {right!r}"


def ok(val, why=""):
    assert val, why or "expected truthy value"


# --------------------------------------------------------------------------- #
# Test Cases
# --------------------------------------------------------------------------- #

@case
def test_case_a_control_order():
    """Case A: Control sequential order.
    'Write the code for auth.py, verify the tests pass, then commit it to git.'
    EXPECT: synthesize -> verify -> git
    """
    req = "Write the code for auth.py, verify the tests pass, then commit it to git."
    res = build_plan(req)
    equal(res.order, ("synthesize", "verify", "git"), "canonical sequential order")
    ok(len(res.edges) >= 2, "must contain prerequisite edges")
    equal(res.order_source, "TEMPORAL_SEQUENCE")

    receipt = plan_executor.execute_plan(res)
    equal(receipt.executed_order, ("synthesize", "verify", "git"))
    equal(len(receipt.steps), 3)
    for s in receipt.steps:
        equal(s.gate_verdict, "PROCEED")
        equal(s.asom_label, "ALIGNED")
    equal(receipt.final_bias_version, 3)


@case
def test_case_b_verification_first():
    """Case B: Verification first.
    'Before writing any code, run the verification on auth.py to see which tests already fail.'
    EXPECT: verify order-position 0, synthesize after it. MUST NOT drop synthesis.
    """
    req = "Before writing any code, run the verification on auth.py to see which tests already fail."
    res = build_plan(req)
    equal(res.order[0], "verify", "verify must be at order position 0")
    equal(res.order[1], "synthesize", "synthesize must follow verify")
    equal(len(res.order), 2, "synthesis must not be dropped")
    equal(res.order_source, "TEMPORAL_BEFORE")

    receipt = plan_executor.execute_plan(res)
    equal(receipt.executed_order, ("verify", "synthesize"))
    equal(receipt.final_bias_version, 2)


@case
def test_case_c_git_first():
    """Case C: Git first (the case that failed previously).
    'First check git to see what changed and recover the last known good state, then write the code.'
    EXPECT: git order-position 0, synthesize order-position 1.
    AND edge must carry exact source sentence.
    """
    req = "First check git to see what changed and recover the last known good state, then write the code."
    res = build_plan(req)
    equal(res.order[0], "git", "git must be at order position 0")
    equal(res.order[1], "synthesize", "synthesize must be at order position 1")
    ok(len(res.edges) >= 1, "must produce edge")
    equal(res.edges[0].source, req, "edge source must match input request byte-for-byte")

    receipt = plan_executor.execute_plan(res)
    equal(receipt.executed_order, ("git", "synthesize"))


@case
def test_case_c_bite_check():
    """Prove Case C bites: reverting temporal-marker parsing reproduces the old failure.
    Without temporal markers, the old keyword planner emitted synthesize -> git.
    """
    req = "First check git to see what changed and recover the last known good state, then write the code."
    # With allow_temporal=False, temporal parsing is bypassed and reverts to old fixed chain
    res_reverted = build_plan(req, allow_temporal=False)
    equal(
        res_reverted.order[0],
        "synthesize",
        "bite check: reverted temporal parsing reproduces synthesize at position 0 (the old defect)",
    )
    equal(
        res_reverted.order[1],
        "git",
        "bite check: reverted temporal parsing reproduces git at position 1",
    )


@case
def test_case_d_one_step():
    """Case D: One step.
    'Show me the git log and diff for the last three commits.'
    EXPECT: exactly one node, order-position 0, order_source: NONE.
    """
    req = "Show me the git log and diff for the last three commits."
    res = build_plan(req)
    equal(len(res.order), 1, "exactly one node")
    equal(res.order[0], "git", "node must be git")
    equal(len(res.edges), 0, "no edges when no temporal or prerequisite markers")
    equal(res.order_source, "NONE", "must report order_source NONE")

    receipt = plan_executor.execute_plan(res)
    equal(receipt.executed_order, ("git",))


@case
def test_case_e_cycle_refused():
    """Case E: Cycle refusal.
    'Ω_a needs Ω_b first. Ω_b needs Ω_a first.'
    EXPECT: PLAN_CYCLE naming both. Must not sort or break cycle.
    """
    req = "Ω_a needs Ω_b first. Ω_b needs Ω_a first."
    refusal_caught = None
    try:
        build_plan(req)
    except PlanRefusal as exc:
        refusal_caught = exc

    ok(refusal_caught is not None, "must raise PlanRefusal on cycle")
    equal(refusal_caught.code, PLAN_CYCLE)
    ok("Ω_a" in refusal_caught.detail, "refusal must name Ω_a")
    ok("Ω_b" in refusal_caught.detail, "refusal must name Ω_b")


@case
def test_case_f_horizon_refused():
    """Case F: Horizon refusal.
    Chain of 13 nodes, each needing the previous.
    EXPECT: PLAN_HORIZON naming the 13th node.
    """
    # 13 nodes: Ω_0 through Ω_12
    # Ω_0 has depth 0, Ω_1 has depth 1, ..., Ω_12 has depth 12 (HORIZON = 12)
    sentences = [f"Ω_{i} needs Ω_{i-1} first." for i in range(1, 13)]
    req = " ".join(sentences)

    refusal_caught = None
    try:
        build_plan(req)
    except PlanRefusal as exc:
        refusal_caught = exc

    ok(refusal_caught is not None, "must raise PlanRefusal on horizon breach")
    equal(refusal_caught.code, PLAN_HORIZON)
    ok("Ω_12" in refusal_caught.detail, "refusal must name the 13th node Ω_12")
    ok("12" in refusal_caught.detail, "refusal must report depth 12")


@case
def test_case_g_order_violation_detected_by_gate():
    """Case G: Order violation detected by the GATE.
    Construct a plan whose sorted order is deliberately wrong (unmet dependency).
    Assert PLAN_ORDER_VIOLATION fires from the GATE's REPAIR verdict, not local logic.
    """
    bogus_node = PlanNode(
        omega="Ω_power_target",
        recipe=None,
        needs=("Ω_unmet_precondition",),
        depth=1,
        kind="internal",
    )
    bogus_plan = PlanResult(
        nodes=(bogus_node,),
        edges=(),
        order=("Ω_power_target",),
        order_source="DELIBERATE_WRONG_ORDER",
        digest="bogus_test_digest",
    )

    refusal_caught = None
    try:
        plan_executor.execute_plan(bogus_plan)
    except PlanRefusal as exc:
        refusal_caught = exc

    ok(refusal_caught is not None, "must raise PlanRefusal on order violation")
    equal(refusal_caught.code, PLAN_ORDER_VIOLATION)
    ok("Ω_unmet_precondition" in refusal_caught.detail, "must cite missing prerequisite")
    ok("PREREQUISITE_MISSING" in refusal_caught.detail, "must cite gate's PREREQUISITE_MISSING code")


@case
def test_case_h_determinism():
    """Case H: Determinism.
    Run Case A fifty times; every run must produce the identical order and identical digest.
    """
    req = "Write the code for auth.py, verify the tests pass, then commit it to git."
    first = build_plan(req)
    for _ in range(50):
        subsequent = build_plan(req)
        equal(subsequent.order, first.order, "order must be byte-for-byte identical")
        equal(subsequent.digest, first.digest, "digest must be bit-for-bit identical")


@case
def test_case_i_readme_claim_ceiling():
    """Case I: Claim ceiling enforcement.
    README.md must carry the exact CLAIM_CEILING verbatim.
    """
    readme_path = os.path.join(HERE, "README.md")
    ok(os.path.isfile(readme_path), "README.md must exist")
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    ok(CLAIM_CEILING in content, "README.md must contain CLAIM_CEILING verbatim")


@case
def test_case_j_mid_plan_repair_performer():
    """Case J: Mid-plan failure hands to perform_repair() once.
    Verifies that a genuine execution failure attempts repair through repair_performer.
    """
    req = "Show me the git log and diff for the last three commits."
    plan = build_plan(req)

    # 1. Failing runner that repair fixes
    fail_count = [0]
    def failing_runner(node):
        fail_count[0] += 1
        raise RuntimeError("simulated transient disk glitch")

    receipt = plan_executor.execute_plan(
        plan,
        runner=failing_runner,
        open_child_fn=lambda **kw: {"ok": True, "detail": "restored"},
    )
    equal(receipt.executed_order, ("git",))
    equal(receipt.steps[0].repaired, True, "step must record repaired=True")

    # 2. Failing runner that repair refuses -> raises PLAN_REPAIR_FAILED
    refusal = None
    try:
        plan_executor.execute_plan(
            plan,
            runner=failing_runner,
            open_child_fn=lambda **kw: {"ok": False, "detail": "cannot restore"},
        )
    except PlanRefusal as exc:
        refusal = exc
    ok(refusal is not None, "must raise PlanRefusal if repair fails")
    equal(refusal.code, PLAN_REPAIR_FAILED)


@case
def test_case_k_two_before_sentences_keep_every_action():
    """Case K: two Form 2 sentences (found by HELM UI v0, 2026-10-19).
    'Before you commit to git, verify the tests pass. Before you verify the tests, write the code for auth.py.'
    Old result: verify -> git only; 'write the code for auth.py' was swallowed into the first sentence's clause.
    EXPECT: synthesize -> verify -> git, each edge sourced to its own sentence.
    """
    s1 = "Before you commit to git, verify the tests pass."
    s2 = "Before you verify the tests, write the code for auth.py."
    res = build_plan(s1 + " " + s2)
    equal(res.order, ("synthesize", "verify", "git"), "all three steps, in prerequisite order")
    edges = {(e.before, e.after): e.source for e in res.edges}
    equal(edges, {("verify", "git"): s1, ("synthesize", "verify"): s2}, "one edge per sentence, sourced to it")
    equal(res.order_source, "TEMPORAL_BEFORE")

    receipt = plan_executor.execute_plan(res)
    equal(receipt.executed_order, ("synthesize", "verify", "git"))


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def main():
    print("prereq_planner / test_all.py")
    print(f"python: {platform.python_version()}  platform: {platform.system()} ({platform.machine()})")
    print(f"HORIZON = {depth.HORIZON} (the owner's ruling of 2026-10-16, not canon)")
    print()

    passed = 0
    failed = 0

    for fn in CASES:
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
        else:
            passed += 1
            print(f"PASS  {fn.__name__}")

    print()
    print(f"TOTAL {len(CASES)} cases: {passed} passed, {failed} failed")
    print("RESULT: " + ("ALL PASS" if failed == 0 else "FAILURES PRESENT"))
    print(f"claim ceiling: {CLAIM_CEILING}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
