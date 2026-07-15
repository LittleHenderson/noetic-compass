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
- Create a separate, single-use Render operator API key for this collection.
  It must be supplied only to the collector child process with the silent
  prompt below and must be able to read deploy metadata for customer service
  `srv-d9bijbjtqb8s73cn4n20`. Never add any Render account key to the production
  service environment, an environment group, a secret file, a command
  argument, command text, shell history, or either output. Do not reuse,
  revoke, or rotate an existing CI/automation key for this collection.
- Run from Render Shell on customer service `srv-d9bijbjtqb8s73cn4n20`. The collector
  refuses to run unless `RENDER_SERVICE_ID` matches that service and
  `RENDER_GIT_COMMIT` matches `--master-head`; this prevents a plausible
  receipt from being collected by a different service or source revision. The
  production image already copies this bounded collector, and its Render
  deploy readback uses only Python standard-library HTTPS support, so no
  Render CLI or additional runtime package is required.

Bootstrap ordering warning: the collector's platform-provisioned probe owners
are synthetic customer-journey identities, not the permanent primary owner.
They must neither satisfy nor block first-owner bootstrap. Account bootstrap
and startup checks are scoped to the exact granted tenant named by
`NC_ACCOUNTS_BOOTSTRAP_TENANT_ID` (normally `primary`), even though all account
records share one internal storage partition. Keep
`NC_ACCOUNT_BOOTSTRAP_SECRET` available until the permanent primary owner has
been bootstrapped and its login/recovery path is verified; never retire it
because a probe tenant merely has an active owner.

## Collect

Run this exact Bash block from the exact deployed production service
environment. It refuses a pre-existing `RENDER_API_KEY`, disables history in a
subshell, disables inherited shell tracing before the hidden read, reads the
dedicated single-use key without echo, passes it only in the collector process
environment, preserves the collector exit status, and unsets it on normal exit
or interruption:

```bash
(
  set +x
  set +o history
  trap 'unset RENDER_API_KEY' EXIT
  trap 'exit 130' HUP INT TERM

  if [[ -v RENDER_API_KEY ]]; then
    printf 'Refusing persistent RENDER_API_KEY; remove it from the service environment.\n' >&2
    exit 2
  fi

  IFS= read -r -s -p 'Temporary single-use Render API key: ' RENDER_API_KEY
  printf '\n'
  if [[ -z "$RENDER_API_KEY" ]]; then
    printf 'RENDER_API_KEY is required.\n' >&2
    exit 2
  fi

  RENDER_API_KEY="$RENDER_API_KEY" \
    python scripts/collect_hosted_customer_journey_evidence.py \
      --master-head <exact-40-character-master-sha> \
      --deploy-id <exact-live-render-deploy-id> \
      --output /tmp/hosted-customer-journey-evidence.json \
      --safe-artifact-output /tmp/hosted-customer-journey-receipt.json
  status=$?
  unset RENDER_API_KEY
  trap - EXIT HUP INT TERM
  exit "$status"
)
```

Immediately after the subshell exits, revoke only that dedicated single-use
operator key in signed-in Render Account Settings, whether collection passed
or failed. Confirm that key is no longer active before continuing. Do not
revoke or rotate an existing CI/automation key. If the single-use key was ever
entered anywhere other than the hidden prompt, treat it as exposed and revoke
it immediately.

The command intentionally pins `https://cas-harness-customer-api.onrender.com`; an
alternate origin, credentialized URL, query, or redirect target is refused.
Before any tenant, account, entitlement, audit, or share mutation, it performs
an authenticated read-only `GET` of exactly
`/v1/services/srv-d9bijbjtqb8s73cn4n20/deploys/<deploy-id>` at
`https://api.render.com`. The response must bind the supplied deploy ID and
master SHA to status `live`, trigger `new_commit`, and monotonic, non-future
`createdAt`/`finishedAt` timestamps. After share revocation and both session
logouts, the collector performs the same provider read again and requires the
entire parsed deployment response and its SHA-256 to be unchanged. A missing
key, non-200 response, redirect, identity/state/timing drift, or provider
payload mutation leaves the gate `OPEN`; the collector does not write either
output file.

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
  it contains no raw operator secret, Render API key, account credential, JWT,
  tenant/account identifier, share ID, or share token. The v3 source receipt
  records only the exact Render service/deploy facts, provider response
  SHA-256 values, HTTP statuses, and deployment timing needed to prove the two
  provider readbacks.

## Validate and publish separately

First validate the evidence against the exact live identities:

```bash
python scripts/publish_customer_production_acceptance_authority.py validate \
  --gate hosted_customer_journey \
  --evidence /tmp/hosted-customer-journey-evidence.json \
  --expected-master-head <exact-40-character-master-sha> \
  --expected-deploy-id <exact-live-render-deploy-id>
```

Publication is a separate compare-and-swap operation. Read the current gate
head, use an independently recorded authorization artifact, pin the validated
evidence SHA-256, publish, and verify the public authority endpoint readback.
Never convert a failed or partial collector result into `present` manually.
