# What the registered depth buys, and how training changes the recurrence's regime

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_depth_value.py` (output `depth_value.txt`)
**Spend:** $0.00. `torch` used only to deserialise checkpoints; all arithmetic on plain lists.

---

## Why this measurement is valid despite the rebuild gap

`RECONSTRUCTION_GAP.md` established that the pure-Python rebuild reaches only **+0.781
correlation** with the recorded logits, so no absolute number from it may be presented as the
machine's. **This measurement uses no absolute numbers.** It feeds the *same* input to the *same*
saved block at several depths and compares the depths **with each other**. A wrong input moves all
depths together; it cannot manufacture or hide a difference *between* them. The comparison is
therefore valid even though the input is approximate.

The probe set is 120 world-typed reference slots from `context` and `definition` packets, and the
depths are the registered ones, `(1, 2, 4, 8)`. The prediction path runs **depth 8** for every
slot (`prediction_depth = 8`, and every recorded prediction carries `depth: 8`).

---

## The measurement

Mean logit-vector cosine and argmax agreement between depths, on the same inputs:

**cursor 0 — the untrained block**

| comparison | mean logit cosine | argmax agreement |
|---|---:|---:|
| depth 1 vs 2 | 0.990148 | 85.00% |
| depth 1 vs 4 | 0.989352 | 80.00% |
| depth 1 vs 8 | 0.989381 | 80.00% |
| depth 2 vs 4 | 0.999693 | 95.00% |
| depth 2 vs 8 | 0.999695 | 95.00% |
| **depth 4 vs 8** | **1.000000** | **100.00%** |

**cursor 160 — the trained block**

| comparison | mean logit cosine | argmax agreement |
|---|---:|---:|
| depth 1 vs 2 | 0.929298 | 41.67% |
| depth 1 vs 4 | 0.876005 | 26.67% |
| depth 1 vs 8 | 0.858026 | 23.33% |
| **depth 2 vs 4** | 0.975797 | **66.67%** |
| depth 2 vs 8 | 0.954439 | 54.17% |
| **depth 4 vs 8** | **0.989746** | **82.50%** |

Logit scale by depth, as the mean over probes of the within-slot standard deviation across the
64 symbols:

| depth | cursor 0 | cursor 160 |
|---:|---:|---:|
| 1 | 0.043412 | 0.343673 |
| 2 | 0.045048 | 0.630459 |
| 4 | 0.045008 | 0.654277 |
| 8 | 0.045004 | 0.658688 |

---

## Reading 1 — untrained, the recurrence is a contraction to a fixed point

At cursor 0, **depth 4 and depth 8 are bit-identical on this probe set**: cosine `1.000000`,
argmax agreement `100.00%`. From depth 2 to depth 4 the cosine is `0.999693`. The untrained
recurrence reaches its fixed point by about depth 4 and every further pass is a no-op.

**A caution on cursor 0's high agreement figures.** Its logit sd across 64 symbols is about
`0.043`, so the scores are near-ties and the argmax is largely decided by the first-wins
tie-break rather than by the vector. The 85% and 95% agreements at cursor 0 are partly an
artifact of near-ties and are not evidence that the untrained recurrence is sufficient. The
`depth 4 vs 8` cosine of exactly `1.000000` is the load-bearing number there, because it is a
statement about the vectors, not about the argmax.

## Reading 2 — training moves the recurrence off that fixed point

At cursor 160, depth 4 vs 8 is **no longer identical**: cosine `0.989746` and the **argmax differs
in 17.5% of slots**. The trained recurrence is still moving at the registered depth where the
untrained one had stopped.

So training did not merely rescale the block. It changed the **dynamical regime**: an iteration
that used to converge to a fixed point by depth 4 now keeps moving to depth 8. That is a
measurable property of the trained machine and it is not something the architecture declares.

## Reading 3 — the late passes resolve near-ties rather than sharpen the read

The marginal return collapses quickly. Between consecutive registered depths the argmax changes
in:

| transition | cursor 160 argmax agreement | so the answer changes in |
|---|---:|---:|
| depth 1 → 2 | 41.67% | **58.3%** of slots |
| depth 2 → 4 | 66.67% | 33.3% of slots |
| depth 4 → 8 | 82.50% | **17.5%** of slots |

And the logit **scale** saturates well before the argmax does: sd goes `0.630459 → 0.654277 →
0.658688` from depth 2 to depth 8, a **+4.5%** rise in total and only **+0.67%** across the last
four passes.

**That combination is the finding.** Across the last four passes the score spread barely moves
(+0.67%) while one answer in six flips. The late passes are therefore **reshuffling near-tied
decisions rather than improving the read**. They cost twice the block forward passes and they do
not make the winning score any larger.

**This is a hypothesis about the recorded alias concentration, and it is labelled as one.**
`READOUT_COLLAPSE_RESULT.md` recorded that at cursor 160 the model emits only 9 of 64 aliases with
`W36` at 44.3%, and its cause is still open. A mechanism that flips one near-tie in six at
constant score spread is a plausible contributor to a concentrated output distribution, because
near-tie resolution is exactly where a systematic bias would show up. **It is not established
here, and the concentration's cause remains open.**

## What the architecture could do with this

Two concrete questions this measurement puts in front of the architecture, neither of them
answered here:

1. **Is depth 8 earning its cost?** It flips 17.5% of answers relative to depth 4 at a scale
   change of 0.67%. Whether those flips are right more often than wrong is not measurable without
   the sealed targets, and is the natural object of an authorised run.
2. **Why does training make the recurrence non-convergent?** Untrained it is a contraction.
   Trained it is not. If the recursion is meant to settle, something in the training is pushing it
   away from settling, and the fixed-point reading of the recurrence is then not what the trained
   machine does.

## What is NOT established here

- **The input is approximate.** The rebuild reaches +0.781 correlation with the recorded logits.
  Every statement above is a comparison between depths on a shared input, which is why it
  survives that; but no absolute logit, no accuracy and no claim about the recorded run's
  decisions follows from it.
- **"Correct" is not measured.** Nothing here says whether any depth is right, only how the depths
  differ from each other.
- **120 probes, one arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`, world-typed reference
  slots only. Other slot types were not probed.
- **The near-tie-reshuffling reading is an inference from two numbers**, the scale change and the
  flip rate. It has not been demonstrated by inspecting the score distribution directly.
- **No GPU work was launched.** The reference encoder is CUDA-only by an explicit fail-closed
  guard and the installed torch is `2.11.0+cpu`.
