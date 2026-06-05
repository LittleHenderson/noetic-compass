DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — Data Rights Request Process (DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Scope**: CAS Harness invite-only comped NDA beta. All timelines below are beta-scoped targets, not legal commitments.
**Draft date**: 2026-06-04

> This draft describes how a beta participant can ask to access, export, or delete their data, and the target timelines during the beta. Because the beta is comped, invite-only, and small, these requests are handled largely **manually** rather than through self-service tooling. Counsel must confirm the exact rights, response deadlines, identity-verification standard, and any regime-specific obligations (for example GDPR / CCPA) before external use.

---

## 1. What you can request (beta scope)

A beta participant may request, with respect to data tied to their account, audits, or lead record:

1. **Access** — a description of what categories of their data we hold and how it is processed.
2. **Export** — a copy of their audit Evidence Packets and associated input/output records in a machine-readable format (for example JSON), plus their CRM/lead record.
3. **Deletion** — deletion of their data, subject to the operational and retention caveats in §5.
4. **Correction** — correction of inaccurate contact/CRM data.

Note on scope: BYOK customer API keys are **ephemeral and never stored at rest** (see `privacy_policy_DRAFT.md` §4), so there is nothing to access, export, or delete for that category.

## 2. How to submit a request

During the beta, requests are submitted to the contact in `security_contact_DRAFT.md` (the same channel handles privacy and security inquiries during the beta). A request should include:

- the account email / invite identity used in the beta, and
- which right is being exercised (access / export / deletion / correction) and, if partial, which audits or records.

## 3. Identity verification

Before acting on an access, export, or deletion request, we will reasonably verify that the requester controls the account/identity tied to the data — typically by confirming control of the invite email. We will not disclose or delete data on an unverified request. (Final verification standard is for counsel.)

## 4. Target timelines (beta)

| Step | Beta target |
|---|---|
| Acknowledge receipt of a request | Within ~5 business days |
| Complete an access or export request | Within ~30 days of verified request |
| Complete a deletion request | Within ~30 days of verified request, subject to §5 |

These are **operational targets for a comped beta**, not statutory commitments. Where a specific legal regime imposes a shorter or longer deadline, counsel must set the governing timeline before external use.

## 5. Deletion caveats (honest)

- **S3 anchors under Object Lock GOVERNANCE retention.** Anchored Evidence Packets sit under an approximately 30-day rolling Object Lock GOVERNANCE window (see `data_retention_and_worm_disclosure_DRAFT.md`). A deletion request may be satisfied either by an authorized operator override of the Governance retention (permitted, and tamper-evident on re-verify) or by letting the rolling window lapse. We will tell the requester which path was used.
- **Hash-chain integrity.** Because the integrity chain is append-only and tamper-evident, deleting the contents a packet commits to is detectable by design. Deletion removes packet payload/data; it does not rewrite history silently.
- **Single-instance scope.** Durability is single-instance restart-survival only; there is no replica/backup fleet from which additional copies must also be purged during the beta. Counsel should confirm this remains true if backups are later introduced.
- **Legal/operational holds.** We may retain limited data where required to comply with law, resolve disputes, prevent abuse, or enforce the Beta Terms and NDA.

## 6. No charge

Handling rights requests during the comped beta is free. We may decline or charge for requests that are manifestly unfounded or excessive, to the extent permitted by applicable law (mechanics for counsel).

## 7. Escalation

If a participant is unsatisfied with how a request was handled, they may escalate to the founder via the same contact channel. Any regulator-complaint pathway is for counsel to specify per the applicable regime.

---

**END — rights_request_process_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
