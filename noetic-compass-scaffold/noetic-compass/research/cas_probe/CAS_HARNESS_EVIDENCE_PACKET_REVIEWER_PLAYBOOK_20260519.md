# CAS Harness Evidence Packet Reviewer Playbook

Date: 2026-05-19

## Purpose

This is the step-by-step reviewer path for researchers, developers, and skeptical stakeholders. The point is to make a CAS Harness claim inspectable without asking anyone to trust the builder.

## Plain English Answer

Can CAS expose blind spots?

Yes, when the host model is open enough to expose activations. CAS can show where a trained CAS readout is strong, weak, unstable, drifting, or conflicted across layers.

What it cannot honestly say yet:

- "I saw the exact internal neuron that caused the answer."
- "The model has a CAS compiler inside its head."
- "Weights fired."

Correct wording:

> CAS inspected hidden activations and found weak or unstable evidence for this CAS structure under a trained readout.

Weights are static. Activations change per input. Weight geometry tells us whether the learned CAS subspace aligns with model weight matrices; activation traces tell us what happened on a specific input.

## Researcher Review: Step By Step

1. Identify the claim tier.

   Check whether the packet claims readout, ablation, likelihood conditioning, blind-spot tracing, or weight alignment. Each tier has different strength.

2. Verify provenance.

   Confirm:

   - model name and revision
   - code commit
   - fixture SHA-256
   - activation artifact SHA-256
   - report SHA-256
   - pre-registration file committed before the run

3. Verify the data split.

   Confirm that layer/model selection used validation data and that test data was reported after selection.

4. Check leakage controls.

   Confirm the model-facing English did not contain raw CAS labels, formula symbols, or class names unless that was the explicit test.

5. Inspect the probe result.

   Read:

   - selected layer
   - test accuracy
   - macro-F1
   - per-class accuracy
   - lacunarity
   - confidence/entropy

6. Inspect blind spots.

   Look for:

   - stable-wrong traces
   - early-correct-then-drift traces
   - conflicted traces
   - high-lacunarity classes
   - low-confidence classes

   Then check whether those classes were under-represented in the fixture. If the fixture is balanced, the blind-spot claim is stronger.

7. Inspect causal/readout tests.

   If the packet includes ablation, verify:

   - targeted subspace removal drops the readout
   - random same-rank controls do not explain the drop
   - the claim remains readout-causal unless generation was separately tested

8. Inspect eta-to-epsilon conditioning.

   For CPL2, verify:

   - probe-readable prefix beats no-prefix
   - probe-readable prefix beats partner-readable prefix
   - paired Wilcoxon passes
   - positive-share passes
   - raw-symbol controls remain separated from readable-context controls

9. Inspect weight geometry.

   Weight geometry answers:

   > Is this learned CAS subspace unusually aligned with static model token-weight matrices?

   It does not answer:

   > Did this exact weight cause this exact answer?

10. Read the boundary section.

   The boundary section is load-bearing. If the packet says a result is likelihood conditioning, do not upgrade it to generation control.

## Developer Implementation: Step By Step

1. Capture activations from the host model with hook access.

   Store:

   - focus-token hidden state
   - final-token hidden state
   - mean-over-sequence hidden state
   - sample ids
   - layer positions

2. Train CAS probes on a frozen train split.

   Use validation to choose the layer/readout. Do not choose by test.

3. Emit the trace object.

   Include:

   - input text
   - selected readout/layer
   - predicted CAS label
   - confidence
   - entropy
   - layer trace
   - blind-spot flags

4. Attach provenance.

   Include:

   - model name/revision
   - code commit
   - fixture hash
   - activation hash
   - report hash

5. Attach verification controls.

   Include:

   - text baseline
   - metadata baseline
   - random same-rank controls
   - raw-symbol controls when testing prefix conditioning

6. Emit claim-level badges.

   Example:

   - hard trace: copied ids / hashes verified
   - derived trace: trained probe readout
   - neural estimate: activation attribution or weight geometry
   - warning: drift, blind spot, contradiction, unsupported leap

7. Make the packet exportable.

   Reviewers need JSON first. UI is secondary.

## What A Stakeholder Gets

They get a path from claim to artifact:

> "Here is the model, here is the exact data, here is the exact commit, here is the activation file hash, here is the probe result, here are the controls, here are the blind spots, and here is what we are not claiming."

That is the credibility surface.
