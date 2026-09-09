# Graph-first candidate + targeted ^6 trainer mode — RESULTS (pure phase)

## Status

The targeted-module trainer mode is built and pure-tested. **No training has
been performed.** No GPU, no AWS launch, no reservation, no torch or cas_cjt
import, no change to accepted models or the ledger.

## What was built (owner-directed, all corrections enforced)

- Graph model — four pieces: node = idea box (label + contents about itself),
  connector = carries the commonality of its two adjacent boxes (validated),
  branches ARE connectors, no limit on connectors/contents, no answer edges,
  derived connectors never stored.
- Lesson families — binding (color/shape/value, one/two hops, changed
  request) and whole-part ^6 (LIST_PARTS, FIND_SHARED_PART, REACHED_VIA over
  bicycle/cart/wheel-style families with renamed, shuffled labels).
- Deterministic reference checker; CAS and generic framings share identical
  graphs and answers.
- Sealed dataset: train 48 / practice 16 / validation 16 / test 16, seed
  `20260909`, byte receipt in `dataset_001/`.
- Trainer mode `cas_meta2/graph_teaching/trainer.py`: targets contract
  `cas.cjt.operation.^6.decompose/0.2`, plasticity role `operator.^6`,
  everything else frozen; bounded updates (64 steps, 600 s wall, lr 0.003);
  per-op before/after losses; checkpoint identity; containment report naming
  any forbidden parameter change; `evaluate_sealed()` reads only the sealed
  splits, post-training.
- Honest gap: the real AWS framework hook
  (`gpu_adapter.build_graph_training_framework`) is the next build step,
  authorized only by a signed run request (see `AUTHORIZATION_REQUEST_AWS.md`,
  job `cas-meta2-teaching-graph-20260909011302-e654ae56`, NOT launched).

## Test evidence (byte-verifiable)

- Full suite: **116 passed, 24 subtests passed**.
- `tests/test_graph_training.py` (12), `tests/test_graph_teaching.py` (20),
  `tests/test_binding_fit_launch.py` (43), `tests/test_binding_fit_worker_execution.py` (3),
  `tests/test_budget.py` (38 incl. subtests).
- Captured output: `checks_001/pytest_output.txt`, sha256
  `0cc529b240da26b07fb66544eab333389e2a45db0b3d0427a7164af49941623e`,
  receipt `checks_001/receipt.json`.

## Full local path to these results

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\teaching_cycle_001\graph_first_candidate_001\training_mode_001\RESULTS.md`

(Companion records in the same directory: `MODE_README.md`,
`AUTHORIZATION_REQUEST_AWS.md`; checks in `checks_001\`.)

## Next step

Owner-signed authorization for the AWS adapter build + the single paid
training run (new job, one new `$4.00` reservation). Until then: nothing runs.
