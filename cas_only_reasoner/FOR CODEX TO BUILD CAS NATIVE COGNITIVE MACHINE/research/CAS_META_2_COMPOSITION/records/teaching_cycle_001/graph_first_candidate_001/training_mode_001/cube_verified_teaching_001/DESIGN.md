# CUBE_VERIFIED_TEACHING_001 — design record

**Completion statement:** **`TEACHING_DATA_READY_NEURAL_UNTESTED`**

The checked intermediate teaching records, worked traces, public/teacher
separation, and task-binding specifications are implemented and tested. No neural
lessons were delivered, no weights were updated, and no paid execution was
authorized.

**Owner directive:** implement a small, deterministic teacher that turns the
existing cube graph into checked component decisions and a complete worked
answer, compiles them into the existing lesson interfaces, and never lets the
teacher's solution substitute for the learner's independent result.

**Execution boundary:** no model loading, no neural execution, no training, no
reservation, no AWS launch, no accepted-model change. The cube schema, accepted
models, existing graph semantics, registered curricula and panels, retained
checkpoints, historical results, and the pending contrast probe are untouched.
Pooling, token embeddings, list normalization, the readout, and the ^6
architecture were not changed.

## 1. What was built

| File | Role |
|---|---|
| `cas_meta2/graph_teaching/verified_teaching.py` | the deterministic teacher, the schema objects, the compiler |
| `cas_meta2/graph_teaching/verified_training.py` | the candidate-only execution connection and its dry-run plan |
| `cas_meta2/graph_teaching/candidate_run.py` | the instrumented candidate wrapper, the explicit execution order, and the proposed teaching schedule |
| `tests/test_graph_teaching_verified_teaching.py` | 23 tests |
| `tests/test_graph_teaching_verified_training.py` | 12 tests |
| `tests/test_graph_teaching_candidate_run.py` | 12 tests |
| `tools/graph6_cube_node_check.py` | extended with an opt-in `--verified-teaching` section and an `--artifacts` writer; the default report is unchanged, so the earlier `CUBE_NODE_CHECK.json` still reproduces byte-for-byte |
| `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_verified_teaching_001/` | `DESIGN.md`, `TASK_BINDINGS.md`, `EXECUTION_CONNECTION.md`, `CANDIDATE_RUN_001.md`, `SOURCE.json`, `check_report.json` (revision 3), `check_report_rev2.json` (preserved), and `exports/<ordering_mode>/` |

Report revisions: `check_report_rev2.json` (sha256 `5e145595…e545b`) is preserved
unchanged; `check_report.json` is revision 3, which carries the corrected stub counters
and the candidate preparation.

Each export directory holds one ordering mode and nothing else: the five `.jsonl`
records, `cycle_plan.json`, and an `EXPORT_MANIFEST.json` naming the mode, the ordering
rule, the slot distribution, the slot-alignment summary, and the field translation.

Nothing else was created: no service, no launcher, no second framework.

## 2. The teaching chain, and what each link is checked by

```text
public graph
   -> component questions (existing REACHED_VIA semantics)
   -> teacher-checked answers with grounded witnesses
   -> a checked explanation connecting the component decisions
   -> the original complete-answer question
```

Compiled counts, matching the delivered fixture exactly: 1 public context, 8
public exercises (5 `component-route/0.1` + 3 `whole-answer/0.1`), 8 teacher
targets, **16 step contrasts**, 1 teacher trace with 5 component corrections and
1 final answer, 6 lesson variants, 5 practice variants, 7 stages.

### Named roles bind to the reference function's real argument order

The compiler never infers argument order from English. `ROLE_BINDINGS` declares
the mapping and `_verify_role_bindings()` checks it against
`inspect.signature` at import time:

| Operation | Named roles | Reference function | Real parameters |
|---|---|---|---|
| `LIST_PARTS` | `whole_id` | `direct_parts` | `(graph, idea_id)` |
| `FIND_SHARED_PART` | `first_whole_id`, `second_whole_id` | `shared_parts` | `(graph, a, b)` |
| `REACHED_VIA` | `whole_id`, `candidate_id` | `reach_kind` | `(graph, part_id, idea_id)` |

So `REACHED_VIA(whole_id, candidate_id)` becomes
`reach_kind(graph, part_id=candidate_id, idea_id=whole_id)`: the *candidate* is
the part and the *whole* is the idea. A test asserts this, and a change to the
reference signature fails closed with `VT_REFERENCE_SIGNATURE_CHANGED`.

### Verification checks meaning, not parsing

| Claim | Obligation checked |
|---|---|
| `direct` | the branch exists with that whole, that direction, that constituent (`VT_WITNESS_BRANCH_ENDPOINT_MISMATCH`) |
| `via:X` | the branch references form the contiguous supported path from whole to candidate (`VT_WITNESS_PATH_NOT_CONTIGUOUS`, `VT_WITNESS_PATH_MISMATCH`) |
| `absent` | a complete relevant inventory is declared (`VT_WITNESS_ABSENCE_REQUIRES_COMPLETE_INVENTORY`, `VT_WITNESS_ABSENCE_IN_INCOMPLETE_CONTEXT`); "no connection was recorded" never means "no connection exists" in an incomplete graph |
| `complete list` | both obligations: no foreign member (`VT_INVENTORY_FOREIGN_MEMBER`) and no missing member (`VT_INVENTORY_MISSING_MEMBER`), with the branch set matching the declared inventory |
| `unique shared part` | exactly one shared constituent (`VT_SHARED_PART_NOT_UNIQUE`), witnessed by both containment branches |

A target starts `PENDING_REFERENCE_CHECK` with `checker_identity: null`, exactly
as the delivered fixture leaves it. After compilation, all 8 targets read
`VERIFIED` with `checker_identity =
cas_meta2.graph_teaching.reference@aab7af24638c842b` (the digest of
`reference.py`). A field saying "verified" is never the verification.

**A false intermediate step disqualifies a positive trace.** `verify_trace`
checks every component step; one false step makes the trace `REJECTED` even when
the final list answer is correct, and the faulty step is retained separately as
`NEGATIVE_STEP_EXAMPLE`. The test demonstrates exactly this: a "Rim is a direct
Bicycle part" step is refused, the final `LIST_PARTS` target still verifies, and
the trace is rejected.

### Contrasts, and no second model

Each exercise carries two contrasts (16 in total) between the positive choice and
each verified negative under the *same* public context. Every contrast is
`VALIDATED` with one of the checked reason codes:

| Reason code | Contrasts |
|---|---|
| `FOREIGN_PART` | 6 |
| `MISSING_REQUIRED_PART` | 5 |
| `DIRECT_VS_INDIRECT` | 5 |

An equally correct alternative is never labelled a negative
(`contrast_reason` returns `None` when the choice equals the derived answer). No
pairwise reward loss, no preference model, no second optimizer update: the
learning interface remains ordinary correct-choice supervision.

## 3. The answer boundary

Three rules, all tested:

1. **Public identity covers public material only.** `exercise_id` and
   `choice_id` are digests of the record minus its own id, bound to the
   repository `canonical()` profile. No target, witness, or preferred-choice
   label enters them.
2. **Slot order never depends on the answer.** The declared rule permutes the
   three choices with a seed over the question and the *set* of choices. The
   earlier draft would have placed the answer in slot 0 in all 8 exercises; the
   shortcut check caught it, and the distribution is now 2/3/3 across slots
   0/1/2. The delivered fixture's authored order is used only in
   `choice_order="authored_fixture"` mode, to reproduce public identity.
3. **`prefix_mode: "none"`.** Each prediction receives its declared graph and
   question. `final_prediction_receives_component_answers` is false and the
   compiler refuses to attach component answers to a final exercise
   (`VT_TRACE_COMPONENT_PROFILE`, `VT_TRACE_COMPONENT_REPEATS_FINAL`).

Visibility is the declared `graph-only/0.1` profile: the entire permitted raw
graph, the question and the three choices are retained; derived inventories,
solved intersections, worked paths and narrative solutions are withheld, using
the same single declaration list as the cube profile
(`VT_VISIBILITY_DECLARATION_DIVERGED` guards against the two drifting apart). An
explicitly assisted event may release the withheld fields afterwards; an
unassisted event may not. `answer_boundary_check` recompiles the same question
under several declared targets and requires identical bytes.

## 4. Fixture compatibility, measured

The delivered `Cube_Verified_Step_Example_v0.1.json` (36,940 bytes, sha256
`dcda4cd6be8dad598e06646adb999250c4491c1719b7922d54473c7c169a8be4`) is compared,
not trusted:

| Reading | Result |
|---|---|
| counts (contexts, exercises, targets, contrasts, traces, variants) | identical: 1, 8, 8, 16, 1, 6 |
| `context_id` reproduced | yes |
| choice sets matching, compared by question | 8 of 8 |
| `exercise_id` reproduction, authored choice order | **8 of 8** |
| `exercise_id` reproduction, declared choice order | 2 of 8 (choice order differs on 6) |
| `public_context_digest` reproduced | **16 of 16** (see below) |
| cycle plan stages and lesson variants | identical |

The identity rule the fixture documents ("SHA-256 of compact sorted-key UTF-8
JSON") was reverse-engineered from the fixture and confirmed: `context_id`,
`choice_id`, and `exercise_id` all reproduce under the repository
`canonical()`. The repository profile is ASCII-escaped by default while the
fixture says `ensure_ascii=false`; for this content the two coincide, and a
versioned translation is declared for non-ASCII content.

### The previously "unreproducible" digest is resolved, and my reading was wrong

The earlier version of this record reported `public_context_digest` as an
authored value the compiler could not reproduce, after searching subsets of the
graph context. **The owner traced it: the field hashes the COMPLETE public
exercise, including its `exercise_id` — "context" there means the whole decision
context, not the shared graph.** Re-checked here: **all sixteen values reproduce
exactly** under `sha256(compact sorted-key UTF-8 JSON of the public exercise)`.
My earlier search was looking at the wrong scope because the field name was
ambiguous; that reading is withdrawn, not softened.

The candidate translation therefore carries two unambiguous names, recorded in
every export manifest:

| Name | Scope | Example |
|---|---|---|
| `public_exercise_digest` | the complete public exercise, its own id included | the fixture's 16 values, reproduced |
| `public_graph_digest` | the shared graph context only (scene, view, nodes, branches) | a different value, e.g. `b14dad05…` for this scene |

The old ambiguous key `public_context_digest` is **not** emitted by the
compiler. The delivered fixture is preserved unchanged, and the translation is
recorded in `exports/<mode>/EXPORT_MANIFEST.json` under `field_translation`.

## 5. Ordering mode and slot alignment

Every export names exactly one ordering mode, and the artifacts, the check
report, and the manifest for that mode are written together:

| Mode | Rule | Answer-slot distribution | Purpose |
|---|---|---|---|
| `declared` | the three choices are permuted with a seed over the question and the choice **set**, so no slot depends on which choice is correct | 2 / 3 / 3 across slots 0 / 1 / 2 | the candidate export |
| `authored_fixture` | the delivered fixture's authored choice order | 5 / 3 / 0 | fixture reproduction only |

The earlier single export mixed these: `DESIGN.md` quoted the declared
distribution while `teacher_targets.jsonl` had been written in authored order
(5 / 3 / 0). The owner caught the mismatch. Both modes now have their own
directory and manifest, so no file can be read under the wrong mode.

`expected_slot` is derived from the position of `expected_choice_id` in that
exercise's final ordered choices, and `slot_alignment_check` re-derives it
through **all six orderings of three choices**: 8 exercises × 6 permutations =
**48 readings, all aligned** (`all_permutations_align: true`).

**A balanced slot count is not what proves target independence.** The evidence
for that is the boundary reading: `compile_public_exercise` receives a public
case with no target field at all, and `answer_boundary_check` recompiles the same
question under several declared targets and requires identical bytes.

## 6. The candidate-only execution connection

`verified_training.py` makes the connection at the one point where a target enters
the loop, and demonstrates it by driving the **real** `trainer.run_training`
through a recording stub learner:

```text
TeacherTarget.expected_answer -> record["correct"]
  -> adapter.public_records(record, arm)["encoded_correct_index"]
  -> trainer.make_task(record, arm)["correct"]
  -> GraphLearner.step: cross_entropy(scores, encoded_correct_index)   [real_framework.py 297-307]
  -> optimizer.step()   (operation:^6 allowlist only)
```

Readings: 8 records, 64 stub training-step calls, 0 actual optimizer updates, all 8
records reached, the corrective targets used are exactly the teacher's five verified
answers, `neural_execution: false`, `torch_imported: false`, `learner_is_a_stub: true`.
`EXECUTION_CONNECTION.md` records why the connection enters at `run_training`
rather than `trainer.launch` (which has no record-injection parameter), and what a
future authorized run would still need.

`candidate_run.py` then wraps that connection into an instrumented candidate run with the
declared chronological order and a proposed teaching schedule: **8 blocks of 5 component
questions then 3 whole-answer questions, 64 supervised corrections, a declared 5:3
component-to-final ratio, 0 automatic retries**, labelled **checked component teaching**.
`CANDIDATE_RUN_001.md` states the schedule, the evaluation proposal, and the decisions the
owner still has to make. The wrapper rehearses cleanly with injected stubs (64 recorded
predictions, each taken before its own update) and refuses to run without an owner
authorization record.

## 7. Counts kept apart

```json
{"compiled_stages": 7, "presented_stages": 7, "neural_presentations": 0,
 "supervised_decisions": 0, "optimizer_updates": 0, "complete_neural_cycles": 0,
 "distinct_graph_families": 1}
```

A compiled seven-stage plan is not seven neural presentations, a passive
presentation is not an update, and a complete neural cycle needs real delivery
receipts. `actual_execution` records 8 repository reference calls and zero
neural calls, updates, AWS calls, and reservations. The `minimum_complete_guided_cycles_per_family`
and `maximum_optimizer_updates` fields are present and left `null`: neither the
old 64-update allowance nor the earlier 1,024-cycle allocation is imported.
`execution_enabled` is false.

The simulated transport exists only to demonstrate compiler and recording
behaviour; it is labelled `SIMULATED`, `is_model_prediction: false`,
`counts_as_neural_delivery: false`, and its scores read `"unavailable"`, never
zero.

## 8. Scope evidence

- The modules import `graph`, `cube_node`, `reference`, `trainer`, and (inside one
function) `cube_profile`. Tests assert they contain no `import torch`, no `boto3`,
no `gpu_adapter`, and no `real_framework` import; the connection check reports
`torch_imported: false`.
- The pinned cube bundle and the delivered fixture are read, never written; a
test re-checks their hashes.
- `TASK_BINDINGS.md` names repository functions verified from source, and a test
checks each signature so the document cannot drift from the code.

## 9. Known limits (unchanged from the fixture, plus what this work adds)

1. Only an illustrative small scene, not a balanced dataset or held-out panel.
2. Numeric delivery is unimplemented for stages 1, 2, 3, 4, and 6; their content
   is prepared, not bound.
3. The story/recomposition task remains unimplemented; stage 6 carries a
   restricted final-list binding proposal only.
4. The simulated transport and the connection stub are not model predictions.
5. Shorter component questions do not by themselves fix or disprove a
   list-scoring bias; the list-length/readout hypothesis stays open and the
   prepared contrast probe stays pending.
6. The connection check's 64 updates are the frozen budget running on a stub: not
   a training result, and not evidence about learning.
7. Six pre-existing suite errors in two worker/rehearsal files remain (module
   stubbing order, environment-dependent); reported, not weakened.

## 10. Reproduction

```
cd <composition root>
python -m pytest tests/test_graph_teaching_verified_teaching.py \
                 tests/test_graph_teaching_verified_training.py -q   # 35 tests
python -m tools.graph6_cube_node_check --verified-teaching \
       --artifacts <new dir> --output <new dir>/check_report.json   # both export modes
python -m tools.graph6_cube_node_check --output <new path>          # unchanged report
```
