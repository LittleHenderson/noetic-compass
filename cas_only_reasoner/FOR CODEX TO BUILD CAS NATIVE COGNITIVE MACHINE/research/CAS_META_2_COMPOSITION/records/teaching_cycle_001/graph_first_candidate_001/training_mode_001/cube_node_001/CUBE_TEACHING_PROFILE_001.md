# CUBE_TEACHING_PROFILE_001 — one machine-facing seven-stage cube lesson

**Owner directive:** "Build one end-to-end cube lesson that clearly states at each of the 7
stages … exact neuron-facing input, any prediction target, the corrective signal,
whether an optimizer update happens, and record the assistance state. Leave analogies or
stories as guided presentation only unless we define a real task later. Keep using the
three existing graph tasks. Don't create new heads unless it's unavoidable. And also keep
guided and unassisted clearly separate. One more bit, clean up the target-dependent slot
ordering in new compilations only. Don't touch old evidence."

**Status of this record:** specification and compilation only. No training, no
reservation, no launch, no GPU, no optimizer step, no delivered neural lesson.

**Claim state:** *schema valid* and *lesson specification compiled*. It is **not**
lesson delivered, not practice improved, not transfer demonstrated. The counters in this
record say so explicitly: `optimizer_updates: 0`, `delivered_neural_lessons: 0`.

Generated artefacts (both in
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/`):

| File | Bytes | sha256 |
|---|---|---|
| `CUBE_TEACHING_PROFILE_001.json` | 145,955 | `391c1578bbc6ab944ac599528ac41d3e28c1fc3e599dc83466b4e6dc961045b3` |
| `CUBE_NODE_CHECK.json` (previous handoff, unchanged) | 80,153 | `1df29252dbf3a69f54726ff6f22208f0ad50fc9843f28a5b32fb95ff87226651` |

Code: `cas_meta2/graph_teaching/cube_profile.py`, tests
`tests/test_graph_teaching_cube_profile.py` (20 tests), tool
`tools/graph6_cube_teaching_profile.py`.

---

## 1. The demonstration lesson

Public question: `LIST_PARTS(Bicycle)`. Deterministic answer: `["Frame", "Wheel"]`.

Three public choices, in the slots the module receives:
`slot 0 = ["Frame","Wheel"]`, `slot 1 = ["Frame","Rim","Wheel"]`, `slot 2 = ["Frame"]`.
The correct slot is 0 in both the guided and the unassisted delivery, because the slot
order is a function of the public exercise only.

### Guided delivery

| Stage | Visits | Kind | Module input | Predicts | Correction | Update when run | Withheld |
|---|---|---|---|---|---|---|---|
| 1 name_and_function | core, face_1 | presentation | no | no | no | no | 0 |
| 2 context | face_2 | presentation | no | no | no | no | 0 |
| 3 analogy | face_3 | presentation | no | no | no | no | 0 |
| 4 explicit_mapping | face_4 | presentation | no | no | no | no | 0 |
| 5 guided_decomposition | face_5 | supervised_task | **yes** (49 tokens) | **yes** | **yes** | **yes** | 0 |
| 6 recomposition | face_6 | presentation | no | no | no | no | 0 |
| 7 reinforcement | core + all six faces | supervised_task | **yes** (49 tokens) | **yes** | **yes** | **yes** | 0 |

Counts: 7 stages, 5 presentations, 2 supervised tasks, 2 module inputs, 2 predictions
required, 2 corrective examples, **0 optimizer updates, 0 delivered neural lessons**, 1
graph family, 1 assistance level recorded. 44 face paths visible, 0 withheld.

### Unassisted delivery of the same question

Identical task identity (`ad7cee60c8fc6ecb`), identical choice slots, identical token
digest. Differences are exactly two: the declared mask, and whether the answer is
delivered.

| Stage | Kind | Module input | Predicts | Correction delivered | Update when run |
|---|---|---|---|---|---|
| 5 guided_decomposition | assessment | yes (49 tokens) | yes | **no** | **no** |
| 7 reinforcement | assessment | yes (49 tokens) | yes | **no** | **no** |

Counts: 7 stages, 5 presentations, **0 supervised tasks, 2 assessments, 0 corrective
examples**, 0 optimizer updates, 0 delivered neural lessons. 36 face paths visible, **8
withheld**.

Stages 1–4 and 6 are presentation in both deliveries.

### What the module actually receives at stage 5

```json
{"problem": "Facts (labels as presented in view_context):\n
             Bicycle contains Wheel\nBicycle contains Frame\nCart contains Wheel\n
             Cart contains Platform\nWheel contains Rim\n
             LIST_PARTS(Bicycle): what does it directly contain?\n
             Choose one of the three supplied options.\n",
 "observations": [{"slot": 0, "tag": "['Frame', 'Wheel']",            "values": [0.0 x 8]},
                  {"slot": 1, "tag": "['Frame', 'Rim', 'Wheel']",    "values": [0.0 x 8]},
                  {"slot": 2, "tag": "['Frame']",                    "values": [0.0 x 8]}]}
```

That is the frozen public contract: one problem string and exactly three observations of
eight numbers each. Prediction is the module's own argmax over the three slots. The
corrective signal for a supervised stage is cross-entropy over those three slots against
target index 0.

### The intended parameter-update path (not executed here)

```text
contract    cas.cjt.operation.^6.decompose/0.2
role        operation:^6
updates     the registered module's own parameters only, through the existing
            trainer allowlist (trainer.scope_parameters)
excluded    the frozen encoder, the frozen dot-product readout, anything outside
            the admitted plasticity role
objective   cross-entropy over the three public slots against the declared target index
check       trainer.containment_report must show no digest change outside the allowlist
```

Every `update` block in the record carries
`occurs_in_this_preparation: false` with the reason "specification only: no module was
constructed and no optimizer step was taken"; `would_occur_when_run` is true only for the
two supervised stages of a guided delivery.

## 2. The two decisions, implemented as asked

**Three familiar questions only.** `scored_operations` is exactly `LIST_PARTS`,
`FIND_SHARED_PART`, `REACHED_VIA`. `new_heads_required` is empty. No new output
vocabulary, no new loss, no new head.

**Face 5 during guided teaching, withheld in an unassisted test.** Guided withholds
nothing: the inventory, the correspondence table, and the worked explanation are the
instruction, and the score is labelled assisted. Unassisted keeps the public `contains`
facts — the evidence the task needs — and withholds the preassembled solution.

**Five stages declined, in writing.** Stages 1, 2, 3, 4, and 6 are recorded as
`presentation` with the note that scoring them would need a separately declared output
vocabulary, loss, and training adapter. `unsupported_scorings_declined` names each
candidate exercise the schema proposed and states the reason. Analogies and stories are
guided presentation only, as instructed.

**Guided and unassisted stay separate.** Different visibility profile id, different
delivery id, different correction delivery, different counters. They share only the
public exercise — same identity, same choices, same slots, same tokens — so a comparison
between them differs in visibility and correction alone.

## 3. The visibility rule was changed to a declaration

The previous record chose what to hide **from the answer**: it scanned for fields that
named the answer's cubes and withheld those. The owner's reviewer flagged the risk that a
mask whose pattern depends on the answer can itself become a clue. That is now fixed in
the new compilation path:

- `VISIBILITY_DECLARATIONS` states, once per (operation, assistance level), the fields
  withheld. All four unassisted declarations are the same four field patterns:
  `face_2.structured.fact_refs`, `face_5.structured.direct_branch_refs`,
  `face_6.structured.steps[*].uses_branch_refs`, `face_6.structured.steps[*].text`.
- The mask is the expansion of those patterns over the cubes the question asks about.
  `mask_is_declared` checks that the mask is exactly that expansion, no more and no less.
- The answer can now only ever **refuse** a lesson (`CUBE_UNASSISTED_PROFILE_DISCLOSES_
  ANSWER`), never shape one. The check runs after the mask is built, from the declared
  profile, and the audit is reported beside it.

For `LIST_PARTS(Bicycle)` the declared mask withholds 8 addressable leaves. The earlier
answer-derived list named 8 entries too, but 2 of those were group paths rather than
leaves, so the declared rule is slightly broader: it withholds the whole story, its
anchor line included.

**Audit of every askable question** (`audit_all_questions`): 51 questions, **51 compile
unassisted, 0 refused**, and **0 residual disclosures** inside the asked-cube scope. In
the wider scope — every cube of the bundle, not only the asked ones — 8 questions still
have a field that names an answer element. Those fields belong to cubes the question does
not ask about, and they restate the public graph (for example Bicycle's inventory lists
Wheel, which is the public branch `Bicycle contains Wheel`). The scope decision is
recorded rather than hidden, and the wider number is reported so it can be revisited.

**One scanner defect found and corrected in the new layer.** The delivered example gives
the technical view the one-letter labels `A`–`F`. The old prose scanner found the letter
"B" inside the analogy label "Kit B", resolved it to a different cube, and reported a
disclosure that does not exist. The new audit matches prose only against labels that do
not occur inside another label; `A`, `B`, `C`, and `F` are excluded for that reason, and
`Kit A`/`Kit B` still match. `cube_node`'s scanner is left exactly as published, because
its record is already evidence.

## 4. Target-independent identity and slot order, new compilations only

The new path enforces three things, and the check exercises the whole
compile → visibility → encode path rather than swapping a target after the fact:

1. **The public path cannot see the answer.** `compile_public_exercise` receives a public
   case whose only keys are `op` and `question`; a target field there is refused
   (`CUBE_PUBLIC_CASE_CARRIES_TARGET`). Task identity, the three choices, the mask, the
   prompt, and the token list are all computed from that.
2. **A disagreeing target is refused.** `attach_target` compares the declared target with
   the answer the deterministic checker derives from the public graph and fails closed
   (`CUBE_DECLARED_TARGET_NOT_THE_DERIVED_ANSWER`). So the private target cannot steer the
   learner's input even by accident: it cannot disagree.
3. **Identity ignores the assistance level.** `task_id`/`public_id` cover the public
   exercise only, so the same question offers the same three choices in the same slots
   guided and unassisted. A separate `delivery_id` records the assistance level and the
   profile for bookkeeping.

Readings from `target_independence_check`, for all four assistance levels (worked, guided,
hinted, unassisted): `identical_under_target_change = true` on task id, public id, derived
answer, learner view, withheld paths, visible paths, tokens, and the encoded public
record; `disagreeing_targets_refused = true` for both alternative choices;
`slot_order_identical_across_assistance_levels = true`.

**The legacy dependency, shown and not touched.** `legacy_ordering_demonstration` reads
the existing rule with the frozen functions: the old generator folds the answer into
`record_id`, and the frozen public-record extraction derives slot order from `record_id`.
With the same three choices and two different declared targets, that rule produces **2
distinct slot orders**. The new rule, with the same two targets, produces 1. Old records,
datasets, checkpoints, and results are unchanged; `cube_node` still emits
`cas-cube-lesson/1` and the new module emits `cas-cube-lesson/2`. This is a reading of the
data path, **not** evidence that any model used the difference, and it is not offered as
an explanation of the earlier negative results.

`hinted` is declared but withholds nothing and is therefore recorded as assisted. This
profile implements no graded hint policy; inventing one would be a policy claim, not a
data rule.

## 5. What this record does not claim

- It does not claim any cube lesson reached a module. `delivered_neural_lessons` is 0.
- It does not claim the cube representation improves learning. The only graph-learning
  measurement remains `VARIED_CURRICULUM_NOT_ESTABLISHED` from attempt 004, with
  `LIST_PARTS` at 23/180 = 12.8 % on the frozen panel.
- It does not settle the list-length or readout hypothesis. No adapter was written, and
  the option geometry of the three slots is whatever the frozen codec produces.
- It does not claim the five presentation stages teach anything. A presented face is not a
  scored exercise and not an optimizer update.
- It does not claim the legacy `record_id` dependency caused any past result.
- It does not claim the audit is complete protection. It measures the declared rule
  against one scene; the wider-scope reading is 8 questions, and a different bundle with
  different labels would need its own audit.

## 6. Open items for the owner

1. **The wider-scope reading (8 of 51 questions).** If a future presentation shows every
   cube's faces during a scored task, the declared mask — scoped to the asked cubes —
   would leave those fields visible. Making the scope "all cubes" is a one-line change to
   the declaration and would be a new profile version; it is not made here.
2. **No graded hint policy.** `hinted` currently equals `guided` in visibility.
3. **`assistance_states_recorded` counts distinct levels (1 per profile).** It counts what
   it says; a per-stage variety of assistance levels does not exist yet.
4. **Seven stages are still one question.** Stages 5 and 7 ask the same public question
   with different declared variations available; a curriculum that varies the questions
   across the three operations is a curriculum decision, still open.
5. **Pre-existing suite errors remain.** The cube suites pass 41/41 (21 + 20). The whole
   graph selection reads `315 passed, 11 skipped, 5203 deselected, 6 errors`; the 6
   errors come from two worker/rehearsal test files that stub `gpu_adapter` through
   `sys.modules`, and both files pass when run alone. This is not a fully green suite
   claim.

## 7. Reproduction

```
cd <composition root>
python -m tools.graph6_cube_teaching_profile --output <new path>
python -m pytest tests/test_graph_teaching_cube_profile.py \
                 tests/test_graph_teaching_cube_node.py -q
```

The tool refuses to overwrite an existing file, so a re-run proves reproducibility by
producing a byte-identical second copy.
