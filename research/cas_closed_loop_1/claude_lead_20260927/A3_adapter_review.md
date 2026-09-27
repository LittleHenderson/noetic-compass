# A3 adapter review — research/cas_closed_loop_1 @ aa600668 (amendment f6253e1a)

Read-only. No repo imports executed. Evidence: static reading of HEAD vs provenance/producer_8f55cc3a snapshot,
the pinned runtime (`_runtime/cncm`, bytes verified equal to git blob 8182ad52), stdlib-only CPython probes on
3.11.15 and 3.12.3 (`scratchpad/probe_setprofile.py`), and the two local lead runs at HEAD
(`claude_lead_20260927/run_20260927T04{5459,5944}Z/pytest.xml`: 61 collected, 3 failed).

## Verdict: CHANGES_REQUIRED

All three DeepSeek items are implemented and, on inspection, correct. But the amendment's own regression tests for
items 1 and 3 cannot run: `test_native_step_adapter.py` uses `TerminalStatus` at L138/L142/L285 while the name is
imported only function-locally at L102. Result at HEAD: `test_no_frame_has_no_return_identity_before_during_and_after_root_call`
and `test_work_join_refuses_records_removed_from_trace_bound_state[False|True]` fail with NameError (reproduced twice).
The acceptance boundary (HARNESS_SPEC "Acceptance boundary": all cases must run and pass on the frozen source) is unmet,
and the central item-3 rule (self-consistent resealed state refused) has zero executable coverage.
Fix: add `from cncm.model import TerminalStatus` at module scope of the test file. Corroboration: a sibling run with only that
line added (`scratchpad/PATCH_test_native_step_adapter_import.diff`, `wt_patch_pytest.xml`) shows 61/61 passing, including the three
cases above — so the adapter logic for items 1 and 3 is verified by those tests once they can execute; the defect is the test import only.

## Item 1 — no-frame return_identity: IMPLEMENTED
- `native_step_adapter.py:238,249-250`: identities only from `state.rpm_stack`; `return_identity = identities[-1] if identities else None`;
  the producer's `identity(None)` fallback (fabricated `source_snapshot=state.state_hash`) is gone. `:243-248` keep state/root context separately;
  `:253-255` atlas_binding/profile_coordinates None + READ_ONLY authority. Frame ids embed push-time state_hash (`compound_kernel.py:133-136`), so the
  unique-suspension lookup (`:221-222`) cannot false-positive within an episode.
- Tests: `test_all_eleven_identity_fields...:101-124` PASSES and covers both branches in-loop (None/[] when no frames; 11 fields + top-frame equality otherwise).
  `test_no_frame_has_no_return_identity...:127-143` FAILS (NameError L138) — MAJOR. `test_runtime_location_is_detached...:91-98` and
  `test_closed_loop.py:137-139` (root_call instead of return_identity) PASS.
- NOTE: runtime_location reads `machine.state`/`coordinator.trace` after `result()` rather than the validated result's fields (equivalent, inconsistent with item 3).

## Item 2 — I_executed <= I_allocated, exact dispatch, meter breach: IMPLEMENTED
- `verify_receipt :60-66` exact-int (bool rejected) `0<=I_executed<=I_allocated<=1` + recomputed digest; `StepGrant :86-87`; exact bound-method identity
  (`__self__`, `__func__ is _ADVANCE`, `__code__`) `:290-293` before any entry; busy hook refused `:295-296`; meter `:297-306`; `entry_refused` ->
  `InvalidNativeObservation` with no receipt `:316-319`. `control.py:86-96` pops/re-digests; counters untouched so `verify_receipt` holds
  (asserted `test_closed_loop.py:73`, replay `run_closed_loop.py:108`).
- Tests (all PASS): repeated-dispatch wrapper x3 `:146-167`; internal re-entry clears meter `:170-193`; rehashed over-allocation `:196-201`;
  substituted callable `:204-209`; digest alteration `:212-216`; native fault keeps I_executed=1 + verify_receipt `:69-88`; grant validation `:53-58`.
- MAJOR (trust-model-dependent): the meter is per-thread. Patch `CompoundMachine._execute` to run `orig_advance(self, allow_acquisition=True)` once in a
  `threading.Thread` (join) after the real step: second entry is neither counted nor refused; chain/prefix/budget checks pass (events are genuine);
  a receipt with `I_executed=1` for two real entries is returned and verifies. Probe case C confirms on 3.11 and 3.12. Same threat class as the in-scope
  re-entry test; needs no hook change or native mutation. Harden with `threading.setprofile(entry_meter)` for the window and/or refuse if
  `threading.active_count()` changed, or narrow the spec claim to same-thread entries.
- NOTE: hook-clearing re-entry (`sys.setprofile(None)` inside patched `_execute`) is explicitly out of scope, but `if sys.getprofile() is not entry_meter`
  in the `finally` would catch it (and the exception-cleared case) for free. NOTE: `I_attempted` unconstrained by verify_receipt (always
  `int(calls and enabled)` at HEAD). NOTE: 3.12 `sys.getprofile()` cannot see sys.monitoring tools; they do not disturb the meter (probe E/F).
  NOTE: L320 branch unreachable.

## Item 3 — state-bound work join: IMPLEMENTED
- `:141-144` `machine.result()` first (ContractError -> WORK_STATE_HISTORY_INVALID) before any record read; `:146-149` catalog and event map from
  `observed.final_state`/`observed.trace`; `:152-157` sealed/hash/equality per event; `:181-182` `catalog_state_binding`. Refusal of a resealed state comes from
  `compound_engine.py:55` (`state.state_hash != last post_state_hash or trace_head != last event_hash`); `result()` is not memoized (`:257-262`);
  `machine.state` is the live StateStore object (`nested_engine.py:158-160`, `kernel.py:141-142`); `CompoundState.to_dict` covers all record tuples.
- Tests: `test_work_join_refuses_records_removed_from_trace_bound_state[False|True]:282-302` — the ONLY coverage of the resealed rule and the binding —
  FAILS (NameError L285) — MAJOR. PASS: `test_empty_work_join_still_refuses_a_corrupt_state:305-308` (non-self-consistent hash only),
  `test_work_join_refuses_duplicate_and_changed_event:273-279`, `test_corrupt_existing_event_is_refused...:255-260`,
  `test_closed_loop.py:test_wrong_method_is_rejected...:100-115`, replay `run_closed_loop.py:118-132` via demo/fresh-process tests.
- MINOR: `observed` (validated result, L142) is shadowed by the report-body list at L169; harmless today, fragile. NOTE: `catalog_state_binding` has
  no consumer (execute_grant does not check it against `after`; replay skips it by design). NOTE: chain anchor is machine-private
  (`_episodes[-1].initial_state_hash`); a full state+last-event+trace_head rewrite passes `result()` (outside trust model; replay's caller-held digests catch it).

## Python 3.11 vs 3.12
No divergence found for the relied-upon semantics (hook exception clears profile and propagates; `f_locals['self']` at 'call'; method identity;
settrace coexistence) — identical on 3.11.15 and 3.12.3. NameError failures are interpreter-independent; AWS worker enforces 3.12 (`worker.py:64`).
`test_launch_transport` needs boto3/botocore (2 extra failures in the first local run without them) — wheelhouse concern, not adapter.
