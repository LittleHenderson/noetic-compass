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

## Recommendation

Add `vernmyfb3ck9po` to both frozensets. Decide separately whether to drop the non-existent `hilj2rzs54gi06` — **recommend keeping it**, since a stale protective entry is harmless and removing it is a change with no safety benefit.

**This is the owner's call**, because it edits hash-locked files and re-pins the freeze. It is not blocking: the launch blocker remains the missing GitHub secret `RUNPOD_CANARY_V2_API_KEY`.

No pod created. No GPU exists. Experiment **`NOT RUN`**.
