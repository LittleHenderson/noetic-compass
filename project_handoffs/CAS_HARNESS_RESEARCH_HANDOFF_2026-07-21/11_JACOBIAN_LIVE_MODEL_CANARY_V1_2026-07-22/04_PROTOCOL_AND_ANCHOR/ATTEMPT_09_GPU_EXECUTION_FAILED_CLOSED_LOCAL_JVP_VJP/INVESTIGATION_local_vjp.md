# Attempt 9 follow-up: owner-directed investigation of the LOCAL VJP gate (2026-07-24)

Owner directive (Option 1): before setting any threshold, determine whether the
`4.24e-3` local VJP floor is float32 precision, a real forward-vs-reverse method
defect, or a formulation issue — then decide.

## Result: it is a metric-normalization (conditioning) artifact, not a derivative defect.

Worst-5 VJP measurements decomposed from the frozen A9 float32 artifacts
(`a9_vjp_decompose.py`, `a9_vjp_conditioning.py`). The VJP relative error
`|direct_vjp - target^T M source| / |direct_vjp|` splits into a forward-vs-reverse
autodiff gap (`fr_gap`, no matrix) and a matrix-estimation term (`mtx_gap`):

| meas  | vjp_relerr | fr_gap  | mtx_gap | jvp_relerr | dominant   |
|-------|-----------|---------|---------|-----------|------------|
| r1/l3 | 4.241e-03 | 4.156e-04 | 3.826e-03 | 4.787e-04 | MATRIX-EST |
| r2/l9 | 3.573e-03 | 1.419e-04 | 3.431e-03 | 2.225e-04 | MATRIX-EST |
| r7/l6 | 3.313e-03 | 1.327e-04 | 3.446e-03 | 2.185e-04 | MATRIX-EST |
| r3/l3 | 1.729e-03 | 6.752e-04 | 2.404e-03 | 2.384e-04 | MATRIX-EST |
| r2/l6 | 1.204e-03 | 1.498e-04 | 1.054e-03 | 5.354e-04 | MATRIX-EST |

Forward-vs-reverse agreement is fine (`fr_gap` ~1.3e-4..6.8e-4, the benign
method floor; in ABSOLUTE terms ~1e-6). The dominant term is `mtx_gap`. But the
conditioning check shows `mtx_gap` is itself a normalization artifact:

| meas  | \|direct_vjp\| | abs_mtx_err | \|\|M.src-Jsrc\|\| | \|\|Jsrc\|\| | M_cond   | \|dvjp\|/scale |
|-------|------------|-------------|-----------------|-----------|----------|-------------|
| r1/l3 | 7.31e-03   | 2.80e-05    | 4.75e-04        | 0.993     | 7.2e+04  | 0.204       |
| r2/l9 | 1.43e-03   | 4.89e-06    | 2.65e-04        | 1.189     | 2.9e+03  | 0.033       |
| r7/l6 | 1.23e-03   | 4.24e-06    | 2.52e-04        | 1.154     | 1.1e+04  | 0.030       |
| r3/l3 | 2.29e-03   | 5.51e-06    | 3.55e-04        | 1.487     | 6.2e+04  | 0.043       |
| r2/l6 | 1.61e-02   | 1.70e-05    | 5.75e-04        | 1.075     | 2.8e+04  | 0.415       |

The absolute error on each projection (`abs_mtx_err`) is tiny (~5e-6..3e-5) and
roughly flat; the VJP RELATIVE error blows up only because the denominator
`|direct_vjp| = |target^T J source|` collapses (`|dvjp|/scale` = 0.03..0.42, i.e.
the random rademacher target is 3-40% of a typical projection — nearly orthogonal
to `J.source`). M is ill-conditioned (cond 3e3..7e4), which is expected for a
hidden-space Jacobian and is exactly why some random projections land small.

## Diagnosis and recommendation

The estimated Jacobian is accurate (JVP vector relerr ~5e-4; absolute bilinear
error ~1e-5), forward and reverse mode agree to ~1e-6, and float64 would not move
any of this (the small denominator is geometry, not precision). The `4.24e-3` is
an ILL-CONDITIONED ERROR METRIC: the VJP relative error normalizes by a random
projection scalar that is sometimes near-zero.

Recommendation: do NOT loosen the VJP gate to ~5e-3 (that would bake the
ill-conditioned metric into the acceptance criteria). Fix the VJP relative-error
NORMALIZATION so it divides by the natural bilinear scale (e.g. `||target|| *
||J.source||`, or a floored denominator) instead of `|direct_vjp|`. Under a
robust denominator the worst VJP "error" is ~`abs_mtx_err/||Jsrc||` ~ 2.8e-5,
which PASSES even a strict 1e-4 gate. This is the owner's "tighten the VJP
formulation" branch — and it makes the STRICT gate pass legitimately rather than
loosening it. It is a trust-surface change to `jacobian_lens_canary_core.py`
(the VJP relative-error definition), so it needs owner sign-off, tests, a full
suite pass, a fresh implementation freeze, and a fresh Attempt 10 identity.

The JVP gate (full-vector relerr, floor ~5.35e-4) is a separate, smaller question:
it is a genuine but benign matrix-accuracy floor and would pass at a documented
~1e-3 limit; it is not conditioning-pathological like the VJP metric.
