"""EXPRESSIVITY at K = 4 -- the open half of audit item 9.

Non-absorption says no RELABELLING of the parameters reproduces the relabelled model. It does
NOT say the architecture cannot REPRESENT that function with freely fitted parameters. Only the
first was ever measured. This measures the second.

CONTROL DISCIPLINE (imposed after I shipped a fabricated measurement):
  No conclusion is printed unless BOTH controls behave, and both run through the SAME code path
  as the measurement itself:

    POSITIVE CONTROL  fitting the architecture to ITS OWN output must reach a LOW residual.
                      If the fitter cannot fit in-class targets, every other number is noise.
    NEGATIVE CONTROL  fitting a genuinely OUT-OF-CLASS target must reach a HIGH residual.
                      If it fits that too, the metric cannot discriminate anything.

  If either control fails, this script REFUSES to state a result. That is the exact failure
  mode that produced the earlier fabricated "free lunch" number: its control did not share a
  code path with the thing it was controlling, so neither could catch the other.

Run:  python k4_expressivity.py     Cost: $0, local CPU, numpy. No GPU, no ML frameworks.
"""
import numpy as np

K, DE, H, ACT = 4, 4, 6, 4
IDENT = list(range(K))


def make(rng):
    return ([rng.normal(0, .5, (DE, H)) for _ in range(K)],
            [rng.normal(0, .5, (H, H)) for _ in range(K)],
            [rng.normal(0, .1, H) for _ in range(K)],
            rng.normal(0, .5, (H, ACT)))


def fwd(p, Eb, assign):
    """Batched forward. Eb: (N, K, DE). Returns (N, ACT) and the cached activations."""
    W, U, b, Rd = p
    N = Eb.shape[0]
    h = np.zeros((N, H))
    hs = []
    for k in range(K):
        h = np.tanh(Eb[:, assign[k], :] @ W[k] + h @ U[k].T + b[k])
        hs.append(h)
    return h @ Rd, hs


def grads(p, Eb, assign, Y):
    """Analytic gradients. This is what makes the fit feasible; finite differences were not."""
    W, U, b, Rd = p
    N = Eb.shape[0]
    out, hs = fwd(p, Eb, assign)
    dout = 2.0 * (out - Y) / N
    gRd = hs[-1].T @ dout
    dh = dout @ Rd.T
    gW = [None] * K
    gU = [None] * K
    gb = [None] * K
    for k in range(K - 1, -1, -1):
        dz = dh * (1 - hs[k] ** 2)
        gW[k] = Eb[:, assign[k], :].T @ dz
        gb[k] = dz.sum(0)
        hprev = hs[k - 1] if k > 0 else np.zeros((N, H))
        gU[k] = dz.T @ hprev
        dh = dz @ U[k]
    return (gW, gU, gb, gRd), float(np.mean((out - Y) ** 2))


def fit(target, Etr, Ete, seed, steps=1500, restarts=3, lr=0.02):
    Ytr, Yte = target(Etr), target(Ete)
    best = np.inf
    for rs in range(restarts):
        p = make(np.random.default_rng(seed * 100 + rs))
        st = [[np.zeros_like(x) for x in grp] if isinstance(grp, list) else np.zeros_like(grp)
              for grp in p]
        m = [[np.zeros_like(x) for x in grp] if isinstance(grp, list) else np.zeros_like(grp)
             for grp in p]
        for t in range(1, steps + 1):
            g, _ = grads(p, Etr, IDENT, Ytr)
            for gi in range(4):
                if isinstance(p[gi], list):
                    for j in range(K):
                        m[gi][j] = .9 * m[gi][j] + .1 * g[gi][j]
                        st[gi][j] = .999 * st[gi][j] + .001 * g[gi][j] ** 2
                        p[gi][j] -= lr * (m[gi][j] / (1 - .9 ** t)) / (
                            np.sqrt(st[gi][j] / (1 - .999 ** t)) + 1e-8)
                else:
                    m[gi] = .9 * m[gi] + .1 * g[gi]
                    st[gi] = .999 * st[gi] + .001 * g[gi] ** 2
                    p[gi][:] = p[gi] - lr * (m[gi] / (1 - .9 ** t)) / (
                        np.sqrt(st[gi] / (1 - .999 ** t)) + 1e-8)
        pred, _ = fwd(p, Ete, IDENT)
        best = min(best, float(np.linalg.norm(pred - Yte) / np.linalg.norm(Yte)))
    return best


rng = np.random.default_rng(20260902)
Etr = rng.normal(0, 1, (3000, K, DE))
Ete = rng.normal(0, 1, (3000, K, DE))
base = make(np.random.default_rng(11))
other = make(np.random.default_rng(77))
mlpW1 = rng.normal(0, .5, (K * DE, 24))
mlpW2 = rng.normal(0, .5, (24, ACT))

print("=" * 78)
print("EXPRESSIVITY AT K = 4  -- can the architecture REPRESENT the relabelled function?")
print("=" * 78)
print(f"  fit: analytic gradients, Adam, 1500 steps x 3 restarts, {len(Etr)} train / {len(Ete)}")
print("  held out. Metric = relative RMSE on the HELD-OUT set.\n")

targets = [
    ("POS CTRL  the baseline model itself", lambda E: fwd(base, E, IDENT)[0], "pos"),
    ("POS CTRL  another random in-class model", lambda E: fwd(other, E, IDENT)[0], "pos"),
    ("NEG CTRL  random 2-layer MLP (out of class)",
     lambda E: np.tanh(E.reshape(len(E), -1) @ mlpW1) @ mlpW2, "neg"),
    ("NEG CTRL  flat / no-U summed model (out of class)",
     lambda E: sum(np.tanh(E[:, k, :] @ base[0][k] + base[2][k]) for k in range(K)) @ base[3],
     "neg"),
]
for pi in [(1, 0, 2, 3), (0, 1, 3, 2), (1, 2, 3, 0), (3, 2, 1, 0), (2, 0, 3, 1)]:
    targets.append((f"RELABEL   pi={pi}", lambda E, q=list(pi): fwd(base, E, q)[0], "test"))

res = {}
print(f"  {'target':<48}{'heldout rel RMSE':>18}")
for i, (name, fn, kind) in enumerate(targets):
    r = fit(fn, Etr, Ete, 30 + i)
    res[name] = (r, kind)
    print(f"  {name:<48}{r:>18.4e}")

pos = [v for v, k in res.values() if k == "pos"]
neg = [v for v, k in res.values() if k == "neg"]
tst = [v for v, k in res.values() if k == "test"]

print()
print("  CONTROL CHECK -- the conclusion is withheld unless both pass:")
pos_ok = max(pos) < 5e-2
neg_ok = min(neg) > 5e-2
print(f"    POSITIVE  worst in-class fit  = {max(pos):.4e}   must be < 5e-2   "
      f"{'PASS' if pos_ok else 'FAIL'}")
print(f"    NEGATIVE  best out-of-class   = {min(neg):.4e}   must be > 5e-2   "
      f"{'PASS' if neg_ok else 'FAIL'}")
print()

if not (pos_ok and neg_ok):
    print("  -> CONTROLS FAILED. NO RESULT IS STATED. The fitter cannot separate in-class from")
    print("     out-of-class targets at this budget, so the relabelled numbers mean nothing.")
    print("     Increase steps/restarts or reduce the problem before reading anything into them.")
else:
    print(f"    relabelled targets: min {min(tst):.4e}   max {max(tst):.4e}")
    ratio = min(tst) / max(pos)
    print(f"    weakest relabelled target is {ratio:.1f}x the worst in-class floor")
    print()
    if min(tst) > 10 * max(pos):
        print("  -> NOT EXPRESSIBLE AT MATCHED CAPACITY. Relabelled targets sit far above the")
        print("     in-class floor, in the same range as genuinely out-of-class targets.")
        print("     Non-equivariance is accompanied by non-expressibility AT THIS CAPACITY.")
    elif min(tst) < 3 * max(pos):
        print("  -> EXPRESSIBLE. The architecture CAN represent the relabelled function with")
        print("     freely fitted parameters, so non-equivariance does NOT separate the")
        print("     hypothesis classes. The precedence claim is much weaker than it looks.")
    else:
        print("  -> INTERMEDIATE and NOT DECISIVE. Do not report this as either result.")

print()
print("  SCOPE: matched capacity only. A WIDER model may represent the relabelled function.")
print("  That is NOT tested here and must not be inferred from these numbers.")
