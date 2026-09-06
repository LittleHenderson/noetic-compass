# V3 campaign contract

This is source integration and pure local checking, not an AWS or learning result.

Entrypoint: `python -m cas_meta2.campaign_v3 --output <new META2-contained directory> --max-wall-seconds <60..6600> [--smoke-only]`.
The launcher supplies the exact four-field experiment identity plus the AWS job
and `CAS_META2_RUN_GPU_TESTS=1`. Authorization is checked before neural imports.
The profile is `learning_v3`; the source specification is `EXPERIMENT_V3.json`.

## Required execution sequence

1. A separate child constructs seed 20260919 with all 4,488 exclusions and proves
   cold JSON consistency. Only its process can own all construction labels.
2. The campaign checks the public manifest and all four file byte hashes. It
   opens training rows but does not parse private test labels.
3. Three actual-copy CUDA modes use the exact SHA-bound training file. The
   separate two-case trainer CUDA module uses authored fixtures only.
4. Main-process actual-copy preflight and three unchanged native smoke fixtures.
5. Paired training with format-3 initial/selected/last checkpoints; all five
   prediction sets are sealed together; actual outer CUDA cleanup must pass.
6. Only then record the private-opening receipt, recheck cold full-data meaning,
   run the unchanged native references/executor/verifier, and report all 360
   arm verdicts. Wrong valid programs are not replaced or shortened.

The launcher runs its separate early 27 policy/loss cases and 4 native-contract
cases. The campaign does not pretend those are its own five cases.

## Stable evidence files

- `campaign_receipt.json`: schema `cas-meta2-campaign-receipt/3`; full status
  `CAS_META_2_V3_AWS_CAMPAIGN_COMPLETED`; smoke status
  `CAS_META_2_V3_AWS_SMOKE_COMPLETED`; failures use
  `CAS_META_2_V3_AWS_CAMPAIGN_BLOCKED` and `completed=false`.
- `experiment`: exactly `profile`, `entrypoint`, `spec_path`, `spec_sha256`.
  `aws_job_id` is a separate campaign field. Source identity includes the
  candidate module files, source test list, both JSON exclusion assets, spec,
  packaging and GPU requirement bytes. Provider/source-freeze authority remains
  in the separate launch manifest; local file hashes are not Git verification.
- `dataset_construction_receipt.json`: schema
  `cas-meta2-dataset-construction/3`; command/exit and process-receipt hash,
  manifest hash, separate-process assertion, seed and 4,488 exclusion count.
  Raw logs and `process_receipt.json` stay under `dataset_construction/`.
- `gpu_gates_v3.json`: schema `cas-meta2-campaign-gpu-gates/3`; `groups` contains
  `actual_copy` (3 cases) and `trainer` (2 cases). Each binds its command/process
  receipt and exact JUnit byte hash/counts. No skips or failures can pass.
  `gpu_tests/<group>/` retains `stdout.txt`, `stderr.txt`, `process_receipt.json`,
  `junit.xml`, and all `basetemp/` files. Actual-copy basetemp has cold1/warm1/
  repeated2 preflight receipts. Trainer basetemp has `authored_checkpoint_receipt.json`
  (`cas-meta2-authored-checkpoint-test/3`) and `authored_cleanup_receipt.json`
  (`cas-meta2-authored-cleanup-test/3`). The cleanup fixture explicitly declares
  its mocked inner workload; actual CUDA allocation/backward and outer cleanup
  remain real. These fixture checkpoints are not campaign candidates.
  Both commands explicitly include `-m gpu` to override the project's
  default `-m 'not gpu'`. Final command order is Python, `-B -m pytest -m gpu
  -q -p no:cacheprovider`, JUnit path, basetemp path, then the exact test file.
- `gpu_preflight_copy_v3.json`, `training_cleanup_v3.json`, `smoke_receipt.json`,
  and unchanged per-case native evidence remain fully retained.
- `predictions.jsonl` and `predictions_seal.json` bind every public case and all
  five arms before `test_gold_opening_receipt.json` can be written.
- `dataset_validation_v3.json` binds the post-seal cold full-data validation.
  It is not a native-answer result.
- Full candidate files: `candidate_{cas,generic}_{initial,best,last}.pt` plus
  `checkpoints.json`, training history, selection records and raw generated
  validation/training-probe outputs. `selected` metadata uses the `_best.pt`
  filenames. Checkpoint format is `cas-meta2-candidate-checkpoint/3`.
- `evaluation_results.json` and `evaluation_groups.json` preserve full 72-case
  denominators per arm and 24 cases per matched group. Groups are not 72
  independent graphs. `payload_sha256.json` includes every output file except
  itself; the outer packet independently binds that index and all bytes.

## Fixed bounds and failure behavior

Phase limits total 6,600 seconds: construction120, actual-copy tests240,
trainer tests180, main copy preflight120, native smoke180, training2700,
prediction480, native evaluation2400, final evidence180. Before learning,
5,760 seconds must remain for those four final allocations. The registered
training configuration is not silently shortened. Completed paired epochs can
stop under the trainer's fixed allocation; unfinished work cannot become a
completed campaign. The launcher's independent 7,200-second resource cutoff
and shared budget remain required.

Subprocess groups are terminated on timeout and raw files are retained. Native
workers retain completed/partial cases and are terminated without retry on
failure. Artifact size remains 2 GiB expanded and 1 GiB compressed externally.
No claim of improvement, CAS advantage, general reasoning, full Noetics,
qualified memory, CNCM completion or hardware follows from passing these checks.

The final focused source check is 53 pure tests. See
`gpu_selection_correction_receipt.json` for the corrected campaign/source hashes.
The original 52-test receipt remains preserved; it did not establish GPU execution.
