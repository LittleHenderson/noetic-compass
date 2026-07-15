# Airtable CRM acceptance source runbook

Purpose: collect the Airtable lead/upsert/readback portion of the
`support_crm` customer-production gate from the exact public Render service.
The command submits one synthetic lead through `POST /api/crm/public/leads`,
reopens the append-only lead ledger, and binds the Airtable adapter's strict
upsert, direct record readback, and unique deduplication-list readback.

This runbook does not publish acceptance authority. Its fragment always says
`OPEN` and names `resolved_support_ticket_sla` as missing. A resolved support
ticket, acknowledgement, response-time/SLA receipt, remote lifecycle change,
and authorized publication remain separate operations. Do not change
`support_crm` to `present` from this source receipt alone.

## Public intake contract

New lead intake requires both fields explicitly:

```json
{
  "consent_to_contact": true,
  "privacy_notice_version": "<published-notice-version>"
}
```

The server pins the notice URL to `https://cascompass.ai/privacy`, records a
whole-second UTC consent timestamp, and stores
`consent_schema_version=noetic_crm_consent.v1`. The lead is immutable; sync and
pipeline updates preserve the exact consent boolean, URL, notice version,
timestamp, and consent schema version.

`privacy_notice_version` is an identifier for the notice that was actually
published and shown to the submitter. It is not legal text, and the collector
does not choose or invent it. Use the approved release identifier or published
content digest supplied by the legal/publication process.

## Airtable table fields

The configured table must contain the existing lead, deduplication, owner, and
lifecycle fields plus these fixed consent/readback fields:

- `Consent to Contact` (checkbox/boolean)
- `Consent Recorded At UTC` (single-line text or a field that preserves the
  exact `YYYY-MM-DDTHH:MM:SSZ` value)
- `Consent Schema Version` (single-line text)
- `Privacy Notice URL` (URL or single-line text)
- `Privacy Notice Version` (single-line text)

The adapter includes all five in the PATCH upsert and verifies their exact
values in both subsequent reads. Any missing, stale, or changed value fails
closed as `sync_failed`; it cannot earn `synced`.

## Prerequisites

- Run from Render Shell on service `srv-d82ph683kofs73d210e0`.
- `RENDER_GIT_COMMIT` must equal the supplied exact protected `master` SHA.
- `NC_CRM_PROVIDER=airtable` and the complete `NC_AIRTABLE_*` provider contract
  must be present. The API origin remains exactly `https://api.airtable.com/v0`.
- `NC_CRM_LEAD_STORE_PATH` must be an absolute durable path shared with the API
  process.
- The exact deployed build must include the v2 public lead contract. Existing
  v1 ledger rows remain readable, but they cannot satisfy this acceptance
  source because they have no explicit consent record.
- Use a newly approved, currently published privacy notice version. Never put
  the Airtable token, raw record ID, raw lead ID, or real customer data on the
  command line.

## Collect

From the exact production Render Shell:

```bash
python scripts/collect_airtable_crm_acceptance_source.py \
  --master-head <exact-40-character-master-sha> \
  --deploy-id <exact-live-render-deploy-id> \
  --privacy-notice-version <approved-published-version> \
  --source-receipt-output /tmp/airtable-crm-source-receipt.json \
  --fragment-output /tmp/support-crm-fragment.json
```

The command creates one non-customer probe address below
`acceptance.invalid`. It is intentionally persisted in the local lead ledger
and Airtable so the receipt proves a real provider effect and restart-safe
readback. It outputs only domain-separated SHA-256 hashes of the local lead ID
and Airtable record ID plus the adapter's existing
`sha256:<64 lowercase hex>` response digest.

## Required pass conditions

- The public route returns HTTP `200`, `captured=true`, `synced=true`, and exact
  `sync_status=synced` under `noetic_crm.v2`.
- The durable lead readback matches the public response and retains the exact
  consent record.
- The persisted receipt names exact provider `airtable`, binds one Airtable
  record ID, and proves readback, deduplication, owner assignment, lifecycle,
  and the adapter response digest.
- Consent time is at or before provider verification time, which is at or
  before observation time.
- Neither output contains an email address, raw lead ID, raw Airtable record
  ID, credential, bearer token, or provider response body.
- The fragment remains exact `OPEN` with
  `missing_required_evidence=["resolved_support_ticket_sla"]`.

## Complete the gate separately

An authorized gate builder may combine this hashed source receipt with a real
resolved support-ticket/SLA artifact. The final `support_crm` evidence must
preserve the fragment's exact `crm_lead` and `consent` fields, including
`source_receipt_sha256`, and then pass both the runtime acceptance-authority
validator and `scripts/verify_customer_production_acceptance.py`. Publication
is a separate compare-and-swap operation. A CRM source receipt by itself is
never `present` and never customer-production `ACCEPT`.
