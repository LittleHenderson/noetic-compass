# test_rgm01.py — unit tests for the RGM-0.1 machinery (run with test_rgm0.py before commit).
from cmb_r1_v01_core import role_traj, propagate_variant, build_generic_geometry, adj_from_links, echo_attack, ROLE
import cmb_r1_core as K
import random

def test_role_coarsening():
    K.SEED = 20260901
    mem, topics, marg = K.build_corpus()
    rng = random.Random(1)
    build_generic_geometry(mem, rng)
    for m in list(mem.values())[:50]:
        rt = m["role_trajectory"]
        assert len(rt) == len(m["trajectory"])
        assert all(o in (0, 1, 2, 3, 4) for o in rt)
    # 2 and 3 collapse to the same role (the deliberate loss)
    assert ROLE[2] == ROLE[3] == 1

def test_variants_deterministic_and_bounded():
    K.SEED = 20260901
    mem, topics, marg = K.build_corpus()
    adj = K.build_adjacency(mem)
    seeds = {"m0000": 1.0, "m0001": 0.8}
    for mode in ("recurrent", "max", "sum"):
        a1, act1, e1, s1 = propagate_variant(adj, seeds, mem, mode, 3, 0.3, 0.5, 20, True)
        a2, act2, e2, s2 = propagate_variant(adj, seeds, mem, mode, 3, 0.3, 0.5, 20, True)
        assert a1 == a2 and act1 == act2
        assert len(a1) <= 20 and s1 == 3

def test_recurrent_matches_v01_resonate():
    K.SEED = 20260901
    mem, topics, marg = K.build_corpus()
    adj = K.build_adjacency(mem)
    seeds = {"m0000": 1.0, "m0007": 0.9, "m0013": 0.7}
    a_new, act_new, _, _ = propagate_variant(adj, seeds, mem, "recurrent", K.DEPTH, K.DAMPING, K.GAMMA, K.TOPK_WAVE, True)
    a_old, act_old, _, _ = K.resonate(adj, seeds, mem, True)
    assert set(a_new) == set(a_old) and set(act_new) == set(act_old)

def test_echo_attacks_structure():
    K.SEED = 20260901
    mem, topics, marg = K.build_corpus()
    rng = random.Random(7)
    q1 = echo_attack(mem, rng, 0, "near_miss")
    q2 = echo_attack(mem, rng, 1, "overlap")
    assert len(q1["distractors"]) == 20
    assert len(q2["distractors"]) == 20
    fm = [m for m in q2["distractors"]]
    roots = {mem[m]["provenance_root_id"] for m in fm}
    assert len(roots) == 2
    T = mem[q1["targets"][0]]
    f0 = mem[q1["distractors"][0]]
    assert K.traj_sim(T["trajectory"], f0["trajectory"]) >= 0.75

if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items() if k.startswith("test_")}.items()):
        fn()
        print("PASS", name)
    print("ALL TESTS PASS")
