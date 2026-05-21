# Stage 27A Component Path-Patching

**Status:** `PASS_BOUNDED_COMPONENT_PATH_PATCHING`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 26 source status: `PASS_BOUNDED_COMPONENT_ATTRIBUTION`
- Formal gate valid: `True`

## Path Patching

- Eval rows: `512`
- Baseline acc: `0.7832`
- Ablated acc: `0.1855`
- Patched acc: `0.7832`
- Targeted drop: `0.5977`
- Recovered acc: `0.5977`
- Recovery fraction: `1.0000`

## Matched Patch Control

- p(random >= actual): `0.0323`
- Random mean recovery fraction: `-0.0028`
- Random p95 recovery fraction: `0.0098`

## Selected Components

- `L5H3`
- `L5H5`
- `L5H0`
- `L5H10`
- `L1H6`
- `L5H6`

## Top Restored Classes

- `F3T` n=21 baseline=1.000 ablated=0.048 patched=1.000 lost=0.952 recovered=0.952
- `F4T` n=21 baseline=0.905 ablated=0.000 patched=0.905 lost=0.905 recovered=0.905
- `F3E` n=11 baseline=0.818 ablated=0.000 patched=0.818 lost=0.818 recovered=0.818
- `F4f` n=21 baseline=0.810 ablated=0.000 patched=0.810 lost=0.810 recovered=0.810
- `F5T` n=21 baseline=0.857 ablated=0.048 patched=0.857 lost=0.810 recovered=0.810
- `F7T` n=21 baseline=0.952 ablated=0.143 patched=0.952 lost=0.810 recovered=0.810
- `F7A` n=21 baseline=0.810 ablated=0.000 patched=0.810 lost=0.810 recovered=0.810
- `F3A` n=21 baseline=0.857 ablated=0.095 patched=0.857 lost=0.762 recovered=0.762
- `F6T` n=21 baseline=0.905 ablated=0.143 patched=0.905 lost=0.762 recovered=0.762
- `F1E` n=14 baseline=0.714 ablated=0.000 patched=0.714 lost=0.714 recovered=0.714

## Sanity Controls

- Baseline repeat disagreement rate: `0.000000`

## Boundary

Stage 27A is bounded path-patching over the Stage 26 selected Pythia-160M attention-head family. It does not identify exact neurons, complete circuits, raw CAS-symbol understanding, an internal CAS compiler, free-form generation control, or cross-model component generality.
