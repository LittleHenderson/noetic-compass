"""Independent re-measurement of the two attack findings that CHANGE a committed record.

The adversarial design attack on CJT-CASCADE-S0 returned two claims sharper than my own, and
one of them says a gate I registered two commits ago does not work. Program discipline: verify
an agent's claim by re-measuring it before adopting it.

  B4  The span gate is BLIND TO ORDER. Claim: with stages that commute EXACTLY -- so sequence is
      provably irrelevant -- C13_SPAN_GATE still PASSES. If true, the gate never measured
      sequential composition at all, and it cannot license SEQUENTIAL_CASCADE_COMPOSITION_VALUE
      either, not merely CAS_OHM_VALUE.

  B5  GATE_EPS_NOT_A_SIDE_CHANNEL DOES NOT FIRE. Claim: at my registered floor R >= 1e4 * eps,
      the hidden cause is still recoverable from the eps residue. If true, the gate I wrote into
      the D0 preregistration as amendment A2 is ineffective as written.

Every conclusion is DERIVED from the number printed above it.

Run:  python verify_attack_findings.py
Cost: $0, local CPU, numpy only. No GPU, no training, no network.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "CJT_OHM_0R"))
import ohm0r as M  # noqa: E402

RNG = M.RNG
EPS = M.EPS
D, NST, TRIALS = 12, 4, 200


def bar():
    print("=" * 78)


# ====================================================================== B4
bar()
print("B4  Is C13_SPAN_GATE blind to ORDER?")
bar()
print("  Diagonal matrices COMMUTE. If every stage is diagonal then dW_i dW_j = dW_j dW_i")
print("  exactly, so the order of the cascade is PROVABLY IRRELEVANT -- every ordering gives")
print("  the identical W_eff. A gate that measures sequential composition must therefore")
print("  report ~0 here. Let us see what it reports.")
print()


class Diag:
    """Same interface as Basis, but every stage is diagonal -- all stages commute exactly."""

    def __init__(self, d, n, s):
        self.W0 = RNG.normal(0, .3, (d, d))
        self._d = [np.diag(RNG.normal(0, .3, d)) for _ in range(n)]
        self.s, self.n = s, n

    def dW(self, j):
        return self._d[j]

    def series(self, alpha, x):
        I = np.eye(self.W0.shape[0])
        Mx = I
        for j in range(self.n):
            Mx = (I + self.s * alpha[j] * self.dW(j)) @ Mx
        return (Mx @ self.W0) @ x

    def series_expert(self, j, x):
        I = np.eye(self.W0.shape[0])
        return ((I + self.s * self.dW(j)) @ self.W0) @ x


def span_resid(b, compose, expert, trials=TRIALS):
    worst = 0.0
    for _ in range(trials):
        x = RNG.normal(0, 1, b.W0.shape[1])
        al = RNG.dirichlet(np.ones(b.n))
        y = compose(al, x)
        E = np.stack([expert(j, x) for j in range(b.n)], axis=1)
        beta, *_ = np.linalg.lstsq(E, y, rcond=None)
        worst = max(worst, float(np.linalg.norm(y - E @ beta) / (np.linalg.norm(y) + 1e-12)))
    return worst


vals = []
for k in range(3):
    Bd = Diag(D, NST, 0.7)
    comm = max(
        float(np.max(np.abs(Bd.dW(i) @ Bd.dW(j) - Bd.dW(j) @ Bd.dW(i))))
        for i in range(NST) for j in range(NST)
    )
    r = span_resid(Bd, lambda a, x, b=Bd: b.series(a, x), Bd.series_expert)
    vals.append((comm, r))
    print(f"  run {k + 1}:  max commutator ||dW_i dW_j - dW_j dW_i||_inf = {comm:.10e}"
          f"   span residual = {r:.10e}   gate = {'PASS' if r > 1e-3 else 'FAIL'}")

print()
max_comm = max(v[0] for v in vals)
min_res = min(v[1] for v in vals)
if max_comm == 0.0 and min_res > 1e-3:
    print(f"  -> CONFIRMED. Every commutator is EXACTLY {max_comm:.1f}, so order provably does not")
    print(f"     matter, and the gate still PASSES (worst-case residual {min_res:.6e} > 1e-3).")
    print()
    print("     THE GATE DOES NOT MEASURE SEQUENCE. It measures DEGREE >= 2 CURVATURE -- the")
    print("     product picks up s^2 terms whether or not the factors commute. So it cannot")
    print("     license SEQUENTIAL_CASCADE_COMPOSITION_VALUE either, not merely CAS_OHM_VALUE.")
elif max_comm != 0.0:
    print(f"  -> the stages did NOT commute (max {max_comm:.3e}); this test did not isolate order.")
else:
    print(f"  -> the gate FAILED on commuting stages (residual {min_res:.6e}); it does read order.")

# ====================================================================== B5
print()
bar()
print("B5  Does GATE_EPS_NOT_A_SIDE_CHANNEL actually fire at its registered floor?")
bar()
print(f"  eps = {EPS:g}.  Conductance is  g = m*rho*psi*V/(R + eps).")
print("  A collision pair is two states whose IDEAL conductance is identical (V1/R1 == V2/R2)")
print("  but whose cause differs. The registered floor was R >= 1e4 * eps, on the theory that")
print("  it puts the residue below 1e-4 of the signal. TEST: at that floor, can a controller")
print("  that sees ONLY g still tell the two causes apart?")
print()
print("  R_floor_mult   R1            R2            g1-g2 (relative)   separable by g alone?")
for mult in [1e2, 1e4, 1e6, 1e8]:
    R1 = mult * EPS
    R2 = 2.0 * R1
    V1, V2 = R1, R2                       # V/R == 1 for both -> IDEAL g identical
    g1 = V1 / (R1 + EPS)
    g2 = V2 / (R2 + EPS)
    rel = abs(g1 - g2) / max(abs(g1), abs(g2))
    # A controller seeing only g separates the causes iff g1 != g2 in float.
    sep = "YES" if g1 != g2 else "no"
    tag = "   <== MY REGISTERED FLOOR" if mult == 1e4 else ""
    print(f"  {mult:>10.0e}   {R1:.6e}  {R2:.6e}  {rel:.6e}      {sep}{tag}")

print()
print("  Now the decisive form: 200 collision pairs at the registered floor, all with")
print("  IDEAL g identical, cause assigned at random. Can a single threshold on g recover it?")
n = 200
gs, causes = [], []
for i in range(n):
    cause = int(RNG.integers(0, 2))
    base = 1e4 * EPS * float(RNG.uniform(1.0, 10.0))
    R = base * (1.0 if cause == 0 else 3.0)     # different cause -> different R ...
    V = R                                        # ... but V/R identical, so ideal g identical
    gs.append(V / (R + EPS))
    causes.append(cause)
gs, causes = np.array(gs), np.array(causes)
order = np.argsort(gs)
gs_s, c_s = gs[order], causes[order]
best = 0.0
for i in range(1, n):
    acc = max((c_s[:i] == 0).sum() + (c_s[i:] == 1).sum(),
              (c_s[:i] == 1).sum() + (c_s[i:] == 0).sum()) / n
    best = max(best, acc)
print(f"    ideal g for every state = {1.0:.1f} exactly (V/R == 1 by construction)")
print(f"    actual g range          = [{gs.min():.15f}, {gs.max():.15f}]")
print(f"    spread                  = {gs.max() - gs.min():.6e}")
print(f"    best single threshold on g recovers the cause at accuracy = {best:.6f}"
      f"   (chance = 0.5)")
print()
if best > 0.6:
    print("  -> CONFIRMED, AND THE GATE I REGISTERED IS INEFFECTIVE AS WRITTEN.")
    print("     States whose IDEAL conductance is identical carry a systematic eps residue that")
    print("     recovers the hidden cause well above chance, AT the floor I registered.")
    print("     The floor bounds the residue's SIZE; it does not remove its CORRELATION with the")
    print("     cause. A vanishing but SYSTEMATIC difference is still a perfect side channel,")
    print("     because a learned controller reads sign and order, not magnitude.")
    print()
    print("     REPAIR: a magnitude floor cannot work. Either remove eps from the divisor (guard")
    print("     R = 0 by construction instead), or QUANTIZE g before any controller sees it, so")
    print("     that states with equal ideal conductance are bit-identical downstream.")
else:
    print(f"  -> the cause is NOT recoverable above chance ({best:.6f}); the floor holds.")
