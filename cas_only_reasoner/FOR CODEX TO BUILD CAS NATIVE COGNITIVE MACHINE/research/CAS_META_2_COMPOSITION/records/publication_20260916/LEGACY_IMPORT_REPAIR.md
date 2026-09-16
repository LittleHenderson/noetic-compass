# Legacy import repair

The six legacy launchers retain a static hash check before importing the shared budget module. Their old pin referred to the superseded budget implementation and prevented seven test modules from collecting.

The pin is now the reviewed budget file SHA-256 `cb3c78a0dfed166857109710cb8eac79dd337d837c839d558565982084b5a22f` in `launch_v3.py`, `launch_ablation_v4.py`, `launch_fit_v5.py`, `launch_contrast_v6.py`, `launch_recovery_v6.py`, and `launch_prototype_v7.py`. The hash is deliberately static. A later budget edit still fails closed until reviewed and re-pinned. Historical approval, cap, package, reservation and provider checks are unchanged.

Validation command:

```text
python -B -m pytest -q tests/test_bundle_v3.py tests/test_launch_v3.py tests/test_launch_ablation_v4.py tests/test_launch_fit_v5.py tests/test_launch_contrast_v6.py tests/test_launch_recovery_v6.py tests/test_prototype_v7_launcher.py
```

Result: **126 tests and 129 subtests passed**, exit 0. These are pure/fake-provider checks; no real cloud or neural execution occurred in this validation. They establish that the import blocker is repaired and the covered legacy contracts still pass. They do not establish that any legacy paid job is presently authorized or launchable against the current campaign ledger.
