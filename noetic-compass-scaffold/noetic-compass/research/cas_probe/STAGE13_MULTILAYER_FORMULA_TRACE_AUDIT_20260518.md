# Stage 13 Multi-Layer Formula Trace Audit

**Status:** `STAGE13_MULTILAYER_TRACE_AUDIT_COMPLETE`

## Plain English

CAS Harness can inspect open-model hidden activations by training probes over saved activation snapshots. In this audit, it traces the Stage 12 formula-family signal across every layer and readout position, then names where the signal is strong, where it drifts, and where blind spots appear.

Weights are static. Activations are what change when an input passes through the model. So the correct phrase is activation evidence or weight alignment, not weights firing.

## Headline Reproduction

- Prior Stage 12 readout/layer: `final_token` layer `2`
- Prior Stage 12 test accuracy: `0.8995`
- Recomputed Stage 13 matching accuracy: `0.8995`

## Best Multi-Layer Readout

- Readout: `focus_token`
- Layer: `12`
- Validation accuracy: `1.0000`
- Test accuracy: `0.9540`
- Test lacunarity: `0.0016`
- Mean confidence: `0.9637`
- Normalized entropy: `0.0452`

## Readout Layer Scan

| Readout | Best val layer | Val acc | Test acc | Test lacunarity |
|---|---:|---:|---:|---:|
| `focus_token` | 12 | 1.0000 | 0.9540 | 0.0016 |
| `final_token` | 7 | 1.0000 | 0.9186 | 0.0018 |
| `mean_over_seq_len` | 5 | 0.8500 | 0.6752 | 0.0134 |

## Blind Spot Candidates

- `focus_token`: `cardinality_assertion` (0.803), `set_operation_formula` (0.828), `membership_assertion` (0.818), `cover_partition_formula` (0.849), `yield_query` (0.854)
- `final_token`: `cardinality_assertion` (0.777), `set_operation_formula` (0.818), `production_recipe` (0.838), `membership_assertion` (0.835), `cover_partition_formula` (0.846)
- `mean_over_seq_len`: `relation_dependency` (0.551), `production_recipe` (0.602), `membership_assertion` (0.617), `cover_partition_formula` (0.622), `yield_query` (0.645)

## Trace Stability

| Readout | Stable-correct | Stable-wrong | Early-correct-drift | Late-emerging | Conflicted | Uncertain |
|---|---:|---:|---:|---:|---:|---:|
| `focus_token` | 3756 | 8 | 98 | 85 | 253 | 0 |
| `final_token` | 3635 | 0 | 276 | 68 | 221 | 0 |
| `mean_over_seq_len` | 1907 | 145 | 986 | 343 | 819 | 0 |

## Example Audit Pack

The JSON report includes up to 40 high-priority examples per readout, sorted toward stable-wrong, conflicted, uncertain, and early-drift rows first.

## Boundary

This is a hidden-activation trace audit. It supports blind-spot and drift inspection for open models with activation access. It does not prove Pythia executes a CAS compiler, does not identify exact causal neurons, and does not prove generation steering.
