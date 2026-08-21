# Gate 2 — rebuild record after the audit fix — 2026-08-21

**Status: `BUILT_OFFLINE_NOT_DEPLOYED`. Nothing uploaded, nothing deployed, no AWS resource mutated.** This page records the new frozen state so the owner can decide the deployment step with exact numbers in hand.

## Why a rebuild was forced

The audit fix touched `template.yaml` (restored two DynamoDB item-level grants; added a `Rule` forbidding the two binding hashes from being equal) and `tests/test_guardian_runtime.py` (two regression tests, proven to bite). Both files are inside the hash lock, and `build.ps1` verified this correctly by refusing:

```
THREW: HASH_LOCK_MISMATCH_TEMPLATE_SHA256
```

**There is no automatic re-lock path in `build.ps1` — it only verifies.** That is deliberate: re-freezing is a human act. `core-lock.json` was therefore updated explicitly, and both the old and new values are recorded below rather than silently overwritten.

## Exactly what moved

| lock field | from | to |
|---|---|---|
| `template_sha256` | `968e0faafcfa5b3ada874293cc753068e3bce4d37915fe409cb73c000ed88cd5` | `f32dbf76369b875d782327789076d9e66f82f845d1b57d94dfd87171ab7944fd` |
| `tests_sha256` | `a35d8ae7ec68433c0fc476e370705be401625e354e22c0cc9c5633fa7dfda754` | `e23dc872f0c33f4e3311950f72d81a457c13dc8fa63ff7a1c72e61a9d475f1de` |

**Unchanged, verified:** `core_sha256`, `runtime_sha256`, `state_machine_sha256`, `build_script_sha256`, `binding_tool_sha256`, `core_tests_sha256`, `precreate_tests_sha256` — seven of nine locked files untouched.

## The downstream hashes this changes

`core-lock.json`'s own digest is compiled into `guardian_build_identity.py` inside the runtime zip, so the artifact necessarily changes too:

| stack parameter | old value | **new value** |
|---|---|---|
| `CoreLockSha256` | `cfbefb0df13f6b8b3636e7b0fecd2fe20dacdef4754b3505c0ff19eefe95d0f7` | **`6b71e33d3e98308d8f72903a2643f7b6721511a1b53ac6642601f79a4707f453`** |
| `RuntimeZipSha256` | `326f483639b8b48ec8718ddf166663a721710e353968cde59d601bc22858baf9` | **`487145fa705aea91bf58169e2ea14624fd3ef3b7667b53bf3cb3275418180ad7`** |
| `LambdaArtifactVersion` | `EEQnP8kRPGmZBrFZAZk3AbsV3Lk2kBXA` | **not yet assigned** — S3 issues it on upload |

New artifact: **66,155 bytes**, entries `aws_production_guardian_core.py`, `guardian_build_identity.py`, `guardian_runtime.py`.

**Verified the zip actually carries the fix:** the packaged `guardian_build_identity.py` contains `CORE_LOCK_DOCUMENT_SHA256 = "6b71e33d…"` and the new `template_sha256` `f32dbf76…`; a search for the old `968e0faa…` returns **nothing**.

## The consequence the owner must weigh

**The LIVE activation is no longer a binding-only change.** RUNBOOK §7's rule is *same artifact version, only the listed binding parameters change*. That rule can no longer be satisfied — `RuntimeZipSha256` and `CoreLockSha256` both move. The existing change set `live-activation-for-owner-review` is therefore **doubly obsolete**: it pins the old artifact, and its `DeploymentBindingSha256` was never verifiable in the first place.

**Recommended sequence, none of it performed here:**

1. Upload the new zip; capture the S3 `VersionId`.
2. Delete the obsolete change set.
3. Create a fresh change set with: new `LambdaArtifactVersion`, `RuntimeZipSha256 = 487145fa…`, `CoreLockSha256 = 6b71e33d…`, `DeploymentBindingSha256 = a54c1810957e8903527f28e16a3856ee91b2eae90757705557949015c1e8fa3e`, `DeploymentBindingObjectSha256 = e40f34010e61098839cde9ea420233b7d50e65a7ece31cba968d326101e157f1`, `DeploymentBindingObjectVersion = 13XIqvsTspxqaqYWG3.sTMxC2XjLM7dx`.
4. Owner re-reviews against the **corrected** checklist.
5. Execute only once the Lambda quota clears.

Step 3 will now be **protected by the new `Rule`**: if the two binding hashes are ever set equal again, CloudFormation refuses the change set outright. That check exists because the value cannot be reviewed by a human — it is `NoEcho`, masked in the console and in `describe-change-set`, and redacted in CloudTrail.

## Suites at this state

`428 passed, 0 failed` (guardian + canary tooling), including the two new regression tests. Canary v2 + runtime `85 passed`; C14 adapter `48 passed`. **Total 561 passed, 0 failed.**

## Standing

Gate 2 remains **blocked** on the AWS Lambda quota — applied `10.0`, needs `≥ 108`, request `9b482ab5a8384b608285a2283f923876t4B7wPfM` still `CASE_OPENED`, support **CaseId `178728801200760`**, opened `2026-08-20 21:53:22 PT` and not updated since `21:53:36 PT`. The Support API is unreadable from here (`SubscriptionRequiredException` — no paid support plan), so the case can only be read by the owner in the console.

Nothing launched. No pod touched. Production `INERT`. The A40/Pythia experiment remains **`NOT RUN`**.
