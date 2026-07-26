# PCBA Engineer — Owner Claim Review

**Date:** 2026-07-25
**Reviewer:** Little Henderson (author and owner)
**Scope:** the four `*_claim_review_signed` authority receipts for
*CAS PCBA Engineer*.

This document is the artifact those four receipts attest to. It records what
was reviewed and what was approved, so the receipt points at something rather
than at nothing.

## What is being approved

For each of the four claim areas below, the owner has reviewed the claims the
book actually makes, in the text as it now stands, and approves them **at the
scope stated in the book** — no wider.

### 1. Reference board safety claim (Chapter 18, CSB)

The book claims the CSB is an engineering artifact whose behaviour follows from
named components with named parameters: a Stage 3 safety CJT at `sat=0.8`, a
matched differential pair, a red-path fuse at `threshold=0.9`, and no via
permitting an Operational signal to bias the Principled charter.

**Approved as:** a description of a reference design and its intended
behaviour. **Not approved as:** a claim that any deployed system has been
tested to behave this way. The book states this limit itself, on the copyright
page and in the Chapter 26 Bench Note ("certification is a claim about the
circuit, never about values").

### 2. Memory board cognitive memory claim (Chapter 21, CMB)

The book claims a write path, an address decoder, and Fisher-Rao-distance
retrieval.

**Approved as:** an architectural description. **Not approved as:** a measured
retrieval-accuracy or lacunarity result. No such evaluation has been run; see
the open receipts below.

### 3. Power board burnout prevention claim (Chapter 22, CPMB)

The book claims per-domain regulation, current limiting, brownout detection,
sequencing and thermal management, and draws an analogy to human burnout.

**Approved as:** an architectural description and an analogy. **Not approved
as:** a human-factors finding, or as advice about managing burnout in people.

### 4. Governance regulatory claim (Chapter 26)

Chapter 26 has been reframed during this review. It no longer asserts that CCB
artifacts *satisfy* the EU AI Act, NIST AI RMF or ISO/IEC 42001. It now states
that they line up with the kind of evidence those frameworks ask for, that
conformity is determined by the relevant authority and not by this book, that
"certification" here means an internal signed engineering record rather than
assessment by a notified body, and that nothing in the chapter is legal advice.

**Approved as:** a drafting aid. **Not approved as:** a compliance opinion.

## What is NOT covered by this review

The following remain open and are **not** signed. They assert that a test was
run and passed, or that a review by a specific competence took place. Neither
can be created by authorization:

- `csb_red_team_report_pass`, `csb_false_positive_eval_pass`
- `cmb_memory_retrieval_eval_pass`, `cmb_lacunarity_eval_pass`
- `cpmb_load_budget_eval_pass`
- `audit_retention_proof_pass`
- `legal_review_signed`, `regulatory_mapping_reviewed`,
  `customer_disclosure_reviewed`, `cmb_privacy_review_signed`,
  `cpmb_human_factors_review_signed`

The book has been written so that it does not depend on any of them. Where a
claim would have required one, the claim was narrowed instead.
