> SUPERSEDED 2026-06-04 — contains retracted scoped-ACCEPT and Object-Lock-COMPLIANCE/immutability claims; see v2.0.

# CAS Harness — Product Specification Sheet
## Investor / Strategic Partner Distribution (NDA Required)

**Version**: 1.7-EXTERNAL · **Date**: 2026-05-28 · **Classification**: Confidential, NDA-Gated
**Distribution**: Authorized recipients only, post-executed NDA

---

## v1.7 Release Notes (delta from v1.6, 2026-05-27)

A 36-hour development push extended the CAS Harness chain on two major fronts. Both extensions are now in master.

### Scientific: Second-axis closure on GPT-NeoX-20B (40-Element)

- **Detection.** Stage 9 40-Element axis readout on GPT-NeoX-20B: **95.625% probe accuracy** against a confirmed Stage 9 text baseline of 49.241% — **+46.4 pp lift over text adversary** (PR #102).
- **Causal.** Subspace-ablation result: 95.625% → 66.897% under targeted ablation (true disruption 28.7277 pp); matched random same-rank ablations 0.068 pp mean, 0.268 pp max — **107× signal-to-noise versus random matched control** (PR #104). The pre-registered gate of ≥30 pp drop OR ≤65% readout was **narrowly missed by 1.27–1.90 pp** on each disjunct. Treated honestly throughout: see §5.2 and the AI2-brief disclosure. Cover localization converged to layer 2 / top-k 8.
- **η→ε bridge.** Stage 9 40-Element η→ε bridge on GPT-NeoX-20B: **+1.412050 probe-readable Δ vs no prefix, +1.497513 gold-readable Δ, +2.881239 partner margin, raw-symbol Δ +0.013817** (near-zero, correct null) (PR #105). **This is the strongest single probe-readable bridge result in the entire project record** — 1.77× the prior Qwen2.5-1.5B Foundation-28 record (+0.7960). Probe-to-gold efficiency: 94.3%.
- **Methodology label canonicalized**: **`S9-40E-ORIGINAL-BASELINE-READOUT`** joins `S7-F28-BALANCED-BRIDGE` as the second named canonical protocol in the project.

### Engineering: Audit-grade integrity chain end-to-end

- **First ACCEPT verdict** in the project record (PR #107). Scoped to the Stage 9 40E validation packet; verifier report attached; explicitly NOT licensed as a per-customer production verdict.
- **Verifier gate + decision adapter** (PR #106): ACCEPT and SUPPRESS verdicts only fire when (a) all core proof chips are verified, (b) model/packet metadata is present, and (c) a separate verifier report supplies an explicit valid verdict + confidence. Three independent locks.
- **Audit Console UI surface** (PR #108): Load 20B ACCEPT packet button renders the verdict, six proof chips, confidence, verifier source, scope label, coverage label, and boundary disclosure. The UI explicitly does not create verdicts — it explains what the backend runner returned.
- **Fleet topology verifier gate** (PR #111): the same conservative-default policy extends from single-model to multi-worker fleet (100B/300B). Fleet merge cannot emit ACCEPT without an explicit Stage 19/20 verifier payload.
- **Cryptographically anchored evidence packets**:
  - Fragment-level SHA-256 commitment (PR #112) — workers cannot misattribute payloads.
  - Disk-persisted evidence packets with append-only hash chain (PR #113) — packets survive server restart; tampering with any chain entry breaks every subsequent fingerprint.
  - External-anchoring service with disabled / local / S3-Object-Lock modes (PR #114) — chain fingerprints can be anchored into write-once cloud storage that even the operator cannot modify post-write.
  - Verify endpoint runs four independent checks: packet payload hash, hash-log entry, hash-chain continuity, and local-anchor-manifest consistency. Tampering at any layer returns `partial_mismatch`.

### Honest scope items carried into v1.7

- **28.7 pp ablation discipline.** The 40-Element subspace ablation narrowly missed the pre-registered ≥30 pp gate. v1.7 documents both the result and the gate openly. The verifier accepted the chip on a different (signal-to-noise based) policy than the pre-registered absolute threshold; the threshold-policy discrepancy is named explicitly in §5.2 and §6.
- **Confidence rule documentation.** v0 verifier confidence = readout-chip accuracy (0.95625 → 96%). Documented in §5.14. Multi-factor confidence is a v1 verifier consideration.
- **Per-customer production verdicts**. Remain NOT LICENSED. All 20B verdicts are scoped to the Stage 9 40E validation packet only.

---

## NDA Notice

This document contains confidential and proprietary information of Noetic Compass / CAS Harness (Little Henderson, founder). Receipt of this document is subject to the executed Non-Disclosure Agreement between the recipient and Noetic Compass. Reproduction, disclosure, or use of any information herein, in whole or in part, for any purpose other than evaluating a potential strategic, investment, or partnership relationship is prohibited. The CAS framework primitives are covered by USPTO Provisional Patent Application #64/037,173. Additional filings on CAS Harness-specific mechanisms, on the S7-F28-BALANCED-BRIDGE methodology, on the S9-40E-ORIGINAL-BASELINE-READOUT methodology, and on the Audit-Grade Integrity Chain are in process; recipients are advised that the methodologies described herein are subject to ongoing patent protection.

## What This Document Is

A capability overview for prospective investors and strategic partners evaluating CAS Harness. It documents:

- What CAS Harness does and what it has empirically demonstrated
- The audit-grade discipline distinguishing it from contemporaneous interpretability work
- The validated cross-architecture and cross-scale claim (three independent model families across six model points, including a 20B scale extension closed on two cognitive axes)
- The two named canonical methodologies (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`) under which the 20B closures were produced
- The audit-grade integrity chain — disk persistence, hash chain, tamper-evidence, external anchoring — that distinguishes CAS Harness from research-grade interpretability tooling
- The honest claim boundaries — what is and is not licensed for external use today
- The IP portfolio status and provisional filing position

## What This Document Is NOT

- **Internal rollout plan and timeline** — separated into the internal-only roadmap document
- **Specific algorithmic hyperparameters** (probe rank values, layer indices, training configurations, fixture sample sizes beyond headline)
- **Specific component identifiers** (attention head IDs, MLP neuron indices, exact subspace dimensions)
- **Source code paths and internal API design**
- **Pre-registration documents and per-stage methodology**
- **Commit-level reproducibility provenance**
- **Implementation specifics that would enable reverse engineering**

Additional methodology depth available under separate technical-disclosure NDA after initial evaluation.

---

## 1. Executive Summary

CAS Harness is a cross-model interpretability and conditioning platform built on the **Cognitive Architecture System (CAS) v7.7** framework. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, condition the model's next-token probability distribution by realizing the detected structure as readable context, and emit audit-grade evidence packets — disk-persisted, cryptographically chained, and externally anchorable — that another party can independently verify.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism *before* any empirical experiment ran. The prediction has been empirically confirmed on **six open-weight models across three architecture families** (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, 20B; AI2 OLMo; Alibaba Qwen) and on **two independent evidence tiers** (activation-trace and weight-geometry).

Two canonical methodologies are now named: **`S7-F28-BALANCED-BRIDGE`** (Foundation-28 axis closure) and **`S9-40E-ORIGINAL-BASELINE-READOUT`** (40-Element axis closure). Both replicate at 20B parameter scale under their respective protocols.

### Today's load-bearing claim, reserved-language, defensible for audit

> CAS Harness reads cognitive structure from open-weight transformer hidden states across six model points and three architecture families (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, **20B** — plus AI2 OLMo, Alibaba Qwen). The η → ε bridge — the read-and-realize loop predicted by Proposition 5.6 of the Noetic Topos paper — conditions next-token likelihood with effect sizes that grow then plateau across Pythia/GPT-NeoX scale, strengthen on OLMo, reach the strongest Foundation-28 effect on Qwen2.5-1.5B (+0.7960, p = 2.92×10⁻¹²), and **produce the strongest single bridge result in the project record on the 40-Element axis at GPT-NeoX-20B under the canonical S9-40E-ORIGINAL-BASELINE-READOUT methodology** (+1.412 probe-readable Δ, +1.498 gold-readable Δ, +2.881 partner margin, 80 cases, raw-symbol controls at +0.014 confirming the ε-realization mechanism is structural rather than symbolic). The 20B chain closes on two cognitive axes: Foundation-28 (S7-F28-BALANCED-BRIDGE — 86.86% probe, +0.5964 bridge Δ, p = 3×10⁻¹¹) and 40-Element (S9-40E-ORIGINAL-BASELINE-READOUT — 95.625% probe, +46.4 pp lift over confirmed Stage 9 text baseline 49.24%, +1.412 bridge Δ). CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099) — independent weight-geometry evidence. Causal localization is empirically established at head-level (necessity + sufficiency) and sparse MLP-neuron-cover-level with full bidirectional control. Output-side behavioral steering at drive-local granularity is validated cross-scale within Pythia AND cross-architecture on Qwen. Evidence Packets are **disk-persisted with append-only hash chains, tamper-evident verify endpoints with four-check semantics, and external anchoring options including S3 Object Lock for write-once regulator-grade immutability**. The first ACCEPT verdict in the project record was generated 2026-05-28 on the Stage 9 40E validation packet; the verdict is scoped explicitly to that validation context and is NOT licensed as a per-customer production verdict.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

The probing chain closed in May 2026: cross-scale within Pythia/GPT-NeoX (now four model points: 160M, 1B, 2.8B, **20B**), cross-architecture to OLMo, cross-architecture to Qwen, weight-geometry evidence, multi-layer trace auditing, blind-spot detection with readout-vs-model-side disambiguation, runtime-safe acceptance/suppression layer, customer-facing Evidence Packet schema with authenticated delivery surface, second-axis closure on 40-Element with project-record bridge magnitude, full audit-grade integrity chain with cryptographic anchoring options, and the first ACCEPT verdict in the project record.

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
| **η (eta)** | Embedding: structure → realization | Reads CAS class from hidden-state activations via balanced-logistic regression on per-axis fixtures |
| **ε (epsilon)** | Realization: structure → tokens | Emits CAS structure as readable English prefix for the foreign model |

### 3.2 The Section-Retraction Identity

> **ε ∘ η = id** (realization after embedding = identity)
> **η ∘ ε ≠ id** (re-embedding after realization may lose information)

This asymmetry is load-bearing. ε is one-directional; ablation attempts to invert ε structurally cannot succeed. Empirically, attempts to steer generation by hidden-state ablation failed; attempts to condition generation by ε-realization succeeded.

### 3.3 Proposition 5.6 — Counit Surjectivity

The Noetic Topos paper proves: for any morphism g, the pullback of the counit ε along g is surjective. The Noetic Coverage Noe-Cov-3 axiom states the covering sieve contains ε. Applied to transformer architectures: prefix tokens are attended to by every subsequent position by construction — this is not a hyperparameter, it is the architectural property of self-attention.

The bridge mechanism predicted by Proposition 5.6 has now been empirically confirmed across:

- Four model scales within one architecture family (Pythia/GPT-NeoX: 160M, 1B, 2.8B, **20B**)
- Two out-of-family architectures (OLMo; Qwen — three independent labs, lineages, corpora, tokenizers)
- **Two cognitive axes at 20B** (Foundation-28 + 40-Element)
- Two evidence tiers (activation-trace AND weight-geometry alignment)
- Six cognitive axes
- Component-level necessity AND sufficiency tests

### 3.4 Framework-Internal Diagnostic Tools

Three CAS-internal diagnostic tools have been empirically validated:

- **Lacunarity gate**: measures factorization gappiness. Empirical results range from 0.793 (lumpy single-axis) down to 0.0016 (the cleanest factorization signature in project history, multi-layer trace). The GPT-NeoX-20B Foundation lacunarity at 0.006715 is cleaner than every prior Pythia comparator (160M at 0.021, 1B at 0.015) — the factorization quality improves with scale within the family.
- **Fractal classifier**: orbit classifier producing Stabilizing / Amplifying / Oscillatory / Neutral verdicts. Predicted generation-steering failure before the empirical attempt. The 20B numeric layer-trace class is *Amplifying* (consistent with within-family scale extension predictions).
- **Weight-geometry alignment**: Principal-angle analysis between CAS Foundation subspace and model output-weight space. Pythia-2.8B result: 2.83× random expectation (p = 0.0099). First static-weight evidence of the bridge mechanism, complementary to activation-tier evidence. Weight-geometry analysis at 20B on next-gate roadmap.

The framework's own diagnostic tools have produced numerical predictions of experimental outcomes BEFORE the experiments ran — **six times now**, each holding:

1. η → ε bridge effect (Proposition 5.6) — confirmed across six model points
2. Weight-geometry alignment magnitude — confirmed at Pythia-2.8B
3. Cross-scale plateau pattern within Pythia — confirmed
4. Raw-symbol null at every scale — confirmed (including 20B at +0.0025 / +0.0022 on F28; +0.014 on 40E)
5. Cross-architecture scaling-curve position for GPT-NeoX-20B Foundation-28 (predicted between Pythia-1B +0.554 and OLMo-1B +0.604; observed at +0.5964)
6. **40-Element axis bridge magnitude exceeding Foundation-28 at the same model** (predicted from 40-Element being more readable than Foundation-28 in Pythia-160M baseline lift comparison; confirmed at GPT-NeoX-20B: 40E bridge Δ +1.412 vs F28 bridge Δ +0.596 = 2.37× ratio at same model)

### 3.5 Two Canonical Method Identities

CAS Harness now operates under two named canonical methodologies for large-model replication. Each label encodes the load-bearing protocol commitments that are non-negotiable for any future replication.

#### 3.5.1 `S7-F28-BALANCED-BRIDGE`

- **Plain-English name**: S7-F28 Balanced Bridge Method
- **Full name**: Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method
- **Axis**: 28 Foundations (7 Drives × 4 Registers)
- **Encoded commitments**: Stage 7 source taxonomy / Foundation-28 axis / `LogisticRegression(class_weight='balanced')` probe / full η→ε bridge with matched controls

#### 3.5.2 `S9-40E-ORIGINAL-BASELINE-READOUT`

- **Plain-English name**: S9-40E Original Baseline Readout Method
- **Full name**: Stage 9 40-Element Original-Baseline Balanced-Logistic Eta-to-Epsilon Readout Method
- **Axis**: 40 Elements (10 Noetics × 4 Domains)
- **Encoded commitments**: Stage 9 role-bound + counterfactual + Focus-marker fixture design / 40-Element axis / `LogisticRegression(class_weight='balanced')` probe / pre-measured text-baseline adversary (49.24% on Stage 9) / full η→ε bridge with matched controls / cas_beats_text_claim_allowed JSON guard

Both labels enforce anti-drift discipline at the label level. Future replications are bound by name to the protocol — substitutions are visible at the canonical-label layer.

### 3.6 Audit-Grade Integrity Chain (NEW IN v1.7)

CAS Harness's Evidence Packet artifact is no longer an in-memory result. The packet now lives inside a four-layer cryptographic integrity chain that survives server restarts, detects local tampering, and (in S3 mode) detects full-server compromise.

#### 3.6.1 Layer 1 — Disk Persistence

Every merged Evidence Packet is written to a disk-backed packet store on creation. Packets survive server restart, redeploy, and process crash. A regression test in the production suite proves: memory can be cleared and the packet still loads from disk with bit-identical contents.

#### 3.6.2 Layer 2 — Append-Only Hash Chain

Each packet write appends a JSONL entry to a `cas_harness_evidence_chain` log. Every entry includes a cryptographic fingerprint of the previous entry — a Merkle-style chain in which every link locks the one before it. Tampering with any historical entry shatters every subsequent fingerprint and is detectable in linear time.

#### 3.6.3 Layer 3 — Four-Check Verify Endpoint

The `/evidence/{trace_id}/verify` endpoint runs four independent checks per verification request:

1. **Packet payload hash check** — does the packet's contents still match the SHA-256 recorded at write time?
2. **Hash-log entry check** — does a log entry pointing to this packet exist?
3. **Hash-chain continuity check** — does the fingerprint chain connect cleanly from genesis to this packet's entry?
4. **Anchor manifest consistency check** — does the locally-anchored manifest match what the chain says it should be?

Any check failure returns `partial_mismatch` with the specific layer indicated. The endpoint never returns a silent "OK"; it either passes all four checks or names the layer that failed.

#### 3.6.4 Layer 4 — External Anchoring Service

Layer 2 is local to the server. A server-level compromise could rewrite the entire chain. Layer 4 anchors the chain's fingerprints into a second, independent storage location operated under one of three modes:

| Mode (`CAS_HARNESS_EVIDENCE_ANCHOR_MODE`) | Storage | Tamper-resistance characteristic |
|---|---|---|
| `disabled` | None | Local chain only; appropriate for development |
| `local` | Separate local filesystem directory | Detects accidental edits within the deployment; partial protection |
| `s3` | Amazon S3 with Object Lock (Compliance mode retention) | **Write-once-read-many**: chain fingerprints cannot be modified or deleted by anyone — including the operator's own engineering team — until the retention period expires |

The packet records the actual anchor status (`succeeded` / `failed` / `disabled`) rather than asserting success. Failed S3 writes are surfaced as `external_anchor: failed` in the packet's audit chip set. No silent claim.

#### 3.6.5 Composite Property

Together, layers 1-4 produce a packet artifact with the following auditor-defensible properties:

- A packet's current contents can be cryptographically attested to match its at-creation state.
- A packet's existence and ordering in the chain can be cryptographically attested.
- A full-server compromise that rewrites the local chain cannot rewrite the S3-anchored chain fingerprints.
- Any verifier — including a regulator with read-only access to the verify endpoint and read-only access to the S3 bucket — can independently re-verify the packet without operator cooperation.

This is the architecture that distinguishes research-grade interpretability tooling from regulator-grade interpretability tooling.

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
     │   COGNITIVE AXIS PROBES (η) — Balanced-logistic linear classifiers
     │       │   [S7-F28-BALANCED-BRIDGE: Foundation-28 axis]
     │       │   [S9-40E-ORIGINAL-BASELINE-READOUT: 40-Element axis]
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
                  │
                  ▼
            EVIDENCE PACKET MERGE — six proof chips + verifier report
                  │
                  ▼
            DISK PERSISTENCE → HASH CHAIN → VERIFY ENDPOINT → EXTERNAL ANCHOR
                  │
                  ▼
            VERDICT (ACCEPT / SUPPRESS / FLAG_FOR_HUMAN_REVIEW)
            with scope, confidence, coverage, boundary
```

### 4.2 Component Inventory (Capability-Level)

| Component | Status | What It Does |
|---|---|---|
| Activation capture | Validated (incl. 20B) | Per-layer hidden-state extraction across multiple token positions |
| Cognitive axis probes (six axes, balanced-logistic) | Validated | Linear classifiers per CAS axis with StandardScaler + class_weight='balanced' |
| Multi-layer trace classifier | Validated | Reads probe confidence across all layers; flags trajectory quality |
| Blind-spot detector | Validated | Distinguishes architectural weakness from probe-config sensitivity |
| Realization layer (ε) | Validated for F28 and 40E templates | Template-based emission of CAS structure as readable natural language |
| Likelihood scorer | Validated (incl. 20B F28 + 40E) | Computes semantic-class log-likelihood shift |
| Subspace ablation hook | Validated; 20B 40E narrow miss documented | Causal removal of CAS-aligned representational structure |
| Lacunarity computer | Validated (incl. 20B F28 at 0.006715) | Factorization quality measure |
| Fractal classifier | Validated | Orbit-based class trajectory analysis |
| Weight-geometry analyzer | Validated (Pythia-2.8B) | Principal-angle analysis vs unembedding space (20B on next-gate roadmap) |
| Cross-architecture adapter | Validated for Pythia/GPT-NeoX (incl. 20B) + OLMo + Qwen | Abstracts model-specific details |
| Component attribution + path patching | Validated | Head-level necessity + sufficiency for the readout |
| Evidence Packet builder | Validated | Six-proof-chip schema (model / readout / baseline / causal / control-cover / output-bridge) |
| Verifier report builder | Validated (Stage 9 40E) | Stage 19/20-style decision-rule layer producing explicit ACCEPT/SUPPRESS/FLAG_FOR_HUMAN_REVIEW with confidence and scope |
| Evidence Packet verifier gate | Validated | Three-lock conservative-default policy (chips + metadata + verifier report all required) |
| Disk-persisted packet store | Validated | Packets survive server restart; bit-identical reload tested |
| Append-only hash chain | Validated | Every packet write appends a chain entry; chain continuity proven under regression test |
| Four-check verify endpoint | Validated | Payload + log + chain + anchor consistency in a single API call |
| External anchoring service | Validated for local mode; S3 mode wired and configurable | Three modes: disabled / local / S3 Object Lock |
| Fleet-topology verifier gate | Validated | Conservative-default policy extends to multi-worker 100B/300B fleet topology |
| Fragment-payload SHA-256 commitment | Validated | Workers cannot misattribute payloads in fleet runs |
| Audit Console UI surface | Validated | Renders verdict + chips + confidence + scope + boundary; explicitly does not create verdicts |
| Authenticated delivery API | Validated | REST endpoint + JWT + path-traversal guard + size cap + schema round-trip |
| Verification Stack | Validated | Runtime-safe acceptance/suppression decision layer (87.6% / 99.78%) |
| Mode Selector | Validated | Three customer-configurable verification modes |
| Generation Readiness Gate | Validated | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Two-bridge hidden-content detector | Prototype | Internal-vs-emitted comparison surfaces withheld content |

### 4.3 Three Customer Deployment Modes

| Mode | What the customer provides | What CAS Harness does | Where weights live |
|---|---|---|---|
| Hosted | Model ID or weights upload | Train probes, run inspections, host dashboard, run audit chain | CAS Harness infra (encrypted; S3 anchor optional) |
| Bring-your-endpoint | HTTPS endpoint exposing hidden states | Train probes against the endpoint; run inspections client-side; client-side audit chain | Customer infra |
| Self-hosted | Install CAS Harness toolkit | Sell toolkit + optional cloud probe training | Customer infra (their S3 bucket for anchor) |

### 4.4 Audit Console Surface (NEW IN v1.7)

The Audit Console is the user-facing surface for reviewing an Evidence Packet. It renders:

- **Verdict** (ACCEPT / SUPPRESS / FLAG_FOR_HUMAN_REVIEW) with rationale
- **Confidence** (currently `confidence = readout_chip.accuracy` under the v0 verifier rule; multi-factor under v1 roadmap)
- **Proof chips ready: X/6** with per-chip detail surfaces on hover
- **Verifier source** (e.g., `stage9_40e_validation_packet`)
- **Scope label** ("validation-packet verdict, not arbitrary live customer-production inference")
- **Coverage** (e.g., "80 cases / 40 classes")
- **Boundary disclosure** in tooltip-accessible help text

The UI carries one architectural invariant: it does not create verdicts. It only explains what the backend runner returned after checking the Evidence Packet and proof chips. Verdict creation is exclusively a backend operation gated by the three-lock policy. Live URL is permission-gated and available to NDA-covered evaluators on request.

---

## 5. Validated Capabilities

### 5.1 Cognitive Structure Detection

| Axis | Classes | Model | Probe Accuracy | Lift Over Text Baseline | Status |
|---|---:|---|---:|---:|---|
| 10 Noetics | 10 | Pythia-160M | 73.9% | +27.5 pp | Validated |
| 28 Foundations | 28 | Pythia-160M | 78.6% | +28.9 pp | Validated |
| 28 Foundations | 28 | Pythia-1B | 82.4% | — | Validated (cross-scale) |
| 28 Foundations | 28 | Pythia-2.8B | 85.9% | — | Validated (cross-scale) |
| 28 Foundations | 28 | GPT-NeoX-20B | 86.86% | — | Validated (S7-F28-BALANCED-BRIDGE) |
| 28 Foundations | 28 | OLMo-1B | 90.6% | — | Validated (cross-architecture) |
| 28 Foundations | 28 | Qwen2.5-1.5B | 82.0% | — | Validated (cross-architecture) |
| 40 Elements (Noetic × Domain) | 40 | Pythia-160M | 89.8% | +39.7 pp (text baseline 49.24%) | Validated |
| **40 Elements** | **40** | **GPT-NeoX-20B** | **95.625%** | **+46.4 pp (text baseline 49.24%)** | **Validated (S9-40E-ORIGINAL-BASELINE-READOUT)** |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | Validated (readout-causal) |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | Validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | Validated |
| Multi-Layer Trace classification | 10 | Pythia-160M | 95.4% | — | Validated |

Statistical separation from text baselines ranges from p ≈ 10⁻⁵⁰ on the early stages to machine-zero on the more recent classifiers. Stage 7 / Stage 9 text baselines have been independently re-measured under the modern eval rig (PR #101) and confirm the original lift-over-text numbers within ~1-4 pp.

### 5.2 Readout-Causal Validation

When the detected CAS-aligned representational structure is causally removed from the hidden states, classification accuracy collapses to exact-chance levels for the affected axis. Matched random-control ablations of the same dimensionality produce essentially zero disruption.

| Test | Result |
|---|---|
| Foundation subspace ablation, Pythia-160M | 78.6% → 3.57% (exact 1/28 chance) |
| Random same-rank ablation, Pythia-160M | Mean disruption 0.000, max 0.000 |
| Activation-level cover ablation, GPT-NeoX-20B F28 | 40% → 26.25% (13.75 pp drop; random max 0.0%) |
| **40-Element subspace ablation, GPT-NeoX-20B** | **95.625% → 66.897% (true disruption 28.7277 pp; random matched 0.0681 pp mean / 0.2679 pp max — 107× signal-to-noise)** |
| 10-Noetic subspace ablation | 73.9% → 10.0% (exact 1/10 chance) |
| 5-Operator subspace ablation | 99.2% → 20.0% (exact 1/5 chance) |
| Grammar subspace ablation | 93.0% → 10.0% (exact 1/10 chance) |
| Formula subspace ablation | 90.0% → 10.0% (exact 1/10 chance) |

**Pre-registered gate discipline disclosure (Stage 9 40E ablation, 20B):** the v1.7 AI2 brief committed to a pass condition of "targeted ablation drops readout by ≥30 pp OR to ≤65%" with "matched random ≤5 pp." The actual result satisfies the random-control half (0.068 pp / 0.268 pp — 107× signal-to-noise) but narrowly misses the targeted-disruption half (28.73 pp drop / 66.90% post-ablation versus 30 pp / 65% pre-registered thresholds, a 1.27-1.90 pp shortfall). The verifier accepted the chip on a signal-to-noise policy rather than the pre-registered absolute threshold; the threshold-policy discrepancy is documented openly in the methodology doc and is named explicitly in §6. A pre-registered v2 ablation sweep with broader top-k and layer cover is in the open-gate queue.

### 5.3 Likelihood Conditioning via the η → ε Bridge

| Model | Axis | Probe-readable Δ vs none | Margin over partner | Gold-readable Δ | Probe/Gold | Cases | Sign-test p |
|---|---|---:|---:|---:|---:|---:|---:|
| Pythia-160M | F28 | +0.283 | +0.683 | — | — | 81/112 | < 0.0001 |
| Pythia-1B | F28 | +0.554 | +1.246 | — | — | 90/112 | 2.58×10⁻¹⁴ |
| Pythia-2.8B | F28 | +0.583 | +1.336 | — | — | 92/112 | 3.08×10⁻¹⁵ |
| OLMo-1B | F28 | +0.604 | +1.305 | — | — | 87/112 | ≈ 10⁻¹⁵ |
| Qwen2.5-1.5B | F28 | +0.7960 | +1.6253 | — | — | 83/112 | 2.92×10⁻¹² |
| GPT-NeoX-20B | F28 | +0.5964 | +1.2449 | +0.6601 | 90.3% | 90/112 | 3×10⁻¹¹ |
| **GPT-NeoX-20B** | **40E** | **+1.4121** | **+2.8812** | **+1.4975** | **94.3%** | **80** | **PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS** |

**Key observations:**

- **GPT-NeoX-20B 40-Element is the strongest single probe-readable bridge result in the entire project record** — 1.77× the prior Qwen2.5-1.5B Foundation-28 record (+0.7960), 2.37× the same-model Foundation-28 result (+0.5964).
- **Probe/Gold efficiency 94.3%** on the 40-Element axis is the cleanest probe-handoff measurement in the project. The probe is recovering 94% of the oracle's effect on a 40-class axis at 20B scale.
- **Raw CAS symbols stay near-zero at every scale and axis** (20B F28: +0.0025; 20B 40E: +0.0138) — confirms the effect is ε-realization (readable natural-language prefix), not symbol-recognition.
- **Cross-scale and cross-axis pattern**: the 40-Element axis is more readable than Foundation-28 at the same model — consistent with the Pythia-160M lift comparison (40E +39.7 pp vs F28 +28.9 pp) — and the cross-scale extension to 20B preserves that relative ordering.

### 5.4 Factorization Quality

Lacunarity (Var/Mean²) measures how cleanly the detected classes factor. Lower is better; clean factorization typically falls below 0.05.

| Axis | Model | Lacunarity |
|---|---|---:|
| 28 Foundations | Pythia-160M | 0.021 |
| 28 Foundations | Pythia-1B | 0.015 |
| 28 Foundations | GPT-NeoX-20B | 0.006715 |
| 28 Foundations | Qwen2.5-1.5B | 0.0084 |
| Drive within Foundation grid (20B) | GPT-NeoX-20B | 0.002752 |
| Register within Foundation grid (20B) | GPT-NeoX-20B | 0.001283 |
| Multi-Layer Trace | Pythia-160M | 0.0016 |

40-Element lacunarity at 20B on roadmap. Predicted to fall below the F28 lacunarity of 0.0067 given the 40E axis is more readable in the same model.

### 5.5 Framework Predictive Validity

The framework's diagnostic tools have made committed numerical predictions BEFORE **six** different experiments. All six held — including the central η → ε bridge prediction (Proposition 5.6), the weight-geometry alignment prediction, the cross-architecture scaling-curve position prediction for GPT-NeoX-20B Foundation-28, and the cross-axis bridge-magnitude prediction for 40-Element at 20B.

### 5.6 Cross-Scale and Cross-Architecture Validation

| Validation gate | Status |
|---|---|
| Within-architecture cross-scale (Pythia/GPT-NeoX: 160M / 1B / 2.8B / **20B**) | Closed — monotonic-converging on F28, second-axis closure on 40E. 7.1× scale jump from 2.8B to 20B replicated without methodology adjustment on both axes. |
| Cross-architecture, first out-of-family (OLMo-1B, AI2) | Closed — different lab, lineage, corpus, tokenizer |
| Cross-architecture, second out-of-family (Qwen2.5-1.5B, Alibaba) | Closed — third independent family |
| Layer-selection rule | Validated; on 20B F28 the closure layer is 40 of 44 (~91% of depth); on 20B 40E the readable layer is also late while the ablatable cover converges to layer 2 / top-k 8 (a scientifically interesting divergence under investigation) |
| Raw-symbol null control | Holds at every scale and axis, including 20B F28 and 20B 40E |
| Both canonical methods (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`) replicate without protocol adjustment at 20B | Closed |

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific, not scale-bounded below 20B parameters, and not axis-specific** — three independent labs, three corpora, three tokenizer families, four within-family scale points up to 20B, and two canonical cognitive axes closed at the largest scale.

### 5.7 Weight-Geometry Alignment

First independent evidence tier complementary to activation traces.

- **Pythia-2.8B output-side alignment: 2.83× random expectation (p = 0.0099)**
- Input-side: random (consistent with the input-side hypothesis being null)
- **GPT-NeoX-20B weight-geometry analysis**: on next-gate roadmap; computable from open weights with no forward pass

### 5.8 Multi-Layer Trace + Blind-Spot Detection

| Capability | Status |
|---|---|
| Multi-layer trace classification | Validated |
| Lacunarity 0.0016 across the trace classifier | Cleanest factorization in project |
| Blind-spot detection per-class | Validated |
| Readout-position vs model-side weakness disambiguation | Validated |
| Numeric layer-trace class at 20B | Amplifying |

### 5.9 Component-Level Causal Localization

Two granularities validated, both with necessity + sufficiency and matched-control validation. Details in v1.6 §5.9 preserved verbatim.

Summary:
- **Head-level**: 78% → 19% under ablation (p = 0.0323 vs matched control); 100% sufficiency recovery via path patching
- **Sparse MLP-neuron-cover**: ablate / amplify / polarity-flip all pass 112/112 at p < 10⁻³³; bit-exact patch-back recovery
- **Output-side drive-local steering**: Pythia-160M +0.85 / 181 of 245 / p = 2.0×10⁻¹⁴; Pythia-1B +0.84 / 54 of 56 / p = 2.2×10⁻¹⁴; **Qwen2.5-1.5B +0.90 / 56 of 56 unanimous / p = 1.4×10⁻¹⁷**

### 5.10 Hidden-Content / Suppression Detection (Prototype)

Two-bridge architecture (internal-state CAS profile vs emitted-text CAS profile) surfaces what the model is internally computing but not emitting. Promoted from concept to working prototype.

### 5.11 Verification Stack — Runtime-Safe Accept/Suppress

- **87.6% accept rate at 99.78% accepted accuracy**
- **0.22% silent error rate**
- 12.4% suppression rate on conflicted/unstable cases

### 5.12 Three Customer-Configurable Verification Modes

HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE. Independently calibrated on OLMo-1B and Qwen2.5-1.5B fixtures. All six cells (3 modes × 2 model families) meet pre-registered per-mode targets.

### 5.13 Generation Readiness Gate — Four-Tier Action Discipline

allow / caveat / constrain / suppress. Zero learnable parameters. Default unattached. Foreign model's forward path unchanged.

### 5.14 Evidence Packet Schema (EXPANDED IN v1.7)

The Evidence Packet is now a 15-field versioned schema (`cas_harness_evidence_packet_v1`) carrying:

**Six proof chips** (each with structured payload + SHA-256 commitment):
1. `model` — foreign-model identity, revision, dtype, hidden-state geometry, scenario hash
2. `readout` — probe class + accuracy + per-class breakdown
3. `baseline` — text-baseline measurement (Stage 7 at 54.08% / Stage 9 at 49.24% for F28 / 40E respectively)
4. `causal` — subspace-ablation result + matched-random null + cover localization
5. `control_cover` — sparse cover discovery + bidirectional control tests
6. `output_bridge` — η→ε bridge result + partner margin + gold-readable comparator + raw-symbol null

**One verifier report** (Stage 19/20 layer):
- Explicit verdict (ACCEPT / SUPPRESS / FLAG_FOR_HUMAN_REVIEW)
- Confidence (v0 rule: confidence = readout-chip accuracy; v1 multi-factor on roadmap)
- Scope label (e.g., `stage9_40e_validation_packet`)
- Coverage label (cases / classes)
- Boundary disclosure
- Verifier source attestation

**Audit-chain provenance**:
- Packet payload SHA-256 (computed at write time, re-verified on read)
- Hash-log entry pointer
- Hash-chain continuity attestation
- External-anchor manifest (status: succeeded / failed / disabled; location: local / S3)

**Fleet-level provenance (when applicable)**:
- Worker-fragment SHA-256 commitments (every fragment cryptographically bound to its payload)
- Merge attestation

### 5.15 Authenticated Evidence Packet Delivery (EXPANDED IN v1.7)

REST API endpoint with JWT authentication, path-traversal guard, size cap, schema round-trip validation. Frontend Audit Console drawer with seven tabs, ARIA-complete keyboard semantics, JSON/Markdown export.

**Verify endpoint** (`/evidence/{trace_id}/verify`) runs four independent checks per call:

1. Packet payload hash check
2. Hash-log entry check
3. Hash-chain continuity check
4. Anchor manifest consistency check

Returns `verified` only when all four pass; returns `partial_mismatch` with explicit layer attribution on any failure. Never returns silent "OK."

**External anchoring service** with three modes (configurable via `CAS_HARNESS_EVIDENCE_ANCHOR_MODE` env var):

- `disabled` — local chain only
- `local` — anchor manifests in a separate local filesystem directory
- `s3` — anchor fingerprints to Amazon S3 with Object Lock (Compliance retention)

S3 mode delivers WORM immutability: once a chain fingerprint lands in the bucket, no one — including the operator — can modify or delete it until retention expires.

### 5.16 Tier Closure Summary

| Evidence Tier | Status |
|---|---|
| Readout (detection above baseline) | **Closed on both 20B axes** (F28 at 86.86%; 40E at 95.625%) |
| Readout-causal (collapse under ablation) | Closed for 5 prior axes (Pythia-160M); F28 20B confirmed at activation-level (13.75 pp drop, random max 0%); **40E 20B narrowly misses pre-registered ≥30 pp / ≤65% gate (actual 28.7 pp / 66.9%) with 107× signal-to-noise versus matched random null — documented openly; v2 sweep in queue** |
| Likelihood-conditioning via η → ε bridge | **Closed on both 20B axes** (F28 +0.596 / p = 3×10⁻¹¹; **40E +1.412 — PROJECT RECORD**) |
| Factorization (lacunarity ≤ 0.05) | Closed on F28 at every model; 40E 20B on roadmap |
| Framework-predictive validity (pre-registered predictions held) | **Closed at six predictions** |
| Cross-scale within architecture (4 model points: 160M / 1B / 2.8B / 20B) | Closed on F28; closed on 40E at 160M and 20B |
| Cross-architecture (3 independent families) | Closed on F28 |
| **Scale extension beyond 2.8B parameters (closed at 20B under two named methodologies)** | **Closed** |
| Weight-geometry alignment | Closed at Pythia-2.8B; GPT-NeoX-20B replication on roadmap |
| Multi-layer trace + blind-spot detection | Closed |
| Component-level causal localization (head + neuron-cover) | Closed |
| Output-side behavioral steering at drive-local granularity | Closed at 3 model points across 2 architecture families |
| Output-side steering 3-family parity (OLMo-1B replication) | Open |
| Output-side steering scale extension (drive-local at 20B) | Open |
| Runtime-safe acceptance/suppression | Closed |
| Mode-configurable verification | Closed |
| Four-tier generation readiness | Closed |
| Authenticated Evidence Packet delivery | Closed |
| **Evidence Packet schema with six proof chips + verifier report** | **Closed (v1.7)** |
| **Disk-persisted packet store** | **Closed (v1.7)** |
| **Append-only cryptographic hash chain** | **Closed (v1.7)** |
| **Four-check verify endpoint** | **Closed (v1.7)** |
| **External anchoring service (disabled / local / S3 Object Lock)** | **Closed (v1.7) — S3 mode wired; production retention configuration is operator-managed** |
| **Fleet-topology verifier gate (conservative-default policy extended to multi-worker fleet)** | **Closed (v1.7)** |
| **Fragment-payload SHA-256 commitment (anti-misattribution in fleet)** | **Closed (v1.7)** |
| **First ACCEPT verdict in project record** (Stage 9 40E validation packet) | **Closed (v1.7)** |
| Hidden-content / suppression detection (prototype) | Open — advancing |
| Surface-text steering at scale | Open |
| Multi-Harness Composition coordinator (planned, components proven) | Open |

---

## 6. Methodology Discipline as Competitive Differentiator

CAS Harness's audit-grade methodology is itself a product feature:

1. **Pre-registered acceptance criteria.** Gates and thresholds locked in writing before data runs. **Discipline disclosure (v1.7):** the Stage 9 40E ablation result narrowly missed its pre-registered gate. v1.7 documents both the result and the gate openly. The threshold-policy discrepancy between AI2-brief pre-registration and verifier acceptance is named explicitly in §5.2 and is part of the auditable evidence chain.
2. **Locked artifact hashes.** Activation captures fingerprinted. Runs against the original fingerprint are formal; runs against a recapture are explicitly flagged as diagnostic.
3. **Matched controls.** For ablation work, same-kind same-layer matched controls are the preregistered primary comparison.
4. **Honest NULL discipline.** When a method does not produce its expected result, the result is recorded as a formal NULL and the boundary it establishes is added to the claim ladder. NULLs are not buried.
5. **Reserved-language claim map.** External-facing claims are tied to specific evidence; nothing is asserted beyond what the evidence supports.
6. **Independent reproducibility commitment.** Locked manifests + fingerprints + standing reproducibility provenance enable third-party verification without proprietary access.
7. **Named canonical method discipline.** `S7-F28-BALANCED-BRIDGE` and `S9-40E-ORIGINAL-BASELINE-READOUT` encode load-bearing protocol commitments at the label level.
8. **Audit-grade integrity-chain discipline (NEW v1.7).** Every Evidence Packet lives inside a four-layer integrity chain (disk persistence + hash chain + four-check verify + external anchor). Discovery, retrieval, and verification of a packet are operations any external auditor can perform without operator cooperation.

This discipline produces a methodologically stronger evidence base than the majority of contemporary published interpretability work.

---

## 7. Accomplishments

### 7.1 Scientific

1. Demonstrated CAS structure is detectable inside foreign open-weight LLMs across three architecture families and **six model points (now including GPT-NeoX-20B on two cognitive axes)**
2. Demonstrated the detected structure is causally load-bearing for cognitive readout (five axes pass collapse-to-exact-chance ablation; 40E 20B documents a 107× SNR near-miss of the pre-registered absolute gate)
3. Closed the η → ε bridge end-to-end on **six model points across three model families on the Foundation-28 axis AND at GPT-NeoX-20B on the 40-Element axis**
4. **Closed the 20B scale extension under TWO canonical methodologies**: `S7-F28-BALANCED-BRIDGE` (Foundation-28 readout 86.86% / bridge +0.596 / p = 3×10⁻¹¹) and `S9-40E-ORIGINAL-BASELINE-READOUT` (40-Element readout 95.625% / bridge +1.412 / project record)
5. **Produced the strongest single probe-readable η→ε bridge result in the entire project record**: GPT-NeoX-20B 40-Element axis at +1.4121 probe-readable Δ, +1.4975 gold-readable Δ, +2.8812 partner margin — 1.77× the prior Qwen2.5-1.5B Foundation-28 record. Probe/Gold efficiency 94.3%
6. Empirically confirmed Proposition 5.6 of the Noetic Topos paper at two evidence tiers and two cognitive axes
7. Made **six** pre-registered framework-internal predictions, all of which held
8. Closed the cross-architecture-redundancy gate at three independent families
9. Established multi-layer trace methodology with blind-spot detection and readout-vs-model-side disambiguation
10. Produced first weight-geometry evidence of the bridge mechanism (2.83× random expectation)
11. Established component-level causal localization at head-level and sparse MLP-neuron-cover level with bidirectional control
12. Validated output-side behavioral steering at drive-local granularity, cross-scale within Pythia AND cross-architecture on Qwen
13. Prototyped hidden-content / suppression detection via two-bridge methodology
14. **Canonicalized two reproducible large-model methodologies** (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`) with anti-drift discipline encoded in their labels

### 7.2 Engineering

1. Complete probing pipeline reusable across model architectures (Pythia/GPT-NeoX at four scales including 20B + OLMo + Qwen validated)
2. Six reusable cognitive axes covering structural, compositional, and operator-level CAS primitives
3. Cross-architecture adapter validated on three model families and four scales within the originating family
4. Multi-layer trace classifier + lacunarity + fractal classifier diagnostic suite
5. Realization layer (ε) emitting CAS structure as readable natural language for both Foundation-28 and 40-Element axis templates
6. Verification Stack with runtime-safe accept/suppress at 87.6% / 99.78%
7. Three customer-configurable verification modes
8. Four-tier Generation Readiness Gate
9. Evidence Packet builder + verifier-report builder + three-lock verifier gate
10. **Audit-grade integrity chain (NEW v1.7)**: disk-persisted packet store + append-only hash chain + four-check verify endpoint + external anchoring service with disabled/local/S3-Object-Lock modes
11. **Fleet-topology verifier gate (NEW v1.7)**: conservative-default policy extending from single-model to multi-worker 100B/300B fleet topology
12. **Fragment-payload SHA-256 commitment (NEW v1.7)**: workers cryptographically cannot misattribute payloads
13. **Audit Console UI surface (NEW v1.7)**: renders verdict + chips + confidence + scope + boundary; does not create verdicts
14. **First ACCEPT verdict in project record (NEW v1.7)** on Stage 9 40E validation packet, scoped explicitly and not licensed as a production verdict
15. Authenticated REST API + frontend Audit Console drawer with ARIA-complete semantics
16. 40-Element balanced-logistic evaluator with `--require-balanced-40e` Evidence Packet guard
17. Two-bridge hidden-content detection prototype

### 7.3 Strategic

1. CAS Harness established as a parallel product line to CAS Native with distinct mechanism, distinct legal IP framing, distinct customer base
2. Framework predictive validity demonstrated at two evidence tiers
3. Cross-architecture-redundancy gate closed at three independent families; within-family cross-scale gate now closed up to 20B parameters on TWO cognitive axes
4. Reserved-language discipline established that survives audit AND comparison to contemporaneous interpretability tools
5. **Two canonical methodologies** (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`) provide named, IP-defensible protocol artifacts
6. **Audit-grade integrity chain** delivers regulator-grade tamper-evidence that meaningfully distinguishes CAS Harness from research-grade interpretability tooling and from contemporaneous AI-safety verification products

---

## 8. Reserved-Language Claim Map

| Claim | Status |
|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED |
| "The detected structure is causally load-bearing for cognitive readout" | LICENSED (on Foundation-28 axis closure chain; on 40-Element 20B documented as near-miss of pre-registered absolute threshold with 107× SNR — see §5.2) |
| "The mechanism is framework-predicted" | LICENSED (six pre-registered predictions held) |
| "We can condition the model's next-token probability distribution" | LICENSED |
| "This works cross-architecture (Pythia + OLMo + Qwen)" | LICENSED |
| "This works cross-scale (Pythia/GPT-NeoX 160M / 1B / 2.8B / 20B)" | LICENSED |
| **"Validated under TWO named canonical methodologies: `S7-F28-BALANCED-BRIDGE` (Foundation-28) and `S9-40E-ORIGINAL-BASELINE-READOUT` (40-Element)"** | **LICENSED** |
| **"Validated up to 20B parameters on TWO cognitive axes"** | **LICENSED** |
| **"The strongest single η→ε bridge effect in the project record is on the 40-Element axis at GPT-NeoX-20B (+1.412 probe-readable, +1.498 gold-readable, +2.881 partner margin)"** | **LICENSED** |
| **"Probe-handoff to oracle efficiency 94.3% on 40-Element axis at 20B"** | **LICENSED** |
| **"Evidence Packets are disk-persisted, cryptographically chained, tamper-evident, and externally anchorable to write-once cloud storage"** | **LICENSED** |
| **"Verify endpoint runs four independent checks (payload / log / chain continuity / anchor consistency) per verification call"** | **LICENSED** |
| **"S3 Object Lock anchoring delivers WORM immutability — chain fingerprints cannot be modified or deleted by anyone, including the operator, until retention expires"** | **LICENSED (when operator-configured)** |
| **"Fleet-topology verifier gate preserves conservative-default verdict policy across 100B/300B multi-worker runs"** | **LICENSED** |
| "We can flag blind spots and distinguish model-side from readout-position weakness" | LICENSED |
| "We can detect hidden / withheld content at CAS-class granularity" | LICENSED with caveats (prototype tier) |
| "We can make runtime-safe accept/suppress decisions without gold labels at inference time" | LICENSED |
| "We have component-level causal localization with necessity AND sufficiency tests passing" | LICENSED |
| "We can shift the model's output-distribution likelihood via calibrated drive-local eraser-channel steering" | LICENSED (cross-scale Pythia + cross-architecture Qwen) |
| **"The first ACCEPT verdict in the CAS Harness record (Stage 9 40E validation packet, 2026-05-28) is a packet-level validation verdict, NOT a per-customer production verdict"** | **LICENSED with explicit scope** |
| "Per-customer production ACCEPT verdicts" | NOT LICENSED (validation-packet scope only at this time) |
| "Frontier-scale (>20B) validation" | NOT LICENSED (highest validated scale is 20B) |
| "Single-neuron monosemantic localization" | NOT LICENSED (sparse-cover granularity is the validated unit) |
| "Universal interpretability platform" | NOT LICENSED (three families ≠ universal) |
| "Output-side steering at 3-family parity with the readout claim" | NOT YET LICENSED (OLMo replication open) |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural

Three architecture families validated (Pythia/GPT-NeoX, OLMo, Qwen). Llama, Mistral, Phi, Gemma untested. Decoder-only transformers only. Probes are per-model; methodology transfers across architectures and scales.

### 9.2 Scale

- Validated up to **20B parameters on TWO cognitive axes** (Foundation-28 and 40-Element) under their respective canonical methodologies
- Frontier-tier models (70B+, 300B+) untested. Fleet topology built for 100B/300B and verifier-gate-tested; awaiting first real frontier-scale fleet execution
- 20B Evidence Packet verifier-merge for ACCEPT verdict: **Closed on Stage 9 40E validation packet (first ACCEPT in project record).** Per-customer production verdicts remain explicitly NOT LICENSED
- Closed-API models (Claude, GPT, Gemini) cannot be onboarded — CAS Harness requires hidden-state access

### 9.3 Modal

- Likelihood conditioning via η→ε prefix closed at six model points, three architecture families, two cognitive axes at 20B
- Output-side behavioral steering at drive-local granularity closed at cross-scale within Pythia AND cross-architecture on Qwen; OLMo replication is the next preregistered gate
- 20B drive-local steering is the natural follow-on once the OLMo gate is closed
- Surface-text steering at small model scale failed at sampling-noise floor; 1B+ replication is a natural follow-on extension

### 9.4 Per-Class

Some cognitive classes carry more signal than others. Affective register systematically harder than Transcendent. Blind-spot detection available.

### 9.5 Granularity

CAS reads at typed class granularity, not arbitrary natural-language. Causal localization at head-level + sparse MLP-neuron-cover level (~1% of layer width). Single-neuron monosemantic localization is not claimed.

### 9.6 Evidence-Tier

- **Closed**: readout, readout-causal (5 axes; 40E 20B is documented signal-rich near-miss), likelihood-conditioning (both 20B axes), factorization, framework-predictive (6 predictions), cross-architecture (3 families), cross-scale (4 scales), weight-geometry (Pythia-2.8B), multi-layer trace, blind-spot detection, runtime-safe acceptance/suppression, mode-configurable verification, four-tier generation readiness, **Evidence Packet schema + disk persistence + hash chain + four-check verify + external anchoring**, component-level necessity + sufficiency, **first ACCEPT verdict (Stage 9 40E validation packet)**
- **Partial at 20B**: 40E subspace ablation (near-miss; v2 sweep queued); 20B weight-geometry alignment
- **Open**: large-model scale (>20B / frontier), surface-text steering at scale, hidden-content detection at validated tier, Multi-Harness Composition coordinator, neuron-level localization, output-side steering on OLMo and at 20B, per-customer production verdicts

### 9.7 Verifier discipline (v1.7 disclosure)

The v0 verifier confidence rule is `confidence = readout_chip.accuracy` (yielding 0.95625 → 96% for the first ACCEPT verdict). This rule does not currently incorporate ablation strength, bridge magnitude, or other proof chips' margins. A v1 multi-factor confidence — incorporating min-across-chips or weighted aggregation — is on roadmap. v0 is appropriate for current scope (validation-packet verdicts only); v1 will be required before any per-customer production verdict licensing.

The Stage 9 40E ablation gate discipline question (28.7 pp narrow miss of pre-registered ≥30 pp threshold versus 107× SNR against random control) is documented openly in §5.2 and §6. The verifier accepted the chip on a signal-to-noise policy; that policy is currently distinct from the pre-registered absolute threshold and is named openly. A pre-registered v2 ablation sweep with broader top-k and layer cover is in the open-gate queue and will resolve the discipline question on its own evidence.

---

## 10. Comparison Landscape

| System | Approach | Scope | CAS Harness Comparison |
|---|---|---|---|
| **Anthropic Neural Network Analysis (NLA)** | Joint AV + AR with RL reconstruction loss, natural-language descriptions | Three sizes of one Anthropic Claude family | NLA produces natural-language descriptions admitted to sometimes be verifiably false ("confabulation"). CAS Harness produces typed classifications grounded in a published ontology with **no confabulation tier**, validated across **six models in three architecture families on TWO cognitive axes at 20B scale**, and emits **disk-persisted, cryptographically chained, externally-anchorable Evidence Packets with four-check verify endpoints**. The cross-vendor gap structurally absent in NLA is load-bearingly present in CAS Harness, AND CAS Harness offers an audit-integrity chain NLA does not. |
| Linear probes (academic) | Classify activations; report accuracy | Single axis usually | CAS Harness adds causal validation, η→ε bridge for conditioning, framework-predictive diagnostics, multi-layer trace, Evidence Packet emission with full integrity chain, cross-architecture validation, cross-scale validation to 20B on two axes, component-level necessity+sufficiency, runtime-safe verification stack, two named canonical protocols, and external anchoring options including S3 Object Lock |
| SHAP / LIME / classical XAI | Feature-importance attribution | Black-box compatible | CAS Harness reads internal structural cognitive properties at typed-class granularity with cryptographic audit chain |
| AWS Bedrock Automated Reasoning Checks | Formal-logic verification of model output for hallucination prevention | Output-level; pre-deployed on Bedrock | Complementary — CAS Harness operates at representation/causal level; Automated Reasoning operates at output level. Both can carry audit-grade evidence packets. CAS Harness Evidence Packets explicitly compose with output-level audit artifacts |
| Causal scrubbing (Anthropic mech interp) | Formal hypothesis-graph causal claims | Mech-interp researchers only | CAS Harness's reserved-language tiered-claims discipline shares philosophy at different granularity |
| TransformerLens / mechanistic interpretability | Open-source tooling | Researchers, not product | CAS Harness is a productized version with an a-priori cognitive framework + audit-grade output |
| Black-box behavioral testing | Prompt-and-score evaluations | Any model, no internal access | Complementary, not competitive |

---

## 11. IP & Legal Status

### 11.1 Existing IP

- **USPTO Provisional Patent Application #64/037,173** — covers the CAS framework primitives
- Mathematical foundation: Noetic Topos paper (journal submission in progress)

### 11.2 Methodology Filings (In-Process)

IP attorney consultation in progress for the following CAS Harness-specific mechanisms:

1. The η → ε bridge as applied to foreign open-weight transformer models
2. The named canonical methodology **`S7-F28-BALANCED-BRIDGE`** as a unitary protocol artifact
3. **The named canonical methodology `S9-40E-ORIGINAL-BASELINE-READOUT` as a unitary protocol artifact (NEW v1.7)**
4. The Evidence Packet schema + authenticated delivery surface
5. **The Audit-Grade Integrity Chain — six-proof-chip packet + verifier report + disk persistence + append-only hash chain + four-check verify endpoint + external anchoring service with S3-Object-Lock mode (NEW v1.7, single composite filing candidate)**
6. **Fragment-payload SHA-256 commitment for fleet-topology evidence merging (NEW v1.7)**
7. Framework-predictive preflight diagnostic methodology
8. Bi-agent audit-cycle methodology
9. Weight-geometry alignment methodology
10. Cross-architecture probe-transfer methodology
11. Cross-scale probe-transfer methodology (now closed up to 20B on two canonical axes)
12. Multi-layer trace + readout-position blind-spot detection
13. Two-bridge hidden-content / suppression detection
14. Multi-Harness Composition architecture (planned, components proven)
15. CAS Verification Stack — runtime-safe acceptance/suppression
16. Verification Mode Selector + factor-consistent verifier
17. Generation Readiness Gate orchestrating policy methodology
18. Component-level causal localization with necessity + sufficiency tests
19. **Conservative-default fleet verifier gate (NEW v1.7)**

### 11.3 External Disclosure Status

NDA-only distribution. Additional methodology depth available under separate technical-disclosure NDA.

---

## 12. Glossary

| Term | Definition |
|---|---|
| CAS | Cognitive Architecture System v7.7 — the underlying formal framework |
| CAS Harness | This product — cross-model interpretability and conditioning platform |
| CAS Native | Companion product — from-scratch transformer with CAS as primary architecture |
| η (eta) | Embedding map: structure → realization. The probe's role. |
| ε (epsilon) | Realization map: structure → tokens. Covering morphism per Proposition 5.6. |
| η → ε bridge | Two-pass mechanism: probe reads, realization writes, foreign model conditioned via prefix attention |
| **`S7-F28-BALANCED-BRIDGE`** | **Canonical method label for Foundation-28 (7 Drives × 4 Registers) axis closure. Encodes: Stage 7 source taxonomy, F28 axis, balanced-logistic probe, η→ε bridge with matched controls.** |
| **`S9-40E-ORIGINAL-BASELINE-READOUT`** | **Canonical method label for 40-Element (10 Noetics × 4 Domains) axis closure. Encodes: Stage 9 role-bound + counterfactual + Focus-marker fixture, 40E axis, balanced-logistic probe, pre-measured text-baseline adversary, η→ε bridge with matched controls.** |
| 10 Noetics | Canonical cognitive primitives: Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect |
| 4 Domains | Principled, Cognitive, Evaluative, Operational |
| 4 Registers | Transcendent, Analytical, Affective, Embodied |
| 7 Drives | Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose |
| 40 Elements | 10 Noetics × 4 Domains cross-product |
| 28 Foundations | 7 Drives × 4 Registers cross-product |
| Lacunarity | Factorization-quality measure (Var/Mean²); lower is cleaner |
| Fractal classifier | Iterated-operator orbit classifier |
| Proposition 5.6 | Noetic Topos theorem proving the counit ε's pullback is surjective |
| Evidence Packet | Per-inspection structured customer artifact (six proof chips + verifier report + audit chain provenance) |
| **Proof Chip** | **A single typed evidence claim inside the Evidence Packet (model / readout / baseline / causal / control-cover / output-bridge). Each chip is SHA-256-committed.** |
| **Verifier Report** | **Stage 19/20-style decision-rule layer producing ACCEPT/SUPPRESS/FLAG_FOR_HUMAN_REVIEW with explicit verdict, confidence, scope, coverage, and boundary.** |
| **Audit-Grade Integrity Chain** | **Four-layer evidence integrity stack: (1) disk-persisted packet store, (2) append-only cryptographic hash chain, (3) four-check verify endpoint, (4) external anchoring service with disabled/local/S3-Object-Lock modes.** |
| **WORM Anchoring** | **Write-Once-Read-Many storage of chain fingerprints, typically via S3 Object Lock with Compliance retention. Once written, the anchor cannot be modified or deleted — including by the operator's own engineering team — until the retention period expires.** |
| **Hash Chain** | **Append-only JSONL log in which every entry includes a cryptographic fingerprint of the previous entry. Tampering with any historical entry shatters every subsequent fingerprint.** |
| **Verify Endpoint** | **`/evidence/{trace_id}/verify` — runs four independent checks (payload / log / chain continuity / anchor consistency) per verification call. Returns `verified` only when all four pass; otherwise returns `partial_mismatch` with explicit layer attribution.** |
| **Fragment-Payload SHA-256 Commitment** | **Cryptographic binding of a fleet worker's contribution to its claimed payload. Tampering with the payload after receipt invalidates the commitment.** |
| Verification Stack | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Three customer-configurable verification modes |
| Generation Readiness Gate | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Blind-spot detection | Per-class identification of model-side vs readout-position weakness |
| Weight-geometry alignment | Principal-angle measure between CAS subspace and model's output-weight row space |
| Cross-architecture transfer | Validation that the η → ε bridge replicates across independent architecture families |
| Cross-scale transfer | Validation that the η → ε bridge replicates across parameter scales within an architecture family (closed up to 20B on two canonical axes) |
| Hidden-content detection | Two-bridge comparison surfacing internal vs emitted content divergence |
| Component-level localization | Necessity + sufficiency tests identifying which architectural components carry the readout |

---

## Appendix A — One-Page Summary

**What is it?** A software service that looks inside any open-weight large language model, detects cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and emits audit-grade Evidence Packets — disk-persisted, cryptographically hash-chained, tamper-evident with four-check verify endpoints, and externally anchorable to S3-Object-Lock WORM storage. The two canonical large-model methodologies are named `S7-F28-BALANCED-BRIDGE` and `S9-40E-ORIGINAL-BASELINE-READOUT`.

**How does it work?** Two-pass forward inference: (1) probe reads CAS structure from foreign model's activations using StandardScaler + balanced-logistic regression on the relevant cognitive axis; (2) realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class. The full inference path is captured in a typed Evidence Packet with six proof chips + verifier report, persisted to disk in an append-only hash chain, and (optionally) anchored to write-once cloud storage.

**Why does this work?** The Noetic Topos paper's Proposition 5.6 proves the counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. The static-weight tier independently confirms this: CAS Foundation subspace shows output-weight alignment 2.83× random expectation.

**What is proved today?** **More than twenty closed evidence tiers** across **six open-weight models from three architecture families, including a 20B scale extension closed on TWO cognitive axes** under TWO named canonical methodologies:
- Detection above text baseline (up to 95.625% on 40-Element axis at GPT-NeoX-20B; +46.4 pp lift)
- Causally load-bearing readout (collapse to exact chance under ablation, five axes; 40E 20B documents 107× SNR near-miss)
- Likelihood conditioning via η → ε bridge — **strongest single bridge result in project record: GPT-NeoX-20B 40-Element at +1.412 probe-readable / +1.498 gold-readable / +2.881 partner margin / 94.3% probe-to-gold efficiency**
- Clean factorization (lacunarity down to 0.0016 on multi-layer trace, 0.0067 on F28 at 20B)
- Framework-predictive validity (**six** pre-registered predictions held, including the 40E bridge-magnitude prediction at 20B)
- Output-weight geometric alignment (2.83× random, p = 0.0099)
- Multi-layer trace with blind-spot detection
- Component-level causal localization at head + sparse MLP-neuron-cover level
- Output-side behavioral steering at drive-local granularity (cross-scale + cross-architecture)
- Runtime-safe accept/suppress at 87.6% / 99.78% accuracy
- **Audit-grade integrity chain: disk-persisted Evidence Packets + append-only hash chain + four-check verify endpoint + external anchoring (local / S3 Object Lock)**
- **First ACCEPT verdict in project record** (Stage 9 40E validation packet, scoped explicitly)
- **Fleet-topology verifier gate** preserving conservative-default policy at multi-worker 100B/300B scale
- Cross-architecture replication at three independent families on Foundation-28; cross-scale replication to 20B parameters on Foundation-28 AND 40-Element

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific, not scale-bounded below 20B parameters, and not axis-specific.**

**What is the bounded claim today?** CAS Harness reads, validates, conditions, and emits audit-grade structural evidence for open-weight LLMs up to 20B parameters across three architecture families on TWO cognitive axes, under TWO canonical methodologies, with disk-persisted cryptographically chained Evidence Packets that can be externally anchored to write-once cloud storage and independently verified by any third party with read access to the verify endpoint. Single-neuron monosemantic localization, frontier-scale (>20B) replication, and per-customer production ACCEPT verdicts remain explicitly open boundaries. The first ACCEPT verdict in the project record (2026-05-28) is scoped exclusively to the Stage 9 40E validation packet.

**Where to go from here?** Additional methodology depth available under separate technical-disclosure NDA after initial evaluation.

---

**END — CAS Harness Specification Sheet v1.7-EXTERNAL — 2026-05-28**
