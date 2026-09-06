# Live retrospective comparison job

Job: `cas-meta2-20260906025939-e933c868`.
Instance: `i-0b3aca5fdecdec7ac` (`g7.2xlarge`, Blackwell; not T4).
Source: `3da01c577c47978e595caaff1ebbe9b30c3a87b6`.
Source archive SHA-256:
`e680545e231d7f9f7fca0dd4f84e3fe4988b3d7c129c83a0bfe313ea809fdbc2`.

Launch command (from this research directory):

```text
C:/Python314/python.exe -B aws/launch_ablation_v4.py --execute --archive records/aws_ablation_v4_source_001/source.zip --sha256 e680545e231d7f9f7fca0dd4f84e3fe4988b3d7c129c83a0bfe313ea809fdbc2 --source-sha 3da01c577c47978e595caaff1ebbe9b30c3a87b6 --approved-cap-usd 400.00 --profile default --subnet-id subnet-0eb3ca4bf5ca98f24 --receipt-dir records/aws_ablation_v4_001
```

The launcher reported the created instance and confirmed the independent AWS
schedule. The separate read-only observer confirmed `running`, schedule `ENABLED`,
and termination expression `at(2026-09-06T04:59:57)` in UTC. A later S3 progress
record shows `gpu_contract_tests.log` running at 03:03:03 UTC. This is startup
progress, not passed tests, completed prediction or a learning result.

The ledger advanced to revision 6: $46 reserved / $354 unreserved within the $400
total cap. This includes the new $7 reservation and is not an AWS invoice.

Observe the existing job using `read_status.py` or the still-running launcher
session. Do not rerun the launch command because a polling call times out. Keep
the mutable launch receipt in `records/aws_ablation_v4_001/` until the job reaches
a terminal state; then preserve the complete packet and verify cleanup.

The observer performs only identity, instance, schedule and bounded S3 status
reads. It creates separate timestamped local records and never starts, restarts,
stops or changes cloud resources. No local neural work is performed.
