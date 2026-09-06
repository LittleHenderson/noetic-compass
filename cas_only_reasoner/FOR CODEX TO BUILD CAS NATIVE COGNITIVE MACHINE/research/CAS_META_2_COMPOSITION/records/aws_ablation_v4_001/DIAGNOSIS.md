# Decoder comparison stopped before prediction

Job: `cas-meta2-20260906025939-e933c868`.
Frozen source: `3da01c577c47978e595caaff1ebbe9b30c3a87b6`.
Packet SHA-256: `53b5be708b4e12206f8f35357977fd020a34d8426db616eb09a068682c743642`.

The parent stopped at `gpu_contracts` with subprocess exit 5.
The exact child stdout says `2 deselected in 0.91s`; stderr is empty.
The project's pytest configuration defaults to `-m 'not gpu'`, and the
parent command omitted the explicit `-m gpu` override. Thus neither of the
two decoder contract tests executed. This is a test-selection error, not a
failed decoder assertion or evidence that the model improved.

The separate launcher gates completed: 4 native GPU tests and 27 policy GPU
tests passed. Dataset reconstruction matched all five original file hashes.
Prediction and native comparison did not run. No training was performed.

The new byte-only inspector returned
`RETROSPECTIVE_FAILED_OR_PARTIAL_RUN`, with 90 member files, no inspection
issues, all included bytes checked, and the original full index verified.
The packet reports no omitted files. This is a complete packet for a failed
run, not a completed experiment or an independent stored semantic audit.
See `../aws_ablation_v4_inspection_001/inspection_receipt.json`.

The terminal launcher receipt confirms instance termination, no remaining
job volumes, and an empty cleanup-error list. Its compute/disk/IP estimate
is $0.419087522, excluding S3, transfer and taxes; this is not an AWS invoice.
The $7 reservation remains in the campaign ledger and is not refunded by
this estimate. The source archive and failed evidence remain unchanged.

The working candidate now supplies the explicit GPU marker and its simulated
parent test checks that argument. Full guarded local validation passed under
`../local_ablation_gpu_selection_fix_v4_001`: 1,214 test functions and 178
subtests passed, with 8 GPU modules skipped locally and no failures.
All captured source and 316 protected files stayed unchanged during validation.
The corrected source is `9f562c761c7cb84c767673b2fab735cdd031b499`.
This is a separately reviewed correction, not an automatic retry.

The independent `cleanup_receipt.json` at 2026-09-06 03:16:05 UTC confirms
all seven provider cleanup checks passed.

Next: qualify a new source-bound comparison before another bounded AWS launch. Neither this
launch-script correction nor its software tests count as a learned skill.
