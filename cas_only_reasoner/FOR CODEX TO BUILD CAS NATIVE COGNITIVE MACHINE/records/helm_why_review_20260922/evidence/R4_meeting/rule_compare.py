# R4 meeting: the frozen grader's per-seed rule vs trusted_rescore's per-seed rule, re-implemented
# from evaluate_gates.py:283-287,316-318 (ALPHA = 1/100 at :112) and trusted_rescore.py:62,437.
# kinds/worlds conditions are identical in both, so only (b, c) is enumerated. Population n = 18.
from fractions import Fraction
from math import comb
ALPHA = Fraction(1, 100)
def tail(b, n):
    return Fraction(1) if n == 0 else Fraction(sum(comb(n, k) for k in range(b, n + 1)), 2 ** n)
grader = lambda b, c: b > c and tail(b, b + c) <= ALPHA
rescore = lambda b, c: b >= 7 and c == 0
g_only, r_only = [], []
for b in range(0, 19):
    for c in range(0, 19 - b):
        if grader(b, c) and not rescore(b, c): g_only.append((b, c))
        if rescore(b, c) and not grader(b, c): r_only.append((b, c))
print("grader passes, rescorer fails:", len(g_only), "cells; smallest per c:",
      {c: min(b for b, cc in g_only if cc == c) for c in sorted({c for _, c in g_only})})
print("rescorer passes, grader fails:", len(r_only), r_only)
print("Helm 2.0 seeds: (11,1) grader", grader(11, 1), "rescore", rescore(11, 1), "| (12,0)", grader(12, 0), rescore(12, 0), "| (7,1)", grader(7, 1), rescore(7, 1))
