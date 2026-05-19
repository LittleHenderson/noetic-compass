# Stage 13 Multi-Layer Trace Audit Gates

Date: 2026-05-18
Branch: `experiment/cas-probe-pythia`

## Purpose

Stage 13 tests whether CAS Harness can audit hidden-state blind spots across depth, not just produce one best-layer classifier.

The input is the already-captured Stage 12 equation/formula activation artifact. No new model forward pass is authorized for this stage. The audit trains the same formula-family readout at every available layer and readout position, then traces each test example through the stack.

Plain English question:

> Does CAS see where the formula-family signal appears, strengthens, weakens, drifts, or becomes internally conflicted?

## Evidence Level

Allowed claim:

> CAS Harness can inspect open-model hidden activations and produce a layer-by-layer trace of a CAS readout, including class-level blind spots and unstable examples.

Not allowed:

- Pythia has a CAS compiler inside its weights.
- Pythia internally validates formulas.
- CAS can see exact neurons that caused a generation.
- Weights "fire." Weights are static parameters; activations are the per-input values that change.
- The Stage 13 audit proves generation steering.

## Inputs

- Fixture: `stage12_equations_formulas_full_20260517.jsonl`
- Activations: `stage12_equations_formulas_full_activations_20260517.npz`
- Prior report: `stage12_equations_formula_probe_report_20260517.json`

## Procedure

For each readout:

- `focus_token`
- `final_token`
- `mean_over_seq_len`

For each layer position:

1. Train a balanced logistic regression readout on the locked Stage 12 train split.
2. Evaluate on locked validation and test splits.
3. Record accuracy, macro-F1, confidence, entropy, per-class accuracy, and per-class lacunarity.
4. Save test predictions per layer.

For each test example:

1. Trace predicted labels across all layer positions.
2. Record the first layer that predicts the gold label.
3. Record the longest stable run of identical predictions.
4. Record switch count across layers.
5. Record majority label and final-layer label.
6. Classify the trace shape:
   - `stable_correct`
   - `stable_wrong`
   - `early_correct_then_drift`
   - `late_emerging_correct`
   - `conflicted`
   - `uncertain`

## Diagnostic Gates

This is a trace audit, so it is not a new product pass/fail gate. It has diagnostic checks:

1. Reproduction check: the Stage 12 headline readout/layer must reproduce the prior test accuracy within `1e-9`.
2. Layer trace check: at least one readout must show a validation-selected layer with test accuracy above the best Stage 12 text baseline by at least `+0.05`.
3. Blind-spot check: the report must name the weakest class per readout using per-class accuracy and confidence/entropy, not just a single overall score.
4. Stability check: the report must quantify how many test examples are stable, drifting, conflicted, or late-emerging.

## Blind Spot Definition

For this audit, a CAS blind spot is not mysticism and not an accusation that the model "cannot think."

It means:

> A CAS label or example has weak, unstable, or missing hidden-state evidence under a trained readout.

A class-level blind spot is flagged when it is among the bottom classes by per-class accuracy, has below-average confidence, or has above-average entropy.

An example-level blind spot is flagged when the layer trace is conflicted, uncertain, or stable-wrong.

## Output Artifacts

- `stage13_multilayer_formula_trace_audit_20260518.json`
- `STAGE13_MULTILAYER_FORMULA_TRACE_AUDIT_20260518.md`
- `STAGE13_CLAIMS_MATRIX_20260518.md`

## Boundary

If Stage 13 works, the correct claim is that CAS Harness can audit open-model hidden activations for CAS-readable structure and blind spots across layers. It still does not prove direct access to exact causal neurons or internal compiler execution.
