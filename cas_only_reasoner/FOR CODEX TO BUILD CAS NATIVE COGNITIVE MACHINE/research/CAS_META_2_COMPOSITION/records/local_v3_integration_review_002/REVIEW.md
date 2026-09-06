# Final integration corrections and focused verification

Observed 2026-09-06 UTC. This record follows the incomplete review in
`local_v3_integration_review_001`; it does not replace that earlier observation.

The trainer now subtracts the registered 480-second prediction reserve from
the learning deadline, rather than 120 seconds. Its pure tests evaluate the
actual arithmetic expression with several setup durations. The source changes
are confined to version 3; the old trainer and accepted runtime are unchanged.

Both new audit test files are present. The new inspector skips Git archive
ancestor directory entries before checking the package prefix. A regression
uses the actual nested-directory shape. The inspector also checks new source
assets before using the unchanged older native-source checker. Both auditors
check actual Git objects before importing project helpers.

The focused command below passed 125 tests in 3.93 seconds, exit 0. It includes
the complete profile inventory test that was previously deselected.

```text
C:/Python314/python.exe -B -c "import sys; from tools.validate_local_v3 import NoNeuralOrProviderImports; sys.meta_path.insert(0,NoNeuralOrProviderImports()); import pytest; raise SystemExit(pytest.main(['tests/test_inspect_cloud_packet_v3.py','tests/test_audit_stored_packet_v3.py','tests/test_train_v3_static.py','tests/test_v3_integration_static.py','-q','-p','no:cacheprovider','--basetemp=C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_tmp/v3-focused-005','--junitxml=records/local_v3_integration_review_002/focused.xml']))"
```

The working directory was this CAS_META_2_COMPOSITION package. Environment:
`PYTHONDONTWRITEBYTECODE=1`, both `CAS_META1_RUN_GPU_TESTS` and
`CAS_META2_RUN_GPU_TESTS` were `0`, `CUDA_VISIBLE_DEVICES` was empty,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and `PYTEST_ADDOPTS` / `PYTEST_PLUGINS`
were empty. Neural and provider-client imports were blocked inside pytest.
The JUnit SHA-256 is
`b23f9ce8e105c8ebda63107b3f186e6125f4c767b8351a1dd89a975d38cfebdf`.
The focused stdout is recorded in the task tool result; this directory retains
the original JUnit file. The combined runner separately saves raw output.

The candidate remains untrained at this observation. The combined pure suite,
source freeze, real cold-start Git/source checks, AWS GPU gates, learning and
native evaluation, stored evidence audit and live resource cleanup are separate
gates. Neither these mock checks nor an unchanged source archive proves them.

## Combined check completed after the focused observation

`C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_learning_v3_004`
completed with exit 0: 1,137 test functions and 178 subtests passed, seven GPU
modules skipped, zero failures/errors. JUnit contains 1,322 entries including
the seven skips. Pytest reported 278.13 seconds; the full runner took
291.9129618 seconds. Its 97 source files and 316 protected baseline files were
identical before and after. The duplicate-ZIP-member warning is intentional
test data, not an unreported test failure.

The new runner receipt SHA-256 is
`b1c3ba096a724c5934d01b89ae4ffe4798aebc041940ef598f25834e69c85043`.
Original stdout/stderr, JUnit and before/after source hashes are retained in
`records/local_learning_v3_004`. No model tensors or provider calls ran in that
validation process. The separate provider snapshot was read-only and did not
launch anything. Source freeze and cloud evidence remain separate gates.
