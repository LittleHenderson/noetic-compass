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
import math
import os
import pathlib
import random
import re
import subprocess
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


def launcher():
    """The AWS job's launcher module (imported, never run against AWS here)."""
    job = str(HERE.parent / "hset2_aws_job")
    if job not in sys.path:
        sys.path.insert(0, job)
    import launch
    return launch


def codex_design_text():
    """EVALUATION_DESIGN_v0_4.md at Codex's c3a128ee (A2.7), from git objects; None if the object is not here."""
    rel = ("cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_eval_design_20260923/"
           "EVALUATION_DESIGN_v0_4.md")
    run = subprocess.run(["git", "-C", str(HERE), "show", "%s:%s" % (H().DESIGN_SOURCE_COMMIT, rel)], capture_output=True)
    return run.stdout if run.returncode == 0 else None


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
    # PUBLIC_EXCLUDED version 2 (T5, default Q-B): 3 + 24 six-node classes in the universe are removed
    assert summary["six_node_universe"]["classes_after_public_excluded"] == 5047
    assert summary["public_excluded"]["file"] == "PUBLIC_EXCLUDED_v2.json" == S0.PUBLIC_EXCLUDED_FILE
    assert (sides["DEV"]["group_count"], sides["DEV"]["class_count"]) == (503, 1324)
    assert (sides["TEST"]["group_count"], sides["TEST"]["class_count"]) == (1429, 3723)
    # the DEV side, DEV_NEW_6 and DEV_DECOYS_6 are exactly those of version 1 (digests of the first commit)
    assert sides["DEV"]["groups_digest"] == "29349b328b8150719c9f5cc03f65fae43602cc9476e9362c6e388028c84d35de"
    assert summary["dev_new_6"]["digest"] == "e1c046a464e794873ccfd7d64344cdc418a5bd4121d6deefa49261ed96cdf682"
    assert summary["dev_decoys_6"]["digest"] == "7d3b68e489b7e97ddd2e109b27a9f4960579356d4a7e5e93a73e3d2c1cb8ce85"
    # every committed file, the history file PUBLIC_EXCLUDED_v1.json included, is among the recomputed ones
    assert set(files) == {S0.PUBLIC_EXCLUDED_V1_FILE, S0.PUBLIC_EXCLUDED_FILE, S0.DEV_GROUPS_FILE, S0.TEST_GROUPS_FILE,
                          S0.SUMMARY_FILE}
    assert set(summary["files_sha256"]) == set(files) - {S0.SUMMARY_FILE}
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
    """Version 1 is kept as history, byte for byte (its sha256 is the one of the first commit, 853e645d)."""
    raw = (HERE / S0.PUBLIC_EXCLUDED_V1_FILE).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == "f101cbdd2984e5bcd21389f8ed76ef4550bc3817735c65f0acb8c8afc6d23b98"
    pe = json.loads(raw.decode("utf-8"))
    assert pe["counts_by_nodes"] == {"5": 3, "6": 4}
    names = sorted(n for r in pe["classes"] for n in r["fixture_shape_names"])
    assert names == ["S5A", "S5B", "S5C", "S6A", "S6B", "S6D", "S6STAR"]
    for r in pe["classes"]:
        assert r["digest"] == hashlib.sha256(r["canonical_form"].encode("utf-8")).hexdigest()
        n, edges = S0.key_shape(r["canonical_form"])
        assert oracle.canonical_form(n, edges) == (n, edges)
        assert r["inside_degree_4_universe"] == (r["fixture_shape_names"] != ["S6STAR"])
    assert pe["version_1_input"]["sha256"] == S0.FIXTURE_SHA256


def test_public_excluded_version_2():
    """T5 (Claude's default Q-B): version 2 = version 1 + exactly the 24 TEST-side classes of the 40 public HSET-1B
    DEV_NEW_6 classes, all 6-node; nothing at 5 nodes changes, so TEST_NEW_5 and its pinned public digest cannot."""
    v1 = json.loads((HERE / S0.PUBLIC_EXCLUDED_V1_FILE).read_text(encoding="utf-8"))
    v2 = json.loads((HERE / S0.PUBLIC_EXCLUDED_FILE).read_text(encoding="utf-8"))
    assert S0.PUBLIC_EXCLUDED_FILE == "PUBLIC_EXCLUDED_v2.json" and v2["version"] == 2
    assert v2["counts_by_nodes"] == {"5": 3, "6": 28}
    extra = ("added_in_version", "hset1b_dev_new_6_draw_order", "hset2_stage0_side")
    old = [{k: v for k, v in r.items() if k not in extra} for r in v2["classes"] if r["added_in_version"] == 1]
    new = [r for r in v2["classes"] if r["added_in_version"] == 2]
    assert sorted(old, key=lambda r: r["digest"]) == sorted(v1["classes"], key=lambda r: r["digest"])
    assert len(new) == 24
    t5 = json.loads((HERE / "PROPOSED_T5_OLDER_PUBLIC_TEST_SIDE.json").read_text(encoding="utf-8"))
    assert {r["digest"] for r in new} == {r["class_digest"] for r in t5["rows"] if r["hset2_side"] == "TEST"}
    drawn = S0.hset1b_dev_new_6_keys()                                     # recomputed from the public seed
    assert len(drawn) == len(set(drawn)) == 40
    for r in new:
        assert drawn[r["hset1b_dev_new_6_draw_order"]] == r["canonical_form"]
        assert r["nodes"] == 6 and r["inside_degree_4_universe"] and r["hset2_stage0_side"] == "TEST"
        assert S0.side_of_group(r["degree_multiset_group_key"]) == "TEST"
        assert r["digest"] == hashlib.sha256(r["canonical_form"].encode("utf-8")).hexdigest()
        n, edges = S0.key_shape(r["canonical_form"])
        assert oracle.canonical_form(n, edges) == (n, edges)
    # the 16 others sit on the DEV side and are not added
    assert sum(1 for k in drawn if S0.side_of_group(S0.group_key(S0.key_shape(k))) == "DEV") == 16
    five = lambda doc: {r["canonical_form"] for r in doc["classes"] if r["nodes"] == 5}      # noqa: E731
    assert five(v2) == five(v1)
    assert v2["class_digests_digest"] == S0.list_digest(sorted(r["digest"] for r in v2["classes"]))
    assert v2["version_1_history"]["class_digests_digest"] == v1["class_digests_digest"]


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
        "THREE_HOP_FIRST_CHILD", "SINGLE_ROOT_FALLBACK", "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP", "FRONTIER_FALLBACK")


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


def test_frontier_fallback_rules():
    """Finding V-1: two-hop, then VIA when a node exactly 2 steps out has a child and the part has a parent. It never
    checks where the third step goes. Under the default D1 value "a" it is a bar of both reach claims (the other D1
    values: test_d1_switch_records_every_option)."""
    Hm = H()
    first, bfs = "first_direct_constituent_lexical_v1", "bfs_immediate_predecessor_lexical_v1"
    q = lambda part, rule: {"arguments": {"whole": "w/n0", "part": "w/n%d" % part}, "rule": rule}   # noqa: E731

    def run(world, part, rule):
        base, _ = A._comparators("reach", world, q(part, rule))
        return Hm.extra_reach_payloads(world, q(part, rule), base)
    via = lambda k: {"state": "VIA", "via": "w/n%d" % k}                                          # noqa: E731
    absent = {"state": "ABSENT", "via": None}
    # 1. two roots (n0, n4); the part n3 is 3 steps from the whole. SINGLE_ROOT_FALLBACK says ABSENT; the frontier
    # rule says VIA, and both of its vias equal the gold (first-child: n1; BFS: n2, the part's parent that has a parent)
    edges = [(0, 1), (1, 2), (2, 3), (4, 3), (4, 5)]
    world = plain_world(6, edges)
    rank = {i: i for i in range(6)}
    assert hw.reach_gold(6, edges, 0, 3, rank, hw.REACH_FIRST) == ("VIA", 1)
    assert hw.reach_gold(6, edges, 0, 3, rank, hw.REACH_BFS) == ("VIA", 2)
    assert run(world, 3, first)["SINGLE_ROOT_FALLBACK"] == absent
    assert run(world, 3, first)["FRONTIER_FALLBACK"] == via(1)
    assert run(world, 3, bfs)["FRONTIER_FALLBACK"] == via(2)
    # 2. no path at all (the part's only parent n4 is a root), but the frontier has a child: the first-child form
    # answers VIA wrongly; the BFS form finds no parent with a parent and keeps ABSENT
    edges = [(0, 1), (1, 2), (2, 5), (4, 3), (4, 5)]
    world = plain_world(6, edges)
    assert hw.reach_gold(6, edges, 0, 3, rank, hw.REACH_FIRST) == ("ABSENT", None)
    assert run(world, 3, first)["FRONTIER_FALLBACK"] == via(1)
    assert run(world, 3, bfs)["FRONTIER_FALLBACK"] == absent
    # 3. the first-child via is the whole's child with the MOST children (ties: lowest rank)
    edges = [(0, 1), (0, 2), (2, 3), (2, 4), (3, 5), (1, 4)]
    world = plain_world(6, edges)
    assert A._comparators("reach", world, q(5, first))[0]["TWO_HOP_FIRST_CHILD"] == absent
    assert run(world, 5, first)["FRONTIER_FALLBACK"] == via(2)                    # n2 has 2 children, n1 has 1
    # 4. the two-hop answer comes first; a frontier with no child keeps ABSENT
    chain = plain_world(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
    assert run(chain, 2, first)["FRONTIER_FALLBACK"] == via(1)
    assert run(chain, 1, bfs)["FRONTIER_FALLBACK"] == {"state": "DIRECT", "via": None}
    short = plain_world(6, [(0, 1), (1, 2), (3, 4), (4, 5), (3, 1)])
    assert run(short, 5, first)["FRONTIER_FALLBACK"] == absent                  # n2, 2 steps out, has no child
    # 5. the default D1 value "a": registered in both claims
    reg = Hm.registered_comparators()
    assert Hm.D1_FRONTIER_DECISION == "a" and reg["design_owner_switches"]["D1_FRONTIER_DECISION"] == "a"
    assert all("FRONTIER_FALLBACK" in reg["reach"][c] for c in ("REACH_3_STEP_TRANSFER_6", "REACH_4_STEP_TRANSFER_6"))


def test_d1_switch_records_every_option(tmp_path, monkeypatch):
    """Review of 4c402209, finding 2: D1 is one recorded constant with one value per option. Every value except "a"
    changes the 3-step claim's status or name; FRONTIER_FALLBACK stays a bar of the 4-step claim under every value;
    option c and unknown values are refused before any salt is read; each value has its own bar-set digest."""
    Hm = H()
    three_hop = {"THREE_HOP_FIRST_CHILD", "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"}
    digests = {}
    for value in ("a", "b_not_testable", "b_rename"):
        monkeypatch.setattr(Hm, "D1_FRONTIER_DECISION", value)
        Hm.check_d1()
        reg = Hm.registered_comparators()
        digests[value] = hw.sha(reg)
        three, four = Hm.reach_claim_names()
        assert set(reg["reach"]) == {three, four} and four == "REACH_4_STEP_TRANSFER_6"
        assert "FRONTIER_FALLBACK" in reg["reach"][four]
        assert set(reg["reach"][four]) - set(reg["reach"][three]) >= three_hop
        assert set(reg["reach"][three]) <= set(reg["reach"][four])
        assert reg["design_owner_switches"]["D1_FRONTIER_DECISION"] == value
        assert reg["design_owner_switches"]["D1_meaning"] == Hm.D1_OPTIONS[value]
        if value == "a":
            assert three == "REACH_3_STEP_TRANSFER_6" and "FRONTIER_FALLBACK" in reg["reach"][three]
            assert reg["declared_not_testable_by_D1"] == []
            assert reg["computed_not_registered_printed_only"]["reach"] == {three: [], four: []}
        if value == "b_not_testable":                       # the name stays; the claim is declared NOT_TESTABLE
            assert three == "REACH_3_STEP_TRANSFER_6" and "FRONTIER_FALLBACK" in reg["reach"][three]
            assert reg["declared_not_testable_by_D1"] == ["REACH_3_STEP_TRANSFER_6"]
        if value == "b_rename":                             # a new name; FRONTIER printed for it, not a bar of it
            assert three == "REACH_BEYOND_TWO_HOP_AND_ROOT_COUNT_6" and "REACH_3_STEP_TRANSFER_6" not in reg["reach"]
            assert "FRONTIER_FALLBACK" not in reg["reach"][three]
            assert reg["computed_not_registered_printed_only"]["reach"] == {three: ["FRONTIER_FALLBACK"], four: []}
            assert "does NOT show 3-step path following" in Hm.REACH_3_STEP_RENAMED_SCOPE
    assert len(set(digests.values())) == 3
    for value, pattern in (("c", "^REFUSED: D1 option c"), ("b", "^REFUSED: D1_FRONTIER_DECISION must be one of")):
        monkeypatch.setattr(Hm, "D1_FRONTIER_DECISION", value)
        with pytest.raises(SystemExit, match=pattern):
            Hm.check_d1()
        with pytest.raises(SystemExit, match=pattern):         # the build refuses before it reads anything
            Hm.main(["--package-root", ".", "--out-public", str(tmp_path / "p"), "--out-sealed", str(tmp_path / "s"),
                     "--throwaway-seed", "t"])
    assert not (tmp_path / "p").exists()


@needs_root
def test_d1_options_in_the_reach_cell_summary(monkeypatch):
    """The D1 values as the reach cell summary prints them, on a tiny throwaway build (public strings only)."""
    Hm = H()
    import copy
    import hset2_throwaway_ranges as R
    from cas_meta2.typed_teaching import source
    Hm._init(ROOT)
    vocab, _ = hw.vocabulary(source)
    stage0 = Hm.load_stage0(pathlib.Path(ROOT))
    salt1a, salt2 = throwaway_salt(NON_BREACHING_SEED, "hset1a"), throwaway_salt(NON_BREACHING_SEED, "hset2")
    D = Hm.derive(stage0, salt1a, salt2, vocab, source, limit_foci=2, only="reach")
    items = [i for i in D["items"] if i["split"] == "TEST_NEW_6"]
    rows = R.fast_rows(Hm, items)
    by_cluster = {}
    for item in items:
        by_cluster.setdefault(item["cluster_id"], []).append(item)
    members = [c for c in D["single_clusters"] if c["split"] == "TEST_NEW_6" and c["cell"] == "REACH_BFS"]
    assert members
    out = {}
    for value in ("a", "b_not_testable", "b_rename"):
        monkeypatch.setattr(Hm, "D1_FRONTIER_DECISION", value)
        out[value] = Hm.summarise_reach_cell(hw, A, "REACH_BFS", copy.deepcopy(members), rows, by_cluster, salt2, "-")
    a, bnt, bre = out["a"]["claims"], out["b_not_testable"]["claims"], out["b_rename"]["claims"]
    assert set(a) == set(bnt) == {"REACH_3_STEP_TRANSFER_6", "REACH_4_STEP_TRANSFER_6"}
    assert "FRONTIER_FALLBACK" in a["REACH_3_STEP_TRANSFER_6"]["W_by_comparator"]
    assert "computed_not_registered_W" not in a["REACH_3_STEP_TRANSFER_6"]
    # b_not_testable: NOT_TESTABLE whatever the floor says; the floor is still printed
    block = bnt["REACH_3_STEP_TRANSFER_6"]
    assert block["can_carry_a_claim"] is False and out["b_not_testable"]["can_carry_a_claim"] is False
    assert block["why_not"].startswith("declared NOT_TESTABLE before any build (D1 option b_not_testable")
    assert block["floor_result_before_the_D1_declaration"]["can_carry_a_claim"] == a["REACH_3_STEP_TRANSFER_6"]["can_carry_a_claim"]
    assert block["W_by_comparator"] == a["REACH_3_STEP_TRANSFER_6"]["W_by_comparator"]
    # b_rename: the new name, FRONTIER printed as a diagnostic in every view, the scope note attached
    assert set(bre) == {"REACH_BEYOND_TWO_HOP_AND_ROOT_COUNT_6", "REACH_4_STEP_TRANSFER_6"}
    renamed = bre["REACH_BEYOND_TWO_HOP_AND_ROOT_COUNT_6"]
    assert "FRONTIER_FALLBACK" not in renamed["W_by_comparator"]
    assert renamed["computed_not_registered_W"] == {
        "FRONTIER_FALLBACK": a["REACH_3_STEP_TRANSFER_6"]["W_by_comparator"]["FRONTIER_FALLBACK"]}
    assert set(renamed["a2_views"]["computed_not_registered_W_by_view"]) == {"FRONTIER_FALLBACK"}
    assert renamed["scope_note"] == Hm.REACH_3_STEP_RENAMED_SCOPE
    # the 4-step claim is the same under every value, FRONTIER included
    assert (a["REACH_4_STEP_TRANSFER_6"]["W_by_comparator"] == bnt["REACH_4_STEP_TRANSFER_6"]["W_by_comparator"]
            == bre["REACH_4_STEP_TRANSFER_6"]["W_by_comparator"])
    assert "FRONTIER_FALLBACK" in a["REACH_4_STEP_TRANSFER_6"]["W_by_comparator"]


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
    out = Hm.analogy_payloads(bank_public(worlds), "F", set(), key)
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
    # N1: the flags tie-break guess (degree, then declared-flag position, then rank) pairs F and D4 node for node
    assert out["DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK"] == {"world_id": "D4"}
    assert set(out) == set(Hm.analogy_comparators()) | set(Hm.analogy_computed_not_registered())
    # Codex A2.1: every family member is its own comparator. Aliases in numeric order: A1=W0, B2=W1, C3=W2, D4=W3, F=W4
    assert [out["FIXED_POSITION_%d" % j]["world_id"] for j in range(1, 8)] == ["A1", "B2", "C3", "D4", None, None, None]
    assert [out["FIXED_ALIAS_W%d" % k]["world_id"] for k in range(8)] == ["A1", "B2", "C3", "D4", "F", None, None, None]
    # E = [C3, D4] (same degree, other domain); NO_MATCH when len(E) < m; else E[0]
    assert [out["STATUS_BY_COUNT_%d" % m]["world_id"] for m in range(9)] == ["C3", "C3", "C3"] + [None] * 6
    # with the decoy removed, the partner is the only same-degree other-domain candidate
    out = Hm.analogy_payloads(bank_public([w for w in worlds if w["world_id"] != "C3"]), "F", set(), key)
    assert out["OTHER_DOMAIN_ONLY"] == {"world_id": "D4"} and out["FLAG_ANCHOR"] == {"world_id": None}
    assert [out["STATUS_BY_COUNT_%d" % m]["world_id"] for m in range(3)] == ["D4", "D4", None]
    # a partner whose two (1,1) nodes are numbered the other way round: its ONE degree-sorted guess breaks an edge, so
    # the guess rules answer NO_MATCH although an isomorphic partner is there (they may not search)
    swapped = [(0, 3), (0, 2), (3, 1), (1, 4)]                              # S5A with nodes 1 and 3 swapped
    assert oracle.canonical_form(5, swapped) == oracle.canonical_form(5, S5A)
    bank = [worlds[0], worlds[3], named("E5", 5, swapped, "container", participants=[0, 3, 1])]
    out = Hm.analogy_payloads(bank_public(bank), "F", set(), key)
    assert out["DEGREE_GUESS_THEN_CHECK"] == out["WHOLE_ANCHOR_GUESS_THEN_CHECK"] == {"world_id": None}
    assert out["FLAG_ANCHOR_GUESS_THEN_CHECK"] == {"world_id": "E5"}      # F's participants 0, 1, 3 land on 0, 3, 1
    assert out["DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK"] == {"world_id": "E5"}   # the flag positions break the (1,1) tie
    assert not Hm.flags_tiebreak_guess(worlds[0], worlds[3])                # C3: same degrees, other wiring
    # a trained shape (4 nodes or fewer) is not novel
    small =[named("F", 4, [(0, 1), (1, 2), (2, 3)], "mechanical"), named("E", 4, [(0, 1), (1, 2), (2, 3)], "container")]
    out = Hm.analogy_payloads(bank_public(small), "F", {key((4, [(0, 1), (1, 2), (2, 3)]))}, key)
    assert out["CANDIDATE_ONLY_NOVELTY"] == {"world_id": None}


def test_codex_a2_1_families_and_switches(monkeypatch):
    """Codex A2.1: FIXED_POSITION_1..7 and STATUS_BY_COUNT_0..8 are registered bars; the pre-A2 tuned bars survive only
    as their complete untuned tables (no bar dropped) and as a labelled diagnostic; the N1 switch is recorded."""
    Hm = H()
    reg = Hm.registered_comparators()
    bars = reg["analogy"]
    for name in (["FIXED_POSITION_%d" % j for j in range(1, 8)] + ["STATUS_BY_COUNT_%d" % m for m in range(9)]
                 + ["FIXED_ALIAS_W%d" % k for k in range(8)] + ["DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK"]):
        assert bars.count(name) == 1, name
    assert "BEST_FIXED_POSITION" not in bars and "STATUS_BY_COUNT" not in bars
    # every bar of the first version (853e645d) is still a bar, or its whole table is (A2 only adds)
    old = ["ALWAYS_NO_MATCH", "FIRST_CANDIDATE", "NODE_EDGE_COUNT_MATCH", "DEGREE_MULTISET_MATCH", "FLAG_ANCHOR",
           "CANDIDATE_ONLY_NOVELTY", "OTHER_DOMAIN_ONLY", "DEGREE_GUESS_THEN_CHECK", "WHOLE_ANCHOR_GUESS_THEN_CHECK",
           "FLAG_ANCHOR_GUESS_THEN_CHECK"]
    assert set(old) <= set(bars)
    assert reg["pre_A2_tuned_bars_completed_untuned"] == {"BEST_FIXED_POSITION": ["FIXED_ALIAS_W%d" % k for k in range(8)],
                                                          "STATUS_BY_COUNT": ["STATUS_BY_COUNT_%d" % m for m in range(9)]}
    # the digest of the bar set changed from the verified 1520e17c build's
    assert hw.sha(reg) != "1a233f311ac4585149600a7812748aa33ac27253640db22c8931dcfae0f8de17"
    # the N1 switch: off, the rule leaves the bar list, stays computed and printed, and the digest changes
    monkeypatch.setattr(Hm, "REGISTER_FLAGS_TIEBREAK_GUESS", False)
    off = Hm.registered_comparators()
    assert "DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK" not in off["analogy"]
    assert off["computed_not_registered_printed_only"]["analogy"] == ["DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK"]
    assert hw.sha(off) != hw.sha(reg)


def test_flag_key_order_and_tie_rule_pinned_by_toys():
    """Q-C (bus claude-0024) and A2.7 D2: the exact flag-key order and tie convention, pinned by public toy examples
    before the key is made. Every key ascending: in-degree, then out-degree, [child-of-the-declared-whole,] flag
    position (whole 0, second participant 1, third 2, any other node 3), then rank."""
    Hm = H()
    # 1. a star: the root (in 0, out 4) comes before the leaves (in 1, out 0), so in-degree is the first key; among the
    # leaves the flags decide (node 3 is participant 2, node 1 is participant 3), then rank (2 before 4)
    star = named("S", 5, [(0, 1), (0, 2), (0, 3), (0, 4)], "mechanical", participants=[0, 3, 1])
    assert Hm.tiebreak_order(star) == [0, 3, 1, 2, 4]
    # 2. a chain 0 -> 1 -> 2 -> 3 whose (1, 1) tie holds a child of the whole (node 1, no flag) and a non-child (node 2,
    # flag 1): the flags put 2 first; CHILDREN_LAST puts the non-child 2 first; CHILDREN_FIRST puts the child 1 first
    chain = [(0, 1), (1, 2), (2, 3)]
    C = named("C", 4, chain, "mechanical", participants=[0, 2, 3])
    assert Hm.tiebreak_order(C) == [0, 3, 2, 1]
    assert Hm.tiebreak_order(C, "last") == [0, 3, 2, 1]
    assert Hm.tiebreak_order(C, "first") == [0, 3, 1, 2]
    with pytest.raises(ValueError):
        Hm.tiebreak_order(C, "sideways")
    # 3. the direction of the whole-child key changes answers (verifier note VN-1), so both directions are bars (Q-A).
    # F declares a leaf as its whole (so F's (1, 1) tie has no child of the whole and the flags order it); T declares
    # its root. The chain has one automorphism, so a guess passes only if it maps node i to node i.
    T = named("T", 4, chain, "container", participants=[0, 3, 1])
    F_last = named("F", 4, chain, "mechanical", whole=3, participants=[3, 2, 0])      # flags order the tie [2, 1]
    F_first = named("F", 4, chain, "mechanical", whole=3, participants=[3, 1, 0])     # flags order the tie [1, 2]
    assert Hm.flags_tiebreak_guess(F_last, T, "last") and not Hm.flags_tiebreak_guess(F_last, T, "first")
    assert Hm.flags_tiebreak_guess(F_first, T, "first") and not Hm.flags_tiebreak_guess(F_first, T, "last")
    # the same, through the analogy bank rule (one guess per same-degree, other-domain candidate)
    key = lambda shape: S0.class_key(oracle.canonical_form(*shape))   # noqa: E731
    out = Hm.analogy_payloads(bank_public([F_last, T]), "F", set(), key)
    assert out[Hm.WHOLE_CHILD_LAST] == {"world_id": "T"} and out[Hm.WHOLE_CHILD_FIRST] == {"world_id": None}
    out = Hm.analogy_payloads(bank_public([F_first, T]), "F", set(), key)
    assert out[Hm.WHOLE_CHILD_FIRST] == {"world_id": "T"} and out[Hm.WHOLE_CHILD_LAST] == {"world_id": None}
    # T's own flags order its tie [1, 2] (participant 3 is node 1): the plain flags rule passes the second pair only
    assert not Hm.flags_tiebreak_guess(F_last, T) and Hm.flags_tiebreak_guess(F_first, T)
    # the rule text is published with the bar set (and so inside its digest)
    reg = Hm.registered_comparators()
    assert reg["tie_rules_pinned"] == Hm.TIE_RULES
    for name in (Hm.FLAGS_TIEBREAK,) + Hm.WHOLE_CHILD_BARS:
        assert name in Hm.TIE_RULES
    assert "ascending (whole first)" in Hm.TIE_RULES["flag_position"]


def test_bar_set_conforms_to_a2_7(monkeypatch):
    """A2.7 (Codex, c3a128ee) word for word: every bar name it gives is registered under that exact name, in the claims
    it names; plus Claude's default Q-A (R1: both whole-child directions), whose switch is recorded in the digest."""
    Hm = H()
    reg = Hm.registered_comparators()
    three, four = reg["reach"]["REACH_3_STEP_TRANSFER_6"], reg["reach"]["REACH_4_STEP_TRANSFER_6"]
    assert Hm.D1_FRONTIER_DECISION == "a"                                           # D1: option (a)
    for bar in ("FRONTIER_FALLBACK", "SINGLE_ROOT_FALLBACK"):
        assert bar in three and bar in four
    assert set(four) - set(three) == {"THREE_HOP_FIRST_CHILD", "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"}
    d2 = ["DEGREE_GUESS_THEN_CHECK", "WHOLE_ANCHOR_GUESS_THEN_CHECK", "FLAG_ANCHOR_GUESS_THEN_CHECK",
          "DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK"]
    for bar in d2:
        assert reg["analogy"].count(bar) == 1, bar
    assert "WHOLE_ANCHOR_GUESS_THEN_CHECK" in reg["correspondence"]
    assert '"FLAGS_TIEBREAK_GUESS_THEN_CHECK"' not in json.dumps(reg)             # the old name is gone
    assert reg["a2_7_named_bars_registered_under_the_same_names"]["analogy"] == d2
    assert "never a bar" in reg["exact_search_ceiling"]
    # the A2.7 names and sentences appear verbatim in Codex's text (whitespace joined), when the object is here
    text = codex_design_text()
    if text is not None:
        assert hashlib.sha256(text).hexdigest() == Hm.DESIGN_V0_4_SHA256_AT_SOURCE
        a27 = " ".join(text.decode("utf-8").split("### A2.7")[1].split())
        for name in d2 + ["FRONTIER_FALLBACK", "SINGLE_ROOT_FALLBACK", "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP",
                          "THREE_HOP_FIRST_CHILD"]:
            assert "`%s`" % name in a27, name
        for sentence in Hm.REACH_CLAIM_LIMITS_A2_7:
            assert sentence in a27, sentence
        a23 = " ".join(text.decode("utf-8").split("### A2.3")[1].split("### A2.4")[0].split())
        assert '"%s"' % Hm.CONFIRMATORY_CAPTION_A2_3 in a23.replace("**", "")
    # R1 (Q-A): both directions registered; option b moves them to printed-only and widens the scope; c is refused
    assert Hm.R1_ANALOGY_SCOPE_DECISION == "a"
    for bar in Hm.WHOLE_CHILD_BARS:
        assert reg["analogy"].count(bar) == 1
    assert reg["design_owner_switches"]["R1_ANALOGY_SCOPE_DECISION"] == "a"
    assert Hm.scope_sentence() == Hm.SCOPE_SENTENCE
    monkeypatch.setattr(Hm, "R1_ANALOGY_SCOPE_DECISION", "b_widen_scope")
    off = Hm.registered_comparators()
    assert not set(Hm.WHOLE_CHILD_BARS) & set(off["analogy"])
    assert off["computed_not_registered_printed_only"]["analogy"] == list(Hm.WHOLE_CHILD_BARS)
    assert hw.sha(off) != hw.sha(reg) and Hm.scope_sentence().startswith(Hm.SCOPE_SENTENCE + " Under R1 option b")
    monkeypatch.setattr(Hm, "R1_ANALOGY_SCOPE_DECISION", "c")
    with pytest.raises(SystemExit, match="R1 option c"):
        Hm.check_d1()
    monkeypatch.setattr(Hm, "R1_ANALOGY_SCOPE_DECISION", "zz")
    with pytest.raises(SystemExit, match="R1_ANALOGY_SCOPE_DECISION must be one of"):
        Hm.check_d1()


def test_presalt_manifest_matches_the_build():
    """A2.7's pre-key deliverable: the committed PRESALT_MANIFEST_HSET2.json carries the bar set exactly as the build
    registers it, its digest, the tie rules and the launcher pins (the salt pin still None, for the custodian)."""
    Hm = H()
    launch = launcher()
    m = json.loads((HERE / "PRESALT_MANIFEST_HSET2.json").read_text(encoding="utf-8"))
    assert m["registered_comparators"] == Hm.registered_comparators()
    assert m["registered_comparators_digest"] == hw.sha(Hm.registered_comparators())
    assert m["tie_rules_pinned"] == Hm.TIE_RULES
    assert m["pins"]["EXPECTED_TEST5_SHAPES_DIGEST"] == launch.EXPECTED_TEST5_SHAPES_DIGEST
    assert m["pins"]["UV_TARBALL_SHA256"] == launch.UV_TARBALL_SHA256
    assert m["pins"]["HSET2_SALT_SHA256"] is None and Hm.HSET2_SALT_SHA256 is None
    assert m["public_excluded"]["class_digests_digest"] == json.loads(
        (HERE / S0.PUBLIC_EXCLUDED_FILE).read_text(encoding="utf-8"))["class_digests_digest"]
    summary = json.loads((HERE / S0.SUMMARY_FILE).read_text(encoding="utf-8"))
    assert m["stage0_files_sha256"] == summary["files_sha256"]


# ============================================================================ clusters, floor, statistics (s5, s7)
def test_cluster_counting_and_tuned_diagnostic():
    """A cluster is right only if all 4 rows are right; no parameter is chosen for a claim (Codex A2.1): the old tuned
    choice is printed only as a labelled diagnostic, and the binding bar is the worst family member."""
    Hm = H()
    names = Hm.analogy_comparators()
    rows = {}
    clusters = []
    for f in range(3):
        items = ["c%d|%s|pres%d" % (f, st, k) for st in ("MATCH", "NO_MATCH") for k in (0, 1)]
        for i in items:
            rows[i] = {"comparators": {x: True for x in names}}
            rows[i]["comparators"]["FIXED_ALIAS_W1"] = f == 0
            rows[i]["comparators"]["STATUS_BY_COUNT_0"] = False
        clusters.append({"items": items, "shape_key": "s%d" % f, "group_key": "g%d" % f})
    rows["c1|NO_MATCH|pres1"]["comparators"]["FLAG_ANCHOR"] = False          # one presentation wrong: cluster wrong
    rows["c2|NO_MATCH|pres0"]["comparators"]["FIXED_ALIAS_W0"] = False
    Hm.cluster_results(clusters, rows, names)
    assert [c["comparators"]["FLAG_ANCHOR"] for c in clusters] == [True, False, True]
    assert [c["comparators"]["FIXED_ALIAS_W0"] for c in clusters] == [True, True, False]
    block = Hm.floor_block(A, clusters, names, need_groups=True)
    W = block["W_by_comparator"]
    assert W["FLAG_ANCHOR"] == 1 and W["FIXED_ALIAS_W0"] == 1 and W["FIXED_ALIAS_W1"] == 2 and W["STATUS_BY_COUNT_0"] == 3
    assert block["binding_W"] == 0 and block["distinct_degree_groups"] == 3
    diag = Hm.tuned_diagnostic(W)
    assert diag["label"].startswith("DIAGNOSTIC_ONLY_NEVER_A_BAR")
    assert diag["BEST_FIXED_POSITION"] == {"chosen": "FIXED_ALIAS_W2", "W": 0}   # the first alias with W 0
    assert diag["BEST_STATUS_BY_COUNT"] == {"chosen": "STATUS_BY_COUNT_1", "W": 0}


def view_cluster(cid, group, classes, **right):
    return {"cluster_id": cid, "view_group": group, "role_classes": classes, "shape_key": classes[0],
            "comparators": {"X": right.get("X", False), "Y": right.get("Y", True)}}


def test_view_units_and_feasibility_counts():
    """Codex A2.2 / A2.4: degree groups, shared-shape components (transitive), W in every view, the floors."""
    Hm = H()
    members = [view_cluster("a1", "gA", ["k1", "f1"]), view_cluster("a2", "gA", ["k2", "f2"], X=True),
               view_cluster("b1", "gB", ["k3", "f1"], X=True),          # shares f1 with gA
               view_cluster("c1", "gC", ["k4", "k3"], X=True),          # shares k3 with gB: gA-gB-gC one component
               view_cluster("d1", "gD", ["k5"]), view_cluster("e1", "gE", ["k6"], X=True)]
    groups, comp = Hm.view_units(members)
    assert sorted(groups) == ["gA", "gB", "gC", "gD", "gE"]
    assert comp["gA"] == comp["gB"] == comp["gC"] and len({comp["gA"], comp["gD"], comp["gE"]}) == 3
    block = Hm.views_block(members, ("X", "Y"))
    assert block["units"] == {"original_cluster": 6, "degree_group": 5, "shared_shape_component": 3}
    # X is wrong on a1 (gA) and d1 (gD): 2 clusters, 2 groups, 2 components; Y is never wrong
    assert block["W_by_comparator_by_view"]["X"] == {"original_cluster": 2, "degree_group": 2, "shared_shape_component": 2}
    assert block["binding_by_view"]["degree_group"]["comparator"] == "Y" and block["binding_by_view"]["degree_group"]["W"] == 0
    assert block["size_distributions"] == {"clusters_per_degree_group": {"1": 4, "2": 1},
                                           "degree_groups_per_component": {"1": 2, "3": 1},
                                           "clusters_per_component": {"1": 2, "4": 1}}
    assert block["floors"]["applies"].startswith("PRINTED_NOT_BINDING") and not block["floors"]["meets_every_floor"]
    assert "shared-shape components 3 < 10" in block["floors"]["not_testable_reasons"]
    assert block["repaired_vs_unchanged_informative_count"]["state"] == "NOT_YET_OBSERVED"
    assert Hm.views_block(members, ("X",), confirmatory_analogy=True)["floors"]["applies"].startswith("BINDING")
    # counts only: no class or group key reaches the printed block
    text = json.dumps(block)
    assert not any(s in text for s in ("gA", "k1", "f1", "a1"))


def test_paired_views_exact():
    """Codex A2.2: exact rational group and component means; the sign tail; B > C, positive overall difference and
    p <= 0.01. Here the cluster view passes but the group view cannot: every win sits in one degree group."""
    Hm = H()
    members = [view_cluster("w%d" % i, "g0", ["s%d" % i], X=False) for i in range(12)]
    members += [view_cluster("t%d" % i, "g%d" % (i + 1), ["u%d" % i], X=True) for i in range(9)]
    groups, comp = Hm.view_units(members)
    model = {c["cluster_id"]: True for c in members}
    bar = {c["cluster_id"]: c["comparators"]["X"] for c in members}
    out = Hm.paired_views(A, members, groups, comp, model, bar)
    assert out["overall_accuracy_difference"] == "4/7"                     # 12 wins of 21 clusters
    assert out["original_cluster"]["b"] == 12 and out["original_cluster"]["c"] == 0 and out["original_cluster"]["pass"]
    assert out["original_cluster"]["label"] == "CONDITIONAL_CLUSTER_DIAGNOSTIC"
    assert out["degree_group"] == {"units": 10, "B": 1, "C": 0, "ties": 9, "p_exact": "1/2", "p": 0.5, "pass": False}
    assert out["shared_shape_component"]["B"] == 1 and not out["shared_shape_component"]["pass"]
    # mixed signs inside a group: its mean is exact (1 - 1 + 1) / 3 = 1/3 > 0
    mixed = [view_cluster("m%d" % i, "gm", ["x%d" % i], X=(i == 1)) for i in range(3)]
    g2, c2 = Hm.view_units(mixed)
    res = Hm.paired_views(A, mixed, g2, c2, {"m0": True, "m1": False, "m2": True},
                          {c["cluster_id"]: c["comparators"]["X"] for c in mixed})
    assert res["degree_group"]["B"] == 1 and res["overall_accuracy_difference"] == "1/3"
    # the scorer's per-cell call: the model against every bar in every view
    ev = Hm.evaluate_cell_views(A, members, ("X", "Y"), model)
    assert ev["passes_every_bar"] == {"original_cluster": False, "degree_group": False, "shared_shape_component": False}
    assert ev["per_bar"]["Y"]["original_cluster"]["b"] == 0                # Y is right everywhere: nothing to win


def test_sign_tail_and_conditional_power_exact():
    Hm = H()
    from fractions import Fraction
    assert Hm.sign_tail_exact(0, 0) == 1 and Hm.sign_tail_exact(7, 0) == Fraction(1, 128)
    assert Hm.sign_tail_exact(9, 1) == Fraction(11, 1024)
    assert [Hm.sign_min_wins(d) for d in (0, 6, 7, 9, 10, 12)] == [None, None, 7, 9, 10, 11]
    assert Hm.conditional_sign_power(6, (1, 1)) == 0 and Hm.conditional_sign_power(7, (1, 1)) == 1
    # a brute-force check against the definition, d = 12, q = 0.6
    brute = sum(Fraction(math.comb(12, B)) * Fraction(3, 5) ** B * Fraction(2, 5) ** (12 - B) for B in range(13)
                if B > 12 - B and Hm.sign_tail_exact(B, 12 - B) <= Fraction(1, 100))
    assert Hm.conditional_sign_power(12, (3, 5)) == brute
    table = Hm.sign_power_table([7, 3])
    assert table["all_win_minimum_discordant_units"] == 7
    assert sorted(table["by_unit_count"]) == ["3", "7"]
    assert table["by_unit_count"]["7"]["1.00"] == [0, 0, 0, 0, 0, 0, 0, 1.0]
    assert len(table["by_unit_count"]["3"]["0.60"]) == 4
    # review of 4c402209, finding 3: 12 significant digits beside the 6-place values (one list per q, d = 0..top)
    digits = table["by_discordant_count_12_significant_digits"]
    assert digits["0.60"][7] == Hm.sig12(Fraction(3, 5) ** 7) == "0.0279936" and len(digits["0.60"]) == 8
    assert Hm.sig12(Fraction(1, 10 ** 9)) == "1e-09"                       # a small power does not print as 0


def test_exact_view_power_under_the_hset1a_model():
    """Review of 4c402209, finding 3: the HSET-1A power grid recomputed exactly at the group and component levels.
    Checked against HSET-1A's own float grid (cluster level), a hand count (never-loses, groups) and a brute-force sum
    over every cluster outcome (groups and components, one uniform and one never-loses setting)."""
    Hm = H()
    import itertools
    from fractions import Fraction
    # 1. the original cluster view equals HSET-1A's power_given_bar (12 of 30 clusters wrong for the bar)
    members = [view_cluster("c%d" % i, "g%d" % i, ["s%d" % i], X=(i >= 12)) for i in range(30)]
    groups, comp = Hm.view_units(members)
    ex = Hm.exact_view_power(members, groups, comp, "X", "original_cluster")
    grid = Hm.power_grid(A, 12, 30)
    for name in ("uniform_model_accuracy", "never_loses_where_bar_is_right_wins_fraction"):
        assert set(ex[name]) == set(grid[name])
        for key, value in grid[name].items():
            assert abs(ex[name][key]["value"] - value) <= 2e-6, (name, key)
    # 2. never-loses 0.5, 10 groups each with one bar-wrong and one bar-right cluster: a group wins with
    # probability 1/2 and never loses, so the pass needs 7 or more wins: (120 + 45 + 10 + 1) / 1024
    members = []
    for g in range(10):
        members += [view_cluster("w%d" % g, "g%d" % g, ["a%d" % g]), view_cluster("r%d" % g, "g%d" % g, ["b%d" % g], X=True)]
    groups, comp = Hm.view_units(members)
    ex = Hm.exact_view_power(members, groups, comp, "X", "degree_group")
    assert ex["state"] == "COMPUTED_EXACT" and ex["units"] == 10 and ex["units_where_the_bar_is_wrong_somewhere"] == 10
    assert ex["never_loses_where_bar_is_right_wins_fraction"]["0.50"]["value_12_significant_digits"] == Hm.sig12(Fraction(176, 1024))
    # 3. brute force: 8 groups (one with 2 wrong and 1 right, one with 1 and 1, six with 1 wrong); g0 and g1 share a
    # class, so there are 7 components
    spec = [("g0", 2, 1), ("g1", 1, 1)] + [("g%d" % k, 1, 0) for k in range(2, 8)]
    members = []
    for g, wrong, right in spec:
        shared = ["shared"] if g in ("g0", "g1") else []
        members += [view_cluster("%sw%d" % (g, i), g, ["%s-w%d" % (g, i)] + shared) for i in range(wrong)]
        members += [view_cluster("%sr%d" % (g, i), g, ["%s-r%d" % (g, i)], X=True) for i in range(right)]
    groups, comp = Hm.view_units(members)
    assert len(groups) == 8 and len(set(comp.values())) == 7

    def brute(view, win, keep):
        total = Fraction(0)
        for outcome in itertools.product((0, 1), repeat=len(members)):
            weight, d = Fraction(1), {}
            for c, right in zip(members, outcome):
                p = keep if c["comparators"]["X"] else win
                weight *= p if right else 1 - p
                d[c["cluster_id"]] = right - int(c["comparators"]["X"])
            gmean = {g: Fraction(sum(d[c["cluster_id"]] for c in cs), len(cs)) for g, cs in groups.items()}
            if view == "degree_group":
                values = list(gmean.values())
            else:
                by = {}
                for g, v in gmean.items():
                    by.setdefault(comp[g], []).append(v)
                values = [sum(vs, Fraction(0)) / len(vs) for vs in by.values()]
            B, C = sum(v > 0 for v in values), sum(v < 0 for v in values)
            if B > C and Hm.sign_tail_exact(B, C) <= Fraction(1, 100):
                total += weight
        return total
    for view in ("degree_group", "shared_shape_component"):
        ex = Hm.exact_view_power(members, groups, comp, "X", view)
        assert ex["state"] == "COMPUTED_EXACT" and ex["bar_cluster_accuracy"] == round(2 / 11, 6)
        assert sorted(ex["uniform_model_accuracy"]) == ["0.2818", "0.3818", "0.4818", "1.0000"]
        q = Fraction("0.3818")
        value = brute(view, q, q)
        assert 0 < value < Fraction(1, 10 ** 2)                  # small, and still printed with its digits
        assert ex["uniform_model_accuracy"]["0.3818"]["value_12_significant_digits"] == Hm.sig12(value)
        assert (ex["never_loses_where_bar_is_right_wins_fraction"]["0.75"]["value_12_significant_digits"]
                == Hm.sig12(brute(view, Fraction(3, 4), Fraction(1))))
        assert ex["uniform_model_accuracy"]["1.0000"]["value"] == 1.0
    # 4. fewer than 7 units where the bar is wrong: exactly 0 in every setting
    few = [view_cluster("f%d" % i, "g%d" % i, ["t%d" % i], X=(i >= 6)) for i in range(20)]
    g4, c4 = Hm.view_units(few)
    ex = Hm.exact_view_power(few, g4, c4, "X", "degree_group")
    assert ex["state"].startswith("EXACT_ZERO")
    assert all(v["value"] == 0 for name in ("uniform_model_accuracy", "never_loses_where_bar_is_right_wins_fraction")
               for v in ex[name].values())
    assert "UPPER BOUND" in Hm.POWER_ASSUMPTIONS


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
    launch = launcher()
    D2 = launch.D
    assert launch.worst_case_usd() < launch.DOLLAR_CEILING == 1.00
    pins = launch.builder_pins((HERE / "hset2_build.py").read_bytes())
    assert pins == {"HSET1A_SALT_SHA256": H().HSET1A_SALT_SHA256, "HSET2_SALT_SHA256": H().HSET2_SALT_SHA256,
                    "SOURCE_COMMIT": launch.SOURCE_COMMIT}
    for value in (pins["HSET2_SALT_SHA256"], launch.EXPECTED_TEST5_SHAPES_DIGEST, launch.UV_TARBALL_SHA256):
        assert pin_or_none(value)                                  # None until the coordinator commits it (review F7)
    # set in the pre-salt round: HSET-1A's public test_shapes_digest, and uv 0.12.7's published tarball sha256
    assert launch.EXPECTED_TEST5_SHAPES_DIGEST == "1b5a1d6872a69c350a73e51888cf7a942e00d5ea5747fa883a85f43444792bf9"
    assert launch.UV_TARBALL_SHA256 == "788f18abea7c5f55d6216e4f5613fd89d4d59b631efeec117b2b07fe72f1da21"
    assert launch.UV_VERSION == "0.12.7"
    assert D2 + "hset2/PUBLIC_EXCLUDED_v2.json" in launch.CLAUDE_FILES and D2 + "hset2/PUBLIC_EXCLUDED_v1.json" in launch.CLAUDE_FILES
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


def test_launcher_dry_run_refuses_only_for_the_salt_pin(tmp_path):
    """Acceptance: the AWS job's dry run makes no AWS call and refuses ONLY because HSET2_SALT_SHA256 (the custodian's
    pin) is missing. Run as a child process in which importing boto3 fails loudly; before the round's commit it may
    also name the uncommitted files, which is reported separately and is not a pin."""
    launch = launcher()
    assert launch.pin_refusals((HERE / "hset2_build.py").read_bytes()) == ["HSET2_SALT_SHA256"]
    pinned = (HERE / "hset2_build.py").read_bytes().replace(b"HSET2_SALT_SHA256 = None",
                                                           b'HSET2_SALT_SHA256 = "' + b"a" * 64 + b'"', 1)
    assert launch.pin_refusals(pinned) == []                        # with a (throwaway) pin, nothing else is missing
    fake = tmp_path / "no_aws"
    fake.mkdir()
    (fake / "boto3.py").write_text('raise ImportError("DRY_RUN_IMPORTED_BOTO3")' + chr(10), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(fake) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    before = set((HERE.parent / "hset2_aws_job").iterdir())
    run = subprocess.run([sys.executable, "-B", str(HERE.parent / "hset2_aws_job" / "launch.py"), "--dry-run"],
                         capture_output=True, text=True, env=env, timeout=240)
    assert run.returncode == 1, run.stderr[-500:]
    assert "DRY_RUN_IMPORTED_BOTO3" not in run.stderr + run.stdout and "Traceback" not in run.stderr
    message = run.stderr.strip()
    assert re.match(r"^BUNDLE_REFUSED [(][0-9][)]: ", message), message[:200]
    items = message.split("): ", 1)[1].split(" | ")
    pins = [i for i in items if not i.startswith("UNCOMMITTED_BUILDER_OR_JOB_FILES")]
    assert pins == [launch.PIN_REFUSALS["HSET2_SALT_SHA256"]], items
    assert set((HERE.parent / "hset2_aws_job").iterdir()) == before      # no machine script, no launch record


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
    assert set(summary["cells"]["TEST_NEW_6/ANALOGY"]["W_by_comparator"]) == set(H().analogy_comparators())
    assert set(summary["cells"]["TEST_NEW_6/CORRESPONDENCE"]["W_by_comparator"]) == set(H().CORRESPONDENCE_COMPARATORS)
    for claim in ("REACH_3_STEP_TRANSFER_6", "REACH_4_STEP_TRANSFER_6"):
        assert set(summary["cells"]["TEST_NEW_6/REACH_BFS"]["claims"][claim]["W_by_comparator"]) == set(reg["reach"][claim])
        assert "FRONTIER_FALLBACK" in reg["reach"][claim]
    # Codex A2.1: no tuned choice decides anything; it is printed only as a labelled diagnostic
    an = summary["cells"]["TEST_NEW_6/ANALOGY"]
    assert "tuned_parameters_chosen_on_this_cell" not in an
    assert an["tuned_on_this_cell_diagnostic_not_a_bar"]["label"].startswith("DIAGNOSTIC_ONLY_NEVER_A_BAR")
    # Codex A2.2 / A2.4: every claim cell has the three views; the table is labelled THROWAWAY; the confirmatory
    # claim is registered with its floors; repaired-versus-unchanged is not observed yet
    feas = summary["a2_4_feasibility"]
    assert feas["table_state"].startswith("THROWAWAY") and feas["rows"]
    assert {(r["cell"], r["claim"]) for r in feas["rows"]} >= {
        ("TEST_NEW_6/ANALOGY", None), ("TEST_NEW_6/CORRESPONDENCE", None), ("TEST_NEW_5/CORRESPONDENCE", None),
        ("TEST_NEW_6/REACH_BFS", "REACH_3_STEP_TRANSFER_6"), ("TEST_NEW_6/REACH_FIRST_DIRECT", "REACH_4_STEP_TRANSFER_6")}
    for r in feas["rows"]:
        assert set(r["units"]) == {"original_cluster", "degree_group", "shared_shape_component"}
        assert r["units"]["shared_shape_component"] <= r["units"]["degree_group"] <= r["units"]["original_cluster"]
        for view, b in r["binding_by_view"].items():
            assert b["W"] <= r["units"][view]
        assert r["repaired_vs_unchanged_informative_count"]["state"] == "NOT_YET_OBSERVED"
        for n in set(r["units"].values()):
            assert str(n) in feas["conditional_sign_power_by_unit_count"]["by_unit_count"]
        # review of 4c402209, finding 3: the HSET-1A grid, exact, in every view, for that view's binding bar
        assert set(r["exact_power_under_hset1a_model"]) == set(r["units"]) and "UPPER BOUND" in r["power_assumptions"]
        for view, ex in r["exact_power_under_hset1a_model"].items():
            assert ex["bar"] == r["binding_by_view"][view]["comparator"] and ex["units"] == r["units"][view]
            assert ex["state"] in ("COMPUTED_EXACT", "NO_UNITS") or ex["state"].startswith("EXACT_ZERO")
    assert feas["conditional_sign_power_by_unit_count"]["by_discordant_count_12_significant_digits"]
    # review of 4c402209, finding 4: both-arm packet-route acceptance is named as still required
    assert feas["both_arm_packet_route_acceptance"]["state"] == "NOT_YET_CHECKED"
    assert "20208c92" in feas["both_arm_packet_route_acceptance"]["still_required"]
    assert reg["design_owner_switches"]["D1_FRONTIER_DECISION"] == "a"
    assert summary["claims_before_any_model"]["REACH_3_STEP_TRANSFER_6"]["d1_frontier_decision"]["value"] == "a"
    rep = summary["claims_before_any_model"]["REPAIR_IMPROVES_ANALOGY_6"]
    assert rep["status_if_not"] == "NOT_TESTABLE" and rep["not_testable_reasons"]      # 1 focus per split: too few
    # review of 4c402209, note 7: the status words the future scorer must carry
    assert rep["mechanism_gate_status"]["state"] == "MECHANISM_GATE_OPEN"
    assert rep["inference_assumptions_status"]["state"] == "OPEN_FOR_THE_BUILDER_SCORER_REVIEW"
    assert {"INFERENCE_ASSUMPTIONS_UNSUPPORTED", "MECHANISM_GATE_OPEN"} <= set(rep["status_words_the_scorer_must_use"])
    # review of 4c402209, finding 1 (R1): Claude's default Q-A registers the whole-child rule in both directions
    for claim in ("ANALOGY_BEYOND_DEGREE_6", "REPAIR_IMPROVES_ANALOGY_6"):
        r1 = summary["claims_before_any_model"][claim]["r1_analogy_scope_decision"]
        assert r1["value"] == "a" and r1["state"].startswith("CLAUDE_DEFAULT_Q_A_APPLIED")
    for bar in H().WHOLE_CHILD_BARS:
        assert bar in summary["cells"]["TEST_NEW_6/ANALOGY"]["W_by_comparator"]
    for claim in ("REACH_3_STEP_TRANSFER_6", "REACH_4_STEP_TRANSFER_6"):     # A2.7 D1 wording, word for word
        assert summary["claims_before_any_model"][claim]["claim_limits_A2_7"] == list(H().REACH_CLAIM_LIMITS_A2_7)
    assert rep["caption_only_if_every_condition_passes_A2_3"] == H().CONFIRMATORY_CAPTION_A2_3
    assert summary["splits"]["public_excluded_class_digests_digest"] == json.loads(
        (HERE / "PUBLIC_EXCLUDED_v2.json").read_text(encoding="utf-8"))["class_digests_digest"]
    assert summary["inference_assumptions"]["state"] == "OPEN_FOR_THE_BUILDER_SCORER_REVIEW"
    assert summary["success_rule"].count("CONDITIONAL_CLUSTER_DIAGNOSTIC") == 1
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
