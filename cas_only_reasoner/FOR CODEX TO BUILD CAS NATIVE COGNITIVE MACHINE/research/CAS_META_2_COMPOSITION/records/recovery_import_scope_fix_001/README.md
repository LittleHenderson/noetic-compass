# Recovery import-test isolation correction

The two corrected import checks pass in fresh Python processes. The mixed-import
check also passes when other allowed test modules are already present. This is
a test-isolation correction, not a change to the executor, neural model, runtime
source checks, or canonical import guard.

## Scope and result

- Focused: 2 test functions passed; no failures, errors, or skips.
- Mixed-import integration: 5 test functions passed; no failures, errors, or skips.
- The integration repeats the same two tests and adds the three existing pure
  SDK checks. These counts are separate runs, not seven distinct tests.
- Both edited test files kept identical bytes before and after these checks.
- No model, GPU, provider request, packet read, or current task-data read occurred.

The former assertions inspected every module left in the shared pytest process.
That wrongly treated another test's allowed imports as imports caused by these
modules. Each corrected test now starts an isolated child with
`-I -S -B`, checks the actual source path and before/after import footprint,
and traps forbidden imports and subprocess, shell, or network actions.
The child also checks that its import hooks and search path stay unchanged.

The integration deliberately preloads an inert `cas_meta2.native` module stub
(not native code) and the canonical permitted `botocore.exceptions` imports.
It then runs the corrected tests and the three existing SDK checks under the
unchanged canonical guard. The raw child footprints are in each stdout file.

## Exact identities

- `tests/test_contrast_recovery_v6_core.py`:
  `308b0d0cb9d8062d860157f26a12497ca839c7e264e7540ad507c5a329f0cb16`
- `tests/test_recovery_v6_profile.py`:
  `35ab7b3dab795c797ca2db5709893e563e0cab4686f70587082f81a2e9c3d684`
- `receipt.json`:
  `b27b275dd119850c94af314179b9eb1bf2128ea77158caa6d008bff66aaf5bd6`

## Reproduction and records

Command: `C:/Python314/python.exe -B records/recovery_import_scope_fix_001/run.py`
from the active META2 package directory. The exact absolute commands, working
directory, retained scratch paths, timestamps, Python identity, output hashes,
and test counts are in `receipt.json` and each stage's process record.
The `focused/` and `integration/` directories retain stdout, stderr, and JUnit.

This used the existing Python 3.14.0 environment, not a fresh package install.
The runner requires new empty output paths; do not overwrite these retained
records when repeating it. A new clean-source full-suite run is still required
after the source freeze. The earlier failed clean-source receipt remains intact
in `../clean_source_recovery_v6_001/`.
