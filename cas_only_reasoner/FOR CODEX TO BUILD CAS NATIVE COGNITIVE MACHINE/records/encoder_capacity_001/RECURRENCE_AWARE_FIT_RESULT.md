# The recurrence's 19.15-point cost was an aiming error, and fixing it recovers 17.38 points

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_recurrence_aware_fit.py` (output `recurrence_aware_fit.txt`)
**Applied in:** `tools/prepare_analytic_arm.py`, now recurrence-aware by default
**Spend:** $0.00. Pure standard library. No model, no GPU, no target opened.

---

## The starting point

`PREPARATION_RESULT.md` measured the analytic initialisation two ways, out-of-fold:

| reading | focus-world alias accuracy |
|---|---:|
| direct, `^6(x) = T·tanh(x)` | **63.83%** |
| through the registered depth-8 recurrence | **44.68%** |

The recurrence appeared to cost 19.15 points. The hypothesis was that this is an **aiming error**:
the closed-form solve fits `T` so that `T·tanh(encoded)` reads well, but the run never evaluates
the block on the encoded slot. It evaluates it on `incoming` — the encoded slot **plus a scaled
carry of the block's own previous output** — eight times over. So the solve optimised a functional
the run does not compute.

## Finding 1 — the depth profile says exactly where the loss enters

Naive fit, scored at each registered depth, out-of-fold over the 564 slots:

| depth | correct | accuracy |
|---:|---:|---:|
| 0 (direct) | 360/564 | **63.83%** |
| **1** | 360/564 | **63.83%** |
| 2 | 253/564 | **44.86%** |
| 4 | 246/564 | 43.62% |
| 8 | 252/564 | 44.68% |

**Depth 1 is identical to depth 0.** That is exact and expected: at depth 1 the state is still
zero, so `state_rms = 0`, the carry term is `0.5·rms(e)/sqrt(rms(e)²+0+ε²)·0 = 0`, and
`incoming = encoded`. The block sees what the solve fitted it on, and the score is unchanged.

**The loss happens on pass 2**, when the carry first becomes non-zero — 63.83% to 44.86% in one
step. Passes 4 and 8 neither recover nor worsen it (43.62%, 44.68%). So the recursion degrades the
initialisation once and then sits there; it is not diverging, and it is not converging to
something better either.

## Finding 2 — fitting for the functional the run computes recovers the loss

A fixed-point refinement, each round re-fitting on `tanh(incoming)` for **every `incoming` the
current parameters actually feed the block** across the registered depth, then scored through the
recurrence on the same held-out rows:

| round | depth 0 | **depth 8** | fitted on |
|---:|---:|---:|---|
| 0 | 63.83% | **44.68%** | encoded slots |
| **1** | 62.77% | **61.88%** | recurrence states |
| **2** | 62.94% | **62.06%** | recurrence states |

**44.68% → 61.88% on the first refinement, 62.06% on the second.** That is **+17.38 points**, and
the refinement is a genuine fixed point: rounds 1 and 2 differ by **0.18 points**.

The cost of aiming correctly is about **one point** when the parameters are read directly
(63.83% → 62.94%). So the refined `T` reads the encoded slot nearly as well *and* survives the
recurrence.

## The corrected statement

> The registered recurrence does not intrinsically cost 19 points. It costs 19 points **when the
> block is fitted on an input the run never feeds it**. Fit the block for the functional the run
> actually computes and the residual cost is **0.88 points** (62.94% direct, 62.06% through the
> recurrence).

This is an architectural finding about how the plastic block must be initialised, not a property
of the recursion. `tools/prepare_analytic_arm.py` now performs the refinement by default —
`fit_folds(..., refinements=2)` — and `--refinements 0` reproduces the naive fit for comparison.

## What this does to arm A

| | before | after |
|---|---:|---:|
| direct forward | 63.83% | 62.94% |
| **through the registered recurrence** | **44.68%** | **62.06%** |
| focus alias ranked #1 (of 564) | 252 | **350** |
| distinct aliases emitted (of 64) | 24 | 24 |
| commonest alias share | 11.3% | **6.9%** |

Through the recurrence — the reading that resembles what a run would do — **62.06%** is:

| comparison | value |
|---|---:|
| the trained learner's frozen-readout focus decodability | **50.0×** |
| versus 1/64 chance | **39.7×** |
| versus the strongest null (majority class, 4.6099%) | **13.46×** |

**G6 passes on both readings**: 24 distinct aliases with the commonest at 7.3% (direct) or 6.9%
(through the recurrence), against the recorded baseline of 9 distinct with `W36` at 44.3%.

**P6 is superseded.** It predicted the recurrence would cost arm A between 10 and 30 points, on the
naive fit. With the recurrence-aware fit the prediction is a cost of **under 2 points**, and the
gate is rewritten accordingly.

## What is NOT established here

- **This is a construction measurement, not a run.** Nothing was launched. No reservation, no
  device, no AWS.
- **The encoded slots are rebuilt.** `RECONSTRUCTION_GAP.md` measures that rebuild at **+0.781
  correlation** with the recorded logits. For the analytic parameters the block itself is exact
  (identity residual `0.000e+00`), so this approximation enters only through the input.
- **The figures are on ONE field** — focus-world alias decodability, a single 64-way choice — and
  are **not** the whole-answer exact-match metric the course scores. The two must never be
  presented together as an improvement.
- **Fitting and evaluation are both on the learner's own registry**, 564 packets with only 24 of
  64 worlds present. The fit is out-of-fold, which is what makes the numbers admissible at all.
- **The refinement is not proven to be the optimum.** Two rounds reach a fixed point; whether a
  different parameterisation of the refinement would do better has not been explored.
- **This does not touch the five many-decision kinds.** It concerns the world-naming slot. The
  `edge_account`/`parts`/`context`/`definition`/`role_set` defect is separate
  (`DECISION_STRUCTURE_RESULT.md`).
