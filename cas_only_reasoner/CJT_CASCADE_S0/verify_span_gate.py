"""CJT-CASCADE-S0 pre-design verification of the ONE fact that justified this lane.

The cascade lane was authorized on a single surviving result from CJT-OHM-0R: the cascade
composition sits OUTSIDE the linear span of the additive family, while a matched additive
control sits inside it. This script re-measures that claim on the COMMITTED construction
before any design work is done.

Three questions. Every conclusion is DERIVED from the number printed above it -- never
hard-coded. (The D0 verification script's defect was a conclusion that contradicted its
own output; that must not recur.)

  Q1  What number does the committed C13_SPAN_GATE actually produce?
  Q2  Is that number CAS-specific, or does any random system produce it?
  Q3  Is it a FREE DIAL set by the builder's choice of s?

Run:  python verify_span_gate.py
Cost: $0, local CPU, numpy only. No GPU, no training, no network.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "CJT_OHM_0R"))
import ohm0r as M  # noqa: E402

RNG = M.RNG
DIMS = (12, 12, 3, 4)          # exactly the committed Basis(12, 12, 3, 4)
TRIALS = 200                   # exactly the committed c13 trial count


def span_resid(B, compose, expert, trials=TRIALS):
    """Verbatim re-implementation of the committed c13 residual."""
    worst = 0.0
    for _ in range(trials):
        x = RNG.normal(0, 1, B.W0.shape[1])
        al = RNG.dirichlet(np.ones(B.n))
        y = compose(al, x)
        E = np.stack([expert(j, x) for j in range(B.n)], axis=1)
        beta, *_ = np.linalg.lstsq(E, y, rcond=None)
        worst = max(worst, float(np.linalg.norm(y - E @ beta) / (np.linalg.norm(y) + 1e-12)))
    return worst


def bar():
    print("=" * 78)


# ---------------------------------------------------------------------- Q1
bar()
print("Q1  What does the COMMITTED C13_SPAN_GATE actually print?")
bar()
B = M.Basis(*DIMS)
ok, msg, data = M.c13(B)
print(f"  committed c13 -> pass={ok}")
print(f"  {msg}")
print(f"  additive = {data['additive']:.6e}    cascade = {data['series']:.6f}")
committed = data["series"]
print()
print("  RECORDED IN THE FINDINGS / SPEC SHEET / MEMORY: cascade 0.2096, additive 3.0e-16")
if abs(committed - 0.2096) > 0.01:
    print(f"  -> MISMATCH. The committed package produces {committed:.4f}, NOT 0.2096.")
    print("     0.2096 was the INDEPENDENT AUDITOR'S number from its own reimplementation,")
    print("     transcribed into the record as though it were this package's. Two")
    print(f"     implementations of the same check differ by {0.2096 / committed:.2f}x.")
else:
    print("  -> matches the recorded number.")

# ---------------------------------------------------------------------- Q2
print()
bar()
print("Q2  Is the residual CAS-SPECIFIC, or does ANY random system produce it?")
bar()
print("  NOTE: the committed Basis has NO CAS content. W0, A, B and U are all RNG.normal")
print("  draws. So this question is really: what is the null distribution of the gate?")
print()
vals = []
for _ in range(15):
    Bk = M.Basis(*DIMS)
    vals.append(span_resid(Bk, lambda a, x, b=Bk: b.series(a, x), Bk.series_expert))
vals = np.array(vals)
print(f"  15 independent random systems, EXACT c13 protocol (trials={TRIALS})")
print(f"    min {vals.min():.6f}   mean {vals.mean():.6f}   max {vals.max():.6f}"
      f"   sd {vals.std(ddof=1):.6f}")
if vals.min() > 1e-3:
    print("  -> EVERY purely random system is 'outside the additive span'. The gate has NO")
    print("     discriminating power for CAS: it only distinguishes a PRODUCT of matrices")
    print("     from a SUM of matrices, which is a fact of linear algebra.")
else:
    print("  -> some random systems sit inside the span; the gate may carry structure.")
z = (committed - vals.mean()) / vals.std(ddof=1)
print(f"  committed value {committed:.6f} sits {z:.2f} sd from the random mean"
      f"  ({(vals < committed).mean() * 100:.0f}th percentile)")

# ---------------------------------------------------------------------- Q3
print()
bar()
print("Q3  Is the residual a FREE DIAL set by the builder's choice of s?")
bar()
print(f"  s is hard-coded in Basis.__init__ as {M.Basis(*DIMS).s}. No registered gate constrains it.")
print("  A fresh Basis and a fresh trial stream are drawn for EVERY s, so the rows are")
print("  comparable to each other and none inherits another's RNG state.")
print()
print("       s     additive        cascade       mean |s*dW_j|_2   c13 gate")
sweep = {}
for s in [1.0, 0.7, 0.5, 0.3, 0.1, 0.05, 0.03, 0.01]:
    Bs = M.Basis(*DIMS)
    Bs.s = s
    add = span_resid(Bs, lambda a, x, b=Bs: b.linear_weight(a, x), Bs.additive_expert)
    ser = span_resid(Bs, lambda a, x, b=Bs: b.series(a, x), Bs.series_expert)
    nrm = float(np.mean([np.linalg.norm(s * Bs.dW(j), 2) for j in range(Bs.n)]))
    gate = "PASS" if (add < 1e-10 and ser > 1e-3) else "FAIL"
    sweep[s] = ser
    note = "   <== COMMITTED DEFAULT" if s == 0.7 else ""
    print(f"  {s:6.3f}   {add:.4e}    {ser:.6e}   {nrm:12.4f}   {gate}{note}")

print()
ratio = sweep[0.1] / sweep[0.01]
print(f"  cascade residual, s=0.1 -> s=0.01 : {ratio:.1f}x  ->  exponent ~ {np.log10(ratio):.2f}")
if np.log10(ratio) > 1.5:
    print("  -> SECOND ORDER in s, as the algebra predicts: the cross term s^2*a_i*a_j*dW_j*dW_i")
    print("     is the only part the additive mixture cannot express, and it vanishes")
    print("     quadratically while the arms' own effect vanishes linearly.")
else:
    print("  -> not clearly second order; do not conclude from this run.")

span = sweep[1.0] / sweep[0.01]
print(f"  full sweep range: {sweep[1.0]:.6e} down to {sweep[0.01]:.6e}  =  {span:.0f}x")
flips = [s for s in sorted(sweep) if sweep[s] <= 1e-3]
if flips:
    print(f"  the c13 gate FLIPS to FAIL at s <= {max(flips):g}.")
    print("  => ONE HARD-CODED FLOAT SELECTS WHETHER THE GATE PASSES. That is a free dial,")
    print("     the same defect class that killed the last three designs.")
else:
    print("  the gate passes across the whole sweep; s is not a status dial.")

nrm07 = float(np.mean([np.linalg.norm(0.7 * M.Basis(*DIMS).dW(j), 2) for j in range(DIMS[3])]))
print()
print(f"  At the committed default s = 0.7 the stages have mean operator norm {nrm07:.4f}.")
if nrm07 > 0.5:
    print("  -> these are NOT small perturbations. (I + s*a*dW) is far from the identity, so the")
    print("     cascade is a genuinely DEEPER, DIFFERENT model -- not the same model composed")
    print("     differently. The effect is large only where the comparison is unmatched.")
else:
    print("  -> the stages are small perturbations; the comparison is depth-matched.")
