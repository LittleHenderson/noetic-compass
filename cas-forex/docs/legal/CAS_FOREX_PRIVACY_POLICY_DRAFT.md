# CAS Forex Privacy Policy Draft

Status: Draft for local development. Counsel review required before public, hosted, paid, or multi-user use.

CAS Forex stores local operational evidence needed to run, audit, and diagnose the trading cockpit. Hosted or multi-user deployment requires a final privacy policy, retention policy, deletion process, and support workflow.

## Data CAS Forex May Store

- Trading evidence: orders, attempted dispatches, broker receipts, account snapshots, positions, strategy decisions, blocked-trade reasons, risk checks, and performance reports.
- Owner settings: authorization switches, risk caps, AI dial settings, delegated live/money authority settings, manual-order journal reasons, notification preferences, and local device pairing state.
- Diagnostic data: API health, terminal bridge health, operator status, audit rows, error messages, and readiness reports.
- Notification destinations: web push subscriptions and webhook URLs used for observational system events.
- Money-movement evidence: provider responses, receipts, ledger entries, event hashes, before/after balance snapshots, transfer caps, and destination-allowlist metadata needed for audit and reconciliation.

## Secrets

Broker/API secrets should remain server-side or in encrypted runtime stores. Secrets should not be exposed to browser JavaScript, committed to source control, or pasted into public logs.

## Payment and Broker Data

CAS Forex should not store raw bank-card numbers, raw bank login credentials, or custody records. Payment, deposit, withdrawal, KYC, and custody details belong with the broker or payment provider.

## Legal And Review Records

CAS Forex may store legal/compliance preparation artifacts such as disclosure
drafts, legal review checklists, and counsel-review record metadata needed to
track public-launch readiness. These records are operational readiness evidence,
not proof of legal approval by themselves.

## Public Launch Gap

Before public launch, add final legal review, data export/deletion process, retention schedule, support contact, incident process, and jurisdiction-specific privacy updates.
