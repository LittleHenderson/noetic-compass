# Corrected v5 Stage S retry — reauthorization proposal

**Date:** 2026-10-25  
**Status: NOT AUTHORIZED.** This proposal and its local package create no AWS resources and do not launch anything. The one launch already authorized under the previous proposal is consumed.

## Why a retry is proposed

The previous attempt failed before the Stage S runner started. Its bootstrap asked for `/latest/meta-data/launch-time`, which EC2 IMDS returned as HTTP 404. The fix in the review package reads `pendingTime` from AWS's instance identity document at `/latest/dynamic/instance-identity/document` and verifies the document's instance ID, region, and zone before starting the hard-stop timer. AWS documents that endpoint and field in its [retrieval guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/retrieve-iid.html) and [identity document fields](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-identity-documents.html).

The saved source remains available and passed its current checks: **1,920** replies, **1,280** existing Mistral labels, capture SHA-256 `26a3aba342e0a0cf1d13d0875c931bd6e81f61de48af22e09a374ead8e34d832`, and label SHA-256 `54724f4f15f1eaed2ce840694e7e750810c6db9c224ec1c54bfdcb1808279868`. A retry would label only the missing **640** replies. It would generate **0** new Qwen replies.

## Proposed single attempt

- **Run ID:** `typed-probe-v5-stage-continuation-retry1-20261025`. Use a new S3 prefix, new temporary resource names, and a write-once launch record.
- **Compute:** one On-Demand `g5.2xlarge` in `us-west-2c`; one `RunInstances` request; no retry and no alternate-zone fallback.
- **Time:** maximum **3,500 EC2 seconds from launch**, including setup. The Mistral/Stage S runner guard is **3,000 seconds from launch**. A scheduled stop is set for about **3,000 seconds** after schedule creation, with at most **300 seconds** of AWS retry age; an instance timer requests AWS termination at **3,350 seconds from launch**.
- **Combined EC2:** the prior approved conservative total was **7,001/10,800 seconds**. The failed attempt used at most **97 seconds** and its watchdog proof used **28 seconds**, so the retry starts from **7,126 seconds**. A new proof capped at **120 seconds** plus a **3,500-second** Stage S attempt projects **10,746/10,800 seconds**, leaving **54 seconds**.
- **Watchdog:** prior use is **294/420 seconds**. The new proof may use at most **120 seconds**, ending at no more than **414/420 seconds**, with **6 seconds** left. If it fails or exceeds **120 seconds**, do not launch.
- **AWS cost:** the refreshed maximum-scenario estimate is **US$3.708043703703703703703703704**, below the existing **US$5.00** cap. It conservatively prices the full **10,800 G5 seconds** and **420 watchdog seconds**, plus the disks, S3 allowance, and public IPv4. Refresh the AWS price immediately before setup and again before launch; stop if the estimate exceeds **US$5.00**. The final invoice is not settled by this estimate.
- **Claude:** Stage S upper bound **US$4.249728**; total cap **US$10.00**. The failed attempt sent no judge batch and used **US$0** of paid Claude inference. Count each request before submission; no retry of an unconfirmed batch.
- **Data and stage:** use the saved source run `typed-probe-v5-stage-s-transformers-retry-20261025`; no new Qwen generation, no overwrite of its prefix, and no Stage C. Stage C remains **NOT AUTHORIZED**.
- **Cleanup:** terminate the instance and delete its disk, schedules, temporary key, Lambda, profile, and IAM roles. Retain S3 receipts.

## Review package and gates

The local package is `docs/working/typed_probe_v5_stage_s_continuation_retry1_20261025/`. Its setup and proof scripts contain an explicit authorization latch set to `False`; `prepare`, the watchdog proof, and `launch` stop before AWS calls until the owner supplies the exact line below and the latch is updated. No local model run is included.

The earlier failed attempt and its cleanup are recorded in [the result report](typed_probe_v5_stage_s_continuation_result_20261025.md). The frozen approval for that attempt is not reusable for this retry.


Package pins for the main execution files (SHA-256):

- `stage_s_continuation.py`: `53eaffa8e9d10556f7704ab759ed5eaf4142867dae5a5099abed1df27aacd046`
- `watchdog_e2e_proof_transformers_retry.py`: `4bc0a6360d81f62f05ecbc1c392fee4f3fa5d1c4dfffdd646601f58fa9bebee2`
- `user_data_stage_s.sh`: `93823ed5e32225c370297c75a9d677bfbd4a6058233c204c25671d22fdb6e92f`

## Owner decision

To authorize the single retry described here, reply exactly:

`AUTHORIZED: yes; GO — approve one corrected Stage S retry under docs/working/typed_probe_v5_stage_s_continuation_retry_proposal_20261025.md.`

Otherwise no further Stage S launch or Stage C work will be performed.
