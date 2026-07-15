# Runtime / WORM Evidence Collector

Purpose: produce the unsigned, secret-safe JSON inputs for the
`runtime_worm` customer-production gate. The collector performs one real audit
and therefore writes one fresh Evidence Packet through the deployed API. It
does not publish `/internal/acceptance/runtime-worm`, edit the acceptance
manifest, or create customer-production `ACCEPT`.

## Required inputs

- The exact protected `master` SHA deployed by the public Render service.
- The exact Render deploy ID and its live completion timestamp. The deployment
  must still be inside the gate's 30-minute freshness window.
- A current account bearer token in `CAS_HARNESS_API_TOKEN`. Keep the token in
  the environment; the command has no token argument, so it cannot leak through
  process arguments.
- A Render API key with read access to the production service in
  `RENDER_API_KEY`. It is likewise environment-only.

The fixed production API is
`https://cas-harness-customer-api.onrender.com`. A different origin, redirect,
embedded credential, query, or fragment fails closed.

## Command

Run from `noetic-compass-scaffold/noetic-compass`:

```powershell
$env:CAS_HARNESS_API_TOKEN = '<current account bearer token>'
$env:RENDER_API_KEY = '<read-capable Render API key>'
python scripts/collect_runtime_worm_evidence.py `
  --master-head <40-character-protected-master-sha> `
  --deploy-id <exact-public-render-deploy-id> `
  --deployed-at-utc <exact-live-deployment-timestamp> `
  --output .customer-production-evidence/runtime-worm.json `
  --safe-artifact-output .customer-production-evidence/runtime-worm-source-receipt.json
```

Clear `CAS_HARNESS_API_TOKEN` and `RENDER_API_KEY` after the command. Neither
output contains either credential.

## What must pass

1. The exact Render deploy endpoint reports the pinned deploy ID at the pinned
   commit with `status=live`, `trigger=new_commit`, and the pinned finish time.
   The collector checks it both before and after the runtime/WORM probe so a
   deployment change during collection fails closed.
2. `/health/ready` returns HTTP `200`, `ready=true`, and exact `ok` readback for
   API, CAS engine, database, real live worker, and S3 WORM configuration.
3. `/atlas/live/health/realmode` returns the exact
   `REAL_PYTHIA_WEIGHTS_LOADED` contract for
   `EleutherAI/pythia-160m`, including real manifest and loaded-model flags.
4. A nonce-bound audit completes as `FLAG_FOR_HUMAN_REVIEW`. Any `ACCEPT`
   response is a hard failure.
5. The returned packet echoes the exact nonce-bearing prompt, audit mode,
   selected modules, audit ID, model, and protected commit SHA; then
   `POST /evidence/{trace_id}/verify` returns `overall=all_match` for that exact
   trace.
6. The external-anchor check re-reads the exact S3 bucket/key/version and exact
   manifest bytes. The structured receipt must prove `GOVERNANCE` or
   `COMPLIANCE`, `retention_days >= 31`, a full configured retention window,
   and at least 30 days remaining.
7. The resulting evidence document passes the same canonical gate validator
   used by the production authority store and the final manifest verifier.

## Outputs and boundary

`runtime-worm.json` is a canonical
`cas_harness_customer_production_gate_evidence.v2` document. The source receipt
hashes the audit ID, trace ID, S3 object key, and S3 version ID; it also hashes
the worker ID while the gate document preserves the contract-required raw
worker ID. Public deployment identities (`service_id`, `deploy_id`, and commit
SHA) remain exact. Raw S3 bucket/key/version values, audit/trace IDs, and bearer
credentials are never written or printed.

The source receipt explicitly records `authority_published=false` and
`customer_production_status=OPEN`. Exit zero means only that the two local JSON
documents are internally bound and verifier-compatible. Publishing authority
is a separate authenticated operation; the final cross-gate verifier and human
release decision remain separate. Do not describe this collector as
customer-production `ACCEPT`.
