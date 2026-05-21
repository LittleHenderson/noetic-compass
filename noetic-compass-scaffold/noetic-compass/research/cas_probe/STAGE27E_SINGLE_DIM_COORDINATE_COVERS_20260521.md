# Stage 27E Single-Dim Coordinate Covers

**Status:** `PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 27C source status: `PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS`
- Stage 27D source status: `PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS`
- Single-coordinate resolution: `True`
- Coordinate width: `1`
- Learn/eval disjoint: `True`

## Evaluation

- Learn rows: `112` (4 per class)
- Eval rows: `112` (4 per class)
- Coordinate-cover mean margin: `9.454989`
- Random-coordinate mean margin: `5.527455`
- Stage 27C class-head mean margin: `8.940174`
- Coordinate-cover positive margin share: `0.9911`

## Paired Controls

- Coordinate > random-coordinate mean: `112 / 112` (share `1.0000`, p `1.92593e-34`, mean delta `3.927534`)
- Coordinate > Stage 27C class-head cover: `63 / 112` (share `0.5625`, p `0.109566`, mean delta `0.514815`)
- Mean coordinate gain: `4.085348`
- Mean Stage 27C class-head gain: `3.570533`
- Mean coordinate gain / mean class-head gain: `1.144184`

## Pair-Kind Breakdown

| Pair kind | n | Coordinate mean | Coordinate > random share | Coordinate > class-head share |
|---|---:|---:|---:|---:|
| `same_drive_diff_register` | 112 | 9.454989 | 1.0000 | 0.5625 |

## Example Per-Class Coordinate Covers

- `F1T`: `L1H6S35`, `L5H3S8`, `L5H3S58`, `L5H3S28`, `L5H3S1`, `L5H3S11`, `L5H3S60`, `L5H5S12`
- `F1A`: `L5H10S37`, `L5H10S30`, `L1H6S56`, `L5H10S6`, `L5H10S45`, `L5H10S8`, `L5H10S49`, `L5H10S42`
- `F1f`: `L5H10S46`, `L5H10S41`, `L5H10S25`, `L5H5S16`, `L5H10S10`, `L5H10S62`, `L5H10S14`, `L5H5S26`
- `F1E`: `L1H6S56`, `L1H6S35`, `L5H3S49`, `L5H3S0`, `L1H6S26`, `L1H6S44`, `L5H3S31`, `L1H6S43`
- `F2T`: `L5H3S1`, `L5H5S20`, `L5H3S11`, `L5H3S49`, `L5H3S8`, `L5H3S0`, `L5H3S28`, `L5H3S60`
- `F2A`: `L5H10S37`, `L5H0S31`, `L5H10S62`, `L5H10S6`, `L5H10S53`, `L5H10S43`, `L5H10S17`, `L5H10S13`
- `F2f`: `L5H10S46`, `L5H10S37`, `L5H10S30`, `L1H6S17`, `L1H6S33`, `L5H10S25`, `L1H6S30`, `L1H6S42`
- `F2E`: `L5H10S29`, `L5H10S19`, `L5H10S10`, `L5H10S9`, `L5H5S0`, `L5H5S32`, `L5H10S6`, `L5H10S57`
- `F3T`: `L5H5S20`, `L5H3S11`, `L5H3S28`, `L5H3S1`, `L5H3S49`, `L5H3S54`, `L5H3S60`, `L5H3S0`
- `F3A`: `L5H10S37`, `L5H10S30`, `L5H10S6`, `L5H10S42`, `L5H10S62`, `L5H10S15`, `L5H0S21`, `L5H10S8`
- `F3f`: `L5H10S46`, `L5H0S31`, `L5H0S27`, `L5H10S25`, `L5H10S30`, `L5H0S40`, `L5H10S62`, `L5H10S14`
- `F3E`: `L1H6S56`, `L1H6S35`, `L5H5S32`, `L5H5S39`, `L5H5S63`, `L5H3S26`, `L5H5S23`, `L5H5S29`

## Boundary

Stage 27E is bounded to single coordinates of pre-output-projection attention-head vectors inside the Pythia-160M Stage 27C Foundation covers. These coordinates are not literal neurons. Stage 27E does not identify MLP neurons, complete circuits, token sonar, Noetic/40-Element covers, raw CAS-symbol understanding, an internal CAS compiler, or generation control.
