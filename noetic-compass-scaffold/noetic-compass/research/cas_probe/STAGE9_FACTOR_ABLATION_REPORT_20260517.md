# Stage 9.1 40 Elements Factor/Ablation Report

**Status:** `STAGE9_FACTOR_CHECK_FULL_PASS`

Locked readout: `focus_token` layer `5`.

| Factor | Status | Chance | Activation Acc | Best Text Acc | Lift | Ablated Acc | Random Max Disruption | p(random >= targeted) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| domain | `FACTOR_READOUT_AND_ABLATION_PASS` | 0.2500 | 0.9230 | 0.7500 | +0.1730 | 0.2500 | 0.0000 | 0.0323 |
| noetic | `FACTOR_READOUT_AND_ABLATION_PASS` | 0.1000 | 0.9154 | 0.7500 | +0.1654 | 0.1000 | 0.0000 | 0.0323 |
| interaction | `FACTOR_READOUT_AND_ABLATION_PASS` | 0.0250 | 0.8980 | 0.5009 | +0.3971 | 0.0250 | 0.0000 | 0.0323 |

## Boundary

This is readout-level factorization and ablation evidence. It does not prove hidden-state steering, raw-symbol understanding, visible generation control, or cross-model generality.
