# RUNBOOK — Step 2: re-derive a COHERENT live guardian binding

**Date:** 2026-08-21 · **Status:** written, **nothing applied**. `$0`, read-only analysis only.
**Purpose:** convert Step 2 from `BLOCKED` into one reviewed owner action. This runbook does **not** weaken any gate; it makes the gate bindable **correctly**.

---

## 1. Why Step 2 is blocked (the finding, restated exactly)

The four all-zero parameters cannot be honestly filled, because **no coherent binding exists for the live stack**. Three artifacts disagree:

| artifact | AWS account | runtime ZIP | core-lock |
|---|---|---|---|
| **LIVE stack** `cas-runpod-guardian-v1` (§4.7) | **`807562639912`** | **`326f483639b8b48ec8718ddf166663a721710e353968cde59d601bc22858baf9`** | — |
| computed binding `deployment-binding.PREPROD.json` | `063693212118` | `9ebc90c2048669a0026dafb046b465c7d5a7405b172d32bcacf55ad80548e16e` | `7c14e68f…` |
| working-tree rebuild (`dist/`, verified) | — | `9ebc90c2…` | `7c14e68f…` |
| `timing-evidence.json` (measured against the LIVE runtime) | `063693212118` | `326f4836…` | **`cfbefb0d…`** |

**Two independent mismatches:**
1. **Wrong account + wrong runtime.** The only computed binding targets **preprod** (`063693212118`, runtime `9ebc90c2`). The live stack is a **different account** (`807562639912`) running a **different build** (`326f4836`).
2. **Two core-locks.** The tree rebuild yields `7c14e68f`; the timing evidence measured against the live `326f4836` runtime records `cfbefb0d`. **Two builds, two locks.**

**Pushing the preprod values into the live stack would bind the gate to the wrong account and the wrong runtime — a weaker/wrong gate.** That is the exact thing your Step-2 instruction forbids. This is why nothing was filled.

## 2. The four parameters (live template `infra/runpod_guardian_live_candidate/template.yaml`)

| # | parameter | what it must hash |
|---|---|---|
| 1 | `DeploymentBindingSha256` | `sha256(DOMAIN + canonical(binding source))`, source **excludes** the two hash fields |
| 2 | `DeploymentBindingObjectSha256` | `sha256(raw binding object bytes)` — a **different** input from #1 |
| 3 | `CoreLockSha256` | `sha256(core-lock.json)` for the build that is actually deployed |
| 4 | `TimingValidationEvidenceSha256` | `sha256(timing-evidence.json)` measured **against that same build** |

All four are `^[0-9a-f]{64}$` with an all-zero default that acts as an **activation blocker, not an empty set**.

## 3. The decision you must make first (this is the fork)

**Option A — bind to the deployed build (`326f4836`).** Requires recovering the exact source that produced `326f4836`; the working tree does **not** contain it (the tree builds `9ebc90c2`). If that source cannot be reproduced byte-for-byte, **Option A is impossible** and you must take Option B.

**Option B — redeploy the current reviewed build (`9ebc90c2`) to the live account, then bind to it.** This makes the deployed artifact match a build you can reproduce and audit. It requires a live stack update in account `807562639912` **and fresh timing evidence measured against `9ebc90c2` in that account** (the existing timing evidence is preprod + `326f4836`, so it does not transfer).

> **Recommendation: Option B.** A binding is only meaningful if you can reproduce the bound artifact from reviewed source. `326f4836` is currently unreproducible from the repo, so binding to it would be a hash with no checkable provenance.

## 4. Steps for Option B (each step is checkable; nothing here weakens a gate)

1. **Confirm the target.** `aws cloudformation describe-stacks --stack-name cas-runpod-guardian-v1 --region us-west-2` in account `807562639912`. Record `ActivationMode` (expect `INERT`) and the current runtime ZIP hash (expect `326f4836…`).
2. **Rebuild reproducibly.** Run the repo build; verify `dist/guardian-runtime.zip` = `9ebc90c2…` and `core-lock.json` = `7c14e68f…`. **Both already verified in the current tree.** Abort on any mismatch.
3. **Upload the artifact** to the live account's artifact bucket under a key containing its own hash; record `VersionId`.
4. **Measure fresh timing evidence in the live account against `9ebc90c2`** using `tools/runpod_open_weight_canary_v2/measure_guardian_timing_evidence.py`. It must record `runtime_zip_sha256 = 9ebc90c2…` and a `core_lock_sha256` equal to `7c14e68f…`. **If those two fields do not match the rebuild, STOP — the mismatch has recurred.**
5. **Generate the binding** with `infra/runpod_guardian_live_candidate/create_deployment_binding.py`, pointed at account `807562639912`, the live stack, the uploaded artifact, and the new timing evidence. It emits all four hashes.
6. **Verify the binding before applying** — all four must be non-zero; `deployment_binding_sha256 ≠ deployment_binding_object_sha256` (they hash different inputs); `runtime_zip_sha256` = `9ebc90c2…`; `aws_account_id` = `807562639912`; every ARN resolves in that account.
7. **Create a CloudFormation CHANGE SET (do not execute).** Review it: exactly the four parameters change from all-zero to the derived values; **no gate, condition, or allowed-value list is loosened**; `ActivationMode` stays `INERT`.
8. **Owner executes the change set.** ← the only step that alters live state.
9. **Re-verify after apply:** the four stack parameters equal the binding file; guardian still `INERT`; ledger count still `0`; zero EC2 instances; GPU cost still zero.

## 5. Hard rules for whoever runs this
- **Never** copy the preprod values (`87f02931…`, `bd010e40…`, `59462f7d…`, `7c14e68f…`) into the live stack. They belong to a different account and, for three of the four, a different build.
- **Never** relax `AllowedValues`, the `^[0-9a-f]{64}$` pattern, or the `INERT`-only allowlist to make a step pass.
- **Never** treat an all-zero default as "no protected set" — it is an activation blocker.
- If any verification in §4 fails, **stop and record the failure**. Do not proceed to the change set.

## 6. Status
- **Blocked on:** the owner's Option A/B decision, then the change-set execution in step 8.
- **Agent-completable at `$0` after that decision:** steps 1–7 (all read-only or local, ending at an **unexecuted** change set for review).
- **Nothing in this runbook has been applied.** Step 2 remains `OPEN`.
