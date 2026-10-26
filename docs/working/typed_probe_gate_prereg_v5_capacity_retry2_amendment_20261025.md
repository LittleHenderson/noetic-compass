# Typed-Probe v5 Stage S capacity retry 2 amendment — 2026-10-25

**Status: AUTHORIZED: yes.** This dated entry records the owner's approval for exactly one additional Stage S launch attempt in `us-west-2c`, after the previously authorized `us-west-2a` attempt failed for capacity. It does not change the frozen Stage S science plan and does not authorize Stage C.

## Owner instruction

> “GO; the current one-attempt approval is used.”

The instruction authorizes one new attempt under the existing caps. The prior one-attempt approval was consumed by the rejected `us-west-2a` request. This amendment permits only the new `us-west-2c` attempt described here.

## One-attempt scope

- Run ID: `typed-probe-v5-stage-s-capacity-retry2-20261025`.
- One Stage S launch request in `us-west-2c`, subnet `subnet-0eb3ca4bf5ca98f24`, VPC `vpc-0df2f8cc1b9f23838`, using the existing security group `sg-0562c483e0364cdab` with zero inbound rules.
- Keep the frozen `g5.2xlarge`, AMI, models and revisions, 120-row prompt bank, rubric, sampling, judge panel, analysis, 5,400-second Stage S limit, and shutdown guard. No second zone, second launch request, or local model run is allowed.
- The EC2 launch client must be configured for one total request attempt. A conditional, write-once S3 record must be created before that request. If the record already exists, the run must stop before calling EC2.
- First prove the exact-run-tag watchdog. If any proof check fails, or its measured use exceeds the remaining **135 seconds**, do not launch Stage S.

## Limits

- AWS maximum-scenario estimate must be refreshed before preparation and launch and remain at or below **US$5.00**. The refreshed estimate before this attempt was **US$3.707840740740740740740740740**; this is an estimate, not a settled bill.
- Claude API total cap remains **US$10.00**. The frozen Stage S upper bound remains **US$4.249728**.
- Combined EC2 cap remains **10,800 seconds**. The conservative count before this attempt is **1,273 seconds**, leaving **9,527 seconds**. Stage S may use at most **5,400 seconds**.
- The watchdog sentinel cap remains **300 seconds total**. Verified prior receipts used **165 seconds**, leaving at most **135 seconds** for this proof.
- Preserve the proof, launch receipt, source hashes, AWS logs, and cleanup records. If launch fails, make no second attempt under this amendment.

## Stage C

**NOT AUTHORIZED.** Wakil must label all 30 blind examples, at least **24/30** must exactly match the frozen panel, and a separate owner authorization is required.

Decision record: `docs/working/agent_exchange/decisions.md`.
