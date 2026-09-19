"""LB9 — stability of the draft's shared 8-round recurrence, simulated in numpy.

Draft update (DESIGN_DRAFT v0.1, section 2.2):
    h <- h + ^6( W_self h + W_down * sum(parents) + W_up * sum(children) )
with ^6 = _DecomposeTransform = merge(cat(tanh(left x), tanh(right x))), left/right 64x64,
merge 64x128, all bias-free; RMS normalisation per round; SHARED weights over 8 rounds.

The draft does not name the placement of the RMS normalisation, so all three placements
are simulated, plus the no-normalisation control. The ^6 block is applied as
W2.tanh(W1.x) with W1 = [left; right] (128x64) and W2 = merge (64x128) -- the exact form
MEASURED in CASFORMER_V0_2_MAP section 5 -- so gradients through all eight shared rounds
are exact and no autograd library is needed.
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
print("bank world node-count histogram:", dict(Counter(len(w["nodes"]) for w in worlds.values())))
print("largest bank world: %d nodes; bank worlds have at most %d edges"
      % (max(len(w["nodes"]) for w in worlds.values()), max(len(w["contains"]) for w in worlds.values())))
dev = c.development_packets(devdoc)
sizes = Counter(len(next(w for w in q["source"]["worlds"] if w["world_id"] == q["source"]["focus_world_id"])["nodes"]) for q in dev.values())
print("development panel focus-world node counts (packets 59):", dict(sizes))

D = 64
FEATURES = 9


def make_weights(rng, scheme):
    if scheme == "torch_default":
        return (rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D)),
                rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D)),
                rng.uniform(-1 / np.sqrt(2 * D), 1 / np.sqrt(2 * D), (D, 2 * D)))
    if scheme == "he_normal":
        return (rng.normal(0, np.sqrt(2 / D), (D, D)), rng.normal(0, np.sqrt(2 / D), (D, D)),
                rng.normal(0, np.sqrt(2 / (2 * D)), (D, 2 * D)))
    if scheme == "xavier":
        return (rng.normal(0, np.sqrt(2 / (D + D)), (D, D)), rng.normal(0, np.sqrt(2 / (D + D)), (D, D)),
                rng.normal(0, np.sqrt(2 / (D + 2 * D)), (D, 2 * D)))
    if scheme == "over_large":
        return (rng.normal(0, 1.0, (D, D)), rng.normal(0, 1.0, (D, D)), rng.normal(0, 1.0, (D, 2 * D)))
    raise ValueError(scheme)


def rms_norm(x, eps=1e-8):
    return x / (np.sqrt(np.mean(x * x)) + eps)


def step(h, pars, kids, Wl, Wr, Wm, mode):
    hh = rms_norm(h) if mode == "input" else h
    a = hh + pars @ hh + kids @ hh
    left, right = a @ Wl.T, a @ Wr.T
    tl, tr = np.tanh(left), np.tanh(right)
    out = np.concatenate([tl, tr], axis=-1) @ Wm.T
    h = h + out
    if mode == "output":
        h = rms_norm(h)
    sat = 0.5 * (float(np.mean(np.abs(left) > 2.0)) + float(np.mean(np.abs(right) > 2.0)))
    return h, sat, float(np.abs(out).mean()), float(np.abs(out).max())


def run(feats, adj, weights, *, rounds, mode):
    Wl, Wr, Wm = weights
    kids, pars = adj, adj.T
    Win = np.random.default_rng(999).normal(0, 1 / np.sqrt(FEATURES), (D, FEATURES))
    h = feats @ Win.T
    if mode == "output":
        h = rms_norm(h)
    sats, deltas, maxes = [], [], []
    for _ in range(rounds):
        h, sat, dmean, dmax = step(h, pars, kids, Wl, Wr, Wm, mode)
        sats.append(sat)
        deltas.append(dmean)
        maxes.append(float(np.abs(h).max()))
    return h, sats, deltas, maxes


def jacnorm(feats, adj, weights, *, rounds, mode):
    """Spectral norm of d(sum_i h_i^K)/d(h^0), carried blockwise through K shared rounds."""
    Wl, Wr, Wm = weights
    kids, pars = adj, adj.T
    n = adj.shape[0]
    Win = np.random.default_rng(999).normal(0, 1 / np.sqrt(FEATURES), (D, FEATURES))
    h = feats @ Win.T
    if mode == "output":
        h = rms_norm(h)
    # J[i, j] = d h_i / d h_j  -> tensor [N, N, D, D]
    J = np.zeros((n, n, D, D))
    for i in range(n):
        J[i, i] = np.eye(D)
    for _ in range(rounds):
        hh = rms_norm(h) if mode == "input" else h
        a = hh + pars @ hh + kids @ hh
        left, right = a @ Wl.T, a @ Wr.T
        tl, tr = np.tanh(left), np.tanh(right)
        # d out_i / d a_i
        B = np.einsum("ik,jk->ijk", (1 - tl * tl) @ Wl, Wm[:, :D]) + \
            np.einsum("ik,jk->ijk", (1 - tr * tr) @ Wr, Wm[:, D:])
        # d a_i / d hh_j = delta_ij I + pars[i,j] I + kids[i,j] I
        Jnew = np.zeros_like(J)
        for i in range(n):
            for j in range(n):
                coeff = (1.0 if i == j else 0.0) + float(pars[i, j]) + float(kids[i, j])
                if coeff:
                    Jnew[i, j] += coeff * B[i]
        if mode == "output":
            for i in range(n):
                r = np.sqrt(np.mean(h[i] * h[i])) + 1e-8
                u = h[i] / r
                R = (np.eye(D) - np.outer(u, u)) / r
                Jnew[i] = R @ Jnew[i]
        J = J + Jnew
        h = h + np.concatenate([tl, tr], axis=-1) @ Wm.T
        if mode == "output":
            h = rms_norm(h)
    return float(np.linalg.norm(J.reshape(n * D, n * D), 2))


SHAPES = {
    "3-node": (3, [(0, 1), (1, 2)]),
    "4-star": (4, [(1, 0), (1, 2), (1, 3)]),
    "4-V": (4, [(0, 1), (0, 3), (1, 2), (3, 2)]),
    "10-node": (10, [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (5, 6), (3, 7), (7, 8), (8, 9)]),
}


def adjof(n, edges):
    a = np.zeros((n, n))
    for x, y in edges:
        a[x, y] = 1.0
    return a


print()
print("FORWARD, 8 shared rounds, 50 seeds: mean max|h| after the last round, and mean tanh saturation")
print("(saturation = fraction of pre-activations with |z| > 2, where tanh' < 0.071)")
for scheme in ("torch_default", "he_normal", "xavier", "over_large"):
    for mode in ("none", "input", "output"):
        cells = []
        for name, (n, edges) in SHAPES.items():
            adj = adjof(n, edges)
            mx, st = [], []
            for seed in range(50):
                rng = np.random.default_rng(seed)
                feats = rng.normal(0, 1, (n, FEATURES))
                h, sats, _, maxes = run(feats, adj, make_weights(rng, scheme), rounds=8, mode=mode)
                mx.append(maxes[-1])
                st.append(float(np.mean(sats)))
            cells.append("%s max|h|=%.4g sat=%.4f" % (name, float(np.mean(mx)), float(np.mean(st))))
        print("  %-13s rms_after=%-7s %s" % (scheme, mode, " | ".join(cells)))

print()
print("TRAJECTORY, torch_default init, rms AFTER the update: mean max|h| at rounds 1..8")
for name, (n, edges) in SHAPES.items():
    adj = adjof(n, edges)
    curve = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        feats = rng.normal(0, 1, (n, FEATURES))
        Wl, Wr, Wm = make_weights(rng, "torch_default")
        Win = np.random.default_rng(999).normal(0, 1 / np.sqrt(FEATURES), (D, FEATURES))
        h = rms_norm(feats @ Win.T)
        vals = []
        for _ in range(8):
            h, _, _, mx = step(h, adj.T, adj, Wl, Wr, Wm, "output")
            vals.append(mx)
        curve.append(vals)
    print("  %-9s %s" % (name, " ".join("%.4g" % v for v in np.mean(np.array(curve), axis=0))))

print()
print("TRAJECTORY, torch_default init, NO rms at all: mean max|h| at rounds 1..8 (bounded by 8 x ^6 range)")
for name, (n, edges) in SHAPES.items():
    adj = adjof(n, edges)
    curve = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        feats = rng.normal(0, 1, (n, FEATURES))
        Wl, Wr, Wm = make_weights(rng, "torch_default")
        Win = np.random.default_rng(999).normal(0, 1 / np.sqrt(FEATURES), (D, FEATURES))
        h = feats @ Win.T
        vals = []
        for _ in range(8):
            h, _, _, mx = step(h, adj.T, adj, Wl, Wr, Wm, "none")
            vals.append(mx)
        curve.append(vals)
    print("  %-9s %s" % (name, " ".join("%.4g" % v for v in np.mean(np.array(curve), axis=0))))

print()
print("PER-ROUND UPDATE SIZE, torch_default init (mean |out| per round); a fixed point needs this to -> 0")
for mode in ("none", "input", "output"):
    adj = adjof(4, SHAPES["4-V"][1])
    rows = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        feats = rng.normal(0, 1, (4, FEATURES))
        h, sats, deltas, maxes = run(feats, adj, make_weights(rng, "torch_default"), rounds=8, mode=mode)
        rows.append(deltas)
    print("  rms_after=%-7s %s" % (mode, " ".join("%.4g" % v for v in np.mean(np.array(rows), axis=0))))

print()
print("GRADIENT: spectral norm of d(sum of final node states)/d(initial node states) through 8 SHARED rounds")
for scheme in ("torch_default", "he_normal", "over_large"):
    for mode in ("none", "input", "output"):
        cells = []
        for name, (n, edges) in SHAPES.items():
            adj = adjof(n, edges)
            vals = []
            for seed in range(2):
                rng = np.random.default_rng(seed)
                feats = rng.normal(0, 1, (n, FEATURES))
                vals.append(jacnorm(feats, adj, make_weights(np.random.default_rng(seed + 5000), scheme), rounds=8, mode=mode))
            cells.append("%s %.4g" % (name, float(np.mean(vals))))
        print("  %-13s rms_after=%-7s %s" % (scheme, mode, " | ".join(cells)))
