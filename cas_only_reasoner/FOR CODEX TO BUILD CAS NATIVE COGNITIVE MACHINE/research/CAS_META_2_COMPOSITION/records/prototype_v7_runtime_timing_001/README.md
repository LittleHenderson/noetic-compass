# V7 recorded native timing — not a GPU profile

The saved record contains a substantial amount of work, but it does not identify why case 45 missed the deadline. Its selected generic program calls for **39 native runs versus 11 in the checked reference**, with 37 committed runs saved. That is a workload warning, not proof of a deadlock or a measured hardware bottleneck.

## What these timings cover

This check hashes each input against the already pinned full extraction and partial-native receipts. It reads 71 whole-case receipts, their 355 arm timings, the three separate saved rejected arms from case 45, and the native process receipt. All input members are rehashed afterward. It executes no model, tensor operation, task, database, or provider call.

The frozen evaluator permits eight concurrent workers. Within each case, the private reference runs first; the five arms then run in their registered order. Reference time includes its identity check and verification. Arm time includes admission, execution or failure-prefix checking, verification, identity checks and result writes. These are not isolated CUDA-kernel times.

## Recorded durations for the common 71 completed cases

| Arm | Recorded status | Cases | Mean seconds | Maximum seconds |
|---|---|---:|---:|---:|
| CAS trained | EXECUTED | 12 | 192.461 | 486.065 |
| CAS trained | POST_ADMISSION_RUNTIME_FAILURE | 1 | 6.788 | 6.788 |
| CAS trained | REJECTED | 58 | 0.047 | 0.048 |
| CAS untrained | REJECTED | 71 | 0.048 | 0.050 |
| Generic trained | EXECUTED | 14 | 152.431 | 196.069 |
| Generic trained | POST_ADMISSION_RUNTIME_FAILURE | 4 | 15.664 | 49.981 |
| Generic trained | REJECTED | 53 | 0.047 | 0.048 |
| Generic untrained | REJECTED | 71 | 0.047 | 0.070 |
| Rule | EXECUTED | 71 | 111.416 | 197.407 |

These rows deliberately cover the common 71, not the whole 72 assigned tasks. CAS trained has one additional rejected arm in case 45. CAS untrained and generic untrained also have their separate case-45 rejection receipts. Generic trained's unfinished duration and the rule's unstarted duration are **unknown/not available**, not zero measurements.

Whole-case recorded durations range from 66.353 to 585.796 seconds, with mean 200.204 seconds. Their sum is 14,214.512 worker-seconds. Workers overlap, so this sum is **not** elapsed cloud time or billed time. The actual enclosing native process recorded 2,700.688235096 seconds before failure.

The record has no final case-45 worker receipt, exact start time, finished generic arm duration, or per-tick GPU profile. It does not locate the worker's last instruction. The next sealed node 37 and the first recorded mismatch at RUN index 2 remain separate facts. No longer timeout, added compute allowance, retry or new launch is applied.

## Reproduce the read-only count

From the META2 package directory:

```powershell
./records/prototype_v7_runtime_timing_001/check.ps1
```

The script prints JSON and does not write files. `receipt_001.json` preserves the interpreted result, while `command_capture_001.json` preserves the exact executed command and tool-returned output text. That tool text is not claimed as an independent original child-stream capture.

Receipt SHA256: `ae09f901270f6ac14bdb650b6e7540fd8e1c3b918d2066df64b1dbf54fdcc5da`.
Read-only script SHA256: `9d9e982b9ab6f4d2e97cc65f99e7c7174737ff48719bd8d85868408c975300b8`.
Source remains `42f9164754312f12850d9b8789c062fa7fb8069f`; original partial audit remains `bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f`.

The next performance decision needs measured execution/verification timing if it is to distinguish GPU cost from host work and concurrency. These saved elapsed totals do not settle that question. This diagnosis does not alter the failed learning result or expand spending authority.
