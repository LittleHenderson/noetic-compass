# Stage 22.2 Diagnostic Instrumentation Audit

**Status:** `INSTRUMENTATION_REQUIRED_BEFORE_ATTRIBUTION`

## Locked Artifact Audit

| Artifact | Instrumented | Present fields | Missing fields |
|---|---:|---|---|
| `stage19a_formula_verification_stack_20260519.json` | `false` | - | rpm_satisfaction, rpm_gate_decision, lacunarity_scores, gap_map_summary, lacunarity_gate_decision, inversion_axis_scores, inversion_flag_count, inversion_gate_decision, gate_decisions |
| `stage19b_cross_arch_foundation_verification_stack_20260519.json` | `false` | - | rpm_satisfaction, rpm_gate_decision, lacunarity_scores, gap_map_summary, lacunarity_gate_decision, inversion_axis_scores, inversion_flag_count, inversion_gate_decision, gate_decisions |
| `stage20b_generation_readiness_packets_20260519.json` | `false` | rpm_satisfaction, inversion_flag_count | rpm_gate_decision, lacunarity_scores, gap_map_summary, lacunarity_gate_decision, inversion_axis_scores, inversion_gate_decision, gate_decisions |

## Required Fresh-Runner Fields

| Field | Gate | Type | Purpose |
|---|---|---|---|
| `rpm_satisfaction` | `rpm_gate` | float in [0, 1] | Scalar runtime RPM-chain satisfaction used by the readiness gate. |
| `rpm_gate_decision` | `rpm_gate` | allow|caveat|constrain|suppress | Per-row decision attributable specifically to RPM. |
| `lacunarity_scores` | `lacunarity_gate` | object or numeric vector | Per-row state/fractal/domain/drive/RPM lacunarity values. |
| `gap_map_summary` | `lacunarity_gate` | object | Compact count/max/mean summary of the per-slot gap map. |
| `lacunarity_gate_decision` | `lacunarity_gate` | allow|caveat|constrain|suppress | Per-row decision attributable specifically to lacunarity/gap evidence. |
| `inversion_axis_scores` | `inversion_scan_gate` | array[7] float in [0, 1] | Per-axis inversion-resistance or inversion-risk scores. |
| `inversion_flag_count` | `inversion_scan_gate` | integer >= 0 | Number of inversion axes crossing the configured flag threshold. |
| `inversion_gate_decision` | `inversion_scan_gate` | allow|caveat|constrain|suppress | Per-row decision attributable specifically to inversion evidence. |
| `gate_decisions` | `rpm_gate` | object | Merged per-gate decisions for all diagnostic gates, preserving individual attribution. |

## Boundary

Current locked reports can validate ensemble, factor, trace, mode, readiness-policy, and evidence-packet layers. They cannot attribute RPM, lacunarity, or inversion gates until these per-row diagnostic fields are emitted by a fresh runner.
