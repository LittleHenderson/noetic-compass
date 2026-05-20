# Stage 22.4 Instrumented Verifier Preflight

**Status:** `RUNNER_PATCH_READY_LOCAL_ARTIFACTS_MISSING`

## Checks

- Runner patched: `True`
- `--emit-diagnostics` flag present: `True`
- Diagnostic row helper present: `True`
- Diagnostic rows emitted by runner: `True`
- Local activation artifacts present: `False`
- Can run locally: `False`
- Inversion numeric proxy ready: `True`

## Required Fields

| Field | Present |
|---|---:|
| `rpm_satisfaction` | `True` |
| `rpm_gate_decision` | `True` |
| `lacunarity_scores` | `True` |
| `gap_map_summary` | `True` |
| `lacunarity_gate_decision` | `True` |
| `inversion_axis_scores` | `True` |
| `inversion_flag_count` | `True` |
| `inversion_gate_decision` | `True` |
| `gate_decisions` | `True` |

## Activation Artifacts

| Artifact | Present |
|---|---:|
| `stage15_olmo1b_activations_20260519.npz` | `False` |
| `stage16_qwen15b_activations_20260519.npz` | `False` |

## Boundary

The runner now emits Stage 22.2-compatible row fields. RPM and lacunarity are runtime proxy diagnostics. Inversion fields are numeric Stage 22.6 runtime structural proxies when the patched runner is used.

## Pod Command

```bash
python research/cas_probe/run_stage19b_cross_arch_foundation_verification_stack.py --models olmo1b,qwen15b --emit-diagnostics --out-report stage22_4_instrumented_cross_arch_verification_stack_20260519.json --out-md STAGE22_4_INSTRUMENTED_CROSS_ARCH_VERIFICATION_STACK_20260519.md
```
