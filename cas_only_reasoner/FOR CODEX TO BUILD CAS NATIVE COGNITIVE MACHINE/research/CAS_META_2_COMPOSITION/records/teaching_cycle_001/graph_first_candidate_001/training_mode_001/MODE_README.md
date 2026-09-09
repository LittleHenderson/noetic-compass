# Targeted ^6 specialist — training mode (pure phase complete)

The training mode for the graph-first candidate exists and is pure-tested:
`cas_meta2/graph_teaching/trainer.py`. No GPU, no AWS, no torch import, no
cas_cjt import, no reservation. The ledger is untouched.

## What the mode does

1. Builds the whole-part lesson records from the **train + practice** splits
   only (`FIND_SHARED_PART`, `LIST_PARTS`, `REACHED_VIA`). The sealed
   validation/test splits are never read by the training path.
2. Resolves the registered target: contract
   `cas.cjt.operation.^6.decompose/0.2`, plasticity role `operator.^6`.
3. Freezes every parameter outside the admit-listed group and records a
   digest snapshot of all parameters before training.
4. Runs exactly the bounded number of updates (frozen budget below), applying
   checker-derived corrections; the graph supplies facts, the checker supplies
   feedback, the module makes the selections. No answer edges exist.
5. Records a digest snapshot after training and reports **containment**:
   any parameter digest change outside the allowlist is flagged by name.
6. Reports per-op before/after losses, actual completed updates, and the
   checkpoint identity; claims stay honest
   (`specialist_claimed: false`, `sealed_splits_read: false`,
   `answer_edges_present: false`).
7. `evaluate_sealed()` is the separate post-training evaluator that reads only
   the sealed validation/test splits.

## Frozen budget (declared and enforced by the mode)

```text
learning_rate        = 0.003
max_optimizer_steps  = 64
max_wall_seconds     = 600.0
```

## Two arms

`launch(..., arm="cas")` and `launch(..., arm="generic")` train on the same
graph records; only the prompt framing differs (CAS adds the three Noetic
questions). Reports are produced per arm.

## The honest gap (what the AWS authorization would fund next)

`real_framework()` fails closed with `GRAPH_TRAINING_FRAMEWORK_HOOK_NOT_BUILT`
until the authorized AWS adapter build implements
`gpu_adapter.build_graph_training_framework` (real torch via `_cuda()`, the
real decompose module from cas_cjt, real `resolve_plasticity_groups`, and the
real learner factory). That adapter, its package, and the launch path are the
next build step — see `AUTHORIZATION_REQUEST_AWS.md`. No run occurs without an
owner-signed authorization for a new job and a new `$4.00` reservation.

## Pure evidence

`tests/test_graph_training.py` — 12 tests: frozen budget, unique decompose
contract, scope freezing, containment reporting, bounded updates with
before/after per-op losses, train/practice-only records, launch report shape
and honest claims, forbidden-change flagging, budget-mismatch refusal, arm
framing, sealed-only evaluation, and no-heavy-imports at module level.
See `checks_001/` for the captured full-suite receipt.
