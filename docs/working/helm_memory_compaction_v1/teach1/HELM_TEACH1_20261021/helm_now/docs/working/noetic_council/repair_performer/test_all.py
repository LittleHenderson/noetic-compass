"""test_all.py -- the repair performer's own suite.

Every case here can fail. Two of them exist specifically so that a rule cannot be quietly
weakened: `the_second_glue_field_is_load_bearing` and `the_actor_never_forces_a_verdict`.
"""
from __future__ import annotations

import dataclasses
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import actor
import rpm_gate as G
import depth as D
import loop as L

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def equal(left, right, why=""):
    assert left == right, "%s: %r != %r" % (why or "values differ", left, right)


def ok(value, why=""):
    assert value, why or "expected a true value"


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
def a_power_block(gap="the stock of the ingredient", depth_number=0, dirty=False):
    return G.RpmCause(blocked_node="P", depth=depth_number, unsatisfied=(gap,),
                      ancestor_dirty=dirty)


def a_child_that_works(**_kwargs):
    return {"ok": True, "detail": "a stand-in child for the wiring tests"}


def a_child_that_refuses(**_kwargs):
    return {"ok": False, "detail": "this child cannot fit it"}


def clear_only_unsatisfied(request, gap):
    """The FIRST glue this build tried: it leaves `blocked_node` set. Kept so a test can prove
    the second field is not decoration."""
    remaining = tuple(u for u in request.cause.unsatisfied if u != gap)
    return dataclasses.replace(request.cause, unsatisfied=remaining)


# --------------------------------------------------------------------------------------------
# 1. THE REAL CHAIN CLOSES
# --------------------------------------------------------------------------------------------
@case
def the_real_chain_closes_and_the_parent_gate_says_so():
    """The headline. Real gate, real engine, real verifier."""
    ledger, out = actor.demonstration()
    equal(out["outcome"], actor.REPAIRED, "the chain must close")
    equal(out["child_run"], True, "the child must have run")
    equal(out["parent_verdict"].verdict, G.REPAIR, "the parent starts blocked")
    ok(out["parent_verdict"].sub_goal is not None, "the gate must name a sub-goal")
    equal(out["after"].verdict, G.PROCEED, "the parent's own gate must pass afterwards")
    equal(out["after"].code, "NOTHING_BLOCKED")


@case
def the_child_is_a_real_engine_that_the_verifier_kept():
    """The child is not a stand-in: a fit was kept and it holds up on held-out rows."""
    ledger, out = actor.demonstration()
    detail = out["child"]["detail"]
    ok("TaskB_d3" in detail, "the child ran rb_c4's own TaskB_d3 family")
    ok('"start_kept": 1' in detail, "the verifier kept start 1")
    ok('"heldout": "32/32"' in detail, "held-out was 32 of 32")


@case
def the_sub_goal_comes_from_the_gate_in_the_engines_own_notation():
    ledger, out = actor.demonstration()
    equal(out["parent_verdict"].sub_goal, "RPM(the stock of the ingredient)@1")


# --------------------------------------------------------------------------------------------
# 2. THE GLUE -- and proof that each field is load-bearing
# --------------------------------------------------------------------------------------------
@case
def the_second_glue_field_is_load_bearing():
    """Clear only `unsatisfied` and the parent STILL refuses. This is what makes the test bite:
    if someone deletes the `blocked_node=None` from the glue, this case fails."""
    request = actor.make_request(a_power_block(), prerequisites=("the stock of the ingredient",))
    verdict = G.rpm_gate(request)
    equal(verdict.verdict, G.REPAIR)
    half_glued_cause = clear_only_unsatisfied(request, verdict.gap)
    half = G.rpm_gate(actor.make_request(half_glued_cause, bias_version=request.bias_version + 1))
    equal(half.verdict, G.REPAIR, "half a glue is not a glue")
    equal(half.code, "BLOCK_NEEDS_A_CHILD_CHAIN",
          "the node is still marked blocked, which is exactly why the field must move")


@case
def gluing_the_request_alone_changes_nothing_the_gate_reads():
    """The first glue this build tried removed the gap from `prerequisites` and left `cause`
    untouched. The gate reads `cause`, so nothing happened."""
    request = actor.make_request(a_power_block(), prerequisites=("the stock of the ingredient",))
    verdict = G.rpm_gate(request)
    untouched = actor.make_request(request.cause,
                                   prerequisites=tuple(p for p in request.prerequisites
                                                       if p != verdict.gap),
                                   bias_version=request.bias_version + 1)
    after = G.rpm_gate(untouched)
    equal(after.verdict, G.REPAIR, "the request's prerequisites are not what the gate decides on")
    equal(after.code, "PREREQUISITE_MISSING")


@case
def the_bias_goes_strictly_newer_across_the_glue():
    ledger, out = actor.demonstration()
    equal(out["after"].code, "NOTHING_BLOCKED")
    versions = [line["bias_version"] for line in ledger if "bias_version" in line]
    ok(versions and versions[-1] == 2, "the glued request carries bias version 2")


# --------------------------------------------------------------------------------------------
# 3. THE DISENGAGE LADDER -- it names the gap rather than guessing
# --------------------------------------------------------------------------------------------
@case
def no_sub_goal_means_disengage_not_guess():
    """A REPAIR verdict with no target must stop and say so. It must not invent a target."""
    real_gate = G.rpm_gate

    class Targetless:
        verdict = G.REPAIR
        gap = "something"
        sub_goal = None
        code = "PREREQUISITE_MISSING"

    try:
        G.rpm_gate = lambda request: Targetless()
        ledger = []
        request = actor.make_request(a_power_block())
        out = actor.perform_repair(request, a_child_that_works, ledger)
    finally:
        G.rpm_gate = real_gate
    equal(out["outcome"], actor.DISENGAGED_NO_TARGET)
    equal(out["child_run"], False, "a targetless repair opens no child")


@case
def at_the_horizon_the_gate_refuses_before_any_child_is_opened():
    """A block AT the horizon never reaches the actor's own guard, because the gate has already
    refused it. The actor's horizon check is a second belt, not the first one -- and this case
    pins which of the two actually does the work."""
    ledger = []
    deep = actor.make_request(a_power_block(depth_number=D.HORIZON))
    out = actor.perform_repair(deep, a_child_that_works, ledger)
    equal(out["parent_verdict"].verdict, G.REFUSE,
          "a block at the horizon is REFUSED by the gate itself")
    equal(out["child_run"], False, "no child may be opened at the horizon")
    equal(out["outcome"], actor.NOT_REPAIRED)
    seen = [line["what"] for line in ledger]
    ok("depth_check" not in seen,
       "the gate refused first, so the actor's own depth check never had to run")


@case
def the_actors_own_horizon_guard_still_holds_if_the_gate_lets_it_through():
    """The second belt. If a verdict ever claims REPAIR for a child that would sit past the
    horizon, the actor must refuse to open it."""
    real_gate = G.rpm_gate

    class ClaimsRepair:
        verdict = G.REPAIR
        gap = "something"
        sub_goal = "RPM(something)@13"
        code = "PREREQUISITE_MISSING"

    try:
        G.rpm_gate = lambda request: ClaimsRepair()
        ledger = []
        deep = actor.make_request(a_power_block(depth_number=D.HORIZON))
        out = actor.perform_repair(deep, a_child_that_works, ledger)
    finally:
        G.rpm_gate = real_gate
    equal(out["outcome"], actor.DISENGAGED_HORIZON,
          "the actor's own guard must refuse a child past the horizon")
    equal(out["child_run"], False)


@case
def a_child_that_refuses_is_recorded_and_does_not_repair():
    ledger = []
    request = actor.make_request(a_power_block(), prerequisites=("the stock of the ingredient",))
    out = actor.perform_repair(request, a_child_that_refuses, ledger)
    equal(out["outcome"], actor.DISENGAGED_CHILD_REFUSED)
    equal(out["child_run"], True, "it still ran, and that is recorded")
    seen = [line["what"] for line in ledger]
    ok("child_run" in seen and "outcome" not in seen,
       "a refused child ends the attempt before any outcome line")


# --------------------------------------------------------------------------------------------
# 4. THE GATE STILL DECIDES -- the actor cannot repair what the gate refuses
# --------------------------------------------------------------------------------------------
@case
def a_dirty_ancestor_is_refused_and_never_repaired():
    ledger = []
    request = actor.make_request(a_power_block(dirty=True))
    out = actor.perform_repair(request, a_child_that_works, ledger)
    equal(out["parent_verdict"].verdict, G.REFUSE, "a dirty line is REFUSED, not repaired")
    equal(out["outcome"], actor.NOT_REPAIRED)
    equal(out["child_run"], False, "a refused turn opens nothing")


@case
def the_actor_never_forces_a_verdict():
    """The actor holds no verdict of its own. It must not contain the words PROCEED, REPAIR or
    REFUSE as a literal it could return on its own authority."""
    source = inspect.getsource(actor.perform_repair)
    for word in ('"PROCEED"', '"REPAIR"', '"REFUSE"'):
        assert word not in source, (
            "the actor names %s as a literal; verdicts come from the gate and nowhere else" % word)


@case
def asom_and_the_eye_are_not_in_the_decision_path():
    """No readout and no eye may appear in this module's decision path."""
    source = inspect.getsource(actor.perform_repair)
    for forbidden in ("asom", "eye", "readout"):
        assert forbidden not in source.lower(), "the actor reaches for %r" % (forbidden,)


# --------------------------------------------------------------------------------------------
# 5. THE RECORD
# --------------------------------------------------------------------------------------------
@case
def every_attempt_leaves_ledger_lines():
    ledger, out = actor.demonstration()
    seen = [line["what"] for line in ledger]
    for required in ("parent_gate", "depth_check", "child_run",
                     "parent_gate_after_glue", "outcome"):
        ok(required in seen, "the ledger is missing a %r line" % (required,))
    ok(len(ledger) >= 5)


@case
def the_claim_ceiling_is_stated_here_and_in_the_readme():
    readme = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
    ok(actor.CLAIM_CEILING in readme, "README.md must carry the claim ceiling verbatim")
    ok("PLANTED" in actor.CLAIM_CEILING, "the ceiling must say the failure is planted")
    ok("MODELLED" in actor.CLAIM_CEILING, "the ceiling must say the glue is modelled")


@case
def the_request_field_list_is_not_widened():
    """A label field on the request is how a caller would tell the gate its answer."""
    fields = tuple(f.name for f in dataclasses.fields(L.GateRequest))
    equal(fields, G.GATE_REQUEST_FIELDS, "the request shape must not change")
    assert "label" not in fields, "GateRequest must never carry a label"


# --------------------------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------------------------
def main():
    import platform
    print("repair_performer / test_all.py")
    print("python: %s  platform: %s" % (platform.python_version(), platform.system()))
    print("HORIZON = %d  (the owner's ruling, not canon)" % (D.HORIZON,))
    print()
    passed = failed = 0
    for fn in CASES:
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print("FAIL  %s: %r" % (fn.__name__, str(exc)))
        except Exception as exc:
            failed += 1
            print("ERROR %s: %s: %s" % (fn.__name__, type(exc).__name__, exc))
        else:
            passed += 1
            print("PASS  %s" % (fn.__name__,))
    print()
    print("TOTAL %d cases: %d passed, %d failed" % (len(CASES), passed, failed))
    print("RESULT: %s" % ("ALL PASS" if failed == 0 else "FAILURES PRESENT",))
    print("claim ceiling: %s" % (actor.CLAIM_CEILING,))
    print("claim ceiling, repeated: %s" % (actor.CLAIM_CEILING,))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
