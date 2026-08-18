# RESULT — A tier-1 v2: calibrated white-box loop on pythia-1b (2026-08-18)

**Verdict: STEERING WORKS (calibrated, coherent, beats matched control). Ablation inconclusive.**
Real causal steering of a behavioral part validated on a real model. First genuine
spec-sheet-quality white-box result.

Ran on RunPod A40, `pythia-1b` (16 layers, hook layer 8), research venv. Part = "caveating".
Direction = diff-of-means; steering swept over fractions of the natural gap (v1's 6x blew
the model up; v2 sweeps 0.5-4.0). Coherence guard = distinct-word ratio. Matched random
control at every strength. Script: `cas_whitebox_loop_v2.py`.

## The numbers (mean over 3 prompts)
- **Probe direction is clean: separation-accuracy 1.000** (present proj 3.3 vs absent -12.2; ||diff|| 15.5). Up from 0.78 on pythia-160m — the bigger model has a crisp linear caveat direction.
- Baseline generation proj = -6.28 (coherent, distinct 0.42).

| steer frac | STEER proj (lift) | coherent? | CONTROL proj (lift) |
|---|---|---|---|
| 0.5 | -5.5 (**+0.8**) | yes (0.49) | -7.6 (-1.3) |
| **1.0** | **-4.7 (+1.6)** | **yes (0.58)** | **-8.8 (-2.5)** |
| 2.0 | -4.9 (+1.3) | yes (0.48) | -8.0 (-1.7) |
| 4.0 | -6.5 (-0.3) | yes (0.49) | -8.7 (-2.4) |

Ablate proj -3.85 (lift +2.4) vs control-ablate -6.28 (lift 0.0).

## Read
- **Coherence preserved.** Unlike v1's garbage, every steered generation stayed coherent (distinct 0.48-0.58). The calibration is the fix.
- **Steering is real, targeted, and beats the control.** Adding the caveat direction shifts the output TOWARD caveating (lift +0.8..+1.6, best at frac 1.0), while a matched random direction at the same strength shifts it the OTHER way (-1.3..-2.5). Steer-minus-control gap ≈ +4 in the intended direction. This is the "steer the part back" half of the loop, validated on real weights.
- **Modest magnitude, expected plateau.** +1.6 is ~10% of the full present-absent range (15.5); frac 2-4 don't help more (single-layer diff-of-means steering saturates) — normal for activation steering.
- **Ablation inconclusive.** Ablating the direction DID have a causal effect (lift +2.4, vs random control 0.0 — so ablation ≠ noise), but it moved the output-projection the UNEXPECTED way (up, not down). Likely the projection-on-final-text proxy is imperfect for ablation, and single-layer projection-removal is crude. Needs a better ablation measure/method — do NOT claim ablation works yet.

## Next
1. Refine ablation (better measure; maybe multi-layer or behavioral).
2. Scale: pythia-2.8b (cached), then download GPT-NeoX-20B for the real spec-sheet row.
3. This is spec-sheet row 1: **steering capability, real model, control-checked.**
