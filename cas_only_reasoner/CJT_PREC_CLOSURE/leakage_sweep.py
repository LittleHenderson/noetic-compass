"""C2b -- the free-lunch measure ACROSS DRAWS, not from one.

closure.py's C2 measured a single random device and got 0.3802 against a chance of 0.2500.
A single draw cannot support a claim about an architecture: the readout is random, so one
draw can align with the secret type->action map by luck. This sweeps independent draws.

Run:  python leakage_sweep.py     Cost: $0, local CPU, numpy. No GPU, no training.
"""
import numpy as np

DE, H, K = 4, 6, 4


def make(K, rng, u=0.5):
    return ([rng.normal(0, .5, (DE, H)) for _ in range(K)],
            [rng.normal(0, u, (H, H)) for _ in range(K)],
            [rng.normal(0, .1, H) for _ in range(K)],
            rng.normal(0, .5, (H, K)))


def chain(p, E):
    W, U, b, Rd = p
    h = np.zeros(H)
    for k in range(K):
        h = np.tanh(E[k] @ W[k] + U[k] @ h + b[k])
    return h @ Rd


print("ZERO-PARAMETER leakage of the PRECEDENCE device, across independent draws.")
print("Each row is a fresh device AND a fresh secret type->action map pi.")
print("A zero-parameter reader takes argmax of the device output. It never learns pi.\n")
print("  seed   pi            0-param acc   above chance")
accs = []
for sd in range(12):
    rng = np.random.default_rng(700 + sd)
    p, pi = make(K, rng), rng.permutation(K)
    n, hit = 4000, 0
    for _ in range(n):
        c = int(rng.integers(0, K))
        E = rng.normal(0, 1, (K, DE))
        E[c] += 2.5
        hit += (int(np.argmax(chain(p, E))) == pi[c])
    accs.append(hit / n)
    print(f"  {sd:4d}   {list(int(x) for x in pi)}   {accs[-1]:11.4f}   {accs[-1] - .25:+.4f}")

a = np.array(accs)
se = a.std(ddof=1) / np.sqrt(len(a))
print(f"\n  mean {a.mean():.4f}   sd {a.std(ddof=1):.4f}   min {a.min():.4f}   max {a.max():.4f}"
      f"   (chance 0.2500)")
print(f"  mean - chance = {a.mean() - .25:+.4f}   se {se:.4f}   ratio {(a.mean() - .25) / se:+.2f}")
print()
if abs(a.mean() - .25) < 2 * se:
    print("  -> AT CHANCE IN EXPECTATION. The device carries no SYSTEMATIC type->action")
    print("     information, which is the property the free-lunch claim needs.")
    print(f"  -> BUT the spread is large (min {a.min():.4f}, max {a.max():.4f}). A SINGLE draw")
    print("     can leak badly by luck, so the claim MUST be stated over draws. The single-draw")
    print("     figure of 0.3802 from closure.py C2 is NOT evidence either way.")
else:
    print("  -> systematically off chance; the free-lunch claim FAILS as stated.")
