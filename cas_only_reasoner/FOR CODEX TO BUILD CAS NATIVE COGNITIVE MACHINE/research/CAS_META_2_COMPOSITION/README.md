# CAS-META-2: learned program composition

This is a separate experimental candidate, not a replacement for the accepted CAS-META-0 runtime or the completed CAS-META-1 pilot.

The next measured skill is to turn a bounded problem into a new nested CJT program with named intermediate values, then execute it through unchanged native CJT APIs. The candidate must emit operations, calls, and bindings, not just select a prepared whole program.

Latest state (2026-09-05): the second learning run from source
`410bce98307a5644db51928459b73391c7066b72` finished on AWS. Its saved report
shows CAS 0/72 and generic 0/72 correct tasks after training, versus rule 72/72.
Full protocol acceptance is **blocked**: the GPU preflight marked success despite
68,157,440 bytes remaining allocated after cleanup from an initial zero. The
unchanged inspector rejected that claim, and the full stored auditor refused
to proceed. Original failed receipts and six checkpoints are preserved under
`records/aws_learning_v2_001*`. A separately labelled stored-result diagnostic
does not override that failure. AWS shutdown and resource cleanup have been
independently verified. The ledger reserves $25 total, leaving $375 unreserved;
these are reservations, not invoices. See `records/aws_learning_v2_001/RESULT.md`.

First full run: source `b5f1718e63a2b5cf72b4b606d513d0524b9226ac` completed on an RTX PRO 4500 Blackwell. Both four-test GPU gates, three native execution preflights, 200 matched training epochs, and all 72 cases / 360 comparison choices completed. The file inspection and separate stored-record audit passed. The latter checked all 1,915 traces against the published schema across 222 databases and replayed the stored composition evidence. It did not load checkpoints or independently rerun neural inference.

The checked learning outcome is **negative**: CAS trained 0/72, CAS untrained 0/72, generic trained 0/72, generic untrained 0/72, rule 72/72. The trained policies produced more admitted programs (CAS 28, generic 35) than their untrained versions (zero), but none solved a held-out task. No successful learned composition, CAS advantage, or general reasoning is established by this run. Six checkpoints and all raw outcomes are retained.

The run keeps Drive and summed absolute current unchanged and sets initial gate saturation to twice the configured maximum input length. All gate parameters remain trainable. The GPU checks cover default training geometry, finite nonzero gradients, operating-region measurements and a resistance intervention. Earlier pure checks recorded 367 passed tests and 52 passed subtests with all 316 protected files unchanged (`records/local_candidate_004/receipt.json`). Those pure checks are not a neural result.

The first preflight's gradient failure is preserved under `records/aws_smoke_001`, bound to source `2a3ec1132770b121881a49effee2aa5d4e0494fb`. The full run's initial audit failure was a cross-platform file-order mismatch; `records/AWS_FULL_002_INDEX_ORDER_CORRECTION.md` explains its narrowly tested correction. Original experiment bytes were not changed.

First full-run records:

- `records/aws_full_002/launch_receipt.json` and `cloud_artifacts.zip`: source/job identity, raw evidence and six saved checkpoints.
- `records/aws_full_002_inspection/inspection_receipt.json`: all 2,476 packet members checked; no issues.
- `records/aws_full_002_stored_audit/stored_audit_receipt.json`: full stored audit passed; 72 private reference runs and all 360 sealed choices checked, in addition to the three execution preflights.
- `records/aws_full_002_learning_summary/learning_summary.json`: verified paired and depth comparisons, training exposure, selected checkpoints, detailed rejections and compute.
- `records/aws_full_002_diagnosis_v2/diagnosis_receipt.json` and `REPORT.md`: reproducible data diagnosis. Test unknown-token share is 43.84%; child-call control structure and some target names were never positive training examples. The first diagnostic receipt's serialization defect is preserved separately, not presented as valid.
- `records/aws_full_002_cleanup_verification/closure_verification_receipt_v2.json`: independent read-only cleanup checks. Paid job resources are gone; three encrypted result objects retain seven-day expiry.
- At that run's closure, the recorded compute/EBS/IPv4 estimate was about **$1.85**, excluding S3, transfer and taxes. It is not an invoice. The ledger then reserved $18 total and left $382 unreserved; no reservation was refunded.

The next learning experiment must preserve structural names, teach the control
forms it asks the model to combine, and evaluate wording, unfamiliar graphs and
deeper nesting separately. Fixing unknown tokens alone is not proven sufficient:
both learned arms also failed all 36 shallower depth-2 test cases. The rule parser
knows all three wording families; its score is an executable reference ceiling,
not a comparison with equal prior language knowledge.

## Preserved evidence

The side-by-side second learning protocol is described in `LEARNING_V2.md` and
registered in `EXPERIMENT_V2.json`. It adds lossless text features, nested-call
training and freely generated validation selection. It has now run on AWS, with
the negative result and unresolved full-protocol gate described above.
Final pure prelaunch checks passed 615 tests plus 89 subtests, with two GPU modules
skipped and all 316 protected files unchanged (`records/local_learning_v2_002`).
The original learning/runtime entrypoints and negative learning result remain
unchanged. The launcher now has an explicit, manifest-bound profile selector.

- Accepted executor baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.
- Completed learning pilot evidence: `6a4524d5f21f77194b35d0830d2b16da8530b17d`.
- The separate third-party receipt `../CAS_META_1_LEARNED_SELECTION/records/third_party_semantic_audit_glm2/audit_receipt.json` reports 72 references, 360 reverified executions, and matching verdicts: CAS trained 66/72, CAS untrained 8/72, generic trained 61/72, generic untrained 8/72, rule 72/72. It is a stored-evidence audit, not a new neural run. Its source file remains untouched.

## Boundaries

- All model construction, training, tensor computation, and neural evaluation must run on AWS CUDA. Laptop checks are pure parsing, hashes, control logic, and stored-evidence checks.
- No further T4 use. The amended AWS allowance is $400 total across the earlier pilot, this campaign and later research. The shared `records/budget/campaign_ledger.json` preserves all earlier reservations and records the current unreserved allowance. A reservation is a conservative allowance, not an AWS invoice.
- Baseline source, native parameters, contracts, verifiers, and earlier raw evidence remain unchanged. No automatic merge.
- This candidate initially supports unary procedure inputs and a bounded acyclic call graph. Named intermediate values are real reference selections. This is not yet arbitrary multi-input composition, unbounded recursion, missing-skill acquisition, or complete Noetic semantics.
- The first curriculum uses controlled wording that describes the required operations and dependencies. The model translates that wording into executable program structure; it is not yet discovering an algorithm from an outcome-only request. Held-out program JSON and answers are withheld during prediction, but the public instructions deliberately contain procedural information.
- Functional addresses identify a place in a program. Separate run and call identities identify an execution. Oscillatory phase is never the sole chain identity.
- A valid trace is necessary but not sufficient: correctness also requires the expected dependency graph, bindings, and actual native output bytes.

See `VISION_REQUIREMENTS.md` for the full endpoint and open requirements. A small successful experiment must not be relabeled as completion of that endpoint.
