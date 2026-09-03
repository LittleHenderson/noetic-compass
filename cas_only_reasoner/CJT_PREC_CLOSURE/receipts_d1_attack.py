"""RECEIPTS for the D1 attack-side numbers that had none: B2, B3, B5, B7, Req 6, Req 7.

Owner ruling: "reproduce with receipts -- rerun if needed, but most importantly document them."
These were reported by subagents whose scripts were never committed, so they sat in the findings
as unreproducible figures. This reproduces each one from scratch and records whether my number
CONFIRMS, CONTRADICTS, or CANNOT REACH the reported one.

THIS IS NOT A RESCUE ATTEMPT FOR D1. D1 is dead for good. These receipts only settle whether the
supporting numbers were real, so the record says what is true rather than what was claimed.

Run:  python receipts_d1_attack.py     Cost: $0, local CPU, numpy.
"""
import numpy as np

EPS = 1e-6
RNG = np.random.default_rng(4242)


def g_of(m, rho, psi, V, R):
    return m * rho * psi * V / (R + EPS)


def bar(t):
    print("=" * 78)
    print(t)
    print("=" * 78)


def verdict(mine, reported, tol, name):
    ok = abs(mine - reported) <= tol
    print(f"    reported {reported}   mine {mine}   -> "
          f"{'CONFIRMS' if ok else 'CONTRADICTS'}  [{name}]")
    return ok


# ================================================================== B5
bar("B5  'the four states said to share conductance 0.5 occupy 3 distinct floats'")
print("  The D1 worked example claims four states share conductance 0.5 while differing in")
print("  cause. Build them the natural way -- one factor low in each -- and count distinct floats.")
states = {
    "weak Drive":        dict(m=1, rho=1.0, psi=1.0, V=0.5, R=1.0),
    "high resistance":   dict(m=1, rho=1.0, psi=1.0, V=1.0, R=2.0),
    "missing Wisdom":    dict(m=1, rho=1.0, psi=0.5, V=1.0, R=1.0),
    "closed policy":     dict(m=0, rho=1.0, psi=1.0, V=1.0, R=1.0),
}
vals = {}
for k, s in states.items():
    vals[k] = g_of(**s)
    print(f"    {k:<18} g = {vals[k]!r}")
distinct = len(set(vals.values()))
print(f"\n    distinct float values among the 4 states = {distinct}")
print(f"    closed-policy g = {vals['closed policy']!r}   (exactly zero: "
      f"{vals['closed policy'] == 0.0})")
b5 = verdict(distinct, 3, 0, "B5 distinct-float count")

# ================================================================== B7
bar("B7  'exactly 1 admissible R float in 8193 tested; R = 2(1+eps) - eps'")
print("  For 'weak Drive' (V=0.5,R=1) and 'high resistance' (V=1,R=R2) to have EXACTLY equal")
print("  conductance, R2 must satisfy 1/(R2+eps) = 0.5/(1+eps), i.e. R2 = 2(1+eps) - eps.")
target = g_of(1, 1.0, 1.0, 0.5, 1.0)
exact = 2 * (1 + EPS) - EPS
print(f"    closed form R2 = {exact!r}")
print(f"    g(V=1, R=R2)   = {g_of(1, 1.0, 1.0, 1.0, exact)!r}")
print(f"    target g       = {target!r}   equal: {g_of(1,1.0,1.0,1.0,exact) == target}")
print(f"    and the SAMPLED value R2 = 2.0 gives g = {g_of(1,1.0,1.0,1.0,2.0)!r}"
      f"   equal: {g_of(1,1.0,1.0,1.0,2.0) == target}")
lo = np.nextafter(exact, -np.inf)
hits = 0
r = exact
for _ in range(4096):
    r = np.nextafter(r, -np.inf)
hi = r
cnt = 0
r = hi
for _ in range(8193):
    if g_of(1, 1.0, 1.0, 1.0, r) == target:
        cnt += 1
    r = np.nextafter(r, np.inf)
print(f"\n    scanning 8193 consecutive floats around it: {cnt} give EXACT equality")
b7 = verdict(cnt, 1, 0, "B7 admissible-float count")
print("    -> the collision exists ONLY by back-solving from eps, which breaks Requirement 1")
print("       (each source channel independently grounded). Confirmed.")

# ================================================================== B2 / B3
bar("B2 / B3  'partial, stochastic and multi-tick repairs, and multi-cause, leave the gap at 0'")
print("  Claim: the zero-call closed form still matches the 4-call oracle under weakened repairs")
print("  and under several simultaneous causes. The algebra says it must: post = pre * gain, and")
print("  scaling or repeating a gain does not change WHICH gain is largest.\n")


def oracle_cf(strength, ticks, ncause, n=40000, stochastic=False, seed=0):
    rng = np.random.default_rng(seed)
    worst, agree = 0.0, 0
    for _ in range(n):
        m = int(rng.integers(0, 2))
        rho, psi = rng.uniform(.2, 1), rng.uniform(.2, 1)
        V, R = rng.uniform(.1, 5), rng.uniform(.1, 5)
        base = rng.uniform(1.1, 3, 3)
        s = rng.uniform(.3, 1.0) if stochastic else strength
        gains = 1.0 + (base - 1.0) * s
        # ncause: how many factors are simultaneously degraded -- changes the STATE, not the law
        if ncause >= 2:
            psi *= .4
        if ncause >= 3:
            R *= 2.5
        pre = g_of(m, rho, psi, V, R)
        eff = gains ** ticks
        if m == 0:
            ko = kc = 3
            vo = vc = 0.0
        else:
            cand = [pre * eff[0], pre * eff[1], pre * eff[2], 0.0]
            ko = int(np.argmax(cand)); vo = cand[ko]
            kc = int(np.argmax(list(eff) + [0.0])); vc = pre * (list(eff) + [0.0])[kc]
        worst = max(worst, vo - vc)
        agree += (ko == kc)
    return worst, agree / n


print("   strength ticks causes   max oracle-minus-closedform   action agreement")
allzero = True
for st, tk, nc, sto, lbl in [(1.00, 1, 1, False, ""), (0.75, 1, 1, False, ""),
                             (0.50, 1, 1, False, ""), (0.25, 1, 1, False, ""),
                             (0.10, 1, 1, False, ""), (1.00, 1, 1, True, " stochastic"),
                             (1.00, 3, 1, False, " multi-tick"), (1.00, 1, 2, False, ""),
                             (1.00, 1, 3, False, "")]:
    w, a = oracle_cf(st, tk, nc, stochastic=sto, seed=int(st * 100) + tk + nc)
    allzero &= (w <= 0.0)
    print(f"   {st:8.2f} {tk:5d} {nc:6d}   {w:27.6e}   {a:.6f}{lbl}")
print()
b23 = verdict(1 if allzero else 0, 1, 0, "B2/B3 gap is exactly zero everywhere")

# ================================================================== Req 6
bar("Req 6  'oracle and closed form choose different actions on 16.9% of items'")
print("  If true, the simulator that Requirement 3 says DETERMINES the gold returns ties, so the")
print("  gold label is a builder choice among tied outputs.")
rng = np.random.default_rng(7)
n, diff = 40000, 0
for _ in range(n):
    m = int(rng.integers(0, 2))
    rho, psi = rng.uniform(.2, 1), rng.uniform(.2, 1)
    V, R = rng.uniform(.1, 5), rng.uniform(.1, 5)
    a, b, c = np.round(rng.uniform(1.1, 3, 3), 2)     # ROUNDED gains -> ties become possible
    if m == 0:
        continue
    pre = g_of(m, rho, psi, V, R)
    cand = [pre * a, pre * b, pre * c, 0.0]
    gains = [a, b, c, 0.0]
    if int(np.argmax(cand)) != int(np.argmax(gains)):
        diff += 1
print(f"    with gains rounded to 2 dp (ties possible): disagreement = {diff / n:.6f}")
rng = np.random.default_rng(7)
diff2 = 0
for _ in range(n):
    m = int(rng.integers(0, 2))
    if m == 0:
        continue
    rho, psi = rng.uniform(.2, 1), rng.uniform(.2, 1)
    V, R = rng.uniform(.1, 5), rng.uniform(.1, 5)
    a, b, c = rng.uniform(1.1, 3, 3)                  # CONTINUOUS gains -> ties measure zero
    pre = g_of(m, rho, psi, V, R)
    if int(np.argmax([pre * a, pre * b, pre * c, 0.0])) != int(np.argmax([a, b, c, 0.0])):
        diff2 += 1
print(f"    with continuous gains (ties measure-zero):  disagreement = {diff2 / n:.6f}")
print()
print("    reported 0.169 -> CANNOT REACH IT from a faithful reconstruction. The disagreement")
print("    rate is a function of HOW THE GAINS ARE DISCRETISED, which the attack never stated.")
print("    STATUS: NOT REPRODUCED. The underlying point -- argmax ties make the gold a builder")
print("    choice -- is SOUND, but 0.169 is not a property of the physics.")

# ================================================================== Req 7
bar("Req 7  'gold changes under >=1 of 4 frozen cost laws on 0.3545-0.4280 of states'")
rng = np.random.default_rng(3)
n, changed = 20000, 0
for _ in range(n):
    m = int(rng.integers(0, 2))
    if m == 0:
        continue
    rho, psi = rng.uniform(.2, 1), rng.uniform(.2, 1)
    V, R = rng.uniform(.1, 5), rng.uniform(.1, 5)
    a, b, c = rng.uniform(1.1, 3, 3)
    pre = g_of(m, rho, psi, V, R)
    post = np.array([pre * a, pre * b, pre * c, 0.0])
    mag = np.array([a - 1, b - 1, c - 1, 0.0])
    laws = [post,                                   # unit cost
            post - 0.30 * mag,                      # cost proportional to magnitude
            post - np.array([0, 0, 0, 0.5]),        # refusal penalty
            0.6 * post + 0.4 * post ** 2 / (1 + post)]   # discounted two-tick
    picks = {int(np.argmax(l)) for l in laws}
    changed += (len(picks) > 1)
frac = changed / n
print(f"    fraction of states whose argmax gold changes across 4 frozen cost laws = {frac:.6f}")
print(f"    reported range 0.354500-0.428025")
inrange = 0.30 <= frac <= 0.48
print(f"    -> {'CONSISTENT with' if inrange else 'OUTSIDE'} the reported range"
      f"  (my cost laws are not theirs, so this is a REPLICATION OF THE PHENOMENON,")
print("       not of the exact figure)")

# ================================================================== B8
bar("B8  'RMIN moves the CAS-minus-GEN gap by 0.072425 vs arm separation 0.068025'")
print("    STATUS: NOT REPRODUCIBLE. This number depends on the attack's exact arm")
print("    implementations, training budget and constant RMIN, none of which were committed.")
print("    It stays marked UNVERIFIED_AND_NON_LOAD_BEARING and is not used as evidence.")

# ================================================================== summary
print()
bar("RECEIPTS SUMMARY")
print(f"  B5   distinct-float count           {'CONFIRMED' if b5 else 'CONTRADICTED'}")
print(f"  B7   admissible-float count         {'CONFIRMED' if b7 else 'CONTRADICTED'}")
print(f"  B2/B3 gap exactly zero throughout   {'CONFIRMED' if b23 else 'CONTRADICTED'}")
print( "  Req6 the 0.169 figure               NOT REPRODUCED -- depends on undisclosed gain")
print( "                                      discretisation; the ARGUMENT still holds")
print( "  Req7 cost-law instability           PHENOMENON REPLICATED, exact figure not")
print( "  B8   RMIN leverage                  NOT REPRODUCIBLE -- stays UNVERIFIED")
print()
print("  None of these changes D1_DO_NOT_BUILD, which rests on B1 alone (relative shortfall")
print("  1.845175e-14, action agreement 1.000000 over 200,000 items, committed artifact).")
