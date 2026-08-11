# CJT_JSPACE_OHM_JOINED_CANARY_V0 — Implementation Blueprint

Created: `2026-07-23T00:18:22.0538305Z`

Status:

`PLANNING_PACKAGE_CREATED / IMPLEMENTATION_SEQUENCED_AFTER_ATTEMPT_4 / NO_JOINED_RUNNER / NO_JOINED_PROTOCOL / NO_JOINED_MODEL_EXECUTION / SHADOW / NONE / NOT_LICENSED`

This blueprint specifies how to build the joined experiment that the project
actually needs. It is not a frozen protocol, runnable code, execution receipt,
scientific result, or product license.

## 1. Purpose and evidence boundary

The joined canary must test whether CJT Bias, corrected v7.4 RPM, J-Space,
CAS-Ohm response curves, signed internal interventions, and ablation add
measurable value to hidden-state probing and generated behavioral outcomes.

It must answer four different questions without collapsing them:

1. Can CAS Harness observe registered internal mediators?
2. Do J-Space/CJT/RPM/CAS-Ohm measurements improve held-out prediction over
   strong surface and ordinary-hidden-state baselines?
3. Does a registered internal intervention cause the intended mediator and
   generated behavior to move together, while controls stay bounded?
4. Does the complete result replicate across untouched prompt families,
   seeds, architecture families, and eventually a genuine 300B-class run?

A positive small-model smoke proves only wiring. A positive Pythia pilot does
not prove cross-architecture universality. A 300B resource plan does not prove
300B execution. Missing or ambiguous evidence fails closed.

## 2. Controlling source bindings

| Source | Role | SHA-256 |
|---|---|---|
| `.../CONTRACTS/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md` | Controlling experimental design | `c39eb46bcc5aa3d482c9a53ec82fbf4362058f56817b0c3e644d3fd9636ba4fe` |
| `.../ONTOLOGY/CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721_at_5d9a9d42.md` | Controlling external-drive/CJT boundary | `0a2962d9acc824bf8959b5f35830875e1728eb2ea33f7ed8ccba039d5594deb7` |
| `.../PROTOCOLS/JSPACE_CORRESPONDENCE_V0_DRAFT.json` | J-Space draft and semantic-source contract | `31dcfda7f85abc02f9692b95c82d0e6c9f89ca2c44ab063acf83a7ac3ce5215d` |
| `.../10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CJT_BIAS_RPM_OHM_STATISTICAL_V1.json` | Synthetic statistical plumbing; not model evidence | `2452a8cb52038f2f6f93fc2217537ba1432622c9eda70e99c5039ad2825f14e7` |
| Attempt 4 corrected `STATUS.md` | Technical dependency and current execution boundary | `4ed1a6d3405e6b3eb8c82cb50ee9269da79ee9a8db3dd46f5f99fad037d6c62b` |

Attempt 4 corrected source identity:

- commit: `be97bc7f76d1e9f5e501702660678d4af3081f5e`
- tree: `4eb382528e8a4cee81a1c043f65bf0dcfa369ccf`

Semantic arms must remain distinct:

- original TKS D3 is primary, raw source SHA-256
  `d3dac0ef5c94ccd768da0f18987846d8d0c0fa0b366e13dccc49c82252d2fc12`;
- A124 is a deployed-rewrite comparator, raw source SHA-256
  `a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0`;
- CAS compact is a generated comparator whose generator is
  `live-trace-worker/scripts/build_foundation28_scenarios.py`, SHA-256
  `07dd7ac7ec5335beb332efeb3071e4058257040a9651c30bd3a392467c10b384`.

The future freeze must bind the full source paths, byte sizes, raw hashes,
canonical hashes where applicable, and source identity records. Changed bytes
require review and a new protocol identity.

## 3. Mandatory gate order

1. Independently verify a corrected Attempt 4 technical pass.
2. Create a separate joined-runner reconciliation worktree.
3. Port historical behavioral code file-by-file while preserving negative and
   withdrawn-license records.
4. Implement schemas, adapter qualification, condition construction,
   directions, interventions, execution, analysis, artifacts, receipts, and an
   independent receiver.
5. Pass CPU toy-model, synthetic recovery, and fail-closed negative tests.
6. Build a genuinely independent prompt bank, outcome rubric, leakage screens,
   and simulation-based power analysis.
7. Freeze exact model revision, adapter, code, dependencies, prompts, seeds,
   thresholds, condition manifest, and analysis plan.
8. Externally timestamp the exact protocol and source/data manifests before
   claim-bearing model access.
9. Run a narrow Pythia-160M wiring smoke as `SHADOW / NONE / NOT_LICENSED`.
10. Run the powered 2,205-base-cell-per-seed pilot plus all registered
    intervention/control expansions.
11. Independently reconstruct all metrics and conclusions from raw evidence.
12. Repeat unchanged gates on at least one non-GPT-NeoX open-weight family.
13. Qualify distributed execution and run a genuine pinned 300B-class model
    with complete recoverable receipts.

No later gate may borrow status from an earlier gate.

## 4. Common condition and identity contract

Every condition/arm must be immutable and content-addressed. The frozen schema
must include at least:

- `protocol_id`, `protocol_version`, `protocol_sha256`;
- `run_id`, `base_cell_id`, `arm_id`, `condition_id`;
- exact model repository, revision, config, tokenizer, chat template,
  generation configuration, and model-file hashes;
- architecture-adapter ID, version, code hash, qualification receipt hash;
- code commit/tree/bundle, dependency lock/root, runtime, OS, driver, CUDA,
  hardware, provider, and worker identities;
- prompt-bank ID, prompt-family/group ID, exact prompt bytes and token IDs;
- calibration/selection/evaluation split and independence role;
- seed-domain identities, public/randomness provenance, and exact seed;
- `V_ext`, `C`, `B`, measured `b`, `S_RPM`, `G_RPM`,
  `I_internal`, `E`, `alpha`, and all normalization/baseline identities;
- semantic direction, sign, layer, hook, token position, tensor shape, dtype,
  device, intended dose, realized mediator displacement, and off-target
  displacement;
- intervention arm, hook-fire count, model-reset proof, and hook-cleanup proof;
- raw logits, likelihoods, generated output, registered output functional,
  behavioral labels, uncertainty inputs, wall time, peak memory, and cost;
- expected and observed artifact/receipt counts, hashes, and failure state.

Recommended deterministic identity:

`condition_id = SHA256(RFC8785_CANONICAL_JSON(condition_identity_payload))`.

Duplicate keys, non-finite values, unknown enum members, implicit defaults,
missing hashes, or reused condition IDs are hard failures.

The observation map must freeze exactly one relationship:

- `C_EQUALS_I_AT_REGISTERED_TEST_POINT`; or
- `EXPLICIT_TRANSDUCTION`, with a frozen `C = T(V_ext, B)`.

Leaving `C` and `I_internal` unrelated is a stop condition.

## 5. Minimum factorial design

### 5.1 External drive — five base levels

The base design uses a mechanically generated, interval-calibrated set:

- `NEGATIVE_HIGH`;
- `NEGATIVE_LOW`;
- `ZERO`;
- `POSITIVE_LOW`;
- `POSITIVE_HIGH`.

Actual dose values are frozen only after calibration. Surface length, token
count, lexical intensity, encoding, and payload family are matched or modeled.
Preregistered overload points expand the design beyond these five levels.

### 5.2 CJT Bias — seven conditions

- `NEUTRAL`;
- `INTENDED_SAFETY`;
- `CONFLICTING_ADVERSARIAL`;
- `LOW_CUTOFF_CANDIDATE`;
- `CENTERED_ACTIVE_CANDIDATE`;
- `HIGH_SATURATION_CANDIDATE`;
- `MATCHED_BIAS_SHAM`.

Each manipulation must move the registered bias coordinate without silently
changing `V_ext` or the cause coordinate.

### 5.3 Corrected RPM — nine conditions

- intact ordered `DESIRE_TO_WISDOM_TO_POWER`;
- `DESIRE_MISSING`;
- `WISDOM_MISSING`;
- `POWER_MISSING`;
- `CONTENT_MATCHED_REORDERED`;
- `IRRELEVANT_RANK_DECODABILITY_MATCHED`;
- `CORRUPTED_INVOLUTION`;
- `RESTORED_AFTER_FAILURE`;
- `SEMANTIC_SHAM`.

Every prerequisite identity, decision, order, and result is retained. RPM
cannot be inferred from the final output alone.

### 5.4 Prompt groups — seven outcome-relevant families

- clean task completion;
- benign instruction conflict;
- prompt injection that the model follows;
- prompt injection that the model safely refuses;
- injected text that the model ignores;
- matched surface/length controls;
- off-target capability and safety controls.

### 5.5 Exact base count

`5 x 7 x 9 x 7 = 2,205` base cells **per seed**.

This is not the total number of forward passes. Seeds, independent prompt
replicates, overload points, layers/tokens, and intervention arms multiply the
base count. Power analysis must use independent prompt families/groups as its
cluster unit; duplicated rows and repeated seeds are not independent samples.

## 6. Keep every physical/Noetic candidate variable separate

- `V_ext`: externally supplied desire/stimulus/trigger/Above-Cause drive.
- `C`: registered cause-terminal coordinate after the drive enters the model.
- `B` and `b`: intended Bias condition and measured Bias coordinate.
- `S_RPM`: ordered prerequisite trace.
- `G_RPM`: conduct, deny, or unresolved RPM result.
- `I_internal`: registered hidden-state response/flow surrogate.
- `E`: registered downstream output effect.
- `alpha`: internal experimental intervention dose.

`alpha` is not `V_ext`. A hidden-state change is not an output change. RPM is
not a fourth CJT terminal and is not resistance.

Candidate quantities:

- `beta_dir = dE/dC` at fixed Bias and RPM;
- `beta_FR = ||dE/dC||_FR`, kept separate because it discards sign;
- `g_B = dE/dB` at fixed cause and RPM;
- `r_pi_CAS_derived = beta_dir/g_B`, only with stable independent
  identification and direct bias-equivalence validation;
- `G_eff = dI_internal/dV_ext`;
- `R_eff = 1/G_eff`, only when the slope is stably nonzero;
- `causal_control_gain = dE/dalpha`;
- `Delta_RPM(E) = E(intact ordered chain) - E(disrupted chain)`.

## 7. One-condition execution topology

Each condition/arm must execute as one instrumented transaction:

1. Validate the frozen protocol, manifest, adapter, dependencies, worker, and
   model identities.
2. Construct the prompt mechanically and bind exact prompt bytes/token IDs.
3. Reset the clean model state and run a baseline forward pass with live graph.
4. Capture `C`, measured `b`, `I_internal`, J-Space projections,
   off-target states, and the full RPM trace.
5. Measure the registered output functional and projected JVP/VJP; run the
   frozen finite-difference consistency check where required.
6. Attach exactly one isolated intervention arm.
7. Prove the hook fired the expected count at the exact tensor/layer/token,
   and record intended versus realized mediator displacement.
8. Generate output under the frozen decoding configuration.
9. Retain raw generation, logits/likelihoods, deterministic outcome fields,
   and blinded/human-review fields.
10. Verify RPM trace/order and off-target budgets.
11. Atomically publish raw artifacts plus a condition receipt.
12. Remove all hooks, reset state, and recheck model parameters/files.

The hidden mediator and generated behavior must come from the same
condition/arm. Post-hoc joining of unrelated runs is forbidden. A condition is
incomplete if either side is missing.

## 8. Intervention and ablation arms

The full protocol must include:

- observational baseline without an intervention hook;
- true no-op;
- hook-attached zero-vector sham;
- intended `+alpha` and `-alpha` signed dose sweeps;
- matched-norm random direction;
- matched-norm orthogonal direction;
- unrelated or shuffled-label semantic direction;
- wrong sign;
- wrong layer;
- wrong token;
- intended mediator/subspace ablation;
- matched-rank random ablation;
- matched-rank orthogonal ablation;
- RPM intact, disrupted, reordered, restored, and sham contrasts where
  registered.

Every hook must fail closed if its coordinate is invalid, it never fires, it
fires too often, the tensor shape/device differs, the realized displacement is
zero or wrong-signed, or cleanup cannot be proven. Historical
`app/runtime/ablation_probe.py` behavior that can silently no-op on invalid
coordinates is not claim-grade until this is corrected and tested.

## 9. Prompt-injection behavioral outcome contract

The bank and receipt must represent separate axes:

- injection presence;
- attack family, payload family, domain, encoding, and template;
- attack success/following;
- safe refusal;
- ignored injection;
- clean/benign task completion;
- safety violation;
- off-target capability degradation;
- label provenance and reviewer agreement.

Proposed outcome enum:

- `ATTACK_FOLLOWED`;
- `SAFE_REFUSAL`;
- `INJECTION_IGNORED`;
- `BENIGN_CONFLICT_RESOLVED`;
- `CLEAN_TASK_COMPLETED`;
- `OFF_TARGET_HARM`;
- `AMBIGUOUS_HUMAN_REVIEW`.

Mechanically verifiable outcomes are preferred. Ambiguous or disagreeing
labels become `AMBIGUOUS_HUMAN_REVIEW`; they are never coerced into a favorable
class. Raw generations are always retained.

Hold out entire attack/template/payload families. Freeze prompt authorship,
label manual, reviewer blinding, group split, duplicate screen, and leakage
screen before model access.

Required baselines include word TF-IDF, character 3–5-grams, length/token
count, encoding/domain/payload metadata, layer 0/embedding, ordinary hidden
activations, and the strongest combined surface model. A useful internal
detector must add held-out value beyond those controls and distinguish
attack-following from safe refusal and ignored injection at a bounded
false-positive rate.

The historical hidden-state result around `0.897` balanced accuracy was beaten
by character controls around `0.925–0.931`. That license remains withdrawn.
The new design must not reuse the old PRESENT/ABSENT or
PRESENT-implies-refusal confound.

## 10. J-Space role and limits

J-Space supplies registered semantic geometry:

- original TKS D3 primary directions;
- A124 and CAS compact comparator directions;
- deterministic nonnegative orthogonal matching pursuit;
- sparsity `k=25`;
- J and non-J components, `R2_J`, and registered direction signs;
- Haar-rotation, activation-PCA, pseudo-definition, random-direction,
  duplicate/leakage, and character-surface controls.

J-Space is a sparse union of nonnegative cones, not an ordinary linear
subspace. Direction/prototype texts, tokens, baselines, layers, hashes, and
signs must be frozen before evaluation.

The detached historical NPZ may support retrospective direction construction
and diagnostics only. It is not live Jacobian/JVP/VJP evidence. J-Space may
nominate or measure a mediator; by itself it proves neither semantics,
causality, steering, prompt-injection detection, universality, nor 300B
execution.

## 11. Eta-to-epsilon bridge role and limits

The eta-to-epsilon lane converts a hidden probe prediction (`eta`) into a
readable CAS prefix (`epsilon`) and measures a second-pass continuation
likelihood. It is a readable mediation/comparator experiment, not an internal
activation intervention.

Required readable-prefix controls:

- no prefix;
- gold readable prefix;
- probe-predicted readable prefix;
- partner/wrong readable prefix;
- raw symbol prefix;
- semantic-matched readable non-CAS prefix;
- irrelevant readable prefix.

Eta-to-epsilon is not `V_ext`, not `alpha`, not J-Space correspondence, and
not prompt-injection prevention. Behavioral output claims require separate
generated-output evidence from the joined transaction.

## 12. CAS-Ohm/CJT curve competition and uncertainty

Fit on calibration groups and predict untouched groups. Competing families:

- null/constant;
- affine, treating delta-linear and affine as one equivalence class;
- reciprocal;
- saturating;
- Hill;
- piecewise-linear;
- monotone non-parametric;
- interactions containing Bias and RPM.

Selection uses grouped held-out error and a frozen complexity penalty. Report:

- held-out RMSE and predictive R-squared;
- calibration error and residual structure;
- prompt-family cluster-bootstrap 95% intervals;
- seed/control variation;
- multiplicity correction;
- parameter/ratio uncertainty;
- the stable operating range.

Use paired/Fieller intervals for `r_pi_CAS_derived`. A denominator interval
approaching or crossing zero yields `UNAVAILABLE`, never infinity or a clipped
number. If a nonlinear model wins, report a local small-signal approximation
or reject the Ohm label.

Predefine and validate `CUTOFF`, `ACTIVE`, `SATURATION`, and
`BREAKDOWN_CANDIDATE`. RPM conclusions must bound Wisdom/Power subspace
containment and unequal probe-strength explanations.

## 13. Component-value ablation ladder

To answer whether each proposed component helps, run paired grouped comparisons
on the same untouched groups:

1. surface/provenance baseline;
2. ordinary hidden activations;
3. CAS readout without J-Space/CJT/RPM/CAS-Ohm;
4. J-Space alone;
5. CAS-Ohm features alone;
6. CJT/Bias/RPM without J-Space;
7. preregistered complete joined system;
8. negative, random, orthogonal, shuffled, and sham systems.

Report incremental held-out lift, uncertainty, multiplicity-adjusted tests,
calibration, safety/utility budgets, and negative-control behavior. A stronger
combined score without paired component attribution is not evidence that every
component helped.

## 14. Evidence, receipts, and independent verification

Before claim-bearing access, externally timestamp the exact protocol, code,
data/prompt manifests, model revision, adapter, thresholds, and analysis plan.

The runner must produce:

- PRE and POST environment/model/runtime evidence;
- create-once run, cell, arm, and artifact identities;
- an expected-versus-observed condition/arm ledger;
- atomic no-overwrite per-condition receipts;
- raw tensor, Jacobian/JVP/VJP, logit, likelihood, generation, label, RPM,
  intervention, and resource artifacts;
- per-file hashes, sizes, aggregate/Merkle roots, and durable off-host copies;
- explicit partial/failure receipts and checkpoint/resume history;
- no hidden suppression of failed or unfavorable results.

The independent receiver must recompute condition completeness, hook evidence,
mediator displacement, behavioral counts, curve selection, uncertainty,
ablation-ladder comparisons, and final status from raw artifacts. It must not
trust summary assertions.

All joined research remains:

`SHADOW / verdict_influence=NONE / claim_status=NOT_LICENSED`.

No joined artifact enters customer Evidence Packets, proof chips, production
verdicts, or customer `ACCEPT` until a separate promotion gate closes.

## 15. Architecture-adapter contract and universality path

Define a stable Probe IR plus exact-revision adapters. Each adapter must:

- fingerprint config, weights, tokenizer, chat template, and remote code;
- enumerate real layers from model metadata, never parameter-scale guesses;
- map residual, attention, MLP, normalization, unembed, and tuple outputs;
- bind exact hook tensor, layer, token position, padding, and generation cache;
- support capture, JVP/VJP, intervention, ablation, and cleanup;
- report tensor shapes, dtypes, devices, sharding, and MoE expert routing.

Qualification requires:

- baseline/no-hook functional equivalence;
- complete capture and exact hook-fire counts;
- intended tensor-change proof;
- finite-difference versus JVP/VJP consistency;
- wrong-coordinate rejection;
- no lingering hooks or parameter mutation;
- adapter-specific independent reconstruction.

An unknown model enters `DISCOVERY_CAPTURE`, adapter selection/generation, and
technical diagnostics. Customer verdicts fail closed while support is
unqualified, but research toward universality continues.

At least one unchanged replication on a non-GPT-NeoX open-weight architecture
is required before any cross-architecture advancement. Additional families
must include dense and MoE designs rather than treating all models as a
sequential dense stack.

## 16. Genuine 300B execution seams

A real 300B lane requires more than `device_map=auto`:

- pinned sharded weight and remote-code manifests;
- tensor, pipeline, and expert parallel loading;
- active-versus-total MoE expert accounting;
- projected JVP/VJP or randomized low-rank sketches;
- approximation and reconstruction-error gates;
- deterministic model/condition/shard partitioning;
- per-shard checkpoints, idempotent resume, and lease fencing;
- authenticated/mTLS workers and signed/hash-bound fragments;
- independent aggregation and redundant spot checks;
- durable fragment transport and recovery reads;
- measured GPU/RAM/disk/network preflight and actual cost/time;
- small-model single-versus-distributed parity;
- worker-loss, host-loss, replay, corruption, and resume fault injection.

Only execution of the exact pinned 300B-class model through the complete frozen
protocol with complete recoverable evidence closes the 300B gate. A planner,
memory estimate, worker count, receipt count, or small-model simulation does
not.

## 17. Candidate narrow smoke scope

The first smoke should use exact
`EleutherAI/pythia-160m@50f5173d932e8e61f858120bcb800b97af589f46`.

It must be deliberately small and non-claim-bearing, but it must exercise:

- every software module and receipt type;
- every factor level at least once;
- every intervention/control class at least once;
- intact, disrupted, reordered, restored, and sham RPM paths;
- attack-following, refusal, ignored, clean, and off-target outcome handling;
- both intended and realized mediator displacement;
- full raw-artifact recovery and independent recomputation;
- fail-closed missing/duplicate/corrupt artifact tests.

The exact smoke cells must later be generated by a deterministic covering
algorithm and frozen in a manifest. This planning document does not choose
their count or bytes. A smoke pass means only that the complete test bench is
wired correctly.

## 18. Powered pilot and analysis freeze

Before the pilot:

- simulate power and precision using prompt-family clusters;
- freeze the minimum detectable effects, safety/utility budgets, FPR, primary
  endpoints, multiplicity families, stopping rules, and seed count;
- freeze calibration, selection, and untouched evaluation partitions;
- freeze all condition cells and required arm expansions;
- externally timestamp the exact package.

The base is 2,205 cells per seed. The final expected count must explicitly
multiply base cells by prompt replicates, seeds, registered arms, overload
points, and any layer/token replication. Completion requires exact count
equality and no duplicate cells.

Positive pilot evidence remains exact-model evidence until unchanged
architecture-diverse replication closes its separate gate.

## 19. Proposed implementation namespace

- `research/joined_canary_contract.py`
- `research/joined_condition_manifest.py`
- `research/joined_model_adapter.py`
- `research/joined_directions.py`
- `research/jspace_correspondence.py`
- `research/joined_interventions.py`
- `research/joined_executor.py`
- `research/joined_analysis.py`
- `research/joined_artifacts.py`
- `research/joined_receipts.py`
- `research/joined_runner.py`
- `scripts/prepare_cjt_jspace_ohm_joined_canary_v0.py`
- `scripts/run_cjt_jspace_ohm_joined_canary_v0.py`
- `scripts/verify_cjt_jspace_ohm_joined_canary_v0_independent.py`

Implementation must not alter the frozen Attempt 4 commit, manifest, PRE,
query, or execution namespace.

## 20. Historical branch reconciliation

Prompt-injection, trajectory-break, behavior-dataset, and signed causal
intervention apparatus exists only on divergent branch
`origin/codex/cas-harness-public-beta-candidate` at
`f8a72008c01f5133224dbea4be02bb1acff614f7`.

Do not merge or cherry-pick the branch wholesale. Port individual files and
their tests into a separate worktree, review against current schemas/security,
and preserve negative records including:

- the withdrawn hidden prompt-injection license;
- the character-baseline loss;
- the non-replicating expanded causal result;
- surface-clean injection-bank construction failure;
- any `FAIL`, `OPEN`, and `NOT_LICENSED` result.

Importing only favorable apparatus would corrupt the evidence history.

## 21. Entry and exit criteria

### Implementation entry

- corrected Attempt 4 has an independent technical pass;
- its frozen evidence is preserved;
- separate worktree/namespace exists;
- source/branch ledger is reviewed;
- no joined claim status has been advanced.

### Narrow-smoke exit

- every software lane and control class executes;
- hidden mediator plus generation are jointly captured;
- hook and reset/cleanup proofs pass;
- complete receipts recover and independently reconstruct;
- all negative tests fail closed as specified;
- status remains `SHADOW / NONE / NOT_LICENSED`.

### Pilot exit

- expected and observed full counts match;
- untouched grouped analyses and uncertainty recompute;
- controls and safety/utility budgets pass;
- unfavorable outcomes remain retained;
- independent receiver agrees;
- result is reported only at its exact-model evidence ceiling.

### Universality and 300B exit

- unchanged gates replicate across qualified architecture families;
- genuine distributed 300B execution completes with fault recovery,
  approximation bounds, authenticated workers, and durable evidence;
- a separate promotion review determines any `LICENSED` scope.

## 22. Exact next construction action after Attempt 4

Create a separate joined-runner reconciliation worktree from the corrected
post-Attempt-4 source. First implement only the condition schema, adapter
interface, toy model, hook-fire assertions, receipt schema, and independent
negative-test verifier. Then reconcile historical behavioral modules
file-by-file. Do not start with a GPU run and do not freeze the joined protocol
until the prompt bank and power analysis are independently reviewed.

