# Typed-Probe v5 Stage S capacity retry amendment — 2026-10-25

**Status: AUTHORIZED: yes.** This owner-approved amendment permits one Stage S launch attempt after AWS rejected the frozen `us-west-2b` launch for insufficient On-Demand capacity.

## Owner instruction

> “GO — authorize one Stage S launch attempt in either us-west-2a or us-west-2c under the existing caps.”

## Scope

- One Stage S attempt only, run ID `typed-probe-v5-stage-s-capacity-retry-20261025`, using `us-west-2a` and existing subnet `subnet-0bb8fa82c2a7177b3` in VPC `vpc-0df2f8cc1b9f23838`.
- Keep the existing `g5.2xlarge`, AMI, region, model revisions, prompt bank, rubric, sample count, judge panel, analysis, runtime guard and instance cleanup settings. Use existing security group `sg-0562c483e0364cdab`, which has no inbound rules.
- `us-west-2a` is one of the two zones named by AWS after the capacity rejection. Choosing it does not guarantee capacity. Refresh all checks before launch.
- Make at most one EC2 `RunInstances` call. If that call fails, stop. Do not try `us-west-2c` as a second launch under this amendment.

## Limits and gates

- AWS all-in cap: **US$5.00**. Refresh the live maximum-scenario estimate before preparation and again before launch; stop if it exceeds the cap. The prior maximum-scenario estimate was **US$3.707840740740740740740740740**.
- Claude API cap: **US$10.00 total**. Stage S upper bound: **US$4.249728**. No paid model request is allowed above the frozen protocol limits.
- Combined EC2 ceiling: **10,800 seconds**. Conservative usage to date is **1,241 seconds** (538 seconds from the first failed GPU instance; at most 570 seconds from the second failed GPU instance until AWS first showed `terminated`; 133 watchdog-sentinel seconds), leaving **9,559 seconds**. Stage S is limited to **5,400 seconds**. Stage C remains closed; if Stage S uses its full limit, no more than **4,159 seconds** remain for any later Stage C.
- Watchdog sentinel ceiling: **300 seconds total**. Verified prior receipts account for **133 seconds**, leaving **167 seconds** for this run's proof. Check all prior tagged instances and disks are absent; verify the prior receipts sum to 133 seconds; prove the exact new run tag with the scheduled smoke, IAM tag boundary, live sentinel termination, and disk deletion. If any check fails or the proof exceeds 167 seconds, do not launch.
- Before the single launch call, refresh price, model IDs, frozen input hashes, secure parameter, private S3 controls and active-instance checks. The launch gate must verify the new proof receipt.
- Keep the Claude key in SSM `SecureString` only while needed. Clean up the key and temporary roles after the attempt; retain S3 and CloudWatch evidence.

## Stage C

**NOT AUTHORIZED.** Wakil must label all 30 blind examples; at least **24/30** must exactly match the frozen panel; separate owner authorization is still required.

Decision record: `docs/working/agent_exchange/decisions.md`.
