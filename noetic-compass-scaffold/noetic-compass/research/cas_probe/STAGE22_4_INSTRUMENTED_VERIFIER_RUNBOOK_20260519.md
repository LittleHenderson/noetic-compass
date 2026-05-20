# Stage 22.4 Instrumented Verifier Runbook

**Status:** `RUNNER_PATCHED_LOCAL_EXECUTION_BLOCKED_BY_MISSING_ACTIVATIONS`

## Purpose

Stage 22.4 patches the Stage 19B cross-architecture verifier so the next pod
run emits Stage 22.2 diagnostic rows for every test example, including
suppressed rows.

The local workspace does not contain:

- `stage15_olmo1b_activations_20260519.npz`
- `stage16_qwen15b_activations_20260519.npz`

So the full verifier cannot be rerun locally. The code path is patched and
unit-tested; the data run must happen where the activation binaries exist.

## Command

```bash
python research/cas_probe/run_stage19b_cross_arch_foundation_verification_stack.py \
  --models olmo1b,qwen15b \
  --emit-diagnostics \
  --out-report stage22_4_instrumented_cross_arch_verification_stack_20260519.json \
  --out-md STAGE22_4_INSTRUMENTED_CROSS_ARCH_VERIFICATION_STACK_20260519.md
```

## What The Patch Emits

Each `diagnostic_rows[]` entry includes:

- `rpm_satisfaction`
- `rpm_gate_decision`
- `lacunarity_scores`
- `gap_map_summary`
- `lacunarity_gate_decision`
- `inversion_axis_scores`
- `inversion_flag_count`
- `inversion_gate_decision`
- `gate_decisions`

## Boundary

RPM and lacunarity are deterministic runtime proxies:

- RPM proxy = Drive/Register recomposition consistency.
- Lacunarity proxy = readout-vote and trace-state concentration.

Inversion is still not measured by the Stage 19B runner. Its fields are emitted
with `not_evaluated` / `not_measurable` markers so downstream tools cannot
mistake missing inversion evidence for a null effect.

## Expected Audit

After the pod run:

1. Check `diagnostic_rows` count equals OLMo test rows + Qwen test rows.
2. Check accepted and suppressed rows both have diagnostic rows.
3. Check `diagnostic_summary.inversion_measured_rows == 0`.
4. Rerun Stage 22.1 attribution against the Stage 22.4 artifact if the goal is
   proxy attribution for RPM/lacunarity.
5. Do not claim true inversion attribution until a real inversion scanner is
   wired into the runner.
