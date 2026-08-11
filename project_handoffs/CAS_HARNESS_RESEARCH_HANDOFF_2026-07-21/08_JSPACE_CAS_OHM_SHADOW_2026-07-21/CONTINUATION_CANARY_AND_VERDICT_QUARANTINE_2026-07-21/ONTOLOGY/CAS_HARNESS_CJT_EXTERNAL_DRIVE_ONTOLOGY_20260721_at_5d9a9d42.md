# CAS Harness CJT External-Drive Ontology Decision

Date: 2026-07-21

Status: controlling design decision for CAS Harness research and implementation.
This is an ontology and measurement contract, not an empirical result and not
a `LICENSED` capability.

## Owner clarification

Outside the Cognitive Junction Transistor (CJT) sits the driving potential:
desire, stimulus, trigger, and the `^8` Above/Cause. The external drive is
applied to the CJT; it is not produced by the CJT and must not be silently
collapsed into an internal hidden-state coordinate.

The project therefore uses this boundary:

1. `V_ext` is the registered external drive presented to the circuit.
   Depending on the experiment, its controlled realization can be a desire
   condition, stimulus, prompt trigger, or `^8` Above/Cause input.
2. The CJT receives that drive at its cause/input boundary and transforms it
   under a separately registered bias and operating condition.
3. `I_internal` is a measured response inside the model or CJT
   representation. It may be an activation projection, flow surrogate, or
   another preregistered quantity, but it is not the external drive.
4. The effect/output is measured downstream from the CJT. A hidden-state change
   is not automatically an output change.
5. An internal intervention dose `alpha` is an experimental clamp or
   injection. It must not be called `V_ext` unless a separate, prospective
   calibration establishes the mapping from external drive to that internal
   intervention.

In plain English: the stimulus is the battery feeding the component; the CJT is
the component; an activation reading is a meter reading inside the circuit.
Those three things cannot share one label.

## Measurement consequences

Any CAS-Ohm or J-Space experiment must keep the following variables distinct:

- external drive: `V_ext`;
- cause-terminal state or activation: `C`;
- CJT bias: `B`;
- RPM prerequisite trace: `S_RPM`;
- RPM conduct/deny result: `G_RPM`;
- internal response surrogate: `I_internal`;
- downstream effect: `E`;
- internal intervention dose, when used: `alpha`.

Bias is the CJT base/control condition that sets its operating point. It must be
held fixed when cause gain is estimated and varied independently when framing
sensitivity is estimated.

RPM is the corrected v7.4 one-directional prerequisite structure. It decides
whether a dependent operation may proceed. In the circuit mapping it is a
diode/sequencer around the CJT, not a fourth CJT terminal and not another name
for resistance. An RPM pass cannot be inferred merely because a downstream
effect appeared; the prerequisite trace and its order must be observed or
independently manipulated.

The following quantities may be estimated only under a fixed, hash-bound test
contract:

- signed directional cause gain: `beta_dir = dE/dC` at fixed bias;
- Fisher-Rao gain magnitude: `beta_FR = norm(dE/dC)_FR`, kept separate
  from `beta_dir` because a norm discards sign;
- framing sensitivity: `g_m = dE/dB` at fixed cause;
- derived CJT ratio: `r_pi_CAS_derived = beta_dir/g_m`, only if both
  derivatives are independently identified in the same local operating region
  and a direct bias-response check agrees;
- external-drive response: `dI_internal/dV_ext`;
- causal output response to an internal intervention: `dE/dalpha`;
- effective resistance-like quantity: `Delta V_ext / Delta I_internal`, only
  after the external drive and internal response have been operationally
  calibrated.

These are model calibration quantities. They are not physical volts, amperes,
ohms, or proof that a neural network obeys a physical electrical law.

## How Ohm's equations translate

The ordinary electrical identities are useful as candidate equations after the
variables above have been operationally defined:

- `V = I * R` becomes `Delta V_ext = R_eff * Delta I_internal`;
- `I = V / R` becomes `Delta I_internal = Delta V_ext / R_eff`; and
- `R = V / I` becomes `R_eff = Delta V_ext / Delta I_internal`.

The delta form is preferred because model responses often have a non-zero
baseline. A local differential form, `r_eff = dV_ext / dI_internal`, may be
more accurate when the response is approximately linear only over a small
stimulus range. `V_ext` and `I_internal` are registered, normalized model
measurements; they are not literal electrical units.

The equations earn practical value only if a preregistered stimulus-dose sweep
shows that they predict untouched responses better than competing null,
constant, affine, saturating, Hill, reciprocal, and piecewise models. The fit
must include uncertainty intervals, seed and prompt-group replication, and
out-of-range checks. If the straight-line relation loses, the Harness records
that result instead of forcing an Ohm label onto the data.

Other electrical formulas do not transfer automatically. For example,
`P = V * I` is not a cognitive-power measurement unless a separate experiment
defines and validates what `P` means. Kirchhoff-style conservation likewise
requires a conserved, measured flow and cannot be inferred from activation
magnitudes alone.

## Cause, current, bias, and RPM identification rule

The contract must state whether `C` and `I_internal` are the same
registered scalar at one exact test point or whether a frozen transduction
`C = T(V_ext, B)` connects them. Leaving both undefined disconnects the CJT
and Ohm equations.

The minimum useful experiment is crossed:

`external-drive dose x bias condition x RPM condition x prompt group x seed`.

The RPM factor must include the corrected Desire to Wisdom to Power chain,
individual missing-prerequisite conditions, content-matched reordered
conditions, irrelevant-chain and sham controls, and a restored-chain condition.
The bias factor must include matched low, centered-active, high, adversarial,
and sham conditions without changing the tested external stimulus.

The detailed prospective design is recorded in
`docs/working/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md`.

## CAS Harness consequences

### Hidden-state probing

Reading hidden states and activations measures the internal response side of the
boundary. It does not by itself identify the external cause, the CJT transfer
function, or a downstream causal effect.

### Prompt-injection detection

A serious CJT prompt-injection experiment must manipulate or classify a
registered external stimulus, probe the internal response before output, beat
surface-text and matched controls, and then replicate on untouched prompt
groups. It must also hold the safety bias constant or manipulate it
independently, and test intact versus missing or reordered RPM safety
prerequisites. A text label alone does not establish an internal CJT mechanism.

### Output control

Output control is a separate causal gate. The experiment must show that a
registered external drive or internal intervention changes the intended
mediator and downstream output in the predicted direction while sham, random,
orthogonal, wrong-direction, and off-target controls remain bounded.

### Evidence and claims

Research receipts remain `SHADOW`, have `verdict_influence=NONE`, and are
`NOT_LICENSED` until their own prospective gates close. This boundary guides
the work; it does not prohibit research or cap the CAS Harness universality
objective.

## Source binding

The owner clarification above is controlling for this project. It is consistent
with the locally supplied PCBA/CJT sources that describe cause entering a CJT
from the circuit and effect leaving it:

- `book/CAS_PCBA_Engineer/Chapter_09_CJT_Deep_Dive.md`
  - local-file SHA-256:
    `e789b2a17a9a4cf497873b46544fdd7b257e74818b54c885181784389740d020`
- `book/CAS_PCBA_Engineer/Chapter_04_Your_First_Cognitive_Circuit.md`
  - local-file SHA-256:
    `16b1a766ed385f8350a50fb45259dc4dee405532630d6b77512ee911bb6f5858`
- `book/manuscript/Chapter_27_RPM_Structure.md`
  - local-file SHA-256:
    `b15f64293d24e6c64c6070554e1cc55570ddbae8cb16f78205d65f72839ab35e`

These hashes bind the local source bytes reviewed on 2026-07-21. If either
source changes, the ontology must be re-reviewed rather than silently carried
forward.
