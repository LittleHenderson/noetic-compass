# Stage 25 SAE Feature Localization Pilot

**Status:** `NULL_SAE_FEATURE_READOUT_NOT_ESTABLISHED`

## Artifact Contract

- Contract: `LOCKED_ARTIFACT_MATCH`
- Formal gate valid: `True`

## Reconstruction

- Heldout explained variance: `0.9830`
- Heldout MSE: `0.016820`

## Sparsity

- Mean active features per row: `2303.16`
- Dead feature rate: `0.0000`

## CAS Alignment

- Top-k mean abs alignment: `0.304165`
- p(random >= actual): `0.0099`

## Feature Specificity

- Mean top-minus-other activation: `0.680869`
- p(random >= actual): `0.0099`

## Causal Feature Drop

- Reconstructed baseline acc: `0.7776`
- Targeted removal acc: `0.7785`
- Targeted drop: `-0.0009`
- p(random >= actual): `0.7624`

## Top Feature Candidates

- Feature `4002` -> `F2A` alignment `0.370528`
- Feature `4555` -> `F1A` alignment `0.349603`
- Feature `5053` -> `F2A` alignment `0.340789`
- Feature `1043` -> `F2A` alignment `0.338422`
- Feature `2566` -> `F7E` alignment `0.334354`
- Feature `4494` -> `F5E` alignment `0.327633`
- Feature `851` -> `F5T` alignment `0.320927`
- Feature `3400` -> `F1E` alignment `0.318551`
- Feature `4256` -> `F6T` alignment `0.315549`
- Feature `780` -> `F5f` alignment `0.315006`
- Feature `5747` -> `F4A` alignment `0.309898`
- Feature `1345` -> `F6T` alignment `0.307294`
- Feature `1758` -> `F6A` alignment `0.306352`
- Feature `5705` -> `F1E` alignment `0.298846`
- Feature `4209` -> `F2A` alignment `0.295608`
- Feature `4391` -> `F3A` alignment `0.294499`
- Feature `2302` -> `F4f` alignment `0.293097`
- Feature `3969` -> `F5E` alignment `0.292141`
- Feature `1390` -> `F4f` alignment `0.288392`
- Feature `1860` -> `F6A` alignment `0.284910`

## Boundary

Stage 25 trains an SAE over residual-stream readout activations and reports feature candidates. It does not identify exact causal neurons, complete circuits, raw CAS-symbol understanding, an internal CAS compiler, or free-form generation control.
