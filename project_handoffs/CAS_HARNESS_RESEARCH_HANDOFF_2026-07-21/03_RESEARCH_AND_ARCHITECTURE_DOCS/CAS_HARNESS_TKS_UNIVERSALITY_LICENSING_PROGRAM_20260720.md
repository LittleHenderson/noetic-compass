# CAS Harness TKS-First Universality and Capability-Licensing Program

Date: 2026-07-20 PDT  
Status: controlling capability doctrine, corpus reconciliation, and execution program  
Project objective: universal hidden-state/activation probing and causal testing across open-weight models, including genuine 300B-class execution  
Current customer-production status: `OPEN`  
This document does not issue a new customer verdict or rewrite historical evidence.

## 1. Direct correction

CAS Harness is supposed to read hidden states and activations. That is the center of the product, not an optional extra.

The earlier sentence—“CAS Harness supports an open-weight model only after that exact model and revision satisfy a published architecture-adapter, calibration, causal-control, execution-capacity, evidence-integrity, and acceptance contract. Unknown or unsupported models fail closed”—mixed two different ideas:

1. whether CAS is allowed to attempt to inspect a model; and
2. whether CAS is allowed to issue a customer-grade verdict about that model.

The first should be broad and ambitious. The second should be evidence-controlled. The corrected doctrine is:

> CAS Harness is designed to attempt introspection on every legally accessible open-weight model whose runtime can expose internal tensors. For an unknown model, CAS must inspect the architecture, select or generate an adapter, run a canary capture, and produce an integration diagnostic. It may not silently invent a semantic score or customer-grade verdict before calibration, controls, execution binding, and evidence recovery pass. Failure closes the verdict—not the universality program.

“Unsupported” must mean “not integrated yet,” not “CAS has decided this model is impossible.” An unknown model enters `DISCOVERY_CAPTURE`; it does not disappear into a permanent rejection bucket.

The engineering target is genuine universality:

- common access to internal model states;
- a common TKS semantic target space;
- model-specific learned maps into that target;
- cross-model and cross-family validation;
- causal intervention and output-effect measurement;
- real distributed execution at 300B and beyond;
- recoverable evidence rather than summary receipts.

The customer claim becomes universal only when the published universality coverage contract passes. The project is authorized to build toward that claim now.

## 2. What “supports a model” must mean

The word “supports” is too ambiguous for engineering. CAS Harness needs separate capability states:

| Capability state | Exact meaning |
|---|---|
| `MODEL_DISCOVERED` | CAS can read the configuration and enumerate the relevant architecture graph. |
| `ACTIVATION_CAPTURE_VERIFIED` | CAS can capture real, nonempty, correctly shaped tensors at registered hook points and replay a canary. |
| `TKS_READOUT_VALIDATED` | A source-locked TKS probe beats the required controls on held-out data for the named model/revision. |
| `CAUSAL_EFFECT_VALIDATED` | Registered interventions alter the intended tensor and produce the preregistered downstream effect beyond matched controls. |
| `DISTRIBUTED_EXECUTION_VERIFIED` | The real model weights execute across the declared topology; ranks own real shards rather than each loading a full copy. |
| `EVIDENCE_RECOVERABLE` | Raw evidence bytes survive restart/failure and independently reconstruct the packet with matching hashes. |
| `MODEL_CAPABILITY_LICENSED` | The exact named capability is allowed in external claim text for the exact model/revision/protocol. |
| `UNIVERSALITY_LICENSED` | The published architecture-family coverage, holdout, causal, scale, and evidence criteria all pass. |

A model can pass capture and fail semantic calibration. It can pass semantic readout and fail causal control. It can pass on one GPU and fail distributed recovery. These are separate facts, not contradictions.

In plain English: finding the diagnostic socket, attaching a sensor, understanding the measurement, proving the sensor changes the right component, and completing a fleet-scale inspection are five different accomplishments.

## 3. The honesty boundary is not a project boundary

This rule is controlling for future agents:

> An honesty or scope boundary describes what the current evidence licenses today. It is not a ceiling on CAS Harness, not a prohibition on research, not a reason to remove universality from the roadmap, and not permission to call an unfinished capability impossible.

Required behavior:

- Preserve failures and null results so the project can learn from them.
- Repair an unsatisfiable gate prospectively instead of repeating a broken experiment forever.
- Never change a frozen gate after seeing its result and pretend the old experiment passed.
- Version a corrected gate before collecting new data, preserve the old result, and continue.
- Pair every `OPEN` or `NOT LICENSED` capability with the evidence needed to close it, the next experiment, the compute tier, and a concrete next action.
- Treat `NOT LICENSED` as a time-indexed claim state, not a permanent judgment about CAS.
- Fail closed on a customer verdict when evidence is missing; fail informatively during research by returning adapter diagnostics and a work order.
- Do not use caution language to erase genuine prior achievements.

Honesty is the instrument panel. It shows where the vehicle is now; it does not decide where the vehicle is allowed to go.

## 4. The TKS corpus materially changes the architecture

The user’s correction is right: the semantic lineage is not an arbitrary 40-label CAS list. The project draws from the TKS v7.4 corpus, the TKS Formal Mathematical Manual, the Noetic Topos, the original TKS definitions, CAS operational extensions, the CAS compiler, Programming in CAS, the CAS synthetic-data generator, and the empirical probe line.

The correct description is:

> CAS Harness uses a TKS-derived canonical ontology with versioned CAS operational extensions and learns model-specific maps from internal model states into that shared semantic structure.

J-space/Jacobian-lens methods and CAS-Ohm can improve how CAS measures and falsifies those maps. They do not replace TKS meanings.

### 4.1 Canonical TKS authority

`TKS_v7.4_MASTER.tex` explicitly calls v7.4 canonical and authoritative and lists:

- 40 Elements, `A1-D10`;
- 10 Noetics;
- 7 Foundations and 28 Sub-Foundations;
- 22 Acquisitions.

`TKS_v7_4_FULL_BEAUTIFUL.txt` contains the integrated corrected edition, including ontology, semantics, language/compiler specifications, Noetic Topos material, and the corrected Noetic Manifold construction.

The exact ten current Noetic meanings are also locked by `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` from the Tootra Math Handbook:

- `^0` Idea
- `^1` Mind
- `^2` Positive
- `^3` Negative
- `^4` Vibration
- `^5` Female
- `^6` Male
- `^7` Rhythm
- `^8` Above/Cause
- `^9` Below/Effect

The alternative book vocabulary—Identity, Differentiation, Abstractification, Concretization, Integration, Empathetic Alignment, Critical Evaluation, Directed Focus, Expansion, Contraction—is superseded for claim-bearing semantics. It may be retained only as an explicitly named historical or comparator vocabulary.

An important subtlety: `^0` can be semantically named Idea while also acting as an algebraic identity. Semantic name and algebraic role must be separate fields.

### 4.2 TKS supplies an architecture-independent target space

The corrected Noetic Manifold construction replaces a discrete 40-point differential target with the open probability simplex:

```text
Delta_39_open = { p in R^40 : every p_k > 0 and sum(p_k) = 1 }
```

It defines a smooth state map:

```text
sigma : M -> Delta_39_open
```

and a discrete readout by the largest coordinate:

```text
readout(p) = Idea[argmax_k sigma(p)_k]
```

This is a powerful universality foundation because every model can map into the same 40-state codomain even when its hidden width, layer count, framework, routing scheme, or architecture differs.

For an LLM, CAS should operationalize a family of learned maps:

```text
sigma(model, revision, layer, hook) : R^(hidden_width) -> Delta_39_open
```

The formal manual defines the destination. It does not train this LLM map. Its own constant-state example permits a mathematically valid `sigma` that reads nothing. Therefore formal target-space universality and empirical hidden-state universality are complementary layers, not rivals.

### 4.3 Use the product structure as an internal consistency test

The canonical ontology is not merely a flat 40-way label set. CAS can use its factorization to detect weak or inconsistent probes.

Required multi-head outputs:

- Element head: distribution over 40 Elements;
- World head: distribution over four Worlds;
- Noetic head: distribution over ten Noetics;
- Sub-Foundation head: distribution over 28 Sub-Foundations;
- Foundation head: distribution over seven Foundations;
- Acquisition head: 22-way output after the Acquisition taxonomy is reconciled.

Consistency constraints:

```text
p(Element = World x Noetic) must marginalize to the World and Noetic heads.
p(SubFoundation = Foundation x World) must marginalize to the Foundation and World heads.
The World marginal from both factorizations must agree within a calibrated tolerance.
```

This converts the ontology into a falsifiable measurement system. A probe that reports high 40-way accuracy but inconsistent World/Noetic marginals is not a trustworthy semantic instrument.

### 4.4 Noetic Topos as a new empirical program

The conservative journal source proves a formal site/topos construction under stated axioms and explicitly says predictive cognitive or safety measurement remains future empirical work.

That does not make the Noetic Topos irrelevant. It supplies a measurable hypothesis:

- local token-, span-, layer-, and hook-level TKS distributions are local sections;
- registered compatibility maps define how adjacent local observations should agree;
- a gluing residual measures local-to-global inconsistency;
- prompt injection, contradiction, or unstable generation may raise that residual before visible failure.

This becomes a new preregistered feature lane, not a pre-proved detector. It should compete against ordinary uncertainty, entropy, logit margin, text, provenance, and random-graph controls.

## 5. Source conflicts that must become experiments, not confusion

The depth of the corpus is a strength, but several translations currently collide.

### 5.1 `A1-D10` versus `A0-D9`

TKS v7.4 and the owner-locked original fixtures use `A1-D10`. The normalized element JSON uses `A0-D9`, moving the Idea mode from position 10 to index 0.

The intended mapping is approximately:

```text
TKS W10 <-> normalized W0 <-> CAS ^0
TKS W1..W9 <-> normalized W1..W9 <-> CAS ^1..^9
```

This is a cyclic renumbering. It is not safe to join datasets by the raw symbol alone. Every record must carry:

- native source symbol;
- normalized index;
- semantic definition ID;
- crosswalk version and hash.

### 5.2 The two owner definition payloads are different semantic versions

Workspace raw payload:

```text
docs/working/tks_owner_locked_definitions_20260603.json
SHA-256 D3DAC0EF5C94CCD768DA0F18987846D8D0C0FA0B366E13DCCC49C82252D2FC12
```

Protected deployed payload:

```text
C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass\api\resources\tks_owner_locked_definitions_20260603.json
SHA-256 A124302ED93C7B8571B24A5CDF14433ADF904EB94FD65895C6FD25FAE58E28A0
```

They have the same 40 and 28 codes, but 20 of 40 Element definition strings and 8 of 28 Foundation definition strings differ. Several changes are more than punctuation.

They must be named separately, for example:

- `TKS_OWNER_RAW_40_28_D3DA_V1`
- `TKS_DEPLOYED_NORMALIZED_40_28_A124_V1`

The raw original-TKS arm should be primary in the next comparison. The deployed form remains an operational variant until an owner-approved transformation record selects or reconciles the wording. Probe weights trained on one hash are not automatically compatible with the other.

### 5.3 TKS Worlds are being mapped to two CAS axes

One implementation maps:

```text
TKS A/B/C/D Worlds -> CAS P/C/E/O Domains
```

The CAS Foundational Clarifications also use:

```text
TKS A/B/C/D Worlds -> CAS T/A/f/E Registers
```

CAS Domains and Registers are explicitly orthogonal, so both mappings cannot silently be treated as the same identity mapping.

Until resolved:

- preserve native `tks.world`;
- preserve native `tks.element40` and `tks.subfoundation28`;
- store CAS Domain and Register translations as separate, named crosswalk outputs;
- train separate heads;
- never overwrite the native TKS label.

### 5.4 TKS Foundations and CAS Drives are position-related, not definition-identical

TKS includes Unity, Wisdom, Life, Companionship/Love, Power, Material/Wealth, and Lust/Continuation/Creation. CAS uses Unity, Wisdom, Vitality, Connection, Agency, Structure, and Purpose.

Reports must distinguish:

- native TKS-F28 (`1a-7d`);
- CAS Drive-by-Register (`F1-F7` by `T/A/f/E`);
- the translation profile relating them.

Calling both “CAS-F28” hides which meanings were actually tested.

### 5.5 The 22 Acquisition vocabularies conflict

TKS v7.4 defines 22 Acquisitions as a root acquisition plus seven Desire, seven Wisdom, and seven Power families. The normalized JSON contains a different named list including Recall, Recognition, Retention, Reception, Attraction, Repulsion, and others.

Do not train an Acquisition probe until the project declares whether these are:

- two layers of one system;
- aliases under a formal crosswalk;
- or different versions.

### 5.6 Algebra profiles differ

The checked-in Rust engine uses selected involution pairs and mod-10 composition. The broader TKS corpus describes additional pairings and a complete composition table.

Use explicit profile names:

- `tks_v7_4_algebra_profile`
- `cas_engine_mod10_profile`

Then test claimed equivalence instead of assuming it.

### 5.7 `main.md` inventory result

No exact `main.md` was located in the TKS corpus or workspace. The likely relevant local sources are:

- `peer_review/journal_submission/main.tex`—the conservative Noetic Topos paper;
- `noetic-compass-scaffold/noetic-compass/dashboard/public/noetic-topos.md`—the dashboard/book-style chapter;
- byte-identical `main.pdf` / `noetic-topos.pdf` copies located under Downloads and the dashboard.

If a separate `main.md` exists elsewhere, its exact path and hash should be added. This analysis does not pretend to have reviewed an unlocated file.

The candidate byte-bound registry is:

```text
docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json
```

## 6. What is genuinely built and useful now

### 6.1 The Python compiler is real

The checked-in Python compiler implements:

- lexing;
- parsing to an AST;
- static type and admissibility checks;
- lowering to bytecode;
- VM execution;
- diagram generation;
- register extraction;
- recipes, sets, tuples, relations, functions, modules, and other extended constructs.

A dependency-isolated smoke test compiled a real relation successfully. The full notation pytest entrypoint was blocked in this workspace by an unrelated missing `google.generativeai` dependency imported by the global API test fixture; that is an environment dependency failure, not evidence of compiler failure.

The compiler source itself correctly says it does not implement every broader manuscript law. That is an integration backlog, not absence of a compiler.

### 6.2 The Rust engine is real

The Rust tree contains `casc-syntax`, `casc-ir`, `casc-types`, `casc-cli`, and `caspm`, plus ontology, RPM, recipe, yield, and Python-binding machinery. Focused `casc-syntax` and `casc-ir` tests completed successfully in this review.

The remaining integration question is whether every documented high-level language construct routes through the richest Rust semantics. Some Python VM fallbacks are simpler than the available Rust engine.

### 6.3 The CAS synthetic-data generator is substantial

The `cas-synthetic` tree contains versioned v7.4-v7.7 generators, validators, template systems, conversational and free-form generators, recovery tools, mixture controllers, evaluation packs, and large data/manifests.

Focused tests run during this review:

```text
42 passed in 3.16s
```

The passing suite covered v7.4, v7.5, v7.6 production, v7.7 Rule 4, and composite validation.

The SDG can materially improve CAS Harness by producing:

- balanced semantic axes;
- hard negatives;
- matched surface controls;
- multi-turn prompt-injection trajectories;
- causal dose-sweep scenarios;
- architecture-family holdouts;
- compiler-valid structural fixtures;
- reproducible seeds and manifests.

Its present weakness is provenance: generated records and templates are not uniformly bound to an exact definition hash and crosswalk. Structural validation does not prove that an English paraphrase preserves original TKS meaning.

Required SDG upgrade:

```text
definition_authority_id
definition_sha256
native_axis_id
native_label_id
crosswalk_id
crosswalk_sha256
paraphrase_method/model/revision/seed
surface_leakage_result
meaning_preservation_result
```

The SDG should become the controlled data factory for universality, not a hidden replacement source for TKS meaning.

### 6.4 Programming in CAS contains valuable architecture and stale semantics

The book correctly documents major product ideas: compiler-backed cognitive states, an IR, runtime traces, simplex encoders, Fisher-Rao geometry, typed fibers, SSM directions, compiler-mediated generation, and future safety/governance designs.

However, current chapter sources use the superseded Noetic vocabulary and sometimes describe proposed guarantees as if already enforced. The book’s own audit header marks it as a draft containing implemented, future, and speculative material.

Required treatment:

- preserve the architectural ideas;
- reconcile every Noetic name against the normative definitions;
- generate language examples from the actual parser grammar;
- tag every feature `implemented`, `prototype`, `planned`, or `hypothesis`;
- do not use stale book labels to generate claim-bearing probes.

This is repair and consolidation, not deletion of the work.

## 7. Existing hidden-state achievements, accurately preserved

The evidence is stronger than “only two tiny Pythia models,” but it is not one uniform evidence tier.

| Result | Definitions | Model / location | Surface control | Internal result | Correct interpretation |
|---|---|---|---|---|---|
| Historical 40E readout | Original TKS `A1-D10` role-bound meanings | Pythia-160M | about 50.1% | 89.8%, about +39.7pp | Strong historical source-anchored readout; not a universal result. |
| Historical F28 readout | Short/working F28 summaries | Pythia-160M | about 49.7% | 78.6%, +28.9pp; targeted ablation to 1/28 chance | Strong historical F28 result, but not original-TKS-vs-short controlled comparison. |
| Original TKS40 readout | Exact original Stage-9 role-bound fixture | GPT-NeoX-20B, layer 2 | CountVectorizer 49.2411%; hash 50%; majority 2.5% | 95.625%, macro-F1 95.617%; +46.384pp | Genuine 20B hidden-state evidence. Final packet remains `FLAG_FOR_HUMAN_REVIEW`; no standing `ACCEPT`. |
| Original TKS40 causal subspace | Same original TKS40 fixture | GPT-NeoX-20B, layer 2 | Same-rank random disruption mean 0.0681pp, max 0.2679pp | 95.625% to 66.8973%; 28.7277pp disruption | Real diagnostic causal evidence. It narrowly missed a stricter preregistered chance-level closure criterion and is not complete output control. |
| Original TKS40 eta-to-epsilon bridge | Same original TKS40 fixture | GPT-NeoX-20B | raw symbol effect about +0.0138 | readable-prefix delta +1.4121; partner margin +2.8812; selected element 97.5% | `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS` at the likelihood level; not customer `ACCEPT`. |
| F28 versus GoEmotion pilot | Short/working F28 definitions | Pythia-2.8B, layer 24 | F28 36.0%; GoEmotion 57.143% | F28 49.857%, +13.857pp; rival lift +0.429pp; scrambled F28 3.857% | Meaningful deep-layer signal and +13.429pp lift advantage, but preregistered +20pp recoverability floor missed: `BLOCKED_CAS_NOT_RECOVERABLE`. |
| Qwen typed readout | Typed fixture, not the clean original-vs-short A/B | Qwen2.5-1.5B-Instruct, layer 14 | strongest TF-IDF 86.747% | 91.566%, +4.819pp | Typed coverage `PASS`; not text-separable universality or prompt-injection proof. |
| Prompt-injection W0 re-audit | Encoded attack bank | Qwen-1.5B, layer 18 | later char n-gram 92.5-93.1% | hidden BA 89.6875% | Initial PASS was withdrawn; strongest surface control won. Internal prompt-injection claim remains `OPEN` / `NOT LICENSED`. |

Two different facts about the definitions must both be preserved:

1. The strongest source-anchored hidden-state line uses original TKS40 meanings and produced serious results, including the 20B 95.625% readout.
2. There is not yet a same-model, same-neutral-evaluation, same-split, same-hook, same-seed GPU ablation where only original-TKS versus short-CAS definitions changes.

The cleanest direct original-versus-short evidence so far is a fixture/semantic-recovery comparison, not a hidden-state A/B: shortened F28 fixtures recovered only about 15.71-18.57% in the cited blind checks, while original-TKS iterations reached about 60.71-63.57%. That supports the user’s memory that original meanings preserved semantic signal better, while telling us exactly which GPU experiment is still required.

## 8. The decisive original-TKS versus compact-CAS GPU experiment

This should be the first new model experiment because it is inexpensive, resolves a major source question, and improves every later probe.

### 8.1 Arms

- Arm A: `TKS_OWNER_RAW_40_28_D3DA_V1`—full original owner wording.
- Arm B: `TKS_DEPLOYED_NORMALIZED_40_28_A124_V1`—current protected operational wording.
- Arm C: normalized rich Sub-Foundation definitions, hash `5507BF...`, if admitted by the authority manifest.
- Arm D: shortened CAS translation summaries, explicitly comparator-only.
- Arm E: coherent matched non-TKS ontology.
- Arm F: shuffled-label/random-direction nulls.

### 8.2 Fair design

Hold constant:

- exact model and immutable revision;
- tokenizer and config;
- neutral evaluation scenarios;
- train/calibration/holdout groups;
- prompt style and length distribution;
- layers and hook semantics;
- token-position policy;
- classifier family and hyperparameter search budget;
- seeds;
- surface, embedding, layer-0, random-direction, and permutation controls.

Definitions should influence only the registered concept-construction or training arm. All arms must be evaluated on the same independently labeled, neutral holdout bank.

### 8.3 Required metrics

- 40-way and factorized World/Noetic macro-F1;
- 28-way and factorized Foundation/World macro-F1;
- hidden-minus-strongest-text lift;
- canonical-minus-compact difference with clustered bootstrap confidence interval;
- calibration error;
- seed dispersion;
- layer stability;
- cross-family transfer;
- ontology-factorization residual;
- targeted ablation versus same-rank random and orthogonal controls.

### 8.4 Decision rule

Do not use a single arbitrary threshold for every axis. Freeze axis-specific minimum effect sizes after a power analysis and before activation capture. At minimum, the canonical arm must:

- beat its strongest surface/embedding control by a preregistered practical margin;
- beat the compact arm with a positive lower confidence bound;
- beat coherent random and shuffled controls;
- preserve ontology-factorization consistency;
- repeat across seeds;
- retain value on a held-out architecture family before a cross-family claim.

This experiment can turn the user’s observed advantage into a clean, licensed definition-selection result.

## 9. Universal model-adapter architecture

Universality does not require one hard-coded hook path. It requires one invariant measurement contract plus automatically selected physical adapters.

### 9.1 Universal Probe IR

Every architecture adapter should map native tensors into a shared Probe IR:

```text
residual_pre
attention_input
attention_q / attention_k / attention_v
attention_output
mlp_input
mlp_intermediate
mlp_output
router_logits
expert_input
expert_output
residual_post
final_norm
final_logits
state_space_state
recurrent_state
vision/audio tower states
cross_attention states
```

Every observation carries:

```text
model_revision, architecture_family, native_module_path,
semantic_hook, pre_or_post_module, layer/block, token/position,
batch, head/expert, rank/shard owner, tensor shape, dtype,
quantization, capture transform, adapter version
```

### 9.2 Discovery pipeline

For an unknown model:

1. Resolve immutable model/config/tokenizer/code revisions.
2. Inspect config without loading all weights.
3. Build a module graph and identify repeated blocks.
4. Match known adapter signatures.
5. If unmatched, run shape/graph inference and propose candidate semantic hooks.
6. Load a bounded canary configuration or the smallest safe real execution.
7. Fire hooks on sentinel tokens and verify nonempty tensors and expected shape transitions.
8. Run zero/sham perturbations and a bounded tensor-effect canary.
9. Emit an adapter manifest plus ambiguities.
10. Continue to semantic calibration when the canary is sound; otherwise return a precise integration work order.

### 9.3 Required adapter families

- Hugging Face PyTorch dense decoder;
- GPT-NeoX/Pythia;
- Llama/Mistral/Qwen/OLMo-style variants;
- encoder-decoder;
- JAX/Flax;
- Mixture-of-Experts with router, shared expert, and selected-expert semantics;
- state-space/recurrent models;
- multimodal towers and cross-attention;
- custom remote-code sandbox adapter;
- distributed Megatron/DeepSpeed/vLLM-style runtimes where hooks live on owning ranks.

The current four-path stack discovery is the seed of this system, not the end.

## 10. Making the four disputed capability statements licensed

### 10.1 Structural discovery -> semantic probe validation

License target: `UNIVERSAL_TKS_SEMANTIC_READOUT`.

Required closure:

- owner-approved source registry and exact definition hashes;
- native TKS labels preserved;
- versioned architecture adapters and Probe IR;
- hook-fired and shape receipts;
- original-TKS-vs-compact controlled GPU A/B;
- strong text/embedding/random/coherent-ontology controls;
- factorization consistency;
- confidence intervals and multiple seeds;
- leave-one-architecture-family-out evaluation;
- independent repeat.

### 10.2 Planning estimate -> real execution

License target: `DISTRIBUTED_EXECUTION_300B`.

Required closure:

- real model weights and immutable manifest;
- measured memory, throughput, load time, and headroom;
- tensor/pipeline/expert parallel topology;
- per-rank shard ownership proof;
- real hooks on owning ranks;
- no full-model-per-worker shortcut;
- plan values compared to measurements and planner recalibrated;
- injected OOM/rank/worker failure;
- restart/resume from checkpoint;
- full audit completion.

### 10.3 Receipt count -> recoverable evidence

License target: `FLEET_EVIDENCE_RECOVERABLE`.

Required closure:

- raw evidence fragment bytes uploaded, not just metadata receipts;
- content hash, byte length, media/schema version, job/lease/rank binding;
- independent readback and hash verification;
- idempotent fragment registry;
- checkpointed merge state;
- process restart and host/rank loss test;
- reconstruction on an independent verifier process;
- packet hash and every fragment hash match;
- incomplete or conflicting evidence can never produce `ACCEPT`.

### 10.4 Small-model success -> genuine 300B result

License target: `UNIVERSAL_SCALE_300B`.

Required closure:

- pass the adapter/capture/semantic/causal/evidence gates on smaller dense and MoE models;
- pass a 20B corrected repeat;
- pass a 100B-class distributed model;
- execute the pinned 300B/314B target with real weights;
- complete the same probe/control packet schema;
- survive fault injection and reconstruction;
- repeat registered samples;
- publish the exact model/revision/topology/protocol claim.

Passing the 300B target is a cornerstone of universality and licenses the scale capability. It is not used as a substitute for architecture-family diversity.

## 11. Prompt-injection detection program

Prompt injection is not one binary phenomenon. CAS should measure four stages:

1. `INJECTION_PRESENT`: attack content exists in the input or retrieved/tool content.
2. `INJECTION_RECOGNIZED`: the model internally represents the content as an instruction/conflict.
3. `INJECTION_FOLLOWING_INTENT`: internal trajectory moves toward obeying the attacker.
4. `AUTHORITY_VIOLATION`: the output or tool action actually crosses the instruction boundary.

Surface/provenance systems are expected to be strongest for Stage 1. Hidden-state CAS earns value by improving Stages 2-3 and predicting Stage 4 beyond visible text and provenance.

### 11.1 TKS-derived hypotheses

Candidate registered mechanisms include:

- `^2 Positive`: attraction/affinity toward the injected instruction;
- `^3 Negative`: repulsion/refusal;
- `^5 Female`: model/context composition and receptivity;
- `^7 Rhythm`: repeated exposure and entrainment across turns/tokens;
- `^8 Above/Cause`: injected trigger;
- `^9 Below/Effect`: internally or visibly caused action;
- RPM admissibility/prerequisite failures;
- Noetic Topos gluing residuals across system/developer/user/tool/retrieval authority layers.

These are preregistered hypotheses. The corpus does not itself prove an LLM detector.

### 11.2 Benchmark design

Include:

- clean tasks and benign conflicts;
- direct jailbreaks;
- indirect web, file, retrieval, email, and tool injections;
- encoded, obfuscated, multilingual, visual, and multimodal attacks;
- multi-turn, long-context, sleeper, and adaptive attacks;
- data-exfiltration and tool-abuse attempts;
- quoted security discussion and negated instructions as hard negatives;
- matched prompts where attack presence is held constant but model intent/outcome differs;
- authority/provenance labels for every span.

Split by attack family, source, template, payload, and model. Near-duplicates may not cross folds.

### 11.3 Required comparisons

- word and character n-grams;
- semantic embeddings;
- provenance and instruction hierarchy;
- token identity and generated prefix;
- ordinary hidden states;
- source-locked TKS probes;
- J-space/Jacobian-lens features;
- CAS-Ohm intervention-response features;
- Noetic Topos compatibility residuals;
- combined model;
- random directions and coherent matched ontologies.

The previous Qwen W0 PASS was correctly withdrawn because a char n-gram baseline beat it. That result should design W1, not prohibit W1.

### 11.4 Licensing conditions

The hidden-state prompt-injection capability becomes licensed only when it adds held-out value beyond the strongest surface/provenance system, generalizes across named architecture families, survives adaptive attacks, maintains benign utility, is calibrated at a registered operating point, and repeats independently.

## 12. Controlling output and causal intervention

CAS must distinguish three levels:

- readout: predict a TKS state from activations;
- causal influence: intervention changes a registered internal or output measure;
- safe control: a bounded policy reliably shifts behavior while preserving safety and unrelated capability.

The current live eraser coordinate defect remains a real engineering blocker: a direction calibrated in a 3,072-wide MLP-intermediate space was applied to a 768-wide post-projection tensor. That can create silent no-ops or manipulate the wrong coordinate system.

Required control sequence:

1. register the exact native hook and tensor space;
2. reject out-of-range or dimension-mismatched directions;
3. prove the hook fired;
4. prove the intended tensor changed;
5. dose sweep zero, low, medium, and high interventions;
6. compare sham, same-norm random, orthogonal, wrong-TKS-axis, and label-permuted controls;
7. measure target log odds, task outcome, attack success, perplexity, calibration, refusal, toxicity, and unrelated capability;
8. use J-space to measure output relevance independently;
9. use CAS-Ohm only as a fitted response-profile family competing with affine, saturating, Hill, and piecewise alternatives;
10. add rollback and human-review rules;
11. repeat across model families and scale tiers.

The defensible mature claim is not “CAS can force arbitrary text.” It is:

> On licensed model-and-behavior pairs, CAS applies a bounded, measured intervention that changes a registered output distribution while remaining within registered safety and utility limits.

## 13. How J-space and CAS-Ohm improve CAS without replacing TKS

### J-space/Jacobian lens

Use it as an independent output-relevance coordinate system:

- test whether TKS-readable directions are also related to future token distributions;
- find output-relevant directions CAS did not preselect;
- measure alignment between TKS directions and J-space directions;
- detect when a highly readable TKS feature is epiphenomenal rather than output-relevant;
- prioritize causal interventions.

It begins in shadow mode and cannot alter verdicts until replicated on pinned model adapters with controls.

### CAS-Ohm

Use it as an experimental dose-response discipline:

- intervention dose is controlled input;
- mediator activation is measured at a registered hook;
- output effect is preregistered;
- local gain, saturation, cutoff, residual, and off-target effects are estimated with uncertainty;
- competing curve families are evaluated on held-out data.

“Voltage,” “current,” and “resistance” are operational variable names, not literal electrical measurements. The guide’s honesty boundary prevents category mistakes; it does not prevent developing a successful response model.

## 14. GPU and RunPod requirements

Yes—GPUs are required to finish the hidden-state, causal, cross-architecture, and 300B work. They are not required for source reconciliation, fixture generation, surface controls, schema work, compiler tests, or evidence-recovery unit tests.

### 14.1 Immediate low-cost lane

Known persistent worker:

```text
hilj2rzs54gi06
1 x RTX 4000 Ada, 20 GB
```

Use it for:

- Pythia-160M/1B;
- Qwen around 0.5B-1.5B;
- original-TKS-versus-compact GPU A/B;
- adapter canaries;
- prompt-injection W1 pilot;
- evidence byte upload/readback/restart tests.

Do not use it for 20B or 300B.

### 14.2 20B and architecture-diverse lane

Use one H100 80GB or H200 141GB for:

- corrected GPT-NeoX-20B repeat;
- Pythia-2.8B;
- small/medium Qwen, OLMo, Llama, and Mistral models;
- full-layer capture, causal ablation/patching, and bridges.

GPT-NeoX-20B bf16 weights are about 40GB before runtime and activation overhead. A 48GB card may be possible for constrained inference but leaves little claim-grade margin.

### 14.3 MoE lane

Use two to four H100/H200 GPUs for a smaller MoE to validate:

- router hooks;
- selected and shared experts;
- expert ownership;
- tensor/pipeline/expert parallelism;
- distributed reductions;
- rank-failure recovery.

### 14.4 Genuine 300B/314B lane

A 300B dense-equivalent bf16 weight set is about 600GB. Grok-1’s 314B stored weights are about 628GB before runtime overhead. Active experts per token do not remove the need to store all expert weights.

Practical starting topologies:

- 8 x H200 141GB = 1.128TB aggregate VRAM;
- 16 x H100 80GB = 1.28TB aggregate VRAM.

Eight H100s provide only 640GB total, which is effectively no safe runtime headroom.

RunPod’s official pricing page, updated 2026-07-17, listed H200 Pods at $4.39/GPU-hour and H100 SXM Pods at $2.99/GPU-hour; its cluster listing showed H200 SXM at $4.31/GPU-hour. At those posted rates:

- 8 x H200 cluster is about $34.48/hour;
- 16 x H100 SXM is about $47.84/hour.

These are planning figures, not a provider quote or a total job estimate. Storage, idle time, retries, data transfer, availability, and debugging add cost.

Use a persistent network volume large enough for weights, fixtures, checkpoints, and evidence staging. RunPod documents that network volumes persist independently of compute and can attach to Instant Clusters, but simultaneous multi-worker writes need application-level coordination. Copy claim-bearing artifacts to independent evidence storage before cluster teardown.

### 14.5 Spend order

Do not pay for 300B debugging that can be caught on 1B:

1. source registry and fixtures locally;
2. original-TKS A/B on the existing 20GB worker;
3. adapter/capture/evidence canaries;
4. 20B corrected repeat on one H100/H200;
5. smaller MoE on 2-4 GPUs;
6. 100B-class rehearsal;
7. 300B/314B cluster run.

## 15. Closure matrix

| Capability license | Current evidence | Next closure action | GPU tier |
|---|---|---|---|
| TKS semantic source authority | Strong corpus; unresolved payload/crosswalk conflicts | Approve field-level authority manifest and version the D3DA/A124 variants | None |
| Source-bound SDG | Real/tested SDG; definitions not uniformly hash-bound | Add registry/hash fields and semantic-conformance gates | None |
| Universal activation capture | Several dense stacks; no complete adapter SDK | Build Probe IR, discovery workflow, and family adapters | Existing GPU then 1x H100/H200 |
| Original-TKS superiority result | Strong semantic-recovery history; no controlled GPU A/B | Run Section 8 experiment | Existing 20GB worker |
| Cross-family TKS readout | Pythia/GPT-NeoX plus partial Qwen evidence at unequal tiers | Same protocol on Pythia, Qwen, OLMo, Llama/Mistral, small MoE; hold out a family | 20GB then 1-4x H100/H200 |
| Prompt-injection hidden-state detector | W0 initial PASS withdrawn after char baseline | Run four-stage W1 with provenance/text/adaptive controls | 20GB pilot; 1x H100/H200 confirmatory |
| Causal output influence | Genuine 20B subspace/bridge evidence; live eraser dimension defect | Fix hook space; tensor/output receipts; dose and safety controls | 1x H100/H200 |
| Recoverable fleet evidence | Summary/receipt plumbing exists; raw-byte recovery incomplete | Upload/readback/restart/reconstruct real fragments | Local + existing GPU |
| Real MoE execution | Planner/spec work; no claim-grade router/expert lane | Small MoE distributed gate | 2-4x H100/H200 |
| Genuine 100B | `OPEN` | Rehearsal with full packet and faults | 4-8 GPUs, model-dependent |
| Genuine 300B/314B | `OPEN` | Pinned Grok-1 or approved equivalent on real model-parallel cluster | 8x H200 or 16x H100 starting target |
| Universality | Explicit project objective; not one uniform completed tier | Pass capture, semantics, causal, family-holdout, scale, and evidence contracts | All tiers |

## 16. Build order

### P0: semantic identity and doctrine

- Adopt this fail-closed-on-verdict doctrine.
- Preserve universality as the explicit target.
- Reconcile D3DA versus A124 definitions.
- Lock native TKS labels and field-level source authority.
- Resolve TKS World to CAS Domain/Register mappings.
- Reconcile Foundation/Drive and Acquisition mappings.
- Mark stale book Noetic labels superseded/comparator-only.

### P1: source-bound measurement

- Add definition and crosswalk hashes to SDG rows, probe datasets, captures, directions, and packets.
- Build the invariant Probe IR and adapter manifest.
- Fix the live eraser hook-space mismatch.
- Carry raw evidence bytes and independent readback.

### P2: inexpensive decisive experiments

- Run original-TKS versus compact/deployed/comparator arms on the existing GPU.
- Run prompt-injection W1 pilot.
- Add factorization and Noetic Topos gluing residuals in shadow mode.

### P3: 20B closure

- Repeat GPT-NeoX-20B with exact definition hash, corrected hook semantics, uncertainty, matched controls, evidence transport, and current verdict policy.
- Add J-space and CAS-Ohm response profiles in shadow mode.

### P4: architecture universality

- Run the same source-locked suite on Qwen, OLMo, Llama/Mistral, and a small MoE.
- Use leave-one-family-out transfer.
- Promote automatic adapter discovery.

### P5: distributed scale

- Prove small MoE topology and failure recovery.
- Complete a 100B-class rehearsal.
- Execute and reconstruct a genuine 300B/314B audit.

### P6: capability publication

- Publish model-by-capability evidence rows, not an undifferentiated model list.
- Publish confidence intervals, controls, failures, missingness, definition hashes, and topology.
- License each capability when its row passes.
- License universality when the full coverage contract passes.

## 17. Permanent future-agent rules

1. Universality is a project objective. Do not remove it because the current evidence is incomplete.
2. Fail closed on customer verdict promotion, not on research, adapter discovery, or model integration.
3. An unknown open-weight model enters `DISCOVERY_CAPTURE` and produces diagnostics.
4. Never say `NOT LICENSED` means impossible, permanently unsupported, or outside the project.
5. Every open capability must have a closure experiment, evidence list, compute tier, and next action.
6. Read the canonical production tracker and this document before redefining scope.
7. TKS is the foundational semantic lineage for claim-bearing probe work.
8. Never substitute short CAS summaries for original TKS definitions unless the short form is an explicit comparator arm.
9. Preserve native TKS labels; CAS translations are additional versioned fields.
10. Never silently renumber `A1-D10` as `A0-D9`.
11. Never silently collapse TKS Worlds, CAS Domains, and CAS Registers.
12. Never call D3DA and A124 the same definition version.
13. Keep semantic name separate from algebraic role.
14. Treat SDG templates and LLM paraphrases as derived data, not semantic authority.
15. Treat Programming in CAS as a valuable draft/architecture source whose stale Noetic names require reconciliation.
16. “Compiler-valid” means structurally executable; it does not automatically mean psychologically true, empirically validated, or safe.
17. A formal definition or theorem is not a hidden-state result. A hidden-state result is not automatically causal. A causal result is not automatically safe control.
18. Preserve the original-TKS successes, the withdrawn ACCEPT, the failed surface-controlled injection result, and every null result.
19. Do not let a weak comparator invalidate a strong source-grounded readout; report the two claim lanes separately.
20. J-space and CAS-Ohm may add measurements but may not rename or replace TKS semantics.
21. Do not claim 300B from a plan, worker count, or small-model extrapolation.
22. Do not claim recoverable evidence from receipt count without stored bytes and restart reconstruction.
23. If a gate is internally impossible, document the proof, version a corrected preregistration before new data, and continue the program.
24. The honesty boundary is a truth-control mechanism, never a project capability ceiling.

## 18. Final disposition

CAS Harness has already achieved meaningful work:

- a deep TKS mathematical and semantic corpus;
- a serious formal Noetic Topos and simplex target space;
- working Python and Rust compiler components;
- a substantial tested synthetic-data system;
- real Pythia, Qwen, and GPT-NeoX hidden-state research;
- a 95.625% original-TKS40 GPT-NeoX-20B readout;
- genuine targeted causal disruption evidence;
- a 97.5% selected eta-to-epsilon bridge result;
- operational audit, fleet, and evidence infrastructure that can be extended rather than discarded.

The main technical problem is not that universality is forbidden. It is that the semantic lineage, adapter layer, distributed runtime, and evidence transport are not yet unified end to end.

The corrected direction is therefore expansion with discipline:

> Bind the exact original TKS meanings, preserve native axes, learn a model-specific map into the shared TKS state space, automatically discover adapters for unknown models, test semantics and causality against hard controls, carry recoverable evidence, and climb the real GPU ladder through 20B, MoE, 100B, and 300B.

That is what a perfectly finished CAS Harness should do.

## 19. Exact local and external references

- TKS v7.4 master: `C:\Users\wakil\Downloads\Everthing-Tootra-TKS\TKS_v7.4_MASTER.tex`
- Integrated corrected TKS v7.4: `C:\Users\wakil\Downloads\Everthing-Tootra-TKS\TKS_v7_4_FULL_BEAUTIFUL.txt`
- TKS Formal Mathematical Manual v7.2: `C:\Users\wakil\Downloads\Everthing-Tootra-TKS\TKS_FORMAL_MATHEMATICAL_MANUAL_v7.2_COMPLETE.tex`
- Tootra Math Handbook: `C:\Users\wakil\Downloads\Everthing-Tootra-TKS\tootra_math_handbook (1).md`
- CAS Foundational Clarifications: `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md`
- Noetic Topos conservative paper: `C:\Users\wakil\OneDrive\Desktop\tksCAS\peer_review\journal_submission\main.tex`
- Noetic Topos dashboard chapter: `C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\dashboard\public\noetic-topos.md`
- Programming in CAS: `C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas\`
- CAS SDG: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\`
- Owner raw definitions: `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\tks_owner_locked_definitions_20260603.json`
- Protected definition payload: `C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass\api\resources\tks_owner_locked_definitions_20260603.json`
- Prior J-space/CAS-Ohm/300B analysis: `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md`
- Canonical production tracker: `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md`
- RunPod pricing: https://www.runpod.io/pricing
- RunPod network-volume documentation: https://docs.runpod.io/storage/network-volumes
- xAI Grok-1 release: https://github.com/xai-org/grok-1
