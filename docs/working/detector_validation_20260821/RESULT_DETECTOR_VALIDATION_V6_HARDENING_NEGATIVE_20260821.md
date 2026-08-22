# RESULT v6 — framing/surface hardening — a LOAD-BEARING NEGATIVE — 2026-08-21

**The most important result in this series, and it is a NEGATIVE that corrects the earlier over-optimistic readings. It is not buried; it is the headline.** Real `pythia-160m` through the attested engine, CPU, `$0`. Raw: `detector_validation_v6_hardening_results.json` (sha256 in file). Script: `detector_validation_v6_hardening.py`.

## What this tested — the mandatory char-level surface control

A prior W0 detector was **withdrawn** for failing exactly this control. The rule (house discipline): a detector is real only if it beats a **char-ngram surface baseline** on stimuli where the construct is conveyed **without the training vocabulary**. Protocol: train the activation detector on **explicit** stimuli, test on an **implicit** set (valence via scenario, no good/bad adjectives; causality with the *because/so/therefore* connectives **stripped**), and compare — on the same implicit test set — against a char-ngram (n=2,3,4) nearest-centroid surface model. Layer 6.

## Result — the detectors do NOT survive the surface control

| axis (train explicit → test implicit) | activation detector | char-ngram surface | shuffle null | verdict |
|---|---:|---:|---:|---|
| `^2`/`^3` valence (implicit scenario) | 0.562 | 0.438 | 0.312 | **NOT HARDENED** |
| `^8`/`^9` cause-effect (connective-stripped) | 0.562 | **0.625** | 0.312 | **NOT HARDENED** |

- **Valence:** the activation detector beats the surface baseline (`0.562` vs `0.438`) — a weak positive — but sits far below the `0.70` hardening bar. On implicit valence it is barely above chance.
- **Cause/effect:** the surface baseline **beats** the activation detector (`0.625` vs `0.562`). Strip the connectives and the `^8`/`^9` detector, trained on connective-rich stimuli, **fails to transfer** — confirming the exact confound flagged as an honest caveat in v3.

## What this means — honest and load-bearing

**The earlier v1–v5 "perfect" cross-topic results are register-bound, and substantially surface-confounded.** Those runs tested cross-*topic* but within the same *explicit register* as training. This run shows the detectors **do not generalize to implicit expression** of the same construct on this model: strip the giveaway vocabulary/connectives and separation collapses to ~`0.56` (near chance for a 2-way task).

- This **does not invalidate** the v1–v5 numbers — they are real for same-register, cross-topic separation.
- It **bounds** them: what was measured is closer to "the model linearly encodes the surface framing of valence/causality" than "the model has a transferable valence/causality representation the detector reads."
- It is the correct, expected outcome of a rigorous control, and it is worth more than another perfect number: it is the line between a real harness and a demo.

## Correction to my earlier claim

I earlier reported the valence and cause-effect axes as strongly validated and generalizing. That was true only within the explicit register. **The surface-controlled test downgrades them to NOT HARDENED.** The spec-sheet entries for v1–v3 stand as same-register results; this entry is the surface-control ceiling that qualifies them.

## The fix this points to (not done here)

- Train detectors on **register-diverse** stimuli (explicit + implicit mixed) so the direction cannot ride on surface markers, then re-run this exact control.
- Report every axis with its **surface-controlled** number alongside its same-register number.
- This is now the gating test every CAS detector must pass before any "validated" claim.

## Claim states

- **Real:** ~112 forward passes on real weights; the activation detector; the char-ngram baseline; the shuffle null; every number.
- **Accepted:** none.
- **Open:** register-diverse training; larger n (16 test items per axis is noisy); other axes (Domain-4, Operator-10) must face this same control.
- **Not licensed:** any product sentence claiming these axes are validated — the surface-controlled result is NOT HARDENED.

**No pod. No GPU. `$0`. A negative kept as an asset.**
