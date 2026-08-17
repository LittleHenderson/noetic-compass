# CAS Gate 5 — verified operator runbook (package 20260818)

One clean top-to-bottom flow for a single live one-shot run of the frozen Gate 5 AWS package. Copy each fenced block as-is. Every token and hash below is pinned and pre-filled — change nothing except `CAS_BILLING_ATTESTATION` (you set it yourself) and the per-file `NEXT_RELATIVE` values in Step 4.

---

## One-time prerequisites (before Step 1)

- An IAM **operator user `cas-g5-operator`** with `AdministratorAccess` already exists in account **807562639912**.
- Open **CloudShell in `us-west-2`, signed in as that IAM user — never the account root.** (AWS categorically denies `sts:AssumeRole` to root, so a root session can never complete `00`; confirmed live 2026-08-16.)
- Upload the archive **`aws_cloudshell_unarmed_20260818.tar.gz`** to CloudShell **`$HOME`**.
- The capsule payload files (`capsule_manifest.json`, `capsule_manifest.sha256`, the 12 transfer files, and `invoke_gate5_aws_full_verifier.ps1`) must also be available in `$HOME` when their step calls for them.

### Session discipline — read once, obey throughout

- **One-hour role-chaining cap.** CloudShell operator creds are themselves session creds, so `00`'s `AssumeRole` is role chaining, capped at exactly **3600 s** — the AWS platform maximum here (confirmed live 2026-08-17). You never get a longer session; you get a *fresh* hour by rerunning `00`.
- **Rerun `00` immediately before every later phase** so each phase starts on a nearly-full hour. Rerunning `00` is idempotent and safe: it verifies exact reuse of the already-created roles and reconstructs the first-bootstrap AMI/subnet boundary from the retained boundary file.
- **Re-set `CAS_BILLING_ATTESTATION` before every `00` rerun.** `00` re-validates `CAS_BILLING_ATTESTATION == ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)` on **every** invocation (not only the first), so a multi-hour run that crosses UTC midnight will make a later `00` **abort** (clean pre-billing abort, not a burned cycle) on a stale attestation. Before each later `00`, re-confirm the active default payment method and re-export `CAS_BILLING_ATTESTATION` with **today's** UTC date. Every later `00` block below already includes this export line.
- **Only `00` and `99` run as the operator** (from the retained operator prompt). Every other script (`01`, `02_stage`, `03`, `03b`, `02_provision`, `04`, `05`, `05b`, `06`, `07`) runs **inside the provisioner child shell** that `00` exec's.
- **IAM propagation delay:** the first 1–2 `sts:AssumeRole` calls right after roles are first created can return `AccessDenied`. Remedy: exit the child, wait ~15–30 s, **rerun `00`** — never resubmit downstream work.
- **NEVER resubmit a VM-side wait that outlives a session.** Resume only through the documented continuation lanes (`04 … watch`; `05b … observe/export`). And once you reach Step 6, **NEVER rerun `execute`** — the one-use claim is consumed exactly once regardless of how it returns.

---

## Step 1 — Operator bootstrap + one-hour STS session (`00`)

Purpose: verify the archive + `PACKAGE.sha256`, create the three per-run IAM roles + instance profile, assume the provisioner role for a fresh one-hour session, and drop into a credential-only child shell with no root fallback.

> Set `CAS_BILLING_ATTESTATION` **only after** you personally re-confirm the active default payment method **on today's UTC date**. `00` recomputes that date with `date -u` at runtime; if you cross UTC midnight before `00` runs, it will mismatch and abort. The `set +e / +u / +o pipefail` lines are intentional (`00` ends by exec-ing a fresh child) — copy them verbatim.

```bash
set -euo pipefail
export CAS_RUN_ID="g5-$(date -u +%Y%m%d%H%M%S)-$(openssl rand -hex 4)"
export CAS_PACKAGE_ARCHIVE="$HOME/aws_cloudshell_unarmed_20260818.tar.gz"
export CAS_PACKAGE_ARCHIVE_SHA256="a843f37e165e00a465a6dc633b7e299986a02a510ab8b0bb0dff501e33b0c528"
printf '%s  %s\n' "$CAS_PACKAGE_ARCHIVE_SHA256" "$CAS_PACKAGE_ARCHIVE" | sha256sum --check --strict -
export CAS_PACKAGE_PARENT="$HOME/cas-g5-package-$CAS_RUN_ID"
test ! -e "$CAS_PACKAGE_PARENT"
mkdir -m 700 -- "$CAS_PACKAGE_PARENT"
tar --no-same-owner -xzf "$CAS_PACKAGE_ARCHIVE" -C "$CAS_PACKAGE_PARENT"
cd "$CAS_PACKAGE_PARENT/aws_cloudshell_unarmed_20260818"
sha256sum --check --strict PACKAGE.sha256
export CAS_EXPECTED_ACCOUNT_ID="807562639912"
export CAS_OPERATOR_PRINCIPAL_ARN="arn:aws:iam::807562639912:user/cas-g5-operator"
export CAS_APPROVED_PACKAGE_SHA256="525365c4035ba644fb39793c88cbfcdda09ddad7fa3a84317a3c6e37e9bd61e1"
export CAS_BILLING_ATTESTATION="ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)"
export CAS_ROOT_BOOTSTRAP_TOKEN="CREATE-PROVISIONER:${CAS_RUN_ID}:${CAS_APPROVED_PACKAGE_SHA256}"
set +e
set +u
set +o pipefail
bash 00_root_bootstrap_and_assume.sh
```

- Provisioner role: `cas-g5-<SUFFIX>-provisioner`; STS session name `CasG5Provisioner-<SUFFIX>`, where `SUFFIX` = first 12 hex of `sha256(CAS_RUN_ID)`.
- `00` exports into the child: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_SESSION_EXPIRATION`, plus `CAS_EXPECTED_ACCOUNT_ID` / `CAS_APPROVED_PACKAGE_SHA256` / `CAS_RUN_ID`. `lib.sh` sets `AWS_REGION=us-west-2`, `AWS_DEFAULT_REGION=us-west-2`, `AWS_PAGER=""`, `AWS_CLI_AUTO_PROMPT=off`.
- **Keep this operator prompt open.** You return to it to rerun `00` before every later phase and to run `99`.
- If the first assume fails with `AccessDenied` (IAM propagation), exit the child, wait ~15–30 s, rerun `00`.

---

## Step 2 — Read-only preflight (`01`)

Purpose: prove the environment read-only (quota ≥ 8 vCPU, zero other instances, pinned Windows AMI, default VPC/subnet + active IGW route, live Windows On-Demand price) and write immutable `state.json` (`preflight_status=PASS_READ_ONLY`). Creates no workload resource.

Run in the **same provisioner child that `00` just exec'd**:

```bash
set -euo pipefail
bash 01_preflight_readonly.sh
less "$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/preflight-summary.json"
```

- **Immutable state:** `01` refuses to run if `state.json` for this `CAS_RUN_ID` already exists. **Any clean retry after state was written requires a brand-new `CAS_RUN_ID`.**
- The six-hour estimate written to state is **not** a hard spending cap (`budget_is_hard_cap:false`).
- If STS died before `state.json` was written: exit, rerun `00` (same `CAS_RUN_ID`), rerun `01`. Once `state.json` exists, a fresh attempt needs a new `CAS_RUN_ID`.

---

## Step 3 — Create the private staging bucket (`02_stage_bucket_unarmed`)

Purpose: create **only** the private, versioned, SSE-S3 (AES256), Block-Public-Access-all-four, BucketOwnerEnforced, TLS-only transfer/evidence bucket. No EC2, network, Scheduler, SQS, SSM, or test action.

Same child (no session floor of its own):

```bash
export CAS_STAGE_TOKEN="CREATE-STAGING-BUCKET:${CAS_RUN_ID}"
bash 02_stage_bucket_unarmed.sh
unset CAS_STAGE_TOKEN
```

- Bucket name is derived, not set: `cas-g5-807562639912-us-west-2-<first 12 hex of sha256(CAS_RUN_ID)>`.
- Preconditions from state: `preflight_status=PASS_READ_ONLY`, `aws_resources_created=0`, `provision_status=NOT_STARTED`, staging not already attempted.
- On success: `provision_status=STAGING_BUCKET_READY_NO_COMPUTE`, `staging.status=PRIVATE_BUCKET_READY_NO_COMPUTE`; state mirrored to `s3://<bucket>/receipts/<run>/control/resource-state.json`.
- On failure the built-in trap deletes the exact empty bucket and resets `aws_resources_created=0`. If the bucket may remain, abandon the run with `07_teardown.sh full` using `CAS_TEARDOWN_TOKEN=DELETE:${CAS_RUN_ID}` + `CAS_ACK_NO_RECEIPTS=DELETE_EMPTY_OR_FAILED_RUN:${CAS_RUN_ID}`, then run `99`. A clean retry needs a new `CAS_RUN_ID`.

---

## Step 4 — Stream the 14-file capsule (`03`) + successor wrapper (`03b`) — still no compute

Purpose: upload the sealed manifest + detached seal, then the 12 transfer files one at a time, verify all 14 remotely, and upload the audited PowerShell wrapper. CloudShell `$HOME` is 1 GB and the sealed surface is ~1.05 GB, so **the whole capsule must never sit in `$HOME`** — stage/upload/delete each file individually.

> These pre-compute phases run in the Step-1 child. If the one-hour session is running low at any point here, exit, rerun `00`, and resume the sub-step you were on (uploads are idempotent; `uploaded-objects.json` records what is already verified).

### 4a — `03 init` (upload sealed manifest + detached seal)

```bash
export TRANSFER_ROOT="$HOME/cas-g5-transient-$CAS_RUN_ID"
test ! -e "$TRANSFER_ROOT"
mkdir -m 700 -- "$TRANSFER_ROOT"
df -B1 "$HOME"
du -sb "$HOME" 2>/dev/null || true
mkdir -p -- "$TRANSFER_ROOT/manifest"
test -f "$HOME/capsule_manifest.json"
test -f "$HOME/capsule_manifest.sha256"
mv -n -- "$HOME/capsule_manifest.json" "$TRANSFER_ROOT/manifest/capsule_manifest.json"
mv -n -- "$HOME/capsule_manifest.sha256" "$TRANSFER_ROOT/manifest/capsule_manifest.sha256"
bash 03_upload_capsule_objects.sh init \
  "$TRANSFER_ROOT/manifest/capsule_manifest.json" \
  61F8182BE31830ED4A897DE0B2564085AD7BE05E826AFC65E9B6A0EBF3D15097 \
  "$TRANSFER_ROOT/manifest/capsule_manifest.sha256" && \
rm -f -- "$TRANSFER_ROOT/manifest/capsule_manifest.json" \
  "$TRANSFER_ROOT/manifest/capsule_manifest.sha256"
```

- Positional manifest hash (uppercase, verbatim): `61F8182BE31830ED4A897DE0B2564085AD7BE05E826AFC65E9B6A0EBF3D15097`. `init` also enforces manifest bytes = 18311, seal bytes = 88, seal sha256 = `A3D38D6E36417530BBFBDE7791E9BEE4BF16FF65306686AC45D97B12964E5D55`.
- Preconditions: `provision_status=STAGING_BUCKET_READY_NO_COMPUTE`, `staging.status=PRIVATE_BUCKET_READY_NO_COMPUTE`. `init` refuses to run twice (any preexisting local/S3 manifest or seal → new `CAS_RUN_ID`).
- The `&&` chaining deletes the local copies **only if `init` succeeds**. If the manifest/seal are already uploaded (`capsule.status=MANIFEST_SEALED_TRANSFER_FILES_PENDING`), skip `init` and go straight to 4b.

### 4b — `03 object` loop (×12) then `03 verify` all 14

For **each** of the 12 relative paths printed by the `jq` list, run the block below once — replacing `NEXT_RELATIVE` with exactly one printed path. One file at a time is mandatory (chunk basenames like `part-0000.bin` recur across artifacts; staging two at once overwrites the wrong file).

```bash
export STATE_MANIFEST="$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/capsule-upload/capsule_manifest.json"
jq -r '(.support_files[].relative_path),(.artifacts[].parts[].relative_path)' "$STATE_MANIFEST"
export NEXT_RELATIVE='replace/with/one/printed/relative_path'
export UPLOADED_BASENAME="$(basename "$NEXT_RELATIVE")"
test ! -e "$TRANSFER_ROOT/$NEXT_RELATIVE"
test -f "$HOME/$UPLOADED_BASENAME"
mkdir -p -- "$(dirname "$TRANSFER_ROOT/$NEXT_RELATIVE")"
mv -n -- "$HOME/$UPLOADED_BASENAME" "$TRANSFER_ROOT/$NEXT_RELATIVE"
bash 03_upload_capsule_objects.sh object "$TRANSFER_ROOT" "$NEXT_RELATIVE" && \
rm -f -- "$TRANSFER_ROOT/$NEXT_RELATIVE"
df -B1 "$HOME"
unset NEXT_RELATIVE UPLOADED_BASENAME
# --- repeat the block above EXACTLY 12 times, once per printed relative_path ---
test "$(find "$TRANSFER_ROOT" -type f -print -quit)" = ''
bash 03_upload_capsule_objects.sh verify
```

- `03 object` takes no hash arg — it reads the sealed byte/hash row for `NEXT_RELATIVE` from the local manifest and enforces the match. `NEXT_RELATIVE` must be POSIX-relative (no leading `/`, no backslash/colon, no `.`/`..`).
- Total surface = 14 files / 1,049,741,973 bytes; transfer-file count = 12. `03 verify` re-downloads all 14 remote objects by immutable version id and re-hashes them; on success it advances `capsule.status=UPLOADED_HASH_VERIFIED_UNMATERIALIZED`.
- Resume mid-loop after any STS expiry at the next un-uploaded path — re-running `03 object` on an already-present matching object is safe.

### 4c — `03b` upload successor wrapper (last step before any compute)

```bash
test -f "$HOME/invoke_gate5_aws_full_verifier.ps1"
bash 03b_upload_successor_wrapper.sh \
  "$HOME/invoke_gate5_aws_full_verifier.ps1" \
  2501FF2487995670C45101AE1480E083B64338549859E97DF3445FF8A34D837A && \
rm -f -- "$HOME/invoke_gate5_aws_full_verifier.ps1"
```

- Positional wrapper hash (verbatim): `2501FF2487995670C45101AE1480E083B64338549859E97DF3445FF8A34D837A`; wrapper bytes must equal 141548. The legacy hash `afb3f693527c76aca8b8d014ec6d2604a3add5a90fffe01644927deb0ddc5da9` is **prohibited** in the cloud successor lane.
- Precondition: `capsule.status=UPLOADED_HASH_VERIFIED_UNMATERIALIZED` (capsule fully uploaded+verified, still no compute). On success: `materialization.wrapper_status=UPLOADED_FROZEN_UNARMED_NOT_EXECUTED`.
- A preexisting wrapper object is rejected (no overwrite) → new `CAS_RUN_ID`. **No EC2 billing has started yet.**

---

## Step 5 — Provision the inert host (`02_provision`) + materialize UNARMED (`04`)

> **▶ Before this phase: exit the child (`exit`) and rerun `00` from the operator prompt for a fresh full hour.** `02_provision` needs ≥ 3480 s of session before it creates compute — only ~2 minutes of slack — so run `02` **immediately** after `00`. This is the first billing event.

### 5a — refresh `00`, then `02_provision` (the inert host)

From the operator prompt (re-set the billing attestation, then rerun `00`):

```bash
export CAS_BILLING_ATTESTATION="ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)"
bash 00_root_bootstrap_and_assume.sh
```

Then **immediately, inside the fresh child:**

```bash
export CAS_APPLY_TOKEN="CREATE:${CAS_RUN_ID}:M7I2XLARGE"
bash 02_provision.sh
unset CAS_APPLY_TOKEN
```

- Token literal: `CREATE:${CAS_RUN_ID}:M7I2XLARGE` (tag `M7I2XLARGE`, not the dotted `m7i.2xlarge`).
- Creates one temporary `m7i.2xlarge` Windows host: SSM-only (no RDP/inbound), IMDSv2 required, two encrypted 100 GiB gp3 volumes, six-hour termination deadline (EventBridge Scheduler + LocalSystem task — **not** a guaranteed spend cap).
- On success: `provision_status=INERT_HOST_READY_NO_HARNESS_AUTHORITY`.

### 5b — refresh `00`, then `04` run (submit + poll + externally verify the receipt)

> **▶ Exit the child and rerun `00` again** — `04` run needs ≥ 3300 s of its own fresh session, and the host must still have ≥ 5 h of life.

From the operator prompt (re-set the billing attestation, then rerun `00`):

```bash
export CAS_BILLING_ATTESTATION="ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)"
bash 00_root_bootstrap_and_assume.sh
```

Then inside the fresh child:

```bash
bash 04_materialize_and_verify_unarmed.sh
```

- Submits ONE SSM `AWS-RunPowerShellScript` command (`--timeout-seconds 7320`, `executionTimeout 7200`) running the LocalSystem unarmed materializer, polls to `Success`, then re-downloads the sealed receipt by immutable version and exhaustively verifies bytes/hash/schema/runtimes (git 2.52.0 / python 3.14.0 / pwsh 7.6.4), AMI `ami-05eea18612b5be529` owner `801119661308`, volume identity, ACL, and Git topology. `provider_calls` must equal 18.
- Preconditions: `provision_status=INERT_HOST_READY_NO_HARNESS_AUTHORITY`, `capsule.status=UPLOADED_HASH_VERIFIED_UNMATERIALIZED`, `wrapper_status=UPLOADED_FROZEN_UNARMED_NOT_EXECUTED`, `receipt_sha256` empty, and `ssm_command_id` empty. **A second plain `run` is refused.**
- On success: `capsule.status=MATERIALIZED_UNARMED_EXTERNALLY_VERIFIED`, `materialization.status=PASS_UNARMED_EXTERNAL_REHASH_AND_SCHEMA`; still unarmed (`harness_authority=absent`, `harness_execution=NOT_STARTED`).
- On SSM `Cancelled/TimedOut/Failed/Cancelling`: it writes `materialize.failed.json` and dies with **no retry** — rebuild with a new `CAS_RUN_ID`.

**`04 … watch` continuation lane** — use **only** when `04` run's polling died because STS expired **while the VM-side materialization was still running** (state now has `ssm_command_id` present and `materialization.status=SYSTEM_MATERIALIZATION_RUNNING_UNARMED`, `receipt_sha256` empty). Do **not** rerun `run`. Exit, re-set `CAS_BILLING_ATTESTATION`, rerun `00` (watch needs only ≥ 600 s), then inside the fresh child:

```bash
bash 04_materialize_and_verify_unarmed.sh watch
```

`watch` re-polls the retained command id and runs the identical receipt verification; it uploads nothing and can never resubmit. If the watch session also expires, re-set `CAS_BILLING_ATTESTATION`, rerun `00`, and run `watch` again.

---

## Step 6 — Final preclaim (`05`) + EXECUTE-ONCE dispatch (`05b`) — the one irreversible claim

> **▶ Exit the child and rerun `00` for a fresh full hour.** `05` needs ≥ 3420 s of session and the host must have ≥ 18000 s (5 h) of life.
>
> **🚫 CRITICAL: do NOT refresh STS between `05` and `05b execute`.** Execute binds to the exact `AWS_SESSION_EXPIRATION` **and** the access-key-id SHA-256 that `05` recorded, and to a preclaim receipt valid for only **10 minutes**. Any intervening `00` refresh invalidates execute.

### 6a — refresh `00`, then `05` final provider/host preclaim (no authority created)

From the operator prompt (re-set the billing attestation, then rerun `00`):

```bash
export CAS_BILLING_ATTESTATION="ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)"
bash 00_root_bootstrap_and_assume.sh
```

Then inside the fresh child:

```bash
bash 05_final_provider_preclaim.sh
```

- Fresh read-only provider + Windows observations; writes an encrypted preclaim receipt. Creates no dispatch, claim, authority, wrapper task, or model action.
- Single-shot: refuses to run if `final_preclaim.status` is already set. Emits `final_preclaim.status=PASS_PROVIDER_AND_HOST_PRECLAIM_ONLY_NO_AUTHORITY`. Preclaim receipt `valid_until = observed + 600 s`.
- If the 10-minute window lapses before execute, it **cannot** be reused or replaced — abandon this `CAS_RUN_ID`, terminate compute, rebuild with a new one.

### 6b — `05b execute` (SAME session as `05` — no `00` between)

```bash
export WRAPPER_SHA="2501FF2487995670C45101AE1480E083B64338549859E97DF3445FF8A34D837A"
export MATERIALIZATION_SHA="$(jq -r '.materialization.receipt_sha256' \
  "$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/state.json" | tr '[:lower:]' '[:upper:]')"
export CAS_DISPATCH_TOKEN="EXECUTE-ONCE:${CAS_RUN_ID}:${WRAPPER_SHA}:${MATERIALIZATION_SHA}"
bash 05b_run_or_reconcile.sh execute
unset CAS_DISPATCH_TOKEN
```

- Token shape: `EXECUTE-ONCE:g5-<runid>:2501FF24…A34D837A:<UPPER materialization sha256>`.
- Installs the immutable one-hour dispatch-authority object (no replacement) and starts ONE non-admin local-`wakil` S4U execute task, then bounded-waits, records the consumed-claim boundary, and performs the terminal VM-evidence export. Session floors: ≥ 3300 s at entry, ≥ 3000 s immediately before the irreversible SSM submit; host TTL ≥ 18000 s throughout.
- The verifier can run **far longer** than one hour. The Execute bounded wait is auto-capped to `(session budget − 300 s)`. If the verifier outlives the cap, the wait ends as a **clean bounded failure with the claim already consumed exactly once** — expected, not an error.
- On terminal result: claim present → `harness_execution='CONSUMED / NO RETRY'`; wrapper returned before a claim → `'S4U WRAPPER RETURNED BEFORE CLAIM / REVIEW REQUIRED / NO AUTOMATIC RETRY'` (acceptance-ambiguous). **Either way, no automatic retry.**

> **🚫 NEVER rerun `execute`.** There is no clean re-run of a consumed or acceptance-ambiguous claim. If it did not reach the terminal export, resume via the observe/export lanes below — never `execute`, never `reconcile`-first.

### 6c — observe / reconcile / export

Re-derive the two hashes after any `00` refresh (they feed every token here):

```bash
export WRAPPER_SHA="2501FF2487995670C45101AE1480E083B64338549859E97DF3445FF8A34D837A"
export MATERIALIZATION_SHA="$(jq -r '.materialization.receipt_sha256' \
  "$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/state.json" | tr '[:lower:]' '[:upper:]')"
```

`observe` is read-only (no token) and safe to run repeatedly:

```bash
bash 05b_run_or_reconcile.sh observe
```

**Normal-return path** — execute already reached its terminal VM export and state proves the one-use claim was **CONSUMED**. Reconcile is recovery-only (requires `harness_execution='CONSUMED / NO RETRY'`; never reruns the verifier), then export copies the VM evidence namespace to the private receipt prefix:

```bash
export CAS_RECONCILE_TOKEN="RECONCILE-ONLY:${CAS_RUN_ID}:${WRAPPER_SHA}:${MATERIALIZATION_SHA}"
bash 05b_run_or_reconcile.sh reconcile
unset CAS_RECONCILE_TOKEN

export CAS_EXPORT_TOKEN="EXPORT:${CAS_RUN_ID}:${WRAPPER_SHA}:${MATERIALIZATION_SHA}"
bash 05b_run_or_reconcile.sh export
unset CAS_EXPORT_TOKEN
```

**Acceptance-ambiguous path** — execute did **not** reach its terminal export (session cap hit, or S4U wrapper returned before a claim). Observe until the Execute S4U task is no longer `Running`, then export to terminalize and bind state — **without running `reconcile` first** (reconcile would die, since state is not yet `CONSUMED`):

```bash
bash 05b_run_or_reconcile.sh observe
export CAS_EXPORT_TOKEN="EXPORT:${CAS_RUN_ID}:${WRAPPER_SHA}:${MATERIALIZATION_SHA}"
bash 05b_run_or_reconcile.sh export
unset CAS_EXPORT_TOKEN
```

Only if this guarded export flips state to `CONSUMED / NO RETRY` does the normal-return `reconcile` above become permissible afterward. If export cannot terminalize to `CONSUMED`, stop — this run is done; rebuild with a new `CAS_RUN_ID` if a clean attempt is needed. If STS expires during any lane, exit to the operator prompt, re-set `CAS_BILLING_ATTESTATION`, rerun `00`, re-derive the two hashes, resume `observe`/`export` — **never `execute`.**

---

## Step 7 — Export receipts (`06`) + teardown (`07`) + root cleanup (`99`)

> **▶ Exit the child and rerun `00` for a fresh session before `06`/`07`.** They have no minimum-session floor but need a live session; if it expires mid-run, exit, re-set `CAS_BILLING_ATTESTATION`, rerun `00`, rerun the script (subject to `06`'s export-tree guard).

### 7a — refresh `00`, then `06` export receipts

From the operator prompt (re-set the billing attestation, then rerun `00`):

```bash
export CAS_BILLING_ATTESTATION="ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)"
bash 00_root_bootstrap_and_assume.sh
```

Then inside the fresh child:

```bash
df -B1 "$HOME"
du -sb "$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID" 2>/dev/null || true
bash 06_export_receipts.sh
```

- Downloads + hashes every versioned object under `receipts/$CAS_RUN_ID/` (plus the immutable dispatch-authority object when present) into a fixed, no-reuse export tree, then packages `cas-g5-${CAS_RUN_ID}-receipts.tar.gz`.
- **Export-tree guard:** hard-refuses if `.../export` already exists — preserve/review it; there is no in-place rerun (clean re-export needs a new `CAS_RUN_ID`).
- **Fresh-evidence requirement:** if `harness_execution != NOT_STARTED`, `06` demands a fresh terminal VM-evidence observation bound to the current state. If stale/absent, run `05b observe` then `export` (Step 6c) first, then `06`.
- On success: `receipt_export.status=EXPORTED_AND_EXTERNALLY_REHASHABLE`, and `receipt_export.archive_sha256` is set. **Copy the `.tar.gz` and its `.sha256` outside CloudShell and re-hash the copy** — that lowercase digest becomes `CAS_RECEIPT_SHA256` for `07 full`. Files land at:
  - `$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/export/cas-g5-${CAS_RUN_ID}-receipts.tar.gz`
  - `$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/export/cas-g5-${CAS_RUN_ID}-receipts.tar.gz.sha256`

### 7b — `07 teardown compute` (stop EC2 billing)

Terminate the exact per-run instance + its DeleteOnTermination volumes + the termination schedule; retain the S3 bucket and IAM support resources so receipt review can continue.

```bash
export CAS_TEARDOWN_TOKEN="TERMINATE:${CAS_RUN_ID}"
bash 07_teardown.sh compute
unset CAS_TEARDOWN_TOKEN
```

**Emergency destructive override** (stop billing, knowingly forfeit VM evidence — only if you cannot export first):

```bash
export CAS_ACK_EVIDENCE_LOSS="TERMINATE_WITH_UNEXPORTED_VM_EVIDENCE:${CAS_RUN_ID}"
export CAS_TEARDOWN_TOKEN="TERMINATE:${CAS_RUN_ID}"
bash 07_teardown.sh compute
unset CAS_ACK_EVIDENCE_LOSS CAS_TEARDOWN_TOKEN
```

- Fails closed on evidence: if `harness_execution != NOT_STARTED` and VM evidence is not uploaded, compute teardown dies unless the ack guard is set. **So run `06` (after `05b`) before stopping compute.**
- On success: `compute_teardown_status=INSTANCE_TERMINATED_DELETE_ON_TERMINATION_VOLUMES_ABSENT`, `teardown_status=COMPUTE_ONLY_COMPLETE_SUPPORT_RESOURCES_RETAINED`.

### 7c — `07 teardown full` (zero per-run footprint)

Delete instance + volumes, termination schedule + group, watchdog DLQ, all run-tagged security groups, and the ephemeral bucket with ALL versions/delete-markers/multipart uploads. IAM roles/profile are retained for `99`.

Choose **exactly one** evidence-disposition lane; unset incompatible ACK guards first (as shown).

**Normal lane — verified local receipt archive (from `06` + external re-hash):**

```bash
export CAS_RECEIPT_ARCHIVE="$HOME/cas-g5-cloudshell-state/$CAS_RUN_ID/export/cas-g5-${CAS_RUN_ID}-receipts.tar.gz"
export CAS_RECEIPT_SHA256="lowercase_digest_from_the_externally_rehashed_copy"
export CAS_TEARDOWN_TOKEN="DELETE:${CAS_RUN_ID}"
bash 07_teardown.sh full
unset CAS_TEARDOWN_TOKEN CAS_RECEIPT_ARCHIVE CAS_RECEIPT_SHA256
```

**Alt lane A — no authority or execution ever started:**

```bash
unset CAS_RECEIPT_ARCHIVE CAS_RECEIPT_SHA256 CAS_ACK_EVIDENCE_LOSS_FULL CAS_ACK_AUTHORITY_EVIDENCE_LOSS_FULL
export CAS_ACK_NO_RECEIPTS="DELETE_EMPTY_OR_FAILED_RUN:${CAS_RUN_ID}"
export CAS_TEARDOWN_TOKEN="DELETE:${CAS_RUN_ID}"
bash 07_teardown.sh full
unset CAS_ACK_NO_RECEIPTS CAS_TEARDOWN_TOKEN
```

**Alt lane B — VM evidence was deliberately forfeited:**

```bash
unset CAS_RECEIPT_ARCHIVE CAS_RECEIPT_SHA256 CAS_ACK_NO_RECEIPTS CAS_ACK_AUTHORITY_EVIDENCE_LOSS_FULL
export CAS_ACK_EVIDENCE_LOSS_FULL="DELETE_AFTER_UNEXPORTED_VM_EVIDENCE:${CAS_RUN_ID}"
export CAS_TEARDOWN_TOKEN="DELETE:${CAS_RUN_ID}"
bash 07_teardown.sh full
unset CAS_ACK_EVIDENCE_LOSS_FULL CAS_TEARDOWN_TOKEN
```

**Alt lane C — authority upload/install was ambiguous and its evidence cannot be exported** (try `06` first to archive the provider-history proof; use this only when that export is impossible):

```bash
unset CAS_RECEIPT_ARCHIVE CAS_RECEIPT_SHA256 CAS_ACK_NO_RECEIPTS CAS_ACK_EVIDENCE_LOSS_FULL
export CAS_ACK_AUTHORITY_EVIDENCE_LOSS_FULL="DELETE_AFTER_UNEXPORTED_AUTHORITY_ATTEMPT:${CAS_RUN_ID}"
export CAS_TEARDOWN_TOKEN="DELETE:${CAS_RUN_ID}"
bash 07_teardown.sh full
unset CAS_ACK_AUTHORITY_EVIDENCE_LOSS_FULL CAS_TEARDOWN_TOKEN
```

- On success: `aws_resources_created=0`, `teardown_status=FULL_TEARDOWN_COMPLETE`. Protected bucket `cas-harness-runpod-92754088` is never touched; the default VPC and subnets are preserved. **Copy `teardown.receipt.json` + `teardown.sha256` outside CloudShell and re-hash before leaving.**

### 7d — `99` root cleanup (from the operator prompt, after full teardown)

Exit the provisioner child; from the **original operator prompt** (or account root — root is accepted here because IAM deletion needs no `AssumeRole`):

```bash
export CAS_ROOT_CLEANUP_TOKEN="DELETE-PROVISIONER:${CAS_RUN_ID}:${CAS_APPROVED_PACKAGE_SHA256}"
bash 99_root_cleanup_provisioner.sh
unset CAS_ROOT_CLEANUP_TOKEN
```

- Deletes exactly the instance profile, `cas-g5-<SUFFIX>-ec2-role`, `cas-g5-<SUFFIX>-scheduler-role`, and `cas-g5-<SUFFIX>-provisioner` (only if `CasRunId`/`PackageSha256` tags match and no unexpected policies). Fails closed if any per-run non-IAM resource still exists — run full teardown first.
- Idempotent: on any transient hiccup, rerun `99` with the same tokens. Receipt at `.../root-cleanup/root-cleanup.receipt.json` (+ `.sha256`) — copy and externally re-hash before leaving CloudShell.

---

## Recovery lane — bootstrap-only `99` (early abort, only IAM objects exist)

Use this exact lane **only when `00` succeeded but `01` never completed / never wrote `state.json`** — i.e. just the temporary IAM objects exist and no per-run provider resource was created. Exit the child; from the operator prompt (or root):

```bash
export CAS_ACK_BOOTSTRAP_ONLY="NO_MAIN_PREFLIGHT_OR_PROVIDER_RESOURCES:${CAS_RUN_ID}"
export CAS_ROOT_CLEANUP_TOKEN="DELETE-PROVISIONER:${CAS_RUN_ID}:${CAS_APPROVED_PACKAGE_SHA256}"
bash 99_root_cleanup_provisioner.sh
unset CAS_ACK_BOOTSTRAP_ONLY CAS_ROOT_CLEANUP_TOKEN
```

- `CAS_ACK_BOOTSTRAP_ONLY` is required **precisely because `state.json` is absent**. If `state.json` exists and recorded created resources (`aws_resources_created != 0`), this is the wrong guard — do full teardown first (that path instead demands `teardown_status == FULL_TEARDOWN_COMPLETE`).
- `99` fails closed if any per-run bucket/instance/volume/ENI/SG/Scheduler/DLQ still exists. Re-export the pinned vars first if this is a fresh operator prompt: `CAS_RUN_ID`, `CAS_EXPECTED_ACCOUNT_ID`, `CAS_APPROVED_PACKAGE_SHA256`.

---

## Continuation-lane quick reference

| Situation | Resume with | Never |
|---|---|---|
| STS expired between phases (nothing submitted mid-flight) | exit child → re-set `CAS_BILLING_ATTESTATION` → rerun `00` (same `CAS_RUN_ID`, same exported vars) → resume the phase | — |
| `04` run polling died while VM materialization still running (`ssm_command_id` set, `receipt_sha256` empty) | `04 … watch` | rerun `04` plainly |
| `05b execute` reached terminal export, state = `CONSUMED / NO RETRY` | `05b observe` → `05b reconcile` → `05b export` | rerun `execute` |
| `05b execute` returned acceptance-ambiguous (cap hit / wrapper returned before claim) | `05b observe` (until Execute not `Running`) → `05b export`, **no reconcile first** | rerun `execute`; `reconcile` first |
| Session died during `06`/`07` (CloudShell-local, nothing submitted) | re-set `CAS_BILLING_ATTESTATION` → rerun `00` → rerun the script (mind `06`'s export-tree guard) | — |

**Loud rule:** never rerun `execute`, never rerun `04` against a consumed/completed materialization, and never resubmit a VM-side command that outlived its session. The one-use claim is consumed exactly once — export what exists, terminate compute, and rebuild with a **new `CAS_RUN_ID`** if a clean retry is required.

---

## Expected cost & footprint

- Roughly **~$5 of Windows On-Demand** for one `m7i.2xlarge` host over the short verifier window (no RDP/inbound, SSM-only, six-hour termination deadline as a backstop — not a hard cap; tear down as soon as work ends).
- After `07 full` + `99`: **zero per-run footprint** — instance, both EBS volumes, termination schedule/group, watchdog DLQ, all run-tagged security groups, and the ephemeral bucket (all versions) deleted; IAM roles/profile removed by `99`. Protected bucket `cas-harness-runpod-92754088` and the default VPC are untouched.

**Identities to re-verify externally before trusting any run:**
- `CAS_APPROVED_PACKAGE_SHA256` (= sha256 of `PACKAGE.sha256`): `525365c4035ba644fb39793c88cbfcdda09ddad7fa3a84317a3c6e37e9bd61e1`
- `CAS_PACKAGE_ARCHIVE_SHA256` (reviewed archive digest): `a843f37e165e00a465a6dc633b7e299986a02a510ab8b0bb0dff501e33b0c528`

Account `807562639912` · region `us-west-2` · operator `arn:aws:iam::807562639912:user/cas-g5-operator`.

---

## Verification note

Adversarial pass corrected two confirmed divergences, both verified against the real scripts:

1. **`04` SSM failure status list** (`04_materialize_and_verify_unarmed.sh:178`): the failure `case` is `Cancelled|TimedOut|Failed|Cancelling`; the runbook omitted `Cancelling`. Step 5b now reads `Cancelled/TimedOut/Failed/Cancelling`.
2. **`CAS_BILLING_ATTESTATION` staleness on later `00` reruns** (`00_root_bootstrap_and_assume.sh:32-33`): `00` re-validates the attestation against `date -u '+%Y-%m-%d'` on **every** invocation, so a run crossing UTC midnight would abort a later `00`. Added a Session-discipline rule and prepended `export CAS_BILLING_ATTESTATION="ACTIVE_DEFAULT_PAYMENT_METHOD_CONFIRMED_$(date -u +%Y-%m-%d)"` to every later `00` rerun block (Steps 5a/5b/6a/7a, the `04 … watch` and continuation lanes, and the quick-reference table).

All other report items were rejected as non-divergences (the "≥5h host life at 04 is advisory" and "`00` refresh inserted between `02` and `04`" notes were explicitly confirmed by the reports as faithful to the README / a safer reading, not errors). No token, hash, byte count, session floor, or status string was altered.