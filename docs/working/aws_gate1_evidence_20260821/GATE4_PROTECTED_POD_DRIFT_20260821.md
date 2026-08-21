# Gate 4 pre-launch finding — the guardian's protected-pod list has drifted

**Severity: LOW-MODERATE. Recorded at that level deliberately — this is a defence-in-depth gap, not an imminent failure, and it is stated as such.**

Found while exercising the arm path offline for `$0`, before any launch.

## The drift

Both independent stop components hard-code the same list:

```python
precreate_guardian_offline.py:32   PROTECTED_POD_IDS = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06"})
github_stop_supervisor.py:31       EXCLUDED_POD_IDS  = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06"})
```

Measured against the real account inventory:

| pod | in the protected list? | exists? | owner's standing instruction |
|---|---|---|---|
| `q2oqlooejhin7s` | **yes** | yes | "never delete or mutate" — **correctly protected** |
| `vernmyfb3ck9po` | **NO** | yes | "keep stopped; do not restart, update, or delete" — **not in the list** |
| `hilj2rzs54gi06` | yes | **no** | protects a pod that no longer exists |

## Honest severity assessment

The list is **enforced** — `precreate_guardian_offline.py:345`, `:529`, `:651` all raise on a protected ID. So it is live logic, not decoration.

**But the exposure is limited, and saying otherwise would overstate it.** The guardian binds to one exact pod by ID and by high-entropy exact name, and `vernmyfb3ck9po`'s name does **not** match `POD_NAME_PATTERN` (it ends in 8 hex characters, the pattern demands 32). So the name-recovery path cannot select it. The protected list is the **backstop**, and the backstop is what has the hole.

Net: no known path today reaches `vernmyfb3ck9po` through the guardian. The defect is that the layer specifically designed to make that impossible does not currently name it.

## Why fix it now rather than later

`protected_pod_ids` is **embedded in the arm receipt** (`:496`) and validated by exact match (`:242`, `:347`). Changing the list invalidates every previously issued receipt. Doing it **before** any receipts exist is free. Doing it after a launch means re-issuing the receipt chain.

Both files are inside the canary's hash-locked source manifest, so the change also requires the re-pin procedure already exercised twice today (manifest → prereg self-hash → test literal → full suites).

## SCOPE CORRECTION — it is four runtime files across three freeze systems, not two

A wider search changed the size of this change. The same list is duplicated in **four** runtime files, plus a test:

| file | constant | freeze system |
|---|---|---|
| `precreate_guardian_offline.py:32` | `PROTECTED_POD_IDS` | not in the canary manifest |
| `github_stop_supervisor.py:31` | `EXCLUDED_POD_IDS` | **canary source manifest** |
| `create_provider_launch_receipt.py:57` | `PROTECTED_POD_IDS` | **canary source manifest** |
| `aws_production_guardian_core.py:120` | `REQUIRED_PROTECTED_POD_IDS` | **guardian `core-lock.json`** |
| `test_aws_production_guardian_core.py:2484` | parametrised over both IDs | test |

The name `REQUIRED_PROTECTED_POD_IDS` is the tell: this is a **cross-component contract**. All four copies must agree, and the value is embedded in receipts and validated by exact match. Changing it means editing four files and re-pinning **three separate freeze systems** — the canary source manifest, the preregistration self-hash, and the guardian core lock — then re-running all suites.

**Also identified: `hilj2rzs54gi06` is not junk.** The July handoff records show it as the **production pod** of the Jacobian canary work (`ATTEMPT_05_PRE_ANCHOR_FREEZE_RECORD.json`, `production_pod_instance_id`). It is a deliberate historical protection whose pod is no longer in the account. Keeping it is correct.

## Recommendation

Add `vernmyfb3ck9po` to both frozensets. Decide separately whether to drop the non-existent `hilj2rzs54gi06` — **recommend keeping it**, since a stale protective entry is harmless and removing it is a change with no safety benefit.

**This is firmly the owner's call**, and the scope correction above is why I did not simply do it: a four-file cross-component contract spanning three freeze systems is not a safe unilateral edit, and getting it half-applied would be worse than the gap it closes. It is not blocking: the launch blocker remains the missing GitHub secret `RUNPOD_CANARY_V2_API_KEY`.

No pod created. No GPU exists. Experiment **`NOT RUN`**.

---

## APPLIED 2026-08-21 — owner authorized ("do the protected-pod fix")

`vernmyfb3ck9po` is now protected in **all four** runtime components. `hilj2rzs54gi06` retained, as recommended, because it is a deliberate historical protection.

**Five edits:**

| file | constant |
|---|---|
| `precreate_guardian_offline.py:32` | `PROTECTED_POD_IDS` |
| `github_stop_supervisor.py:31` | `EXCLUDED_POD_IDS` |
| `create_provider_launch_receipt.py:57` | `PROTECTED_POD_IDS` |
| `aws_production_guardian_core.py:120` | `REQUIRED_PROTECTED_POD_IDS` |
| `test_aws_production_guardian_core.py:2484` | parametrised over all three IDs |

**Three freeze systems re-pinned:**

| lock | from | to |
|---|---|---|
| `core-lock.json` → `core_sha256` | `097c4db555741696…` | `525f4e33beb4c472…` |
| `core-lock.json` → `core_tests_sha256` | `502f2d3e45f71ec1…` | `368c0525773f5dca…` |
| canary `required_source_file_manifest_sha256` | `BD4CCE31…2A31` | `61D45BF1406F8CD3E11384774DBB2CF1C12FC20E354DEF9F03E249059C16ABB9` |
| preregistration self-hash | `5EAEE855…CEE8` | `6A3E320724F5D326E0A4E3D8B0D60AE18194F1D2CD64591F74274CE6E7F1DECF` |

Only `core_sha256` and `core_tests_sha256` moved inside the core lock — the runtime, ASL, template, build script, binding tool and the other two test files are untouched, which is the expected blast radius and confirms nothing extra was disturbed.

**Verified functionally, not just by diff.** All four constants were loaded from their modules and compared: all four agree, `vernmyfb3ck9po` present in all four, `q2oqlooejhin7s` still present, `hilj2rzs54gi06` retained.

**Suites: 576 passed, 0 failed** (85 canary + trajectory, 48 adapter, 443 guardian + tooling).

## ⚠️ CONSEQUENCE THE OWNER MUST KNOW — the LIVE stack now lags the repository

`core-lock.json` now hashes to `7c14e68f6faea5e06598389a181170643c6e30ffe69374a05d5f61ffb64c9c00`. The **deployed** preprod stack carries `CoreLockSha256 = f1b659a779e8b016456b519daaeaf7ea1c24823a4e0008f857fb2655361bc2c0`.

**These no longer match, and that is expected — but it means the LIVE guardian is still running the OLD core, which does NOT protect `vernmyfb3ck9po`.**

The repository is now correct. The deployed stack is not yet. Closing that gap requires rebuilding the guardian runtime ZIP and deploying it as a new artifact version through a fresh change set — the same procedure executed for Gate 2, and a separate authorized action.

**Practical risk in the meantime: low.** The deployed preprod guardian cannot reach RunPod at all — its provider secret is a refusal payload, so it fails closed before any provider contact. It cannot act on any pod, protected or otherwise. The gap is real but currently unreachable.

**No pod created. No GPU exists. Experiment `NOT RUN`.**

## Runtime REBUILT (not deployed) — 2026-08-21

The guardian runtime was rebuilt so the protected-pod fix is packaged and ready. **Built only. Nothing deployed.**

```
status                 : BUILT_OFFLINE_NOT_DEPLOYED
core_sha256            : 525f4e33beb4c472bea1fdfb45aab831ce56e02f5ecbbd323514e5ab3a6549b1
core_lock_sha256       : 7c14e68f6faea5e06598389a181170643c6e30ffe69374a05d5f61ffb64c9c00
core_tests_sha256      : 368c0525773f5dcabc24f32257d17dc597ad1a8ff8a0fb40d5c7f0aa371fa329
zip_sha256             : 9ebc90c2048669a0026dafb046b465c7d5a7405b172d32bcacf55ad80548e16e
zip_bytes              : 66169
zip_entries            : aws_production_guardian_core.py, guardian_build_identity.py, guardian_runtime.py
```

**The build script independently re-verified the lock and accepted it** — `core_sha256` and `core_lock_sha256` in the manifest match the values re-pinned above, which is a second confirmation that the re-lock was done correctly rather than merely written down.

Unchanged, as expected: `runtime_sha256 7df3cb30…`, `state_machine_sha256 70dc66f4…`, `template_sha256 e6a24702…`, `build_script_sha256 32ff3113…`, `binding_tool_sha256 e64f69a2…`, `tests_sha256 e23dc872…`, `precreate_tests_sha256 15699cfb…`.

**Deployed vs built:**

| | deployed (LIVE now) | built (ready) |
|---|---|---|
| runtime ZIP | `326f4836…` , `66154` B | `9ebc90c2…` , `66169` B |
| protects `vernmyfb3ck9po` | **no** | **yes** |

Deploying it is a **separate authorized action**: upload the ZIP as a new artifact version, create a change set, review, execute — the Gate 2 procedure. It is deliberately not done here.

**No pod created. No GPU exists. Experiment `NOT RUN`.**
