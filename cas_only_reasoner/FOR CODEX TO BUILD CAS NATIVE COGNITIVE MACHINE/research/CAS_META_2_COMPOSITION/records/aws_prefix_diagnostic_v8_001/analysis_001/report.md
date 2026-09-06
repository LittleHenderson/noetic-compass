# Saved-prefix diagnostic: offline JSON report

COMPLETE_DIAGNOSTIC_JSON_ANALYZED

Existing development checkpoints and tasks only. No new training, fresh held-out generalization, native task correctness, rule-arm measurement, or CAS-specific advantage is established. Unmatched contexts have no assigned local correctness. Grammar-complete output is not task success.

Archive SHA-256: `c3bd5c9d4676f0d498894fb3f78115e85b1fa9ff3b8b64ad4a6c760675d13a09`

Task rows analyzed: 480/480. All diagnostic row hashes verified: True.

Saved-development action agreement: 480/480; mismatches: 0.

Scores below are correct/scored. Own-prefix coverage is scored/scheduled references. N/A means no scored opportunity, not zero accuracy. Depth is reference-task depth.

## Child selection and CALL-input binding: multiple options only

| Checkpoint | Partition | Depth | Role | Assisted raw | Assisted masked | Own raw | Own masked | Own coverage |
|---|---|---:|---|---:|---:|---:|---:|---:|
| cas_initial | train_probe | 2 | call_target | 0/32 | 13/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 2 | call_input | 10/32 | 14/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 3 | call_target | 0/32 | 17/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 3 | call_input | 20/32 | 21/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | validation | 2 | call_target | 0/128 | 44/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 2 | call_input | 60/128 | 70/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 3 | call_target | 0/128 | 70/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 3 | call_input | 80/128 | 82/128 | N/A (0) | N/A (0) | 0/128 |
| cas_selected | train_probe | 2 | call_target | 32/32 | 32/32 | 29/29 | 29/29 | 29/32 |
| cas_selected | train_probe | 2 | call_input | 31/32 | 31/32 | 28/29 | 28/29 | 29/32 |
| cas_selected | train_probe | 3 | call_target | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | train_probe | 3 | call_input | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | validation | 2 | call_target | 90/128 | 90/128 | 30/41 | 30/41 | 41/128 |
| cas_selected | validation | 2 | call_input | 72/128 | 72/128 | 20/30 | 20/30 | 30/128 |
| cas_selected | validation | 3 | call_target | 71/128 | 72/128 | 22/26 | 22/26 | 26/128 |
| cas_selected | validation | 3 | call_input | 112/128 | 113/128 | 12/22 | 12/22 | 22/128 |
| generic_initial | train_probe | 2 | call_target | 0/32 | 12/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 2 | call_input | 14/32 | 14/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 3 | call_target | 0/32 | 18/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 3 | call_input | 20/32 | 22/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | validation | 2 | call_target | 0/128 | 45/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 2 | call_input | 62/128 | 72/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 3 | call_target | 0/128 | 77/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 3 | call_input | 80/128 | 85/128 | N/A (0) | N/A (0) | 0/128 |
| generic_selected | train_probe | 2 | call_target | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 2 | call_input | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 3 | call_target | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 3 | call_input | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | validation | 2 | call_target | 89/128 | 89/128 | 42/58 | 42/58 | 58/128 |
| generic_selected | validation | 2 | call_input | 80/128 | 80/128 | 29/42 | 29/42 | 42/128 |
| generic_selected | validation | 3 | call_target | 74/128 | 76/128 | 24/29 | 24/29 | 29/128 |
| generic_selected | validation | 3 | call_input | 118/128 | 118/128 | 18/24 | 18/24 | 24/128 |

## Completion, reproduction and missing opportunities

| Checkpoint | Partition | Depth | Rows | Saved matches | Mismatches | Termination | Extra sites |
|---|---|---:|---:|---:|---:|---|---:|
| cas_initial | train_probe | 1 | 8/8 | 8 | 0 | {"GRAMMAR_DEAD_END": 8} | 106 |
| cas_initial | train_probe | 2 | 8/8 | 8 | 0 | {"GRAMMAR_DEAD_END": 8} | 75 |
| cas_initial | train_probe | 3 | 8/8 | 8 | 0 | {"GRAMMAR_DEAD_END": 8} | 36 |
| cas_initial | validation | 1 | 32/32 | 32 | 0 | {"GRAMMAR_DEAD_END": 32} | 439 |
| cas_initial | validation | 2 | 32/32 | 32 | 0 | {"GRAMMAR_DEAD_END": 32} | 179 |
| cas_initial | validation | 3 | 32/32 | 32 | 0 | {"GRAMMAR_DEAD_END": 32} | 250 |
| cas_selected | train_probe | 1 | 8/8 | 8 | 0 | {"COMPLETE": 8} | 0 |
| cas_selected | train_probe | 2 | 8/8 | 8 | 0 | {"COMPLETE": 8} | 1 |
| cas_selected | train_probe | 3 | 8/8 | 8 | 0 | {"COMPLETE": 8} | 0 |
| cas_selected | validation | 1 | 32/32 | 32 | 0 | {"COMPLETE": 32} | 0 |
| cas_selected | validation | 2 | 32/32 | 32 | 0 | {"COMPLETE": 21, "GRAMMAR_DEAD_END": 11} | 140 |
| cas_selected | validation | 3 | 32/32 | 32 | 0 | {"COMPLETE": 16, "GRAMMAR_DEAD_END": 16} | 235 |
| generic_initial | train_probe | 1 | 8/8 | 8 | 0 | {"GRAMMAR_DEAD_END": 8} | 113 |
| generic_initial | train_probe | 2 | 8/8 | 8 | 0 | {"GRAMMAR_DEAD_END": 8} | 77 |
| generic_initial | train_probe | 3 | 8/8 | 8 | 0 | {"GRAMMAR_DEAD_END": 8} | 35 |
| generic_initial | validation | 1 | 32/32 | 32 | 0 | {"GRAMMAR_DEAD_END": 32} | 452 |
| generic_initial | validation | 2 | 32/32 | 32 | 0 | {"GRAMMAR_DEAD_END": 32} | 187 |
| generic_initial | validation | 3 | 32/32 | 32 | 0 | {"GRAMMAR_DEAD_END": 32} | 225 |
| generic_selected | train_probe | 1 | 8/8 | 8 | 0 | {"COMPLETE": 8} | 0 |
| generic_selected | train_probe | 2 | 8/8 | 8 | 0 | {"COMPLETE": 8} | 0 |
| generic_selected | train_probe | 3 | 8/8 | 8 | 0 | {"COMPLETE": 8} | 0 |
| generic_selected | validation | 1 | 32/32 | 32 | 0 | {"COMPLETE": 32} | 2 |
| generic_selected | validation | 2 | 32/32 | 32 | 0 | {"COMPLETE": 22, "GRAMMAR_DEAD_END": 10} | 86 |
| generic_selected | validation | 3 | 32/32 | 32 | 0 | {"COMPLETE": 6, "GRAMMAR_DEAD_END": 26} | 268 |

Correspondence totals: {"CONTEXT_CHANGED": 2656, "MATCHED": 2477, "SITE_MISSING": 3955}.

The JSON lists mismatching task IDs, correspondence/legality counts for every group, and each earliest comparable wrong decision. That decision is not automatically the first error in the full trajectory.

<details><summary>All roles: multiple-option scores</summary>

| Checkpoint | Partition | Depth | Role | Assisted raw | Assisted masked | Own raw | Own masked | Own coverage |
|---|---|---:|---|---:|---:|---:|---:|---:|
| cas_initial | train_probe | 1 | observation_binding | 0/8 | 2/8 | 0/8 | 2/8 | 8/8 |
| cas_initial | train_probe | 1 | run_input | 0/56 | 28/56 | N/A (0) | N/A (0) | 0/56 |
| cas_initial | train_probe | 1 | parent_return | 0/8 | 1/8 | N/A (0) | N/A (0) | 0/8 |
| cas_initial | train_probe | 2 | observation_binding | 0/8 | 4/8 | 0/8 | 4/8 | 8/8 |
| cas_initial | train_probe | 2 | call_target | 0/32 | 13/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 2 | call_input | 10/32 | 14/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 2 | run_input | 0/58 | 4/58 | N/A (0) | N/A (0) | 0/58 |
| cas_initial | train_probe | 2 | parent_return | 0/8 | 0/8 | N/A (0) | N/A (0) | 0/8 |
| cas_initial | train_probe | 2 | child_return | 0/24 | 0/24 | N/A (0) | N/A (0) | 0/24 |
| cas_initial | train_probe | 3 | observation_binding | 0/8 | 2/8 | 0/8 | 2/8 | 8/8 |
| cas_initial | train_probe | 3 | call_target | 0/32 | 17/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 3 | call_input | 20/32 | 21/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 3 | run_input | 8/54 | 8/54 | N/A (0) | N/A (0) | 0/54 |
| cas_initial | train_probe | 3 | parent_return | 0/8 | 0/8 | N/A (0) | N/A (0) | 0/8 |
| cas_initial | train_probe | 3 | child_return | 0/24 | 0/24 | N/A (0) | N/A (0) | 0/24 |
| cas_initial | validation | 1 | observation_binding | 0/32 | 10/32 | 0/32 | 10/32 | 32/32 |
| cas_initial | validation | 1 | run_input | 0/234 | 90/234 | N/A (0) | N/A (0) | 0/234 |
| cas_initial | validation | 1 | parent_return | 0/32 | 8/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | validation | 2 | observation_binding | 0/32 | 8/32 | 0/32 | 8/32 | 32/32 |
| cas_initial | validation | 2 | call_target | 0/128 | 44/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 2 | call_input | 60/128 | 70/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 2 | run_input | 33/194 | 51/194 | N/A (0) | N/A (0) | 0/194 |
| cas_initial | validation | 2 | parent_return | 0/32 | 0/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | validation | 2 | child_return | 5/96 | 5/96 | N/A (0) | N/A (0) | 0/96 |
| cas_initial | validation | 3 | observation_binding | 0/32 | 8/32 | 0/32 | 8/32 | 32/32 |
| cas_initial | validation | 3 | call_target | 0/128 | 70/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 3 | call_input | 80/128 | 82/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 3 | run_input | 28/196 | 64/196 | N/A (0) | N/A (0) | 0/196 |
| cas_initial | validation | 3 | parent_return | 0/32 | 0/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | validation | 3 | child_return | 0/96 | 0/96 | N/A (0) | N/A (0) | 0/96 |
| cas_selected | train_probe | 1 | observation_binding | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| cas_selected | train_probe | 1 | run_input | 56/56 | 56/56 | 56/56 | 56/56 | 56/56 |
| cas_selected | train_probe | 1 | parent_return | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| cas_selected | train_probe | 2 | observation_binding | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| cas_selected | train_probe | 2 | call_target | 32/32 | 32/32 | 29/29 | 29/29 | 29/32 |
| cas_selected | train_probe | 2 | call_input | 31/32 | 31/32 | 28/29 | 28/29 | 29/32 |
| cas_selected | train_probe | 2 | run_input | 58/58 | 58/58 | 47/47 | 47/47 | 47/58 |
| cas_selected | train_probe | 2 | parent_return | 8/8 | 8/8 | 7/7 | 7/7 | 7/8 |
| cas_selected | train_probe | 2 | child_return | 24/24 | 24/24 | 19/19 | 19/19 | 19/24 |
| cas_selected | train_probe | 3 | observation_binding | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| cas_selected | train_probe | 3 | call_target | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | train_probe | 3 | call_input | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | train_probe | 3 | run_input | 54/54 | 54/54 | 54/54 | 54/54 | 54/54 |
| cas_selected | train_probe | 3 | parent_return | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| cas_selected | train_probe | 3 | child_return | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| cas_selected | validation | 1 | observation_binding | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | validation | 1 | run_input | 230/234 | 230/234 | 221/224 | 221/224 | 224/234 |
| cas_selected | validation | 1 | parent_return | 29/32 | 29/32 | 26/28 | 26/28 | 28/32 |
| cas_selected | validation | 2 | observation_binding | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | validation | 2 | call_target | 90/128 | 90/128 | 30/41 | 30/41 | 41/128 |
| cas_selected | validation | 2 | call_input | 72/128 | 72/128 | 20/30 | 20/30 | 30/128 |
| cas_selected | validation | 2 | run_input | 169/194 | 169/194 | 22/22 | 22/22 | 22/194 |
| cas_selected | validation | 2 | parent_return | 14/32 | 14/32 | 0/2 | 0/2 | 2/32 |
| cas_selected | validation | 2 | child_return | 40/96 | 42/96 | N/A (0) | N/A (0) | 0/96 |
| cas_selected | validation | 3 | observation_binding | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | validation | 3 | call_target | 71/128 | 72/128 | 22/26 | 22/26 | 26/128 |
| cas_selected | validation | 3 | call_input | 112/128 | 113/128 | 12/22 | 12/22 | 22/128 |
| cas_selected | validation | 3 | run_input | 161/196 | 161/196 | 20/22 | 20/22 | 22/196 |
| cas_selected | validation | 3 | parent_return | 32/32 | 32/32 | 10/10 | 10/10 | 10/32 |
| cas_selected | validation | 3 | child_return | 39/96 | 39/96 | N/A (0) | N/A (0) | 0/96 |
| generic_initial | train_probe | 1 | observation_binding | 0/8 | 2/8 | 0/8 | 2/8 | 8/8 |
| generic_initial | train_probe | 1 | run_input | 0/56 | 28/56 | N/A (0) | N/A (0) | 0/56 |
| generic_initial | train_probe | 1 | parent_return | 0/8 | 1/8 | N/A (0) | N/A (0) | 0/8 |
| generic_initial | train_probe | 2 | observation_binding | 0/8 | 4/8 | 0/8 | 4/8 | 8/8 |
| generic_initial | train_probe | 2 | call_target | 0/32 | 12/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 2 | call_input | 14/32 | 14/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 2 | run_input | 4/58 | 10/58 | N/A (0) | N/A (0) | 0/58 |
| generic_initial | train_probe | 2 | parent_return | 0/8 | 0/8 | N/A (0) | N/A (0) | 0/8 |
| generic_initial | train_probe | 2 | child_return | 0/24 | 0/24 | N/A (0) | N/A (0) | 0/24 |
| generic_initial | train_probe | 3 | observation_binding | 0/8 | 2/8 | 0/8 | 2/8 | 8/8 |
| generic_initial | train_probe | 3 | call_target | 0/32 | 18/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 3 | call_input | 20/32 | 22/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 3 | run_input | 8/54 | 10/54 | N/A (0) | N/A (0) | 0/54 |
| generic_initial | train_probe | 3 | parent_return | 0/8 | 0/8 | N/A (0) | N/A (0) | 0/8 |
| generic_initial | train_probe | 3 | child_return | 0/24 | 0/24 | N/A (0) | N/A (0) | 0/24 |
| generic_initial | validation | 1 | observation_binding | 0/32 | 10/32 | 0/32 | 10/32 | 32/32 |
| generic_initial | validation | 1 | run_input | 0/234 | 88/234 | N/A (0) | N/A (0) | 0/234 |
| generic_initial | validation | 1 | parent_return | 0/32 | 8/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | validation | 2 | observation_binding | 0/32 | 8/32 | 0/32 | 8/32 | 32/32 |
| generic_initial | validation | 2 | call_target | 0/128 | 45/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 2 | call_input | 62/128 | 72/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 2 | run_input | 41/194 | 55/194 | N/A (0) | N/A (0) | 0/194 |
| generic_initial | validation | 2 | parent_return | 0/32 | 0/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | validation | 2 | child_return | 5/96 | 5/96 | N/A (0) | N/A (0) | 0/96 |
| generic_initial | validation | 3 | observation_binding | 0/32 | 8/32 | 0/32 | 8/32 | 32/32 |
| generic_initial | validation | 3 | call_target | 0/128 | 77/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 3 | call_input | 80/128 | 85/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 3 | run_input | 41/196 | 64/196 | N/A (0) | N/A (0) | 0/196 |
| generic_initial | validation | 3 | parent_return | 0/32 | 0/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | validation | 3 | child_return | 0/96 | 0/96 | N/A (0) | N/A (0) | 0/96 |
| generic_selected | train_probe | 1 | observation_binding | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 1 | run_input | 56/56 | 56/56 | 56/56 | 56/56 | 56/56 |
| generic_selected | train_probe | 1 | parent_return | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 2 | observation_binding | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 2 | call_target | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 2 | call_input | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 2 | run_input | 58/58 | 58/58 | 58/58 | 58/58 | 58/58 |
| generic_selected | train_probe | 2 | parent_return | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 2 | child_return | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| generic_selected | train_probe | 3 | observation_binding | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 3 | call_target | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 3 | call_input | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 3 | run_input | 54/54 | 54/54 | 54/54 | 54/54 | 54/54 |
| generic_selected | train_probe | 3 | parent_return | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 3 | child_return | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| generic_selected | validation | 1 | observation_binding | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | validation | 1 | run_input | 228/234 | 229/234 | 226/232 | 227/232 | 232/234 |
| generic_selected | validation | 1 | parent_return | 30/32 | 30/32 | 26/27 | 26/27 | 27/32 |
| generic_selected | validation | 2 | observation_binding | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | validation | 2 | call_target | 89/128 | 89/128 | 42/58 | 42/58 | 58/128 |
| generic_selected | validation | 2 | call_input | 80/128 | 80/128 | 29/42 | 29/42 | 42/128 |
| generic_selected | validation | 2 | run_input | 178/194 | 178/194 | 25/25 | 25/25 | 25/194 |
| generic_selected | validation | 2 | parent_return | 16/32 | 16/32 | 1/1 | 1/1 | 1/32 |
| generic_selected | validation | 2 | child_return | 45/96 | 45/96 | N/A (0) | N/A (0) | 0/96 |
| generic_selected | validation | 3 | observation_binding | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | validation | 3 | call_target | 74/128 | 76/128 | 24/29 | 24/29 | 29/128 |
| generic_selected | validation | 3 | call_input | 118/128 | 118/128 | 18/24 | 18/24 | 24/128 |
| generic_selected | validation | 3 | run_input | 168/196 | 168/196 | 38/42 | 38/42 | 42/196 |
| generic_selected | validation | 3 | parent_return | 32/32 | 32/32 | 17/17 | 17/17 | 17/32 |
| generic_selected | validation | 3 | child_return | 31/96 | 31/96 | 2/2 | 2/2 | 2/96 |

</details>

<details><summary>Grammar-forced choices, reported separately</summary>

| Checkpoint | Partition | Depth | Scheduled | Assisted raw | Assisted masked | Own raw | Own masked | Own coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| cas_initial | train_probe | 1 | 8 | 0/8 | 8/8 | N/A (0) | N/A (0) | 0/8 |
| cas_initial | train_probe | 2 | 32 | 0/32 | 32/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | train_probe | 3 | 32 | 16/32 | 32/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | validation | 1 | 32 | 0/32 | 32/32 | N/A (0) | N/A (0) | 0/32 |
| cas_initial | validation | 2 | 128 | 3/128 | 128/128 | N/A (0) | N/A (0) | 0/128 |
| cas_initial | validation | 3 | 128 | 46/128 | 128/128 | N/A (0) | N/A (0) | 0/128 |
| cas_selected | train_probe | 1 | 8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| cas_selected | train_probe | 2 | 32 | 32/32 | 32/32 | 28/28 | 28/28 | 28/32 |
| cas_selected | train_probe | 3 | 32 | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | validation | 1 | 32 | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| cas_selected | validation | 2 | 128 | 128/128 | 128/128 | 32/32 | 32/32 | 32/128 |
| cas_selected | validation | 3 | 128 | 128/128 | 128/128 | 40/40 | 40/40 | 40/128 |
| generic_initial | train_probe | 1 | 8 | 0/8 | 8/8 | N/A (0) | N/A (0) | 0/8 |
| generic_initial | train_probe | 2 | 32 | 0/32 | 32/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | train_probe | 3 | 32 | 18/32 | 32/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | validation | 1 | 32 | 0/32 | 32/32 | N/A (0) | N/A (0) | 0/32 |
| generic_initial | validation | 2 | 128 | 3/128 | 128/128 | N/A (0) | N/A (0) | 0/128 |
| generic_initial | validation | 3 | 128 | 65/128 | 128/128 | N/A (0) | N/A (0) | 0/128 |
| generic_selected | train_probe | 1 | 8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| generic_selected | train_probe | 2 | 32 | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | train_probe | 3 | 32 | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | validation | 1 | 32 | 32/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| generic_selected | validation | 2 | 128 | 128/128 | 128/128 | 33/33 | 33/33 | 33/128 |
| generic_selected | validation | 3 | 128 | 128/128 | 128/128 | 49/49 | 49/49 | 49/128 |

</details>

Mean negative log-likelihood, all-score totals and complete subgroup counts are retained in analysis.json.
