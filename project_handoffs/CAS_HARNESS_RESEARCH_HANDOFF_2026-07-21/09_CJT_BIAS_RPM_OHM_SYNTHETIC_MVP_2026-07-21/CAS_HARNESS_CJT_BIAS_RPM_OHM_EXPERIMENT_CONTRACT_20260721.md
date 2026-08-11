# CAS Harness CJT Bias, RPM, and CAS-Ohm Experiment Contract

Date: 2026-07-21

Status: `DRAFT_PROSPECTIVE_DESIGN / SHADOW / VERDICT_INFLUENCE_NONE /
NOT_LICENSED`.

This contract adds CJT bias and the corrected v7.4 RPM structure to the
CAS-Ohm measurement program. It does not change the frozen
`JACOBIAN_LENS_CANARY_V0` bytes or claim ceiling. It is not executable as a
claim-bearing protocol until its datasets, power analysis, runner, model
revisions, code hashes, and external protocol anchor are frozen.

The purpose is to test whether the electrical/Noetic isomorphism yields useful,
predictive LLM measurements. The isomorphism is the theory under test. It is not
discarded in advance, and it is not used as a substitute for measurement.

## 1. Circuit and prerequisite topology

The candidate circuit keeps these quantities distinct:

1. `V_ext`: external desire, stimulus, trigger, or `^8` Above/Cause.
2. `C`: the cause-terminal coordinate after the drive enters the model.
3. `B`: the CJT bias/base control coordinate.
4. `S_RPM`: the ordered Desire-to-Wisdom-to-Power prerequisite trace.
5. `G_RPM`: the RPM conduct, deny, or unresolved result.
6. `I_internal`: a registered hidden-state response or flow surrogate.
7. `E`: a registered downstream effect or output functional.
8. `alpha`: an optional internal activation intervention, never silently
   relabelled as external drive.

The CJT has three terminals: Cause, Bias, and Effect. RPM is not a fourth
terminal. It is the one-way prerequisite gate and power sequencer around or
upstream of the CJT. A downstream result does not prove that RPM ran; the
prerequisite trace and order must be observed or independently manipulated.

In plain English: `V_ext` is the supply, `C` is the input lead, `B` is
the control knob that sets the working position, the CJT is the component,
RPM is the safety interlock, `I_internal` is the meter reading, and `E`
is the output lead.

## 2. Source binding and terminology

The controlling local sources reviewed for this contract are:

- `book/CAS_PCBA_Engineer/Chapter_09_CJT_Deep_Dive.md`
  - SHA-256:
    `e789b2a17a9a4cf497873b46544fdd7b257e74818b54c885181784389740d020`
  - Cause/Bias/Effect terminals, characteristic curves, operating regions,
    gain, transconductance, and input-resistance design quantities;
- `book/manuscript/Chapter_27_RPM_Structure.md`
  - SHA-256:
    `b15f64293d24e6c64c6070554e1cc55570ddbae8cb16f78205d65f72839ab35e`
  - corrected v7.4 Desire-to-Wisdom-to-Power section-retraction structure;
- `book/CAS_PCBA_Engineer/Chapter_08_Diodes.md`
  - SHA-256:
    `63ecb8b79994821455924cbb9239075cae569e7a9c8c2ee229a2903db57ecc3e`
  - one-directional prerequisite-gate circuit mapping;
- `book/CAS_PCBA_Engineer/Chapter_14_Power_Management.md`
  - SHA-256:
    `1a5d35efe40d6920b7e66f8d6aeaec0eb2c6f10be913acbe60beb10e5ffa1374`
  - safe startup/power sequencing versus normal causal flow; and
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
  - SHA-256:
    `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880`
  - RPM and production-recipe distinctions.

The current contract uses `Recursive Prerequisite Model` for RPM. Some
engineering prose uses `Recovery/Prerequisite Mechanism`. The alias is
recorded rather than treated as a different structure.

The corrected v7.4 account is a section-retraction, not the older v6.1 RPM
monad. It requires:

`epsilon_I composed_with eta_I = identity_I`

and does not require the reverse composition to be an identity. The experiment
therefore tests one-way prerequisite dependence and must not assume
reversibility.

## 3. Observation-map contract

Before outcome data are opened, the run must freeze scalar coordinates:

- `c = dot(u_C, h_C - h_C0)`;
- `b = dot(u_B, h_B - h_B0)`;
- `i = dot(u_I, h_I - h_I0)`; and
- `e = F(output) - F0`.

It must freeze the directions, baselines, normalization, hooks, layers, token
positions, model revision, tokenizer bytes, and output functional.

The protocol must choose exactly one of these relationships:

1. `C_EQUALS_I_AT_REGISTERED_TEST_POINT`: `c` and `i` are the same
   scalar observation at one exact location; or
2. `EXPLICIT_TRANSDUCTION`: a frozen function `c = T(V_ext, B)` connects
   the external drive/bias to the cause coordinate, while `i` is a different
   downstream internal response.

Leaving `C` and `I_internal` as unrelated labels disconnects the CJT and
Ohm equations and is a stop condition.

## 4. Candidate measurements

All derivatives are local and conditioned on exact model/revision, layer,
hook, token position, prompt group, seed, bias, RPM state, and operating
region.

### 4.1 Signed directional cause gain

At fixed bias with intact RPM:

`beta_dir = partial e / partial c
           = transpose(u_E) * J_EC * u_C`.

This preserves the registered direction and sign.

### 4.2 Fisher-Rao gain magnitude

The source-defined magnitude is recorded separately:

`beta_FR = norm(partial E / partial C)_FR`.

`beta_FR` and `beta_dir` are not interchangeable. A norm measures
magnitude or maximum local sensitivity and discards sign; the directional
quantity measures one registered pathway.

### 4.3 Bias sensitivity or transconductance

At fixed cause and RPM condition:

`g_B = partial e / partial b
    = transpose(u_E) * J_EB * u_B`.

This is the candidate framing/substrate sensitivity. The bias manipulation
must not rewrite the tested external stimulus, and the run must measure whether
the cause coordinate moved despite the intended hold.

### 4.4 Derived CJT input-resistance quantity

The source supplies a `beta/g_m` relationship. CAS Harness initially names
the model quantity:

`r_pi_CAS_derived = beta_dir / g_B`.

It is not reported as measured resistance unless:

1. `beta_dir` and `g_B` are independently identified in the same local
   operating region;
2. the confidence interval for `g_B` stays away from zero;
3. the sign is stable across seeds and untouched groups; and
4. a direct experiment measures the bias change needed to reproduce the
   effect of a cause change.

Until then, the ratio is a cause-versus-bias effect-equivalence coefficient.
Near-zero or sign-unstable `g_B` makes it `UNAVAILABLE`, not an
arbitrarily large precise number.

### 4.5 CAS-Ohm response

At fixed bias and RPM condition, fit:

`Delta i = G_eff * Delta V_ext + error`

and define `R_eff = 1/G_eff` only when the slope is stably nonzero.
Equivalent candidate forms are:

- `Delta V_ext = R_eff * Delta I_internal`;
- `Delta I_internal = Delta V_ext / R_eff`; and
- `r_eff = dV_ext / dI_internal` within a local small-signal range.

Fit `G_eff` or `R_eff` on calibration groups and use it to predict
untouched groups. Computing `R=V/I` on an observation and then claiming
`V=IR` fits that same observation is circular and proves nothing.

### 4.6 Internal causal response

For output-control experiments:

`causal_control_gain = dE/dalpha`.

It remains separate from `dI_internal/dV_ext` until a prospective
external-to-internal calibration connects them.

### 4.7 RPM gate contrast

RPM is measured as a prerequisite contrast, not resistance:

`Delta_RPM(E) =
  E(intact ordered D-to-W-to-P chain) -
  E(missing, invalid, or reordered chain)`.

Every prerequisite decision and its order must appear in the receipt. A final
output alone is insufficient.

## 5. Crossed prospective design

The experiment crosses:

`external-drive dose x bias condition x RPM condition x prompt group x seed`.

The exact sample size and seed count are set by simulation-based power and
precision analysis before results are opened.

### 5.1 External drive

Use at least five signed interval-scale levels including zero and both
directions, plus preregistered overload points. Natural-language labels such as
weak, medium, and strong are merely ordinal unless a separate calibration makes
their intervals meaningful.

The dose generator must be mechanical and frozen. Surface length, token count,
and lexical intensity are matched or included as controls.

### 5.2 Bias

Use at least:

- neutral bias;
- intended/safety bias;
- conflicting/adversarial bias;
- low/below-cutoff candidate;
- centered-active candidate;
- high/near-saturation candidate; and
- matched bias sham.

The run must verify that each intended bias manipulation actually changes the
registered bias coordinate without simply changing `V_ext` or `C`.

### 5.3 Corrected RPM factor

Use:

- intact `D -> W -> P`;
- Desire missing, represented by `V_ext=0` where appropriate;
- Wisdom missing;
- Power missing;
- all prerequisites present but content-matched and reordered;
- an irrelevant but decodability/rank-matched chain;
- a corrupted/involution prerequisite;
- restored prerequisites after a failed condition; and
- an RPM sham with no semantic change.

The RPM result fails closed if the trace, order, or prerequisite identities are
missing.

Two confounds receive explicit controls:

1. `P` may be contained in the measured `W` subspace; and
2. the `W` probe may simply be stronger than the `P` probe.

An ablation of `W` followed by a `P` collapse is not prerequisite
evidence until subspace containment and unequal-probe-strength alternatives are
bounded.

### 5.4 Prompt groups

Use untouched, group-separated families for:

- clean task completion;
- benign instruction conflict;
- prompt injection the model follows;
- prompt injection the model safely refuses;
- injected text the model ignores;
- matched surface/length controls; and
- off-target capability and safety controls.

Generic behavioral divergence cannot distinguish successful hijacking from safe
refusal.

## 6. Operating-region identification

Estimate an effect-versus-cause/external-drive characteristic family for every
bias condition. Region labels are frozen as hypotheses and become observations
only from held-out results:

- `CUTOFF`: downstream effect remains within a registered baseline/noise
  band and local gain is below threshold;
- `ACTIVE`: a stable local slope predicts untouched groups;
- `SATURATION`: effect plateaus and the incremental derivative approaches a
  registered bound; and
- `BREAKDOWN_CANDIDATE`: an independently measured wrong-axis or involution
  effect appears under overload.

A large residual, random sign flip, or severe output alone does not establish
breakdown or involution.

The observed Q-point is an empirical operating location under a registered
load/constraint. A design-authored Q-point is a prediction, not live evidence.

## 7. Competing models and uncertainty

The Ohm/local-linear candidate competes on untouched groups against:

- null/constant;
- affine with intercept;
- reciprocal;
- saturating;
- Hill-type;
- piecewise-linear;
- monotone non-parametric; and
- interaction models containing bias and RPM terms.

Selection uses grouped held-out prediction error and a frozen complexity
penalty. Report held-out RMSE, predictive R-squared, residual structure,
calibration error, prompt-family cluster-bootstrap 95% intervals, seed/control
variation, multiplicity correction, and the operating range over which the
selected model remains stable.

Ratio intervals fail closed when their denominator approaches or crosses zero.
If a nonlinear model wins, record a local small-signal approximation or reject
the Ohm candidate instead of forcing the label.

## 8. Required controls

The run includes:

- surface-text and length baselines;
- matched-norm random and orthogonal directions;
- sham intervention;
- wrong-sign direction;
- wrong layer and wrong token;
- bias sham and RPM sham;
- missing and reordered RPM prerequisites;
- decodability/rank-matched non-prerequisite chains;
- attack-success versus safe-refusal separation;
- exact rerun and multi-seed repeatability;
- negative-control tasks; and
- a genuinely untouched, independently authored neutral holdout before any
  semantic license candidate.

## 9. Prompt-injection detection gate

A useful result must show:

1. injection dose changes a registered internal mediator;
2. transfer slope, bias sensitivity, region transitions, or held-out residuals
   differ between attack-following, safe-refusal, ignored-injection, and clean
   groups;
3. bias and RPM contributions remain separately identifiable;
4. the internal signal beats surface-text controls on unseen attack families;
5. results replicate on untouched groups and seeds; and
6. a preregistered threshold detects attack success at a bounded false-positive
   rate without labelling safe refusal as hijacking.

Until all six close, this is a response diagnostic, not licensed
prompt-injection detection.

## 10. Causal output-control gate

An internal dose `alpha` is introduced only after the observational map is
frozen. A useful result must show:

1. `alpha` changes the intended mediator in the registered direction;
2. the downstream output changes in the predicted direction;
3. sham, random, orthogonal, wrong-direction, wrong-layer, and wrong-token
   controls remain bounded;
4. RPM safety prerequisites and their trace remain intact;
5. clean-task capability and off-target safety remain inside preregistered
   budgets; and
6. the result replicates across untouched groups and seeds.

A hidden-state shift by itself is not output control.

## 11. Falsification and stop rules

Reject the tested CAS-Ohm/CJT observation map for its registered scope if:

- the linear candidate does not beat competing curves;
- parameters or operating regions are unstable across seeds/groups;
- `C` and `I_internal` lack a frozen relationship;
- `beta_dir` and `g_B` cannot be independently identified;
- `r_pi_CAS_derived` is denominator-dominated or fails direct validation;
- bias cannot be separated from prompt/cause change;
- missing/reordered RPM conditions behave like sham;
- RPM evidence is explained by subspace containment or probe imbalance;
- surface baselines match or beat the internal signal;
- causal controls move as much as the intended mediator;
- safe refusal and successful hijacking remain indistinguishable; or
- the exact result fails same-revision replication.

This falsifies the tested observation map or scope. It does not by itself
disprove the Noetic Topos, the formal isomorphism program, or a future better
measurement map.

## 12. Evidence and verdict boundary

Every receipt includes exact model/revision, source/code hashes, prompt-group
ID, seed, token IDs, layer/hook/position, drive dose, bias identity and measured
coordinate, full RPM trace/result, observation-map choice, mediator, output
functional, operating region, fitted model, uncertainty, controls, hardware,
wall time, peak memory, and cost.

Receipts remain `SHADOW`, `verdict_influence=NONE`, and `NOT_LICENSED`.
They cannot create customer proof chips or an `ACCEPT` verdict. Missing
receipts, unregistered bias, or incomplete RPM traces fail closed.

## 13. Architecture and 300B boundary

Raw activation magnitudes and percentile normalization do not solve
cross-architecture comparability. Each model/revision needs semantic-direction
alignment, hook equivalence, tokenizer controls, and model-specific
calibration.

The scalar projections, projected JVP/VJP measurements, and local derivatives
here can reduce storage and compute compared with full dense Jacobians. They are
therefore plausible instruments for 300B probing.

They do not implement model-parallel loading, tensor/expert sharding,
checkpoint/recompute, restartable shards, authenticated workers, durable
fragment transport, or approximation-error gates. A 300B plan becomes a result
only after the exact large model executes the complete frozen protocol with
recoverable receipts.

## 14. Promotion order

1. Review this contract against the semantic-source registry.
2. Implement a dependency-light synthetic recovery harness proving that
   `beta_dir`, `beta_FR`, `g_B`, `r_pi_CAS_derived`, `G_eff`,
   operating regions, and RPM contrasts can be recovered from known curves.
3. Freeze the runner, scenario manifests, power analysis, and exact protocol.
4. Place the digest in an independent timestamp/anchor.
5. Run the Pythia technical calibration on an isolated research GPU.
6. Run untouched prompt-injection and causal-control experiments.
7. Repeat unchanged gates on independently registered architecture families.
8. Build and execute the sharded 300B lane.

The honesty boundary records which evidence gates are open today. It is not a
ceiling on the project, permission to discard the theory, or a substitute for
doing the work.
