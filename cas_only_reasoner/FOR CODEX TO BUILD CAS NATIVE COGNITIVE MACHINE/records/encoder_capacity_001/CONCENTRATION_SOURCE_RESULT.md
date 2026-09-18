# The concentration is the training's, and the analytic fit does not share it

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_concentration_source.py` (output `concentration_source.txt`)
**Spend:** $0.00. `torch` used only to deserialise checkpoints and read the frozen public course.

---

## The probe

210 **pseudo-random unit vectors** — inputs carrying no task information at all — fed through four
parameterisations on the same recurrence, the same frozen readout, and the same inputs. **The encoder
is never touched**, so `RECONSTRUCTION_GAP.md`'s +0.781 correlation limits nothing here.

| parameterisation | depth | distinct | commonest | share | entropy |
|---|---:|---:|---|---:|---:|
| **identity — no block at all**, `f(x) = x` | 1 | **59** | W5 | 3.3% | **5.752** |
| identity — no block at all | 8 | **59** | W5 | 3.3% | **5.752** |
| untrained, cursor 0 | 1 | 58 | W44 | 4.8% | 5.586 |
| untrained, cursor 0 | 8 | 57 | W36 | 4.8% | 5.535 |
| trained, cursor 160 | 1 | 44 | W47 | 10.0% | 4.853 |
| **trained, cursor 160** | **8** | **27** | **W40** | **25.2%** | **3.752** |
| **analytic — arm A** | 1 | **24** | W15 | 10.0% | 4.394 |
| **analytic — arm A** | 8 | **24** | W22 | **8.6%** | **4.404** |
| *uniform, no machine at all* | — | *64* | — | *1.6%* | *6.000* |
| *recorded, real slots, cursor 160* | *8* | *9* | *W36* | *44.3%* | *2.516* |

## Finding 1 — the frozen readout's geometry is nearly uniform

**The identity row involves no parameter: `f(x) = x` and the readout's argmax is taken directly.**
It gives **59 distinct aliases, 3.3% commonest, 5.752 bits** — close to the uniform 64 / 1.6% /
6.000.

So the frozen Rademacher readout is **not** inherently biased toward a few symbols. Whatever
concentration the machine shows is produced by the parameters, not by the codebook's geometry. That
rules out one whole family of explanations and it is the reason the identity row was worth running.

## Finding 2 — training is the cause, and the recurrence amplifies it

The untrained block leaves the distribution nearly as spread as the identity (58 → 57 distinct,
4.8%). The trained block does not:

| | distinct | commonest share | entropy |
|---|---:|---:|---:|
| untrained, depth 1 | 58 | 4.8% | 5.586 |
| trained, depth 1 | 44 | 10.0% | 4.853 |
| untrained, depth 8 | 57 | 4.8% | 5.535 |
| **trained, depth 8** | **27** | **25.2%** | **3.752** |

Training alone more than doubles the commonest share at depth 1, and the recurrence more than
doubles it again. This is on inputs the block has never seen.

## Finding 3 — the analytic fit does not share the trained block's concentration

On the same task-free inputs the closed-form `T` gives a distribution that is **markedly more spread
than the trained block's**:

| | distinct | commonest share | entropy |
|---|---:|---:|---:|
| trained, depth 8 | 27 | **25.2%** | **3.752** |
| **analytic, depth 8** | 24 | **8.6%** | **4.404** |

The counts are comparable — 27 and 24 — and the **shares are not**: 25.2% against 8.6%, and
0.65 bits of entropy apart. The trained block returns to one alias a quarter of the time whatever
it is given; the analytic parameters do so under a tenth of the time.

**And the analytic fit is stable through the recurrence** where the trained block is not:

| | depth 1 | depth 8 | change |
|---|---:|---:|---:|
| trained | 4.853 | 3.752 | **−1.101 bits** |
| **analytic** | 4.394 | **4.404** | **+0.010 bits** |

The recurrence costs the analytic fit nothing at all on task-free inputs. It costs the trained block
a full bit of entropy. That is the same asymmetry `RECURRENCE_AWARE_FIT_RESULT.md` found from the
other direction.

## Finding 4 — the trained block collapses further on *real* inputs; the analytic fit does not

Side by side, the same measurement on task-free inputs and on the machine's real ones:

| | task-free inputs | real encoded slots |
|---|---|---|
| trained, depth 8 | 27 distinct, **25.2%** | **9 distinct, 44.3%** (recorded) |
| analytic, depth 8 | 24 distinct, **8.6%** | **24 distinct, 6.9%** (out-of-fold, `preparation_report.txt`) |

**The analytic fit behaves the same on both** — around 24 distinct aliases with the commonest under
10%. **The trained block behaves very differently**: spread-ish on invented inputs, severely
concentrated on real ones. So the trained block's concentration is driven specifically by the
**task distribution** — it is doing something to real slots that it does not do to random ones —
while the analytic fit is not.

That is a sharper statement than "training concentrates the readout". It says the trained block
**loses variety precisely where the task lives.**

## What this does for arm A

**G6's prediction is now supported by an encoder-free measurement.** The preparation supported it
through the rebuilt encoder; this supports it through inputs that need no encoder at all. The
conclusion is the same from both directions:

> The analytic parameters do not concentrate the way the trained block does, on either the task
> distribution or on inputs carrying no information.

**And it adds a prediction the preparation could not make.** The recurrence costs the analytic fit
**+0.010 bits** of entropy on task-free inputs and costs the trained block **−1.101 bits**. If arm A
runs and the recurrence turns out to be costly for it, that contradicts this measurement, not merely
the approximate rebuild.

## What is NOT established here

- **Nothing was scored.** Entropy and share are distributional facts. They say nothing about
  correctness, and the targets are sealed. **A spread readout is not automatically a right one** —
  the analytic fit spreads while reaching 62.06%, and the trained block concentrates while reaching
  1.24%, but nothing here shows the spread *causes* the accuracy.
- **The task-free inputs are invented.** They isolate the parameters; they are not a claim about the
  course.
- **The analytic `T` here is a single fold's fit**, not the per-fold set the preparation uses. It is
  a valid parameterisation for a task-free probe, and it is not the arm's artifact.
- **The four rows are not independent.** Each adds to the one above it, so the differences include
  interactions as well as the named change.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`.
- **Depth 1 and 8 only.** Depths 2 and 4 were not measured here.
- **The concentration is still not shown to be harmful.** Nothing in this record establishes that
  reducing it improves anything.
- **No GPU work was launched.**
