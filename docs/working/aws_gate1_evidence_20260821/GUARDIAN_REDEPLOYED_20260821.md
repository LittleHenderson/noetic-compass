# Guardian REDEPLOYED — the running guardian now protects `vernmyfb3ck9po` — 2026-08-21

**Owner said "redeploy the guardian". Executed. `UPDATE_COMPLETE` in ~45 s. The `OPEN` gap recorded earlier today is CLOSED.**

## The catch that made this non-trivial

The runtime compares the stack parameter `CoreLockSha256` against a value **compiled into the ZIP** and raises `COMPILED_CORE_LOCK_MISMATCH` if they differ (`guardian_runtime.py:3129-3136`). Verified the new ZIP compiles `CORE_LOCK_DOCUMENT_SHA256 = "7c14e68f…"` by extracting `guardian_build_identity.py` from the archive.

**So the parameter had to move with the artifact.** Shipping the new ZIP without also updating `CoreLockSha256` would have bricked all nine Lambdas at the activation gate.

The deployment binding also embeds four of the moved values, so it had to be regenerated too — this was a four-part change, not a one-line parameter bump.

## What moved

| | from | to |
|---|---|---|
| runtime ZIP | `326f4836…` , `66154` B | `9ebc90c2…` , **`66169`** B |
| artifact S3 version | `EEQnP8kR…` | `ug1rcQ3jzkeiZ9lvnLNrNGjoi9EhE35m` |
| `CoreLockSha256` | `f1b659a7…` | `7c14e68f6faea5e06598389a181170643c6e30ffe69374a05d5f61ffb64c9c00` |
| binding doc `core_sha256` | `097c4db5…` | `525f4e33…` |
| `DeploymentBindingSha256` | `a54c1810…` | `87f0293105b3b84202d52e7d2cbd209f90dd62634981e4d7ee2ce80ed522bf9d` |
| `DeploymentBindingObjectSha256` | `e40f3401…` | `92add9c4fca1cb040a5908fa6635842d62c40094d8b8174614528206a7efab85` |
| binding S3 version | `13XIqvs…` | `jeWBLBDaTc213srwVpOLgr5XE916DexO` |

Ten other parameters carried with `UsePreviousValue`.

**The binding tool refused the first attempt** — `FAIL_CLOSED:BindingError` / `INPUT_KEYSET_MISMATCH`, because the input carried extra keys from the output document. Rebuilt with exactly its 32 required keys. The tool behaving fail-closed on a malformed input is the design working.

**The two binding hashes are correctly distinct** (`92add9c4…` over raw bytes, `87f02931…` domain-prefixed over the source), and the runtime's own `_sha256(DOMAIN + _binding_canonical(source))` independently recomputes `87f02931…` — verified before upload.

## Pre-flight and execution

All seven checks green, including the artifact link now resolving to the new `66,169`-byte ZIP. Change set `guardian-redeploy-protected-pod-fix`: **19 modifications, 0 replacements, 0 removals**.

```
[   0s] UPDATE_IN_PROGRESS
[  45s] UPDATE_COMPLETE
```

## Verified after — in the deployed code, not the repo

All nine functions `LIVE`, one code revision `nryQwgSGaaACba+w`, `CORE_LOCK_SHA256 = 7c14e68f…` on every one, reserved concurrency total **`8`**.

**The decisive check:** the deployed Lambda package was downloaded from AWS and `aws_production_guardian_core.py` read out of it:

```python
REQUIRED_PROTECTED_POD_IDS = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06", "vernmyfb3ck9po"})
```

**`vernmyfb3ck9po` is now protected inside the running guardian**, proven from the artifact AWS is actually executing.

**Behaviour unchanged:** the `rate(1 minute)` recovery timer still fails closed with `GUARDIAN_RECOVERY_FAIL_CLOSED:ACTIVATIONERROR` — the deliberate provider-secret refusal. A *different* error would have meant the redeploy broke something. It did not.

## Standing

Repository and deployed stack are back **in agreement**. Gates 1, 2, 3 complete. **Gate 4 still blocked on the GitHub secret `RUNPOD_CANARY_V2_API_KEY`**, which only the owner can place.

No pod created. No GPU exists. The A40/Pythia experiment remains **`NOT RUN`**.
