# Clean-source v6 audit

The full guarded pure suite passes from a separately created clean checkout of
`acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0`, without using uncommitted files from
the active META2 worktree.

**Result: 1,529 test functions and 178 subtests passed; 10 GPU tests skipped;
1 intentional duplicate-ZIP warning.** There were no failures or errors.
JUnit reports 1,717 entries because that total includes subtests and skips.

This is a clean-source check in the **existing Python environment**. It is not a
fresh-environment installation test, a wheel-install test, a GPU result, or a
learning result.

## Source and retained worktree

Frozen source: `acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0`

Independent detached worktree:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/contrast-v6-audit-acbb266f`

Frozen package:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/contrast-v6-audit-acbb266f/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

The target was confirmed absent before creation. The recorded command used
`git -c core.autocrlf=false worktree add --detach` at the exact source SHA.
Git status was completely clean before validation. Afterward, the only
untracked files were the five outputs of this audit under its new records
directory; no tracked file changed.

The active task was not relocated. No existing worktree, accepted model,
executor, verifier, permission code, or checkpoint was changed. The already-live
GPU job was not queried, stopped, restarted, or modified.

## What was verified

The independent wrapper checked **485 distinct committed files** against binary
Git objects and checkout bytes before and after the suite:

- 151 source/configuration files covered by the frozen validator.
- All 316 protected baseline files, plus their exact manifest.
- All 11 extra inputs pinned by the v6 launch profile.
- The six retained prototype-practice files, including its builder, verifier,
  receipts, README, and 256-task file.

There were **zero Git-object or checkout-byte mismatches**. The before and
after inventories are identical. The protected manifest SHA-256 is
`476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0`.

The committed prototype contains **256 tasks**. The committed exclusion
inventory contains **8,053 distinct graph signatures**. The pinned profile
inputs are present in this clean checkout and match their declared hashes.
No input was supplied from the active worktree's untracked evidence.

The registered source configuration declares **640 training, 96 validation,
and 72 test tasks**, using seed `2026092601`. These numbers are configuration
checks here, not newly generated or evaluated data. This audit did not generate
that registered dataset or open any live-job held-out predictions.

The frozen contrast curriculum tests generate only the already documented
seed-`926603` development fixture. The campaign tests mock the GPU, dataset,
training, and evaluation subprocesses; the dataset rejection test replaces
generation with a failing sentinel. The registered-seed run was not invoked.

## Commands, environment, and import restrictions

`create_worktree.py` records the exact checkout command and its raw output in
`worktree_creation.json` and the matching stdout/stderr files.

`run.py` verifies the frozen validator and profile bytes before importing their
pure helpers. It then runs the unchanged
`tools/validate_local_v3.py` from the clean package with a new output directory.
The exact absolute command is preserved in `receipt.json`. Inherited
`PYTHONPATH` was removed so it could not substitute the active worktree.

The historical validator performs syntax, source, protected-byte, pure-data,
control-flow, and mocked-backend checks. Neural libraries and provider client
imports are blocked. A small documented `botocore.exceptions` class dependency
is allowed for mocked-provider tests; this is not an AWS client or provider call.
GPU test execution is disabled and automatic pytest plugin loading is disabled.

The existing environment was:

- Python 3.14.0 at `C:/Python314/python.exe`
- pytest 9.0.2
- jsonschema 4.26.0
- boto3 and botocore 1.43.87 distribution metadata present
- Torch 2.11.0 distribution metadata present, but no Torch import or tensor work

No environment was created and no package was installed. Metadata presence does
not prove an installed neural dependency works. No provider call or paid action
was performed.

Raw pytest duration was **157.81 seconds**. The frozen validator took
**162.93155949999982 seconds**. The full independent wrapper, including before
and after Git-byte checks and artifact copying, took
**172.75237160000052 seconds**.

## Evidence files

This audit record directory is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/clean_source_contrast_v6_001`

- `receipt.json`: final source-bound audit, exact command, counts, environment,
  scope, and artifact hashes.
- `validation_receipt.json`: the unchanged validator's copied receipt.
- `stdout.txt`, `stderr.txt`, and `tests.xml`: exact copied test outputs.
- `validator.stdout.txt` and `validator.stderr.txt`: the wrapper's captured
  validator output.
- `source_before.json` and `source_after.json`: independent 485-file Git-object
  and checkout inventories.
- `source_snapshot_before.json`: the frozen validator's own initial snapshot.
- `worktree_creation.json` and corresponding raw outputs: checkout creation.
- `create_worktree.py` and `run.py`: audit-only reproduction helpers.

Final receipt SHA-256:

`037814b7a392fc4b2e4b4236afe3ffb3b72cd0e96849ebd32cc258d461e47194`

The original validation outputs and short temporary test directory remain
retained. Their exact paths are in the receipts. Existing outputs are not
overwritten; reproduction requires a new worktree/output location.

## Boundary

This result closes the clean-source pure-check question for this exact v6
commit in the recorded environment. It does not establish fresh-install
reproduction, learned generalization, CAS-specific advantage, native GPU
execution, or production readiness. It does not change the earlier held-out
CAS **0/72** result or the separate familiar-program **24/24** fit result.

