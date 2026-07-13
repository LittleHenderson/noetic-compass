# Private account-canary quota proof

This runbook proves the quota gate only on the isolated private Render service
`cas-harness-api-accounts-canary` (`srv-d9akoolaeets73bp3e7g`). It must not be run on the public
`noetic-compass-api` service. It does not enable accounts or billing on public production, call
Stripe, create a charge, or call a paid model provider.

## Required deployed posture

Sync/deploy `render.canary.yaml` only after the protected exact-SHA CI checks pass. Keep Blueprint
Auto Sync disabled. Before starting, verify the private canary has exactly this posture:

- `NC_DEPLOYMENT_PROFILE=accounts-canary`
- `NC_ACCOUNTS_ENABLED=true`
- `NC_QUOTAS_ENABLED=true`
- `NC_QUOTA_MONTHLY_AUDIT_LIMIT=2`
- `NC_BILLING_ENTITLEMENTS_ENABLED=false`
- `NC_BILLING_PROVIDER=null`
- `NC_FLEET_SERVICE_AUTH_ENABLED=false`
- `NC_MOCK_LLM=true`
- shared `NC_DATABASE_URL` points at `cas-harness-postgres-accounts-canary`
- the service remains `pserv` (private), not a public web service

The verifier fails closed unless all of those safety conditions, the expected Render service ID,
and a loopback API URL are present. It never prints the platform secret, temporary account
credentials, bearer tokens, database URL, or replacement credentials.

## Phase 1: establish the pre-restart state

Open a Render Shell/SSH session on the canary instance, choose a new lowercase proof ID, and run:

```bash
python scripts/verify_account_canary_quotas.py pre \
  --proof-id quota-20260713a \
  --expected-service-id srv-d9akoolaeets73bp3e7g
```

The script uses local/no-provider audit sessions. With a limit of two it must report:

- tenant A reaches usage `2`;
- retrying tenant A's first audit returns `200` without another unit;
- tenant A's third logical audit returns exact HTTP `429` with
  `code=audit_quota_exceeded`, `limit=2`, `count=2`, and the current UTC period;
- tenant B can still run its first audit;
- tenant B receives `404` for tenant A's audit ID;
- adjacent `audits:2099-12` and `audits:2100-01` counters each hold one independent unit in the
  same hosted Postgres store;
- `restart_shared_postgres` is `pending_post_phase`.

Keep the JSON output as the pre-restart evidence receipt. It contains identifiers and counts only,
not credentials.

## Restart or deploy the private canary

Restart/redeploy only `srv-d9akoolaeets73bp3e7g`. Record the Render deploy/restart receipt (for
example, the `dep-...` deploy ID). Wait for the private service readiness check to pass. Do not
scale, restart, sync, or deploy the public service.

The post phase requires both a changed Render instance/container fingerprint and the operator's
control-plane receipt. A same-instance rerun cannot be presented as restart proof.

## Phase 2: prove durability and remove temporary credential access

Open a new Render Shell/SSH session on the restarted canary and run the same proof ID with the
recorded receipt. Complete both phases within the same UTC calendar month; the verifier rejects a
cross-month restart exercise so a refreshed allowance cannot be mistaken for lost durability.

```bash
python scripts/verify_account_canary_quotas.py post \
  --proof-id quota-20260713a \
  --expected-service-id srv-d9akoolaeets73bp3e7g \
  --restart-receipt dep-example-replace-with-real-id
```

The post phase must report `status=present` and prove:

- tenant A's sessions and capped counter survived the instance replacement;
- retry remains idempotent and tenant A's overflow remains exact `429`;
- tenant B reaches its own independent limit and receives its own exact `429`;
- cross-tenant reads remain `404`;
- the two synthetic adjacent-month counters survived in shared Postgres;
- both temporary account credentials were rotated to random values that are immediately discarded;
- the old derived credentials return `401` and their prior sessions return `401`.

If phase 2 fails after the restart, rerun it only after diagnosing the reported assertion. If it
fails during credential cleanup, use the account-canary operator controls to rotate the remaining
proof account credential and revoke its sessions before declaring the exercise closed.

## Claim boundary

A successful result makes the bounded private-canary quota/retry/tenant/month/restart proof
`present`. Public account mode, public quotas, billing entitlements, Stripe, paid invoices,
steady-state production HA, and customer-production `ACCEPT` remain `OPEN` / unavailable until
their separate gates pass.
