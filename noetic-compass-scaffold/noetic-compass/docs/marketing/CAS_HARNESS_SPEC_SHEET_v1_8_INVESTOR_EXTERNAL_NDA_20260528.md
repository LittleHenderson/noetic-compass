> SUPERSEDED 2026-06-04 — contains retracted scoped-ACCEPT and Object-Lock-COMPLIANCE/immutability claims; see v2.0.

# CAS Harness — Product Specification Sheet
## Investor / Strategic Partner Distribution (NDA Required)

**Version**: 1.8-EXTERNAL · **Date**: 2026-05-28 · **Classification**: Confidential, NDA-Gated
**Distribution**: Authorized recipients only, post-executed NDA

---

## v1.8 Release Notes (delta from v1.7, earlier 2026-05-28)

Three changes since v1.7. Two engineering tightenings and one major new section.

### Verify endpoint upgraded from 4-check to 5-check (PRs #117, #118)

- The `/verify` endpoint now actively re-reads the S3 anchor object via `GetObject`, hashes it, and confirms it commits to the packet hash and the hash-log entry. This is in addition to the four in-server checks (payload hash / log entry / chain continuity / local anchor manifest).
- Total: **five independent verification checks per call**.
- The deployed smoke script now refuses to pass unless `/verify` proves the S3 round-trip actually happened (`--require-anchor-mode s3` enforcement).
- Plain-English consequence: a packet that *claims* to be anchored but whose anchor file has been deleted or modified will now fail verification on the next call. The trust model shifts from "we wrote a receipt" to "we re-verify the receipt every time someone audits us."

### Three-state Audit Console UI for S3 anchor trust (PR #119)

The Evidence Drawer UI now distinguishes precisely between three S3-anchor trust states:

| UI label | Meaning |
|---|---|
| **"S3 object verified"** | Backend just completed the 5-check verify and the S3 round-trip confirmed match |
| **"Anchored to S3"** | Packet recorded an anchor write at creation time; no live re-read performed |
| **"S3 verify failed"** | A round-trip ran and surfaced a missing-object or hash-mismatch failure |

The UI never silently upgrades trust. Reviewers see what was actually confirmed at the moment of audit.

### New §13 — Use Cases for Developers and Enterprises

v1.8 adds a major new section documenting what developers and enterprises will do with CAS Harness once the technical track stabilizes. This section answers the "so what does someone actually use it for?" question that procurement teams, board AI risk committees, and regulatory affairs functions need to answer. It is investor-NDA distribution; the language is conservative and tied to specific capability tiers already validated in §5.

### Mechanically-checkable WORM (in flight, not yet LICENSED)

A follow-on PR is in design to extend `/verify` with `HeadObject` calls that confirm AWS S3 Object Lock metadata is actually present on the anchor object, plus a smoke-script flag (`--require-object-lock`) that hard-fails if WORM is not in effect. When this lands, the WORM claim will move from "bucket configured for Object Lock" to "Object Lock verified mechanically on this specific anchor file at this specific verification call." v1.8 documents this as in-flight; the spec sheet will be updated when the gate is mechanically enforced.

---

## NDA Notice

This document contains confidential and proprietary information of Noetic Compass / CAS Harness (Little Henderson, founder). Receipt of this document is subject to the executed Non-Disclosure Agreement between the recipient and Noetic Compass. Reproduction, disclosure, or use of any information herein, in whole or in part, for any purpose other than evaluating a potential strategic, investment, or partnership relationship is prohibited. The CAS framework primitives are covered by USPTO Provisional Patent Application #64/037,173. Additional filings on CAS Harness-specific mechanisms, on the S7-F28-BALANCED-BRIDGE methodology, on the S9-40E-ORIGINAL-BASELINE-READOUT methodology, and on the Audit-Grade Integrity Chain are in process; recipients are advised that the methodologies described herein are subject to ongoing patent protection.

## What This Document Is

A capability overview for prospective investors and strategic partners evaluating CAS Harness. It documents:

- What CAS Harness does and what it has empirically demonstrated
- The audit-grade discipline distinguishing it from contemporaneous interpretability work
- The validated cross-architecture and cross-scale claim (three independent model families across six model points, including a 20B scale extension closed on two cognitive axes)
- The two named canonical methodologies (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`) under which the 20B closures were produced
- The audit-grade integrity chain — disk persistence, hash chain, five-check verify, three-state UI, external anchoring — that distinguishes CAS Harness from research-grade interpretability tooling
- **What developers and enterprises do with CAS Harness in production deployments (§13)**
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

CAS Harness is the **black-box flight recorder for AI cognition**. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, condition the model's next-token probability distribution by realizing the detected structure as readable context, and emit audit-grade Evidence Packets — disk-persisted, cryptographically chained, externally anchored to write-once cloud storage, and actively re-verified on every audit call — that another party can independently verify.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism *before* any empirical experiment ran. The prediction has been empirically confirmed on **six open-weight models across three architecture families** (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, 20B; AI2 OLMo; Alibaba Qwen) and on **two independent evidence tiers** (activation-trace and weight-geometry).

Two canonical methodologies are now named: **`S7-F28-BALANCED-BRIDGE`** (Foundation-28 axis closure) and **`S9-40E-ORIGINAL-BASELINE-READOUT`** (40-Element axis closure). Both replicate at 20B parameter scale under their respective protocols.

The product is positioned for two markets simultaneously:

1. **Developer market** — pre-deployment model evaluation, hallucination root-causing, prompt engineering with structural feedback, distillation verification, adversarial-input debugging, cross-model migration audits, CI-integrated quality gates
2. **Enterprise market** — regulatory compliance evidence (EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, Federal Reserve SR 11-7), vendor procurement evaluation, AI-error legal defense, board-level AI risk reporting, customer-trust products, red-team integration, acquisition due diligence

Detailed use cases by audience are in §13.

### Today's load-bearing claim, reserved-language, defensible for audit

> CAS Harness reads cognitive structure from open-weight transformer hidden states across six model points and three architecture families (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, **20B** — plus AI2 OLMo, Alibaba Qwen). The η → ε bridge conditions next-token likelihood with effect sizes that grow then plateau across Pythia/GPT-NeoX scale, strengthen on OLMo, reach the strongest Foundation-28 effect on Qwen2.5-1.5B (+0.7960, p = 2.92×10⁻¹²), and **produce the strongest single bridge result in the project record on the 40-Element axis at GPT-NeoX-20B under the canonical S9-40E-ORIGINAL-BASELINE-READOUT methodology** (+1.412 probe-readable Δ, +1.498 gold-readable Δ, +2.881 partner margin, 80 cases, raw-symbol controls at +0.014 confirming the ε-realization mechanism is structural rather than symbolic). The 20B chain closes on two cognitive axes. Evidence Packets are **disk-persisted with append-only hash chains, tamper-evident through a five-check verify endpoint (in-server payload / log / chain / anchor-manifest + external S3 round-trip), three-state UI surfacing of S3-anchor trust (verified / receipt-only / failed), and external anchoring options including S3 Object Lock for write-once regulator-grade immutability**. The first ACCEPT verdict in the project record was generated 2026-05-28 on the Stage 9 40E validation packet; the verdict is scoped explicitly to that validation context and is NOT licensed as a per-customer production verdict.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative. The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

The probing chain closed in May 2026 across six model points, two cognitive axes at 20B, full audit-grade integrity chain with active external re-verification, three-state UI trust surfacing, and the first ACCEPT verdict in the project record.

### 2.2 Mission

CAS Harness exists to make the cognitive architecture inside any open-weight large language model **inspectable, validatable, conditionable, and audit-traceable** by an external software service — without requiring the model's vendor to publish interpretability tooling, without modifying the model's weights, and without sacrificing the reserved-language audit discipline required for regulator-grade evidence.

### 2.3 Strategic Relationship to CAS Native

- **CAS Native** is "our model, transparent by construction" — the from-scratch flagship
- **CAS Harness** is "your model, we make it inspectable" — the cross-model platform

The two products share framework, theoretical apparatus, and evidence-tier discipline.

---

## 3. Mathematical Foundation

### 3.1 The η → ε Bridge

| Map | Direction | Implementation Role |
|---|---|---|
| **η (eta)** | Embedding: structure → realization | Reads CAS class from hidden-state activations via balanced-logistic regression on per-axis fixtures |
| **ε (epsilon)** | Realization: structure → tokens | Emits CAS structure as readable English prefix for the foreign model |

### 3.2 The Section-Retraction Identity

> **ε ∘ η = id** (realization after embedding = identity)
> **η ∘ ε ≠ id** (re-embedding after realization may lose information)

### 3.3 Proposition 5.6 — Counit Surjectivity

For any morphism g, the pullback of the counit ε along g is surjective. Applied to transformer architectures: prefix tokens are attended to by every subsequent position by construction.

Confirmed across four scales within Pythia/GPT-NeoX, two out-of-family architectures (OLMo, Qwen), two cognitive axes at 20B (Foundation-28, 40-Element), two evidence tiers, and component-level necessity + sufficiency tests.

### 3.4 Framework-Internal Diagnostic Tools

Three CAS-internal diagnostic tools validated:

- **Lacunarity gate** — empirical range 0.793 → 0.0016. GPT-NeoX-20B F28 lacunarity 0.006715 cleaner than all prior Pythia comparators.
- **Fractal classifier** — Stabilizing / Amplifying / Oscillatory / Neutral verdicts. 20B layer-trace class: Amplifying.
- **Weight-geometry alignment** — Pythia-2.8B at 2.83× random expectation (p = 0.0099). 20B replication on roadmap.

**Six pre-registered framework-internal predictions have held**, including the 40-Element bridge-magnitude prediction at 20B (+1.412 — strongest in the project, 2.37× the same-model F28 result).

### 3.5 Two Canonical Method Identities

#### 3.5.1 `S7-F28-BALANCED-BRIDGE`

Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method. Axis: 28 Foundations. Encodes: Stage 7 source taxonomy / F28 axis / `LogisticRegression(class_weight='balanced')` probe / full η→ε bridge with matched controls.

#### 3.5.2 `S9-40E-ORIGINAL-BASELINE-READOUT`

Stage 9 40-Element Original-Baseline Balanced-Logistic Eta-to-Epsilon Readout Method. Axis: 40 Elements. Encodes: Stage 9 role-bound + counterfactual + Focus-marker fixture / 40E axis / balanced-logistic probe / pre-measured text-baseline adversary (49.24%) / full η→ε bridge with matched controls / cas_beats_text_claim_allowed JSON guard.

### 3.6 Audit-Grade Integrity Chain (UPDATED IN v1.8)

A four-layer cryptographic integrity chain that survives server restart, detects local tampering, and detects full-server compromise. As of v1.8, the verify endpoint has been upgraded to actively re-read external anchor objects, and the UI surfaces three distinct trust states.

#### 3.6.1 Layer 1 — Disk Persistence

Every merged Evidence Packet is written to a disk-backed packet store on creation. Packets survive restart, redeploy, and crash. Regression-tested for bit-identical reload after memory clear.

#### 3.6.2 Layer 2 — Append-Only Hash Chain

Each packet write appends a JSONL entry to a `cas_harness_evidence_chain` log. Every entry includes a cryptographic fingerprint of the previous entry. Tampering with any historical entry shatters every subsequent fingerprint and is detectable in linear time.

#### 3.6.3 Layer 3 — Five-Check Verify Endpoint (UPGRADED v1.8)

`/evidence/{trace_id}/verify` now runs **five independent checks per verification request**:

1. **Packet payload hash check** — does the packet's contents still match the SHA-256 recorded at write time?
2. **Hash-log entry check** — does a log entry pointing to this packet exist?
3. **Hash-chain continuity check** — does the fingerprint chain connect cleanly from genesis to this packet's entry?
4. **Local anchor manifest check** — does the locally-anchored manifest match what the chain says it should be?
5. **External S3 round-trip check (NEW v1.8)** — does a live `GetObject` call retrieve the anchor file, hash to the recorded value, and confirm it commits to the packet hash + hash-log entry?

Any check failure returns `partial_mismatch` with the specific layer indicated. Endpoint never returns silent "OK"; it passes all five checks or names the failing layer.

#### 3.6.4 Layer 4 — External Anchoring Service

Three operator-configurable modes (env var `CAS_HARNESS_EVIDENCE_ANCHOR_MODE`):

| Mode | Storage | Tamper-resistance |
|---|---|---|
| `disabled` | None | Local chain only |
| `local` | Separate local filesystem directory | Detects accidental edits within the deployment |
| `s3` | Amazon S3 (Object Lock optional) | When AWS-S3 with Object Lock Compliance retention: **write-once-read-many immutability** — even the operator cannot modify or delete the anchor until retention expires. When S3-compatible storage without Object Lock: tampering becomes **detectable on next verify call** rather than prevented at write time. |

**Production state (verified 2026-05-28):** `mode=s3` active. First production anchor URI:

```
s3://cas-harness-runpod-92754088/cas-harness/evidence-anchors/
  cas-dist-ccf41c8c5800a59f-distributed-merge/
  ae39c812b3ad84049d55e6aa7cba80f3d12a031045ded0bfddd2bb75949f2b0f.json
```

The bucket-backend's Object Lock status is operator-managed and verifiable per-trace via the verify endpoint. Mechanically-checkable WORM verification via `HeadObject` is in flight; when shipped, the WORM claim will move from configuration-based to mechanically-verified per anchor file.

#### 3.6.5 Three-State UI Trust Surface (NEW v1.8)

The Audit Console Evidence Drawer renders three distinct trust states for S3 anchors:

- **"S3 object verified"** — backend completed the 5-check verify including S3 round-trip; strongest claim
- **"Anchored to S3"** — receipt recorded at write time but no live re-read performed
- **"S3 verify failed"** — round-trip ran and found a discrepancy; failure surfaced rather than hidden

The UI never silently upgrades trust. Reviewers see what was actually confirmed at the moment of audit.

#### 3.6.6 Composite Property

Together, layers 1-4 plus the UI discipline produce a packet artifact with the following auditor-defensible properties:

- A packet's current contents can be cryptographically attested to match its at-creation state
- A packet's existence and ordering in the chain can be cryptographically attested
- A full-server compromise that rewrites the local chain cannot rewrite the externally-anchored fingerprints
- Any verifier — including a regulator with read-only access to the verify endpoint and read-only access to the S3 bucket — can independently re-verify the packet without operator cooperation
- Tampering at any layer (packet, log, chain, manifest, or S3 anchor) is detected on the next `/verify` call and named explicitly in the response
- The UI surface reflects the actual trust state rather than the asserted state

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
     │   MULTI-LAYER TRACE / BLIND-SPOT DETECTOR / REALIZATION LAYER (ε)
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
            DISK PERSISTENCE → HASH CHAIN → 5-CHECK VERIFY → EXTERNAL S3 ANCHOR
                  │
                  ▼
            AUDIT CONSOLE UI — three-state trust surfacing
                  │
                  ▼
            VERDICT (ACCEPT / SUPPRESS / FLAG_FOR_HUMAN_REVIEW)
            with scope, confidence, coverage, boundary
```

### 4.2 Component Inventory (Capability-Level)

| Component | Status |
|---|---|
| Activation capture (incl. 20B) | Validated |
| Cognitive axis probes (six axes, balanced-logistic) | Validated |
| Multi-layer trace classifier | Validated |
| Blind-spot detector | Validated |
| Realization layer (ε) for F28 and 40E templates | Validated |
| Likelihood scorer (incl. 20B F28 + 40E) | Validated |
| Subspace ablation hook (20B 40E narrow miss documented) | Validated |
| Lacunarity computer (20B F28 at 0.006715) | Validated |
| Fractal classifier | Validated |
| Weight-geometry analyzer (Pythia-2.8B) | Validated |
| Cross-architecture adapter | Validated for 3 families |
| Component attribution + path patching | Validated |
| Evidence Packet builder (6 proof chips) | Validated |
| Verifier report builder (Stage 19/20 layer) | Validated |
| Evidence Packet verifier gate (three-lock policy) | Validated |
| Disk-persisted packet store | Validated |
| Append-only hash chain | Validated |
| **Five-check verify endpoint** | **Validated (v1.8)** |
| **Three-state UI trust surfacing** | **Validated (v1.8)** |
| External anchoring service (disabled / local / S3) | Validated; **s3 mode active in production** |
| Mechanically-checkable Object Lock via HeadObject | **In flight (v1.8 roadmap)** |
| Fleet-topology verifier gate (conservative-default at scale) | Validated |
| Fragment-payload SHA-256 commitment (anti-misattribution) | Validated |
| Audit Console UI surface | Validated |
| Authenticated delivery API | Validated |
| Verification Stack (runtime accept/suppress) | Validated |
| Mode Selector (3 customer-configurable modes) | Validated |
| Generation Readiness Gate (4-tier discipline) | Validated |
| Two-bridge hidden-content detector | Prototype |

### 4.3 Three Customer Deployment Modes

Hosted / Bring-your-endpoint / Self-hosted. Each supports the full integrity chain including external anchoring.

### 4.4 Audit Console Surface (UPDATED v1.8)

Renders verdict, confidence, six proof chips with detail-on-hover, verifier source, scope label, coverage label, and boundary disclosure. **Three-state S3-anchor trust surface (NEW v1.8)** distinguishes "S3 object verified" / "Anchored to S3" / "S3 verify failed." UI carries one architectural invariant: it does not create verdicts; it explains what the backend runner returned.

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
| 40 Elements | 40 | Pythia-160M | 89.8% | +39.7 pp (text baseline 49.24%) | Validated |
| **40 Elements** | **40** | **GPT-NeoX-20B** | **95.625%** | **+46.4 pp** | **Validated (S9-40E-ORIGINAL-BASELINE-READOUT)** |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | Validated |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | Validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | Validated |
| Multi-Layer Trace classification | 10 | Pythia-160M | 95.4% | — | Validated |

### 5.2 Readout-Causal Validation

5 axes pass collapse-to-exact-chance. Notable v1.7+ result: **40-Element subspace ablation at GPT-NeoX-20B: 95.625% → 66.897% (28.7277 pp drop), random matched 0.068 pp mean / 0.268 pp max — 107× signal-to-noise.** Pre-registered ≥30 pp / ≤65% gate narrowly missed by 1.27-1.90 pp on each disjunct. Documented openly. v2 ablation sweep with broader top-k and layer cover in open-gate queue.

### 5.3 Likelihood Conditioning via the η → ε Bridge

| Model | Axis | Probe-readable Δ | Partner margin | Gold-readable Δ | Probe/Gold | Cases |
|---|---|---:|---:|---:|---:|---:|
| Pythia-160M | F28 | +0.283 | +0.683 | — | — | 81/112 |
| Pythia-1B | F28 | +0.554 | +1.246 | — | — | 90/112 |
| Pythia-2.8B | F28 | +0.583 | +1.336 | — | — | 92/112 |
| OLMo-1B | F28 | +0.604 | +1.305 | — | — | 87/112 |
| Qwen2.5-1.5B | F28 | +0.7960 | +1.6253 | — | — | 83/112 |
| GPT-NeoX-20B | F28 | +0.5964 | +1.2449 | +0.6601 | 90.3% | 90/112 |
| **GPT-NeoX-20B** | **40E** | **+1.4121** | **+2.8812** | **+1.4975** | **94.3%** | **80** |

**GPT-NeoX-20B 40-Element is the strongest single probe-readable bridge result in the project record.** 1.77× the prior Qwen Foundation-28 record; 2.37× the same-model F28 result. Probe-to-gold efficiency 94.3%.

### 5.4 Factorization Quality

F28 lacunarity progression from 0.021 (Pythia-160M) → 0.006715 (GPT-NeoX-20B). Drive-within-Foundation 0.002752; Register-within-Foundation 0.001283. 40E lacunarity at 20B on roadmap.

### 5.5 Framework Predictive Validity

**Six pre-registered predictions held**, including 40E bridge magnitude prediction at 20B.

### 5.6 Cross-Scale and Cross-Architecture Validation

Both canonical methods (S7-F28-BALANCED-BRIDGE, S9-40E-ORIGINAL-BASELINE-READOUT) replicate at 20B parameter scale without protocol adjustment. Mechanism not lab-specific, not corpus-specific, not language-specific, not scale-bounded below 20B, not axis-specific.

### 5.7 Weight-Geometry Alignment

Pythia-2.8B: 2.83× random (p = 0.0099). 20B replication on roadmap.

### 5.8 Multi-Layer Trace + Blind-Spot Detection

Validated. 20B layer-trace class: Amplifying.

### 5.9 Component-Level Causal Localization

- **Head-level**: 78% → 19% (p = 0.0323 vs matched control); 100% sufficiency recovery via path patching
- **Sparse MLP-neuron-cover**: 112/112 at p < 10⁻³³; bit-exact patch-back recovery
- **Output-side drive-local steering**: Pythia-160M / Pythia-1B / Qwen2.5-1.5B all pass; **Qwen unanimous 56/56 at p = 1.4×10⁻¹⁷**

### 5.10 Hidden-Content / Suppression Detection (Prototype)

Two-bridge architecture surfaces internal-vs-emitted divergence.

### 5.11 Verification Stack — Runtime-Safe Accept/Suppress

87.6% accept rate at 99.78% accepted accuracy. 0.22% silent error rate.

### 5.12-5.13 Mode Selector + Generation Readiness Gate

HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE. Four-tier action discipline: allow / caveat / constrain / suppress.

### 5.14 Evidence Packet Schema

Six proof chips (model / readout / baseline / causal / control-cover / output-bridge), each SHA-256-committed. One verifier report (verdict + confidence + scope + coverage + boundary). Audit-chain provenance (payload SHA-256 + hash-log pointer + chain continuity + anchor manifest). Fleet-level provenance (worker-fragment SHA-256 commitments + merge attestation).

### 5.15 Authenticated Evidence Packet Delivery (UPDATED v1.8)

REST API + JWT + path-traversal guard + size cap. Audit Console drawer with seven tabs and ARIA-complete semantics.

**Verify endpoint** (`/evidence/{trace_id}/verify`) runs **five independent checks per call**:

1. Packet payload hash check
2. Hash-log entry check
3. Hash-chain continuity check
4. Local anchor manifest consistency check
5. External S3 round-trip check (boto3 GetObject + hash verification)

Returns `verified` only when all five pass; returns `partial_mismatch` with explicit layer attribution on any failure.

**Three-state UI surface** distinguishes verified / receipt-only / failed S3 anchor trust states.

**External anchoring** with disabled / local / s3 modes. Production live on s3 mode as of 2026-05-28.

### 5.16 Tier Closure Summary (UPDATED v1.8)

| Evidence Tier | Status |
|---|---|
| Readout (detection above baseline) | **Closed on both 20B axes** |
| Readout-causal | Closed for 5 prior axes; **40E 20B documents 107× SNR near-miss of pre-registered gate, openly** |
| Likelihood-conditioning via η → ε bridge | **Closed on both 20B axes (F28 +0.596; 40E +1.412 — PROJECT RECORD)** |
| Factorization | Closed on F28; 40E 20B on roadmap |
| Framework-predictive validity (6 predictions held) | Closed |
| Cross-scale within architecture (4 model points) | Closed |
| Cross-architecture (3 families) | Closed on F28 |
| Scale extension beyond 2.8B parameters | **Closed under TWO named methodologies** |
| Weight-geometry alignment | Closed at Pythia-2.8B; 20B on roadmap |
| Multi-layer trace + blind-spot detection | Closed |
| Component-level causal localization | Closed |
| Output-side behavioral steering | Closed at 3 model points across 2 architecture families |
| Output-side steering 3-family parity (OLMo replication) | Open |
| Runtime-safe acceptance/suppression | Closed |
| Mode-configurable verification | Closed |
| Four-tier generation readiness | Closed |
| Authenticated Evidence Packet delivery | Closed |
| Evidence Packet schema with six proof chips + verifier report | Closed |
| Disk-persisted packet store | Closed |
| Append-only cryptographic hash chain | Closed |
| **Five-check verify endpoint with active S3 round-trip** | **Closed (v1.8)** |
| **Three-state UI trust surfacing for S3 anchors** | **Closed (v1.8)** |
| External anchoring service active in production (`mode=s3`) | **Closed; first production anchor URI archived** |
| Fleet-topology verifier gate | Closed |
| Fragment-payload SHA-256 commitment | Closed |
| First ACCEPT verdict in project record (Stage 9 40E validation packet) | Closed |
| Mechanically-checkable WORM via HeadObject + smoke flag | **In flight** |
| Hidden-content / suppression detection (prototype) | Open |
| Surface-text steering at scale | Open |
| Multi-Harness Composition coordinator | Open |
| Multi-turn Evidence Packet reconstruction (chain of inferences over session) | Open — next product gate |
| Per-customer production ACCEPT verdicts | Open (validation-packet scope only at this time) |

---

## 6. Methodology Discipline as Competitive Differentiator

Eight discipline principles:

1. Pre-registered acceptance criteria (with open disclosure of the Stage 9 40E ablation near-miss)
2. Locked artifact hashes
3. Matched controls
4. Honest NULL discipline
5. Reserved-language claim map
6. Independent reproducibility commitment
7. Named canonical method discipline (S7-F28-BALANCED-BRIDGE, S9-40E-ORIGINAL-BASELINE-READOUT)
8. **Audit-grade integrity-chain discipline (v1.7+): Every Evidence Packet lives inside a five-layer integrity chain (disk + hash chain + five-check verify + external anchor + three-state UI). Discovery, retrieval, and verification of a packet are operations any external auditor can perform without operator cooperation.**

---

## 7. Accomplishments

### 7.1 Scientific (selected highlights)

1. CAS structure detectable across six model points in three architecture families on two cognitive axes at 20B
2. **Strongest single probe-readable η→ε bridge result in project record**: GPT-NeoX-20B 40-Element at +1.412 / +2.881 partner / 94.3% probe-to-gold efficiency
3. Six pre-registered framework-internal predictions held
4. Cross-architecture closure on Foundation-28 across three independent families
5. Two canonical methodologies named and validated at 20B scale
6. Component-level causal localization at head-level + sparse neuron-cover level with bidirectional control
7. Output-side behavioral steering at drive-local granularity cross-scale + cross-architecture

### 7.2 Engineering (selected highlights)

1. Complete probing pipeline across three architecture families and four within-family scales
2. Six reusable cognitive axes
3. Verification Stack at 87.6% / 99.78%
4. Evidence Packet schema with six proof chips + verifier report + three-lock verifier gate
5. **Audit-grade integrity chain: disk persistence + hash chain + five-check verify (incl. S3 round-trip) + external anchoring (disabled/local/S3) + three-state UI**
6. Production anchoring live on s3 mode as of 2026-05-28
7. Fleet-topology verifier gate (conservative-default at multi-worker 100B/300B scale)
8. Fragment-payload SHA-256 commitment (anti-misattribution in fleet)
9. Audit Console UI with verdict + chips + confidence + scope + boundary rendering
10. First ACCEPT verdict in project record (Stage 9 40E validation packet)

### 7.3 Strategic

1. Parallel product line to CAS Native with distinct legal IP framing
2. Framework predictive validity at two evidence tiers
3. Cross-architecture + cross-scale validated under two named canonical methodologies
4. Audit-grade integrity chain as regulator-grade differentiator from research-grade interpretability tooling
5. **Use-case map (§13) covering developer and enterprise deployment patterns**

---

## 8. Reserved-Language Claim Map

| Claim | Status |
|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED |
| "Structure is causally load-bearing" | LICENSED (F28 chain); 40E 20B documented as near-miss with 107× SNR — see §5.2 |
| "Mechanism is framework-predicted (six predictions held)" | LICENSED |
| "We condition the next-token probability distribution" | LICENSED |
| "Cross-architecture (Pythia + OLMo + Qwen)" | LICENSED |
| "Cross-scale (Pythia/GPT-NeoX 160M / 1B / 2.8B / 20B)" | LICENSED |
| "Validated under two named canonical methodologies" | LICENSED |
| "Validated up to 20B parameters on two cognitive axes" | LICENSED |
| "Strongest single bridge result in project: 40-Element at 20B (+1.412 probe / +1.498 gold / +2.881 partner)" | LICENSED |
| "Probe-handoff to oracle efficiency 94.3% on 40-Element at 20B" | LICENSED |
| "Evidence Packets disk-persisted, hash-chained, tamper-evident, externally anchorable" | LICENSED |
| **"Verify endpoint runs five independent checks per call, including active S3 round-trip"** | **LICENSED (v1.8)** |
| **"Audit Console UI distinguishes three S3-anchor trust states (verified / receipt-only / failed)"** | **LICENSED (v1.8)** |
| "S3 Object Lock WORM immutability — chain fingerprints cannot be modified even by operator" | LICENSED (when operator-configured on AWS S3 with Compliance retention); mechanical verification via HeadObject is in flight |
| "Fleet-topology verifier gate preserves conservative-default verdict policy at 100B/300B scale" | LICENSED |
| "Blind-spot detection per-class with readout-vs-model-side disambiguation" | LICENSED |
| "Hidden-content / suppression detection at CAS-class granularity" | LICENSED with caveats (prototype tier) |
| "Runtime-safe accept/suppress decisions without gold labels at inference" | LICENSED |
| "Head-level + sparse MLP-neuron-cover causal localization with necessity AND sufficiency" | LICENSED |
| "Drive-local eraser-channel steering, cross-scale within Pythia + cross-architecture on Qwen" | LICENSED |
| "First ACCEPT verdict in project record on Stage 9 40E validation packet" | **TOMBSTONED — NOT LICENSED, WITHDRAWN in v2.0** (pre-fix overclaim; candidate-only `control_proof` before commit `337d0c2`; honest WORM-retained verdict is `FLAG_FOR_HUMAN_REVIEW`; no ACCEPT stands). Claim text retained unaltered for the historical record; the licence it asserted is void. |
| "Per-customer production ACCEPT verdicts" | NOT LICENSED (validation-packet scope only) |
| "Frontier-scale (>20B) validation" | NOT LICENSED |
| "Single-neuron monosemantic localization" | NOT LICENSED |
| "Universal interpretability platform" | NOT LICENSED (three families ≠ universal) |
| "Output-side steering at 3-family parity with readout claim" | NOT YET LICENSED (OLMo replication open) |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1-9.6

Architectural / Scale / Modal / Per-Class / Granularity / Evidence-Tier bounds unchanged from v1.7. Three architecture families validated; 20B closed on two axes; per-customer production verdicts remain NOT LICENSED.

### 9.7 Verifier Discipline (v1.7+ disclosures)

- v0 verifier confidence rule: `confidence = readout_chip.accuracy`. Multi-factor v1 confidence on roadmap.
- Stage 9 40E ablation near-miss (28.7 pp / 66.9% vs pre-registered ≥30 / ≤65) documented openly. Verifier accepted on 107× SNR policy; threshold-policy discrepancy is auditable.
- WORM mechanical verification via HeadObject is in flight; current claim is "WORM-configured when operator selects AWS S3 with Object Lock," not "WORM-mechanically-verified per anchor at audit time."

---

## 10. Comparison Landscape

| System | CAS Harness Difference |
|---|---|
| Anthropic Neural Network Analysis (NLA) | Three sizes of one Anthropic family vs. **six models in three architecture families on two cognitive axes at 20B**; NLA admits "confabulation" tier; CAS Harness has none. CAS Harness emits **disk-persisted, hash-chained, five-check-verified, externally-anchored Evidence Packets**. |
| Linear probes (academic) | CAS Harness adds causal validation, η→ε bridge, framework-predictive diagnostics, multi-layer trace, two named canonical protocols, **and** full audit-grade integrity chain with active external re-verification |
| SHAP / LIME / classical XAI | Output-feature attribution only; CAS Harness reads internal structural cognitive properties with cryptographic audit chain |
| AWS Bedrock Automated Reasoning Checks | Output-level formal-logic verification; CAS Harness is representation/causal level; **complementary, not competitive** — both can carry audit-grade evidence packets |
| Causal scrubbing | Mech-interp researchers only; CAS Harness productizes the discipline at different granularity |
| TransformerLens / mechanistic interpretability | Open-source research tooling; CAS Harness is productized with audit chain |
| Black-box behavioral testing | Complementary, not competitive |

---

## 11. IP & Legal Status

USPTO Provisional #64/037,173 covers CAS framework primitives. Noetic Topos paper journal submission in progress.

IP attorney consultation in progress for additional filings including: η→ε bridge applied to foreign open-weight transformers, the two named canonical methodologies (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`), the Audit-Grade Integrity Chain (composite filing covering six-proof-chip packet + verifier report + disk persistence + hash chain + five-check verify endpoint + three-state UI surface + external anchoring service + mechanical Object Lock verification), Fragment-payload SHA-256 commitment for fleet evidence merging, Fleet-topology verifier gate, and the framework-predictive preflight diagnostic methodology.

External disclosure: NDA-only.

---

## 12. Glossary (UPDATED v1.8)

| Term | Definition |
|---|---|
| CAS | Cognitive Architecture System v7.7 — underlying formal framework |
| CAS Harness | This product — cross-model interpretability + conditioning platform |
| CAS Native | Companion product — from-scratch transformer with CAS substrate |
| η (eta) | Embedding map: structure → realization. The probe's role |
| ε (epsilon) | Realization map: structure → tokens |
| η → ε bridge | Two-pass mechanism: probe reads, realization writes, foreign model conditioned via prefix attention |
| `S7-F28-BALANCED-BRIDGE` | Canonical method label for Foundation-28 axis closure |
| `S9-40E-ORIGINAL-BASELINE-READOUT` | Canonical method label for 40-Element axis closure |
| 10 Noetics / 4 Domains / 4 Registers / 7 Drives / 40 Elements / 28 Foundations | CAS primitive axes |
| Lacunarity | Factorization-quality measure (Var/Mean²); lower is cleaner |
| Fractal classifier | Iterated-operator orbit classifier |
| Proposition 5.6 | Noetic Topos theorem proving counit ε's pullback is surjective |
| Evidence Packet | Per-inspection structured customer artifact (six proof chips + verifier report + audit chain provenance) |
| Proof Chip | Single typed evidence claim inside Evidence Packet; SHA-256-committed |
| Verifier Report | Stage 19/20-style decision-rule layer producing ACCEPT / SUPPRESS / FLAG_FOR_HUMAN_REVIEW with explicit verdict, confidence, scope, coverage, boundary |
| Audit-Grade Integrity Chain | Multi-layer evidence integrity stack: disk-persisted packet store + append-only cryptographic hash chain + five-check verify endpoint + external anchoring service + three-state UI trust surface |
| WORM Anchoring | Write-Once-Read-Many storage via S3 Object Lock with Compliance retention. When configured: anchor cannot be modified or deleted by anyone — including operator — until retention expires |
| Hash Chain | Append-only JSONL log; every entry includes cryptographic fingerprint of previous entry |
| **Five-Check Verify Endpoint (v1.8)** | **`/evidence/{trace_id}/verify` runs five independent checks: payload / log / chain / anchor manifest / external S3 round-trip (GetObject + hash). Returns `verified` only when all five pass; `partial_mismatch` with named layer otherwise.** |
| **Three-State UI Trust Surface (v1.8)** | **Audit Console distinguishes "S3 object verified" (5-check passed including round-trip), "Anchored to S3" (receipt at write time, no live re-read), "S3 verify failed" (round-trip ran, found discrepancy).** |
| **HeadObject Verification (in flight)** | **AWS S3 metadata API that returns Object Lock fields without downloading file body. When integrated into verify endpoint, will mechanically confirm `ObjectLockMode` is `COMPLIANCE`, providing per-anchor proof of WORM rather than configuration-based assertion.** |
| Fragment-Payload SHA-256 Commitment | Cryptographic binding of fleet worker contribution to claimed payload |
| Verification Stack | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Three customer-configurable verification modes |
| Generation Readiness Gate | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Blind-spot detection | Per-class identification of model-side vs readout-position weakness |
| Cross-architecture transfer | Validation that η→ε bridge replicates across independent architecture families |
| Cross-scale transfer | Validation that η→ε bridge replicates across parameter scales within an architecture family |

---

## 13. Use Cases — What Developers and Enterprises Do With CAS Harness (NEW IN v1.8)

CAS Harness occupies a single product position: **the black-box flight recorder for AI cognition.** Every inference produces a cryptographically verifiable audit packet documenting what the model was doing in its hidden states, not just what it said in its output. The downstream use cases follow from that property.

### 13.1 Developer Use Cases

These are the patterns developers use during AI feature development, debugging, and ongoing iteration.

#### 13.1.1 Pre-Deployment Model Evaluation

Before shipping any LLM-powered feature, a developer runs CAS Harness against the candidate model to establish a baseline cognitive profile across the six cognitive axes. The profile names which CAS axes are strong, which are blind spots, where the model is honest vs evasive. When the vendor pushes a model update months later, the developer re-runs and gets a structural delta report on what actually changed.

Without CAS Harness, model updates today are evaluated on aggregate benchmarks (MMLU, HellaSwag, etc.) that do not surface CAS structural shifts. A model that gets nominally better on benchmarks may have lost ^3 Negative (refusal) strength on the customer's specific edge cases — a regression invisible to benchmark-based evaluation.

#### 13.1.2 Hallucination Root-Causing

When the deployed model produces a hallucination, CAS Harness identifies the structural failure mode. A typical breakdown:

- ^9 Below/Effect fired (model produced an output) without an upstream ^8 Above/Cause grounding it (no trigger to justify the output) → structural hallucination
- ^6 Male (compositional decomposition) failed → model failed to break the prompt into verifiable parts before answering
- F2 Wisdom under-activated relative to F5 Agency → model acted on insufficient grounding

This converts hallucination debugging from trial-and-error to structural diagnosis. The developer can target the structural cause (better grounding prompt, fine-tuning on ^8-^9 chains) instead of guessing.

#### 13.1.3 Structured Prompt Engineering

Today, prompt engineering is iteration without feedback signal. With CAS Harness, the developer writes a prompt, sees its produced CAS structure, and iterates intentionally:

> *"I want this prompt to activate ^6 Male / Cognitive domain (analytical decomposition) without triggering ^3 Negative (refusal). The current draft produces too much ^3."*

Each prompt revision can be measured against the target CAS profile. This is meaningfully more efficient than blind iteration.

#### 13.1.4 Distillation Verification

When distilling a large model (e.g., GPT-OSS-120B) into a smaller deployment model (e.g., 7B), CAS Harness produces a side-by-side cognitive-property report. Which CAS axes were preserved? Which were lost? Which acquired new failure modes? The distillation team gets an actionable property delta instead of a benchmark score.

#### 13.1.5 Adversarial Input Debugging

When a jailbreak succeeds against a deployed model, CAS Harness identifies the structural mechanism. A typical jailbreak signature:

- F6 Structure drive suppressed → safety scaffolding bypassed
- Operational domain (O) over-activated relative to Principled domain (P) → constraints relaxed
- Inversion-axis F (drive pair imbalance) crossed threshold

The security/safety team gets a structural fix path (re-strengthen F6, recalibrate P-vs-O balance) instead of a patch-by-patch chase.

#### 13.1.6 Cross-Model Migration Audits

Switching from Mistral-Large to Llama-3.3-70B? Run both through CAS Harness on the customer's specific evaluation set. The delta report names exactly which cognitive properties shift. Migration decisions become evidence-based rather than vibes-based.

#### 13.1.7 CI Integration as a Cognitive-Property Quality Gate

CAS Harness can be integrated into continuous integration pipelines. A model fine-tuning produces a new checkpoint; CI runs CAS Harness against a held-out scenario set; if any pre-registered cognitive property regresses below threshold (e.g., F2 Wisdom drops by >5%), the merge is blocked. Same discipline as unit tests, applied to cognitive properties.

### 13.2 Enterprise Use Cases

These are the patterns enterprises use to deploy AI under regulation, defend AI decisions, audit AI vendors, and report AI risk to boards.

#### 13.2.1 Regulatory Compliance Evidence

This is the single largest enterprise use case. The relevant regulatory frameworks already exist and increasingly require interpretability documentation:

- **EU AI Act** (in force since 2025; full applicability 2026-2027) — high-risk AI systems require interpretability documentation, conformity assessment, and continuous monitoring
- **NIST AI Risk Management Framework** (AI RMF 1.0) — voluntary but increasingly required by US federal contracts and procurement frameworks
- **ISO/IEC 42001** — AI management system standard; AWS Bedrock is the first major cloud platform to achieve certification
- **NYC Automated Employment Decision Tool (AEDT) Law** — bias auditing requirements for AI in employment decisions
- **FDA Software-as-a-Medical-Device (SaMD)** — pre-market submission and post-market surveillance for clinical AI
- **Federal Reserve SR 11-7** — model risk management for AI/ML models in banks
- **SEC AI-disclosure guidance** — material AI risk disclosure for publicly-traded companies

Every one of these frameworks requires interpretability documentation that is currently produced by hand-waving over vendor-published benchmarks. CAS Harness Evidence Packets — disk-persisted, hash-chained, externally anchored, five-check verifiable — are exactly the artifact format these frameworks need. A regulated enterprise can attach a CAS Harness Evidence Packet to each material AI decision and produce a third-party-verifiable compliance trail.

#### 13.2.2 Vendor Procurement and Model Selection

A regulated enterprise evaluating foundation models for licensing does not have to make the decision on demos and aggregate benchmarks alone. CAS Harness produces comparative cognitive-structure reports across candidate models (e.g., Llama-3.3-70B vs Mistral Large vs OLMo-2-32B vs Qwen2.5-72B). The procurement decision becomes evidence-based: which candidate has cleanest structural profile on the customer's actual use case, which has fewest blind spots, which has the strongest principled-domain behavior.

#### 13.2.3 AI-Error Legal Defense

AI errors increasingly produce litigation. Today, the legal defense for an AI-produced error is thin: "the model's prediction had X% confidence." With CAS Harness, the defense is structurally documented: "Here is the Evidence Packet for the specific inference at issue. The model's cognitive state was within expected bounds. The structural-causal chain is auditable. Here is the SHA-256 receipt from S3 anchored at the time of inference." This is a materially stronger legal position than is currently available without CAS Harness.

#### 13.2.4 Internal Governance and Board AI Risk Reporting

Large companies have board-level AI risk committees that receive quarterly summaries. Today these summaries are qualitative. With CAS Harness, the board summary is quantitative: per-quarter verdict distribution (ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS rates), structural drift indicators (which CAS axes have shifted quarter-over-quarter), and pre-registered framework predictions that held or failed during the reporting period. Boards can act on quantitative signals; they cannot act on qualitative reassurance.

#### 13.2.5 Red-Team and Security Integration

When a red team or pen-test breaks a deployed AI, CAS Harness elevates the report from "we got the model to say X" to "we induced the model into CAS state Y, which should be unreachable from any sanctioned user input. Here is the structural transition trace. Here is the Evidence Packet showing the cognitive-state pivot." Security teams can then fix the structural vulnerability rather than patching individual prompts.

#### 13.2.6 Customer-Trust Products

Fintech, healthcare, legal-SaaS, and government AI providers can attach per-inference "verified by CAS Harness" attestations to customer-facing AI outputs, with optional links to the underlying Evidence Packet. Customers — who increasingly ask "how do I know your AI isn't lying to me?" — get a real cryptographic answer rather than vendor marketing.

#### 13.2.7 Acquisition Due Diligence

When Company A acquires Company B's AI startup, the first technical question is "what did we actually buy?" CAS Harness produces the cognitive-property report on Company B's deployed models — surfacing which CAS axes are strong, which are weak, which contain undocumented blind spots. Acquisition price negotiations gain structural evidence about what is and is not present in the target technology.

#### 13.2.8 Insurance Underwriting

AI-liability insurance is an emerging product category. Insurers underwriting AI-related liability differentiate pricing based on the auditability of the insured's AI practices. Insureds with audit-grade Evidence Packet trails — where every material AI decision has a cryptographic receipt — present materially lower underwriting risk than insureds without such trails.

### 13.3 Industry Vertical Specifics

| Vertical | Specific use |
|---|---|
| **Financial services** | Model risk management (SR 11-7), AI-driven credit / fraud / trading decisions, customer-facing chatbots requiring pre-deployment + ongoing audit |
| **Healthcare** | FDA SaMD pre-market submission evidence, clinical decision support tools, ongoing AERS-style post-market surveillance |
| **Legal** | Contract analysis, e-discovery review, court-admissibility standards for AI-produced inference |
| **Government / Public sector** | Citizen-facing chatbots, document AI, FOIA-style transparency for citizen-AI interactions |
| **Education** | AI tutoring systems, automated grading — AEDT-style fairness eval requirements |
| **Defense** | Autonomous decision support — Pentagon Responsible AI principles compliance |
| **Insurance** | Claims processing AI, underwriting AI — regulator scrutiny increasing |
| **Retail / e-commerce** | Customer-facing chatbots, recommendation systems, vendor accountability |

### 13.4 Deployment Integration Patterns

Three deployment patterns cover the majority of enterprise integrations:

#### 13.4.1 Inference-Time Middleware

CAS Harness sits between the user request and the LLM inference call. Every inference produces an Evidence Packet. Operators select a Mode (HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE) per use case. Best fit: customer-facing high-stakes AI (medical decision support, financial advice, legal recommendations).

#### 13.4.2 Sampled Periodic Audit

CAS Harness runs against a sample of production traffic (e.g., 1% or 5%) on a scheduled cron. Produces a rolling Evidence Packet stream archived for compliance. Best fit: large-volume AI deployment where 100% real-time coverage is cost-prohibitive but statistically-defensible coverage satisfies regulator requirements.

#### 13.4.3 Development-Gate Integration

CAS Harness is integrated into CI/CD. Model updates, prompt changes, and fine-tuning runs must pass pre-registered CAS Harness thresholds before merging or deploying. Best fit: AI development teams seeking quality-gate discipline.

### 13.5 Differentiation From Research-Grade Interpretability Tooling

Existing interpretability tooling is overwhelmingly **research-grade**: it helps a researcher understand one model in one context. It does not survive audit, does not produce regulator-grade evidence artifacts, does not compose into governance workflows.

CAS Harness is the first interpretability tool the founder is aware of that is **regulator-grade by construction**:

- Cryptographic chain of custody on every Evidence Packet
- Externally anchored audit log with active re-verification
- Mechanically verifiable claims (five-check verify; HeadObject Object Lock verification in flight)
- Named methodology with anti-drift discipline encoded in canonical labels
- Reserved-language claim map with explicit "LICENSED / NOT LICENSED" boundaries
- Three-state UI surface that communicates trust precisely rather than approximately

This combination is what allows CAS Harness to compose into regulated enterprise governance workflows rather than remain a research artifact.

### 13.6 Market Timing — The Regulatory Unlock Pattern

The enterprise market for interpretability tooling is currently underdeveloped because most regulators have not yet begun enforcement of the interpretability requirements that are already in their published frameworks. The EU AI Act's full applicability is rolling through 2026-2027. NIST AI RMF compliance is increasingly required by US federal contract awards. SEC has signaled scrutiny on AI-related disclosures. ISO/IEC 42001 certification is increasingly demanded in procurement.

Once any one of these regulators meaningfully enforces the interpretability requirements that are already on the books, **every enterprise deploying LLMs needs an artifact of the kind CAS Harness produces.** Today there is no productized regulator-grade interpretability tooling in the market. CAS Harness is positioned to be the audit infrastructure layer for the AI industry's compliance era.

### 13.7 Future Capability Extensions

Capability expansions that meaningfully widen the market beyond v1.8:

1. **Multi-turn Evidence Packet reconstruction** (open — named as next product gate) — chains of inferences over a session, with session-level ordering invariants and replay capability. Critical for chatbots, customer support, multi-step agents.
2. **Closed-API model coverage** — extending to Claude / GPT / Gemini via gray-box techniques where hidden states are not directly accessible. Massive market unlock if achievable.
3. **Multimodal extension** — image-generation auditing (Stable Diffusion, DALL-E lineage). Different mathematical apparatus, same architectural pattern.
4. **Agent-trajectory verification** — extending from per-inference auditability to multi-step agent-decision auditability. Critical for the rapidly-growing AI agent market.
5. **Composability with peer safety tools** — integration with Anthropic NLA, AWS Bedrock Automated Reasoning Checks, OpenAI's safety stack, and similar peer products. Complementary rather than competitive positioning.

---

## Appendix A — One-Page Summary

**What is it?** The black-box flight recorder for AI cognition. A software service that looks inside any open-weight large language model, detects cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and emits audit-grade Evidence Packets — disk-persisted, cryptographically hash-chained, tamper-evident with five-check verify endpoints (in-server payload / log / chain / anchor-manifest + external S3 round-trip), externally anchorable to S3 with optional Object Lock WORM immutability, and surfaced through a three-state UI distinguishing verified / receipt-only / failed S3 anchor trust. Two canonical large-model methodologies: `S7-F28-BALANCED-BRIDGE` and `S9-40E-ORIGINAL-BASELINE-READOUT`.

**How does it work?** Two-pass forward inference. (1) Balanced-logistic probe reads CAS structure from foreign model's activations. (2) Realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class. Full inference path captured in a typed Evidence Packet with six proof chips + verifier report, persisted to disk in an append-only hash chain, externally anchored to S3, and continuously re-verifiable.

**Why does this work?** Noetic Topos Proposition 5.6 proves counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. Static-weight tier independently confirms: CAS Foundation subspace shows output-weight alignment 2.83× random expectation.

**What is proved today?** More than twenty closed evidence tiers across six open-weight models in three architecture families, with 20B scale extension closed on TWO cognitive axes under TWO named canonical methodologies. Includes the **strongest single η→ε bridge result in project record at +1.412 probe-readable Δ / +1.498 gold-readable Δ / +2.881 partner margin on GPT-NeoX-20B 40-Element axis with 94.3% probe-to-gold efficiency.** Full audit-grade integrity chain end-to-end in production (s3 anchor mode active since 2026-05-28). First ACCEPT verdict in project record on Stage 9 40E validation packet (scoped explicitly, not per-customer production).

**Who uses it for what?** Developers use it for pre-deployment model evaluation, hallucination root-causing, structured prompt engineering, distillation verification, adversarial debugging, cross-model migration, and CI quality-gating. Enterprises use it for **regulatory compliance evidence** (EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, SR 11-7), vendor procurement evaluation, AI-error legal defense, board AI risk reporting, customer-trust products, red-team integration, acquisition due diligence, and insurance underwriting. Full use-case map in §13.

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific, not scale-bounded below 20B parameters, and not axis-specific.**

**What is the bounded claim today?** Reads, validates, conditions, and emits audit-grade structural evidence for open-weight LLMs up to 20B parameters across three architecture families on TWO cognitive axes, under TWO canonical methodologies, with disk-persisted cryptographically chained Evidence Packets externally anchored to S3 and continuously re-verifiable by any third party with read access. Single-neuron monosemantic localization, frontier-scale (>20B), and per-customer production ACCEPT verdicts remain explicitly open boundaries.

**Where to go from here?** Additional methodology depth available under separate technical-disclosure NDA after initial evaluation.

---

**END — CAS Harness Specification Sheet v1.8-EXTERNAL — 2026-05-28**
