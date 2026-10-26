# v5 Stage S retry 2 result — 2026-10-25

**Status: 🟥 FAILED / WITHDRAWN.** The one authorized Stage S attempt was accepted by AWS, then stopped during startup before the Stage S runner began. The failed attempt is retained in the record. No second launch is authorized by the consumed one-attempt approval.

## Exact AWS receipt

- Run ID: `typed-probe-v5-stage-continuation-retry2-20261025`
- Instance: `i-069472ad4637e887b`, `g5.2xlarge`, `us-west-2c`
- RunInstances request ID: `b129579e-4a18-42b1-9e66-7cf4c0d186ab`
- CloudTrail launch event: `2026-10-25T09:51:19Z`
- CloudTrail termination request: `2026-10-25T09:52:42Z`, request `a7037483-7877-4bcd-a03a-76b26ca27ad5`
- Observed EC2 time: **83 seconds**. This is the observed launch-to-termination interval, not a settled invoice.
- Maximum AWS scenario estimate: **US$3.708043703703703703703703704**, under the **US$5.00** cap. The estimate is not the final billed amount.
- EC2 accounting: prior recorded use **7,492 seconds** + this attempt **83 seconds** = **7,575/10,800 seconds**, leaving **3,225 seconds**.

## What happened

AWS downloaded part of the frozen startup package. The bootstrap exit receipt records `exit_code=1` at `2026-10-25T09:52:39Z`. The retained startup log ends before any PyTorch, Transformers, or GPU readiness result and before the message that starts the Stage S continuation. The runner did not begin.

The package has a **confirmed hash mismatch**: `user_data_stage_s.sh` expects runner SHA-256 `53eaffa8e9d10556f7704ab759ed5eaf4142867dae5a5099abed1df27aacd046`, while the frozen `stage_s_continuation.py` is `43b96097b75e718c52a4727263467a35885305c3bd58d22a1c1e5580eb10333d`. If startup reached the check at `user_data_stage_s.sh` line 112, that check would exit with code 1. The saved log ends before that line, so this is a confirmed defect and a plausible cause, but the exact failing command is **not proven**.

## Stage S outputs

- New Mistral labels: **0/640**.
- Claude inference batches: **0 submitted**; no batch-arm receipts or batch IDs exist in this run prefix.
- New Qwen replies: **0**.
- Stage S result manifest: **not produced**.
- Stage C: **NOT AUTHORIZED**.

The run prefix retains the startup log, exit record, launch receipts, and frozen inputs. No Stage S model output was produced.

## Cleanup

**CLEANUP_PASS.** AWS confirmed one instance terminated, **0** run-tagged EBS volumes remaining, both schedules deleted or absent, the temporary secure parameter deleted, the watchdog Lambda deleted, the instance profile deleted, and all three run-specific IAM roles deleted. The S3 evidence bucket and run records were preserved.

## Required before any later attempt

Correct the startup runner hash and add a pre-launch consistency check that compares the startup script's pinned hash with the frozen runner file. Keep the correction in a new, separate package so this failed package and its receipts remain unchanged. A new Stage S launch would require a new one-attempt owner authorization. No Stage C work is authorized.
