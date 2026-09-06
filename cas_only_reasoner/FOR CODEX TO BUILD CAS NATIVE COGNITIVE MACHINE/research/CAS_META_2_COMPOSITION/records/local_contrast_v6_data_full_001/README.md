# Full pure regression for training-input separation

Command from CAS_META_2_COMPOSITION:
`C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_contrast_v6_data_full_001`

Result: **1,402 test functions and 178 subtests passed; 9 GPU tests skipped.**
JUnit records 1,589 entries including subtests and skips, with 0 failures and
0 errors. Parent wall time: 224.33536949999962 seconds. All 137 recorded source
files and 316 protected files matched their before/after snapshots.

The full validator blocks neural/provider imports, uses retained homebase
scratch, and saves raw stdout/stderr, XML, commands, environment overrides,
and source identities. No GPU or provider call occurred.

This establishes pure adapter behavior and compatibility with the covered
software tests. It does not establish CUDA training, native task correctness,
OS-level access isolation, fresh generalization, or model promotion. The next
implementation is the candidate CUDA trainer and bounded launch integration.
