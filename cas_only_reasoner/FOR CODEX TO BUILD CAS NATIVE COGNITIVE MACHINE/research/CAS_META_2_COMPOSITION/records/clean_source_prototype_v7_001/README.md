# Clean source v7 audit at 80e44f20

The focused preparation checks passed, but the full suite failed because a new
test left an import blocker active for later tests. This record preserves the
failure unchanged. It is not a clean full-suite pass.

## Source and environment

- Source: `80e44f20a3f2c66a62754212729ce6e11ff9c8fe`.
- New detached checkout: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/contrast-v7-audit-80e44f20`.
- Checkout used `core.autocrlf=false`; initial Git status was empty.
- All **556** checked Git blobs and checkout files matched before and after.
  This includes **158 source files**, **316 protected baseline files**, and
  **75 explicitly selected preparation input files** (these sets overlap).
- Original **256** practice tasks, saved seed **926603** input bundle, and
  source-pin file were present in Git and matched their raw bytes.
- Existing Python **3.14.0**, pytest **9.0.2**, jsonschema **4.26.0**.
  Distribution metadata also records boto3/botocore **1.43.87** and torch
  **2.11.0**. No model or provider client was imported or run.
- This was not a fresh-environment or wheel-install test.

No current v6 campaign data or registered dataset was opened or generated.
Active-worktree untracked files were not used as inputs.

## Separately measured checks

| Check | Result |
| --- | --- |
| Full unchanged guarded validator | **3 failed, 1538 passed, 10 skipped, 193 subtests passed, 1 warning** |
| Original adapter suite | **41 passed**, no failures/errors/skips |
| Public loader suite | **18 passed**, no failures/errors/skips |
| Cold portable roundtrip | **9 parent files byte-identical**, 8-file public export, 2 identical public loads |
| Bridge suite inside roundtrip | **12 tests + 15 subtests passed** |
| Synthetic exposure suite inside roundtrip | **8 tests + 3 subtests passed** |

Do not add these counts together: the full suite includes the bridge tests,
and focused checks deliberately repeat coverage. Full-suite JUnit reports
1744 entries, including subtests and skips.

The public roundtrip recorded zero private-file reads, parser/generator calls,
parent imports, subprocess/Git calls, or network attempts. It added no import
hook and did not change the module search path. Source bytes and all protected
baseline bytes remained unchanged.

## Exact full-suite failure

The three failing tests were:

```text
tests/test_launch.py::LaunchTests::test_cleanup_deletes_owned_role_when_policy_already_absent
tests/test_launch.py::LaunchTests::test_cleanup_will_not_delete_untagged_security_group
tests/test_validate_local_v3.py::test_real_sdk_exception_import_works_without_live_client_modules
```

Each traceback reaches `tests/test_contrast_v7_bridge.py:19`.
That test module installs `NoNeuralOrProvider` globally at import and never
removes it. Its blanket `botocore` block overrides the canonical validator's
explicit allowance for the pure `botocore.exceptions` import closure.
The affected tests use exception classes and mocked providers, not live clients.

The correction is to keep the bridge's import blocker scoped to its own
imports/tests, restoring `sys.meta_path` on exit. The canonical full
validator, source loader, model, executor, and old fixtures need no change.
No correction was applied to this frozen checkout or to these results.

## Commands and evidence

The commands actually run were:

```powershell
& 'C:/Python314/python.exe' -B 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/clean_source_prototype_v7_001/create_worktree.py'
& 'C:/Python314/python.exe' -B 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/clean_source_prototype_v7_001/run.py'
```

`run.py` verifies the initial clean checkout and raw Git bytes, then starts
the full unchanged `tools/validate_local_v3.py` in one process. The focused
checks run in separate processes. All commands, working directories, time
limits, UTC times, output hashes, and environment identity are retained in
`receipt.json` and the individual `*.process.json` records.

The cold check used the unchanged committed bridge `run.py`, copied into
the new empty sibling `records/clean_source_v7_bridge_001/` in the audit
checkout. Its original source pin stayed
`9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d`.
Its original/rebuilt manifest stayed
`19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29`.

Retained evidence:

- `worktree_creation.json` and raw creation output.
- `source_before.json`, `source_after.json`: all 556 exact byte identities.
- `full_validator_artifacts/`: original receipt, full stdout/stderr, JUnit.
- `adapter_artifacts/`: original 41-test receipt, stdout/stderr, JUnit.
- `public.stdout.txt`, `public.stderr.txt`: exact 18-test output.
- `portable_bridge_artifacts/`: copied runner, receipts, pins, and outputs.
- The original generated diagnostic bundles remain in the detached checkout.
- `receipt.json`: final failed audit receipt, SHA-256
  `dec93b989ee66c6e4c79476dcc06631d14df947ed5c77aef5b2ab109e103d9d1`.

The full validator ran for 174.809 seconds including its wrapper; pytest
reported 166.80 seconds. It completed normally, not by timeout. All failed
and successful results are preserved; no automatic retry or source edit
occurred inside the frozen audit.

This is preparation and test-isolation evidence. It is not AWS execution,
model learning, held-out performance, release installation, or evidence of
a CAS-specific advantage.

