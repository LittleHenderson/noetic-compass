# CAS Harness: J-Space, CAS-Ohm, Architecture-General, and 300B Capability Analysis

Date: 2026-07-20 PDT  
Status: capability blueprint and evidence-bound audit; not a production acceptance artifact  
Protected implementation inspected: 81b5c18bd83e1f01ccd398dcad3865a674335b7f  
Customer-production status: OPEN  
Architecture-general probing: OPEN / NOT LICENSED  
Genuine 300B-class execution: OPEN / NOT LICENSED  
Prompt-injection detection: OPEN / NOT LICENSED  
Causal output steering: OPEN / NOT LICENSED  
CAS-Ohm verdict influence: OPEN / NOT LICENSED  
Jacobian-lens verdict influence: OPEN / NOT LICENSED

## Controlling correction - 2026-07-20

This analysis remains the detailed review of the three supplied J-space and CAS-Ohm artifacts, but its original wording about unknown models is superseded by the TKS-first universality doctrine in `CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md`.

Universality is an explicit CAS Harness engineering objective. An unknown open-weight model enters architecture discovery, adapter selection or generation, and canary activation capture. Missing evidence blocks a customer-grade semantic verdict; it does not block research, adapter development, or the universality program. The honesty boundary records what is claimable now. It is not a ceiling on what CAS Harness is required or permitted to become.

## Implementation checkpoint - 2026-07-21

The first executable research-shadow foundation is complete in isolated branch
codex/jspace-ohm-shadow-20260721 at commit
de1a117d028e655840931e9702911c1967a3d6a4. It is disabled by default,
verdict-excluded, NOT_LICENSED, and claim-ineligible. It safely reads the
recovered signed Pythia-160M hidden-state artifact, binds source and artifact
identity, and emits a canonical metadata-only receipt.

This checkpoint does not revise the open capability judgments below.
JSPACE_CORRESPONDENCE_V0 is BASELINE_ONLY,
JACOBIAN_LENS_V0 is NOT_COMPUTABLE_FROM_ACTIVATION_ONLY, and
CAS_OHM_RESPONSE_PROFILE_V0 is BASELINE_ONLY. Actual correspondence,
gradient/JVP/VJP measurement, intervention-dose experiments,
prompt-injection detection, output control, cross-architecture replication,
and 300B execution remain to be performed.

The final full Git bundle SHA-256 is
13034e27046c689aa1fe8aec12959d2d94c58a601ab9c49014ae4335b70c68cd.
The final receipt file SHA-256 is
308673144c7a373eee3666b3d95dd70559a843d23fe6069741020fb7c29eb99d
and its canonical content SHA-256 is
0f1c18ffc42acb28ea9626529f759faeb36782557a2e2bfaf0894b4ec6a0f886.
Verification passed Python compilation, 13 focused tests, all 248 worker
tests, and independent final review.

## Eta-to-epsilon / RPM integration correction - 2026-07-21

The formal eta/epsilon bridge is RPM's section-retraction pair
`X -> R(X) -> X`, with `epsilon_X composed_with eta_X = identity_X`; it is
not a separate fifth module. It is conceptually composable with CJT
Cause/Bias/Effect factors, a Jacobian-derived J-Space measurement lane, and a
local CAS-Ohm response model. No typed cross-system mathematical composition
or transformer-to-Noetica functor has yet been constructed or proved.

New empirical work must therefore keep these operations distinct:

- `probe_readout(h_l)` for hidden-state decoding;
- `J_l = D_(h_l) H_future` and registered `q_J(h_l, J_l)` for J-Space;
- `rho_readable(z_probe)` for readable-prefix rendering;
- direct activation intervention `alpha` for causal output-control testing;
- `V_ext`, CJT bias `B`, and separately observed RPM state for the crossed
  response design; and
- `Delta i = G_eff * Delta V_ext + error` only inside a frozen bias/RPM/
  operating-region stratum.

The historical worker's eta/epsilon names remain immutable artifact labels,
not proof that its probe and readable prefix instantiate the formal natural
transformations. The saved GPT-NeoX-20B values remain real but scoped:
`0.975` is probe classification and `+1.412050` is readable-English-prefix
conditioning; neither tests section-retraction identity or naturality, and
the matched readable non-CAS prefix control is still missing.

Combined status:
`FORMAL_RPM_IDENTITY_CORRECT / CONCEPTUALLY_COMPOSABLE /
EMPIRICALLY_UNJOINED / SHADOW / NOT_LICENSED`.

The controlling detailed contract is
`docs/working/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md`.

## 1. Direct answer

Yes. A perfectly finished CAS Harness must actually perform every capability it claims, on the exact model, revision, probe, evidence tier, and operating conditions named by the claim.

The supplied documents do not prove that CAS Harness can currently probe any open-weight model or complete a genuine 300B audit. They do establish useful research hypotheses, proposed measurements, and an operationalization protocol. The repository also contains a serious local 300B evaluation plan. A plan is not a completed run.

The corrected long-term product promise is:

> CAS Harness is designed to attempt hidden-state and activation introspection on every legally accessible open-weight model whose runtime exposes internal tensors. For an unknown model, CAS inspects the architecture, selects or generates an adapter, runs a canary capture, and returns an integration diagnostic. CAS fails closed on an unsupported customer verdict or unsafe execution - not on scientific exploration and not on the universality objective.

Universality does not require one brittle hard-coded hook to work unchanged everywhere. It requires a universal Probe IR and capability contract with architecture-specific adapters for transformer, MoE, recurrent/state-space, multimodal, and future runtime families. The shared TKS semantic codomain remains stable while the learned hidden-state map, hook locations, tensor shapes, and execution backend adapt to the model.

The concrete scale target remains a real 300B-class audit. The existing local matrix selects xAI Grok-1, a 314B Mixture-of-Experts model, as a demanding primary engineering target. A successful pinned Grok-1 audit licenses that model-scale result and closes a cornerstone of the 300B program. Universality is licensed by the larger published coverage contract: diverse families, held-out adapters, semantic and causal controls, fault recovery, and reproducible evidence.

## 2. Evidence vocabulary

This analysis uses the following boundaries:

- BUILT: source exists.
- TESTED: a named test exercised a named behavior.
- DEPLOYED: the exact source commit is bound to a live deployment identity.
- EMPIRICALLY VALIDATED: real model measurements passed a preregistered protocol.
- LICENSED: the evidence is sufficient for the exact external claim.
- OPEN: work or evidence is still incomplete.
- NOT LICENSED: the claim must not be made from current evidence.

Structural module discovery is not semantic probe validation. A planning estimate is not execution. A receipt count is not recoverable evidence. A successful small-model run is not a 300B result.

## 3. Executive findings

| Question | Current answer | Evidence boundary |
|---|---|---|
| Do local documents describe a 300B goal? | Yes | A genuine-evaluation matrix names 20B, 100B, and 300B-class targets and pass criteria. |
| Has a genuine 300B audit run? | No evidence found | All execution above 20B remains OPEN or NOT LICENSED in the canonical tracker. |
| Is there genuine 20B research execution? | Yes, with important limits | Local GPT-NeoX-20B records contain real activation capture, readouts, interventions, and a human-review packet; they do not provide a standing ACCEPT or universality proof. |
| Can the current planner make a 300B plan? | Partly | Exactly 300B is labeled ENGINEERED_NOT_VALIDATED, but planning does not provide a matching distributed runtime. |
| Do current workers divide a 300B model across workers? | No | The generic shard worker loads the complete model before selecting assigned layers. |
| Is generic architecture support proven? | No | The adapter recognizes several decoder-stack paths; this proves mechanical discoverability, not semantic equivalence or probe validity. |
| Does CAS presently detect prompt injection? | No licensed evidence | Current keyword/regex checks are surface heuristics; the prior hidden-state result must remain failed against its strongest control. |
| Does CAS presently control output through calibrated neurons? | Not reliably | The inspected live eraser attaches 3,072-space cover coordinates to a 768-wide post-projection tensor. |
| Does the CAS-Ohm guide supply a validated measurement law? | No | It is an experimental analogy and proposed calibration scheme, not an empirically established law of LLM computation. |
| Can Jacobian lens improve CAS? | Potentially | It can add an independent output-relevance measurement lane, initially in shadow mode only. |
| Can CAS-Ohm improve CAS? | Potentially | It can force dose-response, residual, saturation, and off-target testing after its quantities are operationally identified. |

## 4. Supplied artifact ledger

The three supplied files were read completely and rendered for visual inspection.

| Artifact | Role | SHA-256 |
|---|---|---|
| C:\Users\wakil\Downloads\CAS_vs_JSpace_Comparison_Memo_v1.docx | Candidate comparison and integration memo | A6236EEAB5194F875A105E5153E5B47948C147A3EDAFC5241EAFACBA979B1259 |
| C:\Users\wakil\Downloads\CAS_Ohm_Quantification_Guide-2.pdf | Experimental electrical-analogy quantification guide | 89AE13C0A5D6208E328E9EDC55F816609BB172076CC13093DCCCCF418145CE64 |
| C:\Users\wakil\Downloads\CAS_Ohm_Harness_Operationalization_Addendum_v0_1.docx | Proposed instrumentation and falsification protocol | 0B62BBC66828A273E5458CC4D98EEE9B341554A474CCACB6387B209B5F0BE5E5 |

These hashes identify the exact reviewed bytes. They do not validate the documents’ scientific claims.

## 5. What the J-space comparison memo contributes

### 5.1 Useful contribution

The memo identifies a productive triangulation strategy:

1. Black-box behavior asks what the model did.
2. Existing CAS probes ask whether registered CAS concepts are readable at registered internal locations.
3. Jacobian-lens readouts ask which internal directions are output-relevant under a fitted local-linear approximation.
4. Matched controls test whether apparent CAS structure beats simpler lexical, length, domain, refusal, and random-direction explanations.

This could improve CAS because an independently derived coordinate system is a stronger test than repeatedly measuring a taxonomy with tools designed around that same taxonomy.

### 5.2 Required corrections

The memo must not be used as claim authority without the following changes:

- Replace “assumption-free” with “taxonomy-independent discovery under explicit local-linear and architecture assumptions.”
- Replace “output-causal by construction” with “output-relevant under the fitted local-linear approximation.”
- Replace “mapping” between CAS and J-space primitives with “candidate correspondence.”
- Report each model, exact revision, architecture, dataset, probe, control, evidence tier, and result separately. A named model list is not a validated multi-architecture pipeline.
- Preserve the prior failed prompt-injection experiment permanently. A new J-lens method must be registered as W1; it cannot supersede or erase W0.
- Treat the memo’s independent-replication statement as unsupported until a separate primary artifact is produced. The official paper acknowledges Neel Nanda for feedback; that is not an independent replication report.

### 5.3 Appropriate initial role

Create an optional jlens_probe_v0 lane with these restrictions:

- disabled by default;
- shadow mode only;
- excluded from verdict calculation;
- exact upstream commit pinned or vendored;
- model, tokenizer, fitting corpus, layer, seed, dtype, hardware, and artifact hashes retained;
- raw internal readouts kept away from third-party explainers;
- unavailable adapters enter integration diagnostics; unsafe execution and customer verdicts fail closed;
- no claim expansion until preregistered replication and controls pass.

The official Jacobian-lens implementation is a reference repository that says it is not maintained. CAS must assume maintenance and security-review responsibility if it adopts the code.

## 6. What the CAS-Ohm Quantification Guide contributes

### 6.1 Useful contribution

The guide’s most valuable rule is its honesty boundary: its proposed values are design scores, calibration values, or ratings, not literal voltmeter readings from a model. That boundary prevents false present-tense claims; it is not a project boundary and must never be used to remove universality, 300B execution, prompt-injection detection, or causal output control from the engineering program.

It proposes:

- V as drive or motivational pressure;
- I as measured activation or flow;
- R as constraint, policy, capability, context, or friction;
- beta as local gain;
- predicted-versus-observed residuals;
- cutoff, active, saturation, and breakdown regions;
- cascade and parallel-path hypotheses;
- model- or board-specific full-scale calibration.

This is useful as a prompt to perform controlled response experiments. It is not yet a validated measurement system.

### 6.2 Mathematical limits

The equation V = IR is algebraically valid only after V, I, and R have independent operational meanings. The guide has not established that law for LLMs.

Important limitations are:

- If R is defined as V divided by I, the equation is a tautology rather than a predictive discovery.
- Observing I alone cannot identify V and R separately.
- Observing only a downstream effect cannot identify beta and I separately.
- A residual cannot by itself distinguish hidden resistance from unmodelled gain, feedback, nonlinearity, offsets, or measurement error.
- The proposed hidden-resistance formula becomes unstable near zero observed flow.
- Electrical series and parallel identities do not automatically apply to transformer residual paths, nonlinear branches, or MoE routing.
- Multiplying scalar gains is valid only for a locally linear, unbranched approximation; a transformer normally requires Jacobians and additive path terms.
- Board-specific full scale means Q4 values are not inherently comparable across models.
- Clipping the normalized score at 10 destroys overload magnitude.
- Q4 cutoffs, face-card anchors, and example tolerances have no supplied statistical provenance.
- The guide’s 0.1–10 resistance range conflicts with a repository chapter that uses a 0–100 resistance scale and calls the mapping an exact isomorphism.

### 6.3 Defensible reframing

CAS-Ohm should become an experimental Ohm Response Profile:

- V becomes an externally controlled intervention or attack dose d.
- M at layer l becomes a standardized causal mediator.
- E becomes a preregistered output effect such as target-token log odds, attack success, task success, or abstention.
- G at layer l becomes the estimated local slope of M with respect to d.
- Effective resistance, if reported at all, becomes the reciprocal of a stable nonzero fitted slope within a registered local region.
- Beta becomes the estimated change in E per controlled change in M.
- Residuals become cross-fitted, standardized prediction errors with uncertainty.

The reciprocal model must compete on held-out data against null, affine, saturating, Hill-type, and piecewise alternatives. CAS must not assume in advance that the electrical curve wins.

## 7. What the Operationalization Addendum contributes

The addendum is the most directly actionable of the three documents. It proposes:

- at least one instrumented field in every claim-bearing record;
- exclusion of zero-instrument records from Evidence Packets;
- an exact test point containing model/revision, layer, token position, direction provenance, and hook type;
- signed activation projections;
- paired contexts;
- intervention-dose sweeps;
- local Jacobians;
- cutoff and saturation measurements;
- downstream and off-target effects;
- four falsification predictions for local linearity, cascade gain, parallel conductance, and residual validity;
- versioned calibration profiles;
- read-only treatment of safety directions.

This can become a real experimental protocol. It does not supply:

- a generic ModelAdapter implementation;
- model-specific direction calibrations;
- MoE router/expert semantics;
- a distributed 300B runtime;
- a prompt-injection benchmark result;
- an output-steering result;
- durable fleet evidence transport;
- a production license.

## 8. Current implementation audit

### 8.1 Protected and live boundary

The inspected protected source is commit 81b5c18bd83e1f01ccd398dcad3865a674335b7f. The canonical tracker records that the current live customer service remains on that protected pre-remediation commit. Candidate audit-remediation commits exist only in isolated local worktrees and are not protected, pushed, merged, or deployed.

No capability in those candidate commits may be described as live.

Local records do contain genuine EleutherAI GPT-NeoX-20B research execution:
real model loading, activation capture, held-out readouts, intervention/control
work, and a hash-bound Evidence Packet whose honest retained disposition is
human review rather than a standing ACCEPT. Some evidence tiers are strong and
some remain partial, post-hoc, null, or GREY. This is real 20B research evidence;
it is not customer-production acceptance, CAS-specificity, 100B/300B evidence,
or architecture universality.

### 8.2 Planner/runtime mismatch

The protected scale planner:

- estimates weight memory from parameter count and storage bytes;
- adds an 18 percent runtime overhead;
- divides estimated runtime memory by worker count;
- can estimate layer count instead of resolving exact configuration metadata;
- invents tensor-shard assignment names when worker count exceeds layer count;
- labels exactly 300B ENGINEERED_NOT_VALIDATED;
- labels above 300B EXPERIMENTAL_NOT_VALIDATED.

The protected generic probe worker:

- loads AutoModelForCausalLM for the complete model;
- uses device_map auto inside that one worker;
- selects assigned layers only after the complete model is loaded;
- gives every independent worker its own model load.

Therefore, adding probe workers does not divide one 300B model’s resident weights. The current planner describes memory savings that the current execution model does not implement.

The plan must distinguish:

- model-parallel ranks, which jointly hold one model;
- expert-parallel ranks, which distribute MoE experts;
- probe-task workers, which distribute scenarios over an existing model-runtime group;
- data-parallel replicas, which duplicate entire model-runtime groups.

### 8.3 Structural adapter is not semantic support

The architecture adapter recognizes several common decoder layer-stack paths and can label them mechanically hookable. Its own source says this does not certify probe meaning or comparable readout quality.

For every family, CAS still needs:

- semantic hook definitions such as residual_pre, residual_post, attention_out, mlp_intermediate, mlp_out, router_logits, expert_out, and final_logits;
- exact tensor shapes;
- token-position policy;
- direction dimensionality and provenance;
- model-specific calibration;
- MoE routing and expert identity;
- held-out empirical validation.

Unknown hooks, mismatched dimensions, missing layers, or unsupported topology must block customer-audit dispatch, while a bounded discovery canary returns an adapter diagnostic and a concrete integration work order.

### 8.4 Current generic readout is not the addendum’s measurement

The open-weight shard worker captures the last token, converts activations to absolute values, and retains mean absolute value, maximum absolute value, and top absolute coordinates. It then pools top absolute values before applying an optional linear probe.

This loses sign and stable hidden-coordinate identity across the pooled vector. It is not the addendum’s signed projection of h onto a registered direction u at an exact test point.

A full signed-vector capture script exists and is a better foundation, but it still needs model/tokenizer/config hashes, exact revision resolution, semantic hook identity, direction provenance, calibration profile, token-position policy, and evidence binding.

### 8.5 Fleet evidence is local, not recoverably delivered

The fleet worker can write the complete evidence payload to a local fragment file. Its API receipt contains:

- worker and lease identity;
- produced and missing output names;
- completion status;
- a fragment reference.

It does not transmit the evidence payload bytes, immutable object version, content size, or independently reread object hash to the API. A merged packet can therefore count receipts and fragment references without possessing recoverable scientific evidence after worker-local state is lost.

The required sequence is:

1. Worker writes the complete fragment.
2. Worker uploads it to immutable or versioned object storage.
3. Storage returns object identity and version.
4. Worker records byte count and content hash.
5. Receipt binds URI, object version, byte count, hash, lease, model, probe, and execution identity.
6. API and verifier reread the object and independently recompute the hash.
7. Restart rehydration reconstructs the packet from durable bytes, not worker-local metadata.

### 8.6 High-severity live eraser coordinate defect

The live Pythia runner says the model has:

- hidden width 768;
- MLP intermediate width 3,072.

Stage-27F cover labels include coordinates such as L5N2346 and L5N2648, which are valid in the 3,072-wide intermediate space.

The live hook is attached to the full MLP module output after projection back to hidden width 768. The eraser filters requested coordinates against output.shape[-1]:

- coordinates above 767 are silently ignored;
- coordinates below 768 modify post-projection hidden coordinates, not the claimed intermediate neurons.

A direct in-memory diagnostic against the protected code produced:

    hidden_width: 768
    coord_2346_changed: False
    coord_142_changed: True
    coord_142_value_after_gain_0_5: 0.5

The existing live-control test checks only that coordinates 142 and 2346 were resolved into the intervention. It does not prove that the intended intermediate tensor changed or that the output changed.

Required disposition:

- treat drive_local_eraser as NOT LICENSED for output-control claims;
- quarantine or visibly mark the current control experimental;
- move the hook to the exact calibrated intermediate representation or recalibrate covers in the actual post-projection space;
- reject out-of-range coordinates rather than silently ignoring them;
- require hook-fired, tensor-before, tensor-after, coordinate-space, direction, gain, checksum, and output-effect receipts;
- add sham, random-coordinate, wrong-drive, zero-dose, and safety non-regression tests.

### 8.7 Prompt-injection support is not yet a detector

The protected pipeline contains surface patterns such as jailbreak and bypass. These may be useful cheap heuristics, but they are not a validated prompt-injection detector.

A real detector must separate:

1. Injection content is present.
2. The model internally recognizes the injection.
3. The model intends to follow the injection.
4. The model actually violates the instruction boundary.

It must model system, developer, user, tool, retrieval, file, and web-content provenance. It must cover direct, indirect, encoded, multilingual, multi-turn, long-context, sleeper, data-exfiltration, and adaptive attacks, plus benign security discussion as hard negatives.

## 9. Architecture-general universality and customer-support contract

An architecture becomes CUSTOMER-LICENSED only when all six gates pass. It enters discovery and canary capture before that point, and every failed gate produces a versioned integration or validation task rather than a permanent rejection.

### Gate A: subject identity

- exact model ID and resolved immutable revision;
- license and permitted use;
- tokenizer, config, and weight-manifest hashes;
- code revision and required remote-code hash;
- dtype and quantization implementation;
- deterministic or bounded-nondeterministic replay declaration.

### Gate B: semantic adapter

- exact layer enumeration;
- exact hidden, MLP, attention, router, and expert shapes;
- semantic hook map;
- token-position policy;
- shard/rank ownership;
- hook-fired verification;
- fail-closed behavior for every mismatch.

### Gate C: measurement calibration

- direction ID, version, dimension, hook semantic, sign, and normalization;
- training, calibration, control, and untouched holdout hashes;
- matched surface and random-direction controls;
- confidence intervals and seed dispersion;
- model-revision-specific calibration.

### Gate D: causal controls

- zero dose;
- sham intervention;
- same-norm random direction;
- orthogonal direction;
- wrong-drive direction;
- label permutation;
- monotonic or preregistered response;
- intended effect and off-target effect;
- safety and utility non-regression.

### Gate E: execution and evidence

- real runtime topology;
- lease-to-rank ownership;
- authenticated worker identity and replay rejection;
- plan-to-execution binding;
- durable evidence bytes;
- independent hash reread;
- checkpoint/restart recovery;
- OOM and worker-loss fail-closed behavior.

### Gate F: empirical acceptance

- preregistered dataset and thresholds;
- held-out families;
- strong baselines;
- uncertainty and missingness;
- independent repeat;
- complete Evidence Packet;
- accepted verifier result;
- exact claim text limited to the passed evidence.

## 10. Genuine 300B-class gate

### 10.1 Primary engineering target

xAI Grok-1 is an appropriate primary mechanical target because its official release specifies:

- 314B total parameters;
- eight MoE experts;
- two active experts per token;
- 64 layers;
- embedding size 6,144;
- JAX reference implementation.

This intentionally exposes current gaps in JAX support, expert routing, real model parallelism, hook ownership, and evidence collection. It is a base model, so it should not be the sole prompt-injection behavior target.

A dense 300B bf16 model requires approximately 600 GB for weights alone. Grok-1’s total stored weights are approximately 628 GB at two bytes per parameter before runtime overhead. Active parameters per token do not eliminate the need to store the total expert weights.

### 10.2 Required runtime

Use a verified distributed runtime that supports the target architecture:

- tensor parallelism;
- pipeline parallelism where appropriate;
- expert parallelism for MoE;
- activation and probe hooks colocated on the owning rank;
- bounded reductions of registered projections rather than unbounded central activation dumps;
- runtime topology captured in the Evidence Packet.

Do not count hundreds of independent full-model loaders as model sharding.

### 10.3 300B acceptance sequence

1. Pin model source, revision, license, tokenizer, config, and all weight shards.
2. Hash and inventory every artifact.
3. Load the real model across the declared hardware topology.
4. Measure actual resident memory, load time, throughput, and failure margins.
5. Verify every layer, router, expert, and registered test point against configuration metadata.
6. Capture signed evidence from preregistered sentinel layers and token positions.
7. Run CAS probes, matched surface baselines, random ontologies, and random directions.
8. Run CAS-Ohm response experiments only for calibrated directions.
9. Run J-lens only through a validated JAX/MoE adapter; begin with reduced sentinel layers if preregistered.
10. Prove rank ownership, worker authentication, plan binding, and evidence-byte durability.
11. Inject worker death, rank loss, OOM, restart, and stale/replayed receipt faults.
12. Reconstruct and verify the complete Evidence Packet from durable storage.
13. Independently repeat or recompute registered samples.
14. Default to FLAG_FOR_HUMAN_REVIEW until every acceptance gate passes.

### 10.4 What the first pass would license

Acceptable:

> CAS Harness completed an evidence-backed audit on xAI Grok-1 revision X using protocol Y and runtime topology Z. The listed probes and controls passed the listed thresholds.

Not acceptable:

> CAS Harness works on every open-weight model.

## 11. Prompt-injection W1 program

The old failed result remains W0. J-space and CAS-Ohm can define a new W1 only with a frozen protocol.

### 11.1 Dataset

Include:

- clean tasks;
- benign instruction conflicts;
- direct jailbreaks;
- indirect retrieval, tool, file, and web injections;
- encoded and obfuscated attacks;
- multilingual attacks;
- multi-turn and long-context attacks;
- data-exfiltration attempts;
- adaptive white-box attacks;
- quoted security text and security education as hard negatives.

Split by attack family, template, source, and model. Do not randomly split near-duplicate prompt variants across train and test.

### 11.2 Baselines

Compare:

- word features;
- character n-grams;
- semantic embeddings;
- length, domain, payload, and provenance metadata;
- visible output classifiers;
- ordinary hidden activations;
- J-lens alone;
- CAS alone;
- CAS-Ohm response features alone;
- combined registered model.

### 11.3 Metrics

Report:

- precision-recall curve and AUPRC;
- false-positive rate at a preregistered true-positive rate;
- per-attack-family recall;
- worst-group performance;
- calibration;
- clean-task utility;
- refusal inflation and over-refusal;
- confidence intervals clustered by prompt family;
- model-, tokenizer-, seed-, and decoding-specific results.

### 11.4 Licensing gate

No prompt-injection detection claim is licensed unless the internal features add preregistered held-out value beyond the strongest surface/provenance baseline, generalize across specified model families, retain acceptable benign utility, and survive adaptive testing.

Even then, internal detection is a secondary control. Instruction authority separation, content provenance, tool allowlists, sandboxing, output validation, and least privilege remain primary defenses.

## 12. Output influence and control program

CAS should not promise deterministic control over arbitrary text. The defensible target is:

> On licensed model-and-behavior pairs, CAS applies a bounded, measured intervention that shifts a registered output distribution while preserving registered safety and utility constraints.

Required sequence:

1. Fix and regression-test the coordinate-space defect.
2. Register the exact hook, tensor shape, direction, coordinate system, and alpha bounds.
3. Demonstrate that the hook fired and altered the intended tensor.
4. Sweep zero, low, medium, and high doses.
5. Compare sham, random, orthogonal, wrong-drive, and no-intervention controls.
6. Measure target-token log odds, task outcome, attack success, perplexity, calibration, helpfulness, refusal, toxicity, and unrelated capability.
7. Require monotonicity or another preregistered response shape.
8. Enforce safety-direction read-only rules.
9. Roll back or require human review on invariant failure.
10. Independently repeat before any external claim.

Training-time counterfactual reflection and inference-time activation intervention are separate technologies and must not share a claim.

## 13. Hallucination and factuality boundary

CAS-Ohm or J-lens features cannot determine truth by themselves. A strong internal flow can support a false answer.

Hallucination research must use external truth or source grounding:

- answerable and unanswerable question answering;
- citation-supported responses;
- retrieval conflicts;
- adversarial misinformation;
- temporal facts;
- abstention and selective prediction.

The valid question is whether internal features add held-out predictive value beyond output confidence, retrieval entailment, source verification, and factuality baselines.

## 14. Build order

### Phase 0: claim containment and safety repair

- Keep external claim language tied to current evidence while actively executing the 300B, universality, prompt-injection, and causal-control licensing tracks; do not quarantine the objectives themselves.
- Quarantine or visibly label drive_local_eraser experimental.
- Preserve W0 and the withdrawn ACCEPT record.
- Do not allow J-lens or CAS-Ohm fields to influence verdicts.

### Phase 1: measurement correctness

- Build the versioned ModelAdapter contract.
- Fix semantic hook placement and the eraser coordinate space.
- Build the direction and calibration registry.
- Preserve signed vectors and exact test points.
- Add hook-fired and tensor-effect receipts.
- Reject silent no-ops.

### Phase 2: evidence correctness

- Bind model revision, weights, tokenizer, config, adapter, probe, scenarios, dtype, quantization, hardware, code, and container to each lease.
- Upload raw evidence fragments to immutable/versioned storage.
- Reread and independently verify fragment hashes.
- Add restart reconstruction and fault tests.
- Enforce cryptographic worker authentication, revocation, and replay rejection.

### Phase 3: scientific validation

- Run Pythia-160M response and J-lens replications.
- Repeat on Pythia-1B and Pythia-2.8B.
- Add one small OLMo, one Qwen, one Llama/Mistral family model, and one small MoE.
- Use leave-one-family-out testing and matched controls.
- Run the prompt-injection W1 benchmark.
- Run bounded steering experiments only after detector and measurement gates pass.

### Phase 4: scale runtime

- Implement real tensor, pipeline, and expert parallelism.
- Reconcile and repeat the existing genuine GPT-NeoX-20B research packet under the corrected hook, control, evidence, and verdict gates.
- Pass a 100B-class MoE audit.
- Execute the pinned Grok-1 314B gate.
- Repeat and independently verify.

### Phase 5: licensed release

- Publish exact model-by-tier evidence.
- Publish uncertainty, missingness, failures, and controls.
- Limit claim language to passed rows.
- Obtain the separate customer-production, legal, operational, and release authorities.

## 15. Minimum acceptance matrix

| Gate | Present status | Required closure evidence |
|---|---|---|
| Exact subject identity | Partial | Immutable revision plus weight, tokenizer, config, code, and license hashes |
| Semantic adapter | Partial structural support | Exact hook semantics, dimensions, topology, and fail-closed conformance |
| Signed activation capture | Partial | Registered test points and deterministic replay |
| Direction provenance | OPEN | Frozen construction, controls, holdouts, sign, normalization, and compatibility |
| CAS-Ohm measurement validity | OPEN / NOT LICENSED | Parameter recovery, alternative curves, held-out predictions, uncertainty |
| J-lens replication | OPEN / NOT LICENSED | Pinned implementation, model-specific replication, baselines, controls |
| Prompt-injection W1 | OPEN / NOT LICENSED | Held-out attack families, strong baselines, calibrated operating point |
| Output intervention | OPEN / NOT LICENSED | Coordinate fix, hook/effect receipt, controls, safety and utility bounds |
| MoE support | OPEN | Router, expert, active/total parameter, placement, and expert-effect evidence |
| Plan-to-execution binding | OPEN | Cryptographic binding of every declared runtime and probe field |
| Evidence durability | OPEN | Durable bytes, version, size, hash, reread, reconstruction |
| Worker trust | Partial | Mandatory scoped authentication, replay rejection, revocation, duplicate checks |
| Fault recovery | OPEN | OOM, worker loss, rank loss, restart, and no false ACCEPT |
| Genuine 20B research execution | Present with mixed/limited tiers; no standing ACCEPT | Reconcile and repeat under corrected controls, evidence transport, and current verdict policy |
| Genuine 100B | OPEN / NOT LICENSED | Real pinned MoE execution and complete packet |
| Genuine 300B class | OPEN / NOT LICENSED | Real Grok-1 or approved equivalent execution and complete packet |
| Customer-production acceptance | OPEN | All nine canonical gates plus distinct release authority |

## 16. Novice metaphor map

- Model adapter = the correct diagnostic socket for a particular engine.
- Semantic hook = the exact sensor port, not merely any wire nearby.
- CAS direction = a calibrated ruler designed for one measurement space.
- J-lens = a second gauge showing which internal changes are related to future words.
- CAS-Ohm profile = an experimental load test showing response as the control knob changes.
- Alpha or dose = the control-knob setting.
- Model-parallel rank = one work bay holding part of the same giant engine.
- Probe worker = an inspector running assigned tests on that shared engine.
- Calibration profile = the instrument’s calibration certificate.
- Matched control = a comparison repair that reveals whether the special tool added real value.
- Evidence fragment = one signed page of the laboratory notebook.
- Evidence Packet = the complete sealed notebook.
- Acceptance gate = the rule saying exactly what must be true before the shop may put PASS on the report.

## 17. Final disposition

The documents should be adopted as inputs to a controlled research and engineering program, with corrections:

- J-space: optional shadow measurement lane and independent triangulation tool.
- CAS-Ohm guide: experimental response-profile hypothesis, not a physical law or current score.
- Operationalization addendum: foundation for a versioned instrumentation and falsification protocol.
- 300B local matrix: authoritative plan for what must be executed, not evidence that execution occurred.

The immediate new blocker is the live eraser coordinate-space defect. It undermines the current output-control mechanism and its test coverage. Correctness must be demonstrated at the tensor and output level before any output-control claim is restored.

The project’s honest present statement is:

> CAS Harness has substantial real foundations: source-anchored TKS probe results, genuine GPT-NeoX-20B activation/readout/causal work, executable CAS compiler and SDG components, a partially engineered architecture/fleet framework, and a concrete 300B execution ladder. No standing ACCEPT follows from the historical 20B packet. The project objective is universal open-weight hidden-state and activation probing; its remaining claim rows now have explicit closure experiments rather than permanent scope exclusions.

The controlling source, semantic-reconciliation, licensing, and GPU execution program is `docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md`.

## 18. Primary references

- Anthropic, Verbalizable Representations Form a Global Workspace in Language Models: https://transformer-circuits.pub/2026/workspace/index.html
- Anthropic Jacobian-lens reference implementation: https://github.com/anthropics/jacobian-lens
- xAI Grok-1 official open release: https://github.com/xai-org/grok-1
- Local genuine large-model evaluation matrix: C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass\docs\working\cas_harness_large_model_genuine_eval_matrix_20260526.md
- Canonical production tracker: C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md
