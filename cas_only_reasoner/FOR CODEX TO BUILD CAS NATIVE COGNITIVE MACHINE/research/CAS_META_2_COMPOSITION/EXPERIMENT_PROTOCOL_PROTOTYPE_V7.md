# Exact-original curriculum experiment: v7

Preparation, not a training result. The source-bound registration and current-job
GPU check must admit this experiment before its full training starts. No model,
tensor computation, checkpoint loading, training, or inference runs on the laptop.

## Data and scoring fixed before full training

The planned split is 896 training records, 96 validation records, and 72 test
records. Training contains a new 640-record base plus all 256 original practice
records, with their original contents and provenance preserved. The original
128 pairs stay together and are allowed only in training. The tokenizer learns
from training records only. These counts become actual counts only after the
AWS data child writes and passes `dataset_assembly_receipt.json`.

| Split | Depth 1 | Depth 2 | Depth 3 | Depth 4 | Total |
|---|---:|---:|---:|---:|---:|
| Training | 128 | 384 | 384 | 0 | 896 |
| Validation | 32 | 32 | 32 | 0 | 96 |
| Test | 0 | 0 | 48 | 24 | 72 |

The frozen 8,837-signature inventory excludes all known program structures from
the new base, validation, and test partitions. It includes the previous failed
v6 run's exposed training, validation, and test programs. The original 256 remain
in that exclusion inventory; their explicit training-only import is the sole
exception. The parent checks program, input, and split identities independently
and exports no private test file to the trainer.

The test contains 24 related triplets, not 72 independent structures:

- `same_depth`: an unseen depth-3 program, with new observations and familiar
  wording combinations.
- `wording_shift`: that same depth-3 program and observations, with held-out
  wording combinations.
- `deeper_calls`: its paired unseen depth-4 program, with the same observations
  and familiar wording combinations.

Thus this test measures new program combinations and new task instances together.
It does not separately estimate fresh-instance performance on previously learned
program structures. The earlier familiar-program 24/24 check remains a separate
practice result. Validation programs are also separated from training, and use
their own wording combinations. All declared attempted cases remain in scores.

## Matched candidate training

CAS and generic candidates use the unchanged v3 policy implementations, decoder,
loss, optimizer, seed, example order, and validation-only selection rule inherited
by the v6/v7 trainer. The proposed 200 epochs at batch size 16 mean 11,200 optimizer
steps per family. Actual completed epochs and steps must be recounted from output.
Selected checkpoints come only from validation scores; neither test answers nor
test execution outcomes select a checkpoint. The rule uses the same permitted
task information and the same accepted executor. It performs no neural training.

Both initial and selected candidate predictions are sealed before private test
targets are opened for native evaluation. The five arms are CAS initial/selected,
generic initial/selected, and rule. The accepted model, executor, permissions,
verifier, and baseline weights stay unchanged. No automatic promotion follows.

## Execution and reporting

The full campaign must first pass its own GPU smoke: the existing saved 352/24/9
fixture, exact 256-record import, one epoch and 22 steps per family, real exited
child processes, changed CUDA checkpoint tensors, and native evaluation of all
9 references and 45 arm attempts. This smoke is not a generalization result.

For the new 72 test cases, report complete-task correctness before/after by depth
and condition, with attempted denominators; input-binding and child-selection
accuracy; first recorded wrong decisions and failure categories; selected
checkpoint hashes; epochs, optimizer steps, native work, wall time, and cost.
An exact generated program is a diagnostic, not proof of a correct executed task.
A valid trace alone is not task correctness. Literal name differences may penalize
equivalent renaming, and the first recorded difference is not proof of the earliest
causal neural token.

The sole separately validated post-start exception is the accepted runtime's
`repair cannot open without a durable distinct ^6 round trip`. It counts as an
incorrect task, not an admission rejection. Its committed trace prefix is retained;
unrecorded failed-tick work and unverified component scores remain unknown. Other
unexpected errors fail the campaign. The rule must solve every reference case.

## Boundaries and spending

The earlier CAS 0/72, generic 12/72, rule 72/72 held-out result is unchanged.
The familiar-program fit and failed v6 training/replay remain separately labelled.
Replaying the v6 choices does not make that original failed campaign complete and
does not create a new fresh test.

Only a source-frozen clean-checkout package may launch. The launcher must reserve
the next bounded job from the canonical campaign ledger, check provider state, and
enforce the approved GPU type, resource limits, independent termination timer,
collection limits, and verified cleanup. Remaining authorization is not a spending
target. Estimates and reservations are not provider invoices. There is no automatic
retry, merge, release acceptance, CAS-advantage claim, or neural-core redesign.

The reserved amount is $7. Before launch, the declared time limits are GPU check
450 seconds, data assembly 180, training 3,300, native evaluation 2,700, campaign
6,900, compute 7,200, and instance lifetime 7,800. The launcher checks the live
price against its $2.52/hour ceiling; its conservative compute-plus-ancillary
budget calculation is $6.46 within the $7 reservation. That is not an invoice.
The earlier 72-case recovery used 2,221.574 seconds of native evaluation; the new
limit provides 478.426 seconds of headroom, not proof the fresh cases will fit.
The earlier nine-case GPU smoke used 203.235 seconds, but the new smoke includes
more training steps and extra data checks. If a declared time limit is exceeded,
preserve partial evidence and stop; do not extend the running job or retry it.
