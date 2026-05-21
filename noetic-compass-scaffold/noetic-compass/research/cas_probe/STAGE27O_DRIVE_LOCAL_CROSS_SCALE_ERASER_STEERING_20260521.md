# Stage 27O Drive-Local Cross-Scale Eraser Steering

**Status:** `PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING`

## Contracts

- Stage 8 CPL2 source: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`
- Stage 8 manifest model revision: `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2`
- Stage 27N source: `GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL`
- Loaded model revision: `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2`
- Learn/eval disjoint: `True`
- Held-out eval rows: `56`

## Learned Drive-Local Covers

- Candidate layers: `[12, 13, 14, 15]`
- Candidate components: `36`
- Cover size per drive: `6`
- Eraser covers: `{'1': ['L15H3', 'L13H3', 'L15H7', 'L14H3', 'L14H0', 'L12H4'], '2': ['L15MLP', 'L13MLP', 'L12MLP', 'L13H1', 'L15H0', 'L12H3'], '3': ['L13H4', 'L12H4', 'L15H6', 'L14H5', 'L12H5', 'L12MLP'], '4': ['L15MLP', 'L13MLP', 'L15H1', 'L14H3', 'L15H0', 'L14H4'], '5': ['L15MLP', 'L13H0', 'L12H4', 'L12H1', 'L13H1', 'L14H0'], '6': ['L12MLP', 'L14MLP', 'L13H3', 'L15H1', 'L13H4', 'L12H1'], '7': ['L15MLP', 'L13H1', 'L13H0', 'L12H1', 'L13H4', 'L12H3']}`
- Drive selected scales: `{'1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.25, '6': 0.0, '7': 0.0}`

## Held-Out Evaluation

- Drive-local increment mean: `0.838640`
- Drive-local random increment mean: `-0.163433`
- Drive-local > random: `54 / 56` (share `0.9643`, p `2.21628e-14`, mean delta `1.002073`)

## Stage 27N Comparison

- Stage 27N status: `GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL`
- Stage 27N global increment mean: `0.184636`
- Stage 27N drive-calibrated increment mean: `0.476230`

## Boundary

Stage 27O is bounded cross-scale evidence for drive-local calibrated output-side eraser-cover intervention over Pythia-1B CPL2 likelihood margins. It is not cross-architecture evidence, not weight editing, not complete circuit discovery, not model-wide control, and not visible free-form generation control.
