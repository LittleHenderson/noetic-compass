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

New lead intake requires explicit contact consent:

```json
{
  "consent_to_contact": true
}
```

The server, not the browser, owns the exact notice publication status, version,
URL, and byte-level content SHA-256. It pins the URL to
`https://cascompass.ai/privacy`, records a whole-second UTC consent timestamp,
and stores `consent_schema_version=noetic_crm_consent.v2`. An older caller may
send `privacy_notice_version` only as a compatibility assertion; a mismatch is
rejected and the value never becomes storage authority. The lead is immutable;
sync and pipeline updates preserve the exact consent boolean, publication
status, URL, notice version/content hash, timestamp, and consent schema version.

Current production defaults are deliberately fail-closed. The exact live page
is SHA-256
`e94df1615dde4122836b47a74e32d45c79b63c1603db3bd1aee01f62d7ddae28`,
version `draft-2026-07-14`, and publication status `OPEN`; the page itself says
`FLAG_FOR_HUMAN_REVIEW`. `POST /api/crm/public/leads` therefore returns HTTP
`503` before persistence. A legal/publication operation must replace the
server-owned version/hash with a different finalized notice and set exact
`present`. The collector independently downloads `/privacy`, re-hashes its
exact bytes, and rejects `OPEN`/draft markers before creating a probe lead.

## Airtable table fields

The configured table must contain the existing lead, deduplication, owner, and
lifecycle fields plus these fixed consent/readback fields:

- `Consent to Contact` (checkbox/boolean)
- `Consent Recorded At UTC` (single-line text or a field that preserves the
  exact `YYYY-MM-DDTHH:MM:SSZ` value)
- `Consent Schema Version` (single-line text)
- `Privacy Notice URL` (URL or single-line text)
- `Privacy Notice Version` (single-line text)
- `Privacy Notice Content SHA-256` (single-line text)
- `Privacy Notice Publication Status` (single-line text; accepted rows are
  exact `present`)

The adapter includes all five in the PATCH upsert and verifies their exact
values in both subsequent reads. Any missing, stale, or changed value fails
closed as `sync_failed`; it cannot earn `synced`.

## Prerequisites

- Run from Render Shell on service `srv-d82ph683kofs73d210e0`.
- `RENDER_GIT_COMMIT` must equal the supplied exact protected `master` SHA.
- Provide `RENDER_API_KEY` to that shell process only. The collector performs
  authenticated, no-redirect reads of the exact service and supplied deploy,
  requiring deploy status `live` and commit equal to `RENDER_GIT_COMMIT`. Never
  write the key to either output or command line.
- `NC_CRM_PROVIDER=airtable` and the complete `NC_AIRTABLE_*` provider contract
  must match exact production: base `appXBoYskbfjNaFTs`, table `Leads`, dedup
  field `Dedup Key`, owner field/value `Owner` / `CAS Harness`, lifecycle field
  `Pipeline Status`, and API base `https://api.airtable.com/v0`.
- `NC_CRM_LEAD_STORE_PATH` must be exact `/var/data/leads.jsonl`. The collector
  also verifies Render disk `dsk-d8fomrd8nd3s738rnee0` (`noetic-data`) is
  mounted at `/var/data`; `/tmp`, relative paths, and other absolute paths are
  rejected.
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
  --source-receipt-output /tmp/airtable-crm-source-receipt.json \
  --fragment-output /tmp/support-crm-fragment.json
```

The `/tmp` paths above are output artifacts only; the lead authority remains
the exact `/var/data/leads.jsonl` persistent-disk ledger. The command creates
one non-customer probe address below
`acceptance.invalid`. It is intentionally persisted in the local lead ledger
and Airtable so the receipt proves a real provider effect and restart-safe
readback. It outputs only domain-separated SHA-256 hashes of the local lead ID
and Airtable record ID plus the adapter's existing
`sha256:<64 lowercase hex>` response digest.

## Required pass conditions

- The public route returns HTTP `200`, `captured=true`, `synced=true`, and exact
  `sync_status=synced` under `noetic_crm.v2`.
- Render API proves the supplied deploy is exact `live` at the supplied commit,
  and the source receipt binds the exact service/disk response hashes.
- The live privacy page bytes match the server-owned SHA-256, publication is
  exact `present`, and no checked-in `OPEN`/draft marker remains.
- The durable lead readback matches the public response and retains the exact
  consent record.
- The persisted receipt names exact provider `airtable`, binds one Airtable
  record ID, and proves readback, deduplication, owner assignment, lifecycle,
  and the adapter response digest.
- Consent time is at or before provider verification time, which is at or
  before observation time.
- Neither output contains an email address, raw lead ID, raw Airtable record
  ID, credential, bearer token, or provider response body.
- The fragment embeds the entire secret-safe source receipt, recomputes its
  canonical SHA-256, and binds that digest into `crm_lead`; a same-shaped but
  unrelated hash is insufficient. The fragment remains exact `OPEN` with
  `missing_required_evidence=["resolved_support_ticket_sla"]`.

## Complete the gate separately

An authorized gate builder may combine this hashed source receipt with a real
resolved support-ticket/SLA artifact. The final `support_crm` evidence must
preserve the fragment's exact `crm_lead` and `consent` fields, including
`source_receipt_sha256`, and then pass both the runtime acceptance-authority
validator and `scripts/verify_customer_production_acceptance.py`. Publication
is a separate compare-and-swap operation. A CRM source receipt by itself is
never `present` and never customer-production `ACCEPT`.
