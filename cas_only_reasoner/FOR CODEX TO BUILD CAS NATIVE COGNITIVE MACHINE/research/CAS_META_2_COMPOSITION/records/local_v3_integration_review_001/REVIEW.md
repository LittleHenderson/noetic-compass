# Learning-v3 integration review

Recorded 2026-09-06 00:04 UTC. This is a source/pure-test review, not GPU
execution, a source freeze, a learned result or full release acceptance.
The source basis before these new integration files is
`c5c01a3010b4283932cd1720303393d6d4dea1c1`.

## Concrete integration findings

- The draft launcher removed `CAS_META2_RUN_GPU_TESTS` before the campaign,
  although the new campaign and its later GPU tests require that flag. The new
  launcher now keeps it set. Frozen launchers are unchanged.
- The draft campaign omitted `-m gpu` from the later 3+2 test command, while the
  project default selects `not gpu`. The new campaign now explicitly selects
  GPU tests. Its original pure receipt and separate correction receipt remain
  in `records/local_campaign_v3`.
- The draft inspector's SHA regex used an escaped literal backslash instead of
  an end anchor. It rejected ordinary full SHA strings. The regex is corrected
  and the root cross-component test directly checks valid and invalid hashes.
- The draft inspector omitted `dataset_id` from its detached dataset document.
  The actual v3 validator requires that identity. The field has been added;
  production data is still reserved for AWS construction.
- The new campaign records `requirements-gpu.txt`. The v3 inspector must check
  that additional file separately before handing the unchanged native-source
  subset to the old source-binding checker. The old checker is not edited.
- Review identified that manifest hashes alone cannot prove which Git commit
  supplied imported audit code. Actual Git-object verification before helper
  imports is being added and tested before source freeze. A changed sidecar
  cannot be allowed to redefine the source while keeping an old SHA label.

## Root cross-component check

The command below ran with neural/provider imports blocked, both GPU flags set
to `0`, CUDA hidden and pytest plugin autoload disabled:

```text
C:/Python314/python.exe -B -c "import sys; from tools.validate_local_v3 import NoNeuralOrProviderImports; sys.meta_path.insert(0,NoNeuralOrProviderImports()); import pytest; raise SystemExit(pytest.main(['tests/test_v3_integration_static.py','-q','-k','not manifest_profile','-p','no:cacheprovider']))"
```

Observed output: `26 passed, 1 deselected in 0.64s` (exit 0).
The deselected test checks the complete profile file inventory; the two new
auditor test files were still being written. It is not a passed inventory gate.

Root test source SHA-256 at this check:
`45262d527fee3dd1a727eb79eda34f71410401282ad507e825df93e9e841dda3`.
The tests compare config values/types, actual phase limits, gate commands,
fixed-depth counts, exclusions and frozen-file hashes. They do not run GPU
test bodies or construct the reserved curriculum.

## Remaining evidence

The final audit checks, full combined pure run, source-freeze commit, pinned
bundle, actual cloud gates/training/evaluation, byte/stored audits and direct
provider cleanup remain open at this observation. No AWS job or new budget
reservation was created during this review. The shared ledger remains revision
4: $32 reserved and $368 unreserved under the $400 total cap.
