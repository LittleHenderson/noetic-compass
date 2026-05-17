# Stage 9.1 Gates: 40 Elements Factorization + Readout Ablation

**Status:** pre-registered before Stage 9.1 factorization or ablation run.

**Branch:** `experiment/cas-probe-pythia`

## Scope

Stage 9.0 showed that the original TKS 40 Elements are recoverable from
Pythia-160M hidden states above text and metadata baselines.

Stage 9.1 asks whether that signal decomposes into:

- **Domain/World:** `A/B/C/D`
- **Noetic:** `1..10`
- **Interaction:** full `A1..D10`

This remains readout-level science. It does **not** test hidden-state
steering or generated-language control.

## Locked Inputs

- Fixture: `stage9_elements_pilot_20260517.jsonl`
- Activation artifact: `stage9_elements_pilot_activations_20260517.npz`
- Stage 9.0 report: `stage9_elements_pilot_probe_report_20260517.json`
- Locked readout: `focus_token`
- Locked layer: `5`

The locked layer comes from Stage 9.0 validation selection. Stage 9.1 must not
rescan or choose a new layer.

## Tasks

For each factor:

1. Train text-only baselines on the frozen split.
2. Train metadata baselines for diagnostics.
3. Train a `StandardScaler` + `LogisticRegression(lbfgs, class_weight=balanced)`
   activation probe on `focus_token` layer 5.
4. Compute activation-vs-text paired McNemar.
5. Remove the trained probe subspace from the locked-test activations.
6. Compare targeted removal against `30` same-rank random complement removals.

## Factor Gates

For a factor to pass cleanly, both must pass:

**Readout gate**

- Activation test accuracy lift over best text baseline `>= +0.05`.
- McNemar p vs best text `< 0.05`.

**Readout-causal ablation gate**

- Targeted subspace removal drops accuracy to at most `chance + 0.05`.
- One-sided empirical p for random-disruption >= targeted-disruption `< 0.05`.

Metadata baselines are diagnostics. Because the fixture is pair/focus
counterfactual by construction, metadata can identify the active factor in
some pair types. Metadata does not override the text/readout/ablation gate,
but any metadata shortcut must be reported.

## Overall Verdict

- `STAGE9_FACTOR_CHECK_FULL_PASS`: Domain, Noetic, and Interaction all pass
  readout + ablation.
- `STAGE9_FACTOR_CHECK_INTERACTION_PLUS_PARTIAL_PASS`: full 40-way
  interaction passes, and at least one of Domain/Noetic passes.
- `STAGE9_FACTOR_CHECK_READOUT_ONLY`: full interaction readout passes but
  ablation does not.
- `STAGE9_FACTOR_CHECK_NULL`: full interaction does not pass the readout gate.

## Claim Boundary

If Stage 9.1 passes:

> The original TKS 40 Elements are not only readable from Pythia hidden states;
> the trained readout subspace is load-bearing for the CAS readout, and the
> signal can be decomposed into Domain/World and/or Noetic factors.

If Stage 9.1 is mixed:

> The 40-way interaction is real, but one factor may be text-explained or
> entangled.

Either way, Stage 9.1 does not prove hidden-state steering, raw-symbol
understanding, visible generation control, or cross-model generality.
