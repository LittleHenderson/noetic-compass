# Hosted Paid-Disk Durability Evidence — 2026-06-03

## Claim

The hosted Render service `noetic-compass-api` now has **single-host restart durability** for the state ledger and CRM lead store.

Plain English: the service has a real attached disk at `/var/data`; data written there survived a Render deploy/restart and was served back by the new process.

## Render Configuration Observed

Service:

```json
{
  "id": "srv-d82ph683kofs73d210e0",
  "name": "noetic-compass-api",
  "plan": "standard",
  "buildPlan": "starter",
  "numInstances": 1,
  "updatedAt": "2026-06-03T02:12:31.9972Z"
}
```

Disk:

```json
{
  "id": "dsk-d8fomrd8nd3s738rnee0",
  "name": "noetic-data",
  "mountPath": "/var/data",
  "sizeGB": 1,
  "serviceId": "srv-d82ph683kofs73d210e0",
  "createdAt": "2026-06-03T02:03:25.996372Z"
}
```

Relevant environment variables:

```json
[
  {"key": "NC_STATE_LEDGER_ENABLED", "value": "true"},
  {"key": "NC_STATE_LEDGER_READ_AUTHORITY", "value": "true"},
  {"key": "NC_STATE_LEDGER_PATH", "value": "/var/data/state_ledger.db"},
  {"key": "NC_CRM_LEAD_STORE_PATH", "value": "/var/data/leads.jsonl"}
]
```

## Important Failed Pre-Check

Before the disk path variables were corrected, the service had a paid instance but still wrote to `/tmp`:

```json
[
  {"key": "NC_STATE_LEDGER_PATH", "value": "/tmp/state_ledger.db"},
  {"key": "NC_STATE_LEDGER_READ_AUTHORITY", "value": "true"},
  {"key": "NC_STATE_LEDGER_ENABLED", "value": "true"}
]
```

That failed the persistence proof:

```json
{
  "lead": {
    "ok": false,
    "status": 404,
    "body": "{\"detail\":\"lead 'lead-b0aaa211f4b54b45' not found\"}"
  },
  "lead_count": 0,
  "status": {
    "posture": "enabled_ledger_read_authoritative",
    "audit_count": 0,
    "fleet_counts": {"workers": 0, "fleet_runs": 0, "fragment_refs": 0}
  }
}
```

This was a configuration failure, not an application-health failure: the app was healthy, but it was still writing to ephemeral storage.

## Corrected Baseline After `/var/data` Env Vars

After setting:

- `NC_STATE_LEDGER_PATH=/var/data/state_ledger.db`
- `NC_CRM_LEAD_STORE_PATH=/var/data/leads.jsonl`

and redeploying (`dep-d8foprn40ujc73b9caf0`, live at `2026-06-03T02:10:39.987258Z`), a new CRM lead was created:

```json
{
  "lead_id": "lead-3c5d8d3268754c1a",
  "email": "codex-disk-proof-1780452677@example.com",
  "sync_status": "sync_pending",
  "created_at": "2026-06-03T02:11:17.381465+00:00"
}
```

Then the hosted state-ledger verifier created a new post-disk audit:

```json
{
  "audit_id": "cas-dist-3aa09bc1ad35fcee",
  "posture": "enabled_ledger_read_authoritative",
  "reads_before": 0,
  "reads_after": 92,
  "divergences_found": 0,
  "workers": 2,
  "receipts": 2,
  "pass": true
}
```

## Restart Event

Triggered Render deploy:

```json
{
  "id": "dep-d8foqnhkh4rs73cque1g",
  "trigger": "api",
  "commit": "f6c9d94b3713a45e8f6d167bae8c4e32238b4ae5",
  "status": "live",
  "finishedAt": "2026-06-03T02:12:31.995960Z"
}
```

## Post-Restart Result

The CRM lead survived:

```json
{
  "lead": {
    "ok": true,
    "value": {
      "lead_id": "lead-3c5d8d3268754c1a",
      "email": "codex-disk-proof-1780452677@example.com",
      "sync_status": "sync_pending",
      "created_at": "2026-06-03T02:11:17.381465+00:00"
    }
  },
  "lead_count": 1
}
```

The state ledger rehydrated the pre-restart audit/fleet state:

```json
{
  "posture": "enabled_ledger_read_authoritative",
  "audit_count": 1,
  "fleet_counts": {
    "workers": 2,
    "fleet_runs": 1,
    "fragment_refs": 2
  },
  "divergence_tally": {
    "reads_compared": 2,
    "reads_served": 0,
    "divergences_found": 0,
    "last_divergence": null
  }
}
```

A fresh verifier run after restart also passed:

```json
{
  "audit_id": "cas-dist-2521a6be75c79773",
  "posture": "enabled_ledger_read_authoritative",
  "reads_before": 0,
  "reads_after": 110,
  "divergences_found": 0,
  "workers": 2,
  "receipts": 2,
  "pass": true
}
```

## Honest Boundary

This earns:

- Hosted single-instance restart durability for the state ledger.
- Hosted single-instance restart durability for local CRM lead capture.
- Read-authority serving from `StateStore` still passes after restart.

This does **not** earn:

- Host-loss durability. The disk is attached to one Render service instance; losing the underlying host is a separate claim.
- Multi-instance durability. `numInstances` is `1`.
- External CRM sync. The lead remains `sync_pending`; it was captured locally, not landed in HubSpot/Airtable/etc.
- Phase 4 deletion of process-global dicts. That remains held.

## Starter Instance Correction

After the first proof, Render reported the service on `plan: standard`, not the intended `starter`. The service plan was corrected through the Render API:

```json
{
  "id": "srv-d82ph683kofs73d210e0",
  "name": "noetic-compass-api",
  "plan": "starter",
  "buildPlan": "starter",
  "updatedAt": "2026-06-03T02:35:06.648377Z"
}
```

The disk and env vars remained correct:

```json
{
  "disk": {
    "id": "dsk-d8fomrd8nd3s738rnee0",
    "name": "noetic-data",
    "mountPath": "/var/data",
    "sizeGB": 1
  },
  "env": [
    {"key": "NC_STATE_LEDGER_PATH", "value": "/var/data/state_ledger.db"},
    {"key": "NC_CRM_LEAD_STORE_PATH", "value": "/var/data/leads.jsonl"},
    {"key": "NC_STATE_LEDGER_ENABLED", "value": "true"},
    {"key": "NC_STATE_LEDGER_READ_AUTHORITY", "value": "true"}
  ]
}
```

Then deploy `dep-d8fp5v57vvec739eu010` went live at `2026-06-03T02:36:40.390737Z`. After that Starter deploy:

```json
{
  "lead": {
    "ok": true,
    "lead_id": "lead-3c5d8d3268754c1a"
  },
  "lead_count": 1,
  "status": {
    "posture": "enabled_ledger_read_authoritative",
    "audit_count": 2,
    "fleet_counts": {
      "workers": 2,
      "fleet_runs": 2,
      "fragment_refs": 4
    }
  }
}
```

The hosted verifier also passed after the Starter deploy:

```json
{
  "audit_id": "cas-dist-addaf4804fe2f41a",
  "reads_served": "0->128",
  "divergences_found": 0,
  "workers": 2,
  "receipts": 2,
  "pass": true
}
```

So the final paid-disk posture is the intended one: `starter` + 1 GB disk at `/var/data`, verified after restart.
