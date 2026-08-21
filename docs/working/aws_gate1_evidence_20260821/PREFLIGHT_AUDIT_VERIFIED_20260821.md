# LIVE pre-flight audit — VERIFIED findings — 2026-08-21

**7 surfaces audited, 23 findings raised, 6 survived 3-lens adversarial verification. Every finding below was then RE-VERIFIED by hand against live AWS and the real code — the agents were not taken at face value, and one of their headline claims did not survive that re-check.** Raw agent report retained at `PREFLIGHT_AUDIT_RAW_20260821.txt`.

**Standing consequence: the armed executor was DISARMED the moment this landed.** It would have executed a change set carrying an unverifiable binding parameter.

---

## CORRECTION to the audit's own headline — recorded before anything else

The agents' Finding 1 stated that the change set sets `DeploymentBindingSha256` **and** `DeploymentBindingObjectSha256` to the same value `9d6b2b74…`. **That is false of the change set.** The agents read `docs/working/aws_gate1_evidence_20260821/timing_evidence/live_changeset_parameters.PREPROD.json`, a **stale scratch file**, not the deployed change set.

Read live from AWS (`describe_change_set`):

| parameter | live change-set value | correct? |
|---|---|---|
| `DeploymentBindingObjectSha256` | `e40f34010e61098839cde9ea420233b7d50e65a7ece31cba968d326101e157f1` | **CORRECT** |
| `DeploymentBindingObjectVersion` | `13XIqvsTspxqaqYWG3.sTMxC2XjLM7dx` | **CORRECT** |
| `DeploymentBindingSha256` | `****` (NoEcho) | **UNVERIFIABLE** |

**And `9d6b2b74…` is not a random wrong value — it is the SHA-256 of the *superseded* 3,910-byte binding object.** Proven by listing S3 versions:

| S3 version | bytes | sha256 | required? |
|---|---|---|---|
| `13XIqvsTspxqaqYWG3.sTMxC2XjLM7dx` | **3935** | `e40f3401…` | **yes — pinned by the change set** |
| `sFs3f6L4c8FR.1JhZDnE3tIC60U4FcK3` | 3910 | `9d6b2b74…` | no — pinned only by the stale file |

So the stale file describes an older activation attempt. **The change set itself is correct on every parameter that can be read.**

---

## FINDING 1 (revised) — the one hash nobody can check — **BLOCKS A VERIFIED ACTIVATION**

**The runtime requires two *different* values, and the one that matters most cannot be verified by anyone — including the owner.**

Computed with the guardian's **own functions** (`_sha256`, `_binding_canonical`, `DEPLOYMENT_BINDING_DOMAIN`) against the real 3,935-byte document:

```
DeploymentBindingSha256       MUST be  a54c1810957e8903527f28e16a3856ee91b2eae90757705557949015c1e8fa3e
DeploymentBindingObjectSha256 MUST be  e40f34010e61098839cde9ea420233b7d50e65a7ece31cba968d326101e157f1
```

They differ by construction (`create_deployment_binding.py:182-184`: the digest is taken over the source, then two more fields are appended before serialisation), and `a54c1810…` equals the document's own internal `deployment_binding_sha256` field — confirming it is the required value.

`guardian_runtime.py:2975-2980` recomputes `sha256(DOMAIN + canonical(source))` and `hmac.compare_digest`s it against `DEPLOYMENT_BINDING_SHA256`. A mismatch raises `LOCAL_MATERIAL_BINDING_DIGEST_MISMATCH` inside `_activation_gate`, for **every** capability, before any provider contact — all nine Lambdas fail closed, including STOP.

**Why this is unverifiable, not merely unknown:** `template.yaml:16` marks the parameter `NoEcho: true`. It is masked in the console, masked in `describe_change_set`, and **CloudTrail redacts it too** — verified: the `CreateChangeSet` event of `2026-08-21T05:03:15Z` records `DeploymentBindingSha256 = None`.

**The evidence that it is probably wrong:** `HOW_TO_REVIEW_THE_CHANGE_SET.md:32` documents the value as `e40f3401…` "(shows as `****`, NoEcho)" and line 33 says the object hash is the "(same value)". If the change set was built from that checklist, the parameter holds `e40f3401…` — **provably the wrong one**.

**Verdict: not "the change set is broken", but "the change set cannot be proven sound."** Under the project's own rule — *a status with no checkable artifact is not a status* — that is disqualifying on its own.

**Fix:** delete the change set and create a fresh one with both values set explicitly from the proven pair above, then add a CloudFormation `Rule` asserting the two parameters are **not equal**, so this class can never be executed again.

## FINDING 2 — **CONFIRMED BY HAND** — destroys the single paid CREATE attempt

**`CreateProxyRole` cannot execute its own DynamoDB transaction.**

Verified directly:

- `template.yaml:305-320` — `CreateProxyRole` grants exactly `secretsmanager:GetSecretValue` and `dynamodb:TransactWriteItems`.
- `guardian_runtime.py:1974` / `:2017` — the one transaction contains an `"Update"` item and a `"ConditionCheck"` item.
- DynamoDB authorises `TransactWriteItems` **per item, by that item's own action** — `Update` needs `dynamodb:UpdateItem`, `ConditionCheck` needs `dynamodb:ConditionCheckItem`.
- **`grep -c` over the whole live-candidate template returns `0` for `dynamodb:UpdateItem` and `0` for `dynamodb:ConditionCheckItem`.** Neither is granted anywhere.
- The **predecessor** template `infra/runpod_precreate_guardian_aws/template.yaml` grants `dynamodb:UpdateItem` at lines `618`, `980`, `1027`, `1074`, `1121`. The pairing existed and was lost.

**When it bites:** not at this activation — the preprod refusal payload trips earlier. It stays hidden until the secret is made real: the **one paid create attempt**. The durable non-retryable marker is committed *before* the failing call, so the outcome is `NO_CREATE_DISPATCHED_SAFE_LOSS` — the POST to RunPod never issued, the one-shot spent, the money gone.

**Fix:** `Action: [dynamodb:TransactWriteItems, dynamodb:UpdateItem, dynamodb:ConditionCheckItem]`.

## FINDING 3 — **CONFIRMED BY HAND** — the human gate cannot catch Finding 1, and the deployment violates its own runbook

Two parts, both verified.

**(a) The checklist states an impossible pair.** `HOW_TO_REVIEW_THE_CHANGE_SET.md:32-33` gives both hashes as `e40f3401…` and says "(same value)". That is unsatisfiable for any document. A reviewer following it exactly **confirms** Finding 1 rather than catching it — and the file already records the verdict "review passed."

**(b) The INERT stack has recovery switched ON, against RUNBOOK §4.** Read live from the deployed stack:

```
ActivationMode        = INERT
RecoveryEnabled       = TRUE          <- RUNBOOK requires FALSE while INERT
RecoveryScheduleState = ENABLED       <- RUNBOOK requires DISABLED while INERT
EventBridge rule cas-harness-preprod-guardian-RecoverySchedule-EGPlYAmRkvLa: State=ENABLED, rate(1 minute)
recovery Lambda invocations, last 6h: 165
```

The recovery Lambda **has been firing and failing `DEPLOYMENT_IS_INERT` for hours.** Harmless — it fails closed, which is the design working — but it means the deployment never matched its own documented INERT posture, and the checklist's "unchanged" line hid it.

## FINDING 4 — plausible (standing 2/3) — the first LIVE error will accuse the owner

The documented expected outcome `PROVIDER_SECRET_FORMAT_INVALID` is **unobservable**. A bare `except Exception:` at `aws_production_guardian_core.py:887-892` swallows the transport error and re-raises `ValidationError("SECRET_GUARD_REJECTED_EXACT_CREATE_REQUEST")`, which `guardian_runtime.py:3274-3275` collapses to `GUARDIAN_FAIL_CLOSED:VALIDATIONERROR`. That string's only defined meaning is "your create request contains credential material" — the inverse of the truth. Not verified by hand to the same depth as 1-3; recorded as plausible.

---

## Surfaces audited and found CLEAN

Named so coverage is visible. Hypotheses were raised against each and **refuted by the code**: activation-gate outcome collapse; an autouse fixture disabling the gate; RUNBOOK §6 timing-hash error; KMS decrypt missing on the activation-document read; non-canonical bytes passing the hash gate; create-proxy retry envelope exceeding timeout; recovery preempting a healthy RUNNING owner; reserved concurrency colliding with ASL retry; execution-history exhaustion; DLQ with no consumer; a refusal string being forwarded to RunPod as a bearer token; `ProviderSecretArn` reverting to its placeholder default.

**Freeze integrity: INTACT.** All nine hash-locked files verified byte-identical to `core-lock.json`. **Every defect found lives in artifacts OUTSIDE the lock** — the parameter file and the review checklist. That is the structural lesson: the freeze protects the code, and the operator's actual parameter values were never inside it.

## What this audit CANNOT establish

- It is a **static read plus live read-only AWS queries**. **No LIVE execution occurred and no AWS resource was mutated.**
- A clean surface is **not proof it works** — it means the specific hypotheses raised were refuted. The canary defect proves absence of evidence is not evidence of absence.
- `DeploymentBindingSha256` remains **unknown**, not proven wrong. Finding 1 is a verifiability failure, not a demonstrated mismatch.
- Finding 4 was not hand-verified to the depth of 1-3.

## Recommended order

1. Fix Finding 2 (one template line) — it is the one that costs real money.
2. Rebuild the change set with the proven distinct hash pair; add the not-equal `Rule`.
3. Correct the review checklist; bring the parameter file under the hash lock.
4. Decide the `RecoveryEnabled` posture deliberately.
5. Then re-review, and only then execute.

**Nothing launched. No pod touched. Production `INERT`. The A40/Pythia experiment remains `NOT RUN`.**
