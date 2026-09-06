# Full pure regression of the contrast curriculum candidate

Command, from CAS_META_2_COMPOSITION:

`C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_contrast_v6_full_001`

Result: **1,373 test functions and 178 subtests passed; 9 GPU tests skipped.**
JUnit contains 1,560 entries, including subtests and skips; 0 failures and
0 errors. Parent wall time: 145.2129605 seconds.

The validator recorded 135 source files and 316 protected files. Before/after
source and protected snapshots matched. Neural and provider imports were blocked.
Raw output, XML, commands, environment overrides, and hashes are in this folder.

The focused curriculum run previously passed 48 tests, recorded in
`records/local_contrast_v6_001/tests_v2.xml`. This wider run checks compatibility
with the existing pure suite, not CUDA behavior or native task correctness.
No AWS job was launched. No new learned capability or accepted model revision
is claimed. GPU training/evaluation integration remains incomplete.
