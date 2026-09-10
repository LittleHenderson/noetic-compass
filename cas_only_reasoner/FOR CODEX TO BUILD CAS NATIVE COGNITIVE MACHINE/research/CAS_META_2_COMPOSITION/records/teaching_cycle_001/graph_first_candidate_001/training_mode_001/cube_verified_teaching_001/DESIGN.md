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
| `tests/test_graph_teaching_verified_teaching.py` | 23 tests, all passing |
| `tools/graph6_cube_node_check.py` | extended with an opt-in `--verified-teaching` section and an `--artifacts` writer; the default report is unchanged, so the earlier `CUBE_NODE_CHECK.json` still reproduces byte-for-byte |
| `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_verified_teaching_001/` | `DESIGN.md`, `TASK_BINDINGS.md`, five `.jsonl` records, `cycle_plan.json`, `check_report.json`, `SOURCE.json` |

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
| `public_context_digest` reproduced | **no** |
| cycle plan stages and lesson variants | identical |

The identity rule the fixture documents ("SHA-256 of compact sorted-key UTF-8
JSON") was reverse-engineered from the fixture and confirmed: `context_id`,
`choice_id`, and `exercise_id` all reproduce under the repository
`canonical()`. The repository profile is ASCII-escaped by default while the
fixture says `ensure_ascii=false`; for this content the two coincide, and a
versioned translation is declared for non-ASCII content.

**One authored value is not reproduced.** `public_context_digest` is not any
digest derivable from the public context under the repository canonicalization —
it was searched across every subset of the context fields and several
repository-shaped graph records, with no match. It is reported as
`"unreproduced_authored_values": ["public_context_digest"]` rather than matched by
inventing a rule.

## 5. Counts kept apart

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

## 6. Scope evidence

- The module imports `graph`, `cube_node`, `reference`, and (inside one function)
`cube_profile`. A test asserts it contains no `import torch`, no `boto3`, no
`gpu_adapter`, and no `real_framework` import.
- The pinned cube bundle and the delivered fixture are read, never written; a
test re-checks their hashes.
- `TASK_BINDINGS.md` names repository functions verified from source, and a test
checks each signature so the document cannot drift from the code.

## 7. Known limits (unchanged from the fixture, plus what this work adds)

1. Only an illustrative small scene, not a balanced dataset or held-out panel.
2. Numeric delivery is unimplemented for stages 1, 2, 3, 4, and 6; their content
   is prepared, not bound.
3. The story/recomposition task remains unimplemented; stage 6 carries a
   restricted final-list binding proposal only.
4. The simulated transport is not a model prediction.
5. Shorter component questions do not by themselves fix or disprove a
   list-scoring bias; the list-length/readout hypothesis stays open and the
   prepared contrast probe stays pending.
6. `public_context_digest` remains unreproduced.
7. Six pre-existing suite errors in two worker/rehearsal files remain (module
   stubbing order, environment-dependent); reported, not weakened.

## 8. Reproach-free reproduction

```
cd <composition root>
python -m pytest tests/test_graph_teaching_verified_teaching.py -q     # 23 tests
python -m tools.graph6_cube_node_check --verified-teaching \
       --artifacts <new dir> --output <new dir>/check_report.json
python -m tools.graph6_cube_node_check --output <new path>             # unchanged report
```
