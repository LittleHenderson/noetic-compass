# The alias concentration has three separable causes, and training is the largest

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_input_independence.py` (output `input_independence.txt`)
**Spend:** $0.00. `torch` used only to deserialise checkpoints; all arithmetic on plain lists.

---

## Why this test is not limited by the reconstruction gap

`RECONSTRUCTION_GAP.md` measures the pure-Python rebuild of the **encoder** at +0.781 correlation
with the recorded logits, so nothing depending on a rebuilt encoded slot may be treated as the
machine's. **This test never touches the encoder.** The block, the recurrence and the frozen readout
are exact for the saved weights and the frozen rows, so feeding *invented* inputs through them is
exact arithmetic on the real trained parameters.

## The measurement

210 inputs per regime, both checkpoints, at depth 1 and depth 8:

| checkpoint | depth | regime | distinct | commonest | share | entropy |
|---|---:|---|---:|---|---:|---:|
| cursor 0 | 1 | pseudo-random unit vectors | **58** | W44 | 4.8% | 5.586 |
| cursor 0 | 1 | one constant vector | 1 | W58 | 100.0% | 0.000 |
| cursor 0 | 8 | pseudo-random unit vectors | **57** | W36 | 4.8% | 5.535 |
| cursor 0 | 8 | one constant vector | 1 | W58 | 100.0% | 0.000 |
| cursor 160 | 1 | pseudo-random unit vectors | **44** | W47 | 10.0% | 4.853 |
| cursor 160 | 1 | one constant vector | 1 | W26 | 100.0% | 0.000 |
| **cursor 160** | **8** | **pseudo-random unit vectors** | **27** | **W40** | **25.2%** | **3.752** |
| cursor 160 | 8 | one constant vector | 1 | W40 | 100.0% | 0.000 |

For reference: a **uniform** distribution over 64 aliases is 64 distinct, 1.6% commonest, 6.000
bits. The **recorded** distribution at cursor 160 over the real world-typed reference slots is
**9 distinct, `W36` at 44.3%, 2.516 bits**.

**The constant-input row is the control.** One input, one output, 1 distinct alias, 100% — the
pipeline is deterministic, and what it says when told nothing differs between checkpoints (W58
untrained, W40 trained).

## The answer to the open question

Random unit vectors contain no task information at all. Feeding them in isolates what the weights
do on their own, and the chain is monotone at every stage:

| stage | distinct | commonest share | entropy |
|---|---:|---:|---:|
| uniform, no machine at all | 64 | 1.6% | 6.000 |
| **untrained block, one pass** (cursor 0, depth 1, random) | **58** | 4.8% | 5.586 |
| **+ the recurrence** (cursor 0, depth 8, random) | 57 | 4.8% | 5.535 |
| **+ training the block** (cursor 160, depth 1, random) | **44** | 10.0% | 4.853 |
| **+ the recurrence again** (cursor 160, depth 8, random) | **27** | 25.2% | 3.752 |
| **+ the real encoded slots** (recorded, cursor 160) | **9** | 44.3% | 2.516 |

**Training the block alone moves the readout from 58 distinct aliases to 44, and from 4.8% to
10.0% on the commonest, on inputs it has never seen.** Adding the recurrence takes it to 27 and
25.2%. The real inputs take it the rest of the way to 9 and 44.3%.

**So the concentration is not caused by the inputs, and not by the encoder.** The largest single
contributor is the training, and it is visible with inputs that carry no information whatsoever.
The real encoded slots are a further contributor, and the recurrence is a third.

## The apparent contradiction from rounds 10 and 11 is resolved

Round 10 claimed the trained block "collapses onto an input-independent fixed point". Round 11
refuted that using the block's own output vectors: the weights **grew** (effective operator norm
0.361559 → 7.135410, ×19.73) and the block became **more** input-sensitive (mean pairwise cosine
0.563576 → 0.491361, rms-from-mean 0.028791 → 0.280260). Round 11 therefore withdrew the collapse
claim.

**Both measurements are correct, and this table shows how they fit together.** The trained block's
output vector varies *more* across inputs while the **readout's argmax varies less** — 58 distinct
aliases to 44 at depth 1, and 57 to 27 at depth 8, on identical random inputs.

The two are not in conflict. Training makes the block's output **larger and more variable**, and
simultaneously pushes it into a region where the frozen readout's argmax is decided by fewer of its
rows. The output vector spreads; what the readout *says* narrows.

**The withdrawn claim was wrong about the mechanism and right about the effect.** The effect is real
and is now measured with no encoder in the loop. What is not true is that the output vector is
constant; what is true is that its readout projections concentrate.

## What this means for the architecture

The concentration is a **property of the trained weights, measured on task-free inputs**. That
places it squarely in the plastic block and its interaction with the frozen readout, and it means:

- it is **not** an encoder defect, so no encoder change addresses it;
- it is **not** a data-coverage defect, so more course variety does not address it;
- it **is** visible at depth 1, so it is the block's own doing, with the recurrence as an amplifier
  rather than the origin.

It does **not** say the concentration is harmful. A concentrated readout is not automatically a
wrong one, and nothing here measures correctness — the targets are sealed. What it does say is that
**the machine's answer at a world-typed slot is substantially determined before its input is
consulted**, and that is a property an architecture review should account for.

## What is NOT established here

- **This is not a run and nothing was scored.** The targets are sealed; no accuracy follows from any
  number here. Concentration is a distributional fact, not an error rate.
- **The regimes are not the machine's real inputs.** Regimes 2 and 3 are invented. They isolate the
  weights; they are not a claim about the course.
- **The four arithmetic causes are separated, not attributed.** Training, the recurrence and the
  input all contribute; nothing here partitions the total effect quantitatively, and the stages are
  not independent of one another.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`. The other five runs of the study were
  not probed.
- **Depth 1 and depth 8 only.** Depths 2 and 4 were not measured in this test.
- **`W40` and `W36` are different aliases.** The commonest alias under random inputs at cursor 160 is
  `W40`, not the recorded `W36`. So the weights' own preference and the recorded outcome are related
  but not identical, and the difference is the input's contribution.
- **No GPU work was launched.**
