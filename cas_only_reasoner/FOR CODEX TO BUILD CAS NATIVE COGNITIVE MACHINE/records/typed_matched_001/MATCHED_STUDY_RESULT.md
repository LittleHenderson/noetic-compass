# Completed matched teaching comparison

All six GPU runs completed and passed the independent evidence audit. Component-first teaching scored higher than the mixed control in two of three matched pairs and tied in one. The differences are small and absolute performance on unfamiliar graphs is poor. Both methods finished below their shared pre-teaching development score. A useful, durable learning advantage has not been established.

## What was compared

Three model seeds each ran both teaching methods. ALT_COMPONENT_WHOLE teaches components before whole tasks; MIXED_SAME_ITEMS mixes the same lessons within batches. The learner, encoder, information, corrections, initial model/optimizer/random state and measured work match within every pair. Only the grouping/order of 256 supplementary presentations changes; the other 896 presentations remain fixed.

This is one controlled teaching-order comparison. It does not compare CAS architecture with all usual teaching methods. The ordinary dependency-graph schedule is identical to the component-first schedule, so it is not counted as a distinct third method.

## Main results

| Prespecified development measure | Component-first | Mixed control | Component-first minus control |
| --- | ---: | ---: | ---: |
| Mean learning-curve score | 2.4788% | 2.0544% | +0.4244 percentage points |
| Mean final transfer score | 3.7423% | 0.3472% | +3.3951 percentage points |
| Eligible retention comparisons | 0 of 3 pairs | 0 of 3 pairs | Unassessed |

Both methods started at 6.5201% on the family-balanced development measure. The final transfer scores are below that starting point. The observed relative advantage therefore does not establish improved unfamiliar-problem performance over the initial learner.

Raw final answers were **4/177 for component-first versus 1/177 for the control**, down from **21/177 in each method before teaching**. This is the same 59-question panel repeated with three model initializations, not 177 different problems. The panel contains six development topologies (8–10 nodes) after training on 3–4-node worlds. Development answers supplied no training corrections; the protected final panel was not opened for this study.

The primary score gives equal weight to six topology families and, within each, equal weight to the parts question and the mean reach score. One correct parts answer can therefore move the balanced score more than one correct reach answer. The raw counts above remain essential context.

The learning-curve score is the normalized trapezoid across updates 0, 40, 80, 120 and 160: (A0 + 2*A40 + 2*A80 + 2*A120 + A160) / 8, where **A is the family-balanced development accuracy at that update, not the raw correct-out-of-59 count**. Substituting the raw counts into this formula gives different numbers; the raw counts are reported in "Every run" below and must not be used in it. A higher value is better accuracy along this fixed training schedule. It is not a measured percentage speedup or proof that a threshold was reached in fewer steps.

## Every run

| Model seed | Method | Exposed course before → after /564 | Development correct at updates 0 / 40 / 80 / 120 / 160 (each /59) | Curve score | Final transfer score | Retention before → after /96 |
| --- | --- | --- | --- | ---: | ---: | --- |
| 20260917 | Component-first | 38 → 193 | 4 / 0 / 0 / 0 / 0 | 0.4630% | 0.0000% | 46 → 36 |
| 20260917 | Mixed control | 38 → 192 | 4 / 0 / 0 / 0 / 0 | 0.4630% | 0.0000% | 47 → 38 |
| 20260918 | Component-first | 37 → 200 | 17 / 1 / 1 / 3 / 3 | 5.4109% | 2.8935% | 47 → 34 |
| 20260918 | Mixed control | 37 → 203 | 17 / 1 / 1 / 3 / 1 | 5.1794% | 1.0417% | 48 → 37 |
| 20260919 | Component-first | 39 → 196 | 0 / 0 / 1 / 1 / 1 | 1.5625% | 8.3333% | 47 → 34 |
| 20260919 | Mixed control | 39 → 189 | 0 / 0 / 1 / 1 / 0 | 0.5208% | 0.0000% | 45 → 34 |

All six runs improved fit to exposed course questions. Totals after teaching are 589/1692 versus 584/1692: five additional correct answers for component-first across the same 564 questions repeated in three runs. These exposed results do not establish transfer.

Retention used 96 probes without worked-answer supports, before and after 16 updates teaching definition/context questions. The frozen competence threshold is at least 48/96 before that interval in both arms of a pair. Only the seed-20260918 control reached it; no component-first arm did. All six raw probe scores declined. Retention remains unassessed under the preset rule; this is not evidence that the methods retain equally well. Public facts remain visible, and this is an intervening-teaching test, not a long elapsed-time test.

## Saved-output diagnosis and next action

The following is descriptive diagnosis after the completed comparison, not an added primary endpoint. Each denominator combines three runs of the same exposed question bank.

| Exposed question kind | Component-first before → after | Mixed control before → after |
| --- | ---: | ---: |
| analogy | 25 → 36 / 210 | 25 → 32 / 210 |
| context | 3 → 0 / 210 | 3 → 0 / 210 |
| correspondence | 0 → 250 / 264 | 0 → 249 / 264 |
| definition | 1 → 0 / 210 | 1 → 0 / 210 |
| edge_account | 0 → 0 / 210 | 0 → 0 / 210 |
| parts | 18 → 46 / 159 | 18 → 47 / 159 |
| reach | 65 → 246 / 321 | 65 → 245 / 321 |
| role_set | 2 → 11 / 108 | 2 → 11 / 108 |

Context, definition and edge-account answers remain at zero after main teaching in both methods across all three seeds. The next research step is to inspect the saved predictions for these failures, the unfamiliar-graph collapse and the losses during intervening teaching, then freeze a targeted correction and a fresh matched test. Causal explanations are still hypotheses. More seeds alone would not repair the low competence. Keep the protected final panel untouched while developing the fix.

## Execution and verification

- All six runs used worker source e6bdf30524c0cea3da05e8c39899ca6fc059553d and the same pinned source archive.
- Each run executed 160 main teaching updates, 16 intervening-teaching updates and two separately counted verification replays: 178 actual updates, 1,296 training presentations, 71,922 core forward calls and 2,951 predictions.
- Across the study: 1,068 actual updates, 7,776 presentations, 431,532 core forward calls and 17,706 predictions. Counted work matches between arms; elapsed time need not match exactly.
- Independent file checks passed 3,504 collected files, 2,364 worker artifacts, 2,382 required delivery objects, 18 checkpoint reconstructions and 12 exact last-update replays.
- All three paired initializations match in model, optimizer, encoder and random state. The three model seeds produce distinct initial model identities.
- These final audits read saved JSON and bytes with the Python standard library. No local model execution or checkpoint tensor decoding was used.

Cleanup observation: 2026-09-17T11:45:51.313048+00:00. All six lifecycle receipts confirm instance termination, role removal and security-group cleanup. A fresh scoped EC2 query returned the final two instances as terminated and did not return the four older IDs; absence alone is not treated as proof of termination. Private evidence buckets are retained.

Budget: six $7 reservations, $42 total for this study, no automatic retries. The campaign ledger is revision 84, with $501 reserved and $4,499 unreserved of the $5,000 authorized cap. Reservations are bounds, not invoices.

## Evidence

- [Frozen paired result](admission_001/paired_result.json)
- [Independent complete audit](independent_complete_audit_001.json)
- [Provider and budget observation](completion_provider_observation_001.json)
- [Frozen study admission](admission_001/study.json)
- [Independent work plan](independent_work_plan_001.json)
- [Supervisor log](supervisor_001.log)

| Record | SHA-256 |
| --- | --- |
| admission_001/study.json | 154dee19e678aa3520b47528100642d73303c836230abcb7db6bc02d242a5099 |
| admission_001/paired_result.json | b7df49aa479a97c37637489399a892115ded9f159036069f7e41abacca11139e |
| independent_complete_audit_001.json | 5f6b8dcbe3238135a52bf5954bf7d34ac44b495b6dd3a4919cbee7e6c30be022 |
| completion_provider_observation_001.json | f5b8e9752c1520094097994e0cd29f075068fcf5d3750a24991ec9667d02fe4b |

Source archive SHA-256: 2feff28c52fbbe5a230d4f1f32c936c9d9434bc514d5cf92d998fc917cbc72fc.

The earlier negative three-seed recurrence result remains unchanged. The full CNCM vision remains active and incomplete. These three development pairs, conditional on one encoder and one course, do not establish general CAS superiority, recursive learning from the viewer, a final-set result, or completion of the machine.
