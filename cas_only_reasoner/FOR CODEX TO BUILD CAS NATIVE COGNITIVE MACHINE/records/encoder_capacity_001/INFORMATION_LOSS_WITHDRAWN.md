# Tenth self-correction — the "26-point information loss" was my probe's penalty, not the block

**Record:** `records/encoder_capacity_001/`
**Script:** `check_information_loss.py` (output `information_loss_check.txt`)
**Withdraws:** the headline of `STAGE_INFORMATION_RESULT.md`
**Spend:** $0.00. `torch` used only to deserialise checkpoints.

---

## What was claimed

`STAGE_INFORMATION_RESULT.md` reported that the registered `^6` architecture reduces focus-world
decodability from **63.83%** to **37.3%**, called it a loss of 26.5 points, and concluded that the
block "**discards 42% of the focus world's linearly available information**". It went on to explain
the analytic initialisation as "bypassing the block's information loss entirely".

**That conclusion does not follow from the measurement, and it is false.** The probe used a **fixed
ridge penalty of λ = 1.0** on every feature set. An invertible linear map followed by a mildly
nonlinear `tanh` preserves information; what it changes is *conditioning*. A penalty suited to raw
encoded slots can be badly suited to a transformed space.

## The check that refutes it

**A penalty sweep**, same features, same folds, λ from 1e-6 to 1e4:

| features | λ=1e-6 | λ=1e-4 | λ=0.01 | λ=0.1 | **λ=1.0** | λ=10 |
|---|---:|---:|---:|---:|---:|---:|
| `x` (encoded slot) | 64.54% | 64.54% | 64.54% | 64.72% | **63.65%** | 56.03% |
| `tanh(x)` | 64.72% | 64.72% | 64.72% | 64.72% | **63.83%** | 56.03% |
| **`^6_untrained(x)`** | **65.07%** | **66.31%** | 60.99% | 51.06% | **37.23%** | 21.81% |
| **`^6_trained(x)`** | **66.49%** | **66.31%** | 61.17% | 55.32% | **37.41%** | 19.86% |

**At λ = 1e-4 the block reads 66.31% and 66.31%. At λ = 1e-6 it reads 65.07% and 66.49% — higher
than the raw encoded slot's 64.72%.**

**The block does not discard information. It preserves all of it, and at a suitable penalty slightly
more.** The 37% was the probe misreading an ill-conditioned feature space.

**Whitening confirms it.** Standardising each feature set to unit variance and classifying at λ = 1:

| features | raw best over the sweep | whitened @ λ=1 |
|---|---:|---:|
| `x` | 64.72% | 66.31% |
| `tanh(x)` | 64.72% | 66.13% |
| **`^6_untrained(x)`** | 66.31% | **65.96%** |
| `^6_trained(x)` | 66.49% | 56.38% |

**The untrained block's output is informative and merely badly scaled** — whitening recovers it to
65.96%, level with the raw slot.

**And the map is not rank-deficient.** Singular values of the effective linear map
`merge_left @ left + merge_right @ right`:

| | largest | smallest | ratio | rank holding 99% of the sum |
|---|---:|---:|---:|---:|
| untrained | 0.707129 | 6.265253e-05 | 1.129e4 | **56 of 64** |
| trained | 14.851412 | 3.353687e-03 | 4.428e3 | **49 of 64** |

Full rank, badly conditioned. Information is not destroyed; it is stretched unevenly.

## The corrected finding

> The registered `^6` block **preserves** the focus world's linearly available information. At
> λ = 1e-4 it reads **66.31%** untrained and **66.31%** trained, against **64.72%** for the raw
> encoded slot. It does so **ill-conditioned** — the effective linear map's singular values span
> 1.1e4 (untrained) and 4.4e3 (trained) — so a fixed ridge penalty of λ = 1.0 misreads it as 37%.

**One of the record's claimed architectural defects is withdrawn.** There is no information loss in
the block to bypass, so the round-19 explanation of why the analytic initialisation works is also
withdrawn: it does not bypass a loss that does not exist.

## What survives, and what it is strengthened to

**The saturation sweep stands.** It involved no trained parameter and remains valid: decodability is
flat to slightly rising from `s` = 1 to `s` = 32 and only degrades past `s` = 64, so scalar
saturation is not a mechanism. Unaffected by the penalty error.

**The "training changes nothing" finding is strengthened, not weakened.** At λ = 1e-4 the untrained
and trained blocks read **66.31% and 66.31%** — identical to two decimal places. At λ = 1e-6, 65.07%
and 66.49%. On how much linearly decodable information the block carries about the focus world, 160
AdamW updates changed essentially nothing. That was the round-19 finding that mattered and it is now
cleaner.

## What the trained machine's 1.24% therefore is *not*

It is **not** information loss in the block. The information is present at **66.3%** through the
trained block, and it is present for the frozen readout too — `REACHABLE_SOLUTION_RESULT.md` measured
that the frozen rows realise **any** linear classifier exactly, at residual 2.798e-14. A linear read
of `^6_trained(x)` at λ = 1e-4 reaches 66.31%; the trained machine reaches 1.24%.

**So the failure is entirely in how the frozen readout's argmax is arranged, not in what the block
carries.** That is exactly what `CONCENTRATION_SOURCE_RESULT.md` measured independently: training
concentrates the readout's emissions from 57 distinct aliases to 27 on task-free inputs, and
`W36` to 44.3% on real ones.

**The record is back to two defects for the world-naming slot, not three: the trained block's
readout mapping concentrates, and the answer assembly has no composition (OS-026).** No
information-loss defect exists.

## Why this is the tenth self-correction and what it says about the method

**The check was run before the claim propagated**, on my own headline, by asking what the probe
would do if the claim were false. A penalty sweep and a whitening step are cheap, they cost nothing,
and they take one round.

The failure mode is worth naming: **a fixed hyperparameter applied across feature sets turns a
conditioning difference into an apparent capability difference.** The record's other probes use
λ = 1.0 too, and any of them that compares feature sets of different scaling inherits the same
risk. `measure_information_through_stages.py` was the first to compare across stages; the earlier
stage-by-stage numbers in this record should be read with the sweep in mind.

## What is NOT established here

- **The information is preserved; that does not mean the trained machine works.** It reads 1.24%.
  Preservation and usability are different claims, and this record makes only the first.
- **λ → 0 is not a free lunch.** A very small penalty is fitting noise as well as signal, and the
  `x` and `tanh(x)` rows barely move across λ = 1e-6 to 0.1 while the block rows move a great deal.
  The sweep identifies the block's conditioning; it does not recommend λ = 1e-6 for anything.
- **The whitened `^6_trained(x)` row is 56.38%**, below the untrained block's 65.96%. Whitening is a
  single global linear transform and is not the same correction the λ sweep applies. The two checks
  agree on the untrained block and are less clear on the trained one.
- **The comparison is on one quantity** — the focus-world alias at one representative slot per
  packet — and the encoded slot is rebuilt at +0.781 correlation with the recorded logits. Every
  comparison is between rows on the same rebuilt inputs.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`.
- **No GPU work was launched.**
