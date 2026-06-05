DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — Security Contact & Vulnerability Disclosure (DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Scope**: CAS Harness invite-only comped NDA beta.
**Draft date**: 2026-06-04

> This is a stub for a security disclosure / contact policy. The contact address and PGP key are placeholders that the founder must fill in before any external use. It is not legal advice.

---

## 1. Reporting a security issue

If you believe you have found a security vulnerability in CAS Harness, please report it privately. Do **not** disclose it publicly until we have had a reasonable opportunity to investigate and remediate.

- **Security contact**: `security@noeticcompass.com` *(PLACEHOLDER — founder to confirm/create this mailbox before external use)*
- **General/founder contact**: *(PLACEHOLDER — founder to add)*
- **Encryption**: *(PLACEHOLDER — add a PGP key / fingerprint if encrypted reports are to be supported)*

During the beta, this same channel also handles privacy inquiries and data-rights requests (see `rights_request_process_DRAFT.md`).

## 2. What to include

To help us triage quickly, please include:
- a description of the issue and its potential impact,
- the steps to reproduce (proof-of-concept welcome),
- affected endpoint(s) / component(s), and
- your name/handle for credit (optional).

## 3. Scope

In scope: the CAS Harness beta application and its APIs as made available to invited participants. Out of scope (unless explicitly invited): denial-of-service testing, social engineering of staff, physical attacks, and testing against third-party subprocessors (Render, AWS, Vercel, Airtable, or any participant-selected LLM provider — report issues in those services to the respective vendor). Subprocessors are listed in `subprocessors_DRAFT.md`.

## 4. Safe-harbor posture (placeholder for counsel)

We intend to treat good-faith security research conducted within this scope as authorized and will not pursue action against researchers who (a) act in good faith, (b) avoid privacy violations and data destruction, (c) do not access or modify other participants' data beyond the minimum needed to demonstrate a finding, and (d) give us reasonable time to remediate before any disclosure. **This safe-harbor language is a placeholder and must be finalized by qualified counsel before external use.**

## 5. Our response targets (beta)

| Step | Beta target |
|---|---|
| Acknowledge a report | Within ~5 business days |
| Initial assessment / triage | Within ~10 business days |
| Remediation timeline | Communicated case-by-case based on severity |

These are operational targets for a comped beta, not commitments.

## 6. Honest security posture

We disclose known limitations rather than hide them. As of this draft: the beta runs on a **single-instance** deployment with **no proven host-loss durability**; the paid-tenant security spine (sessions/revocation, role-based access control, tenant isolation on every surface, durable security-event logging) is **still being built out and is not fully enabled**; and Evidence Packet anchoring is S3 Object Lock **GOVERNANCE** mode (tamper-evident, operator-overridable — not immutable). See `data_retention_and_worm_disclosure_DRAFT.md`. We welcome reports that help us close these gaps.

## 7. No bounty (beta)

There is no paid bug-bounty program during the comped beta. We will credit reporters who wish to be named.

---

**END — security_contact_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
