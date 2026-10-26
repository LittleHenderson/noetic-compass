import itertools, numpy as np
from core import *

np.set_printoptions(precision=6, suppress=False)

# ---------- 0. gradient check (the fit is worthless if the gradient is wrong)
p = rand_params(0)
r = np.random.default_rng(1)
E = r.normal(size=(7, K, DE))
T = r.normal(size=(7, ACT))
loss, g = grads(p, E, T)
eps = 1e-6
worst = 0.0
for key in ["W", "U", "b", "Rd"]:
    A = p[key]
    idx = [tuple(np.unravel_index(i, A.shape)) for i in
           r.choice(A.size, size=min(12, A.size), replace=False)]
    for ix in idx:
        old = A[ix]
        A[ix] = old + eps
        lp = np.mean((forward(p, E) - T) ** 2)
        A[ix] = old - eps
        lm = np.mean((forward(p, E) - T) ** 2)
        A[ix] = old
        num = (lp - lm) / (2 * eps)
        worst = max(worst, abs(num - g[key][ix]) / (abs(num) + 1e-12))
print(f"GRADCHECK max rel err over 48 coords = {worst:.3e}")

# ---------- 1. anchor: absorption by MODULE-POSITION permutation
# baseline params, K=5 -> 119 non-identity relabelings x 120 module permutations
p = rand_params(42)
Eb = np.random.default_rng(7).normal(size=(512, K, DE))
base = forward(p, Eb)
print(f"baseline out rms = {np.sqrt(np.mean(base**2)):.6f}")

perms = list(itertools.permutations(range(K)))


def permute_modules(p, sig):
    """module at position k of new params := module from position sig[k]"""
    return dict(W=p["W"][list(sig)], U=p["U"][list(sig)], b=p["b"][list(sig)], Rd=p["Rd"])


best_overall = np.inf
best_rec = None
per_relab = []
for pi in perms[1:]:                      # 119 non-identity relabelings
    tgt = forward(p, Eb, assign=np.array(pi))
    bb = np.inf
    for sig in perms:                     # 120 module permutations
        q = permute_modules(p, sig)
        v = rel_rmse(forward(q, Eb), tgt)
        if v < bb:
            bb = v
            bs = sig
    per_relab.append(bb)
    if bb < best_overall:
        best_overall, best_rec = bb, (pi, bs)
print(f"ANCHOR  best rel residual over 119 relab x 120 module perms = {best_overall:.4e}")
print(f"        argmin relabel={best_rec[0]} moduleperm={best_rec[1]}")
print(f"        median over 119 relabelings                        = {np.median(per_relab):.4e}")
print(f"        max    over 119 relabelings                        = {np.max(per_relab):.4e}")

# ---------- 2. FLAT control: U removed, outputs summed
def flat_forward(p, E, assign=None):
    Kk = p["W"].shape[0]
    if assign is None:
        assign = np.arange(Kk)
    tot = 0.0
    for k in range(Kk):
        tot = tot + np.tanh(E[:, assign[k], :] @ p["W"][k] + p["b"][k]) @ p["Rd"]
    return tot

fbase = flat_forward(p, Eb)
bestf = np.inf
for pi in perms[1:]:
    tgt = flat_forward(p, Eb, assign=np.array(pi))
    for sig in perms:
        q = permute_modules(p, sig)
        v = rel_rmse(flat_forward(q, Eb), tgt)
        bestf = min(bestf, v)
print(f"FLAT control best rel residual (119 x 120)                 = {bestf:.4e}")
