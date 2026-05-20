# Stage 22.3 Diagnostic Sample Instrumentation

**Status:** `STAGE22_3_SAMPLE_INSTRUMENTATION_PARTIAL`

## Headline

- Instrumented accepted sample rows: `50`
- Rows with Stage 22.2 required field names present: `50`
- Suppressed sample rows seen: `50`
- Suppressed sample rows with votes: `0`
- Inversion-ready rows: `0`

## Boundary

This sample instrumentation proves the row contract shape for accepted Stage 19B sample rows. RPM and lacunarity are vote/factor proxies, not fresh neural RPM/lacunarity diagnostics. Inversion remains unmeasured. Full attribution requires rerunning the verifier with per-row diagnostics for both accepted and suppressed rows.

## Next Runner Requirements

- `emit_all_test_rows`: `true`
- `include_suppressed_row_votes`: `true`
- `compute_true_inversion_axis_scores`: `true`
- `compute_neural_or_deterministic_lacunarity_scores`: `true`
- `compute_rpm_satisfaction_without_gold_labels`: `true`