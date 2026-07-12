# CAS Harness — Product Specification Sheet

**Investor / Strategic Partner Distribution (NDA Required)**

**Version**: CURRENT (consolidated) · **Date**: 2026-06-07 · **Classification**: Confidential, NDA-Gated
**Maintenance addendum**: 2026-07-12
**Framework**: Cognitive Architecture System (CAS) **v7.7**
**Distribution**: Authorized recipients only, post-executed NDA

> **About this sheet.** This is a single consolidated, current spec sheet. It carries forward the lean structure of the earlier v1.6-RECONCILED edition and replaces its content with the current source-of-truth (v2.1 investor edition, 2026-06-04). Where the older edition and the current record disagreed, the current record governs and the older language has been removed. No previously validated result is strengthened here; every boundary is stated honestly.

---

> **Standing disclaimer.** Noetic Compass holds no SOC 2, ISO/IEC 42001, or other third-party security/compliance certification. Evidence Packets are *designed to support* compliance documentation but do not by themselves satisfy any regulation, and nothing herein is legal advice. CAS Harness makes no "certification," "guaranteed," "100%," "world-first," or "only" claims. A scoped-validation ACCEPT is **not** a customer-production ACCEPT. Patent-pending — US Provisional Application No. 64/037,173, filed 04/13/2026 (Utility—Provisional).

---

## NDA Notice

This document contains confidential and proprietary information of Noetic Compass / CAS Harness (Little Henderson, founder). Receipt is subject to the executed Non-Disclosure Agreement between the recipient and Noetic Compass. Reproduction, disclosure, or use of any information herein, in whole or in part, for any purpose other than evaluating a potential strategic, investment, or partnership relationship is prohibited. Patent-pending — US Provisional Application No. 64/037,173, filed 04/13/2026 (Utility—Provisional). Additional filings on CAS Harness-specific mechanisms — the `S7-F28-BALANCED-BRIDGE` and `S9-40E-ORIGINAL-BASELINE-READOUT` methodologies, the Audit-Grade Integrity Chain (including the ACCEPT-requires-WORM gate and HeadObject mechanical WORM verification), the TKS-Meaning Preservation Rule, the MTC pre-registration framework, the Fleet build apparatus, and the converted-checkpoint provenance schema — are in process. Recipients are advised that the methodologies described herein are subject to ongoing patent protection.

## What This Document Is

A capability overview for prospective investors, strategic partners, and technical reviewers conducting NDA-gated code-walk verification of CAS Harness. It documents:

- What CAS Harness does and what it has empirically demonstrated
- The audit-grade discipline distinguishing it from contemporaneous interpretability work
- The validated cross-architecture and cross-scale claim (three independent model families across six model points, with a 20B scale extension closed on two cognitive axes)
- The two named canonical methodologies under which the 20B closures were produced
- The audit-grade integrity chain — disk persistence, append-only hash chain, five-check verify, three-state UI, external S3 anchoring, the ACCEPT-requires-WORM gate, and HeadObject mechanical WORM verification
- The Evidence Packet (verdict + six proof chips), the verdict vocabulary (ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS), and the Fleet build that shards large models across workers
- The honest claim boundaries — what is and is not licensed for external use today, including the **probabilistic** (not absolute) uniqueness posture (§9.8.1)
- The IP portfolio status and pending provisional filing position

## What This Document Is NOT

The following is deliberately withheld from external distribution:

- **Internal rollout plan and timeline** — separated into the internal-only roadmap document
- **Specific algorithmic hyperparameters** (probe rank values, layer indices, training configurations, fixture sample sizes beyond headline)
- **Specific component identifiers** (attention head IDs, MLP neuron indices, exact subspace dimensions)
- **Source code paths and internal API design beyond architectural categories**
- **Pre-registration documents and per-stage methodology beyond what is needed to interpret claim scope**
- **Commit-level reproducibility provenance**
- **Implementation specifics that would enable reverse engineering**

Additional methodology depth is available under a separate technical-disclosure NDA after initial evaluation. The redaction approach is moderate: the *what* is fully visible; the *exactly how* is preserved as IP.

---

## 1. Executive Summary

CAS Harness is the **black-box flight recorder for AI cognition** — a cross-model interpretability and conditioning platform built on the Cognitive Architecture System (CAS) v7.7. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, condition the model's next-token probability distribution by realizing the detected structure as readable context, and emit **audit-grade Evidence Packets** that another party can independently verify.

Each Evidence Packet carries a verdict — **ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS** — plus **six proof chips** (model / readout / baseline / causal / control-cover / output-bridge). Packets are disk-persisted (single-instance restart-survival proven; multi-instance / host-loss durability NOT proven), cryptographically hash-chained, externally anchored to S3 Object Lock, actively re-verified on every audit call, and gated such that the final ACCEPT verdict requires mechanically-verified WORM-retention proof or is automatically downgraded to FLAG_FOR_HUMAN_REVIEW.

The external anchor is **tamper-EVIDENT, not immutable**: it uses **S3 Object Lock in Governance mode** with an approximately **30-day rolling retention window**, and is **operator-overridable** by a principal holding `s3:BypassGovernanceRetention`. The guarantee the chain provides is that any such override is detected on the next `/verify` call — not that deletion or overwrite is physically prevented.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the **η → ε bridge** mechanism *before* any empirical experiment ran. The prediction has been empirically confirmed on **six open-weight models across three architecture families** (EleutherAI Pythia / GPT-NeoX at four scales — 160M, 1B, 2.8B, 20B; AI2 OLMo; Alibaba Qwen) and on **two independent evidence tiers** (activation-trace and weight-geometry).

Two canonical methodologies are named: **`S7-F28-BALANCED-BRIDGE`** (Foundation-28 axis closure) and **`S9-40E-ORIGINAL-BASELINE-READOUT`** (40-Element axis closure). Both replicate at 20B parameter scale under their respective protocols.

For models too large for a single worker, the **Fleet build** shards the model across **Probe Workers** coordinated by a **Fleet Executor** and **Scale Planner**, with a fleet-topology verifier gate (conservative-default policy). The architecture is engineered toward **300B+** parameters; the 300B figure is **ENGINEERED, NOT VALIDATED** — no audit result above 20B is licensed.

### Today's load-bearing claim — reserved-language, defensible for audit

> CAS Harness reads cognitive structure from open-weight transformer hidden states across six model points and three architecture families (EleutherAI Pythia / GPT-NeoX at four scales — 160M, 1B, 2.8B, **20B** — plus AI2 OLMo, Alibaba Qwen). The η → ε bridge conditions next-token likelihood with effect sizes that grow then plateau across Pythia / GPT-NeoX scale, strengthen on OLMo, reach the strongest Foundation-28 effect on Qwen2.5-1.5B (+0.7960, p = 2.92×10⁻¹²), and produce the strongest single bridge result in the project record on the 40-Element axis at GPT-NeoX-20B under the canonical `S9-40E-ORIGINAL-BASELINE-READOUT` methodology (+1.412 probe-readable Δ, +1.498 gold-readable Δ, +2.881 partner margin, 80 cases; raw-symbol controls at +0.014 confirm the ε-realization mechanism is structural, not symbolic). The 20B chain closes on two cognitive axes. Evidence Packets are disk-persisted with append-only hash chains (single-instance restart-survival proven; multi-instance / host-loss durability NOT proven), tamper-evident through a five-check verify endpoint (in-server payload / log / chain / anchor-manifest + external S3 round-trip), three-state UI surfacing of S3-anchor trust (verified / receipt-only / failed), externally anchored with optional S3 Object Lock (Governance mode, ~30-day rolling window, operator-overridable via `s3:BypassGovernanceRetention` — so the guarantee is tamper-evidence on re-verify, not physical immutability), and gated such that the final ACCEPT verdict requires mechanically-verified WORM-retention proof or is downgraded to FLAG_FOR_HUMAN_REVIEW automatically.

> **No ACCEPT verdict stands in the project record.** The Stage 9 40E validation packet's honest WORM-retained verdict is **FLAG_FOR_HUMAN_REVIEW**; the previously reported 2026-05-28 ACCEPT was a pre-fix overclaim from a candidate-only `control_proof` and has been withdrawn. Per-customer production ACCEPT verdicts remain NOT LICENSED, and a scoped-validation ACCEPT would not equal a customer-production ACCEPT in any case.

The product is positioned for two markets simultaneously: a **developer market** (pre-deployment evaluation, hallucination root-causing, structured prompt engineering, distillation verification, adversarial debugging, cross-model migration audits, CI quality gates) and an **enterprise market** (regulatory-compliance evidence, vendor procurement, AI-error legal defense, board-level AI risk reporting, customer-trust products, red-team integration, acquisition due diligence). Detailed use cases are summarized in §9 closing notes and held in full in the companion use-case map.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative (a from-scratch transformer-based language model built on CAS as its primary architectural substrate). The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

The probing chain closed in May 2026 on the **presence, causal role, and conditionability** of the structure across six model points, two cognitive axes at 20B, and a full audit-grade integrity chain. The further question — whether the structure is **CAS-specific** rather than a generic semantic partition that any coherent ontology of similar shape might induce — remains open. The matched-taxonomy control designed to answer it has not yet returned a pass; its first blind comparator returned an indeterminate **GREY** (§5.10, §9.8). Accordingly, the universality framing in the originating question is treated as an open research question, not a closed claim.

### 2.2 Mission

CAS Harness exists to make the cognitive architecture inside any open-weight large language model **inspectable, validatable, conditionable, and audit-traceable** by an external software service — without requiring the model's vendor to publish interpretability tooling, without modifying the model's weights, and without sacrificing the reserved-language audit discipline required to produce regulator-facing evidence artifacts.

### 2.3 Strategic Relationship to CAS Native

- **CAS Native** is "our model, transparent by construction" — the from-scratch flagship.
- **CAS Harness** is "your model, we make it inspectable" — the cross-model platform.

The two products share the same underlying framework, theoretical apparatus, and evidence-tier discipline. They diverge at the substrate: CAS Native trains weights on CAS-structured targets from scratch; CAS Harness reads CAS structure from a foreign model's existing weights.

---

## 3. Mathematical Foundation

### 3.1 The η → ε Bridge

CAS Harness's central architectural pattern is the eta-epsilon bridge, mathematically grounded in the Noetic Topos paper.

| Map | Direction | Implementation Role |
|---|---|---|
| **η (eta)** | Embedding: structure → realization | Reads CAS class from hidden-state activations via balanced-logistic regression on per-axis fixtures |
| **ε (epsilon)** | Realization: structure → tokens | Emits CAS structure as a readable English prefix for the foreign model |

> **Implementation locator.** Both maps are computed *offline* by the capture / probe worker (`run_stage9_40e_eta_epsilon_bridge.py` for 40E and its F28 sibling). The service-side packet module (`cas_harness_evidence_bridge.py`) does **not** compute η or ε — it normalizes and verifies the worker's output packet and emits the six proof chips. Wherever this sheet says "the bridge computes," read it as the offline worker.

### 3.2 The Section-Retraction Identity

> **ε ∘ η = id** (realization after embedding = identity)
> **η ∘ ε ≠ id** (re-embedding after realization may lose information)

This asymmetry is load-bearing: prerequisite satisfaction is one-directional. Empirically, attempts to steer generation by hidden-state ablation behaved as expected for a one-directional map, while conditioning generation by ε-realization succeeded.

### 3.3 Proposition 5.6 — Counit Surjectivity

For any morphism g, the pullback of the counit ε along g is surjective. Applied to transformer architectures: prefix tokens are attended to by every subsequent position by construction — this is not a hyperparameter, it is the architectural property of self-attention.

Confirmed across four scales within Pythia / GPT-NeoX, two out-of-family architectures (OLMo, Qwen), two cognitive axes at 20B (Foundation-28, 40-Element), two evidence tiers, and component-level necessity + sufficiency tests.

### 3.4 Framework-Internal Diagnostic Tools

Three CAS-internal diagnostic tools are validated:

- **Lacunarity gate** — factorization-gappiness measure; empirical range 0.793 → 0.0016. GPT-NeoX-20B F28 lacunarity 0.006715 is cleaner than all prior Pythia comparators.
- **Fractal classifier** — Stabilizing / Amplifying / Oscillatory / Neutral orbit verdicts. 20B layer-trace class: Amplifying.
- **Weight-geometry alignment** — principal-angle analysis between the CAS Foundation subspace and model output-weight space. Pythia-2.8B at 2.83× random expectation (p = 0.0099). 20B replication on the roadmap.

**Six pre-registered framework-internal predictions have held**, including the 40-Element bridge-magnitude prediction at 20B (+1.412 — strongest in the project record, 2.37× the same-model F28 result).

### 3.5 Two Canonical Method Identities

- **`S7-F28-BALANCED-BRIDGE`** — Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method. Axis: 28 Foundations. Encodes Stage 7 source taxonomy / F28 axis / `LogisticRegression(class_weight='balanced')` probe / full η→ε bridge with matched controls.
- **`S9-40E-ORIGINAL-BASELINE-READOUT`** — Stage 9 40-Element Original-Baseline Balanced-Logistic Eta-to-Epsilon Readout Method. Axis: 40 Elements. Encodes Stage 9 role-bound + counterfactual + Focus-marker fixture / 40E axis / balanced-logistic probe / pre-measured text-baseline adversary (49.24%) / full η→ε bridge with matched controls / `cas_beats_text_claim_allowed` JSON guard.

### 3.6 Audit-Grade Integrity Chain

A five-layer cryptographic integrity chain that survives **single-instance** server restart (multi-instance / host-loss durability NOT proven — see §9.10), detects local tampering, detects full-server compromise, mechanically verifies WORM retention on every audit call, and forces non-WORM-retained packets to downgrade from ACCEPT to FLAG_FOR_HUMAN_REVIEW.

1. **Disk Persistence.** Every merged Evidence Packet is written to a disk-backed store on creation; regression-tested for bit-identical reload after memory clear. **Scope:** durability is proven for single-instance restart-survival only — the deployment runs one Postgres server with no replica and no failover.
2. **Append-Only Hash Chain.** Each packet write appends a JSONL entry to a `cas_harness_evidence_chain` log; every entry includes a cryptographic fingerprint of the previous entry. Tampering with any historical entry shatters every subsequent fingerprint and is detectable in linear time.
3. **Five-Check Verify Endpoint** (`/evidence/{trace_id}/verify`) — runs five independent checks per request: (1) packet payload hash, (2) hash-log entry exists, (3) hash-chain continuity from genesis, (4) local anchor-manifest consistency, (5) external S3 round-trip (`GetObject` + hash). Any failure returns `partial_mismatch` with the specific layer named; the endpoint never returns a silent "OK."
4. **External Anchoring with Mechanical WORM.** Three operator-configurable modes (`disabled` / `local` / `s3`). In `s3` mode with Object Lock, the verify endpoint and deployment smoke script call **`HeadObject`** on every anchor object, confirm `ObjectLockMode` is **`GOVERNANCE`**, and confirm `ObjectLockRetainUntilDate` is in the future. **Governance mode is operator-overridable** (`s3:BypassGovernanceRetention`); the mechanism therefore proves retention is *present and current at audit time* and makes any override *tamper-evident* — it is **not** a proof of physical immutability, and the retention window is an approximately **30-day rolling** one, not permanent.
5. **ACCEPT-Requires-WORM Gate.** The verifier's final ACCEPT verdict requires `packet_proof` for all three retention conditions simultaneously: (a) anchor written, (b) S3 object re-read and hash-matched, (c) Object Lock retention mechanically active. If any one is missing, an explicit ACCEPT is automatically converted to **FLAG_FOR_HUMAN_REVIEW**. The gate mechanism is verified; **no packet has passed it to a standing ACCEPT** (the only prior ACCEPT was withdrawn — see §1, §5.9).

**Three-state UI trust surface.** The Audit Console Evidence Drawer renders "S3 object verified" (full 5-check incl. round-trip), "Anchored to S3" (receipt at write time, no live re-read), or "S3 verify failed" (round-trip ran, found a discrepancy). The UI never silently upgrades trust; reviewers see what was actually confirmed at the moment of audit. The UI does not create verdicts — it explains what the backend runner returned.

**Composite property.** Any verifier — including a regulator with read-only access to the verify endpoint and the S3 bucket — can independently re-verify a packet without operator cooperation. Tampering at any layer (packet, log, chain, manifest, S3 anchor, or Object Lock retention) is detected on the next `/verify` call and named explicitly.

---

## 4. Architecture

### 4.1 System Overview

```
ENGLISH PROMPT
     │
     ▼
FOREIGN OPEN-WEIGHT MODEL (Pythia 160M / 1B / 2.8B / GPT-NeoX-20B, OLMo, Qwen, future families)
     │
     ├── Multi-layer hidden-state capture
     │       │
     │       ▼
     │   COGNITIVE AXIS PROBES (η) — balanced-logistic linear classifiers
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
            DISK PERSISTENCE → HASH CHAIN → 5-CHECK VERIFY → S3 ANCHOR → WORM (Governance)
                  │
                  ▼
            ACCEPT-REQUIRES-WORM GATE — ACCEPT needs all three retention proofs
                  │
                  ▼
            AUDIT CONSOLE UI — three-state trust surfacing
                  │
                  ▼
            VERDICT (ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS)
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
| Disk-persisted packet store (single-instance) | Validated |
| Append-only hash chain | Validated |
| Five-check verify endpoint | Validated |
| Three-state UI trust surfacing | Validated |
| External anchoring service (disabled / local / S3) | Validated; **s3 mode active in production** |
| HeadObject mechanical WORM verification (Governance mode) | Validated |
| ACCEPT-requires-WORM gate | Validated (gate mechanism; no standing ACCEPT) |
| Fleet build — Probe Workers + Fleet Executor + Scale Planner | Validated (apparatus); 300B = ENGINEERED, NOT VALIDATED |
| Fleet-topology verifier gate (conservative-default at scale) | Validated |
| Fragment-payload SHA-256 commitment (anti-misattribution) | Validated |
| Audit Console UI surface | Validated |
| Authenticated delivery API | Validated |
| Verification Stack (runtime accept / suppress) | Validated |
| Mode Selector (3 customer-configurable modes) | Validated |
| Generation Readiness Gate (4-tier discipline) | Validated |
| MTC pre-registration infrastructure (dual-labeled fixture generator, eligibility gate) | Validated (open evidence tier) |
| TKS-Meaning Preservation Rule enforcement (Surface Gate + Recoverability Gate) | Validated |
| Converted-checkpoint provenance schema (Grok-1 BF16) | Validated (in-flight scale extension, infrastructure only) |
| Two-bridge hidden-content detector | Prototype |

### 4.3 Three Customer Deployment Modes

Hosted / Bring-your-endpoint / Self-hosted. Each supports the full integrity chain including external anchoring and the ACCEPT-requires-WORM gate.

### 4.4 Fleet Build — Sharding to 300B+ (ENGINEERED, NOT VALIDATED)

A model too large for one worker is sharded across **N Probe Workers**, each hosting a sub-harness on its layer slice. Coordination is handled by a **Fleet Executor** (stitches per-worker chips, reconciles probe overlaps at shard seams, coordinates cross-worker ablation by computing the projection direction once and applying it identically at each worker's relevant layer) and a **Scale Planner** (worker / layer assignment and topology planning). Each sub-harness runs the same probe stack locally, emits proof chips for its slice, and **commits a fragment SHA-256 of its raw activation tensor** so the fleet aggregator can prove no worker swapped tensors (anti-misattribution). **Raw activations never cross the wire** — only chips, hashes, and local verdicts travel.

The **fleet-topology verifier gate** applies a **conservative-default policy**: a fleet ACCEPT is emitted **only if** every worker independently reports ACCEPT, all fragment hashes verify, and topology is complete; any worker reporting SUPPRESS / FLAG, any invalid fragment hash, or any absent / timed-out worker forces the fleet verdict to FLAG / SUPPRESS. The unified packet then passes through the same ACCEPT-requires-WORM gate as a single-model packet.

> **Scale honesty.** The Fleet build is engineered toward **300B+** parameters and is exercised against an in-flight frontier-scale target (a 314B BF16 community checkpoint; see §5.11). The 300B figure describes **engineered capacity, not a validated result**: no detection, causal, or bridge result above 20B is licensed. "300B" is **ENGINEERED, NOT VALIDATED.**

### 4.5 Audit Console Surface

Renders verdict, confidence, six proof chips with detail-on-hover, verifier source, scope label, coverage label, and boundary disclosure. The three-state S3-anchor trust surface distinguishes "S3 object verified" / "Anchored to S3" / "S3 verify failed." When an explicit verifier ACCEPT is downgraded due to missing WORM proof, the UI shows the verdict as FLAG_FOR_HUMAN_REVIEW with a tooltip naming which of the three WORM proofs failed (anchor write / re-read match / Object Lock active). Architectural invariant: the UI does not create verdicts; it explains what the backend runner returned.

> **Reference diagrams (held for NDA code-walk).** Five reference-grade architecture diagrams — Phase 1 standalone structure, Phase 2 attached-to-one-model, Phase 3 Fleet Executor on a 300B model, η→ε bridge detail, and the η₁/η₂ two-bridge hidden-content detector — are available to technical reviewers under NDA. Each component named in a diagram corresponds to a discoverable subsystem in the codebase.

---

## 5. Validated Capabilities

### 5.1 Cognitive Structure Detection

| Axis | Classes | Model | Probe Accuracy | Lift Over Text Baseline | Status |
|---|---:|---|---:|---:|---|
| 10 Noetics | 10 | Pythia-160M | 73.9% | +27.5 pp | Validated |
| 28 Foundations | 28 | Pythia-160M | 78.6% | +28.9 pp | Validated |
| 28 Foundations | 28 | Pythia-1B | 82.4% | — | Validated (cross-scale) |
| 28 Foundations | 28 | Pythia-2.8B | 85.9% | — | Validated (cross-scale) |
| 28 Foundations | 28 | GPT-NeoX-20B | 86.86% | — | Validated (`S7-F28-BALANCED-BRIDGE`) |
| 28 Foundations | 28 | OLMo-1B | 90.6% | — | Validated (cross-architecture) |
| 28 Foundations | 28 | Qwen2.5-1.5B | 82.0% | — | Validated (cross-architecture) |
| 40 Elements | 40 | Pythia-160M | 89.8% | +39.7 pp (text baseline 49.24%) | Validated |
| **40 Elements** | **40** | **GPT-NeoX-20B** | **95.625%** | **+46.4 pp** | **Validated (`S9-40E-ORIGINAL-BASELINE-READOUT`)** |
| 5 Operators | 5 | Pythia-160M | 99.2% | +3.6 pp | Validated |
| 10 Expression Shapes | 10 | Pythia-160M | 93.0% | +28.6 pp | Validated |
| 10 Compiler-Valid Formulas | 10 | Pythia-160M | 90.0% | +26.0 pp | Validated |
| Multi-Layer Trace classification | 10 | Pythia-160M | 95.4% | — | Validated |

> **Disclosure on the GPT-NeoX-20B 40-Element headline (95.625% / +46.4 pp).** Two facts a reviewer should have up front: (1) the readout **peaks at layer 2 of 44** — an early-layer peak, consistent with the probe reading near-surface lexical features as much as deep structure; (2) the "+46.4 pp lift" is measured against a CountVectorizer / text-hash baseline (≈49.24% / 50.0%), a deliberately weak adversary — a 20B model encodes surface tokens far more richly than bag-of-words, so beating that baseline is **necessary but not sufficient** for a CAS-specific signal. The shuffled-label control passes cleanly (2.62% vs 2.5% chance), so the readout is not fitting label noise. **Group-disjointness is a recorded check, not a claim:** the eval report carries `train_test_group_overlap_count = 0` over 4,160 counterfactual-pair groups (caveat: the raw scenario source is a gitignored artifact, so independent re-derivation requires the recorded fields or the scenario file out of band; a hashed manifest is a tracked follow-up). The strong-adversary test (matched-taxonomy) is **OPEN** (§5.10, §9.8). The LICENSED reading of this row is *"the model linearly encodes the label distinction above a surface-text classifier,"* not *"CAS-specific cognition at 95.6%."*

### 5.2 Readout-Causal Validation

Five axes pass collapse-to-exact-chance under subspace ablation with clean random nulls. Notable result: **40-Element subspace ablation at GPT-NeoX-20B: 95.625% → 66.897% (28.73 pp drop), random matched 0.068 pp mean / 0.268 pp max — 107× signal-to-noise.** The pre-registered ≥30 pp / ≤65% gate was narrowly missed by 1.27–1.90 pp on each disjunct; documented openly. A v2 ablation sweep with broader top-k and layer cover is in the open-gate queue.

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

**GPT-NeoX-20B 40-Element is the strongest single probe-readable bridge result in the project record** — 1.77× the prior Qwen Foundation-28 record and 2.37× the same-model F28 result. Raw-CAS prefixes stay null at every scale (−0.020 to +0.003), confirming the effect is ε-realization, not symbol recognition.

### 5.4 Factorization Quality (Lacunarity)

F28 lacunarity progression from 0.021 (Pythia-160M) → 0.006715 (GPT-NeoX-20B); Drive-within-Foundation 0.002752; Register-within-Foundation 0.001283. 40E lacunarity at 20B is on the roadmap.

### 5.5 Framework Predictive Validity

Six pre-registered framework-internal predictions have held, including the 40E bridge-magnitude prediction at 20B. The framework's own diagnostic tools produced numerical predictions of experimental outcomes before the experiments ran.

### 5.6 Cross-Scale and Cross-Architecture Validation

Both canonical methods replicate at 20B parameter scale without protocol adjustment. The mechanism is empirically established as not lab-specific, not corpus-specific, not language-specific, not scale-bounded below 20B, and not axis-specific. Cross-architecture closure on Foundation-28 holds across three independent families (Pythia / GPT-NeoX, OLMo, Qwen).

### 5.7 Weight-Geometry Alignment

Pythia-2.8B: CAS Foundation subspace shows output-weight alignment 2.83× random expectation (p = 0.0099). 20B replication on the roadmap.

### 5.8 Multi-Layer Trace + Blind-Spot Detection

Validated; the detector distinguishes model-side weakness from readout-position weakness. 20B layer-trace class: Amplifying.

### 5.9 Component-Level Causal Localization

- **Head-level:** 78% → 19% (p = 0.0323 vs matched control); 100% sufficiency recovery via path patching.
- **Sparse MLP-neuron-cover:** 112/112 at p < 10⁻³³; bit-exact patch-back recovery.
- **Output-side drive-local steering:** Pythia-160M (+0.85, 181/245, p = 2.0×10⁻¹⁴), Pythia-1B (+0.84, 54/56, p = 2.2×10⁻¹⁴), Qwen2.5-1.5B (+0.90, 56/56 unanimous, p = 1.4×10⁻¹⁷). Bounded to drive-local eraser-channel methodology; global / universal-cover steering was empirically falsified (too coarse). Cross-architecture scope: two families (Pythia + Qwen); OLMo replication is the next pre-registered gate for three-family parity.

### 5.10 Matched-Taxonomy Control (MTC) — Open Tier, First Blind Comparator = GREY

Every closed tier above establishes that the model linearly encodes whatever distinctions the CAS labels track, and that this encoding is causally load-bearing. **None of these tiers distinguishes** (a) "the CAS label set is linearly recoverable and causally load-bearing" (LICENSED) from (b) "the recovered structure is **CAS-specific** rather than one coherent relabeling of generic semantic structure" (NOT YET LICENSED). Claim (b) is inherently **comparative** and can only be earned against cardinality-matched alternatives.

Two pre-registered fixture attempts produced documented nulls before reaching the matched-comparator gate:

- **MTC v1 — Surface Gate fail (text leakage).** Text-baseline classifier scored 100%; the surface text leaked the answer key. Rejected before activation capture. Build error; fixture redesigned.
- **MTC v2 — Recoverability Gate fail (TKS-meaning removal).** Aggressive de-leakage removed surface leakage (text baseline → ~1%) but also stripped the TKS-canonical meaning and assigned labels by random shuffle, so CAS recoverability collapsed to ~chance (40E +1.00 pp, F28 +2.158 pp; required +20 pp). Diagnosed as a **meaning-removed** fixture (a build error), not a signal-absent one. This null motivated the **TKS-Meaning Preservation Rule** (§6).

**MTC Condition-3 — first blind matched-taxonomy comparator (2026-06-03) = GREY.** The first comparator to clear both fixture-validity gates and run blind (GPT-NeoX-20B; CAS meaning carried in everyday scenarios, topic/frame orthogonal to CAS, domain carried as register; CAS scored blind against a cardinality-matched control on the same activations) returned **GREY**: CAS did **not** beat the matched control by the pre-registered margin, landing in the pre-registered indeterminate band. **A GREY is not a pass** — CAS-specificity remains **NOT LICENSED**. **Scope:** this GREY is confined to the Condition-3 comparative-specificity test; it does **not** touch the 40E hidden-readout detection (95.625%) or the η→ε bridge PASS, which stand as before (subject to the separate, pre-existing signal-vs-leakage adjudication in §9.8).

Both nulls and the GREY comparator are part of the discipline record, not concealment. The matched-taxonomy specificity claim and the "universal rather than something we invented" framing both remain NOT LICENSED.

### 5.11 Frontier-Scale (>20B) Extension — In-Flight, Not Licensed

CAS Harness is mid-execution on its first audit-chain extension above 20B parameters, against a **community Hugging Face BF16 conversion of a 314B-parameter model whose publisher of record ships only a JAX original**. Every Evidence Packet generated against this target carries an explicit **converted-checkpoint provenance schema** — `model_publisher_of_record`, `original_checkpoint_format`, `consumed_checkpoint`, `conversion_path`, `conversion_authority` (third-party, not the publisher), `consumed_checkpoint_revision_sha` (pinned HF commit), `consumed_checkpoint_sha256_per_shard`, and `conversion_audit_status: unverified-by-cas-harness`. These fields make it unambiguous that **CAS Harness audited the model that ran**, not the model the publisher released directly.

**LICENSED about this work:** the audit infrastructure (provenance schema, hash-pinned download, per-shard SHA-256, watcher-gated smoke). **NOT LICENSED:** any audit *result* — no detection, causal, or bridge result has been generated above 20B. Frontier-scale validation remains NOT LICENSED.

### 5.12 Hidden-Content / Suppression Detection (Prototype)

A two-bridge architecture (η₁ from internal hidden states; η₂ from re-probed emitted text) surfaces internal-vs-emitted divergence and classifies it into seven typed hiding shapes (withheld content, self-censored content, latent capability, suppressed reasoning, frame manipulation, persona drift, involution content). Output is a **bounded typed-class assignment** that cannot confabulate beyond the seven-class set — positioned as a complement to published "evaluation-awareness" findings where natural-language self-description can confabulate. **Prototype tier:** wired, returns typed-class output, qualitatively interpretable; **no pre-registered confirmatory gate has closed; not licensed for production accept / suppress decisions.**

### 5.13 Verification Stack, Mode Selector, Generation Readiness Gate

- **Verification Stack — runtime-safe accept / suppress:** 87.6% accept rate at 99.78% accepted accuracy; 0.22% silent error rate. Uses only non-oracle internal states at inference; gold labels required only at validation time. Every suppression carries reasons.
- **Mode Selector:** three customer-configurable modes — HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE.
- **Generation Readiness Gate:** four-tier action discipline — allow / caveat / constrain / suppress.

### 5.14 Evidence Packet Schema

Six proof chips (model / readout / baseline / causal / control-cover / output-bridge), each SHA-256-committed; one verifier report (verdict + confidence + scope + coverage + boundary); audit-chain provenance (payload SHA-256 + hash-log pointer + chain continuity + anchor manifest + HeadObject WORM status); fleet-level provenance (worker-fragment SHA-256 commitments + merge attestation); converted-checkpoint provenance for frontier-scale targets.

### 5.15 Tier Closure Summary

| Evidence Tier | Status |
|---|---|
| Readout (detection above baseline) | Closed on both 20B axes |
| Readout-causal (collapse to exact chance under ablation) | Closed for 5 prior axes; 40E 20B documents a 107× SNR near-miss of the pre-registered gate, openly |
| Likelihood-conditioning via η → ε bridge | Closed on both 20B axes (F28 +0.596; 40E +1.412 — project record) |
| Factorization (lacunarity) | Closed on F28; 40E 20B on roadmap |
| Framework-predictive validity (6 predictions held) | Closed |
| Cross-scale within architecture (4 model points) | Closed |
| Cross-architecture (3 families) | Closed on F28 |
| Scale extension beyond 2.8B (20B) | Closed under TWO named methodologies |
| Weight-geometry alignment | Closed at Pythia-2.8B; 20B on roadmap |
| Multi-layer trace + blind-spot detection | Closed |
| Component-level causal localization (head + sparse neuron-cover) | Closed |
| Output-side behavioral steering (drive-local, 2 families) | Closed |
| Output-side steering 3-family parity (OLMo replication) | Open |
| Runtime-safe acceptance / suppression | Closed |
| Mode-configurable verification | Closed |
| Four-tier generation readiness | Closed |
| Authenticated Evidence Packet delivery | Closed |
| Evidence Packet schema (6 proof chips + verifier report) | Closed |
| Disk-persisted packet store (single-instance restart-survival) | Closed (single-instance only) |
| Multi-instance / host-loss durability (replica + failover) | **Open — NOT proven** (one Postgres server, no replica/failover; see §9.10) |
| Append-only cryptographic hash chain | Closed |
| Five-check verify endpoint with active S3 round-trip | Closed |
| Three-state UI trust surfacing | Closed |
| External anchoring active in production (`mode=s3`) | Closed |
| HeadObject mechanical WORM-retention verification (Governance mode) | Closed — proves retention present/current at audit time; operator-overridable, so tamper-evidence not immutability |
| ACCEPT-requires-WORM-retention gate | Closed (gate mechanism); **no packet has passed it to a standing ACCEPT** |
| Fleet-topology verifier gate + fragment SHA-256 commitment | Closed |
| ~~First ACCEPT verdict in project record (Stage 9 40E packet)~~ | **WITHDRAWN — pre-fix overclaim (candidate-only control_proof); honest verdict is FLAG_FOR_HUMAN_REVIEW; no ACCEPT stands** |
| Matched-taxonomy CAS-specificity | **Open** — v1 nulled (text-leak), v2 nulled (meaning-removal), first blind comparator (Condition-3, 2026-06-03) = GREY; NOT LICENSED |
| Frontier-scale (>20B) validation | **Open** — in-flight; audit infrastructure live; no results LICENSED; 300B = ENGINEERED, NOT VALIDATED |
| Hidden-content / suppression detection (prototype) | Open |
| Surface-text steering at scale | Open |
| Multi-Harness Composition coordinator | Open |
| Multi-turn Evidence Packet reconstruction | Open — next product gate |
| Per-customer production ACCEPT verdicts | Open (validation-packet scope only at this time) |

---

## 6. Methodology Discipline as Competitive Differentiator

CAS Harness's audit-grade methodology is itself a product feature. Nine discipline principles govern every validated stage:

1. **Pre-registered acceptance criteria** — gates and thresholds locked in writing before data runs (with open disclosure of the Stage 9 40E ablation near-miss and the two MTC fixture nulls).
2. **Locked artifact hashes** — activation captures fingerprinted; recapture runs flagged as diagnostic.
3. **Matched controls** — same-kind same-layer matched controls are the pre-registered primary comparison.
4. **Honest NULL discipline** — when a method does not produce its expected result, the result is recorded as a formal NULL and the boundary it establishes is added to the claim ladder. The two MTC nulls and the Condition-3 GREY are the clearest examples.
5. **Reserved-language claim map** — external claims are tied to specific evidence; nothing is asserted beyond what the evidence supports (§8).
6. **Independent reproducibility commitment** — locked manifests + fingerprints enable third-party verification without proprietary access.
7. **Named canonical method discipline** — `S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`.
8. **Audit-grade integrity-chain discipline** — five-layer chain (disk + hash chain + five-check verify + HeadObject mechanical WORM + ACCEPT-requires-WORM gate + three-state UI), independently performable by any external auditor.
9. **TKS-Meaning Preservation Rule** *(equal tier to #1–#8).* A recoverability fixture must preserve the TKS-canonical semantic content of every class it asks the model to recover. The fixture may strip surface answer-key wording (vocabulary anchors, framework names, operator notation) but must not strip the meaning that wording was naming. Meaning-removed prompts produce false NULLs that look like falsifications but are build errors. Every future recoverability fixture must pass, in order, a **Surface Gate** (text-baseline near chance) and a **Meaning Preservation Gate** (independent CAS-competent raters recover labels from meaning at calibrated above-baseline accuracy) before any GPU-tier capture is authorized.

This discipline produces a methodologically stronger evidence base than the majority of contemporary published interpretability work. The nulls and the GREY are documented precisely because selectively reporting only confirmatory results would void this differentiator.

---

## 8. Reserved-Language Claim Map

External-facing claims must use this table. LICENSED claims are evidence-backed; NOT-LICENSED claims must not appear in any external or public copy.

| Claim | Status |
|---|---|
| "CAS reads cognitive structure from foreign open-weight models" | LICENSED |
| "Structure is causally load-bearing" | LICENSED (F28 chain); 40E 20B documented as a 107× SNR near-miss — see §5.2 |
| "Mechanism is framework-predicted (six predictions held)" | LICENSED |
| "We condition the next-token probability distribution" | LICENSED |
| "Cross-architecture (Pythia/GPT-NeoX + OLMo + Qwen)" | LICENSED |
| "Cross-scale (Pythia/GPT-NeoX 160M / 1B / 2.8B / 20B)" | LICENSED |
| "Validated under two named canonical methodologies" | LICENSED |
| "Validated up to 20B parameters on two cognitive axes" | LICENSED |
| "Strongest single bridge result in project: 40-Element at 20B (+1.412 probe / +1.498 gold / +2.881 partner)" | LICENSED |
| "Probe-handoff to oracle efficiency 94.3% on 40-Element at 20B" | LICENSED |
| "Evidence Packets disk-persisted (single-instance restart-survival), hash-chained, tamper-evident, externally anchorable" | LICENSED (single-instance durability only; multi-instance/host-loss NOT proven — see §9.10) |
| "Verify endpoint runs five independent checks per call, including active S3 round-trip" | LICENSED |
| "Audit Console UI distinguishes three S3-anchor trust states (verified / receipt-only / failed)" | LICENSED |
| "HeadObject mechanical WORM check confirms Object Lock (Governance mode) retention is present and current per-anchor at audit time" | LICENSED |
| "ACCEPT-requires-WORM gate: an explicit ACCEPT requires all three retention proofs or is downgraded to FLAG_FOR_HUMAN_REVIEW" | LICENSED (gate mechanism; no packet has passed it to a standing ACCEPT) |
| "S3 Object Lock Governance retention makes any operator override of an anchor tamper-evident on the next verify call" | LICENSED (tamper-evidence, NOT physical immutability) |
| "S3 Object Lock immutability — chain fingerprints cannot be modified even by the operator" | NOT LICENSED (Governance mode is operator-overridable via `s3:BypassGovernanceRetention`; ~30-day rolling retention; the guarantee is tamper-evidence, not immutability/COMPLIANCE-mode) |
| "Fleet build shards models across Probe Workers / Fleet Executor / Scale Planner with a conservative-default verifier gate" | LICENSED (apparatus) |
| "Validated at 300B / frontier scale" | NOT LICENSED — 300B is ENGINEERED, NOT VALIDATED; no result above 20B is licensed |
| "Blind-spot detection per-class with readout-vs-model-side disambiguation" | LICENSED |
| "Hidden-content / suppression detection at CAS-class granularity" | LICENSED with caveats (prototype tier; not for production decisions) |
| "Runtime-safe accept/suppress decisions without gold labels at inference" | LICENSED |
| "Head-level + sparse MLP-neuron-cover causal localization with necessity AND sufficiency" | LICENSED |
| "Drive-local eraser-channel steering, cross-scale within Pythia + cross-architecture on Qwen" | LICENSED |
| "TKS-Meaning Preservation Rule governs all recoverability fixtures (Surface Gate + Meaning Preservation Gate)" | LICENSED (methodology) |
| "MTC stage pre-registered with two openly documented fixture nulls (v1 leak / v2 meaning-removal)" | LICENSED (methodology) |
| "Frontier-scale converted-checkpoint audit infrastructure deployed with provenance disclosure schema" | LICENSED (infrastructure only — no audit results) |
| "First ACCEPT verdict in project record on Stage 9 40E validation packet" | NOT LICENSED — WITHDRAWN (pre-fix overclaim; candidate-only control_proof; honest verdict FLAG_FOR_HUMAN_REVIEW; no ACCEPT stands) |
| "Per-customer production ACCEPT verdicts" | NOT LICENSED (validation-packet scope only) |
| "A scoped-validation ACCEPT equals a customer-production ACCEPT" | NOT LICENSED (the two are distinct; scoped-validation ≠ customer-production) |
| "Frontier-scale (>20B) validation" | NOT LICENSED |
| "Single-neuron monosemantic localization" | NOT LICENSED (sparse-cover is the validated unit) |
| "Universal interpretability platform" | NOT LICENSED (three families ≠ universal) |
| "CAS structure is CAS-specific rather than a generic semantic partition" | NOT LICENSED (Stage MTC open; two fixture nulls; first blind comparator Condition-3 = GREY) |
| "Absolute uniqueness — no system can ever match CAS" | NOT CLAIMED / NOT THE TARGET (see §9.8.1; the target is probabilistic speciality, which is itself still OPEN) |
| "Universal rather than something we invented" | NOT LICENSED (specificity required first; Condition-3 GREY) |
| "Output-side steering at 3-family parity with readout claim" | NOT YET LICENSED (OLMo replication open) |
| Any "certification / guaranteed / 100% / world-first / only" claim | NOT LICENSED (no third-party certification held; see standing disclaimer + §9.11) |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural
Three architecture families validated (Pythia/GPT-NeoX, OLMo, Qwen). Three ≠ universal. Llama, Mistral, Phi, Gemma untested. Decoder-only transformers only; encoder-only (BERT) and encoder-decoder (T5) untested. Closed-API models (Claude, GPT, Gemini) cannot be onboarded — CAS Harness requires hidden-state access. Probes are per-model; the methodology transfers across architectures, trained probes do not.

### 9.2 Scale
Up to 20B parameters across two cognitive axes under two named canonical methodologies. Beyond 20B: the Fleet build is engineered toward 300B+ and a 314B converted-checkpoint extension is in flight, but **no audit result above 20B is licensed** and **300B is ENGINEERED, NOT VALIDATED**. Frontier-scale validation remains NOT LICENSED.

### 9.3 Modal
Text only. No multimodal (image, audio, video) validation.

### 9.4 Per-Class
Some CAS classes carry more signal than others; affective register is systematically harder to read than transcendent. Blind-spot classes are identified with readout-vs-model-side disambiguation. Per-class claims are bounded by the per-class evidence.

### 9.5 Granularity
Head-level and sparse-MLP-neuron-cover localization validated. Single-neuron monosemantic localization is NOT claimed.

### 9.6 Evidence-Tier
Detection / readout-causal / η→ε bridge / weight-geometry are validated as named in §5.15. Hidden-content detection is prototype. Surface-text steering at scale is open.

### 9.7 Verifier Discipline
- v0 verifier confidence rule: `confidence = readout_chip.accuracy`. Multi-factor v1 confidence on the roadmap.
- Stage 9 40E ablation near-miss (28.7 pp / 66.9% vs pre-registered ≥30 / ≤65) documented openly; threshold-policy discrepancy is auditable.
- **Withdrawn ACCEPT:** the previously reported "first ACCEPT verdict" (Stage 9 40E validation packet) is withdrawn — it rested on a candidate-only `control_proof` stamped verified before the fixing commit. The honest WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW; the console honesty gate downgrades it accordingly; no ACCEPT stands.
- **ACCEPT-requires-WORM gate** mechanically downgrades even an explicit ACCEPT to FLAG_FOR_HUMAN_REVIEW if any of the three retention proofs is missing. Gate verified; no packet has passed it to a standing ACCEPT.
- **HeadObject mechanical WORM verification** confirms Object Lock Governance-mode retention is present and current per-anchor; Governance mode is operator-overridable, so this proves tamper-evidence, not physical immutability.

### 9.8 Comparative-Specificity
The matched-taxonomy specificity claim ("CAS is CAS-specific rather than a generic semantic partition") is **NOT LICENSED**. Stage MTC is openly pre-registered with two documented fixture nulls (v1 text-leak, v2 meaning-removal — both build errors caught by pre-registered gates, not findings against CAS) and a first blind comparator (GPT-NeoX-20B, Condition-3, 2026-06-03) that returned **GREY** (CAS did not beat the cardinality-matched control by the pre-registered margin). The GREY is scoped to the comparator and does **not** touch the 40E detection or η→ε bridge.

> **Signal-vs-leakage adjudication is OPEN, not closed.** The v1 detection-lift *interpretation* is not yet settled: the original 40E fixture carries a 49.24% exact-fixture text baseline; the readout peaks at layer 2 of 44; and the v1 prompt embeds each element's **definition gloss verbatim** (the class code and framework words were stripped, but the meaning-bearing gloss was not). All three facts are consistent with a meaningful fraction of the lift being gloss/surface-carried. The pre-registered adjudicator is **Stage LSA (Leakage-vs-Signal Adjudication)** — a judge-based test (CAS-competent model-blind raters plus an independent `gemini-3.1-pro-preview` rater) that takes the original v1 items, applies a frozen "remove answer-key wording, preserve TKS meaning" strip contract, and tests whether labels are still recoverable from meaning alone. Until Stage LSA returns, the LICENSED reading of the 95.625% readout is the narrow one: **the model linearly encodes the label distinction more strongly than a bag-of-words text classifier** — not that the lift is established CAS-specific signal.

**9.8.1 Uniqueness claim posture — probabilistic speciality, not absolute uniqueness.** CAS Harness does **not** claim, and does not treat as its target, *exhaustive* uniqueness — that no other label system (real, synthetic, or not-yet-invented) could match CAS on this task. That bar is not empirically reachable (it would require testing every framework, including future and adversarially-constructed ones) and is **explicitly disclaimed**. The target is narrower and falsifiable: **probabilistic speciality** — evidence, accumulated across *repeated blind matched-taxonomy comparators*, that CAS captures non-arbitrary structure a cardinality-matched control does not. The honest claim ladder:

1. **Detection (strongest today).** "CAS/TKS structure is linearly readable from model activations." Supported by the GPT-NeoX-20B 40E readout (95.625%), **LICENSED** under the narrow reading in §9.8 (stronger than a bag-of-words classifier), with the signal-vs-leakage adjudication (Stage LSA) still **OPEN**.
2. **Comparative speciality (the realistic next claim).** "CAS outperforms tested matched non-CAS label systems." **NOT yet supported** — the one blind matched comparator run to date (Condition-3) is GREY; no clean run yet exists in which a fair, matched, independent rival taxonomy scored low.
3. **Probabilistic speciality (the eventual investor/scientific claim).** "Repeated matched-comparator wins + strong readout make CAS likely to be capturing non-arbitrary structure." Reachable but **not yet earned** — it requires at least one clean blind matched-comparator *win*, which has not occurred.
4. **Absolute uniqueness.** "No system can ever match CAS." **Explicitly not claimed, and not the target.**

> Net: **detection is LICENSED; comparative and probabilistic speciality are OPEN / NOT LICENSED** pending a matched-comparator win; **absolute uniqueness is disclaimed.** The single result that moves CAS-specificity from rung 2 to rung 3 is one blind matched-taxonomy comparator in which CAS beats the cardinality-matched control by the pre-registered margin. Detection and readout are the **licensed core**; uniqueness/speciality is neither licensed nor framed as a closed or proprietary claim.

### 9.9 Frontier-Scale Scope
Frontier-scale (>20B) audit work is **infrastructure-only LICENSED, results-NOT-LICENSED**. The provenance schema, hash-pinned download, per-shard SHA-256, and converted-checkpoint disclosure (the consumed checkpoint is a third-party HF conversion of a JAX original; the conversion is not audited by CAS Harness) are operational. No detection, causal, or bridge result has been generated. 300B remains ENGINEERED, NOT VALIDATED.

### 9.10 Durability
Evidence-Packet durability is proven **only** for single-instance restart-survival: on one paid-disk instance, packets survive restart, redeploy, and crash with regression-tested bit-identical reload. **Multi-instance and host-loss durability are NOT proven** — the deployment runs a single Postgres server with no replica and no failover. High availability, geographic redundancy, and host-loss durability are **NOT LICENSED**. This is an infrastructure-maturity bound, not a property of the integrity chain itself (the hash chain and external S3 anchor remain independently re-verifiable wherever the packet data survives).

### 9.11 No Certification
Noetic Compass holds **no** SOC 2, ISO/IEC 42001, or other third-party security or compliance certification. Evidence Packets are **designed to produce regulator-facing evidence artifacts** that support compliance documentation; they do **not** by themselves satisfy any regulation, and nothing in this document is legal advice. Framings such as "regulator-grade by construction," "court-admissible," "compliant," "certified," "guaranteed," "100%," "world-first," or "only" are **NOT claimed**. Where regulatory regimes are named, they describe the documentation need the artifacts are designed to support, not a certification held.

> **Use-case note (held in full in the companion map).** Developers use CAS Harness for pre-deployment model evaluation, hallucination root-causing, structured prompt engineering, distillation verification, adversarial-input debugging, cross-model migration audits, and CI cognitive-property quality gates. Enterprises use it for regulatory-compliance evidence (EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, SR 11-7), vendor procurement, AI-error legal defense, board AI-risk reporting, customer-trust products, red-team integration, acquisition due diligence, and insurance underwriting — each subject to the certification and legal-advice disclaimers above.

---

## 10. Comparison Landscape

| System | CAS Harness Difference |
|---|---|
| Vendor neural-network / introspection analysis (single-family, self-report-based) | Three sizes of one family vs **six models in three architecture families on two cognitive axes at 20B**. Published self-report/introspection work admits a "confabulation" tier (natural-language self-description can be verifiably ungrounded); CAS Harness does not use the self-report modality at all — every verdict is a typed classification read from hidden states and validated causally, and the typed-class hidden-content detector (§5.12) cannot confabulate beyond a bounded class set. This is a difference in *kind*, not a quality comparison of two versions of one tool. CAS Harness emits disk-persisted, hash-chained, five-check-verified, HeadObject-WORM-verified (Governance mode, tamper-evident), ACCEPT-requires-WORM-gated Evidence Packets. |
| Linear probes (academic) | Classify activations, report accuracy, usually single-axis. CAS Harness adds causal validation, the η→ε bridge, framework-predictive diagnostics, multi-layer trace, two named canonical protocols, **and** a full audit-grade integrity chain with active external re-verification + mechanical WORM-retention verification (tamper-evidence, not immutability). |
| SHAP / LIME / classical XAI | Output-feature attribution only; CAS Harness reads internal structural cognitive properties with a cryptographic audit chain. |
| AWS Bedrock Automated Reasoning Checks | Output-level formal-logic verification; CAS Harness operates at representation/causal level. **Complementary, not competitive** — both can carry audit-grade evidence packets. |
| Causal scrubbing / mechanistic interpretability | Researcher tooling; CAS Harness productizes the discipline at a different (product) granularity, with an audit chain and a verdict gate. |
| TransformerLens / mech-interp tooling | Open-source research tooling, not a product; CAS Harness is a productized version with an a-priori cognitive framework + audit-grade output. |
| Black-box behavioral testing | Prompt-and-score, any model, no internal access. Complementary, not competitive. |

> Do **not** assert that any specific competing interpretability tool "produces false output." The defensible, sourced claim is modality-based (self-report introspection can confabulate; CAS Harness's typed-class readout cannot exceed its bounded class set), as stated above.

---

## 11. IP & Legal Status

### 11.1 Existing IP
- The CAS framework primitives are the subject of a **pending** USPTO provisional patent application. Patent-pending — US Provisional Application No. 64/037,173, filed 04/13/2026 (Utility—Provisional).
- Mathematical foundation: Noetic Topos paper (journal submission in progress).

### 11.2 Methodology Filings (In-Process — IP-counsel consultation in progress)
The following CAS Harness-specific mechanisms are candidates for separate IP filings and are held from detailed public disclosure until filed:

- η→ε bridge applied to foreign open-weight transformers
- The two named canonical methodologies (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`)
- The Audit-Grade Integrity Chain composite (six-proof-chip packet + verifier report + disk persistence + append-only hash chain + five-check verify endpoint + three-state UI + external anchoring service + HeadObject mechanical WORM-retention verification (Governance mode) + ACCEPT-requires-WORM gate)
- Fragment-payload SHA-256 commitment for fleet evidence merging; the Fleet build (Probe Workers + Fleet Executor + Scale Planner) and fleet-topology verifier gate
- Framework-predictive preflight diagnostic methodology
- The TKS-Meaning Preservation Rule and the Meaning Preservation Gate apparatus
- The MTC pre-registration infrastructure (dual-labeled fixture generator, materializer eligibility gate, pre-committed comparator gates)
- The converted-checkpoint provenance schema and hash-pinned reproducibility apparatus
- Component-level causal localization with necessity + sufficiency tests

### 11.3 External Disclosure Status
This investor-facing document is distributed only under executed NDA. Recipients are not authorized to disclose, reproduce, or use any content beyond the scope of the executed agreement. Additional methodology depth is available under a separate technical-disclosure NDA after initial evaluation. Public disclosure of any §11.2 mechanism prior to filing may affect its patentability; sequencing is subject to patent-counsel guidance.

---

## 12. Maintenance & Validation Update (2026-07-12)

This current addendum records a code-maintenance and red-team pass. It strengthens no previously validated result and changes no claim boundary; every `LICENSED` / `NOT LICENSED` / `OPEN` status in sections 1-11 stands.

**Pushed maintenance branch; no pull request yet.** Branch `fix/cas-harness-findings-20260630` contains pushed commits `5583f7bf`, `9b44a6d1`, `08ad0a4d`, and `3b126f24`. No draft pull request has been opened and there is no PR URL to report. Branch evidence is `1526 passed, 8 skipped, 3 xfailed` full API, `22 passed` focused middleware/CORS, `358 passed` CAS Harness selection, and `233 passed` worker tree. The two prior pytest collection blockers are fixed. These are local/branch engineering results, not hosted-production proof, customer-production proof, or `ACCEPT`.

**CORS/middleware repair (local branch complete; hosted proof OPEN).** Browser-managed CORS credentials are disabled for every origin while explicit Bearer `Authorization` headers remain available. Effective order is `CORS -> RequestId -> AuditLog -> JWTAuth -> RateLimit`. Real Origin-bearing `401` and deterministic `429` responses carry required CORS/request-id behavior without `Access-Control-Allow-Credentials`. Hosted/deployed CORS proof remains `OPEN`, and durable append-only security-audit storage remains `OPEN`.

**RPM/diode correction after adversarial review.** The directional RPM/diode tool is exactly `PROTOTYPE` and `ENGINEERED-NOT-VALIDATED`; real-model result is `unavailable`, maximum claim route is `FLAG_FOR_HUMAN_REVIEW`, causal/prevention/product claims remain `NOT LICENSED`, and empirical bridge remains `OPEN`. It is not in the product branch. Its two executable/test files are removed from the legal-branch tip pending a claim-safe rebuild.

The red team demonstrated concrete bypasses and missing controls: self-attested surface status with no artifact/hash/metric binding; `n_random=0` plus `subsumption_threshold=2.0` manufactured `PASS_DIRECTIONAL_PENDING_REVIEW`; missing hidden-minus-char/length and rank/accuracy-matched non-prerequisite controls; nondetection mislabeled as survival; invalid split fallback; unsafe `allow_pickle=True`; overclaiming reverse causality/no dependence; missing `PROTOTYPE`, provenance, and split evidence; and absent CI/API/Evidence-Packet/runbook integration. No synthetic run or directional output licenses a real-model or product claim.

### Historical maintenance baseline (2026-06-30)

The remainder of this subsection is retained as a dated engineering record. The 2026-07-12 update above governs where states differ.

This addendum records an engineering-maintenance pass. It **strengthens no previously validated result** and changes **no claim boundary**; every LICENSED / NOT LICENSED / OPEN status in §1–§11 stands.

**Operational re-validation (engineering, not a customer-production claim).** The checked-in product branch was re-verified locally: the CAS Harness API/service layer passes its full unit-test suite (harness, auth, middleware, CORS, audit — all green), and the offline worker's readout/ablation/neuron-cover/bridge/merge suites pass. This confirms the checked-in code is internally consistent and test-green; it is **not** a hosted-production, per-customer, or `ACCEPT` claim (those remain as bounded in §1, §5.15, §9).

**Maintenance fixes landed** (on an internal review branch, pending owner sign-off before merge): a stale evidence-packet-merge test was aligned to the canonical verbatim-proof-chip behavior; a deprecated scikit-learn argument was removed from the probe constructors (behavior-neutral).

**Pre-launch security review.** An authorized red-team of the launch/auth surface was performed. It confirmed several defenses are correctly in place (production JWT-secret enforcement, fail-closed token minting, fail-closed audit-session owner scoping, validated model-endpoint handling, path-traversal defenses). Two low-risk hardenings were applied (credentialed-CORS restricted to an explicit origin allowlist; failed-authentication requests are now audit-logged). Additional **paid-launch-gating** items were identified and are tracked internally (authentication of the alpha's currently-public reference audit lifecycle; role-based authorization on privileged fleet/anchor operations; removal of the debug-mode token mint). These do not affect any §8 claim; per-customer production `ACCEPT` remains **NOT LICENSED** and the durability/certification bounds of §9.10–§9.11 are unchanged. Consistent with the standing disclaimer, this review is not a third-party security certification.

**New analytical primitive — directional (RPM/diode) causal-necessity knockout.** A fixed-probe cross-ablation test was added to the diagnostic toolset: it ablates one CAS-typed subspace and measures a **held-fixed** second probe (no retrain), yielding a causal-*necessity* read distinct from the existing recoverability-style ablation, with a two-leg asymmetry verdict and an explicit **subsumption control** that downgrades a geometrically-confounded directional result to GREY rather than a pass. **Status: PROTOTYPE — validated on synthetic ground-truth only; NOT yet run on a real model.** Verdict ceiling `FLAG_FOR_HUMAN_REVIEW` (no `ACCEPT`); open-weight-only. It does not license "detects/prevents/removes prompt injection internally" or "proves causal control" (both remain NOT LICENSED). It complements — does not replace — the validated §5.2 subspace-ablation necessity test.

---

**End of investor-facing specification. Confidential, NDA-Gated. Version CURRENT (consolidated) · 2026-06-07 (maintenance addendum 2026-07-12, §12) · Noetic Compass / CAS Harness · Built on the Cognitive Architecture System (CAS) v7.7 · Patent-pending — US Provisional Application No. 64/037,173, filed 04/13/2026 (Utility—Provisional).**
