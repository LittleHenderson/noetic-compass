# Runtime / WORM Evidence Collector

Purpose: produce the unsigned, secret-safe JSON inputs for the
`runtime_worm` customer-production gate. The collector performs one real audit
and therefore writes one fresh Evidence Packet through the deployed API. It
does not publish `/internal/acceptance/runtime-worm`, edit the acceptance
manifest, or create customer-production `ACCEPT`.

## Required inputs

- The exact protected `master` SHA deployed by the public Render service.
- The exact Render deploy ID and its live completion timestamp. A stable
  deployment may predate the runtime proof window; it remains exact protected
  provenance rather than being refreshed through a no-op redeploy.
- For the existing account-token command only, a current account bearer token
  in `CAS_HARNESS_API_TOKEN`. The preferred hosted wrapper instead creates one
  synthetic session in memory and refuses an inherited bearer.
- A Render API key with read access to the production service in
  `RENDER_API_KEY`. It is likewise environment-only.

The fixed production API is
`https://cas-harness-customer-api.onrender.com`. A different origin, redirect,
embedded credential, query, or fragment fails closed.

## Hosted Render Shell command (preferred)

The production image includes a bounded wrapper that creates one random
synthetic probe owner, grants that tenant a two-hour `manual_comped`
`beta_comped` entitlement, keeps its generated credential and bearer token in
one Python process, invokes the same runtime/WORM collector, and confirms
logout before writing either output. The synthetic owner is never the
configured primary owner and cannot authorize publication.

Use a separate single-use Render operator API key. Run this block from Render
Shell on service `srv-d9bijbjtqb8s73cn4n20`; enter the key only at the hidden
prompt, then revoke that key immediately after the command exits:

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
  if [[ -v CAS_HARNESS_API_TOKEN ]]; then
    printf 'Refusing inherited CAS_HARNESS_API_TOKEN.\n' >&2
    exit 2
  fi

  IFS= read -r -s -p 'Temporary single-use Render API key: ' RENDER_API_KEY
  printf '\n'
  if [[ -z "$RENDER_API_KEY" ]]; then
    printf 'RENDER_API_KEY is required.\n' >&2
    exit 2
  fi

  RENDER_API_KEY="$RENDER_API_KEY" \
    python scripts/collect_hosted_runtime_worm_evidence.py \
      --master-head <exact-40-character-master-sha> \
      --deploy-id <exact-live-render-deploy-id> \
      --deployed-at-utc <exact-live-finishedAt-timestamp> \
      --output /tmp/runtime-worm-evidence.json \
      --safe-artifact-output /tmp/runtime-worm-source-receipt.json
  status=$?
  unset RENDER_API_KEY
  trap - EXIT HUP INT TERM
  exit "$status"
)
```

Before the first account mutation, the wrapper re-reads and validates the
caller-selected `live` / `new_commit` deployment, exact commit, exact finish
time, and caller pin. It refuses any inherited account bearer.
Only crash-resumable tenant provisioning is retried with the exact same
payload; entitlement, login, and audit ambiguity are never retried. A
collector failure triggers best-effort
logout and writes no output. Even after success, the account and provisioning
rows remain durable, its discarded credential remains valid for
login, the entitlement expires after two hours, and the audit/WORM object is
immutable. A lost entitlement response may have committed the entitlement and
its durable ledger revision even though the wrapper does not retry or proceed.
A lost login response may have committed a durable server-side session before
the bearer is known; that unknowable session cannot be explicitly logged out
and remains until the configured session expiry (normally 60 minutes). A
process crash after login can likewise leave a session until expiry. These
failure paths write no evidence, but their durable rows remain; run exactly one
intentional probe per evidence cycle and never loop this command.

## Existing account-token command

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
   The collector checks the full canonical provider record both before and
   after the runtime/WORM probe so any deployment-record change during
   collection fails closed.
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

The gate event is the earliest of the fresh readiness observation, real-worker
observation, and WORM write. Those runtime/WORM timestamps and the evidence
observation remain inside the fixed 30-minute freshness window. The exact
deployment completion must be at or before that event, but its age does not
substitute for—or invalidate—fresh capability proof. Readiness must precede
the worker check, and the WORM write must follow it; only the receipt
validator's bounded five-second provider clock skew is accepted.

## Outputs and boundary

`runtime-worm.json` is a canonical
`cas_harness_customer_production_gate_evidence.v2` document. The
`cas_runtime_worm_source_receipt.v2` source receipt binds that fresh event and
the historical exact deployment separately. It
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
