# Clean recovery source audit at bd3341b0

The full clean-source check failed on two new tests that inspected imports left
by other tests. The saved portable v7 round trip passed. This directory preserves
the failed result; it is not a passing release receipt.

Source commit: `bd3341b0da893d0a68cfc05fb454848d2f027cd7`.
The detached worktree was created with `core.autocrlf=false`, and its initial
Git status was empty. Exact commands and paths are retained in the creation
receipt, process records, and main receipt.

## Full guarded check

The unchanged `tools/validate_local_v3.py` reported:

- 2 failed, 1687 passed, 10 skipped, 2 deselected, and 1 warning.
- 338 passed subtests, counted separately from test functions.
- JUnit contains 2037 entries, including the subtests and skips.
- No errors or timeout; source and protected files remained unchanged.

The failed tests were:

- `RecoveryCoreTests.test_module_imports_remain_pure`: a shared-process
  assertion found `cas_meta2.native` already loaded by another test.
- `test_recovery_v6_profile.test_no_neural_import`: its shared-process
  assertion rejected the canonical permitted pure botocore exception imports.

These failures do not establish an executor or protected-baseline defect.
The two assertions need fresh-process import checks. Their correction and
focused results are recorded separately in `../recovery_import_scope_fix_001/`;
this checkout and its failed outputs were not patched or rerun in place.

## Byte and dependency checks

All 641 distinct checked files matched their expected hashes, committed Git
blobs, and raw checkout bytes before and after. This includes the 557-file
recovery closure (538 frozen original dependencies), 176 validator source files,
316 protected files, and required v7 preparation inputs. These overlapping
categories are not additive. No mismatch was found.

The recovery source manifest at this commit is
`14994f7d875f414e8137da48adf793abb7b6f051097a97e94c61298563eebfa3`.
The initial Git status is empty. Final untracked paths are the new audit
outputs; no tracked source changes were found.

The stored exclusion inventory contains 8837 unique signatures: all 8053 prior
entries and 784 additional entries. This audit checked its committed bytes,
stored origin sets, and union counts. It did not reopen the underlying packet
or regenerate the inventory from current task data.

## Separate portable proof

The unchanged committed bridge runner was copied to a new empty record
directory in the clean worktree. Its known seed-926603 diagnostic round trip
passed: nine merged files matched the prior bundle byte for byte, eight public
training files were exported, and two fresh public-only loads passed without
private reads, parser or parent calls, Git, network, or hook/path changes.
Bridge checks: 12 test functions and 15 subtests. Exposure checks: 8 test
functions and 3 subtests. These overlap the full suite and are not added to it.

The original/rebuilt merged manifest is
`19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29`;
source pins are
`9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d`;
the public loader is
`5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0`.

## Evidence boundary

This used the existing Python 3.14.0 environment, not a fresh installation.
No registered dataset, model, GPU job, provider request, paid launch, training,
or held-out recovery execution was performed. The portable result proves
preparation and loading behavior only, not a new learning result.

`receipt.json` SHA256:
`222c7de2806a1b6caff86a918cf805baab630e86d84238908e1d4b3b5e6cbc29`.
Raw outputs and original JUnit/validator receipt are in
`full_validator_artifacts/`; the unchanged portable proof and its raw outputs
are in `portable_bridge_artifacts/`. The original retained scratch/worktree
paths are in the process records. Nothing was deleted.
