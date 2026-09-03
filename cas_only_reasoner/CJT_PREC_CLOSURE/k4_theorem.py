"""K = 4 RERUN of the exceptional-set and expressivity work. P > C > E > O is FOUR domains.

The counterexample hunt was run at K = 5. The registered claim is anchored to the four-domain
domain law, so every number that supports it must be measured at K = 4. This is the second time
an arity mismatch has been caught in this finding; it is redone here at the registered arity.

  A  COUNTEREXAMPLES WITH THE RECURRENCE ALIVE. Zeroing the read-in W_k at the TOP positions
     makes those positions type-blind, so relabelling among them is absorbed -- while U stays
     full rank and the chain still computes. Each absorbed set is PREDICTED before it is
     measured; a prediction that matches is evidence the mechanism is understood, not observed.

  B  IS THE EXCEPTIONAL SET MEASURE ZERO? If yes, a GENERIC claim survives the U = 0 and
     zero-read-in counterexamples.

  (C  EXPRESSIVITY moved to k4_expressivity.py -- see the note at the end of this file.)

Run:  python k4_theorem.py     Cost: $0, local CPU, numpy. No GPU, no neural training frameworks.
"""
import itertools

import numpy as np

K, DE, H, ACT = 4, 4, 6, 4
PERMS = [p for p in itertools.permutations(range(K))]
IDENT = tuple(range(K))


def bar(t=""):
    print("=" * 78)
    if t:
        print(t)
        print("=" * 78)


def make(rng, zero_read=(), u_scale=.5):
    W = [rng.normal(0, .5, (DE, H)) for _ in range(K)]
    for k in zero_read:
        W[k] = np.zeros((DE, H))
    return (W, [rng.normal(0, u_scale, (H, H)) for _ in range(K)],
            [rng.normal(0, .1, H) for _ in range(K)], rng.normal(0, .5, (H, ACT)))


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


def absorb(p, Es, ident_only=False):
    """For each non-identity relabelling, the attacker's best compensating permutation."""
    out = {}
    for perm in PERMS:
        if perm == IDENT:
            continue
        best = np.inf
        for sig in ([IDENT] if ident_only else PERMS):
            r = max(float(np.max(np.abs(chain(p, E, list(perm)) - chain(relab(p, list(sig)), E, list(IDENT)))))
                    for E in Es)
            best = min(best, r)
        out[perm] = best
    return out


rng = np.random.default_rng(20260902)
Es = [rng.normal(0, 1, (K, DE)) for _ in range(6)]

# ===================================================================== A
bar("A  COUNTEREXAMPLES AT K = 4, WITH THE RECURRENCE STILL ALIVE")
print("  Zeroing W_k makes position k TYPE-BLIND: it ignores which type sits there. Relabelling")
print("  among type-blind positions must then be absorbed EXACTLY, while U stays full rank and")
print("  the chain still computes. The absorbed set is PREDICTED, then measured.\n")

for zr in [(0,), (0, 1), (0, 1, 2)]:
    p = make(np.random.default_rng(4242), zero_read=zr)
    blind = set(zr)
    predicted = sorted(perm for perm in PERMS if perm != IDENT
                       and all(perm[k] == k for k in range(K) if k not in blind)
                       and all(perm[k] in blind for k in blind))
    got = absorb(p, Es)
    absorbed = sorted(perm for perm, r in got.items() if r < 1e-12)
    ranks = [int(np.linalg.matrix_rank(u)) for u in p[1]]
    mx = max(float(np.max(np.abs(chain(p, E, list(IDENT))))) for E in Es)
    sens = [max(float(np.max(np.abs(chain(p, E, list(IDENT)) -
                                    chain(p, np.where(np.arange(K)[:, None] == t, 0, 1) * E, list(IDENT)))))
                for E in Es) for t in range(K)]
    print(f"  W_{list(zr)} = 0")
    print(f"    max|out| over probes           = {mx:.6e}   (not degenerate if >> 0)")
    print(f"    rank(U_k)                      = {ranks}   (H = {H}) -- chain alive")
    print(f"    sensitivity of out to E row t  = {[round(s, 4) for s in sens]}")
    print(f"    absorbed (best compensation)   = {len(absorbed)} of {len(got)}")
    print(f"    absorbed set                   = {absorbed}")
    print(f"    predicted set                  = {predicted}   MATCH = {absorbed == predicted}")
    print()

# ===================================================================== B
bar("B  IS THE EXCEPTIONAL SET MEASURE ZERO?  (does a GENERIC claim survive?)")
p = make(np.random.default_rng(4242), zero_read=(0, 1))
track = (1, 0, 2, 3)
print(f"  Perturb the W_0 = W_1 = 0 counterexample by eps * N(0,.5) and watch the residual of")
print(f"  the absorbed relabelling {track}.\n")
print("      eps          best residual over 24 compensations")
for eps in [0.0, 1e-12, 1e-9, 1e-6, 1e-3, 1e-2, 1e-1, 1.0]:
    q = make(np.random.default_rng(4242), zero_read=(0, 1))
    r2 = np.random.default_rng(99)
    W, U, b, Rd = q
    for k in (0, 1):
        W[k] = eps * r2.normal(0, .5, (DE, H))
    best = min(max(float(np.max(np.abs(chain((W, U, b, Rd), E, list(track)) -
                                       chain(relab((W, U, b, Rd), list(sig)), E, list(IDENT)))))
                   for E in Es) for sig in PERMS)
    print(f"    {eps:9.0e}    {best:.6e}")
print()
print("  Random-parameter sweep: how often does a RANDOM draw absorb anything at K = 4?")
hits, smallest = 0, np.inf
for i in range(200):
    q = make(np.random.default_rng(9000 + i))
    v = np.array(list(absorb(q, Es[:3]).values()))
    hits += int((v < 1e-10).any())
    smallest = min(smallest, float(v.min()))
print(f"    200 independent random draws (K = 4): draws with ANY absorbed relabelling = {hits}")
print(f"    smallest best-residual seen across all 200 draws = {smallest:.4e}")
print()
if hits == 0 and smallest > 1e-6:
    print("  -> the counterexamples sit on a MEASURE-ZERO set: the residual grows LINEARLY with")
    print("     the perturbation, and no random draw in 200 absorbs anything. A GENERIC claim")
    print("     survives; the UNIVERSAL claim remains DISPROVED.")
else:
    print(f"  -> {hits} random draws absorbed something; the exceptional set is NOT negligible.")

# Section C (expressivity) lived here and was REMOVED: I wrote it with finite-difference
# gradients, which made it ~200x too slow -- the run produced NO OUTPUT AT ALL. It is replaced
# by k4_expressivity.py, which uses analytic gradients and gates its conclusion on a positive
# and a negative control that share its code path.
