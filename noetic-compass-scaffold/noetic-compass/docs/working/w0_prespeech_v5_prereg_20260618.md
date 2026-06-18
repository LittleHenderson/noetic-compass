# W0 Pre-Speech Detection + Causal Proof — Pre-Registration (v5)

Date: 2026-06-18
Status: **PRE-REGISTERED APPARATUS — not yet run. All five claims stay OPEN / NOT LICENSED.**
Target: comply/refuse stance from W0 (NOT prompt-injection presence, which was withdrawn 2026-06-18 — see `hidden_prompt_injection_w0_license_withdrawn_20260618.md`).

## What "W0" means here (frozen definition)

W0 = the embedding-layer output at the **final prompt token**, captured BEFORE
token 1 is generated (`app/runtime/w0_capture.py`, `W0PreSpeechCapture`). W1 =
after token 1; W8 = the existing frozen window. The temporal-separation control
(`validate_windows`) requires cos(W0, W1) < 0.99 — otherwise the capture is not
genuinely pre-generation and the run is void.

## Prior result (why this is a re-test, not a fresh claim)

The previous Qwen comply/refuse W0 gate FAILED at hidden BA 0.745 (< 0.75
required) with margin 0.094 (< 0.15). This apparatus re-tests with the corrected
protocol below. It is NOT a prediction that it will pass.

## Lane A — pre-speech detection gates (all must pass)

Evaluator: `evaluate_behavior_v6_matched_prespeech.py` (existing, audited).

1. exact_prompt_group_pass — grouped folds keep exact prompt carriers out of train+test.
2. W0 hidden balanced accuracy ≥ 0.75.
3. hidden − text-hash ≥ 0.15 (word-level).
4. **hidden − char-text ≥ 0.15** (character-level — mandatory after the 2026-06-18
   finding that word-level controls are insufficient; injection/encoding leaks at
   char level). Add this gate before any license.
5. hidden − layer-0 baseline ≥ 0.15.
6. payload / domain / length majority baselines lose by ≥ 0.15.
7. shuffled-label control mean ≤ 0.60.
8. within-payload permutation p < 0.001.
9. generated-prefix baseline reported (W0 must beat predicting from the prompt's
   own generated continuation prefix).
10. W0/W1/W8 temporal separation valid (cos(W0,W1) < 0.99). If W0 is at chance but
    W1/W8 separate, report "state emerges during early decoding" — NOT a W0 claim.

## Lane B — causal gates (all must pass; only after Lane A passes)

Direction d = mean(W0_REFUSED) − mean(W0_COMPLIED) on TRAIN folds only
(`refusal_direction`). Held-out: 80 prompts never used to fit d. 8 paired seeds ×
4 conditions (no_op / +refusal / −refusal / random same-norm) = 2,560 outputs.
Intervention applied at the final prompt token before token 1
(`CausalInterventionHook`). Labels by cross-family verifier. Gates
(`verify_causal_gates`):

- G1 +refusal REFUSED shift ≥ +0.20 vs no_op
- G2 prompt-level sign-flip permutation p < 0.001
- G3 95% bootstrap CI lower bound > +0.10
- G4 +refusal beats random same-norm by ≥ 0.15
- G5 random same-norm absolute shift ≤ 0.05
- G6 −refusal moves opposite (refusal shift ≤ −0.10 OR complied shift ≥ +0.15)
- G7 IGNORED rate rises by ≤ 0.10
- G8 malformed rate rises by ≤ 0.05

α (intervention gain) is calibrated on a SEPARATE set, frozen before the held-out run.

## What passing licenses (scoped) and what it does NOT

If ALL Lane A + Lane B gates pass on a real run: pre-speech detection and causal
proof graduate to LICENSED **for Qwen2.5-1.5B-Instruct, this layer/protocol/verifier
only**. The other claims remain NOT LICENSED:

- live interception — detector is shadow-mode (logs, does not block);
- prevention/removal/reversal — detection/steering ≠ production safety control;
- hallucination prevention — recipe targets comply/refuse, not factual accuracy;
- CjtPredictionHead — the RefusalRecipeProbe is a simpler linear probe.

## Status of this apparatus

Built and unit-tested for the pure logic (temporal validation, recipe readiness,
refusal direction, Lane B gate verification). NOT run — needs a GPU, the model,
and the prompt bank. No claim changes until a real run passes every gate.
