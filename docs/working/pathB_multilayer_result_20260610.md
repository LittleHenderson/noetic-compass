# Path B — multi-layer probe sweep: APPARENT win is SURFACE LEAKAGE (not an internal detector)

**Date:** 2026-06-10  ·  **Status: EXPLORATORY — false-positive flagged.** The automated script printed "POSITIVE (internal detection REAL, layer 12)". **That verdict is OVERRIDDEN here on disciplined grounds: it is surface/payload leakage, not internal cognition.**

## What ran
Captured raw activations at all 29 hidden_states indices (0=embeddings, 1..28=blocks), prompt-state + early-generation window, on the existing 280 prompts (240 injected + 40 clean), greedy/fp32/seed 1234 (reproduces v1 generations, so v1 verified labels apply by prompt_id). Locally: fresh L2 comply/refuse logistic probe per layer×state, 6-fold stratified CV, bootstrap CIs. Labels: COMPLIED 160 / REFUSED 24 (within injected). npz `pathB_activations.npz`, archived to `D:\tksCAS-archive\pathB_multilayer_20260610\`.

## Result (and why it is a trap)
- **WINDOW AUC ≈ 0.999–1.000 at EVERY layer**, including **layer 0**. PROMPT AUC ≈ 0.89–0.95, **layer 0 = 0.927**.
- **Layer 0 is the raw token embeddings — zero transformer computation.** It can only encode the literal tokens. So near-ceiling AUC there is the smoking gun:
  - **Window ≈ 1.0 = surface leakage.** The window is the first 8 *generated* tokens. REFUSED responses literally begin "I cannot / I'm sorry / I won't…"; COMPLIED begin with the content — *different tokens*. The probe reads the refusal text, not a hidden state. (This is exactly what the v4 design's **W0 pre-generation control** existed to catch; Path B as run had no such control — the "window" is post-generation.)
  - **Prompt ≈ 0.92 = the v1 payload confound.** COMPLIED vs REFUSED are largely *different prompts* (different payloads; the 24 refusals concentrate in the system-prompt-extraction classes). Layer-0 prompt AUC 0.93 = the probe reads *which payload* from its token embeddings, not the model's stance.
- Neither read needs any computation to hit near-ceiling → **both are surface confounds**, the two the program has fought since v1.

## Honest verdict
**Path B did NOT validate an internal comply/refuse detector.** It reproduced leakage. The frozen criteria ("window AUC ≥ 0.75") were necessary but **insufficient** — they lacked a W0 pre-generation control and assumed matched payloads, so they accepted a leakage result. The clean test still requires **matched comply/refuse on the SAME prompt, read BEFORE generation** — which our data lacks (`G_matched = 2` in both v1 and v4).

## Implication for the 40/28/recipe idea
A richer encoding (40 Elements / 28 Foundations / CAS recipes) **cannot fix leakage** — it would leak more elaborately. The blocker is the **data design** (no matched pairs), not the readout's richness. So:
- The richer CAS **formula** belongs on the **output side** (where reading the produced text is legitimate) — there it buys the traceable `Θ(Ω)` equation per response (the product value), not a false internal claim.
- A real internal test needs a matched-pair capture (v4-style sampling, but with enough refusals to clear `G_matched ≥ 40`) read at W0 (pre-generation) — a deliberate build, not salvageable from v1.

**Near-term honest capability stands: the output-side post-hoc Noetic-Polarity audit (text-scored ^2−^3, AUC 0.956).**
