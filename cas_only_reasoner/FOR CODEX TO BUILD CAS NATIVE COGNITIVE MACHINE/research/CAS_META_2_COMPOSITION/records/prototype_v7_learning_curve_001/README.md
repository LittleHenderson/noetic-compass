# Verified training curves

This package renders only the pinned training-recount JSON. It does not read task files or checkpoints, recompute graphs, load models/tensors, run neural or native execution, or contact providers. The underlying run failed during native evaluation; none of these files changes that status.

## Current outputs

`run_001/learning_curve.md` contains every measured epoch and depth, a before/selected/final summary, checkpoint identities, and the data split limits. `run_001/learning_curve.csv` has 132 depth rows. `run_001/checkpoints.csv` has the exact six checkpoint records, including their historical remote paths. `run_001/render_receipt.json` binds the input, renderer, output hashes and cell checks.

Only 22 generation measurements per family were recorded: epochs 0, 1 and every tenth epoch through 200. The report does not invent scores for the intervening epochs. The original best-so-far `selected` flag is preserved as `selected_at_epoch`; `final_selected_checkpoint` separately identifies CAS epoch 200 and generic epoch 180.

The ratios measure exact generated program-plus-binding matches, not completed native task answers. Validation uses 32 cases per depth; the training probe uses 8. Test data has no depth-2 group, although validation does. The 72 test variants form 24 related triplets and jointly change instances and program combinations; they are not 72 independent structures or two separately isolated generalization tests.

## Exact commands

These PowerShell commands work from any directory. They require only the local Python standard library. The tests include a synthetic score fixture and the already-pinned recount; neither generates tasks or runs a model.

```powershell
$curveRoot = 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_learning_curve_001'
python -B "$curveRoot/test_build.py"
python -B "$curveRoot/verify_saved.py" --render-receipt "$curveRoot/run_001/render_receipt.json" --sha256 c697a33ca67a5e9e4ea5972fba78ce94352479fd9e3e40171cd546e5bc97b0c4
```

The second command is read-only. It rechecks each output hash and all CSV fields/Markdown table cells against the externally pinned recount.

To rebuild into a fresh directory:

```powershell
python -B "$curveRoot/build.py" --receipt "$curveRoot/../prototype_v7_training_recount_001/receipt_001.json" --receipt-sha256 452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76 --output "$curveRoot/run_002"
```

`run_002` must not exist. For another rerun, choose another new directory inside this package. Do not delete or overwrite saved evidence. CSV and Markdown content is deterministic; the new render receipt records the actual command/time and therefore has a new hash.

## Current hashes

- Pinned input: `452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76`.
- Renderer: `732456f953d87fd494dc31358a1758677b63c16bea4c83506ff97caacfb2baec`.
- Saved render receipt: `c697a33ca67a5e9e4ea5972fba78ce94352479fd9e3e40171cd546e5bc97b0c4`.
- Markdown: `d13f97d76f85070958b3b38db5488f0b691aa4a41236260513c1188984622323`.
- Learning-curve CSV: `977c9141c7d46db90e13447bb4d5e74b45b6a9a42343e36a7065ea3e2f0a248d`.
- Checkpoint CSV: `de387ca32902520a0cd92130a16b8f41c9e889654ba797c43f60b8cd1060f42f`.

The renderer verified 1,980 curve CSV fields, 60 checkpoint CSV fields and 708 Markdown data cells. Nineteen tests passed; `tests_output.txt`, `run_output.txt` and `verification_output.txt` preserve this agent's executed output. `ROOT_CHECK.md` and `root_tests_output.txt`, if present, are separate root-owned checks and were not edited here.
