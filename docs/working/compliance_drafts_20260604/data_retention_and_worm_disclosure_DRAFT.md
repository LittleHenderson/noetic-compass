DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — Data Retention & WORM Anchoring Disclosure (DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Scope**: CAS Harness invite-only comped NDA beta.
**Draft date**: 2026-06-04

> This draft states, honestly and without overclaim, how long CAS Harness keeps data and what the Evidence Packet "WORM anchoring" actually guarantees. It exists specifically to prevent the corrected overclaims (immutability, permanence, Compliance-mode, standing `ACCEPT`) from re-appearing in any external document. It is not legal advice.

---

## 1. Why this disclosure exists

An earlier internal description called the Evidence Packet anchor "immutable," "permanent," "write-once-read-many," "Compliance-mode," and "not deletable even by the operator." **Those descriptions overstated the deployed configuration and are withdrawn.** This document records the accurate posture so participants are not misled.

## 2. Evidence Packet WORM anchoring — what it actually is

When an Evidence Packet is anchored to Amazon S3, the anchor uses:

- **S3 Object Lock in `GOVERNANCE` mode** — **not** `COMPLIANCE` mode.
- An **approximately 30-day rolling retention window** — **not** permanent retention.
- **Tamper-evident on re-verify** — each `/verify` call re-reads the anchor via a live S3 `GetObject` round-trip and a `HeadObject` retention check, so any change is detectable on the next verification.
- **Operator-overridable** — a privileged principal holding the `s3:BypassGovernanceRetention` permission **can** delete or overwrite the anchor before retention expires.

### 2.1 What this explicitly is NOT
- It is **NOT immutable**. Governance mode is overridable by a privileged operator.
- It is **NOT permanent**. Retention is an approximately 30-day rolling window, not forever.
- It is **NOT WORM-`COMPLIANCE`-mode**. The deployment uses `GOVERNANCE` mode.
- It is **NOT** a guarantee that an anchor "cannot be deleted even by the operator." It can.

### 2.2 What the guarantee actually is
The guarantee is **tamper-evidence on the next `/verify` call**, not physical prevention of change. If an anchor were altered or removed, the five-check verify (in-server payload / hash-log / hash-chain continuity / local anchor manifest / external S3 round-trip) plus the `HeadObject` WORM-retention check would surface the discrepancy and name the failing layer rather than returning a silent "OK." The mechanism proves retention is **present and current at audit time** and makes any override **tamper-evident** — that is the honest claim.

### 2.3 Anchor location
Anchors are written to Amazon S3 in the `us-west-2` region. See `subprocessors_DRAFT.md`.

## 3. Durability — single-instance restart-survival only

Evidence Packets are disk-persisted on a single paid-disk instance and have been shown to survive process restart, redeploy, and crash on that one instance, with regression-tested bit-identical reload.

**Multi-instance and host-loss durability are NOT proven.** The deployment runs a single database (Postgres) server with **no replica and no failover**. Loss of that host — or its disk — is not covered by any tested recovery path. Accordingly, CAS Harness makes **no** claim of high availability, geographic redundancy, or host-loss durability during the beta; such claims are **NOT LICENSED**.

This is an infrastructure-maturity bound, not a flaw in the integrity chain itself: the append-only hash chain and the external S3 anchor remain independently re-verifiable wherever the packet data survives.

## 4. Retention schedule (beta posture)

| Data | Retention | Honest qualifier |
|---|---|---|
| Evidence Packet (local disk) | Life of the packet on the single instance | Single-instance restart-survival only; host-loss NOT covered |
| Evidence Packet S3 anchor | ~30-day rolling Object Lock GOVERNANCE retention | Tamper-evident, operator-overridable; NOT immutable, NOT permanent, NOT COMPLIANCE-mode |
| Hash chain / hash-log | Life of the packet on the single instance | Append-only; tamper-evident, not tamper-proof |
| Model inputs/outputs in packet | Life of the packet (deletable on request) | See `rights_request_process_DRAFT.md` |
| Activations/readouts | Derived values inside packet; large raw artifacts not durably persisted by default | — |
| BYOK customer API keys | Not retained — ephemeral, never stored at rest | See `privacy_policy_DRAFT.md` §4 |
| CRM / lead data | While lead relationship active; deletable on request | Local store unless Airtable sync configured |
| Auth tokens | Short-lived (bounded by expiry) | — |
| Operational/request logs | Limited operational window | — |

Final committed retention periods are for counsel to set before any external use.

## 5. Verdict honesty interacts with retention

Anchoring an Evidence Packet does **not** upgrade its verdict. A packet whose verdict is **`FLAG_FOR_HUMAN_REVIEW`** stays `FLAG_FOR_HUMAN_REVIEW` after anchoring. As of this draft, **no `ACCEPT` verdict stands** in the project record; per-customer production `ACCEPT` is **NOT LICENSED**. The `ACCEPT`-requires-WORM gate is a mechanism that *downgrades* an `ACCEPT` to `FLAG_FOR_HUMAN_REVIEW` when any WORM-retention proof is missing — it has not been used to mint a standing `ACCEPT`.

## 6. Deletion mechanics caveat

Because anchors sit under a ~30-day Object Lock GOVERNANCE window, a deletion request (see `rights_request_process_DRAFT.md`) may be satisfied either by an operator override of the Governance retention (which is permitted and tamper-evident) or by letting the rolling window lapse. Counsel should confirm the deletion path that best matches the final published retention commitment.

---

**END — data_retention_and_worm_disclosure_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
