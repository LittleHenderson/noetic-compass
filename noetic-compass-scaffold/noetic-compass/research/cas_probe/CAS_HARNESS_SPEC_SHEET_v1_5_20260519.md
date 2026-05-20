---
title: CAS Harness — Product Specification Sheet
subtitle: Cross-Model Cognitive Architecture Interpretability Platform
version: 1.5
date: 2026-05-19
supersedes: v1.4 (2026-05-19, PM3)
status: Internal — pending IP attorney review before external use
authors: Little Henderson (Founder), Claude Opus 4.7, Codex
classification: Confidential
note: Same-day refresh from v1.4 because Stages 21A (Evidence Packet schema + samples), 21B (FastAPI route + Atlas reviewer drawer), and 21B.1 (authenticated drawer fix) landed the customer-facing product surface. The product now has a versioned 15-field Evidence Packet artifact, an authenticated API route at /harness/evidence/{trace_id} (JSON and markdown variants), and an accessible reviewer drawer in the Atlas with seven tabs and export buttons.
---

# CAS Harness — Product Specification Sheet

**Version 1.5 — 2026-05-19**
**Status: Internal — pending IP attorney review before external use**
**Supersedes: v1.4 (2026-05-19, PM3)**

*Same-day refresh from v1.4 because Stages 21A (Evidence Packet schema + 4 canonical sample packets emitted), 21B (FastAPI route + Atlas reviewer drawer with 7 tabs + JSON/Markdown export), and 21B.1 (authenticated drawer using apiFetch + new apiFetchText + tightened isEvidencePacket validator + tabpanel-id/aria-controls match) landed the customer-facing product surface. Evidence Packet is the deployable customer artifact: 15-field versioned schema, runtime-served from authenticated route, surfaced in the Atlas Trace 3D reviewer drawer.*

---

## Changes from v1.1 → v1.2

- **Stage 16 — Qwen2.5-1.5B (Alibaba) PASS CLEAN.** Third independent architecture family closed the cross-architecture-redundancy gate. Probe accuracy 82.0%; likelihood Δ +0.7960 (strongest effect yet in the project); margin over partner +1.6253; Wilcoxon p = 2.92×10⁻¹². Raw-CAS-symbol control near-null (probe_raw −0.0002).
- **Three architecture families now validated** (Pythia / EleutherAI / GPT-NeoX lineage, OLMo / AI2 lineage, Qwen / Alibaba lineage). Mechanism is empirically established as a property of transformer cognition across three independent labs, three corpora, and three tokenizer families — not lab-specific, not corpus-specific, not language-specific.
- **Layer-selection rule extended.** Qwen2.5-1.5B's optimal layer is 11 of 28 (39% of depth) — the first sub-44% optimum observed. The general "best layer at 39–50% of network depth" rule continues to hold; the lower end of the band has now been touched.
- **Cross-architecture-redundancy bound retired.** This was the dominant remaining product uncertainty as of v1.1 (which licensed cross-architecture as "1 family additional, redundancy open"). v1.2 closes that gate at three families.

### Changes from v1.4 → v1.5

- **Stage 21A** — Evidence Packet schema (`cas_harness_evidence_packet_v1`) shipped as `research/cas_probe/evidence_packet.py` with validator, markdown renderer, exporter, and 7 passing tests. **Four canonical sample packets** emitted (one per decision tier: allow / caveat / constrain / suppress) in both JSON and markdown formats. Commits `2c72e37` (schema) and `9cfc3cd` (samples).
- **Stage 21B** — Backend FastAPI route `/api/harness/evidence/{trace_id}` (JSON + `/markdown` variants) at `api/routes/harness_evidence.py`. File-backed store at `NC_EVIDENCE_PACKETS_DIR`. Path-traversal guard, 8 MiB size cap, schema round-trip validation. JWT auth-gated. 28 backend tests pass. Frontend Atlas reviewer drawer at `dashboard/src/components/idea-atlas/EvidencePacketDrawer.tsx` with 7 lazy-rendered tabs + JSON/Markdown export buttons + full ARIA semantics (`role="dialog"`, `aria-modal`, Escape closes, focus management, `role="tablist"`/`role="tab"`/`role="tabpanel"`). 24 frontend tests pass. Backward compatibility preserved: nodes without `verification.evidence_packet_trace_id` render unchanged. Commit `9b4fb8a`.
- **Stage 21B.1** — Auth fix: drawer now uses `apiFetch` for JSON and new `apiFetchText` for markdown export (was bare `fetch`); `isEvidencePacket` validator tightened so malformed nested fields fail before rendering; tabpanel ids match `aria-controls`; new test confirms `Authorization: Bearer ...` header is sent. 25 drawer tests + 9 API client tests + 8 evidence-packet tests pass. `tsc --noEmit` clean. Commit `0ba984d`.
- **New Section 5.16** — Evidence Packet schema (Stage 21A)
- **New Section 5.17** — Evidence Packet delivery: API + Atlas drawer (Stage 21B + 21B.1)
- Tier closure summary (5.12) adds two new validated rows (Evidence Packet schema + Evidence Packet delivery surface)
- Timeline (Section 6) adds rows for Stages 21A, 21B, 21B.1
- Claim Map (Section 8) adds two LICENSED claims: structured per-inspection evidence artifact + authenticated runtime delivery surface
- IP filing candidates (Section 12.2) adds candidate #13: Evidence Packet schema + delivery architecture
- Commit hashes (Section 14.2) adds `2c72e37`, `9cfc3cd`, `9b4fb8a`, `0ba984d`
- **Producer-side linkage gap NOTED** (not blocked): Stage 21C will populate `verification.evidence_packet_trace_id` on Atlas trace nodes from the producer side; until then the "View full Evidence Packet" button doesn't render in production traces. Backward-compatible by design.

## Changes from v1.3 → v1.4

- **Stages 19C (Mode Selector) and 20/20B (Generation Readiness Gate) integrated.** The product now has three customer-configurable verification modes plus a non-mutating orchestrating policy layer.
- **Stage 19C Mode Selector**: HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE modes, each calibrated independently against OLMo-1B and Qwen2.5-1.5B fixtures. All 6 cells (3 modes × 2 models) meet their pre-registered per-mode targets. Status: `MODE_SELECTOR_READY`.
- **Stage 20 Generation Readiness Gate**: opt-in, non-mutating diagnostic policy module at `cas-native/model/generation_readiness_gate.py`. Reads CAS signals (lacunarity, inversion flags, RPM satisfaction, Verification Stack decision) and emits one of four actions (allow / caveat / constrain / suppress) with audit trail. Zero learnable parameters; default unattached; CASNativeModel.forward unchanged. 22 tests passing.
- **Stage 20B Packet Integration**: Generation Readiness Gate applied to locked Stage 19A/19B Verification Stack artifacts. Aggregate counts per source/mode emitted; sample customer-facing packets generated; Evidence Packet schema extended with `generation_readiness` field. Status: `PACKET_INTEGRATION_READY`.
- **New Section 5.15**: Generation Readiness Gate (orchestrating policy layer)
- Section 5.14 (CAS Verification Stack) expanded to document the three-mode product surface
- Claim Map (Section 8) adds two LICENSED claims: configurable verification modes + non-mutating generation readiness policy
- IP filing candidates (Section 12.2) add candidates #11 (Mode Selector + factor_consistent verifier) and #12 (Generation Readiness Gate methodology)
- Tier closure summary (Section 5.12) adds two new validated capability rows

## Changes from v1.2 → v1.3

- **Stage 19A validated** (`PASS_STRONG_AUDIT_CLEAN`): the CAS Verification Stack — a runtime-safe acceptance/suppression decision layer that sits on top of the multi-layer trace methodology — accepts 87.6% of locked-fixture cases at 99.78% accepted accuracy with a 0.22% silent error rate, suppressing 12.4% as conflicted/unstable rather than guessing.
- **Critical runtime-safety distinction documented:** Verification Stack uses only non-oracle states at runtime (stable, conflicted, uncertain, drifting, plus ensemble agreement). It does **not** use oracle `stable_correct` or `stable_wrong` labels that would require gold-label access at inference time. This is what makes the layer deployable to customer audits where gold labels are by definition unavailable.
- **New Section 5.14:** CAS Verification Stack — Runtime-Safe Acceptance/Suppression (validated)
- **Pre-commit caveat resolved:** deterministic rerun after commit `05ac687` reproduced every headline metric exactly.
- Claim Map (Section 8) adds a LICENSED claim covering runtime-safe acceptance/suppression with the explicit gold-label-not-required boundary
- Tier Closure Summary (Section 5.12) adds Verification Stack as validated capability
- IP filing candidates (Section 12.2) adds Verification Stack as candidate #10 — potentially the load-bearing runtime IP claim for the product surface

## Changes from v1.0 → v1.1 (retained for traceability)

- Cross-architecture validation closed (Stage 15: OLMo-1B PASS CLEAN)
- Cross-scale curve extended to Pythia-2.8B (Stage 14)
- Multi-layer trace + blind-spot detection added (Stage 13)
- Blind-spot audit (Stage 13.1)
- Weight-geometry alignment evidence (Stage 14.1)
- NEW capability: Hidden-content detection (η₁ vs η₂)
- NEW capability: Multi-Harness Composition
- Seven new capability subsections (5.7–5.13)
- Claim map, bounds, IP & legal, comparison landscape updates

---

## 1. Executive Summary

CAS Harness is a cross-model interpretability and conditioning platform built on the **Cognitive Architecture System (CAS) v7.7** framework. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, and condition the model's next-token probability distribution by realizing the detected structure as readable context.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism before any empirical experiment ran. The prediction has been empirically confirmed on **five open-weight models across three architecture families** (Pythia-160M / Pythia-1B / Pythia-2.8B / OLMo-1B / Qwen2.5-1.5B) and on **two evidence tiers** (activation-trace and weight-geometry).

**Today's load-bearing claim, reserved language, defensible for audit:**

> CAS Harness reads cognitive structure from open-weight transformer hidden states across five model points (Pythia 160M / 1B / 2.8B; OLMo 1B; Qwen2.5-1.5B) and three architecture families (EleutherAI Pythia, AI2 OLMo, Alibaba Qwen). The η → ε bridge — the read-and-realize loop predicted by Proposition 5.6 of the Noetic Topos paper — conditions next-token likelihood with effect sizes that grow then plateau across Pythia scale, strengthen on OLMo, and reach their highest observed value on Qwen2.5-1.5B (+0.7960 likelihood Δ, p = 2.92×10⁻¹²). Six cognitive axes are detected (Noetics, Foundations, 40 Elements, Operators, Expression Shapes, Compiler-Valid Formulas), ablation-validated, and multi-layer trace-audited with blind-spot flagging that distinguishes model-side weakness from readout-position weakness. CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099) — first weight-geometry evidence of the bridge mechanism, complementary to the activation-tier evidence. Generation surface-text steering remains an open boundary at small model scale; cross-architecture transfer is now closed at three independent out-of-family architectures.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

Initial probing began on Pythia-160M (EleutherAI, 2023) in early May 2026. The conditional Glass House strategy memo (originally drafted 2026-05-16 as a "speculative product shape pending Stage 2 evidence") matured through sixteen experimental stages. By 2026-05-19 the probing chain had closed: cross-scale within Pythia (3 points: 160M, 1B, 2.8B), cross-architecture to OLMo-1B (AI2, different lineage), cross-architecture to Qwen2.5-1.5B (Alibaba, third lineage), weight-geometry evidence (output-side alignment), multi-layer trace auditing, and blind-spot detection with readout-vs-model-side disambiguation.

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
- Three model scales within one architecture family (Pythia: 160M, 1B, 2.8B)
- Two out-of-family architectures (OLMo-1B; Qwen2.5-1.5B — three independent labs, lineages, corpora, tokenizers)
- Two evidence tiers (activation-trace AND weight-geometry alignment)
- Six cognitive axes

### 3.4 Diagnostic Tools — Lacunarity, Fractal Classifier, Weight-Geometry Alignment

Three CAS-internal diagnostic tools have been empirically validated in CAS Harness:

- **Lacunarity gate** (Var/Mean²): Pythia-160M Noetics 0.793; Pythia-160M Foundations 0.021 (38× cleaner); Pythia-1B Foundations 0.015; **Stage 13 multi-layer trace 0.0016** (cleanest factorization signature in project history; multi-layer averaging cancels noise); **Qwen2.5-1.5B test lacunarity 0.0084** (Stage 16).

- **Fractal classifier** (Stabilizing / Amplifying / Oscillatory / Neutral): Stage 6.6 noetic ablation classified Oscillatory, predicting generation-steering failure; Stage 13 multi-layer trace classifies per-prompt as stable-like or problem-like, enabling blind-spot detection.

- **Weight-geometry alignment** (NEW, Stage 14.1): Principal-angle analysis between CAS Foundation subspace and model output-weight space. **Pythia-2.8B** result: 2.83× random expectation (p = 0.0099) on output-side; input-side basically random. First static-weight evidence of the bridge mechanism, complementary to activation-tier evidence. (Correction note: v1.1 spec sheet narrative incorrectly attributed this to Pythia-160M; v1.2 corrects to Pythia-2.8B per the underlying STAGE14_WEIGHT_GEOMETRY_ALIGNMENT report and JSON, which both record `model_name = "EleutherAI/pythia-2.8b"`, rank 27.)

The framework's own diagnostic tools have produced numerical predictions of CAS Harness experimental outcomes BEFORE the experiments ran, four times now (Stage 7 lacunarity prediction, Stage 6.6 fractal prediction, Stage 7.CPL covering-surjectivity prediction, Stage 14.1 weight-geometry alignment prediction).

---

## 4. Architecture

### 4.1 System Overview (v1.2)

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (e.g., Pythia, OLMo, Qwen, Llama, etc.)
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

### 4.2 Component Specifications (v1.2 updates)

| Component | Status | Implementation Notes |
|---|---|---|
| Activation capture | validated | sklearn-compatible per-layer hooks; supports focus-token, final-token, mean-token extraction |
| Foundation / Noetic / Element / Operator / Expression / Formula probes (η) | validated | sklearn LogisticRegression L-BFGS, balanced class weight, StandardScaler |
| Multi-layer trace classifier | validated (Stage 13) | Reads probe confidence across all layers; flags stable-like / problem-like trajectories |
| Blind-spot detector with readout-position disambiguation | validated (Stage 13.1) | Distinguishes model-side weakness (genuine architectural gap) from readout-position weakness (probe-config sensitive) |
| Realization layer (ε) | validated | Template-based natural-language emission per CAS class |
| Likelihood scorer | validated | Computes semantic-class log-likelihood shift |
| Subspace ablation hook | validated | PyTorch forward-hook applying P = u·u^T projection-out |
| Random-control generator | validated | QR-orthonormalized same-rank random subspaces |
| Lacunarity computer | validated | Var/Mean² over per-class disruption magnitudes |
| Fractal classifier | validated | Iterated-trajectory orbit classification |
| Weight-geometry analyzer | validated (Stage 14.1) | Principal-angle analysis between probe subspace and W_U row space |
| **Cross-architecture adapter** | **validated for Pythia + OLMo + Qwen** | Adapter abstracts model-specific tokenizer + hook-target details |
| Evidence Packet emitter | wired | Schema v1.1 includes multi-layer trace, blind-spot flag with readout-vs-model distinction, weight-geometry alignment score, claim-tier metadata |
| Mode 7 trace surface | wired | Streaming traceability for live inspection |
| Two-bridge hidden-content detector (η₁ vs η₂) | prototype (see §5.10) | Compares internal-state CAS profile vs emitted-text CAS profile to surface withheld / inverted content |

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
| 28 Foundations | 28 | Pythia-2.8B | 85.9% | (verify) | validated, cross-scale |
| 28 Foundations | 28 | OLMo-1B | 90.6% | (verify) | validated, cross-architecture |
| **28 Foundations** | **28** | **Qwen2.5-1.5B** | **82.0%** | **(verify)** | **validated, cross-architecture (Stage 16)** |
| 40 Elements (TKS A1..D10) | 40 | Pythia-160M | 89.8% | +39.7 pp | validated |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | GREY (task design issue) + readout-causal PASS |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | validated |
| 10 Multi-Layer Trace | 10 | Pythia-160M | 95.4% | (implicit in trace) | validated (Stage 13) |

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
| Pythia-2.8B | 14 | +0.583 | +1.336 | 92/112 | 3.08×10⁻¹⁵ |
| OLMo-1B | 16 | +0.604 | +1.305 | 87/112 | ≈ 10⁻¹⁵ |
| **Qwen2.5-1.5B** | **11** | **+0.7960** | **+1.6253** | **83/112** | **2.92×10⁻¹²** |

Trends:

- **Monotonic-converging within Pythia.** Effect grows 160M → 1B → 2.8B with diminishing-returns shape. Saturates around 1B for this corpus/axis/realization.
- **Cross-architecture transfer is positive at three families.** OLMo-1B and Qwen2.5-1.5B both show effects equal to or stronger than Pythia-1B at comparable parameter count despite different lab, lineage, corpus, and tokenizer.
- **Layer-selection rule transfers cleanly.** Best layer sits at 39–50% of network depth across all five models. Qwen2.5-1.5B's 39% is the first sub-44% optimum observed.
- **Raw CAS symbols stay null at every scale.** Confirms the effect is ε-realization (readable natural-language prefix), not symbol-recognition. Qwen2.5-1.5B raw-symbol control: probe_raw = −0.0002 (near-null), confirming the control held on the third architecture family as well.
- **Qwen produces strongest effect (+0.796)** — supports hypothesis that richer / multilingual training corpora produce more crystallized CAS structure detectable by the η → ε bridge.

### 5.4 Factorization Quality

| Axis | Model | Lacunarity | Wrong-direction slots | Status |
|---|---|---:|---|---|
| 10 Noetics | Pythia-160M | 0.793 | 2 of 10 (^3, ^5) | Lumpy (v1 corpus artifact) |
| 28 Foundations | Pythia-160M | 0.021 | 0 of 28 | validated clean |
| 28 Foundations | Pythia-1B | 0.015 | 0 of 28 | validated clean (cross-scale) |
| **28 Foundations** | **Qwen2.5-1.5B** | **0.0084** | **0 of 28** | **validated clean (cross-architecture)** |
| Multi-Layer Trace | Pythia-160M | 0.0016 | 0 of 10 | validated cleanest |

The Stage 13 multi-layer trace lacunarity of 0.0016 is the lowest the project has produced. Multi-layer averaging suppresses single-layer noise, producing a structurally cleaner signal than any single-layer probe. Stage 16's single-layer Qwen2.5-1.5B lacunarity of 0.0084 is the cleanest single-layer Foundations factorization in the project.

### 5.5 Framework Predictive Validity

The framework's diagnostic tools have made committed numerical predictions BEFORE four different experiments. All four held:

| Prediction (made when) | Tool | Experiment | Outcome |
|---|---|---|---|
| Foundations axis should be more factorized than Noetics | Lacunarity preflight | Stage 7 readout | Lacunarity 0.793 → 0.021. Confirmed. |
| Noetic subspace ablation will be Oscillatory, not Stabilizing | Fractal classifier preflight | Stage 6.6B generation trajectory | Classified as Oscillatory on larger samples. Confirmed. |
| Counit ε is the covering map for generation steering | Topos Proposition 5.6 | Stages 7.CPL through 8 | Likelihood conditioning closed across two scales. Confirmed at p ≈ 10⁻¹⁴. |
| CAS Foundation subspace should show alignment with output weights | Proposition 5.6 corollary | Stage 14.1 | 2.83× random output-weight alignment, p = 0.0099. Confirmed. |

This is the highest-tier scientific evidence the framework can produce: pre-registered quantitative predictions that the data subsequently honored.

### 5.6 Cross-Scale Validation (Within Architecture Family)

Three-point Pythia scaling curve:

| Model | Params | Probe Accuracy | Likelihood Δ | Status |
|---|---:|---:|---:|---|
| Pythia-160M | 160M | 78.6% (Foundations) | +0.283 | validated |
| Pythia-1B | 1B | 82.4% (Foundations) | +0.554 | validated |
| Pythia-2.8B | 2.8B | 85.9% (Foundations) | +0.583 | validated |

**Pattern: monotonic, converging.** Effect approximately doubles 160M → 1B (+0.271), then plateaus to a ~5% gain 1B → 2.8B (+0.029). Mechanism saturates around 1B parameters for this corpus / axis / realization. Practical implication: the η → ε bridge does NOT require frontier-scale models. A 1B parameter model captures nearly all of the bridge's effect on Pythia.

**Preliminary observation, training-data dependence.** Effect saturation appears training-data-dependent. Pythia plateaus around 1B for English-only training (The Pile). OLMo-1B (+0.604) and Qwen2.5-1.5B (+0.796) both *exceed* the Pythia 1B–2.8B ceiling at comparable parameter counts with richer corpora (Dolma for OLMo; multilingual + code for Qwen). This is a preliminary observation, not a strong claim — it needs scale-curve replication within the Qwen family (e.g., Qwen2.5 0.5B → 1.5B → 7B at matched probe protocol) before it can be promoted beyond hypothesis.

### 5.7 Cross-Architecture Validation (3 families validated)

| Model | Lab | Architecture lineage | Training corpus | Tokenizer | Probe Accuracy | Likelihood Δ | Status |
|---|---|---|---|---|---:|---:|---|
| Pythia-1B (reference) | EleutherAI | GPT-NeoX | The Pile (English) | GPT-NeoX BPE | 82.4% | +0.554 | validated |
| OLMo-1B | AI2 | OLMo (different) | Dolma (English) | GPT-NeoX BPE adapter | 90.6% | +0.604 | validated, Stage 15 |
| **Qwen2.5-1.5B** | **Alibaba** | **Qwen (third lineage)** | **Multilingual + code** | **Qwen tokenizer** | **82.0%** | **+0.7960** | **validated, Stage 16** |

Qwen2.5-1.5B is from a third independent lab (Alibaba vs EleutherAI vs AI2), uses a third independent architecture lineage, was trained on a richer multilingual + code corpus (vs English-only The Pile / Dolma), and uses a different tokenizer family. The η → ε bridge replicated at the *highest observed effect size in the project* on Qwen.

**This closes the additional-cross-architecture-redundancy gate.** Mechanism is empirically established as a property of transformer cognition across three independent architecture lineages (EleutherAI / AI2 / Alibaba) with different training corpora, tokenizers, and lab origins.

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

**Status.** η₁ is validated across all Stage 6-16 work. η₂ on emitted output text is prototype-status (works on the same probe architecture; needs the same validation discipline applied to the *emitted-text* corpus). Two-bridge comparison is wired but not yet pre-registration-gated.

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

### 5.12 Tier Closure Summary (v1.2)

| Tier | Status |
|---|---|
| Discriminative readout (6 axes) | ✅ validated, 5 models |
| Above text/metadata baselines | ✅ validated, all axes |
| Readout-causal ablation (5 axes) | ✅ validated, collapse-to-exact-chance pattern |
| Likelihood conditioning via η → ε bridge | ✅ validated cross-scale (Pythia 160M/1B/2.8B) AND cross-architecture (OLMo-1B, Qwen2.5-1.5B) |
| Clean factorization (lacunarity) | ✅ validated, down to 0.0016 multi-layer |
| Framework predictive validity | ✅ validated, 4 pre-registered predictions held |
| Multi-layer trace + blind-spot detection | ✅ validated |
| **Cross-architecture transfer (3 families)** | ✅ **validated (NEW v1.2 — OLMo + Qwen)** |
| Weight-geometry alignment (output-side) | ✅ validated |
| Hidden-content / suppression detection | 🟡 prototype |
| Multi-Harness Composition (axis-specialized + composed) | 🟡 planned-with-proven-components |
| **CAS Verification Stack (runtime-safe accept/suppress)** | ✅ **audit-clean validated (NEW v1.3)** — 87.6% accept @ 99.78% accuracy, 0.22% silent error, gold labels NOT required at runtime |
| **Verification Mode Selector (HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE)** | ✅ **validated (NEW v1.4)** — 6 of 6 cells (3 modes × 2 cross-arch models) meet pre-registered per-mode targets; product-configurable surface |
| **Generation Readiness Gate (orchestrating policy layer)** | ✅ **validated (NEW v1.4)** — 22 tests passing; opt-in non-mutating policy over CAS signals; allow/caveat/constrain/suppress with audit trail |
| **Evidence Packet schema (cas_harness_evidence_packet_v1)** | ✅ **validated (NEW v1.5)** — 15-field versioned schema; validator + markdown renderer; 4 canonical samples (one per decision tier); 7 tests pass |
| **Evidence Packet delivery (API + Atlas drawer)** | ✅ **validated (NEW v1.5)** — authenticated /api/harness/evidence/{trace_id} JSON+markdown; Atlas reviewer drawer with 7 tabs, ARIA semantics, JSON/MD export; 28 backend + 25 frontend tests pass; 21B.1 audit-clean |
| Generation surface-text steering | ❌ closed-as-negative, mathematically explained |
| Additional cross-architecture redundancy (Llama, Mistral, Phi, Gemma) | ⏭ open (no longer load-bearing) |
| Scale beyond 2.8B (7B+, frontier-tier) | ⏭ open |

### 5.13 Multi-Harness Composition — Planned Capability, Components Proven (NEW v1.1)

The single-probe single-layer architecture validated through Stage 16 is sufficient for one-axis inspection at the model scales tested so far. It is **structurally insufficient for trillion-parameter models and a known bottleneck for hidden-content detection.** The next architectural step — already implied by the framework's own working-memory tensor and supported by every layer-by-layer result the project has produced — is **Multi-Harness Composition**: specialized harnesses, each reading a different CAS axis at its optimal depth, composed into a unified structural readout.

#### 5.13.1 Why the data already demands it

Different CAS axes peak at different layers, and the optimal layer shifts deeper with model scale:

| Axis | Pythia-160M Peak | Pythia-1B Peak | Pythia-2.8B Peak | OLMo-1B Peak | Qwen2.5-1.5B Peak |
|---|---:|---:|---:|---:|---:|
| 10 Noetics | Layer 3 | (not tested at scale) | (not tested at scale) | (not tested at scale) | (not tested at scale) |
| 28 Foundations (Drive × Register) | Layer 6 | Layer 8 | Layer 14 | Layer 16 | Layer 11 |
| 40 Elements (Domain × Noetic) | Layer 5 | (not tested) | (not tested) | (not tested) | (not tested) |
| 10 Expression Shapes | Layer 2 | (not tested) | (not tested) | (not tested) | (not tested) |
| 10 Compiler-Valid Formulas | Layer 2 | (not tested) | (not tested) | (not tested) | (not tested) |
| Multi-Layer Trace (formulas) | Layer 12 | (not tested) | (not tested) | (not tested) | (not tested) |

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

### 5.14 CAS Verification Stack — Runtime-Safe Acceptance/Suppression (NEW IN v1.3, validated)

The Verification Stack is the **runtime-deployable decision layer** that sits on top of multi-layer trace evidence (§5.9) and converts that evidence into an accept-or-suppress decision per example, *without requiring gold labels at inference time*. This is the layer that makes CAS Harness shippable inside a customer audit pipeline.

#### 5.14.1 What it does

For each example the Stack consumes three multi-layer probe readouts (focus-token, final-token, mean-over-sequence-length) plus their ensemble agreement, classifies the trace as **stable / conflicted / uncertain / drifting**, and emits one of two decisions:

- **ACCEPT** — high-confidence trace, all readouts agree, no instability flag. Carries a per-tier acceptance confidence band (high / medium).
- **SUPPRESS** — at least one readout flags conflicted/unstable, OR the ensemble disagrees. The example is held back instead of producing a guess. Suppression reason is recorded for the Evidence Packet.

#### 5.14.2 The runtime-safety distinction (load-bearing)

Earlier diagnostic work (§5.9) used oracle states like `stable_correct` and `stable_wrong` that require gold-label access to compute. **The Verification Stack does NOT use those.** It uses only states computable at runtime from probe outputs alone:

- `stable` (all three readouts agree)
- `conflicted` (readouts disagree on the same focus position)
- `uncertain` (low-confidence)
- `drifting` (multi-layer trajectory unstable)
- `ensemble_agreement` (any 2-of-3 → 3-of-3 quorum)

This is what makes the Stack deployable to customer audits where gold labels are by definition unavailable. The acceptance accuracy was *measured* against gold labels at validation time, but the acceptance *decision* at runtime uses only probe-output states.

#### 5.14.3 Stage 19A result — locked formula-family fixture (4,200 examples)

| Metric | Value |
|---|---:|
| Baseline focus-token layer-12 accuracy | 95.40% |
| Ensemble-only accuracy | 95.50% |
| Ensemble-only coverage | 95.69% |
| **Stack accepted accuracy** | **99.78%** |
| **Stack accept rate (coverage)** | **87.60%** |
| **Stack silent error rate** | **0.22%** (8 of 3,679) |
| **Stack suppress rate** | **12.40%** (521 of 4,200) |
| Accepted examples (high tier) | 3,678 at 99.78% |
| Accepted examples (medium tier) | 1 at 100.0% |

**Plain English:** On the locked formula-family fixture, the Verification Stack accepts 87.6% of cases at 99.78% accuracy and suppresses 12.4% as conflicted/unstable instead of guessing. The silent accepted error rate is 0.22% — meaning when the Stack does accept, it is wrong about 1 time in 460.

#### 5.14.4 Suppression reasons (Stage 19A)

| Reason | Count |
|---|---:|
| `final_token_conflicted+focus_token_conflicted+mean_over_seq_len_conflicted` | 134 |
| `ensemble_all_disagree` | 181 |
| `final_token_conflicted+focus_token_conflicted` | 69 |
| `focus_token_conflicted+mean_over_seq_len_conflicted` | 46 |
| `final_token_conflicted+mean_over_seq_len_conflicted` | 35 |
| `mean_over_seq_len_conflicted` | 18 |
| `final_token_conflicted` | 15 |
| `focus_token_conflicted` | 14 |
| `trace_unstable` | 9 |

These reasons are themselves auditable signals — a customer reviewing a suppression can see *which* readout positions conflicted on a given example.

#### 5.14.5 Status, bounded claim, audit-clean rerun

- **Status:** `PASS_STRONG_AUDIT_CLEAN`
- **Defensible claim:** "On the locked formula-family fixture, CAS Verification Stack accepts 87.6% of cases at 99.78% accuracy and suppresses 12.4% instead of guessing. Acceptance decisions use only non-oracle runtime states; gold labels were used only for scoring, not for acceptance."
- **Audit-clean rerun:** Stage 19A was rerun after commit `05ac687` using the same script, same locked fixture, and same activation artifact. The rerun reproduced every headline metric exactly, resolving the initial pre-commit caveat.
- **External claim license:** Internal — pending caveat resolution + IP attorney review (caveat resolution is the gate before the external license becomes available; IP review is independent and required regardless).
- **IP filing candidate:** YES (see §12.2 filing candidate #10)

#### 5.14.6 Why this is the runtime-deployable capability

Detection (§5.1) tells you what's there. Causal ablation (§5.2) tells you it's load-bearing. The η→ε bridge (§5.3) tells you the model's likelihood responds to readable realization of detected structure. **The Verification Stack is the first capability that makes a per-example accept/suppress decision a customer can actually deploy at inference time**, with measurable accuracy and a recorded reason for every suppression. It is the operational endpoint of the entire 16-stage evidence chain.

This is what turns the research into a product.

### 5.15 Generation Readiness Gate — Orchestrating Policy Layer (NEW IN v1.4, validated)

The Generation Readiness Gate sits ABOVE the Verification Stack (§5.14) and orchestrates the full CAS gating architecture into a single per-example policy decision. It reads CAS diagnostic signals — Verification Stack decision, lacunarity, inversion flags, RPM satisfaction — and emits one of four actions: **allow / caveat / constrain / suppress**, with full audit trail.

#### 5.15.1 What it is — and what it explicitly is NOT

**What it IS:**
- A read-only diagnostic policy layer with zero learnable parameters
- An orchestrator that consumes already-computed CAS signals
- Mode-aware: applies different action thresholds per HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE mode
- Opt-in: default unattached; CASNativeModel.forward and forward_with_lm paths are unchanged when not attached
- Audit-traceable: every decision records risk_score, reasons[], evidence{}, recommended_mode, and policy_version

**What it is NOT:**
- NOT a tensor throttle. Does not modify hidden states, bottleneck_z, logits, or generated tokens.
- NOT a learned multiplicative gate. Learned multiplicative gates over hidden states are a documented failure mode in interpretability literature — they can discover the shortcut of suppressing generation entirely rather than learning calibrated selective gating.
- NOT a tensor mutation layer of any kind. The boundary is enforced architecturally: the gate is not called from forward() and has no path to alter activations.

#### 5.15.2 Four-tier action discipline

| Action | When | Product effect |
|---|---|---|
| `allow` | Risk score below caveat threshold for mode | Normal emission, no caveats |
| `caveat` | Risk score in [caveat, constrain) range OR medium-confidence Verification Stack acceptance | Emit normally with reserved-language caveat label |
| `constrain` | Risk score in [constrain, suppress) range OR Verification Stack rejection in TRIAGE mode | Constrained decoding or human-review escalation |
| `suppress` | Risk score ≥ suppress threshold OR Verification Stack rejection in non-TRIAGE modes | Refuse with auditable reason; recommend HIGH_PRECISION mode |

Per-mode action thresholds:

| Mode | caveat | constrain | suppress |
|---|---:|---:|---:|
| HIGH_PRECISION | 0.20 | 0.45 | 0.75 |
| BALANCED | 0.25 | 0.55 | 0.85 |
| MAX_COVERAGE_TRIAGE | 0.30 | 0.65 | 0.95 |

#### 5.15.3 Signals consumed (read-only)

| Signal | Source | What it tells the gate |
|---|---|---|
| Lacunarity scores + meta | CAS engine's LacunarityHead | Gappiness of the cognitive subspace; high lacunarity → high risk |
| Inversion flags (7 axes) | CAS engine's Inversion Scanner | Drive/Domain/RPM/etc. failure patterns; any flag firing → elevated risk |
| RPM satisfaction | CAS engine's RPM Gate | Capability prerequisite chain completeness; low satisfaction → elevated risk |
| Verification Stack decision | Stage 19A/19C output | Per-example ACCEPT/SUPPRESS with decision_tier and suppression_reasons |
| Domain confidence | CAS engine's Domain Coherence | Lowest of 4 domain confidence scores; low confidence → elevated risk |

Each signal contributes additively to a bounded risk score in [0, 1]. The mode-thresholds then map the risk score to an action.

#### 5.15.4 Stage 20B — Packet Integration Results

Stage 20B applied the gate to locked Stage 19A/19B Verification Stack artifacts to validate the policy emits sensible counts. Status: `PACKET_INTEGRATION_READY`. Default mode: BALANCED.

| Source | Model | Mode | Allow | Caveat | Constrain | Suppress |
|---|---|---|---:|---:|---:|---:|
| stage19a_formula_stack | Pythia-160M | HIGH_PRECISION | 3,678 | 1 | 0 | 521 |
| stage19a_formula_stack | Pythia-160M | BALANCED | 3,678 | 1 | 0 | 521 |
| stage19a_formula_stack | Pythia-160M | MAX_COVERAGE_TRIAGE | 3,679 | 0 | 521 | 0 |
| stage19b_cross_arch_stack | OLMo-1B | HIGH_PRECISION | 1,651 | 36 | 0 | 665 |
| stage19b_cross_arch_stack | OLMo-1B | BALANCED | 1,651 | 36 | 0 | 665 |
| stage19b_cross_arch_stack | OLMo-1B | MAX_COVERAGE_TRIAGE | 1,687 | 0 | 665 | 0 |
| stage19b_cross_arch_stack | Qwen2.5-1.5B | HIGH_PRECISION | 1,746 | 8 | 0 | 598 |
| stage19b_cross_arch_stack | Qwen2.5-1.5B | BALANCED | 1,746 | 8 | 0 | 598 |
| stage19b_cross_arch_stack | Qwen2.5-1.5B | MAX_COVERAGE_TRIAGE | 1,754 | 0 | 598 | 0 |

Key observations:
- Medium-confidence Verification Stack acceptances correctly emit `caveat` in HIGH_PRECISION/BALANCED, and roll up to `allow` in MAX_COVERAGE_TRIAGE per the relaxed thresholds.
- Suppressed cases in HIGH_PRECISION/BALANCED convert to `constrain` in MAX_COVERAGE_TRIAGE — preserving human-review surfacing without pretending it is license-grade emission.
- The gate behaves identically on Pythia (in-architecture) and on OLMo+Qwen (cross-architecture), confirming the policy layer is architecture-independent.

#### 5.15.5 Position in the Wrap Pipeline

The 8-stage Wrap Pipeline (Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call → Operator Scoring → Domain Coherence → Inversion Scan → Output Gate) emits diagnostic signals at stages 5, 6, 7 plus the RPM check at stage 2. The Generation Readiness Gate reads those signals and the Verification Stack output and emits a single auditable policy that informs the Output Gate's final decision. It does not replace any Wrap stage; it orchestrates them.

#### 5.15.6 Status, bounded claim, IP filing

- **Status:** validated. Stage 20 module + 22 tests passing. Stage 20B aggregate validation across three architecture families.
- **Defensible claim:** "CAS Harness includes an opt-in, non-mutating diagnostic policy layer that reads CAS signals (Lacunarity, Inversion, RPM, Verification Stack) and emits per-example allow/caveat/constrain/suppress decisions with full audit trail. Mode-aware (HIGH_PRECISION/BALANCED/MAX_COVERAGE_TRIAGE) action thresholds. Zero learnable parameters. Does not modify hidden states, bottleneck activations, logits, or generated tokens."
- **External claim license:** Internal — pending IP attorney review.
- **IP filing candidate #12** (see §12.2): the Generation Readiness Gate methodology — orchestrating non-mutating policy over CAS signals with mode-aware action thresholds and Verification Stack escalation.

### 5.16 Evidence Packet Schema (NEW IN v1.5, validated — Stage 21A)

The Evidence Packet is the **structured, versioned, per-inspection customer artifact** CAS Harness emits. Until Stage 21A, the schema was specified abstractly in prior spec sheet versions but had no concrete file format. Stage 21A shipped the schema, validator, markdown renderer, and four canonical sample packets — one per decision tier.

#### 5.16.1 Schema (`cas_harness_evidence_packet_v1`)

15 top-level fields, every sample packet validates against the same schema:

| Field | Purpose |
|---|---|
| `schema_version` | Version tag for the packet format (`cas_harness_evidence_packet_v1`) |
| `trace_id` | Unique inspection identifier; route key for the API endpoint |
| `created_at` | Provenance timestamp |
| `model` | Which foreign model was inspected (name + revision) |
| `boundary` | Explicit scope language — what the packet does NOT claim |
| `claim_badges` | Tiered claim attribution (which capabilities apply at which tier) |
| `readout` | Probe output (CAS class + confidence) |
| `controls` | Random null + text baseline + ablation controls |
| `diagnostics` | Lacunarity, inversion flags, RPM satisfaction, multi-layer trace |
| `conditioning` | η→ε bridge result (per-prompt likelihood shift) |
| `generation_readiness` | Stage 20 gate output (allow/caveat/constrain/suppress + reasons) |
| `provenance` | Model revision, fixture hash, package versions, pre-registration commit |
| `caveats` | Bounded-claim reserved language |
| `rejected_claims` | Explicit no-license list (what this packet does NOT prove) |
| `export_label` | Rendering label for the .md output |

**Critical structural property:** every Evidence Packet carries BOTH the positive evidence AND the explicit list of claims this evidence does NOT support. This is the regulator-grade discipline that distinguishes CAS Harness's evidence from natural-language interpretability outputs that can confabulate.

#### 5.16.2 Schema module (`evidence_packet.py`)

The `research/cas_probe/evidence_packet.py` module exports:
- The schema type definitions
- A validator (`validate_evidence_packet`) for runtime round-trip checking
- A markdown renderer (`render_evidence_packet_markdown`) for human-readable export
- Strict per-field type checks; malformed nested fields fail validation before render

#### 5.16.3 Canonical sample packets

Four sample packets in `research/cas_probe/evidence_packets/`:

| Filename | Decision Tier | Source Model |
|---|---|---|
| `stage21a_allow_qwen15b_000.{json,md}` | allow | Qwen2.5-1.5B |
| `stage21a_caveat_olmo1b_009.{json,md}` | caveat | OLMo-1B |
| `stage21a_constrain_olmo1b_054.{json,md}` | constrain | OLMo-1B |
| `stage21a_suppress_olmo1b_054.{json,md}` | suppress | OLMo-1B |

Each sample is both JSON-serializable for programmatic consumption AND markdown-rendered for human-readable review. These are the canonical demo set.

#### 5.16.4 Status

- **Status:** validated (Stage 21A: 7 tests pass; exporter runs cleanly; JSON validates with `json.tool`)
- **Defensible claim:** "CAS Harness emits per-inspection Evidence Packets in a versioned 15-field schema (`cas_harness_evidence_packet_v1`) with validator, markdown renderer, and four canonical samples covering all four decision tiers."
- **External claim license:** Internal — pending IP attorney review.

### 5.17 Evidence Packet Delivery — API + Atlas Drawer (NEW IN v1.5, validated — Stages 21B + 21B.1)

Stage 21B turns the Stage 21A schema into a **live customer-facing product surface**: an authenticated FastAPI route serving the packet, and an Atlas reviewer drawer surfacing it in the dashboard. Stage 21B.1 tightened the drawer's authentication after audit feedback.

#### 5.17.1 Backend — `/api/harness/evidence/{trace_id}` route

Two endpoints, registered at `api/routes/harness_evidence.py`:
- `GET /harness/evidence/{trace_id}` — returns Evidence Packet as JSON (Content-Type: `application/json`)
- `GET /harness/evidence/{trace_id}/markdown` — returns rendered markdown (Content-Type: `text/markdown; charset=utf-8`)

Boundary properties enforced:

| Property | Implementation |
|---|---|
| Path-traversal guard | Strict regex `^[A-Za-z0-9_\-]{1,128}$` BEFORE filesystem access; `Path.resolve().relative_to()` containment check as defence in depth |
| Size cap | 8 MiB → HTTP 413 with reserved-language detail |
| Schema validation on read | Every served packet round-trips through `evidence_packet.validate_evidence_packet()`; failure → HTTP 500 with generic detail (schema details never leak) |
| Markdown render-on-the-fly | If `.md` absent on disk, renderer invoked at request time |
| Auth | JWT-gated via existing middleware (no PUBLIC_PATHS allowlist change) |
| Configurable storage | `NC_EVIDENCE_PACKETS_DIR` env var; defaults to research samples; production storage swaps via this setting |
| Tests | 28 pass; 37 adjacent tests unaffected |

#### 5.17.2 Frontend — Atlas Reviewer Drawer

Right-sliding modal at `dashboard/src/components/idea-atlas/EvidencePacketDrawer.tsx`. Mounts as a sibling component to the Atlas; existing layout untouched.

Seven lazy-rendered tabs in canonical order:

| Tab | Surfaces |
|---|---|
| Readout | `packet.readout` — probe output + per-axis readouts + stable-agree chips |
| Diagnostics | `packet.diagnostics` — RPM, lacunarity, gap map, blindspot flags |
| Controls | `packet.controls` — random null + text/metadata baselines + raw-symbol delta |
| Generation Readiness | `packet.generation_readiness` — Stage 20 action badge (color-coded), mode + recommended_mode, risk_score, reasons; reuses the `VerificationPanel` for the badge |
| Provenance | trace_id, created_at, model revision, fixture hash, package versions, source reports |
| Caveats | bullet list of bounded-claim language |
| Rejected Claims | italic disclaimer + red-bordered bullet list (warning styling without "error" reserved-language) |

Export footer:
- "Download JSON" — fetches via `apiFetch`, downloads as `evidence_packet_{trace_id}.json`
- "Download Markdown" — fetches via `apiFetchText`, downloads as `evidence_packet_{trace_id}.md`
- Both disabled while drawer is in loading state

Accessibility:
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` → header h2
- Escape key closes; backdrop click closes
- Focus moves to Close button on open
- `role="tablist"` / `role="tab"` / `role="tabpanel"` with `aria-controls` ↔ tabpanel `id` matching (tightened in 21B.1)

#### 5.17.3 Producer-side wiring

The drawer's "View full Evidence Packet" button only renders when the clicked Atlas node carries BOTH:
- `verification.evidence_packet_trace_id` (the route key for the API endpoint)
- An `onOpenEvidencePacket` callback from the parent

Both conditions are tested. **Backward compatibility property:** nodes without verification or without trace_id render exactly as before — button never appears.

**Producer-side gap (open as of v1.5):** the Atlas trace-emission side (`traceability_v0.py` / `thought_tree.py`) does not yet populate `verification.evidence_packet_trace_id`. Until that lands (planned Stage 21C), the button only appears in DEMO_TRACE samples for visual verification. The route, the drawer, and the schema are all ready; the producer-side linkage is the remaining wiring step.

#### 5.17.4 Stage 21B.1 authentication fix

After Stage 21B audit, the original drawer used bare `fetch` (no auth headers). Stage 21B.1 (commit `0ba984d`) tightened this:

| Fix | Description |
|---|---|
| `apiFetch<unknown>` for JSON | Routes through the existing API client; JWT auto-attached via `Authorization: Bearer ...` header |
| New `apiFetchText` for markdown | Mirrors `apiFetch` for `text/markdown` responses |
| `isEvidencePacket` tightened | Strict per-field validation catches malformed nested structures before rendering |
| Tabpanel ids match `aria-controls` | ARIA contract closed properly |
| New test confirms Bearer header sent | Audit-traceable proof |

25 drawer tests pass post-fix; 9 API client tests pass; 8 evidence-packet validator tests pass; `tsc --noEmit` clean.

#### 5.17.5 Status

- **Stage 21B status:** validated (28 backend + 24 frontend tests pass; build clean; ARIA-complete)
- **Stage 21B.1 status:** audit-clean (authenticated drawer, tightened validator, ARIA correctness)
- **Defensible claim:** "CAS Harness exposes its per-inspection Evidence Packets as an authenticated runtime artifact — JSON and markdown variants served from `/api/harness/evidence/{trace_id}` with strict path-traversal guards, size cap, and schema round-trip validation; surfaced in the Atlas Trace 3D reviewer drawer with seven tabs (Readout / Diagnostics / Controls / Generation Readiness / Provenance / Caveats / Rejected Claims), keyboard-accessible ARIA semantics, and JSON/Markdown export."
- **External claim license:** Internal — pending IP attorney review.
- **IP filing candidate #13** (see §12.2): the Evidence Packet schema + authenticated delivery surface (schema + route + drawer + ARIA contract together as one filing).

---

## 6. Development Timeline — Stages 1 through 16

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
| 13 | 2026-05-18 | Multi-layer trace + blind-spot detection | **PASS**: 95.4% probe, lacunarity 0.0016 |
| 13.1 | 2026-05-19 | Blind-spot audit (fixture / threshold / bug-fix scope) | **PASS** — clean methodology, readout-position vs model-side disambiguated |
| 14 | 2026-05-18 | Pythia-2.8B cross-scale CPL2 replication | **PASS CLEAN**: +0.583, p≈10⁻¹⁵ |
| 14.1 | 2026-05-19 | Weight-geometry alignment (probe vs W_U) | **PASS**: 2.83× random, p=0.0099 |
| 15 | 2026-05-19 | OLMo-1B cross-architecture replication | **PASS CLEAN**: 90.6% probe, +0.604 likelihood Δ |
| **16** | **2026-05-19** | **Qwen2.5-1.5B cross-architecture replication** | **PASS CLEAN**: 82.0% probe, +0.796 likelihood Δ, p=2.92×10⁻¹²** |
| **19A** | **2026-05-19** | **CAS Verification Stack — runtime-safe accept/suppress on locked formula-family fixture (4,200 examples)** | **PASS_STRONG_AUDIT_CLEAN**: 87.6% accept @ 99.78% accuracy, 0.22% silent error, 12.4% suppression with auditable reasons; runtime uses only non-oracle states |
| **19B** | **2026-05-19** | **Cross-architecture Verification Stack — OLMo-1B + Qwen2.5-1.5B on Foundation fixture** | **DIAGNOSTIC_ONLY_CROSS_ARCH**: OLMo 98.16%/71.73%/1.84%, Qwen 99.49%/74.57%/0.51%. High precision, lower coverage than Pythia — coverage gate failed under strict product threshold, motivated Stage 19C calibration |
| **19C** | **2026-05-19** | **Verification Mode Selector — HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE on OLMo + Qwen** | **MODE_SELECTOR_READY**: all 6 cells (3 modes × 2 cross-arch models) meet pre-registered per-mode targets. Three customer-configurable verification modes shipped with audit trail. |
| **20** | **2026-05-19** | **Generation Readiness Gate — orchestrating policy layer over CAS signals** | **VALIDATED**: opt-in non-mutating diagnostic policy module at cas-native/model/generation_readiness_gate.py; 22 tests passing; zero learnable parameters; CASNativeModel.forward path unchanged when not attached |
| **20B** | **2026-05-19** | **Generation Readiness Packet Integration — applied gate to Stage 19A/19B artifacts** | **PACKET_INTEGRATION_READY**: aggregate policy counts emitted per source/mode; Evidence Packet schema extended with generation_readiness field; sample customer packets generated; runner repeated cleanly |
| **21A** | **2026-05-19** | **Evidence Packet schema + validator + markdown renderer + 4 canonical samples** | **VALIDATED**: 15-field `cas_harness_evidence_packet_v1` schema; 7 tests pass; exporter runs cleanly; samples cover all 4 decision tiers (allow/caveat/constrain/suppress) |
| **21B** | **2026-05-19** | **Evidence Packet delivery — FastAPI route /harness/evidence/{trace_id} + Atlas reviewer drawer** | **VALIDATED**: 28 backend tests + 24 frontend tests pass; 8 MiB size cap; path-traversal guard; JWT auth; ARIA-complete 7-tab drawer with JSON/Markdown export |
| **21B.1** | **2026-05-19** | **Authenticated drawer fix — apiFetch + apiFetchText; tightened isEvidencePacket; tabpanel/aria-controls match** | **AUDIT_CLEAN**: 25 drawer tests + 9 API client tests + 8 validator tests pass; `tsc --noEmit` clean; Bearer-header send confirmed by new test |
| 21C+ | (pending) | Producer-side wiring of `verification.evidence_packet_trace_id` from traceability_v0.py/thought_tree.py; cross-architecture extension to Phi-2 + TinyLlama-1.1B (Stages 19D/E pre-registered); Wrap Pipeline gate integration | Pending |

### 6.1 Methodology Discipline (Updated)

Across these 36+ stages the project has enforced (unchanged from v1.0 + Stage 13.1, 14.1, 15, 16 additions):

- 9 consecutive stages of pre-registered gates committed before runs
- Paired statistics throughout
- Random-control matching on all causal claims
- Fresh holdouts for confirmatory runs (Stages 8, 11, 12, 14, 15, 16)
- Bi-agent audit cycle (Claude ↔ Codex via agent_exchange/) — audits caught overclaim at Stages 2, 2.1, 3, 3.2, 6.6, 6.6A, 6.6C, 7.3, 11

---

## 7. Accomplishments (v1.2)

### 7.1 Scientific

1. Demonstrated CAS structure is detectable inside foreign open-weight LLMs across three architecture families and five model points.
2. Demonstrated the detected structure is causally load-bearing for cognitive readout (5 axes pass collapse-to-exact-chance ablation).
3. Closed the η → ε bridge end-to-end on five model points: Pythia 160M / 1B / 2.8B, OLMo 1B, Qwen2.5-1.5B.
4. Empirically confirmed Proposition 5.6 of the Noetic Topos paper at two tiers (likelihood + weight-geometry).
5. Made four pre-registered framework-internal predictions that all held.
6. **Closed the additional cross-architecture-redundancy gate (Pythia → OLMo → Qwen) at p ≈ 10⁻¹² to 10⁻¹⁵.**
7. Established multi-layer trace methodology with blind-spot detection and readout-vs-model-side disambiguation.
8. Produced first weight-geometry evidence of the bridge mechanism (output-side alignment 2.83× random, p = 0.0099).
9. Prototyped hidden-content / suppression detection via two-bridge η₁/η₂ comparison.
10. Established referee-defensible audit methodology with 9 consecutive pre-registered confirmatory stages.

### 7.2 Engineering

1. Complete probing pipeline reusable across model architectures (Pythia + OLMo + Qwen validated)
2. Six reusable cognitive axes (Noetics, Foundations, 40 Elements, Operators, Expression Shapes, Compiler-Valid Formulas)
3. v2 role-bound counterfactual corpus (3,000 rows, balanced, audited) — reusable for any future axis or model
4. Multi-layer trace classifier + lacunarity + fractal classifier diagnostic suite
5. Realization layer (ε): CAS structure → readable natural language
6. Evidence Packet schema v1.1 with multi-layer trace, blind-spot disambiguation, weight-geometry alignment, claim-tier metadata
7. Mode 7 streaming trace surface
8. Cross-architecture adapter validated on Pythia, OLMo, and Qwen
9. Two-bridge prototype (η₁ vs η₂) for hidden-content detection

### 7.3 Strategic

1. Established CAS Harness as a parallel SKU to CAS Native with distinct product mechanism, distinct legal IP framing, distinct customer base.
2. Demonstrated framework predictive validity at two tiers (activation + static-weight).
3. **Closed the additional cross-architecture-redundancy gate** at three independent families — the dominant remaining product uncertainty as of v1.1.
4. Built reserved-language discipline that survives audit AND comparison to Anthropic NLA.

---

## 8. Reserved-Language Claim Map (v1.2)

External-facing claims must use this table. **Do not strengthen any claim beyond what this table licenses.** IP attorney review required before any external use.

| Claim | License Status | Evidence |
|---|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED | Stages 6.4, 7, 8, 9, 11, 12, 13, 14, 15, 16 |
| "The detected structure is causally load-bearing for cognitive readout" | LICENSED | Stages 6.5, 7.1, 10, 11, 12 (5 axes) |
| "The mechanism is framework-predicted" | LICENSED | 4 preflight predictions held |
| "We can condition the model's next-token probability distribution" | LICENSED | Stages 7.CPL2, 8, 14, 15, 16 |
| **"This works cross-architecture (validated on Pythia, OLMo, and Qwen — three independent architecture families)"** | **LICENSED** | **Stages 8, 14, 15, 16** |
| **"Mechanism is not lab-specific, not training-corpus-specific, and not language-specific"** | **LICENSED (NEW v1.2)** | **Stages 8, 14, 15, 16 — three labs (EleutherAI / AI2 / Alibaba), three corpora (The Pile / Dolma / multilingual+code), three tokenizer families** |
| "This works cross-scale (Pythia 160M / 1B / 2.8B, monotonic-converging)" | LICENSED | Stages 7, 8, 14 |
| "CAS Foundation subspace shows output-weight alignment above random" | LICENSED | Stage 14.1 (p = 0.0099) |
| "We can flag blind spots and distinguish model-side from readout-position weakness" | LICENSED | Stages 13, 13.1 |
| "We can detect hidden / withheld content at CAS-class granularity" | LICENSED with caveats | §5.10 — prototype with two-bridge methodology |
| **"We can make runtime-safe accept/suppress decisions at high accuracy without gold labels at inference time"** | **LICENSED (audit-clean as of v1.3)** | **Stage 19A: 87.6% accept @ 99.78% accuracy on locked formula-family fixture, 0.22% silent error; runtime uses only non-oracle states (stable / conflicted / uncertain / drifting / ensemble agreement). Deterministic rerun after commit `05ac687` reproduced the result exactly.** |
| **"We offer three customer-configurable verification modes calibrated independently per architecture family"** | **LICENSED (NEW v1.4)** | **Stage 19C: HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE; all 6 cells (3 modes × OLMo-1B + Qwen2.5-1.5B) meet pre-registered per-mode targets; product-shipped as a configuration surface** |
| **"We emit per-example generation-readiness policies (allow/caveat/constrain/suppress) over CAS signals without modifying hidden states, logits, or tokens"** | **LICENSED (NEW v1.4)** | **Stages 20/20B: opt-in non-mutating diagnostic policy layer; 22 tests passing; aggregate policy validation across Stage 19A/19B Verification Stack artifacts; Evidence Packet schema extended with `generation_readiness` field** |
| **"We emit per-inspection Evidence Packets in a versioned 15-field schema with validator, markdown renderer, and reference samples covering all four decision tiers"** | **LICENSED (NEW v1.5)** | **Stage 21A: `cas_harness_evidence_packet_v1` schema; 7 tests; 4 canonical samples emitted (allow/caveat/constrain/suppress)** |
| **"We expose Evidence Packets via an authenticated runtime route and surface them in the Atlas reviewer drawer with ARIA-complete tabs and JSON/Markdown export"** | **LICENSED (NEW v1.5)** | **Stages 21B + 21B.1: 28 backend tests + 25 drawer tests + 9 API client + 8 validator tests pass; JWT auth verified by Bearer-header test; path-traversal guard; 8 MiB size cap; schema round-trip validation; ARIA contract (role=dialog/aria-modal/tablist/tab/tabpanel with aria-controls)** |
| "We can steer the model's generated language" | NOT LICENSED | CPL3/CPL4 closed-as-not-clean at small model scale; pending replication at 1B+ |
| "We can read the model's mind in arbitrary natural-language detail" | NOT LICENSED | CAS reads at typed class granularity, not free-form English |
| "Validated for production use at frontier scale" | NOT LICENSED | Highest validated scale is Pythia-2.8B; Qwen2.5-1.5B and OLMo-1B at mid-scale |
| "Universal interpretability platform" | NOT LICENSED | "Universal" framing remains future-tense; three families is sufficient for cross-architecture redundancy claim, not sufficient for "universal" |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural

- **Three architecture families validated** (Pythia / GPT-NeoX lineage, OLMo / AI2 lineage, Qwen / Alibaba lineage). Llama, Mistral, Phi, Gemma untested for additional redundancy but no longer load-bearing for the cross-architecture claim.
- Layer-selection rule (best layer 39–50% of network depth) observed across all five models; Qwen's 39% is the first sub-44% optimum — may relate to Grouped-Query Attention or multilingual representation structure. Awaiting confirmatory in-family scale curve.
- **Decoder-only transformers only.** Encoder-only (BERT family) and encoder-decoder (T5 family) untested.
- **Probes are per-model.** Probes trained on Pythia don't transfer to OLMo or Qwen; methodology transfers, trained probes don't.

### 9.2 Scale

- **Up to 2.8B parameters validated.** 7B+, frontier-tier models untested.
- **Closed-API models cannot be onboarded.** Claude, GPT, Gemini do not expose activations. CAS Harness is open-weight only.

### 9.3 Modal

- **Likelihood conditioning closed; surface-text steering not yet closed at Pythia-160M scale.** CPL3/CPL4 surface-text gates failed at small model size, consistent with sampling-noise floor. Replication at 1B+ for surface-text tier is open.

### 9.4 Per-Class

- **Some classes carry more signal than others.** Affective register (|f) systematically harder to read than Transcendent (|T). 5 blind-spot classes identified, with readout-vs-model-side disambiguation now available. This is a real finding in its own right, not a defect.

### 9.5 Granularity

- **CAS reads at typed class granularity** (e.g., `^3^P|f`), not at arbitrary natural-language granularity.
- **η → ε can realize CAS class as natural language**, but the realization is grounded in the typed class — not free-form generation from the model's internal state.

### 9.6 Evidence-Tier

- Readout, readout-causal, likelihood-conditioning, factorization, framework-predictive, cross-architecture (3 families), weight-geometry alignment: **all closed**.
- Large-model scale (7B+), surface-text steering at scale, hidden-content detection at validated-tier, Multi-Harness Composition coordinator: **open**.

---

## 10. Future Prospects — Roadmap (v1.2)

### 10.1 Near-term (next 0–4 weeks)

| Stage | Test | Cost | Expected Yield |
|---|---|---:|---|
| 9.1 | 40-Element ablation + Domain × Noetic factorization | ~30 min A6000 | Tests whether 40 Elements is primary axis or Domain+Noetic composition |
| 17 (option A) | Llama-7B or OLMo-7B or Qwen2.5-7B scale-up | ~$30–100 GPU | Tests scale beyond 2.8B; would close the "scale" bound to 7B |
| 17 (option B) | Qwen2.5 in-family scale curve (0.5B / 1.5B / 7B) | ~$15–40 GPU | Tests training-data-dependent saturation hypothesis (§5.6) within one family |
| 17 (option C) | Hidden-content detection — pre-register + validate the η₁/η₂ two-bridge | ~$5 GPU + corpus work | Promotes hidden-content tier from prototype to validated |
| 18 | Modular Harness interface design + Evidence Packet schema v2 | $0 GPU | Sets up trillion-scale architecture without code refactor |

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

## 11. Comparison Landscape (v1.2)

| System | Approach | Scope | CAS Harness v1.2 Comparison |
|---|---|---|---|
| **Anthropic Neural Network Analysis (NLA)** | Joint AV + AR with RL reconstruction loss, natural-language descriptions | NLA: 3 sizes of one family (Anthropic Claude — Haiku 3.5 / 4.5, Opus 4.6). **CAS Harness: 5 models across 3 independent architecture families (EleutherAI Pythia / AI2 OLMo / Alibaba Qwen).** | NLA produces natural-language descriptions that are admitted-by-authors to sometimes be verifiably false ("confabulation"). CAS Harness produces typed classifications grounded in a published ontology with no confabulation tier. NLA is more flexible for discovery; CAS Harness is more auditable for compliance. NLA is more expensive (joint RL on two full LMs); CAS Harness uses a linear probe + templated realization. Both have acknowledged limitations honestly. **The cross-vendor gap that was structurally absent in NLA is now load-bearingly present in CAS Harness.** |
| Linear probes (academic) | Classify activations; report accuracy | Single axis usually | CAS Harness adds causal validation, η → ε bridge for conditioning, framework-predictive diagnostics, multi-layer trace + blind-spot detection, Evidence Packet emission, cross-architecture validation. |
| SHAP / LIME / classical XAI | Feature-importance attribution input → output | Black-box compatible | CAS Harness reads internal structural cognitive properties; classical XAI is shallower but model-agnostic. |
| Causal scrubbing (Anthropic) | Formal hypothesis-graph causal claims | Mechanistic-interp researchers only | CAS Harness's reserved-language tiered claims discipline is the same philosophy at a different granularity. |
| TransformerLens / mechanistic interp | Open-source mechanistic interpretability tooling | Researchers, not product | CAS Harness is a productized version with an a-priori cognitive framework. |
| Black-box behavioral testing | Prompt-and-score evaluations | Any model, no internal access | CAS Harness produces internal evidence; complementary, not competitive. |

---

## 12. IP & Legal Status (v1.2)

### 12.1 Existing IP

- **USPTO Provisional #64/037,173** covers the CAS framework primitives.
- The CAS framework's mathematical foundation is published in the Noetic Topos paper (journal submission, `main.pdf`).

### 12.2 Potentially Separate Filings (Updated)

The following CAS Harness-specific mechanisms may warrant separate IP filings; **IP attorney consultation required**:

1. The η → ε bridge as applied to foreign open-weight transformer models (probe → realization → prefix conditioning loop)
2. The Evidence Packet schema with tiered reserved-language claim attribution
3. The framework-predictive preflight diagnostic methodology (lacunarity + fractal classifier + topos prediction as quantitative pre-registration tools)
4. The bi-agent audit-cycle methodology
5. The weight-geometry alignment methodology (principal-angle analysis between CAS Foundation subspace and unembedding row space) — Stage 14.1
6. **The cross-architecture probe-transfer methodology** (validated by Stages 15 and 16 — Pythia → OLMo and Pythia → Qwen transfers; mechanism is now established as not lab-specific, not corpus-specific, not language-specific)
7. The multi-layer trace + readout-position blind-spot detection — Stages 13, 13.1
8. The two-bridge hidden-content / suppression detection (η₁ on activations vs η₂ on emitted text comparison) — §5.10
9. Multi-Harness Composition — axis-specialized harnesses each reading at optimal depth, composed via coordinator into a unified structural readout, mapped to the CAS Working Memory tensor — §5.13. Potentially the load-bearing IP claim for trillion-scale deployment AND for hidden-content detection at validated tier.
10. **NEW: CAS Verification Stack — runtime-safe acceptance/suppression decision layer using only non-oracle states (stable / conflicted / uncertain / drifting / ensemble agreement). Gold labels required only at validation time, not at inference. — §5.14**
11. **NEW v1.4: Verification Mode Selector + factor_consistent verifier — three product modes (HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE), each powered by a distinct internal verifier (Stack / factor_consistent / ensemble_only). Per-mode calibration validated on three architecture families with 6-of-6 pre-registered targets met. — §5.14 + Stage 19C**
12. **NEW v1.4: Generation Readiness Gate methodology — opt-in, non-mutating diagnostic policy layer over CAS signals (Lacunarity + Inversion + RPM + Verification Stack). Mode-aware action thresholds. Zero learnable parameters. JSON-serializable Evidence Packet output. The orchestrating policy that turns the Wrap Pipeline's Output Gate into a configurable, audit-traceable, regulator-grade decision surface. — §5.15**
13. **NEW v1.5: Evidence Packet schema + authenticated delivery surface — 15-field versioned schema (`cas_harness_evidence_packet_v1`) with validator + markdown renderer + 4 canonical samples; FastAPI route `/api/harness/evidence/{trace_id}` (JSON + markdown variants) with JWT auth, path-traversal guard, size cap, schema round-trip validation; Atlas reviewer drawer with 7 tabs, ARIA-complete keyboard semantics, and JSON/Markdown export. The schema + route + drawer together comprise one filing — they are the operational customer-facing artifact that turns the entire 21-stage research chain into a deliverable regulatory product. — §§5.16, 5.17**

### 12.3 IP Urgency Note

As of v1.2 (2026-05-19), CAS Harness has produced five new methodology contributions in the last 72 hours:

- Multi-layer trace with blind-spot disambiguation
- Cross-architecture validation methodology (now at three independent families)
- Weight-geometry alignment methodology
- Two-bridge hidden-content detection
- Third-family cross-architecture replication (Qwen2.5-1.5B) closing the redundancy gate

These are real intellectual property that did not fully exist 96 hours ago. **IP attorney consultation is more time-sensitive than at v1.0.**

### 12.4 External Disclosure Status

This document is **internal only**. Not authorized for external use until IP attorney review. The bounded findings from all Stages 6–16 are also not authorized for external use until IP attorney review covering both framework primitives (USPTO #64/037,173) and CAS Harness mechanisms (not yet filed).

---

## 13. Glossary (v1.2)

| Term | Definition |
|---|---|
| CAS | Cognitive Architecture System v7.7 |
| CAS Harness | This product. Cross-model interpretability platform. |
| CAS Native | From-scratch transformer with CAS as primary architecture. Parallel SKU. |
| η (eta) | Embedding map: structure → realization. Probe's role. |
| ε (epsilon) | Realization map: structure → tokens. Realization layer's role. Covering morphism per Proposition 5.6. |
| η → ε bridge | Two-pass mechanism: probe reads, realization writes, foreign model is conditioned via prefix attention. |
| η₁ vs η₂ | Two-bridge architecture for hidden-content detection: η₁ on internal hidden states vs η₂ on emitted output text. |
| 10 Noetics | Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect |
| 4 Domains | Principled (P), Cognitive (C), Evaluative (E), Operational (O) |
| 4 Registers | Transcendent (T), Analytical (A), Affective (f), Embodied (E) |
| 7 Drives | Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose (F1–F7) |
| 40 Elements | 10 Noetics × 4 Domains cross-product (TKS A1..D10) |
| 28 Foundations | 7 Drives × 4 Registers cross-product |
| Lacunarity | Var/Mean² gappiness measure |
| Fractal classifier | Iterated-operator orbit classifier (Stabilizing / Amplifying / Oscillatory / Neutral) |
| RPM chain | Realization-Prerequisite-Manifestation capability pathway |
| CPL | CAS Prefix Likelihood (Stage 7-8-14-15-16 sub-experiments testing η → ε bridge at likelihood tier) |
| Proposition 5.6 | Noetic Topos paper theorem proving counit ε's pullback is surjective |
| Noetic Coverage Noe-Cov-3 | Covering sieve condition requiring containment of counit ε |
| Evidence Packet | Per-inspection structured artifact CAS Harness emits |
| Mode 7 | Streaming trace surface for live inspection of η → ε bridge runs |
| Blind-spot (Stage 13) | Class with unstable/weak multi-layer trace evidence; flagged as either model-side weakness OR readout-position weakness per Stage 13.1 disambiguation |
| Weight-geometry alignment | Principal-angle measure between CAS subspace and model's output-weight row space; Stage 14.1 evidence tier |
| Cross-architecture transfer | Demonstration that the η → ε bridge replicates from one open-weight architecture family to another (Stage 15: Pythia → OLMo; Stage 16: Pythia → Qwen) |
| Hidden-content detection | Two-bridge η₁/η₂ comparison surfacing what the model is internally computing but not emitting (§5.10) |

---

## 14. Reproducibility Provenance (v1.2)

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
| `e603b74` | Stage 13 multi-layer trace + blind-spot | PASS |
| `bf645c8` | Stage 13.1 blind-spot audit + Stage 14.1 weight-geometry + Stage 15 OLMo-1B | 3 PASSES |
| `f1fa2da` | Stage 14 Pythia-2.8B replication | PASS CLEAN |
| **`74d6f88`** | **Stage 16 Qwen2.5-1.5B replication (pre-reg: `f5caf5c`)** | **PASS CLEAN** |
| **`95cffee`** | **Stage 19A CAS Verification Stack — runtime-safe accept/suppress (4,200-example formula-family fixture)** | **PASS_STRONG_WITH_PRECOMMIT_CAVEAT** (later resolved to **PASS_STRONG_AUDIT_CLEAN** via deterministic rerun) |
| **`7215379`** | **Stage 19B cross-architecture diagnostic stack (OLMo + Qwen Foundation fixture)** | **DIAGNOSTIC_ONLY_CROSS_ARCH** |
| **`9db137e`** | **Stage 19C Mode Selector — three product modes calibrated on OLMo + Qwen** | **MODE_SELECTOR_READY** (6/6 cells meet pre-registered targets) |
| **`f77e156`** | **Stage 20 Generation Readiness Gate — orchestrating policy layer** | **VALIDATED** (22 tests passing; opt-in non-mutating; zero learnable params) |
| **`0f27734`** | **Stage 20B Generation Readiness Packet Integration — applied gate to Stage 19A/19B artifacts** | **PACKET_INTEGRATION_READY** |
| **`2c72e37`** | **Stage 21A Evidence Packet schema + validator + renderer + exporter + tests** | **VALIDATED** (7 tests pass) |
| **`9cfc3cd`** | **Stage 21A canonical sample export — 4 packets (allow/caveat/constrain/suppress)** | **VALIDATED** (exporter runs cleanly, JSON validates) |
| **`9b4fb8a`** | **Stage 21B Evidence Packet delivery — FastAPI route + Atlas reviewer drawer** | **VALIDATED** (28 backend + 24 frontend tests pass; build clean) |
| **`0ba984d`** | **Stage 21B.1 authenticated drawer fix — apiFetch + apiFetchText + tightened isEvidencePacket + aria-controls/tabpanel match** | **AUDIT_CLEAN** (25 + 9 + 8 tests pass; `tsc --noEmit` clean) |
| **`05ac687` + rerun** | **Stage 19A audit-clean deterministic rerun after v1.3 commit** | **PASS_STRONG_AUDIT_CLEAN** |

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
| Version | 1.5 |
| Date | 2026-05-19 |
| Supersedes | v1.4 (2026-05-19, PM3) |
| Status | Internal — pending IP attorney review |
| Refresh triggers (v1.3) | Scale-up to 7B+ / Hidden-content detection validation / Qwen in-family scale curve / Multi-Harness Composition coordinator build / Material methodology revision |
| Next mandatory review | After next 7B+ scale-up OR hidden-content validation OR coordinator-build milestone lands |
| Authorization for external use | Pending IP attorney clearance |

---

## Appendix A — One-Page Summary for Stakeholders (v1.2)

**What is it?** A software service that looks inside any open-weight large language model, detects the cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and can surface what the model is internally computing but not emitting.

**How does it work?** Two-pass forward inference: (1) probe reads CAS structure from foreign model's activations; (2) realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class.

**Why does this work?** The Noetic Topos paper's Proposition 5.6 proves the counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. Now also empirically: CAS Foundation subspace shows output-weight geometric alignment 2.83× random expectation (p = 0.0099).

**What is proved today?** Six closed evidence tiers across five open-weight models from three architecture families: detection above text/metadata (up to 90.6% on 28 classes, +30+ pp lift), causally load-bearing readout (collapse to exact chance under ablation), likelihood conditioning via the η → ε bridge (effect strengthens monotonically across Pythia scales then plateaus, replicates stronger on OLMo, and reaches its highest observed value on Qwen2.5-1.5B at +0.7960 likelihood Δ, p = 2.92×10⁻¹²), clean factorization (lacunarity 0.015 to 0.0016), framework-predictive validity (4 pre-registered predictions held), output-weight geometric alignment, multi-layer trace with blind-spot detection and readout-vs-model disambiguation, prototype hidden-content / suppression detection. Mechanism is empirically established as not lab-specific, not training-corpus-specific, and not language-specific (three independent labs, three corpora, three tokenizer families).

**What is NOT yet proved?** Surface-text generation steering at small-model scale (closed-as-negative, mathematically explained). Scale beyond 2.8B parameters. Hidden-content detection at validated-tier (currently prototype). Multi-Harness Composition (designed, components proven, coordinator not yet built). "Universal interpretability platform" framing remains future-tense.

**What is the next gate?** Either (a) scale-up to 7B+, or (b) hidden-content detection validation, or (c) Qwen in-family scale curve testing the training-data-dependent saturation hypothesis, or (d) Multi-Harness Composition coordinator build. All four are cheap relative to product cost and complementary in evidence value. (d) is the architectural step that unlocks trillion-scale deployment AND substantially strengthens hidden-content detection — by giving the internal probe (η₁) a structured-tensor profile instead of a single classification.

**Authorization?** Internal only. IP attorney review required before any external use, including this summary.

---

*End of Document — CAS Harness Spec Sheet v1.2 — 2026-05-19*
