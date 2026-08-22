# STEP 2 — LIVE change set for review. **NOT SUBMITTED. NOT SUBMITTABLE TODAY.**

**Date:** 2026-08-22 · **Status:** 🟥 **BLOCKED — and the block is a finding, not a delay.**
**Produced by:** a 3-lens audit of the LIVE candidate (`infra/runpod_guardian_live_candidate/`), the binding tooling, and the recorded external-resource state. **Nothing was created, modified, applied, or submitted to AWS.**

---

## 0. The one-paragraph answer

You asked me to fill four all-zero SHA-256 fields and review the LIVE change set, without weakening any gate to make it pass. **I can honestly compute 2 of the 5 hash fields; 3 cannot be honestly computed from anything that exists on disk.** More importantly, the audit found that **the gate protecting this step is already weaker than it appears — including one demonstrated bypass that was reproduced against the repo's own archived files.** Filling the hashes today would have produced a stack that *looks* bound and is not. The honest deliverable is therefore this review plus a blocker list, not a submitted change set.

---

## 1. 🟥 DEMONSTRATED BYPASS — the pre-submit control can be walked straight past

`tools/runpod_open_weight_canary_v2/verify_activation_parameters.py` is the **only** thing that actually refuses a bad LIVE parameter set (CloudFormation `Rules:` are **not enforced** by `CreateChangeSet`/`CreateStack` — measured 2026-08-21, already documented in the template).

**The bypass:** the verifier returns `[]` — i.e. PASS — immediately whenever `ActivationMode` is not exactly the string `LIVE`, **including when the key is simply ABSENT.**

**This was reproduced, not theorised.** The auditor ran the tool against the repo's own archived defective parameter file — the one carrying the exact duplicated-hash defect the tool was written to catch — and it printed `OK: parameter set is submittable`, exit `0`, because that file has no `ActivationMode` key.

**Why this is not academic:** any parameter set assembled with CloudFormation **`UsePreviousValue`** omits `ParameterValue`. A stack that is already LIVE stays LIVE from its previous value — while reaching the verifier looking INERT, and being waved through.

**This is precisely the failure mode your instruction names.** The gate is not being *made* weaker; it *already is* weaker than its own documentation claims.

## 2. 🟥 The control cannot see the parameter it most needs to see

`DeploymentBindingSha256` is `NoEcho: true`. `describe_change_set` returns `****`. So `preflight_live_activation.py` (lines 44–46) **substitutes a hard-coded literal** for it.

**Consequence:** the verifier never actually checks the `DeploymentBindingSha256` that is in the change set — it checks a constant the script supplies. The tool's own `****` refusal can never fire on that path. Verification of the anchor parameter is **structurally impossible** through the available mechanism.

## 3. 🟥 Recovery arming has ZERO runtime enforcement

`RecoveryEnabled` and `RecoveryScheduleState` are **not** in `_BINDING_SOURCE_FIELDS`, and `_expected_activation_contract()` **hard-codes `recovery_enabled: True`** as a constant.

**Consequence:** a LIVE stack with recovery **disarmed** still produces a *matching* digest, and no mismatch fires anywhere at runtime. The only thing that would catch it is the manual verifier — which §1 shows can be bypassed.

## 4. 🟥 No interlock

A repo-wide grep finds **no `create_change_set` caller anywhere** except the verifier's own docstring. **Nothing forces the verifier to run, and nothing records that it ran.** It is advisory.

---

## 5. What CAN be honestly computed today — 2 of 5

| field | value | caveat |
|---|---|---|
| `CoreLockSha256` | `7c14e68f6faea5e06598389a181170643c6e30ffe69374a05d5f61ffb64c9c00` | ⚠ CRLF-dependent — see §7 |
| `RuntimeZipSha256` | `9ebc90c2048669a0026dafb046b465c7d5a7405b172d32bcacf55ad80548e16e` | ⚠ **not** the deployed build — see §8 |

All nine locked hashes in `core-lock.json` were verified against the actual files and match `dist/build-manifest.json` and the `guardian_build_identity.py` compiled inside the ZIP.

## 6. What CANNOT be honestly computed — 3 of 5

| field | why not |
|---|---|
| `DeploymentBindingSha256` | No binding input or document exists for LIVE account `807562639912`. The only one on disk targets **preprod `063693212118`**. |
| `DeploymentBindingObjectSha256` | Same — plus it requires the object's S3 `VersionId`, which only exists after upload. |
| `TimingValidationEvidenceSha256` | The only timing evidence on disk was measured against a build that the tree cannot reproduce, with a different core-lock. |

**Missing inputs for LIVE that are recorded nowhere:** `ProviderSecretArn` for `807562639912` · `DeploymentBindingObjectKey` / `Version` · the KMS receipt-signing key ARN · the DynamoDB ledger table ARN · nine Lambda ARNs. `create_deployment_binding.py` fails closed with `INPUT_KEYSET_MISMATCH` on anything less, so **the binding cannot even be generated** until these are read live.

---

## 7. 🟥 The hashes are properties of the CHECKOUT, not the commit

`git core.autocrlf=true` means `core-lock.json` is **890 bytes CRLF = `7c14e68f`** in this working tree but **878 bytes LF = `eb4f77a3`** as the committed blob.

**Consequence:** "reproduce the bound artifact from reviewed source" is **not reproducible across platforms today.** A third party checking out the same commit on Linux computes a different hash and concludes the binding is wrong. *(This is the same class of defect as the `fd_generator.py` CRLF bug found on 2026-08-21 — second occurrence, so it is a pattern, not a one-off.)*

## 8. 🟥 The deployed runtime cannot be reproduced

The LIVE stack runs ZIP `326f4836…`. The working tree builds `9ebc90c2…`. The existing timing evidence was measured against the **unreproducible** build, with core-lock `cfbefb0d…` versus the tree's `7c14e68f…`, and the preprod binding pins template `968e0faa…` (two revisions stale) versus the tree's `e6a24702…`.

**Five artifacts disagree about which build is bound.** Also: `dist/guardian-runtime.zip` and `dist/build-manifest.json` are **git-ignored** — the only copy of the artifact `9ebc90c2` describes exists on this one disk.

## 9. 🟨 A capability-selective mismatch that a smoke test would miss

The on-disk timing evidence and binding disagree (`cfbefb0d`/`326f4836` vs `7c14e68f`/`9ebc90c2`), which `_verify_timing_evidence` rejects as `TIMING_EVIDENCE_BINDING_MISMATCH` — **but only on observe/create/starter.** The containment capabilities skip `_verify_activation_documents` entirely. **A containment-path smoke test would pass and the mismatch would not surface.**

## 10. 🟨 Reserved capacity — one inconsistency

8 of 9 Lambdas carry `ReservedConcurrentExecutions: !If [LiveMode, 1, !Ref AWS::NoValue]`. **The starter function has none** — and it is the state-machine entry point. At the documented account limit of `1000`, reserving 1 each costs 8 of the headroom, so this is trivially affordable; the omission is an inconsistency to close, not a capacity problem.

---

## 11. The change set — as it would be, and why it is not submitted

```
STACK      cas-runpod-guardian-v1        (account 807562639912, us-west-2)
ACTION     UPDATE  ActivationMode INERT -> LIVE
STATUS     *** NOT SUBMITTED — 3 of 5 required hashes have no honest source ***

ActivationMode                    LIVE
CoreLockSha256                    7c14e68f6faea5e06598389a181170643c6e30ffe69374a05d5f61ffb64c9c00   [computable, CRLF caveat]
RuntimeZipSha256                  9ebc90c2048669a0026dafb046b465c7d5a7405b172d32bcacf55ad80548e16e   [computable, NOT the deployed build]
DeploymentBindingSha256           <<UNRESOLVED — no LIVE binding document exists>>
DeploymentBindingObjectSha256     <<UNRESOLVED — no LIVE binding object exists>>
TimingValidationEvidenceSha256    <<UNRESOLVED — evidence measured against an unreproducible build>>
DeploymentBindingObjectKey        <<UNRESOLVED>>
DeploymentBindingObjectVersion    <<UNRESOLVED>>
TimingEvidenceObjectVersion       <<UNRESOLVED — currently empty string, which LIVE forbids>>
ProviderAccountId                 user_38E4xHk5H6yjrzEh4KUse08Ia8U
ProviderSecretArn                 <<UNRESOLVED — no secret recorded for 807562639912>>
RecoveryEnabled                   TRUE      [note: NOT runtime-enforced, see §3]
RecoveryScheduleState             ENABLED   [note: NOT runtime-enforced, see §3]
```

**I did not fill the three unresolved hashes with the preprod values.** Doing so would produce a stack that passes every automated check and is bound to the wrong account and a stale build — the exact "make the gate pass" failure you prohibited.

---

## 12. 🔒 OWNER DECISIONS REQUIRED (nothing proceeds without these)

1. **Which stack is the LIVE target?** Two are each described as LIVE in evidence written the same day: `cas-harness-preprod-guardian` (`063693212118`) and `cas-runpod-guardian-v1` (`807562639912`). Every requirement above has two contradictory answers until you name one.
2. **Option A or Option B for the runtime?** **A:** recover the source bytes that produce `326f4836` and bind the deployed artifact. **B:** rebuild + redeploy `9ebc90c2`, then re-measure timing. **B makes activation more than the binding-only change the runbook describes.**
3. **The bypass (§1)** — fix the verifier to fail closed on a missing `ActivationMode`, and/or interlock it into the submission path. This is a process decision.
4. **CRLF (§7)** — pin the checkout as part of the build definition, or normalise to LF, so hashes are reproducible by a third party.

## 13. Claim state
- **Real:** every defect above is from source reading plus local execution of the offline verifier; the bypass was **reproduced against the repo's own archived file**.
- **UNKNOWN, not passed:** no live-AWS verification of the stack's current parameters was performed in the audit environment (no boto3 on the default PATH there). `preflight_live_activation.py` already encodes the rule that a check which could not run is `UNKNOWN`, never a pass.
- **Not weakened:** no gate, assertion, or check was relaxed. Every item states what must **exist** first.
- **Not submitted:** no change set was created; nothing was applied.
