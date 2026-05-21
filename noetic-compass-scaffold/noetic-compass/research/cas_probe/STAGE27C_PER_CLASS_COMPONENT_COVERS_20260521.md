# Stage 27C Per-Class Component Covers

**Status:** `PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 26 source status: `PASS_BOUNDED_COMPONENT_ATTRIBUTION`
- Stage 27A source status: `PASS_BOUNDED_COMPONENT_PATH_PATCHING`
- Stage 27B context status: `GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL`
- Learn/eval disjoint: `True`

## Evaluation

- Learn rows: `112` (4 per class)
- Eval rows: `112` (4 per class)
- Class-cover mean margin: `8.940174`
- Global-prefix mean margin: `5.268136`
- Random-subset mean margin: `5.557486`
- Full-global mean margin: `6.371307`
- Class-cover positive margin share: `1.0000`

## Paired Controls

- Class > global-prefix: `109 / 112` (share `0.9732`, p `4.51147e-29`, mean delta `3.672039`)
- Class > random-subset mean: `111 / 112` (share `0.9911`, p `2.1763e-32`, mean delta `3.382689`)
- Mean class gain: `3.570533`
- Mean full-global gain: `1.001666`
- Mean class gain / mean full-global gain: `3.564595`

## Pair-Kind Breakdown

| Pair kind | n | Class mean | Class > prefix share | Class > random share |
|---|---:|---:|---:|---:|
| `same_drive_diff_register` | 112 | 8.940174 | 0.9732 | 0.9911 |

## Example Per-Class Covers

- `F1T`: `L5H5`, `L5H3`, `L1H6`
- `F1A`: `L5H10`, `L1H6`, `L5H0`
- `F1f`: `L1H6`, `L5H5`, `L5H10`
- `F1E`: `L1H6`, `L5H3`, `L5H0`
- `F2T`: `L5H3`, `L5H5`, `L1H6`
- `F2A`: `L5H10`, `L5H0`, `L5H6`
- `F2f`: `L5H6`, `L1H6`, `L5H10`
- `F2E`: `L5H10`, `L5H5`, `L5H3`
- `F3T`: `L5H3`, `L5H5`, `L1H6`
- `F3A`: `L5H10`, `L5H0`, `L5H6`
- `F3f`: `L5H6`, `L5H10`, `L5H0`
- `F3E`: `L5H3`, `L5H5`, `L1H6`

## Boundary

Stage 27C is bounded to Pythia-160M Stage 7 Foundation probe-logit margins inside the Stage 26/27A validated six-head component family. It does not test Noetic/40-Element covers, token sonar, exact neurons, complete circuits, raw CAS-symbol understanding, or generation control.
