"""Owner audit item 9: can a MORE GENERAL transformation than a parameter permutation absorb
the precedence chain? My original test searched permutations only. That is the weakest
absorption group, so passing it proves less than I implied.

tanh is ODD, so the transformations T satisfying tanh(Tx) = T tanh(x) are exactly the SIGNED
permutations -- a group 2^K times larger than the permutations. That is the correct natural
absorption group for this architecture, and it is what an attacker actually has.

This test enlarges the search from 120 permutations to 120 * 2^5 = 3840 signed permutations.

Run:  python extend_absorption_test.py     Cost: $0, local CPU, numpy. No GPU, no training.
"""
import itertools
import numpy as np

RNG = np.random.default_rng(20260902)
K, DE, H, ACT = 5, 4, 6, 5


def make():
    return ([RNG.normal(0, .5, (DE, H)) for _ in range(K)],
            [RNG.normal(0, .5, (H, H)) for _ in range(K)],
            [RNG.normal(0, .1, H) for _ in range(K)],
            RNG.normal(0, .5, (H, ACT)))


def chain(p, E, assign):
    W, U, b, Rd = p
    h = np.zeros(H)
    for k in range(K):
        h = np.tanh(E[assign[k]] @ W[k] + U[k] @ h + b[k])
    return h @ Rd


def flat(p, E, assign):
    W, U, b, Rd = p
    return sum(np.tanh(E[assign[k]] @ W[k] + b[k]) for k in range(K)) @ Rd


def signed_permute(p, sigma, signs):
    """Relabel modules AND flip signs -- the full group that commutes with an odd nonlinearity."""
    W, U, b, Rd = p
    return ([W[sigma[k]] * signs[k] for k in range(K)],
            [U[sigma[k]] * signs[k] for k in range(K)],
            [b[sigma[k]] * signs[k] for k in range(K)],
            Rd)


p = make()
E = RNG.normal(0, 1, (K, DE))
ident = list(range(K))
SIGNS = [np.array(s, dtype=float).reshape(-1, 1) * 0 + 1 for s in [()]]  # placeholder
sign_sets = [np.array(s) for s in itertools.product([1.0, -1.0], repeat=K)]

for name, fwd in (("PRECEDENCE CHAIN", chain), ("FLAT (D0/S0 shape)", flat)):
    best_overall = np.inf
    for perm in itertools.permutations(range(K)):
        if list(perm) == ident:
            continue
        target = fwd(p, E, list(perm))
        best = np.inf
        for sig in itertools.permutations(range(K)):
            for sg in sign_sets:
                cand = fwd(signed_permute(p, list(sig), sg), E, ident)
                best = min(best, float(np.max(np.abs(target - cand))))
        best_overall = min(best_overall, best)
    n = 120 * len(sign_sets)
    print(f"  {name:20s} best residual over 119 relabelings x {n} SIGNED permutations "
          f"= {best_overall:.4e}")

print()
print("  The permutation-only test gave chain 4.6108e-02, flat 0.0000e+00.")
print("  If the chain figure survives the LARGER group, the non-equivariance is more robust")
print("  than my original test showed. If it collapses, my claim was overstated.")
