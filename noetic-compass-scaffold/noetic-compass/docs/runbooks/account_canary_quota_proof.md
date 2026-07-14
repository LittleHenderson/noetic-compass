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
- `NC_DEBUG=false`
- `NC_STATE_LEDGER_ENABLED=true`
- `NC_STATE_LEDGER_READ_AUTHORITY=true`
- `NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE=false`
- `NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true`
- `CAS_HARNESS_EVIDENCE_ANCHOR_MODE=disabled`
- `NC_DEFAULT_LLM_PROVIDER=mock`
- `NC_ACCOUNT_BOOTSTRAP_SECRET` and legacy `ACCOUNT_BOOTSTRAP_SECRET` raw-empty/unset after
  first-owner bootstrap
- `NC_MOCK_LLM=true`
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX=cas-harness/accounts-canary/evidence-anchors`
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION=us-west-2`
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE=GOVERNANCE`
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS=31`
- nonempty canary bucket, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`
- operator-generated random `NC_PLATFORM_TENANT_PROVISIONING_SECRET` with at least 32 visible ASCII
  characters and no whitespace (the verifier validates this shape, not its entropy)
- `RENDER_SERVICE_ID=srv-d9akoolaeets73bp3e7g`
- `RENDER_SERVICE_TYPE=pserv` (private), not `web`
- `RENDER_GIT_BRANCH=release/accounts-canary-20260713`
- shared `NC_DATABASE_URL` targets the dedicated non-secret Postgres host
  `dpg-d9akobtaeets73bp29kg-a`, role `cas_harness_canary`, and single database path
  `/cas_harness_accounts_canary`

The verifier pins the stable canary service ID, Render service type, release branch, quota limit
of `2`, and parsed database hostname instead of trusting operator-supplied values. It rejects all
database URL query/path parameters so libpq routing options cannot override that hostname.
It also refuses every `PG*` environment override before constructing the Postgres client.
`RENDER_EXTERNAL_URL` is not used as a public/private signal because Render can populate it for
this private service. The verifier also requires every dark flag to be explicitly false and a
literal `127.0.0.1` or `::1` API URL. It ignores proxy environment variables and refuses HTTP
redirects. It never prints the platform secret, temporary account credentials, bearer
tokens, database URL, database password, or replacement credentials. `Dockerfile.api` installs
only this bounded verifier at
`/app/scripts/verify_account_canary_quotas.py`; the required CI container smoke proves that exact
runtime file exists, imports, and returns successful `--help` output before the image can pass.
The proof model ID is pinned to `quota-proof-local-no-provider`; focused tests keep it outside the
hosted/live-worker and customer-provider routes so `NC_MOCK_LLM=true` cannot spend provider
compute.

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

If the pre phase fails after tenant provisioning starts, its deterministic private proof
credentials may still be active. Do not simply switch to a fresh proof ID: first inspect both
proof lanes, rotate any active credentials, revoke their sessions, and reconcile or remove the
partial marker.

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
  --restart-receipt dep-0123456789abcdefghijklmn
```

The post phase must report `status=present` and prove:

- tenant A's sessions and capped counter survived the instance replacement;
- retry remains idempotent and tenant A's overflow remains exact `429`;
- tenant B reaches its own independent limit and receives its own exact `429`;
- cross-tenant reads remain `404`;
- the two synthetic adjacent-month counters survived in shared Postgres;
- both temporary account credentials were rotated to random values that are immediately discarded;
- the old derived credentials return `401` and their prior sessions return `401`.

If phase 2 fails after the restart but before credential rotation starts, diagnose the reported
assertion before retrying. Once any post-phase credential rotation begins, do not blindly rerun:
a partial rotation or marker-write failure requires reconciling both proof lanes, their sessions,
and the durable proof marker first. Use the account-canary operator controls to rotate any
remaining proof credential and revoke its sessions before declaring the exercise closed.

## Claim boundary

A successful result makes the bounded private-canary quota/retry/tenant/month/restart proof
`present`. Public account mode, public quotas, billing entitlements, Stripe, paid invoices,
steady-state production HA, and customer-production `ACCEPT` remain `OPEN` / unavailable until
their separate gates pass.
