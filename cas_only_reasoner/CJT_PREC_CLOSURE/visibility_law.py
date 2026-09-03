"""Can the two counterexample families be replaced by ONE precise law?

Both known counterexamples to universal non-absorption look different but may be the same
thing. U = 0 kills the recurrence so only the last position reaches the output. W_k = 0 makes
position k type-blind. In BOTH cases the absorbed relabellings were exactly those permuting
positions whose evidence never reaches the output.

  CONJECTURED VISIBILITY LAW
      Call position k VISIBLE if changing the evidence of the type sitting there changes the
      output. Then a relabelling sigma is ABSORBED if and only if sigma FIXES EVERY VISIBLE
      POSITION.

If this holds it replaces a proof sketch with six gaps by one statement that predicts the
exceptional set exactly -- which is far cheaper for a referee to check than a sketch.

The law is FALSIFIABLE and this script tries hard to falsify it, on seven constructions
including ones neither counterexample family covers (a severed mid-chain link, a readout that
kills the signal, saturated biases, and generic parameters).

CONTROL DISCIPLINE: visibility is measured through the SAME forward function used for the
absorption test, and a POSITIVE control (all positions visible => nothing absorbed) and a
NEGATIVE control (no positions visible => everything absorbed) must both behave, or no verdict
is printed.

Run:  python visibility_law.py     Cost: $0, local CPU, numpy.
"""
import itertools

import numpy as np

K, DE, H, ACT = 4, 4, 6, 4
PERMS = list(itertools.permutations(range(K)))
IDENT = tuple(range(K))
PROBES = [np.random.default_rng(500 + i).normal(0, 1, (K, DE)) for i in range(8)]


def chain(p, E, assign):
    W, U, b, Rd = p
    h = np.zeros(H)
    for k in range(K):
        h = np.tanh(E[assign[k]] @ W[k] + U[k] @ h + b[k])
    return h @ Rd


def relab(p, sig):
    W, U, b, Rd = p
    return ([W[sig[k]] for k in range(K)], [U[sig[k]] for k in range(K)],
            [b[sig[k]] for k in range(K)], Rd)


def visible(p):
    """A position is VISIBLE if perturbing the evidence that enters there moves the output.
    Measured through the SAME chain() the absorption test uses."""
    vis = []
    rng = np.random.default_rng(31337)
    for k in range(K):
        moved = 0.0
        for E in PROBES:
            for _ in range(6):
                E2 = E.copy()
                E2[IDENT[k]] = E2[IDENT[k]] + rng.normal(0, 1.5, DE)
                moved = max(moved, float(np.max(np.abs(
                    chain(p, E, list(IDENT)) - chain(p, E2, list(IDENT))))))
        if moved > 1e-9:
            vis.append(k)
    return vis


def absorbed_set(p):
    out = []
    for perm in PERMS:
        if perm == IDENT:
            continue
        best = min(max(float(np.max(np.abs(chain(p, E, list(perm))
                                           - chain(relab(p, list(sig)), E, list(IDENT)))))
                       for E in PROBES) for sig in PERMS)
        if best < 1e-12:
            out.append(perm)
    return sorted(out)


def predict(vis):
    """The law: sigma is absorbed iff it fixes every VISIBLE position."""
    return sorted(perm for perm in PERMS if perm != IDENT and all(perm[k] == k for k in vis))


def build(name, rng, mut):
    W = [rng.normal(0, .5, (DE, H)) for _ in range(K)]
    U = [rng.normal(0, .5, (H, H)) for _ in range(K)]
    b = [rng.normal(0, .1, H) for _ in range(K)]
    Rd = rng.normal(0, .5, (H, ACT))
    p = mut([W, U, b, Rd])
    return name, (p[0], p[1], p[2], p[3])


def sever_mid(p):
    p[1][2] = np.zeros((H, H))          # cut the link INTO position 2: 0 and 1 cannot reach out
    return p


def kill_readout(p):
    p[3] = np.zeros((H, ACT))           # nothing reaches the output at all
    return p


def saturate(p):
    for k in range(K):
        p[2][k] = np.full(H, 60.0)      # biases so large every tanh pins at +1
        p[0][k] = p[0][k] * 1e-6
        p[1][k] = p[1][k] * 1e-6
    return p


CASES = [
    build("generic (no degeneracy)", np.random.default_rng(1), lambda p: p),
    build("W_0 = 0", np.random.default_rng(2),
          lambda p: (p.__setitem__(0, [np.zeros((DE, H))] + p[0][1:]) or p)),
    build("W_0 = W_1 = W_2 = 0", np.random.default_rng(3),
          lambda p: (p.__setitem__(0, [np.zeros((DE, H))] * 3 + p[0][3:]) or p)),
    build("U = 0 everywhere", np.random.default_rng(4),
          lambda p: (p.__setitem__(1, [np.zeros((H, H))] * K) or p)),
    build("U_2 = 0  (severed mid-chain)", np.random.default_rng(5), sever_mid),
    build("Rd = 0  (readout killed)", np.random.default_rng(6), kill_readout),
    build("saturated biases", np.random.default_rng(7), saturate),
]

print("=" * 78)
print("VISIBILITY LAW:  sigma is ABSORBED  <=>  sigma FIXES EVERY VISIBLE POSITION")
print("=" * 78)
print("  Seven constructions, including three that neither known counterexample family covers.")
print("  Visibility is measured through the SAME forward function as the absorption test.\n")

rows = []
for name, p in CASES:
    vis = visible(p)
    got = absorbed_set(p)
    pred = predict(vis)
    ok = got == pred
    rows.append((name, vis, len(got), len(pred), ok))
    print(f"  {name}")
    print(f"    visible positions   = {vis}")
    print(f"    absorbed (measured) = {len(got):2d} of 23")
    print(f"    absorbed (LAW says) = {len(pred):2d} of 23      MATCH = {ok}")
    if not ok:
        print(f"      measured  {got}")
        print(f"      predicted {pred}")
    print()

# ---- controls, through the same code path -------------------------------------
pos_name, pos_vis, pos_got, pos_pred, _ = rows[0]          # generic: all visible
neg = [r for r in rows if r[1] == []]                       # readout killed: none visible
pos_ok = pos_vis == [0, 1, 2, 3] and pos_got == 0
neg_ok = bool(neg) and neg[0][2] == 23

print("=" * 78)
print("  CONTROL CHECK -- no verdict is printed unless both behave:")
print(f"    POSITIVE  generic params: all 4 positions visible and 0 absorbed   "
      f"{'PASS' if pos_ok else 'FAIL'}")
print(f"    NEGATIVE  readout killed: 0 positions visible and all 23 absorbed  "
      f"{'PASS' if neg_ok else 'FAIL'}")
print("=" * 78)
print()

if not (pos_ok and neg_ok):
    print("  CONTROLS FAILED -- NO VERDICT. The visibility probe or the absorption test is not")
    print("  behaving on the two cases whose answers are known a priori, so nothing below the")
    print("  controls can be trusted. Fix the probe before reading anything into the table.")
else:
    hits = sum(1 for r in rows if r[4])
    print(f"  the law predicted the absorbed set exactly in {hits} of {len(rows)} constructions")
    if hits == len(rows):
        print()
        print("  -> NOT FALSIFIED by any of the seven, including the three the known")
        print("     counterexample families do not cover. This replaces two ad-hoc")
        print("     counterexample families with ONE statement, and it makes the exceptional")
        print("     set explicit:")
        print()
        print("       EXCEPTIONAL SET = { theta : some position is INVISIBLE }")
        print()
        print("     A referee now has to check one law and one definition, not a sketch with")
        print("     six gaps. THIS IS NOT A PROOF -- it is a sharpened, falsifiable claim that")
        print("     survived seven attempts to break it.")
    else:
        print()
        print("  -> FALSIFIED. The law does NOT capture the exceptional set. The rows marked")
        print("     MATCH = False above are counterexamples to the law itself, and the two")
        print("     original families remain the best description.")
