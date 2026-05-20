# Stage 22.1 Gate Attribution Bench

**Status:** `STAGE22_1_GATE_ATTRIBUTION_COMPLETE`

## Headline

| Gate | Status | Attribution |
|---|---|---|
| Ensemble gate | `MEASURABLE` | coverage `90.1%`, accepted accuracy `91.3%` |
| Factor consistency | `MEASURABLE` | accuracy `4.1%` vs ensemble, coverage `-7.6%` vs ensemble |
| Trace stability | `MEASURABLE` | accuracy `3.4%` vs factor, coverage `-9.4%` vs factor |
| Generation readiness | `PARTIALLY_MEASURABLE` | policy path measurable; neural lacunarity/RPM/inversion absent |
| Evidence Packet | `MEASURABLE` | completeness `100.0%` |
| RPM | `NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS` | Per-row RPM satisfaction is not recorded except placeholder policy evidence. |
| Lacunarity | `NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS` | Neural lacunarity-head values are absent from Stage 19/20 locked reports. |
| Inversion scan | `NOT_MEASURABLE_FROM_LOCKED_ARTIFACTS` | Per-row inversion scan outputs are absent from Stage 19/20 locked reports. |

## Mode Selector

| Mode | Coverage | Accepted accuracy | Silent error |
|---|---:|---:|---:|
| `BALANCED` | `82.6%` | `95.4%` | `4.6%` |
| `HIGH_PRECISION` | `73.2%` | `98.8%` | `1.2%` |
| `MAX_COVERAGE_TRIAGE` | `90.1%` | `91.3%` | `8.7%` |

## Boundary

Only gates with per-row or component-level measurements in locked artifacts may receive numeric attribution. RPM, lacunarity, and inversion require a fresh Stage 22.2 runner unless per-row signals are added to the artifact set.
