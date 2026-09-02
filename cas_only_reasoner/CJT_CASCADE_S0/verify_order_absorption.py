"""Is a 'shuffle the CAS stage ordering and retrain' control available in the cascade lane?

This is the D0 question, transplanted. D0 died because D5_CAS_TYPES_SHUFFLED turned out to be
EXACTLY D4_CAS_TYPED_REPAIR under a compensating parameter permutation (worst residual
0.0000e+00 over all 720 permutations of 6 channels). The owner then RETIRED
label-shuffle-after-retraining as a control for symmetric architectures.

The cascade lane's only CAS-specific content is WHICH STAGE RUNS FIRST. If a generic learned
cascade can reach the CAS-ordered cascade's function by indexing its own stages differently,
then ordering is a coordinate choice, the retirement binds here, and no D5-class control exists.

Measured on the COMMITTED construction -- Basis(12, 12, 3, 4) from CJT_OHM_0R/ohm0r.py -- not on
a reconstruction. (Reconstructing rather than using the committed object is how a mismatched
basis crept into my first pass at the span gate.)

Every conclusion below is DERIVED from the number printed above it, never hard-coded.

Run:  python verify_order_absorption.py
Cost: $0, local CPU, numpy only. No GPU, no training, no network.
"""
import itertools
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "CJT_OHM_0R"))
import ohm0r as M  # noqa: E402

RNG = M.RNG
B = M.Basis(12, 12, 3, 4)
N = B.n

print("=" * 78)
print("Is a shuffle-the-CAS-order control available in the cascade lane?")
print("=" * 78)
print(f"  committed construction: Basis(12, 12, 3, 4), s = {B.s}, n = {N} stages")
print()
print("  CAS arm     : runs the stages in the order CAS prescribes.")
print("  GENERIC arm : same family, but its LEARNED stages happen to sit at other indices.")
print("  If the generic arm reproduces the CAS arm exactly, ordering is a COORDINATE CHOICE.")
print()


def cascade(basis, alpha, x, order):
    I = np.eye(basis.W0.shape[0])
    Mx = I
    for j in order:
        Mx = (I + basis.s * alpha[j] * basis.dW(j)) @ Mx
    return (Mx @ basis.W0) @ x


class Relabelled:
    """The generic arm: identical class, stages permuted -- what gradient descent may find."""

    def __init__(self, b, perm):
        self.W0, self.s, self.n = b.W0, b.s, b.n
        self._d = [b.dW(perm[k]) for k in range(b.n)]

    def dW(self, j):
        return self._d[j]


worst = 0.0
count = 0
for perm in itertools.permutations(range(N)):
    count += 1
    x = RNG.normal(0, 1, B.W0.shape[1])
    alpha = RNG.dirichlet(np.ones(N))
    cas = cascade(B, alpha, x, perm)
    gen = cascade(Relabelled(B, perm), np.array([alpha[perm[k]] for k in range(N)]), x, range(N))
    worst = max(worst, float(np.max(np.abs(cas - gen))))

print(f"  enumerated all {count} orderings of {N} stages  (expected {math.factorial(N)})")
print(f"  worst |CAS_ordered - generic_relabelled| = {worst:.4e}")
print()
if worst < 1e-12:
    print("  -> ABSORBED EXACTLY. The generic arm reaches the CAS arm's function for free by")
    print("     indexing its own stages differently. Stage ordering is a SYMMETRY of the model")
    print("     family, not a mechanism.")
    print()
    print("     CONSEQUENCES:")
    print("       1. 'Shuffle the CAS order and retrain' is VACUOUS here, exactly as D5 was in D0.")
    print("       2. The owner's retirement of label-shuffle-after-retraining for symmetric")
    print("          architectures BINDS in this lane.")
    print("       3. Any registered status requiring 'destroyed by shuffling the CAS order' is")
    print("          UNREACHABLE BY CONSTRUCTION -- a necessary conjunct that is identically false.")
    print("       4. No D5-class causal control is available, so no CAS-specific claim is")
    print("          available from this design.")
else:
    print(f"  -> NOT absorbed at residual {worst:.4e}. The two arms are distinguishable, and a")
    print("     shuffle control MIGHT be valid here. Investigate before concluding either way.")
