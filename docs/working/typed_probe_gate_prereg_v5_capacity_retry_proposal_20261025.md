# Typed-Probe v5 Stage S capacity recovery proposal — 2026-10-25

**Status:** 🔒 BLOCKED ON OWNER — proposal only. It does not authorize an AWS launch.

## Why a new decision is needed

The authorized retry, run ID `typed-probe-v5-stage-s-retry2-20261025-0430z`, passed its exact-run-tag watchdog proof. The Stage S launch gate then reached EC2, but AWS rejected `RunInstances` with `InsufficientInstanceCapacity` in the frozen `us-west-2b` zone. No `g5.2xlarge` instance was created. The one additional recovery attempt in the existing amendment is exhausted; that amendment does not permit another launch.

## Proposed bounded change

Authorize one new Stage S launch only, keeping `g5.2xlarge`, the same AMI, region, model versions, prompt bank, rubric, sample count, run limits, and analysis. Change only the availability zone from `us-west-2b` to either currently suggested zone, `us-west-2a` or `us-west-2c`, using the existing same-VPC public subnets:

- `us-west-2a`: `subnet-0bb8fa82c2a7177b3`
- `us-west-2c`: `subnet-0eb3ca4bf5ca98f24`

Both are in `vpc-0df2f8cc1b9f23838`, have public-IP mapping, use its active default route to the internet gateway and default network ACL, and can use the existing security group `sg-0562c483e0364cdab` (no inbound rules). AWS's current instance-offering check listed `g5.2xlarge` in both zones; this does not guarantee capacity when a launch is attempted. The proposed run ID is `typed-probe-v5-stage-s-capacity-retry-20261025`. Select one of the two zones before a single EC2 launch call; if that call fails, stop. Do not fall back to a second launch.

## Limits and gates

- AWS all-in cap remains **US$5.00**. The latest maximum-scenario estimate was **US$3.707840740740740740740740740**. Refresh it before any future launch.
- Claude API cap remains **US$10.00 total**; the frozen Stage S ceiling remains **US$4.249728**. No Claude Message Batch was submitted for the capacity-rejected attempt.
- Combined EC2 ceiling remains **10,800 seconds**. The conservative count to date is **1,241 seconds**: 538 seconds for the first failed GPU launch, at most 570 seconds for the second failed GPU launch (from launch until AWS first reported `terminated`), and 133 watchdog-sentinel seconds. This leaves **9,559 seconds**. If a future Stage S run uses its full **5,400-second** limit, at most **4,159 seconds** would remain for a later Stage C; Stage C still needs its separate human and owner gates.
- Watchdog-sentinel allowance remains **300 seconds total**; **133 seconds** are used, leaving **167 seconds** for one new run's exact-tag proof. If the proof exceeds that allowance or fails, do not launch.
- Use a new exact-run-tag watchdog proof and verify its S3 receipt, scheduled check, IAM tag boundary, source hashes, model IDs, SecureString, current price, and no-active-instance state before the one EC2 call.
- Stage C remains unauthorized; Wakil must label all 30 blind examples, reach at least **24/30** exact panel matches, and give separate authorization.

**Owner authorization:** Not yet granted. If approved, add a dated `AUTHORIZED: yes` decision entry and send `GO` for this specific capacity amendment. Until then, no further Stage S launch is authorized.
