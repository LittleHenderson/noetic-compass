# Stage 26 Component Attribution

**Status:** `PASS_BOUNDED_COMPONENT_ATTRIBUTION`

## Artifact Contract

- Contract: `LOCKED_ARTIFACT_MATCH`
- Formal gate valid: `True`

## Capture

- Rows: `4368`
- Components: `78`
- Finite components: `True`

## Alignment

- Selected mean projection score: `0.313262`
- Matched same-kind/layer p(random >= actual): `0.0323`
- All-component p(random >= actual): `0.0323`

## Ablation

- Eval rows: `512`
- Baseline acc: `0.7832`
- Targeted ablated acc: `0.1855`
- Targeted drop: `0.5977`
- Matched same-kind/layer p(random >= actual): `0.0323`
- All-component p(random >= actual): `0.4839`

## Top Components

- `L5H3`: `0.341237`
- `L5H5`: `0.334239`
- `L5H0`: `0.304439`
- `L5H10`: `0.302108`
- `L1H6`: `0.299577`
- `L5H6`: `0.297972`
- `L5H2`: `0.297595`
- `L5H4`: `0.284761`
- `L1H10`: `0.283683`
- `L4H6`: `0.277498`
- `L5H1`: `0.275428`
- `L4H11`: `0.269672`
- `L4H8`: `0.262427`
- `L0H7`: `0.257012`
- `L4H1`: `0.256454`
- `L5MLP`: `0.255353`
- `L3H7`: `0.252779`
- `L4MLP`: `0.250078`
- `L4H4`: `0.244808`
- `L3H1`: `0.242524`

## Class Specificity

- `F3T` n=21 baseline=1.000 ablated=0.048 drop=0.952
- `F4T` n=21 baseline=0.905 ablated=0.000 drop=0.905
- `F3E` n=11 baseline=0.818 ablated=0.000 drop=0.818
- `F4f` n=21 baseline=0.810 ablated=0.000 drop=0.810
- `F5T` n=21 baseline=0.857 ablated=0.048 drop=0.810
- `F7T` n=21 baseline=0.952 ablated=0.143 drop=0.810
- `F7A` n=21 baseline=0.810 ablated=0.000 drop=0.810
- `F3A` n=21 baseline=0.857 ablated=0.095 drop=0.762
- `F6T` n=21 baseline=0.905 ablated=0.143 drop=0.762
- `F1E` n=14 baseline=0.714 ablated=0.000 drop=0.714

## Boundary

Stage 26 is bounded component attribution over attention heads and MLP blocks. It does not identify exact neurons, complete circuits, raw CAS-symbol understanding, an internal CAS compiler, free-form generation control, or cross-model component generality.
