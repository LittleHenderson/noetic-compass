# CRM Doc 01 - Lead capture and Airtable sync seam (2026-06-02)

**Status: BUILT and WIRED, with Airtable provider code built but not yet enabled in hosted
production.** The lead-capture pipeline is live in the app: a public form can POST a lead, it is
validated, captured, and (with a durable store configured) persisted. Authed sales users can now
move captured leads through the first pipeline stages. Airtable sync exists, but hosted production
still remains capture-only until the Airtable env vars are configured and a real hosted lead returns
`sync_status: "synced"` with an Airtable record id.

This is the first CRM slice of the public-production path. It follows the same declared-vs-verified
discipline as the state ledger and billing seams.

## The one honesty rule

Capturing a lead **on our side** is not the same act as landing it in the **external CRM**. The
load-bearing discriminator is the lead's `sync_status`:

| `sync_status` | Means | Who can set it |
|---|---|---|
| `captured` | Persisted on our side. No external landing claimed. | Any capture. |
| `sync_pending` | A sync was attempted but no real external landing was made. The null provider always lands here. | The null provider. |
| `synced` | Confirmed landed in the external CRM, backed by a real provider `external_id`. | Only a real provider. |
| `sync_failed` | A real sync attempt errored. The lead remains captured locally and the failure is recorded. | A real provider that errored. |

`CRMSyncResult.__post_init__` refuses to construct a `synced=True` result unless `is_real=True` and
`external_id` is present. A stub cannot accidentally claim a CRM landing.

## What is built

```text
api/services/crm/
  __init__.py     public exports
  models.py       Lead / LeadSubmission / CRMSyncResult value objects + honesty guards
  store.py        LeadStore seam: InMemoryLeadStore (dark) + JsonlFileLeadStore (durable)
  sync.py         CRMSyncProvider ABC + NullCRMProvider + AirtableCRMProvider + factory
  service.py      CRMService.capture(): validate -> capture -> sync -> annotate
api/routes/crm.py public capture endpoint + authed sales views + pipeline status updates
tests/test_crm_lead_capture.py
```

Wiring: `api/main.py` builds the service at startup (`build_crm_service(settings)`) and stores it on
`app.state.crm`; the routes read it, with a dark in-memory fallback if the lifespan never ran.
`api/middleware/auth.py` allow-lists the `/api/crm/public` subtree.

## Endpoints

- `POST /api/crm/public/leads` - public, no JWT. The anonymous lead-capture form posts here.
  Body: `{email, name, organization, message, interest, source, metadata,
  consent_to_contact, privacy_notice_version}`. Consent must be exact `true`; the notice version
  must identify what was actually published and shown. Returns the original receipt fields plus
  the pinned privacy URL, notice version, immutable consent timestamp, and consent schema version.
- `GET /api/crm/leads` - authed. Sales list view, newest first.
- `GET /api/crm/leads/{lead_id}` - authed. One lead, or `404`.
- `PATCH /api/crm/leads/{lead_id}/pipeline-status` - authed. Moves one captured lead through the
  supported sales workflow stages: `new`, `contacted`, `qualified`, `won`, `lost`.
  The HTTP route accepts human labels such as `" Contacted "` and normalizes them through the
  domain validator; unsupported statuses return `422` with the CRM validation message.

The captured lead carries the request's `X-Request-ID` as `trace_id`, so a sales record can be traced
back to the HTTP request that created it.

## Configuration

All CRM config is dark by default.

- `NC_CRM_PROVIDER` (default `null`)
  - `null`: capture locally, sync nothing. Honest capture-only default.
  - `airtable`: real Airtable sync, only when all Airtable settings below are present.
  - `hubspot`: declared seam that still fails loud at startup because no HubSpot integration exists.
- `NC_CRM_LEAD_STORE_PATH` (default unset)
  - unset: `InMemoryLeadStore`, which forgets on restart and never pretends otherwise.
  - set: `JsonlFileLeadStore`, append-only JSON lines with flush + fsync. On Render this must point
    at durable disk, currently `/var/data/leads.jsonl`.
- `NC_AIRTABLE_TOKEN`
- `NC_AIRTABLE_BASE_ID`
- `NC_AIRTABLE_TABLE_NAME` (default `Leads`)
- `NC_AIRTABLE_API_BASE_URL` (default `https://api.airtable.com/v0`)
- `NC_AIRTABLE_DEDUP_FIELD` (default `Dedup Key`; must be a single-line text field)
- `NC_AIRTABLE_OWNER_FIELD` (default `Owner`; this integration writes a configured text value)
- `NC_AIRTABLE_OWNER_VALUE` (required and non-empty whenever Airtable is enabled)
- `NC_AIRTABLE_LIFECYCLE_FIELD` (default `Pipeline Status`)
- `NC_CRM_PUBLIC_LEAD_RATE_LIMIT_MAX` (default `5`)
- `NC_CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS` (default `3600`)

Use a least-privilege Airtable personal access token restricted to the one
target base. The adapter performs record PATCH and GET calls only, so the token
needs `data.records:write` and `data.records:read` plus a base role that can edit
the target table; it does not need workspace-wide or schema-write authority.

The Airtable provider fails startup when `NC_CRM_PROVIDER=airtable` is set without the complete
token/base/table/dedup/owner/lifecycle contract. That is intentional: a half-configured provider
would capture locally while looking externally synced. The API base must resolve to the exact
canonical `https://api.airtable.com/v0` value; userinfo, alternate hosts, HTTP, queries, fragments,
and alternate paths are rejected before the bearer token can be sent, and the production transport
does not follow credential-bearing redirects.

## Airtable mapping

The provider PATCHes Airtable's records endpoint with `performUpsert.fieldsToMergeOn` containing
exactly the configured dedup field. The value is a stable domain-separated SHA-256 pseudonym of the
normalized email, so the filter URL does not expose the address. A write response is not enough to
reach `synced`: the provider GETs the returned record id and then performs a filtered list GET for
the dedup key. Both readbacks must contain the exact current fields, owner, and lifecycle; the list
must return exactly one record and it must be the same record id.

Fields sent:

- `Lead ID`
- `Email`
- configured dedup field (pseudonymous key)
- configured owner field/value
- configured lifecycle field (`pipeline_status` value)
- `Name`
- `Organization`
- `Message`
- `Interest`
- `Source`
- `Trace ID`
- `Schema Version`
- `Metadata JSON`

Operational note: the Airtable table must have compatible field names before enabling the provider.
If Airtable rejects the schema/credentials or either readback is stale, missing, wrongly owned, or
ambiguous, the lead remains locally captured and is annotated `sync_failed`. Provider exceptions
are normalized without response bodies, URLs, tokens, or lead PII. A successful lead stores a
secret-safe verification receipt with readback/dedup/owner booleans, lifecycle, verification time,
and a SHA-256 digest of the three parsed provider responses. Provider reads are bounded, duplicate
JSON keys and non-standard `NaN`/infinity constants are rejected, and receipt time is canonical
whole-second UTC (`YYYY-MM-DDTHH:MM:SSZ`).

## What the tests prove

`tests/test_crm_lead_capture.py` now covers:

- the null provider never reports a landing;
- Airtable provider construction fails loud without credentials or an owner value;
- PATCH `performUpsert` uses one configured pseudonymous email key;
- create then retry/update returns the same external id and the filtered list remains unique;
- direct and filtered readbacks reject ambiguous duplicates, a different record id, missing/wrong
  owner, wrong lifecycle/dedup key, and stale lead/email fields;
- provider HTTP/transport/JSON errors do not expose test secrets or lead PII;
- verification receipts survive a JSONL restart and legacy JSON without a receipt still loads;
- missing record id is an error;
- a sync failure leaves the lead captured locally and annotated `sync_failed`;
- the durable JSONL store survives simulated restart;
- the public endpoint requires no auth and the sales views require auth.
- pipeline status updates require auth, bump the lead version, preserve `sync_status` / `external_id`,
  reject unknown stages, persist to the store, and return `404` for missing leads.
- pipeline status hardening proves store-level atomicity for concurrent updates, JSONL appends one
  new version per status change, and route validation uses the same domain normalizer as the model.

Current focused Airtable/CRM verification: `97 passed` across
`tests/test_crm_lead_capture.py` and `tests/test_crm_airtable_verification.py`.

## Hosted production status

Hosted Render production currently has the durable lead store under `/var/data/leads.jsonl`, but
external CRM sync is still not enabled. To turn it on:

1. Create or confirm an Airtable base/table with the fields listed above.
2. Create a personal access token scoped only to that base with
   `data.records:read` and `data.records:write`.
3. Set these Render env vars together:
   - `NC_CRM_PROVIDER=airtable`
   - `NC_AIRTABLE_TOKEN=<secret>`
   - `NC_AIRTABLE_BASE_ID=<base id>`
   - `NC_AIRTABLE_TABLE_NAME=<table name>`
   - `NC_AIRTABLE_DEDUP_FIELD=<single-line text field>`
   - `NC_AIRTABLE_OWNER_FIELD=<text owner field>`
   - `NC_AIRTABLE_OWNER_VALUE=<non-empty accountable owner>`
   - `NC_AIRTABLE_LIFECYCLE_FIELD=<lifecycle field>`
4. Redeploy.
5. Provision the fixed consent fields listed in
   `docs/runbooks/airtable_crm_acceptance_source.md`, then submit a hosted lead through
   `POST /api/crm/public/leads` with explicit consent and the approved published-notice version.
6. Confirm the public response has `sync_status: "synced"` and `synced: true`; then use the authed
   lead read route to verify the non-empty `external_id` and persisted verification receipt.

Until that hosted proof passes, the honest production posture is: **captured durably, not externally
synced**.

Hosted pipeline-status smoke after `6aeb19f`: authed
`PATCH /api/crm/leads/lead-121dc923f575416d/pipeline-status` returned `200`, moved that smoke lead
to `pipeline_status: "contacted"`, bumped it to `version: 3`, and preserved
`sync_status: "sync_pending"` / `external_id: null`.

Hosted pipeline-status hardening smoke after `ad83151`: authed
`PATCH /api/crm/leads/lead-121dc923f575416d/pipeline-status` with
`{"pipeline_status":" Qualified "}` returned `200`, normalized the status to
`pipeline_status: "qualified"`, bumped it to `version: 4`, and preserved
`sync_status: "sync_pending"` / `external_id: null`.

## Public endpoint anti-abuse

`POST /api/crm/public/leads` is intentionally anonymous, so it cannot use the API-key limiter. The
route now has its own narrow guard before persistence:

- a hidden `website` field acts as a honeypot; non-empty values are rejected before capture;
- a per-client sliding-window limiter defaults to 5 submissions per hour;
- the client key is best-effort from `X-Forwarded-For` first, then the socket client host.

This is enough to avoid launching a completely unguarded anonymous write endpoint. It is honestly
not a full WAF, distributed bot defense, captcha, or edge-rate-limit system.

## Still not done

1. Hosted Airtable credentials are not configured yet.
2. No HubSpot provider exists.
3. Pipeline workflow is still minimal: `pipeline_status` can move through the first five stages, but
   there is no task/follow-up scheduler, notes timeline, owner assignment, NDA flag, or deal-value
   workflow yet.
4. The public endpoint has an in-process honeypot + per-client limiter, but broad public launch still
   needs edge-level abuse controls if traffic becomes hostile.
