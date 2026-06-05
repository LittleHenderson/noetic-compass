DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — Beta Terms of Use (DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Program**: Invite-only, comped (no-charge) NDA beta of CAS Harness operated by Noetic Compass (Little Henderson, founder).
**Draft date**: 2026-06-04

> These draft terms govern participation in the CAS Harness beta. They are a working document for review by the founder and qualified counsel. They are not a binding agreement, not an offer, and not legal advice. CAS Harness claim-status words (`ACCEPT`, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, `LICENSED`, `NOT LICENSED`, `OPEN`) are used in their exact technical sense and must not be softened.

---

## 1. The beta is invite-only and comped

CAS Harness is offered during this period only to participants Noetic Compass has expressly invited, at **no charge**. Access is granted under (a) an executed Non-Disclosure Agreement and (b) these Beta Terms. Invites are not transferable. Noetic Compass may modify, suspend, or end the beta, or revoke any participant's access, at any time and for any reason.

## 2. The service is EXPERIMENTAL

CAS Harness is **experimental, pre-release software under active development**. It may contain errors, may change without notice, may produce incomplete or incorrect results, and may be unavailable. Features described in marketing or documentation may be partial, gated, disabled, or labeled `EXPERIMENTAL_NOT_VALIDATED`. Frontier-scale (greater than 20B parameter) audits and any matched-taxonomy "CAS-specificity" conclusions are **OPEN / NOT LICENSED** and must not be relied on.

## 3. NO WARRANTY

THE SERVICE AND ALL EVIDENCE PACKETS, VERDICTS, SCORES, AND OTHER OUTPUTS ARE PROVIDED **"AS IS" AND "AS AVAILABLE," WITHOUT WARRANTY OF ANY KIND**, express or implied, including (without limitation) any implied warranties of merchantability, fitness for a particular purpose, accuracy, non-infringement, availability, durability, or that results are complete, correct, or reproducible. Noetic Compass does not warrant that the service will be uninterrupted, secure, or error-free. (Final warranty-disclaimer and limitation-of-liability language is for counsel.)

## 4. An `ACCEPT` verdict is NOT a certification and NOT a guarantee

This is a load-bearing term of the beta:

- A CAS Harness verdict of **`ACCEPT`** is **not** a certification, accreditation, approval, seal, or guarantee of any kind. It does **not** certify that an audited model is safe, correct, compliant, fit for any purpose, or free of defects.
- As of these draft terms, **no `ACCEPT` verdict stands** in the project record, and **per-customer / production `ACCEPT` verdicts are `NOT LICENSED`**. Where proof gates remain open, the honest verdict is **`FLAG_FOR_HUMAN_REVIEW`**.
- A verdict of **`FLAG_FOR_HUMAN_REVIEW`** means exactly that — the result requires human review and is not a pass.
- An Evidence Packet is an **audit record**, designed to *support* a participant's own evaluation and documentation. It does **not** by itself satisfy any regulation, standard, or legal obligation. Noetic Compass holds **no** SOC 2, ISO/IEC 42001, or other third-party certification (see `no_certification_statement_DRAFT.md`).

## 5. The customer remains responsible for their model

The participant — not Noetic Compass — is and remains solely responsible for the AI model(s) they audit and for any decision they make based on CAS Harness output. This includes:

- ensuring they have the right to submit the model, prompts, and data to the service;
- independently evaluating, validating, and deciding whether to deploy, ship, or rely on any model; and
- complying with all laws and regulations applicable to their model and its use.

CAS Harness assists inspection; it does not assume responsibility for the audited model or for the participant's reliance on any result.

## 6. Acceptable use

Participants will not (a) use the service to violate law or third-party rights, (b) attempt to break authentication, exceed authorized scope, or access another participant's data, (c) submit data they are not permitted to submit, or (d) misrepresent a CAS Harness verdict (for example, presenting a `FLAG_FOR_HUMAN_REVIEW` result as an `ACCEPT`, or describing any verdict as a certification).

## 7. Bring-Your-Own-Key (BYOK)

If a participant supplies their own third-party LLM provider API key, that key is treated as an **ephemeral credential and is never stored at rest** (see `privacy_policy_DRAFT.md` §4). The participant is responsible for their own provider account, its costs, and compliance with that provider's terms. Subprocessors and selectable providers are listed in `subprocessors_DRAFT.md`.

## 8. Confidentiality

The beta, the service, its non-public methodologies, and Evidence Packet internals are confidential and governed by the participant's executed NDA. The CAS framework primitives are covered by USPTO Provisional Patent Application #64/037,173; additional filings on CAS Harness mechanisms are in process. Nothing in the beta grants any license to Noetic Compass IP beyond use of the service as invited.

## 9. Data

Data practices for the beta are described in `privacy_policy_DRAFT.md`. Participants acknowledge that audit data may be used internally to improve Noetic Compass products consistent with that policy and their NDA. Durability and retention are limited and disclosed honestly (single-instance restart-survival only; S3 anchoring is Governance-mode, ~30-day rolling, tamper-evident, operator-overridable — not permanent, not immutable). See `data_retention_and_worm_disclosure_DRAFT.md`.

## 10. Limitation of liability (placeholder for counsel)

To the maximum extent permitted by law, Noetic Compass will not be liable for indirect, incidental, special, consequential, or punitive damages, or for lost profits or data, arising from the beta. A liability cap appropriate to a comped beta is to be set by counsel. (This clause is a placeholder and must be finalized by qualified counsel.)

## 11. Changes; governing law

Noetic Compass may update these Beta Terms during the program. Governing law, venue, and dispute-resolution provisions are to be set by counsel before any external use.

---

**END — beta_terms_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
