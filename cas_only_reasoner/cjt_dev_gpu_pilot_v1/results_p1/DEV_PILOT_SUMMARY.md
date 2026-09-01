# CJT-DEV-P1 development pilot summary

**Stage:** P1 | **updates:** 1000 | **selected layer L\*:** 24 | **is_real_model:** True | **status:** `NO_DEV_SIGNAL`

Development-only, non-claim-bearing. No protected split, no claim, no CAS-specific language. Device: AWS g4dn.xlarge T4 us-west-2.

## Final validation accuracy (mean over seeds)

| arm | mean val acc | std | val loss | params |
|---|---|---|---|---|
| S0 plain | 0.2117 | 0.0056 | 2.0179 | 942574 |
| S3 CAS (one-hot) | 0.2123 | 0.0005 | 2.0130 | 951744 |
| S6 uniform | 0.2140 | 0.0037 | 2.0090 | 951744 |
| S7-Δ WordNet soft | 0.2113 | 0.0012 | 2.0145 | 951744 |

## Arm comparison (mean val accuracy)

- **S3 − S0** = +0.0007
- **S3 − S6** = -0.0017
- **S3 − S7-Δ** = +0.0010
- updates to 0.80 val acc: {'S0': None, 'S3': None, 'S6': None, 'S7D': None}
- updates to 0.90 val acc: {'S0': None, 'S3': None, 'S6': None, 'S7D': None}
- updates to 0.95 val acc: {'S0': None, 'S3': None, 'S6': None, 'S7D': None}

## Registered surface references

- **B0 floor** (val): 0.6680
- **B1 ceiling** (val): 1.0000 (the task is exactly surface-solvable)

## Development verdict: `NO_DEV_SIGNAL`

S3 does not clear all three controls by >=0.02: S3-S0=0.000666 S3-S6=-0.001667 S3-S7D=0.001

Total wall-clock: 86.3s across 12 runs.

