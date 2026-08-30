# PREREGISTRATION v0.1 (Phase 0A lock candidate — AWAITING OWNER APPROVAL)

Frozen plan. The eight owner decisions are now closed. Status stays
AWAITING_OWNER_APPROVAL until the owner signs the lock candidate. Once the
protected split is read, no edit is allowed; any change becomes v0.2.

## 1. Research question (immutable)

Can a CAS-aligned local readout, a right-inverse neural intervention, and
a profile-specific CAS-Ohm dose controller reduce the examples, optimizer
steps, or collateral forgetting needed to teach ONE narrow skill to a
small Transformer, compared with matched ordinary LoRA and consolidation
baselines?

## 2. Target task and gold contract

Active/passive semantic-role binding. Output:
`{ "verb": <lemma>, "agent": <entity>, "patient": <entity> }`.
Truth authority: exact match to the frozen gold role record. A CAS
coordinate change is NOT success unless the exact role record improves.
Gold records are generated MECHANICALLY from a template grammar. No
language model labels agent, patient, or verb. Every example is
content-hashed BEFORE any model run.

## 3. Model (Decision 1) — FROZEN

- `Qwen/Qwen2.5-0.5B-Instruct`, revision
  `7ae557604adf67be50417f59c2c2f167def9a775`. Local snapshot confirmed.
- Full SHA-256 of every file: see `MODEL_IDENTITY.json`. Architecture:
  24 layers, hidden 896, 14 heads, 2 KV heads (GQA), qwen2.
- Base model FROZEN.
- Fallback `Qwen/Qwen2.5-1.5B-Instruct` (local snapshot present) ONLY on a
  frozen capacity-floor failure, applied to EVERY arm.

## 4. CAS coordinate and target direction (Decisions 5, 6) — FROZEN

- Readout emits p on the open 40-state simplex (39 independent directions).
- Chart: `FISHER_RAO_LOG_MAP_UNIFORM_HELMERT_V1`. Reference = uniform
  40-state distribution; embedding = square-root probability; tangent
  basis = fixed deterministic 40x39 Helmert basis (orthonormal, orthogonal
  to the all-ones direction); coordinate = Fisher-Rao log map projected
  into that basis. CLR/ILR (Aitchison) are NOT used.
- Target direction (v0.1 controls ONE):
  `EMPIRICAL_ROLE_BINDING_DIRECTION_IN_CAS_COORDINATES`
  = normalize( mean(xi_correct) - mean(xi_reversed) ), derived from
  `readout_fit` ONLY, hashed and frozen before Phase 3. Sign: positive
  movement = toward correct role binding. It is NOT called a canonical CAS
  axis.

## 5. Readout layer (Decision 3) — FROZEN PROCEDURE (not a number)

1. Capture the post-block residual stream from all 24 layers.
2. Fit the identical readout at every layer on `readout_fit`.
3. Evaluate each on `readout_select` by CAS macro-F1.
4. Select the highest; if several are within one standard error, choose
   the earliest layer.
5. Freeze the selected layer and its digest before validation,
   intervention, calibration, or protected evaluation.

## 6. Intervention space (Decision 4) — FROZEN

- Modules: `q_proj` and `v_proj` in the selected layer ONLY.
- CAS realizer space: 32 fixed Frobenius-orthonormal rank-1 directions
  (16 on q_proj, 16 on v_proj); 32 scalar coefficients; basis seed 271828.
- Dose = effective weight-update Frobenius norm `a = ||dW||_F`, or fixed-
  basis coefficient norm. NOT raw LoRA A/B factor norms (rescaling-free).
- Baselines: standard LoRA (rank 4, alpha 8, dropout 0, bias none, same
  layer+modules); matched random-basis learner (same 32-coefficient
  count); ordinary task-gradient update (same fixed basis, same effective
  norm).
- If `reachable_fraction < 0.50`: stop with `INTERVENTION_SPACE_INADEQUATE`.
  Do NOT quietly add layers or rank in v0.1.

## 7. Data splits (Decision 7 partial) — FROZEN

Group-separated, content-hashed:
`capacity_probe`, `readout_fit`, `readout_select`,
`controller_calibration`, `task_train`, `validation`,
`protected_lexical` (unseen nouns/verbs, known construction),
`protected_structural` (known vocab, unseen passive phrasing),
`protected_joint` (unseen vocab AND unseen phrasing).
Split axes: noun, verb, voice, surface construction. No lexical or
structural item leaks across groups where a test claims transfer.
Each protected stratum has >= 200 examples. Protected splits are read
ONCE, only after all thresholds and code are frozen.

## 8. Controls

zero; random same-norm; opposite-sign; orthogonal; wrong layer; wrong
token position; shuffled CAS labels; matched non-CAS taxonomy; ordinary
LoRA; ordinary matched-norm gradient; consolidation baseline (EWC);
no-consolidation ablation.

## 9. Metrics

exact agent/verb/patient accuracy (primary truth); examples-to-threshold
(PRIMARY metric); optimizer-steps-to-threshold; wall-clock incl.
controller overhead; backward compute; old-task retention; held-out
structural transfer; target CAS movement; off-target CAS movement;
bridge_error; dose-response prediction error; reachable_fraction;
false-freeze count; reopened-group count. Report effect sizes +
uncertainty, not p-values alone.

## 10. Claims

- CLAIM 1 READOUT.
- CLAIM 2 REALIZATION.
- CLAIM 3 DOSE (corrected). `y_hat = a / r_eff` is algebraically the
  zero-intercept linear model `y_hat = beta*a` with `beta = 1/r_eff`, so
  it may NOT be tested by "beating zero-intercept linear regression"
  (counterfeit competition). Corrected claim: the profile-specific
  proportional model predicts a DISJOINT held-out split, beats
  zero-response and mean-response baselines, carries calibrated
  uncertainty, and is NOT materially worse than the preregistered affine
  or quadratic alternatives. If affine or quadratic improve held-out MAE
  by more than 5%, the proportional model is rejected (material
  nonlinearity).
- CLAIM 4 split into FOUR separate claims (no "or"):
  - 4A SAMPLE EFFICIENCY: fewer examples-to-threshold.
  - 4B OPTIMIZATION EFFICIENCY: fewer optimizer steps-to-threshold.
  - 4C RETENTION: less loss of previously learned skills.
  - 4D WALL-CLOCK EFFICIENCY: less total elapsed time AFTER controller +
    measurement overhead.
  Each gets its own status and evidence. None substitutes for another.

## 11. Thresholds (Decision 7) — FROZEN

| Gate | Frozen threshold |
|---|---|
| Capacity probe | zero-shot exact accuracy < 0.85 (task not already ceilinged) |
| Plain LoRA capacity | >= 0.85 validation accuracy within 32 examples and 500 steps |
| Final task threshold | >= 0.90 exact triple accuracy |
| Readout | AUROC >= 0.75 AND >= 0.10 above the best matched control |
| Readout uncertainty | 95% bootstrap interval for control difference excludes zero |
| Realization direction | correct sign on >= 80% of held-out interventions |
| Behavioral realization | >= 10 pp improvement over zero/random intervention |
| Collateral damage | <= 2 pp loss on protected active-voice performance |
| Dose model | held-out normalized RMSE <= 0.20 |
| Dose-model adequacy | <= 5% worse MAE than the best preregistered affine/quadratic model |
| Sample efficiency (4A) | >= 25% fewer median examples-to-0.90 than ordinary LoRA |
| Step efficiency (4B) | >= 20% fewer median optimizer steps |
| Wall-clock (4D) | >= 10% lower total time incl. measurement overhead |
| Retention (4C) | >= 5 pp less forgetting at matched new-task accuracy |

Protected sample size: >= 200 per protected stratum.

## 12. Falsifiers (hard)

1. Readout not beating shuffled + matched controls -> CAS-specificity not
   established.
2. CAS coordinate moves but exact role accuracy does not ->
   `READOUT_STEERING_WITHOUT_BEHAVIORAL_GAIN`.
3. eta_hat not beating random + ordinary matched-norm -> withdraw
   realization advantage.
4. Dose model not beating zero/mean and not within 5% of affine/quadratic
   -> withdraw dose claim.
5. Shuffled CAS labels as good as real -> withdraw CAS-semantics claim.
6. Measurement overhead > compute saved -> no wall-clock claim (4D).
7. examples-to-threshold not improved -> withdraw 4A.
8. Consolidation protects old but blocks new more than baseline ->
   selective-plasticity fails.
9. Importance scores not predicting causal ablation damage -> not valid
   tuned-weight indicators.
10. Any result appearing only after inspecting a protected split ->
    belongs to v0.2, no v0.1 credit.

## 13. Seeds (Decision 8) — FROZEN

data_generation 20260830; data_split 161803; intervention_basis 271828;
bootstrap 314159; claim-bearing training seeds [0,1,2,3,4,5,6,7,8,9].
Development-only tests may use other clearly labeled seeds with no
claim-bearing weight.

## 14. Phase gates

P0/P0A plan (this). P1 synthetic right-inverse maths (CPU). P2 readout
validation (no steering). P3 activation-level bridge. P4 LoRA weight
update. P5 CAS-Ohm dose calibration. P6 learning benefit (4A-4D). P7
selective consolidation. P8 replication bundle. One phase at a time; run
tests, save raw outputs, write a receipt, commit once, STOP, report.
