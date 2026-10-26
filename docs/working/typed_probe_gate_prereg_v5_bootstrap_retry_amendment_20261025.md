# Typed-Probe v5 Stage S bootstrap retry amendment

**Status: AUTHORIZED: yes.** This amendment records the owner's approval on 2026-10-25 for one corrected Stage S retry, after the failed first startup. It changes the permitted launch count and adds a short AWS shutdown-watchdog proof; it does not change the science protocol.

## Owner instruction

> “Prove the watchdog works, then launch Stage S within the US$5 AWS cap.”

Earlier owner decisions approved a US$10.00 total Claude API cap and the original Stage S plan. This amendment applies those approvals to this corrected Stage S retry. It does not authorize Stage C.

## Watchdog proof required before Stage S

1. Directly invoke the AWS shutdown watchdog with no matching instance and require `found: 0`, `terminated: 0`.
2. Require the one-time AWS Scheduler smoke event to invoke the same watchdog and log `found: 0`, `terminated: 0`.
3. Check AWS IAM policy simulation: termination is allowed for this run's exact tag and denied for a different run tag.
4. Launch one On-Demand `t3.nano` sentinel in `us-west-2b`, with no public IP, no inbound access, an 8 GiB encrypted `gp3` disk marked `DeleteOnTermination`, and the exact Stage S run-id tag. Invoke the same watchdog while the sentinel is running. Require its receipt to report exactly one instance found and one termination request; then verify that instance is `terminated` and its disk is gone. The sentinel may run for no more than 300 seconds. If any check fails, clean it up and do not launch Stage S.
5. Stage S launch must stop unless the dated S3 watchdog proof receipt passes those checks.

## Retry and money limits

- Stage S only: one corrected `g5.2xlarge` On-Demand retry in `us-west-2b`, using the frozen runner, models, prompt bank, rubric, sampling, and analysis. No local model run, Spot instance, larger instance, parallel instance, or protocol change.
- AWS maximum: **US$5.00 all-in**. Refresh AWS rates before preparation. Include the watchdog sentinel, EC2 time, public IPv4 for Stage S, disks, S3, and request/log charges in the estimate. Stop before creating a Stage S instance if the maximum-scenario estimate exceeds US$5.00.
- Combined GPU-instance time stays at **10,800 seconds** across the failed launch and any later v5 stages. The failed launch used **538 seconds**, leaving **10,262 seconds**. The watchdog sentinel is limited to **300 seconds** and also counts against this combined EC2-time ceiling, leaving at most **9,962 seconds** after its maximum use. Stage S is limited to **5,400 seconds**. If Stage S uses all 5,400 seconds and the sentinel uses all 300 seconds, a future Stage C could use at most **4,562 seconds** from the remaining limit.
- Claude API maximum stays **US$10.00 total** across Stage S and any later, separately authorized Stage C. Stage S keeps its frozen upper bound of **US$4.249728**. The failed startup used **US$0.00** in Claude message charges.
- Count actual sentinel and GPU-instance seconds against the combined 10,800-second ceiling. Do not run instances concurrently.
- Keep the original Stage C gate: Wakil must label all 30 blind examples and at least **24/30** must exactly match the frozen panel. Stage C also requires a new owner authorization; this amendment does not authorize it.

## Run identity and evidence

- Corrected Stage S run ID: `typed-probe-v5-stage-s-retry1-20261025-0400z`.
- Keep the failed startup evidence unchanged. Store this amendment and the watchdog proof under the new run's private S3 evidence prefix.
- Preserve all hashes and receipts. If the watchdog proof fails, classify the operational gate as **🟥 FAILED / WITHDRAWN** and keep Stage S science status **⬜ NULL / INCONCLUSIVE / NOT RUN**.

Authorized by Wakil's direct instruction in this Codex conversation at 2026-10-25T04:06:55Z. Decision record: `docs/working/agent_exchange/decisions.md`.
