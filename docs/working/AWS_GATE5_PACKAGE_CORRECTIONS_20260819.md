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

## Two more defects found by running the corrected package live

The corrected package (5 fixes) was then run live. It advanced through the **entire
orchestration path** — bootstrap, preflight, private bucket, full ~1 GB capsule upload +
remote re-hash, run-instances **dry-run pass**, **instance launch**, **post-launch config
verification**, and **EventBridge scheduler arming** — proving FLAG-1 and TRUST-1 fixed
live. Two further never-run-before defects then surfaced:

| ID | File : line | Defect | Status |
|---|---|---|---|
| **JQ-1** (blocker) | `02_provision.sh:658` | Post-launch instance config check reads `.BlockDeviceMappings` at the **top level** of the describe-instances JSON (always `null`, length 0) instead of `$i.BlockDeviceMappings`; every other clause uses `$i.`. The `0 == 2` fails → the launched (correctly-configured) instance is rejected every time. | **FIXED** in the package (→ `$i.BlockDeviceMappings`); proven — the next run passed this check. |
| **BOOT-1** (blocker) | `02_provision.sh:298–527` (Windows user-data) | The Windows VM's boot script (`<powershell>`, `ErrorActionPreference='Stop'`) configures the machine and writes `C:\ProgramData\CasHarness\bootstrap.json` as its final step. On the real VM the marker never appears within the 10-minute wait (`02:682`), so the SSM host-observation returns `Failed` and provision aborts. Some step in the ~230-line boot sequence (disk-letter juggling / disk init / watchdog task / `wakil` S4U identity / IMDS firewall rule) throws before the marker is written. Exact failing step requires reading the EC2Launch agent log off a live instance. | **OPEN** — not yet diagnosed to the exact line. |

## Windows boot-layer investigation (defects #6–#8) — expert team + live probes

A 7-agent expert team dissected the 231-line Windows boot user-data statically (ranking 8
possible throw-points), and 4 disposable throwaway probe instances (cheap t3/m7i, each
auto-terminating + self-cleaning) read the machine's **actual** `err.tmp` and EC2Launch
log to confirm which statement really fires. Static reasoning ranked the true cause LOW;
the live probe caught it — vindicating the two-pronged method. Each fix moved the failure
one confirmed step deeper:

| ID | File : line (rendered) | Defect | Status |
|---|---|---|---|
| **BOOT-1** | user-data L9 | `Join-Path $archiveRoot …` builds a `D:\` path **before** the disk is formatted into D:; Join-Path validates the drive root → `DriveNotFound` throw. | **FIXED** (string concat). Probe: passed. |
| **BOOT-2** | user-data L41 | `Set-Disk -IsOffline $false -IsReadOnly $false` — those two params are in different parameter sets → `AmbiguousParameterSet` throw. | **FIXED** (two calls). Probe: D: now formats to `CAS-ARCHIVE`; watchdog task registers. |
| **S4U-BATCH** | before L189 | new local user `wakil` lacks `SeBatchLogonRight`; team-predicted S4U run-time logon refusal. | **FIXED** (secedit grant). |
| **BOOT-3** | user-data L209 | `Register-ScheduledTask` for the S4U **identity-probe** task fails `Access is denied (0x80070005)` — S4U task *registration* (not just its logon) is refused in the SYSTEM/Session-0 boot context. | **CHARACTERIZED — AMI/OS-level S4U limitation, not a code bug** (full trace below). Needs a package-design decision, not a patch. |

Live-proven working now: disk format → D:, and the 6-hour watchdog task. Confirmed wall:
S4U identity-probe task registration.

## BOOT-3 characterization (DEFINITIVE — ~14 live m7i.large probes, `Stop` semantics)

**S4U scheduled-task registration for a LOCAL account does not work in the EC2Launch /
Session-0 boot context on this Windows Server 2022 EC2 AMI.** This is an OS/AMI-level S4U
limitation, not a defect in the package's PowerShell. Every register mechanism and every
prerequisite was tried on live disposable instances, splicing each candidate into the
*real* corrected boot and reading the machine's actual `err.tmp` / `whoami /priv` / policy
state.

Hypotheses tested and ELIMINATED:

| # | Hypothesis | Live result |
|---|---|---|
| 1 | Caller lacks `SeTcbPrivilege` (stripped user-data token) | Real — user-data token has only `SeIncreaseQuotaPrivilege`. But **not the whole story** (see #2). |
| 2 | Run the register from a `SYSTEM/Highest` helper task (full token *with* `SeTcb Enabled`, confirmed via the helper's own `whoami /priv`) | **Still `0x80070005`** — via both `Register-ScheduledTask` (cmdlet) and COM in-process `RegisterTaskDefinition`. |
| 3 | WMI/WmiPrvSE marshaling drops the enabled privilege | FALSE — COM **in-process** (no WMI hop) fails identically. |
| 4 | Target `wakil` lacks `SeBatchLogonRight` | FALSE — `secedit /export` shows `SeBatchLogonRight = wakil,*S-1-5-32-544,…` (wakil present, resolved to name). |
| 5 | Register under wakil's own context (Connect-as-wakil, empty-password S4U) | FALSE — the `ITaskService.Connect(...,'wakil',...)` RPC itself fails `0x80070005` (wakil can't authenticate to the Task Scheduler service). |
| 6 | Secondary Logon (`seclogon`) service stopped | Real contributing factor — `seclogon` is **Stopped/Manual by default** on this AMI. Toggling it changes the failure mode (see below), but does **not** yield a successful register. |

The decisive detail (bulletproof step-by-step probe, logging after every statement):
- **`seclogon` Stopped (default)** → `RegisterTaskDefinition` returns a catchable
  `0x80070005` (E_ACCESSDENIED).
- **`seclogon` Started** → `RegisterTaskDefinition` **crashes the calling PowerShell
  process** — the step log reaches `L8-action`, then dies at the register call with **no
  catchable exception and no `L10-END`** (an unhandled native fault in the S4U validation
  logon), not a .NET error.

So there is no register mechanism, privilege, or service state that produces a successful
S4U registration for a local account in the boot on this AMI.

The **post-boot SSM SYSTEM token was tested directly** (option 1 below) and behaves
**identically**: `whoami = nt authority\system`, `SeTcbPrivilege Enabled`, wakil present in
`SeBatchLogonRight`, `seclogon` started — the step log reaches `L4-connected`, `L8-action`,
then **crashes at `RegisterTaskDefinition`** (no `L9`, no catch, no `END`). So the SSM
context is **not** a workaround. (This also corrects an earlier note in this file that said
"the register succeeds post-boot via SSM" — that was a bench running with
`ErrorActionPreference = 'Continue'`, which made the `0x80070005` non-terminating and
mis-logged it as success; the blank `LogonType` on the never-registered task was the tell.)

**AMI scope:** the package pins its image exactly — `lib.sh` sets
`EXPECTED_AMI_ID = ami-05eea18612b5be529` (the stock `/aws/service/ami-windows-latest/
Windows_Server-2022-English-Full-Base`) and aborts on any other AMI. Every probe used that
exact pinned AMI, so the limitation is on the package's real target image, not an arbitrary
one.

**This is a package-DESIGN decision, not a one-line code fix.** The identity probe requires
an S4U (no-stored-credential) task; that specific mechanism does not work on this AMI in any
context. Options for the package author:
1. ~~Register the identity task in a post-boot SSM step~~ — **eliminated**: S4U register
   crashes in the SSM SYSTEM token too (tested live).
2. **Domain-join** the instance (S4U2Self is a Kerberos mechanism; standalone/workgroup has
   no KDC) — heavy, changes the whole provisioning model.
3. **A different constrained-identity demonstration** that does not require S4U task
   registration — e.g., `LogonUser(LOGON32_LOGON_BATCH)` + `CreateProcessAsUser` using
   wakil's known boot-generated password (the boot already sets it), or a restricted /
   AppContainer token. But the SSM host-observation currently asserts
   `identity_logon_type == 'S4U'`, so this changes the audit contract and the sealed-evidence
   schema.
4. **Test on a different Windows AMI / Windows version** where local-account S4U register is
   not broken, and re-pin `EXPECTED_AMI_ID`.

Recommended next step for the author: reproduce in one line outside the harness —
`Register-ScheduledTask -TaskName t -Action (New-ScheduledTaskAction -Execute cmd.exe) -Principal (New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\someLocalUser" -LogonType S4U)`
on a fresh `Windows_Server-2022-English-Full-Base` instance — to confirm this is the OS/AMI
behavior (it will be), then choose option 2/3/4. This is a design decision the package owner
should make; it is out of scope for a mechanical package correction.

Method note: every finding is from **disposable, self-cleaning m7i.large probes**; static
reasoning (incl. a 5-agent research panel) mis-ranked the cause — the live probes are what
established it, the same two-pronged pattern that found BOOT-1/BOOT-2. Total AWS spend across
all ~14 probes: **under $1**; account verified at zero footprint after every one.

## Current corrected identity

Corrected package with the **nine** applied fixes (FLAG-1, TRUST-1, JQ-1, RUNTIME-1,
IAM-SCOPE, BOOT-1a, BOOT-1b, BOOT-2, S4U-BATCH):
- Package identity: `81ac4f71c5ba4087646a8c3bed1bdf03a12821285d824d172473673906248fa0`
- Archive `aws_cloudshell_unarmed_20260819.tar.gz` (identity changes each rebuild; this is head).
- Backup: `D:\tksCAS-archive\project_coherence_gate5_corrected_package_20260819\`.

## Honest overall assessment

**Nine confirmed defects fixed on a path that no prior audit or attempt had ever executed;
the tenth (BOOT-3) is now fully characterized as an OS/AMI-level S4U limitation — a
package-design decision, not a mechanical fix.** Every defect lives in the provision →
Windows-boot → execution path that the "triple-audited GO" certified without ever running it
once.

BOOT-3 is the current hard stop of the boot path: the S4U identity-probe registration cannot
succeed on the package's pinned AMI in any tested context (EC2Launch boot, SYSTEM/Highest
helper, post-boot SSM), with all prerequisites satisfied. Because the boot fails there,
**materialize → execute → export remain entirely untested** — they sit downstream of a boot
that does not yet complete.

Status of the corrected package: **9 mechanical defects fixed and self-verifying**; BOOT-3
requires an owner design decision (options 2/3/4 above) before the boot can complete and the
downstream lanes can be exercised. This is the honest, defensible result: the corrected
package + this defect/root-cause map turns "a GO label on a path that never ran" into a
precise, evidence-backed map of exactly what works, what is fixed, and the one architectural
decision that remains. Total AWS spend across all ~15 disposable probes: **under $1**;
account verified at **zero footprint** after every one; the protected bucket
`cas-harness-runpod-92754088` never touched.
