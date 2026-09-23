import sys, pathlib, random, collections
ROOT = pathlib.Path("D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.dont_write_bytecode = True
for p in (str(ROOT / "records/helm_eval_design_20260923/d1_acceptance"), str(ROOT / "records/helm_eval_design_20260923/hset1a")):
    sys.path.insert(0, p)
import hset_worlds as hw, oracle_isomorphism as oracle, hset1b_build as B
def stats(shape):
    n, edges = shape; edges = list(edges)
    out = collections.Counter()
    aut = hw.automorphisms(n, edges) if n <= 6 else None
    for r in hw.roots(n, edges):
        kids = hw.children(edges, r)
        for p in range(n):
            if p == r: continue
            d = hw.distance(edges, r, p)
            if d is None: out["A"] += 1; continue
            if d == 1: out["D"] += 1; continue
            first = [c for c in kids if p == c or p in hw.reachable(edges, c)]
            level = [x for x in range(n) if hw.distance(edges, r, x) == d - 1 and (x, p) in set(edges)]
            for rule, nt in (("F", len(first) == 1), ("B", len(level) == 1)):
                if nt:
                    out["V" + rule] += 1
                    if d >= 3: out["V" + rule + "3"] += 1
    return out
def gen(mode, seed, n, count):
    rng = random.Random(seed); got = set(); res = []
    while len(res) < count:
        if mode == "D": e = B._density_edges(rng, n)
        elif mode == "T": e = B._tree_edges(rng, n)
        else: e = B._density_edges(rng, n) if rng.random() < 0.5 else B._tree_edges(rng, n)
        if not e or not oracle._weakly_connected(n, e) or not oracle._acyclic(n, e): continue
        o = collections.Counter(a for a, _ in e); i = collections.Counter(b for _, b in e)
        if max(list(o.values()) + list(i.values())) > 4: continue
        c = oracle.canonical_form(n, e)
        if c in got: continue
        got.add(c); res.append(c)
    return res
for mode in ("D", "T", "MIX"):
    for n in (6, 7):
        tot = collections.Counter()
        shapes = gen(mode, "HSET-1B-sampler-tuning", n, 200)
        for s in shapes: tot += stats(s)
        per40 = {k: round(v * 40 / 200, 1) for k, v in tot.items()}
        for rule in ("F", "B"):
            k = min(per40.get("A", 0), per40.get("D", 0), per40.get("V" + rule, 0))
            frac = per40.get("V" + rule + "3", 0) / max(1e-9, per40.get("V" + rule, 0))
            print(mode, n, rule, "per 40 shapes:", {x: per40.get(x, 0) for x in ("A", "D", "V" + rule, "V" + rule + "3")}, "k=%.1f expected W~%.1f" % (k, k * frac), flush=True)
