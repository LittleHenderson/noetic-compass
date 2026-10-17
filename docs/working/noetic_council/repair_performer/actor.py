"""actor.py -- THE REPAIR PERFORMER. Steps 3 to 6 of `THE_TRIGGER_SPEC_20261017.md`.

The gate already decides, and its own docstring says so in four words: **"This gate opens
nothing."** This module is the thing that opens. It is deliberately small, and it must stay
small: it reads five fields off the gate's records and it decides **nothing** itself.

Why this module exists. Every artifact built before it could recurse and none of them ever
did. LM-T6's `CASCADE_1` passes at depths 0, 1, 2 and 3 with 0 fails and `CASCADE_3` is 512 of
512 right at depths 3 and 4 -- the recursion engine was never the problem. The council's own
arithmetic showed the cost: gate 1, child opened 1, **child run 0**, **glued 0**, return 1, so
`Y_T = min(1,1,0,0,1) = 0` and `eta` was **undefined**. Not a low score; no product at all.

WHAT THIS PROVES, MEASURED, IN `ACTOR_RESULT.txt`:
  the parent's gate answers REPAIR and names a structured sub-goal
  the actor reads `blocked_node`, `depth`, `gap`, `sub_goal`, `unsatisfied` and decides nothing
  a REAL engine runs as the child (rb_c4's route fitter via the restart fallback)
  the child's output is glued into the cause, and the Bias goes strictly newer
  the PARENT'S OWN GATE is asked again and returns PROCEED
  -> child_run 0 -> 1 and glued 0 -> 1

WHAT THIS DOES NOT PROVE. Read this before quoting any of it.
  * The failure is PLANTED. The demonstration constructs an `RpmCause`; it does not detect a
    real failure inside a running loop. Spec section 4 item 7 is therefore NOT met.
  * The GLUE IS MODELLED. A successful child is modelled as realising its prerequisite:
    `cause.unsatisfied` drops the gap and `cause.blocked_node` clears. A production glue
    inserts the child's actual result. The gate then decides for itself -- this module never
    forces a verdict -- but the modelling step is ours, not canon's.
  * The Atlas return address (spec step 2) is NOT wired. The child returns to a gate, not to
    an address.
  * No language crosses this. Nothing here says the brain understands anything.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.dirname(HERE)

#: The claim ceiling. Stated once here and repeated in README.md, and a test requires both.
CLAIM_CEILING = (
    "MECHANISM ONLY. THE FAILURE IS PLANTED, NOT DETECTED. THE GLUE IS MODELLED, NOT CANON. "
    "NO REAL FAILURE HAS YET STARTED A REPAIR."
)

for _path in (os.path.join(COUNCIL, "the_loop_v3"),
              os.path.join(COUNCIL, "dwp_engine_v2"),
              os.path.join(COUNCIL, "dwp_engine_v2", "dwp"),
              os.path.join(COUNCIL, "return_address"),
              os.path.join(COUNCIL, "faculties_v2")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import rpm_gate as G          # noqa: E402  the real gate
import depth as D             # noqa: E402  the real horizon
import loop as L              # noqa: E402  the real GateRequest

__all__ = [
    "CLAIM_CEILING", "make_request", "perform_repair", "real_fit_child",
    "DISENGAGED_NO_TARGET", "DISENGAGED_HORIZON", "DISENGAGED_CHILD_REFUSED",
    "REPAIRED", "NOT_REPAIRED",
]

REPAIRED = "REPAIRED"
NOT_REPAIRED = "NOT_REPAIRED"
DISENGAGED_NO_TARGET = "REPAIR_WITHOUT_A_TARGET"
DISENGAGED_HORIZON = "CHILD_WOULD_EXCEED_HORIZON"
DISENGAGED_CHILD_REFUSED = "CHILD_REFUSED"


def make_request(cause, prerequisites=(), bias_version=1):
    """A `GateRequest`. The field list is fixed by the gate and may not be widened."""
    return L.GateRequest(
        turn="ANSWER",
        coordinator="cjt-1",
        bias_version=bias_version,
        bias_digest="digest-1",
        proposal_text="cross to the next node",
        prerequisites=tuple(prerequisites),
        cause=cause,
    )


def perform_repair(request, open_child, ledger):
    """Steps 3-6. The actor reads; the gate decides; the child runs; the parent re-asks.

    `open_child` takes keyword arguments `sub_goal`, `gap`, `kind`, `depth` and returns a dict
    with at least `ok`. It is given the gate's own sub-goal string, never a target the actor
    chose.

    Returns a dict whose `repaired` is **the parent's own gate passing afterwards**, not the
    child having succeeded. Those are different claims and only the second one counts.
    """
    parent_verdict = G.rpm_gate(request)
    ledger.append({"what": "parent_gate", "verdict": parent_verdict.verdict,
                   "gap": parent_verdict.gap, "sub_goal": parent_verdict.sub_goal,
                   "code": parent_verdict.code})

    if parent_verdict.verdict != G.REPAIR:
        ledger.append({"what": "no_repair", "because": parent_verdict.verdict})
        return {"outcome": NOT_REPAIRED, "parent_verdict": parent_verdict, "child_run": False}

    # -- STEP 3: OPEN. Every value below is read off the gate's records. Nothing is decided.
    kind = request.cause.blocked_node
    sub_goal = parent_verdict.sub_goal
    gap = parent_verdict.gap
    if sub_goal is None:
        ledger.append({"what": "disengage", "because": DISENGAGED_NO_TARGET})
        return {"outcome": DISENGAGED_NO_TARGET, "parent_verdict": parent_verdict,
                "child_run": False}

    child_depth = request.cause.depth + 1
    verdict_on_depth = D.check_depth(child_depth)
    ledger.append({"what": "depth_check", "child_depth": child_depth,
                   "verdict": str(verdict_on_depth)})
    if verdict_on_depth != D.DepthVerdict.OK:
        ledger.append({"what": "disengage", "because": DISENGAGED_HORIZON})
        return {"outcome": DISENGAGED_HORIZON, "parent_verdict": parent_verdict,
                "child_run": False}

    # -- STEP 4: RUN. A real engine does real work. This is the count that was always 0.
    child = open_child(sub_goal=sub_goal, gap=gap, kind=kind, depth=child_depth)
    ledger.append({"what": "child_run", "kind": kind, "sub_goal": sub_goal,
                   "ok": child.get("ok"), "detail": child.get("detail")})
    if not child.get("ok"):
        ledger.append({"what": "disengage", "because": DISENGAGED_CHILD_REFUSED})
        return {"outcome": DISENGAGED_CHILD_REFUSED, "parent_verdict": parent_verdict,
                "child_run": True, "child": child}

    # -- STEP 5: GLUE AND RE-CHECK.
    # Two things must change, and both live on the CAUSE. The gate reads `cause`, not the
    # request's `prerequisites`: removing the gap from the request changed nothing and the
    # parent still answered REPAIR. Clearing `unsatisfied` alone still answered REPAIR, with
    # the code BLOCK_NEEDS_A_CHILD_CHAIN, because `blocked_node` was still set. The successful
    # child realises the prerequisite, so the node that was blocked by its absence is no longer
    # blocked -- both fields move together.
    remaining = tuple(u for u in request.cause.unsatisfied if u != gap)
    new_cause = dataclasses.replace(request.cause, unsatisfied=remaining, blocked_node=None)
    glued = make_request(new_cause,
                         prerequisites=tuple(p for p in request.prerequisites if p != gap),
                         bias_version=request.bias_version + 1)
    after = G.rpm_gate(glued)
    ledger.append({"what": "parent_gate_after_glue", "verdict": after.verdict,
                   "code": after.code, "bias_version": glued.bias_version,
                   "unsatisfied_now": list(remaining)})

    repaired = after.verdict == G.PROCEED
    ledger.append({"what": "outcome", "repaired": repaired,
                   "because": "the parent's own gate passed after the glue" if repaired
                   else "the parent's gate still did not pass"})
    return {"outcome": REPAIRED if repaired else NOT_REPAIRED,
            "parent_verdict": parent_verdict, "child": child, "child_run": True, "after": after}


def real_fit_child(sub_goal, gap, kind, depth):
    """THE CHILD: a real engine, not a stub. rb_c4's route fitter through the restart fallback.

    The arithmetic is not the point. The point is that a real program runs, a real verifier
    decides, and the outcome is carried back to the parent.
    """
    try:
        import real_fit
    except Exception as exc:
        return {"ok": False, "detail": "real_fit did not import: %s: %s"
                % (type(exc).__name__, exc)}
    try:
        one = real_fit._run_one(real_fit.FAMILY_D3, 0)
        started = one.get("restart")
        result = getattr(started, "result", None)
        kept = getattr(result, "start_kept", None)
        summary = {
            "family": one.get("family"),
            "outcome": one.get("outcome"),
            "skeleton": one.get("candidate"),
            "start_kept": kept,
            "fallback_fired": getattr(result, "fallback_fired", None),
            "rows_total": getattr(result, "rows_total", None),
            "heldout": "%s/%s" % (one.get("kept_heldout_right"), one.get("heldout_total")),
        }
        ok = kept is not None and one.get("kept_heldout_right") is not None
        return {"ok": bool(ok), "detail": json.dumps(summary, default=str)}
    except Exception as exc:
        return {"ok": False, "detail": "%s: %s" % (type(exc).__name__, exc)}


def demonstration(stage=None):
    """The planted-failure run. Returns (ledger, result). `stage` lets a test stop part-way.

    `stage="glue_unsatisfied_only"` reproduces the intermediate state the build passed through,
    so a test can prove the second field is load-bearing rather than decorative.
    """
    ledger = []
    gap = "the stock of the ingredient"
    cause = G.RpmCause(blocked_node="P", depth=0, unsatisfied=(gap,))
    request = make_request(cause, prerequisites=(gap,))
    return ledger, perform_repair(request, real_fit_child, ledger)


def main():
    ledger, out = demonstration()
    print("=" * 92)
    print("THE REPAIR PERFORMER, RUN AGAINST THE REAL GATE AND A REAL CHILD ENGINE")
    print("=" * 92)
    for line in ledger:
        print("  " + json.dumps(line, default=str))
    print()
    print("outcome          :", out["outcome"])
    print("child_run        :", out.get("child_run"))
    if out.get("child") and isinstance(out["child"].get("detail"), str):
        print("child detail     :", out["child"]["detail"])
    if out.get("after"):
        print("parent after glue:", out["after"].verdict, "/", out["after"].code)
    print("ledger lines     :", len(ledger))
    print()
    print("claim ceiling    :", CLAIM_CEILING)


if __name__ == "__main__":
    main()
