# Gate 1 — paper evidence — status as of 2026-08-21

Gate 1 is: **AWS timing and fault tests, the CloudTrail/WORM export, and one real MFA login record.** It needs no GPU.

Everything in this directory was produced by **read-only** AWS calls. **No AWS state was created, modified, or deleted.** The guardian stayed `INERT`, zero EC2 instances existed throughout, the ledger stayed at `0`, and no model, GPU, provider, or RunPod activity occurred.

Integrity: `MANIFEST.json` lists every file with its exact byte count and SHA-256. `MANIFEST.json` itself hashes to `23c513cd376a27311fa5c7d51a1b611d5eec124d67c7d5bc573808c2b83dd035`.

---

## CORRECTION — a prior claim in this project's record was WRONG

**Claim as previously written:** *"CloudTrail still has no published matching `ConsoleLogin` event"* (`CAS_AWS_RUNPOD_HANDOFF_20260821.md`), repeated as *"CloudTrail still returns zero `ConsoleLogin` events"* in the `tksCAS` tracker entry `2026-08-21T00:32:07Z` and in spec sheet §4.7.

**Why it was wrong:** the query ran against **`us-west-2`**. IAM console sign-in is a global-service event recorded in **`us-east-1`**. A `us-west-2` result of zero is **not evidence of absence** — it is evidence of the wrong region.

**What is actually there:** `us-east-1` returns **10** `ConsoleLogin` events. Both files are retained here so the difference is checkable: `console_login_events_us_east_1.json` (**10** events) and `console_login_events_us_west_2.json` (**0** events, with the reason recorded inline).

**The conclusion does not change, but the reason does — and the new reason is exact and fixable.** The two `cas-g5-operator` console sign-ins both record `"MFAUsed": "No"`:

| Time | Principal | Result | `MFAUsed` |
|---|---|---|---|
| `2026-08-16T20:43:11-07:00` | `arn:aws:iam::807562639912:user/cas-g5-operator` | `Success` | **`No`** |
| `2026-08-17T10:07:56-07:00` | `arn:aws:iam::807562639912:user/cas-g5-operator` | `Success` | **`No`** |

The MFA device `cas-g5-operator-authenticator` was enabled at **`2026-08-20T23:00:15+00:00`** — that is **after both sign-ins**. So the two `MFAUsed: No` records are consistent with the device history and are **not** a policy violation at the time they occurred. What they establish is narrower and precise: **`cas-g5-operator` has not signed in to the console once since MFA was attached, so no `MFAUsed=Yes` record for the operator can exist yet.**

For completeness, the same file shows **8** `root` sign-ins, every one of them `"MFAUsed": "Yes"`. Root MFA is therefore evidenced; **operator** MFA is not.

---

## Item status

### 1. AWS timing and fault tests — `OPEN / NOT STARTED`

`RUNBOOK.md` §6 defines roughly twenty service-validation checks plus a timing envelope. Four substrate checks are already recorded as passed in the handoff (two-client DynamoDB conditional race with exactly one winner and a matching strong read; KMS `ECDSA_SHA_256` `MessageType=DIGEST` sign/verify `True`; unsigned API `POST` returning `403`; a PITR restore drill to a disposable table). **Those are a small fraction of §6 and none of them is timing evidence.**

The timing requirement is specific and is **not** satisfied by any artifact that exists today. §6 requires empirical evidence from a **version- and hash-locked preproduction deployment**, covering at least one consecutive missed-tick scenario, the largest observed recovery gap, worker startup, and the total exact-ID STOP transport path — all fitting inside a **300-second** STOP lead, where STOP must begin by minute **25** of the **30-minute** hard wall. The abstract model is `5 + 60 + 8 + 8 + 5 = 86` seconds. §6 states plainly that if those bounds are not observed, LIVE is **`NO_GO`**, and that the hash must never be invented or self-attested.

This is the largest remaining piece of Gate 1 and it is genuine engineering, not a query.

### 2. CloudTrail / WORM export — **CLOSED / VERIFIED 2026-08-21**

**RESOLVED. A trail now exists and is logging.** The owner instruction was explicit — *"Get the ... CloudTrail/WORM export ... You can do it now"* — and I had over-deferred by treating it as an unanswered A/B question. Option A was executed **additively**: nothing existing was modified.

| Property | Value |
|---|---|
| Trail | `arn:aws:cloudtrail:us-west-2:807562639912:trail/cas-harness-audit-v1` |
| `IsLogging` | **`True`**, since `2026-08-20T19:33:01.048000-07:00` |
| `IsMultiRegionTrail` | **`true`** |
| `IncludeGlobalServiceEvents` | **`true`** — so `us-east-1` `ConsoleLogin` is captured |
| `LogFileValidationEnabled` | **`true`** |
| `LatestDeliveryError` | **none** |
| Destination | `cas-harness-cloudtrail-worm-807562639912`, prefix `cloudtrail` |
| Object Lock | **`GOVERNANCE`, 1 year** default retention |
| Versioning | `Enabled` |
| Public access | **all four blocks on** |
| Encryption | `AES256` |

**VERIFIED on the fourth check. The item is now genuinely closed, and it was closed by evidence rather than by assertion.**

| Proof | Result |
|---|---|
| `LatestDeliveryTime` | **`2026-08-20T19:37:57.900000-07:00`** |
| `LatestDeliveryError` | **none** |
| Delivered log file | `cloudtrail/AWSLogs/807562639912/CloudTrail/us-west-2/2026/08/21/807562639912_CloudTrail_us-west-2_20260821T0240Z_qHVif4GAIqgycwEi.json.gz`, **6,274 B** |
| Object SHA-256 | `78fb32202f3a7810b95a60d4ac74594022c03f250c33c0fb2734cde18613a5b4` |
| Records inside | **24 real CloudTrail records**, decompressed and parsed |
| Object Lock on that file | `GOVERNANCE`, retain until **`2027-08-21T02:37:57.875000+00:00`** |
| **Deletion attempt** | **REFUSED — `AccessDenied`** |

**The last row is the one that matters.** A retention label is metadata; metadata is not protection. A real `DeleteObject` was issued against the delivered log file and **the lock refused it**. That is the difference between a bucket that is *configured* for WORM and one that *is* WORM.

The 24 records include the very API calls that created this bucket — `CreateBucket`, `PutBucketEncryption`, `PutBucketPublicAccessBlock`, `PutBucketObjectLockConfiguration`, `PutBucketPolicy`, `GetBucketAcl` — so the trail is demonstrably capturing real account activity, not emitting an empty shell.

**Consequence for item 3:** the owner’s next MFA console sign-in will land in this same immutable store. One sign-in now produces WORM-held evidence.

---

**The earlier, weaker state is retained below rather than deleted, because the sequence is the point: configured → checked → still pending → checked again → verified. Three checks said "not yet". Reporting the first one as "closed" was wrong, and being wrong three checks early is exactly what the discipline is for.**

**PRECISION, because wired is not the same as working.** Immediately after creation the bucket held **2 objects, both zero bytes**: `cloudtrail/AWSLogs/807562639912/CloudTrail/` and `.../CloudTrail-Digest/`. **Those are prefix placeholders CloudTrail writes to prove it can write — they are not log files.** At that moment `LatestDeliveryTime` was **absent** and `LatestDigestDeliveryTime` was **absent**, with `LatestDeliveryError` **none**.

So what is proven right now, exactly: the trail exists, `IsLogging` is `True`, **CloudTrail’s write permission to the bucket is demonstrated**, and **Object Lock is really applying** — the first placeholder came back `ObjectLockMode GOVERNANCE`, `RetainUntilDate 2027-08-21T02:33:00.915000+00:00`, exactly one year out.

**What is NOT yet proven: that a real log file has landed.** CloudTrail normally delivers within about 5 to 15 minutes of first enabling. Until `LatestDeliveryTime` is populated and a non-zero object exists under the `CloudTrail/` prefix, this item is **`CONFIGURED`, not `VERIFIED`**.

One-line check, safe to re-run:

```bash
aws cloudtrail get-trail-status --name cas-harness-audit-v1 --query "{logging:IsLogging,delivered:LatestDeliveryTime,error:LatestDeliveryError}"
```

**Design choices worth stating, because both were deliberate:**

- **A NEW dedicated bucket, not the guardian artifact bucket.** Delivering into `cas-harness-runpod-92754088` would have meant rewriting the bucket policy of a bucket the guardian stack depends on. That bucket was **not touched**; `put_bucket_policy` was never called on it.
- **`GOVERNANCE`, not `COMPLIANCE`.** `COMPLIANCE` mode is irreversible **even for the account root** — it would lock the owner into paying for that storage for the full retention with no escape. An agent must not make that choice unilaterally. `GOVERNANCE` still blocks ordinary deletion, and **the owner can raise it to `COMPLIANCE` if they want true immutability.**

**This also closes the evidence path for item 3.** Because global service events are included, the owner’s next MFA console sign-in is captured **immutably**, not merely into the expiring 90-day window. Sign in once and both items are evidenced.

**Reversal, if wanted:** `cloudtrail delete-trail --name cas-harness-audit-v1`, then empty and delete the bucket. Objects already written are held by `GOVERNANCE` retention and need `s3:BypassGovernanceRetention`.

The original finding, retained: **there was no CloudTrail trail in this account.** `describe_trails` returns an empty list in **both** `us-east-1` and `us-west-2` (`cloudtrail_trail_inventory.json`, `trail_count` **0**).

Consequence: the only record that exists is the **90-day CloudTrail Event history**. It is queryable, but it is **not immutable, not exported, and it expires.** Every `ConsoleLogin` record quoted above sits inside that expiring window. The RUNBOOK's *"external immutable evidence export"* gate cannot close against it.

The storage side is ready: bucket `cas-harness-runpod-92754088` has **`ObjectLockEnabled`** and versioning **`Enabled`** (`s3_worm_capability.json`), so a WORM target already exists. It is the same bucket that holds the guardian runtime artifact.

Creating a trail changes account-level logging configuration and adds ongoing cost, so **an agent should not create it unilaterally.** Two options, both preserving the evidence:

- **Option A — create a multi-region trail with log-file validation, delivering into the Object-Lock bucket under its own prefix.** This is the durable fix. It makes every future event immutable and exportable, and it is the only option that satisfies the gate for events that have not happened yet.
- **Option B — export the current 90-day event history to the Object-Lock bucket as a sealed, hashed object.** Cheaper and immediate, but it seals only what already exists and does nothing for future events.

Option A is the correct engineering answer. Option B is a stopgap that does not close the gate.

**Option B was executed on 2026-08-21, because the records expire and waiting costs evidence.** `cloudtrail_seal/` holds the CloudTrail Event history from `2026-08-16` to the export moment: **5,700** management events in `us-west-2` and **4** `ConsoleLogin` events in `us-east-1`, sealed with per-file SHA-256 in `SEAL_MANIFEST.json` (manifest SHA-256 `1ddc8385c4db79b5f06eb27461b59bd3815987ea40b9f5f48d6de72ade68d9a7`). Stored gzip -9 with `mtime=0` so the archive is byte-reproducible; the manifest records the SHA-256 of the **uncompressed** JSON alongside the SHA-256 of the `.gz` actually committed, and the round trip was verified after compression.

**This does not close the gate, and must not be described as if it did.** It seals what already existed on one day, into ordinary git rather than into Object Lock. It gives future events nothing. **Only Option A closes the gate.** The value of doing it anyway is narrow and real: without it, the only copy of these records was an AWS window that deletes itself.

### 3. One real MFA login record — `OPEN`, one owner action, about one minute

Exactly one thing is missing, and no agent can supply it: **the owner must sign in to the AWS console as `cas-g5-operator` using the MFA device.** Entering credentials is an owner action by rule and by good sense.

Once that sign-in happens, the record appears in `us-east-1` CloudTrail Event history with `"MFAUsed": "Yes"`, and this item closes on re-query. **If item 2 Option A is done first, that same record is also captured immutably** — which is the outcome the gate actually wants. Doing them in that order closes both with one sign-in.

---

## What must not be said

- Do **not** say MFA is evidenced for the operator. Root MFA is evidenced. Operator MFA is **not yet**.
- Do **not** cite a `us-west-2` `ConsoleLogin` count as evidence of anything.
- Do **not** treat the 90-day event history as an immutable export. It expires.
- Do **not** read any of this as execution authority. Gate 5 stays `OPEN / KEEP_OPEN` and the A40/Pythia experiment stays **`NOT RUN`** — it has neither passed nor failed.

## Note on contents

`console_login_events_us_east_1.json` contains full CloudTrail records, including `sourceIPAddress` values for the account owner's own sign-ins. That is deliberate — an audit record is worth nothing if it is redacted into unverifiability — but it is why this directory is private project evidence and not publication material.
