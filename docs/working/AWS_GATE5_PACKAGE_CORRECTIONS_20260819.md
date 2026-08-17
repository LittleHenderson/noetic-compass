# Gate 5 AWS package — defect findings + corrections (20260819)

## Headline

The frozen package **`aws_cloudshell_unarmed_20260818`** (identity
`525365c4035ba644fb39793c88cbfcdda09ddad7fa3a84317a3c6e37e9bd61e1`), previously
recorded as **"triple-audited GO / P0=0 / P1=0"**, **cannot run to completion.** Its
provision → schedule-arming → preclaim path contains multiple runtime defects that all
three prior static audits and all three prior live attempts missed — because every prior
live attempt died at **bootstrap** (root/AssumeRole, then role-chaining), so the
provisioning path was **never once exercised**. The "GO" status certified a path that had
never run.

This was discovered while executing the verification live (in a WSL-Ubuntu lane against
the real aws CLI, operator `cas-g5-operator`, account `807562639912`). Total AWS spend
during discovery: **~$0.04** (one m7i.2xlarge for ~2–3 min, auto-terminated by the
package's own fail-safe). Zero footprint after cleanup.

## How the defects were found

- **Live**: FLAG-1 (dry-run rejected the flag), TRUST-1 (CreateSchedule rejected the
  role), and the scheduler-resource-scope gap (teardown AccessDenied) surfaced one at a
  time on live compute.
- **Multi-agent static audit** (12 agents: 8 per-script auditors + 1 cross-checker + 3
  adversarial verifiers) then swept the entire provision/materialize/execute/teardown
  path, validating every `aws` flag against the real CLI and mapping every call's required
  IAM action against what each role's policy actually grants. It **confirmed** FLAG-1 and
  TRUST-1 (unanimous 3/0) and found a **new** defect, RUNTIME-1, that no prior attempt had
  reached. It correctly noted the scheduler *action* is granted (so "no missing
  permission"); the live evidence showed the defect is a *resource-scope* mismatch, which
  the action-level check could not see.

## The four defects and their fixes

| ID | File : line | Defect | Fix applied |
|---|---|---|---|
| **FLAG-1** (blocker) | `02_provision.sh:554` | `--no-disable-api-termination` — not a valid `aws ec2 run-instances` flag in any aws CLI v2 (the `--no-…` idiom exists only for DisableApiStop). CLI rejects it at arg-parse, so the authorization dry-run never returns `DryRunOperation` and provisioning dies before any billed call. | → `--enable-api-termination` (same effect: DisableApiTermination=false). Line 555 `--no-disable-api-stop` left unchanged — it is valid. |
| **TRUST-1** (blocker) | `00_root_bootstrap_and_assume.sh:~476` | Scheduler execution-role trust pairs `aws:SourceAccount` with an `ArnLike aws:SourceArn = schedule/<group>/*` condition. EventBridge Scheduler's creation-time role-assumability check does not reliably populate `aws:SourceArn`, so `CreateSchedule` fails ("must allow AWS EventBridge Scheduler to assume the role") and provision aborts. | Removed the `ArnLike aws:SourceArn` clause; kept `StringEquals aws:SourceAccount` (retains confused-deputy protection). |
| **RUNTIME-1** (major) | `05_final_provider_preclaim.sh:229` | `aws ssm wait command-executed` uses botocore's fixed waiter (delay 5 × 20 attempts ≈ 100 s ceiling, no override), but the same script gives the on-VM probe a 120 s deadline plus SSM pickup/module-import overhead. On the slow path the waiter times out and preclaim fails under `set -e` even though the command would have succeeded — intermittent. | Replaced with a bounded 300 s poll on `get-command-invocation` (the package's own `05b:51` pattern), succeeding on `Success`, dying on terminal failure states, using already-granted `ssm:GetCommandInvocation` (no IAM change). |
| **IAM-SCOPE** (major, live-observed) | `00_root_bootstrap_and_assume.sh:350` | Provisioner policy grants `scheduler:DeleteSchedule` scoped to the exact schedule ARN `schedule/<group>/<name>`, but `DeleteScheduleGroup` cascades and requires the action on `schedule/<group>/*`; teardown hit AccessDenied on `schedule/<group>/*`. | Broadened the schedule resource from `…/<schedule>` to `…/*` (still scoped to the run's group). |

## Corrected package identities

- Package dir: **`aws_cloudshell_unarmed_20260819`**
- Archive: **`aws_cloudshell_unarmed_20260819.tar.gz`**, 91,722 B, SHA-256
  **`0d81552669bb1b57cc27e21f507ca9df4e36eb9b909abbb1862734b92ac786dc`**
- Package identity (SHA-256 of `PACKAGE.sha256`):
  **`40a6de66b22076b98cd737c8e3ebbe3d0f6cf0881b400fa9f64f7269122de814`**
- Delta vs 20260818: exactly two files edited (`00_…assume.sh`, `02_provision.sh`,
  `05_final_provider_preclaim.sh` — three files), plus the regenerated `PACKAGE.sha256`.
  Every edit is `bash -n`-clean and the corrected package passes its own
  `sha256sum -c PACKAGE.sha256` (18/18).
- Durable backup: `D:\tksCAS-archive\project_coherence_gate5_corrected_package_20260819\`.

## Status caveat (important)

`20260819` is **corrected and self-verifying, but NOT re-audited** by the independent
triple-audit flow. Two of the fixes (FLAG-1, TRUST-1) are empirically validated against
the real AWS API; RUNTIME-1 and IAM-SCOPE are reasoned + live-corroborated. Before
`20260819` earns a "GO" label it should go through the same independent audit that
`20260818` did — this time with the provisioning path actually exercised. The materialize
→ execute → export path is *also* previously-untested; further defects there remain
possible and will be recorded here if the live run surfaces any.

## Live-run result

_(in progress — updated when the corrected run completes)_
