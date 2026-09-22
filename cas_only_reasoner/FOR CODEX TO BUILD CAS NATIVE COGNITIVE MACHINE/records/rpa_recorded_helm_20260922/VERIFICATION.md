# Retained Helm workbench verification — 2026-09-22

This is an engineering verification record, not a model certificate. The source
run remains Helm 2.0-experimental, NOT_CERTIFIED / NO_TRANSFER_TO_NEW_WORLDS.
No model weights were decoded or loaded; no new inference or training ran.

## Starting state and source custody

- Starting local and remote atlas commit:
  `5b3d713c5e7f2b2fc2959aaf776d0d80ca09d256`.
- New isolated branch: `codex/helm-rpa-recorded-run-20260922`.
- Original atlas checkout was clean and is preserved. Main-checkout unrelated
  changes were not staged or edited. The newer separate `helm3-lab` head
  `86ba3d75431c56147f229f24794805a3d8504f76` does not replace this atlas or
  demonstrate Q4 neural execution.
- Continuation attachment SHA-256:
  `76d7821ac2cb6e007df42c7143ab1a81aa22ef46e6a29c71e5bb42d40665d1f5`.
- Later retained acceptance records were found for the native, compound, scoped
  and cube adapters. Their original source-family and teacher boundaries remain
  unchanged; the older attachment's pending cube status was not promoted blindly.
- No protected final target is included in this development-only selection.
  Complete source identities and selection limits: `SOURCE_IDENTITIES.md`.

The active compiler SHA-256 is unchanged:
`9910a381a9eaba7f75cae8f325867bfe28766676d28b84a09b15e1bf9c10f79e`.
The active CAS-Ohm helper SHA-256 is unchanged:
`20cc15753b43115478c524b00cd015661b225cc57b3f686cdba824e4c2f67afb`.
The prior design-atlas artifacts, PCBA code, coordinate arithmetic and datasets
were not rebuilt or altered for this workbench.

## Current executed tests

Run from the CNCM directory with the installed Python 3.12 interpreter and
`PYTHONDONTWRITEBYTECODE=1`. Basetemp paths are disposable directories under
the outer CNCM homebase, not the retained source directories.

```powershell
python -m pytest tests/test_rpa_recorded_helm.py tests/test_rpa_recorded_helm_view.py tests/test_rpa_ohm_view.py -q -p no:cacheprovider --basetemp 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_test_runs\rpa_recorded_final_20260922' --tb=short --junitxml records/rpa_recorded_helm_20260922/recorded_and_shared_view_tests.xml
```

**75 passed in 62.68 seconds**: 56 retained-record adapter tests, 12 new view and
browser-cleanup tests, and 7 existing Ohm viewer tests. Includes actual Chrome
navigation, exact URI lookup, source stability, saved-view reload, unavailable
coordinates and measurements, mobile width and blocked external requests.

```powershell
python -m pytest tests/test_rpa_model.py tests/test_rpa_scoped_compound.py tests/test_rpa_view.py tests/test_rpa_coordinates.py tests/test_rpa_ohm_atlas.py research/helm_cas_expression_lab/test_cas_ohm_connections.py -q -p no:cacheprovider --basetemp 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_test_runs\rpa_recorded_legacy_20260922' --tb=short --junitxml records/rpa_recorded_helm_20260922/legacy_regression_tests.xml
```

**347 passed in 140.01 seconds**. Together these are **422 distinct passing RPA
and adapter tests**. Earlier repeat passes are not added to that count.
Q4 deterministic preparation tests and exact job metadata are recorded separately
in `q4_preparation/STATUS.md`; they are not learner executions.
The final Q4 suite passed **107 tests in 2.20 seconds**, making **529 distinct
engineering tests** across the three final groups. Its public RFC 8032 signature
test verifies the installed library only, not an owner approval. Final metadata
validation passed under the intended CUDA interpreter without importing Torch.
Plan SHA-256:
`af81383702c9695ae00ba831eac2ae9f28891d40eaa8075b90d3857723d0aa87`.
All ten runtime source pins match the staged Git bytes. The local GPU query
reported six compute PIDs; no process was stopped. Owner authorization was not
found, CUDA execution was not probed, and the proposed neural output does not
exist.

## Executed reproduction

```powershell
python tools/reproduce_recorded_helm_view.py
python tools/render_rpa_view.py records/rpa_recorded_helm_20260922/workbench/helm.json records/rpa_recorded_helm_20260922/workbench/rendered_again.html
```

Both completed successfully. The independent CLI rendering and generated
`workbench/helm.html` were byte-identical, SHA-256
`34ce37a286b02da2324276e4492d2cf836a999d41e57a51d3d54a6b291298405`
(1,849,451 bytes). The redundant second HTML is omitted from the committed pack.
`workbench/manifest.json` binds the generated artifacts; `verification.json`
records all exact address resolutions, both nested navigation checks, fixed
present, unchanged source and retained original checker outcomes.

Document identity:
`088b1d4f83d5533003860d028c6247ed88a03b620021ff64421a61a6fa166271`.
Selection identity:
`d181782419e3480a7f8b39e2bc3bce7eaa28cde21c44bb9abcd0c021bfcd7daf`.

The actual generated page was also captured in Chrome using
`python records/rpa_recorded_helm_20260922/capture_recorded_view.py`.
`browser_qa/browser_proof.json` binds the HTML/document hashes and records the
exact original prediction/checker JSON, fixed present, unavailable measurements,
zero JavaScript exceptions and zero external requests. Desktop correct, desktop
wrong and mobile wrong PNGs are retained. Desktop and mobile wrong-answer
screenshots were visually inspected: labels and records wrap, original and replay
answers stay distinct, and the page has no horizontal overflow.

## Failures retained and resolved

- Three initial backend tests failed because their temporary directories had not
  been created. The fixture setup was corrected; all 56 backend tests passed.
- An early browser attempt hit a restricted local WebSocket/cleanup failure.
  A Chrome parent-exit race could also mask the primary test error. The helper
  now tolerates taskkill exit 128 only when the owned parent has actually exited;
  two mock regressions and the real browser tests pass. Unrelated browsers are
  never terminated. `shared_view_initial_tests.xml` records the successful retry.
- The new browser test found that the shared exact lookup recognized only the
  design atlas URI prefix. `recorded_view_tests.xml` retains its 11-pass/1-fail
  result. Lookup now resolves only an exact source-bound address string from
  the loaded family; the final 75-test group passes.
- One shell invocation after task-context reset ran from the wrong directory and
  failed file-not-found without changing files; the command was rerun with the
  explicit new worktree directory.
- Q4 dependency installation/import attempts and the Windows long-path failure
  are retained in `q4_preparation/`; its final status distinguishes successful
  deterministic preparation from still-unavailable authorization and execution.

## Requirement mapping

| Checks | Evidence and boundary |
|---|---|
| A01–A03 | Pinned development source selection, exact task/input/original prediction/checker/model panels and pure checker replay. No final targets exported. |
| A04–A05 | Negative backend tests reject wrong joins, inner tampering with rehashed envelopes, source/manifest corruption and altered checker bytes. |
| A06–A07 | No thought trace is constructed. Saved learned predictions and deterministic references use distinct records and labels. |
| A08–A09 | All new profiles remain null; existing strict profile/order and permutation regression tests pass. |
| A10–A12 | Backend and real-browser navigation/reference/reload/foreign-address checks pass. Existing profile-identity tests remain unchanged. |
| A13–A14 | No new Ohm readings exist. Existing source/scale/component bindings and 3-versus-2 design tests pass; separate index link preserves declared-design identity. |
| A15–A16 | Bounds, inert hostile labels, content security policy, zero external requests and fresh-process saved-view restoration are covered by current browser tests. |
| A17 | 422 distinct impacted RPA/adapter tests passed in the two retained XML reports. |
| A18 | **NOT_RUN**. No new learner result, neural reload or causal learning intervention is claimed. |

The selected historical checkpoint is available as verified retained bytes, not
an executed model in this viewer. Current resource authorization and Q4 neural
execution remain separate open gates. No scientific benefit claim follows from
adapter or preparation tests.
