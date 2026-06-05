DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — Privacy Policy (BETA DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Scope**: Invite-only, comped (no-charge) NDA beta of CAS Harness operated by Noetic Compass (Little Henderson, founder).
**Draft date**: 2026-06-04

> This is a working draft of a privacy policy for the CAS Harness beta. It describes the data practices the product is *engineered* to follow today. It has not been reviewed by counsel, is not a binding statement to any user, and must not be relied on as legal advice. Every claim-status word below (for example `ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, `LICENSED`, `NOT LICENSED`, `OPEN`) is used in its exact CAS Harness technical sense and must not be softened.

---

## 1. Who we are

CAS Harness is an AI-cognition audit service operated by Noetic Compass. During the beta, the service is offered only to invited participants, at no charge, under a separate Non-Disclosure Agreement and the separate CAS Harness Beta Terms (see `beta_terms_DRAFT.md`).

This policy explains what data the service processes, how long it is kept, who processes it on our behalf, and the choices a beta participant has.

## 2. What this beta is (so the data practices make sense)

CAS Harness inspects an open-weight AI model that a participant points it at, reads cognitive structure from the model's hidden states, and produces an **Evidence Packet** — a structured, cryptographically chained record of what the audit tested and found. The Evidence Packet carries a verdict that is one of `ACCEPT`, `SUPPRESS`, or `FLAG_FOR_HUMAN_REVIEW`.

Honesty note carried into this policy so a participant is not misled by the artifacts they receive: as of this draft, **no `ACCEPT` verdict stands** in the project record, per-customer production `ACCEPT` verdicts are **NOT LICENSED**, and several scientific claims (notably matched-taxonomy "CAS-specificity") remain **OPEN**. An Evidence Packet is an audit record, not a certification.

## 3. Categories of data we process

### 3.1 Model inputs and outputs
The prompts/scenarios sent to the audited model and the model's generated outputs. These are processed to run the audit and are recorded in the Evidence Packet and supporting logs.

### 3.2 Activations and readouts
Internal model activations captured during the audit, and the per-axis probe readouts derived from them (for example, the η→ε bridge measurements and probe accuracies). These are the technical substrate of the audit. For multi-worker (fleet) audits, raw activation tensors stay on the worker that produced them; only small derived values (proof-chip scores) and cryptographic fragment hashes are transmitted to the aggregator.

### 3.3 Audit Evidence Packets
The structured output artifact: six proof chips (each SHA-256-committed), a verifier report (verdict + confidence + scope + coverage + boundary), and audit-chain provenance (payload hash + hash-log pointer + chain continuity + anchor manifest + WORM-retention status). Evidence Packets may be externally anchored to Amazon S3 (see §5 and `data_retention_and_worm_disclosure_DRAFT.md`).

### 3.4 CRM / lead data
If a participant or prospect submits an interest form or is tracked as a sales lead, we process contact and pipeline data (for example name, email, organization, deal stage, notes). Lead capture includes anti-abuse measures (a hidden honeypot field and a rate limiter). Lead data may sync to an external CRM (Airtable) **only if** that integration is configured for the deployment; otherwise it stays in the local lead store.

### 3.5 Account, authentication, and operational data
Account identifiers, invite-code redemption records, authentication tokens, request logs, and audit-session ownership metadata needed to operate and secure the service. (Account features are gated and may be disabled during parts of the beta; this section describes data processed when they are enabled.)

### 3.6 Data we deliberately do NOT harvest at this layer
We do not run advertising trackers and we do not sell personal data (see §7).

## 4. Bring-Your-Own-Key (BYOK) customer API keys are EPHEMERAL and never stored at rest

When a participant runs an audit that calls a third-party LLM provider using their own API key (the "Bring-Your-Own-Key" path), that customer-supplied API key is treated as an **ephemeral, in-memory credential**:

- It is used only to authenticate the participant's chosen provider call for that audit.
- It is **never written to our database, disk, Evidence Packet, hash chain, S3 anchor, logs, or CRM**.
- It is **not retained at rest** after the request that uses it completes.
- In our deployment blueprint, all provider API-key environment variables are marked `sync: false` — they are not stored in the committed configuration and are supplied per-deployment / per-request rather than baked into the product.

The third-party LLM providers a participant may select on the BYOK path are listed in `subprocessors_DRAFT.md`. When a participant uses their own key with one of those providers, that provider processes the request under the provider's own terms and privacy policy, not ours.

> Engineering-honesty caveat for counsel: this section states the *designed* behavior. Before any external publication, the BYOK no-persistence behavior should be independently re-verified end-to-end (request path, logging path, error path) so the policy statement matches deployed reality.

## 5. Where data is processed (subprocessors)

We use a small set of infrastructure subprocessors to run the beta. The current list — Render (application hosting), Amazon Web Services S3 in the `us-west-2` region (Evidence Packet anchoring/storage), Vercel (frontend hosting), Airtable (CRM, only if configured), and the LLM provider a participant chooses on the BYOK path — is maintained in `subprocessors_DRAFT.md`. That file is the authoritative subprocessor list for this draft.

## 6. Retention windows

| Data category | Retention posture (beta draft) |
|---|---|
| Model inputs/outputs in an Evidence Packet | Retained for the life of the Evidence Packet (subject to a participant's deletion request under §8) |
| Activations / readouts | Derived values retained inside the Evidence Packet; large raw activation artifacts are not durably persisted by default in the current build |
| Evidence Packet (local, disk-persisted) | Retained on a single paid-disk instance; **single-instance restart-survival only** — multi-instance / host-loss durability is **NOT** proven (see `data_retention_and_worm_disclosure_DRAFT.md`) |
| Evidence Packet S3 anchor | S3 Object Lock **Governance** mode with an approximately **30-day rolling retention window**, tamper-evident on re-verify, operator-overridable — explicitly **not** permanent and **not** immutable |
| BYOK customer API keys | **Ephemeral; never stored at rest** (see §4) |
| CRM / lead data | Retained while the lead relationship is active; deletable on request |
| Authentication tokens | Short-lived; bounded by token expiry |
| Operational/request logs | Retained for a limited operational window for security and debugging |

Retention specifics are a beta posture and may change; counsel should set final, committed retention periods before any external publication.

## 7. We do not sell your data

Noetic Compass does **not** sell personal data and does **not** share it for cross-context behavioral advertising. Data is processed to operate the audit service, secure it, and (for leads) manage the sales relationship. Data harvested from audits may be used internally to improve Noetic Compass products, including CAS-Native research, consistent with the Beta Terms and the participant's NDA; this internal-use posture should be confirmed and bounded by counsel before publication.

## 8. Your choices and rights

Beta participants may request access to, export of, or deletion of their data. The request path and the (beta-scoped) timelines are described in `rights_request_process_DRAFT.md`. Because the beta is comped and invite-only, some rights mechanics are handled manually rather than through self-service tooling.

## 9. Security

We apply authentication, owner-scoping of audit sessions, and a cryptographic integrity chain on Evidence Packets. Known limitations are disclosed honestly: the beta runs on a single-instance deployment with no proven host-loss durability, and the broader paid-tenant security spine (sessions/revocation, role-based access control, tenant isolation on every surface, durable security-event logging) is still being built out and is not fully enabled. Security contact details are in `security_contact_DRAFT.md`.

## 10. Legal basis for the comped beta

The beta is operated as a limited, invite-only, no-charge evaluation under an executed NDA and the CAS Harness Beta Terms. Processing is grounded in:
- the participant's agreement to the NDA and Beta Terms, and
- our legitimate interest in evaluating, securing, and improving an experimental product with a small set of consenting, invited participants.

This is a draft characterization of the legal basis for a comped beta only; it is **not** a determination of the lawful basis under any specific regime (for example GDPR Article 6 / CCPA). Counsel must confirm the correct legal basis, any required notices, and any cross-border transfer mechanism (the AWS region is `us-west-2`) before external use.

## 11. Changes and contact

This draft will be revised before any external release. Questions about data practices during the beta, and security reports, should go to the contact in `security_contact_DRAFT.md`.

---

**END — privacy_policy_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
