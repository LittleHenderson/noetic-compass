# CAS-Native Architecture Provisional Invention Disclosure

**Title:** CAS-Native Architecture for Structured Cognitive-State Modeling, Slot-Level Domain-Descent Attention, and CAS-Aligned Scoring Integration

**Prepared from:** `PATENT_READINESS_MEMO.md`, the `noetic-compass-scaffold/noetic-compass/cas-native` implementation, and CAS engine integration points in `noetic-compass-scaffold/noetic-compass/cas-engine`

**Status:** Technical invention disclosure for counsel review. Not legal advice.

## 1. Field of the Invention

This disclosure relates to computer-implemented neural architectures, structured representation learning, and machine-assisted evaluation systems for large language models and other sequence-processing models.

More specifically, the invention concerns:

- a neural architecture that represents internal model state as a fixed 40-slot cognitive-state structure;
- a domain-descent attention mechanism that operates over those 40 slots rather than over raw token positions;
- a training path that uses structured CAS labels to supervise the model;
- an assessment and scoring integration path that can use heuristic, self-reported, or external-LLM scoring modes with provenance tracking;
- optional integration with a CAS engine / compiler toolchain for structured expressions, admissibility checks, and machine-readable CAS notation.

This disclosure is intentionally technical. It does not rely on consciousness, metaphysics, Kabbalah, or similar non-technical framing.

## 2. Problem Addressed

Standard transformer architectures are strong sequence models, but they do not natively encode the specific structured constraints used by CAS-native systems in this repository. In particular, standard transformers do not natively provide:

- a fixed 40-state latent cognitive structure aligned to operator/domain semantics;
- a slot-level domain order constraint such as P -> C -> E -> O;
- a prerequisite-aware gate tied to structured CAS state relationships;
- a scoring pipeline that keeps generator, scorer, and calibration provenance separate;
- a training path that treats CAS labels as explicit supervision rather than as incidental metadata;
- a machine-readable bridge between structured CAS expressions and neural outputs.

The practical problem is not abstract theory. The practical problem is how to build a model and surrounding software that:

- consumes natural-language prompts or structured CAS expressions;
- represents them through a constrained internal state;
- processes them with attention, gating, and auxiliary heads that reflect the CAS structure;
- outputs scores, state summaries, and risk signals in a way that can be audited;
- supports validation workflows, benchmark comparisons, and human calibration.

## 3. Summary of the Invention

In one embodiment, the invention is a CAS-native neural architecture and surrounding scoring system that combines:

1. token embeddings and positional encoding;
2. a parallel cognitive-state embedding branch;
3. one or more transformer layers that include:
   - a slot-level domain-descent attention module;
   - a fractal attention module;
   - a prerequisite gate;
   - feed-forward processing;
4. an output head that produces:
   - logits for language modeling,
   - a 40-slot cognitive-state tensor,
   - RPM / prerequisite satisfaction signals,
   - inversion scores,
   - proposition truth values or other structured assessment outputs;
5. a training loop that uses structured CAS labels to build target cognitive-state distributions;
6. a scoring and validation layer that can use:
   - heuristic fallback scoring,
   - self-reported inline scoring,
   - or an external secondary LLM scorer;
7. a calibration and evidence system for tracking scorer agreement, benchmark runs, and error cases.

In another embodiment, the architecture can be paired with a CAS executable language / compiler toolchain for validating, encoding, and replaying structured CAS expressions.

## 4. System Overview

### 4.1 CAS-Native Model

The current CAS-native implementation in `cas-native/model/cas_native_model.py` is organized around these components:

- token embedding plus sinusoidal positional encoding;
- a cognitive-state embedding branch that produces slot weights over 40 cognitive states;
- repeated CAS transformer layers;
- a topological / proposition-scoring head;
- an inversion detector head;
- a language-model head.

Each transformer layer combines:

- `DomainDescentAttention`
- `FractalAttentionHead`
- `PrerequisiteGateLayer`
- feed-forward processing and layer normalization

### 4.2 40-Slot Cognitive-State Structure

The architecture uses a fixed cognitive-state representation of 40 slots.

The 40 slots are used as an explicit intermediate representation. The current code base treats these slots as a structured bank rather than as an incidental hidden dimension. The model computes token-to-slot weights, aggregates token states into slot states, applies slot-level constraints and attention, then projects back to token positions.

The key point is that the domain-order constraint is enforced over slots, not over raw token indices.

### 4.3 Domain-Descent Attention

The `DomainDescentAttention` module in `cas-native/model/domain_descent.py` is the clearest implementation of the slot-level structure.

It:

- accepts token hidden states;
- accepts token-to-slot weights for 40 slots;
- aggregates token states into explicit slot states;
- applies a domain-descent mask over slot-to-slot attention;
- optionally applies P -> C -> E -> O ordering and O -> P feedback logic;
- projects the updated slot states back to token positions.

This is materially different from standard token-only attention because the attention constraint is enforced over a fixed slot bank.

### 4.4 Fractal Attention and Prerequisite Gating

The architecture also includes:

- `FractalAttentionHead`, which introduces a multi-scale / self-similar attention path;
- `PrerequisiteGateLayer`, which computes prerequisite satisfaction and gating behavior.

These modules are used as architectural components that bias the model toward the CAS structure.

### 4.5 Scoring and Validation

The surrounding Noetic Compass system includes:

- a wrap / assessment pipeline;
- scoring modes:
  - `heuristic_fallback`
  - `secondary_llm`
  - `self_reported`
- evidence logging and calibration workflows;
- human validation and reconciliation sessions;
- benchmark and provider comparison runs.

This matters for the invention because the model is not isolated. The surrounding software makes it possible to evaluate outputs consistently and to preserve scorer provenance.

## 5. Detailed Embodiments

### 5.1 Embodiment: CAS-Native Forward Pass

In a representative embodiment, the forward pass proceeds as follows:

1. A token sequence is embedded into a `d_model`-dimensional space.
2. Positional encoding is added.
3. If an attention mask is present, padded positions are zeroed.
4. For each CAS layer:
   - cognitive-state weights are generated;
   - token states are aggregated into 40 slot states;
   - domain-descent attention is computed over the slots;
   - fractal attention is computed over the token sequence;
   - both pathways are blended;
   - the prerequisite gate is applied;
   - feed-forward processing is applied.
5. The final hidden states are normalized.
6. A language-model head produces token logits.
7. The cognitive-state branch recomputes a 40-slot representation from the final hidden states.
8. A pooled representation is generated using masked mean pooling.
9. A topos / proposition head produces structured truth values.
10. An inversion detector produces axis-level inversion scores.

This is a concrete technical pipeline, not a theoretical statement.

### 5.2 Embodiment: 40-Slot Domain-Descent Attention

The 40-slot structure is a central embodiment.

The current implementation:

- defines a fixed bank of 40 cognitive-state slots;
- groups them into 4 domain bands of 10 slots each;
- applies a domain-descent mask so that later-domain slots can attend to earlier slots according to the CAS order;
- optionally carries O -> P feedback back into the earliest domain band;
- preserves padding-mask invariance by zeroing masked token contributions.

In practical terms, this means the model is not merely "looking at tokens." It is operating on an internal state lattice that is explicitly constrained by the CAS domain structure.

### 5.3 Embodiment: Structured Supervision Path

The training loop in `cas-native/training/trainer.py` uses structured CAS labels when available.

It:

- reads operator and domain labels from `cas_scores`;
- converts those labels into a 40-state target distribution;
- normalizes the target onto the simplex;
- computes loss against the model's predicted cognitive state;
- combines that with language-model, RPM, and inversion-related loss components.

This is important because the model is not merely being trained as a generic next-token predictor. It is being trained to align internal structure with CAS-specific supervision.

### 5.4 Embodiment: CAS Scoring Integration

The Noetic Compass API supports multiple scoring paths. In the current implementation:

- `heuristic_fallback` provides deterministic structural scoring;
- `secondary_llm` uses an external scorer provider to grade the primary model;
- `self_reported` is only allowed when explicitly selected and is treated as an advanced mode.

The architecture records scoring provenance so that generator and scorer are not conflated. This is technically important because the system can otherwise drift into "self-grading" behavior that is unsuitable for serious evaluation.

### 5.5 Embodiment: Validation and Calibration

The validation subsystem supports:

- human labels;
- scorer-agreement evidence;
- benchmark-suite logging;
- false-positive / false-negative cases;
- calibration sessions for disagreement reconciliation;
- trend summaries by provider and model.

This is not just product analytics. It is part of the technical system because it supports calibration and evaluation of the CAS-native architecture.

### 5.6 Embodiment: Optional CAS Compiler / Language Integration

The repository also includes a Rust CAS compiler / toolchain in `cas-engine`:

- syntax crate (`casc-syntax`);
- IR crate (`casc-ir`);
- CLI (`casc-cli`);
- package tool (`caspm`);
- compiler / interpreter surfaces in `language.rs`.

That tooling can be used to encode structured CAS expressions, validate admissibility relationships, and create machine-readable examples that are useful for testing and for future model-control integrations.

This should be treated as a related embodiment or adjacent asset, not as the entire invention if the filing budget is limited.

## 6. Explicit 40-Slot / State Attention Story

This section is included because the 40-slot structure is one of the invention's most distinctive technical features.

### 6.1 Why 40 Slots Matter

The architecture maintains a fixed 40-state latent bank. In the current implementation, the model uses:

- 10 operator states per domain;
- 4 domains;
- slot-level aggregation and projection;
- a domain descent mask over slot-to-slot attention.

This gives the model a persistent internal structure that is stable across variable-length input sequences.

### 6.2 Why Slot-Level Attention Is Different

Standard transformers compute attention primarily over token positions.

This architecture instead:

- maps tokens into structured slots;
- enforces a domain-order mask on slot interactions;
- optionally feeds O-domain information back toward P-domain slots;
- then maps the structured slot state back to tokens.

That creates a form of inductive bias that is much closer to a state machine or structured latent space than to a plain token mixer.

### 6.3 Technical Benefit

The technical benefit is not philosophical. It is architectural:

- better control over internal structure;
- clearer mapping from input to output scoring;
- more interpretable separation between domains;
- easier calibration against labels and benchmark cases;
- stronger masking / padding behavior when implemented correctly.

## 7. Training and Supervision Path

The training path is a second important inventive area.

### 7.1 Inputs

Training data may include:

- prompt text;
- response text;
- token-level masks;
- operator scores;
- domain scores;
- human labels;
- benchmark metadata;
- scorer provenance.

### 7.2 Target Construction

The trainer constructs a target cognitive-state distribution from CAS labels.

The current implementation uses:

- operator scores to shape the within-domain distribution;
- domain scores to weight the domains;
- simplex normalization of the resulting 40-state vector;
- uniform fallback when structured labels are unavailable.

### 7.3 Loss Coupling

The loss can combine:

- language modeling loss;
- cognitive-state alignment loss;
- RPM satisfaction loss;
- inversion penalty;
- drift or regularization terms.

This is an important distinction from ordinary language-model training because the model is supervised against structured CAS state objectives, not just next-token likelihood.

## 8. Scoring-Engine Integration

The scoring integration is part of the product and may be part of one or more claim families.

### 8.1 Scoring Modes

The system currently recognizes:

- `heuristic_fallback`
- `secondary_llm`
- `self_reported`

The practical significance is that the system can compare:

- a deterministic structural baseline,
- a separate external scorer,
- and self-reported scores where explicitly allowed.

### 8.2 Provenance and Auditability

The result payload includes scorer provenance so that:

- generator model;
- scorer model;
- scoring mode;
- and validation history

remain visible to the user and to counsel reviewing the system.

### 8.3 Why This Matters for Patent Strategy

This is not just a UI detail. It is part of the technical control plane.

It solves a real system problem: how to keep assessment outputs auditable when the generator and scorer may differ.

## 9. Differentiators Over Standard Transformers

The main differentiators are:

1. A fixed 40-slot cognitive-state bank instead of unconstrained latent mixing.
2. Slot-level domain-descent attention instead of token-only attention.
3. A prerequisite gate tied to structured state relationships.
4. A fractal attention path that is explicitly represented as a separate mechanism.
5. A training path that uses structured CAS labels.
6. A scoring and calibration system that keeps generator and scorer provenance separate.
7. A validation subsystem that stores benchmark and disagreement evidence.
8. Optional integration with a CAS compiler / expression toolchain.

In combination, these features create a specialized architecture for structured assessment rather than a generic transformer with renamed heads.

## 10. Potential Claim Families

These are not final claims. They are candidate claim families for counsel to refine.

### Family A: CAS-Native Neural Architecture

Possible independent claim scope:

- a computer-implemented neural architecture with token embeddings;
- a fixed 40-slot cognitive-state representation;
- slot-level domain-descent attention constrained by a domain order mask;
- a prerequisite gate;
- an output head that emits structured scores or state values.

Dependent claim examples:

- explicit 4-domain / 10-slot partitioning;
- O -> P feedback path;
- masking behavior for padded tokens;
- blended domain and fractal attention paths.

### Family B: Structured Supervision / Training Method

Possible independent claim scope:

- training a neural model using labeled operator and domain scores;
- constructing a 40-slot target distribution from those scores;
- normalizing the target to a simplex;
- optimizing the model toward both language and structured-state objectives.

Dependent claim examples:

- fallback to uniform targets when labels are absent;
- combining cognitive-state loss with RPM and inversion terms;
- using attention masks to preserve padded-token invariance.

### Family C: Assessment and Scoring Control Plane

Possible independent claim scope:

- a computer system that performs model assessment using explicit scoring modes;
- external scorer support;
- scorer provenance capture;
- validation logging and calibration sessions.

Dependent claim examples:

- secondary LLM scorer with fixed provider selection;
- self-reported mode behind an explicit advanced toggle;
- evidence logging for scorer agreement and false-positive/negative cases.

### Family D: CAS Expression / Compiler Integration

Possible independent claim scope:

- a machine-readable CAS expression language;
- parsing and validation of CAS state expressions;
- compilation or lowering to executable forms;
- admissibility-aware execution.

This family may be narrower and more prior-art-sensitive, but it is still potentially valuable.

## 11. Alternative Embodiments

The invention does not need to be limited to the exact implementation currently in the repository.

### 11.1 Alternative Scorers

The external scorer can be:

- Anthropic;
- OpenAI;
- xAI;
- Qwen;
- Meta;
- DeepSeek;
- or a local fine-tuned scorer.

### 11.2 Alternative Latent Sizes

The slot bank does not have to remain exactly 40 in every embodiment, but 40 is the current implementation and the most important disclosure anchor.

### 11.3 Alternative Architecture Topologies

The slot-level domain descent mechanism could be:

- embedded in one layer;
- repeated across layers;
- used only in a subset of layers;
- or used as a preprocessor / postprocessor to a transformer stack.

### 11.4 Alternative Training Regimes

The same architecture could be trained:

- supervised;
- semi-supervised;
- with human calibration;
- with benchmark contrastive data;
- or with synthetic labels generated by a structured scorer.

### 11.5 Alternative Integration Modes

The CAS engine / compiler integration can be:

- a standalone CLI;
- a backend validation service;
- a notebook / research tool;
- or a model-side validation layer.

## 12. Figures To Draw

Counsel or the drafting team should consider preparing the following figures for the provisional packet:

1. System overview diagram showing prompt in, CAS-native model, scorer, validation, and evidence out.
2. CAS-native layer diagram showing token embedding, cognitive-state embedding, domain descent attention, fractal attention, RPM gate, and output heads.
3. 40-slot state diagram showing the 4 domains of 10 states each.
4. Domain-descent mask diagram showing allowed slot-to-slot attention patterns.
5. Training pipeline diagram showing CAS labels to target distribution to loss.
6. Scoring provenance diagram showing generator, scorer, scoring mode, and evidence log.
7. Validation workflow diagram showing human labels, calibration sessions, benchmark runs, and agreement analysis.
8. Optional compiler / expression flow diagram showing CAS source expression to parsed artifact to executable validation.

## 13. Inventorship and Source-Material Notes

This disclosure is based on source material already present in the workspace, including:

- `PATENT_READINESS_MEMO.md`
- `noetic-compass-scaffold/noetic-compass/cas-native/model/cas_native_model.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/model/domain_descent.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/model/fractal_attention.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/model/rpm_gate.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/model/topos_reasoner.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/training/trainer.py`
- `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/evaluate.py`
- `noetic-compass-scaffold/noetic-compass/api/models.py`
- `noetic-compass-scaffold/noetic-compass/api/pipeline/runner.py`
- `noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py`
- `noetic-compass-scaffold/noetic-compass/api/pipeline/llm_scorer.py`
- `noetic-compass-scaffold/noetic-compass/api/routes/validation.py`
- `noetic-compass-scaffold/noetic-compass/api/validation/*.py`
- `noetic-compass-scaffold/noetic-compass/cas-engine/src/language.rs`
- `noetic-compass-scaffold/noetic-compass/cas-engine/crates/casc-syntax`
- `noetic-compass-scaffold/noetic-compass/cas-engine/crates/casc-ir`
- `noetic-compass-scaffold/noetic-compass/cas-engine/crates/casc-cli`
- `noetic-compass-scaffold/noetic-compass/cas-engine/crates/caspm`

Inventorship should be confirmed by counsel. The current repository also shows AI-assisted development history, so the factual record should distinguish:

- who conceived the technical architecture;
- who implemented the code;
- which parts were drafted or refined with AI assistance;
- when the first public disclosure occurred.

Do not list AI systems as inventors. Preserve the human inventorship facts separately for counsel.

## 14. Open Questions For Counsel

1. Should the first filing family be the Noetic Compass assessment/calibration system, the CAS-native model architecture, or the compiler/toolchain?
2. Should the CAS-native architecture and the assessment pipeline be filed as one provisional or split into separate provisionals?
3. How should the public-disclosure timeline be documented for the Vercel deployment, GitHub artifacts, PDFs, and stakeholder demos?
4. Should the provisional include the CAS compiler/toolchain as a related embodiment or as a separate invention family?
5. Should the filing emphasize the fixed 40-slot embodiment, or should it also claim broader slot-count variants?
6. Should the scoring provenance and calibration layer be claimed independently, or kept as dependent claims?
7. Should the drafting strategy prioritize software-method claims, system claims, or both?
8. How much of the current research-stage heuristic scoring should be disclosed versus treated as implementation detail?
9. Are any of the current disclosures already public enough to affect foreign filing strategy?
10. What supporting diagrams, notebooks, demo artifacts, and source excerpts should be assembled before filing?

## 15. Conservative Filing Position

The safest and strongest way to frame this invention is:

> A computer-implemented structured assessment and representation system that uses a fixed 40-slot cognitive-state architecture, slot-level domain-descent attention, structured supervision, and explicit scoring provenance to evaluate and control model outputs.

That framing stays technical, matches the implementation, and avoids overclaiming any unproven philosophical or scientific theory.

## 16. Final Note

This document is an invention disclosure draft, not a patent application.

The next step for counsel is to decide:

- whether to file provisionally immediately;
- which family to file first;
- which diagrams and source excerpts to attach;
- and how to manage any prior public disclosure risk.
