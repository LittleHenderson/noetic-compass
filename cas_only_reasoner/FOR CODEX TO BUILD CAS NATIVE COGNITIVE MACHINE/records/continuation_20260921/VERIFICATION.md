# Continuation verification

All commands ran in the isolated `codex-helm-data` worktree with Python
`C:\Python314\python.exe` 3.14.0 and bytecode disabled. No neural model was
initialized or executed. Tests using neural/checkpoint/job objects are mocked.

| Check | Result |
|---|---|
| Compiler, nesting, new mechanical regressions, offline help, real module demo | 458 passed in 1.20 s |
| Foundations, frozen operation contracts, compiler facts, Q3 data/loader/export, initial Q4 | 304 passed in 124.47 s |
| Final Q4 interfaces, R2, checkpoint, authorization and supervisor mocks | 92 passed in 1.25 s; includes the earlier 48 Q4 tests |
| Original and canonical-identity conversation generator tests | 27 passed in 0.48 s |
| Existing evaluator-boundary scans against final learner files | 2 passed in 0.10 s; already included in the lab test count |
| TypeScript parser on CompilerPage.tsx | No parse diagnostics, TypeScript 6.0.2 |
| Q3 v0.7 build | 10,421 records, build pass |
| Q3 v0.7 schema export and read-only regeneration comparison | 10,421 valid records, all 12 exports match |
| Source/offline directory/ZIP compiler and terminal bytes | Exact equality |
| Recovered v0.5 versus v0.7 visible/target row files | All 24 files identical |
| Frozen engine/reference/operation contracts | No diff from recovered base |
| Q4 metadata-only preparation with explicit v0.7 | PREPARED_NOT_AUTHORIZATION |

The compiler LF SHA-256 is
`61ed5a45970459e49a6948282ce4060e7c3d3d3f7042078228bc97ff252b2527`.
`INTEGRITY.json` records the package, data and concurrent-source hashes.
`Q4_PREPARED_PLAN.json` binds the selected local environment, data, source and
caps. Its saved plan digest is
`3654bc2203cb2c9cf6390f0db4b72af3f7bfecde5dda98243fedd8075987e1df`.
Installed package metadata is not a GPU capacity or runtime-readiness test.
Preparing on AWS would require a new plan for that environment and a current
named-job authorization; no past allowance was reused.

## Exact test commands

Common environment: `PYTHONDONTWRITEBYTECODE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and `TEMP`/`TMP` set to a dedicated test
directory inside the CNCM homebase. The Q4 test key fixtures require that
directory to be outside the repository under test. They are TEST_ONLY keys.

From `noetic-compass-scaffold/noetic-compass`:

```powershell
C:/Python314/python.exe -B -m pytest --noconftest -o addopts= tests/test_notation_compiler.py tests/test_notation_compiler_nesting_and_defects.py tests/test_notation_compiler_continuation.py tests/test_offline_help_text_canon.py tests/test_full_demo_program.py -q -p no:cacheprovider --basetemp '../../_test_runs/compiler_final_all' --tb=short
```

From `research/helm_cas_expression_lab` inside the continuation CNCM folder:

```powershell
C:/Python314/python.exe -B -m pytest -o addopts= test_compiler_nesting_facts.py test_foundations28.py test_operation_contracts.py test_q3_behaviour_records.py test_q3_load_and_export.py test_q3_load_boundary.py test_q3_load_errors.py test_learner_q4.py -q -p no:cacheprovider --basetemp '../../../../_test_runs/lab_final' --tb=short
C:/Python314/python.exe -B -m pytest -o addopts= test_learner_q4.py test_q4_followup.py -q -p no:cacheprovider --basetemp 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_test_runs_codex_q4/final' --tb=short
C:/Python314/python.exe -B -m pytest -o addopts= test_q3_behaviour_records.py::test_no_learner_file_opens_sealed_data test_q3_load_and_export.py::test_no_learner_file_uses_an_evaluators_door -q -p no:cacheprovider --tb=short
C:/Python314/python.exe -B q3_export_behavior_pairs.py
C:/Python314/python.exe -B learner_q4_demo.py
```

From the worktree root:

```powershell
C:/Python314/python.exe -B -m pytest -o addopts= cas-synthetic/tests/test_level3_conversational.py cas-synthetic/tests/test_conversational_canonical_identity.py -q -p no:cacheprovider --basetemp '_test_runs/synthetic_final' --tb=short
C:/Python314/python.exe -B offline-cas/build_offline_package.py
git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check
```

`cr-at-eol` accepts the Windows batch launcher's intentional CRLF. Its former
double carriage returns are removed; generated Python uses LF. The TSX parser
loaded the already installed local TypeScript package, read CompilerPage.tsx
as ScriptKind.TSX, and required an empty parseDiagnostics list. This is syntax
verification of text edits, not a full dashboard build.

## Initial failures retained in this record

- Recovered compiler/help baseline: 20 failed, 396 passed. One failure was a
  missing sparse-checkout docs directory; reserved-name and stale bundle/help
  failures were fixed. Subsequent final suite passes as above.
- First new metadata test used unsupported inline emergent syntax: 1 failed,
  175 passed. It now tests actual compiled emergent state results at the runtime
  boundary instead of inventing syntax. The corrected case passes.
- First broad lab invocation omitted the parent of pytest's temporary path:
  186 passed, 115 setup errors. Creating the parent and setting TEMP/TMP fixed
  setup; the unchanged tests then passed 304/304.
- A misspelled synthetic test filename produced no collected tests. The correct
  two filenames above pass 27/27.
- First final Q4 invocation placed its fake owner key inside the checkout:
  89 passed, 3 correctly rejected that location. With the test key directory
  outside the tested checkout (still inside CNCM), 92/92 pass. The trust guard
  was not weakened.
- A recovery recheck found concurrent changes in the original worktree; this
  was not treated as corruption or reverted. `INTEGRITY.json` records the new
  original commit and different v0.5 manifest alongside the preserved snapshot.

## Open gates and next safe command

Book interpretation N1–N13, W-A/W-B/W-C, nested-set identity and the PCBA route
remain decisions/specifications. Learned T14 acceptance, T15 operation
integration, actual fresh-process neural reload, end-to-end correction and
independent evaluation custody are not complete. The deterministic demo is
labelled `SCRIPTED_FIXTURE_NOT_A_LEARNED_RESULT`.

The next safe command rechecks preparation without launching or overwriting a plan:

```powershell
C:/Python314/python.exe -B q4_smoke_job.py prepare --data-dir data/q3_v0_7 --data-version helm-cas-expression-lab.q3-behaviour-records/0.7 --output '../../records/continuation_20260921/q4_smoke_output' --seed 20260921 --width 64 --max-updates 128 --max-wall-seconds 1800 --train-examples 2048 --dev-examples 16 --device cuda:0
```

The runbook describes the separate authorization step. No real owner key,
signature, GPU execution receipt, AWS instance, price/budget approval, or
scientific acceptance was created in this continuation.
