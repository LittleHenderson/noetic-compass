# CAS Harness — Product Specification Sheet
## Investor / Strategic Partner Distribution (NDA Required)

**Version**: 1.5-EXTERNAL · **Date**: 2026-05-21 · **Classification**: Confidential, NDA-Gated
**Distribution**: Authorized recipients only, post-executed NDA

---

## NDA Notice

This document contains confidential and proprietary information of Noetic Compass / CAS Harness (Little Henderson, founder). Receipt of this document is subject to the executed Non-Disclosure Agreement between the recipient and Noetic Compass. Reproduction, disclosure, or use of any information herein, in whole or in part, for any purpose other than evaluating a potential strategic, investment, or partnership relationship is prohibited. The CAS framework primitives are covered by USPTO Provisional Patent Application #64/037,173. Additional filings on CAS Harness-specific mechanisms are in process; recipients are advised that the methodologies described herein are subject to ongoing patent protection.

## What This Document Is

A capability overview for prospective investors and strategic partners evaluating CAS Harness. It documents:

- What CAS Harness does and what it has empirically demonstrated
- The audit-grade discipline distinguishing it from contemporaneous interpretability work
- The validated cross-architecture claim (three independent model families)
- The honest claim boundaries — what is and is not licensed for external use today
- The IP portfolio status and provisional filing position

## What This Document Is NOT

The following content is deliberately withheld from external distribution:

- **Internal rollout plan and timeline** — separated into the internal-only roadmap document
- **Specific algorithmic hyperparameters** (probe rank values, layer indices, training configurations, fixture sample sizes beyond headline)
- **Specific component identifiers** (attention head IDs, MLP neuron indices, exact subspace dimensions)
- **Source code paths and internal API design**
- **Pre-registration documents and per-stage methodology**
- **Commit-level reproducibility provenance**
- **Implementation specifics that would enable reverse engineering**

Recipients may request additional methodology depth under a separate technical-disclosure NDA after initial evaluation. The redaction approach is moderate: the *what* is fully visible; the *exactly how* is preserved as IP.

---

## 1. Executive Summary

CAS Harness is a cross-model interpretability and conditioning platform built on the **Cognitive Architecture System (CAS) v7.7** framework. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, condition the model's next-token probability distribution by realizing the detected structure as readable context, and emit audit-grade evidence packets that another party can independently verify.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism *before* any empirical experiment ran. The prediction has been empirically confirmed on **five open-weight models across three architecture families** (EleutherAI Pythia at three scales, AI2 OLMo, Alibaba Qwen) and on **two independent evidence tiers** (activation-trace and weight-geometry).

### Today's load-bearing claim, reserved-language, defensible for audit

> CAS Harness reads cognitive structure from open-weight transformer hidden states across five model points and three architecture families (EleutherAI Pythia, AI2 OLMo, Alibaba Qwen). The η → ε bridge — the read-and-realize loop predicted by Proposition 5.6 of the Noetic Topos paper — conditions next-token likelihood with effect sizes that grow then plateau across Pythia scale, strengthen on OLMo, and reach their highest observed value on Qwen2.5-1.5B (+0.7960 likelihood Δ, p = 2.92×10⁻¹²). Six cognitive axes are detected, ablation-validated, and multi-layer trace-audited with blind-spot flagging that distinguishes model-side weakness from readout-position weakness. CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099) — independent weight-geometry evidence of the bridge mechanism. Causal localization is empirically established at two granularities: head-level (necessity via ablation + sufficiency via path patching) AND **sparse MLP-neuron-cover-level with full bidirectional control** — ablating the cover inverts the classification margin, amplifying it strengthens the margin, polarity-flipping it reverses the margin entirely; all three tests pass 112/112 with matched-control validation at p < 10⁻³³ and bit-exact patch-back recovery. Cross-architecture transfer is closed at three independent out-of-family architectures.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

The probing chain closed in May 2026: cross-scale within Pythia (three model points), cross-architecture to OLMo, cross-architecture to Qwen, weight-geometry evidence, multi-layer trace auditing, blind-spot detection with readout-vs-model-side disambiguation, runtime-safe acceptance/suppression layer, and customer-facing Evidence Packet schema with authenticated delivery surface.

### 2.2 Mission

CAS Harness exists to make the cognitive architecture inside any open-weight large language model **inspectable, validatable, conditionable, and audit-traceable** by an external software service — without requiring the model's vendor to publish interpretability tooling, without modifying the model's weights, and without sacrificing the reserved-language audit discipline required for regulator-grade evidence.

### 2.3 Strategic Relationship to CAS Native

CAS Harness is a **parallel product line**, not a replacement for CAS Native:

- **CAS Native** is "our model, transparent by construction" — the from-scratch flagship
- **CAS Harness** is "your model, we make it inspectable" — the cross-model platform

The two products share the same underlying framework, theoretical apparatus, and evidence-tier discipline. They diverge at the substrate: CAS Native trains weights on CAS-structured targets from scratch; CAS Harness reads CAS structure from a foreign model's existing weights.

---

## 3. Mathematical Foundation

### 3.1 The η → ε Bridge

CAS Harness's central architectural pattern is the **eta-epsilon bridge**, mathematically grounded in the Noetic Topos paper.

| Map | Direction | Implementation Role |
|---|---|---|
| **η (eta)** | Embedding: structure → realization | Reads CAS class from hidden-state activations |
| **ε (epsilon)** | Realization: structure → tokens | Emits CAS structure as readable prefix for the foreign model |

### 3.2 The Section-Retraction Identity

> **ε ∘ η = id** (realization after embedding = identity)
> **η ∘ ε ≠ id** (re-embedding after realization may lose information)

This asymmetry is load-bearing. ε is one-directional; ablation attempts to invert ε structurally cannot succeed. Empirically, attempts to steer generation by hidden-state ablation failed; attempts to condition generation by ε-realization succeeded.

### 3.3 Proposition 5.6 — Counit Surjectivity

The Noetic Topos paper proves: for any morphism g, the pullback of the counit ε along g is surjective. The Noetic Coverage Noe-Cov-3 axiom states the covering sieve contains ε. Applied to transformer architectures: prefix tokens are attended to by every subsequent position by construction — this is not a hyperparameter, it is the architectural property of self-attention.

The prediction was made in the Noetic Topos paper's first draft. The bridge mechanism it predicts has now been empirically confirmed across:

- Three model scales within one architecture family (Pythia)
- Two out-of-family architectures (OLMo; Qwen — three independent labs, lineages, corpora, tokenizers)
- Two evidence tiers (activation-trace AND weight-geometry alignment)
- Six cognitive axes
- Component-level necessity AND sufficiency tests

### 3.4 Framework-Internal Diagnostic Tools

Three CAS-internal diagnostic tools have been empirically validated:

- **Lacunarity gate**: measures factorization gappiness. Empirical results range from 0.793 (lumpy single-axis) down to 0.0016 (the cleanest factorization signature in project history, multi-layer trace).
- **Fractal classifier**: orbit classifier producing Stabilizing / Amplifying / Oscillatory / Neutral verdicts. Predicted generation-steering failure before the empirical attempt.
- **Weight-geometry alignment**: Principal-angle analysis between CAS Foundation subspace and model output-weight space. Pythia-2.8B result: 2.83× random expectation (p = 0.0099). First static-weight evidence of the bridge mechanism, complementary to activation-tier evidence.

The framework's own diagnostic tools have produced numerical predictions of experimental outcomes BEFORE the experiments ran — four times now, each holding.

---

## 4. Architecture

### 4.1 System Overview

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (Pythia, OLMo, Qwen, future families)
     │
     ├── Multi-layer hidden-state capture
     │       │
     │       ▼
     │   COGNITIVE AXIS PROBES (η) — Linear classifiers across six axes
     │       │
     │       ▼
     │   MULTI-LAYER TRACE — Stable-like vs problem-like classification
     │       │
     │       ▼
     │   BLIND-SPOT DETECTOR — Model-side weakness vs readout-position weakness
     │       │
     │       ▼
     │   CAS structure label
     │       │
     │       ▼
     │   REALIZATION LAYER (ε)
     │       │
     └───────┴── Prepend to original prompt
                  │
                  ▼
            FOREIGN MODEL — second forward pass with prefix
                  │
                  ▼
            LIKELIHOOD SHIFT in next-token distribution
            EVIDENCE PACKET emitted with full audit trail
```

### 4.2 Component Inventory (Capability-Level)

| Component | Status | What It Does |
|---|---|---|
| Activation capture | Validated | Per-layer hidden-state extraction across multiple token positions |
| Cognitive axis probes (six axes) | Validated | Linear classifiers per CAS axis with standard preprocessing |
| Multi-layer trace classifier | Validated | Reads probe confidence across all layers; flags trajectory quality |
| Blind-spot detector | Validated | Distinguishes architectural weakness from probe-config sensitivity |
| Realization layer (ε) | Validated | Template-based emission of CAS structure as readable natural language |
| Likelihood scorer | Validated | Computes semantic-class log-likelihood shift |
| Subspace ablation hook | Validated | Causal removal of CAS-aligned representational structure |
| Lacunarity computer | Validated | Factorization quality measure |
| Fractal classifier | Validated | Orbit-based class trajectory analysis |
| Weight-geometry analyzer | Validated | Principal-angle analysis vs unembedding space |
| Cross-architecture adapter | Validated for Pythia + OLMo + Qwen | Abstracts model-specific details |
| Component attribution + path patching | Validated (recent) | Head-level necessity + sufficiency for the readout |
| Evidence Packet emitter | Validated | 15-field versioned schema with validator + markdown renderer |
| Verification Stack | Validated | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Validated | Three customer-configurable verification modes |
| Generation Readiness Gate | Validated | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Authenticated delivery API + Atlas drawer | Validated | REST endpoint + frontend reviewer surface |
| Two-bridge hidden-content detector | Prototype | Internal-vs-emitted comparison surfaces withheld content |

### 4.3 Three Customer Deployment Modes

| Mode | What the customer provides | What CAS Harness does | Where weights live |
|---|---|---|---|
| Hosted | Model ID or weights upload | Train probes, run inspections, host dashboard | CAS Harness infra (encrypted) |
| Bring-your-endpoint | HTTPS endpoint exposing hidden states | Train probes against the endpoint; run inspections client-side | Customer infra |
| Self-hosted | Install CAS Harness toolkit | Sell toolkit + optional cloud probe training | Customer infra |

---

## 5. Validated Capabilities

### 5.1 Cognitive Structure Detection

| Axis | Classes | Model | Probe Accuracy | Lift Over Text Baseline | Status |
|---|---:|---|---:|---:|---|
| 10 Noetics | 10 | Pythia-160M | 73.9% | +27.5 pp | Validated |
| 28 Foundations | 28 | Pythia-160M | 78.6% | +28.9 pp | Validated |
| 28 Foundations | 28 | Pythia-1B | 82.4% | — | Validated (cross-scale) |
| 28 Foundations | 28 | Pythia-2.8B | 85.9% | — | Validated (cross-scale) |
| 28 Foundations | 28 | OLMo-1B | 90.6% | — | Validated (cross-architecture) |
| 28 Foundations | 28 | Qwen2.5-1.5B | 82.0% | — | Validated (cross-architecture) |
| 40 Elements (Noetic × Domain) | 40 | Pythia-160M | 89.8% | +39.7 pp | Validated |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | Validated (readout-causal) |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | Validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | Validated |
| Multi-Layer Trace classification | 10 | Pythia-160M | 95.4% | — | Validated |

Statistical separation from text baselines ranges from p ≈ 10⁻⁵⁰ on the early stages to machine-zero on the more recent classifiers. The signal is unambiguous across every axis and model tested.

### 5.2 Readout-Causal Validation

When the detected CAS-aligned representational structure is causally removed from the hidden states, classification accuracy collapses to exact-chance levels for the affected axis. Matched random-control ablations of the same dimensionality produce essentially zero disruption.

| Test | Result |
|---|---|
| Foundation subspace ablation, Pythia-160M | 78.6% → 3.57% (exact 1/28 chance) |
| Random same-rank ablation, Pythia-160M | Mean disruption 0.000, max 0.000 |
| 10-Noetic subspace ablation | 73.9% → 10.0% (exact 1/10 chance) |
| 5-Operator subspace ablation | 99.2% → 20.0% (exact 1/5 chance) |
| Grammar subspace ablation | 93.0% → 10.0% (exact 1/10 chance) |
| Formula subspace ablation | 90.0% → 10.0% (exact 1/10 chance) |

**Five ablation tests pass across five distinct cognitive axes**, each collapsing to exact chance with clean random nulls.

### 5.3 Likelihood Conditioning via the η → ε Bridge

| Model | Probe-readable Δ vs no prefix | Margin over partner | Positive cases | Wilcoxon p |
|---|---:|---:|---:|---:|
| Pythia-160M | +0.283 | +0.683 | 81/112 | < 0.0001 |
| Pythia-1B | +0.554 | +1.246 | 90/112 | 2.58×10⁻¹⁴ |
| Pythia-2.8B | +0.583 | +1.336 | 92/112 | 3.08×10⁻¹⁵ |
| OLMo-1B | +0.604 | +1.305 | 87/112 | ≈ 10⁻¹⁵ |
| **Qwen2.5-1.5B** | **+0.7960** | **+1.6253** | **83/112** | **2.92×10⁻¹²** |

Trends:

- **Monotonic-converging within Pythia.** Effect grows 160M → 1B → 2.8B with diminishing-returns shape.
- **Cross-architecture transfer is positive at three families.** OLMo and Qwen both show effects equal to or stronger than Pythia at comparable parameter count, despite different lab, lineage, corpus, and tokenizer.
- **Raw CAS symbols stay null at every scale.** Confirms the effect is ε-realization (readable natural-language prefix), not symbol-recognition. The mechanism is structural, not lexical.
- **Qwen produces strongest effect.** Consistent with the hypothesis that richer / multilingual training corpora produce more crystallized CAS structure.

### 5.4 Factorization Quality

Lacunarity (Var/Mean²) measures how cleanly the detected classes factor. Lower is better; clean factorization typically falls below 0.05.

| Axis | Model | Lacunarity |
|---|---|---:|
| 28 Foundations | Pythia-160M | 0.021 |
| 28 Foundations | Pythia-1B | 0.015 |
| 28 Foundations | Qwen2.5-1.5B | 0.0084 |
| Multi-Layer Trace | Pythia-160M | 0.0016 |

The 0.0016 multi-layer trace lacunarity is the cleanest factorization the project has produced.

### 5.5 Framework Predictive Validity

The framework's diagnostic tools have made committed numerical predictions BEFORE four different experiments. All four held — including the central η → ε bridge prediction (Proposition 5.6) and the weight-geometry alignment prediction.

### 5.6 Cross-Scale and Cross-Architecture Validation

| Validation gate | Status |
|---|---|
| Within-architecture cross-scale (Pythia 160M / 1B / 2.8B) | Closed — monotonic-converging, plateau around 1B |
| Cross-architecture, first out-of-family (OLMo-1B, AI2) | Closed — different lab, lineage, corpus, tokenizer |
| Cross-architecture, second out-of-family (Qwen2.5-1.5B, Alibaba) | Closed — third independent family, strongest observed effect |
| Layer-selection rule (best layer 39–50% of network depth) | Transfers cleanly across all five models |
| Raw-symbol null control | Holds at every scale |

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, and not language-specific** — three independent labs, three corpora (one English-only, one English-only with different curation, one multilingual+code), three tokenizer families.

### 5.7 Weight-Geometry Alignment

First independent evidence tier complementary to activation traces. Principal-angle analysis between the CAS Foundation subspace and the model's output-weight space.

- **Pythia-2.8B output-side alignment: 2.83× random expectation (p = 0.0099)**
- Input-side: random (consistent with the input-side hypothesis being null)

This is the first static-weight evidence of the bridge mechanism — testable without ever running a forward pass.

### 5.8 Multi-Layer Trace + Blind-Spot Detection

| Capability | Status |
|---|---|
| Multi-layer trace classification | Validated |
| Lacunarity 0.0016 across the trace classifier | Cleanest factorization in project |
| Blind-spot detection per-class | Validated |
| Readout-position vs model-side weakness disambiguation | Validated |

This component answers the question regulators and reviewers will inevitably ask: *"How do you know when CAS Harness can't read the model?"* — and answers it with disambiguated structural diagnostics, not best-guesses.

### 5.9 Component-Level Causal Localization

CAS Harness establishes causal localization at two granularities, both with necessity + sufficiency evidence and matched-control validation.

#### 5.9.1 Head-Level Localization

- **Necessity (component ablation)**: Removing the identified attention-head components drops probe accuracy from 78% to 19%. Matched same-kind / same-layer control ablations do not produce equivalent disruption (p = 0.0323).
- **Sufficiency (path patching)**: Restoring only those components' activations in an otherwise-ablated model produces 100% recovery of probe accuracy. Random matched patch controls do not produce equivalent recovery.

The CAS Foundation readout is carried by an identifiable, causally testable, and matched-control-validated set of attention components.

#### 5.9.2 Sparse Neuron-Cover Localization (Finest Granularity Currently Validated)

A subsequent layer of testing identifies **sparse MLP intermediate-neuron covers** (~1% of layer width) that causally support class-specific Foundation hard-partner readout margins. Three independent tests with matched random-control validation:

| Test | Effect on target-vs-partner margin | Random matched-control effect | Examples passing |
|---|---:|---:|---|
| **Ablate the cover** | Margin inverts (+6.37 → −6.28; total swing 12.65) | −0.13 (essentially zero) | 112 of 112 (p < 10⁻³³) |
| **Amplify the cover** | Margin increases by +12.72 | −0.08 (near-null/negative) | 112 of 112 (p < 10⁻³³) |
| **Polarity-flip the cover** | Margin drops by 25.15, pushing below zero | −0.14 (essentially zero) | 100% of rows (full classification reversal) |

Additional diagnostic: amplifying the **wrong class's** (partner) cover flips the prediction toward the wrong class in 25.9% of rows — independent evidence the cover is genuinely controlling the readout, not riding alongside it.

**Patch-back recovery** after targeted ablation: bit-exact (mean absolute margin error = 0.0).

This is **bidirectional causal control at sparse-neuron-cover granularity**:
- *Remove* the cover → the classification collapses
- *Amplify* the cover → the classification strengthens
- *Flip* the cover's polarity → the classification reverses

The localization is bounded: it is **cover-level**, not single-neuron monosemantic. The sparse cover (32 of 3072 neurons) is the causal unit — individual neurons within the cover may carry additional structure not isolated by this methodology.

### 5.10 Hidden-Content / Suppression Detection (Prototype)

Two-bridge architecture (internal-state CAS profile vs emitted-text CAS profile) surfaces what the model is internally computing but not emitting. Detection at CAS-class granularity. Promoted from concept to working prototype.

### 5.11 Verification Stack — Runtime-Safe Accept/Suppress

The CAS Verification Stack is the runtime-deployable decision surface. It uses only non-oracle internal states (stable / conflicted / uncertain / drifting / ensemble agreement) at inference time. Gold labels are required only at validation time, not at inference.

**Headline result, audit-clean rerun:**
- **87.6% accept rate at 99.78% accepted accuracy**
- **0.22% silent error rate**
- 12.4% suppression rate on conflicted/unstable cases

This is the result that distinguishes CAS Harness from "we trained a classifier" — it provides runtime decisions auditable by a regulator, with reasons attached to every suppression.

### 5.12 Three Customer-Configurable Verification Modes

- **HIGH_PRECISION** — Regulator/legal-grade, low-error, conservative coverage
- **BALANCED** — Default product mode
- **MAX_COVERAGE_TRIAGE** — Human-review feed, maximum coverage

All three modes were independently calibrated on OLMo-1B and Qwen2.5-1.5B fixtures. All six cells (3 modes × 2 model families) meet pre-registered per-mode targets. Status: product-shipped as a configuration surface.

### 5.13 Generation Readiness Gate — Four-Tier Action Discipline

Opt-in, non-mutating diagnostic policy module. Reads CAS signals (Lacunarity + Inversion flags + RPM satisfaction + Verification Stack decision) and emits one of four actions with full audit trail:

- **allow** — output proceeds normally
- **caveat** — output proceeds with surfaced caveat
- **constrain** — output proceeds under constrained generation
- **suppress** — output is withheld with reason codes

Zero learnable parameters. Default unattached. Foreign model's forward path unchanged.

### 5.14 Evidence Packet Schema

15-field versioned schema (`cas_harness_evidence_packet_v1`) with validator, markdown renderer, and reference samples covering all four decision tiers. The customer-facing artifact CAS Harness emits per inspection. Bit-identical reproducibility via `trace_id`.

### 5.15 Authenticated Evidence Packet Delivery

REST API endpoint with JWT authentication, path-traversal guard, size cap, schema round-trip validation. Frontend Atlas reviewer drawer with seven tabs, ARIA-complete keyboard semantics, and JSON/Markdown export. The schema, route, and drawer together comprise the operational customer-facing artifact that turns the 21+ stage research chain into a deliverable regulatory product.

### 5.16 Tier Closure Summary

| Evidence Tier | Status |
|---|---|
| Readout (detection above baseline) | Closed |
| Readout-causal (collapse to exact chance under ablation) | Closed (5 axes) |
| Likelihood-conditioning via η → ε bridge | Closed |
| Factorization (lacunarity below 0.05) | Closed |
| Framework-predictive validity (pre-registered predictions held) | Closed (4 predictions) |
| Cross-scale within architecture (3 model points) | Closed |
| Cross-architecture (3 independent families) | Closed |
| Weight-geometry alignment (static-weight evidence tier) | Closed |
| Multi-layer trace + blind-spot detection | Closed |
| Component-level causal localization (head-level, necessity + sufficiency) | Closed |
| Sparse neuron-cover causal localization (ablation + amplification + polarity-flip + patch-back) | Closed |
| Output-side component steering (likelihood-margin lift) | Partial — directional evidence; row-consistency gate not yet passed; calibrated per-class steering is the next gate |
| Runtime-safe acceptance/suppression | Closed |
| Mode-configurable verification | Closed |
| Four-tier generation readiness | Closed |
| Authenticated Evidence Packet delivery | Closed |
| Hidden-content / suppression detection (prototype) | Open — advancing |
| Scale beyond 2.8B parameters | Open |
| Surface-text steering at scale | Open |
| Multi-Harness Composition coordinator (planned, components proven) | Open |

---

## 6. Methodology Discipline as Competitive Differentiator

CAS Harness's audit-grade methodology is itself a product feature. Each validated stage adheres to:

1. **Pre-registered acceptance criteria.** Gates and thresholds locked in writing *before* data runs. If the data doesn't meet the bar, the claim doesn't ship. No retroactive metrics, no post-hoc explanations.

2. **Locked artifact hashes.** Activation captures fingerprinted. Runs against the original fingerprint are formal; runs against a recapture are explicitly flagged as diagnostic.

3. **Matched controls.** For ablation work, same-kind same-layer matched controls are the preregistered primary comparison. Broad random ablation is acknowledged as a secondary diagnostic with known high-variance properties.

4. **Honest NULL discipline.** When a method does not produce its expected result, the result is recorded as a formal NULL and the boundary it establishes is added to the claim ladder. NULLs are not buried.

5. **Reserved-language claim map.** External-facing claims are tied to specific evidence; nothing is asserted beyond what the evidence supports. The map is auditable.

6. **Independent reproducibility commitment.** Locked manifests + fingerprints + standing reproducibility provenance enable third-party verification without proprietary access.

This discipline produces a methodologically stronger evidence base than the majority of contemporary published interpretability work.

---

## 7. Accomplishments

### 7.1 Scientific

1. Demonstrated CAS structure is detectable inside foreign open-weight LLMs across three architecture families and five model points
2. Demonstrated the detected structure is causally load-bearing for cognitive readout (five axes pass collapse-to-exact-chance ablation)
3. Closed the η → ε bridge end-to-end on five model points across three model families
4. Empirically confirmed Proposition 5.6 of the Noetic Topos paper at two evidence tiers
5. Made four pre-registered framework-internal predictions, all of which held
6. Closed the cross-architecture-redundancy gate at three independent families with p-values from 10⁻¹² to 10⁻¹⁵
7. Established multi-layer trace methodology with blind-spot detection and readout-vs-model-side disambiguation
8. Produced first weight-geometry evidence of the bridge mechanism (2.83× random expectation, p = 0.0099)
9. Established component-level causal localization at head-level with necessity AND sufficiency tests passing (matched-control validated)
10. Established sparse MLP-neuron-cover causal localization with full bidirectional control — ablation, amplification, and polarity-flip — all passing 112/112 examples with p < 10⁻³³ and bit-exact patch-back recovery
10. Prototyped hidden-content / suppression detection via two-bridge methodology
11. Established referee-defensible audit methodology with multiple consecutive pre-registered confirmatory stages

### 7.2 Engineering

1. Complete probing pipeline reusable across model architectures (Pythia + OLMo + Qwen validated)
2. Six reusable cognitive axes covering structural, compositional, and operator-level CAS primitives
3. Cross-architecture adapter validated on three model families
4. Multi-layer trace classifier + lacunarity + fractal classifier diagnostic suite
5. Realization layer (ε) emitting CAS structure as readable natural language
6. Verification Stack with runtime-safe accept/suppress at 87.6% / 99.78%
7. Three customer-configurable verification modes
8. Four-tier Generation Readiness Gate
9. 15-field Evidence Packet schema with validator + renderer + canonical samples
10. Authenticated REST API + frontend reviewer drawer with ARIA-complete semantics
11. Two-bridge hidden-content detection prototype

### 7.3 Strategic

1. CAS Harness established as a parallel product line to CAS Native with distinct mechanism, distinct legal IP framing, distinct customer base
2. Framework predictive validity demonstrated at two evidence tiers
3. Cross-architecture-redundancy gate closed at three independent families
4. Reserved-language discipline established that survives audit AND comparison to contemporaneous interpretability tools

---

## 8. Reserved-Language Claim Map

External-facing claims must use this table.

| Claim | Status |
|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED |
| "The detected structure is causally load-bearing for cognitive readout" | LICENSED |
| "The mechanism is framework-predicted" | LICENSED |
| "We can condition the model's next-token probability distribution" | LICENSED |
| "This works cross-architecture (Pythia + OLMo + Qwen — three independent families)" | LICENSED |
| "Mechanism is not lab-specific, not corpus-specific, not language-specific" | LICENSED |
| "This works cross-scale (Pythia 160M / 1B / 2.8B, monotonic-converging)" | LICENSED |
| "CAS Foundation subspace shows output-weight alignment above random" | LICENSED |
| "We can flag blind spots and distinguish model-side from readout-position weakness" | LICENSED |
| "We can detect hidden / withheld content at CAS-class granularity" | LICENSED with caveats (prototype tier) |
| "We can make runtime-safe accept/suppress decisions without gold labels at inference time" | LICENSED |
| "We offer three customer-configurable verification modes calibrated per architecture family" | LICENSED |
| "We emit per-example generation-readiness policies (allow/caveat/constrain/suppress)" | LICENSED |
| "We emit per-inspection Evidence Packets in a versioned schema" | LICENSED |
| "We expose Evidence Packets via authenticated runtime route + reviewer drawer" | LICENSED |
| "We have component-level causal localization with necessity AND sufficiency tests passing" | LICENSED |
| "We can identify sparse MLP-neuron covers that causally support class-specific structural readouts in any open-weight LLM tested" | LICENSED |
| "We can ablate, amplify, or polarity-flip the sparse neuron covers to remove, strengthen, or reverse the classification — all with matched-control validation and bit-exact patch-back recovery" | LICENSED |
| "We can shift the model's output-distribution likelihood via output-side component steering" | LICENSED PARTIAL (directional evidence; Stage 27K mean lift +0.5576, delta over matched random +0.8502; eraser-suppression channel strongest at +0.8223 mean lift / 69.6% positive share; preregistered row-consistency gate not yet passed, p = 0.3444. Calibrated per-class steering is the next gate.) |
| "We can steer the model's generated language at full row-consistency cleanliness" | NOT LICENSED (Stage 27K GREY result; calibrated per-class/per-row gain tuning required for clean PASS) |
| "We can read the model's mind in arbitrary natural-language detail" | NOT LICENSED (typed class granularity only) |
| "Validated for production use at frontier scale" | NOT LICENSED (highest validated scale is 2.8B) |
| "Universal interpretability platform" | NOT LICENSED (three families ≠ universal) |
| "Single-neuron monosemantic localization" | NOT LICENSED (sparse-cover granularity is the validated unit; individual neurons within the cover may carry additional structure not isolated) |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural

- Three architecture families validated (Pythia / GPT-NeoX lineage, OLMo / AI2 lineage, Qwen / Alibaba lineage). Llama, Mistral, Phi, Gemma untested but no longer load-bearing for the cross-architecture claim.
- Decoder-only transformers only. Encoder-only (BERT family) and encoder-decoder (T5 family) untested.
- Probes are per-model. Methodology transfers across architectures; trained probes do not.

### 9.2 Scale

- Validated up to 2.8B parameters. Frontier-tier models (7B+) untested.
- Closed-API models (Claude, GPT, Gemini) cannot be onboarded — CAS Harness requires hidden-state access. CAS Harness is open-weight only.

### 9.3 Modal

- Likelihood conditioning via η→ε prefix closed at five model points, three architecture families.
- **Output-side component-steering shows directional evidence but not clean row-consistency** (Stage 27K mean likelihood-margin lift +0.5576, delta over matched random +0.8502, row-consistency p = 0.3444). Eraser-suppression single-channel is the strongest observed (+0.8223 mean lift, 69.6% positive share). Calibrated per-class steering is the next preregistered gate; current claim is bounded as PARTIAL directional evidence, not clean control.
- Surface-text steering at small model scale (Pythia-160M) failed at the sampling-noise floor in earlier stages. Replication at 1B+ for surface-text tier remains an open boundary.

### 9.4 Per-Class

- Some cognitive classes carry more signal than others. Affective register systematically harder to read than Transcendent. Several blind-spot classes identified with readout-vs-model-side disambiguation available.

### 9.5 Granularity

- CAS reads at typed class granularity, not at arbitrary natural-language granularity.
- Causal localization is established at **two granularities**: head-level (necessity + sufficiency, matched-control validated) and **sparse MLP-neuron-cover level** (~1% of layer width, full bidirectional control: ablate / amplify / polarity-flip, all matched-control validated, bit-exact patch-back recovery).
- **Single-neuron monosemantic localization** is not claimed. The validated causal unit is the sparse cover, not the individual neuron. Standard sparse-autoencoder feature discovery was empirically tested and did not produce a sparse causal feature basis at this layer — the cover-based methodology took its place.

### 9.6 Evidence-Tier

- **Closed**: readout, readout-causal, likelihood-conditioning, factorization, framework-predictive, cross-architecture (three families), weight-geometry alignment, multi-layer trace, blind-spot detection, runtime-safe acceptance/suppression, mode-configurable verification, four-tier generation readiness, Evidence Packet schema + delivery, component-level necessity + sufficiency.
- **Open**: large-model scale (7B+), surface-text steering at scale, hidden-content detection at validated tier, Multi-Harness Composition coordinator, neuron-level localization.

---

## 10. Comparison Landscape

| System | Approach | Scope | CAS Harness Comparison |
|---|---|---|---|
| **Anthropic Neural Network Analysis (NLA)** | Joint AV + AR with RL reconstruction loss, natural-language descriptions | NLA: three sizes of one model family (Anthropic Claude — Haiku 3.5/4.5, Opus 4.6). **CAS Harness: five models across three independent architecture families.** | NLA produces natural-language descriptions admitted by Anthropic to sometimes be verifiably false ("confabulation"). CAS Harness produces typed classifications grounded in a published ontology with no confabulation tier. NLA is more flexible for discovery; CAS Harness is more auditable for compliance. The cross-vendor gap structurally absent in NLA is load-bearingly present in CAS Harness. |
| Linear probes (academic) | Classify activations; report accuracy | Single axis usually | CAS Harness adds causal validation, η → ε bridge for conditioning, framework-predictive diagnostics, multi-layer trace, Evidence Packet emission, cross-architecture validation, component-level necessity+sufficiency, runtime-safe verification stack. |
| SHAP / LIME / classical XAI | Feature-importance attribution input → output | Black-box compatible | CAS Harness reads internal structural cognitive properties; classical XAI is shallower but model-agnostic. |
| Causal scrubbing (Anthropic mech interp) | Formal hypothesis-graph causal claims | Mech-interp researchers only | CAS Harness's reserved-language tiered-claims discipline shares philosophy at different granularity. |
| TransformerLens / mechanistic interpretability | Open-source tooling | Researchers, not product | CAS Harness is a productized version with an a-priori cognitive framework + audit-grade output. |
| Black-box behavioral testing | Prompt-and-score evaluations | Any model, no internal access | Complementary, not competitive. |

---

## 11. IP & Legal Status

### 11.1 Existing IP

- **USPTO Provisional Patent Application #64/037,173** — covers the CAS framework primitives
- Mathematical foundation: Noetic Topos paper (journal submission in progress)

### 11.2 Methodology Filings (In-Process)

The following CAS Harness-specific mechanisms are candidates for separate IP filings; IP attorney consultation in progress:

1. The η → ε bridge as applied to foreign open-weight transformer models
2. The Evidence Packet schema + authenticated delivery surface
3. Framework-predictive preflight diagnostic methodology
4. Bi-agent audit-cycle methodology
5. Weight-geometry alignment methodology
6. Cross-architecture probe-transfer methodology
7. Multi-layer trace + readout-position blind-spot detection
8. Two-bridge hidden-content / suppression detection
9. Multi-Harness Composition architecture (planned, components proven)
10. CAS Verification Stack — runtime-safe acceptance/suppression
11. Verification Mode Selector + factor-consistent verifier
12. Generation Readiness Gate orchestrating policy methodology
13. Component-level causal localization with necessity + sufficiency tests

### 11.3 External Disclosure Status

This investor-facing document is distributed **only under executed NDA**. Recipients are not authorized to disclose, reproduce, or use any content beyond the scope of the executed agreement. Additional methodology depth is available under separate technical-disclosure NDA after initial evaluation.

---

## 12. Glossary

| Term | Definition |
|---|---|
| CAS | Cognitive Architecture System v7.7 — the underlying formal framework |
| CAS Harness | This product — cross-model interpretability and conditioning platform |
| CAS Native | Companion product — from-scratch transformer with CAS as primary architecture |
| η (eta) | Embedding map: structure → realization. The probe's role. |
| ε (epsilon) | Realization map: structure → tokens. Covering morphism per Proposition 5.6. |
| η → ε bridge | Two-pass mechanism: probe reads, realization writes, foreign model is conditioned via prefix attention |
| 10 Noetics | Canonical cognitive primitives: Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect |
| 4 Domains | Principled, Cognitive, Evaluative, Operational |
| 4 Registers | Transcendent, Analytical, Affective, Embodied |
| 7 Drives | Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose |
| 40 Elements | 10 Noetics × 4 Domains cross-product |
| 28 Foundations | 7 Drives × 4 Registers cross-product |
| Lacunarity | Factorization-quality measure (Var/Mean²); lower is cleaner |
| Fractal classifier | Iterated-operator orbit classifier |
| RPM chain | Realization-Prerequisite-Manifestation capability pathway |
| Proposition 5.6 | Noetic Topos theorem proving the counit ε's pullback is surjective |
| Evidence Packet | Per-inspection structured customer artifact |
| Verification Stack | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Three customer-configurable verification modes |
| Generation Readiness Gate | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Blind-spot detection | Per-class identification of model-side vs readout-position weakness |
| Weight-geometry alignment | Principal-angle measure between CAS subspace and model's output-weight row space |
| Cross-architecture transfer | Validation that the η → ε bridge replicates across independent architecture families |
| Hidden-content detection | Two-bridge comparison surfacing internal vs emitted content divergence |
| Component-level localization | Necessity + sufficiency tests identifying which architectural components carry the readout |

---

## Appendix A — One-Page Summary

**What is it?** A software service that looks inside any open-weight large language model, detects cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and surfaces what the model is internally computing but not emitting — with bit-identical Evidence Packet reproducibility a third party can verify.

**How does it work?** Two-pass forward inference: (1) probe reads CAS structure from foreign model's activations; (2) realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class. The full inference path is captured in a typed, audit-grade Evidence Packet.

**Why does this work?** The Noetic Topos paper's Proposition 5.6 proves the counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. The static-weight tier independently confirms this: CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099).

**What is proved today?** Fifteen closed evidence tiers across five open-weight models from three architecture families:
- Detection above text baseline (up to 90.6% on 28 classes, +30+ pp lift)
- Causally load-bearing readout (collapse to exact chance under ablation, five axes)
- Likelihood conditioning via η → ε bridge (effect strengthens across Pythia scales, replicates stronger on OLMo, reaches its highest observed value on Qwen2.5-1.5B: +0.7960 likelihood Δ, p = 2.92×10⁻¹²)
- Clean factorization (lacunarity 0.015 to 0.0016)
- Framework-predictive validity (four pre-registered predictions held)
- Output-weight geometric alignment (2.83× random, p = 0.0099)
- Multi-layer trace with blind-spot detection and readout-vs-model disambiguation
- Component-level causal localization at head-level with necessity AND sufficiency (matched-control validated)
- **Sparse MLP-neuron-cover causal localization with full bidirectional control** — ablate / amplify / polarity-flip, all 112/112 examples passing at p < 10⁻³³ with bit-exact patch-back recovery
- Runtime-safe accept/suppress at 87.6% / 99.78% accuracy
- Three customer-configurable verification modes (6/6 pre-registered targets met)
- Four-tier generation readiness policy
- 15-field Evidence Packet schema with authenticated delivery
- Two-bridge hidden-content detection prototype
- Cross-architecture replication at three independent families
- Methodology discipline (pre-registration, locked artifacts, matched controls, honest NULLs)

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, and not language-specific** — three independent labs (EleutherAI, AI2, Alibaba), three corpora, three tokenizer families.

**What is the bounded claim today?** CAS Harness reads, validates, conditions, and emits audit-grade structural evidence for open-weight large language models up to 2.8B parameters across three architecture families. Component-level causal localization is established at head granularity. Surface-text steering at small model scale and exact neuron-level localization remain open boundaries, with planned methodological extensions disclosed in this document.

**Where to go from here?** Additional methodology depth available under separate technical-disclosure NDA after initial evaluation. Inquiries: contact founder via the agreement-specified channel.

---

*End of investor-facing specification. Confidential, NDA-Gated, 2026-05-21.*
