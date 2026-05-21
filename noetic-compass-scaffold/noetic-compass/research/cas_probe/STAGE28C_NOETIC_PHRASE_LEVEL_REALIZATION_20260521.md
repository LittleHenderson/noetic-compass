# Stage 28C Noetic Phrase-Level Realization

**Status:** `NULL_NOETIC_PHRASE_LEVEL_REALIZATION_NOT_ESTABLISHED`

## Plain English

This report tests whether Stage 28B's null was caused by the first-token readout. phrase_mean and phrase_last are scored with matching Stage 9 probes and compared against the phrase_first baseline.

## Artifact

- Model: `EleutherAI/pythia-160m`
- Runtime device: `cpu`
- Layer: `5`
- Artifact contract: `LOCKED_ARTIFACT_MATCH`
- Fixture rows: `40`

## Readout Results

| Runtime readout | Stage 9 probe | Probe test acc | Exact | p vs chance | Top-2 | Mean target p | Involution share | Delta vs first | Pass gates |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `phrase_first` | `X_focus` | 0.9145 | 0.1250 | 0.370982 | 0.1500 | 0.1240 | 0.5000 | 0.0000 | `False` |
| `phrase_mean` | `X_mean` | 0.7308 | 0.1250 | 0.370982 | 0.2000 | 0.1249 | 0.5417 | 0.0000 | `False` |
| `phrase_last` | `X_final` | 0.9241 | 0.1000 | 0.576869 | 0.1750 | 0.1017 | 0.5833 | -0.0250 | `False` |

## Per-Readout Per-Noetic

### phrase_first

| Noetic | Name | Exact | Top-2 | Mean target probability | Predicted counts |
|---|---|---:|---:|---:|---|
| `^1` | Mind | 0.000 | 0.000 | 0.001 | `{'^2': 1, '^8': 2, '^9': 1}` |
| `^2` | Positive | 0.000 | 0.250 | 0.000 | `{'^8': 4}` |
| `^3` | Negative | 0.000 | 0.000 | 0.000 | `{'^2': 1, '^8': 3}` |
| `^4` | Vibration | 0.000 | 0.000 | 0.000 | `{'^2': 1, '^8': 3}` |
| `^5` | Female | 0.000 | 0.000 | 0.000 | `{'^3': 1, '^8': 2, '^9': 1}` |
| `^6` | Male | 0.000 | 0.000 | 0.000 | `{'^8': 4}` |
| `^7` | Rhythm | 0.000 | 0.000 | 0.000 | `{'^8': 4}` |
| `^8` | Above/Cause | 0.750 | 0.750 | 0.736 | `{'^8': 3, '^9': 1}` |
| `^9` | Below/Effect | 0.500 | 0.500 | 0.501 | `{'^4': 1, '^6': 1, '^9': 2}` |
| `^0` | Idea | 0.000 | 0.000 | 0.002 | `{'^1': 1, '^4': 1, '^8': 1, '^9': 1}` |

### phrase_mean

| Noetic | Name | Exact | Top-2 | Mean target probability | Predicted counts |
|---|---|---:|---:|---:|---|
| `^1` | Mind | 0.500 | 0.750 | 0.500 | `{'^1': 2, '^2': 1, '^5': 1}` |
| `^2` | Positive | 0.000 | 0.250 | 0.000 | `{'^1': 2, '^5': 2}` |
| `^3` | Negative | 0.000 | 0.000 | 0.000 | `{'^2': 2, '^5': 2}` |
| `^4` | Vibration | 0.000 | 0.000 | 0.000 | `{'^1': 1, '^5': 2, '^8': 1}` |
| `^5` | Female | 0.000 | 0.000 | 0.000 | `{'^1': 1, '^3': 2, '^7': 1}` |
| `^6` | Male | 0.000 | 0.000 | 0.000 | `{'^1': 2, '^2': 2}` |
| `^7` | Rhythm | 0.000 | 0.000 | 0.000 | `{'^1': 1, '^2': 2, '^9': 1}` |
| `^8` | Above/Cause | 0.000 | 0.000 | 0.000 | `{'^1': 1, '^2': 2, '^0': 1}` |
| `^9` | Below/Effect | 0.000 | 0.000 | 0.000 | `{'^2': 1, '^5': 2, '^0': 1}` |
| `^0` | Idea | 0.750 | 1.000 | 0.748 | `{'^2': 1, '^0': 3}` |

### phrase_last

| Noetic | Name | Exact | Top-2 | Mean target probability | Predicted counts |
|---|---|---:|---:|---:|---|
| `^1` | Mind | 0.000 | 0.250 | 0.000 | `{'^3': 1, '^8': 3}` |
| `^2` | Positive | 0.000 | 0.000 | 0.007 | `{'^3': 2, '^8': 2}` |
| `^3` | Negative | 0.250 | 0.750 | 0.262 | `{'^1': 2, '^3': 1, '^8': 1}` |
| `^4` | Vibration | 0.000 | 0.000 | 0.000 | `{'^3': 2, '^9': 2}` |
| `^5` | Female | 0.000 | 0.000 | 0.000 | `{'^3': 2, '^8': 2}` |
| `^6` | Male | 0.000 | 0.000 | 0.000 | `{'^1': 1, '^3': 1, '^8': 1, '^9': 1}` |
| `^7` | Rhythm | 0.000 | 0.000 | 0.000 | `{'^1': 1, '^8': 2, '^9': 1}` |
| `^8` | Above/Cause | 0.500 | 0.500 | 0.498 | `{'^3': 2, '^8': 2}` |
| `^9` | Below/Effect | 0.250 | 0.250 | 0.250 | `{'^3': 1, '^8': 2, '^9': 1}` |
| `^0` | Idea | 0.000 | 0.000 | 0.000 | `{'^3': 1, '^8': 3}` |

## Boundary

Stage 28C tests phrase-level readout positions for single Noetic colloquialisms on Pythia-160M. It does not test Noetic clusters, retrained colloquialism probes, full TKS formulas, exact neurons, or open-ended generation control.
