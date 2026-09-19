# Pre-flight review plan — the two adversarial reviews of the BUILT code

> Written 2026-09-19 at HEAD `489cda65`, before the build finished, so that the reviews can start the moment it
> does and so that what this session learned about where this codebase breaks is not lost.
>
> **Status: PLAN. Neither review has been run.** The practice study ran the same pair and its *second* review found
> three leaks the first redesign had created, so both are required and the second must re-attack the first's fixes.

## 0. What is being reviewed, and when

The nine new files, once built and pytest-green, **before any spend**. Two reviewers, both read-only, both $0, both
pure Python + `numpy` where needed, **no torch and no GPU** — the learner's own guard forbids a local run anyway
(`LINUX_WORKER_REQUIRED`, `TYPED_LEARNER_CUDA_REQUIRED`).

| # | lens | the question it must answer |
|---|---|---|
| R1 | **leaks, shortcuts and custody in the RUN path** | can the study print a label it has not earned, or read an answer it must not? |
| R2 | **run-killers and pipeline fit in the BUILT code** | will a paid job crash, stall, or deliver nothing? |

Each reviewer must produce a findings file with **one instruction per finding** that a builder can apply, and a
severity from a fixed vocabulary. Reviewers must not restate the design reviews: those are done, their findings are
folded into design v0.2, and the question now is whether the **code** honours them.

## 1. R1 — leaks, shortcuts and custody

Everything here has a specific, measured precedent from this session. Each is a place the project has already been
wrong once.

1. **Does any input still carry a held answer?** The reader was changed twice (labels dropped; `is_primary_label`
   removed). Verify against `checker.py`'s own rules that no field the reader emits is an answer component for any
   of the eight kinds, and that no field it emits is *derivable only* from a held answer.
2. **Does any REGISTERED baseline solve gate questions?** The frozen baseline list is: the untrained machine, the
   registered input-blind shortcut, the flag rules, the rank-only rule, the oracle one-hop rules, and the
   majority-symbol rule fitted on **trained** records. For each, state what it scores on the frozen 18 and confirm
   the removal list matches. **A baseline may never be fitted on held answers** — that error was made once this
   session and withdrawn.
3. **The custody order.** Phase A must extract public vectors only and must run **before** the model is seeded;
   phase B must run **after** every pointer evaluation, reload and replay. Verify in the code, not in the docs.
4. **The `TEXT` and `DIRECT_READ` tiers** must never contribute to a label. `role_set`'s excerpt *is* the answer
   (LK1) and `definition`/`context` are two-flag copies (LK2).
5. **`correspondence`** must be **reported** and excluded from the label as a declared false negative, not silently
   dropped. The reader must still print its per-kind result.
6. **The oracle ceilings** must be printed beside the label. A run that gains on `parts` while matching the one-hop
   rule has demonstrated nothing beyond the rule.
7. **The evidence publisher is create-only.** Any file under `results/` that is rewritten or grows must fail the
   upload. Verify the `<name>.partial` + rename discipline and that growing logs live outside `results/`.
8. **A flag-copy-only outcome must receive no label.** This is the single most important behavioural test in the
   build. Confirm the gate reader has it and that it fails when the label logic is loosened.

## 2. R2 — run-killers and pipeline fit

1. **The phase order in the built worker**, and specifically: phase A before seeding (restoring overwrites all
   three RNG streams with no save/restore, `learner.py:358-362`), and phase B last.
2. **`EXPECTED_ARTIFACTS`**: unique, under 500, `required_count == len + 3`, and covering every file the worker
   can be expected to write — including the checkpoint-check artifact and the ablations.
3. **A "reported" check must not be able to fail the job.** The checkpoint-check artifact is written with a
   `status` of `COMPLETE` or `FAILED` **inside it**, and every module it needs is imported at start-up outside any
   `try` (review RK6: a poisoned `attestor.snapshot()` raises `FAILED_IMPORTS` after the money is spent).
4. **The counter key set.** `counter_delta` requires the two snapshots' key sets to match exactly, and the summed
   deltas are compared as canonical bytes against `expected_main_delta`. The contract's `MAIN_COUNTERS` and the
   learner's `COUNTER_KEYS` are the same **11** keys today; one extra or missing key fails
   `MAIN_TRAINING_COUNTERS` after the spend.
5. **The schema handshake.** `graph_training_curriculum_launch.py:1018-1020` demands the worker's `CANDIDATE`,
   `CONFIG_SCHEMA`, `RESULT_SCHEMA` and `FAILURE_SCHEMA` be byte-identical to the launcher's, and the FAILED status
   must be listed in the launcher's `failure_statuses`. Verify by import, both directions.
6. **Deterministic mode.** `torch.use_deterministic_algorithms(True)` is on. Scatter, index, embedding-backward and
   `linalg` paths can raise under it. The learner claims dense matmuls and one-hot matmuls; check it, and check the
   `^6` block's own ops.
7. **Score bounds and loss agreement**: `|score| <= 1e6` and the tensor/plain-Python loss agreement `<= 2e-5`.
8. **The shrunken smoke path.** The worker must run a reduced pass count and reduced evaluation points **without
   changing a registered constant**, or the smoke is impossible and the timing unknown.
9. **The timing measurement.** The job must record per-phase seconds and enough counters that a full-run projection
   is computable — that projection is what decides the pass count and whether the reservation holds.
10. **`python -O` strips `assert`.** Every stop in a spend path must be an explicit `require`, never an `assert`.
11. **Windows line endings.** Every new file must be LF; a CRLF `.py` fails the AWS package build with
    `INPUT_NOT_COMMITTED`. The reviewer should check the bytes, not the editor.

## 3. What each reviewer must NOT do

- Not re-litigate the design. Design v0.2 is final and the two design lenses have reported.
- Not propose a different hypothesis, a different gate, or a weaker threshold. The gate population is frozen at
  **18** with `b = 7`; a reviewer who thinks that is wrong should say so as a `CONFLICT:` and leave the decision to
  the owner, not change it.
- Not run anything paid, and not run the learner at all.

## 4. After the reviews

Fix the findings, then run the second review against the fixed code — the practice study's experience is that the
second review finds what the first fix created. Only then: the $0 dry run for all three seeds, then the AWS smoke.
