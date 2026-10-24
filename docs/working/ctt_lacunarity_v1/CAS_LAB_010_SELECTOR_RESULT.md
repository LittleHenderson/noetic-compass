# CAS-LAB-010 — RPM-guided selector result: best selector is 1.2283×, below the 1.25 bar (2026-10-24)

Status: **preregistered test, executed, FAILS its bar by a narrow margin.** AWS-evaluated: instance
`i-07870238269c37c66`, us-west-2, g5.xlarge, 309.1 s, **0.0944 USD**. Preregistration:
`CAS_LAB_007_RPM_GUIDED_PREREG.md` (unchanged).

## 1. Result

| Selector | Gain | Fraction of oracle | Ratio vs D1 (unguided) |
|---|---:|---:|---:|
| D1 unguided kNN | 0.179647 | 0.3933 | 1.0000 |
| D2 same-cell | 0.072766 | 0.1593 | 0.4050 |
| **D3 same-operator** | **0.220641** | **0.4831** | **1.2283** |
| D4 distance × requirement-concentration | 0.159371 | 0.3489 | 0.8871 |
| D5 random rows | 0.018013 | 0.0394 | 0.1002 |
| Oracle | 0.456759 | 1.0000 | — |

Frozen bar: a label-guided selector must reach **1.25×** D1's oracle fraction. The best, D3, reaches **1.2283×**.

**Verdict: the structural hypothesis fails its pre-registered bar.** It cannot be reported as passing; the margin is
0.0217 short.

## 2. What the numbers say beyond the verdict

- **Operator type is the one useful label.** Restricting the neighbourhood to rows with the same operator (`×` vs `→`)
  beats plain distance: 0.220641 against 0.179647, and it is the best of five selectors at 48.31% of the oracle gain.
  The bar was 1.25×, the result is 1.2283×.
- **Cell identity actively hurts.** D2, same-cell, is the worst label-guided selector at 0.405× — restricting to one
  Noetic×Domain cell throws away most of the useful neighbours. This matters: the earlier rounds were framed around
  "weak cells", and cell identity is the label that performs worst.
- **The requirement-concentration weight hurts** (0.8871×). The design-value proxy adds noise, not signal.
- **Random rows are near zero** (0.0394×), confirming that the neighbourhood is doing real work and the whole effect
  is not a magnitude artefact.

## 3. Honest reading

The second approved option does not produce a validated control rule. It produces one suggestive fact: **the operator
type carries steering-relevant information, the Noetic cell does not.** A 1.2283× improvement from a coarse
two-category label is not nothing, but it was not what was preregistered and it is not a pass.

Two ways forward exist and **neither is claimed**:

1. Preregister the operator-only comparison alone with a fresh bar (this is a new hypothesis, not a rescue of the old).
2. Combine operator gating with a distance-weighted neighbourhood and test on the guard as well as the gain.

Neither was run. Changing the bar after seeing 1.2283× would be exactly the failure mode the preregistration exists to
prevent.

## 4. Claim status

| Statement | Status |
|---|---|
| Same-operator selection beats unguided distance by 1.2283× | `REAL` (one seed, one split) |
| A label-guided selector reaches the 1.25× bar | `FAILED` |
| Cell identity improves selection | `REJECTED` (0.405×) |
| Operator type carries steering-relevant information | `HYPOTHESIS` — the number is real, the interpretation is not tested |
| RPM-guided direction is a validated control rule | `NO` |

## 5. Cost

- This run: **0.0944 USD**.
- Goal total: about **1.07 USD** of the 15.00 USD cap.
- Script failures along the way: three (two indexing errors, one CUDA assert), all recorded in the changelog.
