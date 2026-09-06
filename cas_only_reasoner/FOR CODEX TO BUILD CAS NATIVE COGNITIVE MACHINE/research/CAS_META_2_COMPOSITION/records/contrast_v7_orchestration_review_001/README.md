# Independent v7 orchestration review

The final synthetic suite passed **22 test functions and 8 subtests** in
3.18 seconds, with no failures, errors, or skips. Nine watched source files
and all 316 protected files stayed unchanged during the run.

This review found one concrete receipt-binding defect, reproduced it, and
checked the owner's fix. No production file was edited by this reviewer.

## Finding and correction

The original GPU gate accepted conflicting native receipts. The embedded
receipt still declared nine cases and 45 arm verdicts, while a controlled
stored receipt declared eight cases. Updating the stored-file hash in the
synthetic smoke receipt did not cause rejection.

The valid control passed; the assertion that this mismatch must be rejected
failed. That original two-test output and source identity are preserved in
`finding_001/`. Original campaign SHA256:
`30255344eb177e06b6104957233a6d0645b6cd051e71987badada48ae6e5020a`.

The owner corrected `check_gpu_phase` to require both the stored-file hash and
equality between its decoded contents and the embedded native receipt.
The unchanged negative test now passes. Final tested campaign SHA256:
`aeec4c1015862b00b31187ba7678e1a8608ea1082df01544709a8202f2af726f`.

## Covered behavior

- The GPU gate requires the exact current command and one named passing XML
  test, one current-job smoke receipt, matching source/baseline identities,
  and complete nine-case/45-arm native-smoke counts.
- Changed job/source/baseline, test identity, skip status, command, native
  coverage, or duplicated smoke receipts are rejected.
- The campaign issues GPU, dataset, training, and evaluation commands in that
  order. Its training command is admitted only after the saved assembly receipt
  declares the required actual 896/96/72 counts.
- Dataset receipt PID binding, separate dataset/training PIDs, and dataset exit
  before training start are checked using the unchanged process-exit checker.
- A failure in any phase stops later phases. Failure records are written and
  collection is requested. A collection failure marks an otherwise successful
  record incomplete.
- Training checks run before evaluation and are repeated before final
  completion. Changed training/GPU gates, baseline, or source identity block
  completion. The checks still route through the existing validation-only
  training checker; no selection method or scoring code was replaced on disk.
- A failed training attempt reports `training_attempted=true` and
  `training_performed=null`. A completed checked training phase reports true;
  an assembly failure before training reports false for both.

The time tests use the owner's planned bounds: 6300 seconds total, a 30-second
parent reserve, 3300 seconds for training, 2400 for native evaluation, 300 for
the GPU gate, and 180 for dataset work. Exactly 480 seconds of setup leaves the
required training/native allocation. At 481 seconds, the campaign stops before
training. The tests also check the separate 15-second process allowances.
This proves scheduling checks, not that real GPU work will finish within them.

## Evidence

- Final test file:
  `tests/test_contrast_v7_orchestration.py`,
  SHA256 `e5e792d921559aa285d512fbd5bb604308caa27612b4844ad73279fada733bc5`.
- Final receipt:
  `checks_001/receipt.json`,
  SHA256 `1de60f5073a07d012228e1b1051195a9ddbaf3762076551a3c3b18ec89fa31ab`.
- Original finding receipt:
  `finding_001/receipt.json`,
  SHA256 `3638b89854b6bae829f58e0efd6670002ccab0e776e9e4741f068232021caf32`.

`checks_001/` retains exact commands, environment identity, raw stdout/stderr,
JUnit, and before/after hashes. Its JUnit has 22 test-function entries; the
eight subtests are separately reported in raw output and are not added to those
entries. Synthetic fixture files remain under `scratch/`.

## Boundaries

The tests use synthetic GPU/process/training/native receipts and mocked phase
launch functions. The existing process-exit checker reads those synthetic
records; this is not proof of real process execution or real GPU success.
The earlier cold-child review separately covers real exited local processes.

No fresh curriculum was generated, no neural model or checkpoint was loaded,
and no provider call, paid launch, or live-job change occurred. Readiness
overrides existed only inside test mocks and were restored; preparation flags
on disk stayed unchanged. The Python environment was existing, not freshly
installed. Actual fresh-data counts, training results, GPU completion, and
full campaign reproduction remain outside this focused proof.
