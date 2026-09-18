# Ninth self-correction — the "collapse" claim is unsupported, and the cause is open

> ## PARTLY RESOLVED — `INPUT_INDEPENDENCE_RESULT.md`
>
> The withdrawal below stands: the **mechanism** claimed (the block's output vector becoming nearly
> constant) is refuted, the weights grew and the block became more input-sensitive. **But the
> effect it was trying to describe is real, and is now measured with no encoder in the loop.**
>
> Feeding 210 **pseudo-random unit vectors** — inputs carrying no task information — through the
> saved weights and the frozen readout:
>
> | | distinct aliases | commonest share | entropy |
> |---|---:|---:|---:|
> | untrained block, depth 1 | **58** | 4.8% | 5.586 |
> | untrained block, depth 8 | 57 | 4.8% | 5.535 |
> | **trained block, depth 1** | **44** | 10.0% | 4.853 |
> | **trained block, depth 8** | **27** | **25.2%** | 3.752 |
> | recorded, real slots | 9 | 44.3% | 2.516 |
>
> Training alone narrows the readout's variety from 58 distinct aliases to 44 at depth 1 and from 57
> to 27 at depth 8, on inputs it has never seen.
>
> **So round 10 was wrong about the mechanism and right about the effect.** The output vector is not
> constant — it spreads *more* after training — while the readout's argmax concentrates. The vector
> spreads; what the readout says narrows. Both measurements are correct and they are not in
> conflict.

**Record:** `records/encoder_capacity_001/`
**Scripts:** `measure_block_collapse.py` (output `block_collapse.txt`),
`measure_recurrence_collapse.py` (output `recurrence_collapse.txt`)
**Spend:** $0.00. `torch` used only to deserialise frozen checkpoints; all arithmetic on plain
Python lists.
**Withdraws:** the mechanism claimed in `READOUT_COLLAPSE_RESULT.md`.

---

## What was claimed, and what the check found

`READOUT_COLLAPSE_RESULT.md` reported a real recorded fact and offered a cause for it:

- **the fact**, read from the recorded decisions: at cursor 160 the model emits only **9 of the
  64 world aliases** across the 210 world-typed reference slots, **`W36` accounts for 44.3%** of
  them, and the two world-typed slots of a `definition` question agree at exactly that rate;
- **the cause offered**: "the trained block has collapsed onto an input-independent fixed point."

The recorded fact stands. **The cause does not.** Two checks were run against the saved weights.

### Check 1 — the weights grew, they did not shrink

| matrix | cursor 0 | cursor 160 | ratio |
|---|---:|---:|---:|
| `left.weight` | 4.624080 | 7.132143 | 1.542392 |
| `right.weight` | 4.575654 | 7.097140 | 1.551066 |
| `merge` left half | 3.257300 | 6.227643 | 1.911903 |
| `merge` right half | 3.225275 | 5.946896 | 1.843842 |
| effective linear map, operator norm | **0.361559** | **7.135410** | **19.73×** |

The block is not approaching the zero map. It became a **much higher-gain** map. With an
operator norm of 7.14 and unit-norm inputs, `tanh` saturates, so the module is closer to
`merge @ sign(...)` than to a shrinkage.

### Check 2 — the block is more input-sensitive after training, not less

Same 2,598 real encoded slot vectors through both checkpoints. Output spread:

| checkpoint | mean pairwise cosine | rms from mean | mean norm | rms / norm |
|---|---:|---:|---:|---:|
| 0 | 0.563576 | 0.028791 | 0.350351 | 0.0822 |
| 160 | **0.491361** | **0.280260** | 3.060109 | **0.0916** |

Mean cosine fell, the rms-from-mean rose 9.7×, and the spread as a fraction of the output norm
rose slightly. **The trained block distinguishes its inputs more than the initial one does.**

### Check 3 — the reconstruction does not reproduce the recorded distribution

> **Downgraded. See `RECONSTRUCTION_GAP.md`.** This check used the pure-Python rebuild, which is
> now measured to reach only **+0.781 correlation** with the recorded logit vector and cannot be
> validated in this environment at all: the reference encoder raises `TYPED_ENCODER_CUDA_ONLY` on
> CPU and the installed torch is `2.11.0+cpu`. **Checks 1 and 2 do not use the rebuild and carry
> the refutation on their own**, so the withdrawal below stands; this check is supporting only.

`measure_recurrence_collapse.py` rebuilds the learner's whole forward pass in pure Python from
the source: the encoded slot, then `recurrence.run_passes` with `lambda_ = 0.5`,
`epsilon = 1e-6`, `depth = 8`, carrying `^6`'s own output back into its input each pass, then
the frozen readout argmax. Over 120 world-typed reference slots:

| checkpoint | distinct aliases emitted | most emitted | spread after 8 passes (rms / norm) |
|---|---:|---|---:|
| 0 | 16 of 64 | `W36` = 34 = 28.3% | 0.0814 |
| **160** | **15 of 64** | `W8` = 22 = 18.3% | **0.0901** |

**The recorded distribution at cursor 160 is 9 distinct aliases with `W36` at 44.3%. The
reconstruction gives 15 distinct with `W8` at 18.3%.** It does not reproduce it, so it does not
validate, and it cannot be used to locate the cause.

## What that leaves

- **The recorded concentration is a fact** about the run: 9 of 64 aliases, `W36` at 44.3%,
  focus alias ranked 6th or worse in 157 of 210 world-typed slots. It was read from the
  recorded decisions, not from any model of them.
- **Its cause is not established.** The two candidates — an input-independent component in the
  block, or something in the real forward pass this reconstruction does not capture — are not
  distinguished. The reconstruction misses at least one thing about how the learner runs; what
  that is has not been found.
- **The block did not collapse.** That specific claim is withdrawn. `READOUT_COLLAPSE_RESULT.md`
  is annotated accordingly and kept, because deleting a wrong mechanism is worse than labelling
  one.
- **The limits section of that record was right to flag this.** It said: "'Constant' is a
  description of the emitted symbols, not a proof about the block's output vector. Whether the
  block's 64-dimensional output vector itself is nearly constant, or merely aligned with a few
  readout rows, has not been measured, and the two would need different repairs." It has now
  been measured, and the answer is **neither**: the output vector is spread and input-dependent.

## What still stands, unchanged

Nothing else in the investigation depends on the collapse mechanism.

| finding | status |
|---|---|
| real encoded slot decodes the focus world at 63.65%, 5-fold CV | stands |
| frozen codebook selects all 65 world symbols, min margin 0.7573 | stands |
| frozen readout imposes no constraint, residual 2.798e-14 | stands |
| registered `^6` class reaches 63.83%, exact realisation, residual 0.0 | stands |
| the trained learner reaches 1.24% on that quantity | stands |
| the training objective had not converged at the contract ceiling | stands |
| **the recorded output concentrates on 9 of 64 aliases, `W36` at 44.3%** | **stands** |
| **the cause of that concentration** | **OPEN** |
| Defect B — `edge_account` needs 16 binary decisions, above 10 bits never once right | stands |
| Defect A — reference slots disagree | **withdrawn** (previous round, artifact) |

## Consequence for the phase-0 predictions

**P5 and gates G6/G7 are kept, with their justification restated.** They key on the emitted
alias distribution — more than 9 distinct aliases, commonest below 44.3%, focus alias ranked
first in more than 10 of 210 slots. Those are direct readings of a recorded quantity and they do
not depend on why the concentration happens.

What changes is the interpretation. A pass would no longer read as "the collapse was repaired",
because no collapse was established. It would read as: **the analytic solve moves the block's
readout behaviour off a concentrated distribution** — a real and useful effect, with the
mechanism left open.

## What is NOT established here

- **The reconstruction is not validated.** It reproduces neither the recorded alias distribution
  nor any other recorded selection, so its internals are not evidence about the learner.
- **The cause of the recorded concentration is unknown.** Neither an input-independent
  component nor any specific hyperparameter has been implicated.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`.
- **Nothing was executed on a device.** The checkpoints were deserialised only.
