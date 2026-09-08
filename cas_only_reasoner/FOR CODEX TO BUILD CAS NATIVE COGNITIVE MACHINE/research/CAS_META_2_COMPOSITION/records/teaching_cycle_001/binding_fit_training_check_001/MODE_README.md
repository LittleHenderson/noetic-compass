# Small training-fit mode — `cas_meta2/binding_fit_training`

Owner-authorized design-only build for
`records/teaching_cycle_001/binding_fit_training_check_001/` (see
`OWNER_AUTHORIZATION.json`). This document describes the mode, its budget
declaration points, and the launch interface the authorized run will call.
No neural work, AWS reservation, or launch is performed here.

## What the mode does

Question: **can the CAS/generic binding learning path acquire the compact task
on short task-only inputs?**

1. **Cases** — 24 balanced known binding examples, 8 per binding slot
   (target_binding 0/1/2), drawn from the frozen training families via
   `teaching_cycle.data.build_dataset(seed)` and selected from
   `splits["train"]` only. It never reads `test_fresh`, `test_context`,
   `test_names`, or `development` targets.

2. **Presentation** — SHORT task-only inputs with no explanatory guidance,
   rendered by reusing `teaching_cycle.lesson_contract.make_public` (the
   unassisted wording). The supervised answer is supplied separately as
   `target_binding`; it is never printed inside the question.

3. **Training** — for each family (`cas`, `generic_attention`), actual optimizer
   updates through the identity-checked backward/step contract already proven in
   `teaching_cycle/gpu_adapter.py`:
   `optimizer.zero_grad(set_to_none=True)` → forward → cross-entropy loss →
   `loss.backward()` → identity re-check → `optimizer.step()`, with before/after
   state-identity hashes. The step sequence mirrors
   `gpu_adapter.BindingLearner.teach` (same discipline, same error convention),
   reusing `gpu_adapter._cuda`, `guided_application.fit_tokenizer`, and
   `policy.build_matched_policies` in the real launch path.

4. **Measurement** — loss and accuracy are recorded BEFORE and AFTER the
   updates, per family, plus the optimizer step count and the before/after
   state-identity hash. Forward-only measurement (`evaluate`) is never reported
   as training fit: `training_fit` is `OPTIMIZER_UPDATES_PERFORMED` only when the
   state hash changed and steps advanced, otherwise `FORWARD_ONLY_NOT_FIT`.

5. **Refusals** — the mode refuses empty cases, wrong shapes/balance, missing
   observers, answer-bearing presentations, non-train records, and any attempt
   to read final evaluation targets.

## Budget declaration points

Two parameters, both with strict bounds enforced by `validate_budget`:

| Parameter | Type | Default bound | Meaning |
|---|---|---|---|
| `max_optimizer_steps` | `int` (>= 1) | `48` | Total optimizer steps across the whole run (both families). `48 = 24 cases × 1 step × 2 families`, i.e. "single-digit per example" scale; split evenly per family (`24` each). |
| `max_wall_seconds` | finite `int`/`float` (> 0) | `600.0` | Total wall-clock seconds for the whole run; a step that would cross the bound is refused with `WALL_BUDGET_EXCEEDED`. |

The exact frozen values are declared in the run's `OWNER_AUTHORIZATION.json`
before launch; the defaults above are the mode's declaration points.

## Launch interface

The run calls (all keyword-only):

```python
cas_meta2.binding_fit_training.mode.launch(
    *,
    run_id,                     # str, required (e.g. "binding-fit-001")
    cases=None,                 # optional list of 24 balanced train cases; default builds them
    seed=20260908,              # dataset seed for case building
    max_optimizer_steps=DEFAULT_MAX_OPTIMIZER_STEPS,   # 48
    max_wall_seconds=DEFAULT_MAX_WALL_SECONDS,          # 600.0
    learning_rate=0.003,
) -> dict  # the training-fit report
```

`launch` builds the real learners via the frozen `gpu_adapter`/`policy`
machinery and returns the `run_fit` report (schema
`cas-teaching-binding-fit-training/1`) containing per-family before/after
loss, accuracy, optimizer steps, and state-identity hashes.

The pure, testable core is `run_fit(records, learners, *, max_optimizer_steps,
max_wall_seconds, wall_clock=time.perf_counter)`, which operates on injected
learners so tests never import a real tensor library. `import_torch` is the
mode's only torch-import seam (tests monkeypatch it).

## Tests

`tests/test_binding_fit_training.py` — 25 pure tests with injected fakes,
covering case balance, short presentation, before/after loss+accuracy, the
optimizer actually running through the identity-checked contract, budget
refusals, and final-target access refusal. No real tensor library is imported.
