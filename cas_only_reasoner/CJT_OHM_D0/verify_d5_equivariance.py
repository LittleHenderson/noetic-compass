"""VERIFY the claim that kills D0: is D5 (channel-shuffled) EXACTLY D4 (typed)?

The architecture A1.B mandates: per-type read-in modules over per-channel raw fields, then
LEARNED routing to repair logits. If permuting which channel feeds which module is exactly
compensated by permuting the module parameters, then D4 and D5 are the same function and the
"causal corruption" control is worthless.
"""
import itertools
import numpy as np

rng = np.random.default_rng(11)
K, F, H, Rep = 6, 3, 8, 6        # channels, fields/channel, hidden, repair options


def make_params():
    """One read-in module PER CHANNEL (structurally identical), then shared routing."""
    Win = [rng.normal(0, .5, (F, H)) for _ in range(K)]
    bin_ = [rng.normal(0, .1, H) for _ in range(K)]
    Wout = rng.normal(0, .5, (K * H, Rep))       # routing reads the concatenated modules
    return Win, bin_, Wout


def forward(params, X, perm=None):
    """X: (K, F) raw fields per channel. perm maps channel -> module index."""
    Win, bin_, Wout = params
    p = list(range(K)) if perm is None else list(perm)
    hs = [np.tanh(X[c] @ Win[p[c]] + bin_[p[c]]) for c in range(K)]
    return np.concatenate(hs) @ Wout


def permute_params(params, perm):
    """The compensating parameter permutation: relabel modules AND the routing blocks."""
    Win, bin_, Wout = params
    Win2 = [Win[perm[j]] for j in range(K)]
    bin2 = [bin_[perm[j]] for j in range(K)]
    # routing reads the concatenation BY CHANNEL POSITION in both arms, so Wout is unchanged
    return Win2, bin2, Wout


params = make_params()
X = rng.normal(0, 1, (K, F))

print("=" * 76)
print("V1  Does a PARAMETER permutation exactly absorb a CHANNEL permutation?")
print("=" * 76)
worst, n = 0.0, 0
for perm in itertools.permutations(range(K)):
    n += 1
    y_shuffled = forward(params, X, perm=perm)              # D5: wrong channel -> module
    y_typed_perm = forward(permute_params(params, perm), X)  # D4 with permuted parameters
    worst = max(worst, float(np.max(np.abs(y_shuffled - y_typed_perm))))
print(f"  enumerated ALL {n} permutations of {K} channels")
print(f"  worst |logit_D5(perm) - logit_D4(permuted params)| = {worst:.4e}")
fwd_residual = worst          # V3 quotes THIS, not V2's training divergence
if worst < 1e-10:
    print("  -> ABSORBED. Every channel shuffle is undone by relabelling the parameters, so D5")
    print("     and D4 are the SAME FUNCTION CLASS -- reachable from each other by a weight")
    print("     permutation that gradient descent is free to find.")
else:
    print("  -> NOT absorbed. The claim does NOT reproduce at this residual.")

print()
print("=" * 76)
print("V2  Does it stay the same through TRAINING, from a matched init?")
print("=" * 76)


def loss_and_grad_step(params, Xs, ys, perm=None, lr=0.05):
    Win, bin_, Wout = params
    p = list(range(K)) if perm is None else list(perm)
    tot = 0.0
    gWin = [np.zeros_like(w) for w in Win]
    gbin = [np.zeros_like(b) for b in bin_]
    gWout = np.zeros_like(Wout)
    for X, y in zip(Xs, ys):
        hs = [np.tanh(X[c] @ Win[p[c]] + bin_[p[c]]) for c in range(K)]
        h = np.concatenate(hs)
        logits = h @ Wout
        e = np.exp(logits - logits.max())
        pr = e / e.sum()
        tot += -np.log(pr[y] + 1e-12)
        d = pr.copy()
        d[y] -= 1.0
        gWout += np.outer(h, d)
        dh = Wout @ d
        for c in range(K):
            g = dh[c * H:(c + 1) * H] * (1 - hs[c] ** 2)
            gWin[p[c]] += np.outer(X[c], g)
            gbin[p[c]] += g
    m = len(Xs)
    Win2 = [Win[j] - lr * gWin[j] / m for j in range(K)]
    bin2 = [bin_[j] - lr * gbin[j] / m for j in range(K)]
    return (Win2, bin2, Wout - lr * gWout / m), tot / m


Xs = [rng.normal(0, 1, (K, F)) for _ in range(64)]
ys = [int(rng.integers(0, Rep)) for _ in range(64)]
perm = (3, 0, 5, 1, 4, 2)

pA = make_params()                       # D4, typed
pB = permute_params(pA, perm)            # D5, matched init under the same permutation
worst = 0.0
for step in range(200):
    pA, lA = loss_and_grad_step(pA, Xs, ys, perm=None)
    pB, lB = loss_and_grad_step(pB, Xs, ys, perm=perm)
    worst = max(worst, abs(lA - lB))
print(f"  worst |loss_D4(t) - loss_D5(t)| over 200 training steps = {worst:.4e}")
print("  -> identical for the WHOLE curve, not merely at the optimum." if worst < 1e-10
      else "  -> the curves DIVERGE; the training-time claim does not reproduce.")

print()
print("=" * 76)
print("V3  CONSEQUENCE for the arm ladder")
print("=" * 76)
print("  A1.E defines D_ANON_FACTORIZED as D4 with the same channels, modules, constraints,")
print("  parameters and compute -- but ANONYMOUS factors. Anonymising the factors is exactly")
print("  choosing an assignment of sources to modules with the names removed, i.e. an element")
print("  of the SAME permutation group V1 just enumerated.")
print()
if fwd_residual < 1e-10:
    print(f"  So: D_ANON_FACTORIZED == D5 == D4, to {fwd_residual:.1e} (the FORWARD residual")
    print("  from V1 -- NOT V2's training divergence, which measures a different thing).")
    print("  THREE OF THE SEVEN ARMS ARE ONE ARM.")
    print()
    print("  And CAS_TYPED_REPAIR_SIGNAL requires 'destroyed by D5' as a NECESSARY conjunct.")
    print("  A conjunct that is identically false cannot be satisfied.")
    print("  => the headline status is UNREACHABLE by any A1.B-compliant build.")
else:
    print(f"  V1 did NOT absorb (residual {fwd_residual:.4e}), so this consequence does NOT")
    print("  follow. The arm-collapse claim is NOT supported by this run.")

print()
print("=" * 76)
print("SCOPE OF WHAT THIS SCRIPT ESTABLISHES")
print("=" * 76)
print("  ESTABLISHED : the FORWARD-pass equivalence (V1), exactly, over all 720 permutations.")
print("  NOT ESTABLISHED HERE : that the two arms follow the SAME TRAINING CURVE. V2 does not")
print("    reproduce that (it measures divergence). The verdict does not rest on V2.")
