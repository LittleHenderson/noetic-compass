# Production dependency readiness and runtime-monitor runbook

## Purpose and claim boundary

`GET /health` proves only that the API process can answer. It intentionally
stays HTTP 200 while an external dependency is down so the platform does not
restart a healthy process in a loop.

`GET /health/ready` is the deployment-readiness surface. A configured remote
live worker and a configured S3 WORM authority are load-bearing dependencies:
either one being misconfigured, unauthorized, unreachable, or unverified makes
this endpoint HTTP 503. The checks are metadata-only and cached for 30 seconds.
They do not write an object or run model inference.

A green runtime monitor is operational evidence only. It does not upgrade an
audit from `FLAG_FOR_HUMAN_REVIEW` to `ACCEPT`; production WORM and the wider
public-launch program remain `OPEN` until their own evidence gates pass.
Accounts, quotas, billing entitlements, and the billing provider remain dark.
Proof chips remain `present` only when their evidence exists and `unavailable`
when it does not.

## Resolve `Live worker blocked · service token required`

That label means the API has a non-loopback `ATLAS_LIVE_WORKER_URL`, but its
`ATLAS_LIVE_WORKER_TOKEN` is empty. The API refuses to contact a remote worker
in that half-configured state.

1. Generate one high-entropy shared service token in the approved secret
   manager. Do not put it in Git, an issue, a workflow input, a command-line
   argument, or an evidence file.
2. Set `ATLAS_LIVE_WORKER_TOKEN` to that value in the RunPod worker environment
   and restart the worker process/pod so its middleware reads the value.
3. Set the same value on the Render `noetic-compass-api` service as the
   dashboard-managed `ATLAS_LIVE_WORKER_TOKEN` secret.
4. Confirm `ATLAS_LIVE_WORKER_URL` on the API is the worker HTTP base URL (no
   `/health` suffix), then redeploy the API.
5. Check the non-secret readiness response:

   ```bash
   curl --fail-with-body https://noetic-compass-api.onrender.com/health/ready
   curl --fail-with-body https://noetic-compass-api.onrender.com/atlas/live/health/realmode
   ```

6. Run the protected end-to-end worker/WORM smoke in
   `docs/runbooks/hosted_live_worker_worm_smoke.md`. `/health/realmode` is
   deliberately public and metadata-only, so the full smoke is what also proves
   the API can authenticate a non-health worker request.

The worker token is an app-level CAS service credential. It is not a RunPod
account API key. Do not create or configure `RUNPOD_API_KEY` for readiness or
monitoring.

If the label remains after redeploy, check that both secret values are
byte-for-byte identical, neither has leading/trailing whitespace, the API URL
is the intended current worker, and both services restarted after the change.
The readiness response reports only normalized reasons; it never returns the
URL or token.

## Resolve S3 WORM readiness failures

Production WORM readiness is required when
`CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3` or the tenant Evidence Packet object
store is enabled. Configure all of these on the API service:

```text
CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET
CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION
CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE=GOVERNANCE|COMPLIANCE
CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS=<integer at least 31 for customer-production>
NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY=<stable server-only value of at least 32 bytes>
```

The receipt-attestation key must be identical across replicas and persist across
restarts. Do not rotate it until an explicit historical-receipt migration or
keyring exists; old receipts intentionally fail closed under a different key.

The readiness principal needs these bucket-level read actions on
`arn:aws:s3:::<bucket>`:

```text
s3:GetBucketObjectLockConfiguration
s3:GetBucketVersioning
```

It also retains the existing object-level permissions on the selected prefix
for real packet writes and verification. AWS documents the bucket metadata
permissions in its
[S3 API-to-policy action map](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html).
Do not broaden access to all buckets merely to make readiness green.

Common normalized reasons:

| Reason | Meaning | Operator action |
|---|---|---|
| `s3_configuration_incomplete` | Bucket, lock mode, or retention is missing | Correct the dashboard-managed variables and redeploy |
| `authentication_failed` | The active AWS credential is invalid, expired, or signed incorrectly | Rotate/fix the credential, then redeploy |
| `authority_denied` | Credential is valid but cannot read bucket lock/versioning metadata | Add only the two bucket-level read actions above |
| `bucket_unavailable` | Named bucket is absent or inaccessible | Correct the bucket/region/account binding |
| `object_lock_disabled` | S3 did not report Object Lock enabled | Use an Object-Lock-enabled bucket; do not claim WORM |
| `versioning_disabled` | Bucket versioning is not enabled | Restore versioning before resuming production writes |
| `object_lock_retention_below_minimum` | Configured retention is positive but below the 31-day customer-production minimum | Set retention to at least 31 days, redeploy, and prove a fresh write with at least 30 days remaining |
| `unreachable` | S3 endpoint timed out or could not be reached | Check provider/network status and retry after the 30-second cache window |

Readiness proves authority and bucket capability without writing. After any
WORM fix, still run the hosted smoke with `--require-object-lock`; only a real
write, re-read, hash match, configured retention of at least 31 days, and at
least 30 days remaining on the verified receipt proves the complete
customer-production packet path.

## Scheduled GitHub monitor

The repository-root workflow
`.github/workflows/production-runtime-monitor.yml` runs at minutes 7, 22, 37,
and 52 of each hour and can also be dispatched manually. GitHub may delay a
scheduled run during platform load. Runs are serialized and an in-progress run
is never canceled by a newer invocation before its alert stage. Its stable
checks are:

- `production-api-dependency-readiness`
- `production-worker-realmode`
- `production-render-blueprint-drift`
- aggregate `cas-production-runtime-monitor-gate`
- delivery `cas-production-runtime-alert-delivery`

The repository variable `CAS_PRODUCTION_API_BASE_URL` may override the default
public Render URL. The `RENDER_API_KEY` repository secret is required only for
read-only live Blueprint drift inspection. No worker or RunPod account key is
stored in GitHub.

Treat a failed aggregate as an incident:

1. Open the three component jobs and identify the first normalized failure.
2. Check `/health` separately. HTTP 200 there plus HTTP 503 from
   `/health/ready` means the process is alive and a configured dependency is
   broken; do not restart blindly.
3. Correct the provider configuration/authority, redeploy only when required,
   wait at least 30 seconds for the readiness cache, and manually dispatch the
   workflow.
4. Preserve failed workflow URLs and timestamps in the incident record. Never
   copy response secrets or dashboard environment values into it.

The delivery job creates one deduplicated open GitHub issue labeled
`cas-production-runtime-alert`, or comments on the existing issue when another
failure occurs. The workflow binds that issue to both the fixed label and fixed
title and fails on duplicate matching issues instead of updating an ambiguous
record. It records only the normalized component results and the Actions run
URL. It never copies environment values, credentials, or provider bodies. An
assigned operator must comment `ACK` with the diagnosis and next action. GitHub
issue delivery is `present`; the full customer-production alert-delivery gate
and human acknowledgement remain `OPEN` until their separate evidence
requirements pass. With the optional provider mode disabled, a later fully
green run comments a recovery receipt and closes the issue, but that automated
closure is not acknowledgement evidence. A provider-obligated incident follows
the stricter recovery sequence below.
Failure to create, update, or close the issue makes the delivery job fail rather
than silently dropping the alert.

### Optional primary on-call and secondary escalation adapter

GitHub Issues remains the default incident channel. With no additional
configuration, the workflow behaves exactly as described above: it creates or
updates the deduplicated GitHub issue, skips checkout/Python/provider/artifact
steps, and performs no provider network request. The provider path remains
`unavailable`, and the customer-production `alert_delivery` gate stays `OPEN`.

The optional `webhook_v1` mode is a **custom receipt-contract bridge**. It is
not a direct Slack, Microsoft Teams, PagerDuty, Opsgenie, SMS, or email webhook
integration. Those provider webhooks generally do not return the exact,
event-bound delivery and acknowledgement receipt below. Point these settings
only at a separately operated bridge that authenticates to the selected
provider, verifies the provider result, and translates it into this contract:

| GitHub setting | Kind | Purpose |
|---|---|---|
| `CAS_ALERT_PROVIDER_MODE=webhook_v1` | Actions variable | Explicitly enables the bridge; missing, empty, or exact lowercase `disabled` keeps it dark; other values fail closed |
| `CAS_ALERT_PRIMARY_WEBHOOK_URL` | Actions secret | HTTPS bridge endpoint for `primary_on_call` delivery |
| `CAS_ALERT_PRIMARY_WEBHOOK_TOKEN` | Actions secret | Bearer credential for the primary endpoint |
| `CAS_ALERT_ACK_WEBHOOK_URL` | Actions secret | HTTPS bridge endpoint for provider acknowledgement readback |
| `CAS_ALERT_ACK_WEBHOOK_TOKEN` | Actions secret | Bearer credential for acknowledgement readback |
| `CAS_ALERT_SECONDARY_WEBHOOK_URL` | Actions secret | HTTPS bridge endpoint for `secondary_on_call` escalation |
| `CAS_ALERT_SECONDARY_WEBHOOK_TOKEN` | Actions secret | Bearer credential for the secondary endpoint |

Enabling the mode is fail-closed: all three authenticated endpoints are
required. URLs must use public HTTPS on port 443, cannot contain credentials,
query strings, or fragments, and redirects are refused so an Authorization
header cannot be forwarded to a different origin. Tokens and URLs are read
only from the environment; they are never command-line arguments, log fields,
step-summary fields, or artifact fields.

For each monitor run, the workflow searches all issue states by the exact fixed
title before it performs an exact GitHub issue readback. It does not rely on a
mutable current label to find an incident. The issue number identifies the
incident and its `createdAt` value is the stable P1 emission clock. A wrong
title, missing base label, malformed readback, more than one open incident, or
another ambiguous inventory stops delivery. A manually closed incident with an
unsatisfied provider obligation is reopened; if more than one such closed
incident exists, the workflow fails instead of choosing one.

When provider mode is configured for a new incident, the issue is created with
both `cas-production-runtime-alert` and
`cas-production-provider-obligation` in the same GitHub operation. For an
existing incident, the workflow adds and reads back the obligation before it
posts another failure comment or invokes the bridge. Obligation state is true
when the exact label is currently present **or** the complete issue-event
history contains its exact `labeled` event. Removing the current label cannot
erase that historical obligation. A later empty/`disabled` mode therefore
cannot downgrade the incident: the adapter fails with the issue still open
until the original obligation can be satisfied.

These reads are deliberately bounded and fail closed. The workflow refuses an
issue search that fills its 1,000-result cap, more than 50 exact-title incident
records, an issue timeline beyond 100 events, a non-array response, or any
inventory/readback divergence. This keeps a truncated API result from being
mistaken for proof that no obligation exists.

The adapter hashes the repository and issue number into the stable event
identifier. Primary delivery and secondary escalation requests contain only
incident-stable bytes, so their `Idempotency-Key` (SHA-256 of the exact
canonical request) is identical across 15-minute retries and the bridge must
return the original receipt without paging the person again. ACK readback adds
the current run observation, so a later query receives a new request/key rather
than a cached acknowledgement answer. No changed request is ever sent under an
earlier idempotency key.

The bridge receives a bounded JSON request with schema
`cas_runtime_alert_adapter_request.v1`, action `deliver`, destination
`primary_on_call`, and a normalized event. The event contains only the P1
severity, stable emission time, repository, and GitHub issue reference. Current
run identity/results appear only in the separate observation attached to an ACK
readback. A successful HTTP response must be exactly one JSON object:

```json
{
  "schema_version": "cas_runtime_alert_provider_receipt.v1",
  "action": "deliver",
  "event_id_sha256": "<same 64-lowercase-hex event id>",
  "destination_role": "primary_on_call",
  "status": "delivered",
  "delivered_at_utc": "<UTC timestamp at or after emission>",
  "receipt_id": "<non-secret provider receipt identifier>"
}
```

HTTP redirects, non-200 status, more than 64 KiB, invalid UTF-8/JSON, duplicate
keys, extra or missing fields, wrong event/action/destination, a non-delivered
status, impossible timestamp, or invalid receipt identifier do not count as
delivery. If primary delivery fails, the adapter attempts the secondary path
immediately, but still fails the workflow: a fallback page never becomes a
fabricated dual-destination success.

Before the issue is 600 seconds old, a valid primary receipt leaves the adapter
in `primary_delivered_waiting_for_acknowledgement`; it does not claim a human
ACK. On the first later failing **or recovered** run, the acknowledgement bridge
receives action `check_acknowledgement` and must return exactly:

```json
{
  "schema_version": "cas_runtime_alert_provider_receipt.v1",
  "action": "check_acknowledgement",
  "event_id_sha256": "<same event id>",
  "status": "acknowledged",
  "checked_at_utc": "<UTC provider readback time>",
  "acknowledged_at_utc": "<UTC human acknowledgement time>",
  "actor_role": "incident_commander",
  "receipt_id": "<non-secret provider receipt identifier>"
}
```

For an unacknowledged incident, `status` is `unacknowledged` and both
`acknowledged_at_utc` and `actor_role` must be JSON `null`. Only an exact
`incident_commander` receipt at or after emission and no more than 600 seconds
later suppresses escalation. An explicit unacknowledged response, late ACK,
wrong role, malformed receipt, timeout, or unavailable acknowledgement bridge
triggers action `escalate` to destination `secondary_on_call`. Its successful
response uses the delivery object above with action `escalate` and destination
`secondary_on_call`. Failure to obtain that exact secondary receipt fails the
job.

Recovery cannot erase the obligation. If all component monitors turn green
before 600 seconds, a provider-marked GitHub incident remains open and the
workflow waits for a later poll. At or after 600 seconds, exact timely ACK
readback satisfies the obligation; otherwise exact secondary delivery does.
The adapter records that proof in the secret-safe JSON and the workflow must
successfully upload the artifact before it writes the machine satisfaction
marker `cas-production-provider-satisfied`.

That marker counts only when the complete event history contains an exact
`labeled` event by `github-actions[bot]` whose numeric event ID follows the
obligation event ID. Current label presence, a human-added lookalike label, or
timestamp ordering alone is not satisfaction evidence. The workflow removes
any current lookalike and re-adds the marker with its Actions identity, then
reads back both the label and bounded history. Only after that succeeds may a
recovered incident be commented and closed. A later recovery can trust the
historical machine event even if a current marker was removed.

A missing provider configuration, adapter failure, invalid/missing artifact,
artifact-upload failure, missing/ambiguous machine marker, or secondary failure
leaves or reopens the issue. Incidents with neither a current nor historical
provider-obligation marker preserve the original GitHub-only immediate
recovery behavior. Automated closure still does not assert or fabricate human
acknowledgement.

Each provider-obligated failing or recovery run uploads
`cas-runtime-alert-provider-receipts-<run-id>-<attempt>` for 30 days. The JSON
artifact is deliberately non-authoritative and `OPEN`. It includes normalized
states, timestamps, SHA-256 hashes of provider receipt identifiers and exact
response bodies, and safe reason codes. It never contains a raw provider body,
endpoint URL, token, or raw receipt identifier. The artifact helps an operator
assemble independently verified evidence; it does not publish acceptance
authority, assign an incident role, fabricate an ACK, or make customer
production `ACCEPT`.

Enable GitHub Actions failure notifications for the operators responsible for
this repository. For RunPod funding continuity, use RunPod's native Billing
controls: enable Auto-Pay with an owner-approved threshold and reload amount,
keep low-balance notifications enabled, and maintain a backup payment method.
RunPod documents the threshold/reload behavior in its
[billing guide](https://docs.runpod.io/accounts-billing/billing). These are
operator/account controls, not a reason to add an account-wide RunPod key to CI.
