# CAS Harness M4 License / API / Model Flow

Date: 2026-05-25
Owner: Agent C, M4 Model/API/License Flow
Status: Design pass only; no backend or frontend code edited

## Bottom Line

M4 should turn the Audit Console from a local/demo shell into a controlled alpha product path:

```text
License proves who may run audits.
Model connector proves what model they are auditing.
Usage limits prove how much they may run.
Session tracking proves what happened.
Evidence packets prove why CAS returned the verdict.
```

The current codebase has useful scaffolding, but it does not yet have real license enforcement, real customer API-key storage, or persistent CAS Harness audit sessions. The first implementation slice should add a license exchange endpoint and attach a tiered license identity to the existing JWT/rate-limit path before any external customer model secrets are stored.

## Files Inspected

Backend:

- `api/config.py`
- `api/main.py`
- `api/middleware/auth.py`
- `api/middleware/rate_limit.py`
- `api/middleware/audit.py`
- `api/routes/auth.py`
- `api/routes/atlas_live.py`
- `api/routes/cas_harness_audit.py`
- `api/services/cas_harness_audit_sessions.py`
- `api/models_db.py`
- `api/db.py`
- `api/store.py`
- `api/routes/wrap.py`
- `api/routes/export.py`
- `tests/test_cas_harness_audit.py`

Frontend:

- `atlas-viewer/src/App.tsx`
- `atlas-viewer/src/pages/LoginPage.tsx`
- `atlas-viewer/src/pages/LicensePage.tsx`
- `atlas-viewer/src/pages/ModelConfigPage.tsx`
- `atlas-viewer/src/pages/AuditConsolePage.tsx`
- `atlas-viewer/src/components/auth/ApiKeyManager.tsx`
- `atlas-viewer/src/components/auth/LicenseGate.tsx`
- `atlas-viewer/src/lib/casHarnessAuditApi.ts`
- `atlas-viewer/src/lib/atlasLiveApi.ts`
- `dashboard/src/api/auth.ts`
- `dashboard/src/api/client.ts`

Deploy/config:

- `render.yaml`
- `infra/render.yaml`

Roadmap/docs:

- `docs/working/cas_harness_audit_console_plan_2026_05_25.md`
- `docs/working/cas_harness_audit_console_existing_capability_audit_2026_05_25.md`
- `docs/working/atlas_viewer_full_roadmap_2026_05_22.md`

## What Already Exists

### JWT Gate

`api/middleware/auth.py` validates `Authorization: Bearer <jwt>` on protected endpoints. The decoded token sets:

- `request.state.user`
- `request.state.api_key`

`api/routes/auth.py` can mint demo dashboard JWTs. This is useful for development, but it is not a production license flow.

Current truth:

- Protected API routes already require JWT unless explicitly public.
- JWT expiry exists.
- JWT payload already has an `api_key` field that rate limiting uses.

Current gap:

- `/auth/token` is a dev/demo issuer, not account auth.
- It does not validate email ownership, invite code, license key, subscription state, or customer account status.

### Rate Limiter

`api/middleware/rate_limit.py` has in-memory tier definitions:

| Tier | Requests/min | Monthly cap |
| --- | ---: | ---: |
| community | 10 | 50 |
| professional | 30 | 500 |
| enterprise | 120 | unlimited |

Current truth:

- Rate limiting by `request.state.api_key` exists.
- Monthly usage counting exists in memory.
- Dashboard tokens bypass the monthly cap when `api_key` starts with `dashboard:`.

Current gap:

- The tier is global from env config, not per customer license.
- Counters are in memory and reset on process restart.
- There is no session cap, model slot cap, concurrent run cap, or GPU-minute cap.

### Atlas LIVE Gate

`api/routes/atlas_live.py` already shows the right alpha pattern:

- Browser never sees the worker URL.
- Session creation requires `X-Atlas-Invite-Code`.
- Per-IP and per-code abuse limits exist.
- SSE uses a short-lived stream token because browser `EventSource` cannot send custom headers.
- `/atlas/live/health/realmode` exposes real-worker verification.

This is the best existing template for M4 alpha gating.

Current gap:

- Atlas LIVE invite code is separate from CAS Harness licensing.
- The invite code does not map to a paid license, model slots, customer account, or audit history.

### Audit Console M1 API

`api/routes/cas_harness_audit.py` has session create/status/run/list routes under:

```text
/api/cas-harness/audit
```

It accepts:

- `model_id`
- `endpoint_url`
- `audit_mode`
- `prompt`
- `scenario_text`
- `selected_modules`
- `license_key`

Current truth:

- The request shape already anticipates external model endpoint and license key.
- The service strips `license_key` out of the deterministic audit hash so keys do not leak into the public audit ID.
- The session lifecycle honestly stops before verdict.

Current gap:

- `license_key` is only a placeholder field.
- No license validation happens.
- No external model endpoint validation happens.
- Sessions are stored in process memory.
- `model_status` is only `NOT_CONNECTED_MOCK`.

### Database and Assessment Storage

`api/db.py`, `api/models_db.py`, and `api/store.py` already support optional PostgreSQL storage for assessments.

Current truth:

- SQLAlchemy is already present as an optional persistent layer.
- `Assessment` records are keyed by `api_key`.
- In-memory fallback exists for local development.

Current gap:

- No tables exist for customers, licenses, API credentials, model connectors, audit sessions, audit items, or usage ledgers.

### Frontend License/API Screens

`atlas-viewer/src/pages/LoginPage.tsx`, `LicensePage.tsx`, `ModelConfigPage.tsx`, `ApiKeyManager.tsx`, and `LicenseGate.tsx` exist.

Current truth:

- The product steps exist visually.
- The pages already tell users these flows are alpha placeholders.

Current gap:

- Login does not call backend auth.
- License validation is shape-only.
- Model config only supports Pythia-160M as the current alpha model.
- API-key manager is placeholder copy.
- Audit Console API client does not attach a JWT or license token yet.

## Minimal v0.1 Alpha Flow

The M4 alpha should be simple and honest:

```text
1. User enters invite/license key.
2. API validates license key against server-side allowlist or DB.
3. API returns a short-lived JWT with license claims.
4. User configures model endpoint.
5. API validates endpoint reachability without exposing secrets.
6. User runs audit.
7. API checks tier limits before creating/running session.
8. Session is tracked under license_id + model_connector_id.
9. UI shows verdict, confidence, provenance, or an exact blocked reason.
```

### Step 1: License Exchange

Add:

```text
POST /api/cas-harness/license/activate
```

Request:

```json
{
  "license_key": "cas-alpha-...",
  "email": "user@example.com",
  "invite_code": "optional-alpha-code"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "expires_in_minutes": 60,
  "license": {
    "license_id": "lic_...",
    "tier": "professional",
    "status": "active",
    "expires_at": "2026-06-24T00:00:00Z",
    "model_slots_allowed": 3,
    "audit_sessions_per_month": 500,
    "live_sessions_per_hour": 10,
    "concurrent_sessions": 1
  }
}
```

JWT claims:

```json
{
  "sub": "user@example.com",
  "api_key": "license:lic_...",
  "license_id": "lic_...",
  "tier": "professional",
  "exp": 1770000000
}
```

Why this first:

- Reuses current JWT middleware.
- Reuses current rate limiter's `api_key` identity.
- Avoids building a full account system before alpha.
- Lets Audit Console attach one standard Bearer token to all CAS Harness API calls.

### Step 2: Model Connector Preflight

Add:

```text
POST /api/cas-harness/model-connectors/preflight
```

Request:

```json
{
  "provider": "openai-compatible",
  "endpoint_url": "https://customer.example/v1/chat/completions",
  "model_id": "customer-model-v1",
  "api_key": "secret sent once over TLS",
  "save_connector": false
}
```

Response:

```json
{
  "connector_id": "conn_ephemeral_...",
  "status": "ready",
  "support_level": "exploratory",
  "model_id": "customer-model-v1",
  "endpoint_host": "customer.example",
  "credential_fingerprint": "sha256:abc123...",
  "credential_label": "sk-...9f3a",
  "adapter_status": "openai_compatible_text_only",
  "plain_english_status": "Model endpoint responded. CAS can run text-output audit checks. Deep Atlas internals are not available for this endpoint."
}
```

Important v0.1 rule:

Do not persist customer API keys by default. Use ephemeral, server-side memory for the immediate audit run unless the user explicitly chooses "save this connector".

If "save this connector" is enabled, store only:

- encrypted credential ciphertext
- credential fingerprint hash
- provider
- endpoint host
- model id
- last four visible characters
- created_by license id
- created_at / rotated_at

Never store:

- raw API key in audit session JSON
- raw API key in evidence packet
- raw API key in logs
- raw API key in browser localStorage
- raw API key in URL query params

### Step 3: Session Creation Uses Connector ID

Update the Audit Console session create request to prefer:

```json
{
  "license_id": "lic_...",
  "model_connector_id": "conn_...",
  "audit_mode": "BALANCED",
  "scenario_text": "...",
  "selected_modules": ["verification_stack", "evidence_packet"]
}
```

Keep accepting `endpoint_url` for backward compatibility, but the safe production path is `model_connector_id`.

### Step 4: Tier Checks Before Run

Before creating or running a session, the API should check:

- license status is active
- license has not expired
- monthly audit count is below cap
- per-minute/per-hour limit is below cap
- concurrent session count is below cap
- model slot limit is not exceeded
- selected model support level allows this audit mode
- selected modules are allowed for that tier

If any check fails, the API should return a structured 402/403/409/429 style error, not a generic failure string.

## Tiers and Limits

Recommended v0.1 alpha tiers:

| Tier | Primary user | Req/min | Monthly audit sessions | Live sessions/hour | Concurrent sessions | Model slots | Model scope |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Trial | evaluator | 10 | 25 | 3 | 1 | 1 | Pythia reference + one OpenAI-compatible text endpoint |
| Community | individual | 10 | 50 | 3 | 1 | 1 | Pythia reference only unless manually approved |
| Professional | alpha partner | 30 | 500 | 10 | 1 | 3 | validated model families up to agreed size |
| Enterprise | team/account | 120 | negotiated/unlimited | negotiated | 3+ | unlimited/manual | approved architectures and private workers |

Why this tier shape:

- It matches the existing middleware tier names.
- It gives alpha partners enough room to test without leaving the GPU path unbounded.
- It separates request rate from audit session count. One audit can generate many internal requests, so "requests per minute" alone is not enough.

## Plain-English Blocked States

The Audit Console must never leave users guessing why a run did not start.

| Backend reason | UI headline | UI detail | User action |
| --- | --- | --- | --- |
| missing_license | License required | Enter the license key from your invite before running a CAS audit. | Open License |
| invalid_license | License was not accepted | This key does not match an active CAS Harness alpha license. | Check key or contact support |
| expired_license | License expired | This alpha license expired on `<date>`. Audits are paused until renewal. | Renew or request extension |
| suspended_license | License suspended | This license is paused by CAS Harness support. Existing exports remain available. | Contact support |
| monthly_cap_exceeded | Monthly audit limit reached | This license has used `<used>/<cap>` audit sessions this month. | Upgrade or wait |
| rate_limited | Too many requests | The account is sending requests faster than this tier allows. | Retry after countdown |
| concurrent_limit | Another audit is already running | This tier allows `<n>` live audit session at a time. | Wait or stop running session |
| model_slot_limit | Model slot limit reached | This tier allows `<n>` saved model connector(s). | Remove connector or upgrade |
| endpoint_unreachable | Model endpoint did not respond | CAS Harness could not reach the model endpoint. No audit was run. | Check endpoint URL/network |
| endpoint_auth_failed | Model API key was rejected | The model provider rejected the supplied API key. CAS did not store or expose it. | Replace key |
| unsupported_model | Adapter not available | CAS can audit text output, but deep internal Atlas inspection is not available for this model yet. | Run text audit or request adapter |
| module_not_allowed | Module unavailable on this tier | This license does not include `<module>`. | Disable module or upgrade |
| secret_storage_disabled | Connector not saved | Your API key was used for this run only and was not stored. | Re-enter key next run |

Copy rule:

Blocked states should say what happened, what was protected, and what to do next. Do not show stack traces or provider raw errors unless support mode is enabled.

## Secret Handling Rules

For v0.1 alpha:

1. Browser stores only the CAS Harness JWT and non-secret connector metadata.
2. Customer model API keys are entered in password fields and sent once over HTTPS.
3. Raw keys never appear in URLs.
4. Raw keys never enter session IDs, trace IDs, audit IDs, evidence packets, provenance chips, or logs.
5. API logs use `credential_fingerprint` and `credential_label`, never raw key.
6. Audit session records store `model_connector_id`, not raw credential.
7. Evidence packet records may say "credential verified" and show provider/model/host/fingerprint, but never the key.
8. If persistent credentials are added, encryption must be server-side before database write.

Recommended persistent storage fields:

```text
model_connectors
- connector_id
- license_id
- provider
- endpoint_url_host
- model_id
- support_level
- adapter_status
- credential_fingerprint_sha256
- credential_label
- encrypted_api_key
- created_at
- updated_at
- last_validated_at
- disabled_at

audit_sessions
- audit_id
- license_id
- connector_id
- audit_mode
- selected_modules
- status
- verdict_summary
- confidence_summary
- evidence_packet_trace_id
- created_at
- updated_at

usage_ledger
- ledger_id
- license_id
- event_type
- audit_id
- connector_id
- units
- created_at
- metadata_json
```

## Existing Code to Reuse

Reuse:

- JWT creation/validation shape from `api/middleware/auth.py`.
- Current rate-limit tiers as the starting vocabulary.
- Atlas LIVE invite-code and stream-token pattern for alpha gating.
- Audit Console M1 request/response shape.
- `request.state.api_key` as the first customer identity key.
- `AuditLogMiddleware` for structured request audit logs, after redaction discipline is added.
- SQLAlchemy optional DB pattern from `api/db.py`.

Do not reuse as-is:

- `/auth/token` as a customer license endpoint. It is a demo token issuer.
- Browser localStorage for raw model provider API keys.
- In-memory audit session store as production session tracking.
- Global `NC_RATE_LIMIT_TIER` as commercial tier enforcement.

## Recommended First Implementation Slice

Build M4.1 before external-model secrets:

```text
M4.1: License exchange + licensed Audit Console session gate
```

Deliverables:

1. `POST /api/cas-harness/license/activate`
   - Server-side alpha allowlist from env or small DB table.
   - Returns JWT with `api_key=license:<license_id>`, `license_id`, `tier`, and expiry.

2. `GET /api/cas-harness/license/status`
   - Returns active/expired/suspended, tier limits, usage counters, and model slots.

3. Update Audit Console client to attach `Authorization: Bearer <token>` to CAS Harness audit calls.

4. Add structured API errors for:
   - missing license
   - invalid license
   - expired license
   - monthly cap exceeded
   - concurrent session cap exceeded

5. Persist audit sessions by `license_id` when `NC_DATABASE_URL` exists.
   - Keep in-memory fallback for local tests.

6. UI surfaces a compact account strip:
   - License: Active / Expired / Suspended
   - Tier
   - Audits used this month
   - Model slots used
   - Plain-English blocked reason

Why this is first:

- It makes the product gated and trackable.
- It does not require storing customer provider keys yet.
- It makes the existing Audit Console route commercially meaningful.
- It creates the identity foundation M4.2 external model connectors need.

## M4.2 Implementation Slice

After M4.1 is green:

```text
M4.2: Ephemeral external model connector preflight
```

Deliverables:

1. `POST /api/cas-harness/model-connectors/preflight`
2. Ephemeral connector token with TTL.
3. Provider adapters:
   - OpenAI-compatible chat completion endpoint.
   - Hugging Face hosted inference endpoint.
   - Custom text generation endpoint with declared schema.
4. Safe preflight:
   - reachability
   - authentication
   - model id echo
   - tiny non-sensitive completion or `/models` probe
5. UI blocked states for unreachable, auth failed, unsupported, and exploratory.

Do not persist raw API keys in M4.2 unless the encryption path is implemented and tested.

## M4.3 Implementation Slice

```text
M4.3: Saved model slots
```

Deliverables:

1. Encrypted persistent credentials.
2. Model slot accounting per license.
3. Rotate/delete connector controls.
4. Credential health check.
5. Evidence packet redaction tests.

This is the first slice where real secret storage becomes unavoidable.

## Stakeholder-Safe Product Copy

Use:

- "License active. This account can run 500 CAS audit sessions this month."
- "Model endpoint verified. CAS can run text-output audit checks against this endpoint."
- "Deep Atlas internals are available only for validated open-weight adapters."
- "This API key was used for this run only and was not stored."
- "Audit stopped before billing because the model endpoint rejected the credential."

Avoid:

- "Works with any model."
- "We store your API key safely" before encryption is implemented.
- "Full neural inspection available" for hosted black-box APIs.
- "Unlimited audits" unless the enterprise license explicitly says so.
- "License accepted" when the page only performed a shape check.

## Open Decisions

1. Billing provider: Stripe, Paddle, LemonSqueezy, or manual enterprise only for alpha.
2. Secret storage: no persistent customer keys until encryption/KMS is selected.
3. DB requirement: M4.1 can run allowlist-from-env; persistent commercial launch needs DB.
4. Model connector scope: OpenAI-compatible text endpoints first, open-weight internal adapters second.
5. Legal copy: customer data retention and no-training language must be reviewed before external customer endpoints are invited.

## Acceptance Criteria

M4 is ready for alpha partners when:

- A user cannot create an audit session without an active license token.
- The UI shows tier, expiry, usage, and blocked reasons in plain English.
- Session records are keyed by license identity.
- No raw license key or model API key appears in logs, IDs, evidence packets, or browser storage.
- Rate/session/model-slot limits are enforced before GPU or provider calls start.
- External model endpoint support is labeled as text-output audit, deep Atlas adapter, exploratory, or unsupported.

