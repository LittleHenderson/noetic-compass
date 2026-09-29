# A5 — Current joint-validation delivery: exact test inventory and execution package (2026-09-27)

Executed serially in the lead session (no worker; the harness cannot enforce exclusive files or spending
limits for a subagent, so none was dispatched). Machine-readable twin: `A5_ACCEPTANCE_PACKAGE_20260927.json`.

Claim states used here: **executed locally** = ran in Claude's container (Python 3.11.15) with a retained junit
record, an engineering check and not acceptance; **declared** = the test identity exists in source and Claude never
executed it; **not run in the admitted venue** = no AWS execution exists for this source.

## 1. Source identities and the successor check

| Item | Identity |
|---|---|
| CAS source (this branch head) | `7bbf1e0f7bae635126c05b3203cca706ea8654dc` on `claude/focused-mccarthy-uj45ul`, base `aa6006683d9e798c85667dc0d389a604b0e99053` |
| Native runtime | `8182ad52b4468f18f140837dffee0e7debcfe786` (108 files, `SOURCE_BINDINGS.json`, byte-frozen) |
| SI source (Codex) | `d7808d59c13ea94c6ff35d2327a4acb8535daabc`, tip of `codex/helm-si-three-lead-20260927` |
| Successor check | fetched 2026-09-27 about 13:00Z: `d7808d59` is still the branch tip; no successor commit; its `JOINT_ACCEPTANCE_PLAN.json` already names `corrected_cas_source` = `7bbf1e0f…`, `execute_authorized: false`, status `PREPARED_NOT_ADMITTED_NOT_RUN` |
| Public manifest | `e59767f232c0c6eec3918ab653ffd6c564d25506fd45663307527ceab56d6d6c` (154 rows verified in the 06:53Z recheck) |
| Python bytes since the last execution | `git diff --stat 0cb7b48d..7bbf1e0f -- '*.py'` is empty: every `.py` file executed in the packet-2 runs is byte-identical at this head |

No corrected defect is reopened here: R1 (import), R6 (thread meter), R7 (atlas addresses), R3/R8 (notes) stay
closed as recorded in `SHARED_RETURN_20260927.md`; SI-1/SI-2 stay open on Codex's side as recorded on the PR.

## 2. The owner's five acceptance items mapped to test identities

Counts are from the recorded case identities (`CASE_RECONCILIATION.json`, run `run_20260927T062546Z` and the
packet-2 lane run). "RPA addresses" is read as the return-point (atlas) addresses of `RETURN_ADDRESS_TEST_MAP.json`;
the lane's own history calls them `rpa-atlas`.

| Owner item | CAS test functions (file) | Cases | Last executed |
|---|---|---:|---|
| 1. Actual work allocation and execution measurement | `test_disabled_actuator_retains_allocation_without_execution`, `test_zero_grant_does_not_make_native_call`, `test_granted_step_observes_native_events_and_stale_reuse_is_refused`, `test_invalid_grant_never_reaches_executor[True,-1,2,1.0]`, `test_foreign_episode_refused_before_work`, `test_repeated_dispatch_wrapper_refused_before_native_entry[propagate,swallow,catch_then_third_call]`, `test_internal_reentry_that_clears_meter_never_publishes_a_count`, `test_rehashed_receipt_still_refuses_execution_above_allocation`, `test_substituted_callable_is_refused_before_entry`, `test_receipt_content_digest_detects_alteration`, `test_corrupt_existing_event_is_refused_even_for_zero_grant`, `test_unexecuted_window_has_zero_measured_primitive_work[False-1,True-0]`, `test_work_join_refuses_duplicate_and_changed_event`, `test_work_join_refuses_records_removed_from_trace_bound_state[False,True]`, `test_empty_work_join_still_refuses_a_corrupt_state`, `test_foreign_thread_entry_inside_window_never_publishes_a_count` (adapter); `test_real_repair_exact_return_checked_bias_effect_and_event_bound_work`, `test_wrong_method_is_rejected_and_failed_work_remains_charged` (closed loop); `test_row5_address_carries_no_budget_and_resume_uses_the_live_ledger` (addresses) | 26 | executed locally, all PASSED |
| 2. Exact nested caller return | `test_runtime_location_is_detached_and_has_no_coordinate_return_authority`, `test_all_eleven_identity_fields_and_suspended_snapshot_are_retained`, `test_no_frame_has_no_return_identity_before_during_and_after_root_call`, `test_real_repair_exact_return_checked_bias_effect_and_event_bound_work`, `test_row1_…_return_to_exact_callers`, `test_row2_wrong_address_cannot_select_another_continuation`, `test_row6_equal_or_missing_profiles_never_merge_callers`; record `NESTED_RETURN_TRACE.json` | 7 | executed locally, all PASSED |
| 3. Snapshot-bound RPA addresses | the eleven cases of `test_return_addresses.py` (`test_row1` … `test_row10`, `test_runtime_location_atlas_binding_is_the_address_chain_or_null`) | 11 | executed locally, all PASSED (packet-2 lane junit) |
| 4a. Wrong-method control | `test_wrong_method_is_rejected_and_failed_work_remains_charged`, `test_substituted_callable_is_refused_before_entry`, `test_foreign_loaded_control_dependency_is_not_admitted[compiler_ohm,pcba_check]`, `test_foreign_loaded_dependency_is_refused`, `test_wrong_problem_admission_is_refused`, `test_supported_boards_static_check_and_operation_mask[3 boards]` | 9 | executed locally, all PASSED |
| 4b. Insufficient-budget control | `test_bounded_negative_controls_cannot_commit[options0..3]` (`allow_acquisition False`, `NativeBudget(300, 100)`, `rpm_depth_limit 1`, `max_ticks 2`), `test_rehashed_receipt_still_refuses_execution_above_allocation`, `test_invalid_grant_never_reaches_executor[…]`, `test_row5_…` | 10 | executed locally, all PASSED |
| 4c. Incorrect-result control | `test_recovered_reuse_changed_inputs_wrong_effect_and_invalidation`, `test_corrupt_post_fault_state_is_not_published_as_verified`, `test_native_error_keeps_observed_events_and_never_reports_success`, `test_invalid_ohm_inputs_refused[1-0,NaN-1,Infinity-1,-1-1]`, `test_permission_mask_precedes_invalid_ratio_and_preserves_state`, `test_exact_pinned_ohm_calculation[12-4-3,12-6-2]`, `test_simulated_profile_is_not_admitted`, `test_row10_near_miss_snapshot_hash_is_refused_not_nearest` | 12 | executed locally, all PASSED |
| 4d. Disabled-actuator control | `test_disabled_actuator_retains_allocation_without_execution`, `test_disabled_actuator_keeps_prediction_and_grant_but_executes_nothing`, `test_unexecuted_window_has_zero_measured_primitive_work[False-1,True-0]` | 4 | executed locally, all PASSED |
| 5. Saved evidence, replay, fresh-process reload | `test_retained_exact_evidence_and_producer_bytes`, `test_changed_artifact_bytes_are_refused`, `test_changed_historical_producer_snapshot_is_refused`, `test_ambiguous_git_reference_is_refused[2]`, `test_fresh_process_replays_retained_journal`, `test_truncated_observation_refused_before_native_replay`, `test_row4_address_chain_survives_fresh_process_recovery`, `test_row9_tampered_view_or_journal_cannot_resolve`, `test_row3_repeated_resolution_dispatches_nothing`, the four `LaunchTransportTests` cases (evidence transport, offline); protocol steps `retained_replay`, `witness`, `fresh_process_replay` | 14 | executed locally, all PASSED; protocol steps PASS on `run_20260927T062546Z` |

A case may serve more than one item; the union is all 73 CAS cases, none unmapped. SI counterparts for items 4d
and 5 (Codex's files, declared by AST, **never executed by Claude**): `test_disabled_shadow_preserve_admitted_parent_and_record_measured_overhead[…]`,
`test_fabricated_baseline_config_refused_even_when_disabled`, `test_witness_reloads_in_a_fresh_process_with_same_host_admission`,
`test_replay_rejects_changed_public_copy_even_without_changing_semantics[…]`, `test_failure_preserves_native_work_and_has_no_retry`.

## 3. Declared versus executed

| Set | Declared (AST, per Codex's plan) | Executed by Claude | Where |
|---|---:|---:|---|
| Frozen four CAS files | 62 | 62 passed, 0 failed, 0 errors, 0 skipped | `run_20260927T062546Z`, junit sha256 `2f90bfdb37b8dbcb06cada6bb97088e21fdbd3f5aa21d1a44ab6d594f2e5f7c6` |
| `test_return_addresses.py` | 11 | 11 passed (13 with pointer and probe) | `test_return_addresses_junit_packet2.xml`, sha256 `63d6b3d195e9cbbaefc4f97731af0a1341c72b0ad9a105632576578cca05604f` |
| SI two files | 69 | 0 | never run by Claude |
| Joint | 142 | 0 in the admitted venue | `JOINT_ACCEPTANCE_PLAN.json`: `collected_node_ids null`, `executed false` |

Witness on the executed run: output `3`, 12 host entries, 18 native events; retained replay and fresh-process
replay `EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT`. All of this predates or was disclosed after Codex's 06:21Z
correction; nothing has been executed since `7bbf1e0f`, and nothing is authorized under the lease.

## 4. Exact next acceptance command and route

Route: Codex's established runner only. Claude launches nothing and holds no execution authority.

Joint command, verbatim from `JOINT_ACCEPTANCE_PLAN.json` at `d7808d59`:

```
HELM_SI_EXECUTION_VENUE=ADMITTED_AWS python -B -m pytest -q -p no:cacheprovider --basetemp=/opt/helm-si-output/pytest-temp --junitxml=/opt/helm-si-output/joint-junit.xml research/cas_closed_loop_1/test_native_step_adapter.py research/cas_closed_loop_1/test_closed_loop.py research/cas_closed_loop_1/test_artifacts.py research/cas_closed_loop_1/aws_validation/test_launch_transport.py research/cas_closed_loop_1/test_return_addresses.py research/helm_self_improvement/test_contracts.py research/helm_self_improvement/test_episode.py
```

Expected only if collection matches the declaration: `tests 142, failures 0, errors 0, skipped 0`. Collection in the
admitted venue decides the count; the complete suite is preserved and never lowered to a subset.

CAS-only alternative through the frozen protocol (four files, count 62):

```
python research/cas_closed_loop_1/aws_validation/package.py --freeze --wheelhouse <dir> --source 7bbf1e0f7bae635126c05b3203cca706ea8654dc --expected-tests 62 --authorization-file <owner file> --authorization-sha256 <sha>
python research/cas_closed_loop_1/aws_validation/launch.py --execute --job-directory <job dir> --freeze-sha256 <freeze sha>
```

`worker.py` then requires `tests == expected_tests` with zero failures, errors and skips, the retained replay against
bundle `eae7eb1b…`, the witness (`3`, 12, 18) and the fresh-process replay.

Dependencies Codex's plan pins: Python 3.12 (exact patch recorded), pytest 9.0.2, pydantic 2.12.5, pydantic_core 2.41.5,
boto3 1.43.87, botocore 1.43.87. Claude's local runs used Python 3.11.15; that difference is one more reason they are not acceptance.

## 5. Dependencies on Codex, exact

- **D1.** Re-cut freeze at `7bbf1e0f` (or a joint freeze schema) declaring the collected count, and the decision on
  whether `test_return_addresses.py` joins the frozen set. `worker.py` line 123 hardcodes the four files; the joint
  command lists seven, so the joint run needs a worker or freeze variant that is Codex's to cut.
- **D2.** The frozen concurrency identity is stale. `launch.py` lines 103-108 and `package.py` lines 213-216 permit
  exactly `i-0adf52b7fa801e08b` running job `cas-meta2-tpntr-20260925151836-b981625f-m-20260918` (the 2026-09-25
  seed-18 job). The seed-19 continuation runs on another instance, so the all-regions active-instance check
  (`launch.py` 217-221) raises `UNDECLARED_ACTIVE_INSTANCE_CONCURRENCY_BLOCK` unless the currently permitted instance
  is re-declared in a new freeze. Read from the code; not executed.
- **D3.** Owner-signed execution authorization and cost admission. `execute_authorized` is `false` at `d7808d59`; the
  prior `$1.00` CPU proposal was never executed; never freeze `fab6734e…`.
- **D4.** SI-1 and SI-2 (minor, Codex's files) are open at `d7808d59`; not collection blockers.

## 6. Smallest remaining concrete failure

None known in the CAS source at `7bbf1e0f`: the last executed runs on identical `.py` bytes passed 62/62 and 13/13.
The concrete gap is venue, not code: the 142-case joint suite has never been collected or executed in the admitted
AWS environment, and the frozen launcher would block on D2 if launched unchanged. One unexecuted item off the
acceptance path: `run_local_protocol.py` after the packet-3 `--expected-tests` change has not been run.

## 7. Claim boundary

Not `CAS_AWS_ENGINEERING_VALIDATED`. `RETAINED_RESEARCH_ONLY`, not `PROMOTED`. `$0` spent by Claude; no cloud,
model, provider or worker call; no HELM, Q4 or seed-19 file touched; CASalescence parked.
