# Review sheet — `live-activation-v3-verified` — 2026-08-21

**This replaces `HOW_TO_REVIEW_THE_CHANGE_SET.md`, whose checklist was wrong.** That file told you both binding hashes were the same value. They can never be the same value. A reviewer following it would have *approved* the defect. It has been corrected, but use **this** page.

Stack `cas-harness-preprod-guardian`, account `063693212118`, `us-west-2`. Everything below was read live from AWS, not copied from notes.

---

## First: the thing you were trusting that does not work

Your Gate 2 says *"four SHA-256 fields are still all zeros. Fill them."* The template has a rules block that appears to enforce exactly that.

**It does not. I tested it against real CloudFormation.** All four of these were **accepted**:

| I submitted | The template forbids it | AWS |
|---|---|---|
| `CoreLockSha256` = 64 zeros | yes | **accepted** |
| `TimingValidationEvidenceSha256` = 64 zeros | yes | **accepted** |
| `ProviderAccountId` = `UNBOUND` | yes | **accepted** |
| `RecoveryEnabled` = `FALSE` under `LIVE` | yes | **accepted** |

`Rules` is a Service Catalog feature. Direct CloudFormation ignores it. **The stack would have gone LIVE with all four fields still zeroed.** That gate was never real, and no amount of care in this review would have revealed it — only testing did.

The replacement is `tools/runpod_open_weight_canary_v2/verify_activation_parameters.py`, which runs *before* submission and refuses what CloudFormation waves through. **The parameter set below passed it.**

## What you are approving

**21 resources modified. 0 added. 0 removed. 0 replaced.** The nine Lambdas, their roles, the state machine and the recovery schedule pick up new bindings. Nothing is destroyed; no data is touched.

## The values — check these

| Parameter | Value |
|---|---|
| `ActivationMode` | `LIVE` |
| `CoreLockSha256` | `f1b659a779e8b016456b519daaeaf7ea1c24823a4e0008f857fb2655361bc2c0` |
| `RuntimeZipSha256` | `e59a73e1519154e0ad3d424c2975a282896b93675df6915ed923933831dea10a` |
| `LambdaArtifactVersion` | `tZaIDqpddDwhFcUA4QEwUBG_9UoasYfL` |
| `DeploymentBindingSha256` | **`a54c1810…`** — shows as `****`, see below |
| `DeploymentBindingObjectSha256` | `e40f34010e61098839cde9ea420233b7d50e65a7ece31cba968d326101e157f1` |
| `DeploymentBindingObjectVersion` | `13XIqvsTspxqaqYWG3.sTMxC2XjLM7dx` |
| `TimingValidationEvidenceSha256` | `59462f7d469c53ae377052b953582d43663a3288977e20ff7c7c85149d962126` |
| `TimingEvidenceObjectVersion` | `OsjCHqefUNq6hbeGT2.TurX8ib09vhkw` |
| `ProviderAccountId` | `user_38E4xHk5H6yjrzEh4KUse08Ia8U` — an identifier, **not** a credential |
| `RecoveryEnabled` / `RecoveryScheduleState` | `TRUE` / `ENABLED` |

**The two binding hashes are DIFFERENT, and must be.** `DeploymentBindingSha256` hashes the document *without* its own hash fields, under a domain prefix. `DeploymentBindingObjectSha256` hashes the raw file bytes, which *include* them. If they ever match, one is wrong.

**`DeploymentBindingSha256` is unreviewable by eye.** It is `NoEcho`: masked in the console, masked in the API, and I confirmed **CloudTrail redacts it too**. You cannot check it and neither can I. That is why it is checked by recomputation instead — the verifier re-derives it from the binding document using the guardian's own code and gets `a54c1810957e8903527f28e16a3856ee91b2eae90757705557949015c1e8fa3e`.

## Hash links — verified by fetching the actual bytes

Not asserted. Each object was pulled from S3 **by exact key and version**, then hashed:

| object | bytes | sha256 matches its parameter |
|---|---|---|
| runtime artifact | `66,154` | **yes** |
| deployment binding | `3,935` | **yes** |
| timing evidence | `967` | **yes** |

## What changed since the version you approved

Your earlier "review passed" applied to `live-activation-for-owner-review`, now **deleted as obsolete**. Differences:

1. **The IAM fix.** `CreateProxyRole` could start a database transaction but was not allowed to perform the two operations inside it. It would have failed on your **single paid create attempt**, after the never-retry marker was written and before RunPod was ever contacted. Restored, with two regression tests proven to fail on the old code and pass on the new.
2. **A rebuilt artifact.** The template is hash-locked and its fingerprint is compiled into the package, so fixing it changed the runtime zip and the core-lock hash.
3. **Correct, distinct binding hashes**, verified against the real document.

## Reserved capacity — clear

Lambda `ConcurrentExecutions` is now **`1000`** (was `10`). AWS requires 100 unreserved at all times, so reservable headroom is **`900`**. LIVE reserves **`8`**. **Fits.**

## What will happen if you say go

The stack goes `LIVE`. The nine Lambdas start enforcing their bindings. **The guardian still cannot reach RunPod** — the provider secret in preprod is a deliberate refusal payload, not a credential, so the first activation attempt fails closed. That is the intended test: it exercises the activation machinery only.

Expect the observable failure string to be unhelpful — see audit Finding 4; a bare `except` collapses it to a message that blames your create request. That is a known, recorded defect, not a new problem, and it does not block this step.

## Your options

- **"go"** — I execute immediately, then confirm the stack reaches `UPDATE_COMPLETE` with `ActivationMode=LIVE`.
- **"review failed: <what>"** — I delete the change set and fix what you name.
- **Say nothing** — it sits inert. It never self-executes.

## One thing I could not do for Gate 4

*"Check stock and price first."* The RunPod credential available here reaches `/pods` only; the catalog and pricing endpoints return `400`, and GraphQL returns `403`. **A40 stock and price must be checked in the RunPod console at launch time.** For reference only, not a live quote: the existing stopped canary pod `vernmyfb3ck9po` records `costPerHr 0.44`, under the `$0.50` cap.

Both protected pods re-verified `EXITED` and untouched: `vernmyfb3ck9po` (`0.44`/hr), `q2oqlooejhin7s` (`4.59`/hr).

---

**Current state: stack `INERT`. Nothing executed. No pod touched. The A40/Pythia experiment remains `NOT RUN`.**
