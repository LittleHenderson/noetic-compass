# Stage 7 Late-Layer Additive Drive Probe

**Status:** `EXPLORATORY_LATE_LAYER_ADDITIVE_NOT_ABOVE_RANDOM_GATE`

## Read

This is Claude's late-layer/additive suggestion translated into a bounded logit-margin test. It is exploratory because it reuses the Stage 7 fixture rather than a fresh held-out forced-choice set.

## Results

| Layer | Alpha | Mean Signed Margin Delta | Random Mean | Empirical p | Positive Share |
|---:|---:|---:|---:|---:|---:|
| 10 | -4.0 | 0.0000 | -0.0393 | 0.1935 | 0.250 |
| 10 | -2.0 | 0.0000 | -0.0262 | 0.3871 | 0.250 |
| 10 | 2.0 | 0.0357 | 0.0304 | 0.5806 | 0.250 |
| 10 | 4.0 | 0.0357 | 0.0357 | 0.5484 | 0.286 |
| 11 | -4.0 | 0.0000 | -0.0298 | 0.2903 | 0.250 |
| 11 | -2.0 | -0.0536 | -0.0196 | 1.0000 | 0.143 |
| 11 | 2.0 | 0.0357 | 0.0208 | 0.4194 | 0.250 |
| 11 | 4.0 | 0.0714 | 0.0274 | 0.1935 | 0.357 |

## Implication

The tested late-layer additive Drive directions did not pass the exploratory random-control gate. This weakens the steering route for Pythia-160M and argues for either a fresh forced-choice assay or deeper path/SAE diagnostics before more generation work.
