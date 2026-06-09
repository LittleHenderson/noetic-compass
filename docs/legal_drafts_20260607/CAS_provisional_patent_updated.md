> **DRAFT — must be reviewed by a registered patent attorney/agent before filing; not legal advice.**
> **Public disclosure of these contents may start statutory bars (e.g., the U.S. one-year grace period and immediate foreign-rights loss). KEEP CONFIDENTIAL.** Do not post, present, demo to non-NDA parties, or publish any part of this document until counsel has cleared it and the filing strategy is set.
>
> **Supports US Provisional Application No. 64/037,173, filed 04/13/2026 (Utility—Provisional); this consolidated specification supports the non-provisional/utility conversion.**
>
> **Provisional application no.:** **64/037,173** (Utility — Provisional). Confirmation No. **1346**; Patent Center No. **75259715**; receipt/filing date **04/13/2026** (12:15:55 AM ET); status: received by USPTO. The provisional is **already filed**; the next milestone is a non-provisional (utility) or PCT claiming priority to 64/037,173 by **~04/13/2027**.
>
> **Serial-number note (read this):** Earlier internal drafts flagged "#64/037,173" as suspect on the assumption that U.S. **provisional** applications carry series code **63**. That assumption was outdated. U.S. provisional series codes advance over time (60 → 61 → 62 → 63 → **64**); by 2026 provisionals are assigned **series 64**. The USPTO *Electronic Acknowledgement Receipt* (founder-provided 2026-06-08) confirms **64/037,173 is the REAL, valid provisional** — it is NOT a placeholder and must not be treated as suspect anywhere. The canonical record is `docs/legal_drafts_20260607/PATENT_FILING_FACTS_CONFIRMED.md`. **Attorney action:** confirm filing scope at the utility conversion and docket the **04/13/2027** priority-preservation deadline.

---

# CONSOLIDATED PROVISIONAL PATENT APPLICATION (DRAFT)
## CAS Harness — Cognitive-Structure Auditing, Conditioning, and Evidence-Anchoring for Open-Weight Language Models

**Applicant / Inventor:** Little Henderson (full legal name and residence to be stated on the cover sheet — Form SB/16).
**Prepared:** 2026-06-08 (consolidation of seven legacy mechanism drafts A–G, reconciled to the current build).
**Framework version of record:** Cognitive Architecture System (CAS) **v7.7**.
**Status:** First-pass consolidated draft for attorney review. Bracketed **[ATTORNEY]** / **[VERIFY]** markers flag every point needing legal judgment or a value pulled from the inventor's own records/code before filing.

---

## 0. How this document was produced and what changed (orientation for the attorney)

This draft consolidates and **corrects** three legacy AI-generated artifacts:
- `CAS_Provisional_Drafts_All_Mechanisms.pdf` (seven separate "Provisional A–G" mechanism drafts),
- `CAS_Self_Filing_Provisional_Guide.pdf`,
- `CAS_Provisional_Flowcharts.pdf`.

The legacy drafts were written against **old and thin** information. The product has since matured and — importantly — its honest claim boundaries have been tightened in a deliberate **anti-overclaim correction pass** (CAS Harness spec-sheet v2.0 → v2.1, 2026-06-04, and the compliance disclosure draft of 2026-06-04). This consolidated draft is reconciled to that corrected state. The substantive changes from the legacy drafts are itemized in **Appendix A (Change Log vs. Source)** at the end. The single most important corrections:

1. The **Evidence Packet** is now the central deliverable, with a fixed verdict vocabulary — **`ACCEPT` / `FLAG_FOR_HUMAN_REVIEW` / `SUPPRESS`** — **six** named proof chips, and full **input → CAS → evidence traceability**.
2. **WORM anchoring is tamper-EVIDENT, not immutable.** It uses **Amazon S3 Object Lock in GOVERNANCE mode** with an **~30-day rolling retention window**; it is **operator-overridable** by a principal holding `s3:BypassGovernanceRetention`. The guarantee is *tamper-evidence on the next verification call*, **not** physical immutability, permanence, or `COMPLIANCE`-mode. The words "immutable," "permanent," "write-once-read-many (as an absolute)," "court-admissible," "certified," "compliant," and "guaranteed" are **prohibited** in this filing.
3. A new **Fleet** architecture (sharded large-model auditing with per-worker sub-harnesses, fragment-hash anti-misattribution, and a conservative-default aggregation gate) is described as its own mechanism.
4. No **`ACCEPT`** verdict currently stands in the project record; per-customer production `ACCEPT` is not asserted as having been achieved. Claims are written to cover the *mechanism*, not to assert a result that has not occurred.

**Why one consolidated provisional (vs. seven):** combining keeps a single priority date across interdependent mechanisms that share the same pipeline, integrity chain, and Evidence Packet. **[ATTORNEY]** Decide filing granularity: this single consolidated provisional, OR the legacy A–G split (cheaper to prune at conversion), OR a hybrid. Tradeoffs noted in the filing guide.

**New-matter caveat (priority scope).** Provisional 64/037,173 was filed **04/13/2026**; it protects only what it disclosed on that date. CAS framework additions made *after* 04/13/2026 — **v7.5 Register, v7.6 Production Semantics, v7.7 Operator Discipline, and the Fleet / 300B sharded-audit architecture to the extent it post-dates the filing** — are **not** retroactively covered by the original provisional. This consolidated specification is written to support the non-provisional/utility conversion, where such matter can be brought in; alternatively, post-filing new matter can be protected by its own provisional. **[ATTORNEY]** Confirm with counsel which post-04/13/2026 material rides on the utility filing vs. a fresh provisional, before public disclosure.

---

## 1. Title of the Invention

**Method and System for Auditing, Causally Localizing, Conditioning, and Tamper-Evidently Anchoring the Cognitive Structure of Open-Weight Language Models, with Reproducible Evidence Packets and Sharded-Fleet Execution.**

*(Alternative short title for the cover sheet, [ATTORNEY] to choose: "Cognitive-Structure Audit System for Language Models with Tamper-Evident Evidence Packets.")*

---

## 2. Field of the Invention

The invention relates to machine learning, and more specifically to **interpretability, runtime governance, and auditable evidence generation for pretrained transformer language models**. It concerns reading typed cognitive-structure labels from a model's hidden states; testing whether that structure is causally load-bearing for the model's behavior; conditioning the model's next-token output distribution by realizing detected structure as ordinary input text without modifying weights; deciding at inference time whether to accept, flag, or suppress an output using signals computable without ground-truth labels; packaging the whole inspection as a reproducible, schema-validated, cryptographically chained, externally anchored Evidence Packet; and executing the audit across a fleet of workers when the target model is too large for one machine.

---

## 3. Background of the Invention

### 3.1 The problem

Deployed and pre-deployment language models are increasingly subject to safety, procurement, and regulatory scrutiny, but existing tooling leaves several gaps simultaneously:

- **Reading structure ≠ acting on it.** Linear probes can classify a model's hidden states, but stop at classification — they do not feed the reading back to steer the same model, and they do not establish that the read structure *causes* anything.
- **Steering is invasive and unauditable.** Fine-tuning and activation/representation editing can change behavior, but require weight access or direct intervention in the activation stream, are model-specific, and produce no portable record a third party can check.
- **Runtime gating needs an oracle it does not have.** To accept or suppress an output at serving time, a system must decide *without* the ground-truth answer (which is unavailable at inference). Softmax confidence is poorly calibrated and gives no auditable reason; trained verifiers assume labeled data or distributional stability.
- **Interpretability output is not evidence.** Probe results and notebooks are ad hoc and non-reproducible: a reviewer cannot confirm a stated result corresponds to a specific run, reproduce it bit-for-bit, or verify it has not been altered. Regulators and partners need a **structured, versioned, independently verifiable artifact**.
- **A low probe score is ambiguous.** When a probe fails to recover a structure, two very different causes are confounded — the model may not represent the structure (model-side weakness), or the readout may be reading the wrong layer/position (readout-side weakness). Standard single-layer probing cannot tell these apart, so it cannot answer the question a regulator will ask: *"how do you know your tool can even read this model?"*
- **Correlation is not causation.** Showing a structure is *readable* does not show any specific component *causes* the behavior. Establishing causation requires necessity (removing the component breaks the readout), sufficiency (restoring only it recovers the readout), and matched controls to rule out generic disruption.
- **Frontier-scale models do not fit on one worker.** Auditing a model whose parameters are sharded across many machines raises a misattribution risk (which worker's tensors produced which evidence?) and an aggregation-policy question (when may a sharded audit claim acceptance?) that single-machine tooling does not address.

### 3.2 Prior approaches and their limits

- **Linear / logistic probes:** classify activations; do not condition generation, do not establish causation. *Correlational only.*
- **Activation steering / representation engineering:** edits the activation stream directly — invasive, per-layer hooks, model-specific, hard to audit.
- **Fine-tuning / LoRA:** modifies weights, requires training, changes the model permanently.
- **Prompt engineering:** manual; not derived from the model's own internal state.
- **Softmax confidence / temperature:** uncalibrated; no auditable reason for a decision.
- **Trained moderation / verifier models:** add parameters that can drift and require retraining; assume labeled data at the decision point.
- **Free-text reports / notebooks; generic logging frameworks:** not schema-validated, not reproducible, not authenticated; produce no portable, third-party-verifiable customer artifact.
- **Best-layer selection alone:** picks one layer but does not diagnose why other layers fail; cannot separate model-side from readout-side weakness.
- **Naïve ablation without matched controls:** disruption may be generic rather than specific.
- **Sparse-autoencoder (SAE) feature discovery:** in the inventor's experiments did not, by itself, yield a sparse *causal* feature basis at the relevant layer **[VERIFY against inventor's SAE notes]**.
- **Model self-reports / introspection prompts:** a different, often ungrounded modality; the model may misstate its own internal computation.

### 3.3 The CAS framework context (secular, technical description)

The methods operate over a fixed, typed cognitive ontology — the **Cognitive Architecture System (CAS), version 7.7** — used purely as the label space and grammar for the structures being read, tested, and realized. In secular technical terms relevant to this filing, CAS v7.7 supplies:

- **10 Noetics** (`^0`–`^9`): typed structural-dynamic primitives.
- **4 Processing Domains** (P, C, E, O) under a fixed precedence order, giving **40 Cognitive States** (10 × 4).
- **7 Drives** (F1–F7) and 28 domain-specific drives.
- **4 Registers** (T, A, f, E): an operational-character axis, orthogonal to the above.
- **5 generative operations**, an **admissibility relation** governing which operator applications are valid, and a **compiler/grammar** that validates expressions.
- Derived diagnostics used by the mechanisms below: a **7-axis inversion scan**, a **prerequisite/RPM** satisfaction walk, and a **lacunarity** measure.

For this patent, CAS is the **typed label space and validating grammar**. The mechanisms claimed are general over (a) the choice of cognitive ontology and (b) the family of decoder-only transformer being audited; CAS v7.7 is the worked, enabling embodiment. The claims are drafted so that the *novel machinery* — the read→realize→condition loop, the non-oracle accept/flag/suppress decision, the six-chip reproducible Evidence Packet, the tamper-evident anchoring discipline, the blind-spot disambiguation, the matched-control causal localization, and the sharded-fleet execution with fragment-hash anti-misattribution — does not depend on any particular metaphysical or cultural interpretation of the ontology. *(No esoteric or heritage framing appears in this filing by design.)*

---

## 4. Summary of the Invention

The invention is an end-to-end system and set of methods that take an open-weight transformer language model as an **audit target** and produce a **reproducible, tamper-evident Evidence Packet** characterizing the cognitive structure inside the model and the trustworthiness of a given output. In broad terms it comprises some or all of the following cooperating mechanisms, which may be used together or independently:

- **(A) η→ε conditioning bridge** — a two-pass, weight-frozen method that (1) reads a typed cognitive-structure label from hidden states via a trained embedding map η, (2) realizes that label as a natural-language prefix via a realization map ε, prepends it to the original prompt, and (3) measures the shift in the model's next-token likelihood on a second forward pass. Relies on the section-retraction identity (ε∘η = id; η∘ε ≠ id) and on the architectural fact that ordinary prefix tokens are attended to by every later position — so conditioning needs no special hook.
- **(B) Non-oracle runtime verification stack** — accepts or suppresses an output using only internal-state signals computable *without* the ground-truth answer (stability / agreement / conflict / drift / ensemble-agreement), attaches a human-readable reason to every suppression, and uses ground-truth labels **only offline** to calibrate thresholds. Selectable operating modes (high-precision / balanced / max-coverage-triage).
- **(C) Reproducible Evidence Packet + authenticated delivery** — a versioned, schema-validated structured artifact carrying a verdict (`ACCEPT` / `FLAG_FOR_HUMAN_REVIEW` / `SUPPRESS`), **six proof chips**, the full input→CAS→output trace, provenance, cryptographic hashes, and a trace identifier enabling reproducible regeneration; delivered over an authenticated channel; independently re-verifiable via a multi-check verify endpoint; and **tamper-evidently anchored** (Mechanism F).
- **(D) Multi-layer blind-spot disambiguation** — reads probe confidence across all layers to classify a trajectory's quality and applies a disambiguation rule that separates **model-side** weakness (uniformly low across layers) from **readout-position** weakness (high at some layers but missed by the default readout), yielding an auditable statement about when the tool cannot read a given model/class.
- **(E) Matched-control causal localization** — localizes the causal substrate of a structural readout at attention-head granularity and at sparse-MLP-neuron-cover granularity, proving it with necessity (ablate → readout drops) + sufficiency (path-patch → recovers) + bidirectional control (ablate inverts margin / amplify grows margin / polarity-flip reverses classification), each against matched controls, with bit-exact patch-back. Bounded to sparse-cover granularity — explicitly **not** a single-neuron monosemanticity claim.
- **(F) Tamper-evident integrity chain + WORM anchoring** — disk persistence, an append-only hash chain, a five-check verify endpoint, a three-state trust UI, and external anchoring to S3 Object Lock in **GOVERNANCE mode** (~30-day rolling retention, mechanically re-checked via `HeadObject`), with a gate that downgrades an `ACCEPT` to `FLAG_FOR_HUMAN_REVIEW` whenever any of the three anchor proofs is missing.
- **(G) Generation Readiness Gate** — an opt-in, non-mutating, zero-learnable-parameter policy module that maps combined structural signals to one of four graded actions (allow / caveat / constrain / suppress) with a full audit trail, leaving the model's forward path unchanged.
- **(H) Sharded-Fleet execution** — for a target model too large for one worker: a planner shards the model and assigns layer-slice jobs to probe workers, each running a local sub-harness that emits per-slice proof chips and **commits a fragment SHA-256 of its raw activation tensor**; an aggregator validates the fragment hashes (anti-misattribution), stitches the multi-layer trace, coordinates cross-worker ablation, and a fleet-topology gate applies a **conservative-default** policy (any worker not-`ACCEPT`, any missing fragment hash, or any absent worker → fleet not-`ACCEPT`) before the unified packet passes the same anchoring gate. Raw activations never cross the wire.
- **(I) Two-bridge hidden-content detector (PROTOTYPE)** — compares an internal-hidden-state CAS profile (η₁) against a CAS profile re-read from the emitted text (η₂) and flags a typed-class divergence as content the model represents internally but does not emit. **Disclosed as prototype tier; no confirmatory gate closed.**

A key shared property across (A)–(I) is **traceability**: every claim surfaced to a user is anchored to the exact field, file, hash, or measurement it came from, and the evidence type of each claim is labeled (deterministic compiler trace vs. source-copy evidence vs. derived trace vs. neural-attribution estimate).

---

## 5. Detailed Description

> **Reference-numeral convention.** Each mechanism's flowchart numbers its steps **10, 12, 14, …**; those numerals are used below and re-described in the companion document `CAS_provisional_flowcharts_described.md`. **[ATTORNEY/ILLUSTRATOR]** must attach formal drawings keyed to these numerals before filing; the legacy figures are stylistically degraded and several labels are unreadable.
>
> **Enablement note.** A provisional protects only what it actually teaches. Every **[VERIFY]** below marks a value (layer index, probe rank, threshold, schema field count, effect size) that must be replaced with the **real value from the inventor's code/records** so the disclosure is enabling. Functional-level description of trade-secret internals (exact probe construction, fixture design) is acceptable here; undescribed specifics do not get the priority date.

### 5.A Mechanism A — η→ε Conditioning Bridge (weight-frozen read→realize→condition loop)

**(A.0) What it does.** A two-pass method that (1) reads a typed cognitive-structure label from a foreign open-weight transformer's hidden states using a trained map η, then (2) realizes that label as a natural-language prefix prepended to the original prompt, so that on a second forward pass the model's next-token probability distribution shifts measurably toward the identified structure — with **no modification to the model's weights** and **no intervention in the activation stream during generation**.

**(A.1) How it works** (numerals match Figure A1):

- **(10) Hidden-state capture.** Run the original prompt through the model; capture hidden-state activations at a layer in the middle band of network depth — in one embodiment ~**[VERIFY: 39–50%]** of total depth per a layer-selection rule — at **[VERIFY: which token position(s) — focus token / final token / mean-pooled]**.
- **(12) Embedding map η.** Apply a trained linear/logistic classifier (a "probe") to the captured activations to produce a typed structural label drawn from a fixed ontology (e.g., a 28-class Foundation label, a 40-class Element label, or a 10-class Noetic label). Trained per-model on labeled activation examples; in one embodiment a balanced-logistic probe **[VERIFY: rank/regularization/preprocessing]**.
- **(14) Realization map ε.** Pass the typed label to a template/lookup realization layer that emits a short, readable natural-language prefix expressing the labeled structure. In one embodiment each class maps to a canonical gloss phrase **[VERIFY: template construction]**.
- **(16) Prefix concatenation.** Prepend the realized prefix to the original prompt.
- **(18) Second forward pass.** Run prefix+prompt through the **same** model.
- **(20) Likelihood scoring.** Measure the log-likelihood shift of the target structural class between the prefixed and unprefixed passes; in one embodiment also against (b) a probe-readable prefix, (c) an involution-partner prefix, and (d) a raw-notation prefix as a **null control** (the raw-notation Δ should be ≈ 0; a non-zero raw Δ would indicate symbol recognition rather than realization).

**(A.2) Why it relies on the section-retraction identity.** ε∘η = id (realizing then re-reading recovers the label) while η∘ε ≠ id (re-embedding after realization may lose information). Because the realized prefix is **ordinary input tokens**, the model's self-attention attends to it from every subsequent position by architectural construction — the conditioning requires no special hook. This is the property a regulator can see: the conditioning is a **visible text prefix**, not a hidden activation edit, and is therefore auditable.

**(A.3) Why prior methods don't do it.** Probes classify but never feed the result back. Activation steering acts on the stream invasively and per-layer. Fine-tuning changes weights. None close the read→realize→condition loop using only ordinary prefix tokens — which is what makes this method non-invasive, model-agnostic across decoder-only transformers, and auditable.

**(A.4) Variations.** Capture at any mid-depth layer; single vs. multiple layers; single vs. multi-position capture. η as linear, logistic, low-rank, or shallow MLP probe. ε as fixed gloss, learned template, or retrieval-based phrasing. Ontology as 10-class, 28-class, 40-class, or other typed taxonomy. Scoring as log-likelihood, margin over a partner class, or rank shift. Applicable across decoder-only families (e.g., Pythia/GPT-NeoX, OLMo, Qwen, and others).

**(A.5) Example results (illustration of depth; replace with records).** Cross-family next-token likelihood conditioning across multiple model points; in one set of runs Foundation-axis effects up to **[VERIFY: +0.7960, p = 2.92×10⁻¹²]**, with raw-notation control near zero, indicating the effect is ε-realization (readable prefix) rather than symbol recognition. **[VERIFY every number against canonical result files.]**

### 5.B Mechanism B — Non-Oracle Runtime Verification Stack

**(B.0) What it does.** A runtime decision layer that accepts or suppresses each model output using **only** non-oracle internal-state signals available at inference, attaches a reason to every suppression, and uses ground-truth labels **only during offline validation** (to calibrate thresholds), never at inference.

**(B.1) How it works** (Figure B1):

- **(10) Signal extraction (non-oracle).** Compute a set of signals characterizing the output's stability — e.g., **stable / conflicted / uncertain / drifting / ensemble-agreement** — over selected readouts (in one embodiment across focus-token, final-token, and mean-over-sequence readouts with a **2-of-3 ensemble-agreement** requirement) **[VERIFY exact signal list and ensemble rule]**.
- **(12) Decision function.** Map the signal vector to one of {accept, suppress} via **pre-registered thresholds calibrated offline against gold labels**. In one embodiment, accept only high/medium-stability cases; suppress ensemble disagreement, uncertainty, conflict, or unstable traces.
- **(14) Reason attachment.** On suppression, emit the triggering signal(s) as a human-readable reason code.
- **(16) Mode parameterization.** Thresholds selectable among operating modes — **HIGH_PRECISION** (final component; highest precision, lower coverage), **BALANCED** (factor-consistent component; default), **MAX_COVERAGE_TRIAGE** (ensemble-only; triage, not a final high-confidence claim). Coverage is surfaced honestly; a row outside calibrated coverage becomes `FLAG_FOR_HUMAN_REVIEW` or `SUPPRESS`, never a low-confidence `ACCEPT`.

**(B.2) Why prior methods don't do it.** This decides at inference using only signals computable without the answer while remaining auditable (every suppression carries a reason), and it separates the role of gold labels (calibration-time only) from the inference-time decision — which is what lets it run safely in production without an oracle.

**(B.3) Variations.** Any combination of stability/consistency/agreement signals; decision function as threshold rule, small calibrated classifier, or ensemble vote; reason granularity per-signal or aggregated.

**(B.4) Example results (replace with records).** In one offline audit-clean run on **[VERIFY: 4,200]** rows: accept rate ~**[VERIFY: 87.6%]**, accepted accuracy ~**[VERIFY: 99.78%]**, silent-accepted-error ~**[VERIFY: 0.22%]**, suppression ~**[VERIFY: 12.4%]** on conflicted/unstable cases. Decisions independently auditable, each suppression carrying a reason. **[ATTORNEY: these are offline-validation numbers; do not characterize them as production or customer results.]**

### 5.C Mechanism C — Reproducible Evidence Packet + Authenticated Delivery (the deliverable)

**(C.0) What it does.** Emits, per inspection, a **versioned, schema-validated Evidence Packet** that carries a verdict, six proof chips, the full input→CAS→output trace, provenance, cryptographic hashes, and a trace identifier; validates it against a fixed schema; renders it human-readable; makes it reproducible via the trace identifier; and delivers it over an authenticated channel for independent third-party verification.

**(C.1) How it works** (Figure C1):

- **(10) Packet assembly.** Collect inspection inputs, the CAS expression used, the output, detected labels, causal-test results, the verdict, provenance, hashes, and a `trace_id` into a fixed schema (schema versioned, e.g. `evidence_packet.v1` / `cas_harness_evidence_packet_v1`) **[VERIFY field count and schema name; legacy "15-field" figure is unverified]**.
- **(12) Schema validation.** Run a validator; reject malformed packets.
- **(14) Rendering.** Produce a human-readable (markdown) view from the validated packet.
- **(16) Reproducibility key.** The `trace_id` (and recorded artifact hashes) enable regeneration of the packet; where generation is deterministic (greedy decode + pinned checkpoint), regeneration is bit-identical; where sampled, close-but-not-identical. **[ATTORNEY: keep "reproducible," avoid "guaranteed bit-identical" as an unqualified claim.]**
- **(18) Authenticated delivery.** Serve via a REST endpoint with JWT authentication, a path-traversal guard, a size cap, schema round-trip validation, **tenant-ownership scoping** (a packet is resolved only if the caller's tenant owns the trace), and a reviewer-drawer UI.

**(C.2) The six proof chips** (each present/verified, or explicitly `unavailable`):
1. **`model_proof`** — real model loaded, not fake/demo, model revision/commit captured.
2. **`cas_readout`** — readout votes, selected layers, labels, trace states.
3. **`causal_proof`** — ablation/intervention evidence from the calibrated probe pack (or `unavailable`).
4. **`control_proof`** — matched controls / baselines from the calibrated probe pack (or `unavailable`).
5. **`output_proof`** — actual output text, token ids, logits/hash, token alignment.
6. **`packet_proof`** — Evidence Packet id, hash, schema-validation result, and anchor/WORM-retention proof.

**(C.3) Verdict vocabulary (exactly three).** `ACCEPT`, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`. A customer-safe `ACCEPT` requires all six chips present/verified (or explicitly waived by a documented mode-specific policy, not waived by default) **and** the anchoring gate of Mechanism F. **`FLAG_FOR_HUMAN_REVIEW` is not failure** — it means the system saw enough to know a human is needed but not enough to safely accept or auto-suppress.

**(C.4) Evidence-type vs. claim-support separation (traceability discipline).** Each surfaced claim carries (i) an **evidence-type** label — `cas_hard_trace` (deterministic compiler/slot output), `source_copy_evidence` (pointer-copy from a named input token), `derived_trace` (reconstructed from logs/state), or `neural_attribution_estimate` (mechanistic measurement = evidence, not proof) — and, separately, (ii) a **claim-support** status (supported / partially_supported / unsupported / contradicted / not_applicable / unknown). The two questions ("how was it traced?" vs. "did the answer back it up?") are never conflated. **Reserved language is enforced: never "irrefutable," "proven," "guaranteed correct," or "verified by [any third-party AI/vendor]."**

**(C.5) Independent re-verification.** A reviewer can: open the packet JSON by `trace_id`; reproduce the output from the recorded run command + checkpoint; inspect the exact code at the recorded commit SHA; recompute artifact SHA-256 hashes and compare; and confirm gates passed on a held-out set whose corpus hash matches the packet. The packet is designed to talk for itself, so a skeptical reviewer need not trust the builder.

**(C.6) Why prior methods don't do it.** This binds a versioned schema + validator + reproducibility key + authenticated, tenant-scoped delivery into one artifact, turning an inspection into a portable, third-party-verifiable evidence object — which ad-hoc reports and generic logging do not provide.

**(C.7) Variations.** Schema field set and version; serialization (JSON/other); auth scheme (JWT, mTLS, signed URLs); transport (REST, gRPC); reproducibility via `trace_id` vs. content hash vs. both.

### 5.D Mechanism D — Multi-Layer Trace + Readout-Position Blind-Spot Disambiguation

**(D.0) What it does.** Reads probe confidence across **all** layers to classify a trajectory's quality, and uses the cross-layer pattern to label each class as either a **model-side blind spot** or a **readout-position weakness** — answering "when can the tool not read this model/class?"

**(D.1) How it works** (Figure D1):
- **(10) Multi-layer capture.** Capture activations at every layer (or a defined set).
- **(12) Per-layer confidence.** Apply the probe at each layer; record a confidence profile.
- **(14) Trace classification.** Classify the across-layer profile as stable-like vs. problem-like **[VERIFY classifier form/features]**.
- **(16) Blind-spot disambiguation.** If confidence is uniformly low across all layers → **model-side** weakness; if high at some layers but the default readout missed them → **readout-position** weakness **[VERIFY exact decision rule/thresholds]**.

**(D.2) Why prior methods don't do it.** Single-layer probing collapses two distinct failure causes into one ambiguous number; tracing confidence across full depth and applying a disambiguation rule separates them, yielding an auditable statement about tool reach.

**(D.3) Variations.** Layer subset vs. full depth; confidence-metric choice; trace classifier as threshold heuristic, sequence model, or lacunarity-based; disambiguation-rule variants/thresholds.

**(D.4) Example results (replace with records).** Trace-classifier lacunarity ~**[VERIFY: 0.0016]** (cleanest factorization in record); per-class model-side vs. readout-position disambiguation validated; the mid-depth layer-selection rule transferred across **[VERIFY: all tested]** models.

### 5.E Mechanism E — Matched-Control Causal Localization (head-level + sparse-neuron-cover)

**(E.0) What it does.** Localizes the causal substrate of a structural readout at two granularities — **attention-head level** and **sparse MLP-neuron-cover level** — and proves it with necessity + sufficiency tests and bidirectional control, each against matched controls, with bit-exact patch-back recovery. Explicitly bounded to sparse-cover granularity; **not** a single-neuron monosemanticity claim.

**(E.1) How it works** (Figure E1):
- **(10) Head-level necessity.** Ablate identified attention-head components; readout accuracy drops **[VERIFY: e.g., 78% → 19%]**. Matched same-kind/same-layer controls do not produce equivalent disruption.
- **(12) Head-level sufficiency.** Path-patch — restore only those components' activations in an otherwise-ablated model; readout recovers **[VERIFY: → 100%]**.
- **(14) Sparse-cover identification.** Identify a sparse MLP intermediate-neuron cover (~**[VERIFY: 1% of layer width, e.g., 32 of 3072]**) supporting a class-vs-partner margin.
- **(16) Bidirectional control.** Ablate cover → margin inverts; amplify cover → margin grows; polarity-flip → classification reverses **[VERIFY the three swing magnitudes]**.
- **(18) Patch-back.** Restore the cover → bit-exact recovery (mean abs margin error 0.0).

**(E.2) Why prior methods don't do it.** Necessity + sufficiency + matched controls + bidirectional (not just removal) control + bit-exact patch-back together rule out generic disruption and riding-alongside correlation that single-direction ablation leaves open. The validated causal unit is the **sparse cover** — finer than head-level, without overclaiming single-neuron monosemanticity.

**(E.3) Variations.** Granularity (head-level, neuron-cover, or both); cover size as a parameter; control type (same-kind/same-layer matched primary vs. random secondary); manipulations (ablate, amplify, polarity-flip, partial-gain scaling).

**(E.4) Example results (replace with records).** Head-level necessity (accuracy **[VERIFY 78%→19%]**, matched control p **[VERIFY 0.0323]**) + sufficiency (path-patch **[VERIFY 100%]** recovery); sparse cover: three manipulations pass **[VERIFY: 112/112 at p<10⁻³³]** with bit-exact patch-back; amplifying the wrong-class cover flips prediction in **[VERIFY: 25.9%]** of rows (independent evidence of control). Bounded to sparse-cover, not single-neuron.

### 5.F Mechanism F — Tamper-Evident Integrity Chain + WORM Anchoring (GOVERNANCE-mode)

**(F.0) What it does.** Wraps every Evidence Packet in a five-layer integrity chain so its contents and ordering can be cryptographically attested, local or full-server tampering is detectable, and an external anchor's retention is mechanically re-checked on each verification — and gates the `ACCEPT` verdict on that anchor proof. **The guarantee is tamper-EVIDENCE on re-verify, not physical immutability.**

**(F.1) How it works:**
- **Layer 1 — Disk persistence.** Each merged packet is written to a disk-backed store on creation; survives process restart, redeploy, and crash on a single instance (regression-tested bit-identical reload). **Scope: single-instance restart-survival only; multi-instance / host-loss durability NOT proven** (one database server, no replica, no failover).
- **Layer 2 — Append-only hash chain.** Each write appends a log entry containing a cryptographic fingerprint of the previous entry; tampering with any historical entry shatters every subsequent fingerprint and is detectable in linear time.
- **Layer 3 — Five-check verify endpoint** (`/evidence/{trace_id}/verify`): (1) packet payload hash check; (2) hash-log entry check; (3) hash-chain continuity check; (4) local anchor-manifest check; (5) external S3 round-trip check (live `GetObject` + hash compare). Any failure returns `partial_mismatch` naming the failing layer; the endpoint never returns a silent "OK."
- **Layer 4 — External anchoring with mechanical WORM check.** Operator-configurable modes (`disabled` / `local` / `s3`). In `s3` mode with **Object Lock in GOVERNANCE mode** and an **~30-day rolling retention window**: each verify call issues `HeadObject`, confirms `ObjectLockMode == GOVERNANCE`, and confirms `ObjectLockRetainUntilDate` is in the future. **Governance mode is operator-overridable** — a principal holding `s3:BypassGovernanceRetention` can delete or overwrite the anchor before retention expires. The mechanism therefore proves retention is *present and current at audit time* and makes any override *tamper-evident on the next verify call*; it does **not** physically prevent change, and it is **not** `COMPLIANCE`-mode, **not** immutable, **not** permanent.
- **Layer 5 — `ACCEPT`-requires-anchor gate.** The verifier's final `ACCEPT` requires all three anchor proofs simultaneously — (a) anchor written, (b) anchor re-read and hash-matched, (c) Object Lock retention mechanically active. **If any one is missing, an explicit `ACCEPT` is automatically downgraded to `FLAG_FOR_HUMAN_REVIEW`.**
- **Three-state trust UI.** "S3 object verified" (full 5-check incl. round-trip) / "Anchored to S3" (write-time receipt, no live re-read) / "S3 verify failed" (round-trip found a discrepancy). The UI never silently upgrades trust.

**(F.2) Honest composite property (for the spec, reserved language).** The chain makes a packet's current contents and chain position cryptographically attestable; a full-server compromise that rewrites the local chain cannot rewrite the externally-anchored fingerprints; any party with read-only access to the verify endpoint and the bucket can re-verify without operator cooperation; tampering at any layer is detected on the next `/verify` call and named; and a non-anchor-proven packet cannot present as `ACCEPT`. **As of this drafting, no `ACCEPT` verdict stands in the project record** (a prior reported `ACCEPT` was withdrawn as an overclaim); claims herein cover the *gate mechanism*, not an achieved `ACCEPT`.

**(F.3) Variations.** Anchor backends (S3 Object Lock, other WORM-capable object stores); retention window length; check set; gate predicate. **[ATTORNEY: confirm whether to claim "GOVERNANCE-mode specifically" narrowly or "a tamper-evident, mechanically-re-checked, operator-overridable retention anchor" broadly. The broad form better matches the honest guarantee and avoids tying the claim to one cloud product.]**

### 5.G Mechanism G — Generation Readiness Gate (four-tier, zero-parameter, non-mutating)

**(G.0) What it does.** An opt-in, non-mutating, **zero-learnable-parameter** policy module that reads combined structural signals and emits exactly one of four graded actions — **allow / caveat / constrain / suppress** — with a full audit trail, leaving the model's forward path unchanged.

**(G.1) How it works** (Figure F1):
- **(10) Signal intake.** Read structural signals: lacunarity, inversion flags, RPM/prerequisite satisfaction, gap and domain-confidence signals, and the Verification-Stack decision **[VERIFY exact signal list]**.
- **(12) Action mapping.** Apply a fixed (non-learned) decision policy mapping the signal combination to one of {allow, caveat, constrain, suppress} **[VERIFY the rule]**, with mode-aware thresholds.
- **(14) Audit trail.** Emit the action with the contributing signals as reason codes.

Mapping to product verdicts (one embodiment): allow → `ACCEPT` (if all required provenance present); caveat → `FLAG_FOR_HUMAN_REVIEW`; constrain → `FLAG_FOR_HUMAN_REVIEW` in triage mode, `SUPPRESS` in license-grade modes; suppress → `SUPPRESS`.

**(G.2) Why prior methods don't do it.** Four graded tiers (not binary), zero learnable parameters (no drift/retraining, fully auditable), and non-mutation (the model's forward path is untouched; default unattached) distinguish this from learned moderation and binary filters.

**(G.3) Variations.** Signal set and combination logic; number/labels of tiers; the constrained-generation method invoked by the "constrain" tier; default attached vs. unattached.

### 5.H Mechanism H — Sharded-Fleet Execution (frontier-scale audit with anti-misattribution)

**(H.0) What it does.** Audits a target model too large for one worker by sharding the model across N workers, running a local sub-harness on each layer slice, and aggregating per-slice evidence under a conservative-default gate — **without raw activations ever crossing the wire** and with a **fragment-hash anti-misattribution** guarantee.

**(H.1) How it works** (Figure H1 — new; see flowchart doc):
- **Planning / job assignment.** A planner shards the model by layer ranges and assigns each layer-slice **job** to a probe worker. *(In one embodiment a "Scale Planner" issues shard/layer jobs, workers take leases on jobs and return receipts, and an aggregation "merge-gate" combines completed jobs.* **[VERIFY this orchestration vocabulary — "Scale Planner," "lease," "receipt," "merge-gate" — against the actual implementation; the validated, code-grounded terms are "Fleet Executor," per-worker "sub-harness," "Fleet Aggregator," and "fleet-topology verifier gate." Attorney: prefer the validated terms in claims, recite the orchestration terms as optional embodiments.]*)
- **Per-worker sub-harness.** Each worker hooks its own layer slice, captures locally, runs the same probe stack, ablation, and trace on its activations, and emits **local proof chips** and a **local verdict**.
- **Fragment SHA-256 commit (anti-misattribution).** Each worker commits a SHA-256 of its raw activation tensor so the aggregator can prove Worker K's chips came from Worker K's tensors and not from a substituted source.
- **Aggregation.** A **Fleet Aggregator** validates per-worker fragment hashes, stitches the multi-layer trace across shards, reconciles probe overlaps at shard seams, coordinates cross-worker ablation (computing one subspace-projection direction and having each worker apply it to its own slice), and recomputes lacunarity on the stitched trace. **Only chips, hashes, and local verdicts travel the wire — never raw activations.**
- **Fleet-topology verifier gate (conservative-default).** If any worker reports `SUPPRESS` → fleet `SUPPRESS`; if any worker reports `FLAG` → fleet `FLAG`; if any fragment hash is invalid → fleet `FLAG` (anti-misattribution); if any worker is absent/timed-out → fleet `FLAG` (incomplete cover); **only if all N workers `ACCEPT` AND all fragment hashes verify AND topology is complete** → fleet `ACCEPT` (preliminary).
- **Unified packet + same anchoring gate.** The aggregator emits one unified Evidence Packet (six aggregate cross-worker chips + fleet-topology manifest naming which worker held which layers + per-worker fragment-hash list + per-worker local-verdict roll-up + preliminary fleet verdict), which then passes the Mechanism F anchoring gate (a preliminary fleet `ACCEPT` that cannot prove all three anchor conditions is downgraded to `FLAG_FOR_HUMAN_REVIEW`).

**(H.2) Why prior methods don't do it.** Single-machine tooling cannot audit a sharded frontier model, cannot prove which shard produced which evidence, and has no principled aggregation policy. The fragment-hash commitment + conservative-default gate + activations-stay-local design solve misattribution, over-claiming, and data-movement simultaneously.

**(H.3) Variations.** Shard granularity (layer ranges, tensor-parallel splits); orchestration (planner/lease/receipt vs. direct executor); aggregation policy (conservative-default primary; weighted/quorum variants); fragment-commit hash function.

### 5.I Mechanism I — Two-Bridge Hidden-Content Detector (PROTOTYPE TIER — disclose as preliminary)

**(I.0) What it does.** Computes a CAS profile from internal hidden states (η₁) and a second CAS profile re-read from the emitted output text through the same probe stack (η₂), then compares them; a typed class present internally but absent in emission is flagged as **withheld content** — structure the model represents but does not emit.

**(I.1) How it works** (Figure G1):
- **(10) Internal profile.** Apply η₁ to hidden states → internal typed-class profile.
- **(12) Emitted profile.** Apply η₂ (same typed-class reader) to the emitted text → emitted typed-class profile.
- **(14) Divergence test.** Compare; a class present internally but absent in emission is flagged as withheld at typed-class granularity **[VERIFY comparison metric and threshold]**. (One embodiment classifies the gap into typed "hiding shapes.")

**(I.2) Status.** **Prototype tier:** bridge wired, returns typed-class output, qualitatively interpretable, **but no pre-registered confirmatory gate has been closed. Not licensed for production accept/suppress decisions. Disclosed here as preliminary** to preserve a priority date on the architecture without overstating maturity.

**(I.3) Why prior methods don't do it.** Output-only analysis is blind to internal computation; self-report is a different, ungrounded modality. Comparing two structural profiles (internal vs. emitted) of the same typed ontology is what makes withheld-content detection possible non-invasively.

**(I.4) Variations.** Profile representation; divergence metric (set difference, distributional distance); ontology granularity; flagging threshold.

---

## 6. Claims

> **[ATTORNEY — claims are illustrative and MUST be rewritten by counsel.]** A provisional needs **no** claims; these are included only to anchor scope and to help counsel see the intended coverage. Counsel should (a) decide which mechanisms to pursue, (b) calibrate breadth vs. §112 enablement/written-description against the **[VERIFY]** disclosures, (c) check the prior-art notes in §7, and (d) ensure no claim asserts an unachieved result (e.g., a standing `ACCEPT`) or a prohibited characterization (immutable/certified/guaranteed).

**Independent Claim 1 (System — conditioning bridge).** A system for conditioning the output distribution of a pretrained transformer language model without modifying its weights, comprising: a capture module that records hidden-state activations from the model for an input; a trained embedding map (η) that maps the activations to a typed cognitive-structure label from a fixed ontology; a realization map (ε) that maps the label to a natural-language prefix; a concatenation module that prepends the prefix to the input; and a scoring module that measures a shift in the model's next-token likelihood for a target class between a forward pass on the input and a forward pass on the prefixed input; wherein the prefix is ordinary input tokens attended to by subsequent positions by the model's native self-attention, such that no activation-stream intervention is required during generation.

**Claim 2.** The system of claim 1, wherein the capture module records activations at a layer in a middle band of the model's depth selected by a layer-selection rule.

**Claim 3.** The system of claim 1, wherein the scoring module additionally computes a null-control shift using a raw-notation prefix and a directional-specificity margin using an involution-partner prefix.

**Claim 4.** The system of claim 1, wherein the embedding map is a balanced-logistic probe trained per-model on labeled activation examples, and the ontology is one of a 10-class, 28-class, or 40-class typed taxonomy.

**Independent Claim 5 (Method — non-oracle runtime verification).** A method for deciding, at inference time and without a ground-truth label, whether to accept or suppress an output of a language model, comprising: extracting from the model's internal state a plurality of non-oracle stability signals; mapping the signals via thresholds, calibrated offline against ground-truth labels, to an accept or suppress decision; attaching to each suppression a human-readable reason derived from the triggering signal(s); and selecting the thresholds from among a plurality of operating modes differing in precision/coverage tradeoff; wherein ground-truth labels are used only for offline calibration and never at inference.

**Claim 6.** The method of claim 5, wherein the signals include stability, conflict, uncertainty, drift, and ensemble-agreement over a plurality of readouts with an n-of-m ensemble-agreement requirement, and a row outside calibrated coverage is assigned a human-review or suppress decision rather than an accept decision.

**Independent Claim 7 (System — reproducible Evidence Packet).** A system for producing a verifiable record of a language-model inspection, comprising: an assembly module that collects, into a versioned schema, an input, a structured cognitive expression, an output, detected labels, causal-test results, a verdict selected from exactly {accept, flag-for-human-review, suppress}, provenance, cryptographic hashes of artifacts, and a trace identifier; a schema validator; a renderer producing a human-readable view; a reproducibility key comprising the trace identifier enabling regeneration of the record; and an authenticated delivery endpoint that resolves the record only when the requesting tenant owns the trace; wherein the record carries, for each surfaced claim, both an evidence-type label and a separate claim-support status.

**Claim 8.** The system of claim 7, wherein the record carries six proof chips comprising a model proof, a cognitive readout, a causal proof, a control proof, an output proof, and a packet proof, each being present, verified, or marked unavailable.

**Claim 9.** The system of claim 7, wherein an accept verdict is conditioned on all six proof chips being present or verified and on an anchor-retention proof per claim 11.

**Independent Claim 10 (Method — blind-spot disambiguation).** A method for distinguishing model-side from readout-position weakness in a language model, comprising: capturing activations at a plurality of layers; applying a probe at each layer to form a per-layer confidence profile; classifying the across-layer profile; and labeling a target class as a model-side blind spot when confidence is uniformly low across the layers, and as a readout-position weakness when confidence is high at one or more layers not selected by a default readout.

**Independent Claim 11 (System — tamper-evident anchoring gate).** A system for tamper-evident retention of an inspection record, comprising: a disk-backed store; an append-only hash chain in which each entry contains a fingerprint of the prior entry; a verify endpoint that performs a plurality of independent checks including a live external-object round-trip and an object-retention check, and that on any failure returns a result naming the failing check rather than a success; an external anchor under an operator-overridable, time-bounded retention mode whose retention state is mechanically re-checked on each verification; and a gate that downgrades an accept verdict to a human-review verdict whenever an anchor-write proof, an anchor-re-read-match proof, or an active-retention proof is absent; wherein the system surfaces a tri-state trust indicator and does not characterize the anchor as immutable or permanent.

**Independent Claim 12 (Method — matched-control causal localization).** A method for establishing that a transformer component causes a structural readout, comprising: ablating the component and measuring a drop in readout accuracy against a matched same-kind same-layer control; restoring only the component's activations by path-patching and measuring recovery; identifying a sparse intermediate-neuron cover supporting a class-versus-partner margin; and performing bidirectional control by ablating the cover to invert the margin, amplifying the cover to grow the margin, and polarity-flipping the cover to reverse classification; the method being bounded to sparse-cover granularity.

**Independent Claim 13 (System — sharded-fleet execution).** A system for auditing a language model sharded across a plurality of workers, comprising: a planner assigning layer-slice jobs to the workers; a per-worker sub-harness that captures activations locally on its layer slice, runs a probe stack and ablation locally, and emits local proof chips and a local verdict; a per-worker fragment-commitment module that commits a hash of the worker's raw activation tensor; an aggregator that validates the fragment hashes to attribute each worker's chips to that worker's tensors, stitches a multi-layer trace across shards, and coordinates cross-worker ablation; and a fleet-topology gate that assigns a non-accept fleet verdict if any worker reports a non-accept local verdict, any fragment hash is invalid, or any worker is absent, and assigns an accept fleet verdict only if all workers accept, all fragment hashes verify, and the topology is complete; wherein raw activations remain on each worker and do not cross the network.

**Independent Claim 14 (Method — four-tier non-mutating readiness gate).** A method for governing generation by a language model, comprising: reading a combination of structural signals including a prerequisite-satisfaction signal, an inversion signal, and a stability decision; applying a fixed decision policy having zero learnable parameters to map the signal combination to exactly one of allow, caveat, constrain, and suppress; and emitting the selected action with the contributing signals as reason codes; wherein the method does not modify the model's weights, activations, or logits.

**Claim 15 (Method — two-bridge hidden-content detection).** A method comprising: forming a first typed-class profile from a model's internal hidden states; forming a second typed-class profile from the model's emitted text via the same typed-class reader; and flagging, as withheld content, a typed class present in the first profile and absent from the second.

**Dependent/omnibus claims [ATTORNEY to expand]:** combinations (e.g., the system of claim 7 incorporating the gate of claim 11 and the fleet of claim 13); medium claims (a non-transitory computer-readable medium storing instructions to perform each method); and means-plus-function variants as counsel prefers.

---

## 7. Prior-art and risk notes for counsel (NOT part of the spec)

- **Probing / linear readouts of transformer activations** is a crowded field — Claim 1's novelty rests on the **closed read→realize→condition loop using ordinary prefix tokens** + the section-retraction framing, not on probing per se. Recommend foregrounding the conditioning-via-realized-prefix and the null-control/partner-margin design.
- **Activation steering / representation engineering** (e.g., steering-vector and representation-control literature) is close prior art for "changing model behavior from internal structure." Distinguish on **non-invasive (text-prefix, no hook), weight-frozen, auditable** grounds.
- **Mechanistic interpretability / causal scrubbing / path patching / SAE features** is active prior art for Mechanism E. Distinguish on **matched-control + bidirectional + bit-exact patch-back at sparse-cover granularity**, and **do not** claim single-neuron monosemanticity.
- **Selective prediction / "learning to reject" / calibration** is prior art for Mechanism B. Distinguish on **non-oracle signals + per-suppression reason + calibration-only gold-label use + mode selection**.
- **Provenance/attestation, transparency logs, WORM storage, C2PA-style content credentials** are prior art adjacent to Mechanisms C and F. Distinguish on the **inspection-specific six-chip schema + verdict-gating-on-anchor-proof + tri-state honest trust surface**, and keep the anchoring claim at the honest "tamper-evident, operator-overridable, mechanically re-checked" altitude. **Risk:** claiming WORM/immutability broadly invites both prior-art and enablement/overclaim problems — the §5.F honest framing is deliberately narrower.
- **Distributed/sharded inference and verifiable computation** are prior art adjacent to Mechanism H. Novelty likely sits in **fragment-hash anti-misattribution tying chips to a worker's tensors + conservative-default fleet gate + activations-never-leave-worker**.
- **Inventorship / ownership [ATTORNEY]:** the build used heavy AI assistance. Confirm human-inventorship sufficiency under current USPTO AI-inventorship guidance; AI tools are not inventors, but AI-assisted human invention is patentable — document the human conception of each mechanism.
- **On-sale / public-use / prior-disclosure [ATTORNEY — URGENT]:** there are NDA-gated investor spec sheets, a public "coming-soon" landing page, an alpha/beta program, and arXiv/utility-patent intentions noted in internal rollout plans. **Audit the actual public-disclosure and offer-for-sale timeline before filing the non-provisional** — any non-confidential disclosure or offer may have started the one-year U.S. clock and may already have barred foreign rights. This is the single highest-priority legal item.
- **Provisional 64/037,173 is filed (priority date 04/13/2026).** The provisional is of record and governs priority for the matter it disclosed; the operative deadline is the **~04/13/2027** non-provisional/PCT conversion to preserve that date (see top banner and `PATENT_FILING_FACTS_CONFIRMED.md`). Post-04/13/2026 new matter (v7.5/7.6/7.7, Fleet/300B) is not retroactively covered — confirm its routing (utility filing vs. fresh provisional) with counsel.

---

## 8. Abstract

A system and methods audit, causally localize, condition, and tamper-evidently anchor the cognitive structure of pretrained open-weight transformer language models. A trained embedding map reads a typed cognitive-structure label from a model's hidden states; a realization map emits that label as a natural-language prefix that, prepended to the input, shifts the model's next-token distribution on a second forward pass without modifying weights or intervening in the activation stream. A runtime stack accepts, flags, or suppresses outputs using only non-oracle stability signals, with a reason attached to each suppression and ground-truth labels used only for offline calibration. Each inspection is packaged as a versioned, schema-validated Evidence Packet carrying a verdict (accept / flag-for-human-review / suppress), six proof chips, full input-to-structure-to-output traceability, provenance, and artifact hashes, delivered over a tenant-scoped authenticated channel and independently re-verifiable. A multi-layer disambiguation method separates model-side from readout-position weakness; a matched-control method localizes the causal substrate at attention-head and sparse-neuron-cover granularity; an integrity chain anchors records to an operator-overridable, time-bounded, mechanically re-checked external store and downgrades acceptance when anchor proofs are absent; a four-tier zero-parameter gate governs generation without mutating the model; and a sharded-fleet executor audits frontier-scale models with per-worker fragment-hash anti-misattribution and a conservative-default aggregation gate.

---

## Appendix A — Change Log vs. Source (legacy A–G drafts → this consolidation)

| # | Legacy source (PDF) | What it said | What changed here, and why |
|---|---|---|---|
| 1 | Header / NDA notices | "USPTO Provisional #64/037,173" (also in 51 repo files) | **Confirmed CORRECT** by the USPTO *Electronic Acknowledgement Receipt* (founder-provided 2026-06-08): **64/037,173**, Utility—Provisional, Conf. No. 1346, filed 04/13/2026. The earlier "series code should be 63" flag was outdated — 2026 provisionals are **series 64**. Header now recites the real number + filing metadata; canonical record at `PATENT_FILING_FACTS_CONFIRMED.md`. |
| 2 | Framework references | Implicit older CAS | Reconciled to **CAS v7.7** (40 states, 7 drives, 4 registers, 5 generative ops) as the secular label space. |
| 3 | Prov. C "Evidence Packet" | 15-field schema, JWT delivery, `trace_id` reproducibility | Expanded to current build: **six named proof chips**, **three-verdict vocabulary**, **evidence-type vs. claim-support separation**, **tenant-ownership scoping**, reserved-language rules. Field count marked **[VERIFY]** (legacy "15" unconfirmed). |
| 4 | Prov. B "Verification Stack" | accept/suppress on non-oracle signals; modes | Kept; added the **three-verdict** mapping and explicit coverage-honesty (`FLAG_FOR_HUMAN_REVIEW`), and re-labeled the headline numbers as **offline-validation, not production**. |
| 5 | (absent) WORM/anchoring | Legacy drafts had **no** anchoring mechanism; later marketing called it "immutable/permanent/COMPLIANCE/court-admissible" | **Added Mechanism F at the corrected honest altitude**: S3 Object Lock **GOVERNANCE** mode, ~30-day rolling, `HeadObject` re-check, operator-overridable, **tamper-evident not immutable**, `ACCEPT`-requires-anchor downgrade gate, tri-state UI. Prohibited words listed. |
| 6 | (absent) Fleet | Legacy drafts had **no** scale-out mechanism | **Added Mechanism H**: sharded model, per-worker sub-harness, **fragment SHA-256 anti-misattribution**, Fleet Aggregator, **conservative-default** fleet-topology gate, activations-stay-local. Orchestration vocabulary ("Scale Planner / lease / receipt / merge-gate") flagged **[VERIFY]** vs. validated terms. |
| 7 | Prov. A "η→ε bridge" | two-pass read-realize-condition | Kept as Mechanism A; added the four prefix conditions incl. **raw-notation null control** and **partner margin**; clarified bridge is computed by an **offline worker**, while the service module only normalizes/verifies. |
| 8 | Prov. D / E / F / G | blind-spot, causal localization, readiness gate, hidden-content | Kept as Mechanisms D, E, G, I; **Mechanism I explicitly marked PROTOTYPE / not licensed**; Mechanism E explicitly **bounded to sparse cover, not single-neuron**. |
| 9 | Headline results | "first ACCEPT verdict," strong effect sizes | **Withdrew the "ACCEPT stands" framing** (no `ACCEPT` stands in record); all effect sizes marked **[VERIFY]** against canonical files; claims drafted to cover **mechanisms**, not achieved results. |
| 10 | Esoteric/heritage framing | (some legacy CAS materials carry it) | **Excluded entirely** from this filing; CAS described in secular technical terms only. |

**END — CAS_provisional_patent_updated.md — DRAFT for registered-patent-attorney/agent review. Not legal advice. Keep confidential.**
