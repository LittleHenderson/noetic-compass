# Sixth self-correction — the panels were misread, and one framing was misleading

**Record:** `records/encoder_capacity_001/`
**Trigger:** `worker_report.json` `design` block and `result.json` `summary` of
`typed_matched_001/receipt_20260919_m`.
**Spend:** $0.00. This is a reading correction, not a new measurement.

---

## What was wrong

`UPDATE_TRAJECTORY_RESULT.md`, section A, is headed **"Accuracy did not improve at all."** It
reports that the development curriculum scored 0/59, 0/59, 1/59, 1/59, 0/59 across the five
checkpoints, and concludes that answer accuracy did not improve across the 160 updates.

**Every number in that section is correct. The framing is misleading, and it is misleading in
the direction that matters.** Read without the panel structure it invites the conclusion that
the learner learned nothing. It did not learn nothing. It learned a great deal, and the thing
it learned was the wrong thing.

## The panel structure, from the run's own design block

| panel | field | size | boundary as recorded |
|---|---|---:|---|
| exposed registry course | `registry_packets`, `initial_and_final_prediction_packets` | **564** | the course the learner was taught |
| development | `development_packets` | **59** | `PUBLIC_DEVELOPMENT_TOPOLOGIES_NO_TRAINING_CORRECTIONS_NO_FINAL_PANEL` |
| retention | `retention_packets` | **96** | `OTHER_QUESTION_TEACHING_SAME_PUBLIC_BANK_NO_PARTS_REACH_EDGE_CORRECTIONS_NOT_CONTENT_UNSEEN` |

## What each panel actually did, for arm `MIXED_SAME_ITEMS`, seed `20260919`

From `result.json` `summary`, which is the worker's own report:

| panel | before | after | change |
|---|---:|---:|---:|
| **exposed registry course (564)** | **39/564 = 6.9149%** | **189/564 = 33.5106%** | **+26.5957 pp, 4.85×** |
| development (59) | 0/59 = 0.0000% | 0/59 = 0.0000% | **0**, and it never exceeded 1/59 |
| retention (96) | 45/96 = 46.8750% | 34/96 = 35.4167% | **−11.4583 pp** |

`learning_advantage_established` is **False**. `starting_competence_met` is **False**.

Per kind on the exposed course, before → after:

| kind | before | after |
|---|---:|---:|
| correspondence | 0/88 = 0.00% | **82/88 = 93.18%** |
| reach | 25/107 = 23.36% | **81/107 = 75.70%** |
| parts | 6/53 = 11.32% | 12/53 = 22.64% |
| analogy | 5/70 = 7.14% | 11/70 = 15.71% |
| role_set | 0/36 = 0.00% | 3/36 = 8.33% |
| context | 3/70 = 4.29% | **0/70 = 0.00%** |
| definition | 0/70 = 0.00% | 0/70 = 0.00% |
| edge_account | 0/70 = 0.00% | 0/70 = 0.00% |

**`correspondence` went from nothing to 93.18%.** That is not a learner that failed to learn.

## What this does to the earlier readings

**It does not change the study's headline.** `MATCHED_STUDY_RESULT.md` line 41 is explicit:
"Raw final answers were 4/177 for component-first versus 1/177 for the control, down from
21/177 in each method before teaching. **This is the same 59-question panel repeated with three
model initializations, not 177 different problems.**" The negative-transfer finding is about
the **development** panel, and the development panel is exactly the panel that did not improve.
The headline stands.

**It sharpens the non-convergence finding, and it weakens the under-training reading.**
`UPDATE_TRAJECTORY_RESULT.md` found the batch loss still falling and the gradient norm still
rising when the ceiling stopped the run at 160 of 176. This section explains *why* it was still
falling: **the run was still improving on the exposed course**, from 39/564 to 189/564. It was
converging on what it had been shown, at the moment it was stopped, while the development panel
sat at zero and retention fell by 11.4583 pp.

So "raise `max_updates` and let it finish" is **not** the obvious next experiment. On this
evidence, more updates on the same exposed course would plausibly widen the gap between exposed
performance and transfer, not close it. The ceiling may even be acting as a brake. That is a
reading of one arm on one seed and is offered as one, but it is the opposite of the reading the
earlier section invited, and the earlier section invited it by leaving the panel structure out.

**An eighth question kind does not exist to blame.** `context`, `definition` and
`edge_account` score exactly zero before *and* after. Three of eight kinds are entirely
unmoved by teaching. Zero-score kinds are not a rounding artefact; they are three of the eight
things the machine is asked to do.

## An unresolved disagreement, recorded rather than reconciled

The same 59-question development panel is reported with two different pre-teaching numbers:

- `summary.development_scores` at **cursor 0: 0/59 = 0.0000%**;
- the study's transfer baseline: **21/177 "in each method before teaching"**, which is
  177 = 59 × 3, i.e. **7 per run**.

Both are on the development panel, both are described as pre-teaching, and they disagree.
`development_boundary` reads
`PUBLIC_DEVELOPMENT_TOPOLOGIES_NO_TRAINING_CORRECTIONS_NO_FINAL_PANEL`, so the panel is the
same panel. One of the two measurements is measuring something other than what its name
suggests, and **this record has not established which.** It is left open rather than reconciled
by assertion, because picking the convenient one is how a disagreement becomes a false
certainty.

## The corrected statement, in one paragraph

On arm `MIXED_SAME_ITEMS` seed `20260919`, teaching moved the **exposed** course from 6.9149%
to 33.5106% and `correspondence` from 0% to 93.18%, while the **development** panel stayed at
0/59 and **retention** fell from 46.8750% to 35.4167%. The training objective had not converged
because it was still fitting the exposed course. The learner was not failing to learn; it was
learning the exposed course and not transferring, which is negative transfer, which is what
`MATCHED_STUDY_RESULT.md` already said. What was wrong was this record's section heading, not
the study.

## Files corrected

- `UPDATE_TRAJECTORY_RESULT.md` section A — heading and reading replaced, panel structure and
  the exposed-course numbers added, the per-field and per-kind tables qualified by panel.
- `STATUS.md` Finding 13 — the same correction, so the record does not carry two accounts.
- `OPEN_QUESTIONS.md` OS-022 — the under-training option is downgraded on this evidence.
