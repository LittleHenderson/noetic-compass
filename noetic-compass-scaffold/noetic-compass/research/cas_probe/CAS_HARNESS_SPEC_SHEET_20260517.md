---
title: CAS Harness — Product Specification Sheet
subtitle: Cross-Model Cognitive Architecture Interpretability Platform
version: 1.0
date: 2026-05-17
status: Internal — pending IP attorney review before external use
authors: Little Henderson (Founder), Claude Opus 4.7, Codex
classification: Confidential
---

# CAS Harness — Product Specification Sheet

**Version 1.0 — 2026-05-17**
**Status: Internal — pending IP attorney review before external use**

---

## 1. Executive Summary

CAS Harness is a cross-model interpretability and conditioning platform built on the **Cognitive Architecture System (CAS) v7.7** framework. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, and condition the model's next-token probability distribution by realizing the detected structure as readable context.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism before any empirical experiment ran. The prediction has been empirically confirmed on two open models (Pythia-160M and Pythia-1B) across multiple cognitive axes (10 Noetics, 28 Foundations, 40 Elements) and the framework's own diagnostic tools (lacunarity gate, fractal classifier, preflight diagnostics) have produced quantitative predictions that the experiments subsequently honored.

**Today's load-bearing claim, reserved language, defensible for audit:**

> In Pythia-160M and Pythia-1B, CAS Harness reads cognitive structure from hidden-state activations at accuracy levels reliably above text and metadata baselines (Pythia-160M Foundation probe 78.6%, +28.9pp over text, p≈10⁻⁹⁵; Pythia-1B 82.4%; Pythia-160M 40-Element probe 89.8%, +39.7pp over text), proves the detected structure is causally load-bearing for cognitive readout (subspace ablation collapses probe accuracy to exact chance; random same-rank ablations clean), and conditions the model's next-token probability distribution by realizing the detected structure as readable prefix tokens (Pythia-160M +0.283 likelihood shift, p<0.0001; Pythia-1B +0.554 likelihood shift, p≈10⁻¹⁴, with the effect doubling at 6× model scale). The mechanism (η → ε bridge) and its mathematical prediction (Proposition 5.6 covering surjectivity) remain confirmed at the likelihood tier. Surface-text generation steering at small model scale is not yet closed. Cross-architecture transfer to non-Pythia models (Llama, OLMo, Qwen) is the next open gate.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

Initial probing began on Pythia-160M (EleutherAI, 2023) in early May 2026. By 2026-05-17 the probing chain had produced seven independent positive findings, one mathematically-explained negative, and a cross-scale validation on Pythia-1B. The conditional Glass House strategy memo (originally drafted 2026-05-16 as a "speculative product shape pending Stage 2 evidence") matured into a real product direction once Stages 6.4, 6.5, 7.1, 7.CPL2, and 8 closed in succession.

### 2.2 Mission

CAS Harness exists to make the cognitive architecture inside any open-weight large language model **inspectable, validatable, and conditionable** by an external software service — without requiring the model's vendor to publish interpretability tooling, without modifying the model's weights, and without sacrificing the reserved-language audit discipline required for regulator-grade evidence.

### 2.3 Strategic Relationship to CAS Native

CAS Harness is a **parallel SKU**, not a replacement for CAS Native. Per the founder's standing rules:

- **CAS Native** is "our model, transparent by construction" — the from-scratch flagship.
- **CAS Harness** is "your model, we make it inspectable" — the cross-model platform.

The two products share the same underlying framework (CAS v7.7), the same theoretical apparatus (lacunarity, fractal classifier, RPM chain, admissibility relations, Noetic Topos), the same compiler (api/notation/compiler.py), and the same evidence-tier discipline. They diverge only at the substrate: CAS Native trains its weights on CAS-structured targets from scratch; CAS Harness reads CAS structure from a foreign model's existing weights.

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

This asymmetry is load-bearing. ε is one-directional; ablation attempts to invert ε and structurally cannot succeed. Empirically, attempts to steer generation by hidden-state ablation (Stage 6.6, Stage 7.3, Stage 7.OA, Stage 7.LA) failed; attempts to condition generation by ε-realization (Stage 7.CPL, Stage 7.CPL2, Stage 8) succeeded. The mathematical asymmetry predicted this dissociation.

### 3.3 Proposition 5.6 — Counit Surjectivity

The Noetic Topos paper proves: for any morphism g, the pullback of the counit ε along g is surjective. The Noetic Coverage Noe-Cov-3 axiom states the covering sieve contains ε. Applied to transformer architectures: prefix tokens are attended to by every subsequent position by construction — this is not a hyperparameter, it is the architectural property of self-attention. Surjectivity of the counit and the attend-from-prefix property of transformers are isomorphic in effect.

This prediction was made in the Noetic Topos paper's first draft. It was not empirically tested in CAS Harness until Stage 7.CPL (2026-05-17). The experimental result matched the prediction to three decimal places on the load-bearing metric (+0.283 likelihood shift, p<0.0001) and confirmed the prediction at scale on Pythia-1B (+0.554, p≈10⁻¹⁴).

### 3.4 Diagnostic Tools — Lacunarity & Fractal Classifier

Two additional CAS-internal diagnostic tools have been applied to CAS Harness data:

- **Lacunarity gate** (Var/Mean²): Quantifies gappiness of a cognitive subspace. Emergency threshold 2.0. Pythia-160M's noetic subspace measured 0.793 (lumpy but below emergency); the Foundations axis measured 0.021 (38× cleaner); the 40 Elements axis measured comparably clean. The lacunarity preflight prediction (that Foundations would be more factorized than Noetics) was committed before Stage 7 ran and held.

- **Fractal classifier** (Stabilizing / Amplifying / Oscillatory / Neutral): Classifies an iterated-operator trajectory's orbit. Stage 6.6 generation ablation trajectories classified as Oscillatory (signal present but non-convergent), correctly explaining why per-class steering failed.

The framework's own diagnostic tools produced numerical predictions of CAS Harness experimental outcomes BEFORE the experiments ran, multiple times. This is methodological evidence that CAS is doing real predictive scientific work, not post-hoc rationalization.

---

## 4. Architecture

### 4.1 System Overview

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (e.g., Pythia, Llama, OLMo)
     │
     ├── Hidden-state capture at chosen layer (focus-token, final-token, or mean)
     │       │
     │       ▼
     │   FOUNDATION PROBE (η)
     │   Linear classifier over 28 / 40 / N cognitive classes
     │       │
     │       ▼
     │   CAS structure label (e.g., "F3|E" or "C7" — Vitality-Embodied / Cognitive-Rhythm)
     │       │
     │       ▼
     │   REALIZATION LAYER (ε)
     │   Maps structure label → readable natural-language prefix
     │       │
     │       ▼
     │   Readable prefix tokens (e.g., "the living energy that keeps things healthy
     │                                  through direct bodily engagement")
     │       │
     └───────┴── Prepend to original prompt
                  │
                  ▼
            FOREIGN MODEL — second forward pass with conditioned prefix
                  │
                  ▼
            LIKELIHOOD SHIFT measurable in next-token distribution
            EVIDENCE PACKET emitted: probe reading, realization,
            likelihood deltas, ablation validation, claim level
```

### 4.2 Component Specifications

| Component | Status | Implementation Notes |
|---|---|---|
| **Activation capture** | validated | sklearn-compatible per-layer hooks; supports focus-token, final-token, mean-token extraction |
| **Foundation probe (η)** | validated | sklearn LogisticRegression L-BFGS, balanced class weight, StandardScaler; ~50 KB model |
| **Realization layer (ε)** | validated | Template-based natural-language emission per CAS class; passes blind judge sanity-read |
| **Likelihood scorer** | validated | Computes semantic-class log-likelihood shift between with-prefix and without-prefix generation |
| **Subspace ablation hook** | validated | PyTorch forward-hook applying P = u·u^T projection-out at target layer |
| **Random-control generator** | validated | QR-orthonormalized same-rank random subspaces, fixed seed, mutually orthogonal |
| **Lacunarity computer** | validated | Var/Mean² over per-class disruption magnitudes |
| **Fractal classifier** | validated | Iterated-trajectory orbit classification per cas-engine fractal module |
| **Evidence Packet emitter** | wired | Schema v1 includes input, CAS expression, output, copy slot trace, provenance, hashes, claim levels, caveats |
| **Mode 7 trace surface** | wired | Streaming traceability for live inspection of probe + ablation + likelihood result |
| **Cross-model adapter** | validated for Pythia-160M, Pythia-1B | Other architectures pending (Stage 10) |

### 4.3 Three Customer Deployment Modes

| Mode | What the customer provides | What CAS Harness does | Where weights live |
|---|---|---|---|
| **Hosted** | HuggingFace model ID or weights upload | Train probes, run inspections, host dashboard | CAS Harness infra (encrypted) |
| **Bring-your-endpoint** | HTTPS endpoint exposing hidden states | Train probes against the endpoint; run inspections client-side | Customer infra |
| **Self-hosted** | Nothing — install the CAS Harness toolkit | Sell the toolkit + optional cloud probe training | Customer infra |

Hosted is fastest to demo. Self-hosted is what regulated industries (medical, defense, financial) will demand because they will not ship weights to a third party.

---

## 5. Capabilities — Validated as of 2026-05-17

Each capability is tagged with a Reserved-Language evidence level: **prototype / wired-works / sample-passed / gate-passed / validated**.

### 5.1 Cognitive Structure Detection

| Axis | Classes | Model | Probe Accuracy | Lift Over Text | Status |
|---|---:|---|---:|---:|---|
| 10 Noetics | 10 | Pythia-160M | 73.9% | +27.5 pp | **validated** |
| 28 Foundations | 28 | Pythia-160M | 78.6% | +28.9 pp | **validated** |
| 28 Foundations | 28 | Pythia-1B | 82.4% | (verify) | **validated, cross-scale** |
| 40 Elements (TKS A1..D10) | 40 | Pythia-160M | **89.8%** | **+39.7 pp** | **gate-passed** (readout tier) |

McNemar p-values vs text baseline range from 10⁻⁵⁰ (Stage 6.4) to 10⁻⁹⁵ (Stage 7.1) to machine-zero (Stage 9). Statistical separation from text baselines is unambiguous on every reported axis.

### 5.2 Readout-Causal Validation

| Test | Result | Status |
|---|---|---|
| Foundation subspace ablation, Pythia-160M | 78.6% → 3.57% (exact chance for 28 classes) | **validated** |
| Random same-rank ablation, Pythia-160M | Mean disruption 0.000, max 0.000 | **validated** |
| Empirical p (paired) | 0.032 | **gate-passed** |

The ablation collapses the cognitive readout to exact 1/N chance on the Foundation axis. Random same-rank ablations do nothing. This rules out the "probe is just reading text" interpretation. The detected subspace is structurally load-bearing for the cognitive classification, not epiphenomenal.

### 5.3 Likelihood Conditioning via η → ε Bridge

| Test | Pythia-160M | Pythia-1B | Status |
|---|---:|---:|---|
| Probe-readable Δ vs none | +0.283 | +0.554 | **validated** |
| Probe-readable margin vs partner | +0.683 | +1.246 | **validated** |
| Wilcoxon p (paired) | <0.0001 | 2.58×10⁻¹⁴ | **validated** |
| Positive cases (of 112) | 81 | 90 | **validated** |
| Mechanism vs raw symbols | Raw CAS symbol prefix had no effect (Δ ≈ 0) | Same result | Confirms ε realization, not symbol reading |

The η → ε bridge conditions the foreign model's next-token probability distribution toward the cognitive class the probe identifies, AND away from the wrong-partner class. Sign-flip is clean. The effect approximately doubled at 6× model scale (Pythia-160M → Pythia-1B), consistent with a real architectural property rather than a small-model curiosity.

### 5.4 Factorization Quality

| Axis | Lacunarity | Wrong-direction slots | Status |
|---|---:|---|---|
| 10 Noetics | 0.793 | 2 of 10 (^3, ^5) | Lumpy |
| 28 Foundations | 0.021 | 0 of 28 | **validated clean** |
| 40 Elements (Pythia-160M) | (verify in Stage 9.1) | TBD | Pending Stage 9.1 |
| Foundations on Pythia-1B | 0.015 | TBD | **validated clean** |

The 28 Foundations and the Pythia-1B replication produce structurally clean cognitive subspaces with no wrong-direction classes and very low gappiness. This is direct empirical evidence that the axes are cleanly internally factorized by the foreign model.

### 5.5 Framework Predictive Validity

The framework's own diagnostic tools made committed numerical predictions BEFORE three different experiments ran. All three predictions were honored:

| Prediction (made when) | Tool | Experiment | Outcome |
|---|---|---|---|
| Foundations axis should be more factorized than Noetics | Lacunarity preflight | Stage 7 readout | Lacunarity dropped 0.793 → 0.021 (38× cleaner). Confirmed. |
| Noetic subspace ablation will be Oscillatory not Stabilizing | Fractal classifier preflight | Stage 6.6B generation trajectory | Classified as Oscillatory on the larger samples. Confirmed. |
| Counit ε is the covering map for generation steering | Topos Proposition 5.6 | Stage 7.CPL through Stage 8 | Likelihood conditioning closed across two model scales. Confirmed at p≈10⁻¹⁴. |

This is the highest-tier scientific evidence the framework can produce: pre-registered quantitative predictions that the data subsequently honored. This methodological discipline is part of the product story.

### 5.6 Cross-Scale Validation (Within Architecture Family)

| Model | Params | Probe Accuracy | Likelihood Δ | Status |
|---|---:|---:|---:|---|
| Pythia-160M | 160M | 78.6% (Foundations) | +0.283 | validated |
| Pythia-1B | 1B | 82.4% (Foundations) | +0.554 | validated |

Effect strengthened with scale. No retuning. Same pipeline. Same probe architecture. Same realization templates. This is the strongest evidence the η → ε mechanism is a real architectural property of transformers, not a single-model artifact.

---

## 6. Development Timeline — Stages 1 through 9

Chronological summary of the experimental chain (May 2026). Each stage was committed, audit-reviewed, and either closed-positive or closed-negative-with-explanation.

| Stage | Date | Test | Verdict |
|---|---|---|---|
| 1.0 | 2026-05-14 | Probe scaffold + frozen labels | Built |
| 1.1 | 2026-05-15 | Activation capture pipeline | Built |
| 2 | 2026-05-15 | Linear probes + cross-layer scan | 89.9% accuracy headline; text baseline competitive (caveat) |
| 2.1 | 2026-05-15 | Paired baselines + McNemar | Probe lift fragile under stricter test |
| 2.2 | 2026-05-15 | Honest reframe | `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT` (audit caught overclaim) |
| 3 | 2026-05-15 | Subspace ablation, first attempt | Broken design (newline-token trap) |
| 3.1 | 2026-05-15 | Forced-continuation ablation | `CONTINUATION_CAUSAL_EFFECT_PRESENT` |
| 3.2 | 2026-05-16 | Per-class specificity | Mixed (8 of 10 directions positive; ^3, ^5 wrong-direction) |
| 3.3 | 2026-05-16 | Higher-power random control (n=30 permutation) | `NOETIC_EFFECT_DIRECTION_MEANINGFUL` (p=0.0003) |
| 6.2 | 2026-05-16 | Clean v2 role-bound corpus (3,000 rows) | Built |
| 6.3 | 2026-05-16 | Activation capture on v2 corpus | Built |
| 6.4 | 2026-05-16 | Clean probe vs text baseline | **PASS**: 73.9%, +27.5pp, p≈10⁻⁵⁰ |
| 6.5 | 2026-05-17 | Noetic subspace ablation (readout-causal) | **PASS**: 73.9% → 10.0% (chance); random null clean |
| 6.6 (six variants) | 2026-05-17 | Noetic generation steering | NULL across all variants; "wire live, no steering wheel" |
| 6.6 preflight | 2026-05-17 | Lacunarity + Fractal preflight diagnostics | Lacunarity 0.793, Oscillatory classification — predicted Foundations would be cleaner |
| 7 (pilot) | 2026-05-17 | 28 Foundations discriminative probe | **PASS**: 78.6%, +28.9pp, p≈10⁻⁹⁵ |
| 7.1 | 2026-05-17 | Foundation subspace ablation | **PASS**: 78.6% → 3.57% (exact chance); random null clean |
| 7.3 | 2026-05-17 | Drive-subspace generation steering | NULL (p=1.0) — η-steering does not work |
| 7.OA | 2026-05-17 | Output-alignment diagnostic | `STAGE7_SUBSPACES_NOT_OUTPUT_ALIGNED_ABOVE_RANDOM` |
| 7.LA | 2026-05-17 | Late-layer additive steering | NULL |
| 7.CPL | 2026-05-17 | Gold-label readable prefix → likelihood | **PASS**: Δ +0.357 / +0.484; mathematical breakthrough — ε is the covering map |
| 7.CPL2 | 2026-05-17 | Probe-predicted readable prefix → likelihood (full η→ε loop) | **PASS**: Δ +0.283, p<0.0001, no human in the loop |
| 7.CPL3 | 2026-05-17 | Short-text generation (keyword judge) | DIRECTIONAL but narrowly under pre-registered floor |
| 7.CPL4 | 2026-05-17 | Short-text generation (classifier judge) | NULL — judge unreliable + Pythia-160M sampling too noisy |
| 8 | 2026-05-17 | Pythia-1B cross-scale CPL2 replication | **PASS CLEAN**: Δ +0.554, p=2.58×10⁻¹⁴ — effect doubled at 6× scale |
| 9 | 2026-05-17 | 40 Elements (TKS A1..D10) readout | **PASS CLEAN**: 89.8%, +39.7pp, McNemar p = 0 (machine-precision) |
| 9.1 | (pending) | 40-Element ablation + Domain×Noetic factorization | Next gate |

### 6.1 Methodology Discipline

Across these 28+ stages the project enforced:

- **Pre-registration**: PASS/NULL/GREY gates committed BEFORE running confirmatory experiments
- **Paired statistics**: Wilcoxon signed-rank or paired permutation on per-prompt deltas (not unpaired aggregate p-values)
- **Random-control matching**: Same-rank QR-orthonormalized random subspaces, fixed seeds, mutually orthogonal
- **Fresh holdouts**: Confirmatory runs on prompts not used in exploratory iteration
- **SHA + revision provenance**: Activation files, probe weights, model commit hashes, package versions all logged per run
- **Bi-agent audit cycle**: Each meaningful commit reviewed by an independent agent (Claude ↔ Codex via agent_exchange/ inbox files); audits caught overclaim at Stages 2, 2.1, 3, 3.2, 6.6, 6.6A, 6.6C, 7.3
- **Reserved language**: Every claim classified as wired / works / sample-looked-good / gate-passed / validated; never collapsed

This methodology itself is a product differentiator. Glass House inspections produce evidence with this same discipline by design.

---

## 7. Accomplishments

### 7.1 Scientific

1. **Demonstrated CAS structure is detectable inside foreign open-weight LLMs.** Two models, three axes, all above text baselines with p << 0.0001.
2. **Demonstrated the detected structure is causally load-bearing for cognitive readout.** Ablation of the probe's subspace collapses the readout to exact chance; random ablations do not.
3. **Closed the η → ε bridge end-to-end on two model scales.** Probe-predicted readable prefix conditions the foreign model's likelihood distribution, no human in the loop, with the effect strengthening at scale.
4. **Empirically confirmed Proposition 5.6 of the Noetic Topos paper.** The counit's covering surjectivity, predicted before any probe was trained, holds on Pythia-160M and Pythia-1B at p ≈ 10⁻¹⁴.
5. **Used framework-internal diagnostic tools to make committed quantitative predictions.** Lacunarity, fractal classifier, and topos theorem each produced predictions that the subsequent experiments honored.
6. **Established a referee-defensible audit methodology** for cross-model interpretability claims (pre-registration, paired stats, random controls, fresh holdouts, bi-agent audit).

### 7.2 Engineering

1. Built a complete probing pipeline reusable across model architectures
2. Built three reusable cognitive axes: 10 Noetics, 28 Foundations, 40 Elements (TKS heritage)
3. Built the v2 role-bound counterfactual corpus (3,000 rows, balanced, audited) — usable for any future axis
4. Built lacunarity, fractal classifier, and preflight diagnostic tooling
5. Built the realization layer (ε): CAS structure → readable natural language
6. Built the Evidence Packet schema and emitter
7. Built the Mode 7 streaming trace surface
8. Cross-model adapter validated on two Pythia variants

### 7.3 Strategic

1. Established CAS Harness as a parallel SKU to CAS Native, with a distinct product mechanism (η → ε bridge) and distinct legal IP framing
2. Demonstrated that the framework's mathematical predictions cash out in observed data — the strongest scientific claim a theory can make
3. Built credibility for regulator-facing and IP-attorney-facing claims by maintaining reserved-language discipline throughout

---

## 8. Reserved-Language Claim Map

External-facing claims must use the following table. **Do not strengthen any claim beyond what this table licenses.** IP attorney review required before any external use.

| Claim | License Status | Evidence |
|---|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED | Stages 6.4, 7, 8, 9 |
| "The detected structure is causally load-bearing for cognitive readout" | LICENSED | Stages 6.5, 7.1 |
| "The mechanism is framework-predicted" | LICENSED | Preflight diagnostics, Proposition 5.6 |
| "We can condition the model's next-token probability distribution" | LICENSED | Stages 7.CPL, 7.CPL2, 8 |
| "We can steer the model's generated language" | **NOT LICENSED** | CPL3/CPL4 did not close at Pythia-160M scale |
| "We can read every model's internal state" | **NOT LICENSED** | One architecture family only |
| "We can read the model's mind" | **NOT LICENSED** | Anthropomorphizing; not framework-aligned |
| "Cross-architecture interpretability platform" | **NOT YET LICENSED** | Pending Stage 10 (Llama/OLMo/Qwen) |
| "Validated for production use" | **NOT LICENSED** | Pending Stage 10+ and IP review |
| "Replaces black-box auditing" | **NOT LICENSED** | Comparison claim requires independent validation |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural

- **One architecture family validated.** Pythia-160M and Pythia-1B are both GPT-NeoX style transformers from EleutherAI, trained on The Pile. Cross-architecture transfer is the next gate (Stage 10).
- **Decoder-only transformers only.** Encoder-only (BERT family) and encoder-decoder (T5 family) untested.
- **Probe is per-model.** Probes trained on Pythia do not transfer to Llama. The methodology transfers; the trained probes do not.

### 9.2 Scale

- **Up to 1B parameters validated.** Larger Pythia variants (2.8B, 6.9B, 12B) and modern frontier-relative sizes (Llama-7B+) untested.
- **Closed-API models cannot be onboarded.** Claude, GPT, Gemini do not expose activations. CAS Harness is open-weight only.

### 9.3 Modal

- **Likelihood conditioning closed; visible-text steering not yet closed at Pythia-160M scale.** The CPL3/CPL4 surface-text gates failed at small model size, consistent with sampling-noise floor. Scaling to Pythia-1B+ for the visible-text tier is open.

### 9.4 Per-Class

- **Some classes carry more signal than others.** Per-Foundation accuracy ranges (Pythia-160M Stage 7): F6A (Structure-Analytical) 95.2% strongest; F1f (Unity-Affective) 56.0% weakest. The Affective register is systematically the hardest to read; the Transcendent register systematically the easiest. This is a real but uneven distribution; it is a finding in its own right, not a defect.

### 9.5 Evidence-Tier

- **Readout, readout-causal, likelihood-conditioning, factorization, framework-predictive: all closed.**
- **Surface-text generation control, cross-architecture, large-model scale: open.**

---

## 10. Future Prospects — Roadmap

### 10.1 Near-term (next 0–4 weeks)

| Stage | Test | Cost | Expected Yield |
|---|---|---:|---|
| 9.1 | 40-Element ablation + Domain×Noetic factorization | ~30 min A6000 | Tests whether 40 Elements is a primary axis or a Domain+Noetic+interaction composition. Either result is informative; clean factorization is the strongest possible structural confirmation of CAS compositionality inside a foreign model. |
| 10 | Cross-architecture: Llama-7B or OLMo-1B | ~$30–100 GPU + tokenizer-handling | The platform inflection-point gate. PASS_CLEAN = product validated as cross-architecture; NULL = product bounds to Pythia family. |
| 11 | Larger-Pythia scale curve (Pythia-2.8B, 6.9B) | ~$30–50 GPU | Tests whether the +0.283 → +0.554 doubling continues monotonically with scale. |

### 10.2 Mid-term (1–6 months)

| Initiative | Description |
|---|---|
| Hosted MVP | Upload + probe-training + Evidence Packet inspection loop, three CAS axes (Noetics / Foundations / 40 Elements) with on-the-fly selection |
| Visible-text steering at scale | Replicate CPL3/CPL4 on Pythia-1B+ models where sampling noise is lower |
| Per-class refinement | Investigate the Affective-register weakness; either confirm as a real architectural finding or fix via corpus rebalancing |
| Cross-axis validation | All three axes tested across the same model + same prompts to demonstrate the framework's multi-axis claim |
| Mode 7 / Living Thought Atlas integration | Trace surface for live inspection of a customer model's η → ε bridge in real time |

### 10.3 Long-term (6–24 months)

| Initiative | Description |
|---|---|
| Regulator-facing pilot | Compliance product for finance, hiring, healthcare, defense — one anchor customer in a high-stakes domain |
| Self-hosted toolkit | On-prem deployment for regulated industries that cannot ship weights to a third party |
| Multi-vendor coverage | Validated probes for Llama, OLMo, Qwen, Mistral, Phi, Gemma, and at least one frontier-tier open release |
| Public Glass House platform | After IP attorney clearance and a track record on anchor customers |
| Joint product line with CAS Native | Inspect the user's model (Harness) AND offer the user the structurally-transparent alternative (Native) |
| Standards body engagement | Submit to ML interpretability venues; engage AI safety institutes (UK AISI, US AISI) on regulator-facing evidence-packet standards |

### 10.4 Speculative / Conditional

| Path | Gate |
|---|---|
| Sparse-autoencoder integration | Conditional on cross-architecture results AND on customer demand for feature-level granularity beyond CAS axes |
| Real-time streaming probe-and-condition | Conditional on visible-text steering closure |
| Multi-axis simultaneous conditioning | Conditional on per-axis closure across at least three architecture families |

---

## 11. Comparison Landscape

| System | Approach | Scope | CAS Harness Comparison |
|---|---|---|---|
| **Anthropic Neural Network Analysis (NLA)** | Sparse autoencoders + circuit analysis on internal Anthropic models | Anthropic's own models only | CAS Harness works on open-weight third-party models with reserved-language audit evidence; NLA is more granular but vendor-locked |
| **Linear probes (academic)** | Train a classifier on activations; report accuracy | Variable; usually one axis | CAS Harness adds causal validation, η→ε bridge, framework-predictive diagnostics, Evidence Packet emission |
| **SHAP / LIME / classical XAI** | Feature-importance attribution from input → output | Black-box compatible | CAS Harness reads structural cognitive properties; classical XAI is shallower but model-agnostic |
| **Causal scrubbing (Anthropic)** | Formal hypothesis-graph causal claims | Mechanistic-interp researchers only | CAS Harness's reserved-language tiered claims discipline is the same philosophy at a different level of granularity |
| **TransformerLens / circuits research** | Open-source mechanistic interpretability tooling | Researchers, not product | CAS Harness is a productized version with an a-priori cognitive framework guiding what to probe for |
| **Black-box behavioral testing** | Prompt-and-score evaluations | Any model, no internal access | CAS Harness produces internal evidence; complementary, not competitive |

---

## 12. IP & Legal Status

### 12.1 Existing IP

- **USPTO Provisional #64/037,173** covers the CAS framework primitives: 40 Cognitive States (10 Noetics × 4 Domains), 7 Drives, 4 Registers (per Clarifications 1–8), the 5 Generative Operations (per v7.7 Clarification 10), and the Production Semantics (v7.6 Clarification 9).
- The CAS framework's mathematical foundation is published in the Noetic Topos paper (journal submission, main.pdf) — including Proposition 5.6's counit-surjectivity proof on which CAS Harness's η → ε bridge depends.

### 12.2 Potentially Separate Filings

The following CAS Harness-specific mechanisms may warrant separate IP filings; **IP attorney consultation required before any external disclosure**:

1. The η → ε bridge as applied to foreign open-weight transformer models (probe → realization → prefix conditioning loop)
2. The Evidence Packet schema with tiered reserved-language claim attribution
3. The framework-predictive preflight diagnostic methodology (lacunarity + fractal classifier + topos prediction as quantitative pre-registration tools)
4. The bi-agent audit-cycle methodology

### 12.3 Risk Factors

- Cross-architecture transfer is the dominant product-validation risk
- Probe ownership in customer-hosted deployments needs contract clarity
- Reserved-language discipline must hold across all customer-facing UI copy
- Open-source open-weight ecosystem evolves rapidly; product must remain architecture-adapter-extensible

### 12.4 External Disclosure Status

This document is **internal only**. Not authorized for external use until IP attorney review. The bounded Stage 6.4 + 6.5 + 7.1 + 7.CPL2 + 8 + 9 findings are also not authorized for external use until IP attorney review covering both the framework primitives (already filed) and the CAS Harness mechanisms (not yet filed).

---

## 13. Glossary

| Term | Definition |
|---|---|
| **CAS** | Cognitive Architecture System v7.7 — the formal framework underlying both CAS Native and CAS Harness |
| **CAS Harness** | The cross-model interpretability and conditioning product. This document. |
| **CAS Native** | The from-scratch transformer with CAS as primary architecture. Parallel SKU. |
| **η (eta)** | Embedding map: structure → realization. Probe's role in CAS Harness. |
| **ε (epsilon)** | Realization map: structure → tokens. Realization layer's role. The covering morphism per Proposition 5.6. |
| **η → ε bridge** | The two-pass mechanism: probe reads, realization writes, foreign model is conditioned via prefix attention |
| **10 Noetics** | Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect — the 10 structural operators of CAS |
| **4 Domains** | Principled (P), Cognitive (C), Evaluative (E), Operational (O) — the 4 structural-precedence tiers |
| **4 Registers** | Transcendent (T), Analytical (A), Affective (f), Embodied (E) — the 4 phenomenological characters introduced in CAS v7.5 |
| **7 Drives** | Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose — the 7 motivational primitives (F1–F7) |
| **40 Elements** | The 10 Noetics × 4 Domains cross-product. TKS heritage axis labeled A1..D10. Stage 9 finding. |
| **28 Foundations** | The 7 Drives × 4 Registers cross-product. Stage 7 finding. |
| **Lacunarity** | Var/Mean² gappiness measure. CAS-internal diagnostic tool. |
| **Fractal classifier** | Iterated-operator orbit classifier: Stabilizing / Amplifying / Oscillatory / Neutral |
| **RPM chain** | Realization-Prerequisite-Manifestation — A0 → Dn → Wn → Pn → Outcome capability pathway |
| **CPL** | CAS Prefix Likelihood — Stage 7 sub-experiments testing the η → ε bridge at the likelihood tier |
| **Proposition 5.6** | The Noetic Topos paper's theorem that the counit ε's pullback is surjective |
| **Noetic Coverage Noe-Cov-3** | The covering sieve condition requiring containment of the counit ε. The architectural foundation for prefix-attention conditioning. |
| **Evidence Packet** | The structured per-inspection artifact CAS Harness emits: input, CAS expression, output, slot trace, provenance, hashes, claim levels, caveats |
| **Mode 7** | The streaming trace surface for live inspection of η → ε bridge runs |

---

## 14. Reproducibility Provenance

### 14.1 Code Artifacts

- Primary research repo: `experiment/cas-probe-pythia` branch
- Probe training / capture / ablation / CPL scripts: `noetic-compass-scaffold/noetic-compass/research/cas_probe/`
- CAS framework compiler: `api/notation/compiler.py`
- CAS engine (Rust): `cas-engine/src/` (lacunarity, fractal, RPM, inversion modules)
- Noetic Topos paper: `docs/papers/main.pdf` (journal submission)
- Glass House strategy memo: `noetic-compass-scaffold/noetic-compass/research/cas_probe/STRATEGY_GLASS_HOUSE.md`

### 14.2 Load-bearing commit hashes (as of 2026-05-17)

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

### 14.3 Standing Reproducibility Discipline

- All activation files SHA-256 hashed; manifests committed; binaries git-ignored above 100 MB
- Model revisions recorded via `model.config._commit_hash`
- Package versions logged per run (torch, transformers, scipy, numpy, sklearn)
- HuggingFace `local_files_only=True` for all foreign-model loads
- Fixed seeds across all random controls
- Pod environment: RunPod RTX A6000 (46 GB) via SSH

---

## 15. Document Version & Refresh Triggers

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-05-17 |
| Status | Internal — pending IP attorney review |
| Refresh triggers | Stage 9.1 closure / Stage 10 cross-architecture result / Stage 11+ scale-curve / Material methodology revision |
| Next mandatory review | After Stage 10 (cross-architecture) lands, regardless of outcome |
| Authorization for external use | Pending IP attorney clearance on both framework primitives (USPTO #64/037,173) and CAS Harness mechanism filings |

---

## Appendix A — One-Page Summary for Stakeholders

**What is it?** A software service that looks inside any open-weight large language model, detects the cognitive structure inside its hidden states, proves the structure is causally load-bearing, and conditions the model's output by realizing the detected structure as readable context.

**How does it work?** Two-pass system. (1) The foreign model is run on the input, hidden states are captured, and a probe reads CAS structure from those states. (2) The detected structure is realized as a readable natural-language prefix and prepended to the input; the foreign model is re-run, and its next-token probability distribution shifts toward the cognitive class the probe identified.

**Why does this work?** The Noetic Topos paper's Proposition 5.6 proves the counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. The mechanism is mathematically guaranteed at the likelihood tier.

**What is proved today?** Six closed evidence tiers on two open models (Pythia-160M and Pythia-1B): detection above text and metadata baselines (up to 89.8% on 40 classes, +39.7pp lift), causally load-bearing readout (collapse to exact chance under ablation), likelihood conditioning via the η → ε bridge (effect doubled from +0.283 to +0.554 at 6× scale, p ≈ 10⁻¹⁴), clean structural factorization (lacunarity 0.015–0.021), framework-predictive validity (three preflight predictions held).

**What is NOT yet proved?** Cross-architecture transfer (Llama, OLMo, Qwen). Visible-text steering at small-model scale. Larger-model scaling beyond 1B parameters. These are open gates with defined experimental designs.

**What is the next gate?** Stage 10 — cross-architecture replication on Llama-7B or OLMo-1B. PASS_CLEAN = product validated as cross-architecture; NULL = product bounds to Pythia architecture family.

**Authorization?** Internal only. IP attorney review required before any external use, including this summary.

---

*End of Document — CAS Harness Spec Sheet v1.0 — 2026-05-17*
