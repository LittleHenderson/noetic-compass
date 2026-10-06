# Historical CAS Harness V1-V4 recovery inventory

Date: 2026-08-05  
Recovery source: `d9c1879762233855cd5974676b8179b1e4e75d16`  
Preserved V3 terminal commit: `c638df99a799e79afcb9739478bcc52a197b91d1`  
Recovery mode: local-only, exact Git-source bytes, no model execution

## Outcome

The approved historical CAS Harness V1-V4 paths were recovered into the current worktree from `d9c1879762233855cd5974676b8179b1e4e75d16`. That revision descends from `c638df99a799e79afcb9739478bcc52a197b91d1`, so one source tree contains both the preserved V3 terminal evidence and the V4 preparation. A supplemental recovery then added the exact frozen V1 worker dependency and its exact historical test from the same `d9c18797...` source.

The initial pre-restore collision audit covered 535 source files and the supplemental preflight covered two more. All 537 targets were absent before their respective restore. There were zero divergent files, zero worktree deletions of tracked targets, zero path-type conflicts, and zero extra files in the five closed historical directories. No current or user file was overwritten.

After recovery, all 537 current files are byte-identical to their Git blobs at `d9c1879762233855cd5974676b8179b1e4e75d16`. Their combined size is 95,945,579 bytes. The canonical current-tree inventory SHA-256 is:

`361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f`

The canonicalization rule and all 537 per-file SHA-256 values are in `HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json`. That report is 262,902 bytes with SHA-256 `29651aab7e8b0ff0d8d7082d9878da36ffefe7a9532d6bc8dcb1f319882c9b82`.

## Recovered scope

| Scope | Files |
|---|---:|
| `docs/working/research_intervention_pythia160m_v1/` | 6 |
| `docs/working/research_intervention_pythia160m_v2/` | 16 |
| `docs/working/research_intervention_pythia160m_v3/` | 489 |
| `docs/working/research_intervention_pythia160m_v4/` | 4 |
| `docs/working/research_intervention_pythia160m_v4_execution/` | 5 |
| Approved service files | 11 |
| Approved tests | 6 |
| **Total** | **537** |

Recovered service files:

- `cas_harness_pythia160m_research_lock.py`
- `cas_harness_pythia160m_research_executor.py`
- `cas_harness_pythia160m_research_auditor.py`
- `cas_harness_pythia160m_research_executor_v3.py`
- `cas_harness_pythia160m_research_auditor_v3.py`
- `cas_harness_pythia160m_v3_bootstrap.py`
- `cas_harness_pythia160m_layer_specificity_v4.py`
- `cas_harness_pythia160m_layer_specificity_executor_v4.py`
- `cas_harness_pythia160m_layer_specificity_auditor_v4.py`
- `cas_harness_pythia160m_layer_specificity_bootstrap_v4.py`
- `cas_harness_research_intervention_worker.py`

Recovered tests:

- `test_cas_harness_pythia160m_research_lock.py`
- `test_cas_harness_pythia160m_research_executor.py`
- `test_cas_harness_pythia160m_v3_startup.py`
- `test_cas_harness_pythia160m_layer_specificity_v4.py`
- `test_cas_harness_pythia160m_layer_specificity_execution_v4.py`
- `test_cas_harness_research_intervention_worker.py`

No files were recovered outside this list. In particular, `live-trace-worker`, `src/cas_harness_v2`, Gate 0/1/4 manifests, the Project Coherence charter, and the canonical production TODO were untouched.

## Frozen-hash verification

The verifier checked 48 V3/V4 frozen or preserved file records and every recovered source blob:

- 47 of 48 frozen records match their recorded byte counts and SHA-256 values.
- All 472 V3 raw float32 logit artifacts match their per-record SHA-256 values.
- V3 raw-logit total: 94,973,952 bytes.
- All 537 recovered files match their exact `d9c18797...` Git blob bytes.

One historical terminal binding is internally inconsistent and therefore is **not independently byte-closed**:

| V3 `result.json` form | Bytes | SHA-256 |
|---|---:|---|
| Exact committed `d9c18797...` LF blob | 467,781 | `141e910385bcbda3494dd6ddca7a933d6dad9b7a1b37ef192de6497811b207bd` |
| Terminal-manifest CRLF expectation | 478,182 | `bb9d68c06b86a69b3507b579761356d0d9db8c9396d6268c8255b63aedead90e` |

Replacing each LF in the committed blob with CRLF deterministically produces exactly 478,182 bytes and SHA-256 `bb9d68c06b86a69b3507b579761356d0d9db8c9396d6268c8255b63aedead90e`. This proves the mismatch is line-ending normalization, but it does not make the two byte claims equivalent. The recovery preserves the exact committed Git blob and does not normalize, repair, or reinterpret the historical packet.

Classification:

`HISTORICALLY_INCONSISTENT / NOT_INDEPENDENTLY_BYTE_CLOSED / FAIL_CLOSED`

## Static/model-free test result

The five previously approved historical modules reran with Hugging Face offline flags, an empty CUDA device selection, disabled research/live feature flags, and no model execution:

`43 passed, 4 failed in 28.99s`

The four failures are evidence, not repaired tests:

1. `test_prior_v1_lock_fails_closed_after_successor_executor_exists` now passes the restored worker check and stops on the next missing frozen V1 file, `cas_harness_research_intervention_auditor.py`. That file remains outside this two-file supplemental recovery scope.
2. `test_future_execute_missing_receipt_fails_before_framework_import_or_output` expects the V3 run root to be absent. The preserved terminal V3 run root now exists, so the preparation-only validation correctly stops earlier. This is the stale post-run assertion already described by the historical validation notes.
3. `test_v4_lock_validates_model_free` fails on the V3 `result.json` byte-count mismatch above.
4. `test_v3_terminal_packet_is_hash_bound_and_not_modified` fails on the same LF/CRLF mismatch.

The exact restored V1 worker test was also run separately. Its 31 tests all stop on the missing `scenarios/research_intervention_plan_v0.json`; the paired `research_intervention_synthetic_fixture_v0.json` is also absent. Those frozen fixtures exist in `d9c18797...` but were outside this explicitly bounded two-file supplement. Result:

`31 failed in 1.39s / HISTORICAL_FIXTURE_DEPENDENCIES_ABSENT`

The independent recovery verifier at `tests/cas_harness_v2/test_historical_v1_v4_recovery.py` passed `4 passed in 0.39s`. It recomputes every current file's SHA-256 and raw Git-blob SHA-1 against the `d9c18797...` tree, recomputes the 537-file inventory digest, reproduces the LF-to-CRLF terminal mismatch exactly, confirms the preserved V4 guard-name defect, and asserts the remaining V1 dependency boundary.

The V3 startup compatibility fixture imported the pinned frameworks only; it loaded no tokenizer or model. The V1 worker source itself has no `torch` or `transformers` imports. There was no V4 execution, model inference, generation, successful network connection, provider call, paid compute, receipt creation, receipt validation for execution, nonce creation, or nonce consumption.

## Known V4 pre-receipt defect

The recovered V4 executor remains historically exact and contains the later-confirmed startup defect:

- `cas_harness_pythia160m_layer_specificity_executor_v4.py:443` calls `base.ZeroNetworkGuard()`.
- The immutable delegate defines `CompatibleZeroNetworkGuard` at `cas_harness_pythia160m_research_executor.py:77`; it does not define `ZeroNetworkGuard`.

This recovery does not fix that defect. The canonical controlling status remains:

`PYTHIA160M_V4_FAIL_CLOSED_PRE_RECEIPT / NO RECEIPT / NO NONCE / RUN_NOT_STARTED / RESEARCH_ONLY / OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT`

The V3 terminal status remains:

`PYTHIA160M_V3_FAIL_CLOSED / CONTROL_EFFECT_CEILING_FAIL:wrong_layer / NON_REUSABLE / NO RETRY / RESEARCH_ONLY / OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT`

## Boundary

This is historical source and evidence recovery only. It does not change a claim, Gate 5, Gate 2, `ACCEPT`, `LICENSED`, production readiness, or product behavior. The recovered V3 receipt and nonce remain consumed and non-reusable. V4 remains unexecutable under its historical lock and current controlling status.
