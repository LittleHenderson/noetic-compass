# Stage 24B 40-Element Token Sonar

**Status:** `STAGE24B_40_ELEMENT_SONAR_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH`

## Plain English

This report measures whether original TKS 40-Element readout directions have class-specific token signatures in Pythia-160M's output embedding space. It tests domain and Noetic token geometry directly, rather than relying on the weaker Foundation Register axis.

## Probe

- Model: `EleutherAI/pythia-160m`
- Locked readout: `X_focus` layer `5`
- Probe test accuracy: `0.8980`
- Artifact contract: `LOCAL_RECAPTURE_HASH_MISMATCH`

## Pair-Similarity Controls

| Metric | Actual | Random mean | Random p95 | p(random >= actual) |
|---|---:|---:|---:|---:|
| `same_domain_minus_hard_partner` | -0.049363 | 0.000048 | 0.018363 | 1.0000 |
| `same_noetic_minus_hard_partner` | -0.046497 | 0.000059 | 0.021461 | 1.0000 |
| `same_domain_minus_different` | 0.066225 | 0.000135 | 0.016242 | 0.0099 |
| `same_noetic_minus_different` | 0.069090 | 0.000147 | 0.030619 | 0.0099 |

## Top-Token Readability

- Readable rate: `0.6969`
- Readable tokens: `669 / 960`

## Example Top Tokens

- `A1`: cedes,  sounding,  sink,  defeats,  meets
- `A2`:  call, itat,  Call, ver, ager
- `A3`: ableness, ificate, urations,  char, licts
- `A4`: IL, Export, Import, Energy, Invoke
- `A5`:  Father,  aside,  swine,  father, father
- `A6`: po,  conductors,  pressing,  conductor,  sense
- `A7`: <|padding|>, nav, imonit, FFIRMED, documentclass
- `A8`: hin, iam, Ks, require,  near
- `A9`:  ranks, wig, irt, ament, ion
- `A10`:  courts,  vain,  such, tis,  objects

## Boundary

Stage 24B projects trained 40-Element readout directions through static output embeddings. It does not prove exact neurons, SAE-disentangled features, raw CAS-symbol understanding, or that the model would generate the listed tokens in free-form decoding.
