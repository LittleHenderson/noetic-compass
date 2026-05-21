# Stage 27F Targeted MLP-Neuron Covers

**Status:** `PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 27C source status: `PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS`
- Stage 27E source status: `PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS`
- Learn/eval disjoint: `True`

## Evaluation

- Learn rows: `112` (4 per class)
- Eval rows: `112` (4 per class)
- Targeted neuron-cover mean drop: `12.653024`
- Random neuron-cover mean drop: `-0.132972`
- Targeted positive drop share: `1.0000`
- Clean mean margin: `6.371307`
- Targeted-ablated mean margin: `-6.281717`

## Paired Controls

- Targeted drop > random mean drop: `112 / 112` (share `1.0000`, p `1.92593e-34`, mean delta `12.785996`)
- Patch-back mean abs margin error: `0.00000000`

## Pair-Kind Breakdown

| Pair kind | n | Targeted drop mean | Targeted > random share |
|---|---:|---:|---:|
| `same_drive_diff_register` | 112 | 12.653024 | 1.0000 |

## Example Per-Class Neuron Covers

- `F1T`: `L5N345`, `L5N2346`, `L5N230`, `L5N1583`, `L5N1127`, `L5N1668`, `L5N1849`, `L5N1842`, `L5N2268`, `L5N29`, `L5N1675`, `L5N207`
- `F1A`: `L5N2648`, `L5N2948`, `L5N325`, `L5N808`, `L5N3053`, `L5N2343`, `L5N594`, `L5N1394`, `L5N977`, `L5N1728`, `L5N1580`, `L5N116`
- `F1f`: `L5N84`, `L5N230`, `L5N1354`, `L5N207`, `L5N29`, `L5N1821`, `L5N1983`, `L5N2853`, `L5N2612`, `L5N1394`, `L5N2548`, `L5N1518`
- `F1E`: `L5N1580`, `L5N529`, `L5N2948`, `L5N2145`, `L5N2648`, `L1N3059`, `L5N871`, `L5N1915`, `L5N977`, `L5N22`, `L1N340`, `L5N1122`
- `F2T`: `L5N230`, `L5N1849`, `L5N3041`, `L5N2225`, `L5N2268`, `L5N2469`, `L5N1127`, `L5N1793`, `L5N1714`, `L5N1848`, `L5N2827`, `L5N977`
- `F2A`: `L5N2343`, `L5N1394`, `L5N3053`, `L5N947`, `L5N2688`, `L5N1426`, `L5N1728`, `L5N413`, `L5N1523`, `L5N2047`, `L5N2294`, `L5N2948`
- `F2f`: `L5N230`, `L5N546`, `L5N2612`, `L5N29`, `L5N3041`, `L5N1714`, `L5N1459`, `L1N52`, `L5N1518`, `L5N717`, `L5N1394`, `L1N1414`
- `F2E`: `L5N1915`, `L5N341`, `L5N916`, `L5N2294`, `L5N2346`, `L5N367`, `L5N1830`, `L5N2619`, `L5N63`, `L5N3053`, `L5N2439`, `L5N2883`
- `F3T`: `L5N230`, `L5N2346`, `L5N1127`, `L5N29`, `L5N2097`, `L5N1668`, `L5N2329`, `L5N1583`, `L5N1848`, `L5N1793`, `L5N314`, `L5N1589`
- `F3A`: `L5N325`, `L5N1580`, `L5N2343`, `L5N2948`, `L5N2613`, `L5N116`, `L5N3053`, `L5N1394`, `L5N594`, `L5N22`, `L5N987`, `L5N341`
- `F3f`: `L5N84`, `L5N230`, `L5N1983`, `L5N3053`, `L5N29`, `L5N2612`, `L5N2845`, `L5N159`, `L5N2121`, `L5N1354`, `L5N1714`, `L5N1478`
- `F3E`: `L5N22`, `L5N1580`, `L5N529`, `L5N1122`, `L5N63`, `L5N1830`, `L5N2948`, `L5N1915`, `L5N1842`, `L5N2294`, `L5N2447`, `L5N749`

## Boundary

Stage 27F is bounded to Pythia-160M MLP intermediate neurons in layers selected from Stage 27E coordinate covers, scored against the trained Stage 7 Foundation readout. It is not a complete circuit, not all neurons in the model, not token sonar, not Noetic/40-Element coverage, not raw CAS-symbol understanding, and not generation control.
