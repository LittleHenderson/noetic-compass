# Approved $4 prefix diagnostic — completed

The AWS diagnostic completed successfully. All 480 generated actions matched the saved development actions. The trained models can make some correct choices when given the correct earlier steps, but lose many comparable decision points when generating programs on their own. This is a diagnosis of existing checkpoints, not new training or a new held-out result.

## What actually ran

- Job: `cas-meta2-20260906133828-cff56f29`.
- Instance: `i-0c6b7ad96bd295e99`, `g7.2xlarge`, one NVIDIA RTX PRO 4500 Blackwell Server Edition, AWS us-west-2.
- Python 3.12.3; torch 2.11.0+cu128; CUDA 12.8.
- Worker source: `13f424981d7434b1a92815d1ad5759d543bbd3be`.
- Launch parent: `39d0ed9b65683504d9335963bf57c7ac6ef1d78f`.
- 120 distinct development tasks: 24 training probes and 96 validation tasks. Each has equal task counts at reference depths 1, 2, and 3. Four saved checkpoints repeat this panel, making 480 rows and 9,088 reference decisions.
- All 480 row hashes passed. No missing result files. Worker wall time: 44.708691794 seconds; parent-launched worker process: 45.659185333 seconds.
- No training, native execution, B/R snapshot construction, or local model execution.

Validation tasks were previously used for checkpoint selection. This run does not test new task instances or unseen program combinations.

## Correct-prefix results on nested validation tasks

These scores supply the correct earlier program tokens before each choice. All denominators below are 128 choices, not 128 independent tasks. Grammar masking restricts predictions to allowed token choices. Depth 1 has no child-call sites.

| Model | Reference depth | Child choice: initial → selected | Child input: initial → selected |
|---|---:|---:|---:|
| CAS | 2 | 44/128 → 90/128 | 70/128 → 72/128 |
| CAS | 3 | 70/128 → 72/128 | 82/128 → 113/128 |
| Generic | 2 | 45/128 → 89/128 | 72/128 → 80/128 |
| Generic | 3 | 77/128 → 76/128 | 85/128 → 118/128 |

Improvement is uneven. CAS depth-3 child selection barely changed, and the generic model has stronger selected child-input scores. These results do not establish a CAS-specific advantage.

## Generating without the correct earlier steps

Only matching, legal, observed decision contexts receive a self-prefix score. Missing or changed contexts remain in the coverage denominator.

| Selected model | Reference depth | Child choice correct/scored; coverage | Child input correct/scored; coverage |
|---|---:|---|---|
| CAS | 2 | 30/41; 41/128 | 20/30; 30/128 |
| CAS | 3 | 22/26; 26/128 | 12/22; 22/128 |
| Generic | 2 | 42/58; 58/128 | 29/42; 42/128 |
| Generic | 3 | 24/29; 29/128 | 18/24; 24/128 |

For example, CAS depth-3 child selection is correct at 22 of 26 comparable sites, but only 26 of 128 reference sites remain comparable. Reporting 22/26 alone would hide most of the problem.

Across all four checkpoints, zero scored self-generated sites followed an earlier token-prefix difference. These scores do not measure recovery after a mistake.

The full offline analysis preserves raw-vocabulary versus grammar-masked scores, forced versus multiple-option choices, changed/missing contexts, termination counts, every checkpoint and cohort, and every measured role.

## Evidence and rerun entry points

- `authorization_001/user_message_full.txt`: full actual approval message.
- `authorization_001/owner_approval.json`: explicit $4 job binding and labelled verbatim approval-clause extraction.
- `authorization_001/execute_command.ps1`: exact executed AWS launch command. Historical command only; do not rerun it to analyze the saved result.
- `authorization_001/parent_process_completion.json`: observed parent exit 0.
- `execution_001/launch_receipt.json`: source identities, reservation, provider responses, collection and cleanup.
- `execution_001/cloud_artifacts.zip`: complete raw packet, including exact remote commands, installation reports, environment, all predictions, and raw outputs.
- `analyze_results.py` and `analysis_001/report.md`: offline score and coverage analysis.
- `analyze_first_errors.py` and `first_errors_001/`: offline first-transition analysis; token differences are not native task failures.
- `FINAL_RECEIPT.json`: final file hashes and cost/cleanup boundary.

Archive SHA-256: `c3bd5c9d4676f0d498894fb3f78115e85b1fa9ff3b8b64ad4a6c760675d13a09` (5,522,881 bytes).

## Cleanup, budget, and next step

The server's termination was confirmed at 2026-09-06T14:14:25.271138+00:00. Its temporary disk, schedule, instance profile, two job roles and security group were removed. Inputs were deleted from the dedicated bucket after the downloaded results were verified. The local results remain available; stored AWS results use the seven-day lifecycle rule (recorded expiry: 2026-09-14T00:00:00Z).

The canonical ledger reserved $4.00 for this run: revision 12, $82.00 total reserved, $318.00 unreserved within the existing $400.00 campaign cap. Reservations are not invoices or refunds.

Rounding the interval from launch request through confirmed termination up to 536 seconds gives a time-based compute estimate of $0.3752 at the checked $2.52/hour rate. Storage and request charges are separate. This estimate is not an AWS bill; the full $4 reservation remains recorded.

The earlier held-out CAS 0/72 result remains unchanged. The useful next learning target is one correct child call with correct input and surrounding structure, measured without supplying the answer. The separate B/R state-restoration work remains outside this diagnostic. Accepted model and executor files were not changed.
