# Airtable CRM acceptance source runbook

Purpose: collect the Airtable lead/upsert/readback portion of the
`support_crm` customer-production gate from the exact public Render service.
The command submits one synthetic lead through `POST /api/crm/public/leads`,
reopens its exact immutable revision and current head from the shared Postgres
StateStore, verifies the completed lead migration marker, and binds the
Airtable adapter's strict upsert, direct record readback, and unique
deduplication-list readback.

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

The adapter includes all seven in the PATCH upsert and verifies their exact
values in both subsequent reads. Any missing, stale, or changed value fails
closed as `sync_failed`; it cannot earn `synced`.

## Prerequisites

- Run from Render Shell on customer service `i-0bd0a082507a51ae3`.
- `RENDER_GIT_COMMIT` must equal the supplied exact protected `master` SHA.
- Provide `RENDER_API_KEY` to that shell process only. The collector performs
  authenticated, no-redirect reads of the exact service and supplied deploy,
  requiring deploy status `live` and commit equal to `RENDER_GIT_COMMIT`. Never
  write the key to either output or command line.
- `NC_CRM_PROVIDER=airtable` and the complete `NC_AIRTABLE_*` provider contract
  must match exact production: base `appXBoYskbfjNaFTs`, table `Leads`, dedup
  field `Dedup Key`, owner field/value `Owner` / `CAS Harness`, lifecycle field
  `Pipeline Status`, and API base `https://api.airtable.com/v0`.
- `NC_CRM_LEAD_STORE_BACKEND=state_store`,
  `NC_STATE_LEDGER_ENABLED=true`, and
  `NC_STATE_LEDGER_READ_AUTHORITY=true` are exact. `NC_DATABASE_URL` must be a
  shared PostgreSQL URL. The collector rejects JSONL/file authority.
- The lead JSONL path and mounted Render disk remain one-time migration-source
  infrastructure only. They are not current read or write authority. The
  collector verifies the deployment contract, then reads the migration marker,
  immutable lead revision, and exact head from Postgres.
- CRM and support StateStore records use the exact durable storage/authority
  scope `CONTACT_STATE_TENANT="__cas_customer_operations__"`. This is a global
  internal operations partition, not a customer tenant, customer owner, or
  customer-isolation claim. Never derive or invent customer tenancy from it.
- `NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON` and
  `NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID` are configured only in the
  production service. The active key has an opaque
  `cpk_<32-lowercase-hex>` ID and independently random retained material. Do
  not expose the keyring or raw material to GitHub Actions or any output
  artifact. The opaque ID is emitted only as public `pseudonym_key_id`.
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
  --fragment-output /tmp/support-crm-fragment.json \
  --private-lead-selector-output /tmp/support-crm-private-lead-selector.json
```

All three paths must differ. The command creates one non-customer probe address
below `acceptance.invalid`. It is intentionally persisted in the Postgres lead
revision ledger and Airtable so the receipt proves a real provider effect and
restart-safe readback. The public source receipt is exact
`cas_harness_airtable_crm_acceptance_source.v3`; the `OPEN` fragment is exact
`cas_harness_support_crm_acceptance_fragment.v3`. They publish only
`hmac-sha256-tenant-scoped-v1`, the opaque retained `pseudonym_key_id`, keyed
`lead_subject`, keyed `airtable_record_subject`, keyed `trace_subject`, and
content digests such as the adapter response. The request trace is
caller-supplied and can be low entropy, so its subject uses the exact global
`CONTACT_STATE_TENANT="__cas_customer_operations__"` scope and the same
retained key ID. Neither the raw trace nor an unkeyed `trace_id_sha256` is
public evidence. Among output artifacts, the raw lead ID exists only in the
owner-readable mode-`0600` private selector:

```json
{
  "schema_version": "cas_harness_support_crm_lead_selector.v1",
  "gate": "support_crm",
  "crm_lead_id": "<private-raw-lead-id>"
}
```

Never print, attach, commit, or put that selector in a public evidence bundle.

## Required pass conditions

- The public route returns HTTP `200`, `captured=true`, `synced=true`, and exact
  `sync_status=synced` under `noetic_crm.v2`.
- Render API proves the supplied deploy is exact `live` at the supplied commit,
  and the source receipt binds exact service/deploy response hashes without
  making the retained migration disk current lead authority.
- The live privacy page bytes match the server-owned SHA-256, publication is
  exact `present`, and no checked-in `OPEN`/draft marker remains.
- The shared Postgres lead readback matches the public response, retains the
  exact consent record, and has an exact completed migration marker plus
  immutable revision/current-head agreement.
- The persisted receipt names exact provider `airtable`, binds a keyed subject
  for one Airtable record, and proves readback, deduplication, owner assignment,
  lifecycle, and the adapter response digest.
- Consent time is at or before provider verification time, which is at or
  before observation time.
- Neither public output contains an email address, raw lead ID, raw Airtable
  record ID, raw request trace, legacy unkeyed identifier/trace hash,
  credential, bearer token, or provider response body.
- The fragment embeds the entire secret-safe source receipt, recomputes its
  canonical SHA-256, and binds that digest into `crm_lead`; a same-shaped but
  unrelated hash is insufficient. The fragment remains exact `OPEN` with
  `missing_required_evidence=["resolved_support_ticket_sla"]`.

## Finalize the real support/CRM gate candidate

First capture a real public support-ticket intake through the operator's
approved secret-safe procedure. Route, acknowledge, and resolve that already
persisted ticket through the normal support lifecycle; the finalizer never
creates or advances it. The public route ignores caller-supplied `source` and
stores exact server-owned `cascompass_contact` provenance. It also attempts an
immutable private `support_public_intake_receipt.v1` twice before returning;
that receipt binds the exact initial revision, request trace, consent/privacy
facts, and server route status `201` under the customer-production HMAC key.
Store only the raw durable ticket ID in an owner-readable mode-`0600` input
with this exact shape:

```json
{
  "schema_version": "cas_harness_support_ticket_acceptance_selector.v1",
  "gate": "support_crm",
  "support_ticket_id": "<private-raw-ticket-id>"
}
```

The ticket write is customer-authoritative and the acceptance receipt is an
auxiliary private write. If both bounded receipt attempts fail, the route still
returns the non-PII ticket `201`, but no status is inferred or backfilled:
`support_crm` remains `OPEN` because finalization fails closed without the
receipt. Receipt creation is per-ticket, create-only, and idempotent, so a
partial first write can be safely retried while the ticket is still its exact
initial `received` revision. Once lifecycle movement begins, a missing receipt
cannot be minted retroactively. The server's `201` receipt fact proves route
execution; it does not prove that a client received the response bytes.

After the ticket is resolved within the configured
`NC_SUPPORT_ACK_SLA_SECONDS`, finalize from the exact production Render Shell:

```bash
python scripts/build_support_crm_acceptance_evidence.py \
  --source-receipt /tmp/airtable-crm-source-receipt.json \
  --fragment /tmp/support-crm-fragment.json \
  --private-lead-selector /tmp/support-crm-private-lead-selector.json \
  --private-ticket-selector /tmp/support-crm-private-ticket-selector.json \
  --output /tmp/support-crm-evidence.json \
  --safe-artifact-output /tmp/support-crm-finalization-receipt.json \
  --private-source-selector-output /tmp/support-crm-private-source-selector.json
```

The finalizer requires both contact backends to be exact `state_store`, shared
Postgres read authority, the support migration marker, and exact immutable
ticket revision/head agreement. It also revalidates the exact private
public-intake receipt envelope and HMAC and derives exact HTTP `201` from that
receipt; the private selector cannot assert a status. It preserves the v3 fragment's exact
`crm_lead`, `consent`, and source-receipt digest, derives the keyed ticket
subject with the same retained key ID, validates the runtime authority
contract, and emits public evidence v3 plus a
`cas_harness_support_crm_finalization_receipt.v1` safe artifact. The final
`cas_harness_support_crm_acceptance_selector.v1` private source selector
contains only the raw ticket and lead IDs required for live source
revalidation.

Validate the public evidence as described in
`customer_production_acceptance.md`. For publication, pass the final private
selector as
`--support-crm-source /tmp/support-crm-private-source-selector.json`. The
publisher reopens both durable migration markers, the exact resolved ticket
revision/head, the public-intake receipt, and the exact lead
revision/head/Airtable consent facts before
any public revision, WORM object, operation, or head mutation. Active serving
repeats that validation. Delete all private selectors through the approved
secure-file procedure after exact publication readback.

The source receipt's `pseudonym_key_id` remains authoritative even if the
active key later rotates. Retain that key through finalization, publication,
and every active serve; a missing retained key makes the authority unavailable.
A CRM source receipt by itself is never `present` and never
customer-production `ACCEPT`.
