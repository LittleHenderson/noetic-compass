# Return-address addendum: the ten adapter-level cases, executed

Source rows: `RETURN_ADDRESS_TEST_MAP.json` (`new_adapter_case_needed`). Implementation: `atlas_address.py`, a read-only projection
that builds a snapshot-bound address from existing identities (run, branch, root call, the unique authorized push event, the frame,
and the atlas's `state-<hash>` / `frame-<frame_id>` node scheme with tick-bound contexts). Tests: `test_atlas_address.py`.

Result: **10 passed, 0 failed** in 55.99 s on Python 3.11.15, against the unmodified runtime and adapter. Local only; not in
the 61-case frozen suite; not AWS-executed. Codex's `runtime_location` still reports `atlas_binding: None` until it wires this module.

| Row | Acceptance ids | Required case | Test | Status |
|---:|---|---|---|---|
| 1 | AT15, AT20 | Bind each waiting frame to its own snapshot/node address | `test_row1_two_nested_frames_bind_distinct_snapshot_addresses_and_return_to_exact_callers` | EXECUTED_PASSED |
| 2 | AT16, AT17, AT19, AT27 | Wrong atlas address cannot choose another native continuation | `test_row2_wrong_address_cannot_select_another_continuation` | EXECUTED_PASSED |
| 3 | AT16, AT17, AT19, AT27 | Repeated view event cannot dispatch a new native request | `test_row3_repeated_resolution_dispatches_nothing` | EXECUTED_PASSED |
| 4 | AT10, AT21, AT22 | Preserve root/parent address chain across restart | `test_row4_address_chain_survives_fresh_process_recovery` | EXECUTED_PASSED |
| 5 | AT10, AT21, AT22 | Do not reconstruct budget from suspended snapshot | `test_row5_address_carries_no_budget_and_resume_uses_the_live_ledger` | EXECUTED_PASSED |
| 6 | AT24, AT25, AT26 | Equal/missing profiles cannot merge two call occurrences | `test_row6_equal_or_missing_profiles_never_merge_callers` | EXECUTED_PASSED |
| 7 | AT24, AT25, AT26 | Layout/recentering leaves return-address resolution unchanged | `test_row7_focus_and_hypothesis_changes_leave_resolution_unchanged` | EXECUTED_PASSED |
| 8 | AT10, AT21, AT27 | Adapter preserves one event/address association | `test_row8_one_suspension_event_per_address` | EXECUTED_PASSED |
| 9 | AT24, AT27 | No successful adapter view from tampered replay | `test_row9_tampered_view_or_journal_cannot_resolve` | EXECUTED_PASSED |
| 10 | AT25, AT27 | Use exact matching frame/snapshot, no nearest-node fallback | `test_row10_near_miss_snapshot_hash_is_refused_not_nearest` | EXECUTED_PASSED |

What each case proves and where its boundary is:

- **Row 1.** Two live frames get distinct snapshot nodes, frame nodes and digests; both resolve RESOLVED_LIVE_FRAME in a view rendered while suspended; the authorized RETURN_PRIMITIVE then RETURN_COMPOUND intents name exactly those frame ids in dependency order; root x=3 COMPLETE; in the final view both resolve RESOLVED_HISTORICAL_FRAME_NOT_LIVE. Boundary: The native exact return itself is upstream behavior (test_compound_kernel.py::test_real_nested_construction_installs_program_and_resumes_exact_parent at the runtime commit; not in the 61-case suite). This case binds that behavior to addresses; it does not re-prove the kernel.
- **Row 2.** A crossed address (outer suspension with the inner continuation) is refused SUSPENSION_EVENT_FRAME_MISMATCH; a foreign run id is refused SUSPENSION_EVENT_MISMATCH; the module exposes no resume/dispatch/commit/advance name; journal and stack unchanged. Boundary: Refusal at the address layer only. Native wrong-frame refusal is upstream (test_wrong_return_frame_cannot_resume_or_write_parent).
- **Row 3.** Five resolutions and five chain computations leave state hash, trace length, native budget and the journal byte-identical.
- **Row 4.** The suspended journal is recovered in a separate Python process (subprocess) with the caller-held journal digest; the recomputed chain, including both address digests and the root call occurrence, equals the original.
- **Row 5.** The address has no budget or remaining field; after the nested work completes the live ledger is strictly below the frame's entry budget; the entry budget stays in the continuation as history only.
- **Row 6.** Two occurrences with the same source profile and root goal but different inputs get different run ids, snapshot nodes, frame nodes and digests; one's address is refused in the other's view; a live frame of one machine is FRAME_NOT_LIVE on the other; supplied profile coordinates are refused PROFILE_COORDINATES_HAVE_NO_ADDRESS_ROLE. Boundary: Recorded fact: a machine started from byte-identical inputs is deterministic and reaches the identical run id and frame identities; that is the same episode identity, not a merge of two callers.
- **Row 7.** AtlasSnapshot.focus to another node and the flat_graph presentation give the same resolution (only the reported focus differs); the journal is unchanged. Boundary: The pinned atlas has no geometric layout; focus and flat/graph presentation are the existing view operations.
- **Row 8.** Two computations of the same frame's address are identical; swapping the suspension event hash for another event's hash is refused SUSPENSION_EVENT_MISMATCH; the unique authorized push event is the one bound.
- **Row 9.** A view whose snapshot node state_hash is altered is refused SNAPSHOT_NODE_MISMATCH; a view missing the waiting node is refused WAITING_NODE_NOT_FOUND; a truncated journal fails native recovery (ContractError) before any address exists; an altered address fails its digest.
- **Row 10.** An address whose snapshot hash differs in one hex digit is refused although the real node is present in the view; after the exact return the frame is FRAME_NOT_LIVE.

Nothing in this module resumes, dispatches, commits or advances. Profile coordinates and view focus are never inputs to resolution.
