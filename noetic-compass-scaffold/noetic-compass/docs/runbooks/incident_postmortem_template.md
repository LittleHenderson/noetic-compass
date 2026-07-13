# CAS Harness incident postmortem template

> Copy this file to `docs/working/incident_response/IR-YYYY-MM-DD-NNN-postmortem.md`.
> Remove instructional text, but never fill a blank with an invented fact.
> Use `unknown` plus an owner and next-check time. Do not include secrets.

## Record control

- Incident ID: `IR-YYYY-MM-DD-NNN`
- Title: `[FACTUAL SHORT TITLE]`
- Status: `OPEN | MONITORING | CLOSED`
- Severity history: `[UTC, severity, rationale, decision owner]`
- Detection UTC: `[UTC | unknown]`
- Declaration UTC: `[UTC]`
- Containment UTC: `[UTC | not yet contained]`
- Recovery UTC: `[UTC | not yet recovered]`
- Closure UTC: `[UTC | open]`
- Incident Commander: `[ASSIGN]`
- Security/Forensics Lead: `[ASSIGN]`
- Infrastructure Lead: `[ASSIGN]`
- Recorder: `[ASSIGN]`
- Privacy/Legal decision owner: `[ASSIGN | not engaged, reason]`
- Customer Operations owner: `[ASSIGN | not engaged, reason]`
- Review/closure approver: `[ASSIGN]`

## Claim boundary

State all that apply:

- Compromise status: `confirmed | suspected | not established | ruled out for a named scope`
- Customer impact: `confirmed | suspected | not established | none found in named sources`
- Evidence integrity: `[payload, hash log, hash chain, external anchor, retention—each separately]`
- Production readiness: `OPEN` unless a separate customer-production gate says otherwise
- Legal conclusion: `[assigned decision owner and source | no legal conclusion recorded]`

Do not turn “not established” into “did not happen.” Name the sources and
limitations behind any negative finding.

## Executive summary

In five sentences or fewer:

1. What happened or was observed.
2. What was affected.
3. What was not established.
4. How it was contained and recovered.
5. What remains open.

## Customer, tenant, data, and service impact

| Dimension | Confirmed facts | Unknowns / limitations | Owner / next check |
|---|---|---|---|
| Customers / tenants | | | |
| Authentication / credentials | | | |
| Customer or regulated data | | | |
| Payments / billing | | | |
| Audit execution | | | |
| Evidence Packet payload / hash log / hash chain | | | |
| External WORM anchor / retention | | | |
| Service availability | | | |

## Timeline (UTC)

| UTC | Actor / source | Fact, decision, or action | Evidence reference | Secret-free? |
|---|---|---|---|---|
| | | | | yes |

Label inferred timestamps as estimates. Preserve provider event IDs, deploy
IDs, exact commit SHAs, response classes, and artifact digests; never include a
credential value or full hook URL.

## Detection

- First signal:
- Detection control that fired:
- Detection control that should have fired but did not:
- Time from first known event to detection:
- Audit-log coverage and retention limitations:

## Technical analysis

### Confirmed facts

- `[FACT]`

### Reasonable inferences

- `[INFERENCE, supporting facts, alternative explanations]`

### Unknowns

- `[UNKNOWN, owner, evidence needed, next check UTC]`

### Root cause and contributing conditions

Describe the system/control failure, not a person's character.

- Direct cause:
- Enabling condition:
- Detection gap:
- Containment gap:
- Recovery gap:
- Organizational/process contributor:
- Why existing tests or reviews did not prevent it:

Use “root cause not established” if the evidence does not support one.

## Containment, eradication, and recovery

| Phase | Action | Provider event/deploy/version evidence | Result | Owner |
|---|---|---|---|---|
| Containment | | | | |
| Eradication | | | | |
| Recovery | | | | |

Recovery evidence must identify the exact Git SHA and CI runs. A healthy
service does not by itself establish customer-production `ACCEPT`.

## WORM and redaction handling

- Immutable evidence objects/versions affected:
- Raw secret present in immutable evidence: `yes | no | unknown`
- Immediate rotation/revocation completed:
- Access restriction or redaction manifest:
- Retention/legal-hold decision owner:
- Object Lock mode and verified retain-until (if any):
- External-anchor re-read result:
- Governance bypass/deletion performed: `no | yes, authority and rationale`

## Notification decision

- Decision UTC:
- Decision owner:
- Customer/data scope considered:
- Contracts, jurisdictions, vendor terms, insurer conditions, or authorities considered:
- Decision: `notify | do not notify on current facts | pending`
- Factual basis:
- Source/counsel reference:
- Required recipients and deadlines (if any):
- Next review UTC and trigger:
- Approved message/evidence reference:

This section records a decision; it does not invent legal advice or a universal
deadline.

## What worked

- `[CONTROL OR PRACTICE, evidence]`

## What failed or was missing

- `[CONTROL OR PRACTICE, evidence]`

## Corrective actions

| ID | Action | Risk closed | Owner | Due UTC | Verification test/evidence | Status | Closure approver |
|---|---|---|---|---|---|---|---|
| IR-ACT-001 | | | `[ASSIGN]` | | | `OPEN` | `[ASSIGN]` |

Actions are not complete when code is written; they are complete when the
named verification result exists in the intended environment.

## Claim review

Before closure, review every external/internal claim made during the incident:

- Were facts kept separate from inferences and unknowns?
- Was `no evidence found` scoped to named sources and time?
- Was `WORM` used only with verified Object Lock retention and object re-read?
- Did any health, CI, deployment, or research result get mislabeled as
  customer-production `ACCEPT`?
- Does any `FLAG_FOR_HUMAN_REVIEW` result remain accurately labeled?

## Closure decision

- Closure criteria met:
- Accepted residual risk:
- Open actions moved to:
- Tabletop/re-test evidence:
- Incident Commander approval and UTC:
- Security/Forensics approval and UTC:
- Privacy/Legal decision recorded and UTC (when applicable):
- Customer Operations handoff and UTC (when applicable):
