# What the 160 recorded updates actually did

**Record:** `records/encoder_capacity_001/`
**Run read:** `records/typed_matched_001/receipt_20260919_m/` (arm `MIXED_SAME_ITEMS`,
condition `MIXED_SAME_ITEMS`, seed `20260919`)
**Script:** `measure_update_trajectory.py` (pure standard library; no torch, no device,
no network, no wall-clock input)
**Raw output:** `update_trajectory.txt`
**Spend:** $0.00. Nothing was executed. Every number below is read from bytes that were
already on disk.

---

## Why this measurement was needed

`STATUS.md` recorded an honesty limit on the earlier result: the closed-form ridge solve
reaches 63.65% while the learner reaches 1.24%, and that contrast "establishes
*representability*, not SGD learnability in 160 steps." The under-training reading was
explicitly a hypothesis, not a measured fact.

This record settles it from the run's own telemetry. Two questions:

- **A.** Did answer accuracy improve across the 160 updates?
- **B.** Had the training objective converged when the run stopped?

---

## A. The development panel did not improve — and that is not the whole story

> **CORRECTED. See `PANEL_MISREAD_CORRECTION.md`.** This section was originally headed
> "Accuracy did not improve at all." Every number below is right; the heading was misleading in
> the direction that matters. The 59-question **development** panel is not the course the
> learner was taught. On the **exposed** course the same run improved from **39/564 = 6.9149%**
> to **189/564 = 33.5106%** (+26.5957 pp, 4.85×), with `correspondence` going from 0/88 to
> 82/88. The learner was not failing to learn. It was learning the exposed course and not
> transferring. Read the corrected section below, not the heading above it.

The run scored the **same frozen development curriculum** at five cursors, so the five scorings
are directly comparable. Each question is scored by exact match against a single admissible
answer (`admissible_answer_count: 1`, rule `direct_contains_v1`), so a scored question is right
only if the whole assembled answer is right.

The panels, from the run's own `design` block in `worker_report.json`:

| panel | field | size | boundary as recorded |
|---|---|---:|---|
| exposed registry course | `registry_packets`, `initial_and_final_prediction_packets` | **564** | the course the learner was taught |
| development | `development_packets` | **59** | `PUBLIC_DEVELOPMENT_TOPOLOGIES_NO_TRAINING_CORRECTIONS_NO_FINAL_PANEL` |
| retention | `retention_packets` | **96** | `OTHER_QUESTION_TEACHING_SAME_PUBLIC_BANK_NO_PARTS_REACH_EDGE_CORRECTIONS_NOT_CONTENT_UNSEEN` |

Development panel at the five checkpoints:

| cursor | correct | total | accuracy |
|---:|---:|---:|---:|
| 0 | 0 | 59 | 0.0000% |
| 40 | 0 | 59 | 0.0000% |
| 80 | 1 | 59 | 1.6949% |
| 120 | 1 | 59 | 1.6949% |
| 160 | 0 | 59 | 0.0000% |

Change over the window: **+0.0000 percentage points.**

By kind (correct/total):

| kind | @0 | @40 | @80 | @120 | @160 |
|---|---:|---:|---:|---:|---:|
| parts | 0/6 | 0/6 | 0/6 | 0/6 | 0/6 |
| reach | 0/53 | 0/53 | 1/53 | 1/53 | 0/53 |

The single correct answer appears at cursors 80 and 120 and is lost again by 160.

### The other two panels, which this section originally omitted

From `result.json` `summary`:

| panel | before | after | change |
|---|---:|---:|---:|
| **exposed registry course (564)** | **39/564 = 6.9149%** | **189/564 = 33.5106%** | **+26.5957 pp, 4.85×** |
| development (59) | 0/59 = 0.0000% | 0/59 = 0.0000% | 0 |
| retention (96) | 45/96 = 46.8750% | 34/96 = 35.4167% | **−11.4583 pp** |

`learning_advantage_established` is **False**. `starting_competence_met` is **False**.

Per kind on the exposed course, before → after: correspondence 0/88 → **82/88**, reach 25/107 →
**81/107**, parts 6/53 → 12/53, analogy 5/70 → 11/70, role_set 0/36 → 3/36, context 3/70 →
**0/70**, definition 0/70 → 0/70, edge_account 0/70 → 0/70.

**`correspondence` went from nothing to 93.18%.** Three of the eight question kinds — `context`,
`definition`, `edge_account` — score exactly zero both before and after.

**Limit on this reading.** 59 questions is a coarse instrument. Zero correct out of 59 is
consistent with a true rate as high as about 5%, so this does not prove the development rate is
exactly zero. It does bound any development-panel improvement over the window to less than one
question in 59.

### An unresolved disagreement about the development baseline

The same 59-question development panel carries two different pre-teaching numbers: cursor 0 of
`summary.development_scores` reads **0/59**, while the study's transfer baseline reads
**21/177 "in each method before teaching"** — 177 = 59 × 3, so 7 per run. Both are described as
pre-teaching, on the same panel size, with `development_boundary` naming the same panel. **This
record has not established which is right**, and does not reconcile them by assertion.

---

## B. The objective had not converged — the gradient was still growing

Each of the 160 update receipts carries `raw_batch_loss` and `gradient_squared_norm`.
This is the training-batch loss measured **before** the update is applied.

Consecutive blocks of 20 updates:

| block | steps | mean | min | max |
|---:|---|---:|---:|---:|
| 0 | 0–19 | 1.613087 | 0.942343 | 2.221768 |
| 1 | 20–39 | 1.559153 | 0.644371 | 2.267041 |
| 2 | 40–59 | 1.530956 | 0.822199 | 2.584561 |
| 3 | 60–79 | 1.217111 | 0.577073 | 1.922803 |
| 4 | 80–99 | 1.270649 | 0.580367 | 2.230156 |
| 5 | 100–119 | 1.267108 | 0.537372 | 2.421186 |
| 6 | 120–139 | 1.012291 | 0.279819 | 1.820994 |
| 7 | 140–159 | 0.979089 | 0.277262 | 1.804005 |

- First quarter (updates 0–39) mean: **1.586120**
- Last quarter (updates 120–159) mean: **0.995690**
- Ratio last/first quarter: **0.627752**
- Global minimum `raw_batch_loss`: **0.277262**, at update **159** — the last update of the run
- Per-update Spearman(index, `raw_batch_loss`) = **−0.438668**

Trend test with the autocorrelation removed by blocking: Spearman(block index, block mean)
= **−0.928571**, with **26 of 28** block pairs in the descending order. Exact one-sided
permutation p over all 8! = 40,320 orderings = **0.000868**. The decline is real.

**The gradient norm did not decay. It grew.**

| quantity | first quarter | last quarter | ratio |
|---|---:|---:|---:|
| mean gradient L2 norm | 4.490157e-01 | 6.191440e-01 | 1.378892 |
| max gradient L2 norm over the run | — | — | 1.528121e+00 at update 93 |

Per-update Spearman(index, gradient norm) = **+0.317690**. The largest gradient in the run
occurs at update 93, in the second half.

The registered contract caps updates at 176 (`cas_meta2/typed_teaching/learner.py`,
`TYPED_LEARNER_LIMITS`, `0 < limits["max_updates"] <= 176`) and this run stopped at 160.
**The stopping point is therefore the ceiling, not a scheduling choice.** The run was
stopped mid-descent, with the loss still falling and the gradient still rising.

---

## C. The learning that did happen is confined to two of eleven fields

`normalized_loss` is `raw_loss / log(public_alphabet_size)`, so a uniform prior sits at
**1.0**. Means are over the field entries present across each batch's tasks, not a
per-task average; entry counts differ because fields differ.

| field | alphabet | entries | raw head | raw tail | ratio | norm head | norm tail |
|---|---:|---:|---:|---:|---:|---:|---:|
| correspondence | 7,25 | 208 | 2.273368 | 0.458806 | 0.201818 | 0.769966 | 0.158806 |
| edges | 2 | 80 | 0.670382 | 0.629649 | 0.939239 | 0.967157 | 0.908392 |
| function_ref | 64 | 80 | 4.155710 | 3.990282 | 0.960193 | 0.999237 | 0.959460 |
| kind_ref | 64 | 80 | 4.146553 | 3.914116 | 0.943945 | 0.997035 | 0.941146 |
| nodes | 2 | 213 | 0.696187 | 0.619635 | 0.890041 | 1.004385 | 0.893945 |
| participants | 2 | 80 | 0.728977 | 0.823562 | 1.129750 | 1.051692 | 1.188149 |
| reach | 5,6 | 315 | 1.602468 | 0.779164 | 0.486228 | 0.917934 | 0.444251 |
| roles | 2 | 96 | 0.675657 | 0.597681 | 0.884593 | 0.974767 | 0.862271 |
| setting_ref | 64 | 80 | 4.141473 | 3.966168 | 0.957671 | 0.995814 | 0.953662 |
| whole | 3,4 | 80 | 1.472184 | 2.146532 | 1.458060 | 1.100893 | 1.619377 |
| world_id | 65 | 80 | 2.104432 | 2.101532 | 0.998622 | 0.504130 | 0.503435 |

Uniform-prior references: log(3) = 1.098612, log(64) = 4.158883.

Three readings follow directly from this table.

**C1. The three 64-way reference fields barely move.** `kind_ref`, `function_ref` and
`setting_ref` each have a 64-symbol alphabet. Their normalized loss goes 0.997035 →
0.941146, 0.999237 → 0.959460 and 0.995814 → 0.953662. After 160 updates they remain
within 4–6% of **a uniform prior over 64 symbols.** Identifying one of 64 classes from a
64-dimensional input is the single largest discrimination problem in the loss, and it
receives essentially no learning in the budget available.

**C2. `whole` moved backwards, past uniform.** Its normalized loss goes 1.100893 →
1.619377: after training the model is reliably *more wrong* about the `whole` field than a
uniform guess would be. This is consistent with the negative transfer recorded on the final
held-out set, where the score fell from 6.5201% before teaching to 4/177 and 1/177 after.

**C3. `world_id` is flat and already good.** Its normalized loss is 0.504130 → 0.503435 —
unchanged, and well below uniform from the start. This is the field the frozen codebook
already resolves at 63.65% by closed-form solve, and it is the one field training neither
helps nor hurts.

---

## The architectural reading

Three defects are now separable and each is measured, not inferred.

**D1 — the update ceiling stopped the run while it was still fitting the exposed course.**
Measured: at the point the contract forced the run to stop, the batch loss was at its
global minimum and the gradient norm was still rising (ratio 1.378892, Spearman +0.317690,
maximum at update 93 of 160). No convergence criterion was ever met. `max_updates <= 176`
is a hard field of the registered learner contract, so raising the step count is a
contract-and-authority change, not a tuning knob.

**D1 is not an argument for raising the ceiling, and the panel structure is why.**
The loss was still falling because the run was still improving on the **exposed** course:
39/564 → 189/564, `correspondence` 0/88 → 82/88. Over the same 160 updates the **development**
panel stayed at 0/59 and **retention fell** from 46.8750% to 35.4167%. On this evidence more
updates on the same exposed course would plausibly widen the exposed-versus-transfer gap rather
than close it. The ceiling may be acting as a brake. That is one arm on one seed and is offered
as such, but it is the opposite of the reading this section originally invited, and the earlier
section invited it by leaving the panel structure out. **This is the wording changed by
`PANEL_MISREAD_CORRECTION.md`.**

**D2 — the loss is additive over fields while the metric is conjunctive over the answer.**
Measured: `correspondence` fell by 79% and `reach` by 52% in normalized terms, and over the same
window the **exposed** course rose 6.9149% → 33.5106% while the **development** panel moved from
0/59 to at most 1/59 and back to 0/59. A scored question is correct only when the entire
assembled answer matches the single admissible answer. Field improvement therefore reached the
exposed score and did not reach transfer, and the training signal gives no extra weight to
whichever field is currently binding. Stated precisely: **eleven fields must all be right, three
of eight question kinds (`context`, `definition`, `edge_account`) score exactly zero before and
after, and improving two fields moved the exposed score by 26.5957 pp while moving transfer by
nothing.** A useful objective would have to be conjunctive, or at least report per-field
progress against the all-or-nothing metric.

**D3 — the representation was never the limit, and neither is the codebook.**
The closed-form solve on the same frozen features reaches 63.65% (40.7× chance) and all 65
world symbols are selectable (min normalised margin 0.7573). The reader is the `^6` block,
16,384 plastic parameters in three matrices, and its own optimizer had not converged when
the contract stopped it.

**What follows for the architecture.** The `^6` block as registered
(`merge(concat(tanh(left(x)), tanh(right(x))))`, from `cas_cjt.neural._DecomposeTransform`)
is, at small initialisation, the *linear* map `(merge_left · left + merge_right · right) x`.
That is exactly the function class in which the closed-form solve already succeeds. The
measured gap is therefore an optimisation gap inside a class the module can represent, and
the route that does not require touching the registered 176-update ceiling is to place the
plastic block at the closed-form solution rather than asking 160 stochastic updates to find
it. That is written up separately as
`ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md`, which supersedes nothing: the
earlier `ARCHITECTURE_CHANGE_SPEC_v0.1.md` remains **WITHDRAWN IN FULL**.

---

## What is NOT established here

- **Nothing was executed.** These are readings of a past run, not a new run.
- **One arm, one seed.** The telemetry is arm `MIXED_SAME_ITEMS`, seed `20260919`. The
  matched study ran six jobs over three seeds and two arms; this record reads one of them.
- **A falling training loss is not evidence that held-out accuracy would have risen.** The
  loss is measured on the training batches. Falling training loss with flat held-out
  accuracy is also the signature of fitting the batch stream. This record does **not**
  distinguish those two readings, and the `whole` field moving backwards is a warning
  against assuming the first.
- **The accuracy instrument has one-question resolution.** 0/59 cannot resolve improvements
  smaller than about 1.7 percentage points.
- **No claim is made about how many updates would suffice.** Nothing here bounds the
  required budget from above.
- **No GPU run is proposed or authorised by this record.** Any run that changes
  `max_updates`, the loss, or the initialisation is claim-bearing and needs an
  owner-signed phase record before launch.
