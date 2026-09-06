# Clean preparation-source check: one preserved failure

Source: `4bbb91628ad5b5f7e32d33eb8f7f07fedaa05a3e`.
The full canonical test run did not pass: **1 failed, 1884 passed, 11 skipped,
2 deselected, 1 warning, 356 subtests passed** in 251.98 seconds. JUnit records
2252 entries, including subtests and skips. These counts overlap and are not
added together.

All 619 distinct source/input files matched their Git blobs and raw checkout
bytes before and after. This includes the 602 closed package inputs and all
316 protected files. No tracked source changed. The new cold-child,
orchestration, and smoke-private test modules passed in this run.

The sole failure was:

```text
tests/test_ablation_campaign_v4.py::test_simulated_parent_order_and_failures[False-True]
```

The test deliberately raises a simulated unsafe-output exception. While saving
its failure receipt, unchanged `cas_meta2/campaign_v3.py:74` then raised
`PermissionError: [WinError 5] Access is denied` from `os.replace` on
`campaign_receipt.json.tmp` and `campaign_receipt.json` in retained test scratch.
The full traceback is in `full_validator_artifacts/stdout.txt`. This record does
not assign the access failure to OneDrive, another process, or a code defect.

Receipt SHA256:

```text
b1fa29cc8e5e7341996d18e6ea827bd969acace8d365206fcb9ec2fb8241724d
```

The same unchanged source was later checked in the separate
`../diagnosis_001/` record: the exact case passed once, and the complete old
ablation test file passed all 13 cases. Those limited retries do not turn this
full-suite failure into a full-suite pass or establish its cause.

This was a clean preparation-source check in the existing Python 3.14
environment, not a fresh installation, new learning result, GPU check, or paid
launch. The frozen preparation settings still prohibit training. Active
uncommitted logging changes were excluded. Both the prior audit-runner failure
and this run remain preserved with their separate worktrees and raw evidence.
