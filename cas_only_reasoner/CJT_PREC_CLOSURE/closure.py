"""CJT PRECEDENCE CLOSURE PACKAGE -- $0, local CPU, numpy only. No GPU, no neural training.

Closes the four holes the fresh GLM audit found in the precedence-chain finding, per owner
ruling 2026-09-02. Every conclusion is DERIVED from the number printed above it.

  C1  RE-RUN AT THE CORRECT ARITY. The registered anchor is P > C > E > O -- FOUR domains.
      The committed test used K = 5. Re-run at K = 4: all 23 relabellings against the full
      registered compensation groups, with per-relabelling minimum and maximum.

  C2  REPLACE THE COIN FLIP WITH REAL READERS. My committed "free lunch" test measured
      NOTHING -- it compared RNG.integers(...) == cause (random guessing) against
      cause == cause (a tautology). The device was never read. This is the exact defect this
      program keeps catching in others, and I shipped it. Replaced here with five real readers
      on disjoint fit / held-out splits.

  C3  QUANTIFIER TEST. Is "not absorbed FOR ALL PARAMETERS" true? One structural counterexample
      settles it.

  C4  K SWEEP. Does the effect depend on arity or on capacity?

Run:  python closure.py
"""
import itertools

import numpy as np

RNG = np.random.default_rng(20260902)
DE, H = 4, 6


def bar(t=""):
    print("=" * 78)
    if t:
        print(t)
        print("=" * 78)


# ------------------------------------------------------------------ architecture
def make(K, rng, u_scale=0.5):
    return ([rng.normal(0, .5, (DE, H)) for _ in range(K)],
            [rng.normal(0, u_scale, (H, H)) for _ in range(K)],
            [rng.normal(0, .1, H) for _ in range(K)],
            rng.normal(0, .5, (H, K)))


def chain(p, E, assign):
    W, U, b, Rd = p
    h = np.zeros(H)
    for k in range(len(assign)):
        h = np.tanh(E[assign[k]] @ W[k] + U[k] @ h + b[k])
    return h @ Rd


def flat(p, E, assign):
    W, U, b, Rd = p
    return sum(np.tanh(E[assign[k]] @ W[k] + b[k]) for k in range(len(assign))) @ Rd


def relabel_params(p, sigma, signs=None):
    W, U, b, Rd = p
    K = len(W)
    sg = np.ones(K) if signs is None else signs
    return ([W[sigma[k]] * sg[k] for k in range(K)],
            [U[sigma[k]] * sg[k] for k in range(K)],
            [b[sigma[k]] * sg[k] for k in range(K)], Rd)


def absorption(K, fwd, p, E, signed=False):
    """For every non-identity relabelling, the attacker's BEST compensating transformation."""
    ident = list(range(K))
    perms = list(itertools.permutations(range(K)))
    signsets = [np.array(s, dtype=float) for s in itertools.product([1., -1.], repeat=K)] \
        if signed else [np.ones(K)]
    out = {}
    for perm in perms:
        if list(perm) == ident:
            continue
        tgt = fwd(p, E, list(perm))
        best = np.inf
        for sig in perms:
            for sg in signsets:
                best = min(best, float(np.max(np.abs(tgt - fwd(relabel_params(p, list(sig), sg),
                                                               E, ident)))))
        out[perm] = best
    return out


# ================================================================== C1
bar("C1  RE-RUN AT THE REGISTERED ARITY K = 4  (P > C > E > O)")
K = 4
p4 = make(K, RNG)
E4 = RNG.normal(0, 1, (K, DE))
for label, signed, n in (("permutations", False, 24), ("SIGNED permutations", True, 24 * 16)):
    ch = absorption(K, chain, p4, E4, signed)
    fl = absorption(K, flat, p4, E4, signed)
    cv, fv = np.array(list(ch.values())), np.array(list(fl.values()))
    absorbed = int((cv < 1e-10).sum())
    print(f"  over {len(ch)} relabellings x {n} {label}:")
    print(f"    PRECEDENCE  min {cv.min():.4e}   max {cv.max():.4e}   "
          f"absorbed(<1e-10) {absorbed}/{len(cv)}")
    print(f"    FLAT ctrl   min {fv.min():.4e}   max {fv.max():.4e}   "
          f"absorbed(<1e-10) {int((fv < 1e-10).sum())}/{len(fv)}")
print()
print("  Per-relabelling residuals, PRECEDENCE, signed group:")
ch = absorption(K, chain, p4, E4, True)
for perm, r in sorted(ch.items(), key=lambda kv: kv[1]):
    print(f"    {perm}  {r:.6e}{'   <-- ABSORBED' if r < 1e-10 else ''}")
cv = np.array(list(ch.values()))
print()
if cv.min() > 1e-10:
    print(f"  -> at K = 4 NO relabelling is absorbed; weakest is {cv.min():.4e}.")
    print("     The registered P > C > E > O arity reproduces the effect.")
else:
    print(f"  -> at K = 4, {int((cv < 1e-10).sum())} of {len(cv)} relabellings ARE absorbed.")
    print("     The claim is weaker at the registered arity than at K = 5.")

# ================================================================== C3
print()
bar('C3  QUANTIFIER TEST -- is "not absorbed FOR ALL PARAMETERS" true?')
print("  A chain is only a chain because U couples the stages. Set U = 0 and the recurrence")
print("  dies: h_k no longer depends on h_{k-1}, so the output depends ONLY on the module at")
print("  the LAST position. Every relabelling that fixes the last position must then be")
print("  absorbed EXACTLY. This is a structural counterexample, not a numerical accident.")
print()
p0 = make(K, RNG, u_scale=0.0)
ch0 = absorption(K, chain, p0, E4, False)
fixed_last = {perm: r for perm, r in ch0.items() if perm[K - 1] == K - 1}
vals = np.array(list(ch0.values()))
print(f"  U = 0, K = 4:  {int((vals < 1e-10).sum())}/{len(vals)} relabellings absorbed")
print(f"  of the {len(fixed_last)} relabellings that FIX the last position, "
      f"{sum(1 for r in fixed_last.values() if r < 1e-10)} are absorbed "
      f"(worst {max(fixed_last.values()):.4e})")
nontriv = float(np.max(np.abs(chain(p0, E4, list(range(K))))))
print(f"  and the model is NOT trivially degenerate: |baseline output|_max = {nontriv:.6f}")
print()
if sum(1 for r in fixed_last.values() if r < 1e-10) > 0 and nontriv > 1e-3:
    print("  -> COUNTEREXAMPLE FOUND. 'FOR ALL PARAMETERS' is FALSE.")
    print("     Only a GENERIC / NONDEGENERATE claim can be supported, and the exceptional set")
    print("     must at minimum exclude U = 0. The auditor's 'not absorbed, full stop' wording")
    print("     is NOT supportable; the owner's refusal to freeze it was correct.")
else:
    print("  -> no counterexample from U = 0 in this run.")

# ================================================================== C2
print()
bar('C2  REAL READERS -- replacing the coin flip I shipped')
print("  WHAT THE OLD TEST DID:  RNG.integers(...) == cause   vs   cause == cause")
print("  It never read the device. Both numbers were fabrications of the test harness.")
print()
print("  THE HONEST QUESTION: can a reader get the correct ACTION out of the device WITHOUT")
print("  learning the type->action map? The map is a SECRET PERMUTATION pi, unknown to the")
print("  architecture, so no device can know it a priori -- unless the builder BUILT it in.")
print()
NTR, NTE = 4000, 4000
pi = RNG.permutation(K)                      # secret, arbitrary type -> action map
print(f"  secret type->action map pi = {list(pi)}   (chance = {1 / K:.6f})")


def world(n):
    """Cause c = which type is faulty. That type's evidence row is shifted."""
    Es, cs = [], []
    for _ in range(n):
        c = int(RNG.integers(0, K))
        E = RNG.normal(0, 1, (K, DE))
        E[c] += 2.5
        Es.append(E)
        cs.append(c)
    return np.array(Es), np.array(cs)


Etr, ctr = world(NTR)
Ete, cte = world(NTE)
atr, ate = pi[ctr], pi[cte]

pdev = make(K, RNG)


def dev_out(E, masked_binding=None):
    if masked_binding is None:
        return chain(pdev, E, list(range(K)))
    # anchored singleton mask: position j may write ONLY action masked_binding[j]
    W, U, b, _ = pdev
    h = np.zeros(H)
    acts = np.zeros(K)
    for k in range(K):
        h = np.tanh(E[k] @ W[k] + U[k] @ h + b[k])
        acts[masked_binding[k]] = float(np.linalg.norm(E[k]))
    return acts


feat = {
    "raw evidence (the fair floor -- every arm sees this)": (
        np.array([E.ravel() for E in Etr]), np.array([E.ravel() for E in Ete])),
    "PRECEDENCE device output": (
        np.array([dev_out(E) for E in Etr]), np.array([dev_out(E) for E in Ete])),
    "MASK bound to the TRUE pi (the answer key)": (
        np.array([dev_out(E, pi) for E in Etr]), np.array([dev_out(E, pi) for E in Ete])),
    "MASK bound to a WRONG permutation": (
        np.array([dev_out(E, RNG.permutation(K)) for E in Etr]),
        np.array([dev_out(E, RNG.permutation(K)) for E in Ete])),
}


def zero_param(Xte):
    """ZERO-PARAMETER reader: argmax of the representation. No fitting at all."""
    return float((np.argmax(Xte, axis=1) == ate).mean()) if Xte.shape[1] == K else float("nan")


def linear(Xtr, Xte):
    A = np.c_[Xtr, np.ones(len(Xtr))]
    Y = np.eye(K)[atr]
    Wp, *_ = np.linalg.lstsq(A, Y, rcond=None)
    return float((np.argmax(np.c_[Xte, np.ones(len(Xte))] @ Wp, axis=1) == ate).mean())


def nearest(Xtr, Xte, m=800):
    idx = RNG.choice(len(Xtr), size=min(m, len(Xtr)), replace=False)
    A, ya = Xtr[idx], atr[idx]
    hit = 0
    for i in range(0, len(Xte), 500):
        blk = Xte[i:i + 500]
        d = ((blk[:, None, :] - A[None, :, :]) ** 2).sum(-1)
        hit += int((ya[np.argmin(d, axis=1)] == ate[i:i + 500]).sum())
    return hit / len(Xte)


def mlp(Xtr, Xte, hid=32, steps=400, lr=0.3):
    rng = np.random.default_rng(5)
    d = Xtr.shape[1]
    W1, b1 = rng.normal(0, .3, (d, hid)), np.zeros(hid)
    W2, b2 = rng.normal(0, .3, (hid, K)), np.zeros(K)
    Y = np.eye(K)[atr]
    for _ in range(steps):
        z = np.tanh(Xtr @ W1 + b1)
        o = z @ W2 + b2
        e = np.exp(o - o.max(1, keepdims=True))
        pr = e / e.sum(1, keepdims=True)
        g = (pr - Y) / len(Xtr)
        gW2, gb2 = z.T @ g, g.sum(0)
        dz = (g @ W2.T) * (1 - z ** 2)
        W1 -= lr * (Xtr.T @ dz); b1 -= lr * dz.sum(0); W2 -= lr * gW2; b2 -= lr * gb2
    return float((np.argmax(np.tanh(Xte @ W1 + b1) @ W2 + b2, axis=1) == ate).mean())


def stump(Xtr, Xte):
    """Depth-2 decision tree, greedy, on the strongest two features."""
    best = (0, None)
    for f in range(Xtr.shape[1]):
        for t in np.percentile(Xtr[:, f], [25, 50, 75]):
            L, Rt = Xtr[:, f] <= t, Xtr[:, f] > t
            if L.sum() < 10 or Rt.sum() < 10:
                continue
            lc = np.bincount(atr[L], minlength=K).argmax()
            rc = np.bincount(atr[Rt], minlength=K).argmax()
            acc = ((atr[L] == lc).sum() + (atr[Rt] == rc).sum()) / len(atr)
            if acc > best[0]:
                best = (acc, (f, t, lc, rc))
    if best[1] is None:
        return float("nan")
    f, t, lc, rc = best[1]
    pred = np.where(Xte[:, f] <= t, lc, rc)
    return float((pred == ate).mean())


print()
print(f"  {'representation':<46}{'0-param':>9}{'linear':>9}{'MLP':>8}{'kNN':>8}{'tree':>8}")
res = {}
for name, (Xtr, Xte) in feat.items():
    row = (zero_param(Xte), linear(Xtr, Xte), mlp(Xtr, Xte), nearest(Xtr, Xte), stump(Xtr, Xte))
    res[name] = row
    print(f"  {name:<46}" + "".join(f"{v:>9.4f}" if v == v else f"{'n/a':>9}" for v in row))

print()
ch_z = res["PRECEDENCE device output"][0]
mk_z = res["MASK bound to the TRUE pi (the answer key)"][0]
wr_z = res["MASK bound to a WRONG permutation"][0]
print(f"  ZERO-PARAMETER reader is the free-lunch measure -- it is the only one that reads the")
print(f"  device WITHOUT learning the type->action map.")
print(f"    precedence {ch_z:.4f} | mask@true pi {mk_z:.4f} | mask@wrong pi {wr_z:.4f}"
      f" | chance {1 / K:.4f}")
print()
if abs(ch_z - 1 / K) < 0.05 and mk_z > 0.9:
    print("  -> MEASURED, NOT ASSERTED. The precedence device hands a zero-parameter reader")
    print("     nothing above chance, while a mask bound to the true map hands over the answer.")
    print("     AND NOTE what the mask really is: it is an answer key ONLY when its binding is")
    print("     CHOSEN TO MATCH the true map. Bound to a wrong permutation it scores"
          f" {wr_z:.4f}.")
    print("     That is precisely the 'handing CAS the answer key' the fairness rule forbids:")
    print("     the builder picks the binding.")
else:
    print(f"  -> NOT the expected pattern (precedence {ch_z:.4f} vs chance {1 / K:.4f},")
    print(f"     mask {mk_z:.4f}). Do not adopt the free-lunch claim on this run.")
print()
print("  The FITTED readers measure a DIFFERENT thing -- whether the representation is")
print("  decodable once you are allowed to learn. High numbers there are expected and are NOT")
print("  a free lunch, because every arm may learn. Reported for completeness, not as evidence.")

# ================================================================== C4
print()
bar("C4  DOES THE EFFECT DEPEND ON ARITY OR ON CAPACITY?")
print("     K   relabellings   precedence min   flat min      absorbed/total")
for Kx in (2, 3, 4, 5):
    rng = np.random.default_rng(1000 + Kx)
    px, Ex = make(Kx, rng), rng.normal(0, 1, (Kx, DE))
    c = np.array(list(absorption(Kx, chain, px, Ex, False).values()))
    f = np.array(list(absorption(Kx, flat, px, Ex, False).values()))
    print(f"  {Kx:4d}   {len(c):12d}   {c.min():14.4e}   {f.min():.4e}   "
          f"{int((c < 1e-10).sum())}/{len(c)}")
print()
print("  If the precedence minimum stays far from zero as K shrinks while the flat control")
print("  stays at zero, the effect is topological, not a capacity artefact.")
