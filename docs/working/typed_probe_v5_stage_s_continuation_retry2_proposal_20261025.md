# v5 Stage S retry 2 — reauthorization proposal

**Date:** 2026-10-25  
**Status: AUTHORIZED FOR ONE ATTEMPT; PRE-LAUNCH GATES OPEN.** Owner response received 2026-10-25 02:45:17 -07:00 (2026-10-25T09:45:17Z). This approval covers exactly one retry 2 launch under the limits below; it does not authorize Stage C.

## Why another retry is proposed

The corrected retry reached the Stage S runner. AWS verified Python 3.12.10, PyTorch 2.8.0+cu129, Transformers 4.57.1, and the GPU. Stage S then stopped before labeling because the instance role lacked `s3:GetObjectVersion` for the pinned source manifest. The retry 1 result is 🟥 FAILED / WITHDRAWN; it produced 0/640 new labels, sent 0 Claude requests, and generated 0 Qwen replies. Cleanup passed and its evidence remains in S3. See `typed_probe_v5_stage_s_continuation_retry1_result_20261025.md`.

## Exact permission repair

Keep the existing `s3:GetObject` permission for saved captures. Add `s3:GetObjectVersion` only for these two pinned objects:

- `arn:aws:s3:::cas-harness-runpod-92754088/typed_probe_v5_20261025/typed-probe-v5-stage-s-transformers-retry-20261025/output/run_manifest_stage_s.json`
- `arn:aws:s3:::cas-harness-runpod-92754088/typed_probe_v5_20261025/typed-probe-v5-stage-s-transformers-retry-20261025/output/mistral_votes_stage_s.jsonl`

Before any instance launch, the setup will use AWS's permission simulator to require access for these exact two versioned objects and denial for a capture file and a new-run output file. It will then repeat the saved-source hash checks. The permission does not grant version reads across the bucket or the source prefix.

## Proposed single attempt

- **Run ID:** `typed-probe-v5-stage-continuation-retry2-20261025`; fresh S3 prefix and temporary resource names. One `RunInstances` request only, with no retry and no alternate Availability Zone.
- **Compute:** one On-Demand `g5.2xlarge` in `us-west-2c`.
- **Saved data only:** validate the existing 1,920 replies and 1,280 Mistral labels; add only the missing 640 labels. Generate 0 new Qwen replies.
- **Time:** maximum Stage S instance time **3,000 seconds from launch**. The runner guard is **2,500 seconds**, scheduled stop at about **2,700 seconds**, and instance hard stop at **2,900 seconds**.
- **Combined EC2:** exact recorded use before retry 2 is **7,492/10,800 seconds**: 7,126 prior seconds, 48 seconds for the passed watchdog proof, and 318 seconds for the failed retry 1. This proposal reuses that watchdog proof, so it adds 0 proof seconds. A 3,000-second attempt projects **10,492/10,800 seconds**, leaving **308 seconds**. The remaining watchdog allowance is **78/420 seconds** and will not be spent by this plan.
- **Watchdog gate:** reuse the immutable live-target proof from retry 1 only if its S3 version, body SHA-256, and unchanged `cloud_watchdog.py` SHA-256 match the values pinned in the package. That proof passed in 48 seconds, stopped its temporary test instance, and deleted its disk. For retry 2, the setup must also pass fresh direct and scheduled no-target checks using the new run ID. If any proof or smoke check fails, do not launch.
- **AWS cost:** the last maximum-scenario estimate was **US$3.708043703703703703703703704** under the **US$5.00** cap. Refresh it before setup and again before launch; stop if it exceeds US$5.00. This is an estimate, not a settled invoice.
- **Claude:** Stage S upper bound **US$4.249728**; total cap **US$10.00**. Retry 1 used **US$0** of Claude inference. Check and reserve every request before submission; do not retry an unconfirmed batch.
- **Stage C:** **NOT AUTHORIZED.** The owner-label requirement remains 30 examples with at least 24/30 panel matches, followed by separate authorization.
- **Cleanup:** terminate the instance and remove the run's disk, schedules, temporary key, Lambda, profile, and IAM roles. Preserve the S3 receipts and logs.

## Review package and pre-launch gates

Package: `docs/working/typed_probe_v5_stage_s_continuation_retry2_20261025/`.

The package has Python and shell syntax checks and frozen input hash checks. Its setup and watchdog proof latches are both `False`. It does not create AWS resources or run models. After approval, setup will recheck the AWS account, price, source versions and hashes, empty run prefix, role policy simulation, stored key type and tag, and watchdog proof/smokes. Launch will repeat the price, source, proof, key, Availability Zone, security group, instance offering, and no-existing-instance checks immediately before its single launch request.

## Owner decision

To authorize exactly one attempt within the scope and stop conditions above, reply exactly:

`AUTHORIZED: yes; GO — approve one Stage S retry with the pinned-source-version permission fix under docs/working/typed_probe_v5_stage_s_continuation_retry2_proposal_20261025.md.`

Otherwise this package remains locked. No Stage S launch or Stage C work is authorized by this proposal until that new response is received.

## Owner approval received 2026-10-25T09:45:17Z

OWNER RESPONSE (verbatim): `AUTHORIZED: yes; GO — approve one Stage S retry with the pinned-source-version permission fix under docs/working/typed_probe_v5_stage_s_continuation_retry2_proposal_20261025.md.` 

The approval is for one `g5.2xlarge` attempt in `us-west-2c` with the pinned source-version permission repair and the stated **3,000-second** Stage S limit. All pre-launch price, source, IAM simulation, watchdog-proof, secret, and cleanup gates remain mandatory. Stage C remains NOT AUTHORIZED.
