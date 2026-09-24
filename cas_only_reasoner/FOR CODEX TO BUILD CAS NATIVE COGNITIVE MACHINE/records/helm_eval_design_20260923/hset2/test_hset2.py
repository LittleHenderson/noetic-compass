"""Tests for the HSET-2 build (CLAUDE_BUILT_CLAUDE_CHECKED). Pure Python, THROWAWAY salts and public seeds only.

Three groups, run one at a time (each under about 3 minutes on the laptop):
    python -B -m pytest -p no:cacheprovider -q test_hset2.py -m "not e2e and not slow"
    python -B -m pytest -p no:cacheprovider -q test_hset2.py -m e2e
    python -B -m pytest -p no:cacheprovider -q test_hset2.py -m slow
Tests that build worlds need the pinned CNCM tree (785c9bd1), written by
`../hset2_aws_job/launch.py --materialize-tree DIR` outside the repository; pass it as HSET2_PACKAGE_ROOT.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import random
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import hset2_stage0_public as S0  # noqa: E402

hw, B, oracle = S0.modules()
import hset1a_build as A  # noqa: E402

ROOT = os.environ.get("HSET2_PACKAGE_ROOT")
needs_root = pytest.mark.skipif(not ROOT, reason="HSET2_PACKAGE_ROOT (the materialized 785c9bd1 tree) is not set")
NON_BREACHING_SEED = "tiny-9"          # its throwaway HSET-1A salt puts no PUBLIC_EXCLUDED class in TEST_NEW_5
BREACHING_SEED = "tiny-1"              # its throwaway HSET-1A salt puts one PUBLIC_EXCLUDED class in TEST_NEW_5


def H():
    import hset2_build
    if ROOT:
        hset2_build._paths(ROOT)
    return hset2_build


def throwaway_salt(seed, which):
    return hashlib.sha256((H().THROWAWAY_PREFIX + seed + "|" + which).encode()).hexdigest()


# ============================================================================ split and side rule (A1 D1)
def test_group_key_is_pinned_spelling():
    edges = ((0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (4, 5))
    key = S0.group_key((6, edges))
    pairs = sorted(zip(*[[sum(1 for a, b in edges if b == v) for v in range(6)],
                         [sum(1 for a, b in edges if a == v) for v in range(6)]]))
    assert key == json.dumps([6, [list(p) for p in pairs]], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert key == hw.canon([6, [list(p) for p in hw.degree_multiset(6, list(edges))]])
    assert key == "[6,[[0,2],[1,0],[1,1],[1,1],[1,1],[2,1]]]"


def test_side_rule_bytes():
    for key in ("[6,[[0,2],[1,0],[1,1],[1,1],[1,1],[2,1]]]", "[6,[[0,1],[0,1],[0,1],[0,1],[1,0],[4,1]]]", "x"):
        first = hashlib.sha256(b"HSET-2-group-side-v0.1:" + key.encode("utf-8")).digest()[0]
        assert S0.side_of_group(key) == ("DEV" if first < 64 else "TEST")
    # the byte threshold is 64: a quarter of the byte range
    assert S0.DEV_SIDE_BYTE_BELOW == 64 and S0.GROUP_SIDE_PREFIX == b"HSET-2-group-side-v0.1:"


def test_enumeration_matches_oracle_at_5_nodes():
    assert S0.enumerate_classes(5) == oracle.dag_classes(5)


def test_stage0_committed_outputs_reproduce_and_are_consistent():
    files, _ = S0.outputs(S0.read_fixture_bytes())
    assert S0.committed_check(files, HERE) == []
    summary = json.loads(files[S0.SUMMARY_FILE])
    sides = {s: json.loads(files[f]) for s, f in (("DEV", S0.DEV_GROUPS_FILE), ("TEST", S0.TEST_GROUPS_FILE))}
    assert summary["six_node_universe"]["classes_enumerated"] == 5074
    assert summary["six_node_universe"]["classes_after_public_excluded"] == 5071
    assert (sides["DEV"]["group_count"], sides["DEV"]["class_count"]) == (503, 1324)
    assert (sides["TEST"]["group_count"], sides["TEST"]["class_count"]) == (1434, 3747)
    dev_side = set()
    for s, doc in sides.items():
        for row in doc["groups"]:
            assert S0.side_of_group(row["group_key"]) == s                 # whole groups, by the pinned rule
            for k in row["classes"]:
                assert S0.group_key(S0.key_shape(k)) == row["group_key"]
                if s == "DEV":
                    dev_side.add(k)
    dev6 = summary["dev_new_6"]["classes_in_draw_order"]
    assert len(dev6) == len(set(dev6)) == 60 and set(dev6) <= dev_side
    assert set(summary["dev_decoys_6"]["classes"]) == dev_side - set(dev6)
    again, draws = S0.draw_side(S0.DEV_SEED, "dev", 6, 60, dev_side)
    assert again == dev6 and draws == summary["dev_new_6"]["draws"]


def test_split_five_throwaway_and_withheld_rule():
    classes5 = oracle.dag_classes(5)
    facts5 = {S0.class_key(s): A.shape_facts(hw, s) for s in classes5}
    pe = json.loads((HERE / S0.PUBLIC_EXCLUDED_FILE).read_text(encoding="utf-8"))
    excluded = {r["canonical_form"] for r in pe["classes"]}
    dev5, test5, _ = A.split_five(hw, throwaway_salt(NON_BREACHING_SEED, "hset1a"), facts5)
    assert len(dev5) == len(test5) == 60 and not set(dev5) & set(test5)
    withheld5 = sorted(set(facts5) - set(dev5) - set(test5) - excluded)
    assert H().check_withheld_5(facts5, dev5, test5, withheld5, excluded)
    with pytest.raises(SystemExit, match="WITHHELD_5"):                    # a WITHHELD_5 that also holds a DEV_NEW_5 class
        H().check_withheld_5(facts5, dev5, test5, withheld5 + [dev5[0]], excluded)
    d1, t1, _ = A.split_five(hw, throwaway_salt(BREACHING_SEED, "hset1a"), facts5)
    with pytest.raises(SystemExit, match="CUSTODY_BREACH"):
        H().check_withheld_5(facts5, d1, t1, sorted(set(facts5) - set(d1) - set(t1) - excluded), excluded)


def test_disjointness_is_counted_not_constant():
    """Review F5: every printed disjointness value is counted from the sets, so a breach shows as a non-zero count."""
    Hm = H()
    all5 = ["a", "b", "c", "d", "e"]
    ok = Hm.disjointness_measured(all5, ["a"], ["b"], ["c", "d"], {"e", "x6"}, ["p", "q"], ["r", "s", "t"], ["p"], ["r"], ["s", "t"])
    assert all(v == 0 for k, v in {**ok["five"], **ok["six"]}.items())
    bad = Hm.disjointness_measured(all5, ["a", "b"], ["b"], ["c", "e"], {"e", "q"}, ["p", "q"], ["q", "s", "t"], ["p", "z"], ["r"], ["s"])
    assert bad["five"]["dev_new_5_meets_test_new_5"] == 1 and bad["five"]["withheld_5_meets_public_excluded"] == 1
    assert bad["five"]["classes_not_covered_by_the_four_sets"] == 1                               # "d"
    assert bad["six"]["dev_side_meets_test_side"] == 1 and bad["six"]["public_excluded_on_test_side"] == 1
    assert bad["six"]["test_new_6_off_the_test_side"] == 1 and bad["six"]["dev_new_6_off_the_dev_side"] == 1
    assert bad["six"]["test_side_not_covered_by_test_new_6_and_withheld_6"] == 2                  # "q" and "t"


@needs_root
def test_test5_digest_is_checked_before_any_item_is_built(monkeypatch):
    """Review F10: a wrong --expect-test5-shapes-digest stops the build right after split_five, before items."""
    Hm = H()
    from cas_meta2.typed_teaching import source
    vocab, _ = hw.vocabulary(source)
    stage0 = Hm.load_stage0(pathlib.Path(ROOT))
    salt1a, salt2 = throwaway_salt(NON_BREACHING_SEED, "hset1a"), throwaway_salt(NON_BREACHING_SEED, "hset2")
    built = []
    monkeypatch.setattr(A, "build_items", lambda *a, **k: built.append(1) or ([], []))
    facts5 = {S0.class_key(s): A.shape_facts(hw, s) for s in oracle.dag_classes(5)}
    with pytest.raises(SystemExit, match="^REFUSED: TEST_NEW_5 does not reproduce HSET-1A's public test_shapes_digest$"):
        Hm.derive(stage0, salt1a, salt2, vocab, source, limit_foci=1, facts5=facts5, expect_test5_digest="0" * 64)
    assert built == []
    right = hw.sha(sorted(A.split_five(hw, salt1a, facts5)[1]))
    D = Hm.derive(stage0, salt1a, salt2, vocab, source, limit_foci=1, only="reach", facts5=facts5, expect_test5_digest=right)
    assert D["test5_digest"] == right and built == [1, 1]


# ============================================================================ PUBLIC_EXCLUDED (s3, M11)
def test_public_excluded_version_1():
    pe = json.loads((HERE / S0.PUBLIC_EXCLUDED_FILE).read_text(encoding="utf-8"))
    assert pe["counts_by_nodes"] == {"5": 3, "6": 4}
    names = sorted(n for r in pe["classes"] for n in r["fixture_shape_names"])
    assert names == ["S5A", "S5B", "S5C", "S6A", "S6B", "S6D", "S6STAR"]
    for r in pe["classes"]:
        assert r["digest"] == hashlib.sha256(r["canonical_form"].encode("utf-8")).hexdigest()
        n, edges = S0.key_shape(r["canonical_form"])
        assert oracle.canonical_form(n, edges) == (n, edges)
        assert r["inside_degree_4_universe"] == (r["fixture_shape_names"] != ["S6STAR"])
    assert pe["version_1_input"]["sha256"] == S0.FIXTURE_SHA256


# ============================================================================ comparators on hand-made cases (s6)
def plain_world(n, edges, whole=0, participants=None, domain="mechanical"):
    refs = ["w/n%d" % i for i in range(n)]
    return {"world_id": "w", "nodes": [{"ref": r} for r in refs], "contains": [{"source": refs[a], "target": refs[b]} for a, b in edges],
            "declared_whole": refs[whole], "declarations": {"domain": domain, "participants": [refs[p] for p in (participants or [whole, 1, 2])]}}


def named(world_id, n, edges, domain, whole=0, participants=None):
    w = plain_world(n, edges, whole=whole, participants=participants, domain=domain)
    w["world_id"] = world_id
    w["nodes"] = [{"ref": "%s/n%d" % (world_id, i)} for i in range(n)]
    w["contains"] = [{"source": "%s/n%d" % (world_id, a), "target": "%s/n%d" % (world_id, b)} for a, b in edges]
    w["declared_whole"] = "%s/n%d" % (world_id, whole)
    w["declarations"]["participants"] = ["%s/n%d" % (world_id, p) for p in (participants or [whole, 1, 2])]
    return w


def test_three_hop_first_child_rules():
    three_hop = H().three_hop_payload
    chain = plain_world(5, [(0, 1), (1, 2), (2, 3), (3, 4)])
    q = lambda part, rule: {"arguments": {"whole": "w/n0", "part": "w/n%d" % part}, "rule": rule}   # noqa: E731
    first, bfs = "first_direct_constituent_lexical_v1", "bfs_immediate_predecessor_lexical_v1"
    assert three_hop(chain, q(1, first)) == {"state": "DIRECT", "via": None}
    assert three_hop(chain, q(3, first)) == {"state": "VIA", "via": "w/n1"}   # 2 steps below the child
    assert three_hop(chain, q(4, first)) == {"state": "ABSENT", "via": None}  # 3 steps below the child: out of reach
    assert three_hop(chain, q(2, bfs)) == {"state": "VIA", "via": "w/n1"}
    assert three_hop(chain, q(3, bfs)) == {"state": "VIA", "via": "w/n2"}     # the predecessor at 2 steps
    assert three_hop(chain, q(4, bfs)) == {"state": "ABSENT", "via": None}
    # first-child rule: the LOWEST-RANK child with a short path wins, even if another child reaches it too
    fork = plain_world(6, [(0, 1), (0, 2), (1, 3), (3, 4), (2, 4), (4, 5)])
    assert three_hop(fork, q(4, first)) == {"state": "VIA", "via": "w/n1"}
    assert three_hop(fork, q(5, first)) == {"state": "VIA", "via": "w/n2"}    # n1 needs 3 steps; n2 needs 2
    assert H().reach_comparators() == tuple(A.COMPARATORS["reach"]) + (
        "THREE_HOP_FIRST_CHILD", "SINGLE_ROOT_FALLBACK", "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP")


def test_single_root_fallback_rules():
    """A2 (review F2): two-hop (or three-hop), then VIA a fixed node when the shape has exactly one root."""
    Hm = H()
    first, bfs = "first_direct_constituent_lexical_v1", "bfs_immediate_predecessor_lexical_v1"
    q = lambda part, rule: {"arguments": {"whole": "w/n0", "part": "w/n%d" % part}, "rule": rule}   # noqa: E731

    def run(world, part, rule):
        base, _ = A._comparators("reach", world, q(part, rule))
        return Hm.extra_reach_payloads(world, q(part, rule), base)
    chain = plain_world(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])               # one root
    out = run(chain, 4, first)
    assert out["SINGLE_ROOT_FALLBACK"] == {"state": "VIA", "via": "w/n1"}      # two-hop fails; one root: lowest child
    assert out["SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"] == {"state": "VIA", "via": "w/n1"}
    assert run(chain, 4, bfs)["SINGLE_ROOT_FALLBACK"] == {"state": "VIA", "via": "w/n3"}   # the part's lowest parent
    assert run(chain, 2, first)["SINGLE_ROOT_FALLBACK"] == {"state": "VIA", "via": "w/n1"}  # two-hop answers first
    assert run(chain, 1, bfs)["SINGLE_ROOT_FALLBACK"] == {"state": "DIRECT", "via": None}
    # the BFS fallback names the lowest-RANK parent of the part, not the parent on the path
    diamond = plain_world(6, [(0, 1), (0, 2), (2, 3), (3, 5), (1, 4), (4, 5)])
    assert run(diamond, 5, bfs)["SINGLE_ROOT_FALLBACK"] == {"state": "VIA", "via": "w/n3"}
    # two roots (n0 and n1): the fallback keeps ABSENT, even where a path exists
    two_roots = plain_world(6, [(0, 2), (1, 2), (2, 3), (3, 4), (4, 5)])
    assert run(two_roots, 5, first)["SINGLE_ROOT_FALLBACK"] == {"state": "ABSENT", "via": None}
    assert run(two_roots, 5, first)["SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"] == {"state": "ABSENT", "via": None}
    assert hw.reach_gold(6, [(0, 2), (1, 2), (2, 3), (3, 4), (4, 5)], 0, 5, {i: i for i in range(6)}, hw.REACH_FIRST) == ("VIA", 2)
    # the three-hop form answers a 3-step part by three-hop, not by the fallback
    assert run(chain, 3, first)["SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"] == {"state": "VIA", "via": "w/n1"}
    assert run(chain, 3, bfs)["SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"] == {"state": "VIA", "via": "w/n2"}
    # the 3-step claim's bars leave out exactly the two rules built on three-hop
    reg = Hm.registered_comparators()["reach"]
    assert set(reg["REACH_4_STEP_TRANSFER_6"]) - set(reg["REACH_3_STEP_TRANSFER_6"]) == {
        "THREE_HOP_FIRST_CHILD", "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"}


def test_reach_comparators_hand_made():
    """The eight reviewed HSET-1A reach comparators plus THREE_HOP_FIRST_CHILD, on one hand-made world, against the
    two frozen rules re-implemented in hset_worlds (the gold)."""
    world = named("w", 5, [(0, 1), (0, 2), (1, 3), (3, 4), (2, 4)], "mechanical", participants=[0, 3, 1])
    q = lambda rule: {"arguments": {"whole": "w/n0", "part": "w/n4"}, "rule": rule}              # noqa: E731
    out, _ = A._comparators("reach", world, q("first_direct_constituent_lexical_v1"))
    via = lambda n: {"state": "VIA", "via": "w/n%d" % n}                                        # noqa: E731
    assert out == {"CONSTANT_ABSENT": {"state": "ABSENT", "via": None}, "CONSTANT_DIRECT": {"state": "DIRECT", "via": None},
                   "ONE_HOP": {"state": "ABSENT", "via": None}, "LOWEST_RANK_CHILD": via(1), "RANK_LAST_CHILD": via(2),
                   "TWO_HOP_FIRST_CHILD": via(2), "PARTICIPANT_2": via(3), "DEGREE_RULE": via(1)}
    assert H().three_hop_payload(world, q("first_direct_constituent_lexical_v1")) == via(1)
    assert H().three_hop_payload(world, q("bfs_immediate_predecessor_lexical_v1")) == via(2)
    edges = [(0, 1), (0, 2), (1, 3), (3, 4), (2, 4)]
    rank = {i: i for i in range(5)}
    assert hw.reach_gold(5, edges, 0, 4, rank, hw.REACH_FIRST) == ("VIA", 1)
    assert hw.reach_gold(5, edges, 0, 4, rank, hw.REACH_BFS) == ("VIA", 2)


def test_correspondence_comparators():
    Hm = H()
    chain = [(0, 1), (1, 2), (2, 3)]
    F = named("F", 4, chain, "mechanical", participants=[0, 1, 2])
    # 1. the same numbering, participants misaligned: identity and the degree guess are valid; the anchored guess is not
    T = named("T", 4, chain, "grammatical", participants=[0, 2, 1])
    out = Hm.correspondence_payloads({"worlds": [F, T]}, "F", "T")
    same = [{"source": "F/n%d" % i, "target": "T/n%d" % i} for i in range(4)]
    assert out["ALWAYS_NO_MATCH"] == {"status": "NO_MATCH", "pairs": []}
    assert out["IDENTITY_BY_RANK"] == out["DEGREE_SORTED"] == out["DEGREE_GUESS_THEN_CHECK"] == {"status": "MAPPING", "pairs": same}
    assert out["FLAG_ANCHOR_GUESS_THEN_CHECK"] == {"status": "NO_MATCH", "pairs": []}
    assert out["WHOLE_ANCHOR_GUESS_THEN_CHECK"] == {"status": "MAPPING", "pairs": same}     # A2: the whole alone is aligned
    assert tuple(out) == Hm.CORRESPONDENCE_COMPARATORS
    # 2. reversed numbering, participants aligned with the structure: the degree guess breaks, the anchored guess holds
    R = named("R", 4, [(3, 2), (2, 1), (1, 0)], "grammatical", whole=3, participants=[3, 2, 1])
    out = Hm.correspondence_payloads({"worlds": [F, R]}, "F", "R")
    guess = {p["source"]: p["target"] for p in out["DEGREE_SORTED"]["pairs"]}
    assert guess == {"F/n0": "R/n3", "F/n1": "R/n1", "F/n2": "R/n2", "F/n3": "R/n0"}     # (in, out), then rank
    assert out["DEGREE_GUESS_THEN_CHECK"] == {"status": "NO_MATCH", "pairs": []}
    assert out["FLAG_ANCHOR_GUESS_THEN_CHECK"]["pairs"] == [{"source": "F/n%d" % i, "target": "R/n%d" % (3 - i)} for i in range(4)]
    assert out["IDENTITY_BY_RANK"]["status"] == "MAPPING"
    # A2: the whole-anchored guess maps n0 to R/n3, then sorts the rest by degree: n3 (1,0) goes to R/n0, and the
    # (1,1) pair n1, n2 goes to R/n1, R/n2 by rank, which breaks the edge n0 -> n1. One guess, one check: NO_MATCH
    assert out["WHOLE_ANCHOR_GUESS_THEN_CHECK"] == {"status": "NO_MATCH", "pairs": []}
    # 3. same degrees, different wiring: no guess can pass the check
    G = named("G", 5, [(0, 1), (0, 2), (1, 3), (3, 4)], "mechanical")
    K = named("K", 5, [(0, 1), (0, 2), (1, 3), (2, 4)], "container")
    out = Hm.correspondence_payloads({"worlds": [G, K]}, "G", "K")
    assert out["DEGREE_SORTED"]["status"] == "MAPPING"
    assert out["DEGREE_GUESS_THEN_CHECK"]["status"] == out["FLAG_ANCHOR_GUESS_THEN_CHECK"]["status"] == "NO_MATCH"
    assert out["WHOLE_ANCHOR_GUESS_THEN_CHECK"]["status"] == "NO_MATCH"
    # different node counts: every comparator answers NO_MATCH
    out = Hm.correspondence_payloads({"worlds": [G, F]}, "G", "F")
    assert all(v == {"status": "NO_MATCH", "pairs": []} for v in out.values()) and tuple(out) == Hm.CORRESPONDENCE_COMPARATORS


def bank_public(worlds, focus="F"):
    return {"worlds": worlds, "bank": {"world_ids": sorted(w["world_id"] for w in worlds)}, "focus_world_id": focus}


def test_analogy_comparators():
    Hm = H()
    S5A = [(0, 1), (0, 2), (1, 3), (3, 4)]
    S5B = [(0, 1), (0, 2), (1, 3), (2, 4)]          # same degrees as S5A, other wiring
    CHAIN = [(0, 1), (1, 2), (2, 3), (3, 4)]        # other degrees, same counts
    key = lambda shape: S0.class_key(oracle.canonical_form(*shape))   # noqa: E731
    worlds = [named("F", 5, S5A, "mechanical", participants=[0, 1, 3]),
              named("A1", 5, S5A, "mechanical"),                       # same domain, isomorphic: a distractor
              named("B2", 5, CHAIN, "container"),                      # a filler: same counts, other degrees
              named("C3", 5, S5B, "grammatical", participants=[0, 1, 2]),   # same-degree decoy, flags anchored
              named("D4", 5, S5A, "procedural", participants=[0, 2, 4])]    # the partner, flags not anchored
    out, tuned = Hm.analogy_payloads(bank_public(worlds), "F", set(), key)
    assert out["ALWAYS_NO_MATCH"] == {"world_id": None}
    assert out["FIRST_CANDIDATE"] == {"world_id": "A1"}
    assert out["NODE_EDGE_COUNT_MATCH"] == {"world_id": "B2"}              # first other-domain with equal counts
    assert out["DEGREE_MULTISET_MATCH"] == {"world_id": "C3"}              # first other-domain same-degree
    assert out["FLAG_ANCHOR"] == {"world_id": "C3"}                        # whole, p2, p3 degrees equal the focus's
    assert out["CANDIDATE_ONLY_NOVELTY"] == {"world_id": "B2"}             # focus-blind but for size and domain
    assert out["OTHER_DOMAIN_ONLY"] == {"world_id": None}                  # two same-degree other-domain candidates
    # A2 (review F1): one guess per same-degree other-domain candidate, in alias order. The decoy C3 fails every check;
    # the partner D4 has the focus's own numbering, so the degree guess and the whole-anchored guess pass; its
    # participants sit elsewhere, so the flag-anchored guess fails; the same-domain A1 is never a candidate
    assert out["DEGREE_GUESS_THEN_CHECK"] == out["WHOLE_ANCHOR_GUESS_THEN_CHECK"] == {"world_id": "D4"}
    assert out["FLAG_ANCHOR_GUESS_THEN_CHECK"] == {"world_id": None}
    assert set(out) | set(tuned) == set(Hm.ANALOGY_COMPARATORS)
    assert tuned["BEST_FIXED_POSITION"] == {str(i): {"world_id": w} for i, w in enumerate(["A1", "B2", "C3", "D4", "F"])}
    assert [tuned["STATUS_BY_COUNT"][str(m)]["world_id"] for m in range(4)] == ["C3", "C3", "C3", None]
    # with the decoy removed, the partner is the only same-degree other-domain candidate
    out, _ = Hm.analogy_payloads(bank_public([w for w in worlds if w["world_id"] != "C3"]), "F", set(), key)
    assert out["OTHER_DOMAIN_ONLY"] == {"world_id": "D4"} and out["FLAG_ANCHOR"] == {"world_id": None}
    # a partner whose two (1,1) nodes are numbered the other way round: its ONE degree-sorted guess breaks an edge, so
    # the guess rules answer NO_MATCH although an isomorphic partner is there (they may not search)
    swapped = [(0, 3), (0, 2), (3, 1), (1, 4)]                              # S5A with nodes 1 and 3 swapped
    assert oracle.canonical_form(5, swapped) == oracle.canonical_form(5, S5A)
    bank = [worlds[0], worlds[3], named("E5", 5, swapped, "container", participants=[0, 3, 1])]
    out, _ = Hm.analogy_payloads(bank_public(bank), "F", set(), key)
    assert out["DEGREE_GUESS_THEN_CHECK"] == out["WHOLE_ANCHOR_GUESS_THEN_CHECK"] == {"world_id": None}
    assert out["FLAG_ANCHOR_GUESS_THEN_CHECK"] == {"world_id": "E5"}      # F's participants 0, 1, 3 land on 0, 3, 1
    # a trained shape (4 nodes or fewer) is not novel
    small =[named("F", 4, [(0, 1), (1, 2), (2, 3)], "mechanical"), named("E", 4, [(0, 1), (1, 2), (2, 3)], "container")]
    out, _ = Hm.analogy_payloads(bank_public(small), "F", {key((4, [(0, 1), (1, 2), (2, 3)]))}, key)
    assert out["CANDIDATE_ONLY_NOVELTY"] == {"world_id": None}


# ============================================================================ clusters, floor, statistics (s5, s7)
def test_cluster_counting_and_tuned_choice():
    Hm = H()
    rows = {}
    clusters = []
    for f in range(3):
        items = ["c%d|%s|pres%d" % (f, st, k) for st in ("MATCH", "NO_MATCH") for k in (0, 1)]
        for i in items:
            rows[i] = {"comparators": {x: True for x in Hm.ANALOGY_COMPARATORS if x not in Hm.ANALOGY_TUNED},
                       "tuned": {"BEST_FIXED_POSITION": {"0": True, "1": f == 0}, "STATUS_BY_COUNT": {"0": False, "1": True}}}
        clusters.append({"items": items, "shape_key": "s%d" % f, "group_key": "g%d" % f})
    rows["c1|NO_MATCH|pres1"]["comparators"]["FLAG_ANCHOR"] = False          # one presentation wrong: cluster wrong
    rows["c2|NO_MATCH|pres0"]["tuned"]["BEST_FIXED_POSITION"]["0"] = False
    chosen = Hm.cluster_results(clusters, rows, Hm.ANALOGY_COMPARATORS, Hm.ANALOGY_TUNED)
    assert [c["comparators"]["FLAG_ANCHOR"] for c in clusters] == [True, False, True]
    assert chosen == {"BEST_FIXED_POSITION": "0", "STATUS_BY_COUNT": "1"}   # best on the cell; ties to the first
    assert [c["comparators"]["BEST_FIXED_POSITION"] for c in clusters] == [True, True, False]
    block = Hm.floor_block(A, clusters, Hm.ANALOGY_COMPARATORS, need_groups=True)
    assert block["W_by_comparator"]["FLAG_ANCHOR"] == 1 and block["binding_W"] == 0
    assert block["distinct_shapes_behind_binding_W"] == 0 and block["distinct_degree_groups"] == 3


def test_floor():
    Hm = H()

    def members(n, wrong, groups):
        return [{"comparators": {"X": i >= wrong, "Y": False}, "shape_key": "s%d" % i, "group_key": "g%d" % (i % groups)}
                for i in range(n)]
    assert Hm.floor_block(A, members(40, 12, 12), ("X", "Y"), need_groups=True)["can_carry_a_claim"] is True
    assert Hm.floor_block(A, members(9, 9, 9), ("X",))["can_carry_a_claim"] is False                  # clusters < 10
    b = Hm.floor_block(A, members(40, 9, 12), ("X", "Y"), need_groups=True)
    assert b["can_carry_a_claim"] is False and b["binding_comparator"] == "X" and b["binding_W"] == 9  # W < 10
    b = Hm.floor_block(A, members(40, 12, 9), ("X",), need_groups=True)
    assert b["can_carry_a_claim"] is False and "degree groups 9" in b["why_not"]                        # groups < 10
    assert Hm.floor_block(A, members(40, 12, 9), ("X",))["can_carry_a_claim"] is True                  # not analogy
    assert Hm.smallest_detectable_regression(A) == 7
    p = Hm.power_grid(A, 12, 40)
    assert p["never_loses_where_bar_is_right_wins_fraction"]["1.00"] == 1.0


# ============================================================================ worlds: fresh flags, twins (s4, s5.2)
@needs_root
def test_fresh_flags_kind_words_and_presentations():
    Hm = H()
    from cas_meta2.typed_teaching import source
    vocab, _ = hw.vocabulary(source)
    shape = S0.key_shape("[6,[[0,1],[0,2],[1,3],[2,3],[3,4],[4,5]]]")
    aut = hw.automorphisms(6, list(shape[1]))
    rng = random.Random("fresh-flags-test")
    on_image = 0
    for trial in range(200):
        (fa, fb), ff = Hm.world_pair(hw, vocab, rng, shape, "mechanical")
        (pa, pb), pf = Hm.world_pair(hw, vocab, rng, shape, "container")
        for spec, flags, dom in ((fa, ff, "mechanical"), (pa, pf, "container")):
            assert flags["whole"] in hw.roots(6, list(shape[1]))
            assert len({flags["whole"], flags["p2"], flags["p3"]}) == 3
            assert spec["declarations"]["kind"] in vocab[dom]["kinds"]
            assert set(spec["labels"]) <= set(vocab[dom]["declaration_labels"])
        assert sorted(fa["labels"]) == sorted(fb["labels"]) and fa["labels"] != fb["labels"]
        assert hw.world_from_spec(source, fa)["world_id"] != hw.world_from_spec(source, fb)["world_id"]
        on_image += Hm.flags_on_image(aut, ff, pf)["all_three"]
    assert on_image / 200 < 0.5          # a copied flag set would be on an image every time (review M2)


@needs_root
def test_twin_banks_profile_equality():
    Hm = H()
    from cas_meta2.typed_teaching import source
    vocab, _ = hw.vocabulary(source)
    sides = json.loads((HERE / S0.DEV_GROUPS_FILE).read_text(encoding="utf-8"))
    group_of = {k: row["group_key"] for row in sides["groups"] for k in row["classes"]}
    members = {row["group_key"]: row["classes"] for row in sides["groups"]}
    big = [row["group_key"] for row in sides["groups"] if len(row["classes"]) >= 5][:3]
    foci = [members[g][0] for g in big]
    pool = sorted(group_of)
    ctx = {"hw": hw, "vocab": vocab, "source": source, "S0": S0,
           "aut": lambda k: hw.automorphisms(S0.key_shape(k)[0], list(S0.key_shape(k)[1]))}
    items, clusters = Hm.analogy_items(ctx, "UNIT", "ANALOGY", "unit-test-public-seed", foci,
                                       lambda k: [c for c in members[group_of[k]] if c != k],
                                       lambda k: [c for c in pool if group_of[c] != group_of[k]], {foci[0]})
    assert len(items) == 3 * 2 * 2 and len(clusters) == 3
    for c in clusters:
        assert c["profiles"]["MATCH"] == c["profiles"]["NO_MATCH"]
        assert c["same_degree_other_domain_non_isomorphic_decoys"] == {"MATCH": 3, "NO_MATCH": 4}
        by = {(i["status"], i["presentation"]): i for i in items if i["cluster_id"] == c["cluster_id"]}
        m, nm = by[("MATCH", 0)], by[("NO_MATCH", 0)]
        assert len(m["worlds"]) == len(nm["worlds"]) == 8 and m["classes"][0] == m["classes"][1] == c["shape_key"]
        assert [x for i, x in enumerate(m["classes"]) if i != 1] == [x for i, x in enumerate(nm["classes"]) if i != 1]
        assert m["domains"][2:] == nm["domains"][2:] and nm["roles"][1] == "DECOY" and m["roles"][1] == "PARTNER"
        assert ("DISTRACTOR" in m["roles"]) == c["with_distractor"] == ("DISTRACTOR" in nm["roles"])
    # a tampered twin (one filler swapped for a same-degree world) no longer has the same profile
    rows = [("FOCUS", foci[0], "mechanical"), ("DECOY", members[big[0]][1], "container"),
            ("FILLER", next(c for c in pool if group_of[c] != big[0]), "grammatical")]
    tampered = rows[:2] + [("FILLER", members[big[0]][2], "grammatical")]
    assert Hm.bank_profile(S0, rows) != Hm.bank_profile(S0, tampered)


def test_trained_answer_states_pinned_record():
    Hm = H()
    out = Hm.trained_answer_states()
    assert out["analogy"] == {"MATCH": 70} and out["correspondence"] == {"MAPPING": 88}     # NO_MATCH never trained
    assert {k: out[k] for k in ("REACH_FIRST_DIRECT", "REACH_BFS")} == A.TRAINED_REACH_STATES
    assert "not re-measured" in out["source"]


@needs_root
@pytest.mark.slow
def test_trained_answer_states_remeasured():
    """Review F10: the re-measurement the sealed build runs (158 frozen-checker targets) also runs here and in the AWS
    smoke, so the paid build runs no code path for the first time. It reads only the public course."""
    Hm = H()
    from cas_meta2.typed_teaching import pointer_contract
    frozen = pointer_contract.load_material(pathlib.Path(ROOT))[0]
    out = Hm.trained_answer_states(frozen)
    assert out["analogy"] == {"MATCH": 70} and out["correspondence"] == {"MAPPING": 88}
    assert "re-measured and equal" in out["source"]


# ============================================================================ refusals
def pin_or_none(value):
    """A pin the coordinator commits before launch: None until then, 64 lowercase hex after (review F7)."""
    return value is None or (isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value))


def test_real_mode_refusals(tmp_path, monkeypatch):
    """Passes whether or not the coordinator has committed HSET2_SALT_SHA256 (review F7). No real salt is read."""
    Hm = H()
    base = ["--package-root", ROOT or ".", "--out-public", str(tmp_path / "p"), "--out-sealed", str(tmp_path / "s")]
    salt_file = tmp_path / "throwaway_salt.hex"                                 # 64 hex characters; never a real salt
    salt_file.write_text(throwaway_salt("refusal-test", "salt-file") + "\n", encoding="ascii")
    real = ["--salt-file-hset1a", str(salt_file), "--salt-file-hset2", str(salt_file), "--expect-test5-shapes-digest", "0" * 64]
    if Hm.HSET2_SALT_SHA256 is None:
        with pytest.raises(SystemExit, match="REFUSED: HSET2_SALT_SHA256 is not committed yet"):
            Hm.main(base + real)
    # the refusals that follow a committed pin, exercised here with a THROWAWAY pin in place of the real one
    monkeypatch.setattr(Hm, "HSET2_SALT_SHA256", hashlib.sha256(b"throwaway pin for the refusal test").hexdigest())
    with pytest.raises(SystemExit, match="^REFUSED: the HSET-1A salt is not the one whose sha256 was committed$"):
        Hm.main(base + real)
    with pytest.raises(SystemExit, match=r"^REFUSED: the HSET-1A salt file cannot be read \(FileNotFoundError\)$"):
        Hm.main(base + ["--salt-file-hset1a", str(tmp_path / "missing.hex")] + real[2:])
    with pytest.raises(SystemExit, match="^REFUSED: --expect-test5-shapes-digest must be 64 lowercase hex characters$"):
        Hm.main(base + real[:4] + ["--expect-test5-shapes-digest", "z"])
    with pytest.raises(SystemExit, match="^REFUSED: real mode needs both salt files"):
        Hm.main(base + real[:2])
    monkeypatch.undo()
    with pytest.raises(SystemExit, match="REFUSED"):
        Hm.main(base + ["--throwaway-seed", "t", "--salt-file-hset1a", "x"])
    with pytest.raises(SystemExit, match="REFUSED"):
        Hm.main(["--package-root", ".", "--out-public", str(tmp_path / "p"), "--out-sealed", str(HERE / "sealed_should_not_exist"),
                 "--throwaway-seed", "t"])
    with pytest.raises(SystemExit, match="REFUSED: throwaway outputs may not be written inside a git work tree"):
        Hm.main(["--package-root", ".", "--out-public", str(HERE / "throwaway_should_not_exist"), "--out-sealed",
                 str(tmp_path / "s"), "--throwaway-seed", "t"])
    assert not (HERE / "sealed_should_not_exist").exists() and not (HERE / "throwaway_should_not_exist").exists()
    assert pin_or_none(Hm.HSET2_SALT_SHA256) and Hm.HSET1A_SALT_SHA256.startswith("33f9d350")


def test_sealed_mode_hides_uncaught_exception_text(tmp_path, monkeypatch):
    """Review F6/F8: in real mode an uncaught exception's message reaches only the sealed folder; the public side gets
    its type. (No salt is read: the run is replaced by one that raises.)"""
    Hm = H()
    secret = "[6,[[0,1],[0,2]]]-A-TEST-CLASS-KEY"

    def boom(args):
        raise KeyError(secret)
    monkeypatch.setattr(Hm, "_run", boom)
    with pytest.raises(SystemExit) as caught:
        Hm.main(["--package-root", ".", "--out-public", str(tmp_path / "p"), "--out-sealed", str(tmp_path / "s")])
    message = str(caught.value)
    assert message.startswith("BUILD_FAILED_UNCAUGHT: KeyError") and secret not in message
    assert "written to the sealed output only" in message
    assert secret in (tmp_path / "s" / "build_traceback.txt").read_text(encoding="utf-8")
    assert not (tmp_path / "p").exists()
    # the build's own refusals pass through unchanged
    monkeypatch.setattr(Hm, "_run", lambda args: (_ for _ in ()).throw(SystemExit("REFUSED: a fixed code")))
    with pytest.raises(SystemExit, match="^REFUSED: a fixed code$"):
        Hm.main(["--package-root", ".", "--out-public", str(tmp_path / "p"), "--out-sealed", str(tmp_path / "s2")])
    # throwaway mode is not wrapped (nothing in it is secret; a full traceback helps debugging)
    monkeypatch.setattr(Hm, "_run", boom)
    with pytest.raises(KeyError):
        Hm.main(["--package-root", ".", "--out-public", str(tmp_path / "p"), "--out-sealed", str(tmp_path / "s3"),
                 "--throwaway-seed", "t"])


def test_launcher_limits_and_pins():
    sys.path.insert(0, str(HERE.parent / "hset2_aws_job"))
    import launch
    assert launch.worst_case_usd() < launch.DOLLAR_CEILING == 1.00
    pins = launch.builder_pins((HERE / "hset2_build.py").read_bytes())
    assert pins == {"HSET1A_SALT_SHA256": H().HSET1A_SALT_SHA256, "HSET2_SALT_SHA256": H().HSET2_SALT_SHA256,
                    "SOURCE_COMMIT": launch.SOURCE_COMMIT}
    for value in (pins["HSET2_SALT_SHA256"], launch.EXPECTED_TEST5_SHAPES_DIGEST, launch.UV_TARBALL_SHA256):
        assert pin_or_none(value)                                  # None until the coordinator commits it (review F7)
    assert launch.PYTHON_VERSION.count(".") == 2 and launch.UV_VERSION.count(".") == 2   # exact versions (review F9)
    for name in launch.CLAUDE_FILES + launch.JOB_FILES:
        assert (HERE.parents[2] / name).is_file(), name
    template = (HERE.parent / "hset2_aws_job" / "job.sh.template").read_text(encoding="utf-8")
    for key in ("__MAX_SECONDS__", "__MAX_MINUTES__", "__BUNDLE_URL__", "__RESULTS_URL__", "__SEALED_URL__", "__PROGRESS_URL__",
                "__BUNDLE_SHA256__", "__SOURCE_COMMIT__", "__EXPECT_TEST5__", "__PYTHON_VERSION__", "__UV_VERSION__",
                "__UV_SHA256__"):
        assert key in template
        template = template.replace(key, "X")
    assert "__" not in template.replace("__pycache__", "")
    assert "--throwaway-seed tiny-9 --limit-foci 2" in template and "hset2_stage0_public.py --check" in template
    assert "--remeasure-trained-states" in template                  # the smoke runs the re-measurement (review F10)
    # third-party tools are installed and checked BEFORE the bundle (and its salts) reaches the disk (review F9)
    assert template.index("uv python install") < template.index("bundle.tar.gz")
    assert "sha256sum -c" in template[:template.index("bundle.tar.gz")]
    assert "rm -rf \"$WORK/pkg/sealed\"" in template


# ============================================================================ tiny end to end, and public-output custody
@pytest.fixture(scope="module")
def tiny_build(tmp_path_factory):
    out = tmp_path_factory.mktemp("hset2_e2e")
    code = H().main(["--package-root", ROOT, "--throwaway-seed", NON_BREACHING_SEED, "--limit-foci", "1",
                     "--processes", "1", "--out-public", str(out / "public"), "--out-sealed", str(out / "sealed_throwaway")])
    return code, out


@needs_root
@pytest.mark.e2e
def test_tiny_end_to_end(tiny_build):
    code, out = tiny_build
    assert code == 0
    assert sorted(p.name for p in (out / "public").iterdir()) == ["THROWAWAY_HSET2_BUILD_SUMMARY.json",
                                                                  "THROWAWAY_HSET2_CELLS_NOT_DEV.json"]     # review F11
    summary = json.loads((out / "public" / "THROWAWAY_HSET2_BUILD_SUMMARY.json").read_text(encoding="utf-8"))
    assert summary["build_ok"] is True and summary["mode"] == "THROWAWAY_SALTS_NOT_A_BUILD"
    assert summary["throwaway_warning"].startswith("THROWAWAY_NOT_DEV")
    assert {s["claim_role"] for s in summary["cells"].values()} == {"THROWAWAY_NOT_DEV"}
    assert not any(v for k, v in summary["problems"].items() if k != "errors")
    kinds = summary["counts"]["items_by_kind"]
    assert set(kinds) == {"reach", "parts", "edge_account", "analogy", "correspondence"}
    for cell in ("TEST_NEW_6/ANALOGY", "TEST_NEW_6/CORRESPONDENCE", "TEST_NEW_5/CORRESPONDENCE", "TEST_NEW_6/REACH_BFS"):
        assert cell in summary["cells"]
    assert summary["claims_before_any_model"]["ANALOGY_BEYOND_DEGREE_5"]["status_if_not"] == "NOT_TESTABLE"
    assert summary["no_regression_gates"]["smallest_detectable_regression_c_prime_with_b_prime_0"] == 7
    # every A2 bar is registered, printed and scored in its cells
    reg = summary["identity"]["registered_comparators"]
    assert reg == H().registered_comparators() and summary["identity"]["registered_comparators_digest"] == hw.sha(reg)
    assert set(summary["cells"]["TEST_NEW_6/ANALOGY"]["W_by_comparator"]) == set(H().ANALOGY_COMPARATORS)
    assert set(summary["cells"]["TEST_NEW_6/CORRESPONDENCE"]["W_by_comparator"]) == set(H().CORRESPONDENCE_COMPARATORS)
    for claim in ("REACH_3_STEP_TRANSFER_6", "REACH_4_STEP_TRANSFER_6"):
        assert set(summary["cells"]["TEST_NEW_6/REACH_BFS"]["claims"][claim]["W_by_comparator"]) == set(reg["reach"][claim])
    # the printed disjointness is counted, and every required count is 0 (review F5)
    d = summary["splits"]["disjointness"]
    assert d["how"].startswith("counted") and all(v == 0 for k, v in {**d["five"], **d["six"]}.items()
                                                  if not k.endswith("printed_only_dev_is_public"))
    sealed = json.loads((out / "sealed_throwaway" / "THROWAWAY_HSET2_SEALED_TEST.json").read_text(encoding="utf-8"))
    for item in sealed["items"]:
        assert item["evaluation"]["reader_ok"] and item["evaluation"]["route"] == "LARGER_PATH"
        assert item["evaluation"]["independent_gold_agrees"] and item["evaluation"]["comparator_scoring_consistent"]


@needs_root
@pytest.mark.e2e
def test_public_outputs_hold_no_test_id_or_shape(tiny_build):
    _, out = tiny_build
    sealed = json.loads((out / "sealed_throwaway" / "THROWAWAY_HSET2_SEALED_TEST.json").read_text(encoding="utf-8"))
    secret = set()
    for name in ("TEST_NEW_6", "WITHHELD_6", "TEST_NEW_5", "WITHHELD_5"):
        for key in sealed["splits"][name]:
            secret.add(json.dumps(key))                     # the class key, as it would be written in JSON
            secret.add(hw.sha(key)[:16])                    # the hashed shape id used inside cluster ids
    for item in sealed["items"]:
        e = item["evaluation"]
        secret.update({e["record_id"], e["query_id"], e["source_digest"], e["packet_sha256"], item["cluster_id"],
                       item["item_id"]})
        secret.update(e.get("world_ids", []))
    public_bytes = b"".join(p.read_bytes() for p in sorted((out / "public").iterdir()))
    leaks = [s for s in secret if s.encode("utf-8") in public_bytes]
    assert not leaks, leaks[:3]
    public = json.loads((out / "public" / "THROWAWAY_HSET2_CELLS_NOT_DEV.json").read_text(encoding="utf-8"))
    dev_side = {k for row in json.loads((HERE / S0.DEV_GROUPS_FILE).read_text(encoding="utf-8"))["groups"] for k in row["classes"]}
    dev5 = set(public["splits"]["DEV_NEW_5"])
    for item in public["items"]:
        assert item["split"] in ("DEV_NEW_6", "DEV_NEW_5")
        for cls in item.get("classes", []):
            assert cls in (dev_side if item["split"] == "DEV_NEW_6" else dev5)
