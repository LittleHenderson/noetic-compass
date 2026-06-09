# Provenance and Traceability of AI-Audit Verdicts: The CAS Evidence Packet

**Show-Your-Work Auditing of Cognitive Structure in Open-Weight Transformers, and a Reconstructable Verdict Record**

Little Henderson (Hermes M. Thoth)
Noetic Compass — Cognitive Architecture System (CAS) research program
Date of record: 2026-06-08

**Framework version:** Cognitive Architecture System (CAS) v7.7 (Register Multiplicity and Operator Discipline Extension).
**Status:** Preprint for provenance and priority. **Not peer-reviewed.** Methodology described at the method level; implementation specifics, probe-construction logic, scoring internals, and unfiled mechanisms are reserved.
**Patent posture:** The CAS framework primitives are the subject of a U.S. provisional patent application (pending) — U.S. Provisional Application No. 64/037,173 (Utility—Provisional; filed 04/13/2026). Additional filings on CAS Harness-specific mechanisms (the audit-grade integrity chain, the matched-taxonomy control framework, and related methods) are in process. Nothing herein is legal advice.

---

## Abstract

We describe a method and an evidence format for making the verdict of an AI audit **reconstructable from its evidence**. The unit of work is the **Evidence Packet (EP)**: the record a single audit run emits. Each EP carries one honest verdict drawn from a fixed three-value set — `ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, or `SUPPRESS` — together with the proof chips, blind-spot findings, and integrity metadata that produced it. The central contribution is a **provenance chain**: every verdict is traceable from the audit input, through the recovered cognitive state and its supporting checks ("proof chips"), to the evidence those checks rest on, and the whole packet is externally anchored in a **tamper-evident** Write-Once-Read-Many (WORM) record. The thesis is "show your work" — a verdict that cannot be walked back to its evidence is not a verdict we are willing to stand behind.

The auditing methodology the EP records uses **lift over a text baseline**, not raw probe accuracy, as the headline quantity for any structure-recovery claim. Lift separates genuine extracted structure from mere surface-lexical recoverability: a label that is lexically present in a prompt can yield high raw probe accuracy while contributing little lift, and we treat such high-accuracy / low-lift outcomes as *negative* evidence for extracted structure. Across five model points spanning three independent architecture families (EleutherAI Pythia/GPT-NeoX at four scales, AI2 OLMo, Alibaba Qwen), the method recovers a consistent asymmetry: content taxonomies show large positive lift from low baselines, while operator-notation taxonomies show high raw accuracy correctly flagged by the instrument as surface-symbol presence rather than recovered structure.

We are deliberate about what the present evidence does and does not support, and the provenance chain is built to record that distinction rather than hide it. We report, in the same packets, **disconfirmatory results**: a pre-registered Matched-Taxonomy Control whose first blind comparator returned an indeterminate (GREY) outcome — i.e., the recovered structure was *not* shown to be specific to the proposed taxonomy rather than a generic semantic partition of comparable dimensionality. That open question is part of the provenance: a later re-claimant cannot quietly fabricate a clean result, because the honest record already shows the boundary. We close with limitations stated plainly, including the gap between **scoped validation** results and any **per-customer production** guarantee, and the gap between **demonstration / mock** audits and **live-model** audits.

**Keywords:** provenance, traceability, AI auditing, evidence packet, tamper-evident ledger, WORM, lift over baseline, linear probes, cross-architecture transfer, causal localization, falsification, pre-registration, cognitive architecture, interpretability.

---

## 1. Introduction

### 1.1 The problem: verdicts without provenance

An AI audit produces a judgment — "this behavior is acceptable," "this needs review," "this output should be suppressed." In most tooling that judgment arrives as a number or a label, and the chain from the model's internals to the label is either undocumented or irreproducible. When a result is later questioned — by a regulator, a counterparty, a court, or the auditor's own future self — there is frequently no way to reconstruct *why* the verdict was what it was, or to detect whether the record was altered after the fact.

This preprint addresses that gap directly. It is a provenance document in two senses. First, it establishes a dated public record of authorship and of the methodology and results, including the disconfirmatory ones. Second, and more substantively, it describes a method for attaching provenance **to each audit verdict** so that the verdict is reconstructable from its evidence and resistant to silent post-hoc alteration.

### 1.2 The unit of provenance: the Evidence Packet

The artifact that carries provenance is the **Evidence Packet (EP)**. One audit run emits one EP. An EP is not a summary; it is the auditable record. It contains:

- a single **verdict** from the fixed set `{ ACCEPT, FLAG_FOR_HUMAN_REVIEW, SUPPRESS }`, with any scope qualifier attached (for example, whether the verdict is a scoped-validation result or a customer-production result);
- **proof chips** — the discrete checks that fed the verdict, each carrying a literal status word (`verified` / `present` / `missing` / `failed` / `unavailable`), never softened to "pass";
- **blind-spot / inversion findings** in customer-facing terms — which axis flagged, a severity band, and the customer's own flagged input together with the observed model behavior;
- **integrity metadata** — the external-anchor status, the retention mode, and a trace identifier.

The EP is designed so that every substantive claim about a verdict is anchored to the exact field it came from. This is the traceability principle applied recursively: not only does the audit explain the model, the *explanation of the audit* is itself cited field-by-field back into the packet.

### 1.3 The central thesis: show your work

The organizing commitment is **reconstructability**: a verdict is acceptable only if a second party, given the EP, can walk the chain

> audit input → recovered CAS state → proof chips → underlying evidence → anchored record

and arrive at the same verdict the packet records. Two design consequences follow.

**(a) Honesty is mechanical, not aspirational.** The strongest verdict, `ACCEPT`, is gated: it is emitted only when the integrity proofs hold simultaneously, and is automatically downgraded to `FLAG_FOR_HUMAN_REVIEW` otherwise (Section 4). The system is built so that a missing proof cannot present as a pass.

**(b) Disconfirmatory results are first-class provenance.** A negative or indeterminate result is recorded in the same packet format as a positive one. The auditing discipline we advocate is defined precisely by reporting disconfirmatory results rather than omitting them. This is also a provenance safeguard: the public, dated existence of the honest boundary is exactly what a later fabricator would have to contradict.

### 1.4 Scope and honesty boundaries (read this before the claims)

This document is a **preprint and has not been peer-reviewed.** It describes a method and reports results at a level intended to establish priority and provenance, not to enable reproduction of reserved mechanisms. Three boundaries govern every claim that follows and are stated here so they are not lost later:

1. **Scoped validation is not a production guarantee.** All verdict-level results reported here are *scoped-validation* results on research fixtures and open-weight models. A scoped-validation `ACCEPT` is not a per-customer, production `ACCEPT`. As of this writing, **no standing `ACCEPT` verdict exists in the project record** (Section 4.3), and per-customer production verdicts are explicitly out of scope for this preprint.
2. **No certification is claimed.** Noetic Compass holds no SOC 2, ISO/IEC 42001, or other third-party security/compliance certification. Evidence Packets are designed to *support* compliance documentation; they do not by themselves satisfy any regulation. We do not use "certified," "guaranteed," "immutable," "court-admissible," or "compliant by construction" framings.
3. **Live-model vs demonstration audits.** The integrity chain, the packet format, and the verdict gate are exercised both on real open-weight model audits and on bundled demonstration / reference packets. Where a result rests on a demonstration or mock packet rather than a live-model audit, that is disclosed; demonstration packets that are not anchored correctly return `FLAG_FOR_HUMAN_REVIEW`, never a trusted pass.

---

## 2. Background: CAS and the recovered structure

The audit method recovers **cognitive structure** — a typed state in the Cognitive Architecture System (CAS) v7.7 — from a model's hidden states, and then treats that recovered state as the thing whose presence, causal role, and provenance must be demonstrated.

CAS organizes cognition along orthogonal axes: ten **Noetic** primitives (the structural dynamics of an idea in a mind), four processing **Domains**, seven core **Drives**, and, as of v7.5–v7.7, a **Register** axis specifying the operational character of an operation. The 40 Cognitive States (10 Noetics × 4 Domains) and 7 Drives are the primitives the audit looks for. The v7.7 extension adds operator discipline for register-enriched expressions; it introduces no new primitives, and nothing in the provenance method depends on the v7.7 notation beyond using it as the label space the audit recovers.

For this preprint the relevant fact is narrow: CAS supplies a **fixed, externally specified label space** against which "did the model encode this structure?" is a well-posed question, and "lift over a text baseline" is the quantity we use to answer it honestly (Section 3).

A formal result motivates one of the mechanisms. The method's conditioning step — realizing recovered structure as readable context that shifts the model's next-token distribution — was predicted in advance by a categorical property of the CAS construction (the counit of the Noetic Coverage is a surjective covering morphism). That the mechanism was predicted *before* it was measured is itself part of the provenance story: the prediction is dated and independent of the experiment.

---

## 3. Method: lift over baseline as the honest quantity

### 3.1 Why raw probe accuracy is the wrong headline

A linear probe trained to read a label from hidden states can succeed for an uninteresting reason: the label, or a near-synonym, is lexically present in the prompt, and the "structure" the probe recovers is surface text the model would represent regardless of any deeper cognitive organization. Reporting raw probe accuracy therefore conflates two very different findings.

### 3.2 The quantity we report

We report **lift**: probe performance measured against a **text baseline** — a bag-of-words / surface-lexical classifier given the same items. Lift is the headline for any structure-recovery claim.

- **High raw accuracy with low lift** is treated as *negative* evidence for extracted structure: the instrument is reading surface symbols, not recovered cognition. The packet records this as surface-symbol presence, not as a recovered-structure pass.
- **High lift from a low baseline** is the positive signal: the model encodes the distinction more strongly than a surface classifier can.

This inversion of the usual reporting convention — treating a high-accuracy / low-lift result as a red flag rather than a success — is the methodological core, and it is what lets the provenance chain distinguish "we found structure" from "we found words."

### 3.3 Cross-architecture findings

Applied across five model points in three independent architecture families (EleutherAI Pythia/GPT-NeoX at four scales — 160M, 1B, 2.8B, 20B — plus AI2 OLMo and Alibaba Qwen), the method recovers a consistent asymmetry:

- **content taxonomies** show large positive lift from low baselines;
- **operator-notation taxonomies** show high raw accuracy that the instrument correctly flags as surface-symbol presence rather than recovered structure.

We further report three corroborating tiers, each recorded in the packet that produced it:

1. **Causal load-bearing (with a documented near-miss).** Under matched-control subspace ablation across cognitive axes, recovered structure participates causally in the model's readout. On one axis at 20B the ablation produced a large, high signal-to-noise effect that nonetheless **narrowly missed** its pre-registered acceptance threshold; we report the near-miss as a near-miss, not as a pass. The framing in the packet is the conservative one.
2. **A read-and-realize conditioning loop ("η→ε bridge"),** predicted in advance by the categorical result of Section 2, which shifts next-token likelihood with effect sizes that grow then plateau within a family and replicate across families.
3. **A static-weight evidence tier** showing above-random principal-angle alignment between the recovered subspace and the model's output-weight geometry — evidence independent of any activation trace.

### 3.4 What the method does *not* establish (the specificity question)

A reader must not over-read Section 3.3. That the recovered structure is *present* and *causally relevant* does **not** establish that it is **specific to the CAS taxonomy** rather than a generic semantic partition of comparable dimensionality that the CAS labels happen to span. That is a separate, harder question, and the honest status of it — open — is recorded explicitly (Section 5). We also flag, in the provenance record, an unresolved **signal-vs-leakage** adjudication on the headline detection lift: some fixtures embed each label's definitional gloss, so a fraction of the measured lift may be gloss-carried rather than structure-carried, and the pre-registered adjudication of that question has not yet returned. The conservative reading of the headline readout is therefore the narrow one — *the model linearly encodes the label distinction more strongly than a surface text classifier* — not that the lift is established as taxonomy-specific signal.

---

## 4. The provenance mechanism: traceable verdicts in a tamper-evident record

This section is the provenance/traceability contribution proper.

### 4.1 The verdict and its proof chips

Each EP records exactly one verdict in `{ ACCEPT, FLAG_FOR_HUMAN_REVIEW, SUPPRESS }`. The verdict is not a free-standing label; it is the output of a set of **proof chips**, each of which is itself an auditable object with a literal status word (`verified` / `present` / `missing` / `failed` / `unavailable`). The status words are recorded verbatim and are never collapsed into "pass." A reader reconstructs the verdict by reading the chips: the verdict is a function of the chip statuses, and that function is fixed and inspectable.

Blind-spot and inversion findings ride alongside the verdict in customer-facing terms: which axis flagged, the severity band, and — critically for "where to look" — the customer's own flagged input and the observed model behavior. The methodology behind a probe (how it was constructed or selected, the scoring math) is **not** part of the customer-facing packet; the *result* is shareable, the *method* is reserved.

### 4.2 The integrity chain (what is real, and its limits)

The packet is protected by a layered integrity chain. Stated honestly, with its proven scope and its limits:

- **Disk persistence.** Packets are persisted to disk; this has been proven to survive restart on a **single instance**. **Multi-instance / host-loss durability is NOT proven** — the deployment runs a single database server with no replica and no failover.
- **Append-only hash chain.** Packets are cryptographically chained so that local tampering is detectable on re-verification.
- **Five-check verify endpoint.** A verification call runs five independent checks — in-server payload, log, chain, and anchor-manifest checks, plus an external round-trip to the anchor store.
- **Three-state trust surfacing.** The console distinguishes three external-anchor trust states: `verified`, `receipt-only`, and `failed`. It does not present `receipt-only` or `failed` as `verified`.
- **External anchoring in a tamper-evident WORM record.** Packets are optionally anchored to an external object store under **S3 Object Lock in GOVERNANCE mode** with an approximately **30-day rolling retention window**.

### 4.3 What "WORM" means here — tamper-evident, not immutable

This is the single most important honesty correction in the document, and it governs every WORM claim:

> The anchor uses S3 Object Lock in **GOVERNANCE mode**, **not** Compliance mode, with an approximately **30-day rolling retention** window. A privileged operator holding the `s3:BypassGovernanceRetention` permission **can** delete or overwrite an anchored object. What the chain guarantees is that any such change is **tamper-evident on the next verification call** — not that the record is physically immutable, permanent, or undeletable even by the operator.

We therefore claim **tamper-evidence, not immutability.** We do not describe the anchor as "immutable," "permanent," "write-once-read-many that even the operator cannot delete," or "Compliance-mode." Any of those would overstate the deployed configuration.

### 4.4 The ACCEPT-requires-WORM gate

The strongest verdict is mechanically conditioned on integrity proof. An explicit `ACCEPT` is emitted only when all three retention proofs hold simultaneously:

1. the anchor object was written;
2. the object was re-read and its hash matched;
3. Object Lock retention is mechanically confirmed present and current on that specific object at verification time (via a `HeadObject` check that the lock mode is `GOVERNANCE` and the retain-until date is in the future).

If any one proof is missing, the verifier **automatically downgrades the `ACCEPT` to `FLAG_FOR_HUMAN_REVIEW`.** This converts WORM-anchoring from an optional feature into a hard gate on the final verdict. The trust contract is mechanical: `ACCEPT` means "all three held simultaneously, with receipts." The gate mechanism is verified, and a bundled non-anchored demonstration packet correctly returns `FLAG_FOR_HUMAN_REVIEW` on the negative path.

### 4.5 No standing ACCEPT in the project record (a withdrawn overclaim)

Provenance requires recording our own corrections. An earlier internal note reported a "first `ACCEPT` verdict in the project record" on a scoped-validation packet (the Stage 9 40-Element packet). That report was a **pre-fix overclaim**: it rested on a candidate-only control proof that was stamped verified before the fix that closed the gap. It has been **withdrawn.** The honest WORM-retained verdict for that packet is **`FLAG_FOR_HUMAN_REVIEW`**, and **no `ACCEPT` verdict stands** in the project record as of this writing. Per-customer production `ACCEPT` remains out of scope and unestablished. We document the withdrawal in full because the discipline we advocate requires that a retracted claim leave a visible scar, not a silent edit.

### 4.6 Provenance of the explanation layer

A reading-aid layer can render a packet in plain language for a non-expert. Its design reinforces, rather than dilutes, the provenance contract: every segment of the plain-language reading must be anchored by reference to the exact packet field it came from (an uncited segment is not shown), and the rendered verdict is asserted to equal the packet's recorded verdict — on mismatch, the aid is discarded and only the raw packet verdict is shown (fail-closed). The explanation never upgrades a `FLAG_FOR_HUMAN_REVIEW` or `SUPPRESS` toward a pass, never relabels a scoped-validation result as a production result, and never invents a confidence the packet does not contain.

---

## 5. Disconfirmatory results as provenance

The provenance chain is most valuable precisely where the result is unfavorable, because that is where a later re-claimant is most tempted to fabricate. We therefore record the open boundaries in the same packet format as the positive results.

### 5.1 The Matched-Taxonomy Control and a GREY comparator

To test whether the recovered structure is *specific* to the CAS taxonomy or merely a generic semantic partition of comparable dimensionality, a **Matched-Taxonomy Control (MTC)** was pre-registered. Two early fixture attempts produced documented nulls *before* reaching the comparator gate, each caught by a pre-registered validity gate:

- one fixture was rejected for **surface text leakage** (the text baseline itself scored at ceiling);
- one fixture was rejected for **meaning removal** under over-aggressive de-leakage (recovery collapsed to chance because the de-leaking stripped the underlying meaning, not merely the answer-key words).

Both nulls are build errors in the *fixture*, caught by the gates, not findings against the method — and they are recorded as such. The second motivated a standing methodology rule that a recoverability fixture must preserve the underlying semantic content of every class it asks the model to recover, even as it strips surface answer-key wording.

The first comparator to clear both validity gates and run blind (GPT-NeoX-20B, MTC Condition-3, 2026-06-03) returned **GREY**: CAS did **not** beat the cardinality-matched control by the pre-registered margin, landing in the pre-registered indeterminate band. **A GREY is not a pass.** CAS-taxonomy specificity is therefore **not established** and is explicitly out of scope as a licensed claim.

**Scope of the GREY (recorded precisely).** This indeterminate outcome is confined to the Condition-3 comparative-specificity test. It does **not** retract the detection result or the conditioning-loop result of Section 3; those stand on their own evidence, subject to the separately-open signal-vs-leakage adjudication noted in Section 3.4. The two questions are distinct and are not conflated in the record.

### 5.2 Why the negative result belongs in a provenance preprint

The auditing discipline this document advocates is *defined* by reporting disconfirmatory results rather than omitting them. Stating plainly what the present evidence does and does not support — the recovered structure is present, is causally relevant, and is conditionable across architectures; its *specificity* to the CAS taxonomy is, as of this writing, an open question pending a valid matched-comparator win and a resolved leakage adjudication — is itself the provenance. A dated record that already shows the boundary is the strongest defense against a later fabricated clean result.

---

## 6. Limitations (honest)

Stated plainly, and intended to travel with every claim above:

1. **Not peer-reviewed.** This is a preprint for priority and provenance. It has not undergone external peer review.
2. **Scoped validation ≠ production.** All verdict-level results are scoped-validation results on research fixtures and open-weight models. No per-customer production guarantee is offered, and no standing `ACCEPT` verdict exists in the project record (Section 4.5).
3. **Specificity is open.** The recovered structure is not shown to be CAS-specific rather than a generic semantic partition; the first blind comparator was GREY (Section 5.1), and a signal-vs-leakage adjudication on the headline detection lift is unresolved (Section 3.4).
4. **Architecture bound.** Three architecture families is not "universal." Claim language stays comparative-and-bounded.
5. **Scale bound.** Validation extends to 20B parameters on two cognitive axes. Beyond 20B is not established (a larger-scale audit is infrastructure-only, with no results).
6. **Modal bound.** Text only. No image, audio, or video validation.
7. **Granularity bound.** Head-level and sparse-neuron-cover localization only; single-neuron monosemantic localization is not claimed.
8. **Durability bound.** Single-instance restart-survival is proven; multi-instance / host-loss durability is not.
9. **WORM bound.** Tamper-evidence under Object Lock GOVERNANCE mode with ~30-day rolling retention, operator-overridable — **not** immutability or permanence (Section 4.3).
10. **No certification.** No SOC 2, ISO/IEC 42001, or other third-party certification; nothing herein is legal advice (Section 1.4).

---

## 7. Why this preprint exists

This document establishes a dated, public record of authorship and of the methodology and results, **including the disconfirmatory ones**. The negative and indeterminate results are part of the provenance: they are not the kind of finding a later re-claimant would fabricate, and their presence stamps the work as authentically the author's. The provenance contribution is the converse, applied to the product: each audit verdict carries its own dated, reconstructable, tamper-evident record, so that "show your work" is enforced at the verdict layer rather than promised in prose.

Detailed implementation parameters — the realization-layer construction, the probe-generation and scoring internals, the sharded large-model probing infrastructure, and other mechanisms under in-process patent filing — are deliberately **not** disclosed here and are available only under separate agreement.

---

## 8. Recommended deposit and citation

**To cite:** Henderson, L. (2026). *Provenance and Traceability of AI-Audit Verdicts: The CAS Evidence Packet.* Noetic Compass preprint, 2026-06-08.

**Recommended deposit:** post to a timestamping venue that issues a permanent identifier (for example a DOI via a preprint/archival service, or an arXiv listing with an endorser) so the date of record is independently verifiable. A dated public commit in a version-controlled repository is a reasonable supplement but a DOI/arXiv timestamp is stronger for priority purposes. Before posting, confirm with patent counsel that nothing in the public text discloses an unfiled mechanism beyond the method-level description intended here, and that the patent posture is stated as *pending* (U.S. Provisional Application No. 64/037,173, filed 04/13/2026).

---

*Preprint — not peer-reviewed. Noetic Compass — CAS research program — L. Henderson — 2026-06-08.*
