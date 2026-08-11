The audit is verified against the `launch-scoped-beta` worktree. Every load-bearing claim checks out: `_authorize_mint` + `NC_AUTH_MINT_SECRET` shared-secret gate at `auth.py:49-99` (with the explicit "PHASE-2 SEAM" comment), the real `_build_state_store` Postgres-or-SQLite selection at `state_ledger_bootstrap.py:90-115` with documented fail-loud, and the `production/__init__.py` honesty rule confirming the billing/tenant/compliance modules are import-isolated stubs. The plan below is anchored to those real files. (Note: the audit paths are repo-relative; the working tree root is `noetic-compass-scaffold/noetic-compass/`.)

---

# CAS Harness — PAID-User Launch Security BUILD PLAN

**Scope basis:** 8 read-only audit findings, verified against the `launch-scoped-beta` worktree at `noetic-compass-scaffold/noetic-compass/`. All file paths below are repo-relative to that root unless prefixed otherwise.

**Honesty contract carried throughout (per `production/__init__.py:9-13` and MEMORY):** Stage9 40E = **scoped validation ACCEPT**, never a customer **ACCEPT**. No stub may emit a `*_VERIFIED` / `*_METERED` / `*_WORM_COMMITTED` status. A paid user gets an **ACCEPT** only when the proof gates actually pass; otherwise the console honesty gate downgrades to **FLAG_FOR_HUMAN_REVIEW**. License state is **LICENSED** / **NOT LICENSED**; compliance controls currently sit **NOT_MET**; missing data is **unavailable**; design seams are **OPEN**.

---

## 1. GROUND TRUTH — exists-to-reuse vs genuinely missing

### REAL and reusable (not stubs)

| Asset | Location | What it gives us |
|---|---|---|
| **StateStore spine** | `api/services/production/state_substrate/{interface.py,sqlite_store.py,postgres_store.py}` | Tenant-scoped, versioned (optimistic-concurrency / `VersionConflict`), lease-aware, fail-closed cross-tenant reads. `SqliteStateStore` durable single-host (WAL+fsync), `PostgresStateStore` reported built+verified PG 16.4. Both realize one locked Protocol. |
| **Backend selection + fail-loud install** | `api/state_ledger_bootstrap.py:90-115` (`_build_state_store`), `:48-57,146-176` (`install_state_ledger`) | Exactly the Postgres-when-`NC_DATABASE_URL`-else-SQLite pattern this launch needs; propagates errors loudly, unwinds partial installs. **Currently dark-by-default** (`state_ledger_enabled=False`). |
| **LedgerRecord traceability envelope** | `state_substrate/interface.py:179-232` | `parent_ids`/`source`/`trace_id` — security records inherit object-traceability for free (satisfies the project's object-traceability mandate). |
| **Fail-closed owner-scoping (the prior fix)** | `api/services/cas_harness_audit_sessions.py:90-234,318-327`; resolver `api/routes/cas_harness_audit.py:164-206` (`_caller_identity`) | REAL per-identity ownership: `owner_sub`/`owner_api_key`, `audit_id` owner-keyed, foreign reads return None/empty/404. Covers basic audit sessions **only**. |
| **Per-user scoping precedent** | `api/routes/idea_atlas.py:279-394` (`Idea.user_id == user_id`) | Working template for record-level scoping. |
| **JWT mint/verify transport** | `api/middleware/auth.py:45-84` (verify chokepoint), `:87-95` (`create_token`) | Real HS256 plumbing; single dispatch chokepoint. Payload today is `{sub, api_key, exp}` only. |
| **Phase-1 mint lock** | `api/routes/auth.py:49-99` (`_authorize_mint`) | Shared `NC_AUTH_MINT_SECRET`, constant-time compare, debug-gated-open + secret-required-in-prod. Explicitly labels itself the **"PHASE-2 SEAM"** for per-account keys. |
| **CRM lead pipeline** | `api/services/crm/*` (`JsonlFileLeadStore`) | REAL durable-under-`/var/data` prospect capture. **NOT accounts** — no role/login/account_id. Do not conflate. |
| **Safe render discipline** | `dashboard/src/components/evidence/EvidencePacket.tsx` (JSX `{...}` everywhere) | No `dangerouslySetInnerHTML`/`innerHTML`/markdown-to-HTML anywhere in `dashboard/src` or `atlas-viewer/src`. XSS sink-surface is genuinely clean. |
| **Middleware header write-point** | `api/middleware/request_id.py:29` | `BaseHTTPMiddleware` pattern a `SecurityHeadersMiddleware` can copy. |
| **Tamper-evident audit-trail design** | `api/services/production/compliance.py:290-322` (`AuditTrailEntry`), `:468-529` (`InMemoryAuditTrail.append/verify_chain`) | Correct hash-chained schema + re-walk verify. **STUB** — in-memory, test-only importer. |

### Genuinely MISSING (greenfield)

- **No account entity.** No `account_id / email / display_name / role / status / created_at / updated_at`. The only `Account` (`production/billing.py:91`) is an import-isolated stub with `id/tenant_id/status/created_at` only — no email/role.
- **No accounts/users/invites tables.** SQLite + Postgres stores define only `ledger_records` + `leases`.
- **No server-side invite system.** Atlas-live codes (`atlas_live.py:30-105`) gate streaming, create no account.
- **No session model.** No `jti`/session record/revocation list/refresh rotation. "Logout" is client-side `clearToken()`.
- **No quota/billing enforcement.** No `plan / audit_runs_used / audit_runs_limit / billing_status` anywhere. `QuotaLedger`/`PaymentProvider` are stubs (`billing.py:280,400,471`); the only quota unit modeled is accelerator-seconds.
- **No tenant model.** Distributed/fleet records live under one literal `INTERIM_TENANT="default"` (`state_substrate/migration.py:86`). Token carries no `tenant_id`.
- **No role model / RBAC.** No `role` claim, no central role dependency. Privileged actions (anchor, fleet ops, CRM views) reachable by any valid JWT.
- **No durable security audit log.** Live `noetic.audit` logger writes to stdout, no sink/rotation; ordering bug puts it INSIDE auth so failed-auth 401s are never logged.
- **No security headers / CSP** on the API or the Render static deploys; CORS `allow_credentials=True` + regex matching any `*.vercel.app`.

### Honest stub warning (do not over-credit)
`api/services/production/{billing.py,tenant_isolation.py,compliance.py}` read like production modules but are **import-isolated stubs** (`production/__init__.py:1-13`) imported only by tests. They are correct *shapes/seams*, not implementations. `supports_kms()==False`; no at-rest encryption. Never cite them as a working account/tenant/quota/audit system.

---

## 2. THE SPINE — build FIRST, cannot be parallelized

Everything else (quotas, tenant isolation, RBAC, durable audit log) reads `account_id` / `tenant_id` / `role` / `session_id` off the token or off an account record. None of those exist. **The spine is the single serialized foundation.** It is four tightly-coupled pieces that must land together because they share `middleware/auth.py`, `config.py`, and the DB layer:

**(A) Real Account model + durable accounts/invites storage**
- **Create** `api/services/accounts/models.py` — `Account(account_id, email|username unique, display_name, role, tenant_id, status[active|disabled], created_at, updated_at)` and `InviteCode(code, target_email, role, tenant_id, expires_at, max_uses, uses, redeemed_by, redeemed_at)`. Extend the *shape* of `billing.py:91` (add email/display_name/role); do not import the stub.
- **Create** `api/services/accounts/store.py` — persist via the **StateStore Protocol** as record `kind`s `"account"` and `"invite"` (reuse `LedgerRecord` envelope + `VersionConflict`). No new store engine.
- **Modify** `api/services/production/state_substrate/{sqlite_store.py,postgres_store.py}` — only if the generic `kind`-keyed `ledger_records` table cannot hold these (prefer reusing it; add tables only if a uniqueness constraint on email/code requires it).

**(B) Token claims: `account_id`, `tenant_id`, `role`, `session_id (jti)`**
- **Modify** `api/middleware/auth.py:87-95` (`create_token`) — embed `account_id`, `tenant_id`, `role`, `jti`, `iat`, `nbf`. **Server-derived only**, never from request body.
- **Modify** `api/middleware/auth.py:45-84` (dispatch) — after signature+expiry: look up session by `jti` (revoked? ) and account status (disabled?); attach `request.state.{account_id,tenant_id,role}`. This single chokepoint is what makes "revoked session" and "disabled account" pass.

**(C) Identity-based login replacing the shared-secret mint**
- **Modify** `api/routes/auth.py:49-99` — replace `_authorize_mint` shared-secret path with account lookup + invite redeem. Reject unknown/disabled. Keep the debug-gated-open path for local dev only, behind `settings.debug`, and document its removal at GA.

**(D) Central auth/role/tenant middleware contract**
- **Create** `api/dependencies/authz.py` — ONE `require_role(...)` / `require_scope(...)` FastAPI dependency returning **403** on authenticated-but-unauthorized (reuse the atlas_live 403 pattern at `atlas_live.py:91`), plus a `current_tenant()` helper wrapping the (to-be-wired) `IsolationGuard`.
- **Modify** `api/config.py` — add `accounts_enabled` / public-paid posture flag; ensure `jwt_secret` has no usable default in paid mode (fail-loud if `change-me-in-production`).

**Spine acceptance gate (must pass before ANY Phase 3+ work merges):** unknown user cannot log in; invalid/expired/used invite cannot log in; valid invite activates exactly one account; disabled account cannot log in; token carries server-derived `account_id`+`tenant_id`+`role`+`jti`; body-supplied tenant/role is ignored.

---

## 3. DEPENDENCY-ORDERED BUILD PLAN

> **Parallelization rule.** Phases 1–2 ARE the spine (§2) and are strictly sequential. Once the spine lands, Phases 3/6/8 can run in PARALLEL (disjoint files). Phases 4 and 5 both touch the spine's shared files and must be serialized against each other on those files. Shared-file contention is flagged per phase.

### PHASE 0 — Branch + harness baseline (sequential, blocks all)
- **Build:** fresh branch off `master` (see §6); confirm current internal smoke flow green before changes.
- **Files:** none modified.
- **depends_on:** —. **reuse:** existing test suite.

### PHASE 1 — Accounts + Invites (SPINE part A/C) — SEQUENTIAL
- **Build:** Account + InviteCode models/store on StateStore; redeem endpoint (fail-closed on invalid/expired/used); identity login replacing shared-secret mint.
- **Files:** create `api/services/accounts/{models.py,store.py,invites.py}`, `api/routes/accounts.py`; modify `api/routes/auth.py:49-99`, `api/config.py`.
- **depends_on:** Phase 0. **reuse:** StateStore spine, `LedgerRecord`, owner-scoping shape, `billing.py:91` Account fields, CRM `normalize_email`.
- **Contention:** `config.py`, `auth.py` — owned exclusively by spine work; no other phase may edit until §2 gate passes.

### PHASE 2 — Tokens + Sessions (SPINE part B/D) — SEQUENTIAL
- **Build:** session record (`session_id/jti`, account_id, issued_at, revoked_at, last_seen) on StateStore; `jti` in token; revoke endpoint + logout; session/status check in dispatch; central `require_role`/`current_tenant` dependency; real refresh flow (replaces client.ts random-username re-mint).
- **Files:** create `api/services/sessions/{store.py}`, `api/dependencies/authz.py`; modify `api/middleware/auth.py:45-95`; modify `dashboard/src/api/{client.ts:37-52,89-104,auth.ts}` (kill auto re-mint).
- **depends_on:** Phase 1. **reuse:** StateStore, dispatch chokepoint, `_caller_identity` pattern.
- **Contention:** `middleware/auth.py` — exclusive to spine. **End of spine: §2 gate must pass here.**

--- spine complete; the following may parallelize per the rule ---

### PHASE 3 — Tenant isolation on all customer planes — PARALLEL-ELIGIBLE (own files)
- **Build:** thread `current_tenant()`/identity into every `/distributed/*`, `/distributed/fleet/*`, and `/evidence/{trace_id}` route; add owner/tenant column to distributed + fleet records; flip `INTERIM_TENANT` to the resolved tenant (the documented one-line cutover); evidence GET/verify/anchor must verify caller owns the trace → 404 on mismatch (do NOT rely on trace_id unguessability). Wire the `IsolationGuard` stub into real use.
- **Files:** modify `api/routes/cas_harness_audit.py:1212-1530`, `api/routes/evidence.py:1225-1344`, `api/services/cas_harness_distributed_audits.py:58,315,328`, `api/services/cas_harness_fleet_executor.py`, `cas_harness_fleet_verifier.py`, `state_substrate/migration.py:86`; promote `api/services/production/tenant_isolation.py` to wired.
- **depends_on:** spine (needs `tenant_id` claim). **reuse:** audit-session owner-scoping template, idea_atlas `user_id==sub`, StateStore mandatory-tenant arg.
- **Contention:** none with Phases 6/8. Light overlap with Phase 5 on `cas_harness_audit.py` route file — coordinate (Phase 3 edits distributed/fleet/evidence routes; Phase 5 edits session/run routes).

### PHASE 4 — Quotas + Billing enforcement — SEQUENTIAL vs Phase 5 (shared route file)
- **Build:** real account/plan fields (`plan, audit_runs_used, audit_runs_limit, billing_status`) on the account record; durable `QuotaLedger` on StateStore (promote stub shape); enforcement call after `_caller_identity()` and before `create_session`/`run_session`/`create_distributed_audit` → **HTTP 402/429** at-quota or past-due; reserve-on-start / settle-on-completion (release on FAILED in `fail_session`) so failed validation does not burn quota; real `PaymentProvider` to populate `billing_status`; support/admin read path that does not reserve quota. **Decide billable unit (runs vs GPU-seconds) before coding.**
- **Files:** modify `api/routes/cas_harness_audit.py:1212,1533,1559`, `api/services/cas_harness_audit_sessions.py:263,274,320`; promote `api/services/production/billing.py` (`QuotaLedger`/`Account`/`PaymentProvider`) to wired + durable.
- **depends_on:** spine (Phase 1 account record). **reuse:** `QuotaLedger`/`InMemoryQuotaLedger` reserve/settle shape, owner-key hook point.
- **Contention:** `cas_harness_audit.py` + `cas_harness_audit_sessions.py` shared with Phase 5 — **serialize these two phases on those files.** Honesty: keep "billing OFF" honest until wired; never emit `COST_METERED` from stub data.

### PHASE 5 — RBAC / admin ops — SEQUENTIAL vs Phase 4 (shared route file)
- **Build:** apply `require_role` to currently auth-only privileged endpoints — `/evidence/{trace_id}/anchor` → operator/system; all fleet worker/lease/receipt/merge/verifier + fleet list → operator; owner-scope the two leaky list endpoints (`list_distributed_audit_sessions:1342`, `list_distributed_fleet_runs:1525`); role-gate CRM views (`crm.py:166-198`). Admin/quota-override/cross-tenant-support endpoints built on now-wired billing/tenant seams.
- **Files:** modify `api/routes/evidence.py:1268`, `api/routes/cas_harness_audit.py:1342,1353-1530,1525`, `api/routes/crm.py:166-198`; uses `api/dependencies/authz.py` (from spine).
- **depends_on:** spine (Phase 2 role claim + central dependency). **reuse:** authz dependency, owner-scoping deny-on-ambiguity→404 contract.
- **Contention:** see Phase 4. Do NOT describe pre-RBAC state as "RBAC partial" — there is no role enforcement today.

### PHASE 6 — XSS / headers / CORS — PARALLEL-ELIGIBLE (own files, no DB/auth touch)
- **Build:** `SecurityHeadersMiddleware` (CSP `default-src 'self'` + API/worker origins, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, `frame-ancestors`/`X-Frame-Options`); Render static-host header rules for dashboard + atlas-viewer (nginx.conf does NOT run on Render static); tighten CORS — constrain `cors_origin_regex` to the known domain + one preview pattern instead of all `*.vercel.app`, or drop `allow_credentials` with the wildcard. Preserve JSX-only render discipline as-is.
- **Files:** create `api/middleware/security_headers.py`; modify `api/main.py:140-155`, `api/config.py:108-113` (CORS regex — coordinate one-line edit window with spine's config.py changes), `infra/render.yaml` + repo-root `render.yaml`; add Render static headers config.
- **depends_on:** none (can start immediately after Phase 0; merge after spine to avoid `config.py` collision). **reuse:** `request_id.py` middleware pattern, existing tight `NC_CORS_ORIGINS` allowlist, `nginx.conf` header set as the CSP content source.
- **Contention:** only `config.py` (CORS lines) — sequence the merge after the spine's config edits; otherwise fully independent.

### PHASE 7 — Durable security audit log — depends on spine + Phase 3 (events reference tenant/identity)
- **Build:** durable `AuditTrail` backend on StateStore (promote the `compliance.py` hash-chain stub, persist as kind `"security_audit_log"`); instantiate in `main.py` lifespan + inject; emit explicit events at choke points — login mint/success/fail, 401/403 (incl. failed privileged access), session create/run, evidence anchor, quota/billing denial, invite/account/billing admin actions, cross-tenant denial; **FIX middleware ordering** so the audit emitter wraps `JWTAuthMiddleware` (move `AuditLogMiddleware` outermost) — today failed-auth 401s are never logged; add explicit redaction allowlist (never log Authorization header, `mint_secret`, JWT, BYOK keys; scrub query strings).
- **Files:** modify `api/main.py:152-155` (ordering), `api/middleware/audit.py`; create `api/services/audit_trail/store.py`; emit calls in `auth.py`, `middleware/auth.py`, `cas_harness_evidence_anchor.py`, quota path, accounts/invites routes.
- **depends_on:** spine (identity/tenant in events) + Phase 3 (tenant on cross-tenant events). **reuse:** `AuditTrailEntry`/`InMemoryAuditTrail.verify_chain`, `request_id` trace_id seed.
- **Contention:** `main.py` middleware stack (shared with Phase 6) — coordinate the two `main.py` edits.

### PHASE 8 — Docs + launch posture — PARALLEL-ELIGIBLE (docs only)
- **Build:** update `docs/working/production_readiness/00_index.md` and per-workstream blueprints to reflect wired vs stub; write the BETA-vs-FULL matrix (§5); add the DO-NOT-SHIP checklist (§4) as a release gate; update CHANGELOG.
- **Files:** `docs/working/production_readiness/*`, `CHANGELOG.md`.
- **depends_on:** none (track each phase). **reuse:** existing blueprint docs.

**Parallel map after spine:** `[Phase 3] ∥ [Phase 6] ∥ [Phase 8]` immediately; `[Phase 4] → [Phase 5]` serialized on the shared audit route files; `[Phase 7]` after Phase 3. Merge windows on `config.py` (Phases 1/6) and `main.py` (Phases 6/7) must be sequenced.

---

## 4. RISK FLAGS + DO-NOT-SHIP checklist (mapped to current state)

**BLOCKERS — must be fixed before any paid exposure:**

| # | Risk (current state) | Evidence | Cleared by |
|---|---|---|---|
| 1 | **Ordinary user can anchor any system WORM packet** by `trace_id` — no role gate | `evidence.py:1268`; `cas_harness_audit.py:164-206` | Phase 5 (role) + Phase 3 (tenant-own check) |
| 2 | **Cross-tenant read** of full Evidence Packets (model I/O + activations + readouts) by any authenticated caller who knows/guesses a `trace_id`; all distributed/fleet under one `INTERIM_TENANT` | `evidence.py:1225-1344`; `cas_harness_distributed_audits.py:58,315,328`; `migration.py:86` | Phase 3 |
| 3 | **Quota/paywall bypass via frontend** — shared `VITE_AUTH_MINT_SECRET` shipped in client bundle, `/auth/token` mints for ANY username, no server-side entitlement check | `dashboard/src/api/config.ts:31-39`; `auth.py:84-99`; billing stubs unwired | Spine (Phase 1–2) + Phase 4 |
| 4 | **No server-side quota/billing gate at all** — unlimited audit + distributed runs; real GPU cost-blowout + revenue leakage | `cas_harness_audit_sessions.py:286`; `cas_harness_distributed_audits.py:419,451` | Phase 4 |
| 5 | **Account state in memory** — audit sessions/verdicts in `_SESSIONS` dict; accounts/quotas are unwired stubs; lost on every redeploy/spin-down | `cas_harness_audit_sessions.py:90`; `billing.py:317,400` | Spine (StateStore-backed) |
| 6 | **Default signing secret** `change-me-in-production` forges all tokens if unset in prod (HS256) | `config.py:67` | Spine config fail-loud |
| 7 | **Identity is spoofable** — any username mints a token on one shared secret; `api_key` derivable as `dashboard:<username>`; even owner-scoped routes bypassed by minting victim's identity | `auth.py:96-98` | Spine (per-account keys) |
| 8 | **Disabled account cannot be locked out** — no account record consulted at login | (no account store) | Spine |

**HIGH — fix before GA, acceptable-with-mitigation for invite-only beta:**

| # | Risk | Evidence | Cleared by |
|---|---|---|---|
| 9 | **No durable security audit log**; failed-auth 401s never logged (audit middleware inside auth) — forensic blind spot; SOC2/ISO/GDPR controls NOT_MET | `main.py:152-155`; `compliance.py` stub | Phase 7 |
| 10 | **CORS `allow_credentials=True` + `*.vercel.app` regex** — credentialed cross-origin from attacker-hosted `*.vercel.app` | `main.py:140-148`; `config.py:108-113` | Phase 6 |
| 11 | **No CSP / security headers** on API or Render static — zero defense-in-depth for localStorage token | `middleware/__init__.py:1`; nginx.conf not on Render static | Phase 6 |
| 12 | **No RBAC** — fleet operator actions + all CRM leads reachable by any token | `crm.py:166-198`; `cas_harness_audit.py:1353-1530` | Phase 5 |

**Explicitly NOT a current risk (do not "fix"):**
- **Model text executing script:** PASS — JSX `{...}` auto-escapes; no `dangerouslySetInnerHTML`/`innerHTML`/markdown-HTML anywhere. Preserve as-is.
- **Audit logs storing secrets:** the live request logger happens not to log headers/body — but this is **incidental, not enforced**; Phase 7 must add an explicit redaction allowlist to make it a guarantee.
- **Browser bundle leaking a server-only secret:** PASS — only `VITE_` API URLs/flags + the by-design-public mint secret; no `NC_JWT_SECRET`/LLM/AWS keys.

**Missing-test risk (build these — see §6):** no test asserts auth failure, tenant isolation on distributed/fleet/evidence, role denial, or quota/billing denial. These four test families are themselves DO-NOT-SHIP items.

---

## 5. HONEST BETA-vs-FULL-PRODUCTION framing

**Launch-grade for an invite-only PAID beta (achievable this plan):**
- Per-account identity with server-derived `account_id`/`tenant_id`/`role`/`jti`; unknown/disabled/expired-invite cannot log in.
- All security state durable on StateStore (Postgres in paid mode), survives redeploy.
- Tenant isolation enforced on audit sessions **and** distributed/fleet **and** evidence packets; cross-tenant read/anchor → 404.
- Server-side quota + past-due enforcement at every run choke point (402/429); failed validation does not burn quota.
- RBAC: members cannot anchor system packets, drive fleet ops, or read CRM leads.
- Durable, hash-chained security audit log capturing logins and failed-auth.
- CSP + security headers + tightened CORS.
- **Proof honesty preserved:** a paid user gets **ACCEPT** only when the proof gates actually pass; Stage9 40E remains **scoped validation ACCEPT** (not customer ACCEPT) and the console downgrades to **FLAG_FOR_HUMAN_REVIEW** when honesty gate trips. License surfaces as **LICENSED** / **NOT LICENSED**; absent capture is **unavailable**.

**Beta-only / deferred to FULL production (call out explicitly, do not silently ship as final):**
- **localStorage Bearer token, not HttpOnly cookie.** Beta-acceptable *only behind* the new CSP + no-XSS-sink posture; the HttpOnly+Secure+SameSite cookie migration is the GA item (natural home: the Phase-2 per-account seam). Until then the token is XSS-exfiltratable and CSP is its only defense-in-depth.
- **Invite-comped billing, not real Stripe.** Beta gates on quota + an `invite/comped` `billing_status`; a real `PaymentProvider` (Stripe) that actually moves money is GA. Marketing/contracts must NOT imply metered billing exists until wired — keep "billing OFF" honest.
- **Single-host Postgres, KMS-less.** `IsolationGuard` gives logical partitioning only — no at-rest encryption (`supports_kms()==False`). Multi-host durability + KMS is GA.
- **Compliance controls remain NOT_MET** until Phase 7 ships and is externally assessed; no SOC2/ISO/GDPR claim in beta.

**What an ordinary (member-role) paid user CAN do:** create/run their own audit sessions within quota; read their own sessions, verdicts, and evidence packets; receive **ACCEPT** / **FLAG_FOR_HUMAN_REVIEW** honestly per the proof gates.
**What they CANNOT do:** anchor system WORM packets; register/lease/merge fleet workers; read other tenants' sessions/packets; read or patch CRM leads; exceed quota or run while past-due; obtain **ACCEPT** without the proof gates passing.

---

## 6. EXECUTION

**Branch (off `master`):**
```
launch/paid-security-spine
```
Land the spine here; cut phase branches (`launch/phase3-tenant-isolation`, `launch/phase6-headers-cors`, etc.) off it once the §2 gate is green.

**Targeted test strategy (write/extend in this order):**
1. `tests/test_middleware.py` — extend existing auth tests: **disabled-account rejected**, **revoked-session (jti) rejected**, body-supplied `tenant_id`/`role` ignored, no-usable-default-secret in paid mode. (This file already imports the mint-secret machinery — natural home.)
2. **New** `tests/test_accounts_invites.py` — the §2 spine gate (unknown/invalid/expired/used invite, valid-invite-activates-one-account).
3. **New** `tests/test_tenant_isolation_routes.py` — Tenant A cannot list/GET/run Tenant B distributed+fleet; cannot GET/verify/anchor Tenant B evidence by `trace_id` (→404). (Reuse `test_production_compliance.py`/state-substrate test patterns.)
4. **New** `tests/test_rbac.py` — member cannot anchor / drive fleet / read CRM; operator can; denials are **403**.
5. **New** `tests/test_quota_billing.py` — at-quota → 402/429; failed validation does not burn quota; past-due blocks; support read does not consume quota.
6. **New** `tests/test_security_headers.py` — CSP present in prod mode; CORS rejects an arbitrary `*.vercel.app` origin with credentials.
7. **New** `tests/test_audit_log.py` — login + failed-auth + anchor + quota-denial each write a durable event; secrets never appear; chain `verify_chain` holds across restart.
8. Existing **state-substrate tests** (`test_state_substrate_sqlite.py`, the migration dark-by-default tests) must stay green — they are "sacred" per `state_ledger_bootstrap.py`.

Run `pytest` from `noetic-compass-scaffold/noetic-compass/` before every commit (project rule).

**Deployment env vars required (paid mode):**
- `NC_DATABASE_URL` — **set** (Postgres DSN) so `_build_state_store` selects `PostgresStateStore`; single SQLite file pins to one instance and disables zero-downtime deploys.
- `NC_STATE_LEDGER_ENABLED=true` **and** the new public-paid posture flag — turn the durable ledger on (it is dark-by-default) and arm the fail-loud-if-no-durable-backend guard for security state.
- `NC_JWT_SECRET` — **set** to a real secret; paid-mode startup must fail loud if it equals `change-me-in-production`.
- `NC_AUTH_MINT_SECRET` — retire at GA; during beta, if the debug-open path is removed, this is moot once per-account keys land.
- `NC_CORS_ORIGINS` (tight allowlist, already defined) + `NC_CORS_ORIGIN_REGEX` narrowed off `*.vercel.app`.
- Render: confirm `/var/data` persistent disk; add static-host header rules for dashboard + atlas-viewer.

---

## 7. RECOMMENDED FIRST INCREMENT — tightest valuable PR

**PR title:** `feat(security): account model + invite redemption on StateStore + identity login (spine §2A/§2C)`

**Scope (the spine's account half — reviewable, ~1 cohesive unit):**
- **Create** `api/services/accounts/{models.py,store.py,invites.py}` — `Account` + `InviteCode` persisted via the existing StateStore Protocol as `kind="account"` / `kind="invite"` (reuse `LedgerRecord` envelope; no new store engine).
- **Create** `api/routes/accounts.py` — `POST /accounts/invite/redeem` (fail-closed on invalid/expired/used → creates/activates exactly one account) and an admin-guarded invite-create stub (role gate lands in Phase 5; for now restrict to debug/operator-secret).
- **Modify** `api/routes/auth.py:49-99` — add an **identity-based** branch: when an account exists, mint a token bound to that account's `account_id`/`tenant_id`/`role`; **keep the existing `_authorize_mint` shared-secret + debug-open path intact and unchanged as the fallback** so the current internal smoke flow does not break.
- **Modify** `api/config.py` — add `accounts_enabled` flag (default off). With it off, behavior is byte-for-byte today's; with it on, identity login is active.
- **Tests:** new `tests/test_accounts_invites.py` (the §2 invite gate) + extend `tests/test_middleware.py` for token-carries-account-claims-when-accounts-enabled.

**Why this is the right first cut:**
- It is **flag-gated (`accounts_enabled=False` default)** and leaves `_authorize_mint` and `middleware/auth.py` dispatch untouched on the default path, so **the current internal smoke flow keeps working** — satisfies "does not break the current internal smoke flow."
- It establishes the **durable account record** (clears Risk #5/#8 foundation) on the **already-proven StateStore spine** with zero new persistence engine — lowest-risk, highest-leverage.
- It is the hard prerequisite every later phase consumes; deferring the `create_token` claim-embedding + dispatch session-check to the *second* spine PR (Phase 2) keeps this PR small and keeps the single most dangerous file (`middleware/auth.py`) in its own focused review.

**Explicitly deferred from PR #1 (to keep it reviewable):** session/jti + revocation, the `require_role` dependency, quota enforcement, tenant threading on distributed/fleet/evidence, headers/CORS, audit log. Each is its own phase PR per §3.

---

**Verification note for the reviewer:** all `auth.py` / `state_ledger_bootstrap.py` / `production/__init__.py` line citations above were read directly from `.claude/worktrees/launch-scoped-beta/noetic-compass-scaffold/noetic-compass/` and match the audit. The currently checked-out branch (`wave5.5/harness-launch-declutter`) carries an *earlier, simpler* `auth.py` (open mint, no `_authorize_mint`); the spine must be built from the `launch-scoped-beta` lineage, not the declutter branch — confirm the base commit before starting.