# Stage 27N Cross-Scale Calibrated Eraser Steering

**Status:** `GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL`

## Contracts

- Stage 8 CPL2 source: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`
- Stage 8 manifest model revision: `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2`
- Stage 27M source: `PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING`
- Loaded model revision: `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2`
- Learn/eval disjoint: `True`
- Held-out eval rows: `56`

## Learned Pythia-1B Covers

- Candidate layers: `[12, 13, 14, 15]`
- Candidate components: `36`
- Carrier cover: `L14MLP`, `L15H7`, `L13H3`, `L14H2`, `L13MLP`, `L12H2`
- Eraser cover: `L15MLP`, `L12MLP`, `L15H4`, `L12H4`, `L12H1`, `L12H0`
- Scale grid: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- Global selected scale: `0.0`
- Drive selected scales: `{'1': 1.0, '2': 0.0, '3': 1.0, '4': 0.0, '5': 0.0, '6': 0.0, '7': 0.0}`

## Held-Out Cross-Scale Evaluation

- Global increment mean: `0.184636`
- Global random increment mean: `-0.171235`
- Global > random: `28 / 56` (share `0.5000`, p `0.553073`, mean delta `0.355871`)
- Drive-calibrated increment mean: `0.476230`
- Drive-calibrated random increment mean: `-0.062814`
- Drive-calibrated > random: `27 / 56` (share `0.4821`, p `0.65556`, mean delta `0.539045`)

## Boundary

Stage 27N is bounded cross-scale evidence for calibrated output-side eraser-cover intervention over Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not complete circuit discovery, not model-wide control, and not visible free-form generation control.
