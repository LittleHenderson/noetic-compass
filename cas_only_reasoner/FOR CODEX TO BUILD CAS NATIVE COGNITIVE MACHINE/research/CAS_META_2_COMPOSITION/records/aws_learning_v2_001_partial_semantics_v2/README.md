# Separate checked-path stored-result diagnostic

This copy preserves the original diagnostic and the failed full-protocol
inspection. It does not replace the release gate. A successful stored-record
check still reports `CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED`.

Before imports, the script compares every allowed project source file with Git
snapshot `410bce98307a5644db51928459b73391c7066b72`. A dedicated import resolver
then roots the `tools` namespace explicitly, binds `cas_meta2` and every allowed
submodule to those checked paths, and executes freshly checked source bytes
without loading cached bytecode. Preloaded project modules and unlisted project
imports are refused. The final receipt records each actual loaded module path
and source hash and rechecks that the module objects and bytes did not change.

The exact failed-inspection hash, packet hash, remaining GPU-memory cleanup
issue, ZIP checks, stored semantic checks, and original-record preservation
checks are unchanged. AWS resource cleanup is a separate observation; it does
not close the failed GPU-preflight memory-cleanup check.

Twenty-five focused synthetic tests passed with neural and provider imports
blocked. They cover shadow `tools` and `cas_meta2` packages, preloaded modules,
unlisted imports, changed source bytes, replaced module objects, and the
unchanged failed-acceptance boundary. The additional cases check forward and
backward public definition order, canonical-byte equality, unchanged disk and
input values, and rejection of altered meanings, bindings, types or public text.

The detached JSON adapter applies only to `train.json`, `validation.json`, and
`test_private.json`. It first independently parses the public problem and
requires exact action and canonical-byte equality. It then changes only the
iteration order of `target.program.procedures` to match those public
declarations. The full task and dataset canonical bytes must remain identical.
The final receipt and separate `presentation_order_adapter.json` record every
row checked and affected. No stored JSON or frozen checker is rewritten.

The root agent confirmed that the original diagnostic finished with the
presentation-order mismatch and authorized this corrected run after tests.
The original failed diagnostic and failed full-protocol receipt are preserved.
The separate process receipt records whether this corrected run completed.

From the META2 package root, the diagnostic command is:

```powershell
C:/Python314/python.exe -B records/aws_learning_v2_001_partial_semantics_v2/check_records.py
```

The output is a new `result/diagnostic_receipt.json` in this directory. An
existing result directory is never overwritten.

## Completed diagnostic result

The one corrected process completed at 2026-09-05 22:59:00 UTC with exit code 0.
Status: `CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED`.
It checked 1,778 stored traces in 169 databases, three smoke references and
three smoke candidates, 72 evaluation references, all 360 sealed arm choices,
and the paired group metrics. All 16 loaded project modules/namespaces have
recorded checked paths and source hashes. The original evidence remained
unchanged.

The detached order adapter affected 423 of 888 rows: 342 training, 21 validation,
and 60 test rows. Every whole-task and dataset canonical-byte comparison
remained equal. `result/presentation_order_adapter.json` contains the row-level
record.

The stored task-correct counts were 0/72 for trained CAS, untrained CAS,
trained generic, and untrained generic; the rule selector scored 72/72.
Three trained CAS choices and seven trained generic choices produced valid
traces, but none produced a correct task result. These are checked saved
results, not new neural executions or an accepted full learning protocol.

The failed issue remains
`gpu_preflight_v2:V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED`.
`full_protocol_accepted` remains `false`.

Diagnostic receipt SHA256:
`55a3d0856331f076bb48aceb6fb9f933fc52fd923c78cd7a94412d81ba225e9e`.
The raw process streams and `process_receipt.json` are retained beside the
checker. Neither original failed receipt was replaced.
