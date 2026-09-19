"""What does the relational gate need, and can it detect a real improvement?

Pure arithmetic, standard library only. $0. No torch, no material load.

The gate (owner-confirmed 2026-09-19): the label LEARNS_NEW_WORLDS requires, per seed, an exact one-sided
binomial test on DISCORDANT held-back relational questions with b > c and p <= 0.01, plus gains in at least 2
kinds and at least 2 worlds, and it must hold in ALL THREE seeds.

With c = 0 the p-value is 2**-b, so the smallest passing b is 7 (2**-7 = 0.0078125 <= 0.01).

This script answers: if the machine genuinely improves on a fraction q of the honest relational questions, what is
the chance of clearing the bar? It is a power calculation, not a prediction.

Run:  python -B gate_power.py
"""
from math import comb

THRESHOLD = 0.01
SEEDS = 3


def min_b_for_p(c, threshold=THRESHOLD):
    """Smallest b with P(X >= b) <= threshold, X ~ Binomial(b + c, 0.5), one-sided, AND b > c."""
    b = c + 1
    while True:
        n = b + c
        p = sum(comb(n, k) for k in range(b, n + 1)) / (2 ** n)
        if p <= threshold:
            return b, p
        b += 1


def p_pass_single_seed(n_questions, q_gain, q_loss=0.0, threshold=THRESHOLD):
    """P(b - c discordant with b gains and c losses clears b > c and p <= threshold)."""
    total = 0.0
    for b in range(n_questions + 1):
        for c in range(n_questions - b + 1):
            if b <= c:
                continue
            n = b + c
            p_val = sum(comb(n, k) for k in range(b, n + 1)) / (2 ** n)
            if p_val > threshold:
                continue
            rest = n_questions - b - c
            prob = (comb(n_questions, b) * comb(n_questions - b, c)
                    * (q_gain ** b) * (q_loss ** c) * ((1 - q_gain - q_loss) ** rest))
            total += prob
    return total


print("exact threshold check: smallest passing b for a few loss counts")
for c in (0, 1, 2, 3):
    b, p = min_b_for_p(c)
    print("   c=%d -> b=%d (p=%.10f)" % (c, b, p))

print()
print("power table: P(one seed clears) for a population of N honest relational questions")
print("assumes no losses; three seeds must ALL clear, so cube the single-seed figure")
print()
header = "   N  |" + "".join("   q=%.2f " % q for q in (0.10, 0.20, 0.30, 0.40, 0.50))
print(header)
print("  ----+" + "-" * (len(header) - 6))
for n in (9, 11, 13, 15, 17, 19, 24, 29):
    cells = []
    for q in (0.10, 0.20, 0.30, 0.40, 0.50):
        p1 = p_pass_single_seed(n, q)
        cells.append("  %.4f" % p1)
    print("  %3d |" % n + "".join(cells))

print()
print("all-three-seeds requirement (cube of the single-seed figure):")
print("   N  |" + "".join("   q=%.2f " % q for q in (0.10, 0.20, 0.30, 0.40, 0.50)))
print("  ----+" + "-" * (len(header) - 6))
for n in (9, 11, 13, 15, 17, 19, 24, 29):
    cells = []
    for q in (0.10, 0.20, 0.30, 0.40, 0.50):
        p1 = p_pass_single_seed(n, q)
        cells.append("  %.4f" % (p1 ** SEEDS))
    print("  %3d |" % n + "".join(cells))

print()
print("required improvement count at c = 0:", min_b_for_p(0)[0], "questions, in EVERY seed")
