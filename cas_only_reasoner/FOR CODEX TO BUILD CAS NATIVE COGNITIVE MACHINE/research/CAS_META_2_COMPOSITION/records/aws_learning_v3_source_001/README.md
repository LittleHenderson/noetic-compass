# Learning-v3 pinned source and prelaunch checks

Source commit: `ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70`.
Accepted baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.
No merge was performed.

The source ZIP contains 461 packaged files plus `launch_manifest.json`.
Its size is 4,278,741 bytes; SHA-256 is
`f45df65ff54e3396bc0c66baeb704deb43c3f2a572b6459b9dad253f4183dcd2`.
The source receipt is `source.receipt.json`. All 316 protected baseline
files matched. Historical META1/META2 runs and records are excluded inputs.

```text
C:/Python314/python.exe -B tools/build_launch_bundle_v3.py --output records/aws_learning_v3_source_001/source.zip --experiment-profile learning_v3
C:/Python314/python.exe -B records/aws_learning_v3_source_001/check_cold_sources.py
```

The three fresh-process source checks passed with no neural or provider imports:
launcher archive/local/Git identity, inspector source/config imports, and
stored auditor source plus the published baseline schema. Their exact child
commands and raw stdout/stderr are in `cold_source_checks_001`. The receipt
SHA-256 is `5adfbfc21aa5b6baf26d955457a50998867d7cb3f40f4ec268ac2f99d2e21875`.
These are real source checks, not real GPU tests or a completed result audit.

The source commit includes the complete combined pure validation record:
1,137 tests and 178 subtests passed, seven GPU modules skipped, zero failures
or errors. All 97 source/config/asset files and 316 protected files were
unchanged. See `../local_learning_v3_004/receipt.json`.

## Bounded launch command dispatched after those checks

```text
C:/Python314/python.exe -B aws/launch_v3.py --execute --archive records/aws_learning_v3_source_001/source.zip --sha256 f45df65ff54e3396bc0c66baeb704deb43c3f2a572b6459b9dad253f4183dcd2 --source-sha ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70 --approved-cap-usd 400.00 --profile default --subnet-id subnet-0eb3ca4bf5ca98f24 --receipt-dir records/aws_learning_v3_001
```

Dispatch is not proof of launch, GPU-test success or training. Read the new
launch receipt and provider state for those facts. Do not rerun this command
while the existing launcher is active. There is no automatic retry.

The read-only provider snapshot at `../provider/pre_v3_001` found no active CAS
jobs, eight available-account G-instance quota units, zero P-instance quota,
and the registered g7.2xlarge price of $2.52/hour. A listed offering is not proof
of capacity. The launcher rechecks access, identity, quota and price before
reserving $7 of the $400 task cap and creating job resources.

The 7,200-second resource cutoff, complete stored-result audits, direct AWS
cleanup checks and separate final evidence commit remain required. Keep this
source unchanged until its cloud and stored-evidence checks have finished.
