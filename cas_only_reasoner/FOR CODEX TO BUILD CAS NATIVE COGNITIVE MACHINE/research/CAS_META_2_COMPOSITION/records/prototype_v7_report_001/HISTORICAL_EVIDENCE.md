# Historical evidence index for the v7 report

These are different experiments and different kinds of evidence. None supplies v7's pending score. Paths below are full local addresses; receipt hashes were checked while preparing this index.

## 1. Familiar-program fit: 0/24 → 24/24

Both CAS and generic freely generated all 24 correct program-and-binding targets after training, from 0/24 initially. There were eight known training examples at each of depths 1, 2, and 3. This measures familiar-example fit, **not native task correctness or held-out generalization**.

- Job: `cas-meta2-20260906054131-feae01a9`.
- Source: `6a71e01c3689a1debe56eed842f101dfa4990556`.
- [Recorded fit recount receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/fit_packet_review_v5_001/receipt.json>); status `RECORDED_FIT_RECOUNT_PASSED`.
- Receipt SHA256: `8da83bbd2f931c9a1735cb255104a88560bab221b37db8354447c3888bcaf0b4`.
- [Plain-English fit report](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_fit_v5_001/RESULTS.md>).

The receipt's epoch-0 history and final generation recount give the 0/24 and 24/24 values. It checks recorded scores and checkpoint bytes, not independent neural replay.

## 2. Earlier held-out composition negative: CAS 0/72; generic 12/72; rule 72/72

The later unchanged-checkpoint comparison rechecked the **already-exposed** earlier cases. It reproduced those counts in both decoder modes: CAS untrained/trained 0/72; generic untrained 0/72 and trained 12/72; rule 72/72. Do not call that retrospective comparison another fresh test.

- Comparison job: `cas-meta2-20260906032109-361b34a0`.
- Source: `9f562c761c7cb84c767673b2fab735cdd031b499`.
- [Independent stored-comparison receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_ablation_v4_stored_audit_002/stored_audit_receipt.json>); status `STORED_COMPARISON_AUDIT_PASSED`, completed true, no errors.
- Receipt SHA256: `3dc89119685d6c83ee33bc65019f8ea98ad58f6307613d77d1e95ba8e2502580`.
- [Comparison report](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_ablation_v4_002/RESULTS.md>) and [stored-audit scope](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_ablation_v4_stored_audit_002/README.md>).

Each mode has 72 references and 360 arm choices across 24 matched triplets. The modes reuse the same cases/checkpoints; they are not 144 new tasks. Better binding or trace validity did not yield correct CAS tasks.

## 3. Recovered v6: both models 0/72 before and after; rule 72/72

The separate recovery completed checking the original failed v6 run's sealed choices. It did **not** retrain, alter those choices, or create a fresh test. That original v6 training set had 640 records and **did not append the literal original 256**.

| Group | Attempts per arm | CAS before → after | Generic before → after | Rule |
|---|---:|---:|---:|---:|
| All | 72 | 0 → 0 | 0 → 0 | 72 |
| Depth 3 | 48 | 0 → 0 | 0 → 0 | 48 |
| Depth 4 | 24 | 0 → 0 | 0 → 0 | 24 |

- Recovery job: `cas-meta2-20260906082659-383a339d`.
- Source: `cbf13795202094865744f7c0b5efa234451f9208`.
- [Independent recovery receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_recovery_v6_review_001/run_001/recovery_stored_review.json>); status `RECOVERY_STORED_REVIEW_PASSED`, completed true, no errors.
- Receipt SHA256: `5396e0ab263fa435eefd2b8925382ce802b7af7c8d1c4dae5702d51435349ac3`.
- [Recovered-v6 report](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_recovery_v6_review_001/run_001/SUMMARY.md>).
- [Exact offline audit command and process receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_recovery_v6_review_001/execution_001/process_receipt.json>).

All 72 references and 360 saved choices were checked. CAS trained had 47 pre-execution rejections, 20 complete but wrong executions, and 5 post-start failures. Generic trained had 49, 17, and 6 respectively. Those failures remain incorrect attempts; missing compute remains unknown. This negative does not replace the earlier generic 12/72 result.

## 4. Historical META-3 correction at 63f5b421

Exact commit: `63f5b4210cc4df179193a5b5e3489ff48d79b3dd`.

The two supplied historical tracebacks (malformed learning record and wrong sidecar hash) stop during fixture construction in `source_identity()`, before the rejection checks. The exception is `PROTECTED_BASELINE_BYTES_CHANGED`. The earlier claim that those rejection guards failed is **withdrawn**.

The later clean historical run checked each of the 13 exact reported IDs, all passing within a full **531-pass, one-warning** pure suite. This is one suite containing those 13 tests, not 544 tests. The two relevant guards were reached and produced their explicit rejection receipts.

| Exact test ID | Later rerun |
|---|---|
| `tests/test_native_demo.py::test_import_is_pure_and_native_sources_are_literal_pinned` | PASS |
| `tests/test_native_demo.py::test_fixed_expectation_is_independent_and_passes_unchanged_pure_native_admission` | PASS |
| `tests/test_native_demo.py::test_stage_parent_receipts_record_exit_before_a_reader_can_be_requested` | PASS |
| `tests/test_native_demo.py::test_fresh_child_discovers_all_pinned_runtime_sources_without_neural_import` | PASS |
| `tests/test_packet_inspection.py::test_full_synthetic_byte_packet_preserves_all_bytes_and_sidecars` | PASS |
| `tests/test_packet_inspection.py::test_partial_packet_never_supplies_completed_semantic_audit_inputs` | PASS |
| `tests/test_packet_inspection.py::test_resealed_malformed_records_do_not_pass[gpu]` | PASS |
| `tests/test_packet_inspection.py::test_resealed_malformed_records_do_not_pass[runtime]` | PASS |
| `tests/test_packet_inspection.py::test_resealed_malformed_records_do_not_pass[command]` | PASS |
| `tests/test_packet_inspection.py::test_resealed_malformed_records_do_not_pass[source]` | PASS |
| `tests/test_packet_inspection.py::test_resealed_malformed_records_do_not_pass[native]` | PASS |
| `tests/test_packet_inspection.py::test_resealed_malformed_records_do_not_pass[learning]` | PASS |
| `tests/test_packet_inspection.py::test_wrong_sidecar_hash_cannot_reach_semantic_audit` | PASS |

All **316** protected files matched both the exact Git blobs and checkout bytes before/after: zero missing files and zero mismatches. Therefore a missing-baseline or non-self-contained-commit explanation is **not established by this local evidence**. The original auditor's exact mismatching path and expected/actual hashes remain unavailable. The other eleven original failures lack individual full tracebacks, so their historical causes are not assigned by analogy. Line endings remain only a possible checkout difference, not a proven cause.

- [Per-case reconciliation receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/receipt.json>); SHA256 `49d4f88227218680efb2623c3a222fd79d4fcc47245314476ce3fcb4ecd9c230`.
- [Full explanation and exact source lines](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/README.md>).
- [Raw JUnit results](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/tests.xml>) and [raw test output](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/test_stdout.txt>).
- [316-file comparison before](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/baseline_before.json>) and [after](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/baseline_after.json>); both SHA256 `3134149fa0e332ecde8fa3830abfd045e258906ed8e51fc852a64ba8ebba208d`.
- [Reached learning-record rejection](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/inspection_learning.json>): `META3_DEMO_SCOPE_OR_COUNTS_MISMATCH`.
- [Reached wrong-sidecar rejection](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/inspection_sidecar.json>): `TRUSTED_DEMO_SIDECAR_BINDING_MISMATCH`.
- [Frozen validator command, environment and dependency checks](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_3_PROCEDURAL_MEMORY/records/historical_per_case_reconciliation_002/validation_receipt.json>).

Required historical Git objects and sibling packages must be present for reproduction. This bounded audit used an existing Python environment, not a fresh wheel install. It changed no accepted runtime, guard, or model weight and proves no model capability.

## 5. Current v7 — assembly observed; results pending

The [saved public observation](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_prototype_v7_observation_001/status_20260906T095315185201.json>) at **2026-09-06 09:53:16 UTC** reports 896 training records (128/384/384 at depths 1/2/3), 96 validation records (32 each), 72 test variants (48 depth 3 / 24 depth 4), and 256 imported training records. Observation SHA256: `8297dc59efb0ade489669ce5de7bb599aa745bf06772815f0cbab6270992530f`.

The observation records assembly receipt SHA256 `0547a6cf730272c409cf4e4e691679df5591aa368c34e71d6835cc327d104f91`; this report preparation did not open that current receipt or private dataset. It also is not a new live status check.

- [Registered v7 specification](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/EXPERIMENT_PROTOTYPE_V7.json>); SHA256 `d054f7c29810e02fc581eb2f86cf98e1eeb10489cb34dd9f2a0b6cc6aa0d74c8`.
- [Exact original 256 practice records](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_curriculum_v6_probe_001/tasks.json>); SHA256 `ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46`. Known training data, never fresh held-out evidence.
- [Final clean-source receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/clean_source_prototype_v7_002/run_003/receipt.json>); SHA256 `d761a19b9db1cc469b2439e44da8fda98460064fb88e22b28a276bff929c10c3`. Source `42f9164754312f12850d9b8789c062fa7fb8069f`: 1,908 functions and 356 subtests passed; 603 closed source inputs and 316 protected files matched. This pure test result is not a learning score.
- [Unfilled final report](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_report_001/FINAL_REPORT_TEMPLATE.md>). Current native scores, checked checkpoints, complete audit, final compute/cost and cleanup: **PENDING**.

Matched training conditions are defined in [the v7 trainer](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/contrast_v7/train.py:143>) and [policy construction](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/policy_v3.py:162>). These source files were read as text, not imported. Their SHA256 values are recorded in the source index. Matching steps and approximate parameter counts is not a claim of matching time or FLOPs.

Hashes identify these specific saved records. They do not convert documentary evidence into an independent rerun of GPU arithmetic.
