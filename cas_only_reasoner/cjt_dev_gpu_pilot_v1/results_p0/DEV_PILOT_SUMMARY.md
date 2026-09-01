# CJT-DEV-P1 development pilot summary

**Stage:** P0 | **updates:** 100 | **selected layer L\*:** 6 | **is_real_model:** True | **status:** `P0_SMOKE_OK`

Development-only, non-claim-bearing. No protected split, no claim, no CAS-specific language. Device: AWS g4dn.xlarge T4 us-west-2.

## Final validation accuracy (mean over seeds)

| arm | mean val acc | std | val loss | params |
|---|---|---|---|---|
| S0 plain | 0.2310 | 0.0000 | 1.9218 | 942574 |
| S3 CAS (one-hot) | 0.2140 | 0.0000 | 1.9991 | 951744 |
| S6 uniform | 0.2130 | 0.0000 | 1.9967 | 951744 |
| S7-Δ WordNet soft | 0.2140 | 0.0000 | 1.9990 | 951744 |

## Arm comparison (mean val accuracy)

- **S3 − S0** = -0.0170
- **S3 − S6** = +0.0010
- **S3 − S7-Δ** = +0.0000
- updates to 0.80 val acc: {'S0': None, 'S3': None, 'S6': None, 'S7D': None}
- updates to 0.90 val acc: {'S0': None, 'S3': None, 'S6': None, 'S7D': None}
- updates to 0.95 val acc: {'S0': None, 'S3': None, 'S6': None, 'S7D': None}

## Registered surface references

- **B0 floor** (val): 0.6680
- **B1 ceiling** (val): 1.0000 (the task is exactly surface-solvable)

## Development verdict: `P0_SMOKE_OK`

P0 smoke: all arms trained, losses finite

Total wall-clock: 317.3s across 4 runs.

