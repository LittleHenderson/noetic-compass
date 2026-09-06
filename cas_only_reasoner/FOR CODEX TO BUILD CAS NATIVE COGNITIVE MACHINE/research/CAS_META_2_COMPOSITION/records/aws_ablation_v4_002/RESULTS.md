# Completed unchanged-checkpoint comparison

Job: `cas-meta2-20260906032109-361b34a0`.
Frozen source: `9f562c761c7cb84c767673b2fab735cdd031b499`.
Source archive SHA-256: `3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd`.
Result packet SHA-256: `c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708`.

The AWS job finished with return code zero and no omitted full files. The
downloaded 136,120,962-byte packet contains 4,773 files, with 1,444,124,667
expanded bytes. The v5 inspection passed all byte and receipt checks with no
issues. Its complete inventory and receipt are in
`../aws_ablation_v4_inspection_002/`.

## Recorded outcomes

Each mode has the same 72 already-exposed tasks and five selectors. These are
24 matched task triplets, not 72 independent graphs.

| Selector | Original decoder: correct tasks | Corrected decoder: correct tasks |
| --- | ---: | ---: |
| CAS untrained | 0/72 | 0/72 |
| CAS trained | 0/72 | 0/72 |
| Generic untrained | 0/72 | 0/72 |
| Generic trained | 12/72 | 12/72 |
| Rule | 72/72 | 72/72 |

CAS trained input-binding correctness rose from 19/72 to 36/72; valid traces
rose by the same amount. No CAS procedure, dependency path or final output
was correct in either mode. The correction did not recover a complete skill.
The generic model's input-binding correctness rose from 33/72 to 36/72.

The CUDA contract tests passed: four native-execution tests, 27 policy tests
and two decoder-parity tests. The GPU was NVIDIA RTX PRO 4500 Blackwell Server
Edition, using PyTorch 2.11.0+cu128 and CUDA 12.8.

These are unchanged checkpoints, no new training, and retrospective cases.
Neither fresh generalization nor CAS-specific advantage is demonstrated.
Byte/receipt inspection and stored-outcome audit are complete. The receipt in
`../aws_ablation_v4_stored_audit_002/` reports
`STORED_COMPARISON_AUDIT_PASSED`, with no errors. It checked 4,712 stored
traces in 421 databases, plus 72 reference executions and 360 arm choices
for each decoder mode. The recounted task scores match the table above.
This is frozen stored source replay, not independent neural re-execution.

The first local audit attempt lost its tool session during a host interruption
and left no final audit receipt. The process was confirmed absent and session
50080 returned `Unknown process id`. The same read-only audit was restarted
without relaunching AWS or changing the evidence. The replacement audit
completed at 2026-09-06T05:26:27.620258+00:00. Its receipt SHA-256 is
`3dc89119685d6c83ee33bc65019f8ea98ad58f6307613d77d1e95ba8e2502580`.

## Cleanup and budget

The launcher confirmed termination. A separate read-only provider check at
2026-09-06T04:47:22.778354+00:00 passed all seven checks: instance terminated,
job disks absent, security group absent, worker profile absent, both roles
absent and termination schedule absent. See `cleanup_receipt.json` and
`check_cleanup.py`. The S3 evidence has its separate seven-day expiry policy.

The launch reserved $7. Total campaign reservations remain $53 of the $400
cap, leaving $347 unreserved. The launcher's compute/disk/IP estimate is
$3.523110195740740740740740741; this excludes other charges and is not an AWS
invoice. No reservation refund or new paid run is implied.

## Learning decision

The decoder correction alone is not enough. The next learning experiment must
target complete nested programs, with adequate four-procedure/depth-three
development coverage and a separate deeper-call generalization measurement.
Retain the failed results. Do not train on the exposed test or relabel it as
fresh. Preserve the accepted executor, evaluator and baseline weights.
