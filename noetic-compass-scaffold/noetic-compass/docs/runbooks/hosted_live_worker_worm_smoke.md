# Hosted Live Worker / WORM Smoke Runbook

Purpose: prove the hosted CAS Harness path without SSH. This runbook is for the
live worker/WORM lane only; it does not change backend routes, frontend auth,
quotas, legal copy, or account smoke scripts.

## Required Inputs

- `--base-url`: deployed CAS Harness API, for example `https://noetic-compass-api.onrender.com`
- `--bearer-token`: API bearer token, or set `CAS_HARNESS_API_TOKEN`
- `--worker-url`: hosted live worker URL, or set `ATLAS_LIVE_WORKER_URL`
- `--worker-token`: worker shared secret, or set `ATLAS_LIVE_WORKER_TOKEN`
- `--require-object-lock`: fail unless the Evidence Packet proves S3 Object Lock `GOVERNANCE` or `COMPLIANCE`

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
- Proof chips mirror packet evidence: `present` only when the underlying evidence exists, `unavailable` when it does not.

## Failure Meaning

- Worker token rejection fails: the worker is not launch-protected.
- API audit run fails after direct token success: the API likely is not sending `X-Atlas-Worker-Token` or is pointed at a different worker.
- `/verify overall` is not `all_match`: packet/hash-log/anchor verification is not production-clean.
- Object Lock mode is absent or not `GOVERNANCE` / `COMPLIANCE`: do not use WORM language.
- Verdict is `ACCEPT`: stop. The live open-weight worker smoke must not upgrade `FLAG_FOR_HUMAN_REVIEW`.
