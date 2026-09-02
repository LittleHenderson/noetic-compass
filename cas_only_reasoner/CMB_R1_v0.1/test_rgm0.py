"""RGM-0 unit tests: mechanism-level properties that must hold regardless of experiment outcome."""
import cmb_r1_core as core

def test_order_sensitivity():
    assert core.traj_sim([8, 2, 6, 9], [8, 2, 6, 9]) == 1.0
    assert core.traj_sim([8, 2, 6, 9], [8, 6, 2, 9]) < 1.0
    assert core.traj_sim([8, 2, 6, 9], [9, 6, 2, 8]) < core.traj_sim([8, 2, 6, 9], [8, 6, 2, 9])

def test_profile_blindness_to_order():
    a = core.profile_of([8, 2, 6, 9])
    b = core.profile_of([9, 6, 2, 8])
    assert core.profile_cos(a, b) > 0.999  # static profile cannot see order

def test_generic_geometry_preserves_marginals():
    mems, topics, marg = core.build_corpus()
    core.assign_generic_geometry(mems, marg)
    base = [m["trajectory"] for m in mems.values() if m["family"] == "BASE"]
    gen = [m["generic_trajectory"] for m in mems.values() if m["family"] == "BASE"]
    assert sum(len(t) for t in base) == sum(len(t) for t in gen)
    from collections import Counter
    for pos in range(6):
        cb = Counter(t[pos] for t in base if len(t) > pos)
        cg = Counter(t[pos] for t in gen if len(t) > pos)
        tot_b = sum(cb.values()) or 1
        tot_g = sum(cg.values()) or 1
        for op in set(cb) | set(cg):
            assert abs(cb.get(op, 0) / tot_b - cg.get(op, 0) / tot_g) < 0.05

def test_corruption_preserves_corpus_bag():
    mems, _, _ = core.build_corpus()
    before = Counter_tuple = sorted(tuple(m["trajectory"]) for m in mems.values())
    import copy
    c2 = copy.deepcopy(mems)
    core.corrupt_corpus(c2)
    after = sorted(tuple(m["trajectory"]) for m in c2.values())
    assert before == after  # exact bag preservation

def test_provenance_budget():
    mems, topics, _ = core.build_corpus()
    queries = core.build_queries(mems, topics)
    adj = core.build_adjacency(mems)
    q = queries["ECHO"][0]
    ranked_d, verified_d, _ = core.arm_d(mems, adj, q, provenance_aware=True, use_coherence=True)
    roots = [mems[m]["provenance_root_id"] for m, _ in verified_d]
    assert len(roots) == len(set(roots))  # one representative per root in the verified set

def test_determinism():
    mems1, _, _ = core.build_corpus()
    mems2, _, _ = core.build_corpus()
    k1 = sorted(mems1.keys())
    k2 = sorted(mems2.keys())
    assert k1 == k2
    for k in k1[:50]:
        assert mems1[k]["trajectory"] == mems2[k]["trajectory"]
        assert mems1[k]["semantic"] == mems2[k]["semantic"]

if __name__ == "__main__":
    fns = [test_order_sensitivity, test_profile_blindness_to_order,
           test_generic_geometry_preserves_marginals, test_corruption_preserves_corpus_bag,
           test_provenance_budget, test_determinism]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print("ALL TESTS PASS")