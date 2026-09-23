# Check accounting

These rows have different and overlapping scopes. Do not add them into a single test total.
Saved records repeated across seeds or checkpoints are observations, not fresh independent examples.
No full historical integrity certification was rerun and no neural checkpoint was loaded.

| Role | Newly executed test functions | Input-specific cases and observations | Execution/repetition | Failures and recovery |
|---|---:|---|---|---|
| A1 | 0 named test functions; 1 procedural probe | 50 unique held questions reused across 6 runs = 300 question/run cases; 127 presentations ×2 endpoints ×6 runs = 1,524 answer checks; 108 primary paired cases | 6 successful subject executions, each under 13s; no successful reruns | 1 partial run failed because reload files lacked full population; corrected to source-bound course_p00/p10 files. Truncated text reads and CRLF formatting-check failures preserved. Semantic checker and paired math reuse historical code. |
| A2 | 5 | 2 source ZIPs, 18 member copies, 6 unchanged-function comparisons; 1 symbolic 4-node path observed across 8 steps/version; 64 worlds, 70 analogy inputs, 2 selected witness inputs; 12 saved files/6,768 stored predictions, of which 840 analogy and 1,056 correspondence instances selected; 3 algebra sizes/32 permutations | Decisive suite 1 time, 0.647s; 0 repeat suites | Inspection failures and CRLF/source-byte formatting warnings logged. No neural execution. Saved endpoint instances overlap A1's population; they are not additional independent trials. |
| A3 | Pending first report | Pending | Pending | Pending |
| A4 | Pending first report | Pending | Pending | Pending |
| A5 | Not launched | Pending | Pending | Pending |
| A6 | Not launched | Pending | Pending | Pending |
| A7 | Not launched | Pending | Pending | Pending |

Root custody checks are file identity checks, not model/test behavior: 630 unique paths from 642 rows,
540 ZIP member rows, 3 frozen grader Git sources. Their exact attribution and limitations are in
coordinator/CUSTODY_LOG.md. Original worktree status-list equality does not hash unrelated dirty files.

Follow-up accounting will be appended after registered checks; first-report counts remain original.
