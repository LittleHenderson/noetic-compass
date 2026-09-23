# Q4 panel evaluation: existing evidence recovered, new inference not run

The preserved records already establish three separate diagnostic results for
the **original 128-update checkpoint**. No new model prediction was produced in
this repair task. Both attempted launches stopped before the model loaded.

| Existing-record panel | Exact AST | Valid AST | Ordered operator/tree shape |
| --- | --- | --- | --- |
| All 128 actually consumed teaching examples, RT1 | 0/128 | 128/128 | 44/128 |
| 113 unconsumed-pool examples with new content on actually consumed shapes, derived RT1 subset | 0/113 | 113/113 | 28/113 |
| Original 16 development examples with genuinely new bare tree structures | 0/16 | 16/16 | 0/16 |

The 113 examples are selected from RT1's next 128 shuffled teaching-pool rows.
They are content-disjoint from the actual 128 consumed rows, and their ordered
operator/tree skeletons occur in those consumed rows. Fifteen other unconsumed
rows do not satisfy that familiar-shape condition. These are **unused rows inside
the 2048-row teaching pool**, not the new stricter outside-pool panel.

RT1 saved a uniform output histogram for each 128-row group, not original
per-row prediction receipts. `derive_saved_panels.py` labels the resulting
row checks as derivations, verifies committed RT1 evidence, reconstructs the
original ordering and rechecks every depth total. It does not invent per-row
receipts or rerun inference. `existing_record_panels.json` preserves these
identities and limitations. Exposure itself is reconstructed from the pinned
worker's shuffle and 128 completed single-example updates; per-row IDs were
not logged during training.

The 16 original development predictions are genuine original per-row records.
All their bare and operator-labelled shapes are absent from the complete
teaching pool. Fifteen have a size/depth combination present in that pool;
one is unmatched. Their separate results are 0/15 and 0/1 exact. None of these
visible, previously inspected records is an independent hidden final test.

## New evaluator and selected jobs

The new module prepares and freezes three panels before inference: 16 consumed
teaching rows, 16 declared first-leaf substitutions absent from the entire
teaching pool but with familiar operator/tree skeletons, and 16 existing new
structure rows. The substitutions use aligned token/AST changes and are
explicitly **not recompiled**. Inputs, checkpoint, original source, resource
limits and the new runner are pinned. Reference ASTs and predictions remain
separately labelled. Existing model, decoder, compiler and data files were not
edited; the unchanged CUDA-only loader remains in force.

- `run_001`: failed local shell discovery (`WinError 2`), before GPU admission.
  Its original runner bytes are preserved under `frozen_sources/` and in
  commit `7908b1a7`. The incorrect hard-coded path was fixed by resolving the
  actually installed shell. This is an evaluator integration error, not a
  negative model result.
- `run_002`: explicitly selected after the fix, with its own manifest and
  `replacement_selection.json`. The actual inventory found no matching known
  learning entry point. The original GPU admission policy then refused launch:
  `GPU_BUSY: prelaunch utilization exceeds policy`. The limit is 10%; the
  failed guard did not retain its numerical sample. Do not substitute the
  earlier read-only 30% snapshot for that missing admission sample.
- Both runs: no worker launched, zero new predictions, zero updates, no optimizer,
  no cloud/API, no CPU fallback, no automatic retries. No further job was run.
  Their claims, failures and command logs remain intact.

The selected model budget was at most 48 predictions and 120 seconds, one GPU
job, two CPU threads, with original shared-display capacity/thermal checks.
`GPU_EVALUATION_SELECTION.md` and `replacement_selection.json` document the
selection under the user's standing authorization. No owner signature or
independent Claude approval is claimed.

## Complementary evidence and remaining question

RT1 reproduces the original 16 outputs and supplies the consumed/unconsumed
histograms used above. RT7's 8/8 fit after 2000 updates is a different trained
model and a different teaching set; its 0/16 development result stays separate.
RT2's 256-row, 2000-update diagnostic also remains separate. These results do
not prove that longer training or a larger representation will solve Q4.
The late Helm pointer reach regression is another experiment entirely.

Historical source: `d4c3fc7643201a83693ea9073c14ab42ecc5a570`.
Weights: `d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477`.
Complementary review: `26f1b46515c960a7aed6023f370df95d591ca36a`.
Current frozen manifest canonical SHA-256:
`cc11a4ecb0a23aacdfca00e16239e1a022e5a6c8b7707637c03d00093db34fbf`.

## Tests and next command

Final selected tests: **35 cases, 21 functions, all new; all passed**. Existing
test cases/functions selected: zero. One selected file loaded; 1072 other
tracked repository test filenames were unselected (a census, not a claim of
one runnable whole-repository suite). Initial run: 31 passed, one failed due
to an incorrect expected shuffle fixture. Corrected fixture: 32 passed.
Executable-discovery regression cases: final 35 passed. All receipts remain
under `tests/`; `TEST_SCOPE.json` lists functions and unloaded filenames.

From this worktree's CNCM directory, the next command is a read-only check:

```powershell
& C:/Python314/python.exe -B research/helm_cas_expression_lab/q4_panel_evaluation.py verify --manifest records/helm_integrated_repairs_20260923/q4/input_manifest_002.json --sha256 cc11a4ecb0a23aacdfca00e16239e1a022e5a6c8b7707637c03d00093db34fbf
```

If a later explicit job selection finds the GPU available, the prepared
execution command is below. It has **not been run**; it must use a new output
directory and preserve the same guards. This is not an automatic retry.

```powershell
& C:/Users/wakil/venvs/cas-gpu/Scripts/python.exe -B research/helm_cas_expression_lab/q4_panel_evaluation.py execute --manifest records/helm_integrated_repairs_20260923/q4/input_manifest_002.json --sha256 cc11a4ecb0a23aacdfca00e16239e1a022e5a6c8b7707637c03d00093db34fbf --output records/helm_integrated_repairs_20260923/q4/run_003
```

The frozen manifests bind this worktree's absolute source paths. Copying the
files to a different checkout does not silently authorize or identify a new
source; prepare a new manifest for any changed location/source instead.
