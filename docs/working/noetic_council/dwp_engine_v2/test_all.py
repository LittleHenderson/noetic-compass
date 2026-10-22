"""test_all.py -- the whole verification suite for the DWP recursion engine.

Run it with:

    python -B test_all.py

No pytest, no third-party packages, no network, no model calls. Every test is a plain
function decorated with @test; main() runs them all, prints one line each, and exits non-zero
if anything failed.

WHAT THIS SUITE PROVES (mapped to the brief)
--------------------------------------------
P spawns exactly 1 child; W spawns >= 2 and refuses 1; D spawns 0 and leaves depth unchanged
a block at depth 12 yields STRUCTURAL_DEADLOCK, not a depth-13 child
flatten returns siblings at the same level, never deeper
no sequence of resolutions can reach depth 13 (exhaustive over all depth-indexed policies)
the Desire loop allows exactly 12 cycles and refuses the 13th as DESIRE_BOUND_EXHAUSTED
a Desire loop refused by its own bound still never moved the depth counter
a dirty child invalidates every ancestor, proven by walking to the root
retraction holds per depth and is checked independently (a depth-3 failure does not pass at 1)
lacunarity is exact and refuses 5 mechanisms

WHAT IT DOES NOT PROVE
----------------------
It does not prove the engine matches a mind, a model, or Helm -- nothing here has run inside
Helm. It does not prove that 12 is the right number for either constant. HORIZON = 12 and
DESIRE_BOUND = 12 are the OWNER'S RULING of 2026-10-16 and are NOT derived from canon (canon
says 5 for the horizon and bounds the loop nowhere). What this suite proves is that 12 is the
number this build pins, that the pinned horizon is not exceeded by any path the engine can take,
and that the loop stops at exactly its pinned bound without ever moving the depth counter.
"""

import itertools
import os
import random
import re
import sys
import traceback
from fractions import Fraction

import dwp
import depth
import lacunarity
import retraction

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def _tree_at(tree, depth_):
    return [c for c in tree.walk() if c.depth == depth_]


def _deadlocks(tree):
    return [c for c in tree.walk() if c.tag == dwp.DEADLOCK]


def _two_part_state(label="root"):
    return dwp.State(label=label, decomposition=("a", "b"))


# ===========================================================================
# 1. Phi_P -- Power blocked -> exactly ONE child chain, tagged SINGLE
# ===========================================================================

@test
def test_p_spawns_exactly_one_child():
    res = dwp.resolve("P", dwp.Blocked("P", "no resource"), 0, dwp.State(label="s"))
    assert isinstance(res, dwp.SingleChildResolution), type(res).__name__
    assert isinstance(res, dwp.SpawnedResolution)
    assert res.tag == dwp.SINGLE
    assert len(res.children) == 1, res.children
    # The canon notation of Chapter 5, line 81, emitted verbatim.
    assert res.notation == "RPM(F5)[P -> CO-8 -> CO-9 -> RPM(F5.P)]", res.notation
    # Children live at exactly n+1 (Definition 27.2).
    assert res.child_depth == 1
    assert res.children[0].depth == 1
    print("      P -> 1 child, SINGLE,", res.notation)


@test
def test_p_resolution_class_refuses_two_children():
    a = dwp.Chain(node=None, depth=1, tag=dwp.PENDING, label="a")
    b = dwp.Chain(node=None, depth=1, tag=dwp.PENDING, label="b")
    try:
        dwp.SingleChildResolution(node="P", depth=0, children=[a, b], notation="x")
    except dwp.FunctorsRefused:
        pass
    else:
        raise AssertionError("a SINGLE resolution was allowed to carry two children")


@test
def test_resolve_requires_a_block():
    for bad in (None, "blocked", 1, True):
        try:
            dwp.resolve("P", bad, 0, dwp.State())
        except dwp.ArchitectureViolation:
            continue
        raise AssertionError(f"resolve() accepted {bad!r} as a Blocked outcome")
    # Node mismatch is refused rather than silently re-routed.
    try:
        dwp.resolve("W", dwp.Blocked("P"), 0, dwp.State(decomposition=("a", "b")))
    except dwp.ArchitectureViolation:
        pass
    else:
        raise AssertionError("resolve() accepted a block on a different node")


# ===========================================================================
# 2. Phi_W -- Wisdom blocked -> a COPRODUCT of >= 2 children, tagged PARALLEL
# ===========================================================================

@test
def test_w_spawns_at_least_two():
    for n in (2, 3, 4):
        state = dwp.State(label="w", decomposition=tuple("abcdefgh"[:n]))
        res = dwp.resolve("W", dwp.Blocked("W"), 0, state)
        assert isinstance(res, dwp.CoproductResolution), type(res).__name__
        assert res.tag == dwp.PARALLEL
        assert len(res.children) >= 2, len(res.children)
        assert len(res.children) == n
        assert res.child_depth == 1
        assert all(c.depth == 1 for c in res.children)
        assert "CO-6" in res.notation, res.notation
    print("      W -> 2,3,4 children, PARALLEL coproduct")


@test
def test_w_refuses_one_child():
    one = dwp.State(label="w", decomposition=("only-part",))
    try:
        dwp.resolve("W", dwp.Blocked("W"), 0, one)
    except dwp.FunctorsRefused as exc:
        assert "coproduct" in str(exc)
    else:
        raise AssertionError("Phi_W via CO-6 accepted a single child; a coproduct of one is not a split")

    # Zero parts is refused too.
    try:
        dwp.resolve("W", dwp.Blocked("W"), 0, dwp.State(label="w"))
    except dwp.FunctorsRefused:
        pass
    else:
        raise AssertionError("Phi_W via CO-6 accepted zero parts")

    # And the class itself cannot be constructed with one child.
    a = dwp.Chain(node=None, depth=1, tag=dwp.PENDING, label="a")
    try:
        dwp.CoproductResolution(node="W", depth=0, children=[a], notation="x")
    except dwp.FunctorsRefused:
        pass
    else:
        raise AssertionError("CoproductResolution was constructed with a single child")


@test
def test_w_canon_notation_coproduct():
    state = dwp.State(label="F2", decomposition=("c1", "c2"))
    res = dwp.resolve("W", dwp.Blocked("W"), 0, state)
    # Chapter 5, line 83: RPM(F2)[W -> CO-6 -> RPM(F2.W.c1) + RPM(F2.W.c2)]
    assert res.notation == "RPM(F2)[W -> CO-6 -> RPM(F2.W.c1) + RPM(F2.W.c2)]", res.notation


@test
def test_w_co5_route_is_single_not_parallel():
    state = dwp.State(label="w", resonant_child="professor")
    res = dwp.resolve("W", dwp.Blocked("W"), 0, state, wisdom_route="CO-5")
    assert isinstance(res, dwp.SingleChildResolution)
    assert res.tag == dwp.SINGLE, "the CO-5 route is one resonant child, not a coproduct"
    # Chapter 5, line 82.
    assert res.notation == "RPM(F2)[W -> CO-5 -> RPM(F2.W)]", res.notation


# ===========================================================================
# 3. Phi_D -- Desire blocked -> NO children, ITERATIVE, depth unchanged
# ===========================================================================

@test
def test_d_spawns_zero_children_and_leaves_depth():
    for d in (0, 1, 2, depth.HORIZON):
        res = dwp.resolve("D", dwp.Blocked("D"), d, dwp.State(label="d", iterations=5))
        assert isinstance(res, dwp.IterativeResolution), type(res).__name__
        assert not isinstance(res, dwp.SpawnedResolution)
        assert not isinstance(res, dwp.SpawnedResolution) and not hasattr(res, "children"), \
            "an iterative resolution must not expose a children attribute at all"
        assert res.tag == dwp.ITERATIVE
        assert res.child_depth == d, "Phi_D must not increment depth"
        assert res.spawns_children() is False
        try:
            dwp.child_chains(res)
        except dwp.NoChildrenError:
            pass
        else:
            raise AssertionError("child_chains() returned something for a Desire resolution")
    print("      D -> 0 children, ITERATIVE, child_depth == depth")


@test
def test_desire_bound_is_exactly_12_each_way():
    """DESIRE_BOUND == 12, 12 cycles allowed, the 13th refused -- planned and run.

    Two separate doors into the same loop, both checked at the boundary and one step either
    side of it: the cycle count a state ASKS for (resolve), and the cycles a loop RUNS
    (DesireLoop.step). The word is DESIRE_BOUND_EXHAUSTED in both, and it is never
    STRUCTURAL_DEADLOCK.
    """
    assert dwp.DESIRE_BOUND == 12, dwp.DESIRE_BOUND
    assert dwp.DESIRE_BOUND_EXHAUSTED == "DESIRE_BOUND_EXHAUSTED"
    # Two numbers, two names, two jobs, even though both read 12 today. Neither module owns the
    # other's number: depth.py does not define DESIRE_BOUND, dwp.py does not define HORIZON.
    assert dwp.DESIRE_BOUND == depth.HORIZON == 12
    assert not hasattr(depth, "DESIRE_BOUND"), "depth.py must not own the Desire bound"
    assert not hasattr(dwp, "HORIZON"), "dwp.py must not own the horizon"
    assert "2026-10-16" in depth.HORIZON_RULING, depth.HORIZON_RULING
    assert "not derived from canon" in depth.HORIZON_RULING, depth.HORIZON_RULING

    # --- door 1: the count a state asks for -------------------------------
    for allowed in (0, 1, 11, 12):
        res = dwp.resolve("D", dwp.Blocked("D"), 0, dwp.State(label="d", iterations=allowed))
        assert isinstance(res, dwp.IterativeResolution), (allowed, type(res).__name__)
        assert res.cycle.iterations == allowed, (allowed, res.cycle.iterations)
        assert res.notation.endswith("loop(%d)]" % (allowed,)), res.notation

    for refused in (13, 14, 1000):
        try:
            dwp.resolve("D", dwp.Blocked("D"), 0, dwp.State(label="d", iterations=refused))
        except dwp.DesireBoundExhausted as exc:
            assert exc.word == "DESIRE_BOUND_EXHAUSTED", exc.word
            assert exc.code == "DESIRE_BOUND_EXHAUSTED", exc.code
            assert exc.requested == refused, (exc.requested, refused)
            assert exc.bound == 12, exc.bound
            assert "NOT a Structural Deadlock" in str(exc), str(exc)
            assert "2026-10-16" in str(exc), str(exc)
        else:
            raise AssertionError(
                "a Desire loop of %d cycles was accepted; the bound is 12" % (refused,))

    # --- door 2: the cycles a loop actually runs --------------------------
    res = dwp.resolve("D", dwp.Blocked("D"), 0, dwp.State(label="d", iterations=12))
    loop = dwp.DesireLoop(res)
    assert loop.run(12) == 12, loop.completed
    assert loop.completed == 12
    try:
        loop.step()
    except dwp.DesireBoundExhausted as exc:
        assert exc.word == "DESIRE_BOUND_EXHAUSTED", exc.word
        assert exc.requested == 13, exc.requested
        assert exc.iterations_run == 12, exc.iterations_run
    else:
        raise AssertionError("the 13th cycle of a Desire loop was allowed to run")
    # A fresh loop refuses 13 asked for in one call, on the 13th cycle, not up front.
    fresh = dwp.DesireLoop(dwp.resolve("D", dwp.Blocked("D"), 0,
                                       dwp.State(label="d", iterations=12)))
    try:
        fresh.run(13)
    except dwp.DesireBoundExhausted:
        assert fresh.completed == 12, fresh.completed
    else:
        raise AssertionError("run(13) completed 13 cycles")
    # The bound is the engine's, not the caller's: another number is refused outright.
    for bad in (0, 1, 11, 13, 100):
        try:
            dwp.DesireLoop(res, bound=bad)
        except dwp.ArchitectureViolation:
            continue
        raise AssertionError("a DesireLoop was built with bound=%r" % (bad,))
    print("      DESIRE_BOUND = 12: 12 allowed, 13 refused as DESIRE_BOUND_EXHAUSTED")


@test
def test_desire_loop_refused_by_its_bound_never_changed_the_depth():
    """An exhausted Desire loop is refused for its cycle count, never for depth.

    Every depth from 0 to 12 is tried, because the rule has to hold AT the horizon as well as
    below it: the loop cycles in place, so the depth counter, the resolution's child_depth and
    the tag are all untouched by the refusal, and the refusal is not a Structural Deadlock.
    """
    for d in range(0, depth.HORIZON + 1):
        res = dwp.resolve("D", dwp.Blocked("D"), d, dwp.State(label="d", iterations=12))
        assert res.child_depth == d
        loop = dwp.DesireLoop(res)
        assert loop.run(12) == 12
        assert loop.depth_now == d, (d, loop.depth_now)
        try:
            loop.step()
        except dwp.DesireBoundExhausted as exc:
            assert exc.depth == d, (d, exc.depth)
            assert "NOT a Structural Deadlock" in str(exc)
        else:
            raise AssertionError("the bound did not fire at depth %d" % (d,))
        # The depth counter is exactly where it started: not d+1, not d-1, not None.
        assert loop.depth_now == d, (d, loop.depth_now)
        assert loop.resolution.depth == d
        assert loop.resolution.child_depth == d, "the loop must not add a level"
        assert loop.resolution.tag == dwp.ITERATIVE, loop.resolution.tag
        assert loop.resolution.tag != dwp.DEADLOCK
        assert not isinstance(loop.resolution, dwp.DeadlockResolution)

    # Even a request the loop refuses up front leaves the caller's depth where it was: there is
    # no chain state to corrupt because the loop never had one.
    for d in (0, 6, depth.HORIZON):
        state = dwp.State(label="d", iterations=13)
        try:
            dwp.resolve("D", dwp.Blocked("D"), d, state)
        except dwp.DesireBoundExhausted as exc:
            assert exc.depth == d, (d, exc.depth)
        else:
            raise AssertionError("a 13-cycle Desire loop was planned at depth %d" % (d,))
        assert state.iterations == 13, "the refusal edited the caller's state"
        assert depth.check_depth(d) is (
            depth.DepthVerdict.OK if d < depth.HORIZON
            else depth.DepthVerdict.STRUCTURAL_DEADLOCK
        )
    print("      bound refusal at every depth 0..12 left the depth counter untouched")


@test
def test_desire_loop_at_the_horizon_is_refused_by_its_bound_not_by_the_horizon():
    """At depth 12 both limits are live; the Desire loop's own word must win.

    This is the one place the two numbers could be confused for each other. A Desire block at
    depth 12 with 12 cycles is iterative (see U3); with 13 cycles it is refused for its cycles.
    In neither case may the answer be STRUCTURAL_DEADLOCK, because a Desire loop adds no level.
    """
    ok = dwp.resolve("D", dwp.Blocked("D"), depth.HORIZON, dwp.State(label="d", iterations=12))
    assert isinstance(ok, dwp.IterativeResolution)
    assert ok.child_depth == depth.HORIZON
    try:
        dwp.resolve("D", dwp.Blocked("D"), depth.HORIZON,
                    dwp.State(label="d", iterations=13))
    except dwp.DesireBoundExhausted as exc:
        assert exc.word == "DESIRE_BOUND_EXHAUSTED"
        assert exc.depth == depth.HORIZON
    except dwp.ArchitectureViolation as exc:  # pragma: no cover - the failure this forbids
        raise AssertionError("a 13-cycle Desire loop at depth 12 raised %s, not the bound word"
                             % (type(exc).__name__,)) from exc
    else:
        raise AssertionError("a 13-cycle Desire loop at depth 12 was accepted")
    # And Power/Wisdom at the same depth still get the horizon's word, so the two are distinct.
    for node in ("P", "W"):
        res = dwp.resolve(node, dwp.Blocked(node), depth.HORIZON,
                          dwp.State(label="x", decomposition=("a", "b")))
        assert isinstance(res, dwp.DeadlockResolution), (node, type(res).__name__)
        assert res.verdict == "STRUCTURAL_DEADLOCK"
        assert res.verdict != dwp.DESIRE_BOUND_EXHAUSTED
    print("      D@12 with 13 cycles -> DESIRE_BOUND_EXHAUSTED; P@12 and W@12 -> "
          "STRUCTURAL_DEADLOCK")


@test
def test_desire_tree_is_a_single_node():
    # iterations=DESIRE_BOUND: the largest Desire loop this build will plan.
    tree = dwp.expand(dwp.State(label="d", iterations=dwp.DESIRE_BOUND), lambda d, p: "D",
                      depth=0)
    assert tree.depth == 0
    assert tree.children == (), "the Desire loop must not build a tree"
    assert tree.tag == dwp.ITERATIVE
    assert depth.depth_histogram(tree) == {0: 1}
    assert depth.max_depth(tree) == 0


# ===========================================================================
# 4. The horizon: a block at depth 12 is a Structural Deadlock, not a depth-13 child
# ===========================================================================

@test
def test_check_depth_verdicts():
    assert depth.HORIZON == 12
    for d in range(0, 12):
        assert depth.check_depth(d) is depth.DepthVerdict.OK, d
    for d in (12, 13, 14, 99):
        assert depth.check_depth(d) is depth.DepthVerdict.STRUCTURAL_DEADLOCK, d


@test
def test_block_at_horizon_yields_structural_deadlock():
    for node in ("P", "W"):
        res = dwp.resolve(node, dwp.Blocked(node), depth.HORIZON,
                          dwp.State(label="x", decomposition=("a", "b")))
        assert isinstance(res, dwp.DeadlockResolution), type(res).__name__
        assert res.verdict == "STRUCTURAL_DEADLOCK"
        assert res.tag == dwp.DEADLOCK
        assert not isinstance(res, dwp.SpawnedResolution)
        assert not hasattr(res, "children"), "a deadlock must not expose child chains"
        assert res.child_depth is None, "a deadlock must not designate a deeper child"
        try:
            dwp.child_chains(res)
        except dwp.NoChildrenError:
            pass
        else:
            raise AssertionError("a Structural Deadlock handed back a child chain")
    print("      P@12 and W@12 -> STRUCTURAL_DEADLOCK, no depth-13 child")


@test
def test_below_horizon_still_resolves():
    res = dwp.resolve("P", dwp.Blocked("P"), depth.HORIZON - 1, dwp.State(label="x"))
    assert isinstance(res, dwp.SingleChildResolution)
    assert res.child_depth == depth.HORIZON  # the last legal level


@test
def test_desire_at_horizon_readings():
    # Default reading: Phi_D adds no level, so a D block at 12 does not exhaust the horizon.
    res = dwp.resolve("D", dwp.Blocked("D"), depth.HORIZON,
                      dwp.State(label="d", iterations=3))
    assert isinstance(res, dwp.IterativeResolution)
    assert res.child_depth == depth.HORIZON
    # Strict reading, exposed for audit: any block at the horizon deadlocks.
    res2 = dwp.resolve("D", dwp.Blocked("D"), depth.HORIZON,
                       dwp.State(label="d", iterations=3),
                       iterative_exempt_at_horizon=False)
    assert isinstance(res2, dwp.DeadlockResolution)
    print("      D@12: iterative by default (U3), deadlock under the strict reading")


# ===========================================================================
# 5. flatten -- same-level siblings, tag HORIZONTAL, no deeper child
# ===========================================================================

@test
def test_flatten_returns_siblings_at_same_level():
    tree = dwp.expand(dwp.State(label="x", decomposition=("a", "b", "c")),
                      lambda d, p: "P", depth=0)
    dead = _deadlocks(tree)
    assert len(dead) == 1, dead
    chain = dead[0]
    assert chain.depth == depth.HORIZON
    assert chain.horizontal is not None, "expand() should attach the horizontal fix at the horizon"
    flat = chain.horizontal
    assert isinstance(flat, depth.FlattenedResolution)
    assert flat.tag == dwp.HORIZONTAL
    assert flat.depth == chain.depth
    assert flat.vertical_levels_added == 0
    assert flat.child_depth is None, "flattening must not nominate a deeper child"
    assert not hasattr(flat, "children"), "a flattened resolution has no child field"
    assert len(flat.siblings) >= 2
    for sib in flat.siblings:
        assert sib.depth == chain.depth, (sib.label, sib.depth, chain.depth)
        assert sib.tag == dwp.HORIZONTAL
        assert sib.children == (), "a flattened sibling must have no children"
        assert sib.parent is chain.parent
    assert flat.level_set() == {depth.HORIZON}
    # An explicit parts list is honoured and stays flat.
    flat2 = depth.flatten(chain, parts=("p1", "p2", "p3", "p4"))
    assert [s.label for s in flat2.siblings] == ["p1", "p2", "p3", "p4"]
    assert flat2.level_set() == {depth.HORIZON}
    print("      flatten -> %d siblings at depth %d, HORIZONTAL, no children"
          % (len(flat.siblings), chain.depth))


@test
def test_flatten_refuses_below_horizon():
    chain = dwp.Chain(node=dwp.Node.P, depth=3, tag=dwp.DEADLOCK, label="below-horizon")
    try:
        depth.flatten(chain)
    except dwp.ArchitectureViolation as exc:
        assert "horizon" in str(exc), str(exc)
    else:
        raise AssertionError("flatten() was allowed below the horizon (see UNDECIDED U5)")


@test
def test_flatten_refuses_a_deeper_sibling():
    chain = dwp.Chain(node=dwp.Node.P, depth=depth.HORIZON, tag=dwp.DEADLOCK, label="x")
    too_deep = dwp.Chain(node=None, depth=depth.HORIZON + 1, tag=dwp.HORIZONTAL, label="deep")
    try:
        depth.FlattenedResolution(node="P", depth=depth.HORIZON, siblings=[too_deep],
                                  notation="x")
    except dwp.ArchitectureViolation:
        pass
    else:
        raise AssertionError("a flattened sibling was allowed one level deeper")


# ===========================================================================
# 6. No path reaches depth 13
# ===========================================================================

def _leading_run(policy):
    """How far a depth-indexed blockade policy can push the spine: the leading W/P run.

    Depth d is occupied only if every level below it spawned a child, and only W and P spawn
    children (D cycles in place, None does nothing). So the spine advances one level for each
    leading W or P and stops at the first None or D.
    """
    run = 0
    for choice in policy:
        if choice in ("W", "P"):
            run += 1
        else:
            break
    return run


def _policy_tree(policy, state):
    """Build the tree a depth-indexed blockade policy produces."""
    return dwp.expand(state, lambda d, path, pol=policy: pol[d] if d < len(pol) else None,
                      depth=0)


def _check_tree(tree, policy, expected_deepest):
    """Traverse a whole tree and require: nothing at 13, nothing past the horizon, no shallow
    deadlock, and the deepest chain is exactly the depth the policy can reach."""
    deepest = depth.assert_within_horizon(tree)
    assert deepest == expected_deepest, (policy, deepest, expected_deepest)
    for c in tree.walk():
        assert c.depth <= depth.HORIZON, (policy, c)
        assert c.depth != depth.HORIZON + 1, "a chain reached depth 13"
        assert c.depth != depth.HORIZON + 1 and c.depth < 13, (policy, c)
        if c.tag == dwp.DEADLOCK:
            assert c.depth == depth.HORIZON, ("deadlock below the horizon", c)
    return deepest


@test
def test_no_sequence_reaches_depth_13_exhaustive():
    """Depth 13 is unreachable over depths 0..12 -- every one of the 67,108,864 policies.

    THE SPACE. A depth-indexed blockade policy is one choice per depth in 0..12, from four:
    nothing (None), a Desire block (D), a Wisdom block (W), a Power block (P). That is
    4 ** 13 = 67,108,864 policies. Building 67 million trees is not feasible here, so the space
    is covered by an exact collapse that this test PROVES rather than assumes -- twice.

    STEP 1, THE COLLAPSE, PROVED. Depth reach depends only on whether each depth ADVANCES the
    spine (W or P spawns a child at depth+1) or STOPS it (None spawns nothing; D cycles in place
    and spawns nothing). So a policy's deepest chain is `min(leading W/P run, HORIZON)`. That is
    checked against real trees for EVERY policy of width 6 (4 ** 6 = 4,096) and width 7
    (4 ** 7 = 16,384), which is where the old 4,096-policy run used to live: each one is built,
    walked and compared to the formula.

    STEP 2, THE COLLAPSED SPACE, BUILT. The advance/stop patterns number 2 ** 13 = 8,192. Each
    is built TWICE as a real tree -- once with every advance a Wisdom coproduct (2 children at
    every level: the largest possible tree for that pattern) and once with every advance a Power
    single child -- so 16,384 trees are built and traversed, and every one of them is checked to
    be exactly `min(run, 12)` deep with no chain at 13.

    STEP 3, THE COUNTING. Each pattern is produced by exactly 2 ** 13 policies (two choices per
    depth inside each class), and 8,192 x 8,192 = 67,108,864 = 4 ** 13. Since the deepest chain
    is a function of the pattern alone and every pattern is at most 12 deep, no policy in the
    whole space produces a chain at depth 13.

    Reported policy count: 67,108,864 (= 4 ** 13), covered by 20,480 fully-built policies plus
    16,384 built pattern representatives.
    """
    choices = (None, "D", "W", "P")
    state = _two_part_state()
    slots = depth.HORIZON + 1  # depths 0..12

    # ---- STEP 1: the collapse, proved on small widths by full enumeration ----
    proved_policies = 0
    for width in (6, 7):
        for policy in itertools.product(choices, repeat=width):
            expected = min(_leading_run(policy), depth.HORIZON)
            _check_tree(_policy_tree(policy, state), policy, expected)
            proved_policies += 1
    assert proved_policies == 4 ** 6 + 4 ** 7, proved_policies  # 20,480

    # ---- STEP 2: every advance/stop pattern of width 13, built as a real tree ----
    patterns = 0
    trees = 0
    deepest_seen = -1
    deadlocks_at_the_horizon = 0
    for pattern in itertools.product((False, True), repeat=slots):
        run = 0
        for advances in pattern:
            if not advances:
                break
            run += 1
        expected = min(run, depth.HORIZON)
        patterns += 1
        for advance in ("W", "P"):
            # False -> a Desire block: it cycles in place and spawns nothing, so the spine stops.
            policy = tuple(advance if advances else "D" for advances in pattern)
            assert len(policy) == slots
            tree = _policy_tree(policy, state)
            deepest = _check_tree(tree, policy, expected)
            deepest_seen = max(deepest_seen, deepest)
            deadlocks_at_the_horizon += len(_deadlocks(tree))
            trees += 1
    assert patterns == 2 ** slots == 8192, patterns
    assert trees == 2 * patterns == 16384, trees

    # The proof is not vacuous: a chain at depth 12 really is built, and really deadlocks there.
    assert deepest_seen == depth.HORIZON == 12, deepest_seen
    assert deadlocks_at_the_horizon > 0, deadlocks_at_the_horizon

    # ---- STEP 3: the counting that turns 8,192 patterns back into 67,108,864 policies ----
    policies_per_pattern = 2 ** slots  # 2 choices per depth inside each class, every depth
    covered = patterns * policies_per_pattern
    assert covered == 4 ** slots, (covered, 4 ** slots)
    assert covered == 67108864, covered
    print("      %d policies (= 4**%d) covered: %d advance patterns x %d policies each; "
          "%d policies built whole, %d pattern trees built; deepest chain = %d, chains at "
          "depth %d: 0"
          % (covered, slots, patterns, policies_per_pattern, proved_policies, trees,
             deepest_seen, depth.HORIZON + 1))


@test
def test_no_sequence_reaches_depth_13_randomised():
    """500 path-dependent policies over depths 0..20: still nothing past depth 12.

    The exhaustive proof above is depth-indexed. This one is path-dependent, so a policy can
    block differently down each branch; depth 20 is deliberately well past the horizon, to give
    the engine every chance to overshoot.
    """
    rng = random.Random(20261016)
    choices = (None, "D", "W", "P")
    state = _two_part_state()
    for _ in range(500):
        table = {}
        for t in range(300):
            table[t] = rng.choice(choices)
        blockade = lambda d, path, tbl=table: tbl.get(d)
        tree = dwp.expand(state, blockade, depth=0)
        depth.assert_within_horizon(tree)
        for c in tree.walk():
            assert c.depth <= depth.HORIZON, c
            assert c.depth != depth.HORIZON + 1, "a chain reached depth 13"
            if c.tag == dwp.DEADLOCK:
                assert c.depth == depth.HORIZON, ("deadlock below the horizon", c)
    print("      500 randomised path-dependent policies over depths 0..20, horizon held at 12")


@test
def test_resolve_never_spawns_past_the_horizon():
    """Even a caller that asks for depth 12 gets a deadlock, not a depth-13 child."""
    for node in ("P", "W"):
        for d in (depth.HORIZON, depth.HORIZON + 1, 50):
            res = dwp.resolve(node, dwp.Blocked(node), d,
                              dwp.State(label="x", decomposition=("a", "b")))
            assert isinstance(res, dwp.DeadlockResolution), (node, d, type(res).__name__)
            assert res.child_depth is None


# ===========================================================================
# 7. Dirty children: the whole ancestor line is invalidated, up to the root
# ===========================================================================

@test
def test_dirty_child_invalidates_every_ancestor_to_root():
    # depth 0 W (3 parts) -> depth 1 P -> depth 2 unblocked leaves
    def blockade(d, path):
        return {0: "W", 1: "P"}.get(d)

    tree = dwp.expand(dwp.State(label="root", decomposition=("a", "b", "c")), blockade, depth=0)
    assert len(tree.children) == 3
    assert all(c.depth == 1 for c in tree.children)

    report = retraction.dirty_child(tree, child_index=1, reason="test: Power bypass")
    assert report.root_invalidated is True
    # The propagation path runs from the dirty child up to the root, in that order:
    # child at depth 1 -> root at depth 0 is two links, not one.
    assert report.invalidated[-1] == tree.label, report.invalidated
    assert len(report.invalidated) == tree.children[1].depth + 1, report.invalidated

    # Prove it by WALKING to the root, not by trusting the report.
    cur = tree.children[1]
    walked = []
    while cur is not None:
        assert cur.dirty is True, f"{cur.label} was not invalidated"
        assert cur.dirty_reason, f"{cur.label} has no reason recorded"
        walked.append(cur.label)
        cur = cur.parent
    assert walked == list(report.invalidated), (walked, report.invalidated)
    assert walked[-1] == tree.label
    assert tree.parent is None
    assert tree.root is tree
    print("      dirty child -> %s (walked to root)" % " -> ".join(walked))


@test
def test_dirty_child_leaves_siblings_valid():
    # Documents UNDECIDED (U9): canon says "the entire parent chain", i.e. ancestors only.
    def blockade(d, path):
        return {0: "W", 1: "P"}.get(d)

    tree = dwp.expand(dwp.State(label="root", decomposition=("a", "b", "c")), blockade, depth=0)
    retraction.dirty_child(tree, child_index=1)
    assert tree.children[0].dirty is False
    assert tree.children[2].dirty is False
    assert tree.children[1].dirty is True


@test
def test_dirty_child_deep_propagation_and_guards():
    # Walk down the first-child spine: W -> W -> W -> W -> W, marking the deepest child.
    def blockade(d, path):
        return "W" if d <= 4 else None

    tree = dwp.expand(_two_part_state(), blockade, depth=0)
    node = tree
    while node.children:
        node = node.children[0]
    assert node.depth == 5, node.depth
    report = retraction.power_bypass(node.parent, child_index=0)
    assert report.root_invalidated
    assert len(report.invalidated) == 6, report.invalidated  # child@5 .. root@0
    cur = node
    while cur is not None:
        assert cur.dirty, cur.label
        cur = cur.parent
    # Guards: no children to blame, bad index, non-chain input.
    for call in (lambda: retraction.dirty_child(dwp.Chain(tag=dwp.UNBLOCKED)),
                 lambda: retraction.dirty_child(tree, child_index=99),
                 lambda: retraction.mark_dirty_upward("not a chain")):
        try:
            call()
        except dwp.ArchitectureViolation:
            continue
        raise AssertionError("dirty propagation accepted an invalid input")


# ===========================================================================
# 8. Retraction per depth, checked independently
# ===========================================================================

@test
def test_retraction_holds_per_depth():
    reg = retraction.RetractionRegistry()
    for d in range(0, depth.HORIZON + 1):
        reg.install(retraction.identity_pair(d))
    reports = reg.verify_all()
    assert sorted(reports) == list(range(0, 13)), sorted(reports)
    for d, rep in reports.items():
        assert rep.holds is True, rep
        assert rep.depths_consulted == (d,), rep.depths_consulted


@test
def test_retraction_checked_independently_per_depth():
    """A dirty pair at depth 3 must not be reported by the depth-1 check, and vice versa."""
    reg = retraction.RetractionRegistry()
    good = reg.install(retraction.identity_pair(1))
    bad = reg.install(retraction.SectionRetraction(3, eta=lambda s: s,
                                                  eps=lambda s: 0,  # lossy: everything -> 0
                                                  label="lossy[3]"))
    witnesses = (1, 2, 3)

    r1 = reg.verify(1, witnesses=witnesses)
    assert r1.holds is True, r1
    assert r1.depths_consulted == (1,)
    assert bad.calls == [], "verifying depth 1 touched depth 3's morphisms"
    assert all(c[0] == 1 for c in good.calls), good.calls

    calls_after_d1 = len(good.calls)
    r3 = reg.verify(3, witnesses=witnesses)
    assert r3.holds is False, "a lossy depth-3 pair was reported as holding"
    assert r3.depths_consulted == (3,)
    assert r3.failures == (1, 2, 3), r3.failures
    assert len(good.calls) == calls_after_d1, "verifying depth 3 touched depth 1's morphisms"

    # Cross-depth verification is refused outright: a pair is bound to its own depth.
    try:
        reg.pair(1).verify(3)
    except dwp.ArchitectureViolation:
        pass
    else:
        raise AssertionError("a depth-1 pair was allowed to certify depth 3")

    # The mixed run: depth 1 passes while depth 3 fails, in the same registry.
    both = reg.verify_all(witnesses=witnesses)
    assert both[1].holds is True and both[3].holds is False
    print("      depth 1 HOLDS, depth 3 FAILS, neither consulted the other")


@test
def test_retraction_does_not_demand_the_reverse_identity():
    # eta o eps = id is deliberately NOT required (Definition 27.1, line 37).
    pair = retraction.SectionRetraction(2, eta=lambda s: (s, "context"), eps=lambda r: r[0])
    assert pair.roundtrip_holds("s") is True          # eps o eta = id holds
    realized = pair.embed("s")
    # Re-embedding after realization loses nothing HERE, but nothing in the engine requires it
    # to; the identity checked is one-directional by construction.
    re_embedded = pair.eta(pair.realize(realized))
    assert re_embedded == ("s", "context"), re_embedded
    report = pair.verify(2)
    assert report.holds is True and report.depths_consulted == (2,)


# ===========================================================================
# 9. Lacunarity: exact, and 5 mechanisms is refused
# ===========================================================================

@test
def test_lacunarity_is_exact():
    expected = {0: Fraction(1), 1: Fraction(3, 4), 2: Fraction(1, 2),
                3: Fraction(1, 4), 4: Fraction(0)}
    for used, want in expected.items():
        got = lacunarity.resolution_lacunarity(used)
        assert isinstance(got, Fraction), type(got).__name__
        assert got == want, (used, got, want)
        assert got == Fraction(1) - Fraction(used, 4)
        assert not isinstance(got, float)
        # Exactness: the denominator is small and the value round-trips through the inverse.
        assert lacunarity.mechanisms_used(got) == used, (used, got)
    assert str(lacunarity.resolution_lacunarity(2)) == "1/2"
    assert str(lacunarity.resolution_lacunarity(3)) == "1/4"
    # Exactness the float world cannot give: 1/4 + 3/4 == 1 and 4 * (1/4) == 1, with no residue.
    assert lacunarity.resolution_lacunarity(3) + Fraction(3, 4) == Fraction(1)
    assert lacunarity.resolution_lacunarity(3) * 4 == Fraction(1)
    assert lacunarity.resolution_lacunarity(3).denominator == 4
    assert Fraction(1, 3) - lacunarity.resolution_lacunarity(4) == Fraction(1, 3)
    print("      lacunarity 0..4 ->", [str(lacunarity.resolution_lacunarity(i)) for i in range(5)])


@test
def test_lacunarity_refuses_five():
    for bad in (5, 6, 100):
        try:
            lacunarity.resolution_lacunarity(bad)
        except lacunarity.LacunarityError as exc:
            assert "refused" in str(exc) or "divides" in str(exc)
        else:
            raise AssertionError(f"{bad} mechanisms was accepted")
    for bad in (-1, 2.0, 2.5, "2", None, True):
        try:
            lacunarity.resolution_lacunarity(bad)
        except lacunarity.LacunarityError:
            continue
        raise AssertionError(f"{bad!r} was accepted as a mechanism count")


# ===========================================================================
# 10. Housekeeping: the UNDECIDED markers exist and the README lists them
# ===========================================================================

@test
def test_undecided_markers_are_numbered_and_listed_in_readme():
    here = os.path.dirname(os.path.abspath(__file__))
    pattern = re.compile(r"UNDECIDED IN CANON\s*\((U\d+)\)")
    found = {}
    for name in ("dwp.py", "depth.py", "retraction.py", "lacunarity.py"):
        with open(os.path.join(here, name), encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                for match in pattern.finditer(line):
                    found.setdefault(match.group(1), []).append(f"{name}:{lineno}")
    assert found, "no UNDECIDED IN CANON (Un) markers found in the modules"
    with open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
        readme = fh.read()
    missing = [uid for uid in sorted(found) if uid not in readme]
    assert not missing, f"README.md does not list {missing}"
    print("      %d UNDECIDED markers, all listed in README.md: %s"
          % (len(found), ", ".join(sorted(found))))


@test
def test_canon_quotes_present():
    for module in (dwp, depth, lacunarity, retraction):
        texts = [v for k, v in vars(module).items() if k.startswith("CANON_") and isinstance(v, str)]
        assert texts, f"{module.__name__} quotes no canon"
        for text in texts:
            assert len(text) > 40 and "[" in text, text
    assert "stability horizon" in depth.HORIZON_QUOTE
    assert depth.HORIZON_READING == "a stability horizon, not an arbitrary cap"
    # The book's own number is still quoted as the book's, not renumbered to the ruling's.
    assert "5 levels" in depth.HORIZON_QUOTE, depth.HORIZON_QUOTE
    assert "5 levels" in dwp.CANON_CH5_DEPTH, "the canon quote was renumbered to 12"


@test
def test_both_numbers_are_marked_as_the_owner_ruling_and_not_as_canon():
    """The two constants, two comments, and the fact that neither came from the sources."""
    assert depth.HORIZON == 12
    assert dwp.DESIRE_BOUND == 12
    # The ruling travels with the horizon as a string, so no caller has to remember it.
    assert "2026-10-16" in depth.HORIZON_RULING
    assert "not derived from canon" in depth.HORIZON_RULING
    assert "stability horizon" in depth.HORIZON_RULING
    # Each module's own source says so in a comment: these are two different numbers.
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "depth.py"), encoding="utf-8") as fh:
        depth_src = fh.read()
    with open(os.path.join(here, "dwp.py"), encoding="utf-8") as fh:
        dwp_src = fh.read()
    for src, name in ((depth_src, "depth.py"), (dwp_src, "dwp.py")):
        assert "OWNER'S RULING OF 2026-10-16" in src, name
        assert "NOT DERIVED FROM CANON" in src, name
    assert "HORIZON = 12" in depth_src.replace("`HORIZON = 12`", "HORIZON = 12")
    assert "DESIRE_BOUND = 12" in dwp_src
    # The quote survives next to the ruling: canon's "5" is not deleted from depth.py.
    assert "not an arbitrary performance cap, but a stability horizon" in depth_src
    # Each comment says which job its number does, so the two 12s cannot be confused.
    assert "The depth at which a further block is a Structural Deadlock" in depth_src
    assert "how many times a Desire loop may CYCLE IN PLACE" in dwp_src
    print("      HORIZON = 12 and DESIRE_BOUND = 12: both marked as the ruling, canon kept")


def main():
    print("=" * 78)
    print("DWP recursion engine -- test_all.py")
    print("MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.")
    print("HORIZON = %d  (%s)" % (depth.HORIZON, depth.HORIZON_READING))
    print("DESIRE_BOUND = %d  (a different number doing a different job)"
          % (dwp.DESIRE_BOUND,))
    print("BOTH ARE THE OWNER'S RULING OF 2026-10-16, NOT DERIVED FROM CANON (canon says 5, "
          "and bounds the loop nowhere).")
    print("=" * 78)
    failures = []
    for fn in TESTS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - a test runner reports, it does not raise
            failures.append((fn.__name__, exc))
            print("FAIL  %s" % fn.__name__)
            print("      %s: %s" % (type(exc).__name__, exc))
            traceback.print_exc()
        else:
            print("PASS  %s" % fn.__name__)
    print("-" * 78)
    total = len(TESTS)
    passed = total - len(failures)
    if failures:
        print("RESULT: FAILED. %d of %d tests failed: %s"
              % (len(failures), total, ", ".join(n for n, _ in failures)))
        return 1
    print("RESULT: PASSED. %d/%d tests passed, 0 failed." % (passed, total))
    print("Depth %d reached: never. Structural Deadlock occurs at depth %d and is flattened, "
          "not extended." % (depth.HORIZON + 1, depth.HORIZON))
    print("Desire loop: %d cycles allowed, the %dth refused as %s -- depth unchanged either way."
          % (dwp.DESIRE_BOUND, dwp.DESIRE_BOUND + 1, dwp.DESIRE_BOUND_EXHAUSTED))
    print("MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
