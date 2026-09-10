# EXECUTION CONNECTION — where the teacher's target becomes the training correction

**Status:** candidate-only connection, prepared and checked. `execution_enabled: false`.
No launcher, no reservation, no GPU, no paid run, and no neural execution of any kind.
The connection is demonstrated by driving the **real** `trainer.run_training` loop with a
recording stub learner; the stub is not a model and its responses are not predictions.

## 1. The exact point

```text
TeacherTarget.expected_answer                       verified by the repository checker
        |
        v
record["correct"]                                   built by training_records()
        |
        v
adapter.public_records(record, arm)                 frozen public extraction
        ["encoded_correct_index"]                   the numerical slot
        |
        v
trainer.make_task(record, arm)["correct"]           copied unchanged into the task
        |
        v
GraphLearner.step(task)
        torch.nn.functional.cross_entropy(
            scores, self.tasks[position]["encoded_correct_index"])
                                                    real_framework.py lines 297-307
        |
        v
optimizer.step()                                    permitted plasticity group only
```

That cross-entropy call is the only place a target enters the loop. The index it uses is
produced by the frozen codec from `record["correct"]`, and `record["correct"]` is the
teacher's verified answer. Nothing else supplies a target.

Two indices are reported deliberately, because they can differ:

| Reading | Meaning |
|---|---|
| `declared_slot` | the position of the teacher answer in the exercise's declared choices |
| `encoded_correct_index` | the position in the frozen codec's own order |

The check asserts on the **value found at the numerical slot the loss uses**
(`encoded_options[encoded_correct_index] == teacher answer`) and separately that the
encoded options are a permutation of the declared choices — a set change would mean an
option was dropped or added.

## 2. Where the connection enters, and why not at `trainer.launch`

| Function | Takes records? | Used here |
|---|---|---|
| `trainer.run_training(learner, records, arm, budget)` | **yes** | the connection enters here |
| `trainer.make_task(record, arm)` | per record | turns a record into the learner's task |
| `trainer.TrainingBudget().validate()` | — | the frozen budget (rate, steps, wall seconds) |
| `trainer.scope_parameters(framework, model)` | — | the permitted allowlist, `operation:^6` only |
| `trainer.parameter_snapshot` / `containment_report` | — | before/after proof that only allowlisted parameters changed |
| `trainer.launch(...)` | **no** | not used: it has no record-injection parameter and always runs the registered whole-part dataset |

Adding a `records=` parameter to `launch` would change registered training infrastructure,
so it is deliberately **not** done. A candidate run would either (a) call `run_training`
directly with the cube records and the containment calls around it, or (b) first take an
owner decision to version `launch`.

**Indexing requirement.** The learner must be indexed by the *same* records' public
records — `adapter.public_records(record, arm)` for each cube record. Otherwise
`GraphLearner._position` raises `KeyError`; that is the preserved failure from curriculum
attempt 002, recorded so it is not repeated silently.

## 3. What the check reports

`verified_training.connection_check()` drives the real loop over the eight records:

```json
{"records": 8,
 "optimizer_updates_in_this_check": 64,
 "records_that_received_correction": 8,
 "every_record_reached": true,
 "corrective_targets_used": ["\"Wheel\"", "\"absent\"", "\"direct\"",
                             "\"via:Wheel\"", "[\"Frame\",\"Wheel\"]"],
 "neural_execution": false,
 "torch_imported": false,
 "learner_is_a_stub": true,
 "lesson_exposure": {"records_by_op": {"REACHED_VIA": 6, "LIST_PARTS": 1,
                                       "FIND_SHARED_PART": 1},
                     "updates_by_op": {"REACHED_VIA": 48, "LIST_PARTS": 8,
                                       "FIND_SHARED_PART": 8}}}
```

64 is `trainer.FROZEN_MAX_OPTIMIZER_STEPS`, the frozen budget: this is a wiring check on a
stub, not a training result. The five corrective targets used are exactly the teacher's
verified answers — no other target entered the loop.

`verified_training.dry_run_plan()` lists the nine calls a candidate run would make, in
order, with `execution_enabled: false` and the authorization statement attached.

## 4. What this does not do

- It does not train, load a model, import torch, contact a provider, or reserve anything.
- It does not connect stages 1, 2, 3, 4, or 6. Those remain `numeric_delivery_binding:
  UNIMPLEMENTED` and presentation-only. A stored explanation teaches the learner nothing
  unless it enters a declared learning path; the declared objective is ordinary
  three-choice cross-entropy.
- It does not add a head, a loss, a reward model, a preference loss, or output vocabulary.
- It does not change pooling, token embeddings, list normalization, the readout, the ^6
  architecture, previous results, or any checkpoint.
- It does not touch the pending zero-update contrast probe.

## 5. What a candidate run would still need before it could be authorized

1. An owner GO naming the ordering mode (`declared` in this record) and the arm.
2. A stated guided-repetition minimum and update budget: both are present and `null` in
   `cycle_plan.json`, and neither the old 64-update allowance nor the earlier
   1,024-cycle allocation is imported.
3. A decision on whether the containment proof runs around `run_training` or whether
   `trainer.launch` gains a versioned record-injection parameter.
4. The observation contract fulfilled per event, with missing measurements recorded as
   `unavailable` rather than zero.
