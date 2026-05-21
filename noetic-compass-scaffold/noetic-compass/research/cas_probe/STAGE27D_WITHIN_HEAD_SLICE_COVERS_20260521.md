# Stage 27D Within-Head Slice Covers

**Status:** `PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 27C source status: `PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS`
- Stage 27C formal gate valid: `True`
- Learn/eval disjoint: `True`

## Evaluation

- Learn rows: `112` (4 per class)
- Eval rows: `112` (4 per class)
- Slice-cover mean margin: `9.869650`
- Random-slice mean margin: `6.561956`
- Stage 27C class-head mean margin: `8.940174`
- Slice-cover positive margin share: `1.0000`

## Paired Controls

- Slice > random-slice mean: `112 / 112` (share `1.0000`, p `1.92593e-34`, mean delta `3.307694`)
- Slice > Stage 27C class-head cover: `77 / 112` (share `0.6875`, p `4.49011e-05`, mean delta `0.929475`)
- Mean slice gain: `4.500009`
- Mean Stage 27C class-head gain: `3.570533`
- Mean slice gain / mean class-head gain: `1.260318`

## Pair-Kind Breakdown

| Pair kind | n | Slice mean | Slice > random share | Slice > class-head share |
|---|---:|---:|---:|---:|
| `same_drive_diff_register` | 112 | 9.869650 | 1.0000 | 0.6875 |

## Example Per-Class Slice Covers

- `F1T`: `L5H3S1`, `L5H3S7`, `L5H5S2`, `L5H5S1`, `L1H6S4`, `L5H5S5`, `L5H5S7`, `L5H3S0`
- `F1A`: `L5H10S4`, `L1H6S7`, `L5H10S0`, `L5H10S3`, `L5H0S2`, `L5H10S1`, `L5H10S5`, `L5H0S3`
- `F1f`: `L5H10S5`, `L5H5S7`, `L5H5S6`, `L5H10S1`, `L1H6S7`, `L5H10S3`, `L1H6S1`, `L5H5S1`
- `F1E`: `L1H6S7`, `L5H3S3`, `L1H6S4`, `L5H3S1`, `L1H6S5`, `L5H0S0`, `L5H3S6`, `L5H0S2`
- `F2T`: `L5H3S1`, `L5H3S6`, `L5H3S0`, `L5H5S4`, `L5H3S7`, `L5H5S0`, `L1H6S1`, `L5H5S2`
- `F2A`: `L5H10S4`, `L5H0S3`, `L5H10S6`, `L5H0S2`, `L5H10S7`, `L5H10S0`, `L5H10S5`, `L5H10S1`
- `F2f`: `L5H10S5`, `L5H10S3`, `L5H10S4`, `L1H6S0`, `L1H6S1`, `L5H6S4`, `L5H6S0`, `L5H6S2`
- `F2E`: `L5H10S1`, `L5H10S0`, `L5H3S3`, `L5H10S2`, `L5H10S7`, `L5H5S4`, `L5H5S2`, `L5H10S6`
- `F3T`: `L5H5S2`, `L5H3S1`, `L5H3S7`, `L5H3S6`, `L5H5S4`, `L5H5S5`, `L5H3S3`, `L5H3S2`
- `F3A`: `L5H10S4`, `L5H10S5`, `L5H10S1`, `L5H10S0`, `L5H0S2`, `L5H10S7`, `L5H0S3`, `L5H10S6`
- `F3f`: `L5H10S5`, `L5H0S3`, `L5H0S7`, `L5H0S6`, `L5H0S5`, `L5H10S2`, `L5H6S2`, `L5H6S4`
- `F3E`: `L5H3S3`, `L1H6S7`, `L5H3S6`, `L1H6S4`, `L5H5S4`, `L5H5S2`, `L5H5S5`, `L5H3S1`

## Boundary

Stage 27D is bounded to contiguous slices of the pre-output-projection attention-head vectors inside the Pythia-160M Stage 27C Foundation covers. It does not identify exact neurons, MLP neurons, complete circuits, token sonar, Noetic/40-Element covers, raw CAS-symbol understanding, or generation control.
