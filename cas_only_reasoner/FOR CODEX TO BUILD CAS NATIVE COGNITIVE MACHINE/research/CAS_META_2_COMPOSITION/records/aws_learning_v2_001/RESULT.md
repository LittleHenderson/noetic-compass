# Learning v2: completed AWS execution, full acceptance blocked

Source freeze: `410bce98307a5644db51928459b73391c7066b72`.
Job: `cas-meta2-20260905214620-cfdbb893`.
Instance: `i-016458110296bf671`, g7.2xlarge, RTX PRO 4500 Blackwell.
Accepted executor baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.

Source ZIP SHA256:
`11311cf8451a95014b162e7b3b65e6854cf5eb72a61532e4c04168f59520bc5f`.
Returned packet SHA256:
`0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93`.
Returned packet size: 59,648,802 bytes. Safely inspected/extracted members: 2,257.
The source ZIP and builder receipt are preserved in `../aws_learning_v2_001_source`.

## Recorded learning result

All 100 paired epochs completed, 4,800 optimizer steps per model. The selected
CAS checkpoint is epoch 40; the selected generic checkpoint is epoch 60. The
fixed generated-validation rule, not test performance, selected those versions.
Both initial, selected and last checkpoints remain in the unmodified packet.

Saved test counts: CAS untrained 0/72, CAS trained 0/72, generic untrained 0/72,
generic trained 0/72, rule 72/72. CAS trained generated three admitted programs;
generic trained generated seven. None matched the required program and output.
These counts were recounted by the byte inspector; full protocol acceptance
remains blocked. See the separately labelled stored-result diagnostic for its
own narrower checks, never as a substitute acceptance receipt.

The saved generated validation result improved from zero to 13/48 for CAS and
14/48 for the generic model. Those are program/binding matches, not independently
executed task outcomes. They do not establish successful held-out composition.
Post-run diagnosis uses now-exposed targets only to understand the finished run;
they must not be reused as an unseen evaluation set for a revised candidate.

Paired training wall time: 881.958939659 seconds. Recorded optimizer-step time:
CAS 632.9704647489981 seconds; generic 84.74857534299815 seconds. Campaign wall
time: 2637.666095011 seconds. These are different scopes, not additive charges.

## Full acceptance failure: preserved, not waived

`../aws_learning_v2_001_inspection/inspection_receipt.json` reports
`CAS_META_2_V2_PACKET_EVIDENCE_MISMATCH`, with exactly:
`gpu_preflight_v2:V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED`.

The GPU preflight reported allocated memory 0 before and 68,157,440 bytes after
cleanup, yet marked itself passed. The frozen checker correctly rejected it.
`../aws_learning_v2_001_stored_audit/stored_audit_receipt.json` then reports
`CAS_META_2_V2_STORED_PACKET_AUDIT_REJECTED` because a successful full inspection
is required. That gate checked zero traces; it must not be described as passed.

The likely allocation source is retained BLAS workspaces, but actual ownership
was not captured in this run. PyTorch documents their separate cleanup API:
https://docs.pytorch.org/docs/2.11/notes/cuda.html#cublas-workspaces . This hypothesis
does not repair the original record and has no demonstrated causal connection
to the failed learning result. Future preflight corrections stay separate.

## Provider closure and budget

`../aws_learning_v2_001_cleanup_verification/closure_observation_02.json` records
all 20 independent read-only cleanup checks passed at 22:41:13 UTC. The instance
is terminated; its exact volume, security group, instance profile, two roles and
termination schedule are absent. Three encrypted/private result objects retain
seven-day expiry. Earlier pending observations are preserved.

This run reserved $7. The one campaign ledger now reserves $25 total and leaves
$375 unreserved under the $400 total authorization, inclusive of earlier work.
No refunds were assumed. The launcher's compute/EBS/IPv4 estimate is
$2.262287096592592592592592592, excluding S3, transfer and taxes; it is not an
AWS invoice or an account-wide provider spending cap.

## Commands

Executed from the CAS_META_2_COMPOSITION directory, using C:/Python314/python.exe.
The audit commands were invoked through `runpy.run_path` with
`tools.validate_local.NoNeuralImports` installed first. No local neural work ran.

```text
python -B aws/launch.py --execute --archive runs/cas-meta2-410bce98-learning-v2.zip --sha256 11311cf8451a95014b162e7b3b65e6854cf5eb72a61532e4c04168f59520bc5f --source-sha 410bce98307a5644db51928459b73391c7066b72 --approved-cap-usd 400.00 --profile default --subnet-id subnet-0eb3ca4bf5ca98f24 --receipt-dir records/aws_learning_v2_001
python -B tools/inspect_cloud_packet_v2.py --packet records/aws_learning_v2_001/cloud_artifacts.zip --sha256 0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93 --source-sha 410bce98307a5644db51928459b73391c7066b72 --job cas-meta2-20260905214620-cfdbb893 --source-manifest records/aws_learning_v2_001_source/cas-meta2-410bce98-learning-v2.receipt.json --output records/aws_learning_v2_001_inspection --extract records/aws_learning_v2_001_extracted
python -B tools/audit_stored_packet_v2.py --inspection-receipt records/aws_learning_v2_001_inspection/inspection_receipt.json --output records/aws_learning_v2_001_stored_audit
```

The launcher exited successfully; the two full acceptance tools rejected as
described above. Their machine-readable receipts and the packet's exact cloud
commands/raw logs, environment identity and outputs are the primary records.
This document records outcomes, not an accepted release or a claim that the
complete CASformer vision, general reasoning or CAS-specific advantage exists.
