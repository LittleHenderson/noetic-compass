# CAS Harness — Rollout Plan
## Internal Only — Not for External Distribution

**Version**: 1.5-INTERNAL · **Date**: 2026-05-21 · **Classification**: Internal, Founder + Authorized Collaborators Only
**Companion document**: `docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_5_INVESTOR_EXTERNAL_NDA_20260521.md` (the NDA-gated investor-facing capability spec; this rollout plan was deliberately extracted from it)

---

## Classification & Distribution

**This document is NOT to be shared with investors, customers, or strategic partners.** It is the internal companion to the investor-facing spec sheet. It contains forward-looking commitments, cost estimates, vendor-specific scale-up plans, and strategic sequencing that should not be exposed before contractual relationships exist.

The investor-facing spec sheet at `docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_5_INVESTOR_EXTERNAL_NDA_20260521.md` documents what CAS Harness *is* and *has demonstrated*. This document — the rollout plan — documents what CAS Harness *will do next and when*. The first is a capability statement. The second is a strategic plan. They are sent separately for a reason: NDA gates the spec sheet, and even the spec sheet does not reveal the rollout sequence.

---

## 1. Current Status (As of 2026-05-21)

Beyond what's captured in v1.5, the project has advanced through:

- **Stage 22 / 22.1 / 22.2** — CAS Harness ablation bench preregistration, gate-attribution measurements, diagnostic instrumentation contracts
- **Stage 22.4 / 22.5** — Diagnostic verifier runs and proxy attribution (Codex track)
- **Stage 23.A / 23.A.2 / 23.A.3** — Canonical 2D notation map foundation (157 + 12 Ω_* = 169 primitives across 17 kinds; Python + TypeScript adapter; React renderer; HTML visualization tool)
- **Stage 24A / 24B** — Sonar diagnostic + 40-Element formal NULL (static W_U projection insufficient for fine-axis token signatures)
- **Stage 25** — SAE feature pilot formal NULL (sparsity miss + causal removal NULL — standard SAE doesn't deliver clean monosemantic features at this layer)
- **Stage 26** — Component attribution formal PASS_BOUNDED (head-level necessity proven; 6 components drop probe 78% → 19%, matched controls p=0.0323)
- **Stage 27A** — Path patching formal PASS_BOUNDED (head-level sufficiency proven; 100% recovery fraction; matched random patch controls null)
- **Stage 27B** — Component-guided sonar (formal CUDA run completed)
- **Stage 27C / 27E** — Upstream targeting passes feeding 27F
- **Stage 27F** — **Sparse MLP-neuron-cover causal localization formal PASS** (32 of 3072 neurons; targeted ablation inverts margin from +6.37 to −6.28; matched random controls null; 112/112 examples; p = 1.93×10⁻³⁴; patch-back error 0.0)
- **Stage 27G** — **Bidirectional neuron-cover steering formal PASS** (target amplification +12.72 margin gain; matched random −0.08; target polarity-flip −25.15 margin drop, pushing margin below zero in 100% of rows; matched random polarity-flip −0.14; partner-cover amplification flips 25.9% of rows as cross-control)
- **Stage 27J** — Output-side attribution proven (Codex; landed during the 27F→27K sequence)
- **Stage 27K** — **Output-side component steering GREY** (combined carrier amplification + eraser suppression; mean likelihood-margin lift +0.5576; matched random −0.2927; delta over random +0.8502; row-consistency gate failed at p = 0.3444 / 30 of 56 wins; **eraser-suppression single-channel was strongest at +0.8223 mean lift / 69.6% positive share**). Commits: `236c5c5` prereg + `9ef9b29` results.
- **Stage 27N** — Cross-scale global-cover output-side steering on Pythia-1B: **NULL** (one global eraser cover too coarse to resolve cross-Drive distinctions at 1B scale). Established the methodology bound that informed 27O.
- **Stage 27O** — **Cross-scale drive-local output-side eraser steering on Pythia-1B: PASS** (one calibrated eraser cover *per* Foundation drive; mean likelihood-margin lift **+0.8386** vs matched random −0.1634; **54 of 56** held-out rows positive; sign-test **p = 2.22×10⁻¹⁴**). First clean behavioral-control PASS. Commits: `a786714` prereg + `ee5b047` results.
- **Stage 28** — **Cross-architecture replication of drive-local eraser steering: PASS on Qwen2.5-1.5B + Pythia-160M re-test (resolves 27K GREY).** Three model points across two architecture families now validate the protocol with no methodology adjustment:

  | Model | Architecture family | Mean lift | Wins | Sign-test p |
  |---|---|---:|:---:|---:|
  | Pythia-160M | Pythia | +0.85 | 181 / 245 | 2.0 × 10⁻¹⁴ |
  | Pythia-1B | Pythia | +0.84 | 54 / 56 | 2.2 × 10⁻¹⁴ |
  | **Qwen2.5-1.5B** | **Qwen** | **+0.90** | **56 / 56 unanimous** | **1.4 × 10⁻¹⁷** |

  The Qwen result is the strongest single result in the project record — produced on an architecture family different from the one the drive-local protocol was developed on. The Pythia-160M re-test under the drive-local protocol resolves the earlier Stage 27K GREY: that result was a methodology issue (combined channels + fixed gain), not a scale issue.

The empirical picture has clarified materially since v1.5:

- **Static W_U sonar empirically ruled out** for fine-axis per-class fingerprints (Stage 24B NULL)
- **Standard SAE empirically ruled out** for sparse causal CAS features at the tested layer (Stage 25 NULL)
- **Head-level component attribution empirically validated** with necessity AND sufficiency, formal anchor via ACBE Axiom 4.2
- **Sparse neuron-cover localization empirically validated** with full bidirectional control — ablate / amplify / polarity-flip / patch-back, all matched-control validated, all 112/112 at p < 10⁻³³. This is the finest causal granularity currently supported and the first formally PASS-grade neuron-level result in the project.
- **Output-side component steering PARTIAL on Pythia-160M (Stage 27K)** — directional, not row-consistent.
- **Cross-scale global cover NULL on Pythia-1B (Stage 27N)** — one global eraser cover too coarse to resolve cross-Drive distinctions at 1B.
- **Cross-scale DRIVE-LOCAL eraser steering PASS on Pythia-1B (Stage 27O)** — first clean behavioral-control PASS. Mean lift +0.8386, 54/56 rows, p = 2.22×10⁻¹⁴. The working methodology is one calibrated eraser cover *per* Foundation drive.
- **Cross-architecture replication of drive-local eraser steering PASS on Qwen2.5-1.5B (Stage 28)** — first cross-architecture out-of-family behavioral-control PASS. Mean lift +0.90, **56/56 unanimous**, p = 1.4×10⁻¹⁷. The Pythia-160M drive-local re-test in the same stage produced +0.85 / 181 of 245 / p = 2.0×10⁻¹⁴ — resolving the earlier Stage 27K GREY as a methodology issue, not a scale issue. The full NULL/PASS sequence (27K GREY → 27N NULL → 27O PASS → 28 cross-architecture PASS) is part of the auditable methodology — the bound was learned, not assumed. **Cross-architecture footprint for steering is now 2 of the 3 families that closed the readout claim** (Pythia + Qwen); OLMo-1B is the natural next gate to reach three-family parity.

The rollout below should be read against this updated foundation. Some Section 10 items from v1.5 (the rollout content extracted here) are now advanced, some are still relevant, and some have been refined by the recent NULL-then-PASS arc.

---

## 2. Near-Term Roadmap (Next 0–4 Weeks)

| Stage | Test | Cost | Expected Yield |
|---|---|---:|---|
| ~~Stage 27B~~ | ~~Component-guided sonar~~ | ~~Pod-active~~ | ~~Done~~ |
| ~~Stage 27F~~ | ~~Sparse MLP-neuron-cover causal localization~~ | ~~Done~~ | ~~PASS_BOUNDED_MLP_NEURON_COVERS, p < 10⁻³³~~ |
| ~~Stage 27G~~ | ~~Bidirectional neuron-cover steering (amplify + polarity-flip)~~ | ~~Done~~ | ~~PASS_BOUNDED_MLP_NEURON_COVER_STEERING~~ |
| ~~Stage 27H~~ | ~~CPL2 behavioral control test~~ | ~~~$10-30 GPU~~ | ~~Subsumed by Stage 27K's output-side steering test.~~ |
| ~~Stage 27J~~ | ~~Wire output-side attribution~~ | ~~Done~~ | ~~Stage 27J output-side attribution proven (per Codex 2026-05-21 PM)~~ |
| ~~Stage 27K~~ | ~~Output-side component steering (combined carrier amplification + eraser suppression)~~ | ~~Done~~ | ~~GREY: directional evidence (+0.5576 mean lift, delta over random +0.8502), row-consistency p = 0.3444 failed. Eraser-suppression channel strongest at +0.8223 / 69.6%.~~ |
| ~~Stage 27L~~ | ~~Calibrated per-class steering on Pythia-160M~~ | ~~Done~~ | ~~Subsumed; drive-local methodology validated directly at cross-scale (Stage 27O)~~ |
| ~~Stage 27N~~ | ~~Global-cover cross-scale output-side steering on Pythia-1B~~ | ~~Done~~ | ~~NULL — global cover too coarse at 1B; informed Stage 27O methodology~~ |
| ~~Stage 27O~~ | ~~Drive-local cross-scale output-side eraser steering on Pythia-1B~~ | ~~Done~~ | ~~PASS — +0.8386 mean lift, 54/56, p = 2.22×10⁻¹⁴~~ |
| **Stage 27P** | **Wire drive-local eraser-cover support + steering signal into Evidence Packet + Verification Stack** | **$0 GPU — engineering** | **Product move. Per-inspection field: "drive-local cover support: present / weak / conflicted"; per-inspection steering capability surfaced in Evidence Packet. Audit-grade output upgrade.** |
| ~~Stage 28~~ | ~~Cross-architecture replication of Stage 27O drive-local eraser steering~~ | ~~Done~~ | ~~PASS on Qwen2.5-1.5B (56/56, p = 1.4×10⁻¹⁷) + Pythia-160M re-test resolves 27K. OLMo replication pending separately.~~ |
| **Stage 28b** | **OLMo-1B drive-local eraser steering replication — brings steering claim to three-family parity with readout claim (Pythia + OLMo + Qwen)** | **~$20–50 GPU** | **Now the highest-leverage open empirical extension. Methodology is unchanged from Stage 28 (no new design risk); the protocol replicates without adjustment on three model points across two families already. OLMo would close the symmetric three-family footprint.** |
| Stage 27I | Cross-axis: sparse-cover localization for 40 Elements + 10 Noetics | ~$20–40 GPU | Tests whether cover methodology generalizes beyond Foundations |
| Stage 9.1 | 40-Element ablation + Domain × Noetic factorization | ~30 min A6000 | Tests whether 40 Elements is primary axis or Domain+Noetic composition |
| Stage 17 option A | Llama-7B or OLMo-7B or Qwen2.5-7B scale-up | ~$30–100 GPU | Tests scale beyond 2.8B; would close the "scale" bound to 7B |
| Stage 17 option B | Qwen2.5 in-family scale curve (0.5B / 1.5B / 7B) | ~$15–40 GPU | Tests training-data-dependent saturation hypothesis within one family |
| Stage 17 option C | Hidden-content detection — pre-register + validate the η₁/η₂ two-bridge | ~$5 GPU + corpus work | Promotes hidden-content tier from prototype to validated |
| Stage 18 | Modular Harness interface design + Evidence Packet schema v2 | $0 GPU | Sets up trillion-scale architecture without code refactor |
| Stage 23.A.1 | Dashboard adapter migration to canonical 2D notation map (complete) | $0 | Validates foundation end-to-end (shipped: GraphView + Notation2DView) |
| **Product packaging** | Subdomain landing page (`cas-harness.noeticcompass.com` or similar) + one-pager + customer-facing demo flow | $0 — design only | First external surface; required before any paid pilot |

**Sequencing priority** (updated 2026-05-22 after Stage 28 cross-architecture PASS on Qwen):

1. **Stage 28b** — OLMo-1B drive-local eraser steering replication. Brings steering to three-family parity with readout claim (Pythia + OLMo + Qwen). Methodology already proven across 3 model points and 2 families with no adjustment; OLMo is the symmetric extension. ~$20–50 GPU.
2. **Stage 27P** — wire drive-local cover + steering signal into Evidence Packet + Verification Stack. $0 GPU, product move. Ships regardless of Stage 28b outcome.
3. **Update investor spec sheet** ✓ (done — Stage 27O + 28 folded in; behavioral-control LICENSED at two families, three-family parity flagged as next gate)
4. Product packaging — subdomain landing + one-pager finalization + demo flow
5. Stage 27I — extend cover methodology to 40 Elements / Noetics axes
6. THEN: Stage 17 scale-up (7B+) OR Stage 17C hidden-content validation, depending on first paying conversation

---

## 3. Mid-Term Roadmap (1–6 Months)

| Initiative | Description | Dependencies |
|---|---|---|
| **Hosted MVP** | Upload + probe-training + Evidence Packet inspection loop | Subdomain shipped, payment/billing wired |
| **Multi-architecture coverage** | Validated probes for Llama, OLMo, Qwen, Mistral, Phi, Gemma | Stage 28 cross-model replication first |
| **Hidden-content detection at production tier** | Move two-bridge from prototype to validated | Stage 17C validation |
| **Surface-text steering at 1B+ scale** | Replicate CPL3/CPL4 on larger models where sampling noise is lower | Stage 17A scale-up |
| **Mode 7 / Living Thought Atlas integration** | Trace surface for live inspection | Component-guided sonar + path-patching surfaces |
| **Modular Multi-Harness orchestration** | Foundation for trillion-scale fan-out architecture | Stage 18 interface design |
| **First paying pilot customer** | Anchor customer in compliance-adjacent vertical | Subdomain + Hosted MVP + IP attorney clearance |
| **SAE escalation (optional research escalation)** | Larger dictionary, tuned sparsity, possibly different layer | Only if a customer specifically requests feature-level evidence beyond head-level component attribution |
| **Sonar research escalation (per saved memory)** | Active-sonar propagation tracking at head outputs | Optional research escalation, not launch-blocking |

---

## 4. Long-Term Roadmap (6–24 Months)

| Initiative | Description | Strategic Bet |
|---|---|---|
| **Regulator-facing pilot** | Compliance product for finance / hiring / healthcare / defense — one anchor customer | Highest-margin vertical; audit-grade methodology lands hardest here |
| **Self-hosted toolkit** | On-prem deployment for regulated industries | Required for some compliance contexts |
| **Multi-vendor coverage** | Validated probes for all major open-weight families | Defends cross-architecture claim against any single-vendor pushback |
| **Public Glass House platform** | After IP attorney clearance and customer track record | Brand differentiation through methodological transparency |
| **Joint product line with CAS Native** | Inspect the user's model (Harness) AND offer transparent-by-construction alternative (Native) | Two-product portfolio; cross-sell story |
| **Standards body engagement** | TMLR / NeurIPS interpretability venues; AI Safety Institute engagement | Academic credibility + government touchpoints |
| **Sonar-track + SAE-track research escalations** | Feature-level / circuit-level methodological extensions (per saved research memory) | Activated post-product, premium research gates |

---

## 5. Trillion-Scale (Architectural — Multi-Harness Composition as the Load-Bearing Direction)

Trillion-parameter customer deployments will require multiple CAS Harnesses running in parallel. **Multi-Harness Composition is the load-bearing direction** — the other parallelization shapes are supplementary.

### 5.1 Parallelization Shapes

- **Shape B — Axis-specialized harnesses (primary).** Each CAS axis (Noetic, Drive × Register, Domain Descent, Meta-Logic, Production Semantics, Stability, Lacunarity) gets its own harness, each at its optimal depth. **This is the load-bearing direction** because it maps directly onto the CAS Working Memory tensor.
- **Shape A — Parallel across layer regions** (early / mid / late) — naturally falls out of Shape B since different axes peak at different depths
- **Shape C — Parallel across domain specializations** (medical, legal, financial, safety) — productization layer on top of B
- **Shape D — Tiered pipeline** for real-time inference latency (fast-flag → deep-probe → trace-audit)
- **Shape E — Ensemble robustness voting** (multiple variants of each axis-harness)
- **Shape F — Per-MoE-expert harnesses** for Mixture-of-Experts trillion-scale models

### 5.2 Architectural Prep Work to Begin Now

1. **Modular Harness interface** — every existing probe should expose a standardized input/output contract so the coordinator can fan out without refactoring
2. **Schema-extensible Evidence Packet** — per-harness contributions need to carry their own `harness_id`, `harness_version`, and per-axis evidence with the coordinator's merged verdict above
3. **Coordinator prototype** — a thin merging layer that takes outputs from any subset of the existing axis-probes and emits a composite Evidence Packet

These three engineering items are low-cost (no significant new GPU spend; each composed harness is already trained from prior stages). Multi-Harness Composition is the architectural step where the framework's design vision (the Working Memory tensor) becomes the deployed product surface.

---

## 6. Pricing & Revenue (Internal Working Estimates)

*(Placeholder — to be filled in with founder during pricing strategy session.)*

| Tier | Audience | Target Pricing | Validation Trigger |
|---|---|---|---|
| Hosted Trial | Single-model audit, 30-day | TBD | Stage 28 cross-model replication |
| Hosted Standard | Multi-model, ongoing audit | TBD | First three referenceable customers |
| Hosted Regulator-Grade | High-precision mode + compliance reporting | TBD | First regulator pilot |
| Self-Hosted Enterprise | On-prem toolkit + support | TBD | First on-prem customer ask |
| Bring-Your-Endpoint | API-only, customer infra hosts model | TBD | First customer requesting endpoint-only |

---

## 7. IP Filing Sequence

The investor-facing spec sheet lists 13 candidate IP filings. The internal sequencing of those filings:

| Priority | Filing | Trigger |
|---|---|---|
| 1 | η → ε bridge applied to foreign open-weight models | Already in process per IP attorney |
| 2 | Evidence Packet schema + authenticated delivery surface | Filed alongside #1 (operational artifact) |
| 3 | Cross-architecture probe-transfer methodology | **Triggered — Stage 28 (Qwen2.5-1.5B + Pythia-160M re-test) closes the cross-architecture footprint on the steering side; readout claim already validated cross-family.** Ready to file. |
| 4 | Component-level (head-level) necessity + sufficiency testing methodology | **Triggered — Stage 28 confirms protocol replicates without adjustment across two architecture families (Pythia + Qwen).** Ready to file. |
| 4b | **Sparse MLP-neuron-cover causal localization methodology** — targeted cover identification + ablation + amplification + polarity-flip + matched-control validation + bit-exact patch-back recovery (Stages 27F + 27G) | **Time-sensitive — file immediately after IP attorney consultation.** This is the finest-granularity causal localization claim in the project; differentiating against any competing interpretability product. |
| 4c | **Drive-local output-side eraser-channel steering methodology** — per-Foundation-drive calibrated eraser cover applied at output side; **cross-architecture validated across two families** (Pythia-160M + Pythia-1B + Qwen2.5-1.5B; combined wins 235/280, three independent sign-test confirmations). Includes the methodology-bound discovery that global cover is too coarse at 1B scale (Stage 27N NULL → Stage 27O drive-local PASS), and the cross-architecture replication confirming the protocol is not Pythia-specific (Stage 28 Qwen 56/56 unanimous, p = 1.4×10⁻¹⁷). | **Most time-sensitive of the open filings — now ready to file.** First clean behavioral-control claim with cross-architecture footprint. Differentiates against any interpretability tool that reads but does not steer. Pre-registered NULL/PASS sequence + three-replication footprint is part of the IP package. File immediately after IP attorney consultation; do not wait on Stage 28b OLMo replication (that strengthens scope, not the core claim). |
| 5 | CAS Verification Stack — runtime-safe accept/suppress | Already validated, ready to file |
| 6 | Verification Mode Selector + factor-consistent verifier | Already validated, ready to file |
| 7 | Generation Readiness Gate orchestrating policy methodology | Already validated, ready to file |
| 8 | Multi-layer trace + readout-position blind-spot detection | Already validated, ready to file |
| 9 | Framework-predictive preflight diagnostic methodology | Already demonstrated 4× |
| 10 | Two-bridge hidden-content detection methodology | After Stage 17C validation |
| 11 | Weight-geometry alignment methodology | Already validated, ready to file |
| 12 | Multi-Harness Composition architecture | After Stage 18 modular interface ships |
| 13 | Bi-agent audit-cycle methodology | After operational track record |

---

## 8. Strategic Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Anthropic, OpenAI, or others publish a competing interpretability product | Medium-High | High | Cross-architecture moat (CAS Harness works on competitor models; competitor tools rarely do); audit-grade methodology discipline; pre-registered evidence |
| Open-weight models become rare (closed-API consolidation) | Low-Medium | High | Pivot to bring-your-endpoint deployment; emphasize regulator-facing customers who'll require open weights regardless |
| SAE-at-scale work succeeds before our component attribution claim is widely known | Medium | Medium-High | Stage 28 cross-model replication closes the time gap; file IP on component-level necessity + sufficiency methodology now |
| 7B+ scale-up fails (effects saturate before frontier) | Low-Medium | Medium | Reframe as scale-bounded product; multi-architecture coverage substitutes for scale |
| Customer wants neuron-level evidence we can't yet provide | ~~Medium~~ Low (post-27F/G) | Medium | **Now substantially mitigated** — sparse-cover causal localization with bidirectional control is validated. SAE escalation remains as paid follow-on for true monosemantic features if customer specifically requests. |
| Hidden-content detection prototype doesn't promote to validated | Low-Medium | Low (still have core product) | Treat as upside, not load-bearing |

---

## 9. Refresh Triggers for This Plan

This rollout plan refreshes when:

- Stage 27B / Stage 28 results land
- First paying customer signs
- IP attorney issues filing recommendations
- A scale-up experiment (Stage 17) closes
- Hidden-content detection validates or NULLs
- Multi-Harness coordinator prototype ships
- Material framework or methodology revision lands

Next mandatory review: after Stage 28 cross-model replication, OR after first paying-customer conversation, whichever lands first.

---

## 10. Document Coupling

| Document | Audience | What it documents |
|---|---|---|
| `docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_5_INVESTOR_EXTERNAL_NDA_20260521.md` | Investors / strategic partners (NDA-gated) | Capabilities, validated outcomes, claim boundaries |
| **`research/cas_probe/CAS_HARNESS_ROLLOUT_PLAN_v1_5_INTERNAL_20260521.md`** (this document) | **Founder + authorized internal collaborators** | **Forward-looking commitments, sequencing, costs** |
| `research/cas_probe/CAS_HARNESS_SPEC_SHEET_v1_5_20260519.md` | Founder + authorized internal collaborators | Full internal v1.5 spec (the unredacted source for the investor version) |
| Future: `CAS_HARNESS_NDA_template.md` | To be signed before investor document is sent | NDA boilerplate (separate from this) |

The investor spec sheet at `docs/marketing/` is the only document authorized for distribution under executed NDA. This rollout plan stays internal regardless of NDA status.

---

*End of internal rollout plan. Confidential, internal-only, 2026-05-21.*
