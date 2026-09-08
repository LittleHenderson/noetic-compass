# Curriculum Revision — parts_supervised_v1

Directly supervised parts-and-whole teaching for the input-binding task.

Status: **DESIGN_ONLY** — new documented curriculum version. This is not a
silent change to the frozen teaching campaign.

---

## 1. Version and status

- **Name**: `parts_supervised_v1`.
- **Kind**: a NEW documented curriculum version, recorded here, not applied to
  any frozen campaign artifact.
- **Scope**: design only. No launcher, no run authorization, no reservation, no
  code change to `cas_meta2/teaching_cycle/**`, no edit to the frozen teaching
  worker, controller, lesson contract, or the campaign ledger.
- **Frozen campaign**: unchanged. `parts_supervised_v1` is a separate proposal
  that, if ever used, would require its own authorization and reservation flow
  (see section 7). It does not modify, retire, or reinterpret the existing
  seven-stage aligned lesson or the ordinary control lesson.
- **What changes vs. the frozen curriculum**: the frozen curriculum supervises
  one target per delivered view — the final binding slot (`target_binding`,
  an integer in `{0, 1, 2}`). This revision adds, on top of that unchanged
  final target, directly supervised **parts targets** (per-candidate color
  match, shape match, and their conjunction), plus short task-only practice
  with corrective feedback during teaching.

Plain-English summary: the learner already learns to name the whole answer (the
slot). This revision also teaches it to name the parts (which color matches,
which shape matches, which candidate matches both), from its own reading of the
problem, and then to put the parts together into the whole answer.

---

## 2. The seven connected stages, each with an intermediate supervised target

The seven connected stages are kept exactly as named in the frozen contract
(`cas_meta2/teaching_cycle/lesson_contract.py`, `STAGES`):

1. `name_function`
2. `context`
3. `analogy`
4. `mapping`
5. `decomposition`
6. `recomposition`
7. `reinforcement`

The final binding target (`target_binding`, the slot in `{0, 1, 2}`) stays the
supervised target **in every stage**, exactly as today. What this revision adds
is a per-stage **intermediate supervised target** that the learner must also
predict from its own encoding (see section 3).

The intermediate targets are the parts of the binding decision. For one problem
the request is a two-word tag `"color shape"` (for example `"green triangle"`),
and the three observations are candidate tags at slots 0, 1, 2. For each
candidate the learner must predict three per-candidate predicates:

- **(a) color matches request** — does the candidate's color word equal the
  request's color word? (one binary value per candidate, so 3 values),
- **(b) shape matches request** — does the candidate's shape word equal the
  request's shape word? (3 values),
- **(c) both match** — do color AND shape both match? (3 values),

plus the **final slot** — which candidate supplies child A's argument
(one choice among `{0, 1, 2}`).

### The advisor's exact worked example

Request: `green triangle` (color part `green`, shape part `triangle`).
Choices: `blue triangle` (slot 0), `green square` (slot 1),
`green triangle` (slot 2). Training answer: **Slot 2**.

Parts table:

| Slot | Candidate tag    | (a) color matches `green`? | (b) shape matches `triangle`? | (c) both match? | final |
|-----:|------------------|:--------------------------:|:-----------------------------:|:---------------:|:-----:|
| 0    | `blue triangle`  | NO  | YES | NO  | —     |
| 1    | `green square`   | YES | NO  | NO  | —     |
| 2    | `green triangle` | YES | YES | YES | **slot 2** |

The distractors each share exactly one part with the request:
`blue triangle` shares the shape; `green square` shares the color. Only the
candidate that matches both parts is the answer.

### Stage-to-target mapping

Every row keeps the final slot as a supervised target. The added intermediate
target is listed per stage:

| Stage | Intermediate target the learner must predict (in addition to the final slot) |
|-------|--------------------------------------------------------------------------------|
| `name_function` | per-candidate **color match** (a), 3 binary values |
| `context`       | per-candidate **shape match** (b), 3 binary values |
| `analogy`       | per-candidate **both match** (c), 3 binary values |
| `mapping`       | per-candidate **color match AND shape match** (a and b), 6 binary values, one-to-one with the request's two words |
| `decomposition` | the full **parts table**: color match + shape match + both match (a, b, c), 9 binary values |
| `recomposition` | per-candidate **both match** (c) **and the final slot**, so the learner composes the whole from the parts |
| `reinforcement` | the full **parts table** (a, b, c) **and the final slot**, repeated across changed-detail views |

Why this order: the stages introduce one part at a time (color, then shape,
then their conjunction), then the full table, then the recomposed whole, then a
reinforced review. The stage names and their existing lesson prompts are left
unchanged; the new parts target rides alongside the stage.

For the advisor's example, the gold intermediate labels are:

- color match (a): `[0, 1, 0]` (slot 0 blue = no, slot 1 green = yes,
  slot 2 green = yes) — written in slot order.
- shape match (b): `[1, 0, 1]` (triangle = yes, square = no, triangle = yes).
- both match (c): `[0, 0, 1]` (only slot 2).
- final slot: `2`.

---

## 3. The learner predicts the parts from its own encoding — no hidden rule

This is a hard requirement, stated explicitly.

The intermediate answers (color match, shape match, both match) and the final
slot must all be produced by the learner's own forward pass from its own
encoding of the public input. Concretely:

- The parts predictions come from the learner's own supervised heads over its
  own encoding — the same encoder/`token_head` path that already produces the
  3-way `binding_logits` (see `gpu_adapter.py` `_logits`, which reads
  `token_logits[:, 0, BINDING_TOKEN_IDS]`).
- The final slot remains a directly supervised model output (its own
  3-way logits, `argmax` over `BIND0/BIND1/BIND2`). It is **not** computed by a
  rule over the parts at inference.
- A hidden rule must never compute the intermediate answers at inference and
  hand the final selection over. Specifically forbidden at inference: a regex
  or string-match that reads the tags and returns the match predicates, or a
  hand-written `if color == x and shape == y` that then picks the slot. Even the
  composition step (`both = color AND shape`, then pick the slot) must be
  learned and predicted by the learner, not applied as deterministic
  post-processing on top of rule-computed parts.

What stays allowed: the frozen `recover_binding` checker in
`lesson_contract.py` remains a teacher-side **validator** of public inputs. It
is not the learner's answer and does not change. Teacher-side code may also
compute the gold parts labels from the tags in order to form supervised targets.
The prohibition is only on the learner's inference path: the learner's own
network must reproduce the parts and the slot, and nothing may substitute a
rule's output for the learner's final selection.

This is the point of "directly supervised parts-and-whole teaching": the parts
are supervised so the learner builds them; the whole stays supervised so the
learner still learns the final decision itself. The parts heads are auxiliary
supervision that share the encoder; they must not bypass the binding head.

---

## 4. Short task-only practice with corrective feedback DURING teaching

The frozen campaign already checks accuracy at development/readiness intervals
(`controller.py` `observe_development`, gated by `development_interval` and
`readiness_accuracy`). That is a readiness check, not in-loop teaching. This
revision adds short task-only practice **during teaching**, with the correction
shown as the answer.

### Format

A practice item is a task-only miniature problem, not a lesson paragraph:

- **Question**: the request plus the three choices at their slots, in the same
  public-input shape the learner already reads. Example question text:
  `Requested source: green triangle.` with the three candidate tags and their
  slots.
- **Choices**: the three slots (or the three candidate tags at their slots).
- **Answer (as the correction)**: the gold answer, revealed as the feedback.
  For a parts-practice item the answer is the gold predicate vector(s), e.g.
  color match `[0, 1, 0]`. For a complete-decision item the answer is
  `BIND2` (the slot).

Corrective feedback = the correct answer itself, shown after the learner's
prediction. If the learner's prediction differs from the gold answer, the gold
answer is delivered in the immediately following presentation of that task, so
the learner is re-supervised on the correct answer within the same cycle. The
feedback is the answer, not a bare "wrong", and it is applied during teaching,
not deferred to a readiness check.

### Frequency within a cycle

- One **parts-practice item** immediately after each of the seven stages,
  targeting the part(s) that stage introduces (7 per aligned cycle).
- One **complete-decision practice item** after the final `reinforcement`
  stage (1 per aligned cycle).

Total: 8 practice items per aligned cycle, in addition to the 7 stage
presentations. The ordinary control receives the same 8 practice items with the
same timing, so the aligned-vs-ordinary contrast is preserved (only the stage
framing differs).

### Identical assistance for both families

The parts-practice items and their corrective feedback are **byte-identical**
across the CAS family (`CASProgramGenerator`) and the generic family
(`GenericProgramGenerator`), and across both curricula. Neither family gets
more hints, more practice, or earlier corrections than the other. The only
difference between the two families remains the model itself.

---

## 5. Exercise order and changed-detail repetition

Order within the teaching of one family:

1. **Explain** — the stage prompt (the existing stage lesson).
2. **Demonstrate** — a worked demonstration of the parts table for the worked
   example (the advisor's example above), showing color, shape, both, and the
   resulting slot.
3. **Practice parts with feedback** — the parts-practice item(s) for the stage.
4. **Practice the complete decision** — the complete-decision item: predict the
   final slot from the request and choices; correction reveals `BIND{slot}`.
5. **Show the correspondence in another form** — the mapping/analogy view: the
   same rule restated one-to-one (request word → candidate predicate) and in
   the parcel analogy, so the parts are re-seen in a second form.
6. **Repeat with changed details** — re-present the task with a changed request
   or moved slots (below), with the same parts targets and final slot.

### How changed-detail repetition is generated from existing families

Changed-detail variants are generated deterministically from the frozen
family's own observations; no new families or new tags are invented. The two
generators already exist and are pinned in
`cas_meta2/teaching_cycle/binding_diagnostic.py` `_case_variants`
(lines 51–62); the revision reuses that mechanism rather than building a new
generator:

- **request change** (`requested_tag_change`): keep the same three observations,
  change the `requested_tag` to one of the other observation tags. The new
  final target is the slot that holds that tag. Example: with the same choices
  `blue triangle` / `green square` / `green triangle`, change the request to
  `green square`; the answer moves to slot 1.
- **slot permutation** (`slot_permutation`): keep the request, permute the three
  observations across slots 0/1/2. The final target is the slot now holding the
  requested tag. Example: move the choices so `green triangle` sits in a
  different slot; the answer follows the tag, not the old slot number.

Both generators are seeded/deterministic and are applied to training families
only. The changed-detail repetition is part of the teaching loop and never
reaches the sealed evaluation sets (section 7).

---

## 6. Measurement — parts and final binding reported separately

Reuse the existing telemetry/binding instrumentation; do not build a new
monitoring framework.

The frozen diagnostic already reads the learner forward-only via removable
hooks and reports per-group attempted/correct counts
(`binding_diagnostic.py` `_forward_observation` and `execute_comparison`). The
revision extends that same read path to also capture the parts heads, and
reports three separate numbers:

- **Parts accuracy per stage**: fraction of per-candidate predicate predictions
  correct, grouped by stage and by predicate kind (color match, shape match,
  both match). This uses the same `attempted`/`correct` aggregation already
  produced by `execute_comparison`.
- **Final binding accuracy**: fraction of final-slot predictions correct,
  unchanged from the existing `correct`/`attempted` accounting in
  `controller.observe_development` and the diagnostic's `groups`.
- **First-wrong-part**: the earliest stage/predicate where the learner's
  prediction diverges from the gold parts table, per family and per arm. This
  reuses the per-row `correct` booleans already emitted by the diagnostic, keyed
  by stage and predicate.

The parts heads are read through the same removable forward-hooks and the same
telemetry boundary (`TELEMETRY_BOUNDARY`, "observed values distinguish measured
internal states; they do not establish cause"). Scalar and operating-region
statistics reuse `scalar_statistics` / `operating_region_statistics`. No new
monitoring framework, no new causal claim, no new telemetry store.

---

## 7. Boundaries

- **Negative results preserved**: the existing negative held-out composition
  results and the recorded low-binding-accuracy finding are untouched. Nothing
  here erases, reinterprets, or softens them.
- **No claim promotion**: this is a design document. It establishes no
  readiness, mastery, or CAS-advantage claim. `DESIGN_ONLY`; no result.
- **Generalization still sealed**: generalization is measured only on the
  sealed fresh exam (`test_fresh`, `test_context`, `test_names`) outside the
  practice loop. Parts practice and changed-detail repetition are train-only;
  they must not appear in the sealed sets (the frozen worker already rejects
  `Worked`/`BIND` answer text in final inputs — `worker.py`
  `predict_sealed`).
- **Any eventual run needs its own authorization/reservation**: a future run of
  this revision would need its own explicit enable, its own AWS identity
  observation, its own bounded reservation against the campaign ledger, and its
  own source/checkpoint pins. This revision authorizes none of that. The frozen
  worker's separate `train`/`predict` admission and the controller's allocation
  remain the only currently authorized paths.

---

## 8. What stays identical

| Item | Stays identical |
|------|-----------------|
| Task semantics | request tag + three observations → bind the matching slot to child A's argument |
| Encoder | the learner's encoder and tokenizer; parts heads share it, no new encoder |
| Binding-output path | 3-way `binding_logits` over `BIND0/BIND1/BIND2` → `argmax`; final slot from the learner's binding head |
| Both families | CAS and generic, both curricula; identical practice and assistance |
| Final classification loss | cross-entropy over the 3 binding logits (`gpu_adapter.py` `teach`, line 201) |
| Sealed evaluation | the three sealed final sets and the frozen scorer, outside the practice loop |

The frozen lesson contract, guided application, controller, worker, diagnostic,
and ledger are not modified by this document. `parts_supervised_v1` is an
additional, separately authorized-by-itself design, not a change to them.

---

## Files reviewed (grounding)

- `cas_meta2/teaching_cycle/lesson_contract.py`
- `cas_meta2/teaching_cycle/guided_application.py`
- `cas_meta2/teaching_cycle/binding_diagnostic.py`
- `cas_meta2/teaching_cycle/worker.py`
- `cas_meta2/teaching_cycle/controller.py`
- `cas_meta2/teaching_cycle/data.py`
- `cas_meta2/teaching_cycle/gpu_adapter.py` (loss and output path, lines 173–245)
- `cas_meta2/codec.py` (`BINDING_TOKEN_IDS`)
- `records/teaching_cycle_001/CONTINUATION_002_README.md`
- `records/teaching_cycle_001/RESULT.md`

## 9. Data-contrast addendum (2026-09-08, after exact counts)

Counted per candidate over `data.build_dataset(seed=20260908)` (see
`binding_fit_training_check_001/MODE_AND_DATA_CORRECTION.md`): in every
permitted teaching case (train 256, development 64, test_fresh 64,
test_context 64) the candidates are exactly one both-match and two
neither-match - zero color-only and zero shape-only candidates. The three
parts columns are therefore identical in all teaching data, and parts
supervision there would reinforce one signal three times rather than teach
three separable skills.

Two documented options, neither altering the live campaign:

(a) NARROW: describe the lesson as redundant reinforcement of the binding
signal, not as separable part learning.

(b) VERSIONED CONTRAST FAMILIES: propose new, separately versioned and checked
teaching families whose distractors share exactly one attribute with the
request (request `green triangle` with distractors `green square` and `blue
triangle`), so color-only and shape-only candidates occur during teaching.
This is a new documented curriculum change requiring its own authorization.

The advisor's illustrative distractors correspond to option (b). This revision
keeps both options explicit and selects neither without an owner ruling.
