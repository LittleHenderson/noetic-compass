# Final local registration binding

The independent recovery review passed. The v7 registration now includes its
full 5,685,892-byte receipt as source input 603, alongside the preserved original
538 inputs and all previously specified v7 dependencies. This is a local source
change, not an AWS launch, a new learning result, or source-release acceptance.

## Bound identities

| File | SHA-256 |
| --- | --- |
| `records/contrast_recovery_v6_review_001/run_001/recovery_stored_review.json` | `5396e0ab263fa435eefd2b8925382ce802b7af7c8d1c4dae5702d51435349ac3` |
| `EXPERIMENT_PROTOTYPE_V7.json` | `d054f7c29810e02fc581eb2f86cf98e1eeb10489cb34dd9f2a0b6cc6aa0d74c8` |
| `tools/experiment_profiles_prototype_v7.py` | `3331ce53d6f3f57b94cb7603f2b53f3c309a899ab2596b4b040fa1b01ccf6ee0` |
| `aws/launch_prototype_v7_plan.json` | `24fab96db6d1710af35dc24f1ebab6f9cb06d1183d70b9f0643d0061d0b4f882` |

The review has status `RECOVERY_STORED_REVIEW_PASSED`, `completed=true`, and no
errors. Its source, archive, job, runtime manifest, packet, 72 references and
360 candidate outcomes match the separately supplied identities. Packaging
also checks its two recovery GPU tests, four original GPU tests, unchanged
sealed predictions, final source/extraction checks, and absence of new training,
neural imports, tensor loads, provider calls or promotion during the audit.

The profile checks the receipt's exact size and SHA-256 before parsing it. Only
that authenticated review uses the larger 5,685,892-byte decoder limit. Normal
specification and source-pin JSON retains the 4 MiB limit.

The plan now permits only its registered source-bound workflow. Source freeze,
the exact committed bundle, shared budget/ownership checks, and the new current
job's v7 GPU smoke remain required. The smoke must complete before fresh data
generation or full training. An old review does not replace that smoke.

The limits remain those recorded in `README.md` and `timing.json`: GPU450,
dataset180, training3300, native2700, parent6900, compute7200 and lifetime7800
seconds. The $7 reservation and no-retry rule are unchanged. There was no
provider call, reservation, neural execution, fresh task generation, checkpoint
load, staging or commit by this packaging subtask.

## Executed pure checks

Focused packaging:

```text
python -B -m pytest tests/test_prototype_v7_profile.py tests/test_prototype_v7_launcher.py tests/test_prototype_v7_remote.py -q -p no:cacheprovider -p cas_meta2.pytest_no_aliases_v4
CAS_PYTEST_ALIAS_SUPPRESSIONS=24
86 passed in 17.25s
```

Combined v7 checks:

```text
python -B -m pytest tests/test_contrast_v7_bridge.py tests/test_contrast_v7_campaign.py tests/test_contrast_v7_native.py tests/test_contrast_v7_gpu_preflight.py tests/test_contrast_v7_cold_child.py tests/test_contrast_v7_orchestration.py tests/test_contrast_v7_smoke_private.py tests/test_prototype_v7_profile.py tests/test_prototype_v7_launcher.py tests/test_prototype_v7_remote.py -q -p no:cacheprovider -p cas_meta2.pytest_no_aliases_v4
CAS_PYTEST_ALIAS_SUPPRESSIONS=55
231 passed, 33 subtests passed in 56.73s
```

`git diff --check` also passed for the seven changed packaging files. The
earlier bounded public progress publishing fix is preserved. The historical
pre-registration notes remain unchanged as records of what was known then.
