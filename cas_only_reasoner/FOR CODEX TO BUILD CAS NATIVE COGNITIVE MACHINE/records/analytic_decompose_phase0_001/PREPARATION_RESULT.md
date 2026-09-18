# Arm A preparation — what the construction gives, and what the recurrence takes back

> ## SUPERSEDED IN PART — `RECURRENCE_AWARE_FIT_RESULT.md`
>
> The finding below stands: with the **naive** fit the registered recurrence costs 19.15 points
> (63.83% direct, 44.68% through the recurrence). **That cost was an aiming error and it is
> fixed.** The solve fitted `T` on an input the run never feeds the block; re-fitting on the
> states the block is actually given recovers it to **62.94% direct, 62.06% through the
> recurrence** — a residual cost of **0.88 points**. `tools/prepare_analytic_arm.py` now performs
> that refinement by default, and `preparation_report.txt` carries the recurrence-aware numbers.
> Read this file for the depth profile and the diagnosis; read the other one for the result.

**Status:** PREPARATION REPORT. **Not a run. Nothing is licensed.**
**Tool:** `tools/prepare_analytic_arm.py`  **Output:** `preparation_report.txt`
**Depends on:** `cncm/analytic_decompose.py`, `PHASE0_RECORD_DRAFT.md`
**Spend:** $0.00. Pure standard library. No model, no GPU, no provider, no target opened.

---

## What this is

Arm A initialises the registered `^6` block at the closed-form solution and runs with **zero**
updates. `cncm/analytic_decompose.py` is the arithmetic and `PHASE0_RECORD_DRAFT.md` is the
proposal. This tool is the preparation step, so the owner has something concrete to sign rather
than a document describing something that would still have to be built.

**It is a preparation report, not a result.** It measures the **construction** on out-of-fold
rows. It does not measure the machine, and it is not evidence that arm A works.

## The circular version is refused, by name

The tempting shape — fit one `T` on all 564 registry packets and evaluate on all 564 — is
same-sample reconstruction. `refuse_whole_course_fit` always raises, with the reason:

> *"fitting one parameter set on the whole course and evaluating it on 'the same course' is
> same-sample reconstruction. The 63.83% this arm rests on is a 5-fold cross-validated number,
> and the phase-0 record requires the fitting material to be disjoint from every evaluation set.
> Use `fit_folds()`."*

`--whole-course-fit` exists only to hit that guard, and it does.

## The two readings

All numbers are out-of-fold, 5 folds, 451 rows fitted and 113 held out per fold.

| reading | direct forward | **through the recurrence** |
|---|---:|---:|
| cross-validated accuracy | **63.83%** | **44.68%** |
| distinct aliases emitted (of 64) | 24 | 24 |
| commonest alias share | 6.4% | 11.3% |
| focus alias ranked #1 (of 564) | 360 | **252** |
| focus alias #6 or worse | 81 | 132 |

Construction checks, measured rather than asserted:

| check | value |
|---|---:|
| registered parameter shapes hold | `True` |
| worst identity residual (`forward(x) = T·tanh(x)`) | **0.000e+00** |
| worst realisation score residual | **2.435e-14** |

Per-fold parameter digests: `4b86e13e…`, `f9583ccd…`, `27be70ea…`, `2b7ab673…`, `9462d3e2…`.

## Finding 1 — G6 would pass on both readings

G6 as written: *"arm A emits strictly more than 9 distinct world aliases across the 210
world-typed reference slots, and the commonest single alias is below 44.3% of emissions."*

| reading | distinct aliases | commonest share | G6 |
|---|---:|---:|---|
| direct forward | **24** | **6.4%** | **PASS** |
| through recurrence | **24** | **11.3%** | **PASS** |

Against the recorded baseline at cursor 160 — **9 distinct aliases, `W36` at 44.3%** — the
construction moves the emitted-alias distribution a long way in the predicted direction, and it
does so whether or not the recurrence is applied.

**The denominators differ and the comparison is of shape, not of like-for-like counts.** The
preparation scores 564 representative slots, one per packet. The recorded 9-of-64 and 44.3%
figures are over the 210 world-typed reference slots of the `context` and `definition` packets.

## Finding 2 — the registered recurrence takes back 19.15 percentage points

**This is the new number, and it is the more important one.**

Run without the recurrence, the analytic parameters read the focus world at **63.83%** — the
figure the whole proposal rests on. Run **through the registered depth-8 recurrence**, the same
parameters read it at **44.68%**.

The recurrence is not neutral to this initialisation. It costs **19.15 percentage points**, and
the focus alias falls from rank 1 in 360 of 564 slots to 252 of 564.

That lines up with `DEPTH_VALUE_RESULT.md`, which measured on the **trained** block that depth 4
and depth 8 differ in **17.5% of answers** while the logit spread moves by **0.67%** — the late
passes reshuffle near-tied decisions rather than sharpening the read. Here it is visible from the
other side: applying the recurrence to a *known-good* input degrades it.

**What arm A would still be worth.** Even after the recurrence's cost, 44.68% is:

| comparison | value |
|---|---:|
| the trained learner's frozen-readout focus decodability | **1.24%** |
| versus 1/64 chance | **28.6×** |
| versus the strongest null (majority class, 4.6099%) | **9.69×** |
| the gain over the trained learner | **36.0×** |

So the honest prediction is not 63.83%. **It is 44.68% through the registered recurrence**, and
the 19.15-point gap between the two is itself an architectural finding about the recurrence,
independent of arm A.

## Finding 3 — the recurrence reading is the closer prediction, and it is approximate

A run applies `recurrence.run_passes` at depth 8, so the **recurrence reading** is the one that
resembles what a run would do. It is not exact. The block is exact for the analytic parameters —
`forward(x) = T·tanh(x)` holds with residual **0.000e+00**, so `block_forward` computes them
exactly — but the **encoded slot is rebuilt**, and `RECONSTRUCTION_GAP.md` measures that rebuild
at **+0.781 correlation** with the recorded logits. The recurrence reading therefore inherits that
approximation and the direct reading does not.

**Neither reading is a run.** Both are the construction evaluated on rows it was not fitted on.

## What this adds to the phase-0 record

**P6, frozen here: through the registered recurrence, arm A reads the focus world above the
recorded baseline and the recurrence costs it between 10 and 30 percentage points.** Measured
preparation values: 63.83% direct, 44.68% through the recurrence, a cost of 19.15 points. A run
landing outside that 10–30 window means the recurrence reading here is not capturing the real
forward pass and the tool must be revisited before the result is interpreted.

## What is NOT established here

- **This is not a run and nothing was launched.** No arm, no reservation, no device, no AWS.
- **The accuracy figures are on ONE field.** They are focus-world alias decodability, a single
  64-way choice — **not** the whole-answer exact-match metric the course scores. The two are not
  comparable and must never be presented together as an improvement.
- **The construction is fitted and evaluated on the same registry.** The fitting is out-of-fold,
  which is what makes the numbers admissible at all, but the sample is still the learner's own
  564-packet registry with only 24 of 64 worlds present.
- **The recurrence reading carries the +0.781 rebuild approximation** in its input.
- **No claim about `edge_account`, `parts`, `context`, `definition` or `role_set`.** This arm
  touches the world-naming slot only. The five many-decision kinds are a different defect
  (`DECISION_STRUCTURE_RESULT.md`).
- **The preparation report is not a licence.** A run requires an owner-signed phase record, and
  `--write-parameters` writes parameters, not authorisation.
