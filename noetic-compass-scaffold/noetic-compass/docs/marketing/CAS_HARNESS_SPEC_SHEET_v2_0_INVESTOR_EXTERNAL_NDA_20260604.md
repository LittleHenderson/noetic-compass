> **SUPERSEDED 2026-06-04 by v2.1** — adds §9.8.1 uniqueness claim posture (probabilistic speciality; absolute uniqueness over all frameworks is disclaimed and not the target). All five v2.0 corrected claim boundaries are unchanged. Use v2.1 for distribution.

# CAS Harness — Product Specification Sheet
## Investor / Strategic Partner Distribution (NDA Required)

**Version**: 2.0-EXTERNAL · **Date**: 2026-06-04 · **Classification**: Confidential, NDA-Gated
**Distribution**: Authorized recipients only, post-executed NDA

---

> **Standing disclaimer.** Noetic Compass holds no SOC 2, ISO/IEC 42001, or other third-party security/compliance certification; Evidence Packets are designed to support compliance documentation but do not by themselves satisfy any regulation, and nothing herein is legal advice.

---

## v2.0 Release Notes (anti-overclaim correction pass; delta from v1.9, 2026-05-30)

v2.0 is an honesty-and-claim-scope correction over v1.9. No new capability is claimed. Five ground-truth corrections (2026-06-03/04) are applied; everything else in v1.9 carries forward unchanged.

1. **WORM is Object-Lock *Governance*, not *Compliance*; ~30-day rolling retention; tamper-evident on re-verify.** v1.9 described the S3 Object Lock anchor as `COMPLIANCE`-mode, "immutable," "write-once-read-many," and not deletable "even by the operator." That overstates the deployed configuration. The anchors use **Object Lock in GOVERNANCE mode** with an approximately **30-day rolling retention window**. A privileged operator holding `s3:BypassGovernanceRetention` *can* delete or overwrite an anchor; what the chain guarantees is that any such change is **tamper-evident on the next `/verify` call**, not that it is physically prevented. Every "immutable / permanent / even-the-operator-cannot-delete / COMPLIANCE" instance is corrected throughout.
2. **The Stage 9 40E "first ACCEPT verdict" is WITHDRAWN.** v1.9 reported a "first ACCEPT verdict in the project record" on the Stage 9 40E validation packet. That verdict was a pre-fix overclaim — a candidate-only `control_proof` was stamped verified before commit `337d0c2`. The honest WORM-retained verdict for that packet is **FLAG_FOR_HUMAN_REVIEW**; **no ACCEPT stands** in the project record. (Per-customer / production ACCEPT remains NOT LICENSED, unchanged.)
3. **Durability is scoped to single-instance restart-survival.** Disk persistence has been proven to survive restart on a single paid-disk instance. **Multi-instance / host-loss durability is NOT proven** — the deployment runs one Postgres server with no replica and no failover. Durability claims are scoped accordingly.
4. **No certification; "regulator-grade by construction," "court-admissible," and "compliant" framings removed.** Replaced with "designed to produce regulator-facing evidence artifacts." See the standing disclaimer above.
5. **CAS-specificity uniqueness remains OPEN — 2026-06-03 GPT-NeoX-20B Condition-3 comparator = GREY.** The first blind matched-taxonomy comparator (GPT-NeoX-20B, MTC Condition-3, 2026-06-03) returned **GREY**: CAS did **not** beat the matched control by the pre-registered margin. CAS-specificity is **NOT LICENSED**. This GREY result is scoped strictly to the Condition-3 comparator; it does **not** touch the Stage 9 40E hidden-readout detection result (95.625%) or the η→ε bridge PASS, which stand as in v1.9 (subject to the same signal-vs-leakage adjudication that was already open).

---

## v1.9 Release Notes (delta from v1.8)

Six changes since v1.8 (2026-05-28). Three integrity-chain promotions from "in flight" to "closed," one new methodology discipline rule, one major architecture-documentation expansion, and one in-flight scale extension.

### 1. PR #125 — ACCEPT verdict requires WORM-proof, mechanically enforced

The verifier's final ACCEPT verdict now requires `packet_proof` to demonstrate all three integrity conditions simultaneously:

1. S3 anchor was written
2. S3 object was re-read and hash-matched
3. Object Lock / WORM retention is active on the anchor object

If any one of these proofs is missing, **the verifier downgrades an explicit ACCEPT to `FLAG_FOR_HUMAN_REVIEW` automatically.** This converts WORM-anchored evidence from an optional integrity feature to a hard gate on the final verdict. The trust contract is now mechanical, not aspirational: ACCEPT means "all three held simultaneously, with receipts."

Production verification 2026-05-29:
- Trace ID: `cas-dist-032b4bba4a7f15f1-distributed-merge`
- Required anchor mode: `s3`
- Require Object Lock: `yes`
- Result: PASS, Verifier: ACCEPT

Negative-path verification: the bundled demo/reference packet now correctly returns `FLAG_FOR_HUMAN_REVIEW` because it is not WORM-retained. The app no longer treats non-WORM-retained evidence as a final trusted verdict.

### 2. Mechanically-checkable WORM via HeadObject — CLOSED

Was "in flight" in v1.8. Now CLOSED. The `/verify` endpoint and deployment smoke script now confirm AWS S3 Object Lock metadata is actually present on each anchor file via `HeadObject`. The WORM claim has moved from "bucket configured for Object Lock" to "Object Lock verified mechanically on this specific anchor file at this specific verification call."

Strict WORM smoke (production, 2026-05-29):
- Base URL: `https://noetic-compass-api.onrender.com`
- Required anchor mode: `s3`
- Require Object Lock: `yes`
- Result: PASS
- Anchor trace: `cas-dist-9a08ca99d7fe2edb-distributed-merge`

### 3. Five new architecture diagrams (§4.5–§4.9)

§4 has been expanded with five reference-grade architecture diagrams reviewers can cross-walk against the codebase:

- **§4.5** — Phase 1: Standalone harness structure (no model attached)
- **§4.6** — Phase 2: Harness attached to a single audit-target model
- **§4.7** — Phase 3: Fleet Executor on a 300B model with sub-harnesses per worker
- **§4.8** — η→ε bridge detail (the conditioning mechanism by itself)
- **§4.9** — Hidden-content detector η₁/η₂ two-bridge flow (prototype tier)

These diagrams are intended for technical reviewers performing code-walk verification. Each component named in a diagram corresponds to a discoverable subsystem in the codebase.

### 4. NEW METHODOLOGY DISCIPLINE — TKS-Meaning Preservation Rule

A new hard anti-drift rule has been added to the methodology stack at equal tier to the existing eight discipline principles. Reason: a v2 attempt at the matched-taxonomy fixture (see §5.17) was diagnosed as having stripped the TKS-canonical semantic content of the prompts, not just the surface answer-key wording. The collapse it produced was a build error, not a finding. The rule prevents the same class of error in any future fixture.

> **TKS-Meaning Preservation Rule.** A recoverability fixture must preserve the TKS-canonical semantic content of every class it asks the model to recover. The fixture may strip surface answer-key wording (vocabulary anchors, framework names, operator notation), but it must not strip the meaning that wording was naming. A prompt with the answer-key words removed and the underlying TKS-canonical situation also removed is not a "leakage-removed" prompt — it is a meaning-removed prompt. Meaning-removed prompts cannot be used to test recoverability and will produce false NULL results that look like falsifications but are build errors. Recoverability fixtures must pass an explicit Meaning Preservation gate (independent rater verification) before any GPU-tier capture is authorized.

This rule is now part of CAS Harness methodology at the same tier as the existing pre-registration discipline.

### 5. Matched-Taxonomy Control (MTC) stage pre-registered — OPEN with two documented nulls

A new pre-registered evidence tier has been admitted to the open queue: **Matched-Taxonomy Control (MTC)** — a comparative-specificity test designed to distinguish "CAS reads cognitive structure from foreign open-weight transformers" (LICENSED) from "the recovered structure is CAS-specific rather than a generic semantic partition the CAS labels happen to span" (NOT YET LICENSED). Two pre-registered fixture attempts produced documented nulls before reaching the matched-comparator gate:

- **MTC v1** — surface text leakage (text baseline 100%); fixture rejected by pre-registered Surface Gate
- **MTC v2** — TKS-meaning removal under aggressive de-leakage (CAS recoverability collapsed to ~chance); fixture rejected by pre-registered Recoverability Gate; root-cause diagnosed as meaning-removal, not signal-absence

Both nulls are documented openly. The v2 collapse motivated the TKS-Meaning Preservation Rule (above). The matched-taxonomy specificity claim and the "universal rather than something we invented" framing both remain NOT LICENSED, exactly as in v1.8. The v1 detection-lift claims (Stage 9 40E at 95.625% / +46.4 pp, Stage 7 F28 at 86.86%) are unaffected and remain LICENSED — the v2 fixture was never a valid substrate for adjudicating them.

### 6. Grok-1 (xAI, 314B) scale extension — IN FLIGHT, NOT LICENSED

CAS Harness is mid-execution on the first attempt to extend the audit chain above 20B parameters. The audit target is `TevunahAi/Grok-1-BF16` — a community Hugging Face BF16 conversion of `xai-org/grok-1` (xAI's JAX original). This is the first model above 20B parameters being processed by the harness. v1.9 documents the work-in-progress posture and the converted-checkpoint disclosure schema (PR #128) that any Grok-1 Evidence Packet will carry. **No Grok-1 results are LICENSED in v1.9.** Frontier-scale validation (>20B) remains NOT LICENSED.

---

## NDA Notice

This document contains confidential and proprietary information of Noetic Compass / CAS Harness (Little Henderson, founder). Receipt of this document is subject to the executed Non-Disclosure Agreement between the recipient and Noetic Compass. Reproduction, disclosure, or use of any information herein, in whole or in part, for any purpose other than evaluating a potential strategic, investment, or partnership relationship is prohibited. The CAS framework primitives are covered by USPTO Provisional Patent Application #64/037,173. Additional filings on CAS Harness-specific mechanisms, on the S7-F28-BALANCED-BRIDGE methodology, on the S9-40E-ORIGINAL-BASELINE-READOUT methodology, on the Audit-Grade Integrity Chain (including PR #125's ACCEPT-requires-WORM gate and HeadObject mechanical WORM verification), on the TKS-Meaning Preservation Rule, on the MTC pre-registration framework, and on the Grok-1 provenance schema are in process; recipients are advised that the methodologies described herein are subject to ongoing patent protection.

## What This Document Is

A capability overview for prospective investors, strategic partners, and technical reviewers conducting NDA-gated code-walk verification of CAS Harness. It documents:

- What CAS Harness does and what it has empirically demonstrated
- The audit-grade discipline distinguishing it from contemporaneous interpretability work
- The validated cross-architecture and cross-scale claim (three independent model families across six model points, with a 20B scale extension closed on two cognitive axes)
- The two named canonical methodologies under which the 20B closures were produced
- The audit-grade integrity chain — disk persistence, hash chain, five-check verify, three-state UI, external anchoring, **PR #125 ACCEPT-requires-WORM gate, and HeadObject mechanical WORM verification**
- **The five-diagram architecture reference (§4.5–§4.9), suitable for code-walk cross-verification**
- **The TKS-Meaning Preservation Rule** governing all recoverability fixtures (§6.9)
- **The MTC pre-registration with two openly documented nulls and the first blind comparator (GPT-NeoX-20B Condition-3) returning GREY** (§5.17)
- **The Grok-1 in-flight scale extension and converted-checkpoint provenance schema** (§5.18)
- What developers and enterprises do with CAS Harness in production deployments (§13)
- The honest claim boundaries — what is and is not licensed for external use today
- The IP portfolio status and provisional filing position

## What This Document Is NOT

- **Internal rollout plan and timeline** — separated into the internal-only roadmap document
- **Specific algorithmic hyperparameters** (probe rank values, layer indices, training configurations, fixture sample sizes beyond headline)
- **Specific component identifiers** (attention head IDs, MLP neuron indices, exact subspace dimensions)
- **Source code paths and internal API design beyond architectural categories**
- **Pre-registration documents and per-stage methodology beyond what is needed to interpret claim scope**
- **Commit-level reproducibility provenance**
- **Implementation specifics that would enable reverse engineering**

Additional methodology depth available under separate technical-disclosure NDA after initial evaluation.

---

## 1. Executive Summary

CAS Harness is the **black-box flight recorder for AI cognition**. It enables a software service to look inside any open-weight large language model, detect the cognitive structure inside the model's hidden states, prove the detected structure is causally load-bearing for the model's behavior, condition the model's next-token probability distribution by realizing the detected structure as readable context, and emit audit-grade Evidence Packets — disk-persisted (single-instance restart-survival proven), cryptographically chained, externally anchored to S3 Object Lock (Governance-mode, ~30-day rolling retention, tamper-evident on re-verify), actively re-verified on every audit call, and gated such that the final ACCEPT verdict requires mechanically-verified WORM retention proof or is downgraded to FLAG_FOR_HUMAN_REVIEW — that another party can independently verify.

The product is grounded in a formal mathematical result: **Proposition 5.6 of the Noetic Topos paper**, which proves the counit ε of the Noetic Coverage is a surjective covering morphism. This theorem predicted the η → ε bridge mechanism *before* any empirical experiment ran. The prediction has been empirically confirmed on **six open-weight models across three architecture families** (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, 20B; AI2 OLMo; Alibaba Qwen) and on **two independent evidence tiers** (activation-trace and weight-geometry).

Two canonical methodologies are named: **`S7-F28-BALANCED-BRIDGE`** (Foundation-28 axis closure) and **`S9-40E-ORIGINAL-BASELINE-READOUT`** (40-Element axis closure). Both replicate at 20B parameter scale under their respective protocols.

The product is positioned for two markets simultaneously:

1. **Developer market** — pre-deployment model evaluation, hallucination root-causing, prompt engineering with structural feedback, distillation verification, adversarial-input debugging, cross-model migration audits, CI-integrated quality gates
2. **Enterprise market** — regulatory compliance evidence (EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, Federal Reserve SR 11-7), vendor procurement evaluation, AI-error legal defense, board-level AI risk reporting, customer-trust products, red-team integration, acquisition due diligence

Detailed use cases by audience are in §13.

### Today's load-bearing claim, reserved-language, defensible for audit

> CAS Harness reads cognitive structure from open-weight transformer hidden states across six model points and three architecture families (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, **20B** — plus AI2 OLMo, Alibaba Qwen). The η → ε bridge conditions next-token likelihood with effect sizes that grow then plateau across Pythia/GPT-NeoX scale, strengthen on OLMo, reach the strongest Foundation-28 effect on Qwen2.5-1.5B (+0.7960, p = 2.92×10⁻¹²), and **produce the strongest single bridge result in the project record on the 40-Element axis at GPT-NeoX-20B under the canonical S9-40E-ORIGINAL-BASELINE-READOUT methodology** (+1.412 probe-readable Δ, +1.498 gold-readable Δ, +2.881 partner margin, 80 cases, raw-symbol controls at +0.014 confirming the ε-realization mechanism is structural rather than symbolic). The 20B chain closes on two cognitive axes. Evidence Packets are **disk-persisted with append-only hash chains (single-instance restart-survival proven; multi-instance / host-loss durability NOT proven), tamper-evident through a five-check verify endpoint (in-server payload / log / chain / anchor-manifest + external S3 round-trip), three-state UI surfacing of S3-anchor trust (verified / receipt-only / failed), externally anchored with optional S3 Object Lock (Governance-mode retention, ~30-day rolling window, operator-overridable via `s3:BypassGovernanceRetention` — so the guarantee is tamper-evidence on re-verify, not physical immutability), and gated by PR #125 such that the final ACCEPT verdict requires mechanically-verified WORM-retention proof or is downgraded to FLAG_FOR_HUMAN_REVIEW automatically**. No ACCEPT verdict stands in the project record: the Stage 9 40E validation packet's WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW (the previously reported 2026-05-28 ACCEPT was a pre-fix overclaim from a candidate-only control_proof, withdrawn in v2.0). Per-customer production ACCEPT verdicts remain NOT LICENSED.

---

## 2. Origin & Mission

### 2.1 Origin

CAS Harness emerged from R&D adjacent to the **CAS Native** flagship initiative. The originating question was scientific, not product-driven:

> *"If a random open language model — one that has never heard of CAS — is probed for CAS-shaped structure, will the structure be present? If yes, is the framework describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

The probing chain closed in May 2026 across six model points, two cognitive axes at 20B, full audit-grade integrity chain with active external re-verification, three-state UI trust surfacing, PR #125 WORM-retention-gated verdict, and HeadObject mechanical WORM-retention verification. No ACCEPT verdict stands in the project record (the previously reported Stage 9 40E ACCEPT was withdrawn in v2.0; its honest WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW). The universality framing (the second clause of the originating question) remains scientifically open — Stage MTC pre-registered, openly nulled twice, and the first blind matched-taxonomy comparator (GPT-NeoX-20B Condition-3, 2026-06-03) returned GREY; see §5.17 and §9.8.

### 2.2 Mission

CAS Harness exists to make the cognitive architecture inside any open-weight large language model **inspectable, validatable, conditionable, and audit-traceable** by an external software service — without requiring the model's vendor to publish interpretability tooling, without modifying the model's weights, and without sacrificing the reserved-language audit discipline required to produce regulator-facing evidence artifacts.

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

> **Implementation locator.** Both maps are computed by the offline capture/probe worker `live-trace-worker/scripts/run_stage9_40e_eta_epsilon_bridge.py` (40E) and its F28 sibling. The service-side `api/services/cas_harness_evidence_bridge.py` does not compute η or ε — it normalizes and verifies the worker's output packet. See §4.8 naming note.

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

Stage 9 40-Element Original-Baseline Balanced-Logistic Eta-to-Epsilon Readout Method. Axis: 40 Elements. Encodes: Stage 9 role-bound + counterfactual + Focus-marker fixture / 40E axis / balanced-logistic probe / pre-measured text-baseline adversary (49.24%) / full η→ε bridge with matched controls / `cas_beats_text_claim_allowed` JSON guard.

### 3.6 Audit-Grade Integrity Chain (UPDATED IN v1.9)

A five-layer cryptographic integrity chain that survives single-instance server restart (multi-instance / host-loss durability NOT proven — see §9.10), detects local tampering, detects full-server compromise, **mechanically verifies WORM retention on every audit call**, and **forces non-WORM-retained packets to downgrade from ACCEPT to FLAG_FOR_HUMAN_REVIEW (PR #125)**.

#### 3.6.1 Layer 1 — Disk Persistence

Every merged Evidence Packet is written to a disk-backed packet store on creation. Packets survive restart, redeploy, and crash **on a single paid-disk instance** (proven). Regression-tested for bit-identical reload after memory clear. **Scope:** durability is proven for single-instance restart-survival only; multi-instance / host-loss durability is NOT proven — the deployment runs one Postgres server with no replica and no failover (see §9.10).

#### 3.6.2 Layer 2 — Append-Only Hash Chain

Each packet write appends a JSONL entry to a `cas_harness_evidence_chain` log. Every entry includes a cryptographic fingerprint of the previous entry. Tampering with any historical entry shatters every subsequent fingerprint and is detectable in linear time.

#### 3.6.3 Layer 3 — Five-Check Verify Endpoint

`/evidence/{trace_id}/verify` runs **five independent checks per verification request**:

1. **Packet payload hash check** — does the packet's contents still match the SHA-256 recorded at write time?
2. **Hash-log entry check** — does a log entry pointing to this packet exist?
3. **Hash-chain continuity check** — does the fingerprint chain connect cleanly from genesis to this packet's entry?
4. **Local anchor manifest check** — does the locally-anchored manifest match what the chain says it should be?
5. **External S3 round-trip check** — does a live `GetObject` call retrieve the anchor file, hash to the recorded value, and confirm it commits to the packet hash + hash-log entry?

Any check failure returns `partial_mismatch` with the specific layer indicated. Endpoint never returns silent "OK"; it passes all five checks or names the failing layer.

#### 3.6.4 Layer 4 — External Anchoring Service with Mechanical WORM (UPGRADED v1.9)

Three operator-configurable modes (env var `CAS_HARNESS_EVIDENCE_ANCHOR_MODE`):

| Mode | Storage | Tamper-resistance |
|---|---|---|
| `disabled` | None | Local chain only |
| `local` | Separate local filesystem directory | Detects accidental edits within the deployment |
| `s3` | Amazon S3 (Object Lock optional) | When AWS-S3 with Object Lock **Governance**-mode retention (~30-day rolling window): retention is **mechanically verified on each verify call via HeadObject**. Governance mode is **operator-overridable** — a principal holding `s3:BypassGovernanceRetention` can delete or overwrite the anchor before retention expires — so the guarantee is **tamper-evidence on the next verify call**, not physical immutability. When S3-compatible storage without Object Lock: tampering becomes **detectable on next verify call** rather than prevented at write time. |

**Mechanical WORM-retention verification (CLOSED):** The verify endpoint and the deployment smoke script now call `HeadObject` on every anchor object, confirm `ObjectLockMode` is `GOVERNANCE`, and confirm `ObjectLockRetainUntilDate` is in the future. The smoke script accepts a `--require-object-lock` flag that hard-fails verification if Object Lock retention is not in effect. Note: Governance-mode retention is operator-overridable (`s3:BypassGovernanceRetention`); the mechanism proves retention is *present and current at audit time* and makes any override *tamper-evident*, not that the anchor is physically immutable.

**Production state (verified 2026-05-29 strict-mode smoke):**

- `mode=s3` with `require_object_lock=yes` active
- Strict-mode smoke PASS on trace `cas-dist-9a08ca99d7fe2edb-distributed-merge`
- Negative-path PASS: bundled non-WORM demo packet correctly returns FLAG_FOR_HUMAN_REVIEW

The WORM claim has moved from "bucket configured for Object Lock" to "Object Lock verified mechanically on this specific anchor file at this specific verification call."

#### 3.6.5 Three-State UI Trust Surface

The Audit Console Evidence Drawer renders three distinct trust states for S3 anchors:

- **"S3 object verified"** — backend completed the 5-check verify including S3 round-trip; strongest claim
- **"Anchored to S3"** — receipt recorded at write time but no live re-read performed
- **"S3 verify failed"** — round-trip ran and found a discrepancy; failure surfaced rather than hidden

The UI never silently upgrades trust. Reviewers see what was actually confirmed at the moment of audit.

#### 3.6.6 Layer 5 — PR #125 ACCEPT-Requires-WORM Gate (NEW v1.9)

The verifier's final ACCEPT verdict now requires `packet_proof` to demonstrate **all three** WORM-integrity conditions simultaneously:

1. S3 anchor was written
2. S3 object was re-read and hash-matched
3. Object Lock / WORM retention is mechanically active on the anchor object

**If any one proof is missing, the verifier converts an explicit ACCEPT into `FLAG_FOR_HUMAN_REVIEW` automatically.** The trust contract is now mechanical at the verdict layer, not aspirational. ACCEPT means "all three held simultaneously, with receipts."

> **v2.0 correction — no ACCEPT stands.** v1.9 reported a 2026-05-29 production ACCEPT on trace `cas-dist-032b4bba4a7f15f1-distributed-merge`. That verdict has been **withdrawn**: it rested on a candidate-only `control_proof` stamped verified before commit `337d0c2`. The honest WORM-retained verdict for that packet is **FLAG_FOR_HUMAN_REVIEW**. The gate mechanism itself is real and verified (the negative path below holds); what is withdrawn is the claim that any packet has *passed* it to a standing ACCEPT.

Mechanism verification 2026-05-29 (gate behavior, not a standing ACCEPT):
- Trace ID: `cas-dist-032b4bba4a7f15f1-distributed-merge`
- WORM-retained verdict of record: FLAG_FOR_HUMAN_REVIEW (the prior ACCEPT was a pre-fix overclaim, withdrawn in v2.0)
- Negative-path PASS: bundled non-WORM-retained demo packet correctly converts an explicit ACCEPT → FLAG_FOR_HUMAN_REVIEW

#### 3.6.7 Composite Property

Together, the five integrity layers produce a packet artifact with the following auditor-defensible properties:

- A packet's current contents can be cryptographically attested to match its at-creation state
- A packet's existence and ordering in the chain can be cryptographically attested
- A full-server compromise that rewrites the local chain cannot rewrite the externally-anchored fingerprints
- Any verifier — including a regulator with read-only access to the verify endpoint and read-only access to the S3 bucket — can independently re-verify the packet without operator cooperation
- Tampering at any layer (packet, log, chain, manifest, S3 anchor, or Object Lock retention) is detected on the next `/verify` call and named explicitly in the response
- The UI surface reflects the actual trust state rather than the asserted state
- **An ACCEPT verdict is mechanically conditioned on WORM-retention proof; non-WORM-retained packets cannot present as ACCEPT in any audit response** (and as of v2.0 no packet presents as ACCEPT — the only prior ACCEPT was withdrawn)

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
            DISK PERSISTENCE → HASH CHAIN → 5-CHECK VERIFY → S3 ANCHOR → WORM
                  │
                  ▼
            PR #125 GATE — ACCEPT requires all three WORM proofs
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
| Five-check verify endpoint | Validated |
| Three-state UI trust surfacing | Validated |
| External anchoring service (disabled / local / S3) | Validated; **s3 mode active in production** |
| **HeadObject mechanical WORM verification** | **Validated (v1.9)** |
| **PR #125 ACCEPT-requires-WORM gate** | **Validated (v1.9)** |
| Fleet-topology verifier gate (conservative-default at scale) | Validated |
| Fragment-payload SHA-256 commitment (anti-misattribution) | Validated |
| Audit Console UI surface | Validated |
| Authenticated delivery API | Validated |
| Verification Stack (runtime accept/suppress) | Validated |
| Mode Selector (3 customer-configurable modes) | Validated |
| Generation Readiness Gate (4-tier discipline) | Validated |
| **MTC pre-registration infrastructure (dual-labeled fixture generator, materializer eligibility gate)** | **Validated (v1.9, open evidence tier)** |
| **TKS-Meaning Preservation Rule enforcement (Surface Gate + Recoverability Gate)** | **Validated (v1.9)** |
| **Grok-1 BF16 provenance schema (PR #128)** | **Validated (v1.9, in-flight scale extension)** |
| Two-bridge hidden-content detector | Prototype |

### 4.3 Three Customer Deployment Modes

Hosted / Bring-your-endpoint / Self-hosted. Each supports the full integrity chain including external anchoring and the PR #125 ACCEPT-requires-WORM gate.

### 4.4 Audit Console Surface (UPDATED v1.9)

Renders verdict, confidence, six proof chips with detail-on-hover, verifier source, scope label, coverage label, and boundary disclosure. Three-state S3-anchor trust surface distinguishes "S3 object verified" / "Anchored to S3" / "S3 verify failed." **PR #125 surface (NEW v1.9):** when an explicit verifier ACCEPT is downgraded due to missing WORM proof, the UI shows the verdict as FLAG_FOR_HUMAN_REVIEW with a tooltip naming which of the three WORM proofs failed (anchor write / re-read match / Object Lock active). UI carries one architectural invariant: it does not create verdicts; it explains what the backend runner returned.

### 4.5 Architecture Diagram — Phase 1: Standalone Structure (no model attached) [NEW v1.9]

The harness exists as engine + probe machinery + audit chain, fully tested but dormant. No activations flow. The verifier has no payload to evaluate. The S3 anchor is empty. Everything is loaded, waiting.

```
                    CAS HARNESS — STANDALONE STRUCTURE
              (engine armed, probes dormant, audit chain idle)

  ┌─────────────────────────────────────────────────────────────────────┐
  │                       CAS ENGINE (Rust core)                        │
  │                                                                     │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐│
  │  │ Ontology │  │ Scoring  │  │   RPM    │  │Inversions│  │Compiler││
  │  │10 Noetics│  │  per-op  │  │  monad   │  │  7-axis  │  │+notation││
  │  │40 States │  │  + NCCS  │  │  gate    │  │  scanner │  │grammar ││
  │  │ 7 Drives │  │ composite│  │(section- │  │          │  │admissi-││
  │  │4 Domains │  │  weights │  │retraction│  │          │  │ bility ││
  │  │4Registers│  │          │  │  one-way)│  │          │  │        ││
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────┘│
  │                                                                     │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
  │  │  Fractals    │  │   Metric     │  │  Wrap Pipeline (8-stage) │ │
  │  │  (X.Y.Z)     │  │  Fisher-Rao  │  │  Input→RPM→Dial→LLM→     │ │
  │  │              │  │  on Δ°₃₉     │  │  Score→Coherence→Inv→Out │ │
  │  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                   PROBE MACHINERY (no input)                        │
  │                                                                     │
  │  Six axis probes (balanced-logistic, frozen weights):               │
  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      │
  │  │10-Noet│ │28-Foun│ │40-Elem│ │5-Opers│ │10-ExSh│ │10-CmpF│      │
  │  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘ └───────┘      │
  │  (Noetics / Foundations / Elements / Operators /                    │
  │   Expression Shapes / Compiler-Valid Formulas)                      │
  │                                                                     │
  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐│
  │  │ Multi-layer  │ │ Blind-spot   │ │ Subspace ablation hook       ││
  │  │ trace classf │ │  detector    │ │ (random-control machinery   ││
  │  │              │ │              │ │  loaded; no target)         ││
  │  └──────────────┘ └──────────────┘ └─────────────────────────────┘│
  │                                                                     │
  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐│
  │  │ Realization  │ │ Likelihood   │ │ Lacunarity + fractal class  ││
  │  │  layer (ε)   │ │   scorer     │ │ Weight-geometry analyzer    ││
  │  └──────────────┘ └──────────────┘ └─────────────────────────────┘│
  └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │              EVIDENCE PACKET MACHINERY (no payload)                 │
  │                                                                     │
  │  Six Proof Chip slots — empty:                                      │
  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐         │
  │  │model │ │readt │ │basel │ │causal│ │ctrl-cov│ │out-brdg│         │
  │  └──────┘ └──────┘ └──────┘ └──────┘ └────────┘ └────────┘         │
  │                                                                     │
  │  Verifier (Stage 19/20) — three-state decision adapter — IDLE       │
  │     ACCEPT  /  SUPPRESS  /  FLAG_FOR_HUMAN_REVIEW                   │
  └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │              AUDIT-GRADE INTEGRITY CHAIN (empty)                    │
  │                                                                     │
  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
  │  │ Disk persist │ → │ S3 anchor    │ → │ /verify endpoint     │    │
  │  │ + hash chain │   │ + Object Lock│   │ 5 checks (idle)      │    │
  │  │  (genesis)   │   │ WORM mode    │   │ + HeadObject WORM    │    │
  │  └──────────────┘   └──────────────┘   └──────────────────────┘    │
  │                                                                     │
  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
  │  │ Audit Console│ ← │ Three-state  │ ← │ PR #125 ACCEPT-      │    │
  │  │      UI      │   │ trust surface│   │ requires-WORM gate   │    │
  │  └──────────────┘   └──────────────┘   └──────────────────────┘    │
  └─────────────────────────────────────────────────────────────────────┘

  STATE: Engine warm. Probes loaded. Audit chain at genesis hash.
         No model attached. No activations to capture. Verifier has
         no work to do. The first packet, when it comes, will extend
         the hash chain from genesis.
```

### 4.6 Architecture Diagram — Phase 2: Attached to One Model [NEW v1.9]

The model is the audit target. Hooks reach **into** its layers. Activations flow **out** to the probe stack. Probe results feed the chip assembly. Chips drive the verifier. The verdict passes through the PR #125 ACCEPT-requires-WORM gate. The packet gets WORM-anchored. The UI surfaces three-state trust.

```
                  CAS HARNESS — ATTACHED TO ONE MODEL
                  (single audit target, full data flow)

                           ENGLISH PROMPT
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                FOREIGN OPEN-WEIGHT MODEL (e.g. GPT-NeoX-20B)        │
  │                                                                     │
  │   Layer 0 → Layer 1 → Layer 2 → ... → Layer 43 → OUTPUT TOKENS     │
  │     │         │         │                │                          │
  │     ▼         ▼         ▼                ▼                          │
  │  [HOOK]    [HOOK]    [HOOK]   ...     [HOOK]                       │
  │     │         │         │                │                          │
  └─────┼─────────┼─────────┼────────────────┼─────────────────────────┘
        │         │         │                │
        │   ACTIVATIONS (focus-token, BF16, all layers)
        │         │         │                │
        └─────────┴────┬────┴────────────────┘
                       │
                       ▼
           ┌───────────────────────────┐
           │   ACTIVATION CAPTURE      │
           │   (multi-layer tensor)    │
           └───────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌──────────┐  ┌──────────┐  ┌──────────────┐
  │ READOUT  │  │  CAUSAL  │  │   η → ε      │
  │  probes  │  │ ABLATION │  │ BRIDGE        │
  │ (six ax) │  │ (subspace│  │ ε-realization │
  │ →accuracy│  │  project │  │ prefix → re-  │
  │ →lift vs │  │  → re-   │  │ forward pass  │
  │  text BL │  │  forward)│  │ → Δ likelihood│
  └──────────┘  └──────────┘  └──────────────┘
        │              │              │
        ▼              ▼              ▼
  ┌──────────────────────────────────────────────┐
  │  Multi-layer trace + blind-spot detector     │
  │  Lacunarity (Var/Mean²) + fractal class      │
  │  Likelihood scorer (Δ vs no-prefix)          │
  │  Inversion scan (7 axes)                     │
  │  Output-side steering (drive-local eraser)   │
  └──────────────────────────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │       SIX PROOF CHIPS — assembled            │
  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐ ┌──────┐
  │ │model│ │readt│ │basel│ │causl│ │ctlcov│ │outbrg│
  │ │ ID  │ │acc% │ │lift │ │ Δacc│ │match-│ │ η→ε  │
  │ │ ver │ │     │ │ pp  │ │ Δrnd│ │ rank │ │ Δ    │
  │ └─────┘ └─────┘ └─────┘ └─────┘ └──────┘ └──────┘
  └──────────────────────────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │   VERIFIER (Stage 19/20) decision adapter    │
  │   reads all six chips + pre-reg criteria     │
  │     ACCEPT  /  SUPPRESS  /  FLAG_HUMAN       │
  └──────────────────────────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │   Hash chain extension (append-only)         │
  │   Disk persist → S3 anchor → Object Lock WORM│
  │   /verify endpoint 5-check + HeadObject WORM │
  │                                              │
  │   PR #125 GATE: ACCEPT requires all three:   │
  │     (a) anchor written  (b) re-read match    │
  │     (c) Object Lock active                   │
  │   Missing any → forced FLAG_HUMAN            │
  └──────────────────────────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │   AUDIT CONSOLE UI                           │
  │   Three-state trust surface:                 │
  │     ✓ verified  •  receipt-only  •  ✗ failed │
  │   Verdict + chips + confidence + scope       │
  │   PR #125 downgrade notice (when relevant)   │
  └──────────────────────────────────────────────┘

  CONCURRENT SIDE-FLOW (η₁/η₂ hidden-content detector, prototype tier)
  See §4.9 for detail.

  KEY DATA TYPES FLOWING:
    ▶ Activations:  model layers → capture (BF16 tensors, large)
    ▶ Probe scores: capture → chip assembly (small floats)
    ▶ Chip dicts:   chips → verifier (structured JSON, small)
    ▶ Verdict:      verifier → hash chain (~128 bytes + payload)
    ▶ Hash:         chain → S3 (256 bits + manifest)
    ▶ WORM proof:   HeadObject result → PR #125 gate (Object Lock state)
    ▶ Trust state:  UI poll → /verify (returns 5-check pass/fail + WORM state)
```

### 4.7 Architecture Diagram — Phase 3: Fleet Executor on a 300B Model [NEW v1.9]

A 300B model is too big for one worker. The model is sharded across N workers; **each worker hosts a sub-harness on its layer slice**. Each sub-harness runs the same probe stack locally on its activations, emits proof chips for its slice, and **commits a fragment SHA-256 of its raw activation tensor** so the fleet aggregator can prove no worker swapped tensors. The fleet aggregator stitches the chips, applies the **conservative-default policy** (any worker not-ACCEPT → fleet not-ACCEPT), and emits one unified packet that passes through the same PR #125 gate.

```
                CAS HARNESS FLEET EXECUTOR — 300B MODEL
            (sharded model, per-worker sub-harnesses, fleet gate)

                          ENGLISH PROMPT
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       ▼                       │
        │      ┌──────────────────────────────────┐    │
        │      │     300B MODEL — SHARDED         │    │
        │      └──────────────────────────────────┘    │
        │                                              │
        ▼                                              ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ Worker 1     Worker 2     Worker 3     ...     Worker N      │
  │ ┌────────┐  ┌────────┐  ┌────────┐           ┌────────┐      │
  │ │Layers  │  │Layers  │  │Layers  │           │Layers  │      │
  │ │ 1-20   │→ │ 21-40  │→ │ 41-60  │→  ...  →  │ 61-80  │      │
  │ │        │  │        │  │        │           │        │      │
  │ │ HOOK 1 │  │ HOOK 2 │  │ HOOK 3 │           │ HOOK N │      │
  │ └───┬────┘  └───┬────┘  └───┬────┘           └───┬────┘      │
  └─────┼───────────┼───────────┼────────────────────┼───────────┘
        │           │           │                    │
        ▼           ▼           ▼                    ▼
  ┌─────────┐ ┌─────────┐ ┌─────────┐         ┌─────────┐
  │ SUB-    │ │ SUB-    │ │ SUB-    │         │ SUB-    │
  │ HARNESS1│ │ HARNESS2│ │ HARNESS3│ ... ... │ HARNESSN│
  │         │ │         │ │         │         │         │
  │ capture │ │ capture │ │ capture │         │ capture │
  │ probes  │ │ probes  │ │ probes  │         │ probes  │
  │ ablate  │ │ ablate  │ │ ablate  │         │ ablate  │
  │ trace   │ │ trace   │ │ trace   │         │ trace   │
  │  ↓      │ │  ↓      │ │  ↓      │         │  ↓      │
  │ Frag    │ │ Frag    │ │ Frag    │         │ Frag    │
  │ SHA-256 │ │ SHA-256 │ │ SHA-256 │         │ SHA-256 │
  │ commit  │ │ commit  │ │ commit  │         │ commit  │
  │  ↓      │ │  ↓      │ │  ↓      │         │  ↓      │
  │ Local   │ │ Local   │ │ Local   │         │ Local   │
  │ chips + │ │ chips + │ │ chips + │         │ chips + │
  │ local   │ │ local   │ │ local   │         │ local   │
  │ verdict │ │ verdict │ │ verdict │         │ verdict │
  └────┬────┘ └────┬────┘ └────┬────┘         └────┬────┘
       │           │           │                    │
       │   small   │   small   │      ...           │
       │  payload  │  payload  │                    │
       │ (chips +  │ (chips +  │                    │
       │   hashes) │   hashes) │                    │
       └───────────┴─────┬─────┴────────────────────┘
                         │
                         ▼  (no raw activations crossing the wire —
                             those stay on each worker; only chips,
                             hashes, and local verdicts travel)
        ┌──────────────────────────────────────────────┐
        │            FLEET AGGREGATOR                  │
        │                                              │
        │  • Validate per-worker fragment hashes       │
        │    (anti-misattribution — proves Worker K's  │
        │     chips came from Worker K's tensors)      │
        │  • Stitch multi-layer trace across shards    │
        │  • Reconcile probe overlaps at shard seams   │
        │  • Cross-worker ablation coordination        │
        │    (subspace projection applied identically  │
        │     at each worker's relevant layer)         │
        │  • Lacunarity recomputed on stitched trace   │
        └──────────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────────────┐
        │     FLEET-TOPOLOGY VERIFIER GATE             │
        │     (conservative-default policy)            │
        │                                              │
        │     IF any worker reports SUPPRESS           │
        │           → fleet = SUPPRESS                 │
        │     IF any worker reports FLAG               │
        │           → fleet = FLAG                     │
        │     IF any worker fragment hash invalid      │
        │           → fleet = FLAG (anti-misattrib)    │
        │     IF any worker absent / timeout           │
        │           → fleet = FLAG (incomplete cover)  │
        │     IF and only if ALL N workers ACCEPT      │
        │     AND all fragment hashes verified         │
        │     AND topology complete                    │
        │           → fleet = ACCEPT (preliminary)     │
        └──────────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────────────┐
        │     UNIFIED EVIDENCE PACKET                  │
        │   Six aggregate chips (cross-worker)         │
        │   + fleet topology manifest                  │
        │     (which worker held which layers,         │
        │      which probe ran where, timing)          │
        │   + per-worker fragment hash list            │
        │   + per-worker local verdict roll-up         │
        │   + preliminary fleet verdict                │
        └──────────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────────────┐
        │     Hash chain extension                     │
        │     S3 anchor (Object Lock WORM)             │
        │     /verify (5 checks fleet-aware)           │
        │     HeadObject mechanical WORM verification  │
        │                                              │
        │     PR #125 ACCEPT-REQUIRES-WORM GATE        │
        │       Preliminary fleet ACCEPT must clear:   │
        │         (a) anchor written                   │
        │         (b) re-read match                    │
        │         (c) Object Lock active               │
        │       Else → FLAG_FOR_HUMAN_REVIEW           │
        └──────────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────────────┐
        │     AUDIT CONSOLE UI                         │
        │     Fleet verdict (top)                      │
        │     Per-worker chips (expandable rows)       │
        │     Topology view (which worker, which layers)│
        │     Three-state trust surface                │
        │     "Conservative default applied: 1 worker  │
        │      FLAG → fleet FLAG" (when relevant)      │
        │     PR #125 downgrade notice (when relevant) │
        └──────────────────────────────────────────────┘

  KEY DESIGN POINTS:
    ▶ Raw activations NEVER cross the wire — each worker probes
       locally on its own activations and ships only the (small)
       chips + (256-bit) fragment hash.
    ▶ Anti-misattribution: the fragment hash proves that the chips
       Worker K reported came from Worker K's actual tensors and
       not from some other source.
    ▶ Ablation across workers: subspace ablation requires coordinated
       projection across the fleet — the aggregator computes the
       projection direction once and each worker applies it to its
       own layer slice's activations.
    ▶ Conservative-default = correctness over throughput. The fleet
       gate refuses to claim ACCEPT unless every worker independently
       earned ACCEPT.
    ▶ PR #125 inheritance: the fleet verdict, like a single-model
       verdict, is gated on WORM proof. A fleet ACCEPT that cannot
       prove all three WORM conditions is downgraded to FLAG.
```

### 4.8 Architecture Diagram — η→ε Bridge Detail [NEW v1.9]

The conditioning mechanism by itself, isolated from the surrounding system. Shows the two-pass structure, the four prefix conditions (probe-readable, partner-readable, raw-CAS, no-prefix), and the four bridge metrics produced.

> **Naming note — where the bridge is actually computed.** The "η→ε Bridge" names a *measurement procedure*, and two distinct code components share the family name. They are not the same thing and should not be conflated:
> - **The bridge metric is computed offline** by the capture/probe worker `live-trace-worker/scripts/run_stage9_40e_eta_epsilon_bridge.py` (and its F28 sibling). This worker runs the foreign model twice, fits the balanced-logistic probe (η), applies the realization lookup (ε), and computes the Δ-likelihood scores in the diagram below. This is the component that produces the numbers.
> - **The in-service module `api/services/cas_harness_evidence_bridge.py` does NOT compute the bridge.** It is a packet normalizer/validator: it reads the offline worker's output JSON, checks shape and provenance, and emits the six proof chips for the evidence-management service. It performs no model inference and no probe fitting. Its name reflects the artifact it carries, not a computation it runs.
>
> Wherever this spec says "the bridge computes," read it as the offline worker. The service-side module transports and verifies that worker's evidence; it does not re-derive it.

```
                       η → ε BRIDGE — DETAIL
                   (the mechanism, not the system)

                       ENGLISH PROMPT
                              │
                              ▼
       ┌────────────────────────────────────┐
       │   FOREIGN MODEL — FIRST PASS       │
       │   (no prefix, baseline pass)       │
       │                                    │
       │   Layer 0 → ... → Layer L → ...    │
       │      │             │               │
       │      ▼             ▼               │
       │   [hook]        [hook]             │
       │      │             │               │
       └──────┼─────────────┼───────────────┘
              │             │
              ▼             ▼
       ┌────────────────────────────┐
       │ Hidden state at probe      │
       │ layer L (focus-token,      │
       │ per-axis selected layer)   │
       └────────────────────────────┘
                       │
                       ▼  η (eta) — Embedding map
       ┌────────────────────────────┐
       │ Balanced-logistic probe    │
       │ trained on per-axis fixture│
       │ → CAS class prediction     │
       │   e.g. "^3^P|A"            │
       │ (S7-F28-BALANCED-BRIDGE or │
       │  S9-40E-ORIGINAL-BASELINE- │
       │  READOUT)                  │
       └────────────────────────────┘
                       │
                       ▼  ε (epsilon) — Realization map
       ┌────────────────────────────┐
       │ Realization lookup         │
       │ CAS class → readable       │
       │ English prefix             │
       │   e.g. "[prefix text       │
       │   embodying ^3^P|A]"       │
       └────────────────────────────┘
                       │
       ┌───────────────┼────────────────────────────────┐
       │  Four prefix conditions tested per prompt:     │
       │  (a) no-prefix baseline                        │
       │  (b) probe-readable prefix (the ε realization) │
       │  (c) partner-readable prefix                   │
       │      (involution partner ε realization)        │
       │  (d) raw-CAS prefix (notation only, no English)│
       └───────────────┼────────────────────────────────┘
                       │
                       ▼
       ┌──────────────────────────────────────────┐
       │  FOREIGN MODEL — SECOND PASS             │
       │                                          │
       │  [prefix tokens] + [original prompt]     │
       │                                          │
       │  By Prop 5.6 (counit surjectivity),      │
       │  prefix tokens are attended to at every  │
       │  later position by construction.         │
       │                                          │
       │  Next-token likelihood distribution      │
       │  RECOMPUTED under each prefix condition  │
       └──────────────────────────────────────────┘
                       │
                       ▼
       ┌──────────────────────────────────────────┐
       │  Δ-LIKELIHOOD SCORER                     │
       │                                          │
       │  Δ probe = Pr_probe-prefix − Pr_no-prefix│
       │  Δ partner = Pr_partner − Pr_no-prefix   │
       │  Margin = Δ probe − Δ partner            │
       │  Δ raw-CAS = Pr_raw − Pr_no-prefix       │
       └──────────────────────────────────────────┘
                       │
                       ▼
       ┌──────────────────────────────────────────┐
       │  BRIDGE METRICS (per prompt, aggregated  │
       │   to model-axis-fixture level):          │
       │                                          │
       │   Δ probe-readable    ← effect size      │
       │   Margin vs partner   ← directional      │
       │                          specificity     │
       │   Δ raw-CAS           ← null check       │
       │                          (should be ~0;  │
       │                          if not 0, the   │
       │                          bridge is       │
       │                          symbol-rec,     │
       │                          not realization)│
       │   Δ gold              ← oracle-handoff   │
       │                          efficiency      │
       │                          (when available)│
       └──────────────────────────────────────────┘

  PRE-REGISTERED CONTROL PATTERNS (all five models):
    ▶ Raw-CAS Δ at every scale: −0.020 to +0.003 (null, as predicted)
    ▶ Partner-readable Δ at every scale: negative, comparable magnitude
       to probe-readable Δ (the bridge's effect direction is determined
       by which readable structure is realized, not by prefix-presence)
    ▶ Margin (probe − partner) grows monotonically with parameter count
       and corpus richness across tested models
```

### 4.9 Architecture Diagram — Hidden-Content Detector η₁/η₂ [NEW v1.9, PROTOTYPE TIER]

The two-bridge architecture for detecting what the model represents internally that it does not emit in surface text. Reads two CAS profiles in parallel — η₁ from internal hidden states, η₂ from emitted output text re-probed through the same probe stack — and classifies the gap into seven typed hiding shapes. **Prototype tier:** bridge wired, returns typed-class output, qualitatively interpretable, but no pre-registered confirmatory gate has been closed. Not licensed for production accept/suppress decisions.

```
            HIDDEN-CONTENT DETECTOR — η₁ / η₂ TWO-BRIDGE
        (prototype tier; what model represents vs what it emits)

                       ENGLISH PROMPT
                              │
                              ▼
       ┌────────────────────────────────────────────────────┐
       │                FOREIGN MODEL                       │
       │                                                    │
       │  Layer 0 → ... → Layer L → ... → Layer N → OUTPUT  │
       │                    │                       │       │
       │                    ▼                       ▼       │
       │                 [hook]                  emit text  │
       │                    │                       │       │
       └────────────────────┼───────────────────────┼───────┘
                            │                       │
                            ▼                       ▼
       ┌────────────────────────────┐   ┌─────────────────────────────┐
       │   η₁ — INTERNAL probe      │   │   η₂ — EMITTED-TEXT probe   │
       │   reads CAS profile from   │   │   takes output tokens,      │
       │   internal hidden states   │   │   re-runs through CAS probe │
       │   (what the model          │   │   stack at the input side   │
       │    represented)            │   │   (what the model           │
       │                            │   │    actually emitted)        │
       └────────────────────────────┘   └─────────────────────────────┘
                            │                       │
                            └───────────┬───────────┘
                                        │
                                        ▼
       ┌─────────────────────────────────────────────────────┐
       │             GAP COMPARATOR                          │
       │   η₁ profile  vs  η₂ profile                       │
       │   axis-by-axis difference vector                   │
       │   (per-class delta across 40-element grid +        │
       │    7-drive vector + 4-register vector)             │
       └─────────────────────────────────────────────────────┘
                                        │
                                        ▼
       ┌─────────────────────────────────────────────────────┐
       │   TYPED-CLASS HIDING-SHAPE CLASSIFIER               │
       │   Assigns gap to one of 7 typed shapes:             │
       │                                                     │
       │   1. Withheld content — class active in η₁,         │
       │      absent in η₂                                   │
       │   2. Self-censored content — partial η₂ suppression │
       │      relative to η₁ amplitude                       │
       │   3. Latent capability — capability class strong    │
       │      in η₁, absent from emitted reasoning chain     │
       │   4. Suppressed reasoning — reasoning steps in η₁,  │
       │      only conclusion in η₂                          │
       │   5. Frame manipulation — different frame classes   │
       │      between η₁ and η₂                              │
       │   6. Persona drift — speaker-identity class         │
       │      divergence between η₁ and η₂                   │
       │   7. Involution content — η₂ matches involution     │
       │      partner of η₁'s class (e.g., emits ^2 when     │
       │      internally representing ^3)                    │
       │                                                     │
       │   Output: typed-class assignment                    │
       │   (NOT free-form natural language description —     │
       │    bounded class set, cannot confabulate beyond     │
       │    the 7 typed shapes)                              │
       └─────────────────────────────────────────────────────┘
                                        │
                                        ▼
       ┌─────────────────────────────────────────────────────┐
       │   STATUS — PROTOTYPE TIER (NOT LICENSED)            │
       │                                                     │
       │   - Bridge architecturally wired                    │
       │   - Returns typed-class output                      │
       │   - Qualitatively interpretable gap profiles on     │
       │     early sample inspections                        │
       │   - NO pre-registered confirmatory gate closed      │
       │   - NO paired controls run on emitted-text corpus   │
       │   - NO cross-axis confusion-coherence audit         │
       │   - NOT licensed for production accept/suppress     │
       │                                                     │
       │   Positioned as complement to published             │
       │   "evaluation-awareness" findings in the literature:│
       │   natural-language descriptions of hidden state     │
       │   can confabulate; the CAS Harness typed-class      │
       │   shape is bounded by construction and cannot       │
       │   confabulate beyond the 7-class set.               │
       └─────────────────────────────────────────────────────┘
```

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

> **Disclosure on the GPT-NeoX-20B 40-Element headline (95.625% / +46.4 pp).** Two facts a reviewer should have up front, both recorded in `gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json`: (1) **the readout peaks at layer 2 of 44** (`best_layer.layer = 2`, `test_acc = 0.95625`) — an early-layer peak, which is consistent with the probe reading near-surface lexical features as much as deep structure; (2) **the "+46.4 pp lift" is measured against a CountVectorizer/text-hash baseline (49.24% / 50.0%), a deliberately weak adversary** — a 20B model encodes surface tokens far more richly than bag-of-words, so beating that baseline is a *necessary but not sufficient* condition for a CAS-specific signal. The shuffled-label control passes cleanly (2.62%, vs 2.5% chance), so the readout is not fitting label noise. The strong-adversary test (matched-taxonomy) is Stage MTC, which is **OPEN** (§5.17, §9.8). The LICENSED reading of this row is "the model linearly encodes the label distinction above a surface-text classifier," not "CAS-specific cognition at 95.6%."
>
> **Group-disjointness — checked, not asserted.** Near-duplicate leakage across the train/test boundary would inflate this number. It does not, and this is a recorded check rather than a claim: the same eval report (`gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json`) carries `train_test_group_overlap_count = 0` and `train_test_group_overlap_examples = []`. The `method_contract` records the split as `split_key = "metadata.split"` (a fixed, pre-assigned split — `"fixed split by metadata.split; test_split=test"`) and the disjointness grouping as `group_key = "metadata.counterfactual_pair_id"` over `n_base_prompt_groups = 4160`. The overlap check then verifies that no counterfactual-pair group straddles the train/test boundary: zero groups overlap, so both members of any counterfactual pair fall on the same side and cannot leak across it. **Caveat on independent re-derivation:** the raw scenario source (`data/stage9_original_40e_scenarios_20260527.json`) is a gitignored data artifact and is not committed, so a third party cannot currently recompute the disjointness from repository contents alone — they must trust the recorded overlap-count fields or be given the scenario file out of band. Committing a hashed manifest of the scenario groups is a tracked follow-up.

### 5.2 Readout-Causal Validation

5 axes pass collapse-to-exact-chance. Notable result: **40-Element subspace ablation at GPT-NeoX-20B: 95.625% → 66.897% (28.7277 pp drop), random matched 0.068 pp mean / 0.268 pp max — 107× signal-to-noise.** Pre-registered ≥30 pp / ≤65% gate narrowly missed by 1.27-1.90 pp on each disjunct. Documented openly. v2 ablation sweep with broader top-k and layer cover in open-gate queue.

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

Two-bridge architecture surfaces internal-vs-emitted divergence. See architecture diagram §4.9. **Prototype tier:** wired, returns typed-class output, qualitatively interpretable; no pre-registered confirmatory gate closed; not licensed for production decisions.

### 5.11 Verification Stack — Runtime-Safe Accept/Suppress

87.6% accept rate at 99.78% accepted accuracy. 0.22% silent error rate.

### 5.12-5.13 Mode Selector + Generation Readiness Gate

HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE. Four-tier action discipline: allow / caveat / constrain / suppress.

### 5.14 Evidence Packet Schema

Six proof chips (model / readout / baseline / causal / control-cover / output-bridge), each SHA-256-committed. One verifier report (verdict + confidence + scope + coverage + boundary). Audit-chain provenance (payload SHA-256 + hash-log pointer + chain continuity + anchor manifest + **HeadObject WORM status v1.9**). Fleet-level provenance (worker-fragment SHA-256 commitments + merge attestation). **Model-provenance schema v1.9** for converted-checkpoint disclosure (see §5.18).

### 5.15 Authenticated Evidence Packet Delivery (UPDATED v1.9)

REST API + JWT + path-traversal guard + size cap. Audit Console drawer with seven tabs and ARIA-complete semantics.

**Verify endpoint** (`/evidence/{trace_id}/verify`) runs **five independent checks per call**, plus HeadObject WORM verification:

1. Packet payload hash check
2. Hash-log entry check
3. Hash-chain continuity check
4. Local anchor manifest consistency check
5. External S3 round-trip check (boto3 GetObject + hash verification)
6. **HeadObject WORM-retention check** — confirms `ObjectLockMode` is `GOVERNANCE` and `ObjectLockRetainUntilDate` is in the future (Governance mode is operator-overridable; the check proves retention is present and current at audit time and makes override tamper-evident, not that the anchor is immutable)

Returns `verified` only when all five pass and (when configured) the WORM-retention check passes; returns `partial_mismatch` with explicit layer attribution on any failure.

**Three-state UI surface** distinguishes verified / receipt-only / failed S3 anchor trust states.

**External anchoring** with disabled / local / s3 modes. Production live on s3 mode as of 2026-05-28; **strict Object-Lock-retention smoke pass on 2026-05-29.**

**PR #125 ACCEPT-requires-WORM-retention gate:** verifier's explicit ACCEPT verdict requires all three retention proofs (anchor written + re-read match + Object Lock retention active) or is automatically downgraded to FLAG_FOR_HUMAN_REVIEW.

### 5.16 Tier Closure Summary (UPDATED v1.9)

| Evidence Tier | Status |
|---|---|
| Readout (detection above baseline) | **Closed on both 20B axes** |
| Readout-causal | Closed for 5 prior axes; **40E 20B documents 107× SNR near-miss of pre-registered gate, openly** |
| Likelihood-conditioning via η → ε bridge | **Closed on both 20B axes (F28 +0.596; 40E +1.412 — PROJECT RECORD)** |
| Factorization | Closed on F28; 40E 20B on roadmap |
| Framework-predictive validity (6 predictions held) | Closed |
| Cross-scale within architecture (4 model points) | Closed |
| Cross-architecture (3 families) | Closed on F28 |
| Scale extension beyond 2.8B parameters | **Closed under TWO named methodologies (20B)** |
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
| Disk-persisted packet store (single-instance restart-survival) | Closed (single-instance only) |
| Multi-instance / host-loss durability (replica + failover) | Open — NOT proven (one Postgres server, no replica/failover; see §9.10) |
| Append-only cryptographic hash chain | Closed |
| Five-check verify endpoint with active S3 round-trip | Closed |
| Three-state UI trust surfacing for S3 anchors | Closed |
| External anchoring service active in production (`mode=s3`) | Closed; first production anchor URI archived |
| **HeadObject mechanical WORM-retention verification (Governance mode)** | **Closed — proves retention present/current at audit time; operator-overridable, so tamper-evidence not immutability** |
| **PR #125 ACCEPT-requires-WORM-retention gate** | **Closed (gate mechanism); no packet has passed it to a standing ACCEPT** |
| Fleet-topology verifier gate | Closed |
| Fragment-payload SHA-256 commitment | Closed |
| ~~First ACCEPT verdict in project record (Stage 9 40E validation packet)~~ | **WITHDRAWN in v2.0 — pre-fix overclaim (candidate-only control_proof before commit `337d0c2`); honest WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW; no ACCEPT stands** |
| **Matched-taxonomy specificity (CAS vs cardinality-matched comparators)** | **Open — Stage MTC pre-registered; v1 nulled (text-leak), v2 nulled (meaning-removal); first blind comparator (GPT-NeoX-20B Condition-3, 2026-06-03) = GREY (CAS did not beat matched control by pre-registered margin); CAS-specificity NOT LICENSED; TKS-Meaning Preservation Rule adopted (§6.9)** |
| **Grok-1 / frontier-scale (>20B) validation** | **Open — in-flight scale extension (§5.18); audit infrastructure live; no results LICENSED** |
| Hidden-content / suppression detection (prototype) | Open |
| Surface-text steering at scale | Open |
| Multi-Harness Composition coordinator | Open |
| Multi-turn Evidence Packet reconstruction (chain of inferences over session) | Open — next product gate |
| Per-customer production ACCEPT verdicts | Open (validation-packet scope only at this time) |

### 5.17 Matched-Taxonomy Control (MTC) — Open Tier with Two Pre-Registered Nulls (NEW v1.9)

**The question Stage MTC tests:** Every closed tier in this spec sheet establishes that the model linearly encodes whatever distinctions the CAS labels track, and that this encoding is causally load-bearing. **None of these tiers, individually or together, distinguishes between** (a) "the CAS label set is linearly recoverable and causally load-bearing" (LICENSED) and (b) "the recovered structure is *CAS-specific* — the framework describes something distinctive about how the model represents meaning, rather than being one coherent relabeling of generic semantic structure" (NOT YET LICENSED).

This matters because high lift on a coherent semantic partition is expected for essentially any well-formed taxonomy — linear decodability is a generic property of coherent semantic structure read through transformer interfaces. Beating a strong text baseline supports (a) maximally but says nothing about (b). Claim (b) is inherently **comparative** and can only be earned against cardinality-matched alternatives.

**Stage MTC pre-registered methodology:** scrambled-CAS label permutation + alternative-coherent taxonomy + lexical/TF-IDF baseline taxonomy, all applied to the same activations as CAS, with pre-committed gates on lift dominance, flat lacunarity, and nested-factor specificity.

**Two pre-registered fixture attempts produced documented nulls before reaching the matched-comparator gate:**

#### MTC v1 — Surface Gate fail (text leakage)
- v1 dual-labeled fixture generated 2026-05-30
- Text-baseline classifier scored 100% — the surface text leaked the answer key
- Pre-registered Surface Gate triggered; v1 rejected before activation capture
- Disposition: build error; fixture redesigned

#### MTC v2 — Recoverability Gate fail (TKS-meaning removal)
- v2 generator rewritten to fix surface leakage
- Text-baseline collapsed to ~1% (CAS 40E text baseline 1.00%, CAS F28 text baseline 1.43%) — leakage cleanly removed
- 20B activation capture executed: 1000 rows × 44 layers × 6144 dim (40E), 700 rows × 44 layers × 6144 dim (F28)
- Recoverability run on captured activations: CAS hidden readout collapsed to ~chance (40E 5.50% vs 4.50% text baseline = +1.00 pp; F28 5.036% vs 2.878% = +2.158 pp). Required gate: +20 pp lift. Verdict: FALSIFY this fixture as a valid MTC substrate.
- **Root-cause diagnosis (post-mortem of v2 generator code):** v2 explicitly banned the entire TKS-canonical vocabulary (10 Noetic names, 7 Drive names, 4 Register names, framework meta-terms) from every prompt via regex word-boundary check, and assigned CAS labels to the resulting workplace scenarios via random shuffle (no semantic connection between prompt content and CAS label). This was diagnosed as a meaning-removed fixture, not a leakage-removed-with-signal-preserved fixture. The v2 null was a build error: the model failed to recover labels because there was nothing to recover — by construction.
- Disposition: build error; documented openly; the v1 detection-lift result (95.625% / +46.4 pp) is unaffected by the v2 result because v2 was never a valid substrate for adjudicating v1. v2.5 fixture pending under the new TKS-Meaning Preservation Rule (see §6.9).

#### MTC Condition-3 — first blind matched-taxonomy comparator (2026-06-03) = GREY (NEW v2.0)

The first matched-taxonomy comparator to clear both fixture-validity gates and actually run blind was executed on **GPT-NeoX-20B** on **2026-06-03**, under the MTC **Condition-3** protocol (CAS meaning carried in everyday scenarios, topic/frame orthogonal to CAS, domain carried as register; CAS scored blind against a cardinality-matched control taxonomy on the same activations).

- **Result: GREY.** CAS did **not** beat the matched control by the pre-registered margin. The comparator neither confirmed nor cleanly falsified CAS-specificity — it landed in the pre-registered indeterminate band.
- **Consequence:** the matched-taxonomy CAS-specificity claim remains **NOT LICENSED**. A GREY is not a pass; the "CAS-specific rather than a generic semantic partition" claim is still open.
- **Scope of the GREY (important):** this GREY is scoped **strictly to the Condition-3 comparative-specificity test**. It does **not** touch — and must not be read as weakening — the GPT-NeoX-20B Stage 9 40E **hidden-readout detection result (95.625%)** or the **η→ε bridge PASS** (probe-readable Δ +1.412 / gold-readable Δ +1.498 / partner margin +2.881). Those detection and conditioning results stand exactly as in v1.9 (subject to the same signal-vs-leakage adjudication that was already open in §9.8 — that adjudication is a separate, pre-existing question, not a consequence of the Condition-3 GREY).

**Both nulls and the GREY comparator are part of the discipline record, not concealment.** The pre-registered gates fired against the team's own fixture builds, and the first comparator to run blind returned an honest GREY rather than being talked up to a pass — exactly as the discipline is designed to operate. The matched-taxonomy specificity claim and the "universal rather than something we invented" framing both remain NOT LICENSED.

### 5.18 Grok-1 (xAI, 314B) Scale Extension — In-Flight, Not Licensed (NEW v1.9)

CAS Harness is mid-execution on the first audit-chain extension above 20B parameters.

**Audit target:** `TevunahAi/Grok-1-BF16` — a community Hugging Face BF16 conversion of `xai-org/grok-1` (xAI's original JAX-format checkpoint). xAI publishes Grok-1 only in JAX format; the CAS Harness probe stack runs on Hugging Face Transformers. The Tevunah conversion is the available HF-format substrate.

**Posture as of 2026-05-30:**
- 8× NVIDIA H200 pod active (1,128 GB VRAM, 1.5 TiB RAM, NV18 full mesh)
- Model structure validated (64 layers, `model.layers` hook path confirmed)
- BF16 shard download approaching completion (572 GB of 633 GB; 14 of 17 shards)
- Per-shard SHA-256 hashes computed and committed locally
- Model-provenance schema (PR #128) deployed; Evidence Packets generated against Grok-1 will carry explicit converted-checkpoint disclosure
- Download revision pinned to a specific HF commit SHA
- Post-download watcher will refuse to seal provenance unless all 17 shards verified
- After provenance seal: one-scenario one-layer real-activation smoke; then S9-40E layer-28 first probe

**Honest disclosure schema, embedded in every Grok-1 Evidence Packet:**

```json
"model_provenance": {
  "model_family": "grok-1",
  "model_publisher_of_record": "xai-org",
  "original_checkpoint_format": "jax",
  "consumed_checkpoint": "TevunahAi/Grok-1-BF16",
  "consumed_checkpoint_format": "huggingface-bf16",
  "conversion_path": "jax->hf-bf16",
  "conversion_authority": "third-party (TevunahAi), not xAI",
  "consumed_checkpoint_revision_sha": "<pinned-HF-commit>",
  "consumed_checkpoint_sha256_per_shard": [...17 hashes...],
  "license": "Apache-2.0",
  "conversion_audit_status": "unverified-by-cas-harness"
}
```

The `conversion_authority` and `conversion_audit_status` fields are load-bearing. They make it unambiguous that **CAS Harness audited the model that ran**, not the model xAI published directly. Any future stronger claim would require either auditing TevunahAi's conversion methodology or extending CAS Harness to read JAX checkpoints natively.

**What is LICENSED about Grok-1 work as of v1.9:** the audit infrastructure (provenance schema, hash-pinned download, per-shard SHA-256, watcher-gated smoke).
**What is NOT LICENSED about Grok-1 work as of v1.9:** any audit *result*. No detection result, no causal result, no bridge result has been generated on Grok-1. Frontier-scale (>20B) validation remains NOT LICENSED.

---

## 6. Methodology Discipline as Competitive Differentiator (UPDATED v1.9)

Nine discipline principles (one new in v1.9):

1. **Pre-registered acceptance criteria** (with open disclosure of the Stage 9 40E ablation near-miss and the two MTC fixture nulls)
2. **Locked artifact hashes**
3. **Matched controls**
4. **Honest NULL discipline** — including the two MTC nulls documented in §5.17
5. **Reserved-language claim map**
6. **Independent reproducibility commitment**
7. **Named canonical method discipline** — S7-F28-BALANCED-BRIDGE, S9-40E-ORIGINAL-BASELINE-READOUT
8. **Audit-grade integrity-chain discipline** — five-layer chain (disk + hash chain + five-check verify + HeadObject mechanical WORM + PR #125 ACCEPT-requires-WORM gate + three-state UI). Discovery, retrieval, and verification of a packet are operations any external auditor can perform without operator cooperation.

### 6.9 TKS-Meaning Preservation Rule (NEW v1.9, equal tier to #1–#8)

> **A recoverability fixture must preserve the TKS-canonical semantic content of every class it asks the model to recover. The fixture may strip surface answer-key wording (vocabulary anchors, framework names, operator notation), but it must not strip the meaning that wording was naming. A prompt with the answer-key words removed and the underlying TKS-canonical situation also removed is not a "leakage-removed" prompt — it is a meaning-removed prompt. Meaning-removed prompts cannot be used to test recoverability and will produce false NULL results that look like falsifications but are build errors. Recoverability fixtures must pass an explicit Meaning Preservation gate (independent rater verification) before any GPU-tier capture is authorized.**

**Implementation:** every future recoverability fixture (Stage MTC v2.5 and beyond, Grok-1 fixtures, any new model's fixture) must pass two gates in order before any pod-hour is authorized for activation capture:

1. **Surface Gate** — text baseline classifier accuracy near chance (the v1 MTC failure mode is blocked)
2. **Meaning Preservation Gate (NEW v1.9)** — independent CAS-competent raters successfully recover CAS labels from prompt meaning at calibrated above-baseline accuracy (the v2 MTC failure mode is blocked)

A fixture that fails either gate is rejected before any GPU-tier expense. The rule is now part of CAS Harness methodology at the same tier as pre-registration discipline.

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
8. **TKS-Meaning Preservation Rule (NEW v1.9)** added as ninth methodology discipline principle, motivated by openly documented Stage MTC v2 build error

### 7.2 Engineering (selected highlights)

1. Complete probing pipeline across three architecture families and four within-family scales
2. Six reusable cognitive axes
3. Verification Stack at 87.6% / 99.78%
4. Evidence Packet schema with six proof chips + verifier report + three-lock verifier gate
5. **Audit-grade integrity chain**: disk persistence (single-instance restart-survival) + hash chain + five-check verify (incl. S3 round-trip) + HeadObject mechanical WORM-retention check (Governance mode) + PR #125 ACCEPT-requires-WORM-retention gate + external anchoring (disabled/local/S3) + three-state UI
6. Production anchoring live on s3 mode as of 2026-05-28; **strict Object-Lock-retention smoke PASS 2026-05-29**
7. Fleet-topology verifier gate (conservative-default at multi-worker 100B/300B scale)
8. Fragment-payload SHA-256 commitment (anti-misattribution in fleet)
9. Audit Console UI with verdict + chips + confidence + scope + boundary rendering + PR #125 downgrade surface
10. ~~First ACCEPT verdict in project record~~ — **WITHDRAWN in v2.0**: the Stage 9 40E ACCEPT was a pre-fix overclaim (candidate-only control_proof before commit `337d0c2`); honest WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW; no ACCEPT stands in the project record
11. **Five-diagram architecture reference (§4.5–§4.9) for code-walk cross-verification (NEW v1.9)**
12. **MTC pre-registration infrastructure with materializer eligibility gate and TKS-Meaning Preservation enforcement (NEW v1.9)**
13. **Grok-1 BF16 provenance schema and hash-pinned download infrastructure (NEW v1.9)**

### 7.3 Strategic

1. Parallel product line to CAS Native with distinct legal IP framing
2. Framework predictive validity at two evidence tiers
3. Cross-architecture + cross-scale validated under two named canonical methodologies
4. Audit-grade integrity chain as a differentiator from research-grade interpretability tooling — designed to produce regulator-facing evidence artifacts (no third-party compliance certification claimed; see standing disclaimer)
5. Use-case map (§13) covering developer and enterprise deployment patterns
6. **NDA-gated code-walk readiness**: §4 architecture diagrams designed to support technical reviewer cross-verification against codebase

---

## 8. Reserved-Language Claim Map (UPDATED v1.9)

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
| "Evidence Packets disk-persisted (single-instance restart-survival), hash-chained, tamper-evident, externally anchorable" | LICENSED (single-instance durability only; multi-instance/host-loss NOT proven — see §9.10) |
| "Verify endpoint runs five independent checks per call, including active S3 round-trip" | LICENSED |
| "Audit Console UI distinguishes three S3-anchor trust states (verified / receipt-only / failed)" | LICENSED |
| "HeadObject mechanical WORM-retention check confirms Object Lock (Governance mode) retention is present and current per-anchor at audit time" | LICENSED |
| "PR #125 ACCEPT-requires-WORM-retention gate: an explicit ACCEPT requires all three retention proofs or is downgraded to FLAG_FOR_HUMAN_REVIEW" | LICENSED (gate mechanism; no packet has passed it to a standing ACCEPT) |
| "S3 Object Lock Governance retention makes any operator override of an anchor tamper-evident on the next verify call" | LICENSED (tamper-evidence, NOT physical immutability) |
| "S3 Object Lock immutability — chain fingerprints cannot be modified even by the operator" | NOT LICENSED (Governance mode is operator-overridable via `s3:BypassGovernanceRetention`; ~30-day rolling retention; guarantee is tamper-evidence, not immutability) |
| "Fleet-topology verifier gate preserves conservative-default verdict policy at 100B/300B scale" | LICENSED |
| "Blind-spot detection per-class with readout-vs-model-side disambiguation" | LICENSED |
| "Hidden-content / suppression detection at CAS-class granularity" | LICENSED with caveats (prototype tier; see §4.9) |
| "Runtime-safe accept/suppress decisions without gold labels at inference" | LICENSED |
| "Head-level + sparse MLP-neuron-cover causal localization with necessity AND sufficiency" | LICENSED |
| "Drive-local eraser-channel steering, cross-scale within Pythia + cross-architecture on Qwen" | LICENSED |
| "First ACCEPT verdict in project record on Stage 9 40E validation packet" | NOT LICENSED — WITHDRAWN in v2.0 (pre-fix overclaim; candidate-only control_proof before commit `337d0c2`; honest WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW; no ACCEPT stands) |
| **"TKS-Meaning Preservation Rule governs all recoverability fixtures; Surface Gate + Meaning Preservation Gate must pass before any GPU-tier capture"** | **LICENSED (v1.9)** |
| **"MTC stage pre-registered with two openly documented fixture nulls (v1 leak / v2 meaning-removal)"** | **LICENSED (v1.9, methodology claim)** |
| **"Grok-1 (314B BF16) audit infrastructure deployed with converted-checkpoint disclosure schema"** | **LICENSED (v1.9, infrastructure only — no audit results)** |
| "Per-customer production ACCEPT verdicts" | NOT LICENSED (validation-packet scope only) |
| "Frontier-scale (>20B) validation" | NOT LICENSED |
| "Grok-1 audit results" | NOT LICENSED (in-flight; no detection / causal / bridge result available) |
| "Single-neuron monosemantic localization" | NOT LICENSED |
| "Universal interpretability platform" | NOT LICENSED (three families ≠ universal) |
| "CAS structure is CAS-specific rather than a generic semantic partition" | NOT LICENSED (Stage MTC open; two pre-registered fixture nulls; first blind comparator — GPT-NeoX-20B Condition-3, 2026-06-03 — returned GREY; specificity gate not closed) |
| "First blind matched-taxonomy comparator (GPT-NeoX-20B Condition-3) outcome" | GREY — CAS did NOT beat the matched control by the pre-registered margin; CAS-specificity NOT LICENSED. GREY is scoped to the comparator only and does NOT weaken the 40E detection (95.625%) or η→ε bridge PASS |
| "Universal rather than something we invented" | NOT LICENSED (specificity claim required first; Condition-3 comparator GREY; see Stage MTC) |
| "Output-side steering at 3-family parity with readout claim" | NOT YET LICENSED (OLMo replication open) |

---

## 9. Current Bounds & Limitations (Honest)

### 9.1 Architectural Bound

Three architecture families validated (Pythia/GPT-NeoX, OLMo, Qwen). Three ≠ universal. Claim language remains comparative-and-bounded, not universal.

### 9.2 Scale Bound

Up to 20B parameters across two cognitive axes under two named canonical methodologies. Beyond 20B: Grok-1 (314B BF16) audit infrastructure is in flight; no audit results LICENSED. Frontier-scale validation remains NOT LICENSED.

### 9.3 Modal Bound

Text only. No multimodal (image, audio, video) validation.

### 9.4 Per-Class Bound

Some CAS classes are stable across architectures; others show blind-spot or model-side weakness on specific architectures. The blind-spot detector surfaces these. Per-class claims are bounded by the per-class evidence.

### 9.5 Granularity Bound

Head-level and sparse-neuron-cover localization validated. Single-neuron monosemantic localization NOT LICENSED.

### 9.6 Evidence-Tier Bound

Detection / readout-causal / η→ε bridge / weight-geometry are validated as named in §5.16. Hidden-content detection is prototype. Surface-text steering at scale is open.

### 9.7 Verifier Discipline (v1.7+ disclosures, expanded in v1.9)

- v0 verifier confidence rule: `confidence = readout_chip.accuracy`. Multi-factor v1 confidence on roadmap.
- Stage 9 40E ablation near-miss (28.7 pp / 66.9% vs pre-registered ≥30 / ≤65) documented openly. Verifier accepted on 107× SNR policy; threshold-policy discrepancy is auditable.
- **Withdrawn ACCEPT (NEW v2.0):** the previously reported "first ACCEPT verdict in the project record" (Stage 9 40E validation packet, 2026-05-28/29) is **withdrawn**. It rested on a candidate-only `control_proof` stamped verified before commit `337d0c2`. The honest WORM-retained verdict is **FLAG_FOR_HUMAN_REVIEW**; **no ACCEPT stands** in the project record. The console honesty gate now downgrades that packet to FLAG_FOR_HUMAN_REVIEW (no standing WORM ACCEPT).
- **PR #125 ACCEPT-requires-WORM-retention gate:** even an explicit verifier ACCEPT is mechanically downgraded to FLAG_FOR_HUMAN_REVIEW if any of the three retention proofs (anchor written + re-read match + Object Lock retention active) is missing. The trust contract is gated mechanically at the verdict layer. The gate mechanism is verified; no packet has passed it to a standing ACCEPT.
- **HeadObject mechanical WORM-retention verification (CLOSED):** previously "in flight." Now mechanically verified per-anchor at every audit call. Confirms Object Lock Governance-mode retention is present and current; Governance mode is operator-overridable (`s3:BypassGovernanceRetention`), so this proves tamper-evidence, not physical immutability.

### 9.8 Comparative-Specificity Bound (NEW v1.9; comparator result added v2.0)

The matched-taxonomy specificity claim ("CAS is CAS-specific rather than a generic semantic partition") is **NOT LICENSED.** Stage MTC is openly pre-registered with two documented fixture nulls (v1 text-leak, v2 meaning-removal). Both nulls are build errors caught by pre-registered gates, not findings against CAS. The v1 detection-lift results (95.625% / +46.4 pp on 40E, 86.86% on F28) are not *falsified* by the v2 null — v2 was a different, invalid (meaning-removed) substrate and cannot adjudicate v1.

**First blind comparator outcome (NEW v2.0) — GREY.** The first matched-taxonomy comparator to clear both fixture-validity gates and run blind (GPT-NeoX-20B, MTC **Condition-3**, 2026-06-03) returned **GREY**: CAS did **not** beat the cardinality-matched control by the pre-registered margin, landing in the pre-registered indeterminate band. A GREY is not a pass — CAS-specificity stays **NOT LICENSED**. **Scope:** this GREY is confined to the Condition-3 comparative-specificity test. It does **not** touch the 40E hidden-readout detection (95.625%) or the η→ε bridge PASS (those stand as in v1.9). The separate signal-vs-leakage question on the v1 detection lift (below) was already open before Condition-3 and is unchanged by it; the two should not be conflated.

> **Footnote (signal-vs-leakage adjudication is OPEN, not closed).** The v1 detection-lift *interpretation* is not yet settled. Three facts a reviewer should have up front: (1) the original 40E fixture carries a **49.24% exact-fixture text baseline**; (2) the hidden readout peaks at **layer 2 of 44**; (3) the v1 prompt embeds each element's **definition gloss verbatim** — e.g. the prompt for label `A1` literally contains "ultimate source-awareness, unseen purpose, and the soul's contact with what guides all causes," which is `A1`'s own gloss (`element_gloss` field in `stage9_elements_pilot_20260517.v1.jsonl`). The literal class *code* and framework words were stripped (`anti_leak_flags.contains_literal_element_code = false`), but the meaning-bearing gloss was not. All three facts are consistent with a meaningful fraction of the lift being gloss/surface-carried. The internal pilot record (`docs/working/cas_harness_mtc_20b_pilot_results_20260530.md`, "Stage LSA Next Gate") states this directly: *"v1's detection lift may have been substantially carried by surface leakage."*
>
> The pre-registered adjudicator is **Stage LSA (Leakage-vs-Signal Adjudication)**, frozen prereg `docs/working/cas_harness_leakage_signal_adjudication_prereg_20260530.md` (v0.3). It is a **judge-based** test, not another hidden-state probe: CAS-competent, model-blind raters (plus an independent `gemini-3.1-pro-preview` rater) attempt to recover the CAS label from each item's *meaning alone* after answer-key wording is stripped. **Arm A is primary** — it takes the *original v1 items* and applies the frozen strip contract ("remove answer-key wording, preserve the TKS meaning"), a human redaction protocol, not the v2 generator (v2 was wholesale regeneration of unrelated prose, which is why it nulled). If Arm A judges still recover the labels, the v1 items carry meaning beyond surface tells and the result stays scientifically live (but externally restricted until reproduced on a non-leaking instrument); if Arm A judges fail, *"v1 detection-lift claims must be caveated as surface-carried pending re-derivation."* Arm B (v2 stripped items) is supporting diagnostic only. Until Stage LSA Arm A returns, the LICENSED reading of the 95.625% readout is the narrow one — **the model linearly encodes the label distinction more strongly than a bag-of-words text classifier** — not that the lift is established CAS-specific signal.

The specificity claim remains scientifically open and is the subject of pending Stage MTC v2.5 fixture work under the TKS-Meaning Preservation Rule, gated behind Stage LSA Arm B.

### 9.9 Grok-1 Scope Bound (NEW v1.9)

Grok-1 audit work is **infrastructure-only LICENSED, results-NOT-LICENSED.** The provenance schema, hash-pinned download, per-shard SHA-256, and converted-checkpoint disclosure (`TevunahAi/Grok-1-BF16` is a third-party HF conversion of `xai-org/grok-1`'s JAX original; conversion not audited by CAS Harness) are operational. No Grok-1 detection, causal, or bridge result has been generated. Frontier-scale validation explicitly remains NOT LICENSED.

### 9.10 Durability Bound (NEW v2.0)

Evidence-Packet durability is proven **only** for single-instance restart-survival: on one paid-disk instance, packets survive restart, redeploy, and crash, with regression-tested bit-identical reload. **Multi-instance and host-loss durability are NOT proven.** The deployment runs a single Postgres server with no replica and no failover; loss of that host, or its disk, is not covered by any tested recovery path. Claims of high availability, geographic redundancy, or host-loss durability are **NOT LICENSED**. This is an infrastructure-maturity bound, not a property of the integrity chain itself (the hash chain and external S3 anchor remain independently re-verifiable wherever the packet data survives).

### 9.11 No Certification Bound (NEW v2.0)

Noetic Compass holds **no** SOC 2, ISO/IEC 42001, or other third-party security or compliance certification. CAS Harness Evidence Packets are **designed to produce regulator-facing evidence artifacts** that support compliance documentation; they do **not** by themselves satisfy any regulation, and nothing in this document is legal advice. Framings such as "regulator-grade by construction," "court-admissible," or "compliant" are NOT claimed; where regulatory regimes are named (§13), they describe the documentation need the artifacts are designed to support, not a certification held.

---

## 10. Comparison Landscape

| System | CAS Harness Difference |
|---|---|
| Anthropic Neural Network Analysis (NLA) | Three sizes of one Anthropic family vs. **six models in three architecture families on two cognitive axes at 20B**; NLA admits "confabulation" tier; CAS Harness typed-class hidden-content detector (§4.9) cannot confabulate beyond bounded class set. CAS Harness emits **disk-persisted, hash-chained, five-check-verified, HeadObject WORM-retention-verified (Governance mode, tamper-evident), PR #125-gated Evidence Packets**. |
| Linear probes (academic) | CAS Harness adds causal validation, η→ε bridge, framework-predictive diagnostics, multi-layer trace, two named canonical protocols, **and** full audit-grade integrity chain with active external re-verification + mechanical WORM-retention verification (tamper-evidence, not immutability) |
| SHAP / LIME / classical XAI | Output-feature attribution only; CAS Harness reads internal structural cognitive properties with cryptographic audit chain |
| AWS Bedrock Automated Reasoning Checks | Output-level formal-logic verification; CAS Harness is representation/causal level; **complementary, not competitive** — both can carry audit-grade evidence packets |
| Causal scrubbing | Mech-interp researchers only; CAS Harness productizes the discipline at different granularity |
| TransformerLens / mechanistic interpretability | Open-source research tooling; CAS Harness is productized with audit chain + PR #125 verdict gate |
| Black-box behavioral testing | Complementary, not competitive |

---

## 11. IP & Legal Status (UPDATED v1.9)

USPTO Provisional #64/037,173 covers CAS framework primitives. Noetic Topos paper journal submission in progress.

IP attorney consultation in progress for additional filings including:

- η→ε bridge applied to foreign open-weight transformers
- The two named canonical methodologies (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`)
- The Audit-Grade Integrity Chain composite filing covering: six-proof-chip packet + verifier report + disk persistence + append-only hash chain + five-check verify endpoint + three-state UI surface + external anchoring service + **HeadObject mechanical WORM-retention verification (Governance mode) + PR #125 ACCEPT-requires-WORM-retention gate**
- Fragment-payload SHA-256 commitment for fleet evidence merging
- Fleet-topology verifier gate
- Framework-predictive preflight diagnostic methodology
- **TKS-Meaning Preservation Rule and the Meaning Preservation Gate apparatus (NEW v1.9)**
- **MTC pre-registration infrastructure including dual-labeled fixture generator, materializer eligibility gate, and pre-committed comparator gates (NEW v1.9)**
- **Grok-1 BF16 converted-checkpoint provenance schema and hash-pinned reproducibility apparatus (NEW v1.9)**

External disclosure: NDA-only.

---

## 12. Glossary (UPDATED v1.9)

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
| 10 Noetics / 4 Domains / 4 Registers / 7 Drives / 40 Elements / 28 Foundations | CAS primitive axes (Noetic names verbatim from Tootra Math Handbook per CAS v7.7) |
| Lacunarity | Factorization-quality measure (Var/Mean²); lower is cleaner |
| Fractal classifier | Iterated-operator orbit classifier |
| Proposition 5.6 | Noetic Topos theorem proving counit ε's pullback is surjective |
| Evidence Packet | Per-inspection structured customer artifact (six proof chips + verifier report + audit chain provenance) |
| Proof Chip | Single typed evidence claim inside Evidence Packet; SHA-256-committed |
| Verifier Report | Stage 19/20-style decision-rule layer producing ACCEPT / SUPPRESS / FLAG_FOR_HUMAN_REVIEW with explicit verdict, confidence, scope, coverage, boundary |
| Audit-Grade Integrity Chain | Five-layer evidence integrity stack: disk-persisted packet store (single-instance restart-survival) + append-only cryptographic hash chain + five-check verify endpoint + external anchoring service + three-state UI trust surface + **HeadObject mechanical WORM-retention check + PR #125 ACCEPT-requires-WORM-retention gate** |
| WORM Anchoring | S3 Object Lock in **Governance mode** with an approximately 30-day rolling retention window. Mechanically verified per-anchor via HeadObject at audit time. Governance retention is **operator-overridable** (`s3:BypassGovernanceRetention`); the guarantee is **tamper-evidence on re-verify**, not write-once physical immutability. (v1.9 described this as Compliance-mode "write-once-read-many immutability" — corrected in v2.0.) |
| Hash Chain | Append-only JSONL log; every entry includes cryptographic fingerprint of previous entry |
| Five-Check Verify Endpoint | `/evidence/{trace_id}/verify` runs five independent checks: payload / log / chain / anchor manifest / external S3 round-trip (GetObject + hash). Returns `verified` only when all five pass; `partial_mismatch` with named layer otherwise. |
| Three-State UI Trust Surface | Audit Console distinguishes "S3 object verified" (5-check passed including round-trip) / "Anchored to S3" (receipt at write time, no live re-read) / "S3 verify failed" (round-trip ran, found discrepancy) |
| HeadObject WORM-Retention Verification (CLOSED) | AWS S3 metadata API that returns Object Lock fields without downloading file body. Integrated into the verify endpoint to mechanically confirm `ObjectLockMode` is `GOVERNANCE` and retention (`ObjectLockRetainUntilDate`) is current. Provides per-anchor proof that retention is present and current — and makes any operator override tamper-evident — rather than a configuration-based assertion. Governance mode is operator-overridable (`s3:BypassGovernanceRetention`); this is NOT a proof of physical immutability. |
| PR #125 ACCEPT-Requires-WORM-Retention Gate | Verifier's explicit ACCEPT verdict requires `packet_proof` for all three retention conditions: anchor written + re-read match + Object Lock retention active. Missing any proof automatically downgrades ACCEPT to FLAG_FOR_HUMAN_REVIEW. Gate mechanism is verified; as of v2.0 no packet has passed it to a standing ACCEPT. |
| GREY (comparator outcome) | Pre-registered indeterminate band for a matched-taxonomy comparator: CAS neither beats the matched control by the pre-registered margin (which would support specificity) nor is cleanly falsified. The first blind comparator (GPT-NeoX-20B Condition-3, 2026-06-03) returned GREY; CAS-specificity remains NOT LICENSED. |
| Fragment-Payload SHA-256 Commitment | Cryptographic binding of fleet worker contribution to claimed payload |
| Verification Stack | Runtime-safe acceptance/suppression decision layer |
| Mode Selector | Three customer-configurable verification modes |
| Generation Readiness Gate | Four-tier action discipline (allow / caveat / constrain / suppress) |
| Blind-spot detection | Per-class identification of model-side vs readout-position weakness |
| Cross-architecture transfer | Validation that η→ε bridge replicates across independent architecture families |
| Cross-scale transfer | Validation that η→ε bridge replicates across parameter scales within an architecture family |
| **TKS-Meaning Preservation Rule (NEW v1.9)** | **Anti-drift methodology rule at equal tier to pre-registration discipline. Recoverability fixtures must preserve the TKS-canonical semantic content of every class; surface answer-key wording may be stripped, canonical meaning may not. Fixtures must pass a Meaning Preservation Gate (independent rater verification) before GPU-tier capture is authorized.** |
| **Surface Gate (NEW v1.9)** | **Pre-registered fixture-validity gate. Text baseline classifier accuracy must be near chance, or fixture is rejected. The v1 MTC failure mode (100% text baseline) is blocked at this gate.** |
| **Meaning Preservation Gate (NEW v1.9)** | **Pre-registered fixture-validity gate. CAS-competent independent raters must successfully recover CAS labels from prompt meaning at calibrated above-baseline accuracy, or fixture is rejected. The v2 MTC failure mode (TKS-meaning removal) is blocked at this gate.** |
| **Stage MTC — Matched-Taxonomy Control (NEW v1.9)** | **Open pre-registered evidence tier testing whether CAS factorizes model representations more cleanly than cardinality-matched alternative or scrambled taxonomies. Two fixture attempts (v1, v2) produced documented nulls before reaching the matched-comparator gate. v2.5 fixture pending under TKS-Meaning Preservation Rule.** |
| **Grok-1 Model-Provenance Schema (NEW v1.9, PR #128)** | **Evidence Packet field set documenting converted-checkpoint provenance: model_publisher_of_record / original_checkpoint_format / consumed_checkpoint / consumed_checkpoint_format / conversion_path / conversion_authority / consumed_checkpoint_revision_sha / consumed_checkpoint_sha256_per_shard / conversion_audit_status. Makes unambiguous which checkpoint was audited and by whom converted.** |

---

## 13. Use Cases — What Developers and Enterprises Do With CAS Harness

CAS Harness occupies a single product position: **the black-box flight recorder for AI cognition.** Every inference produces a cryptographically verifiable audit packet documenting what the model was doing in its hidden states, not just what it said in its output. The downstream use cases follow from that property.

### 13.1 Developer Use Cases

#### 13.1.1 Pre-Deployment Model Evaluation

Before shipping any LLM-powered feature, a developer runs CAS Harness against the candidate model to establish a baseline cognitive profile across the six cognitive axes. When the vendor pushes a model update, the developer re-runs and gets a structural delta report on what actually changed. Without CAS Harness, model updates today are evaluated on aggregate benchmarks that do not surface CAS structural shifts.

#### 13.1.2 Hallucination Root-Causing

When the deployed model produces a hallucination, CAS Harness identifies the structural failure mode: ^9 Below/Effect fired without an upstream ^8 Above/Cause grounding it; ^6 Male (compositional decomposition) failed; F2 Wisdom under-activated relative to F5 Agency. This converts hallucination debugging from trial-and-error to structural diagnosis.

#### 13.1.3 Structured Prompt Engineering

Developer writes a prompt, sees its produced CAS structure, and iterates intentionally toward a target CAS profile. Meaningfully more efficient than blind iteration.

#### 13.1.4 Distillation Verification

Side-by-side cognitive-property report comparing teacher and student models. Distillation team gets actionable property delta instead of benchmark score.

#### 13.1.5 Adversarial Input Debugging

Jailbreak signatures surface as F6 Structure suppressed / Operational over-activated / Inversion-axis F crossed threshold. Security teams get a structural fix path.

#### 13.1.6 Cross-Model Migration Audits

Delta report names exactly which cognitive properties shift between candidate models.

#### 13.1.7 CI Integration as Cognitive-Property Quality Gate

Model fine-tuning produces a new checkpoint; CI runs CAS Harness against a held-out scenario set; if any pre-registered cognitive property regresses below threshold, the merge is blocked. Same discipline as unit tests, applied to cognitive properties.

### 13.2 Enterprise Use Cases

#### 13.2.1 Regulatory Compliance Evidence

This is the single largest enterprise use case. EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, Federal Reserve SR 11-7, SEC AI-disclosure guidance — every one calls for interpretability documentation that CAS Harness Evidence Packets are **designed to support**. (Evidence Packets are designed to support compliance documentation; they do not by themselves satisfy any regulation, and nothing herein is legal advice. Noetic Compass holds no SOC 2, ISO/IEC 42001, or other third-party certification — see §9.11 and the standing disclaimer.)

#### 13.2.2 Vendor Procurement and Model Selection

Comparative cognitive-structure reports across candidate models. Procurement decision becomes evidence-based.

#### 13.2.3 AI-Error Legal Defense

Structurally documented Evidence Packet with cryptographic SHA-256 receipt anchored to S3 Object Lock (Governance-mode retention, tamper-evident on re-verify) at the time of inference. Intended to support a stronger evidentiary record than is available without CAS Harness. (Not a claim of court-admissibility; admissibility is a determination for a court under applicable rules of evidence. Nothing herein is legal advice.)

#### 13.2.4 Internal Governance and Board AI Risk Reporting

Quantitative summaries: verdict distributions, structural drift indicators, predictions held vs failed. Boards can act on quantitative signals.

#### 13.2.5 Red-Team and Security Integration

Report elevated from "we got the model to say X" to "we induced the model into CAS state Y; here is the structural transition trace; here is the Evidence Packet."

#### 13.2.6 Customer-Trust Products

Per-inference "verified by CAS Harness" attestations to customer-facing AI outputs with optional links to underlying Evidence Packet.

#### 13.2.7 Acquisition Due Diligence

Cognitive-property report on target's deployed models. Acquisition negotiation gains structural evidence.

#### 13.2.8 Insurance Underwriting

Insureds with audit-grade Evidence Packet trails present materially lower underwriting risk.

### 13.3 Industry Vertical Specifics

| Vertical | Specific use |
|---|---|
| **Financial services** | Model risk management (SR 11-7), AI-driven credit / fraud / trading decisions, customer-facing chatbots |
| **Healthcare** | FDA SaMD pre-market submission, clinical decision support tools, post-market surveillance |
| **Legal** | Contract analysis, e-discovery review, evidentiary record-keeping for AI inference (admissibility is for a court to determine; not a claim of court-admissibility) |
| **Government / Public sector** | Citizen-facing chatbots, document AI, FOIA-style transparency for citizen-AI interactions |
| **Education** | AI tutoring systems, automated grading — AEDT-style fairness eval |
| **Defense** | Autonomous decision support — Pentagon Responsible AI principles |
| **Insurance** | Claims processing AI, underwriting AI |
| **Retail / e-commerce** | Customer-facing chatbots, recommendation systems, vendor accountability |

### 13.4 Deployment Integration Patterns

Three patterns cover the majority of enterprise integrations:

#### 13.4.1 Inference-Time Middleware

CAS Harness sits between the user request and the LLM inference call. Every inference produces an Evidence Packet. Operators select a Mode per use case.

#### 13.4.2 Sampled Periodic Audit

CAS Harness runs against a sample of production traffic (e.g., 1% or 5%) on a scheduled cron. Produces a rolling Evidence Packet stream archived for compliance.

#### 13.4.3 Development-Gate Integration

CAS Harness integrated into CI/CD. Model updates, prompt changes, and fine-tuning runs must pass pre-registered CAS Harness thresholds before merging or deploying.

### 13.5 Differentiation From Research-Grade Interpretability Tooling

CAS Harness is the first interpretability tool the founder is aware of that is **designed to produce regulator-facing evidence artifacts** (Noetic Compass holds no SOC 2, ISO/IEC 42001, or other third-party certification; see §9.11 and the standing disclaimer):

- Cryptographic chain of custody on every Evidence Packet
- Externally anchored audit log with active re-verification
- **Mechanically verifiable WORM retention via HeadObject (Governance mode, tamper-evident on re-verify — not physical immutability)**
- **PR #125 ACCEPT-requires-WORM-retention gate at the verdict layer**
- Named methodology with anti-drift discipline encoded in canonical labels
- **TKS-Meaning Preservation Rule enforcing semantic-content discipline on all recoverability fixtures**
- Reserved-language claim map with explicit "LICENSED / NOT LICENSED" boundaries
- Three-state UI surface that communicates trust precisely rather than approximately

### 13.6 Market Timing — The Regulatory Unlock Pattern

EU AI Act full applicability is rolling through 2026-2027. NIST AI RMF compliance increasingly required by US federal contract awards. SEC has signaled scrutiny on AI-related disclosures. ISO/IEC 42001 certification increasingly demanded in procurement. Once any one of these regulators meaningfully enforces the interpretability requirements already on the books, every enterprise deploying LLMs needs an artifact of the kind CAS Harness produces.

### 13.7 Future Capability Extensions

1. **Multi-turn Evidence Packet reconstruction** (open — next product gate)
2. **Closed-API model coverage** — Claude / GPT / Gemini via gray-box techniques
3. **Multimodal extension** — image-generation auditing
4. **Agent-trajectory verification** — multi-step agent-decision auditability
5. **Composability with peer safety tools** — Anthropic NLA, AWS Bedrock Automated Reasoning Checks, OpenAI safety stack
6. **Frontier-scale (>20B) validation** — Grok-1 (314B BF16) audit infrastructure deployed v1.9; results pending

---

## Appendix A — One-Page Summary

**What is it?** The black-box flight recorder for AI cognition. A software service that looks inside any open-weight large language model, detects cognitive structure inside its hidden states, proves the structure is causally load-bearing, conditions the model's output by realizing the detected structure as readable context, and emits audit-grade Evidence Packets — disk-persisted (single-instance restart-survival proven; multi-instance/host-loss durability NOT proven), cryptographically hash-chained, tamper-evident with five-check verify endpoints (in-server payload / log / chain / anchor-manifest + external S3 round-trip + HeadObject WORM-retention check), externally anchored to S3 with mechanically-verified Object Lock Governance-mode retention (~30-day rolling window, operator-overridable, tamper-evident on re-verify — not physical immutability), gated such that the final ACCEPT verdict requires all three WORM-retention proofs (PR #125), and surfaced through a three-state UI distinguishing verified / receipt-only / failed S3 anchor trust. Two canonical large-model methodologies: `S7-F28-BALANCED-BRIDGE` and `S9-40E-ORIGINAL-BASELINE-READOUT`. (Noetic Compass holds no SOC 2, ISO/IEC 42001, or other third-party certification; Evidence Packets are designed to support compliance documentation but do not by themselves satisfy any regulation, and nothing herein is legal advice.)

**How does it work?** Two-pass forward inference. (1) Balanced-logistic probe reads CAS structure from foreign model's activations. (2) Realization layer emits readable prefix; foreign model's likelihood distribution shifts toward the identified cognitive class. Full inference path captured in a typed Evidence Packet with six proof chips + verifier report, persisted to disk in an append-only hash chain (single-instance restart-survival), externally anchored to S3 with Object Lock Governance-mode retention (tamper-evident on re-verify), continuously re-verifiable. See architecture diagrams §4.5–§4.9 for code-walk-ready detail.

**Why does this work?** Noetic Topos Proposition 5.6 proves counit ε is a surjective covering morphism. In transformer terms: prefix tokens are attended to by every later token by architectural construction. Static-weight tier independently confirms: CAS Foundation subspace shows output-weight alignment 2.83× random expectation.

**What is proved today?** More than twenty closed evidence tiers across six open-weight models in three architecture families, with 20B scale extension closed on TWO cognitive axes under TWO named canonical methodologies. Includes the **strongest single η→ε bridge result in project record at +1.412 probe-readable Δ / +1.498 gold-readable Δ / +2.881 partner margin on GPT-NeoX-20B 40-Element axis with 94.3% probe-to-gold efficiency.** Full audit-grade integrity chain end-to-end in production (s3 anchor mode active since 2026-05-28; HeadObject mechanical WORM-retention check closed and strict Object-Lock-retention smoke PASS 2026-05-29; PR #125 ACCEPT-requires-WORM-retention gate enforced at the verdict layer). **No ACCEPT verdict stands in the project record:** the previously reported "first ACCEPT" on the Stage 9 40E validation packet was a pre-fix overclaim (candidate-only control_proof before commit `337d0c2`), withdrawn in v2.0; its honest WORM-retained verdict is FLAG_FOR_HUMAN_REVIEW.

**What is openly NOT proved today?** The matched-taxonomy specificity claim ("CAS is CAS-specific rather than a generic semantic partition") is NOT LICENSED — Stage MTC is openly pre-registered with two fixture nulls (v1 text-leak / v2 TKS-meaning removal), and the first blind comparator (GPT-NeoX-20B Condition-3, 2026-06-03) returned **GREY** (CAS did not beat the matched control by the pre-registered margin; the GREY is scoped to the comparator and does not touch the 40E detection or η→ε bridge). Grok-1 (314B) audit results are NOT LICENSED — infrastructure deployed, no detection / causal / bridge result generated. Frontier-scale (>20B) validation remains NOT LICENSED. Per-customer production ACCEPT verdicts remain NOT LICENSED — and **no ACCEPT verdict of any kind stands** (the prior Stage 9 40E ACCEPT was withdrawn). Multi-instance / host-loss durability is NOT proven (single Postgres server, no replica/failover). Noetic Compass holds no SOC 2 / ISO/IEC 42001 / other third-party certification. The discipline is in the open documentation, not in concealment.

**Who uses it for what?** Developers use it for pre-deployment model evaluation, hallucination root-causing, structured prompt engineering, distillation verification, adversarial debugging, cross-model migration, and CI quality-gating. Enterprises use it for regulatory compliance evidence (EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, SR 11-7), vendor procurement evaluation, AI-error legal defense, board AI risk reporting, customer-trust products, red-team integration, acquisition due diligence, and insurance underwriting. Full use-case map in §13.

**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific, not scale-bounded below 20B parameters, and not axis-specific.**

**What is the bounded claim today?** Reads, validates, conditions, and emits audit-grade structural evidence for open-weight LLMs up to 20B parameters across three architecture families on TWO cognitive axes, under TWO canonical methodologies, with disk-persisted (single-instance restart-survival) cryptographically chained Evidence Packets externally anchored to S3 with mechanically-verified Object Lock Governance-mode retention (tamper-evident on re-verify, operator-overridable — not physical immutability) and PR #125 ACCEPT-requires-WORM-retention verdict gating, continuously re-verifiable by any third party with read access. Single-neuron monosemantic localization, frontier-scale (>20B), per-customer production ACCEPT verdicts (and indeed any standing ACCEPT — none currently stands), matched-taxonomy CAS-specificity (Condition-3 comparator GREY), multi-instance / host-loss durability, and any third-party security/compliance certification all remain explicitly open boundaries.

**Where to go from here?** Additional methodology depth available under separate technical-disclosure NDA after initial evaluation. Architecture diagrams §4.5–§4.9 are designed to support code-walk cross-verification under NDA.

---

**END — CAS Harness Specification Sheet v2.0-EXTERNAL — 2026-06-04**
