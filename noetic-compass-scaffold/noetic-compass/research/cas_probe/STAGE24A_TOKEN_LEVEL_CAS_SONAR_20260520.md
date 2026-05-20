# Stage 24A Token-Level CAS Sonar

**Status:** `STAGE24A_SONAR_TOKEN_SIGNATURES_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH`

## Plain English

This report measures whether the Stage 7 Foundation probe directions have class-specific token signatures in Pythia-160M's output embedding space. It is token-level diagnostic attribution, not open-ended generation control.

## Probe

- Model: `EleutherAI/pythia-160m`
- Locked readout: `X_focus` layer `6`
- Probe test accuracy: `0.7895`
- Artifact contract: `LOCAL_RECAPTURE_HASH_MISMATCH`

## Pair-Similarity Controls

| Metric | Actual | Random mean | Random p95 | p(random >= actual) |
|---|---:|---:|---:|---:|
| `same_drive_minus_hard_partner` | 0.157632 | -0.000858 | 0.032082 | 0.0099 |
| `same_register_minus_hard_partner` | -0.038578 | -0.000591 | 0.030049 | 1.0000 |
| `same_drive_minus_different` | 0.589900 | -0.000030 | 0.037811 | 0.0099 |
| `same_register_minus_different` | 0.393690 | 0.000237 | 0.023678 | 0.0099 |

## Top-Token Readability

- Readable rate: `0.6741`
- Readable tokens: `453 / 672`

## Example Top Tokens

- `F1T`: Spanish, eneath, Italian, CLUS, Bibliography
- `F1A`: sty, ascii, wikipedia, bug, AJ
- `F1f`: oline, olin, idase,  bills, Statement
- `F1E`: ferent,  DOC,  latitude, location, ounty
- `F2T`: rets, mathds, widetilde, underbrace, quette
- `F2A`:  supernatants,  authorities,  comments,  finally,  supernatant
- `F2f`:  charged,  Securities,  Charg,  saturation,  phosph

## Boundary

Stage 24A sonar projects trained readout directions through static output embeddings. It does not prove exact neurons, SAE-disentangled features, raw CAS-symbol understanding, or that the model would generate the listed tokens in free-form decoding.
