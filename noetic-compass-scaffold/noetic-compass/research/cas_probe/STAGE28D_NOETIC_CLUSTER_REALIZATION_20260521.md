# Stage 28D Noetic Cluster Realization

**Status:** `NULL_NOETIC_CLUSTER_REALIZATION_NOT_ESTABLISHED`

## Plain English

This report tests compound Noetic colloquialisms as multi-label clusters by asking whether their two target Noetics are jointly elevated over hard replacement controls.

## Artifact

- Model: `EleutherAI/pythia-160m`
- Runtime device: `cpu`
- Layer: `5`
- Artifact contract: `LOCKED_ARTIFACT_MATCH`
- Fixture rows: `24`

## Readout Results

| Runtime readout | Stage 9 probe | Probe test acc | Mean margin | Positive rows | Sign p | Mean targets in top4 | Both targets top4 | Pass gates |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `phrase_mean` | `X_mean` | 0.7308 | -0.1888 | 7 / 24 | 0.988672 | 0.9583 | 0.1250 | `False` |
| `phrase_last` | `X_final` | 0.9241 | -0.4827 | 4 / 24 | 0.999861 | 0.7083 | 0.0000 | `False` |

## Per-Cluster Margins

### phrase_mean

| Cluster | Targets | Mean margin | Positive share | Mean targets in top4 |
|---|---|---:|---:|---:|
| `attraction_cause` | `^2, ^8` | -0.3772 | 0.000 | 1.000 |
| `attraction_resonance` | `^2, ^4` | 0.3149 | 1.000 | 1.333 |
| `aversion_analysis` | `^3, ^6` | -0.3475 | 0.000 | 1.333 |
| `aversion_vibration` | `^3, ^4` | -0.6780 | 0.000 | 0.667 |
| `identity_arising` | `^5, ^9` | 0.5065 | 1.000 | 0.333 |
| `mind_analysis` | `^1, ^6` | -0.3525 | 0.000 | 1.000 |
| `mind_rhythm` | `^1, ^7` | -0.0840 | 0.333 | 1.000 |
| `resonance_rhythm` | `^4, ^7` | -0.4929 | 0.000 | 1.000 |

### phrase_last

| Cluster | Targets | Mean margin | Positive share | Mean targets in top4 |
|---|---|---:|---:|---:|
| `attraction_cause` | `^2, ^8` | -0.3085 | 0.333 | 1.000 |
| `attraction_resonance` | `^2, ^4` | -0.5482 | 0.000 | 0.667 |
| `aversion_analysis` | `^3, ^6` | -0.0582 | 0.333 | 1.000 |
| `aversion_vibration` | `^3, ^4` | -0.4167 | 0.000 | 1.000 |
| `identity_arising` | `^5, ^9` | -0.6021 | 0.000 | 0.333 |
| `mind_analysis` | `^1, ^6` | 0.1122 | 0.667 | 0.667 |
| `mind_rhythm` | `^1, ^7` | -0.9253 | 0.000 | 0.667 |
| `resonance_rhythm` | `^4, ^7` | -1.1149 | 0.000 | 0.333 |

## Boundary

Stage 28D tests multi-label two-Noetic clusters on Pythia-160M using existing Stage 9 probes. It does not train a cluster classifier, test full formulas/equations, prove exact neurons, or establish generation control.
