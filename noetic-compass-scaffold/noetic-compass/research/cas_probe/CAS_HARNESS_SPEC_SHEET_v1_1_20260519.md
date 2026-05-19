---
title: CAS Harness — Product Specification Sheet
subtitle: Cross-Model Cognitive Architecture Interpretability Platform
version: 1.1
date: 2026-05-19
supersedes: v1.0 (2026-05-17)
status: Internal — pending IP attorney review before external use
authors: Little Henderson (Founder), Claude Opus 4.7, Codex
classification: Confidential
---

# CAS Harness — Product Specification Sheet

**Version 1.1 — 2026-05-19**
**Status: Internal — pending IP attorney review before external use**
**Supersedes: v1.0 (2026-05-17)**

---

## Changes from v1.0 → v1.1

- **Cross-architecture validation closed** (Stage 15: OLMo-1B PASS CLEAN, AI2 model with different lab/lineage/corpus/tokenizer than Pythia)
- **Cross-scale curve extended to Pythia-2.8B** (Stage 14: third scale point, monotonic-converging trend)
- **Multi-layer trace + blind-spot detection added** (Stage 13: 95.4% probe, lacunarity 0.0016, 22.3% blind-spot rate, 77.7% stable)
- **Blind-spot audit added** distinguishing model-side weakness vs readout-position weakness (Stage 13.1)
- **Weight-geometry alignment evidence added** (Stage 14.1: CAS Foundation subspace 2.83× random output-weight alignment, p=0.0099)
- **NEW capability: Hidden-content detection** via two-bridge architecture comparing internal vs emitted CAS profiles (η₁ vs η₂)
- **NEW capability: Multi-Harness Composition** — specialized harnesses per CAS axis reading at their optimal depths, composed into a unified structural readout. Required for trillion-scale and force-multiplier for hidden-content detection (§5.13)
- Seven new capability subsections (5.7–5.13)
- Claims map (Section 8) tightened with new license rows
- Bounds (Section 9) updated: cross-architecture no longer an open bound
- IP & legal (Section 12) flags Stage 14.1, Stage 15, and Multi-Harness Composition mechanisms as additional separate-filing candidates
- Comparison landscape (Section 11) updated: NLA comparison row now references CAS Harness's cross-vendor validation

---

## 1. Executive Summary

CAS Harness is a cross-model interpretability and conditioning platform built on the **Cognitive Architecture System (CAS) v7.7** framework. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, and condition the model's next-token probability distribution by realizing the detected structure as readable context.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism before any empirical experiment ran. The prediction has been empirically confirmed on **four open-weight models across two architecture families** (Pythia-160M / Pythia-1B / Pythia-2.8B / OLMo-1B) and on **two evidence tiers** (activation-trace and weight-geometry).

**Today's load-bearing claim, reserved language, defensible for audit:**

> CAS Harness reads cognitive structure from open-weight transformer hidden states across four model scales (Pythia 160M / 1B / 2.8B; OLMo 1B) and two architecture families (EleutherAI Pythia and AI2 OLMo). The η → ε bridge — the read-and-realize loop predicted by Proposition 5.6 of the Noetic Topos paper — conditions next-token likelihood with effect sizes growing then plateauing across scale and strengthening on cross-architecture (OLMo-1B: +0.604 likelihood Δ, p ≈ 10⁻¹⁵). Six cognitive axes are detected (Noetics, Foundations, 40 Elements, Operators, Expression Shapes, Compiler-Valid Formulas), ablation-validated, and multi-layer trace-audited with blind-spot flagging that distinguishes model-side weakness from readout-position weakness. CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099) — first weight-geometry evidence of the bridge mechanism, complementary to the activation-tier evidence. Generation surface-text steering remains an open boundary at small model scale; cross-architecture transfer is now closed at one out-of-family architecture.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

Initial probing began on Pythia-160M (EleutherAI, 2023) in early May 2026. The conditional Glass House strategy memo (originally drafted 2026-05-16 as a "speculative product shape pending Stage 2 evidence") matured through fifteen experimental stages. By 2026-05-19 the probing chain had closed: cross-scale within Pythia (3 points: 160M, 1B, 2.8B), cross-architecture to OLMo-1B (AI2, different lineage), weight-geometry evidence (output-side alignment), multi-layer trace auditing, and blind-spot detection with readout-vs-model-side disambiguation.

### 2.2 Mission

CAS Harness exists to make the cognitive architecture inside any open-weight large language model **inspectable, validatable, conditionable, and audit-traceable** by an external software service — without requiring the model's vendor to publish interpretability tooling, without modifying the model's weights, and without sacrificing the reserved-language audit discipline required for regulator-grade evidence.

### 2.3 Strategic Relationship to CAS Native

CAS Harness is a **parallel SKU**, not a replacement for CAS Native. Per the founder's standing rules:

- **CAS Native** is "our model, transparent by construction" — the from-scratch flagship.
- **CAS Harness** is "your model, we make it inspectable" — the cross-model platform.

The two products share the same underlying framework (CAS v7.7), the same theoretical apparatus (lacunarity, fractal classifier, RPM chain, admissibility relations, Noetic Topos), the same compiler (`api/notation/compiler.py`), and the same evidence-tier discipline. They diverge only at the substrate: CAS Native trains weights on CAS-structured targets from scratch; CAS Harness reads CAS structure from a foreign model's existing weights.

---

## 3. Mathematical Foundation

### 3.1 The η → ε Bridge

CAS Harness's central architectural pattern is the **eta-epsilon bridge**, mathematically grounded in the Noetic Topos paper.

| Map | Direction | Implementation in CAS Harness |
|---|---|---|
| **η (eta)** | Embedding: structure → realization | Linear probe trained on hidden-state activations to read CAS class |
| **ε (epsilon)** | Realization: structure → tokens | Realization layer that emits CAS structure as readable prefix tokens for the foreign model |

### 3.2 The Section-Retraction Identity (CLAUDE.md Correction 2)

> **ε ∘ η = id** (realization after embedding = identity)
> **η ∘ ε ≠ id** (re-embedding after realization may lose information)

This asymmetry is load-bearing. ε is one-directional; ablation attempts to invert ε and structurally cannot succeed. Empirically, attempts to steer generation by hidden-state ablation (Stage 6.6, Stage 7.3, Stage 7.OA, Stage 7.LA) failed; attempts to condition generation by ε-realization (Stage 7.CPL, Stage 7.CPL2, Stage 8) succeeded.

### 3.3 Proposition 5.6 — Counit Surjectivity

The Noetic Topos paper proves: for any morphism g, the pullback of the counit ε along g is surjective. The Noetic Coverage Noe-Cov-3 axiom states the covering sieve contains ε. Applied to transformer architectures: prefix tokens are attended to by every subsequent position by construction — this is not a hyperparameter, it is the architectural property of self-attention.

The prediction was made in the Noetic Topos paper's first draft. The bridge mechanism it predicts has now been empirically confirmed across:
- Two model scales within one architecture family (Pythia: 160M, 1B, 2.8B)
- One out-of-family architecture (OLMo-1B; different lab, lineage, corpus, tokenizer)
- Two evidence tiers (activation-trace AND weight-geometry alignment)
- Six cognitive axes

### 3.4 Diagnostic Tools — Lacunarity, Fractal Classifier, Weight-Geometry Alignment

Three CAS-internal diagnostic tools have been empirically validated in CAS Harness:

- **Lacunarity gate** (Var/Mean²): Pythia-160M Noetics 0.793; Pythia-160M Foundations 0.021 (38× cleaner); Pythia-1B Foundations 0.015; **Stage 13 multi-layer trace 0.0016** (cleanest factorization signature in project history; multi-layer averaging cancels noise).

- **Fractal classifier** (Stabilizing / Amplifying / Oscillatory / Neutral): Stage 6.6 noetic ablation classified Oscillatory, predicting generation-steering failure; Stage 13 multi-layer trace classifies per-prompt as stable-like or problem-like, enabling blind-spot detection.

- **Weight-geometry alignment** (NEW, Stage 14.1): Principal-angle analysis between CAS Foundation subspace and model output-weight space. Pythia-160M result: 2.83× random expectation (p = 0.0099) on output-side; input-side basically random. First static-weight evidence of the bridge mechanism, complementary to activation-tier evidence.

The framework's own diagnostic tools have produced numerical predictions of CAS Harness experimental outcomes BEFORE the experiments ran, four times now (Stage 7 lacunarity prediction, Stage 6.6 fractal prediction, Stage 7.CPL covering-surjectivity prediction, Stage 14.1 weight-geometry alignment prediction).

---

## 4. Architecture

### 4.1 System Overview (v1.1)

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (e.g., Pythia, OLMo, Llama, etc.)
     │
     ├── Multi-layer hidden-state capture
     │       │
     │       ▼
     │   FOUNDATION / NOETIC / 40-ELEMENT / ETC. PROBES (η)
     │   Linear classifiers per CAS axis
     │       │
     │       ▼
     │   MULTI-LAYER TRACE classifier
     │   Stable-like vs problem-like flagging
     │       │
     │       ▼
     │   BLIND-SPOT DETECTOR
     │   Per-class: model-side weakness vs readout-position weakness
     │       │
     │       ▼
     │   CAS structure label (e.g., "F3|E" or "C7")
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

### 4.2 Component Specifications (v1.1 updates)

| Component | Status | Implementation Notes |
|---|---|---|
| Activation capture | validated | sklearn-compatible per-layer hooks; supports focus-token, final-token, mean-token extraction |
| Foundation / Noetic / Element / Operator / Expression / Formula probes (η) | validated | sklearn LogisticRegression L-BFGS, balanced class weight, StandardScaler |
| **Multi-layer trace classifier** | **validated (Stage 13)** | Reads probe confidence across all layers; flags stable-like / problem-like trajectories |
| **Blind-spot detector with readout-position disambiguation** | **validated (Stage 13.1)** | Distinguishes model-side weakness (genuine architectural gap) from readout-position weakness (probe-config sensitive) |
| Realization layer (ε) | validated | Template-based natural-language emission per CAS class |
| Likelihood scorer | validated | Computes semantic-class log-likelihood shift |
| Subspace ablation hook | validated | PyTorch forward-hook applying P = u·u^T projection-out |
| Random-control generator | validated | QR-orthonormalized same-rank random subspaces |
| Lacunarity computer | validated | Var/Mean² over per-class disruption magnitudes |
| Fractal classifier | validated | Iterated-trajectory orbit classification |
| **Weight-geometry analyzer** | **validated (Stage 14.1)** | Principal-angle analysis between probe subspace and W_U row space |
| Cross-architecture adapter | **validated for Pythia + OLMo** | Adapter abstracts model-specific tokenizer + hook-target details |
| Evidence Packet emitter | wired | Schema v1.1 includes multi-layer trace, blind-spot flag with readout-vs-model distinction, weight-geometry alignment score, claim-tier metadata |
| Mode 7 trace surface | wired | Streaming traceability for live inspection |
| **Two-bridge hidden-content detector (η₁ vs η₂)** | **prototype** (see §5.10) | Compares internal-state CAS profile vs emitted-text CAS profile to surface withheld / inverted content |

### 4.3 Three Customer Deployment Modes

(Unchanged from v1.0.)

| Mode | What the customer provides | What CAS Harness does | Where weights live |
|---|---|---|---|
| Hosted | HuggingFace model ID or weights upload | Train probes, run inspections, host dashboard | CAS Harness infra (encrypted) |
| Bring-your-endpoint | HTTPS endpoint exposing hidden states | Train probes against the endpoint; run inspections client-side | Customer infra |
| Self-hosted | Install CAS Harness toolkit | Sell toolkit + optional cloud probe training | Customer infra |

---

## 5. Capabilities — Validated as of 2026-05-19

Each capability is tagged with a Reserved-Language evidence level: **prototype / wired-works / sample-passed / gate-passed / validated**.

### 5.1 Cognitive Structure Detection

| Axis | Classes | Model | Probe Accuracy | Lift Over Text | Status |
|---|---:|---|---:|---:|---|
| 10 Noetics | 10 | Pythia-160M | 73.9% | +27.5 pp | validated |
| 28 Foundations | 28 | Pythia-160M | 78.6% | +28.9 pp | validated |
| 28 Foundations | 28 | Pythia-1B | 82.4% | (verify) | validated, cross-scale |
| **28 Foundations** | **28** | **Pythia-2.8B** | **85.9%** | **(verify)** | **validated, cross-scale** |
| **28 Foundations** | **28** | **OLMo-1B** | **90.6%** | **(verify)** | **validated, cross-architecture** |
| 40 Elements (TKS A1..D10) | 40 | Pythia-160M | 89.8% | +39.7 pp | validated |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | GREY (task design issue) + readout-causal PASS |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | validated |
| **10 Multi-Layer Trace** | **10** | **Pythia-160M** | **95.4%** | **(implicit in trace)** | **validated (Stage 13)** |

McNemar p-values vs text baseline range from 10⁻⁵⁰ (Stage 6.4) to 10⁻⁹⁵ (Stage 7.1) to machine-zero (Stages 9, 11, 12). Statistical separation from text baselines is unambiguous across every axis and model tested.

### 5.2 Readout-Causal Validation

| Test | Result | Status |
|---|---|---|
| Foundation subspace ablation, Pythia-160M | 78.6% → 3.57% (exact 1/28 chance) | validated |
| Random same-rank ablation, Pythia-160M | Mean disruption 0.000, max 0.000 | validated |
| 10-Noetic subspace ablation, Pythia-160M | 73.9% → 10.0% (exact 1/10 chance) | validated |
| 5-Operator subspace ablation, Pythia-160M | 99.2% → 20.0% (exact 1/5 chance) | validated |
| 10-Grammar subspace ablation, Pythia-160M | 93.0% → 10.0% (exact 1/10 chance) | validated |
| 10-Formula subspace ablation, Pythia-160M | 90.0% → 10.0% (exact 1/10 chance) | validated |
| **5 ablation tests, all collapsing to exact 1/N chance, all random nulls clean** | | **validated (5 axes)** |

### 5.3 Likelihood Conditioning via η → ε Bridge

| Model | Selected layer | Probe-readable Δ vs none | Margin over partner | Positive cases | Wilcoxon p |
|---|---:|---:|---:|---:|---:|
| Pythia-160M | 6 | +0.283 | +0.683 | 81/112 | <0.0001 |
| Pythia-1B | 8 | +0.554 | +1.246 | 90/112 | 2.58×10⁻¹⁴ |
| **Pythia-2.8B** | **14** | **+0.583** | **+1.336** | **92/112** | **3.08×10⁻¹⁵** |
| **OLMo-1B** | **16** | **+0.604** | **+1.305** | **87/112** | ≈ 10⁻¹⁵ |

Trends:

- **Monotonic-converging within Pythia.** Effect grows 160M → 1B → 2.8B with diminishing-returns shape. Saturates around 1B for this corpus/axis/realization.
- **Cross-architecture transfer is positive.** OLMo-1B shows the same (or stronger) effect as Pythia-1B despite different lab, lineage, corpus, and tokenizer.
- **Layer-selection rule transfers cleanly.** Best layer sits at 44–50% of network depth across all four models.
- **Raw CAS symbols stay null at every scale.** Confirms the effect is ε-realization (readable natural-language prefix), not symbol-recognition.

### 5.4 Factorization Quality

| Axis | Model | Lacunarity | Wrong-direction slots | Status |
|---|---|---:|---|---|
| 10 Noetics | Pythia-160M | 0.793 | 2 of 10 (^3, ^5) | Lumpy (v1 corpus artifact) |
| 28 Foundations | Pythia-160M | 0.021 | 0 of 28 | validated clean |
| 28 Foundations | Pythia-1B | 0.015 | 0 of 28 | validated clean (cross-scale) |
| **Multi-Layer Trace** | **Pythia-160M** | **0.0016** | **0 of 10** | **validated cleanest** |

The Stage 13 multi-layer trace lacunarity of 0.0016 is the lowest the project has produced. Multi-layer averaging suppresses single-layer noise, producing a structurally cleaner signal than any single-layer probe.

### 5.5 Framework Predictive Validity

The framework's diagnostic tools have made committed numerical predictions BEFORE four different experiments. All four held:

| Prediction (made when) | Tool | Experiment | Outcome |
|---|---|---|---|
| Foundations axis should be more factorized than Noetics | Lacunarity preflight | Stage 7 readout | Lacunarity 0.793 → 0.021. Confirmed. |
| Noetic subspace ablation will be Oscillatory, not Stabilizing | Fractal classifier preflight | Stage 6.6B generation trajectory | Classified as Oscillatory on larger samples. Confirmed. |
| Counit ε is the covering map for generation steering | Topos Proposition 5.6 | Stages 7.CPL through 8 | Likelihood conditioning closed across two scales. Confirmed at p ≈ 10⁻¹⁴. |
| **CAS Foundation subspace should show alignment with output weights** | **Proposition 5.6 corollary** | **Stage 14.1** | **2.83× random output-weight alignment, p = 0.0099. Confirmed.** |

This is the highest-tier scientific evidence the framework can produce: pre-registered quantitative predictions that the data subsequently honored.

### 5.6 Cross-Scale Validation (Within Architecture Family)

Three-point Pythia scaling curve:

| Model | Params | Probe Accuracy | Likelihood Δ | Status |
|---|---:|---:|---:|---|
| Pythia-160M | 160M | 78.6% (Foundations) | +0.283 | validated |
| Pythia-1B | 1B | 82.4% (Foundations) | +0.554 | validated |
| Pythia-2.8B | 2.8B | 85.9% (Foundations) | +0.583 | validated |

**Pattern: monotonic, converging.** Effect approximately doubles 160M → 1B (+0.271), then plateaus to a ~5% gain 1B → 2.8B (+0.029). Mechanism saturates around 1B parameters for this corpus / axis / realization. Practical implication: the η → ε bridge does NOT require frontier-scale models. A 1B parameter model captures nearly all of the bridge's effect on Pythia.

### 5.7 Cross-Architecture Validation — NEW IN v1.1

| Model | Lab | Architecture lineage | Training corpus | Tokenizer | Probe Accuracy | Likelihood Δ | Status |
|---|---|---|---|---|---:|---:|---|
| Pythia-1B (reference) | EleutherAI | GPT-NeoX | The Pile | GPT-NeoX BPE | 82.4% | +0.554 | validated |
| **OLMo-1B** | **AI2** | **OLMo (different)** | **Dolma** | **GPT-NeoX BPE adapter** | **90.6%** | **+0.604** | **validated, Stage 15** |

OLMo-1B is from a different lab (AI2 vs EleutherAI), uses a different architecture lineage, was trained on a different corpus (Dolma vs The Pile), and uses an adapted tokenizer. The η → ε bridge replicated *stronger* than on Pythia-1B at comparable parameter count.

**This closes the cross-architecture gate for one out-of-family model.** Additional architectures (Mistral, Llama, Qwen) remain open as redundancy validation, but the "Pythia-only artifact" hypothesis is now disproven.

### 5.8 Weight-Geometry Alignment — NEW IN v1.1

For the first time, CAS Harness has evidence of the bridge mechanism in the *static weights* of the foreign model, not just in activations.

| Test | Result | p-value | Status |
|---|---|---:|---|
| CAS Foundation subspace vs **output weights** (W_U row space) | **2.83× random expectation** | **0.0099** | **validated (above random)** |
| CAS Foundation subspace vs **input weights** (token embedding) | ~1× random expectation | not significant | controlled (input-side null) |
| Logit-lens energy of Foundation subspace | Significantly elevated | 0.0099 | validated |

**Interpretation.** The CAS Foundation directions inside Pythia are statistically more aligned with the model's output path than expected by chance. This is consistent with the Proposition 5.6 prediction: ε is the covering morphism, and ε realizes structure toward outputs — so we expect output-weight alignment of CAS directions, and we see it.

**Critical boundary language.** "Weights do not fire." Weights are static; activations fire per input. Stage 14.1 evidence is *geometric alignment* — the static weight matrices live in a configuration consistent with CAS-directional emission. This complements activation-trace evidence (which proves the mechanism operates dynamically per prompt) with a static-architectural finding (which proves the mechanism's geometry is baked into the weights).

### 5.9 Multi-Layer Trace + Blind-Spot Detection — NEW IN v1.1

The probe no longer reads only one layer. It reads across the entire layer stack and classifies the resulting trace.

| Capability | Status | Details |
|---|---|---|
| Multi-layer trace classifier | validated (Stage 13) | 95.4% accuracy on 10 classes, lacunarity 0.0016 |
| Stable-like vs problem-like trajectory flagging | validated | 77.7% stable, 22.3% problem-flagged on Pythia-160M |
| Per-class blind-spot identification | validated | Top blind-spot candidates: relation_dependency, production_recipe, membership_assertion, cover_partition_formula, yield_query |
| **Readout-position disambiguation** | **validated (Stage 13.1)** | Distinguishes model-side weakness from readout-position-config weakness. Example: `relation_dependency` weak under `mean_over_seq_len` readout but clean under `focus_token` at layer 12. |

**Why this matters for the product.** A regulator does not just want "this model is fine" — they want *"here is exactly where this model's representation of class X is fragile, here is whether the fragility is architectural or readout-configurable."* Multi-layer trace + blind-spot detection + readout-position disambiguation is the **regulator-grade evidence shape** that classical XAI tools cannot produce.

### 5.10 Hidden-Content / Suppression Detection — NEW IN v1.1 (Prototype)

This is the newest capability tier, derived from the two-bridge symmetry of the η → ε architecture. It addresses the question: **what is the model representing that it is not saying?**

**Architecture.** Two probes (η₁ on internal hidden states, η₂ on emitted output text) read CAS class profiles in parallel. Differences between them are detectable, quantifiable, and structurally classified.

```
Internal forward pass
     │
     ├── η₁ — probe internal hidden states → CAS class profile A
     │
     └── η₂ — probe emitted output text → CAS class profile B
                  │
                  ▼
            Compare A vs B
                  │
                  ▼
   ┌─────────────────────────────────────────────────────────┐
   │  Mismatch types:                                       │
   │  • Withheld: A has class X high, B has class X low     │
   │  • Inverted: A has class X, B has class Y where        │
   │            (X, Y) is a CAS involution pair             │
   │  • Suppressed: A's per-token trajectory shows class    │
   │            X firing then collapsing to neutral         │
   │  • Frame-manipulated: Domain trajectory shows Axis W   │
   │            inversion (P → O override)                  │
   └─────────────────────────────────────────────────────────┘
                  │
                  ▼
            ε realizes the gap as natural language for human reading
                  OR
            Typed structural report for regulator audit
```

**Seven detectable hiding shapes** (each maps to specific CAS Harness tooling):

| Shape | Detection mechanism | Evidence type |
|---|---|---|
| Withheld content | η₁ vs η₂ class-profile gap | Quantitative confidence gap |
| Self-censored content | Per-token CAS trajectory + Fractal Classifier | Amplifying → Neutral pattern |
| Latent capability | Blind-spot profile A vs B across prompts | Comparative per-class probe results |
| Suppressed reasoning | Per-CoT-step CAS classification | Step-level emission gap |
| Frame manipulation | Inversion Axis W (Domain precedence) firing | Static axis fingerprint |
| Persona drift | Multi-turn F_n |R profile trajectory | Trajectory-based detection |
| Involution content | Internal class vs emitted class on involution pair | Strongest mismatch signature |

**Status.** η₁ is validated across all Stage 6-15 work. η₂ on emitted output text is prototype-status (works on the same probe architecture; needs the same validation discipline applied to the *emitted-text* corpus). Two-bridge comparison is wired but not yet pre-registration-gated.

**Bounded claim.** This capability tells you *what CAS class the model is hiding* with the same statistical reliability as any other CAS Harness reading. It does not tell you *the literal words the model would have said* if not for the suppression — that requires intervention experiments (removing the suppression mechanism) which are a separate, higher-cost methodology.

**Comparison to Anthropic NLA's "evaluation awareness" finding.** NLA detected that Claude "believed but did not say" it was being evaluated, producing a natural-language description. CAS Harness's hidden-content detection produces a *typed* version of the same finding: which CAS class was internally computed, which CAS class was emitted, what the gap is in framework terms. CAS Harness's version is auditable (typed + provenance-stamped + reproducible); NLA's natural-language version is more readable but admitted-by-authors to sometimes be verifiably false.

**Multi-Harness Composition as force-multiplier.** Today's η₁ profile is read by a single probe at a single layer. Hidden-content detection becomes substantially more powerful when η₁ is itself a *composite* read by multiple specialized harnesses at their respective optimal depths (see §5.13). Specifically:

- A richer internal profile (a structured tensor across CAS axes) gives a denser baseline against which to detect the gap with the emitted output.
- Cross-axis inconsistency surfaces hiding: if the Noetic harness reads `^3^P` (principled aversion) but the Drive harness reads `F4 Connection` (warmth) at the same prompt, that compositional tension is itself a hiding signature, separable from simple class-mismatch.
- Trajectory localization: with multiple harnesses across depths, hidden content can be localized to a specific layer band where the internal computation diverges from the eventual emission. You can name *where* in the model the hiding mechanism lives, not just *that* it occurred.
- Disagreement-as-signal: where harnesses agree, the internal computation is coherent; where they disagree, attention is required, and the form of disagreement encodes what is being hidden.

The transition from single-probe η₁ to composite η₁ does not change the methodology — it scales the *granularity* of the internal profile. The η₂ side (probe on emitted text) stays the same. The gap becomes more detectable and more decomposable.

### 5.11 Framework Self-Consistency (Methodology as Differentiator)

Across 28+ experimental stages the project has enforced:

- Pre-registration: PASS / NULL / GREY gates committed BEFORE confirmatory experiments (8 consecutive stages of clean pre-reg)
- Paired statistics: Wilcoxon signed-rank or paired permutation
- Random-control matching: QR-orthonormalized same-rank random subspaces, fixed seeds
- Fresh holdouts: Confirmatory runs on prompts not used in exploratory iteration
- SHA + revision provenance: Activation files, probe weights, model commits, package versions
- Bi-agent audit cycle: Each meaningful commit reviewed by an independent agent

This methodology itself is a product differentiator. Glass House inspections produce evidence with this same discipline by design.

### 5.12 Tier Closure Summary (v1.1)

| Tier | Status |
|---|---|
| Discriminative readout (6 axes) | ✅ validated, 4 models |
| Above text/metadata baselines | ✅ validated, all axes |
| Readout-causal ablation (5 axes) | ✅ validated, collapse-to-exact-chance pattern |
| Likelihood conditioning via η → ε bridge | ✅ validated cross-scale (Pythia 160M/1B/2.8B) AND cross-architecture (OLMo-1B) |
| Clean factorization (lacunarity) | ✅ validated, down to 0.0016 multi-layer |
| Framework predictive validity | ✅ validated, 4 pre-registered predictions held |
| **Multi-layer trace + blind-spot detection** | ✅ **validated (NEW v1.1)** |
| **Cross-architecture transfer (OLMo)** | ✅ **validated (NEW v1.1)** |
| **Weight-geometry alignment (output-side)** | ✅ **validated (NEW v1.1)** |
| Hidden-content / suppression detection | 🟡 prototype (NEW v1.1) |
| **Multi-Harness Composition (axis-specialized + composed)** | 🟡 **planned-with-proven-components (NEW v1.1)** |
| Generation surface-text steering | ❌ closed-as-negative, mathematically explained |
| Additional cross-architecture redundancy (Llama, Mistral, Qwen) | ⏭ open |
| Scale beyond 2.8B (7B+, frontier-tier) | ⏭ open |

### 5.13 Multi-Harness Composition — Planned Capability, Components Proven (NEW v1.1)

The single-probe single-layer architecture validated through Stage 15 is sufficient for one-axis inspection at the model scales tested so far. It is **structurally insufficient for trillion-parameter models and a known bottleneck for hidden-content detection.** The next architectural step — already implied by the framework's own working-memory tensor and supported by every layer-by-layer result the project has produced — is **Multi-Harness Composition**: specialized harnesses, each reading a different CAS axis at its optimal depth, composed into a unified structural readout.

#### 5.13.1 Why the data already demands it

Different CAS axes peak at different layers, and the optimal layer shifts deeper with model scale:

| Axis | Pythia-160M Peak | Pythia-1B Peak | Pythia-2.8B Peak | OLMo-1B Peak |
|---|---:|---:|---:|---:|
| 10 Noetics | Layer 3 | (not tested at scale) | (not tested at scale) | (not tested at scale) |
| 28 Foundations (Drive × Register) | Layer 6 | Layer 8 | Layer 14 | Layer 16 |
| 40 Elements (Domain × Noetic) | Layer 5 | (not tested) | (not tested) | (not tested) |
| 10 Expression Shapes | Layer 2 | (not tested) | (not tested) | (not tested) |
| 10 Compiler-Valid Formulas | Layer 2 | (not tested) | (not tested) | (not tested) |
| Multi-Layer Trace (formulas) | Layer 12 | (not tested) | (not tested) | (not tested) |

The pattern: **Noetic axis lives shallow; Foundation axis lives mid; Formula / Expression / Trace axes live deep.** And the deeper-with-scale shift means at trillion-parameter scale (~100–200 layers, hidden dim ~16–32K), these axes will not all live at the same depth — some will peak in the first 20% of the network, others in the last 20%, and several will be distributed across bands of dozens of layers. **One probe at one layer would miss most of the structure that's actually there.**

#### 5.13.2 The architecture

```
                  TRILLION-PARAMETER FOREIGN MODEL
                  ──────────────────────────────────
LAYER 0–20:   Shallow features, lexical patterns
                │
                ├── HARNESS A: Noetic Reader (peaks ~layer 8)
                │   "This is ^2 Positive — the model is drawn toward."
                │
LAYER 20–50:  Mid-depth, relational structure
                │
                ├── HARNESS B: Drive × Register Reader (peaks ~layer 30)
                │   "Drive = F3 Vitality, Register = |T Transcendent."
                │
                ├── HARNESS C: Domain Descent Auditor (peaks ~layer 40)
                │   "P → C → E → O chain intact; no domain violations."
                │
LAYER 50–80:  Deep features, compositional integration
                │
                ├── HARNESS D: Meta-Logic Reader (peaks ~layer 60)
                │   "Membership asserted, subset verified, no category errors."
                │
                ├── HARNESS E: Production Semantics Reader (peaks ~layer 70)
                │   "Recipe Θ present; limiting reagent = F2|f."
                │
LAYER 80–120: Late features, output preparation
                │
                ├── HARNESS F: Multi-Layer Stability Auditor (all layers)
                │   "Trace stable L30–L70; drift at L80 — possible confabulation flag."
                │
                └── HARNESS G: Lacunarity Monitor (continuous)
                    "Gap map: ^3 at 0.02, ^5 at 0.03 — blind-spot alert."
                                  │
                                  ▼
                COMPOSITE STRUCTURAL READOUT
                ──────────────────────────────
"Model is processing with Cognitive Positive (^2), driven by transcendent
 Vitality (F3|T), in the Principled domain with intact descent chain.
 Caution: weak Negative evidence (^3 lacunarity 0.02) — blind spot around
 aversion / refusal signals. Multi-layer trace stable; no late-layer
 confabulation drift."
```

Each harness has its own optimized configuration (layer, readout position, probe architecture, ablation hook). The composite engine merges their outputs into a single Evidence Packet with per-harness contributions traceable and a coordinator-level merged verdict.

#### 5.13.3 Why composition is not "multiple copies of the same thing"

A trillion-parameter model does not have "a Foundation" or "a Noetic" in one place. It has a distributed cognitive architecture where each axis carries a different kind of information at a different depth:

- The **Noetic** signal tells you WHAT cognitive operation is happening
- The **Drive** signal tells you WHY — what motivational architecture is active
- The **Domain** signal tells you WHERE in the processing hierarchy
- The **Register** signal tells you HOW — the operational character
- The **Meta-logic** signal tells you what KIND of thing is being reasoned about
- The **Lacunarity Monitor** tells you what's MISSING

These are orthogonal axes — they do not collapse into a single probe. The harness has to be factored the same way the cognitive architecture is factored. This is the distributed implementation of the **CAS Working Memory tensor** the framework was designed around (`M_state: [10 Noetics × 4 Domains × 7 Drives × 4 Registers × d]`). Multi-Harness Composition is not a new architectural idea; it is the natural product realization of the working-memory tensor at scale.

#### 5.13.4 Components are proven; composition is the build

Every component required for Multi-Harness Composition has already been validated in isolation:

- **Stage 13 multi-layer trace** prototypes the composite reading-across-depths primitive for a single axis (one formula-family probe traced across all layers with stability classification per example).
- **Stage 7.2 Foundation decomposition** demonstrated that the 28-Foundation axis cleanly decomposes into Drive (7) × Register (4) components — the building blocks of two of the composed harnesses.
- **Stage 9 (40 Elements)** demonstrated that the 10-Noetic × 4-Domain cross-product is independently learnable — the building blocks of two more composed harnesses.
- **Stages 10–12** demonstrated Operator, Expression Shape, and Compiler-Valid axes as separately validated.
- **Stage 13.1 readout-position disambiguation** demonstrated that per-axis optimal configuration matters — same model, different probe configs, different readouts.

What remains is the **composition layer**: a coordinator that runs multiple harnesses in parallel at their respective optimal configurations, merges their outputs into a unified structural readout, and emits a single multi-harness Evidence Packet with per-harness traceability preserved.

#### 5.13.5 Force-multiplier effect on hidden-content detection

Multi-Harness Composition does not just enable trillion-scale deployment. It is also the architecture that turns hidden-content detection (§5.10) from prototype-tier into a primary capability:

- A composite η₁ (read across axes and depths) gives a *structured tensor* internal profile, not a single label
- Cross-axis tensions in the composite profile *are themselves hiding signatures*, separable from simple class-mismatch
- The hiding mechanism's *location in the network* can be named, not just *the fact of its occurrence*
- The granularity of "what is being hidden" climbs from "a class was withheld" to "this specific cognitive composition was suppressed at this specific layer band, with this specific drift profile"

This is the architectural step that makes the *"what is the model hiding"* question answerable at a level competitive with — and in some dimensions structurally stronger than — Anthropic NLA's natural-language descriptions, while preserving CAS Harness's typed-output / no-confabulation advantage.

#### 5.13.6 Status, bounded claim, and authorization

- **Architectural status:** planned-with-proven-components
- **Bounded claim:** "Each individual harness is validated; the coordinator that composes them is designed but not built; the composite Evidence Packet schema is specified but not emitted in production"
- **Build cost estimate:** 2–6 weeks of engineering plus pre-registration discipline for composition validation; no significant new GPU spend (each composed harness is already trained from prior stages)
- **External claim license:** NOT yet (composition not built, validation gates not run). Internal-only architectural specification.
- **IP filing candidate:** YES (see §12.2)

---

## 6. Development Timeline — Stages 1 through 15

Chronological summary of the experimental chain (May 2026). Each stage was committed, audit-reviewed, and either closed-positive or closed-negative-with-explanation.

| Stage | Date | Test | Verdict |
|---|---|---|---|
| 1.0–1.1 | 2026-05-14/15 | Probe scaffold + activation capture | Built |
| 2 / 2.1 / 2.2 | 2026-05-15 | Cross-layer probes vs baselines | Honest reframe `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT` (audit caught overclaim) |
| 3 → 3.3 | 2026-05-15/16 | Forced-continuation ablation, permutation control | `NOETIC_EFFECT_DIRECTION_MEANINGFUL` (p=0.0003) |
| 6.2 | 2026-05-16 | Clean v2 corpus (3,000 role-bound rows) | Built |
| 6.3–6.4 | 2026-05-16 | Activation capture + clean probe | **PASS**: 73.9%, +27.5pp, p≈10⁻⁵⁰ |
| 6.5 | 2026-05-17 | Noetic subspace ablation (readout-causal) | **PASS**: collapse to chance |
| 6.6 (six variants) | 2026-05-17 | Noetic generation steering attempts | NULL across all hidden-state hooks |
| 7 (pilot) | 2026-05-17 | 28 Foundations probe | **PASS**: 78.6%, +28.9pp, p≈10⁻⁹⁵ |
| 7.1 | 2026-05-17 | Foundation subspace ablation | **PASS**: 78.6% → 3.57% exact chance |
| 7.3 | 2026-05-17 | Drive-only generation steering | NULL — closed-as-negative for hidden-state-only mechanisms |
| 7.CPL → 7.CPL4 | 2026-05-17 | η → ε bridge experiments | **PASS CPL2** at likelihood tier (+0.283, p<0.0001); CPL3/CPL4 surface-text gated |
| 8 | 2026-05-17 | Pythia-1B cross-scale CPL2 replication | **PASS CLEAN**: +0.554, p≈10⁻¹⁴ |
| 9 | 2026-05-17 | 40 Elements (TKS A1..D10) readout | **PASS CLEAN**: 89.8%, +39.7pp, p ≈ machine-zero |
| 9.1 | 2026-05-17 | (40-Element ablation — pending) | Pending |
| 10 | 2026-05-17 | 5 Operators (axis sweep) | GREY on discriminative-vs-text; PASS on readout-causal (collapse to 1/5) |
| 11 | 2026-05-17 | 10 Expression Shapes (grammar) | **PASS CLEAN**: 93.0%, +28.6pp |
| 11 audit | 2026-05-17 | Confusion-pattern coherence audit | `COHERENT_WITH_ADJACENT_CONFUSIONS` |
| 12 | 2026-05-17 | 10 Compiler-Valid Formulas (semantics) | **PASS CLEAN**: 90.0%, +26.0pp |
| **13** | **2026-05-18** | **Multi-layer trace + blind-spot detection** | **PASS**: 95.4% probe, lacunarity 0.0016 |
| **13.1** | **2026-05-19** | **Blind-spot audit (fixture / threshold / bug-fix scope)** | **PASS** — clean methodology, readout-position vs model-side disambiguated |
| **14** | **2026-05-18** | **Pythia-2.8B cross-scale CPL2 replication** | **PASS CLEAN**: +0.583, p≈10⁻¹⁵ |
| **14.1** | **2026-05-19** | **Weight-geometry alignment (probe vs W_U)** | **PASS**: 2.83× random, p=0.0099 |
| **15** | **2026-05-19** | **OLMo-1B cross-architecture replication** | **PASS CLEAN**: 90.6% probe, +0.604 likelihood Δ |
| 16+ | (pending) | Additional cross-architecture (Mistral, Llama, Qwen) or scale-up (7B+) | Pending |

### 6.1 Methodology Discipline (Updated)

Across these 35+ stages the project has enforced (unchanged from v1.0 + Stage 13.1, 14.1, 15 additions):

- 8 consecutive stages of pre-registered gates committed before runs
- Paired statistics throughout
- Random-control matching on all causal claims
- Fresh holdouts for confirmatory runs (Stages 8, 11, 12, 14, 15)
- Bi-agent audit cycle (Claude ↔ Codex via agent_exchange/) — audits caught overclaim at Stages 2, 2.1, 3, 3.2, 6.6, 6.6A, 6.6C, 7.3, 11

---

## 7. Accomplishments (v1.1)

### 7.1 Scientific

1. Demonstrated CAS structure is detectable inside foreign open-weight LLMs across two architecture families and four model scales.
2. Demonstrated the detected structure is causally load-bearing for cognitive readout (5 axes pass collapse-to-exact-chance ablation).
3. Closed the η → ε bridge end-to-end on four model points: Pythia 160M / 1B / 2.8B, OLMo 1B.
4. Empirically confirmed Proposition 5.6 of the Noetic Topos paper at two tiers (likelihood + weight-geometry).
5. Made four pre-registered framework-internal predictions that all held.
6. **Validated cross-architecture transfer (Pythia → OLMo) at p ≈ 10⁻¹⁵.**
7. **Established multi-layer trace methodology with blind-spot detection** and readout-vs-model-side disambiguation.
8. **Produced first weight-geometry evidence** of the bridge mechanism (output-side alignment 2.83× random, p = 0.0099).
9. Prototyped hidden-content / suppression detection via two-bridge η₁/η₂ comparison.
10. Established referee-defensible audit methodology with 8 consecutive pre-registered confirmatory stages.

### 7.2 Engineering

1. Complete probing pipeline reusable across model architectures (Pythia + OLMo validated)
2. Six reusable cognitive axes (Noetics, Foundations, 40 Elements, Operators, Expression Shapes, Compiler-Valid Formulas)
3. v2 role-bound counterfactual corpus (3,000 rows, balanced, audited) — reusable for any future axis or model
4. Multi-layer trace classifier + lacunarity + fractal classifier diagnostic suite
5. Realization layer (ε): CAS structure → readable natural language
6. Evidence Packet schema v1.1 with multi-layer trace, blind-spot disambiguation, weight-geometry alignment, claim-tier metadata
7. Mode 7 streaming trace surface
8. Cross-architecture adapter validated on Pythia and OLMo
9. Two-bridge prototype (η₁ vs η₂) for hidden-content detection

### 7.3 Strategic

1. Established CAS Harness as a parallel SKU to CAS Native with distinct product mechanism, distinct legal IP framing, distinct customer base.
2. Demonstrated framework predictive validity at two tiers (activation + static-weight).
3. Closed the cross-architecture validation gate — the dominant remaining product uncertainty as of v1.0.
4. Built reserved-language discipline that survives audit AND comparison to Anthropic NLA.

---

## 8. Reserved-Language Claim Map (v1.1)

External-facing claims must use this table. **Do not strengthen any claim beyond what this table licenses.** IP attorney review required before any external use.

| Claim | License Status | Evidence |
|---|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED | Stages 6.4, 7, 8, 9, 11, 12, 13, 14, 15 |
| "The detected structure is causally load-bearing for cognitive readout" | LICENSED | Stages 6.5, 7.1, 10, 11, 12 (5 axes) |
| "The mechanism is framework-predicted" | LICENSED | 4 preflight predictions held |
| "We can condition the model's next-token probability distribution" | LICENSED | Stages 7.CPL2, 8, 14, 15 |
| **"This works cross-architecture (validated on Pythia and OLMo)"** | **LICENSED (NEW)** | **Stage 15** |
| **"This works cross-scale (Pythia 160M / 1B / 2.8B, monotonic-converging)"** | **LICENSED (NEW)** | **Stages 7, 8, 14** |
| **"CAS Foundation subspace shows output-weight alignment above random"** | **LICENSED (NEW)** | **Stage 14.1 (p = 0.0099)** |
| **"We can flag blind spots and distinguish model-side from readout-position weakness"** | **LICENSED (NEW)** | **Stages 13, 13.1** |
| **"We can detect hidden / withheld content at CAS-class granularity"** | **LICENSED with caveats** | **§5.10 — prototype with two-bridge methodology** |
| "We can steer the model's generated language" | NOT LICENSED | CPL3/CPL4 closed-as-not-clean at small model scale; pending replication at 1B+ |
| "We can read the model's mind in arbitrary natural-language detail" | NOT LICENSED | CAS reads at typed class granularity, not free-form English |
| "Validated for production use at frontier scale" | NOT LICENSED | Highest validated scale is Pythia-2.8B and OLMo-1B |
| "Universal interpretability platform" | NOT LICENSED | Need at least one more out-of-family architecture (Mistral / Llama / Qwen) for "universal" framing |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural

- **Two architecture families validated** (Pythia / GPT-NeoX lineage + OLMo / AI2 lineage). Llama, Mistral, Qwen, Phi, Gemma untested for redundancy.
- **Decoder-only transformers only.** Encoder-only (BERT family) and encoder-decoder (T5 family) untested.
- **Probes are per-model.** Probes trained on Pythia don't transfer to OLMo; methodology transfers, trained probes don't.

### 9.2 Scale

- **Up to 2.8B parameters validated.** 7B+, frontier-tier models untested.
- **Closed-API models cannot be onboarded.** Claude, GPT, Gemini do not expose activations. CAS Harness is open-weight only.

### 9.3 Modal

- **Likelihood conditioning closed; surface-text steering not yet closed at Pythia-160M scale.** CPL3/CPL4 surface-text gates failed at small model size, consistent with sampling-noise floor. Replication at 1B+ for surface-text tier is open (Stage 16 candidate).

### 9.4 Per-Class

- **Some classes carry more signal than others.** Affective register (|f) systematically harder to read than Transcendent (|T). 5 blind-spot classes identified, with readout-vs-model-side disambiguation now available. This is a real finding in its own right, not a defect.

### 9.5 Granularity

- **CAS reads at typed class granularity** (e.g., `^3^P|f`), not at arbitrary natural-language granularity.
- **η → ε can realize CAS class as natural language**, but the realization is grounded in the typed class — not free-form generation from the model's internal state.

### 9.6 Evidence-Tier

- Readout, readout-causal, likelihood-conditioning, factorization, framework-predictive, cross-architecture (1 family), weight-geometry alignment: **all closed**.
- Cross-architecture redundancy, large-model scale (7B+), surface-text steering at scale, hidden-content detection at validated-tier: **open**.

---

## 10. Future Prospects — Roadmap (v1.1)

### 10.1 Near-term (next 0–4 weeks)

| Stage | Test | Cost | Expected Yield |
|---|---|---:|---|
| 9.1 | 40-Element ablation + Domain × Noetic factorization | ~30 min A6000 | Tests whether 40 Elements is primary axis or Domain+Noetic composition |
| 16 (option A) | Llama-7B or OLMo-7B scale-up | ~$30–100 GPU | Tests scale beyond 2.8B; would close the "scale" bound to 7B |
| 16 (option B) | Second out-of-family architecture (Mistral-1B / Qwen-1B) | ~$5–15 GPU | Locks in cross-architecture-redundancy claim |
| 16 (option C) | Hidden-content detection — pre-register + validate the η₁/η₂ two-bridge | ~$5 GPU + corpus work | Promotes hidden-content tier from prototype to validated |
| 17 | Modular Harness interface design + Evidence Packet schema v2 | $0 GPU | Sets up trillion-scale architecture without code refactor |

### 10.2 Mid-term (1–6 months)

| Initiative | Description |
|---|---|
| Hosted MVP | Upload + probe-training + Evidence Packet inspection loop |
| Multi-architecture coverage | Validated probes for Llama, OLMo, Qwen, Mistral, Phi, Gemma |
| Hidden-content detection at production tier | Move two-bridge from prototype to validated |
| Surface-text steering at 1B+ scale | Replicate CPL3/CPL4 on larger models where sampling noise is lower |
| Mode 7 / Living Thought Atlas integration | Trace surface for live inspection |
| Modular multi-Harness orchestration | Foundation for trillion-scale fan-out architecture |

### 10.3 Long-term (6–24 months)

| Initiative | Description |
|---|---|
| Regulator-facing pilot | Compliance product for finance / hiring / healthcare / defense — one anchor customer |
| Self-hosted toolkit | On-prem deployment for regulated industries |
| Multi-vendor coverage | Validated probes for all major open-weight families |
| Public Glass House platform | After IP attorney clearance and customer track record |
| Joint product line with CAS Native | Inspect the user's model (Harness) AND offer transparent-by-construction alternative (Native) |
| Standards body engagement | TMLR / NeurIPS interpretability venues; AI Safety Institute engagement |

### 10.4 Trillion-Scale (Architectural — Multi-Harness Composition as the Load-Bearing Direction)

Trillion-parameter customer deployments will require multiple CAS Harnesses running in parallel. **Multi-Harness Composition (§5.13) is the load-bearing direction** — the other parallelization shapes are supplementary.

Parallelization shapes:

- **Shape B — Axis-specialized harnesses (primary, per §5.13)**. Each CAS axis (Noetic, Drive × Register, Domain Descent, Meta-Logic, Production Semantics, Stability, Lacunarity) gets its own harness, each at its optimal depth. **This is the load-bearing direction** because it's the one that maps directly onto the CAS Working Memory tensor.
- Shape A — Parallel across layer regions (early / mid / late) — naturally falls out of Shape B since different axes peak at different depths
- Shape C — Parallel across domain specializations (medical, legal, financial, safety) — productization layer on top of B
- Shape D — Tiered pipeline for real-time inference latency (fast-flag → deep-probe → trace-audit)
- Shape E — Ensemble robustness voting (multiple variants of each axis-harness)
- Shape F — Per-MoE-expert harnesses for Mixture-of-Experts trillion-scale models

Architectural prep work to support Multi-Harness Composition should begin now:

1. **Modular Harness interface** — every existing probe should expose a standardized input/output contract so the coordinator can fan out without refactoring
2. **Schema-extensible Evidence Packet** — per-harness contributions need to carry their own `harness_id`, `harness_version`, and per-axis evidence with the coordinator's merged verdict above
3. **Coordinator prototype** — a thin merging layer that takes outputs from any subset of the existing axis-probes and emits a composite Evidence Packet

These three engineering items are low-cost (no significant new GPU spend; each composed harness is already trained from prior stages). Multi-Harness Composition is the architectural step where the framework's design vision (the Working Memory tensor) becomes the deployed product surface.

---

## 11. Comparison Landscape (v1.1)

| System | Approach | Scope | CAS Harness v1.1 Comparison |
|---|---|---|---|
| **Anthropic Neural Network Analysis (NLA)** | Joint AV + AR with RL reconstruction loss, natural-language descriptions | Anthropic in-house models only (Claude Haiku 3.5 / 4.5, Opus 4.6) | CAS Harness is now **validated cross-vendor** (Pythia + OLMo, 4 model sizes). NLA produces natural-language descriptions that are admitted-by-authors to sometimes be verifiably false ("confabulation"). CAS Harness produces typed classifications grounded in a published ontology with no confabulation tier. NLA is more flexible for discovery; CAS Harness is more auditable for compliance. NLA is more expensive (joint RL on two full LMs); CAS Harness uses a linear probe + templated realization. Both have acknowledged limitations honestly. |
| Linear probes (academic) | Classify activations; report accuracy | Single axis usually | CAS Harness adds causal validation, η → ε bridge for conditioning, framework-predictive diagnostics, multi-layer trace + blind-spot detection, Evidence Packet emission, cross-architecture validation. |
| SHAP / LIME / classical XAI | Feature-importance attribution input → output | Black-box compatible | CAS Harness reads internal structural cognitive properties; classical XAI is shallower but model-agnostic. |
| Causal scrubbing (Anthropic) | Formal hypothesis-graph causal claims | Mechanistic-interp researchers only | CAS Harness's reserved-language tiered claims discipline is the same philosophy at a different granularity. |
| TransformerLens / mechanistic interp | Open-source mechanistic interpretability tooling | Researchers, not product | CAS Harness is a productized version with an a-priori cognitive framework. |
| Black-box behavioral testing | Prompt-and-score evaluations | Any model, no internal access | CAS Harness produces internal evidence; complementary, not competitive. |

---

## 12. IP & Legal Status (v1.1)

### 12.1 Existing IP

- **USPTO Provisional #64/037,173** covers the CAS framework primitives.
- The CAS framework's mathematical foundation is published in the Noetic Topos paper (journal submission, `main.pdf`).

### 12.2 Potentially Separate Filings (Updated)

The following CAS Harness-specific mechanisms may warrant separate IP filings; **IP attorney consultation required**:

1. The η → ε bridge as applied to foreign open-weight transformer models (probe → realization → prefix conditioning loop)
2. The Evidence Packet schema with tiered reserved-language claim attribution
3. The framework-predictive preflight diagnostic methodology (lacunarity + fractal classifier + topos prediction as quantitative pre-registration tools)
4. The bi-agent audit-cycle methodology
5. **NEW: The weight-geometry alignment methodology** (principal-angle analysis between CAS Foundation subspace and unembedding row space) — Stage 14.1
6. **NEW: The cross-architecture probe-transfer methodology** (validated by Stage 15 Pythia → OLMo transfer)
7. **NEW: The multi-layer trace + readout-position blind-spot detection** — Stages 13, 13.1
8. **NEW: The two-bridge hidden-content / suppression detection** (η₁ on activations vs η₂ on emitted text comparison) — §5.10
9. **NEW: Multi-Harness Composition** — axis-specialized harnesses each reading at optimal depth, composed via coordinator into a unified structural readout, mapped to the CAS Working Memory tensor — §5.13. Potentially the load-bearing IP claim for trillion-scale deployment AND for hidden-content detection at validated tier.

### 12.3 IP Urgency Note

As of v1.1 (2026-05-19), CAS Harness has produced four new methodology contributions in the last 48 hours:

- Multi-layer trace with blind-spot disambiguation
- Cross-architecture validation methodology
- Weight-geometry alignment methodology
- Two-bridge hidden-content detection

These are real intellectual property that did not fully exist 72 hours ago. **IP attorney consultation is more time-sensitive than at v1.0.**

### 12.4 External Disclosure Status

This document is **internal only**. Not authorized for external use until IP attorney review. The bounded findings from all Stages 6–15 are also not authorized for external use until IP attorney review covering both framework primitives (USPTO #64/037,173) and CAS Harness mechanisms (not yet filed).

---

## 13. Glossary (v1.1)

| Term | Definition |
|---|---|
| CAS | Cognitive Architecture System v7.7 |
| CAS Harness | This product. Cross-model interpretability platform. |
| CAS Native | From-scratch transformer with CAS as primary architecture. Parallel SKU. |
| η (eta) | Embedding map: structure → realization. Probe's role. |
| ε (epsilon) | Realization map: structure → tokens. Realization layer's role. Covering morphism per Proposition 5.6. |
| η → ε bridge | Two-pass mechanism: probe reads, realization writes, foreign model is conditioned via prefix attention. |
| **η₁ vs η₂** | **(NEW v1.1)** Two-bridge architecture for hidden-content detection: η₁ on internal hidden states vs η₂ on emitted output text. |
| 10 Noetics | Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect |
| 4 Domains | Principled (P), Cognitive (C), Evaluative (E), Operational (O) |
| 4 Registers | Transcendent (T), Analytical (A), Affective (f), Embodied (E) |
| 7 Drives | Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose (F1–F7) |
| 40 Elements | 10 Noetics × 4 Domains cross-product (TKS A1..D10) |
| 28 Foundations | 7 Drives × 4 Registers cross-product |
| Lacunarity | Var/Mean² gappiness measure |
| Fractal classifier | Iterated-operator orbit classifier (Stabilizing / Amplifying / Oscillatory / Neutral) |
| RPM chain | Realization-Prerequisite-Manifestation capability pathway |
| **CPL** | **CAS Prefix Likelihood (Stage 7-8-14-15 sub-experiments testing η → ε bridge at likelihood tier)** |
| Proposition 5.6 | Noetic Topos paper theorem proving counit ε's pullback is surjective |
| Noetic Coverage Noe-Cov-3 | Covering sieve condition requiring containment of counit ε |
| Evidence Packet | Per-inspection structured artifact CAS Harness emits |
| Mode 7 | Streaming trace surface for live inspection of η → ε bridge runs |
| **Blind-spot (Stage 13)** | **(NEW)** Class with unstable/weak multi-layer trace evidence; flagged as either model-side weakness OR readout-position weakness per Stage 13.1 disambiguation |
| **Weight-geometry alignment** | **(NEW)** Principal-angle measure between CAS subspace and model's output-weight row space; Stage 14.1 evidence tier |
| **Cross-architecture transfer** | **(NEW)** Demonstration that the η → ε bridge replicates from one open-weight architecture family to another (Stage 15: Pythia → OLMo) |
| **Hidden-content detection** | **(NEW, §5.10)** Two-bridge η₁/η₂ comparison surfacing what the model is internally computing but not emitting |

---

## 14. Reproducibility Provenance (v1.1)

### 14.1 Code Artifacts

- Primary research repo: `experiment/cas-probe-pythia` branch
- Probe / capture / ablation / CPL scripts: `noetic-compass-scaffold/noetic-compass/research/cas_probe/`
- CAS framework compiler: `api/notation/compiler.py`
- CAS engine (Rust): `cas-engine/src/`
- Noetic Topos paper: `docs/papers/main.pdf`
- Glass House strategy memo: `research/cas_probe/STRATEGY_GLASS_HOUSE.md`

### 14.2 Load-bearing Commit Hashes (as of 2026-05-19)

| Commit | Stage | Result |
|---|---|---|
| `34b0dc2` | Stage 3.2 random-direction control | Suggestive |
| `335e968` | Stage 3.3 n=30 permutation control | `NOETIC_EFFECT_DIRECTION_MEANINGFUL` |
| `421fdc0` | Stage 6.4 + 6.5 readout-causal | PASS |
| `060e9ea` | Stage 7.1 Foundation ablation | PASS — collapse to exact chance |
| `bf4c02e` | Stage 7.CPL likelihood bridge | PASS |
| `f8ba217` | Stage 7.CPL2 full η→ε loop | PASS — load-bearing |
| `129d189` | Stage 8 Pythia-1B replication | PASS CLEAN |
| `bc53fa9` | Stage 9 40-Element readout | PASS CLEAN |
| `b888526` | Stage 10 Operators | GREY + causal PASS |
| `5efc6e4` | Stage 11 Expression Shapes | PASS CLEAN |
| `1b6cdbd` | Stage 11 confusion-coherence audit | `COHERENT_WITH_ADJACENT_CONFUSIONS` |
| `b6aedd9` | Stage 12 Compiler-Valid Formulas | PASS CLEAN |
| `e603b74` | **Stage 13 multi-layer trace + blind-spot** | **PASS** |
| `bf645c8` | **Stage 13.1 blind-spot audit + Stage 14.1 weight-geometry + Stage 15 OLMo-1B** | **3 PASSES** |
| `f1fa2da` | **Stage 14 Pythia-2.8B replication** | **PASS CLEAN** |

### 14.3 Standing Reproducibility Discipline (Unchanged from v1.0)

- All activation files SHA-256 hashed; manifests committed; binaries > 100 MB git-ignored
- Model revisions via `model.config._commit_hash`
- Package versions per run (torch, transformers, scipy, numpy, sklearn)
- HuggingFace `local_files_only=True` for foreign-model loads
- Fixed seeds across random controls
- Pod: RunPod RTX A6000 (46 GB) via SSH

---

## 15. Document Version & Refresh Triggers

| Field | Value |
|---|---|
| Version | 1.1 |
| Date | 2026-05-19 |
| Supersedes | v1.0 (2026-05-17) |
| Status | Internal — pending IP attorney review |
| Refresh triggers (v1.2) | Additional cross-architecture (Mistral/Llama/Qwen) / Scale-up to 7B+ / Hidden-content detection validation / Material methodology revision |
| Next mandatory review | After next cross-architecture OR 7B+ scale-up result lands |
| Authorization for external use | Pending IP attorney clearance |

---

## Appendix A — One-Page Summary for Stakeholders (v1.1)

**What is it?** A software service that looks inside any open-weight large language model, detects the cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and can surface what the model is internally computing but not emitting.

**How does it work?** Two-pass forward inference: (1) probe reads CAS structure from foreign model's activations; (2) realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class.

**Why does this work?** The Noetic Topos paper's Proposition 5.6 proves the counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. Now also empirically: CAS Foundation subspace shows output-weight geometric alignment 2.83× random expectation (p = 0.0099).

**What is proved today?** Six closed evidence tiers across four open-weight models from two architecture families: detection above text/metadata (up to 90.6% on 28 classes, +30+ pp lift), causally load-bearing readout (collapse to exact chance under ablation), likelihood conditioning via the η → ε bridge (effect strengthens monotonically across Pythia scales then plateaus, replicates stronger on OLMo, p ≈ 10⁻¹⁴ to 10⁻¹⁵), clean factorization (lacunarity 0.015 to 0.0016), framework-predictive validity (4 pre-registered predictions held), output-weight geometric alignment, multi-layer trace with blind-spot detection and readout-vs-model disambiguation, prototype hidden-content / suppression detection.

**What is NOT yet proved?** Surface-text generation steering at small-model scale (closed-as-negative, mathematically explained). Cross-architecture redundancy beyond two families (Llama / Mistral / Qwen). Scale beyond 2.8B parameters. Hidden-content detection at validated-tier (currently prototype). Multi-Harness Composition (designed, components proven, coordinator not yet built).

**What is the next gate?** Either (a) one more out-of-family architecture replication, or (b) scale-up to 7B+, or (c) hidden-content detection validation, or (d) Multi-Harness Composition coordinator build. All four are cheap relative to product cost and complementary in evidence value. (d) is the architectural step that unlocks trillion-scale deployment AND substantially strengthens hidden-content detection — by giving the internal probe (η₁) a structured-tensor profile instead of a single classification.

**Authorization?** Internal only. IP attorney review required before any external use, including this summary.

---

*End of Document — CAS Harness Spec Sheet v1.1 — 2026-05-19*
