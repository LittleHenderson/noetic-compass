# Stage 22.1 Gate Attribution Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Gate Matrix

| Gate | Status | Source | Limitation |
|---|---|---|---|
| `wrap_output_gate` | `reference_only` | raw/no-prefix floor and CPL2 likelihood comparator | The locked artifacts do not contain a live Wrap Output Gate toggle. |
| `ensemble_gate` | `measurable_from_locked_artifacts` | Stage 19B ensemble_only | Measured on OLMo/Qwen Stage 19B cross-architecture fixtures. |
| `factor_consistency_gate` | `measurable_from_locked_artifacts` | Stage 19B factor_consistent | This measures factor consistency, not the whole CAS compiler. |
| `trace_stability_gate` | `measurable_from_locked_artifacts` | Stage 19B stack minus factor_consistent | Gold labels score the result after the fact; runtime gate remains non-oracle. |
| `mode_selector_gate` | `measurable_from_locked_artifacts` | Stage 19C mode selector | Packages existing Stage 19B components; no fresh hidden-state inference. |
| `generation_readiness_gate` | `partially_measurable_from_locked_artifacts` | Stage 20B readiness packets | Stage 20B validates the Verification Stack path only; neural lacunarity/RPM/inversion signals are absent. |
| `evidence_packet_gate` | `measurable_from_locked_artifacts` | Stage 21A packet export | Evidence Packet completeness is auditability, not model accuracy. |
| `rpm_gate` | `not_measurable_from_locked_artifacts` | not recorded per row in Stage 19/20 locked reports | Stage 20B sample evidence sets rpm_satisfaction to 1.0 placeholders; no attribution possible. |
| `lacunarity_gate` | `not_measurable_from_locked_artifacts` | not recorded per row in Stage 19/20 locked reports | Stage 20B explicitly says neural lacunarity-head values are not present. |
| `inversion_scan_gate` | `not_measurable_from_locked_artifacts` | not recorded per row in Stage 19/20 locked reports | Stage 20B sample evidence sets inversion_flag_count to zero placeholders; no attribution possible. |

## Boundary

Only gates with per-row or component-level measurements in locked artifacts may receive numeric attribution. RPM, lacunarity, and inversion require a fresh Stage 22.2 runner unless per-row signals are added to the artifact set.
