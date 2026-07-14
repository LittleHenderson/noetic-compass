# Hosted Live Worker / WORM Smoke Runbook

Purpose: prove the hosted CAS Harness path without SSH. This runbook is for the
live worker/WORM lane only; it does not change backend routes, frontend auth,
quotas, legal copy, or account smoke scripts.

## Required Inputs

- `--base-url`: deployed CAS Harness API, for example `https://noetic-compass-api.onrender.com`
- `--bearer-token`: API bearer token, or set `CAS_HARNESS_API_TOKEN`
- `--worker-url`: hosted live worker URL, or set `ATLAS_LIVE_WORKER_URL`
- `--worker-token`: worker shared secret, or set `ATLAS_LIVE_WORKER_TOKEN`
- `--require-object-lock`: fail unless the Evidence Packet proves S3 Object Lock `GOVERNANCE` or `COMPLIANCE`, configured for at least 31 days with at least 30 days remaining at verification

## Command

```powershell
python scripts/hosted_live_worker_worm_smoke.py `
  --base-url https://noetic-compass-api.onrender.com `
  --bearer-token $env:CAS_HARNESS_API_TOKEN `
  --worker-url $env:ATLAS_LIVE_WORKER_URL `
  --worker-token $env:ATLAS_LIVE_WORKER_TOKEN `
  --require-object-lock
```

## Pass Criteria

- Direct worker `/health/realmode` returns `REAL_PYTHIA_WEIGHTS_LOADED` and `is_real_model: true`.
- Direct worker request without `X-Atlas-Worker-Token` returns HTTP 401.
- Direct worker request with `X-Atlas-Worker-Token` succeeds.
- CAS Harness API audit create/run completes, proving the API sent the worker token server-side.
- The run writes an Evidence Packet and returns an `evidence_packet_trace_id`.
- The audit verdict is `FLAG_FOR_HUMAN_REVIEW`, not `ACCEPT`.
- `POST /evidence/{trace_id}/verify` returns `overall: all_match`.
- With `--require-object-lock`, packet anchor mode is `s3`, status is `anchored`, and Object Lock mode is exactly `GOVERNANCE` or `COMPLIANCE`.
- The packet reports integer `retention_days >= 31`, timezone-aware `retention_requested_at` and `object_lock_retain_until` boundaries spanning at least the full configured window, and at least 30 full days remaining when the smoke verifies it. Exactly 30 days remaining passes; anything less fails closed.
- Proof chips mirror packet evidence: `present` only when the underlying evidence exists, `unavailable` when it does not.

## Failure Meaning

- Worker token rejection fails: the worker is not launch-protected.
- API audit run fails after direct token success: the API likely is not sending `X-Atlas-Worker-Token` or is pointed at a different worker.
- `/verify overall` is not `all_match`: packet/hash-log/anchor verification is not production-clean.
- Object Lock mode is absent or not `GOVERNANCE` / `COMPLIANCE`: do not use WORM language.
- Configured retention is below 31 days, either timestamp boundary is malformed or lacks a timezone, retain-until is shorter than the configured window, or less than 30 days remain: keep customer-production `OPEN` and correct the retention configuration before writing a fresh packet.
- Verdict is `ACCEPT`: stop. The live open-weight worker smoke must not upgrade `FLAG_FOR_HUMAN_REVIEW`.
