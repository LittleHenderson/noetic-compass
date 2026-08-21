# Gate status — 2026-08-21 — where the five gates actually stand

One page, so the next agent does not re-derive any of it. Every number here was measured today. **Nothing was launched, no AWS state was created, modified, or deleted, and the A40/Pythia experiment remains `NOT RUN` — it has neither passed nor failed.**

---

## Gate 1 — paper evidence — `OPEN`; **items 2 and 3 CLOSED**, only item 1 remains

| Item | State | What is missing |
|---|---|---|
| 1. Timing and fault tests | `OPEN / NOT RUN` — route chosen, **but a bootstrap circularity blocks the last measurement** | Harness built and tested; **it has measured nothing.** Needs a hash-locked **preproduction deployment**, which **cannot exist in this AWS account** — see the section below. **Architectural blocker, not a spend one.** |
| 2. CloudTrail / WORM export | **`CLOSED` / VERIFIED** | **Option A executed 2026-08-21.** Trail `cas-harness-audit-v1` is logging, multi-region, log-file validation on, global events included, into a **new dedicated** Object Lock bucket (`GOVERNANCE`, 1 yr). The guardian artifact bucket was **not touched**. **VERIFIED:** delivery at `2026-08-20T19:37:57.900000-07:00`, a **6,274 B** log file holding **24 real records**, object SHA-256 `78fb3220…`, locked until `2027-08-21`, and **a real `DeleteObject` was REFUSED with `AccessDenied`** — the lock protects, it does not merely label. |
| 3. Operator MFA record | **`CLOSED` / VERIFIED** | Owner signed in 2026-08-21. **78** operator events carry `mfaAuthenticated: "true"`; **7** are already inside the WORM bucket, alongside **17** digest files. Evidence SHA-256 `913dcce4…`. |

Both AWS quota blockers are **cleared** (`ec2/L-DB2E81BA` applied `8.0`; Lambda concurrency `1000`). Reserved-capacity arithmetic **fits**: 8 of 9 Lambdas reserve 1 each, leaving 992 unreserved against an AWS floor of 100.

### The preproduction blocker is NOT cost — a second guardian CANNOT coexist in this account

This was found on 2026-08-21 and it changes the owner decision, so it is stated before the rest.

`RUNBOOK.md` §6 requires timing evidence from an *"equivalent version- and hash-locked **preproduction** deployment."* **That deployment cannot be created in AWS account `807562639912` as the template stands.**

Every other resource is stack-scoped — `${AWS::StackName}-control`, `-observe`, `-recovery`, the log groups, the KMS alias — so none of them would collide. **The ledger table is not:**

```yaml
LedgerTable:
  DeletionPolicy: Retain
  UpdateReplacePolicy: Retain
  Properties:
    TableName: !Sub cas-runpod-guardian-global-v1-${AWS::AccountId}
    DeletionProtectionEnabled: true
```

The name is derived from the **account**, with no stack component, and the runtime hardcodes the same derivation: `GLOBAL_LEDGER_TABLE_PREFIX + account`. That table already exists — `cas-runpod-guardian-global-v1-807562639912`, strong-consistent count `0`.

Two consequences:

1. **A second stack fails to deploy.** CloudFormation would attempt to create a table that already exists.
2. **If it were forced, it would be worse than a failure.** Preproduction would read and write the **production** ledger, including the global single-active pointer `CONTROL#GLOBAL_ACTIVE#v1` / `SINGLETON#v1` — the exact mechanism that guarantees only one live authorization exists per account.

**This is a deliberate safety property, not a bug: the guardian is one-per-account by design.** It is also why the cost framing given earlier was wrong. The guardian stack itself is cheap; the GPU is not part of the timing test at all. **The real blocker is architectural.**

**A closed avenue, written down so nobody re-derives it.** DynamoDB table names are **per-region**, so the obvious trick is to deploy preproduction to a different region of the same account, where `cas-runpod-guardian-global-v1-807562639912` does not exist. **It does not work, and it should not be attempted.**

`guardian_runtime.py` pins the region in two places: `EXPECTED_REGION = "us-west-2"` (line 61), enforced at line 2894 (`region != EXPECTED_REGION` → `LOCAL_BINDING_STACK_SCOPE_INVALID`) and again at line 3115 (`AWS_REGION_BINDING_MISMATCH`). A guardian outside `us-west-2` **refuses to activate.**

The schedule would still tick and Lambdas would still emit `REPORT` lines, so the trick would *appear* to yield gap and startup numbers. **Those numbers would be worthless** — measured from a runtime failing its own region check on every invocation, with the STOP transport path never exercised at all. That is a fake measurement wearing the costume of a real one, and §6 asks for an *equivalent* deployment.

Changing `EXPECTED_REGION` is not an escape either: it edits a hash-locked source file, so it breaks `core-lock.json`, the deployment binding, and the freeze in one move.

The owner's options, stated honestly:

- **Option A — stand preproduction up in a SEPARATE AWS account.** The only option that gets timing evidence **without weakening anything.** The single-active guarantee stays intact in both accounts.
- **Option B — parameterize the ledger table name per stack.** Technically easy. **It weakens the account-wide single-active guarantee, which is a safety property, and doing it in order to make a gate pass is exactly what the gate list forbids.** Recorded for completeness, not recommended.
- **Option C — accept that timing evidence is not obtainable now.** LIVE then stays `NO_GO`, which is the honest resting state rather than a failure.

---

## Gate 2 — bind the guardian — `BLOCKED`, strictly downstream of Gate 1 item 1

`create_deployment_binding.REQUIRED` includes `timing_validation_evidence_sha256`, `timing_evidence_bucket`, `timing_evidence_key`, `timing_evidence_version`. **The binding document cannot be built before timing evidence exists and is uploaded.** These two gates are not parallel.

Of the four all-zero stack parameters, exactly one is computable today: `CoreLockSha256` = `cfbefb0df13f6b8b3636e7b0fecd2fe20dacdef4754b3505c0ff19eefe95d0f7`. It is recorded as a computed value and has **not** been written into any stack.

The `LIVE` change-set review is the owner's, by the gate list's own wording.

## Gate 3 — freeze the code — **COMPLETE to its inert ceiling**

**Correction to an earlier, vaguer statement of mine that Gate 3 pinning was "incomplete".** It is not. Measured:

| What the gate asks to pin | State |
|---|---|
| **Image** | **PINNED** — `sha256:4d1721e62b56d345c83b4fd6090664be6daf9312caab5b2e76f23d8231941851`, `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| **Hardware** | **PINNED** — `NVIDIA A40`, capability `[8, 6]`, Python `3.12.3`, torch `2.8.0+cu128`, CUDA `12.8`, dependency-lock hash `9E990C06…`, exact dependency versions, deterministic controls, memory floors |
| **Model** | **PINNED** — `EleutherAI/pythia-160m` at revision `50f5173d932e8e61f858120bcb800b97af589f46`, tree manifest `6373A5C8…`, 5 files each hashed |
| **Source set** | **PINNED and CURRENT** — all 15 frozen files, manifest re-pinned to `6EC46F9A…` today |
| **Receipts** | **SCHEMA-PINNED** — `cas_runpod_provider_launch_receipt.v2`, `cas_runpod_create_authorization.v1`, `cas_runpod_precreate_guardian_arm.v1`, both `required` flags `True` |
| **Commit** | **Enforced `None`** while inert — see below |
| **Test suites** | **488 passed, 0 failed** — canary 85, guardian 355, C14 adapter incl. hostile 48 |

Two things remain unpinned, and **both are structurally impossible to pin right now, not oversights**:

- `required_source_commit_sha256` is **enforced `None`** while `execution_authority` is `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`. Filling it means flipping to `GO_FOR_ONE_ENGINEERING_CANARY_ONLY` — **that is granting execution authority**, an owner act.
- **Receipt instances** cannot exist before a launch. Their schemas are already pinned; the receipts themselves are outputs of Gate 4.

Also fixed today under this gate: the repository had `core.autocrlf=true` and **no `.gitattributes`**, so one `git clone` would have rewritten every hash-locked file to CRLF and broken the whole freeze at once — measured, `core-lock.json` is `cfbefb0d…` as LF and `8be17d98…` as CRLF. Pinned to `eol=lf`; no file content was rewritten.

## Gate 4 — one machine, once — `NOT STARTED`

Requires creating a **paid** RunPod Pod. Preconditions already pinned: `SECURE`, non-interruptible, encrypted volume, `1800` s hard wall, `maximum_spend_usd` the string `"0.50"`, `maximum_provider_create_attempts` `1`. Owner action.

## Gate 5 — run the canary — `NOT STARTED`

Requires Gate 4. **Even a pass proves only the frozen capture/no-op/zero plumbing** — the canary source itself says such a pass is `NOT_PACKET_ELIGIBLE` and `NOT_SCIENTIFIC_RESULT`.

---

## The four owner actions, smallest first

1. ~~Sign in to the AWS console with MFA.~~ **DONE 2026-08-21 — Gate 1 item 3 is CLOSED and the evidence is in Object Lock.**
2. **Rotate the access key.** The only `Active` key on that user is the one recorded as exposed on 2026-08-16/17, and it is the sole credential the AWS lane runs on — **create the replacement first, then deactivate the old one.** Deleting first breaks the lane.
3. ~~Choose Option A or B for CloudTrail.~~ **DONE — Option A executed; Gate 1 item 2 is CLOSED.** Optionally raise Object Lock from `GOVERNANCE` to `COMPLIANCE` if you want retention that even root cannot lift.
4. **DECIDED 2026-08-21: "second account".** Owner steps are in `SECOND_ACCOUNT_RUNBOOK.md` — create an organization, create member account `cas-harness-preprod`, hand over the account ID. **No new access keys needed**: the agent reaches it by assuming `OrganizationAccountAccessRole`, which creates no new long-lived secret. Superseded framing: A second guardian cannot coexist in `807562639912` (see above). Option A is a separate AWS account; Option B weakens a safety property and should not be taken to make a gate pass; Option C is accepting `NO_GO`. This is the only path to Gate 2, and therefore to Gates 4 and 5.

**The trail is already live, so action 1 now closes item 3 with immutable evidence in one sign-in.**

## What must not be said

- Not that any gate has passed. **None has.**
- Not that the timing harness produced a number. **It has measured nothing.**
- Not that the sealed CloudTrail export is an immutable export. **It is not.**
- Not that the re-pin granted execution authority. **It did not**; the document declares itself inert in four separate places.
