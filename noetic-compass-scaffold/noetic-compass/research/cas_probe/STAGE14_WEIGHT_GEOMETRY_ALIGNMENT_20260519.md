# Stage 14 Weight Geometry / Alignment Inspection

**Status:** `CAS_SUBSPACE_WEIGHT_ALIGNMENT_ABOVE_RANDOM_ON_SOME_CHECK`

## Plain English

Weights do not fire. This report inspects whether the trained CAS Foundation probe subspace is geometrically aligned with Pythia-2.8B's static input/output token-weight matrices.

## Probe

- Selected layer: `14`
- Probe rank: `27`
- Test accuracy: `0.8588`

## Alignment

| Check | Actual | Random mean | Random p95 | p(random >= actual) |
|---|---:|---:|---:|---:|
| `output_weight_energy_fraction` | 0.011178 | 0.010524 | 0.010826 | 0.0099 |
| `input_weight_energy_fraction` | 0.010583 | 0.010547 | 0.010667 | 0.3465 |
| `output_logit_lens_energy_fraction` | 0.027121 | 0.009582 | 0.013912 | 0.0099 |

## Interpretation

At least one weight-geometry check is above random same-rank controls. This supports a bounded alignment-inspection claim, not generation control.

## Boundary

This is weight-geometry evidence only. It does not prove exact causal neurons, hidden-state steering, or raw-symbol understanding.
