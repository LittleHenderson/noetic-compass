"""LB17 — the decisive test: does the MEAN-POOLED world vector carry the graph under the
only gradient rule the draft allows it?

Section 2.1 says the directed contains adjacency "is given ONLY to message passing, never
to a readout head", and the heads read node states and pooled world vectors. So the pooled
vector can only learn structure by backpropagating through the node states. That gradient
is:

    d g_w / d h_v^{k} = (1/N) * d h_v^{K} / d h_v^{k}

and the measured spectral norm of that map (LB13) is ~1 (a residual stream with RMS
normalisation is locally near-isometric in this sense). So the pooled vector receives, per
node, essentially the node's own local update: its OWN feature plus a normalised sum of its
neighbours' features -- still ~O(1) and still dominated by the O(1) features, not by a
topology readout.

This script measures the ratio of "pooled vector moved because the GRAPH changed" to
"pooled vector spread because the FEATURES changed", when all node features are alike
(which is the course case: every node is kind "idea" with the same flag set apart from
declared_whole / participant rank / primary rank).
"""
import sys
from pathlib import Path

import numpy as np

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c

frozen, tokenizer, devdoc = c.load_material(CNCM)
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}
shape_sets = {}
for wid, w in sorted(worlds.items()):
    refs = sorted(n["ref"] for n in w["nodes"])
    idx = {r: i for i, r in enumerate(refs)}
    edges = tuple(sorted((idx[e["source"]], idx[e["target"]]) for e in w["contains"]))
    shape_sets.setdefault(edges, 0)
    shape_sets[edges] += 1
shapes = sorted(shape_sets)
print("bank shapes (6 total):", shapes)

# exact per-node flags from the material, to see how alike two nodes really are
flags = {}
for wid, w in sorted(worlds.items()):
    part = list(w["declarations"]["participants"])
    prim = list(w["declarations"]["primary_labels"])
    for n in w["nodes"]:
        r = n["ref"]
        flags[r] = (int(r == w["declared_whole"]), part.index(r) + 1 if r in part else 0,
                    prim.index(r) + 1 if r in prim else 0)
agg = {}
for wid, w in sorted(worlds.items()):
    for n in w["nodes"]:
        key = flags[n["ref"]]
        agg[key] = agg.get(key, 0) + 1
print("node flag triples (is_declared_whole, participant_rank, primary_rank), counts over 244 nodes:")
for k in sorted(agg, key=lambda x: -agg[x]):
    print("   %s : %d nodes" % (str(k), agg[k]))

D, F = 64, 9
rng = np.random.default_rng(11)
Win = rng.normal(0, 1 / np.sqrt(F), (D, F))
Wl = rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D))
Wr = rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D))
Wm = rng.uniform(-1 / np.sqrt(2 * D), 1 / np.sqrt(2 * D), (D, 2 * D))


def encode(feats, edges, n, rounds=2, mode="output"):
    adj = np.zeros((n, n))
    for a, b in edges:
        adj[a, b] = 1.0
    h = feats @ Win.T
    if mode == "output":
        h = h / (np.sqrt(np.mean(h * h)) + 1e-8)
    for _ in range(rounds):
        hh = h / (np.sqrt(np.mean(h * h)) + 1e-8) if mode == "input" else h
        a = hh + adj.T @ hh + adj @ hh
        h = h + np.concatenate([np.tanh(a @ Wl.T), np.tanh(a @ Wr.T)], axis=-1) @ Wm.T
        if mode == "output":
            h = h / (np.sqrt(np.mean(h * h)) + 1e-8)
    return h.mean(axis=0)


print()
print("A: all node features IDENTICAL within a world (feature noise off)")
for rounds in (1, 2, 4, 8):
    vecs = {}
    for edges in shapes:
        n = max(max(e) for e in edges) + 1
        feats = np.tile(np.arange(F, dtype=float) / F, (n, 1))
        vecs[edges] = encode(feats, edges, n, rounds)
    G = np.array([vecs[e] for e in shapes])
    gmean = G.mean(axis=0)
    dev = np.linalg.norm(G - gmean, axis=1)
    print("   rounds %d : ||g_w|| %.4f ; spread across the 6 shapes (mean, max) %.4g, %.4g ; relative spread %.4f"
          % (rounds, float(np.linalg.norm(G, axis=1).mean()), float(dev.mean()), float(dev.max()),
             float(dev.max() / np.linalg.norm(G, axis=1).mean())))

print()
print("B: features drawn randomly per node (the label-vector channel is ON)")
for rounds in (1, 2, 4, 8):
    per_shape = {}
    for edges in shapes:
        n = max(max(e) for e in edges) + 1
        per_shape[edges] = [encode(np.random.default_rng(200 + d).normal(0, 1, (n, F)), edges, n, rounds)
                            for d in range(5)]
    inter, intra = [], []
    keys = sorted(per_shape)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            for va in per_shape[a]:
                for vb in per_shape[b]:
                    inter.append(np.linalg.norm(va - vb))
    for a in keys:
        v = per_shape[a]
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                intra.append(np.linalg.norm(v[i] - v[j]))
    print("   rounds %d : mean ||g_w(a) - g_w(b)||, DIFFERENT shape %.4f ; SAME shape, different features %.4f ; ratio %.4f"
          % (rounds, float(np.mean(inter)), float(np.mean(intra)), float(np.mean(inter)) / float(np.mean(intra))))

print()
print("C: the same, but with features that differ only in the 3 REAL flag dimensions")
print("   (each node's features = [flag0, flag1, flag2, 0,0,0,0,0,0])")
for rounds in (1, 2, 4, 8):
    per_shape = {}
    for edges in shapes:
        n = max(max(e) for e in edges) + 1
        feats = np.zeros((n, F))
        for i in range(n):
            feats[i, 0] = 1.0 if i == 0 else 0.0
            feats[i, 1] = (i % 3) + 1
            feats[i, 2] = (i % 2) + 1
        per_shape[edges] = [encode(feats, edges, n, rounds)]
    G = np.array([per_shape[e][0] for e in shapes])
    gmean = G.mean(axis=0)
    dev = np.linalg.norm(G - gmean, axis=1)
    print("   rounds %d : ||g_w|| %.4f ; spread across the 6 shapes (mean, max) %.4g, %.4g ; relative spread %.4f"
          % (rounds, float(np.linalg.norm(G, axis=1).mean()), float(dev.mean()), float(dev.max()),
             float(dev.max() / np.linalg.norm(G, axis=1).mean())))
