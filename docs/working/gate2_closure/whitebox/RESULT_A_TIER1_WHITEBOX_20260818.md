# RESULT — A tier-1 white-box loop on pythia-160m (2026-08-18)

**Verdict: WIRED, not WORKING.** The loop runs end-to-end on the real model; the science
result is uninterpretable. Honest wired ≠ works.

Ran on RunPod (A40, `pythia-160m@50f5173d`, research venv), script
`cas_whitebox_loop_v1.py`. Part = "caveating". Direction = diff-of-means of hidden states
(present vs absent) at layer 7.

## What worked (the machinery — real milestone)
- Model loaded on the real weights; forward hooks on `gpt_neox.layers[6]` fire.
- Caveat direction found: `||diff||=187.6`, probe separation-accuracy **0.781** (present proj 341.9 vs absent 154.3) — a real, moderate linear direction.
- Both **ablate** (rank-1 projection removal) and **steer** (additive) apply to the live residual stream during generation. The whole loop executes.
- Fixed a real bug: newer transformers returns a Tensor (not a `(tensor,)` tuple) from `GPTNeoXLayer`; the hook now handles both.

## What broke (result is garbage)
- **Steer strength ~6x too strong.** `steer = 6 x diff` (norm ~1125) drove the residual far out of distribution → pure repetition (`"nucleotide nucleotide..."`). Every steer/control number is meaningless.
- **pythia-160m too small** for coherent caveating — baseline output is already degenerate (`"I'm not sure how to do this. I'm not sure..."`), so there is no behavioral caveat to add or remove.
- **Ablation showed no real signal** (baseline caveat-proj ~2.8; almost nothing to remove). Ablate effect +2.9 vs control +0.7 = noise.

## Fixes for the next run
1. **Calibrate steer strength** — sweep the coefficient DOWN (fractions of the gap, on the unit direction) until the output stays coherent; only then is the projection/behavioral measure meaningful.
2. **Bigger model** — `pythia-1b` and `pythia-2.8b` are already cached on the pod; use one so caveating is coherent enough to measure.
3. **Better behavioral measure** — hedge-word / LLM-judge on COHERENT output, not projection-on-degenerate-text.

## Pod state
Report JSON: `/workspace/cas_whitebox_loop_report.json`. Script: `/workspace/cas_whitebox_loop.py`. Temp files left by analysis: `/workspace/_q*.out`, `/workspace/_fa.out` (harmless).
