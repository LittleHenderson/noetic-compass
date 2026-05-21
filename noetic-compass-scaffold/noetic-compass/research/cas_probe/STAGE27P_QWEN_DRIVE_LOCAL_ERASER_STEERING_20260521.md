# Stage 27P Qwen Drive-Local Eraser Steering

**Status:** `PASS_BOUNDED_CROSS_ARCH_QWEN_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING`

## Contracts

- Stage 16 CPL2 source: `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`
- Stage 16 manifest model revision: `8faed761d45a263340a0528343f099c05c9a4323`
- Stage 27O source: `PASS_BOUNDED_CROSS_SCALE_DRIVE_LOCAL_CALIBRATED_ERASER_STEERING`
- Stage 27P-A source: `PASS_QWEN_HOOK_ADAPTER_PREFLIGHT`
- Loaded model revision: `8faed761d45a263340a0528343f099c05c9a4323`
- Learn/eval disjoint: `True`
- Held-out eval rows: `56`

## Learned Qwen Drive-Local Covers

- Candidate layers: `[24, 25, 26, 27]`
- Candidate components: `52`
- Cover size per drive: `6`
- Eraser covers: `{'1': ['L27H8', 'L27H10', 'L27H3', 'L25H3', 'L26H10', 'L26H4'], '2': ['L27MLP', 'L26MLP', 'L25MLP', 'L26H7', 'L24MLP', 'L24H9'], '3': ['L26H2', 'L27H0', 'L26H4', 'L27H8', 'L27H6', 'L25H3'], '4': ['L25MLP', 'L26MLP', 'L24MLP', 'L27H4', 'L27H1', 'L27H3'], '5': ['L27MLP', 'L25H0', 'L27H10', 'L26H3', 'L25H6', 'L24H11'], '6': ['L26MLP', 'L24H8', 'L26H2', 'L25MLP', 'L24MLP', 'L25H3'], '7': ['L27MLP', 'L27H0', 'L25H9', 'L26H11', 'L25H4', 'L26H5']}`
- Drive selected scales: `{'1': 0.0, '2': 0.25, '3': 0.0, '4': 0.0, '5': 0.0, '6': 0.0, '7': 0.0}`

## Held-Out Evaluation

- Drive-local increment mean: `0.896010`
- Drive-local random increment mean: `-0.169345`
- Drive-local > random: `56 / 56` (share `1.0000`, p `1.38778e-17`, mean delta `1.065355`)

## Boundary

Stage 27P is bounded cross-architecture evidence for Qwen drive-local calibrated output-side eraser-cover intervention over CPL2 likelihood margins. It is not universal architecture evidence, not weight editing, not complete circuit discovery, not model-wide control, and not visible free-form generation control.
