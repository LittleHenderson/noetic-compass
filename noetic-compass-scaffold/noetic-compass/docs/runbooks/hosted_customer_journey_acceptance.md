# Hosted Customer Journey Acceptance Runbook

Purpose: collect the `hosted_customer_journey` gate from the real public
customer lane. This is broader than the worker/WORM smoke: it proves account
provisioning, an entitled account-scoped audit, immutable packet readback, a
read-only anonymous share through revocation, and cross-tenant non-enumeration.

The collector produces secret-safe evidence and a source receipt. It does not
publish acceptance authority or change the checked-in acceptance manifest.

## Prerequisites

- The exact protected `master` commit has passed required root CI and is the
  exact live Render deployment supplied to the command.
- Public accounts, durable sessions, billing entitlements, Evidence Packet S3
  storage, Evidence Packet sharing, quotas, and the real hosted worker are
  enabled and healthy.
- S3 authentication works and a fresh packet can be re-read with active Object
  Lock retention of at least 31 configured days and 30 days remaining.
- `NC_PLATFORM_TENANT_PROVISIONING_SECRET` and `NC_BILLING_ADMIN_SECRET` are
  available only in the production operator environment. Never place them on
  the command line or in an evidence file.
- Run from Render Shell on customer service `srv-d9bijbjtqb8s73cn4n20`. The collector
  refuses to run unless `RENDER_SERVICE_ID` matches that service and
  `RENDER_GIT_COMMIT` matches `--master-head`; this prevents a plausible
  receipt from being collected by a different service or source revision.

## Collect

Run from the exact deployed production service environment:

```powershell
python scripts/collect_hosted_customer_journey_evidence.py `
  --master-head <exact-40-character-master-sha> `
  --deploy-id <exact-live-render-deploy-id> `
  --output /tmp/hosted-customer-journey-evidence.json `
  --safe-artifact-output /tmp/hosted-customer-journey-receipt.json
```

The command intentionally pins `https://cas-harness-customer-api.onrender.com`; an
alternate origin, credentialized URL, query, or redirect target is refused.
It creates two probe tenants. The primary receives a two-hour `manual_comped`
`beta_comped` entitlement; that source represents no payment. Its anonymous
share expires after 15 minutes and is explicitly revoked sooner on the happy
path. Known shares and sessions are cleaned up on both success and failure;
response-lost login/share creation can still leave only their server-bounded
session/share lifetime. Probe account records remain durable and the
entitlement expires automatically; do not describe this as account deletion.

## Required pass conditions

- Primary tenant provisioning and account login return HTTP 200 without a
  credential echo.
- A real `EleutherAI/pythia-160m` `BALANCED` audit completes with an exact
  research verdict (`ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, or `SUPPRESS`). The
  collector does not upgrade or reinterpret that verdict.
- The owner downloads JSON for the produced trace and `/verify` returns
  `all_match`, including exactly one successful
  `merged_packet_external_anchor` re-read. The structured verifier receipt must
  bind the same bucket, key, VersionId, manifest SHA-256, mode, request time,
  and retention deadline observed through S3 GET and HEAD.
- The packet's anchor is S3 Object Lock `GOVERNANCE` or `COMPLIANCE`, configured
  for at least 31 days with at least 30 days remaining.
- Anonymous share fetch returns the exact same canonical packet, the share is
  revoked with authenticated metadata readback, and the same token then
  returns 404 or 410. Supplying that token to a management write returns 401.
- The foreign tenant receives exact 404 responses for both the audit status and
  packet, plus share creation, metadata, and revocation attempts. A 401 or 403
  is not accepted because it can disclose existence.
- Output contains only hashed tenant, account, trace, and share-token subjects;
  it contains no raw operator secret, account credential, JWT, tenant/account
  identifier, share ID, or share token.

## Validate and publish separately

First validate the evidence against the exact live identities:

```powershell
python scripts/publish_customer_production_acceptance_authority.py validate `
  --gate hosted_customer_journey `
  --evidence /tmp/hosted-customer-journey-evidence.json `
  --expected-master-head <exact-40-character-master-sha> `
  --expected-deploy-id <exact-live-render-deploy-id>
```

Publication is a separate compare-and-swap operation. Read the current gate
head, use an independently recorded authorization artifact, pin the validated
evidence SHA-256, publish, and verify the public authority endpoint readback.
Never convert a failed or partial collector result into `present` manually.
