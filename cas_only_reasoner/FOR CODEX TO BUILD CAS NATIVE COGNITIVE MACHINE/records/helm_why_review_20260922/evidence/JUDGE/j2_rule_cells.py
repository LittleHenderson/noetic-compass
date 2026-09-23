# JUDGE: compare frozen grader per-seed rule (b > c, exact one-sided binomial p <= 1/100) with the rescorer rule
# (b >= 7, c == 0), over b + c <= 18. Kinds/worlds conditions assumed equal for both. Pure Python.
from fractions import Fraction
from math import comb
def tail(b, n):
    return Fraction(sum(comb(n, k) for k in range(b, n + 1)), 2 ** n)
g_only, r_only = [], []
for b in range(0, 19):
    for c in range(0, 19 - b):
        g = b > c and tail(b, b + c) <= Fraction(1, 100)
        r = b >= 7 and c == 0
        if g and not r: g_only.append((b, c))
        if r and not g: r_only.append((b, c))
print('grader passes, rescorer fails:', len(g_only), g_only)
print('rescorer passes, grader fails:', len(r_only), r_only)
for b, c in ((7, 0), (7, 1), (9, 1), (10, 1), (11, 1), (12, 0)):
    print((b, c), tail(b, b + c), float(tail(b, b + c)))
