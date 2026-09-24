# Helm controlled comparison: current cost evidence and proposed job envelope

Status: **PREPARATION ONLY — NOT LAUNCH AUTHORITY.** This record accompanies the amended launch request. It does not start, retry, stop, delete or modify any cloud resource. The latest user instruction requires a corrected request before launch; an older approval quoted in source is not new authority for this review to execute it. Q4 is separate.

## Current evidence

Read-only provider snapshot: **2026-09-24 04:08:17 UTC**, us-west-2. Source receipt: `COST_STATE.json`. Source branches inspected: integration `197caa322d20ae6830928b20c5b16933e93cd00d`; launch `1fcc15e5fe0183da4572741e4efa675698640ab5`. This is a time-bounded observation, not continuing monitoring.

Two smoke attempts have actually been booked. No main comparison job was found in the current regional inventory or the queried CloudTrail `RunInstances` events since 02:00 UTC:

| Existing attempt | Observed state | Reservation | Spending evidence |
|---|---|---:|---|
| `cas-meta2-tpntr-20260924021244-70490111-m-20260917` | Capacity refused at 02:15:27 UTC; no instance returned | $15 | Compute $0. Four retained S3 objects total 6,754,096 bytes; storage and requests are not zero-cost compute. |
| `cas-meta2-tpntr-20260924033550-3df31d96-m-20260917` | Replacement smoke running on `i-039b7ae505c4c6245`, g7.2xlarge, us-west-2a; launched 03:38:48 UTC | $15 | 1,773.528324 elapsed seconds × current $2.52/hour = **$1.241470 compute exposure** at observation. This is not a finalized bill or final job cost. |

The running smoke has a 75 GiB gp3 root volume, `vol-0bbd58d49a4782ed3`, with delete-on-termination enabled. Its bucket had 144 objects totalling 51,586,314 bytes. Only metadata was read; model files and prediction content were not opened. A local launch receipt and reservation exist; the final `result.json` did not yet exist. Consequently the smoke is **RUNNING / NOT YET DELIVERED**, not a passed prerequisite.

The canonical ledger is revision 106, updated 03:38:27 UTC, with exactly these two matching $15 reservations: **$30 booked for this study**. Its $831 campaign-wide total and $5,000 campaign cap include unrelated work and do not enlarge this study's proposed $60 actual-spend limit. The stale Git copy is not the canonical ledger. Reservations are not invoices and receive no automatic refund.

Cost Explorer returned estimated account-wide September 23 charges and no September 24 service groups. It cannot establish the final per-job amount or zero current spending. Use provider timestamps and conservative pending-charge estimates until attribution and billing catch up.

The only other regional instance was the owner-retained stopped g6e.xlarge, `i-0c3028734c8885542`, with its existing 300 GiB gp3 volume. It belongs outside this study's incremental budget and must not be deleted as comparison cleanup.

## Observed control path

The live child process was `python.exe` PID 27980 invoking `typed_pointer_launch.py`, with `--reduced-schedule` and the smoke receipt. No `run_on_study.py` process was found. The inspected launcher's lines 947–955 execute one requested job and return. Its immediate parent, PID 75376, was Python reading a program from stdin; that program was not visible in the process record. These observations support a single-smoke child invocation but **do not prove that a separate controller cannot start another job later**. This review neither modified nor terminated that controller.

Subsequent source coordination update: integration `91968e5d17747e7d60b6d4d37b3124657b035a67`, `_handoffs/HELM_NEXT_PHASE_20260923/CLAUDE_STATE_FOR_CODEX_20260924.md`, explicitly records that the **main comparison is HELD until one complete amended launch request is approved**. The existing smoke was started under earlier approval, before that hold, and Claude will file its result. This is the coordinator's stated operating rule; it is separate from the provider/process observation and is not proof of a technical launch lock. The cost snapshot above remains attached to its original time and inspected heads.

## Complete proposed slot count

The following slots are a proposed accounting envelope. P1, P2, M1–M6 and E1 have not been launched by this review. A named, hashed job admission and execution receipt must identify each actual attempt. A failed admission does not silently create a replacement slot.

| Slot | Purpose | Instance / maximum lifetime / root disk | Maximum charge allocation | Ledger booking |
|---|---|---|---:|---:|
| S0 | Existing capacity-refused smoke attempt | No instance | $0 compute; retained object costs counted | $15 already booked |
| S1 | Existing replacement smoke | g7.2xlarge / 4 h / 75 GiB gp3 | $15 | $15 already booked |
| P1 | Public larger-question route for both arms, identity-reader checks, corrected probe calibration | g4dn.2xlarge / 2 h / 100 GiB gp3 | $3 | $15 proposed |
| P2 | HSET-2 build and actual informative-case counts before training | c7i.2xlarge / 2 h / 20 GiB gp3 | $1 | $15 proposed |
| M1 | Fresh unchanged control seed 20260917, run first; predeclared learned-state and public output comparison included | g7.2xlarge / 4 h / 75 GiB gp3 | $15 | $15 |
| M2–M4 | Repaired seeds 20260917, 20260918, 20260919, in that order | Each g7.2xlarge / 4 h / 75 GiB gp3 | $15 each | $15 each |
| M5–M6 | Two additional fresh unchanged controls if the predeclared C fallback is required, or B is chosen upfront | Each g7.2xlarge / 4 h / 75 GiB gp3 | $15 each | $15 each |
| E1 | Eighteen repaired mechanism checkpoint reads, six final endpoints, historical gates, reader and custody checks | g7.2xlarge / 4 h / 75 GiB gp3 | $15 | $15 proposed |

P2's protected-split operations stay with the existing Claude custodian, as the subsequent coordinator state records; builders and Codex receive public material only. This does not establish outside independence. P1 is a public-fixture job and cannot prove custody or publish protected cases. E1 bundles inference and checking; eighteen checkpoint checks do **not** mean eighteen training jobs. There are zero added training updates in E1. Resource bounds specify an attempt limit, not a promise that the task will finish within it.

- **C:** 9 total attempted/proposed slots, including the two existing smoke attempts; **7 future jobs**, of which 4 train. Total proposed reservations **$135**, including $30 already booked and $105 future.
- **B or full C fallback:** 11 total attempted/proposed slots; **9 future jobs**, of which 6 train. Total proposed reservations **$165**, including $30 already booked and $135 future.
- Fixed $15 bookkeeping for P1/P2/E1 is an explicit proposed convention. These are not existing reservations, and admission writers must implement and verify it before the launch request can describe it as operational.
- No automatic retry, replacement, device substitution, zone change or extra evaluation slot is included. A failed slot is reported and leaves its gate open. Failure does not authorize bypassing the original objective or erasing the record.

## Prices, estimates, and maximum exposure

Live AWS Pricing API observations on September 24, for Oregon Linux/shared on-demand instances: g7.2xlarge **$2.52/h**; g4dn.2xlarge **$0.752/h**; c7i.2xlarge **$0.357/h**. gp3 is **$0.08/GB-month**, a public IPv4 address **$0.005/h**, and the first S3 Standard storage tier **$0.023/GB-month**. These are current rate cards, not invoices. Rates must be checked again at admission.

The historical 2.9-hour training duration implies $7.308 compute per full job. Adding a 75 GiB gp3 disk and one public IPv4 address gives about $7.3467 per job using September's 720-hour month. Thus four C training jobs are about **$29.39**, six B jobs about **$44.08**. The repair's actual runtime is not yet measured; this estimate must not be reported as a new measured result.

P1/P2/E1 do not yet have measured runtimes on their final combined scope. Their combined **$19 planning allocation** is a maximum allocation, not an expected-spend measurement. Adding it to the historical training estimate gives **$48.39 for C** or **$63.08 for B**, **plus the smoke attempts' actual compute, disk and address charges. The $19 already includes E1's $1 bounded evidence allowance; do not add that allowance a second time**. Do not relabel the old approximately $30/$45 training-only figures as the cost of the complete comparison.

The independent per-job allocations sum to **$94 for C** or **$124 for B/full fallback**, excluding the first attempt's zero compute but including the running smoke's $15 allocation. These sums are **not authority to spend that amount**. The proposed aggregate actual-spend ceiling remains **$60**, including this study's smoke attempts, P1/P2, training, E1, study storage, requests and transfers.

Even C cannot guarantee completion at all allowed lifetimes within $60: six billable g7 jobs at four hours each—S1, four training jobs and E1—use **$60.48 for compute alone**, before P1/P2 or storage. B/full fallback's eight g7 jobs reach **$80.64 compute alone**. The $60 ceiling therefore permits a **budget-stopped incomplete study**. It cannot simultaneously promise that every maximum-duration slot will run.

Before each start, the controller must use the greater conservative estimate of incurred charges and available attributed billing; include running and unpublished charges and ongoing storage. Add the next job's cap, any unspent prerequisite caps, and the reserved E1 allowance including retention. Do not reserve every unstarted training job at its maximum in this per-job rule; later training may be stopped for budget. The rule protects the funded readout and ceiling, not a guarantee that every training job completes. It must refuse a start that would exceed $60 even if campaign ledger headroom exists. Preserve the earlier $30-before-third-training-job stop. This study's fixed $15 bookings must not be added to actual spend or treated as refunds. Do not use a delayed empty Cost Explorer day as $0 incurred cost.

After the smoke and prerequisite receipts arrive, publish the estimated complete-path cost, the maximum-cap scenario and each proposed next-job admission calculation. If the next job plus reserved prerequisites/readout/retention cannot fit, stop and report the exact shortfall; do not silently increase the ceiling, omit the final evaluation, or launch training that leaves no funded readout.

## Cleanup and remaining accounting gates

Each future admission must identify its immutable source/package, job name, region and zone, machine, resource limits, timeout/watchdog and collection contract. Use one study machine at a time. Training retains the 12,600-second worker limit, 14,100-second guest watchdog and 14,400-second instance limit. Confirm actual termination, root-volume deletion, and removal of each temporary role/profile/security group after collection. An enabled delete-on-termination flag or a dry-run termination API event is not a cleanup receipt.

Retain the evidence objects, checkpoint hashes and failure records under the existing custody restrictions. This review authorizes no object deletion or access-rule change. **Proposed bounded allowance:** reserve $1 inside E1's $15 allocation for incremental study evidence storage, requests and collection through **30 days after E1**. Cap study evidence at 10 GiB, Tier 1 requests at 10,000, Tier 2 requests at 100,000, and internet downloads at 2 GiB. These are proposed limits to implement and measure, not present provider-enforced quotas. Current rates imply approximately $0.25 for 10 GiB-month using a conservative decimal-GB conversion, $0.05 for Tier 1, $0.04 for Tier 2 and $0.20 for 2 GiB downloads at $0.09/GB without assuming a free tier: under $0.54 for that bounded volume. The remaining allowance covers the short execution period and uncertainty. Any earlier retained study charges still count toward the aggregate $60; long calendar delays require re-estimation before admission.

After that finite horizon, preserve the evidence under the owner's existing keep policy and separately report ongoing retention charges and the responsible owner. There is **no automatic deletion** at day 30. Continued storage after the horizon is outside this finite execution envelope; the $60 figure is not a permanent lifetime-cost guarantee. A final report must state those continuing charges instead of calling retention free or describing all cloud costs as ended. Owner-retained resources that predate this comparison remain excluded.

The existing smoke remains in flight at this snapshot. P1/P2/E1 packages, their fixed-reservation bookkeeping, cumulative spending enforcement, measured runtime estimates, implementation of the proposed retention bounds and completion receipts remain prerequisites to a **ready-for-final-approval** request. The future job counts above are fixed; unfinished admission details do not permit extra jobs. This cost note does not claim those gates passed.
