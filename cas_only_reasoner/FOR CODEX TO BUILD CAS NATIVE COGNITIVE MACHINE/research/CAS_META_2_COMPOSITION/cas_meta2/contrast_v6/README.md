# Contrast curriculum candidate

This construction-first builder targets two observed composition mistakes:
binding a step to the wrong input and calling the wrong child procedure.
Each nested practice pair changes exactly one such choice. The pair shares
observations, binding, definition order, and wording template. Both programs
must remain valid and produce different symbolic native work.

Default configuration: 640 training tasks, 96 validation tasks, and 72 test
tasks (24 matched triplets, not 72 independent graphs). Nested practice covers
depths 2 and 3 with four reachable procedures; depth-1 tasks preserve basic
skills. Test triplets compare same-depth, changed wording, and deeper calls
at depths 3, 3, and 4. The independent parser must recover each target from
the public problem. Graphs and observation payloads cannot cross partitions.

`generate` and `write` require an explicit seed and graph-exclusion set.
The known-exposure inventory is recorded under
`records/contrast_v6_exclusions_001/`. Development fixture seed 926603 is exposed;
it must not be described as a fresh learning evaluation.

The code remains nested to avoid changing the old top-level source inventories
used to replay completed experiments. No accepted executor or checkpoint changes.

## Training-data adapter

`data.prepare_training_bundle` runs in the parent process. It checks an
externally supplied manifest digest, verifies all dataset bytes, repeats the
private structural checks, and writes a separate training-input directory.
That directory contains training labels, validation labels, public test inputs,
and the pinned manifest. It contains no private test file.

`data.load_training_bundle` is the trainer entry. It requires the manifest
digest, seed, counts, and exclusions from the caller; rejects unexpected files;
checks actual depth counts; fits text tokens on training problems only; and
does not read or hash private targets or parse test problems into programs.
The manifest's private-file hash is only a reference for later evaluation.
This directory separation is not an operating-system access-control sandbox.
The future launcher must keep private files outside the trainer's mounted inputs
if OS-level isolation is required.

## Remaining GPU integration

`train.py` now supplies the candidate CUDA loop. It uses the frozen lexical-copy
policies, semantic-weighted loss, and original v3 decoder for both families.
Defaults request 200 epochs, paired batches of 16, validation at epoch 0, epoch
1, every tenth epoch, and the final epoch. Selection uses only validation scores
and the frozen worst-depth-first rule. The default 3,600-second worker deadline
reserves 600 seconds for predictions; a deadline fault is incomplete, not an
accepted shortened experiment. No checkpoint is loaded from an accepted model.

Initial, each improved selected checkpoint, final, and recoverable interrupted
states are saved as candidate-only records. Four neural prediction sets are
sealed without running the rule parser or opening private test labels. The
parent must record successful child exit before constructing the rule control
and sending all arms through the unchanged native executor/verifier. The CLI
requires the pinned 8,053-graph exclusion inventory, explicit configuration
files, curriculum seed, job identity, and external dataset-manifest digest.

`checks.py` now recounts saved validation and training-probe actions, replays
selection, checks checkpoint bytes, and binds the four-arm prediction seal to
a successful parent-recorded process exit. It reads no private test labels.
It checks recorded evidence, not independently rerun logits or model gradients.

`evaluation.py` recomputes that gate, adds a rule arm from public problems,
seals all five arms, and then opens private targets. It validates the dataset
again and invokes the unchanged `campaign_v3._case_worker` in eight bounded
spawned workers. Results retain all rejections and report actual task outcomes
by depth and test condition. Failed workers retain partial files; no retries
or model promotion are automatic.

Neither the CUDA loop nor this new evaluation adapter has been executed on
GPU. The AWS-only end-to-end test is `tests/test_contrast_v6_train_gpu.py`;
it now covers a real training subprocess, parent gate, checkpoint reloads,
and nine diagnostic native cases. It must pass on authorized non-T4 CUDA
hardware before the registered experiment starts. This is not yet a complete
bounded launch package. Source/archive binding, GPU gates, budget reservation,
parent orchestration, collection, and cleanup must still be connected.

This is not yet a training launch package. Do not pass these files unchanged
to `train_v3.py`: that trainer requires the v3 manifest and equal per-depth
training counts. This candidate deliberately has unequal per-depth counts.
Likewise, `campaign_v3.report_evaluation_groups` expects v3 provenance names;
the candidate records test conditions in `contrast_side` instead.

The new adapter must validate the explicit counts and exclusions, bind all
source and dataset hashes, train fresh matched CAS/generic candidates, select
checkpoints using validation only, and seal test predictions before private
targets are read. Run all neural work on authorized AWS CUDA hardware, with
bounded runtime, spending reservation, complete result collection, and cleanup.
Keep the old executor and verifier unchanged. Evaluate actual native results
for untrained, trained, generic, and rule selectors; report depth and condition
breakdowns and flat-skill retention. Register the final experiment before
generating its new evaluation instances.

Structural tests do not establish task correctness or learning. The earlier
held-out composition result remains CAS 0/72, generic 12/72, rule 72/72. The
separate known-example fit result (both models 24/24) is not generalization.
