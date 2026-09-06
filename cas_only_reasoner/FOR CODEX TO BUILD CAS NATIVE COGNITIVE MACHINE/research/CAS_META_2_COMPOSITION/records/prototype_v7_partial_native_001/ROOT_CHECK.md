# Independent check of partial-report boundaries

On 2026-09-06, the primary agent independently ran:

```text
C:/Python314/python.exe -I -S -B records/prototype_v7_partial_native_001/test_report.py
C:/Python314/python.exe -I -S -B records/prototype_v7_partial_native_001/test_native_audit.py
```

Both commands exited 0: 10 tests in 0.001 seconds each. These are 20 distinct pure tests, repeated independently after the captured agent run; they are not 40 distinct tests. `root_tests_output.txt` is a UTF-8/LF transcription of the combined returned command output, not the original child output-stream bytes.

These small tests check reporting and missing/rejected-record boundaries. They do not replace the full saved-evidence audit. No neural model, native executor, GPU or provider was used. The primary agent read the current report logic and the final audit-binding path without changing any of the six running Python files.

In particular, an unfinished attempt retains an unknown result; a rule arm that never started is not counted as an attempted or failed task. The 71-case common comparison remains separate from the 72 assigned cases per arm.
