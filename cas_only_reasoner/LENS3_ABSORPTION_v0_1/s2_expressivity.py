"""LENS 3 (a)(b): ABSORPTION BY RELABELLING vs EXPRESSIVITY.

Absorption  : does a PERMUTATION of the existing modules reproduce the relabelled model?
Expressivity: can FRESH parameters W',U',b',Rd' of the SAME architecture reproduce the
              relabelled model as a function of E?

Controls registered BEFORE the run:
  FLOOR-ID   target = the baseline model itself           -> expect optimizer floor
  FLOOR-RAND target = a different random model, same class-> expect optimizer floor
  OOC-FLAT   target = the FLAT (no-U, summed) model       -> known out-of-chain-class-ish
  OOC-MLP    target = a random 2-layer MLP on flat(E)     -> genuinely out of class
Any residual must be read against FLOOR-ID / FLOOR-RAND, never against 0.
"""
import itertools, sys, numpy as np
from core import *

rng = np.random.default_rng(11)
NTR, NTE = 2000, 4000
Etr = rng.normal(size=(NTR, K, DE))
Ete = rng.normal(size=(NTE, K, DE))

P = rand_params(42)                      # the model under test
perms = list(itertools.permutations(range(K)))


def fit(target_tr, target_te, Hfit=H, steps=12000, restarts=4, seed0=0, tag=""):
    """Adam fit of fresh W',U',b',Rd' (hidden width Hfit) to match target on Etr."""
    best = (np.inf, np.inf)
    for r in range(restarts):
        q = rand_params(1000 + seed0 + r, H=Hfit, scale=0.7)
        m = {k: np.zeros_like(v) for k, v in q.items()}
        v = {k: np.zeros_like(x) for k, x in q.items()}
        lr, b1, b2, eps = 3e-2, 0.9, 0.999, 1e-8
        for t in range(1, steps + 1):
            if t == int(steps * 0.6):
                lr = 6e-3
            if t == int(steps * 0.85):
                lr = 1e-3
            _, g = grads(q, Etr, target_tr)
            for key in q:
                m[key] = b1 * m[key] + (1 - b1) * g[key]
                v[key] = b2 * v[key] + (1 - b2) * g[key] ** 2
                q[key] -= lr * (m[key] / (1 - b1 ** t)) / (np.sqrt(v[key] / (1 - b2 ** t)) + eps)
        rtr = rel_rmse(forward(q, Etr), target_tr)
        rte = rel_rmse(forward(q, Ete), target_te)
        if rtr < best[0]:
            best = (rtr, rte)
    return best


def flat_forward(p, E, assign=None):
    Kk = p["W"].shape[0]
    if assign is None:
        assign = np.arange(Kk)
    tot = 0.0
    for k in range(Kk):
        tot = tot + np.tanh(E[:, assign[k], :] @ p["W"][k] + p["b"][k]) @ p["Rd"]
    return tot


def mlp(E):
    r = np.random.default_rng(99)
    A = r.normal(size=(K * DE, 16)); c = r.normal(size=16); B = r.normal(size=(16, ACT))
    X = E.reshape(E.shape[0], -1)
    return np.tanh(X @ A + c) @ B


steps = None
print(f"# Adam steps=12000, restarts=4, N_train={NTR}, N_heldout={NTE}, K={K} DE={DE} H={H} ACT={ACT}")
print(f"# metric = relative RMSE ||fit-target||_F / ||target||_F\n")

rows = []
print(f"{'target':<38} {'train rel':>12} {'heldout rel':>13}", flush=True)


def add(name, res):
    rows.append((name, res))
    print(f"{name:<38} {res[0]:12.4e} {res[1]:13.4e}", flush=True)


# ---- controls
add("FLOOR-ID   baseline model itself", fit(forward(P, Etr), forward(P, Ete), tag="id"))
P2 = rand_params(2024)
add("FLOOR-RAND other random in-class", fit(forward(P2, Etr), forward(P2, Ete), seed0=50))
add("OOC-FLAT   flat/no-U summed model", fit(flat_forward(P, Etr), flat_forward(P, Ete), seed0=100))
add("OOC-MLP    random 2-layer MLP", fit(mlp(Etr), mlp(Ete), seed0=150))

# ---- the real question: 5 relabelings incl. the transposition and the 5-cycle
test_pis = [(1, 0, 2, 3, 4), (0, 1, 2, 4, 3), (1, 2, 3, 4, 0), (4, 3, 2, 1, 0), (2, 0, 4, 1, 3)]
for i, pi in enumerate(test_pis):
    tt = forward(P, Etr, assign=np.array(pi))
    te = forward(P, Ete, assign=np.array(pi))
    add(f"RELABEL    pi={pi}", fit(tt, te, seed0=200 + 10 * i))

# ---- overparameterised: 4x hidden width, on the hardest relabelling
pi = (1, 2, 3, 4, 0)
tt = forward(P, Etr, assign=np.array(pi)); te = forward(P, Ete, assign=np.array(pi))
add(f"RELABEL 4xH pi={pi}", fit(tt, te, Hfit=4 * H, seed0=400))
add("FLOOR-ID 4xH baseline itself", fit(forward(P, Etr), forward(P, Ete), Hfit=4 * H, seed0=450))

print("done")
