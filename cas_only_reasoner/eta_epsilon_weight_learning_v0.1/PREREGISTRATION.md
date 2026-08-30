# PREREGISTRATION v0.1 (candidate — NOT yet hash-locked)

This is the frozen plan. It is a CANDIDATE until the owner reviews it and
it is hash-locked. Once the protected split is read, no edit is allowed;
any change becomes v0.2.

## 1. Research question (immutable)

Can a CAS-aligned local readout, a right-inverse neural intervention, and
a profile-specific CAS-Ohm dose controller reduce the examples,
optimizer steps, or collateral forgetting needed to teach ONE narrow
skill to a small Transformer, compared with matched ordinary LoRA and
consolidation baselines?

## 2. Target task and gold contract

Active/passive semantic-role binding. Exact output:

    { "verb": <lemma>, "agent": <entity>, "patient": <entity> }

Example: "the dog was chased by the cat." -> verb=chase, agent=cat,
patient=dog. Truth authority: exact match to the frozen gold role
record. A CAS probe change is NOT success unless the role record improves.

## 3. Model and intervention space

- Model: smallest existing LOCAL open-weight checkpoint. [OPEN — no local
  small open-weight LLM snapshot has been confirmed on disk this session.
  OWNER DECISION REQUIRED: name the checkpoint + record its hash.]
- Base model FROZEN. Intervention = a small fixed LoRA / low-rank space.
- LoRA locations + rank + fixed orthonormal intervention basis: [OPEN —
  propose after the model is fixed.]
- Escalation: a larger model is allowed ONLY if plain LoRA fails a frozen
  capacity-floor test, and then it applies to EVERY condition.

## 4. CAS coordinate

- Readout emits p in the open 40-state simplex (39 independent
  directions).
- Frozen 39-dim tangent chart: [OPEN — proposed default: centered
  log-ratio (CLR) or isometric log-ratio (ILR). OWNER DECISION REQUIRED.]
- v0.1 controls ONE target direction (the axis separating correct vs
  reversed agent/patient role binding). [OPEN — exact direction defined
  once the chart is fixed.]

## 5. Data splits (group-separated, content-hashed)

Splits: `readout_fit`, `controller_calibration`, `task_train`,
`validation`, `protected`. Split by combinations of noun, verb, voice,
surface construction. No lexical or structural item may leak across
groups where a test claims structural transfer. The `protected` split is
read ONCE, only after all thresholds and code are frozen.

## 6. Controls (minimum)

zero intervention; random same-norm direction; opposite-sign direction;
orthogonal direction; wrong layer; wrong token position; shuffled CAS
labels; matched non-CAS taxonomy; ordinary LoRA; ordinary matched-norm
gradient update; standard consolidation baseline (e.g. EWC);
no-consolidation ablation.

## 7. Metrics

exact agent/verb/patient accuracy; examples-to-threshold;
optimizer-steps-to-threshold; wall-clock incl. controller overhead;
backward compute; old-task retention; held-out structural transfer;
target CAS movement; off-target CAS movement; bridge_error;
dose-response prediction error; reachable_fraction; false-freeze count;
reopened-group count. Report effect sizes and uncertainty, not p-values
alone. Primary metric: examples-to-threshold.

## 8. Thresholds (proposed — OWNER SIGN-OFF REQUIRED)

- role-binding accuracy threshold: [OPEN — propose 0.90 exact.]
- dose-response held-out tolerance: [OPEN.]
- capacity-floor test for model escalation: [OPEN.]
- consolidation causal-drop threshold: [OPEN.]
All thresholds must be fixed BEFORE the protected split is read.

## 9. Falsifiers (hard)

1. Readout not beating shuffled + matched controls -> CAS-specificity not
   established.
2. CAS coordinate moves but exact role accuracy does not ->
   `READOUT_STEERING_WITHOUT_BEHAVIORAL_GAIN`.
3. eta_hat not beating random + ordinary matched-norm -> withdraw
   realization advantage.
4. CAS-Ohm not beating ordinary response fits on held-out -> withdraw
   dose claim.
5. Shuffled CAS labels as good as real -> withdraw CAS-semantics claim.
6. Measurement overhead > compute saved -> no wall-clock claim.
7. examples-to-threshold not improved -> withdraw sample-efficiency claim.
8. Consolidation protects old but blocks new more than baseline ->
   selective-plasticity fails.
9. Importance scores not predicting causal ablation damage -> not valid
   tuned-weight indicators.
10. Any result appearing only after inspecting the protected split ->
    belongs to v0.2, no v0.1 credit.

## 10. Phase gates

- P0 plan (this). P1 synthetic right-inverse maths. P2 readout validation
  (no steering). P3 activation-level bridge. P4 LoRA weight update. P5
  CAS-Ohm dose calibration. P6 learning benefit. P7 selective
  consolidation. P8 replication bundle.
- One phase at a time. Run tests, save raw outputs, write a receipt,
  commit once per phase, STOP, report. Do not auto-start the next phase.

## 11. Seeds

[OPEN — propose a fixed seed set, e.g. {0, 1, 2, 3, 4}, fixed before any
run.]

## 12. Unresolved decisions (must close before Phase 1/Phase 2)

1. Exact local model checkpoint + hash.
2. Tokenizer hash (follows the model).
3. Target layer(s) for the readout.
4. LoRA locations + rank + fixed intervention basis.
5. The frozen 39-dim tangent chart (CLR / ILR / orthonormal basis).
6. The one target direction inside the chart.
7. Numeric thresholds (accuracy, tolerance, capacity floor).
8. Seed set.
