# CAS Harness M1 Risk Audit

Date: 2026-05-25
Owner: Agent F verification/audit lane
Scope: M1 plan plus current PR #76 state in `C:\tmp\atlas-live-cockpit-integration`

## Bottom Line

PR #76 is safe as an M0 product scaffold. It gives the CAS Harness a visible Audit Console route, honest placeholder copy, a backend contract, verdict vocabulary, and reusable audit UI components.

PR #76 is not yet M1. It does not create persisted audit sessions, does not run a model, does not compute a verdict, does not validate a license, and does not create an Evidence Packet. The current API intentionally returns `SCAFFOLD_PENDING_RUNNER`, `NOT_CONNECTED_MOCK`, `verdict=null`, and `confidence=null`.

The next engineering milestone should be described as:

```text
M1: real persisted audit sessions and frontend/API wiring.
```

Do not describe M1 as:

```text
Arbitrary model auditing, production verdicts, signed Evidence Packets,
or real customer model support.
```

Those are later gates unless the implementation lands them.

## Current PR #76 State

### What Exists

- `/audit-console` frontend route.
- Audit Console product shell: connect model, run audit, get verdict, read evidence, inspect in Atlas.
- Reusable frontend audit components:
  - `ModelConnectionCard`
  - `AuditVerdictCard`
  - `ProvenanceChips`
- Pure frontend audit helpers:
  - verdict normalization
  - confidence normalization
  - six proof-style provenance chips
  - customer-safety guard for ACCEPT summaries
- Backend scaffold:
  - `POST /api/cas-harness/audit/session`
  - `GET /api/cas-harness/audit/session/{audit_id}/status`
- Backend tests proving the scaffold does not fabricate verdicts or confidence.

### What Does Not Exist Yet

- No persisted audit-session table/store.
- No `list sessions` endpoint.
- No real state machine beyond `SCAFFOLD_PENDING_RUNNER`.
- No frontend fetch from `/api/cas-harness/audit/session`.
- No license validation.
- No model connector validation.
- No audit runner.
- No durable audit items or per-item verdict rows.
- No Evidence Packet generated from audit sessions.
- No Atlas deep link generated from audit-session trace evidence.

## Top 5 Blockers Before Calling M1 "Real Sessions"

### 1. Backend Session Persistence Is Missing

Current behavior:

- `create_audit_session` hashes the request and returns a deterministic scaffold ID.
- `get_audit_session_status` returns scaffold state for any supplied `audit_id`.
- Unknown IDs are not rejected.
- There is no stored owner, created time, model target, status history, item count, or verdict row.

Why this would make us look foolish:

Technical reviewers will refresh the page or query an arbitrary ID and notice the backend is not tracking a real session.

Required M1 gate:

- Create session persists a row keyed to authenticated user/account.
- Get session returns the persisted row.
- Unknown session IDs return 404.
- Session status survives API restart if the chosen store is durable.
- Tests cover create -> get -> list -> unknown ID -> ownership isolation.

### 2. Frontend/API Schema Drift Is Already Present

Current frontend helper shape:

```text
mode: live | replay | offline
prompt
modelId
sessionId
```

Current backend route shape:

```text
audit_mode: BALANCED | HIGH_PRECISION | MAX_COVERAGE_TRIAGE
model_id or endpoint_url
prompt or scenario_text
selected_modules
license_key placeholder
```

Current page behavior:

- `AuditConsolePage` is static.
- `Run audit` is disabled because no model is connected.
- It does not call the backend route.

Why this would make us look foolish:

The UI and API can both pass their own tests while still being unable to talk to each other.

Required M1 gate:

- Frontend uses the actual backend request/response contract.
- Add an integration test that clicks `Run audit`, posts to `/api/cas-harness/audit/session`, renders the returned `audit_id`, and polls status.
- Add a contract fixture shared by backend tests and frontend tests, or generate TypeScript types from the backend OpenAPI schema.

### 3. License/Auth Is Not A Product Gate Yet

Current state:

- Backend route is protected by JWT middleware, which is good.
- `license_key` on the audit route is explicitly a placeholder.
- Frontend `AuthGate` returns children without enforcement.
- License page accepts key shape only and lets users continue without a key.

Why this would make us look foolish:

The product claim is "licensed/API users can audit their model." Today the UI has a license surface, but it is not an enforceable entitlement gate for audit sessions.

Required M1 gate:

- Session creation requires a real account/license entitlement or a named alpha allowlist.
- License failure blocks session creation with a clear error.
- Usage limits are recorded or explicitly marked "not metered in alpha."
- Tests cover missing token, expired token, missing license, invalid license, and allowed license.

### 4. Evidence Packet Is Not Connected To Audit Sessions

Current state:

- `AuditVerdictCard` can display Evidence Packet metadata.
- The audit route always returns `evidence_packet_trace_id=null`.
- Existing Evidence Packet API is disk/fixture-backed, not audit-session-backed.
- No signed packet or audit-session export is created in PR #76.

Why this would make us look foolish:

Stakeholders will reasonably ask, "Can I download the packet for this audit?" Today the honest answer is no.

Required M1/M2 boundary:

- M1 may show "Evidence Packet not created yet" for real sessions.
- M1 must not show an Evidence Packet button unless a real packet exists.
- M2 must create JSON/Markdown packet output from session rows, model proof, verdicts, and provenance.
- Tests cover packet unavailable vs packet ready.

### 5. Model Support Can Be Overclaimed Easily

Current state:

- Atlas LIVE has a verified Pythia-160M real-weight path.
- CAS Harness Audit Console does not call that path yet.
- External model endpoint fields exist only as validation shape.
- No adapter registry or model-support registry is enforced by the audit route.

Why this would make us look foolish:

Saying "connect your model of choice" before adapter validation exists invites an obvious technical challenge: "Show me a non-Pythia model run."

Required M1 gate:

- UI model support labels must distinguish:
  - supported live reference model
  - exploratory connector
  - unsupported/request adapter
- API must reject unsupported model IDs unless explicitly using a scaffold mode.
- Any real M1 demo should say "Pythia-160M reference audit session" unless another adapter is actually wired.

## Non-Blocking Strengths In PR #76

### 1. Fake Verdict/Confidence Is Currently Avoided

The page shows `NO VERDICT YET` and `Confidence not available`. The API returns `verdict=null` and `confidence=null`.

This is the right behavior for M0.

### 2. Backend Validation Is Better Than A Pure Mock

The route requires:

- model target: `model_id` or `endpoint_url`
- audit input: `prompt` or `scenario_text`
- at least one selected module
- one of the three expected audit modes

That gives M1 a reasonable front-door contract to extend.

### 3. Customer-Safety Guard Exists In The Frontend Helper

`isAuditResultCustomerSafe` blocks unsafe ACCEPT summaries unless model proof, runtime proof, CAS readout, causal proof, control proof, output proof, and packet proof are present.

This is not wired into the page yet, but the guardrail is useful.

### 4. The Docs Say The Right Boundary

The plan and existing-capability audit already warn against:

- any-model claims
- real audit verdict claims
- signed Evidence Packet claims
- fixture-backed "live audit" language

The next implementation needs to keep those boundaries visible in the UI.

### 5. Atlas LIVE Realmode Proof Is A Strong Reusable Ingredient

The Atlas side already has a realmode proof pattern:

```text
REAL_PYTHIA_WEIGHTS_LOADED
is_real_model=true
fake_runtime_env=false
model_loaded=true
load_error=null
manifest_is_real_model=true
```

M1 should reuse that pattern as the model-proof chip for supported reference runs.

## M1 Acceptance Criteria Before A Technical Demo

These are the minimum gates before saying "M1 real sessions" to a technical stakeholder:

1. `POST /api/cas-harness/audit/session` creates a persisted session.
2. `GET /api/cas-harness/audit/session/{audit_id}/status` returns the persisted session, not a synthetic response.
3. Unknown `audit_id` returns 404.
4. Session rows are tied to authenticated user/account.
5. Frontend `Run audit` calls the real backend route.
6. Frontend shows returned `audit_id`, status, model target, selected modules, and whether the session is scaffolded or real.
7. License or alpha allowlist is checked before session creation.
8. Pythia-160M reference path can attach model-proof fields from Atlas LIVE realmode.
9. Fixture/demo sessions are visibly separated from real sessions.
10. Evidence Packet button is hidden or disabled until a real packet exists.
11. Contract tests cover frontend payload vs backend schema.
12. Tests prove no ACCEPT verdict can render without required proof chips.

## Recommended Test Gates

### Backend

- `test_create_session_persists_session`
- `test_get_unknown_session_returns_404`
- `test_session_is_scoped_to_authenticated_user`
- `test_session_creation_requires_license_or_alpha_allowlist`
- `test_scaffold_session_never_returns_verdict_or_confidence`
- `test_real_reference_session_requires_realmode_model_proof`

### Frontend

- `AuditConsolePage` posts the backend payload expected by the API.
- `AuditConsolePage` renders session ID and status from API response.
- `AuditConsolePage` keeps verdict pending when backend returns null verdict.
- `AuditConsolePage` refuses to render ACCEPT if `isAuditResultCustomerSafe` returns false.
- Evidence Packet action is disabled when `evidence_packet_trace_id` is null.

### Contract

- Shared JSON fixture for create-session request and response.
- OpenAPI schema snapshot for `/api/cas-harness/audit/session`.
- Frontend type test that matches backend `audit_mode`, `selected_modules`, and response field names.

## Demo Language

Safe for PR #76:

```text
This is the CAS Harness Audit Console scaffold. It shows the product workflow
and refuses to invent a verdict or confidence before the real runner exists.
```

Safe after M1:

```text
This is a real persisted audit session. The session has an ID, owner, model
target, status, selected modules, and durable result state. Verdict generation
is only shown when the runner has produced evidence.
```

Unsafe until later:

```text
CAS Harness can audit any customer model and export signed Evidence Packets
with final ACCEPT/SUPPRESS/REVIEW verdicts.
```

## Priority Recommendation

Build M1 in this order:

1. Persist sessions and make status real.
2. Wire frontend `Run audit` to the backend.
3. Add license/alpha allowlist enforcement.
4. Add Pythia-160M reference runner connection as the first real model path.
5. Add Evidence Packet linkage only after session rows can produce packet artifacts.

This order avoids the two failure modes that would most damage credibility: fake verdicts and fake portability.
