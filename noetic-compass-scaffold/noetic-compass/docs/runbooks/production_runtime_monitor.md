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
CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS=<positive integer>
```

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
| `unreachable` | S3 endpoint timed out or could not be reached | Check provider/network status and retry after the 30-second cache window |

Readiness proves authority and bucket capability without writing. After any
WORM fix, still run the hosted smoke with `--require-object-lock`; only a real
write, re-read, hash match, and future retention receipt proves the complete
packet path.

## Scheduled GitHub monitor

The repository-root workflow
`.github/workflows/production-runtime-monitor.yml` runs at minutes 7, 22, 37,
and 52 of each hour and can also be dispatched manually. GitHub may delay a
scheduled run during platform load. Its stable checks are:

- `production-api-dependency-readiness`
- `production-worker-realmode`
- `production-render-blueprint-drift`
- aggregate `cas-production-runtime-monitor-gate`

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

Enable GitHub Actions failure notifications for the operators responsible for
this repository. For RunPod funding continuity, use RunPod's native Billing
controls: enable Auto-Pay with an owner-approved threshold and reload amount,
keep low-balance notifications enabled, and maintain a backup payment method.
RunPod documents the threshold/reload behavior in its
[billing guide](https://docs.runpod.io/accounts-billing/billing). These are
operator/account controls, not a reason to add an account-wide RunPod key to CI.
