"""LB16 — does the MEAN-POOLED world vector still see the graph at all?

The world vector is g_w = mean of final node states + W_decl(declaration text). If mean
pooling over a small graph washes the structure out, every world-level head (definition
kind/function, context setting, analogy world, correspondence mode) loses its input, and
the 64-way world scorer becomes a constant. This simulates the draft's exact recurrence
in numpy at the real node counts and measures how much shape information survives.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c

frozen, tokenizer, devdoc = c.load_material(CNCM)
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}

SHAPES = {
    "3-path": ("a", ["b"], ["a"], ["b", "c"]),
    "4-star": ("a", ["b", "c", "d"], ["a", "a", "a"], ["b", "c", "d"]),
    "4-path": (["a"], []),
}
# build the six real shapes from the material instead of hand-writing them
shapes = {}
for wid, w in sorted(worlds.items()):
    refs = sorted(n["ref"] for n in w["nodes"])
    idx = {r: i for i, r in enumerate(refs)}
    edges = tuple(sorted((idx[e["source"]], idx[e["target"]]) for e in w["contains"]))
    shapes.setdefault(edges, 0)
    shapes[edges] += 1
print("distinct shape edge-sets among the 64 bank worlds:", len(shapes))
for e, n in sorted(shapes.items(), key=lambda kv: -kv[1]):
    print("   %s : %d worlds" % (e, n))

D, F = 64, 9


def build_adj(n, edges):
    a = np.zeros((n, n))
    for x, y in edges:
        a[x, y] = 1.0
    return a


def encode(feats, adj, Wl, Wr, Wm, Win, rounds, mode):
    kids, pars = adj, adj.T
    h = feats @ Win.T
    if mode == "output":
        h = h / (np.sqrt(np.mean(h * h)) + 1e-8)
    for _ in range(rounds):
        hh = h / (np.sqrt(np.mean(h * h)) + 1e-8) if mode == "input" else h
        a = hh + pars @ hh + kids @ hh
        h = h + np.concatenate([np.tanh(a @ Wl.T), np.tanh(a @ Wr.T)], axis=-1) @ Wm.T
        if mode == "output":
            h = h / (np.sqrt(np.mean(h * h)) + 1e-8)
    return h


rng = np.random.default_rng(0)
Win = rng.normal(0, 1 / np.sqrt(F), (D, F))
Wl = rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D))
Wr = rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D))
Wm = rng.uniform(-1 / np.sqrt(2 * D), 1 / np.sqrt(2 * D), (D, 2 * D))

print()
print("mean-pooled node vector g_w per shape, three random node-feature draws each")
print("(metric: 1 - cosine between g_w of two DIFFERENT shapes, averaged; and between two")
print(" draws of the SAME shape. A head separating shapes needs the first to be big.)")
for mode in ("output", "none"):
    for rounds in (1, 2, 4, 8):
        per_shape = {}
        for edges in shapes:
            n = max(max(e) for e in edges) + 1
            adj = build_adj(n, edges)
            vecs = []
            for draw in range(3):
                feats = np.random.default_rng(100 + draw).normal(0, 1, (n, F))
                h = encode(feats, adj, Wl, Wr, Wm, Win, rounds, mode)
                vecs.append(h.mean(axis=0))
            per_shape[edges] = vecs
        keys = sorted(per_shape)
        inter = []
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                for va in per_shape[a]:
                    for vb in per_shape[b]:
                        inter.append(1 - float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb))))
        intra = []
        for a in keys:
            v = per_shape[a]
            for i in range(len(v)):
                for j in range(i + 1, len(v)):
                    intra.append(1 - float(v[i] @ v[j] / (np.linalg.norm(v[i]) * np.linalg.norm(v[j]))))
        # nearest-centroid identification of a shape from its pooled vector
        cent = {k: np.mean(per_shape[k], axis=0) for k in keys}
        ok = 0
        tot = 0
        for k in keys:
            for v in per_shape[k]:
                best = max(keys, key=lambda q: float(v @ cent[q] / (np.linalg.norm(v) * np.linalg.norm(cent[q]))))
                ok += int(best == k)
                tot += 1
        print("   rms_after=%-7s rounds %d : inter-shape distance %.6f  intra-shape %.6f  ratio %.2f  nearest-centroid %d/%d"
              % (mode, rounds, float(np.mean(inter)), float(np.mean(intra)),
                 float(np.mean(inter)) / max(float(np.mean(intra)), 1e-12), ok, tot))

print()
print("WORST CASE: how big is the pooled vector's deviation from the mean of ALL shapes?")
print("If g_w barely moves when the graph changes, an untrained 64-way world scorer cannot")
print("rank the right world. Compared against the scale of g_w itself:")
for mode in ("output", "none"):
    for rounds in (2, 8):
        allvecs = []
        for edges in shapes:
            n = max(max(e) for e in edges) + 1
            adj = build_adj(n, edges)
            for draw in range(3):
                feats = np.random.default_rng(100 + draw).normal(0, 1, (n, F))
                allvecs.append(encode(feats, adj, Wl, Wr, Wm, Win, rounds, mode).mean(axis=0))
        A = np.array(allvecs)
        grand = A.mean(axis=0)
        within = np.linalg.norm(A - grand, axis=1)
        print("   rms_after=%-7s rounds %d : ||g_w|| mean %.4f ; ||g_w - grand mean|| mean %.4f ; ratio %.4f"
              % (mode, rounds, float(np.linalg.norm(A, axis=1).mean()), float(within.mean()),
                 float(within.mean()) / float(np.linalg.norm(A, axis=1).mean())))

print()
print("NODE-LEVEL: is a node's state still different across shapes?")
print("(the edge_account head needs two nodes' states to tell an edge from a non-edge)")
for mode in ("output", "none"):
    for rounds in (1, 2, 4, 8):
        n = 4
        edges = ([e for e in shapes if len(e) == 3][0])
        adj = build_adj(n, edges)
        feats = np.random.default_rng(5).normal(0, 1, (n, F))
        h = encode(feats, adj, Wl, Wr, Wm, Win, rounds, mode)
        C = np.array([[float(h[i] @ h[j] / (np.linalg.norm(h[i]) * np.linalg.norm(h[j]))) for j in range(n)] for i in range(n)])
        pair = [C[a, b] for (a, b) in edges]
        nonpair = [C[a, b] for a in range(n) for b in range(n) if a != b and (a, b) not in edges]
        print("   rms_after=%-7s rounds %d : mean cosine of EDGE pairs %.6f ; of NON-edge pairs %.6f ; gap %.6f"
              % (mode, rounds, float(np.mean(pair)), float(np.mean(nonpair)), abs(float(np.mean(pair)) - float(np.mean(nonpair)))))
