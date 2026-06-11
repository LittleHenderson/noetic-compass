# Pre-speech compliance detection on a more-refusing model — scope (the path to the live/causal claim)

**Date:** 2026-06-10  ·  **Status: SCOPE.** Sharpens the open question from the corrected analysis: the live ("catch it before it speaks") detector is gated not on the topos theory but on whether the compliance state is **determinate pre-realization** in a given model. On Qwen-1.5B it is not (within-class pre-speech ^2−^3 = chance 0.56 — the empirical signature of graded truth before realization). The question is whether a different model decides earlier.

## The crisp, falsifiable target
On a candidate model, with the prompt-final state read **before any token is generated (W0)**:
- **PASS (live detection real):** a binary comply/refuse probe on W0 activations separates the two **above chance *within payload class*** (payload controlled), with a held-out CI lower bound > chance. This shows a *pre-speech* signal that is NOT payload identity and NOT realized-output surface — i.e. the compliance "potential" is already determinate in the activations.
- **FAIL (graded until realization, like Qwen):** within-class W0 AUC ≈ chance → the state is indeterminate pre-speech on this model too; only post-speech (output) detection works.

This is the one test that distinguishes the three claims cleanly:
| claim | test |
|---|---|
| output-side detection | output text ^2−^3 / recipe (already AUC 0.956 — shippable) |
| activation detection (post-speech) | window probe (already AUC ~1.0 — but reads realized output) |
| **pre-speech / live detection** | **W0 binary probe, within-class AUC > chance** ← this scope |
| causal (reads state independent of payload) | adds matched same-prompt pairs (still blocked by data scarcity) |

## What the build needs
1. **A model that genuinely flips comply↔refuse on borderline prompts** (so within-class both labels exist with enough n). Candidates: a safety-tuned instruct model that refuses extraction/borderline prompts more readily than Qwen-1.5B — pick by a cheap behavioral screen (the Stage-S screener already exists; reuse it).
2. **Its Gate-A typed probe** OR — simpler for this test — skip the typed probe entirely and read **raw W0 activations** directly (the binary probe does not need the 40-way Gate-A readout; it needs raw hidden states at W0).
3. **Capture W0 across layers** (reuse `capture_multilayer_pathB.py`, but record only the prompt-final position state — the single pre-generation read — so surface tokens cannot leak), label behaviorally, and run the within-class binary probe.
4. **Payload control built in:** screen prompts so that *each payload class* yields both labels on the chosen model (the within-class evaluation requires it). If no model gives within-class both-labels at n≥~40, the live claim is not testable and stays OPEN.

## Cost / sequencing
- Cheap behavioral screen of 2–3 candidate models for within-class comply/refuse flipping (~$2–5, the existing screener).
- Only if a model passes the screen: one W0 multi-layer capture + local within-class binary probe (~$2–5).
- Pre-register the PASS/FAIL above before the capture (decision-first).

## Recommendation
Do this **only if "live interception" is a required product claim.** The shippable capability today is the output-side recipe audit + (optionally) the activation-native post-speech detection probe (`detection_probe_window_v1.json`, claim ceiling = "reads realized output"). The live/causal claim is future work with a now-crisp falsifiable gate.
