DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — No-Certification Statement (DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Scope**: CAS Harness invite-only comped NDA beta.
**Draft date**: 2026-06-04

> This draft is a plain, honest statement of what CAS Harness Evidence Packets are — and are not — for compliance purposes. It is written to stand on its own and to be quoted into other documents. It is not legal advice.

---

## 1. Noetic Compass holds no third-party certification

Noetic Compass holds **no** SOC 2, **no** ISO/IEC 42001, and **no** other third-party security, quality, or AI-management certification. CAS Harness has not been audited or certified by any independent certification body.

Any statement to the contrary — in marketing, a deck, a data sheet, or a conversation — is incorrect and must not be made.

## 2. Evidence Packets support compliance documentation; they do not satisfy regulation

CAS Harness Evidence Packets are **designed to produce regulator-facing evidence artifacts** that can **support** an organization's own compliance documentation (for example interpretability and model-risk evidence that frameworks such as the EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, and Federal Reserve SR 11-7 call for).

An Evidence Packet, by itself, **does not**:
- satisfy, fulfill, or demonstrate compliance with any law, regulation, or standard;
- constitute a certification, accreditation, approval, or seal;
- make any audited model "compliant," "approved," "certified," or "court-admissible."

Whether any artifact satisfies a given regulatory obligation, and whether it is admissible in any proceeding, is a determination for the relevant regulator or court under the applicable rules — not something CAS Harness asserts.

## 3. Withdrawn framings

The following framings are **not** claimed and must not be used about CAS Harness:
- "regulator-grade by construction"
- "court-admissible"
- "compliant" / "makes you compliant"
- "certified" / "certification"
- "immutable" / "permanent" / "write-once-read-many" Evidence Packet anchoring (the anchor is S3 Object Lock **GOVERNANCE** mode, ~30-day rolling, tamper-evident, operator-overridable — see `data_retention_and_worm_disclosure_DRAFT.md`)

The accurate framing is: CAS Harness produces **audit-grade structural evidence artifacts designed to support** compliance documentation.

## 4. Verdict honesty

A CAS Harness verdict of **`ACCEPT`** is not a certification or guarantee. As of this draft, **no `ACCEPT` verdict stands** in the project record and per-customer / production `ACCEPT` is **NOT LICENSED**; where proof gates remain open the honest verdict is **`FLAG_FOR_HUMAN_REVIEW`**. The matched-taxonomy "CAS-specificity" claim is **OPEN** (the first blind comparator returned `GREY`). Detection of cognitive structure from open-weight models is `LICENSED`; comparative/probabilistic CAS-speciality and absolute uniqueness are not.

## 5. Nothing here is legal advice

This statement, and every other document in this folder, is a working draft for review by the founder and qualified counsel. **Nothing in it is legal advice.** Organizations relying on CAS Harness for any compliance purpose are responsible for their own legal and regulatory determinations and should consult their own counsel.

---

**END — no_certification_statement_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
