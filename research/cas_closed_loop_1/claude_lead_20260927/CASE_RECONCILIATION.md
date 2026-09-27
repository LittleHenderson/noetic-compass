# Collected versus executed cases (Claude runs, for DeepSeek's reconciliation)

Expected count stays 61 (57 scientific + 4 launcher-transport). Case identities below come from each run's junit file.

| Run | Tree | Collected | Passed | Failed | Errors | Skipped |
|---|---|---:|---:|---:|---:|---:|
| `run_20260927T045459Z` | exact head aa600668, before boto3/botocore were installed | 61 | 56 | 5 | 0 | 0 |
| `run_20260927T045944Z` | exact head aa600668, pinned boto3/botocore 1.43.87 installed | 61 | 58 | 3 | 0 | 0 |
| `run_20260927T050137Z_patched_worktree` | aa600668 + PROPOSED_PATCH_test_native_step_adapter_import.diff, scratch worktree | 61 | 61 | 0 | 0 | 0 |

Failing case identities per run:

- `run_20260927T045459Z`: `research.cas_closed_loop_1.test_native_step_adapter::test_no_frame_has_no_return_identity_before_during_and_after_root_call`, `research.cas_closed_loop_1.test_native_step_adapter::test_work_join_refuses_records_removed_from_trace_bound_state[False]`, `research.cas_closed_loop_1.test_native_step_adapter::test_work_join_refuses_records_removed_from_trace_bound_state[True]`, `research.cas_closed_loop_1.aws_validation.test_launch_transport.LaunchTransportTests::test_get_and_emergency_put_presign_the_explicit_regional_endpoint`, `research.cas_closed_loop_1.aws_validation.test_launch_transport.LaunchTransportTests::test_non_s3_clients_keep_normal_service_endpoints`
- `run_20260927T045944Z`: `research.cas_closed_loop_1.test_native_step_adapter::test_no_frame_has_no_return_identity_before_during_and_after_root_call`, `research.cas_closed_loop_1.test_native_step_adapter::test_work_join_refuses_records_removed_from_trace_bound_state[False]`, `research.cas_closed_loop_1.test_native_step_adapter::test_work_join_refuses_records_removed_from_trace_bound_state[True]`
- `run_20260927T050137Z_patched_worktree`: none

Full per-case list with outcomes, commands, environment and source hashes: `CASE_RECONCILIATION.json`.

Claude never observed a 52-passed result. Reconciling that figure needs its exact source hash, command, junit and dependency list.
