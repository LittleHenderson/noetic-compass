# The registered `^6` block collapses to a constant, and teaching deepens the collapse

> # WITHDRAWAL — the MECHANISM in this file is withdrawn. Read `COLLAPSE_CLAIM_WITHDRAWN.md`.
>
> The *recorded fact* below stands: at cursor 160 the model emits only 9 of the 64 world aliases
> across the 210 world-typed reference slots, `W36` accounts for 44.3% of them, and the two
> world-typed slots of a `definition` question agree at exactly that rate. That was read from
> the recorded decisions and nothing here retracts it.
>
> The **cause** claimed here does not stand. "The trained block has collapsed onto an
> input-independent fixed point" is refuted by three checks against the saved weights:
>
> - the weights **grew**, 1.54× to 1.91×, and the effective linear map's operator norm went
>   **0.361559 → 7.135410 (19.73×)**;
> - the trained block is **more** input-sensitive than the initial one: over 2,598 real encoded
>   slots, mean pairwise cosine fell 0.563576 → 0.491361 and rms-from-mean rose 0.028791 →
>   0.280260;
> - a full pure-Python rebuild of the learner's forward pass, recurrence included, gives
>   **15 distinct aliases with `W8` at 18.3%** where the record shows **9 with `W36` at 44.3%**,
>   so it does not reproduce and does not validate.
>
> **The recorded concentration is a fact; its cause is OPEN.** Defect A in
> `TWO_DEFECTS_RESULT.md` was already withdrawn as an artifact of counting a supplied
> identifier. **Defect B stands**, and so does every other measurement in this record.
>
> This file is kept rather than deleted, because deleting a wrong mechanism is worse than
> labelling one.

**Record:** `records/encoder_capacity_001/`
**Scripts:** `measure_joint_binding.py` (output `joint_binding.txt`), plus the alias survey in
`alias_survey.txt`
**Spend:** $0.00. Pure standard library. No model, no GPU, no target opened, no provider.
**Status:** the eighth self-correction in this record. It withdraws `TWO_DEFECTS_RESULT.md`
Defect A and restores the identification hypothesis it had replaced.

---

## First, the error that produced Defect A

`measure_world_consistency.py` reported that **70 of 70 `definition` answers name the focus
world** and concluded that identification is not the defect. That conclusion is wrong, and the
measurement that produced it was measuring the wrong thing.

A `definition` answer has three fields:

    function_ref = world-6f7b0ac1f.../decl/function     <- a 64-way decision
    kind_ref     = world-7afc0b967.../decl/kind         <- a 64-way decision
    whole        = world-7afc0b967.../n2                <- a node decision, world supplied

The `whole` field carries the focus world's identifier. The world component of it is **not
decided** — the node-typed slot's symbols are `N0 … Nk`, nodes *of the focus world*, and the
assembly prepends the focus world's identifier because that is the slot's scope. Verified on
three packets: the node slot selected `N2`, `N2`, `N0` and `whole` read `/n2`, `/n2`, `/n0`.

So the first two measurements in that script were polluted by a supplied identifier, and
"names the focus world in 70 of 70 answers" was a tautology. **Defect A is withdrawn.** It was
not a referential-consistency defect; it was an artifact of counting a field that was handed to
the model.

## The measurement that is clean

`measure_joint_binding.py` looks only at slots whose alphabet is the 64 world aliases — the
slots where the world is genuinely decided. Nothing supplied enters it.

Focus-alias rank within each world-typed slot's own ranking, over 70 `context` slots and 140
`definition` slots:

| cursor | ranked #1 | #2 | #3 | #4 | #5 | **#6 or worse** | n |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 (before teaching) | 6 | 4 | 0 | 16 | 2 | **182** | 210 |
| 160 (after teaching) | 10 | 8 | 6 | 15 | 14 | **157** | 210 |

With 64 candidates, uniform chance puts the focus alias in the top 5 about 7.81% of the time.
Measured: **13.33%** before teaching and **25.24%** after. So there is roughly 3.2× chance of
real signal — and it is buried under a much larger constant.

## The constant

What the model actually emits at those 210 slots:

| cursor | distinct aliases emitted | entropy | most emitted | top 5 share |
|---|---:|---:|---|---:|
| 0 | **26** of 64 | **4.164 bits** (max 6.0) | `W49` = 32 = 15.2% | 52.9% |
| 160 | **9** of 64 | **2.516 bits** (max 6.0) | **`W36` = 93 = 44.3%** | **86.2%** |

At cursor 160 the machine emits **`W36` in 93 of 210 world-typed reference slots**, and **never
emits 55 of the 64 aliases at all**. It has stopped being a function of its input.

The corroborating number is exact. `definition` questions have two world-typed slots, and those
two slots **agree with each other 44.3% of the time** — which is precisely the rate at which the
first slot emits `W36`. Against a 1/64 = 1.56% chance of two independent picks agreeing, 44.3%
agreement means the two slots are not making two decisions: they are emitting the same constant.

## What teaching did

Teaching made the readout **more concentrated and not more accurate**:

- distinct aliases emitted: **26 → 9**
- output entropy: **4.164 → 2.516 bits**
- the commonest emission: **15.2% → 44.3%**
- focus alias at rank 1: **2.86% → 4.76%**

That is the signature of a **degenerate optimum**: the trained block outputs something close to
a fixed vector, the frozen readout turns it into `W36`, and the batch loss keeps falling because
the target symbol's *relative* rank inside the slot improves even when the answer is nonsense.

It also explains, with no further assumptions:

- why the loss was still falling and the gradient norm still rising at the contract ceiling
  (`UPDATE_TRAJECTORY_RESULT.md`) — the run was descending into the collapse, not converging on
  a solution;
- why the exposed course improved 6.9149% → 33.5106% while transfer did not
  (`PANEL_MISREAD_CORRECTION.md`) — `correspondence` and `reach` do not run through the
  64-alias slots;
- why `definition` and `context` are 0/70 and why more updates would make it worse
  (OS-022).

## Does a binding fix it? No.

Restoring the identification reading raises the obvious repair: decide the world **once** per
question, jointly across the slots that must agree, and apply the result everywhere. That was
measured from the recorded scores.

| cursor | questions where independent picks name the focus world | joint decision names it | questions rescued |
|---|---:|---:|---:|
| 0 | 6 / 140 = 4.29% | 4 / 140 = 2.86% | 1 |
| 160 | 10 / 140 = 7.14% | 10 / 140 = 7.14% | 3 |

**Joint binding changes nothing.** It cannot: the model's two slots are not disagreeing about
two different worlds, they are both emitting the same wrong constant. There is no incoherence to
repair, and the constraint has nothing to work with. Referential consistency is therefore
**not** the missing piece, and the second half of Defect A's proposed value is withdrawn too.

## What this establishes

> The registered `^6` block, trained for 160 AdamW steps at learning rate 3e-3, does not learn
> to read the world. It collapses onto a near-constant output. After teaching, 55 of the 64
> world aliases are never emitted at all and one of them is emitted 44.3% of the time.

The chain is now closed end to end, and every link is a measurement:

| step | measurement |
|---|---|
| the information is present in the encoded slot | 63.65% free-readout, 5-fold CV |
| the frozen codebook can select every world | 65/65 vertices, min normalised margin 0.7573 |
| the frozen readout is not a constraint | 100.00% argmax agreement, residual 2.798e-14 |
| the registered module can express the solution exactly | `forward(x) = T·tanh(x)`, residual 0.0 |
| **the trained block does not find it — it collapses** | **9 of 64 aliases emitted, entropy 2.516 bits** |

So the defect is neither capacity, nor representation, nor the readout, nor the step budget by
itself. It is that **the training procedure drives the plastic block to an input-independent
fixed point**, and no amount of the same training repairs that. The contract ceiling of 176
updates does not cause it; it limits how far the collapse can run.

**This is the strongest evidence yet that the analytic initialisation is aimed at the right
target**, and it also raises its priority: pinning the block at `T = R⁻¹Wᵀ` replaces a constant
with a fitted input-dependent map that already reaches 63.83% on this exact quantity. The
proposal is no longer "maybe under-training is the problem"; it is "the training converges to a
constant, so do not rely on it to find the solution."

## What is NOT established here

- **Nothing was executed.** Every number is read from recorded scores and public packets.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`. The other five runs of the study
  have not been surveyed for the same collapse.
- **"Constant" is a description of the emitted symbols, not a proof about the block's output
  vector.** The claim is that the *readout's argmax* is dominated by an input-independent
  component. Whether the block's 64-dimensional output vector itself is nearly constant, or
  merely aligned with a few readout rows, has not been measured, and the two would need
  different repairs.
- **The collapse is not shown to be caused by any specific hyperparameter.** Learning rate
  3e-3, weight decay 0.01, 160 steps and the frozen random readout are all candidates and none
  has been isolated.
- **3.2× chance of real signal survives**, so the block is not entirely dead; the statement is
  about domination, not absence.
- **A design for preventing the collapse is not proposed here.** This record establishes the
  defect and its measurement.
