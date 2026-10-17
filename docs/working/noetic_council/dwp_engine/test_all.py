"""test_all.py -- the whole verification suite for the DWP recursion engine.

Run it with:

    python -B test_all.py

No pytest, no third-party packages, no network, no model calls. Every test is a plain
function decorated with @test; main() runs them all, prints one line each, and exits non-zero
if anything failed.

WHAT THIS SUITE PROVES (mapped to the brief)
--------------------------------------------
P spawns exactly 1 child; W spawns >= 2 and refuses 1; D spawns 0 and leaves depth unchanged
a block at depth 5 yields STRUCTURAL_DEADLOCK, not a depth-6 child
flatten returns siblings at the same level, never deeper
no sequence of resolutions can reach depth 6 (exhaustive over all depth-indexed policies)
the Desire loop can run 1000 iterations and depth stays 0
a dirty child invalidates every ancestor, proven by walking to the root
retraction holds per depth and is checked independently (a depth-3 failure does not pass at 1)
lacunarity is exact and refuses 5 mechanisms

WHAT IT DOES NOT PROVE
----------------------
It does not prove the engine matches a mind, a model, or Helm -- nothing here has run inside
Helm. It does not prove that 5 is the right number; it proves that 5 is the number this build
pins and that the pinned number is not exceeded by any path the engine can take.
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
    for d in (0, 1, 2, 5):
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
def test_desire_loop_1000_iterations_depth_stays_0():
    state = dwp.State(label="d", iterations=1000)
    res = dwp.resolve("D", dwp.Blocked("D"), 0, state)
    assert isinstance(res, dwp.IterativeResolution)
    assert res.cycle.iterations == 1000
    assert res.cycle.operators == ("CO-1", "CO-4", "CO-7")
    assert res.notation == "RPM(F3)[D -> CO-1 -> CO-4 -> CO-7 -> loop(1000)]", res.notation
    # Cycle the same state 1000 times: depth must not move.
    for i in range(1000):
        res = dwp.resolve("D", dwp.Blocked("D"), res.child_depth, state)
        assert res.child_depth == 0
    assert res.child_depth == 0
    assert not hasattr(res, "children")
    print("      D x1000 -> depth 0, iterations 1000")


@test
def test_desire_tree_is_a_single_node():
    tree = dwp.expand(dwp.State(label="d", iterations=1000), lambda d, p: "D", depth=0)
    assert tree.depth == 0
    assert tree.children == (), "the Desire loop must not build a tree"
    assert tree.tag == dwp.ITERATIVE
    assert depth.depth_histogram(tree) == {0: 1}
    assert depth.max_depth(tree) == 0


# ===========================================================================
# 4. The horizon: a block at depth 5 is a Structural Deadlock, not a depth-6 child
# ===========================================================================

@test
def test_check_depth_verdicts():
    assert depth.HORIZON == 5
    for d in range(0, 5):
        assert depth.check_depth(d) is depth.DepthVerdict.OK, d
    for d in (5, 6, 7, 99):
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
        assert res.child_depth is None, "a deadlock must not designate a depth-6 child"
        try:
            dwp.child_chains(res)
        except dwp.NoChildrenError:
            pass
        else:
            raise AssertionError("a Structural Deadlock handed back a child chain")
    print("      P@5 and W@5 -> STRUCTURAL_DEADLOCK, no depth-6 child")


@test
def test_below_horizon_still_resolves():
    res = dwp.resolve("P", dwp.Blocked("P"), 4, dwp.State(label="x"))
    assert isinstance(res, dwp.SingleChildResolution)
    assert res.child_depth == 5  # the last legal level


@test
def test_desire_at_horizon_readings():
    # Default reading: Phi_D adds no level, so a D block at 5 does not exhaust the horizon.
    res = dwp.resolve("D", dwp.Blocked("D"), 5, dwp.State(label="d", iterations=3))
    assert isinstance(res, dwp.IterativeResolution)
    assert res.child_depth == 5
    # Strict reading, exposed for audit: any block at the horizon deadlocks.
    res2 = dwp.resolve("D", dwp.Blocked("D"), 5, dwp.State(label="d", iterations=3),
                       iterative_exempt_at_horizon=False)
    assert isinstance(res2, dwp.DeadlockResolution)
    print("      D@5: iterative by default (U3), deadlock under the strict reading")


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
# 6. No path reaches depth 6
# ===========================================================================

@test
def test_no_sequence_reaches_depth_6_exhaustive():
    """Every depth-indexed blockade policy over depths 0..5: four choices each = 4096 trees."""
    choices = (None, "D", "W", "P")
    state = _two_part_state()
    trees = 0
    deepest_seen = -1
    for policy in itertools.product(choices, repeat=depth.HORIZON + 1):
        blockade = (lambda d, path, pol=policy: pol[d] if d < len(pol) else None)
        tree = dwp.expand(state, blockade, depth=0)
        deepest = depth.assert_within_horizon(tree)
        assert deepest <= depth.HORIZON, (policy, deepest)
        for c in tree.walk():
            assert c.depth <= depth.HORIZON, (policy, c)
            assert c.depth != 6, "a chain reached depth 6"
            if c.tag == dwp.DEADLOCK:
                assert c.depth == depth.HORIZON, ("deadlock below the horizon", c)
        deepest_seen = max(deepest_seen, deepest)
        trees += 1
    assert trees == 4 ** (depth.HORIZON + 1)
    assert deepest_seen == depth.HORIZON, deepest_seen
    print("      %d exhaustive policies, deepest chain = %d, none at depth 6"
          % (trees, deepest_seen))


@test
def test_no_sequence_reaches_depth_6_randomised():
    """500 path-dependent policies over depths 0..9: still nothing at depth 6 or below."""
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
    print("      500 randomised policies over depths 0..9, horizon held")


@test
def test_resolve_never_spawns_past_the_horizon():
    """Even a caller that asks for depth 5 gets a deadlock, not a depth-6 child."""
    for node in ("P", "W"):
        for d in (5, 6, 50):
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
    assert sorted(reports) == [0, 1, 2, 3, 4, 5]
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


def main():
    print("=" * 78)
    print("DWP recursion engine -- test_all.py")
    print("MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.")
    print("HORIZON = %d  (%s)" % (depth.HORIZON, depth.HORIZON_READING))
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
    print("Depth 6 reached: never. Structural Deadlock occurs at depth %d and is flattened, "
          "not extended." % depth.HORIZON)
    print("MECHANISM ONLY. THIS IS NOT THE HELM BRAIN. NOTHING HERE HAS RUN INSIDE HELM.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
