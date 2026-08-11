# CAS Harness combined live-model canary readiness

Date: 2026-07-22  
Status: execution-readiness record; not a model result, capability license, customer verdict, or production acceptance artifact

## Controlling answer

The new CAS Harness design has **not** yet been run as one combined live-model
experiment.

No retained run currently joins all of the following on the same exact model,
revision, prompts, layers, token positions, and interventions:

- controlled external drive `V_ext`;
- CJT Bias as a separately manipulated operating-point condition;
- intact, missing, reordered, corrupt, restored, and sham RPM conditions;
- live hidden-state capture and `probe_readout`;
- a live Jacobian/JVP/VJP-derived J-Space measurement;
- a multi-dose CAS-Ohm response profile;
- `rho_readable` and matched readable-prefix controls;
- direct signed activation intervention; and
- downstream output and safety/utility measurements.

Therefore there is no honest percentage, accuracy lift, attack-detection lift,
or output-control improvement attributable to the combined design.

The controlling combined status is:

`FORMAL_RPM_IDENTITY_CORRECT / CONCEPTUALLY_COMPOSABLE / EMPIRICALLY_UNJOINED / SHADOW / NOT_LICENSED`.

This status is an evidence checkpoint, not a restriction on the project. The
project objective remains universal open-weight hidden-state and activation
probing, including a genuine 300B-class execution. The objective does not
become a present-tense claim until the required experiments pass.

## Repaired source checkpoint

The statistical-evidence and ceremony-preparation source is now committed on
isolated branch `codex/cjt-ohm-stat-evidence-20260721`:

- commit: `50cd375fdc179e6a60fbed785e5b726d1fd34c23`;
- tree: `5072a086dbf6450e681c31f2f02dc581e1c90f4b`;
- parent: `25053461c94de23850da7f9c853c420aab1bae62`; and
- embedded offline drand verifier SHA-256:
  `2840ad448b42a251394812dfc97367d83631954ab51b0c1f2b02d76e4207c829`.

Two independent post-repair audits approved this source checkpoint.
Verification passed `158` focused evidence/trust tests, all `576`
live-trace-worker tests, and all `100` production-ingress quarantine tests.
An unmocked Windows Node 24.11.1 run with pinned drand-client 1.4.2 reached
the real BLS path and rejected a nonzero forged signature.

This is still preparation, not execution evidence. No network
preregistration, public-randomness ceremony, Monte Carlo outcome, model run,
GPU run, production deployment, customer verdict, or capability license
occurred. No genuine valid retained drand beacon fixture exists locally, so
the real BLS acceptance path remains untested until the exact future beacon
arrives. Both the official runner and independent receiver must accept that
beacon before outcomes, or the study must fail closed.

## What has actually run

| Evidence lane | What is real | What it does not prove |
| --- | --- | --- |
| Pythia/GPT-NeoX hidden-state readout | Real open-weight hidden-state and probe work exists. | It does not by itself prove J-Space, RPM, CAS-Ohm, or causal output control. |
| GPT-NeoX-20B readable-prefix bridge | Retained selected-element accuracy is `0.975`; readable-prefix likelihood delta is `+1.412050`; raw-symbol delta is `+0.013817`. | These are fixture-specific probe classification and readable-prefix conditioning. The lane lacks the required semantic-matched readable non-CAS control and does not identify the combined mechanism. |
| GPT-NeoX-20B forward intervention | A genuine balanced 14-row forward intervention ran. Target-minus-random was `-0.0383`; target beat random in `5/14` rows. | This was a negative result for that cover/rubric pair, not a pass and not the combined design. |
| Pythia J-Space shadow reader | A detached, hash-bound activation artifact can be validated. | Detached vectors have no computational graph. No live Jacobian, JVP, VJP, or J-Space result exists. |
| CJT/Bias/RPM/CAS-Ohm synthetic lane | Deterministic synthetic recovery and statistical-evidence plumbing exist in shadow mode. | The observations are planted/simulated and `model_execution` is `NONE_SYNTHETIC_ONLY`. They cannot license model probing, prompt-injection detection, output control, universality, or 300B execution. |

The 20B bridge remains `FLAG_FOR_HUMAN_REVIEW`. Historical positive and
negative results must both remain visible.

## What each new component is supposed to add

These are hypotheses to measure, not results already obtained.

- **CJT Cause/Bias/Effect separation:** distinguish the external stimulus from
  the model's operating point and from the downstream effect. This should help
  prevent an apparent response from being mislabelled as a causal stimulus
  effect when it was actually a Bias or baseline shift.
- **RPM:** verify prerequisite identity, order, corruption, and recovery around
  the CJT gate. The formal section-retraction requirement is
  `epsilon_X composed_with eta_X = identity_X`; it does not prove an LLM
  implements those maps.
- **J-Space:** measure which hidden-state directions are locally connected to a
  registered future-output functional. A live approximation must specify the
  layer, token, functional, JVP/VJP estimator, precision, and reconstruction
  tolerance.
- **CAS-Ohm:** fit a held-out response curve such as
  `Delta i = G_eff(B, G_RPM, region) * Delta V_ext + error`, then test whether
  its slope, nonlinearity, saturation, and operating region predict untouched
  cases better than competing curves.
- **`probe_readout`:** decode a registered hidden-state quantity. It is not the
  formal eta map merely because an older artifact used that name.
- **`rho_readable`:** render decoded content into readable text for a separate
  output-conditioning lane. It is not formal epsilon and must beat matched
  readable non-CAS controls.
- **Direct intervention:** add or remove a registered internal direction at
  signed doses and measure the output effect against zero, sham, random,
  orthogonal, wrong-direction, wrong-layer, and wrong-token controls.

## Reusable implementation already present

The first canary does not start from zero. The repository already contains:

- `live-trace-worker/research/exact_token_lens.py` for exact-token J-Space
  adapter logic and the registered reference reduction;
- `live-trace-worker/research_protocols/JACOBIAN_LENS_CANARY_V0.json` for the
  frozen Pythia-160M technical contract;
- `live-trace-worker/scripts/run_open_weight_probe_shard.py` for open-weight
  loading and transformer-layer discovery;
- `live-trace-worker/scripts/capture_open_weight_probe_dataset.py` for raw
  hidden-vector capture;
- `live-trace-worker/app/runtime/probe_runner.py` for the corrected 3,072-wide
  Pythia MLP-intermediate intervention hook and tensor-effect telemetry;
- `live-trace-worker/scripts/run_open_weight_eta_epsilon_bridge.py` for the
  historical readout, readable-prefix, and continuation-scoring lane;
- `live-trace-worker/scripts/run_open_weight_cover_ablation.py` for a fresh
  forward intervention with random/wrong controls; and
- `live-trace-worker/research/cjt_ohm_synthetic.py` for estimator, competing
  curve, operating-region, and RPM contrast plumbing.

## Missing implementation seams

1. There is no executable live J-Space GPU runner. The adapter, protocol, and
   unit-test oracle exist, but no retained production-independent process calls
   live Jacobian/JVP/VJP machinery on the exact model.
2. The ordinary Pythia streaming path uses `torch.no_grad()` and detaches the
   captured tensor. It cannot be reused unchanged for J-Space.
3. The frozen exact-token corpus source snapshot and 1,000-block manifest must
   be materialized and hash-bound.
4. A real-model condition generator must operationalize `V_ext`, Bias, and RPM
   states without silently substituting synthetic variables.
5. No adapter converts real-model measurements into the observation contract
   consumed by the CJT/CAS-Ohm estimators.
6. Prompt-injection work needs a frozen behavioral output functional that
   distinguishes attack-following, safe refusal, ignored injection, benign
   conflict, task completion, and off-target behavior.
7. The readable-prefix lane still needs semantic-matched readable non-CAS and
   irrelevant-readable controls.
8. The joined intervention runner must support signed additive doses and all
   registered direction/layer/token/sham controls.
9. No combined durable evidence receipt yet binds conditions, activations,
   Jacobian/JVP evidence, RPM traces, response curves, interventions, outputs,
   failures, and exact source/model provenance.

## Exact first-canary sequence

### Gate 1 - evidence-runner hardening

Finish the externally anchorable statistical-evidence path and close every
producer/receiver/failure-path review finding. This validates research plumbing
only. It is not a model experiment.

### Gate 2 - frozen technical J-Space canary

1. Freeze the exact WikiText/model/tokenizer source snapshot and block
   manifest.
2. Implement a dedicated differentiable executor for
   `JACOBIAN_LENS_CANARY_V0`; do not put it in the production streaming path.
3. Bind the executor, dependency lock, container, model files, manifest, and
   protocol to exact hashes and an external pre-execution timestamp.
4. Run all eight registered exact-token Pythia-160M blocks.
5. Require the registered Jacobian/JVP/VJP, finite-difference, determinism,
   tensor-shape, resource, and failure-receipt gates.
6. Retain and independently verify successful, failed, and interrupted
   artifacts.

Maximum result: `TECHNICAL_CANARY_PASS`. This does not license semantic or
behavioral claims.

### Gate 3 - joined shadow canary

Freeze a separate protocol, provisionally named
`CJT_JSPACE_OHM_JOINED_CANARY_V0`, only after its runner and negative tests
exist. It must register:

- exact model ID, immutable revision, tokenizer, config, and weight hashes;
- prompt/dataset source, licenses, labels, grouped splits, and untouched test
  groups;
- `V_ext` doses, Bias conditions, RPM conditions, layers, token positions, and
  random seeds;
- `probe_readout`, J-Space `q_J`, `rho_readable`, intervention direction, and
  output functional;
- calibration, selection, and untouched evaluation boundaries;
- surface, provenance, activation, random ontology/direction, prefix, layer,
  token, sham, sign, dose, safety, and utility controls;
- confidence intervals or equivalent uncertainty, multiplicity control,
  missing-data rules, and fail-closed stop rules; and
- raw artifact, checkpoint, source, hardware, cost, failure, and external
  anchor receipts.

The runner must measure every lane on the same prompt/condition rather than
joining unrelated historical files after the fact.

### Gate 4 - measure actual added value

On untouched grouped test data, compare at minimum:

1. surface/provenance baseline;
2. ordinary hidden activations;
3. CAS readout;
4. J-Space alone;
5. CAS-Ohm response features alone;
6. CJT/RPM conditions without J-Space;
7. the preregistered combined system; and
8. negative/random/sham control systems.

Report point estimates with uncertainty, raw counts, group/seed variation,
calibration, false-positive/false-negative behavior, safety/utility effects,
and every registered null or negative result. Only this comparison can answer
whether the new design improves probing.

## GPU and scale ladder

The first qualified technical run requires one isolated research GPU with at
least `24 GB` VRAM because that is the resource floor frozen in the existing
technical protocol. The current 20 GB production worker is below that floor
and must not be repurposed.

The GPU execution is expected to be an hours-scale small-model job. The current
distance is mainly engineering and evidence work: the differentiable executor,
frozen corpus, joined condition adapter, controls, and durable receipt.

The honest scale ladder is:

1. Pythia-160M technical J-Space canary;
2. Pythia-160M joined shadow canary;
3. unchanged-protocol replication on an architecture-diverse 0.5B-1.5B open
   model;
4. confirmatory 20B work with corrected controls and evidence transport;
5. real model-parallel 100B-class rehearsal; and
6. genuine pinned 300B-class execution with distributed checkpoint/recovery,
   authenticated workers, durable artifacts, and a complete verified Evidence
   Packet.

A small-model pass is not a 300B result. A 300B result on one exact revision is
not universal open-weight support. Universality requires the published
architecture-family and held-out adapter coverage contract.

## Plain-English map

- Model = the engine being inspected.
- `V_ext` = the accelerator or external power input.
- CJT = the component with an input, a Bias knob, and an output.
- Bias = the operating-point knob.
- RPM = the safety interlock and prerequisite checklist.
- Hidden state = an internal meter reading.
- J-Space = the gauge showing which internal movement reaches the output.
- CAS-Ohm = the measured calibration/load curve.
- `probe_readout` = the diagnostic scanner.
- `rho_readable` = a translated instruction card used in a separate test lane.
- Intervention = physically adjusting the component to test cause and effect.
- Evidence Packet = the sealed inspection report with the raw measurements and
  provenance needed to reproduce the conclusion.

## Immediate executable next action

Do not spend 300B-scale compute yet. Close the statistical evidence-runner
review, then implement and externally bind the exact Pythia-160M
`JACOBIAN_LENS_CANARY_V0` executor. Provision the separate 24 GB research GPU
only after local differentiable toy tests, exact-token manifest checks,
failure-receipt tests, and evidence-reopen tests pass.

That is the shortest honest path from the current foundations to a measured
answer about whether J-Space, RPM, CJT Bias, and CAS-Ohm improve CAS Harness.
