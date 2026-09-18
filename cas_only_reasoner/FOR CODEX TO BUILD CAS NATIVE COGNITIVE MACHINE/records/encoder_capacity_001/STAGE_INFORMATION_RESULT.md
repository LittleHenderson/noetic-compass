# The `^6` block's architecture costs 26 points of decodability, trained or not

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_information_through_stages.py` (output `information_through_stages.txt`)
**Spend:** $0.00. `torch` used only to deserialise checkpoints; ridge classification in the primal.

---

## The measurement

5-fold cross-validated ridge classification of the focus-world alias through each stage. Chance is
1/64 = 1.5625%.

| features | 5-fold CV | vs chance |
|---|---:|---:|
| **`x`** — the encoded slot itself | **63.65%** | 40.74× |
| **`tanh(x)`** — the analytic initialisation's effective first stage | **63.83%** | 40.85× |
| `tanh(left_untrained @ x)` | 51.95% | 33.25× |
| `tanh(left_trained @ x)` | 48.40% | 30.98× |
| **`^6_untrained(x)`** — the full block | **37.23%** | 23.83× |
| **`^6_trained(x)`** — the full block | **37.41%** | 23.94× |

Scalar saturation sweep, involving **no trained parameter**:

| scale `s` | 5-fold CV | mean &#124;pre-activation&#124; |
|---:|---:|---:|
| 0.25 | 52.84% | 0.0256 |
| 1.00 | 63.83% | 0.1024 |
| **8.00** | **65.78%** | 0.8195 |
| 16.00 | 65.07% | 1.6390 |
| 32.00 | 65.43% | 3.2780 |
| 64.00 | 60.11% | 6.5560 |
| 128.00 | 56.74% | 13.1120 |

## Finding 1 — saturation is not the mechanism

The sweep is **flat to slightly rising** from `s` = 1 to `s` = 32, peaking at **65.78%** at `s` = 8
where the mean absolute pre-activation is 0.82 — well into `tanh`'s curved region. It only degrades
past `s` = 64, where the pre-activations average 6.6 and the function is nearly a sign.

**So scalar saturation of the encoded slot does not discard the class information** over a wide and
relevant range. The hypothesis that the trained block's 19.73× growth in effective operator norm
(`COLLAPSE_CLAIM_WITHDRAWN.md`) destroyed the information by saturating `tanh` is **refuted**.

## Finding 2 — training changes the block's information content almost not at all

| | 5-fold CV |
|---|---:|
| `^6_untrained(x)` | **37.23%** |
| `^6_trained(x)` | **37.41%** |

**A difference of 0.18 percentage points.**

This is the finding, and it is worth stating flatly: **on how much linearly decodable information
the block preserves about the focus world, 160 AdamW updates changed essentially nothing.** The
trained block is not informationally worse than the untrained one. Whatever training did — and
`CONCENTRATION_SOURCE_RESULT.md` shows it concentrated the readout, from 57 distinct aliases to 27
on task-free inputs — **it did not do it by destroying information in the block.**

So the trained block's 1.24% readout performance against the untrained's ~6.9% overall is a change
in **what the frozen readout emits**, not in what the block carries.

## Finding 3 — the block's own architecture is the loss, and it is large

The chain from the input to the block's output loses a great deal, and none of it is training:

| stage | decodability | lost from the previous stage |
|---|---:|---:|
| `x` | 63.65% | — |
| `tanh(x)` | 63.83% | none (the elementwise `tanh` costs nothing) |
| `tanh(left @ x)`, one 64×64 matrix and a `tanh` | 48.40–51.95% | **≈ 12–15 points** |
| **full `^6`** — `merge(concat(tanh(left x), tanh(right x)))` | **37.2–37.4%** | **≈ 12–15 more** |

**The registered `^6` architecture reduces the focus world's linear decodability from 63.83% to
37.3% — a loss of 26.5 points — and it does so whether its weights are trained or random.**

That gives a **ceiling** for the trained run which nothing in that run could have exceeded: a free
linear readout applied to `^6_trained(x)` reaches **37.41%**, so no readout of any kind, however
well trained, could have read the focus world through this block above roughly 37% on this measure.
The learner reached 1.24%.

## Finding 4 — this is why the analytic initialisation works

The analytic construction sets exactly

    left = I₆₄,  right = 0,  merge = [T | 0]   =>   ^6(x) = T · tanh(x)

**the right branch contributes `tanh(0) = 0` and its half of `merge` is zero, so the two-branch
merge collapses to a single linear map with no lossful composition.** And `tanh(x)` measures
**63.83%** — identical to the input.

So the analytic initialisation does not merely fit a good `T`. **It bypasses the block's information
loss entirely**, and that is a second, independent reason it reaches **62.94% direct** where the
trained block's ceiling is 37%.

The two findings now fit together with no loose ends:

| | decodability ceiling through the block | what the machine actually reads |
|---|---:|---:|
| trained `^6` | **37.41%** (free readout) | **1.24%** (frozen readout) |
| analytic `^6` = `T·tanh` | **62.94%** (frozen readout realised exactly) | — |

**The trained machine fails twice over**: the block costs it 26 points before the readout is even
consulted, and the frozen readout then extracts almost none of the 37 that remain — because
training concentrated its emissions (`CONCENTRATION_SOURCE_RESULT.md`).

## What this means for the architecture

**A 64 → 64 → 128 → 64 block with two `tanh` branches and a `merge`, as registered, discards 42% of
the focus world's linearly available information.** That is a measured, architectural cost, present
at initialisation and unchanged by training. It is not a training defect, not a loss defect, and not
an encoder defect.

The analytic initialisation is, in effect, **the degenerate case of that architecture in which the
second branch is switched off** — and it is worth 26 points. That is a strong hint that the block's
two-branch structure is not earning its cost on this task, and that the honest architectural
question is whether `merge(concat(tanh(left x), tanh(right x)))` is the right shape at all.

**No change is proposed here.** This record measures a cost; it does not propose removing the
branch, and any such change is a contract question (the `^6` contract fixes `neural_transform_id =
cas.op.decompose.v1`).

## What is NOT established here

- **Nothing was scored by the machine's own checker.** These are free-readout decodability figures,
  not the whole-answer exact-match metric.
- **The encoded slot is rebuilt**, at +0.781 correlation with the recorded logits
  (`RECONSTRUCTION_GAP.md`). Every row is the same rebuilt input through a different stage, so the
  **comparisons between rows** are valid; no absolute number is the machine's.
- **37.41% is a ceiling for a linear readout, not for every readout.** A nonlinear readout might
  extract more from `^6_trained(x)`. Nothing here establishes that 37% is the maximum attainable.
- **The block's loss is measured on one quantity** — the focus-world alias at one representative
  slot per packet — and says nothing about the other fields the block feeds.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`.
- **No claim that the two-branch structure is wrong.** It may carry information this measurement does
  not probe, and the branch is what `cas.op.decompose.v1` defines.
- **No GPU work was launched.**
