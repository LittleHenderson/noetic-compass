# Stage 27M Robust Calibrated Eraser Steering

**Status:** `PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING`

## Contracts

- Stage 7 prefix source: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- Stage 27J source: `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`
- Stage 27L source: `PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING`
- Learn/eval disjoint: `True`
- Held-out eval rows: `245`

## Calibration

- Eraser cover: `L11MLP`, `L9H3`, `L11H11`, `L10H6`, `L11H9`, `L10H3`
- Scale grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- Global selected scale: `0.0`
- Drive selected scales: `{'1': 0.25, '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.0, '6': 0.25, '7': 0.0}`

## Held-Out Robustness Evaluation

- Global increment mean: `0.767381`
- Global random increment mean: `-0.062216`
- Global > random: `169 / 245` (share `0.6898`, p `1.35376e-09`, mean delta `0.829597`)
- Drive-calibrated increment mean: `0.850062`
- Drive-calibrated random increment mean: `-0.071401`
- Drive-calibrated > random: `181 / 245` (share `0.7388`, p `2.02564e-14`, mean delta `0.921463`)

## Boundary

Stage 27M is bounded larger-sample robustness evidence for calibrated eraser-cover intervention over Pythia-160M CPL2 likelihood margins. It is not complete circuit discovery, not weight editing, not model-wide control, not cross-model control, and not visible free-form generation control.
