# Gate status — 2026-08-21 — where the five gates actually stand

One page, so the next agent does not re-derive any of it. Every number here was measured today. **Nothing was launched, no AWS state was created, modified, or deleted, and the A40/Pythia experiment remains `NOT RUN` — it has neither passed nor failed.**

---

## Gate 1 — paper evidence — `OPEN`, all three items need the owner

| Item | State | What is missing |
|---|---|---|
| 1. Timing and fault tests | `OPEN / NOT RUN` | Harness built and tested; **it has measured nothing.** Needs a hash-locked **preproduction deployment** — real cost, owner decision. |
| 2. CloudTrail / WORM export | `OPEN`, stopgap taken | **No trail exists in this account.** Option B seal committed; **only Option A closes the gate**, and it is billable account configuration. |
| 3. Operator MFA record | `OPEN` | **One owner console sign-in as `cas-g5-operator` with MFA.** An agent must never enter credentials. About one minute. |

Both AWS quota blockers are **cleared** (`ec2/L-DB2E81BA` applied `8.0`; Lambda concurrency `1000`). Reserved-capacity arithmetic **fits**: 8 of 9 Lambdas reserve 1 each, leaving 992 unreserved against an AWS floor of 100.

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

1. **Sign in to the AWS console as `cas-g5-operator` using MFA.** ~1 minute. Closes Gate 1 item 3.
2. **Rotate the access key.** The only `Active` key on that user is the one recorded as exposed on 2026-08-16/17, and it is the sole credential the AWS lane runs on — **create the replacement first, then deactivate the old one.** Deleting first breaks the lane.
3. **Choose Option A or B** for CloudTrail. Option A closes Gate 1 item 2; Option B does not.
4. **Decide on the preproduction deployment.** This unblocks Gate 1 item 1, which unblocks Gate 2, which is the only path to Gates 4 and 5.

Doing 1 after 3-as-Option-A closes two items with one sign-in.

## What must not be said

- Not that any gate has passed. **None has.**
- Not that the timing harness produced a number. **It has measured nothing.**
- Not that the sealed CloudTrail export is an immutable export. **It is not.**
- Not that the re-pin granted execution authority. **It did not**; the document declares itself inert in four separate places.
