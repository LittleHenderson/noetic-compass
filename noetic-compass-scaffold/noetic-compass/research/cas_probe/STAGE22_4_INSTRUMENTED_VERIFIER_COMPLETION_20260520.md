# Stage 22.4 Instrumented Verifier Completion

**Status:** `STAGE22_4_DIAGNOSTIC_ROWS_EMITTED`

## What Ran

The patched Stage 19B cross-architecture verifier was uploaded to the pod and
rerun with:

```bash
python run_stage19b_cross_arch_foundation_verification_stack.py \
  --models olmo1b,qwen15b \
  --emit-diagnostics \
  --out-report stage22_4_instrumented_cross_arch_verification_stack_20260519.json \
  --out-md STAGE22_4_INSTRUMENTED_CROSS_ARCH_VERIFICATION_STACK_20260519.md
```

The first SSH-held attempt hit the client timeout. The second run used detached
logging and completed successfully.

## Headline Result

The verifier result remains the Stage 19B cross-architecture result:

| Model | Status | Accepted accuracy | Coverage | Silent error | Suppressed |
|---|---|---:|---:|---:|---:|
| OLMo-1B | `DIAGNOSTIC_ONLY` | `98.16%` | `71.73%` | `1.84%` | `665` |
| Qwen2.5-1.5B | `DIAGNOSTIC_ONLY` | `99.49%` | `74.57%` | `0.51%` | `598` |

The strict product gate remains `NULL` because coverage is below `80%` on both
architectures. The diagnostic claim remains strong: accepted rows stay
high-precision, while cross-architecture coverage is calibration-limited.

## Diagnostic Row Audit

| Model | Test rows | Diagnostic rows | Accepted | Suppressed | Row parity |
|---|---:|---:|---:|---:|---|
| OLMo-1B | `2352` | `2352` | `1687` | `665` | `pass` |
| Qwen2.5-1.5B | `2352` | `2352` | `1754` | `598` | `pass` |

Per-row diagnostics now exist for accepted and suppressed rows. Each row carries:

- `rpm_satisfaction`
- `rpm_gate_decision`
- `lacunarity_scores`
- `gap_map_summary`
- `lacunarity_gate_decision`
- `inversion_axis_scores`
- `inversion_flag_count`
- `inversion_gate_decision`
- `gate_decisions`

## Attribution Boundary

| Diagnostic | Status | Rows |
|---|---|---:|
| RPM proxy | `proxy_measurable` | OLMo `2081`, Qwen `2061` |
| Lacunarity proxy | `proxy_measurable` | OLMo `2352`, Qwen `2352` |
| Inversion numeric scan | `not_measurable` | `0` |

RPM and lacunarity are deterministic runtime proxies:

- RPM proxy = Drive/Register recomposition consistency.
- Lacunarity proxy = readout-vote and trace-state concentration.

Inversion is still not a numeric diagnostic. Its fields are emitted with
`not_evaluated` / `not_measurable` markers so downstream tools cannot mistake
missing inversion evidence for a null effect.

## Artifact Hashes

| Artifact | SHA-256 |
|---|---|
| `stage22_4_instrumented_cross_arch_verification_stack_20260519.json` | `6c17895d2e385ce57141bbd58fc705060bb10a616ba1ad102203e1a7b79a4c33` |
| `STAGE22_4_INSTRUMENTED_CROSS_ARCH_VERIFICATION_STACK_20260519.md` | `73bdd01d08193fdb49febda4cea011550dd57adba6fad67531fb759450938dd5` |

## Next

Stage 22.4 closes the full-row diagnostic emission gap. The next useful gate is
Stage 22.5: use this artifact to compute full-row RPM/lacunarity proxy
attribution for accepted and suppressed rows, while keeping inversion explicitly
out of scope until the scanner is wired.
