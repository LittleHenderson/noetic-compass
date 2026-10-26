# v5 Stage S retry 4 result

**Date:** 2026-10-25  
**Run ID:** `typed-probe-v5-stage-continuation-retry4-20261025`  
**Proposal:** [retry 4 proposal](typed_probe_v5_stage_s_continuation_retry4_proposal_20261025.md)  
**Status:** Attempt used; launch rejected; no further retry is authorized.

## Outcome

**ATTEMPT — 🟥 FAILED / WITHDRAWN.** AWS received exactly one `RunInstances` request for one On-Demand `g5.2xlarge` in `us-west-2c`. AWS rejected it with `InsufficientInstanceCapacity`. The request receipt was verified in CloudTrail at `2026-10-25T14:31:21Z`: request ID `7ce0c0f5-47f1-40c8-9fec-5a88b0bfc1cb`, event ID `2c76a08b-e223-4c23-8e4f-7c1130bd8fc6`, error `Server.InsufficientInstanceCapacity`. The SDK was limited to one total attempt. No EC2 instance or disk was created. This uses the one approved retry 4 attempt; there will be no retry or zone change under this authorization.

**SCIENCE — ⬜ NULL / INCONCLUSIVE / NOT RUN.** The instance never started, so startup hash checks, Transformers and GPU checks, and Stage S did not run. New Mistral labels: **0/640**. Claude inference requests: **0**. New Qwen replies: **0**. A Stage S output manifest was not created. No local model or training run was performed.

## Checks and cleanup

**PACKAGE — 🔧 METHOD / PROCESS WIN — VALIDATED.** Before the launch attempt, all **12/12** frozen input hashes matched, all four standalone asset hashes, the `run_stage_s_v5.py` pin, and the runner hash matched, and the prepared S3 package verified. The live AWS maximum-scenario estimate was **US$3.708043703703703703703703704/US$5.00**. This is an estimate, not a settled invoice. The direct and scheduled no-target watchdog checks each reported `found: 0` and `terminated: 0`. These checks validate the preparation path; they do not show that the startup script ran on an instance.

**CLEANUP — 🔧 METHOD / PROCESS WIN — VALIDATED.** Cleanup passed. It found **0** instances to terminate and **0** run-tagged disks. The retry 4 secure parameter, Lambda, instance profile, three IAM roles, and schedules were deleted or confirmed absent. S3 receipts and CloudWatch logs were retained. A final AWS read confirmed no active instance, disk, retry 4 IAM role, Lambda, parameter, or schedule remained. The S3 prefix contains the frozen inputs and launch receipts, with no Stage S output manifest.

## Receipts and limits

- AWS failure receipt: `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry4-20261025/provenance/stage_s_launch_attempt.json`
- One-launch armed receipt: `typed_probe_v5_20261025/typed-probe-v5-stage-continuation-retry4-20261025/provenance/stage_s_launch_attempt_armed.json`
- CloudTrail request: `7ce0c0f5-47f1-40c8-9fec-5a88b0bfc1cb`; event `2c76a08b-e223-4c23-8e4f-7c1130bd8fc6`.
- Recorded combined EC2 use before retry 4: **7,672/10,800 seconds**. The frozen plan capped Stage S at **3,000 seconds**, with a **2,500-second** runner guard, **2,700-second** scheduled stop, and **2,900-second** hard stop. It projected **10,672/10,800 seconds**, leaving **128 seconds**. Retry 4 added no EC2 runtime.
- AWS estimate remains under the approved **US$5.00** cap; billing is not settled. Claude inference spend was **US$0** because there were no inference requests. The Claude limits were **US$4.249728** for Stage S and **US$10.00** total.
- **Stage C: NOT AUTHORIZED.** Its separate requirement remains 30 human labels with at least 24/30 panel matches, followed by its own authorization.

## Next

The retry 4 authorization is consumed. Any future Stage S attempt needs a new dated proposal and separate owner authorization. This result does not authorize a different Availability Zone or a second launch.
