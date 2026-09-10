# TASK_BINDINGS — how each verified-teaching exercise would reach the ^6 module

**Status:** specification only. Nothing in this file was executed against a model.
Every function named here exists in the repository at the path given, and
`tests/test_graph_teaching_verified_teaching.py::test_task_bindings_name_real_functions_with_the_documented_shapes`
checks each signature, so this document cannot drift from the code.

The chain, per the directive:

```text
public graph + question + three choices
        |
        v
existing public-record codec and tokenizer        cas_meta2/codec.py, adapter.public_records
        |
        v
declared graph adapter                            adapter.encode_graph / build_task
        |
        v
candidate ^6 module                                real_framework.build_graph_training_framework
        |
        v
existing three-choice scoring                      adapter.readout / predict / score
        |
        v
recorded prediction                                observation contract below
        |
        v
teacher correction during authorized training      trainer.scope_parameters, containment_report
```

No new head, no new output vocabulary, no new loss. A cube does not create a
trainable matrix or an operation registration.

## 1. Repository functions and the shapes they take

| Function | Signature (verified) | Shape it consumes / returns |
|---|---|---|
| `reference.direct_parts` | `(graph, idea_id)` | list of constituent labels, sorted |
| `reference.shared_parts` | `(graph, a, b)` | list of shared direct-constituent labels |
| `reference.reach_kind` | `(graph, part_id, idea_id)` | `"direct"` / `"via:<label>"` / `"absent"` |
| `codec.validate_public` | `(public)` | requires exactly `{"problem", "observations"}`; three slots `0,1,2`; eight finite numbers each |
| `adapter.public_records` | `(record, arm)` | returns `{"public", "encoded_options", "encoded_correct_index", "record_id", "op", "correct"}` |
| `adapter.build_task` | `(record, arm)` | returns `{"record_id","op","arm","tokens","options","correct_index","correct","graph","prompt"}` |
| `adapter.encode_graph` | `(graph_record)` | deterministic token list from a `cas-meta2-graph-teaching-graph/1` record |
| `adapter.readout` / `predict` / `score` | `(prediction_vector, option_vectors[, correct_index])` | dot-product scores, argmax, cross-entropy |
| `real_framework.build_graph_training_framework` | `(torch, device, *, seed, encoder)` | the framework that builds the ^6 module |
| `real_framework.TARGET_CONTRACT_ID` | constant | `cas.cjt.operation.^6.decompose/0.2` |
| `real_framework.TARGET_PLASTICITY_ROLE` | constant | `operation:^6` |
| `trainer.scope_parameters` | `(framework, model)` | `{"allowed", "frozen", "contract_id", "role"}` |
| `trainer.containment_report` | `(before, after, allowed)` | `{"contained", "permitted_changes", "forbidden_changes", "total_changed"}` |

The exercise record shape the codec consumes is the existing one:
`{schema, split, op, graph, question, options, correct, reference, framings, record_id}`,
with the frozen `EXERCISE_SCHEMA` (`cas-meta2-graph-teaching-exercise/1`). The
cube lesson compiler already produces one
(`cube_profile.compile_public_exercise`), and a test feeds it through
`codec.validate_public` successfully.

## 2. Binding per exercise in this bundle

| # | Exercise | Task profile | Binding | Status |
|---|---|---|---|---|
| 1–5 | `REACHED_VIA(whole, candidate)` — Cart, Frame, Platform, Rim, Wheel | `component-route/0.1` | reuse the existing route task: three choices over `direct` / `via:<constituent>` / `absent`, argmax, cross-entropy | **supported** |
| 6 | `LIST_PARTS(whole)` | `whole-answer/0.1` | reuse the existing part-list task: three list alternatives | **supported** |
| 7 | `FIND_SHARED_PART(first, second)` | `whole-answer/0.1` | reuse the existing shared-part task: shared constituent or `none` | **supported** |
| 8 | `REACHED_VIA(whole, candidate)` final | `whole-answer/0.1` | reuse the existing route task at the complete-answer level | **supported** |

Component and final route questions share the same output vocabulary, as the
directive requires. Shorter component questions are *not* a new task; they are
the same `REACHED_VIA` task asked about one candidate at a time.

## 3. Bindings that are deliberately unsupported

| Candidate exercise | Why it is unsupported | Recorded as |
|---|---|---|
| "select the analogy that preserves the relationship" (face 3) | needs a declared analogy output vocabulary, loss, and training adapter | `new_scored_profile_status: "NOT_IMPLEMENTED"` |
| "select the correct role correspondence between two views" (face 4) | same | `NOT_IMPLEMENTED` |
| "select a valid recomposition or complete explanation" (face 6, unrestricted) | same | `RESTRICTED_FINAL_LIST_BINDING_PROPOSED; STORY_TASK_UNIMPLEMENTED` |
| "select the definition/function that matches" (core + face 1) | same | `NOT_IMPLEMENTED` |
| "select the relevant supplied contextual relation" (face 2) | same | `NOT_IMPLEMENTED` |

A new neural head or output vocabulary is **not** to be hidden inside the
adapter. These stay presentation-only until a task profile is declared and
approved.

## 4. How each teaching presentation would affect the learner

| Stage | Material | Effect on a learner | Binding |
|---|---|---|---|
| 1 name/function | core + face 1 | stored text; no module input, no prediction, no update | `UNIMPLEMENTED` (numeric delivery) |
| 2 context | face 2 | the public graph itself; the *graph* is encoded for every scored exercise, the face text is not | partial: graph yes, face text `UNIMPLEMENTED` |
| 3 analogy | face 3 | stored text only | `UNIMPLEMENTED` |
| 4 explicit correspondence | face 4 | stored text only | `UNIMPLEMENTED` |
| 5 guided decomposition | face 5 | five scored component questions reach the module as three-choice tasks | **bound** |
| 6 recomposition/story | face 6 | demonstration only; the restricted final list question is the scored part | story `UNIMPLEMENTED`, list **bound** |
| 7 reinforcement | all views | repeats the bound final question with declared variations | **bound** |

Text that is merely stored, never encoded, and never involved in an update is
**not** counted as effective neural teaching. That is why stages 1, 2, 3, 4 and 6
carry `numeric_delivery_binding: "UNIMPLEMENTED"` in the compiled plan rather
than an implied delivery.

## 5. The observation contract for a future authorized run

When an authorized learner eventually executes, each event retains: the exact
public exercise identity; the actual assistance state; the predicted option and
its semantic value; all three scores or logits; the corrective target and the
moment it was released; option token and item lengths; option vector norms when
measured; checkpoint and update identity; and the actual parameter-change
observations. **Missing measurements are `unavailable`, never zero.** This
answers the earlier evidence gap where practice passes lacked predicted option
strings and per-option scores.

Phase rules: `DEMONSTRATION` shows the worked solution and any prediction is
assisted; `PREDICT_THEN_CORRECT` records the prediction before releasing the
checked correction; `UNASSISTED_MEASUREMENT` receives no worked solution, no
teacher-verified subanswers, and no correct prefix, records the prediction before
evaluating it, and does not update.

Endpoint rule: hashes of saved states compare endpoints only. They do not
establish what happened to unsaved components.

## 6. What the update path would be, and what it excludes

```text
contract    cas.cjt.operation.^6.decompose/0.2
role        operation:^6
updates     the registered module's own parameters only, through
            trainer.scope_parameters
excluded    the frozen encoder, the frozen dot-product readout, anything
            outside the admitted plasticity role
objective   cross-entropy over the three public slots against the declared
            target index
check       trainer.containment_report must show no digest change outside
            the allowlist
```

In this deliverable no module is constructed and no optimizer step is taken:
`optimizer_updates: 0`, `delivered_neural_lessons: 0`, `neural_calls: 0`.
