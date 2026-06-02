# CRM Doc 01 — Lead capture: the dark-by-default seam (2026-06-02)

**Status: BUILT and WIRED, capture-only. NOT yet syncing to any external CRM.** The lead-capture
pipeline is live in the app: a public form can POST a lead, it is validated, captured, and (with a
durable store configured) persisted. What it does **not** do yet is land leads in an external CRM of
record (Airtable / HubSpot / …) — by design. This doc is honest about that line.

This is the first slice of directive #4 ("start the CRM now — not operational yet, required before
public launch"). It is built to the same declared-vs-verified discipline as the rest of the platform.

## The one honesty rule (read this first)

Capturing a lead **on our side** is not the same act as landing it in the **external CRM**. The
load-bearing discriminator is the lead's `sync_status`:

| `sync_status` | Means | Who can set it |
|---|---|---|
| `captured` | Persisted on our side, durable to us. No external landing claimed. | Any capture. |
| `sync_pending` | A sync was *attempted* but the configured provider made no real landing. The dark/null default always lands here — honest that nothing left the building. | The null provider. |
| `synced` | Confirmed landed in the external CRM, backed by a real provider `external_id`. | **Only a real provider.** A stub structurally cannot. |
| `sync_failed` | A real sync attempt errored. The lead is still safely captured locally; the failure is recorded, never swallowed. | A real provider that errored. |

So a prospect is **never** told "you're in our CRM" on the strength of a local capture alone. The
`CRMSyncResult.__post_init__` guard refuses to construct a `synced=True` result without a real
`external_id` and `is_real=True` — the null provider cannot fake a landing even by mistake. This
mirrors `api/services/production/billing.py`'s `fleet_measured` vs `planner_estimate` rule, applied
to go-to-market.

## What got built

```
api/services/crm/
├── __init__.py     public exports
├── models.py       Lead / LeadSubmission / CRMSyncResult value objects + honesty guards
├── store.py        LeadStore seam: InMemoryLeadStore (dark) + JsonlFileLeadStore (durable)
├── sync.py         CRMSyncProvider ABC + NullCRMProvider (dark) + build_crm_provider() factory
└── service.py      CRMService.capture(): validate → capture (durable) → sync → annotate
api/routes/crm.py   public capture endpoint + authed sales views
tests/test_crm_lead_capture.py   37 tests (all green)
```

Wiring: `api/main.py` builds the service at startup (`build_crm_service(settings)`) and stashes it on
`app.state.crm`; the routes read it (with a dark in-memory fallback if the lifespan never ran).
`api/middleware/auth.py` allow-lists the `/api/crm/public` subtree; `api/config.py` adds the two
config knobs below.

## Endpoints

- `POST /api/crm/public/leads` — **public, no auth.** The anonymous lead-capture form posts here.
  Body: `{email (required), name, organization, message, interest, source, metadata}`. Returns an
  honest receipt: `{lead_id, captured, sync_status, synced, schema_version, message}`. A malformed
  email is a `422` — we refuse to capture an uncontactable lead. The captured lead carries the
  request's `X-Request-ID` as its `trace_id`, so it walks back to the request that created it.
- `GET /api/crm/leads` — **authed.** Sales list view, newest first.
- `GET /api/crm/leads/{lead_id}` — **authed.** One lead, or `404`.

## Configuration (both dark by default)

- `NC_CRM_PROVIDER` (default `"null"`) — which external CRM leads sync to.
  - `"null"`: capture locally, sync nothing. The honest default until a real CRM is wired.
  - `"airtable"` / `"hubspot"`: declared seams that currently **fail loud at startup** —
    `build_crm_provider` raises `CRMConfigError` because no real integration has been built. Refusing
    here keeps an operator from believing leads sync to HubSpot when nothing does. When these are
    built, they slot into `sync.py` and nowhere else changes.
- `NC_CRM_LEAD_STORE_PATH` (default unset) — where leads persist.
  - unset → `InMemoryLeadStore`: works with zero config, but **forgets on restart** and never
    pretends otherwise.
  - set → `JsonlFileLeadStore`: append-only JSON-lines, flushed + fsync'd. Real **single-host**
    durability (survives process restart). It is honestly *not* a replicated multi-host database, and
    on an ephemeral host (e.g. Render free-tier `/tmp`) the file is wiped on redeploy — a property of
    the host, not a durability the store can promise away.

## What the tests prove (37, green)

The honesty core (import-isolated, no app): the null provider never reports a landing; the factory
fails loud for unimplemented providers; a sync failure leaves the lead **captured** and annotated
`sync_failed` (never lost); the durable store returns a captured lead after a simulated restart and
keeps capture + sync annotation as two append-only lines; a stale lower-version write never rolls a
lead back. Plus route tests: the public endpoint needs no auth and never over-claims `synced`; the
sales views require auth; the `trace_id` survives the HTTP round-trip.

## Not done here (what "operational before public launch" still needs)

1. **A real provider.** Build `AirtableCRMProvider` / `HubSpotCRMProvider` behind the existing
   `CRMSyncProvider` ABC. Only then can a lead reach `synced`. Until then the honest posture is
   "captured locally, nothing synced".
2. **A durable store in the deployment.** Set `NC_CRM_LEAD_STORE_PATH` to a path on durable storage
   (not ephemeral `/tmp`). Leads are revenue records of record; losing one is losing a customer.
   (Same multi-host durability story as the state ledger — a real database is the eventual backend
   behind the unchanged `LeadStore` seam.)
3. **Pipeline / sales tooling.** `pipeline_status` (`new`→`contacted`→…) exists on the model but has
   no transition endpoint yet; no notification/routing, no dedup-merge UI.
4. **Anti-abuse on the public endpoint.** It is intentionally exempt from JWT and the per-key rate
   limiter (it's anonymous). Before public launch it needs its own abuse controls (per-IP limit /
   captcha / honeypot), mirroring the Atlas LIVE invite-gate pattern.
