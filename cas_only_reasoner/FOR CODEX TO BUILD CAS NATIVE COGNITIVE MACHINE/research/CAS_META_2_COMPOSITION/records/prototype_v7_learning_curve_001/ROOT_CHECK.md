# Independent local presentation check

On 2026-09-06, the primary agent repeated:

```text
C:/Python314/python.exe -B records/prototype_v7_learning_curve_001/test_build.py
```

Result: 19 tests passed in 0.022 seconds; process exit 0. The saved tool-output text is in `root_tests_output.txt` (UTF-8/LF transcription of the returned command output, not the child's original output-stream bytes).

The tests include the pinned actual training receipt and rendered Markdown/CSV, plus refusal of changed counts, missing rows/epochs, wrong denominators, checkpoint changes, and invented native-score claims. This verifies presentation of previously checked records. It does not perform neural inference, native execution, provider access, or a new learning experiment.

The primary agent also read the generated Markdown, including the difference between selected and final checkpoints and the absence of depth-2 held-out tasks.

The primary agent then ran the read-only `verify_saved.py` against render receipt `c697a33ca67a5e9e4ea5972fba78ce94352479fd9e3e40171cd546e5bc97b0c4`. It exited 0 with `SAVED_CURVES_INDEPENDENT_RENDER_CHECK_PASSED`: all 1,980 curve CSV fields, 60 checkpoint CSV fields and 708 Markdown data cells matched the pinned recount.
