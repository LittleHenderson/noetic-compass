# Exact Windows-write failure was not reproduced

The source and tests stayed unchanged at
`4bbb91628ad5b5f7e32d33eb8f7f07fedaa05a3e` in the same clean worktree.

The original full-suite failure is preserved in `../run_002/`. It occurred at
the existing atomic receipt replacement in `cas_meta2/campaign_v3.py:74`:
`PermissionError: [WinError 5] Access is denied`.

Two separate fresh pure processes were then run, in order:

1. The exact test case: **1 passed** in 0.74 seconds.
2. Its entire old ablation test file: **13 passed** in 1.70 seconds.

The exact case is included in both runs; do not add these as 14 distinct tests.
The unchanged canonical import guard was installed in each process. Provider
permissions, child execution and predictions in this old test are simulated;
the test uses saved diagnostic fixture bytes, not new tasks or models.

Classification: **not reproduced in two scoped retries**. The observed failure
was intermittent across these executions, but its cause is not established.
A suite-context effect has not been ruled out, and no process holding a file
handle was identified. A path under OneDrive is not proof that OneDrive caused
the error.

Read-only inspection found both original receipt files still present and
readable, with Windows file attributes `32` and no read-only attribute. Their
bytes and metadata were preserved. No receipt replacement, permission change,
file deletion, or source/test fix was attempted.

Before-and-after checks covered 619 distinct Git/raw file identities, including
the 602 closed inputs and all 316 protected files. Every identity stayed the
same. `outputs/` retains exact commands, raw stdout/stderr, JUnit files, scratch
paths, child receipts, file metadata, source snapshots and the final receipt.

Final diagnostic receipt SHA256:

```text
71651da98b0ea433328f2dbfc82f80de79c703b2e049557d33bee4d51e937eb1
```

This is a narrow reproduction check in an existing Python environment. It does
not claim a successful full-suite rerun, fix the original access failure, or
establish production readiness. No GPU, AWS, checkpoint, or new registered data
was used. The diagnostic wrapper is a separately recorded audit tool; the code
under test and the source-identity helpers came from the exact frozen commit.
