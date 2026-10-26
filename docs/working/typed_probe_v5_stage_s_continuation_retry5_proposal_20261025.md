# v5 Stage S retry 5 — move to us-west-2a after capacity rejection

**Date:** 2026-10-25  
**Status:** AUTHORIZED FOR ONE ATTEMPT; PRE-LAUNCH GATES OPEN. The owner approved retry 5 at 2026-10-25T17:11:27Z with a US$15.00 AWS cap. No retry 5 AWS setup or launch has started.

## Approved scope

The owner approved at most one new Stage S continuation attempt in us-west-2a, with the limits below. Retry 4's approval is consumed and cannot be reused. This proposal does not authorize Stage C to run now. All pre-launch gates remain required.

The retry 5 specific operational amendment is recorded in docs/working/typed_probe_gate_prereg_v5_retry5_operational_amendment_20261025.md. It supersedes the previous US$5.00 AWS cap only for this one attempt; it does not change the frozen science protocol or the earlier run records.

Owner's approval instruction:

“AUTHORIZED: yes; GO — approve one Stage S retry 5 in us-west-2a under docs/working/typed_probe_v5_stage_s_continuation_retry5_proposal_20261025.md, with the AWS cap of US$15.00 and the stated Claude caps.”

Owner response received 2026-10-25T17:11:27Z (verbatim):

AUTHORIZED: yes; GO — approve one Stage S retry 5 in us-west-2a under docs/working/typed_probe_v5_stage_s_continuation_retry5_proposal_20261025.md, with the AWS cap of US$15.00 and the stated Claude caps.

## Current evidence

- Retry 4 is 🟥 FAILED / WITHDRAWN. AWS rejected its only RunInstances request in us-west-2c with InsufficientInstanceCapacity at 2026-10-25T14:31:21Z. No instance or disk was created. The startup script and Stage S did not run. The retry 4 authorization is consumed.
- Stage S remains ⬜ NULL / INCONCLUSIVE / NOT RUN. No new labels were produced by retry 4; no Claude requests or new Qwen replies were sent.
- At 2026-10-25T16:35:20Z, the signed-in AWS identity was account 807562639912, user cas-g5-operator. A read-only query found no tagged v5 instance in pending, running, stopping, or stopped state.
- AWS lists g5.2xlarge as offered in us-west-2a. The available us-west-2a subnet subnet-0bb8fa82c2a7177b3 and retry 4 security group sg-0562c483e0364cdab are in the same VPC, vpc-0df2f8cc1b9f23838, so they are compatible for placement. This does not prove network reachability or guarantee that AWS has a g5.2xlarge available when the request is made; verify network access and capacity again before launch.
- The live source manifest and label-object versions match the frozen pins: manifest version R.WaTufVeoOjQ_M0AqoTowTlOsw0O9Nx, SHA-256 06556ba04ce37b5a6a2cc104140fa184177c8565665ffde6d7326c162309ead8; Mistral checkpoint version UaVLnN.nEcujm3kWFTG1r4ci2UWFgN9f, SHA-256 54724f4f15f1eaed2ce840694e7e750810c6db9c224ec1c54bfdcb1808279868. The manifest reports run status MISTRAL_LABELING and 1,920 saved replies. The frozen checkpoint contains 1,280 Mistral labels, leaving 640 to add. The capture-set SHA-256 is 26a3aba342e0a0cf1d13d0875c931bd6e81f61de48af22e09a374ead8e34d832. Before setup, recheck the exact source versions, hashes, row counts, and current status. Stop if they changed or no longer match the frozen protocol.
- Stage C was authorized by Wakil at 2026-10-25T14:39:02Z. Its prerequisite is still open: Stage S must finish first, then Wakil must label the 30 blinded examples; at least 24/30 must exactly match the panel. Stage C is not part of this proposal's run or budget.

## One proposed attempt

- **Run ID:** typed-probe-v5-stage-continuation-retry5-20261025.
- **Compute:** exactly one On-Demand g5.2xlarge in us-west-2a, using subnet-0bb8fa82c2a7177b3 and the existing security group. Submit one RunInstances request with SDK total attempts set to 1. No retry, alternate zone, or instance type. If AWS reports insufficient capacity, stop and record that result.
- **Work:** continue from the pinned 1,920 saved replies and 1,280 Mistral labels; add only the missing 640 labels and produce the frozen Stage S outputs. Do not generate new Qwen replies or change the frozen scoring rules.
- **Stage S time:** maximum 3,000 EC2 seconds; runner guard 2,500 seconds; scheduled stop at 2,700 seconds; hard stop at 2,900 seconds.
- **Combined EC2 limit:** recorded prior use is 7,672/10,800 seconds. One full 3,000-second attempt would project 10,672/10,800 seconds, leaving 128 seconds. Recheck the ledger before setup; stop if the recorded use changed or the projection exceeds 10,800 seconds.
- **Watchdog:** reuse only the already-tested immutable proof, after checking its exact S3 version and SHA-256 again. Its recorded cumulative use is 342/420 seconds, leaving 78 seconds. Require fresh direct and scheduled no-target checks for retry 5 before launch. Do not exceed the 420-second watchdog limit.
- **AWS cost:** maximum US$15.00 for this proposed attempt, including setup, compute, storage, watchdog, logs, and cleanup. The latest comparable estimate was US$3.708043703703703703703703704 for retry 4; it is not a retry 5 quote and is not an invoice. Refresh the maximum estimate before AWS setup and immediately before launch. If either estimate exceeds US$15.00, stop. Report prior v5 spend separately; do not describe the cap as an invoice or as remaining account balance.
- **Claude API:** maximum US$4.249728 for Stage S and US$10.00 total. Recheck current usage before setup. Reserve each request before sending it; do not retry a batch whose submission status is uncertain.
- **Cleanup:** stop or terminate only retry 5 resources, remove its temporary disk and run-specific schedules, parameters, Lambda, profile, and roles, and preserve S3 receipts and logs. Confirm no retry 5 resources remain.

## Required checks after approval

1. Create a new retry 5 package and run ID. Do not reuse retry 4's launch script or its consumed authorization latch. Pin the new us-west-2a subnet, source objects, runner, startup files, watchdog, proposal, and package manifest by exact hashes.
2. Recheck AWS identity, current source manifest and label counts, empty retry 5 S3 prefix, permissions, API key storage type, current cost estimate, watchdog proof, and direct and scheduled no-target checks. Verify the selected subnet, security group, and AZ match this proposal.
3. Immediately before launch, repeat the cost, source, watchdog, active-instance, subnet, and security-group checks. If any gate fails, stop without submitting RunInstances.
4. Submit exactly one launch request. Keep the complete AWS rejection or instance receipt, Stage S output manifest, exact cost estimate, and cleanup receipt.
5. After Stage S completes, pause for Wakil to label the 30 blinded examples. Stage C may proceed only if at least 24/30 exact matches pass and its separately recorded authorization remains valid.

