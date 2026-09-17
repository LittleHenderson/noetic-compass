# First component-first training result

Historical first-arm report. All six runs have now completed; see [the full matched comparison](MATCHED_STUDY_RESULT.md) for the current result. The running-control statements below describe the original observation time.

**The first arm completed and its evidence passed verification. It improved on supplied lessons, but did not transfer to the unfamiliar graphs. The matched control is running; comparative results are pending.**

| Measurement | Before | After |
|---|---:|---:|
| Exposed course questions | 38/564 | 193/564 |
| Unfamiliar-graph questions | 4/59 | 0/59 |
| Unassisted probes across further teaching | 46/96 | 36/96 |

The exposed-course gain comprises **176 gained answers, 21 lost answers and 17 retained-correct answers**. These are questions already supplied by the course, not held-out learning success.

All four development evaluations after teaching began scored **0/59**, at updates 40, 80, 120 and 160. The frozen family-balanced curve is 0.037037 at update 0 and zero thereafter; its normalized area is 0.00462963 and final transfer score is zero. These are one-arm measurements, not ALT-minus-MIXED differences.

The retention panel started at 46/96, below the preset **48/96** competence threshold. Its formal status is `RETENTION_UNASSESSED`. The observed change is still retained: 32 answers stayed correct, 14 were lost and 4 were gained. Parts went 6/32 to 2/32; reach went 40/64 to 34/64. Public source facts remained visible during the 16 further definition/context updates, as specified in the protocol.

| Exposed question kind | Before | After |
|---|---:|---:|
| Analogy | 11/70 | 7/70 |
| Context | 0/70 | 0/70 |
| Correspondence | 0/88 | 85/88 |
| Definition | 0/70 | 0/70 |
| Edge account | 0/70 | 0/70 |
| Parts | 6/53 | 16/53 |
| Reach | 21/107 | 80/107 |
| Role set | 0/36 | 5/36 |

## Execution and verification

- Condition: `ALT_COMPONENT_WHOLE`; model seed: `20260917`; source seed: `101`; encoder seed: `20260916`.
- All eight training kinds, 1,152 main presentations and 160 main updates were retained. The 16 further-instruction updates and two independent validation replays bring actual work to 178 updates and 1,296 training presentations.
- Measured totals exactly match the independent plan: 71,922 core forward calls, 11,482 slot forwards and 2,951 predictions.
- Worker runtime: **1,673.87 seconds (27 minutes 54 seconds)**. Full launch/collection/cleanup lifecycle: 2,263.73 seconds.
- All **584 collected files**, **394 worker artifacts** and **397 required objects** were checked. No required object is missing.
- Forty-nine loaded project modules match the pinned input manifest. Installed source files stayed unchanged. Three checkpoint reconstructions and two byte-identical replays of the last main update passed.
- GPU instance `i-0dcbfc8321769d483` is confirmed terminated. Role and security-group cleanup passed. The private evidence bucket is retained.

Worker source: `e6bdf30524c0cea3da05e8c39899ca6fc059553d`.
Job: `cas-meta2-tmat-20260917072721-e6bdf305-a-20260917`.
Evidence: `receipt_20260917_a/result.json`, `matched_analysis.json`, `independent_work_audit.json`, `independent_integrity_review.json`, `independent_source_replay_review.json`, and `independent_exposed_transitions.json`.

## Remaining comparison

At 2026-09-17 08:14:35 UTC, the matching `MIXED_SAME_ITEMS` control was running on `i-025f80988385e8af2`. Four additional jobs remain queued for the other two seeds. The six-arm study uses the same frozen source and rules throughout. No CAS teaching advantage, general learning gain, protected-final performance or full-machine completion follows from this single arm.

An early read of the control checkpoint metadata confirms matching model, optimizer, encoder and random-state identities, with zero prior updates. The full paired artifact audit is still required. See `paired_initial_state_20260917_001.json`.
