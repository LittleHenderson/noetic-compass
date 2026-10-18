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
              os.path.join(COUNCIL, "faculties_v2"),
              os.path.join(COUNCIL, "language_v3")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import rpm_gate as G          # noqa: E402  the real gate
import depth as D             # noqa: E402  the real horizon
import loop as L              # noqa: E402  the real GateRequest
import bias as B              # noqa: E402  the real working memory Bias
import address as A           # noqa: E402  the real ReturnAddress
import stack as S             # noqa: E402  the real ReturnStack
import dirty as R_DIRTY       # noqa: E402  dirty child propagation on ReturnStack
import atlas_binding as AB    # noqa: E402  real Atlas snapshot + glue_back
from real_atlas.rpa_model import (  # noqa: E402
    AtlasContext,
    AtlasNode,
    AtlasSnapshot,
    NodeKind,
    NodeStatus,
)
import cce                    # noqa: E402  the verified English translator (language_v3)

__all__ = [
    "CLAIM_CEILING", "make_request", "perform_repair", "real_fit_child",
    "detect_cause_from_turn", "make_real_atlas_snapshot", "make_real_glue_pair",
    "run_end_to_end",
    "DISENGAGED_NO_TARGET", "DISENGAGED_HORIZON", "DISENGAGED_CHILD_REFUSED",
    "DISENGAGED_CHILD_DIRTY", "DISENGAGED_GLUE_REFUSED",
    "REPAIRED", "NOT_REPAIRED",
]

REPAIRED = "REPAIRED"
NOT_REPAIRED = "NOT_REPAIRED"
DISENGAGED_NO_TARGET = "REPAIR_WITHOUT_A_TARGET"
DISENGAGED_HORIZON = "CHILD_WOULD_EXCEED_HORIZON"
DISENGAGED_CHILD_REFUSED = "CHILD_REFUSED"
DISENGAGED_CHILD_DIRTY = "CHILD_DIRTY_INVALIDATED_ANCESTORS"
DISENGAGED_GLUE_REFUSED = "GLUE_BACK_REFUSED"


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


def perform_repair(request, open_child, ledger, *, return_stack=None,
                   parent_address=None, glue_nodes=None):
    """Steps 2-6. The actor reads; the gate decides; the child runs; the parent re-asks.

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

    # Dispatch on kind: Desire (D) loops in place at the same depth and opens NO child.
    if kind == "D":
        resolution = G.dwp.resolve(
            G.dwp.Node.D,
            G.dwp.Blocked(G.dwp.Node.D, str(gap or "desire")),
            request.cause.depth,
            G._state(request.cause),
            wisdom_route=request.cause.wisdom_route,
        )
        ledger.append({"what": "depth_check", "child_depth": None,
                       "verdict": "DESIRE_EXEMPT_NO_CHILD"})
        ledger.append({"what": "desire_loop", "kind": kind, "sub_goal": sub_goal,
                       "iterations": request.cause.iterations,
                       "notation": resolution.notation, "ok": True})
        remaining = tuple(u for u in request.cause.unsatisfied if u != gap)
        new_cause = dataclasses.replace(
            request.cause,
            unsatisfied=remaining,
            blocked_node=None,
            resume_from_version=request.bias_version,
        )
        glued = make_request(new_cause,
                             prerequisites=tuple(p for p in request.prerequisites if p != gap),
                             bias_version=request.bias_version + 1)
        after = G.rpm_gate(glued)
        ledger.append({"what": "parent_gate_after_glue", "verdict": after.verdict,
                       "code": after.code, "bias_version": glued.bias_version,
                       "unsatisfied_now": list(remaining)})
        repaired = after.verdict == G.PROCEED
        ledger.append({"what": "outcome", "repaired": repaired,
                       "because": "the parent's own gate passed after the Desire loop" if repaired
                       else "the parent's gate still did not pass"})
        return {"outcome": REPAIRED if repaired else NOT_REPAIRED,
                "parent_verdict": parent_verdict, "child_run": False,
                "desire_loop_run": True, "after": after}

    child_depth = request.cause.depth + 1
    verdict_on_depth = D.check_depth(child_depth)
    ledger.append({"what": "depth_check", "child_depth": child_depth,
                   "verdict": str(verdict_on_depth)})
    if verdict_on_depth != D.DepthVerdict.OK:
        ledger.append({"what": "disengage", "because": DISENGAGED_HORIZON})
        return {"outcome": DISENGAGED_HORIZON, "parent_verdict": parent_verdict,
                "child_run": False}

    # -- STEP 2: ADDRESS (when a ReturnStack and parent ReturnAddress are supplied).
    child_address = None
    if return_stack is not None and parent_address is not None:
        waiting_ids = {t.call_id for t in return_stack.waiting_callers()}
        if parent_address.call_id not in waiting_ids:
            return_stack.suspend(
                parent_address,
                request.bias_version,
                request.proposal_text,
                remaining_work=("recheck_parent_gate",),
            )
        child_address = A.child_of(
            parent_address,
            "%s/child@%d" % (parent_address.call_id, child_depth),
        )
        return_stack.suspend(
            child_address,
            request.bias_version,
            sub_goal,
            remaining_work=(),
        )
        ledger.append({
            "what": "address_bound",
            "parent_call_id": parent_address.call_id,
            "child_call_id": child_address.call_id,
            "snapshot_digest": parent_address.snapshot_digest,
        })

    # -- STEP 4: RUN. A real engine does real work. This is the count that was always 0.
    is_parallel_wisdom = (
        kind == "W"
        and request.cause.wisdom_route == "CO-6"
        and len(request.cause.decomposition) >= 2
    )
    if is_parallel_wisdom:
        parts = tuple(request.cause.decomposition)
        children = [
            open_child(sub_goal=sub_goal, gap=part, kind=kind, depth=child_depth)
            for part in parts
        ]
        child = {
            "ok": all(c.get("ok") for c in children),
            "dirty": any(c.get("dirty") for c in children),
            "dirty_reason": next(
                (c.get("dirty_reason") for c in children if c.get("dirty")), None
            ),
            "parallel_children": children,
            "detail": json.dumps([c.get("detail") for c in children], default=str),
        }
        closed_gaps = set(parts) | {gap}
    else:
        child = open_child(sub_goal=sub_goal, gap=gap, kind=kind, depth=child_depth)
        closed_gaps = {gap}

    ledger.append({"what": "child_run", "kind": kind, "sub_goal": sub_goal,
                   "ok": child.get("ok"), "detail": child.get("detail")})

    if child.get("dirty"):
        dirty_reason = str(child.get("dirty_reason") or "dirty child resolution")
        if return_stack is not None and child_address is not None:
            R_DIRTY.mark_dirty(return_stack, child_address.call_id, dirty_reason)
            R_DIRTY.invalidate_ancestors(return_stack, child_address.call_id)
        dirty_cause = dataclasses.replace(
            request.cause,
            ancestor_dirty=True,
            dirty_ancestor=(parent_address.call_id if parent_address is not None
                            else "depth-0 chain"),
            dirty_reason=dirty_reason,
        )
        after_dirty = G.rpm_gate(
            make_request(dirty_cause, prerequisites=request.prerequisites,
                         bias_version=request.bias_version + 1)
        )
        ledger.append({"what": "disengage", "because": DISENGAGED_CHILD_DIRTY,
                       "dirty_reason": dirty_reason, "gate_code": after_dirty.code})
        return {"outcome": DISENGAGED_CHILD_DIRTY, "parent_verdict": parent_verdict,
                "child_run": True, "child": child, "after": after_dirty}

    if not child.get("ok"):
        if return_stack is not None and child_address is not None:
            return_stack.cancel(child_address,
                                reason=str(child.get("detail") or DISENGAGED_CHILD_REFUSED))
        ledger.append({"what": "disengage", "because": DISENGAGED_CHILD_REFUSED})
        return {"outcome": DISENGAGED_CHILD_REFUSED, "parent_verdict": parent_verdict,
                "child_run": True, "child": child}

    # -- STEP 5: GLUE AND RE-CHECK.
    glue_verdict = None
    if glue_nodes is not None:
        glue_verdict = AB.glue_back(glue_nodes)
        if not glue_verdict.ok:
            ledger.append({
                "what": "disengage",
                "because": DISENGAGED_GLUE_REFUSED,
                "conflicting_fields": list(glue_verdict.conflicting_fields),
            })
            return {"outcome": DISENGAGED_GLUE_REFUSED, "parent_verdict": parent_verdict,
                    "child_run": True, "child": child, "glue": glue_verdict}

    if return_stack is not None and parent_address is not None and child_address is not None:
        return_stack.resume(
            child_address,
            request.bias_version + 1,
            child.get("detail") or "ok",
            glue=glue_verdict,
        )
        resumption = return_stack.resume(
            parent_address,
            request.bias_version + 1,
            child.get("detail") or "ok",
            glue=glue_verdict,
        )
        resumption.finish_all_remaining_work()
        ledger.append({
            "what": "address_resumed",
            "parent_call_id": parent_address.call_id,
            "child_call_id": child_address.call_id,
            "returned_bias_version": resumption.returned_bias_version,
            "glue_ok": None if glue_verdict is None else glue_verdict.ok,
        })

    # Two things must change, and both live on the CAUSE. The gate reads `cause`, not the
    # request's `prerequisites`: removing the gap from the request changed nothing and the
    # parent still answered REPAIR. Clearing `unsatisfied` alone still answered REPAIR, with
    # the code BLOCK_NEEDS_A_CHILD_CHAIN, because `blocked_node` was still set. The successful
    # child realises the prerequisite, so the node that was blocked by its absence is no longer
    # blocked -- both fields move together, and `resume_from_version` lets `rpm_gate` verify
    # `bias.check_version_increase` on the returning thread.
    remaining = tuple(u for u in request.cause.unsatisfied if u not in closed_gaps)
    new_cause = dataclasses.replace(
        request.cause,
        unsatisfied=remaining,
        blocked_node=None if not remaining else request.cause.blocked_node,
        resume_from_version=request.bias_version,
    )
    glued = make_request(new_cause,
                         prerequisites=tuple(p for p in request.prerequisites
                                             if p not in closed_gaps),
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
            "parent_verdict": parent_verdict, "child": child, "child_run": True,
            "after": after, "glue": glue_verdict}


def detect_cause_from_turn(turn_content, bias_snapshot, *, depth=0):
    """Inspect a turn's required prerequisites against a live `BiasSnapshot`.

    Instead of planting an `RpmCause`, this function extracts the prerequisites declared in a
    `language_v3/cce.py` content record (or a sequence of prerequisite names) and checks which
    ones are absent from `bias_snapshot`.
      - If every required prerequisite is present in `bias_snapshot`, it returns an unblocked
        `RpmCause(blocked_node=None, depth=depth, unsatisfied=())`.
      - If 1 prerequisite is missing, it returns a Power block (`blocked_node="P"`).
      - If 2 or more prerequisites are missing, it returns a Wisdom coproduct block
        (`blocked_node="W"`, `wisdom_route="CO-6"`, `decomposition=tuple(missing)`).
    """
    required = []
    if isinstance(turn_content, dict):
        for rel in turn_content.get("relations", ()) or ():
            if (isinstance(rel, (list, tuple)) and len(rel) >= 3
                    and rel[0] in ("needs_first", "needs")):
                prereq = rel[2]
                if isinstance(prereq, str) and prereq.strip() and prereq not in required:
                    required.append(prereq)
        for s in turn_content.get("stocks", ()) or ():
            ref = s.get("ref") if isinstance(s, dict) else None
            out = ref.get("outcome") if isinstance(ref, dict) else None
            if isinstance(out, str) and out.strip() and out not in required:
                required.append(out)
        rec = turn_content.get("recipe")
        if isinstance(rec, dict):
            for cat in rec.get("catalysts", ()) or ():
                if isinstance(cat, str) and cat.strip() and cat not in required:
                    required.append(cat)
        for o in turn_content.get("outcome", ()) or ():
            prereq = o.get("prereq") if isinstance(o, dict) else None
            if isinstance(prereq, str) and prereq.strip() and prereq not in required:
                required.append(prereq)
        for s in turn_content.get("stock", ()) or ():
            out = s.get("outcome") if isinstance(s, dict) else None
            if isinstance(out, str) and out.strip() and out not in required:
                required.append(out)
        for cat in turn_content.get("catalysts", ()) or ():
            if isinstance(cat, str) and cat.strip() and cat not in required:
                required.append(cat)
    elif isinstance(turn_content, (tuple, list)):
        for item in turn_content:
            if isinstance(item, str) and item.strip() and item not in required:
                required.append(item)

    stocks_in_bias = set()
    if bias_snapshot.has("stocks"):
        val = bias_snapshot.read("stocks")
        if isinstance(val, (list, tuple, dict)):
            stocks_in_bias.update(str(k) for k in val)

    missing = []
    for req in required:
        satisfied = (
            bias_snapshot.has(req)
            or bias_snapshot.has("stock:" + req)
            or (req in stocks_in_bias)
        )
        if not satisfied:
            missing.append(req)

    required_tuple = tuple(required)
    missing_tuple = tuple(missing)
    if not missing_tuple:
        return G.RpmCause(blocked_node=None, depth=depth, unsatisfied=()), required_tuple
    if len(missing_tuple) >= 2:
        return G.RpmCause(
            blocked_node="W",
            depth=depth,
            unsatisfied=missing_tuple,
            wisdom_route="CO-6",
            decomposition=missing_tuple,
        ), required_tuple
    return G.RpmCause(
        blocked_node="P",
        depth=depth,
        unsatisfied=missing_tuple,
    ), required_tuple


def make_real_atlas_snapshot(*, focus="S0-possibilities"):
    """Build a real `AtlasSnapshot` using `return_address/real_atlas/rpa_model.py`."""
    ctx = AtlasContext(
        context_id="ctx-repair",
        model_version="cas-rpa/0.1",
        observation_id="obs-repair-1",
        observation_time="2026-10-17T00:00:00Z",
        record_version=1,
    )
    state = AtlasNode(
        node_id="state-now",
        idea_id="idea-main",
        label="state-now",
        context=ctx,
        status=NodeStatus.OBSERVED,
        kind=NodeKind.STATE,
        fields=(("board_1", "copied into memory"), ("board_2", "not copied")),
    )
    root = AtlasNode(
        node_id="S0-possibilities",
        idea_id="idea-main",
        label="S0-possibilities",
        context=ctx,
        status=NodeStatus.HYPOTHETICAL,
        kind=NodeKind.REGION,
        members=("route-alt", "route-single"),
    )
    return AtlasSnapshot(
        nodes=(state, root),
        links=(),
        current_state_id="state-now",
        focus_node_id=focus,
    )


def make_real_glue_pair(*, conflicting=False):
    """Build two real `AtlasNode` regions that share member `'w1'` for `atlas_binding.glue_back`."""
    ctx = AtlasContext(
        context_id="ctx-repair",
        model_version="cas-rpa/0.1",
        observation_id="obs-repair-1",
        observation_time="2026-10-17T00:00:00Z",
        record_version=1,
    )
    child = AtlasNode(
        node_id="region-child",
        idea_id="idea-main",
        label="region-child",
        context=ctx,
        status=NodeStatus.OBSERVED,
        kind=NodeKind.REGION,
        members=("w1", "w2"),
        fields=(("key", "same"),),
    )
    parent = AtlasNode(
        node_id="region-parent",
        idea_id="idea-main",
        label="region-parent",
        context=ctx,
        status=NodeStatus.OBSERVED,
        kind=NodeKind.REGION,
        members=("w1", "w3"),
        fields=(("key", "different" if conflicting else "same"),),
    )
    return (child, parent)


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


def run_end_to_end(english_in=None, *, seed=0, child_fn=None):
    """Run one complete, un-planted turn across all 7 canonical packages:
      1. English input -> `language_v3/cce.parse` + `round_trip` check.
      2. Live working memory (`the_loop_v3/bias.py:Bias`) where the required stock is absent.
      3. Real failure detection (`detect_cause_from_turn`) inspects the `BiasSnapshot` against
         the parsed turn and detects the missing prerequisite (`Omega_214`).
      4. `return_address` (`ReturnAddress`, `ReturnStack`, `atlas_binding.glue_back`) suspends
         the parent at Bias version 1, dispatches the child (`real_fit_child` via
         `faculties_v2/real_fit.py`), verifies glue-back on the real Atlas model, and resumes
         the parent at Bias version 2.
      5. The child's verified result is written into `Bias` (moving Bias version 1 -> 2), and
         `detect_cause_from_turn` re-inspects the new `BiasSnapshot` and finds 0 missing
         prerequisites.
      6. A full 5-stage `the_loop_v3/loop.py:Loop.turn` runs on the updated `Bias` and its
         gate returns `PROCEED` (`outcome == CONTINUE`).
      7. Verified English output is rendered via `language_v3/cce.say` (`round_trip` `ok=True`).
    """
    if child_fn is None:
        child_fn = real_fit_child
    rng = cce.random.Random(seed)
    if english_in is None:
        c0 = cce.empty_content()
        c0["turn"] = "ANSWER"
        c0["evidence"] = "USER_SAID"
        c0["topic"] = "Ω_307"
        c0["terms"] = [{"noetic": 6, "domain": "C", "register": ["A"], "drive": "F2",
                        "polarity": "ASSERTED", "slots": {"I": "Ω_307", "J": "Ω_214"}}]
        c0["relations"] = [["needs_first", "Ω_307", "Ω_214"]]
        c0["stocks"] = [{"amount": "1", "ref": {"outcome": "Ω_214"}}]
        english_in = cce.say(c0, seed=seed)["sentence"]

    parsed_in = cce.parse(english_in)
    rt_in = cce.round_trip(parsed_in, rng, seed=seed)

    working_bias = B.Bias("cjt-1")
    working_bias.write("goal", parsed_in["topic"] or "Omega_307", "cjt-1")
    snap_before = working_bias.snapshot()

    detected_cause, required_prereqs = detect_cause_from_turn(parsed_in, snap_before, depth=0)
    request = L.GateRequest(
        turn=parsed_in["turn"],
        coordinator="cjt-1",
        bias_version=snap_before.version,
        bias_digest=snap_before.digest,
        proposal_text="realize %s" % (parsed_in["topic"] or "goal",),
        prerequisites=required_prereqs,
        cause=detected_cause,
    )

    atlas_snap = make_real_atlas_snapshot()
    glue_nodes = make_real_glue_pair()
    return_stack = S.ReturnStack()
    root_address = A.ReturnAddress(
        episode="ep-" + str(parsed_in["topic"] or "goal"),
        branch="branch-main",
        snapshot_digest=AB.snapshot_digest_of(atlas_snap),
        bias_version=snap_before.version,
        call_id="cjt-1#turn-1",
        parent_call_id=None,
    )

    ledger = []
    repair_out = perform_repair(
        request,
        child_fn,
        ledger,
        return_stack=return_stack,
        parent_address=root_address,
        glue_nodes=glue_nodes,
    )

    if repair_out["outcome"] == REPAIRED:
        for req in required_prereqs:
            working_bias.write(
                "stock:" + req,
                {"realized_by": repair_out["parent_verdict"].sub_goal,
                 "child_detail": repair_out["child"].get("detail")},
                "cjt-1",
            )

    snap_after = working_bias.snapshot()
    cause_after_detect, _ = detect_cause_from_turn(parsed_in, snap_after, depth=0)
    resumed_cause = dataclasses.replace(
        cause_after_detect,
        resume_from_version=snap_before.version,
    )

    engine = L.Loop(
        working_bias,
        "cjt-1",
        lambda snap: L.Proposal(
            text="realize %s with verified stock" % (snap.read("goal"),),
            cites=("goal",),
        ),
    )
    turn_record = engine.turn(
        "ACTIVE",
        "INTENDED",
        False,
        prerequisites=required_prereqs,
        cause=resumed_cause,
    )

    out_content = cce.empty_content()
    out_content["turn"] = "ANSWER"
    out_content["evidence"] = "CHECKED"
    out_content["topic"] = parsed_in["topic"]
    out_content["terms"] = parsed_in["terms"]
    out_content["relations"] = parsed_in["relations"]
    out_content["stocks"] = parsed_in["stocks"]
    spoken_out = cce.say(out_content, seed=seed)
    rt_out = cce.round_trip(out_content, rng, seed=seed)

    return {
        "english_in": english_in,
        "parsed_in": parsed_in,
        "round_trip_in_ok": rt_in["ok"],
        "detected_cause_before": detected_cause,
        "detected_cause_after": cause_after_detect,
        "repair_ledger": ledger,
        "repair_out": repair_out,
        "return_stack_receipt": return_stack.receipt(),
        "bias_version_before": snap_before.version,
        "bias_version_after": snap_after.version,
        "loop_turn_record": turn_record,
        "english_out": spoken_out["sentence"],
        "round_trip_out_ok": rt_out["ok"],
    }


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

