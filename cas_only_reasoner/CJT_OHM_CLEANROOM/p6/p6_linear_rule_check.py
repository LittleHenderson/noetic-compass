"""P6 mechanism-free LINEAR RULE check -- does a one-line least-squares reader on the raw evidence
match or beat the trained chain arms on genuinely held-out data?

Motivation: a P6 lens review reported that ordinary least squares on the flattened 20-dimensional
evidence reaches about 0.71 held-out in world (a), above every chain arm's held-out accuracy
(0.61-0.69). This script re-measures that claim from the committed world functions with the same
seeds as p6_heldout_repro.py, and adds the majority-class floor. No training of the arms, no
tuning, numpy only, $0, seconds.
"""
import hashlib
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
COMMITTED = HERE.parent.parent / "CJT_PREC_CLOSURE" / "p6_order_test.py"
PINNED = "07e824e242968c11440c4cc3d256bb518cf5579416fc4d848bf3004cc8baa8dd"
raw = COMMITTED.read_bytes().replace(b"\r\n", b"\n")
if hashlib.sha256(raw).hexdigest() != PINNED:
    sys.exit("REFUSED: committed script digest mismatch")
ns = {}
exec(compile(raw.decode().split('print("=" * 78)')[0], str(COMMITTED), "exec"), ns)
K, DE, H, NCLS, NTR, NTE, SEEDS = (ns[k] for k in ("K", "DE", "H", "NCLS", "NTR", "NTE", "SEEDS"))
CAS, REV = ns["CAS_ORDER"], ns["REVERSED"]
HELDOUT_SEED_BASE = 500000


def params_chain(r):
    A = [r.normal(0, .8, (DE, H)) for _ in range(K)]
    B = [r.normal(0, .8, (H, H)) for _ in range(K)]
    return A, B, r.normal(0, .8, (H, NCLS))


def sample_fixed(P, r, n, order):
    A, B, C = P
    E = r.normal(0, 1, (n, K, DE))
    s = np.zeros((n, H))
    for j in range(K):
        s = np.tanh(E[:, order[j], :] @ A[j] + s @ B[j].T)
    return E, np.argmax(s @ C, axis=1)


def sample_random(P, r, n):
    A, B, C = P
    E = r.normal(0, 1, (n, K, DE))
    y = np.empty(n, dtype=int)
    for i in range(n):
        o = r.permutation(K)
        s = np.zeros(H)
        for j in range(K):
            s = np.tanh(E[i, o[j], :] @ A[j] + B[j] @ s)
        y[i] = int(np.argmax(s @ C))
    return E, y


def params_bag(r):
    return [r.normal(0, .8, (DE, H)) for _ in range(K)], r.normal(0, .8, (H, NCLS))


def sample_bag(P, r, n):
    A, C = P
    E = r.normal(0, 1, (n, K, DE))
    s = sum(np.tanh(E[:, t, :] @ A[t]) for t in range(K))
    return E, np.argmax(s @ C, axis=1)


CONDS = [
    ("(a) world = CAS order", params_chain, lambda P, r, n: sample_fixed(P, r, n, CAS),
     lambda r, n: ns["make_world"](r, CAS, n)),
    ("(c) world = REVERSED", params_chain, lambda P, r, n: sample_fixed(P, r, n, REV),
     lambda r, n: ns["make_world"](r, REV, n)),
    ("(b) world = RANDOM per item", params_chain, sample_random, ns["make_world_random_order"]),
    ("(neg) NO order structure", params_bag, sample_bag, ns["make_world_no_structure"]),
]


def ols_fit_predict(Etr, ytr, Ete):
    X = np.hstack([Etr.reshape(len(Etr), -1), np.ones((len(Etr), 1))])
    Y = np.eye(NCLS)[ytr]
    W, *_ = np.linalg.lstsq(X, Y, rcond=None)
    Xt = np.hstack([Ete.reshape(len(Ete), -1), np.ones((len(Ete), 1))])
    return np.argmax(X @ W, axis=1), np.argmax(Xt @ W, axis=1)


print("P6 LINEAR-RULE CHECK  (least squares on the flattened %d-dim evidence + bias; %d parameters)"
      % (K * DE, (K * DE + 1) * NCLS))
print("  same train draws as the committed script (asserted), held-out seed stream %d+sd\n" % HELDOUT_SEED_BASE)
print("  %-28s %10s %10s %12s %12s" % ("condition", "OLS train", "OLS held", "majority tr", "majority he"))
for name, pf, sf, cf in CONDS:
    tr, he, mtr, mhe = [], [], [], []
    for sd in range(SEEDS):
        r = np.random.default_rng(1000 + sd)
        P = pf(r)
        Etr, ytr = sf(P, r, NTR)
        Ec, yc = cf(np.random.default_rng(1000 + sd), NTR)
        assert np.array_equal(Etr, Ec) and np.array_equal(ytr, yc), "train draw differs from committed"
        Ete, yte = sf(P, np.random.default_rng(HELDOUT_SEED_BASE + sd), NTE)
        ptr, pte = ols_fit_predict(Etr, ytr, Ete)
        tr.append((ptr == ytr).mean())
        he.append((pte == yte).mean())
        maj = np.bincount(ytr, minlength=NCLS).argmax()
        mtr.append((ytr == maj).mean())
        mhe.append((yte == maj).mean())
    print("  %-28s %10.4f %10.4f %12.4f %12.4f   (held sd %.4f)"
          % (name, np.mean(tr), np.mean(he), np.mean(mtr), np.mean(mhe), np.std(he, ddof=1)))
print("\n  Reference held-out means from p6_heldout_repro_stdout.txt:")
print("    (a) best chain 0.6868, bag 0.6875 | (c) best chain 0.6739, bag 0.6857 |"
      " (b) best chain 0.3775, bag 0.4219 | (neg) best chain 0.7167, bag 0.8548")
