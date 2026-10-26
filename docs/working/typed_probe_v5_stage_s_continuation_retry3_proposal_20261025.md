# v5 Stage S retry 3 — startup hash-pin repair proposal

**Date:** 2026-10-25  
**Status: AUTHORIZED FOR ONE ATTEMPT; PRE-LAUNCH GATES OPEN.** Owner response received 2026-10-25T10:23:52Z. This covers exactly one retry 3 launch under the limits below; it does not authorize Stage C.

## What retry 2 showed

Retry 2 was 🟥 FAILED / WITHDRAWN. AWS accepted one launch, but the instance exited with code 1 during startup before PyTorch, Transformers, GPU readiness, Stage S, or model calls. It produced **0/640** new labels, **0** Claude inference batches, and **0** new Qwen replies. Cleanup passed; logs and receipts remain available in `typed_probe_v5_stage_s_continuation_retry2_result_20261025.md`.

A package defect is confirmed: the retry 2 startup script pinned runner SHA-256 `53eaffa8e9d10556f7704ab759ed5eaf4142867dae5a5099abed1df27aacd046`, while its frozen runner file hashes to `43b96097b75e718c52a4727263467a35885305c3bd58d22a1c1e5580eb10333d`. The retained startup log does not show the exact failing command, so the mismatch is a definite defect but not a proven immediate cause.

## Exact retry 3 repair

This separate package corrects the startup pin to the frozen runner SHA-256 and adds a local consistency gate to `prepare` and `launch`. The gate compares the startup script's pinned SHA-256 with the actual frozen runner file before any AWS call. The startup script itself is included in the frozen package hashes. If this check fails, preparation stops before AWS setup or instance launch.

The startup still uses the approved AWS Python environment and verifies Transformers `4.57.1` inside the PyTorch environment. It refuses to fall back to the system Python. Retry 2 did not reach those checks, so retry 3 must verify them before it starts Stage S.

## One proposed attempt

- **Run ID:** `typed-probe-v5-stage-continuation-retry3-20261025`.
- **Compute:** exactly one On-Demand `g5.2xlarge` in `us-west-2c`; one `RunInstances` request, no automatic retry, and no alternate zone.
- **Saved inputs:** recheck the pinned 1,920 replies and 1,280 Mistral labels. Add only the missing 640 Mistral labels. Generate no Qwen replies.
- **Time limits:** Stage S maximum 3,000 EC2 seconds; runner guard 2,500 seconds; scheduled stop at 2,700 seconds; hard stop at 2,900 seconds.
- **Combined EC2 limit:** recorded use before retry 3 is **7,575/10,800 seconds**, including the 83-second retry 2 instance. A 3,000-second attempt projects **10,575/10,800 seconds**, leaving **225 seconds**.
- **Watchdog:** reuse the immutable watchdog proof already pinned in the package; new watchdog proof compute is 0 seconds. Cumulative watchdog use remains **342/420 seconds**, leaving **78 seconds** unused. Fresh direct and scheduled no-target checks with the retry 3 run ID must pass before launch.
- **AWS cost cap:** **US$5.00** all-in. The last refreshed maximum-scenario estimate was **US$3.708043703703703703703703704**. Refresh it after any approval and before preparation and again immediately before launch; do not launch if it exceeds US$5.00. This is an estimate, not a settled invoice.
- **Claude cap:** Stage S upper bound **US$4.249728**; total project cap **US$10.00**. Retry 2 submitted no Claude inference batches. Count and reserve every request before submission; do not retry an unconfirmed batch.
- **Stage C:** **NOT AUTHORIZED.** Its 30 human examples and minimum 24/30 panel match still require completion and separate authorization.
- **Cleanup:** terminate the instance and remove only retry 3's disk, schedules, secure parameter, Lambda, profile, and IAM roles. Preserve S3 evidence.

## Before any future launch

After new owner authorization, setup must recheck account identity, live price, saved source versions and hashes, empty run prefix, IAM simulation (including exact pinned-version allows and out-of-scope denies), API key type and run tag, the reused watchdog proof, fresh no-target smokes, and the corrected bootstrap hash gate. Launch must repeat its live price, source, watchdog, secret, subnet, security-group, capacity, and no-existing-instance checks immediately before the one launch call.

**Owner approval received 2026-10-25T10:23:52Z**

OWNER RESPONSE (verbatim): `yes; GO — approve one Stage S retry 3 with the startup hash-pin correction under docs/working/typed_probe_v5_stage_s_continuation_retry3_proposal_20261025.md.`

The owner explicitly approved one Stage S retry 3 attempt. The response omitted the `AUTHORIZED:` prefix requested by the draft; the scope and requested action match exactly. Stage C remains NOT AUTHORIZED. All live pre-launch gates remain mandatory.
## Post-approval package integrity correction (2026-10-25)

The live preflight found that the saved watchdog proof matched the tested watchdog source, but the retry 3 copy had Windows line endings and therefore a different byte hash. The watchdog file is restored byte-for-byte from retry 2, the source used by the pinned passing proof; its behavior is unchanged. The startup shell script had Windows line endings, so its Linux shebang could be read incorrectly. It is now stored with Unix line endings. The setup hash pins below were updated and rechecked. Run ID, inputs, limits, approval scope, and one-launch rule are unchanged.

