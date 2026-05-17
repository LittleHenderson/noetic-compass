# Stage 9 Gates: Original TKS 40 Elements

**Status:** pre-registered before any Stage 9 activation capture or probe run.

**Branch:** `experiment/cas-probe-pythia`

## Scope

Stage 9 tests the user's original TKS "40 Elements" intuition:

> 4 Worlds/Domains x 10 Noetics = 40 cognitive element slots.

Authorized for this first pass:

- Model: `EleutherAI/pythia-160m` only.
- Axis: original TKS 40 Elements (`A1..D10`).
- Mapping:
  - `A` = Spiritual / Transcendent register (`T`)
  - `B` = Mental / Analytical register (`A`)
  - `C` = Emotional / Affective register (`f`)
  - `D` = Physical / Embodied register (`E`)
  - TKS `1..10` = original noetic order:
    `1 Mind`, `2 Positive`, `3 Negative`, `4 Vibration`, `5 Female`,
    `6 Male`, `7 Rhythm`, `8 Above/Cause`, `9 Below/Effect`, `10 Idea`.
  - CAS zero-index note: TKS `10 Idea` corresponds to CAS `^0`; TKS
    `1..9` correspond to CAS `^1..^9`.
- Fixture: role-bound same-sentence counterfactual rows, following the Stage
  6/7 lesson: same sentence, two candidate roles, explicit `Focus: A/B`.
- Capture: focus-token, final-token, and mean-token Pythia hidden states.
- Primary assay: discriminative readout only.

Not authorized in this first Stage 9 pass:

- Pythia-1B or larger models.
- Llama, OLMo, Qwen, or other architectures.
- Hidden-state steering.
- Visible generated-text claims.
- Strategy/memo refresh.

## Why This Axis

The 28 Foundations tested Drive x Register. The 40 Elements test the more
direct CAS state-vector shape:

> Domain/Register x Noetic = 40 cognitive slots.

If this axis works, it may be the cleanest bridge between original TKS source
language and the CAS 40-slot cognitive state vector.

## Fixture Requirements

The builder must:

1. Preserve the original TKS element meanings in paraphrased operational form.
2. Avoid literal label leakage in the English prompt:
   - no `A1`, `B7`, etc.
   - no `^0`, `^1`, etc.
   - no explicit `CAS`, `TKS`, `noetic`, `element`, or label words inside
     the model-facing English prompt.
3. Use balanced labels across all 40 classes.
4. Include both contrast types:
   - same World/Domain, different Noetic
   - same Noetic, different World/Domain
5. Freeze train/val/test split before activation capture.

## Primary Readout Gate

Train all text baselines, metadata baselines, and activation readouts on the
same frozen split. Select the headline activation readout by validation score
only. Report locked-test scores after selection.

PASS_CLEAN requires all:

- Headline activation test accuracy lift over best text baseline `>= +0.05`.
- McNemar exact/binomial p vs best text baseline `< 0.05`.
- Headline activation test accuracy lift over strongest metadata baseline
  `>= +0.03`, unless the metadata baseline is explicitly pair/focus
  diagnostic-only and not usable without answer-key pair construction.
- Full 40-way test accuracy `>= 0.20` (`8x` chance; chance is `0.025`).

NULL if any:

- Headline activation test accuracy `< 0.10`.
- Activation test accuracy is less than or equal to best text baseline.
- McNemar p vs best text baseline `>= 0.20`.

GREY:

- Anything between PASS_CLEAN and NULL.

## Required Reporting

Commit:

- `build_stage9_elements_fixture.py`
- `capture_stage9_elements_activations.py`
- `evaluate_stage9_elements_pilot.py`
- `STAGE9_40_ELEMENTS_GATES_20260517.md`
- fixture JSONL + manifest
- activation manifest JSON, not the activation `.npz` binary
- probe report JSON + markdown
- README row
- Claude audit handoff

Do not commit:

- Full activation `.npz` binary.

## Claim Boundary

If PASS_CLEAN:

> Pythia-160M hidden states carry a 40-Element TKS/CAS readout above text
> baselines on the frozen role-bound fixture.

If NULL:

> This particular 40-Element fixture does not establish an internal readout
> above text baselines.

Either way, Stage 9.0 does not prove hidden-state steering, raw-symbol
understanding, generated-language control, or cross-model generality.
