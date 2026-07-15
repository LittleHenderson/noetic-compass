# Customer CRM/support shared-state migration

This is phase 1 of removing the customer API's attached-disk state. It moves CRM
lead and support-ticket authority to the lifespan-owned shared StateStore while
retaining the existing JSONL files as one-time migration sources.

## Exact customer configuration

`render.customer.yaml` pins:

```text
NC_STATE_LEDGER_ENABLED=true
NC_STATE_LEDGER_READ_AUTHORITY=true
NC_DATABASE_URL=<shared Render PostgreSQL connection>
NC_CRM_LEAD_STORE_BACKEND=state_store
NC_CRM_LEAD_STORE_PATH=/var/customer-support/leads.jsonl
NC_SUPPORT_TICKET_STORE_BACKEND=state_store
NC_SUPPORT_TICKET_STORE_PATH=/var/customer-support/support_tickets.jsonl
```

In `state_store` mode, the paths are not runtime write authorities. On startup,
the API first opens the shared StateStore, strictly parses the source JSONL, and
runs an idempotent migration. A missing source is an exact empty source and gets
an explicit receipt with `source_present=false` and zero line/revision/head
counts. This is evidence of observed absence, not a claim that records moved. It
also prevents a stale file that appears later from being silently ingested after
the authority cutover. A path that exists but is not a regular file fails startup.

Each domain object is stored as:

- an immutable row for every CRM/support domain `version`; and
- a current head row that points to the exact immutable revision and carries its
  SHA-256.

The StateStore row version and the CRM/support domain version are independent.
Per-object leases serialize lifecycle transitions across processes, and the head
write also uses StateStore optimistic concurrency. Equal revision numbers with
different content fail closed.

## Exact global authority scope

Both domains are stored beneath the literal internal partition
`CONTACT_STATE_TENANT="__cas_customer_operations__"`. This value is a global
customer-operations storage and authority scope. It is not a customer tenant
ID, tenant-owner identity, customer-isolation boundary, or proof that a lead or
ticket belongs to any particular customer tenant. Code, evidence, and operator
notes must not invent customer tenancy from this value.

The lead and ticket migration markers, immutable revisions, current heads, and
private `support_crm` acceptance source binding all use this same exact scope.
Changing it would create a different authority and requires a new explicit
migration; an operator must not substitute a selected customer tenant.

## Migration contract

Before writing anything, migration reads and validates the whole UTF-8 JSONL
source. Invalid JSON, duplicate object keys at any depth, non-finite numeric
constants or overflows, blank lines, non-object rows, schema/type drift, corrupt
privacy receipts, non-contiguous histories, changed immutable fields, or
conflicting duplicate revisions fail startup. CRM history must begin at domain
revision 1 and advance exactly once per write. Legacy v1 support history must
also begin at received revision 1, follow only the real lifecycle transitions,
and preserve immutable and already-recorded lifecycle fields; regressions and
timestamp rollback fail before any destination write. The legacy stores'
skip-corrupt-row behavior is deliberately not used for migration.

After copying, migration requires exact parity for every immutable revision and
every latest head, then creates a marker containing only non-secret counts and
SHA-256 fingerprints. Re-running against unchanged bytes verifies the marker and
is a no-op. Changed source bytes, an unmarked extra/conflicting destination row,
or a mismatched marker fail closed.

Startup logs one secret-safe receipt per configured domain with only
`present`, line/revision/head counts, `already_completed`, the source SHA-256,
and the canonical-record SHA-256. No source path, PII, credential, raw record, or
provider identifier is logged.

## Acceptance-source binding after cutover

The v3 Airtable CRM source collector is Postgres-authoritative. It verifies the
lead migration marker, reads the exact immutable lead revision/current head,
and publishes keyed `lead_subject`, `airtable_record_subject`, and
`trace_subject` values. A CRM request trace is caller-supplied and potentially
low entropy, so it uses the exact global authority scope rather than a public
`trace_id_sha256`. The support/CRM finalizer separately verifies the support
migration marker and an already resolved within-SLA ticket revision/head, then
publishes a keyed `ticket_subject`. Raw ticket, lead, Airtable record, and trace
values never become public identity hashes. Raw ticket and lead IDs remain in
owner-only selectors; all four raw source values are revalidated only through
private content-addressed bindings.

All four subjects use the dedicated customer-production pseudonym keyring and
the global authority scope above. The key ID referenced by collected evidence
must remain in `NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON` through
finalization, publication, and every active-authority read, even after a new
active key is selected. Missing markers, missing immutable revisions, head
drift, source drift, or a missing retained key fails closed before public
authority mutation and while actively serving.

## What this does not prove

The checked-in privacy status remains exact `OPEN`; this change does not enable
public PII intake. The attached disk and `numInstances: 1` also remain. Therefore
this phase does not prove two-replica continuity, rolling deploys, zero
downtime, capacity, HA, `support_crm` `ACCEPT`, or overall customer-production
`ACCEPT`. A successful marker/revision read is a necessary source-authority
check, not the real consent, Airtable effect, resolved support lifecycle, SLA,
publication authorization, or active-authority receipt. Remaining file-backed
Evidence Packet/hash state must move before the disk can be removed.
