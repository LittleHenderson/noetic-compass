# Stage 27L Calibrated Eraser Steering

**Status:** `PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING`

## Contracts

- Stage 7 prefix source: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- Stage 27J source: `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`
- Stage 27K source: `GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL`
- Learn/eval disjoint: `True`

## Calibration

- Eraser cover: `L11MLP`, `L9H3`, `L11H11`, `L10H6`, `L11H9`, `L10H3`
- Scale grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- Global selected scale: `0.0`
- Drive selected scales: `{'1': 0.25, '2': 0.0, '3': 1.0, '4': 0.0, '5': 0.0, '6': 0.25, '7': 0.0}`

## Held-Out Evaluation

- Global increment mean: `0.822302`
- Global random increment mean: `-0.151488`
- Global > random: `37 / 56` (share `0.6607`, p `0.0111207`, mean delta `0.973789`)
- Drive-calibrated increment mean: `0.955008`
- Drive-calibrated random increment mean: `-0.129605`
- Drive-calibrated > random: `36 / 56` (share `0.6429`, p `0.0220233`, mean delta `1.084613`)

## Boundary

Stage 27L is bounded calibrated eraser-cover intervention over Pythia-160M CPL2 likelihood margins. It is not complete circuit discovery, not weight editing, not model-wide control, not cross-model control, and not visible free-form generation control.
