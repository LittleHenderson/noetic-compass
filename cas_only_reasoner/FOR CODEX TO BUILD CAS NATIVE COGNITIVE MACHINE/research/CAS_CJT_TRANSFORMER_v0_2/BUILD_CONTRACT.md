# Complete Neural CJT build contract

Status: `COMPLETE FOR THE v0.2 LOCAL MECHANISM PROTOTYPE`

This status is intentionally narrow. It means that one local PyTorch and
SQLite prototype satisfies the 15 behaviors below in one integrated scenario.
It does not mean that a complete CAS-native Transformer, production CNCM
integration, general reasoning, or AGI exists. It also does not show a CAS
learning or reasoning advantage.

## Frozen inputs

Owner specification:

- `C:/Users/wakil/.codex/attachments/fc70cd22-904f-4b20-8f48-0a3b7af0f2e8/pasted-text.txt`
- bytes: `26900`
- SHA-256: `73B44675DABA9A46BE68E0E6B68BB3A482D49B05901D987142A60C88D49E2AEA`

Frozen neural-engine dependency:

- `../CASFORMER_v0_1`
- source aggregate SHA-256:
  `324603ABFDCBA59CB68D7351D822F612C2409DCD396D42E9E91FD3DF2BBE091E`

## Completion rule and test result

The integrated acceptance test is:

```text
tests/test_integrated_runtime.py::test_complete_four_cjt_reasoning_transistor
```

It runs A -> B -> C -> repair R -> resumed C in one durable store. The focused
tests named below supply negative and edge-case evidence. The required full
v0.2 completion check is:

```powershell
python -m pytest -q -p no:cacheprovider
```

The executable tests validate the implementation behavior. The prose and
diagrams are reviewed artifacts; no test claims to prove the truth of a design
document.

The final command results, environment, source fingerprint, and package hashes
are recorded in `artifacts/VALIDATION_RECEIPT.json`. That receipt is local
same-task evidence, not a signature or independent certification.

## Reconciliation rule

CAS-Ohm is the internal neural flow law, but it has no authority to decide
truth or authorize a write. Hard topology, permission, readiness, quarantine,
and budget gates run first. CAS-Ohm then routes only the admitted neural paths
inside an invoked CJT. A separate verifier classifies its candidate Effect. A
separate sole-writer coordinator validates and atomically commits or rejects
the proposed transition.

The current `cncm` runtime is not modified or relabeled. The v0.2 adapter emits
only an inert future-facing candidate envelope. A later, explicit CNCM runtime,
KIR, and authority revision is still required for admission.

## Fifteen required integrated behaviors

| ID | Required behavior | Exact executable evidence | Status |
|---|---|---|---|
| RT-01 | Receive a typed Cause | `tests/test_types_and_schemas.py::test_cause_requires_structured_content_provenance_and_effect_parent`; integrated test above | COMPLETE |
| RT-02 | Read persistent Bias | `tests/test_types_and_schemas.py::test_bias_contains_exactly_six_typed_parts_and_binds_cjt`; integrated test checks the retained recurrent Bias digest after restart | COMPLETE |
| RT-03 | Keep Desire, Wisdom, and Power separate | `tests/test_neural_core.py::test_dwp_preserves_three_hard_axes_and_wire_reasons`; `tests/test_types_and_schemas.py::test_readiness_axes_are_independent_hard_gates` | COMPLETE |
| RT-04 | Route through CAS-Ohm conductance | `tests/test_neural_core.py::test_router_preserves_current_flow_and_semantic_twin`; `test_all_closed_routes_have_exact_zero_and_no_uniform_fallback`; `test_closed_route_has_zero_control_and_score_gradients` | COMPLETE |
| RT-05 | Select a canonical CJT transform | `tests/test_neural_core.py::test_operation_registry_marks_only_decompose_canonical_and_binds_contract`; `test_relation_contract_mismatch_fails_before_neural_execution` | COMPLETE |
| RT-06 | Produce a neural candidate Effect | `tests/test_neural_core.py::test_neural_candidate_comes_only_from_gated_cjt_effect`; `test_neural_zero_flow_and_breakdown_fail_closed_with_zero_gradient` | COMPLETE |
| RT-07 | Make an Effect the next CJT's Cause | Integrated test above; `tests/test_types_and_schemas.py::test_cause_requires_structured_content_provenance_and_effect_parent` | COMPLETE |
| RT-08 | Use an independent accept/reject verifier | `tests/test_neural_core.py::test_verifier_keeps_operating_and_semantic_axes_independent`; `test_verifier_abstains_without_evidence_and_quarantines_stale_binding`; `test_candidate_producer_cannot_be_its_own_verifier` | COMPLETE |
| RT-09 | Open a bounded next-tick repair | Integrated test proves rejection at tick 3, repair at tick 4, resume at tick 5, and an atomically retained, sealed `RepairOutcome`; `tests/test_types_and_schemas.py::test_repair_is_next_tick_bounded_and_return_requires_effect` validates both repair record types | COMPLETE |
| RT-10 | Propose a Bias or parameter update | Integrated test commits a recurrent Bias and a scoped C-operation model intent; `tests/test_types_and_schemas.py::test_gradient_update_requires_external_tensor_artifact` | COMPLETE |
| RT-11 | Commit or roll back through one authorized coordinator | `NetworkAtomicCoordinator` is the sole v0.2 semantic writer; `tests/test_network_coordinator.py::test_poisoned_mixed_memory_batch_writes_nothing_authoritative` checks semantic admission. The trusted compatibility harness supplies atomic-storage evidence through `tests/test_persistence_coordinator_trace.py::test_every_fault_point_rolls_back_the_whole_batch` and `test_stale_and_mixed_invalid_batches_write_nothing`; `test_single_bias_coordinator_rejects_every_state_update_before_write`, `test_single_bias_coordinator_rejects_model_updates_before_write`, `test_single_bias_coordinator_rejects_resealed_qualification_arithmetic`, and `test_single_bias_coordinator_fails_closed_on_repair_frames` prove the harness cannot bypass the network authority boundary. | COMPLETE |
| RT-12 | Survive a real process restart | Integrated test launches a separate Python process and checks the state, model, version, and integrity; `tests/test_persistence_coordinator_trace.py::test_atomic_commit_idempotency_restart_and_public_redaction` | COMPLETE |
| RT-13 | Use changed Bias in later inference | Integrated test reloads the runtime, binds the retained recurrent Bias artifact, and observes a different candidate tensor digest | COMPLETE |
| RT-14 | Refuse or reverse an invalid update | Integrated test rejects a C-authorized update that changes A's bytes and checks an unchanged head/model/Effect set; `tests/test_governed_learning.py::test_invalid_learning_proposals_leave_active_bytes_unchanged`; `tests/test_persistence_coordinator_trace.py::test_compensating_rollback_is_a_new_commit_and_survives_restart` | COMPLETE |
| RT-15 | Reconstruct a complete sealed transition | Integrated test reconstructs every trace and detects a tampered database; `tests/test_persistence_coordinator_trace.py::test_integrity_semantically_reconstructs_every_older_trace`; `test_selected_reconstruction_binds_trace_payload_to_trace_row`; `test_double_rollback_reconstruction_closes_transitive_origins`; `test_resealed_model_manifest_cannot_skip_versions`; `tests/test_integrated_runtime.py::test_persistence_rejects_resealed_malformed_network_biases`; `test_trace_tamper_and_chain_discontinuity_are_detected` | COMPLETE |

These are not 15 disconnected demonstrations. The integrated test exercises all
15 behaviors in one four-CJT episode, while the focused tests test failure
boundaries.

## Ten required deliverables

| ID | Deliverable | Artifact and exact executable evidence | Status |
|---|---|---|---|
| D-01 | Implemented architecture diagram | `ARCHITECTURE.md`; integrated test above exercises the diagram's main path | COMPLETE |
| D-02 | Formal Neural CJT equations | `EQUATIONS.md`; `tests/test_neural_core.py::test_router_preserves_current_flow_and_semantic_twin` and `test_native_plan_is_exact_deterministic_and_not_changed_by_neural_current` | COMPLETE |
| D-03 | Typed Bias-state schema | `cas_cjt/schemas/bias_state.schema.json`; `tests/test_public_api.py::test_standalone_bias_state_schema_is_strict_and_self_contained` | COMPLETE |
| D-04 | Module and API contracts | `API_CONTRACTS.md`; `tests/test_public_api.py::test_version_and_declared_public_surface_are_stable` and `test_documented_entry_point_signatures_are_visible_at_package_root` | COMPLETE |
| D-05 | Full inference tick | `cas_cjt/runtime.py::NeuralCJTRuntime.inference_tick`; integrated test checks all 11 phases; `tests/test_types_and_schemas.py::test_tick_trace_requires_exact_eleven_phase_order_and_no_extras` | COMPLETE |
| D-06 | Full learning tick | `cas_cjt/runtime.py::NeuralCJTRuntime.learning_tick`; integrated test; `tests/test_governed_learning.py::test_staged_learning_clips_large_gradient_and_never_mutates_active_model` | COMPLETE |
| D-07 | Deterministic CNCM boundary | `CNCM_INTEGRATION_BOUNDARY.md` and `cas_cjt/cncm_bridge.py`; `tests/test_cncm_bridge.py::test_absent_or_malicious_neural_core_cannot_change_deterministic_shell` and `test_bridge_source_has_no_current_cncm_import_or_privileged_construction` | COMPLETE AS PROPOSAL-ONLY BOUNDARY |
| D-08 | Minimal end-to-end prototype | `examples/complete_reasoning_transistor.py`; integrated test above; direct command documented in `README.md` | COMPLETE |
| D-09 | Staged path from CASformer to a CJT network | `ROADMAP.md`; integrated test is the executable stage-6 milestone | COMPLETE AS ROADMAP ARTIFACT |
| D-10 | Four-operation registry and expansion path | `OPERATION_EXPANSION.md`; `tests/test_neural_core.py::test_fifth_operation_requires_registration_and_exact_contract_binding` and `test_extension_registration_cannot_override_builtins_or_relation_channels` | COMPLETE AS EXTENSION MECHANISM |

## Mandatory tick order

Every committed inference and learning transition records exactly:

```text
READ -> CANDIDATE -> READINESS -> ROUTE -> EXECUTE -> OBSERVE
-> VERIFY -> DIAGNOSE -> EMIT -> COMMIT -> TRACE
```

The trace contains required fields for each phase and binds the Cause, pre-state
head, pre-model head, candidates, evidence, verifier receipts, intents, compute
records, and proposed post-state.

## Precise claim boundary

This contract establishes local mechanism integration only. It does not
establish natural-language understanding, useful general reasoning,
continual-learning safety, a CAS advantage, biological validity, hardware
equivalence, formal verification, cryptographic identity, independent
timestamping, WORM storage, security, scalability, production readiness,
current CNCM admission, or AGI. Bias memory names candidate Effect history
explicitly; authoritative Published Effects remain separate commit records.
The prototype's `QUARANTINE` disposition fails one candidate closed but does
not persistently change owner-governed quarantine state. Its repair episode
proves bounded next-tick routing, exact return, and atomic closure; it does not
prove that a synthetic repair corrected the original semantic error.

Accordingly, “complete” means that this local prototype satisfies the owner's
15-behavior definition of the first complete neural CJT. It does not mean that
the complete CAS-native Transformer or its intended larger machine exists.
