# v5 Stage S continuation attempt — result and cleanup

**Recorded:** 2026-10-25T09:04:59Z  
**Run ID:** `typed-probe-v5-stage-continuation-20261025`  
**Status:** one authorized launch attempt was used; all run-scoped AWS resources have been removed.

## Results

- **ATTEMPT: 🟥 FAILED / WITHDRAWN.** The single `g5.2xlarge` launch in `us-west-2c` stopped during bootstrap. CloudTrail records exactly one `RunInstances` event, request ID `b955842d-42f2-46b5-a302-0d77775f07cd`, at `2026-10-25T08:56:02Z`. EC2 records termination requested at `2026-10-25T08:57:39Z`, **97 seconds** after launch.
- **SCIENCE: ⬜ NULL / INCONCLUSIVE / NOT RUN.** The continuation runner never started. New Mistral labels: **0/640**. Claude token counts and judge batches: **not submitted**. New Qwen replies: **0**. No local model execution occurred.
- **CAUSE:** the bootstrap script requested `/latest/meta-data/launch-time`; IMDS returned HTTP **404**, and the shell exited with code **22**. AWS documents the launch time as `pendingTime` in the instance identity document at `/latest/dynamic/instance-identity/document` ([retrieval instructions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/retrieve-iid.html), [document fields](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-identity-documents.html)).
- **WATCHDOG: 🔧 METHOD / PROCESS WIN — VALIDATED.** End-to-end AWS proof passed in **28 seconds**; watchdog use is now **294/420 seconds**. The proof instance and disk were removed.
- **AWS LIMIT:** the refreshed maximum-scenario estimate before launch was **US$3.708043703703703703703703704**, under the **US$5.00** cap. This is an estimate, not a final invoice. No Claude batch request was made, so this attempt used **US$0** of the Claude API allowance.
- **CLEANUP: 🔧 METHOD / PROCESS WIN — VALIDATED.** EC2 instance is terminated; run-tagged disks, schedules, Lambda, instance profile, three IAM roles, and the SecureString parameter are absent. S3 receipts and failure logs remain.

## Evidence

- S3 run prefix: `s3://cas-harness-runpod-92754088/typed_probe_v5_20261025/typed-probe-v5-stage-continuation-20261025/`
- Failure log: `output/logs/instance-bootstrap.log`; exit receipt: `output/logs/instance_exit_status.txt` (`exit_code=22`).
- Launch receipt: `provenance/stage_s_launch_attempt.json`.
- Watchdog proof: `provenance/watchdog_proof.json`.
- The approved input manifest and package hashes are retained under `input/` and `provenance/`.

## Authorization state

The owner's approval covered one Stage S launch attempt. That attempt is consumed. No further Stage S launch or Stage C work is authorized by the existing approval. Stage C remains **NOT AUTHORIZED**.

A corrected retry proposal and hash-checked local package are available at [the reauthorization proposal](typed_probe_v5_stage_s_continuation_retry_proposal_20261025.md). They are **not authorized** and have created no AWS resources. The proposal projects **10,746/10,800 combined EC2 seconds**, **414/420 watchdog seconds**, and the same **US$3.708043703703703703703703704** maximum-scenario AWS estimate under the **US$5.00** cap. A new owner response is required before any AWS setup or launch.
