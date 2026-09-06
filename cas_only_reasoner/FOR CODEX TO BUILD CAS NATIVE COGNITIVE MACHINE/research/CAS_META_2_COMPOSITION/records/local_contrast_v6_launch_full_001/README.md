# Full source regression before contrast AWS packaging

Command from CAS_META_2_COMPOSITION:
`C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_contrast_v6_launch_full_001`

Result: **1,529 test functions and 178 subtests passed; 10 GPU tests skipped.**
JUnit contains 1,717 entries including subtests and skips, with 0 failures and
errors. Parent wall time: 203.6345865000003 seconds. All 151 recorded source
files and 316 protected files matched their before/after snapshots.

Raw outputs, XML, exact commands, environment overrides, and source hashes are
retained here. Neural/provider imports were blocked. No GPU or AWS resource
launch occurred during this regression. The registered seed 2026092601 was not
generated. This is prelaunch software evidence, not a learning result.

Separate read-only provider receipts at `records/provider/pre_contrast_v6_001`
show no active CAS jobs, no other active GPU, a G quota of 8 vCPUs, a P quota
of 0, and a g7.2xlarge Linux shared on-demand rate of $2.52/hour. The existing
H100 request remains CASE_OPENED in `h100_status_contrast_v6_001`. These facts
do not prove available launch capacity. No duplicate quota request was sent.
