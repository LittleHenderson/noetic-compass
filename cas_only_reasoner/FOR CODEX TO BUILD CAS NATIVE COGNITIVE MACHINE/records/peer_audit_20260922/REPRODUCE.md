# Reproduce the peer audit

Frozen subject: `626cc84b574e60217a103b72d2f09388d7aa5e34`.
Use the isolated audit checkout, preserving the original agent worktree.
These commands run symbolic code and fixtures only. No training or inference
permission is inferred from an audit package.

```powershell
$base = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
$work = Join-Path $base '_worktrees\codex-helm-peer-audit'
$cn = Join-Path $work 'cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
$record = Join-Path $cn 'records\peer_audit_20260922'
$lab = Join-Path $cn 'research\helm_cas_expression_lab'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:TEMP = Join-Path $base '_test_runs'
$env:TMP = $env:TEMP
```

The compiler help tests read three source copies. A sparse checkout must include
`offline-cas`, `dist/cas-offline`, and the dashboard `src/pages`, as well as the
compiler/tests/docs. Lab export tests require the committed
`$cn/_handoffs/FABLE_HELM_CAS_v1/schemas/behavior_pair.schema.json`.
Set sparse paths from the **repository root**, not the nested CN directory.
The Git snapshot contains all of these; missing materialization is not a source
defect. Temporary Q4 fixture keys must remain outside the audited repository.

## Current suites

```powershell
Set-Location -LiteralPath (Join-Path $work 'noetic-compass-scaffold\noetic-compass')
& 'C:\Python314\python.exe' -B -m pytest --noconftest -o addopts= tests/test_notation_compiler.py tests/test_notation_compiler_nesting_and_defects.py tests/test_notation_compiler_continuation.py tests/test_offline_help_text_canon.py tests/test_full_demo_program.py -q -p no:cacheprovider --basetemp (Join-Path $base '_test_runs\peer_audit_compiler_full_20260922') --junitxml (Join-Path $record 'compiler_tests.xml')

Set-Location -LiteralPath $lab
& 'C:\Python314\python.exe' -B -m pytest -o addopts= test_compiler_nesting_facts.py test_foundations28.py test_operation_contracts.py test_q3_behaviour_records.py test_q3_load_and_export.py test_q3_load_boundary.py test_q3_load_errors.py test_learner_q4.py test_q4_followup.py -q -p no:cacheprovider --basetemp (Join-Path $base '_test_runs\peer_audit_lab_final_20260922') --junitxml (Join-Path $record 'lab_tests.xml')
```

Observed: **639 passed, 1 warning in 2.04s**, then **348 passed in 173.65s**.
The warning is unknown `asyncio_mode` with optional plugins disabled.
The original 99 compiler tests are included, not added again. The help file
contributes 454 cases, not 454 independent compiler mechanisms.

## Source, history and adversarial probes

```powershell
Set-Location -LiteralPath $cn
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/audit_package.py
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/merge/audit_merge.py
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/book/probe_book.py
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/ohm/audit_ohm.py
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/ohm/contract_boundary_probes.py
python records/peer_audit_20260922/probe_parallel_branch.py
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/assemble_claims.py
```

The independent boundary script deliberately exits **1**, with **7 failures and
1 error**. Its original output is `ohm/boundary_failures.txt`; its file was later
renamed without changing bytes to avoid accidental normal pytest collection.
The other probes complete successfully and retain the negative observations
inside their JSON outputs. The parallel-branch probe uses the installed Python
3.12 environment for its existing dependencies and refuses a changed branch
identity. It checks a declared board/Ohm example, never a model answer.

Source copies used by the historical probes come directly from explicit Git
objects. LF-normalized hashes follow the package's declared convention. Byte
identities and source refs remain in the JSON alongside every test receipt.

## Retained setup failures

Before regenerating any output, verify the retained package's raw bytes:

```powershell
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/verify_manifest.py
```

This checks artifact integrity only. The manifest excludes itself and Python
cache directories; it does not certify the underlying claims. Regenerating
receipts may change timings and mutable repository observations.

- `compiler_partial_checkout_tests.xml`: 339 passed because only one of three
  help-text sources was materialized. Final `compiler_tests.xml`: 639 passed.
- `lab_partial_checkout_tests.xml`: 342 passed / 6 failed because the FABLE
  export schema was not materialized.
- `lab_incomplete_sparse_retry_tests.xml`: the same 342 / 6 after an incorrect
  relative sparse-path addition. Final `lab_tests.xml`: 348 passed after the
  correct repository-root sparse addition. No source fix was involved.
- Two exploratory record-printing commands used Windows' default cp1252 and
  could not print/decode Unicode. Explicit UTF-8 and ASCII-safe JSON corrected
  those inspection commands. These were not application/test failures.
- Initial `--no-checkout` worktree setup needed `git read-tree -mu HEAD` to
  populate its empty index after sparse configuration. No tracked source was
  deleted; the original worktree was unaffected.

Use new output/temp names to preserve these receipts when repeating checks.
Do not compare current test files to historical counts without pinning both
implementation and tests; see the six combinations in `ohm/FINDINGS.md`.
