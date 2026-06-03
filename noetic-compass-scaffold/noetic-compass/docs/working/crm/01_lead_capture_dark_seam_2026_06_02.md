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
  Body: `{email, name, organization, message, interest, source, metadata}`. Returns:
  `{lead_id, captured, sync_status, synced, schema_version, message}`.
- `GET /api/crm/leads` - authed. Sales list view, newest first.
- `GET /api/crm/leads/{lead_id}` - authed. One lead, or `404`.
- `PATCH /api/crm/leads/{lead_id}/pipeline-status` - authed. Moves one captured lead through the
  supported sales workflow stages: `new`, `contacted`, `qualified`, `won`, `lost`.

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
- `NC_CRM_PUBLIC_LEAD_RATE_LIMIT_MAX` (default `5`)
- `NC_CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS` (default `3600`)

The Airtable provider fails startup when `NC_CRM_PROVIDER=airtable` is set without token/base/table.
That is intentional: a half-configured provider would capture locally while looking externally synced.

## Airtable mapping

The provider creates one Airtable record per lead by POSTing JSON to
`/v0/{base_id}/{table_name}` with bearer-token auth. A lead reaches `synced` only when Airtable
returns a record id.

Fields sent:

- `Lead ID`
- `Email`
- `Name`
- `Organization`
- `Message`
- `Interest`
- `Source`
- `Trace ID`
- `Pipeline Status`
- `Schema Version`
- `Metadata JSON`

Operational note: the Airtable table must have compatible field names before enabling the provider.
If Airtable rejects the schema or credentials, the lead remains locally captured and is annotated
`sync_failed`.

## What the tests prove

`tests/test_crm_lead_capture.py` now covers:

- the null provider never reports a landing;
- Airtable provider construction fails loud without credentials;
- Airtable provider construction succeeds with token/base/table;
- the provider POSTs the expected record shape and marks a lead `synced` only when Airtable returns a
  real record id;
- missing record id is an error;
- a sync failure leaves the lead captured locally and annotated `sync_failed`;
- the durable JSONL store survives simulated restart;
- the public endpoint requires no auth and the sales views require auth.
- pipeline status updates require auth, bump the lead version, preserve `sync_status` / `external_id`,
  reject unknown stages, persist to the store, and return `404` for missing leads.

Targeted verification for the Airtable slice: `40 passed` in `tests/test_crm_lead_capture.py`.
Targeted verification after the pipeline-status slice: `52 passed` in
`tests/test_crm_lead_capture.py`.

## Hosted production status

Hosted Render production currently has the durable lead store under `/var/data/leads.jsonl`, but
external CRM sync is still not enabled. To turn it on:

1. Create or confirm an Airtable base/table with the fields listed above.
2. Set these Render env vars together:
   - `NC_CRM_PROVIDER=airtable`
   - `NC_AIRTABLE_TOKEN=<secret>`
   - `NC_AIRTABLE_BASE_ID=<base id>`
   - `NC_AIRTABLE_TABLE_NAME=<table name>`
3. Redeploy.
4. Submit a hosted lead through `POST /api/crm/public/leads`.
5. Confirm the response has `sync_status: "synced"`, `synced: true`, and a non-empty
   `external_id`.

Until that hosted proof passes, the honest production posture is: **captured durably, not externally
synced**.

Hosted pipeline-status smoke after `6aeb19f`: authed
`PATCH /api/crm/leads/lead-121dc923f575416d/pipeline-status` returned `200`, moved that smoke lead
to `pipeline_status: "contacted"`, bumped it to `version: 3`, and preserved
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
