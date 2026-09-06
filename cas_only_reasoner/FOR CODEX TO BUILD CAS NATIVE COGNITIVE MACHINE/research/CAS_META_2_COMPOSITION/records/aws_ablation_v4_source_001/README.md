# Pinned retrospective comparison launch package

Source commit: `3da01c577c47978e595caaff1ebbe9b30c3a87b6`.

Archive SHA-256:
`e680545e231d7f9f7fca0dd4f84e3fe4988b3d7c129c83a0bfe313ea809fdbc2`.

The archive contains 492 packaged files plus `launch_manifest.json` and is
11,608,135 bytes. All 316 protected baseline files are preserved. The cold check
validated archive contents, fixed retrospective inputs, experiment identity,
actual committed Git bytes, local executable bytes, shared budget implementation
and the unchanged resource-plan limits. It made no provider call, model import,
neural operation or spending reservation.

The source passed 1,211 pure test functions and 178 subtests; eight GPU modules
were skipped. Those results are in `records/local_launch_ablation_v4_001/`.

The current cold-check ledger read showed $361 unreserved within the $400 total
cap. That is budget accounting, not an AWS bill. This package has not been
cloud-executed, and its saved-model comparison has not produced a result.

Before launching, recheck current provider state through the launcher's guarded
path and preserve the independent deadline permit. H100 approval/capacity is
not established; the existing registered plan uses Blackwell, not T4.
