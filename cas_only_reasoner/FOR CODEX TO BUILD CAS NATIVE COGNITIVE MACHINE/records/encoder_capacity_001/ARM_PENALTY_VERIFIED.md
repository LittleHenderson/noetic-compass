# The ridge penalty does not change arm A's prediction — verified after the tenth correction

**Record:** `records/encoder_capacity_001/`
**Script:** `sweep_arm_penalty.py` (output `arm_penalty_sweep.txt`)
**Spend:** $0.00. Pure standard library. No torch, no device, no target opened.
**Follows:** `INFORMATION_LOSS_WITHDRAWN.md` — applying that lesson rather than only recording it.

---

## Why this was run

The tenth self-correction found that a **fixed ridge penalty of λ = 1.0 applied across
differently-scaled feature sets turns a conditioning difference into an apparent capability
difference**, and that the record's other probes use the same fixed value. The published arm-A
figures were measured at λ = 1.0. So the number the whole proposal rests on needed the same check.

## The sweep

Three orders of magnitude of penalty, naive fit and one recurrence-aware refinement round, each
scored out-of-fold at depth 0 and through the registered depth-8 recurrence:

| penalty | fit | depth 0 | **depth 8** |
|---:|---|---:|---:|
| 1e-4 | naive | **64.72%** | 45.74% |
| **1e-4** | **refined ×1** | 63.48% | **61.70%** |
| 1e-2 | naive | 64.72% | 45.21% |
| **1e-2** | **refined ×1** | 63.48% | **61.70%** |
| 1.0 | naive | 63.83% | 44.68% |
| **1.0** | **refined ×1** | 62.77% | **61.88%** |

## The result

**The curve is flat where it matters.**

| quantity | spread across the sweep |
|---|---:|
| naive fit, depth 0 | **0.89 points** (64.72% → 63.83%) |
| naive fit, depth 8 | **1.06 points** (45.74% → 44.68%) |
| refined fit, depth 0 | 0.71 points (63.48% → 62.77%) |
| **refined fit, depth 8** | **0.18 points** (61.70% → 61.88%) |

**The published figures stand.** 62.94% direct and 62.06% through the recurrence at λ = 1.0 with two
refinement rounds are not penalty artifacts. At one refinement round and λ = 1.0 the depth-8 figure
is **61.88%**, within 0.18 points of the two-round number, so the refinement has converged for
practical purposes after one round.

**The recurrence's cost is also robust.** The naive fit's depth-8 figure is 44.68–45.74% across the
sweep, so the drop from ~64% direct to ~45% through the recurrence — the aiming error
`RECURRENCE_AWARE_FIT_RESULT.md` identified — is **18.98 to 19.51 points at every penalty tested**.

## The contrast, and why it is the useful part

The same kind of sweep on the **trained block's** decodability moved it enormously; on the **arm's
fit** it moves it barely at all:

| feature set | spread across the penalty sweep |
|---|---:|
| `^6_trained(x)` decodability | **29.08 points** (37.23% → 66.49%) |
| **arm A's refined fit, depth 8** | **0.18 points** |

**The arm's features are well-conditioned; the trained block's are not.** That is a second,
independent reading of the same asymmetry the record keeps finding: the analytic construction lands
in a regime where a fixed-penalty linear read works, and the trained block does not.

It also means the tenth correction's lesson is bounded. **Not every probe in this record is
vulnerable to it.** Probes that compare differently-scaled feature sets are — and one was, and it
was caught. Probes that fit and score within one feature space, as this one does, are not.

## Verification honesty

**The best row is mildly optimistic.** The best penalty is selected by looking at the same
out-of-fold numbers that are reported, which is a small selection cost. That is why the **shape of
the curve** is the reading offered here rather than the argmax: with a 0.18-point spread the choice
of penalty is immaterial, and no selection is being relied on.

## What is NOT established here

- **This measures the construction, not a run.** No arm has been launched. No reservation, no
  device, no AWS.
- **One refinement round, not two.** The published 62.06% uses two. The one-round figure 61.88% is
  reported here because the sweep is about the penalty, and the two agree to 0.18 points.
- **The encoded slots are rebuilt** at +0.781 correlation with the recorded logits. Every comparison
  is between rows on the same rebuilt inputs.
- **The figures are on ONE field** — focus-world alias decodability, a single 64-way choice — and are
  **not** the whole-answer exact-match metric the course scores.
- **Only three penalties** were swept (1e-4, 1e-2, 1.0), not the full nine of the tenth correction's
  check. The two extremes where the trained block moved most (1e-6 and 1e-4) are represented by 1e-4.
- **One arm, one seed** for every input to this. `MIXED_SAME_ITEMS`, seed `20260919`.
- **No claim that the flatness would hold for a different loss, a different feature map, or a
  different task.** It holds for this construction on this data.
