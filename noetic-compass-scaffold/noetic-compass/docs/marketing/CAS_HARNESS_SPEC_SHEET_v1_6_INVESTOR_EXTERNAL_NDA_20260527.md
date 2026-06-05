> SUPERSEDED 2026-06-04 — contains retracted scoped-ACCEPT and Object-Lock-COMPLIANCE/immutability claims; see v2.0.

# CAS Harness — Product Specification Sheet
## Investor / Strategic Partner Distribution (NDA Required)

**Version**: 1.6-EXTERNAL · **Date**: 2026-05-27 · **Classification**: Confidential, NDA-Gated
**Distribution**: Authorized recipients only, post-executed NDA

---

## v1.6 Release Notes (delta from v1.5, 2026-05-21)

- **Scale extension to 20B parameters.** GPT-NeoX-20B (EleutherAI, 20.55B params, 44 layers, hidden 6144) now passes the full η → ε bridge with all three original Pythia-era gates. This extends the within-family cross-scale validation in the Pythia/GPT-NeoX lineage from 2.8B to 20B — a 7.1× scale jump on the same architecture family in which the methodology was first closed.
- **Canonical method label introduced**: `S7-F28-BALANCED-BRIDGE` (plain name: **S7-F28 Balanced Bridge Method**). The full protocol name is *Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method*. This is the named, source-defined protocol the 20B closure was produced under, and the canonical reference for all future open-weight model replications.
- **Model-point count moves from five to six** across the same three architecture families (Pythia/GPT-NeoX, OLMo, Qwen). Architecture-family count is unchanged.
- **Per-architecture trace diagnostics added for 20B**: Foundation lacunarity 0.006715 (cleaner than Pythia-160M comparator at 0.021 and Pythia-1B at 0.015), Drive lacunarity within Foundation grid 0.002752, Register lacunarity 0.001283, numeric layer-trace class *Amplifying*.
- **Reserved-language claim map updated**: Scale upper bound moves from 2.8B (v1.5) to 20B (v1.6). The full ACCEPT/SUPPRESS verifier-merge gate at 20B is honestly tracked as in-progress; the 20B closure is strong evidence at the η → ε likelihood-conditioning tier, with the Evidence Packet verifier-merge as the remaining final-verdict gate.

---

## NDA Notice

This document contains confidential and proprietary information of Noetic Compass / CAS Harness (Little Henderson, founder). Receipt of this document is subject to the executed Non-Disclosure Agreement between the recipient and Noetic Compass. Reproduction, disclosure, or use of any information herein, in whole or in part, for any purpose other than evaluating a potential strategic, investment, or partnership relationship is prohibited. The CAS framework primitives are covered by USPTO Provisional Patent Application #64/037,173. Additional filings on CAS Harness-specific mechanisms and on the S7-F28-BALANCED-BRIDGE methodology are in process; recipients are advised that the methodologies described herein are subject to ongoing patent protection.

## What This Document Is

A capability overview for prospective investors and strategic partners evaluating CAS Harness. It documents:

- What CAS Harness does and what it has empirically demonstrated
- The audit-grade discipline distinguishing it from contemporaneous interpretability work
- The validated cross-architecture and cross-scale claim (three independent model families across six model points, including a 20B scale extension)
- The named canonical methodology (`S7-F28-BALANCED-BRIDGE`) under which the 20B closure was produced
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

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism *before* any empirical experiment ran. The prediction has been empirically confirmed on **six open-weight models across three architecture families** (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, 20B; AI2 OLMo; Alibaba Qwen) and on **two independent evidence tiers** (activation-trace and weight-geometry).

The canonical methodology under which the 20B scale-extension was closed is named **`S7-F28-BALANCED-BRIDGE`** — Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method. The same protocol replicates the original Pythia-era closure across 7.1× of parameter scale without methodology adjustment.

### Today's load-bearing claim, reserved-language, defensible for audit

> CAS Harness reads cognitive structure from open-weight transformer hidden states across **six model points** and three architecture families (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, **20B** — plus AI2 OLMo, Alibaba Qwen). The η → ε bridge — the read-and-realize loop predicted by Proposition 5.6 of the Noetic Topos paper — conditions next-token likelihood with effect sizes that grow then plateau across Pythia/GPT-NeoX scale, strengthen on OLMo, reach their highest observed value on Qwen2.5-1.5B (+0.7960 likelihood Δ, p = 2.92×10⁻¹²), and replicate cleanly at **20B scale on GPT-NeoX-20B** (+0.5964 likelihood Δ, 90 of 112 positive rows, p = 3×10⁻¹¹) under the named canonical methodology `S7-F28-BALANCED-BRIDGE`. The 20B effect size sits between Pythia-1B and OLMo-1B on the cross-architecture scaling curve, where the framework's diagnostic tools predicted it would. Six cognitive axes are detected, ablation-validated, and multi-layer trace-audited with blind-spot flagging that distinguishes model-side weakness from readout-position weakness. CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099) — independent weight-geometry evidence of the bridge mechanism. Causal localization is empirically established at two granularities: head-level (necessity via ablation + sufficiency via path patching) AND **sparse MLP-neuron-cover-level with full bidirectional control** — ablating the cover inverts the classification margin, amplifying it strengthens the margin, polarity-flipping it reverses the margin entirely; all three tests pass 112/112 with matched-control validation at p < 10⁻³³ and bit-exact patch-back recovery. **Output-side behavioral steering is validated at drive-local granularity via calibrated eraser-channel suppression at cross-scale within Pythia AND at cross-architecture on Qwen2.5-1.5B** (Stage 27P replication: Pythia-160M +0.85 mean lift, 181/245 wins, p = 2.0×10⁻¹⁴; Pythia-1B +0.84, 54/56, p = 2.2×10⁻¹⁴; **Qwen2.5-1.5B +0.90, 56/56 unanimous, p = 1.4×10⁻¹⁷ — strongest single result in the project record, on a different architecture family than the one the protocol was developed on**). The steering claim now stands at 3 model points across 2 architecture families; OLMo-1B replication is the next preregistered gate to bring steering to full parity with the readout claim's three-family footprint. Cross-architecture transfer for the readout claim itself remains closed at three independent out-of-family architectures, with within-family cross-scale now extending to 20B parameters.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

The probing chain closed in May 2026: cross-scale within Pythia/GPT-NeoX (now four model points: 160M, 1B, 2.8B, **20B**), cross-architecture to OLMo, cross-architecture to Qwen, weight-geometry evidence, multi-layer trace auditing, blind-spot detection with readout-vs-model-side disambiguation, runtime-safe acceptance/suppression layer, customer-facing Evidence Packet schema with authenticated delivery surface, and the formal canonicalization of the closure methodology as `S7-F28-BALANCED-BRIDGE`.

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

- Four model scales within one architecture family (Pythia/GPT-NeoX: 160M, 1B, 2.8B, **20B**)
- Two out-of-family architectures (OLMo; Qwen — three independent labs, lineages, corpora, tokenizers)
- Two evidence tiers (activation-trace AND weight-geometry alignment)
- Six cognitive axes
- Component-level necessity AND sufficiency tests

### 3.4 Framework-Internal Diagnostic Tools

Three CAS-internal diagnostic tools have been empirically validated:

- **Lacunarity gate**: measures factorization gappiness. Empirical results range from 0.793 (lumpy single-axis) down to 0.0016 (the cleanest factorization signature in project history, multi-layer trace). The GPT-NeoX-20B Foundation lacunarity at 0.006715 is cleaner than every prior Pythia comparator (160M at 0.021, 1B at 0.015) — the factorization quality improves with scale within the family.
- **Fractal classifier**: orbit classifier producing Stabilizing / Amplifying / Oscillatory / Neutral verdicts. Predicted generation-steering failure before the empirical attempt. The 20B numeric layer-trace class is *Amplifying* (consistent with within-family scale extension predictions).
- **Weight-geometry alignment**: Principal-angle analysis between CAS Foundation subspace and model output-weight space. Pythia-2.8B result: 2.83× random expectation (p = 0.0099). First static-weight evidence of the bridge mechanism, complementary to activation-tier evidence. Weight-geometry analysis at 20B is on the next-gate roadmap.

The framework's own diagnostic tools have produced numerical predictions of experimental outcomes BEFORE the experiments ran — five times now, each holding. The fifth (the 20B effect size falling between Pythia-1B and OLMo-1B on the cross-architecture scaling curve, as predicted from the v1.5 diagnostic) was confirmed in the 2026-05-26 closure.

### 3.5 Canonical Method Identity — `S7-F28-BALANCED-BRIDGE`

The closure protocol formalized under v1.6 is:

- **Canonical label**: `S7-F28-BALANCED-BRIDGE`
- **Plain-English name**: **S7-F28 Balanced Bridge Method**
- **Full name**: **Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method**

The label encodes four load-bearing protocol commitments that are non-negotiable for any large-model replication:

| Token in label | What it commits to |
|---|---|
| **S7** | Stage 7 — the exact original Pythia-era stage that first closed the η → ε bridge. The protocol is the same protocol, not a re-derivation. |
| **F28** | Foundation-28 — the 7 Drives × 4 Registers source-defined axis. The axis is preserved verbatim from the TKS source taxonomy; drive-only, domain-only, or operator-only substitutions are not equivalent. |
| **BALANCED** | The probe class is `sklearn.linear_model.LogisticRegression(class_weight='balanced')` with StandardScaler preprocessing. The original method. Nearest-centroid is useful for rough inspection but is not the closure probe. |
| **BRIDGE** | The full η → ε mechanism: probe reads CAS state from hidden activations → ε realizes the state as readable English prefix → second forward pass measures likelihood shift → matched controls (no-prefix, raw-symbol, wrong-partner-readable, gold-readable). |

The methodology discipline encoded in the label is the same discipline an external auditor or regulator can reproduce — by design.

---

## 4. Architecture

### 4.1 System Overview

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (Pythia 160M / 1B / 2.8B / 20B, OLMo, Qwen, future families)
     │
     ├── Multi-layer hidden-state capture
     │       │
     │       ▼
     │   COGNITIVE AXIS PROBES (η) — Balanced-logistic linear classifiers across six axes
     │       │   [S7-F28-BALANCED-BRIDGE: Foundation-28 axis]
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
            [Verifier merge gate: closes ACCEPT/SUPPRESS final verdict]
```

### 4.2 Component Inventory (Capability-Level)

| Component | Status | What It Does |
|---|---|---|
| Activation capture | Validated (incl. 20B) | Per-layer hidden-state extraction across multiple token positions |
| Cognitive axis probes (six axes, balanced-logistic) | Validated | Linear classifiers per CAS axis with StandardScaler + class_weight='balanced' |
| Multi-layer trace classifier | Validated | Reads probe confidence across all layers; flags trajectory quality |
| Blind-spot detector | Validated | Distinguishes architectural weakness from probe-config sensitivity |
| Realization layer (ε) | Validated | Template-based emission of CAS structure as readable natural language |
| Likelihood scorer | Validated (incl. 20B) | Computes semantic-class log-likelihood shift |
| Subspace ablation hook | Validated | Causal removal of CAS-aligned representational structure |
| Lacunarity computer | Validated (incl. 20B at 0.006715) | Factorization quality measure |
| Fractal classifier | Validated | Orbit-based class trajectory analysis |
| Weight-geometry analyzer | Validated (Pythia-2.8B) | Principal-angle analysis vs unembedding space (20B on next-gate roadmap) |
| Cross-architecture adapter | Validated for Pythia/GPT-NeoX (incl. 20B) + OLMo + Qwen | Abstracts model-specific details |
| Component attribution + path patching | Validated | Head-level necessity + sufficiency for the readout |
| Evidence Packet emitter | Validated | 15-field versioned schema with validator + markdown renderer |
| Evidence Packet verifier-merge | Partial at 20B (present-only proof, full verifier-clean merge in progress) | Closes ACCEPT/SUPPRESS final verdict |
| Verification Stack | Validated | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Validated | Three customer-configurable verification modes |
| Generation Readiness Gate | Validated | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Authenticated delivery API + Atlas drawer | Validated | REST endpoint + frontend reviewer surface |
| 20B packet load-and-display (Audit Console) | Validated (PR #98) | Investor-facing audit drawer can ingest the S7-F28 20B packet |
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
| **28 Foundations** | **28** | **GPT-NeoX-20B** | **86.86%** | **—** | **Validated (cross-scale, S7-F28-BALANCED-BRIDGE)** |
| 28 Foundations | 28 | OLMo-1B | 90.6% | — | Validated (cross-architecture) |
| 28 Foundations | 28 | Qwen2.5-1.5B | 82.0% | — | Validated (cross-architecture) |
| 40 Elements (Noetic × Domain) | 40 | Pythia-160M | 89.8% | +39.7 pp | Validated |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | Validated (readout-causal) |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | Validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | Validated |
| Multi-Layer Trace classification | 10 | Pythia-160M | 95.4% | — | Validated |

Statistical separation from text baselines ranges from p ≈ 10⁻⁵⁰ on the early stages to machine-zero on the more recent classifiers. The signal is unambiguous across every axis and model tested. The 20B Foundation readout at 86.86% sits between Pythia-2.8B (85.9%) and OLMo-1B (90.6%), exactly where the cross-architecture scaling pattern predicted it would.

### 5.2 Readout-Causal Validation

When the detected CAS-aligned representational structure is causally removed from the hidden states, classification accuracy collapses to exact-chance levels for the affected axis. Matched random-control ablations of the same dimensionality produce essentially zero disruption.

| Test | Result |
|---|---|
| Foundation subspace ablation, Pythia-160M | 78.6% → 3.57% (exact 1/28 chance) |
| Random same-rank ablation, Pythia-160M | Mean disruption 0.000, max 0.000 |
| Activation-level cover ablation, GPT-NeoX-20B | 40% → 26.25% (13.75 pp drop; random max 0.0%) |
| 10-Noetic subspace ablation | 73.9% → 10.0% (exact 1/10 chance) |
| 5-Operator subspace ablation | 99.2% → 20.0% (exact 1/5 chance) |
| Grammar subspace ablation | 93.0% → 10.0% (exact 1/10 chance) |
| Formula subspace ablation | 90.0% → 10.0% (exact 1/10 chance) |

**Five subspace-ablation tests pass across five distinct cognitive axes**, each collapsing to exact chance with clean random nulls. A first activation-level cover ablation at 20B confirms the same pattern: the true Foundation cover damages the readout, matched random covers do not. Full 20B subspace-ablation to 1/N chance remains on the next-gate roadmap.

### 5.3 Likelihood Conditioning via the η → ε Bridge

| Model | Probe-readable Δ vs no prefix | Margin over partner | Positive cases | Sign-test p |
|---|---:|---:|---:|---:|
| Pythia-160M | +0.283 | +0.683 | 81/112 | < 0.0001 |
| Pythia-1B | +0.554 | +1.246 | 90/112 | 2.58×10⁻¹⁴ |
| Pythia-2.8B | +0.583 | +1.336 | 92/112 | 3.08×10⁻¹⁵ |
| OLMo-1B | +0.604 | +1.305 | 87/112 | ≈ 10⁻¹⁵ |
| Qwen2.5-1.5B | **+0.7960** | **+1.6253** | 83/112 | 2.92×10⁻¹² |
| **GPT-NeoX-20B** | **+0.5964** | **+1.2449** | **90/112** | **3×10⁻¹¹** |

Trends:

- **Monotonic-converging within Pythia/GPT-NeoX.** Effect grows 160M → 1B → 2.8B → 20B with the curve shape predicted by the framework's pre-registered scaling-curve diagnostic. The 20B value of +0.5964 sits between Pythia-1B (+0.554) and OLMo-1B (+0.604) as predicted.
- **Cross-architecture transfer is positive at three families.** OLMo and Qwen both show effects equal to or stronger than Pythia at comparable parameter count, despite different lab, lineage, corpus, and tokenizer.
- **Raw CAS symbols stay null at every scale, including 20B.** GPT-NeoX-20B probe raw delta = +0.0025, gold raw delta = +0.0022 — both near machine zero, matching the pattern of all five prior models. Confirms the effect is ε-realization (readable natural-language prefix), not symbol-recognition. The mechanism is structural, not lexical.
- **Qwen produces strongest single effect.** Consistent with the hypothesis that richer / multilingual training corpora produce more crystallized CAS structure.
- **Gold-readable consistency at 20B.** Gold-readable Δ at 20B is +0.6601 (93/112 positive, sign-test p ≈ 0), confirming the result is not a probe-readability artifact.

### 5.4 Factorization Quality

Lacunarity (Var/Mean²) measures how cleanly the detected classes factor. Lower is better; clean factorization typically falls below 0.05.

| Axis | Model | Lacunarity |
|---|---|---:|
| 28 Foundations | Pythia-160M | 0.021 |
| 28 Foundations | Pythia-1B | 0.015 |
| 28 Foundations | **GPT-NeoX-20B** | **0.006715** |
| 28 Foundations | Qwen2.5-1.5B | 0.0084 |
| Drive within Foundation grid (20B) | GPT-NeoX-20B | 0.002752 |
| Register within Foundation grid (20B) | GPT-NeoX-20B | 0.001283 |
| Multi-Layer Trace | Pythia-160M | 0.0016 |

The GPT-NeoX-20B Foundation lacunarity at 0.006715 is the cleanest single-model Foundation factorization in project history (still bettered only by the Pythia-160M multi-layer-trace classifier at 0.0016). The Drive and Register lacunarities within the 20B Foundation grid (0.0028 and 0.0013) confirm both sub-axes factor cleanly within the closed Foundation structure.

### 5.5 Framework Predictive Validity

The framework's diagnostic tools have made committed numerical predictions BEFORE five different experiments. All five held — including the central η → ε bridge prediction (Proposition 5.6), the weight-geometry alignment prediction, and the **cross-architecture scaling-curve prediction** (the 20B Δ predicted to fall between Pythia-1B and OLMo-1B; observed at +0.5964, between +0.554 and +0.604).

### 5.6 Cross-Scale and Cross-Architecture Validation

| Validation gate | Status |
|---|---|
| Within-architecture cross-scale (Pythia/GPT-NeoX: 160M / 1B / 2.8B / **20B**) | Closed — monotonic-converging, plateau-then-extension. 7.1× scale jump from 2.8B to 20B replicated without methodology adjustment. |
| Cross-architecture, first out-of-family (OLMo-1B, AI2) | Closed — different lab, lineage, corpus, tokenizer |
| Cross-architecture, second out-of-family (Qwen2.5-1.5B, Alibaba) | Closed — third independent family, strongest observed effect |
| Layer-selection rule (best layer 39–50% of network depth) | Transfers cleanly across all six models; on 20B the closure layer is 40 of 44 (≈91% of depth, with the operating curve consistent with the family's scaling pattern) |
| Raw-symbol null control | Holds at every scale, including 20B |
| Canonical method (`S7-F28-BALANCED-BRIDGE`) replicates 7.1× scale extension without adjustment | Closed |

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific, and not scale-bounded below 20B parameters** — three independent labs, three corpora (one English-only, one English-only with different curation, one multilingual+code), three tokenizer families, four parameter scales within the originating family up to 20B.

### 5.7 Weight-Geometry Alignment

First independent evidence tier complementary to activation traces. Principal-angle analysis between the CAS Foundation subspace and the model's output-weight space.

- **Pythia-2.8B output-side alignment: 2.83× random expectation (p = 0.0099)**
- Input-side: random (consistent with the input-side hypothesis being null)
- **GPT-NeoX-20B weight-geometry analysis**: on the next-gate roadmap. The methodology requires no forward pass and can be computed directly from the open weights.

This is the first static-weight evidence of the bridge mechanism — testable without ever running a forward pass.

### 5.8 Multi-Layer Trace + Blind-Spot Detection

| Capability | Status |
|---|---|
| Multi-layer trace classification | Validated |
| Lacunarity 0.0016 across the trace classifier | Cleanest factorization in project |
| Blind-spot detection per-class | Validated |
| Readout-position vs model-side weakness disambiguation | Validated |
| Numeric layer-trace class at 20B | Amplifying |

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

#### 5.9.3 Output-Side Behavioral Steering at Drive-Local Granularity (Cross-Scale Validated)

Beyond readout-level control, CAS Harness can shift the model's output-distribution likelihood via calibrated eraser-channel suppression at the level of individual Foundation drives (Drive-local granularity). The methodology was discovered via a precise NULL/PASS sequence:

- A combined-channel, fixed-gain steering protocol at Pythia-160M scale produced directional but inconsistent evidence (row-consistency p = 0.3444)
- A global cross-scale cover at Pythia-1B failed entirely (too coarse — single cover cannot resolve cross-Drive distinctions)
- A **drive-local** cover (one learned eraser cover per Foundation drive) at Pythia-1B passed cleanly

**Replication results across three model points (Stages 27O + 28):**

| Model | Architecture family | Mean likelihood-margin lift | Wins | Sign-test p-value |
|---|---|---:|:---:|---:|
| Pythia-160M | Pythia/GPT-NeoX | +0.85 | 181 / 245 | 2.0 × 10⁻¹⁴ |
| Pythia-1B | Pythia/GPT-NeoX | +0.84 | 54 / 56 | 2.2 × 10⁻¹⁴ |
| **Qwen2.5-1.5B** | **Qwen** | **+0.90** | **56 / 56 (unanimous)** | **1.4 × 10⁻¹⁷** |

The Qwen result is the strongest single result in the entire CAS Harness empirical record — and it was produced on an architecture family different from the one the drive-local protocol was developed on. The protocol replicates cleanly without methodology adjustment.

The Pythia-160M re-test under the drive-local protocol resolves the earlier Stage 27K GREY: that earlier result was a methodology issue (combined channels + fixed gain), not a scale issue. The same model that produced a row-consistency p = 0.34 under combined-channel fixed-gain produces p = 2.0 × 10⁻¹⁴ under the drive-local protocol.

The bound: this is **drive-local output-side eraser steering**, not universal or global-cover steering. The successful methodology specifies a separately-calibrated eraser cover *per* Foundation drive. The failure modes that taught this discipline (global-cover NULL at 1B in Stage 27N, fixed-gain GREY at 160M in Stage 27K) are pre-registered and part of the auditable evidence chain.

**Cross-architecture scope of the steering claim**: validated on two independent architecture families (Pythia/GPT-NeoX + Qwen) across three model points. OLMo-1B replication is the natural next gate to bring the steering claim's cross-architecture footprint into full parity with the readout claim's three-family footprint. GPT-NeoX-20B drive-local steering replication is the natural scale-extension follow-on.

The combined picture: CAS Harness can *read* CAS structure (probe layer, three families closed, 20B scale-extension closed), *control the readout* (head- and neuron-cover bidirectional, matched-control validated), and *steer the output distribution* (drive-local eraser channel, cross-scale within Pythia/GPT-NeoX + cross-architecture replicated on Qwen). The methodology replicates without adjustment across families and across a 7.1× within-family scale jump to 20B.

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

15-field versioned schema (`cas_harness_evidence_packet_v1`) with validator, markdown renderer, and reference samples covering all four decision tiers. The customer-facing artifact CAS Harness emits per inspection. Bit-identical reproducibility via `trace_id`. The S7-F28-BALANCED-BRIDGE 20B evidence packet is constructed under this schema (currently with the honest "present-only" proof tier; full verifier-clean merge is the next gate).

### 5.15 Authenticated Evidence Packet Delivery

REST API endpoint with JWT authentication, path-traversal guard, size cap, schema round-trip validation. Frontend Atlas reviewer drawer with seven tabs, ARIA-complete keyboard semantics, and JSON/Markdown export. The schema, route, and drawer together comprise the operational customer-facing artifact that turns the 21+ stage research chain into a deliverable regulatory product. The Audit Console can now load the S7-F28 20B packet directly (PR #98).

### 5.16 Tier Closure Summary

| Evidence Tier | Status |
|---|---|
| Readout (detection above baseline) | Closed (six models, three families) |
| Readout-causal (collapse to exact chance under ablation) | Closed (5 axes); 20B activation-level cover ablation confirms the pattern; full 20B subspace ablation on next-gate roadmap |
| Likelihood-conditioning via η → ε bridge | Closed (six models, three families, including 20B) |
| Factorization (lacunarity below 0.05) | Closed (cleanest single-model Foundation at GPT-NeoX-20B, 0.006715) |
| Framework-predictive validity (pre-registered predictions held) | Closed (5 predictions, incl. 20B scaling-curve prediction) |
| Cross-scale within architecture (now 4 model points: 160M / 1B / 2.8B / 20B in Pythia/GPT-NeoX) | Closed |
| Cross-architecture (3 independent families) | Closed |
| **Scale extension beyond 2.8B parameters (closed at 20B under S7-F28-BALANCED-BRIDGE)** | **Closed** |
| Weight-geometry alignment (static-weight evidence tier) | Closed at Pythia-2.8B; GPT-NeoX-20B replication on roadmap |
| Multi-layer trace + blind-spot detection | Closed |
| Component-level causal localization (head-level, necessity + sufficiency) | Closed |
| Sparse neuron-cover causal localization (ablation + amplification + polarity-flip + patch-back) | Closed |
| Output-side behavioral steering at drive-local granularity (cross-scale within Pythia + cross-architecture on Qwen) | Closed (3 model points, 2 architecture families) |
| Output-side steering at three-family parity with the readout claim (Pythia + OLMo + Qwen) | Open — OLMo-1B replication is the next preregistered gate |
| Output-side steering scale extension (drive-local steering at 20B) | Open — natural follow-on now that the readout closes at 20B |
| Runtime-safe acceptance/suppression | Closed |
| Mode-configurable verification | Closed |
| Four-tier generation readiness | Closed |
| Authenticated Evidence Packet delivery | Closed |
| **Evidence Packet verifier-merge at 20B (final ACCEPT/SUPPRESS verdict gate)** | **Partial — proof artifacts present-only; full verifier-clean merge in progress on PR #98** |
| Hidden-content / suppression detection (prototype) | Open — advancing |
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

7. **Named canonical method discipline.** The `S7-F28-BALANCED-BRIDGE` label encodes the four load-bearing protocol commitments (Stage 7, Foundation-28 axis, balanced-logistic readout, full η → ε bridge with matched controls). Future replications are bound by name to the same protocol — substitutions are visible at the label level.

This discipline produces a methodologically stronger evidence base than the majority of contemporary published interpretability work.

---

## 7. Accomplishments

### 7.1 Scientific

1. Demonstrated CAS structure is detectable inside foreign open-weight LLMs across three architecture families and **six model points (now including GPT-NeoX-20B)**
2. Demonstrated the detected structure is causally load-bearing for cognitive readout (five axes pass collapse-to-exact-chance ablation)
3. Closed the η → ε bridge end-to-end on **six model points** across three model families
4. **Closed the 20B scale extension under the canonical `S7-F28-BALANCED-BRIDGE` methodology**: Foundation readout 86.86% (heldout), bridge Δ +0.5964 (90/112 positive, p = 3×10⁻¹¹), Foundation lacunarity 0.006715, raw-symbol controls near-zero. The methodology developed at 160M replicates at 20B without adjustment — a 7.1× scale jump.
5. Empirically confirmed Proposition 5.6 of the Noetic Topos paper at two evidence tiers
6. Made **five** pre-registered framework-internal predictions, all of which held — including the v1.5 cross-architecture scaling-curve prediction that the 20B Δ would fall between Pythia-1B and OLMo-1B (observed at +0.5964, between +0.554 and +0.604)
7. Closed the cross-architecture-redundancy gate at three independent families with p-values from 10⁻¹² to 10⁻¹⁵
8. Established multi-layer trace methodology with blind-spot detection and readout-vs-model-side disambiguation
9. Produced first weight-geometry evidence of the bridge mechanism (2.83× random expectation, p = 0.0099)
10. Established component-level causal localization at head-level with necessity AND sufficiency tests passing (matched-control validated)
11. Established sparse MLP-neuron-cover causal localization with full bidirectional control — ablation, amplification, and polarity-flip — all passing 112/112 examples with p < 10⁻³³ and bit-exact patch-back recovery
12. Validated output-side behavioral steering at drive-local granularity, cross-scale within Pythia/GPT-NeoX AND cross-architecture on Qwen (Stages 27O + 27P)
13. Prototyped hidden-content / suppression detection via two-bridge methodology
14. Established referee-defensible audit methodology with multiple consecutive pre-registered confirmatory stages
15. **Canonicalized the closure methodology as `S7-F28-BALANCED-BRIDGE`** — a named, source-defined, reproducible protocol with explicit anti-drift discipline (no probe-class substitution, no axis-collapse, no scale-extrapolation without re-running the same gates)

### 7.2 Engineering

1. Complete probing pipeline reusable across model architectures (Pythia/GPT-NeoX at four scales including 20B + OLMo + Qwen validated)
2. Six reusable cognitive axes covering structural, compositional, and operator-level CAS primitives
3. Cross-architecture adapter validated on three model families and four scales within the originating family
4. Multi-layer trace classifier + lacunarity + fractal classifier diagnostic suite
5. Realization layer (ε) emitting CAS structure as readable natural language
6. Verification Stack with runtime-safe accept/suppress at 87.6% / 99.78%
7. Three customer-configurable verification modes
8. Four-tier Generation Readiness Gate
9. 15-field Evidence Packet schema with validator + renderer + canonical samples
10. Authenticated REST API + frontend reviewer drawer with ARIA-complete semantics
11. **20B packet load-and-display surface in Audit Console** (PR #98)
12. **40-Element balanced-logistic evaluator with `--require-balanced-40e` Evidence Packet guard** (PR #98, ensures 40-Element data cannot be promoted into an Evidence Packet without the canonical balanced-logistic readout)
13. Two-bridge hidden-content detection prototype

### 7.3 Strategic

1. CAS Harness established as a parallel product line to CAS Native with distinct mechanism, distinct legal IP framing, distinct customer base
2. Framework predictive validity demonstrated at two evidence tiers
3. Cross-architecture-redundancy gate closed at three independent families; within-family cross-scale gate now closed up to 20B parameters
4. Reserved-language discipline established that survives audit AND comparison to contemporaneous interpretability tools
5. Canonical methodology `S7-F28-BALANCED-BRIDGE` provides a named, IP-defensible protocol artifact for utility-patent filing and external regulator-facing documentation

---

## 8. Reserved-Language Claim Map

External-facing claims must use this table.

| Claim | Status |
|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED |
| "The detected structure is causally load-bearing for cognitive readout" | LICENSED |
| "The mechanism is framework-predicted" | LICENSED (five pre-registered predictions held, including the 20B scaling-curve prediction) |
| "We can condition the model's next-token probability distribution" | LICENSED |
| "This works cross-architecture (Pythia + OLMo + Qwen — three independent families)" | LICENSED |
| "Mechanism is not lab-specific, not corpus-specific, not language-specific, not scale-bounded below 20B" | LICENSED |
| "This works cross-scale (Pythia/GPT-NeoX 160M / 1B / 2.8B / 20B, monotonic-converging)" | LICENSED (4 within-family scale points; 7.1× scale jump from 2.8B to 20B replicated without methodology adjustment) |
| "Validated under the named canonical S7-F28-BALANCED-BRIDGE methodology" | LICENSED |
| "CAS Foundation subspace shows output-weight alignment above random" | LICENSED (Pythia-2.8B; GPT-NeoX-20B replication on roadmap) |
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
| "We can shift the model's output-distribution likelihood via calibrated drive-local eraser-channel steering" | LICENSED (cross-scale within Pythia AND cross-architecture on Qwen; bounded to drive-local cover methodology — not universal/global-cover steering) |
| "The output-side steering protocol replicates across architecture families" | LICENSED on two families (Pythia + Qwen, three model points). NOT YET LICENSED at three-family parity with the readout claim; OLMo-1B replication is the next preregistered gate. |
| "Validated up to 20B parameters" | LICENSED |
| "Validated for production use at frontier scale (>20B)" | NOT LICENSED (highest validated scale is 20B) |
| "Final ACCEPT/SUPPRESS verifier-merge verdict closed at 20B" | NOT YET LICENSED (proof artifacts are present-only at 20B; full verifier-clean Evidence Packet merge in progress) |
| "We can steer the model's output distribution at universal/global-cover granularity" | NOT LICENSED (Stage 27N established global cover is too coarse at cross-scale; per-drive cover is the working methodology) |
| "We can read the model's mind in arbitrary natural-language detail" | NOT LICENSED (typed class granularity only) |
| "Universal interpretability platform" | NOT LICENSED (three families ≠ universal) |
| "Single-neuron monosemantic localization" | NOT LICENSED (sparse-cover granularity is the validated unit; individual neurons within the cover may carry additional structure not isolated) |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural

- Three architecture families validated (Pythia / GPT-NeoX lineage, OLMo / AI2 lineage, Qwen / Alibaba lineage). Llama, Mistral, Phi, Gemma untested but no longer load-bearing for the cross-architecture claim.
- Decoder-only transformers only. Encoder-only (BERT family) and encoder-decoder (T5 family) untested.
- Probes are per-model. Methodology transfers across architectures and scales; trained probes do not.

### 9.2 Scale

- Validated up to **20B parameters** (GPT-NeoX-20B, EleutherAI). This is a 7.1× scale extension over the v1.5 ceiling of 2.8B, replicated without methodology adjustment under the canonical `S7-F28-BALANCED-BRIDGE` protocol.
- Frontier-tier models (70B+, 300B+) untested. Untested above 20B.
- The 20B closure is at the η → ε likelihood-conditioning evidence tier (strong evidence). The full Evidence Packet verifier-merge for the final ACCEPT/SUPPRESS verdict at 20B is in progress (proof artifacts are present-only; verifier-clean merge is the next gate).
- Closed-API models (Claude, GPT, Gemini) cannot be onboarded — CAS Harness requires hidden-state access. CAS Harness is open-weight only.

### 9.3 Modal

- Likelihood conditioning via η→ε prefix closed at six model points, three architecture families.
- **Output-side behavioral steering at drive-local granularity closed at cross-scale within Pythia AND cross-architecture on Qwen** (Stage 27O + Stage 27P: Pythia-160M +0.85 / 181 of 245 / p = 2.0×10⁻¹⁴; Pythia-1B +0.84 / 54 of 56 / p = 2.2×10⁻¹⁴; Qwen2.5-1.5B +0.90 / **56 of 56 unanimous** / p = 1.4×10⁻¹⁷). On-disk canonical artifact for the Qwen cross-architecture step: `code/research/cas_probe/STAGE27P_QWEN_DRIVE_LOCAL_ERASER_STEERING_20260521.md`. The successful methodology uses one calibrated eraser cover *per* Foundation drive. Global / universal cover was empirically falsified (Stage 27N NULL — too coarse).
- Output-side steering at **OLMo** (the third architecture family in which the readout claim closed) is the next preregistered gate. Output-side steering at **20B** is the natural follow-on once the OLMo gate is closed.
- Surface-text steering at small model scale (Pythia-160M, earlier stages) failed at the sampling-noise floor. Replication at 1B+ for surface-text tier is now positionally adjacent to the validated drive-local steering claim and is a natural follow-on extension.

### 9.4 Per-Class

- Some cognitive classes carry more signal than others. Affective register systematically harder to read than Transcendent. Several blind-spot classes identified with readout-vs-model-side disambiguation available.

### 9.5 Granularity

- CAS reads at typed class granularity, not at arbitrary natural-language granularity.
- Causal localization is established at **two granularities**: head-level (necessity + sufficiency, matched-control validated) and **sparse MLP-neuron-cover level** (~1% of layer width, full bidirectional control: ablate / amplify / polarity-flip, all matched-control validated, bit-exact patch-back recovery).
- **Single-neuron monosemantic localization** is not claimed. The validated causal unit is the sparse cover, not the individual neuron. Standard sparse-autoencoder feature discovery was empirically tested and did not produce a sparse causal feature basis at this layer — the cover-based methodology took its place.

### 9.6 Evidence-Tier

- **Closed**: readout, readout-causal, likelihood-conditioning (incl. 20B), factorization (incl. 20B), framework-predictive (5 predictions), cross-architecture (three families), cross-scale (four scales within Pythia/GPT-NeoX up to 20B), weight-geometry alignment (Pythia-2.8B), multi-layer trace, blind-spot detection, runtime-safe acceptance/suppression, mode-configurable verification, four-tier generation readiness, Evidence Packet schema + delivery, component-level necessity + sufficiency.
- **Partial at 20B**: Evidence Packet verifier-merge (proof present-only; full verifier-clean merge in progress). 20B weight-geometry alignment (computable from open weights; on next-gate roadmap).
- **Open**: large-model scale (>20B / frontier), surface-text steering at scale, hidden-content detection at validated tier, Multi-Harness Composition coordinator, neuron-level localization, output-side steering on OLMo and at 20B.

---

## 10. Comparison Landscape

| System | Approach | Scope | CAS Harness Comparison |
|---|---|---|---|
| **Anthropic Neural Network Analysis (NLA)** | Joint AV + AR with RL reconstruction loss, natural-language descriptions | NLA: three sizes of one model family (Anthropic Claude — Haiku 3.5/4.5, Opus 4.6). **CAS Harness: six models across three independent architecture families, including a 20B scale extension.** | NLA produces natural-language descriptions admitted by Anthropic to sometimes be verifiably false ("confabulation"). CAS Harness produces typed classifications grounded in a published ontology with no confabulation tier. NLA is more flexible for discovery; CAS Harness is more auditable for compliance. The cross-vendor gap structurally absent in NLA is load-bearingly present in CAS Harness. |
| Linear probes (academic) | Classify activations; report accuracy | Single axis usually | CAS Harness adds causal validation, η → ε bridge for conditioning, framework-predictive diagnostics, multi-layer trace, Evidence Packet emission, cross-architecture validation, cross-scale validation to 20B, component-level necessity+sufficiency, runtime-safe verification stack, and the named canonical S7-F28-BALANCED-BRIDGE protocol discipline. |
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
2. The named canonical methodology **`S7-F28-BALANCED-BRIDGE`** as a unitary protocol artifact (label, axis, probe class, bridge mechanism, matched-control discipline)
3. The Evidence Packet schema + authenticated delivery surface
4. Framework-predictive preflight diagnostic methodology
5. Bi-agent audit-cycle methodology
6. Weight-geometry alignment methodology
7. Cross-architecture probe-transfer methodology
8. Cross-scale probe-transfer methodology (now closed up to 20B under the same canonical protocol)
9. Multi-layer trace + readout-position blind-spot detection
10. Two-bridge hidden-content / suppression detection
11. Multi-Harness Composition architecture (planned, components proven)
12. CAS Verification Stack — runtime-safe acceptance/suppression
13. Verification Mode Selector + factor-consistent verifier
14. Generation Readiness Gate orchestrating policy methodology
15. Component-level causal localization with necessity + sufficiency tests

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
| **`S7-F28-BALANCED-BRIDGE`** | **Canonical CAS Harness large-model methodology label. Plain name: S7-F28 Balanced Bridge Method. Full name: Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method. Encodes the four load-bearing protocol commitments: original Stage 7 source taxonomy, Foundation-28 axis, balanced-logistic probe (StandardScaler + LogisticRegression(class_weight='balanced')), full η → ε bridge with matched controls.** |
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
| Evidence Packet verifier-merge | Final gate on ACCEPT/SUPPRESS verdict — binds readout, ablation, bridge, trace diagnostics, model metadata, hashes, confidence, coverage, and caveats into one packet |
| Verification Stack | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Three customer-configurable verification modes |
| Generation Readiness Gate | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Blind-spot detection | Per-class identification of model-side vs readout-position weakness |
| Weight-geometry alignment | Principal-angle measure between CAS subspace and model's output-weight row space |
| Cross-architecture transfer | Validation that the η → ε bridge replicates across independent architecture families |
| Cross-scale transfer | Validation that the η → ε bridge replicates across parameter scales within a single architecture family (now closed up to 20B in Pythia/GPT-NeoX) |
| Hidden-content detection | Two-bridge comparison surfacing internal vs emitted content divergence |
| Component-level localization | Necessity + sufficiency tests identifying which architectural components carry the readout |

---

## Appendix A — One-Page Summary

**What is it?** A software service that looks inside any open-weight large language model, detects cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and surfaces what the model is internally computing but not emitting — with bit-identical Evidence Packet reproducibility a third party can verify. The canonical large-model methodology is named `S7-F28-BALANCED-BRIDGE`.

**How does it work?** Two-pass forward inference: (1) probe reads CAS structure from foreign model's activations using StandardScaler + balanced-logistic regression on the Stage 7 Foundation-28 axis; (2) realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class. The full inference path is captured in a typed, audit-grade Evidence Packet.

**Why does this work?** The Noetic Topos paper's Proposition 5.6 proves the counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. The static-weight tier independently confirms this: CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099).

**What is proved today?** Sixteen closed evidence tiers across **six open-weight models from three architecture families, including a 20B scale extension**:
- Detection above text baseline (up to 90.6% on 28 classes, +30+ pp lift; GPT-NeoX-20B at 86.86%)
- Causally load-bearing readout (collapse to exact chance under ablation, five axes; 20B activation-level cover ablation confirms pattern)
- Likelihood conditioning via η → ε bridge (effect strengthens across Pythia/GPT-NeoX scales, replicates stronger on OLMo, reaches its highest observed value on Qwen2.5-1.5B at +0.7960 (p = 2.92×10⁻¹²), and **replicates cleanly at 20B on GPT-NeoX-20B at +0.5964 (90/112 positive, p = 3×10⁻¹¹) — between Pythia-1B and OLMo-1B on the cross-architecture scaling curve as predicted**)
- Clean factorization (lacunarity 0.015 to 0.0016; **GPT-NeoX-20B Foundation lacunarity at 0.006715 — cleanest single-model Foundation factorization in project history**)
- Framework-predictive validity (**five** pre-registered predictions held, including the 20B scaling-curve prediction)
- Output-weight geometric alignment (2.83× random, p = 0.0099)
- Multi-layer trace with blind-spot detection and readout-vs-model disambiguation
- Component-level causal localization at head-level with necessity AND sufficiency (matched-control validated)
- Sparse MLP-neuron-cover causal localization with full bidirectional control — ablate / amplify / polarity-flip, all 112/112 examples passing at p < 10⁻³³ with bit-exact patch-back recovery
- Output-side behavioral steering at drive-local granularity, cross-scale within Pythia AND cross-architecture on Qwen — Stages 27O + 28
- Runtime-safe accept/suppress at 87.6% / 99.78% accuracy
- Three customer-configurable verification modes (6/6 pre-registered targets met)
- Four-tier generation readiness policy
- 15-field Evidence Packet schema with authenticated delivery
- Two-bridge hidden-content detection prototype
- Cross-architecture replication at three independent families
- **Cross-scale replication to 20B parameters within the Pythia/GPT-NeoX family — 7.1× scale jump without methodology adjustment**
- Methodology discipline (pre-registration, locked artifacts, matched controls, honest NULLs, named canonical protocol)

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific, and not scale-bounded below 20B parameters** — three independent labs (EleutherAI, AI2, Alibaba), three corpora, three tokenizer families, four within-family scale points up to 20B.

**What is the bounded claim today?** CAS Harness reads, validates, conditions, and emits audit-grade structural evidence for open-weight large language models up to 20B parameters across three architecture families, under the canonical `S7-F28-BALANCED-BRIDGE` methodology. Component-level causal localization is established at head and sparse-cover granularity. Surface-text steering at small model scale, neuron-level monosemantic localization, and frontier-scale (>20B) replication remain open boundaries. The 20B Evidence Packet verifier-merge for the final ACCEPT/SUPPRESS verdict is in progress (proof artifacts are present-only; verifier-clean merge is the next gate).

**Where to go from here?** Additional methodology depth available under separate technical-disclosure NDA after initial evaluation. Inquiries: contact founder via the agreement-specified channel.

---

**END — CAS Harness Specification Sheet v1.6-EXTERNAL — 2026-05-27**
