# Helm controlled comparison: current cost evidence and proposed job envelope

Status: **STANDING OWNER AUTHORITY; MAIN EXECUTION NOT_READY.** [Authority record](OWNER_STANDING_AUTHORIZATION_20260924.md). No further owner consent is required for in-scope work; each job still needs its fixed package, technical admission and verified spending headroom. C and the $60 ceiling are unchanged. Q4 remains separate. This document starts or changes no resource.

## Current evidence

**Current reconciliation update:** Claude launched the route-only portion of P1 at 05:53:38 UTC. There are now three observed study attempts (two delivered instances). Reader/probe/admission checks remain open; current future/total counts and expected charges are unknown until their grouping is fixed. The tables and total9/11 arithmetic below preserve the earlier combined-P1 proposal only. They are not a current complete execution envelope. [Public launch review](ROUTE_PREREQUISITE_LAUNCH_REVIEW_20260924.md) records the route's 130-minute outer deadline, $3 cap inside $60, pending results and missing ledger reconciliation. Main execution stays held.

The completed smoke is now a **passed reduced-schedule prerequisite**. Public receipts at launch commit `1ddf6a1e4cdefee8aed30760904c7ec4cf49333e` support all four frozen conditions: launcher exit 0, completed delivery/cleanup, the exact reduced schedule, and completed worker ablation/phase-A checks with `claim_bearing=false`. All 53 ablation keys are present, including the five analogy-head keys. This was 8 main updates plus 2 replay steps; phase B was skipped as registered. It does not prove the full-training runtime or the larger-question route.

[SMOKE_COMPLETION_RECONCILIATION.json](SMOKE_COMPLETION_RECONCILIATION.json) records the checks and their limits. The launcher's exit is supported by its public run log and return rule; this review did not re-run it or independently load the binary checkpoints. The producer reports collection of all 54 required objects. Protected archives were not opened.

Provider observations at **04:26:16 and 04:27:41 UTC on September 24** verified instance termination, absence of the temporary root volume, and no remaining job role/profile/security group. The actual termination event was 04:13:24 UTC; this is distinct from a permissions dry-run. Exact observations are in [SMOKE_PROVIDER_OBSERVATION.json](SMOKE_PROVIDER_OBSERVATION.json). These are timestamped observations, not continuing monitoring.

| Existing attempt | Completed state | Reservation | Charge evidence |
|---|---|---:|---|
| `cas-meta2-tpntr-20260924021244-70490111-m-20260917` | Capacity refused; no instance | $15 | $0 compute; four retained S3 objects, 6,754,096 bytes, still incur storage/request costs. |
| `cas-meta2-tpntr-20260924033550-3df31d96-m-20260917` | Reduced smoke passed; instance `i-039b7ae505c4c6245` terminated, temporary resources removed | $15 | Provider interval 2,076 seconds gives $1.4532 modeled compute. The launch log's conservative formula is 2,431.2951856 / 3,600 × $2.52 + $1.48 = $3.18190662992, which rounds **up to $3.19**, not $3.18. No final invoice is available. |

S1 retains 247 evidence objects, 55,932,238 bytes. Cleanup does not mean those retained objects were deleted or all continuing charges ended. The older 04:08 running observation remains unchanged inside `COST_STATE.json`; its `completion_update` supersedes the smoke status.

[LEDGER_RECONCILIATION.json](LEDGER_RECONCILIATION.json) verifies the canonical working ledger at revision 106: both smoke job IDs occur once, at $15 each, **$30 booked**. Both are absent from its committed revision 73. There are also other uncommitted ledger changes: this review preserves the entire file and does not stage, commit, refund or duplicate any booking. The working SHA-256 is `42eb28a1186deb026e0bd09a195f0787e5203428b10a989aa6adb3a3ef424e9f`. The campaign-wide $831 reserved and $5,000 cap do not change this study's $60 ceiling.

Cost Explorer's delayed account-wide figures do not establish this job's final bill. Admission must account for unpublished charges and retained storage. The owner-retained stopped instance `i-0c3028734c8885542` and its older 300 GiB volume remain outside this study's cleanup.

The current coordination handoff at integration `59d86443edc35bcf57368a99f602cd36530ca11d` assigns Codex the six amendments and keeps preparation, custody and approved AWS execution with Claude. The main comparison remains **HELD FOR TECHNICAL PREREQUISITES**, with standing owner authority now recorded. The smoke was neither stopped nor repeated by this review.

## Complete proposed slot count

The following slots are a proposed accounting envelope. P1, P2, M1–M6 and E1 have not been launched by this review. A named, hashed job admission and execution receipt must identify each actual attempt. A failed admission does not silently create a replacement slot.

| Slot | Purpose | Instance / maximum lifetime / root disk | Maximum charge allocation | Ledger booking |
|---|---|---|---:|---:|
| S0 | Existing capacity-refused smoke attempt | No instance | $0 compute; retained object costs counted | $15 already booked |
| S1 | Completed replacement smoke | g7.2xlarge / 4 h / 75 GiB gp3 | $15 | $15 already booked |
| P1 | Public route for both arms, state/output-reader acceptance, corrected probe calibration and admission/package preparation | g4dn.2xlarge / 2 h / 100 GiB gp3 | $3 | $15 proposed |
| P2 | HSET-2 build and actual informative-case counts before training | c7i.2xlarge / 2 h / 20 GiB gp3 | $1 | $15 proposed |
| M1 | Fresh unchanged control seed 20260917, run first; predeclared learned-state and public output comparison included | g7.2xlarge / 4 h / 75 GiB gp3 | $15 | $15 |
| M2–M4 | Repaired seeds 20260917, 20260918, 20260919, in that order | Each g7.2xlarge / 4 h / 75 GiB gp3 | $15 each | $15 each |
| M5–M6 | Two additional fresh unchanged controls if the predeclared C fallback is required, or B is chosen upfront | Each g7.2xlarge / 4 h / 75 GiB gp3 | $15 each | $15 each |
| E1 | Eighteen repaired mechanism checkpoint reads, six final endpoints, historical gates, reader and custody checks | g7.2xlarge / 4 h / 75 GiB gp3 | $15 | $15 proposed |

P2's protected-split operations stay with the existing Claude custodian, as the subsequent coordinator state records; builders and Codex receive public material only. This does not establish outside independence. P1 is a public-fixture job and cannot prove custody or publish protected cases. Its timing preflight must include admission preparation (roughly 290 source blobs and 18 starting checkpoints), which belongs on AWS. If the combined work cannot fit its two-hour/$3 limit, leave the prerequisite open and revise and technically review the named envelope within the unchanged budget before execution; do not invent an extra job. E1 bundles inference and checking; eighteen checkpoint checks do **not** mean eighteen training jobs. There are zero added training updates in E1. Resource bounds specify an attempt limit, not a promise that the task will finish within it.

- **C:** 9 total attempted/proposed slots, including the two existing smoke attempts; **7 future jobs**, of which 4 train. Total proposed reservations **$135**, including $30 already booked and $105 future.
- **B or full C fallback:** 11 total attempted/proposed slots; **9 future jobs**, of which 6 train. Total proposed reservations **$165**, including $30 already booked and $135 future.
- Fixed $15 bookkeeping for P1/P2/E1 is an explicit proposed convention. These are not existing reservations, and admission writers must implement and verify it before the launch request can describe it as operational.
- No automatic retry, replacement, device substitution, zone change or extra evaluation slot is included. A failed slot is reported and leaves its gate open. Failure does not authorize bypassing the original objective or erasing the record.

## Prices, estimates, and maximum exposure

Live AWS Pricing API observations on September 24, for Oregon Linux/shared on-demand instances: g7.2xlarge **$2.52/h**; g4dn.2xlarge **$0.752/h**; c7i.2xlarge **$0.357/h**. gp3 is **$0.08/GB-month**, a public IPv4 address **$0.005/h**, and the first S3 Standard storage tier **$0.023/GB-month**. These are current rate cards, not invoices. Rates must be checked again at admission.

The historical 2.9-hour training duration implies $7.308 compute per full job. Adding a 75 GiB gp3 disk and one public IPv4 address gives about $7.3467 per job using September's 720-hour month. Thus four C training jobs are about **$29.39**, six B jobs about **$44.08**. The repair's actual runtime is not yet measured; this estimate must not be reported as a new measured result.

P1/P2/E1 do not yet have measured runtimes on their final combined scope. Their combined **$19 planning allocation** is a maximum allocation, not an expected-spend measurement. Adding it to the historical training estimate gives **$48.39 for C** or **$63.08 for B**, **plus the smoke attempts' actual compute, disk and address charges. The $19 already includes E1's $1 bounded evidence allowance; do not add that allowance a second time**. Do not relabel the old approximately $30/$45 training-only figures as the cost of the complete comparison. With the completed smoke's $3.19 conservative bound, these hybrid planning figures become **$51.58 for C** and **$66.27 for B**. They combine a historical training estimate with prerequisite/readout maximum allocations; they are not a measured expected total. Reconcile S0 retained costs within the evidence allowance and refresh delay-related charges before admission. The S1 ancillary allowance may overlap the evidence allocation conservatively. B therefore already exceeds $60 on this planning basis; it cannot be promised as an automatic funded fallback.

The independent per-job allocations sum to **$94 for C** or **$124 for B/full fallback**, excluding the first attempt's zero compute but including the completed smoke's original $15 allocation. These sums are **not authority to spend that amount**. The proposed aggregate actual-spend ceiling remains **$60**, including this study's smoke attempts, P1/P2, training, E1, study storage, requests and transfers.

Even C cannot guarantee completion at all allowed lifetimes within $60: six billable g7 jobs at four hours each—S1, four training jobs and E1—use **$60.48 for compute alone**, before P1/P2 or storage. B/full fallback's eight g7 jobs reach **$80.64 compute alone**. The $60 ceiling therefore permits a **budget-stopped incomplete study**. It cannot simultaneously promise that every maximum-duration slot will run.

Before each start, the controller must use the greater conservative estimate of incurred charges and available attributed billing; include running and unpublished charges and ongoing storage. Add the next job's cap, any unspent prerequisite caps, and the reserved E1 allowance including retention. Do not reserve every unstarted training job at its maximum in this per-job rule; later training may be stopped for budget. The rule protects the funded readout and ceiling, not a guarantee that every training job completes. It must refuse a start that would exceed $60 even if campaign ledger headroom exists. Preserve the earlier $30-before-third-training-job stop. This study's fixed $15 bookings must not be added to actual spend or treated as refunds. Do not use a delayed empty Cost Explorer day as $0 incurred cost.

Using the completed smoke and the forthcoming prerequisite receipts, publish the estimated complete-path cost, the maximum-cap scenario and each proposed next-job admission calculation. If the next job plus reserved prerequisites/readout/retention cannot fit, stop and report the exact shortfall; do not silently increase the ceiling, omit the final evaluation, or launch training that leaves no funded readout.

## Cleanup and remaining accounting gates

Each future admission must identify its immutable source/package, job name, region and zone, machine, resource limits, timeout/watchdog and collection contract. Use one study machine at a time. Training retains the 12,600-second worker limit, 14,100-second guest watchdog and 14,400-second instance limit. Confirm actual termination, root-volume deletion, and removal of each temporary role/profile/security group after collection. An enabled delete-on-termination flag or a dry-run termination API event is not a cleanup receipt.

Retain the evidence objects, checkpoint hashes and failure records under the existing custody restrictions. This review authorizes no object deletion or access-rule change. **Proposed bounded allowance:** reserve $1 inside E1's $15 allocation for incremental study evidence storage, requests and collection through **30 days after E1**. Cap study evidence at 10 GiB, Tier 1 requests at 10,000, Tier 2 requests at 100,000, and internet downloads at 2 GiB. These are proposed limits to implement and measure, not present provider-enforced quotas. Current rates imply approximately $0.25 for 10 GiB-month using a conservative decimal-GB conversion, $0.05 for Tier 1, $0.04 for Tier 2 and $0.20 for 2 GiB downloads at $0.09/GB without assuming a free tier: under $0.54 for that bounded volume. The remaining allowance covers the short execution period and uncertainty. Any earlier retained study charges still count toward the aggregate $60; long calendar delays require re-estimation before admission.

After that finite horizon, preserve the evidence under the owner's existing keep policy and separately report ongoing retention charges and the responsible owner. There is **no automatic deletion** at day 30. Continued storage after the horizon is outside this finite execution envelope; the $60 figure is not a permanent lifetime-cost guarantee. A final report must state those continuing charges instead of calling retention free or describing all cloud costs as ended. Owner-retained resources that predate this comparison remain excluded.

The reduced smoke result and temporary-resource cleanup are closed. P1/P2/E1 packages, their fixed-reservation bookkeeping, cumulative spending enforcement, measured runtime estimates, implementation of the proposed retention bounds and P1/P2 completion receipts remain prerequisites to a **ready-to-execute** packet. The future job counts above are fixed; unfinished admission details do not permit extra jobs. This cost note does not claim those gates passed.

E1 completion and cleanup receipts are post-execution deliverables, not prelaunch prerequisites. If the funded sequence stops early, the same E1 slot may report available public diagnostics, historical-gate losses and missing results as COMPARISON_INCOMPLETE; no partial confirmatory TEST comparison or repair-success claim is permitted.
