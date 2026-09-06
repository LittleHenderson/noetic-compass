# Future-run pytest alias control

The ec9 run failed final evidence collection with `V3_OUTPUT_LINK_DETECTED`.
Its partial packet omitted the offending link path, so the exact remote link
is not established. The GPU tests put pytest basetemp inside the campaign's
output tree, and pytest 9.0.2 creates `current` aliases for numbered temporary
directories. This new opt-in plugin prevents that known source of links.

Load it explicitly for future test processes:

```text
-p cas_meta2.pytest_no_aliases_v4
```

The plugin requires pytest 9.0.2 and the exact SHA-256 of the inspected
`_pytest.pathlib._force_symlink` helper:
`bf2d8dd60869ad74fa271923837893840d400590f1a9aef5db42e25afd2e21c0`.
Unknown versions or changed helpers fail closed. While active, only this
convenience-alias function becomes a counted no-op. Unconfiguration restores
the original helper and refuses to overwrite an unexpected intervening change.
The test output reports the number of suppressed alias requests.

Actual numbered directories and their files remain intact. Explicit symbolic
links are not disabled, removed, followed or accepted by this plugin. The frozen
collector and final payload index retain their link refusal. The original
failed packet and source remain unchanged.

Pure tests exercise real numbered-directory creation with instrumented link
calls, retained file content, unknown-version/helper refusal and overlapping
plugin ownership. They are not a remote reproduction of the failed run.

`tests/test_predict_viability_v4_gpu.py` also adds two authored CUDA tests for
the CAS and generic families: compare the new predictor's `v3` mode with the
frozen predictor, exercise the candidate mode, and verify unchanged model state
and absent parameter gradients. These tests have not run on AWS yet; they use
authored inputs and initial models, not held-out task or training evidence.

## Actual pure child-process check

`records/alias_plugin_process_001/receipt.json` binds an actual Windows pytest
child, the explicitly loaded plugin, its source hashes, exact command and raw
output. One test passed in 0.29 seconds; pytest reported three suppressed alias
requests. Real numbered directories and file content remained available, and
neural/provider imports were blocked. This checks plugin loading in a real
process; a Linux/AWS check remains necessary before calling the packaging issue
closed. The test scratch and XML/stdout/stderr records are retained.

## Full local regression

`records/local_alias_and_gpu_contract_v4_001/receipt.json` records 1,163 passed
test functions and 178 passed subtests, zero failures/errors, eight skipped GPU
modules and 236.1947396 seconds. All 104 source/config files and all 316 protected
baseline files were unchanged during validation. The new authored CUDA tests
were skipped, not passed. No training or GPU evaluation was performed.
