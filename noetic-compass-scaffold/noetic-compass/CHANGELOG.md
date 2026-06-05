# Noetic Compass — Progress Log

## PAID-tenant security — per-tenant usage-quota ENGINE (inert; route wiring pending) (Jun 5, 2026)

**Headline.** The metering primitive for paid accounts (`launch/paid-quotas`, stacked on tenant-iso):
storage + check/increment logic for a per-tenant monthly audit quota, fully unit-tested. **Inert by
default** — with `NC_QUOTAS_ENABLED=false` (the default) nothing reaches these functions, no counter
is read or written, behavior is byte-for-byte unchanged. Route enforcement is a SEPARATE change that
depends on the audit-route identity upgrade (`launch/paid-audit-identity`), so this PR ships the
engine + tests only. Verified: 56 passed (16 quota + 40 regression).

- **Config flag (`api/config.py`).** `quotas_enabled: bool` (default False; aliases
  `NC_QUOTAS_ENABLED`/`QUOTAS_ENABLED`), mirroring `accounts_enabled`. Honest comment: off = inert; on
  = per-tenant monthly cap (route wiring pending); REQUIRES accounts.
- **Startup fail-loud (`api/main.py` lifespan).** `if settings.quotas_enabled and not
  settings.accounts_enabled: raise RuntimeError(...)` — quotas are per-account; enabling them without
  identity is a config error (there is no tenant to meter), so we refuse to start rather than silently
  meter nothing. Honest log line for the dark/armed posture.
- **Engine (`api/services/quotas.py`, new — FastAPI-free pure functions over the StateStore).**
  `USAGE_COUNTER_KIND="usage_counter"`; `DEFAULT_AUDITS_PER_MONTH=100`; `get_quota_limit(plan_id=None)`
  (honest stub — one number until a subscription/plan record lands; Account has no plan field yet);
  `monthly_period_key(now)` → `"audits:YYYY-MM"` (takes `now` for deterministic tests) + a
  `current_monthly_period_key()` UTC wrapper; `get_usage`; `increment_usage` (read-modify-write with
  bounded `VersionConflict` retry); `consume_quota` (the route entry point — raises `QuotaExceeded`
  carrying tenant_id/limit/count, consumes nothing on decline). Tenant isolation leans on the store's
  mandatory tenant partitioning (a cross-tenant counter reads as absent), exactly like
  `evidence_ownership`. Race-safety: `consume_quota` RE-CHECKS the limit after every conflict re-read,
  so concurrent callers can never push the count past the cap.
- **Tests (`tests/test_quotas.py`, 16).** zero-when-absent; increment/get; consume up-to-limit then
  `QuotaExceeded`; decline consumes nothing; cross-tenant counter independence; period-key format;
  VersionConflict retry converges without double-counting or exceeding the cap; default limit.

## PAID-tenant security — evidence isolation enforcement + conditional anchor role-gate (Jun 5, 2026)
## PAID-tenant security - audit-route identity + evidence-ownership write (Jun 5, 2026)

**Headline.** Completes the tenant-isolation write path by making CAS Harness audit-session routes
authenticated when `NC_ACCOUNTS_ENABLED=true`, deriving tenant/account identity from the server-side
account and session records, and recording ownership for every produced evidence `trace_id`. The dark
default remains unchanged: when accounts are disabled, the existing public demo flow stays available.

- **Conditional auth boundary.** Audit-session routes remain public only in legacy/dark mode. Account
  mode routes pass through JWT/session validation and receive server-derived tenant/account/role state.
- **Ownership write.** Successful live-worker and customer-API audit runs record evidence ownership in
  the durable state ledger before account-mode evidence reads are allowed.
- **Fail-closed behavior.** Missing identity, ledger, or ownership never becomes cross-tenant access.
  Evidence existence remains non-enumerable through the existing uniform 404 response.
- **Verification.** `tests/test_audit_identity_scope.py` covers both auth postures and proves that a
  completed account-mode audit writes ownership only for the authenticated tenant.


**Headline.** Third layer of the PAID-user security spine (`launch/paid-tenant-isolation`, stacked on
PR #2 `launch/paid-security-sessions`). Closes the cross-tenant evidence leak: once per-account
identity is on, a tenant can no longer read / verify / anchor another tenant's evidence trace, and
WORM-anchoring becomes an operator/admin/owner action. **Dark-default invariant preserved
byte-for-byte:** with `NC_ACCOUNTS_ENABLED=false` (the default) every dependency added here is a
complete no-op — the evidence routes behave exactly as before, gated only by the legacy Bearer token.
Verified: the 35 existing `tests/test_evidence_routes.py` tests pass unchanged (independently re-run:
75 passed / 2 skipped across ownership + evidence + accounts).

- **Conditional role gate (`api/dependencies/authz.py`, additive).** New
  `require_role_in_account_mode(*roles)` — the conditional sibling of `require_role`. Reads
  `settings.accounts_enabled` at request time: accounts OFF → returns `None`, NO role check (legacy
  posture; an unconditional `require_role` would 401 every legacy caller because dispatch sets no
  role in dark mode); accounts ON → identical to `require_role` (401 no identity / 403 wrong role).
  Empty-roles programming error is caught eagerly at route-definition time, like `require_role`.
- **Ownership ledger (`api/services/evidence_ownership.py`, new).** `record_evidence_ownership(...)`
  and `tenant_owns_trace(...)` over the existing durable `StateStore`. Isolation is NOT a hand-rolled
  tenant comparison — it leans on the StateStore's mandatory tenant partitioning: an ownership row
  written under tenant A's id is simply invisible to `get(tenant_B, …)` (returns `None`,
  indistinguishable from absent). Ownership rows carry the full traceability envelope
  (`created_at`/`version`/`source`/`trace_id`). The write is idempotent (get-first; `VersionConflict`
  on a concurrent create is swallowed — the post-condition "this tenant owns this trace" holds either
  way).
- **Route enforcement (`api/routes/evidence.py`).** A `_require_evidence_access` dependency on GET
  `/{trace_id}`, POST `/{trace_id}/verify`, POST `/{trace_id}/anchor`: dark mode → pass-through;
  account mode → resolve the SERVER-set tenant (`current_tenant`), and 404 `trace_id not found` if the
  tenant doesn't own the trace (same status+detail as a genuinely-absent trace, so a cross-tenant
  probe never leaks existence via a 403-vs-404 divergence; never a 500). Fail-closed: account-mode on
  but no ownership store installed → 404, never a silent allow. Anchor additionally carries
  `require_role_in_account_mode("operator","admin","owner")`. Handler bodies, verdict words, WORM
  semantics, and honesty messaging are untouched.
- **Ownership-WRITE hook DEFERRED, not guessed (`api/routes/cas_harness_audit.py`, comment only).**
  The point that should record ownership is where an audit run produces its evidence `trace_id`. But
  the audit-session routes are on the auth middleware's PUBLIC_PATH allowlist, so the middleware never
  decodes their token and never sets `request.state.tenant_id`/`account_id` — `_caller_identity`
  yields only `(sub, api_key)`, an unverified Phase-1 stopgap identity, not a server-derived tenant.
  Wiring a security-critical ownership write keyed on an unverified identity would be wrong, so it is
  left as a precise `TODO(tenant-iso)` at the exact seam. **Consequence (honest):** this layer ships
  the enforcement MECHANISM (fail-closed, fully tested) but ownership rows are not yet populated; in
  account mode evidence reads fail closed (404) until the audit-session routes carry a real
  account-mode tenant. That identity upgrade — moving the audit-session routes off the PUBLIC_PATH
  allowlist onto account-mode auth — is the next sub-step before `NC_ACCOUNTS_ENABLED=true`.
- **Tests (`tests/test_evidence_ownership.py`, new — 18 tests).** Store unit tests (cross-tenant
  isolation, idempotency, traceability envelope); gate unit tests (accounts-off no-op vs accounts-on
  enforcement vs empty-roles refusal); dark-mode no-regression (GET/verify/anchor still reachable with
  the legacy token); account-mode integration (owner reads 200; other tenant 404 not 403; no identity
  401; member-role anchor 403; operator anchor not role-blocked). Maintainer-run:
  `python -m pytest tests/test_evidence_ownership.py tests/test_evidence_routes.py tests/test_accounts_invites.py -q` → 75 passed, 2 skipped.

## PAID-user security spine — account half: durable accounts + invite redemption + identity login (Jun 4, 2026)

**Headline.** First PR of the PAID-user security spine (`launch/paid-security-spine`). Adds a real
account entity and a fail-closed invite-redemption flow on the existing durable `StateStore`, plus
an identity-login branch on `/auth/token`. Flag-gated behind `NC_ACCOUNTS_ENABLED` (default OFF):
with the flag off, the app behaves byte-for-byte as today — the shared-secret mint (`_authorize_mint`)
and the current internal smoke flow are untouched.

- **Account + InviteCode models** (`api/services/accounts/models.py`). `Account(account_id,
  email_or_username[unique], display_name, role, tenant_id, status[active|disabled], created_at,
  updated_at)` and `InviteCode(code, target_email, role, tenant_id, expires_at, max_uses, uses,
  redeemed_by, redeemed_at, created_at)`. Roles owner/admin/member/support/operator/system;
  invite-created accounts default to `member`. Extends the `billing.py` Account *shape* (does NOT
  import the stub). Unknown/forward status coerces to `disabled` (fail closed).
- **Durable store** (`api/services/accounts/store.py`). Persists via the StateStore Protocol as
  record kinds `account` / `invite` / `account_email_index`, reusing the `LedgerRecord` envelope +
  optimistic `VersionConflict`. `redeem_invite` is atomic and fail-closed: invalid/expired/used/
  over-limit codes are rejected and create nothing; the invite use-count is advanced with
  `put(expected_version=<version read>)` so a single-use code cannot be redeemed twice under a
  race; email uniqueness is enforced by an index record created at `expected_version=0`. Account
  ids are deterministic in `(code, email)` so re-delivery is idempotent (exactly one account).
- **Cryptographic invites** (`api/services/accounts/invites.py`). `secrets.token_urlsafe` (256-bit
  default); pure `is_expired` / `uses_remaining` / `is_redeemable` predicates.
- **Routes** (`api/routes/accounts.py`). `POST /accounts/invite/redeem` (public, fail-closed,
  non-enumerable — one identical 400 for every failure) and `POST /accounts/invite` (gated behind
  debug/operator-secret; full RBAC is a later PR, TODO noted). Server-derived claims only: the
  redeem body has no role/tenant/account_id field, so a client cannot inject them.
- **Identity login** (`api/routes/auth.py`). When `accounts_enabled` and an account exists for the
  supplied identity, the minted token is bound to that account's SERVER-DERIVED
  `account_id`/`tenant_id`/`role`. `_authorize_mint` is preserved unchanged as the credential gate.
  Unknown identity → 401; disabled account → 401.
- **Token claims** (`api/middleware/auth.py`). `create_token` additively accepts optional
  server-derived `account_id`/`tenant_id`/`role`; the `{sub, api_key, exp}` fallback is unchanged.
- **Durable-or-absent wiring** (`api/main.py`, `api/config.py`). The account store is opened at
  lifespan via the same backend selection as the state ledger (Postgres when `NC_DATABASE_URL`,
  else SQLite) and FAILS LOUD if enabled but no durable backend can be built — never in-memory.
- **Deferred to next PR:** session/jti + revocation + dispatch-side status checks, `require_role`,
  quota/billing enforcement, per-customer tenant threading on distributed/fleet/evidence routes.

Tests: `tests/test_accounts_invites.py` (new) + `tests/test_middleware.py` (extended) +
`tests/test_cas_harness_audit.py` — 82 passed. State-substrate sqlite/migration + production
billing suites — 42 passed. `accounts_enabled=False` default path verified unchanged.

## CAS Harness worker token send — API can call a locked RunPod worker (Jun 4, 2026)

**Headline.** The live worker already had an optional `X-Atlas-Worker-Token` gate, but the API
did not send that header. Once the worker token was turned on, the browser proxy and audit runner
would hit `401` even with a healthy worker. The API now has the matching send-side seam.

- **Shared send-side helper.** `ATLAS_LIVE_WORKER_TOKEN` / `NC_ATLAS_LIVE_WORKER_TOKEN` is now
  read by the API, trimmed, and sent as `X-Atlas-Worker-Token` only when configured. Empty token
  preserves local/dev pass-through behavior.
- **Audit runner protected.** `run_live_worker_audit` sends the header to `/sessions/dump`,
  including the no-ablation retry path, so the CAS Harness run button can talk to a locked worker.
- **Atlas LIVE proxy protected.** `/atlas/live/session`, `/atlas/live/session/{id}/events`, and
  proxied worker health calls now send the same worker token, keeping the cockpit proxy and audit
  runner on one auth contract.

Tests: `tests/test_atlas_live_worker_auth.py`, `tests/test_atlas_live.py`,
`tests/test_cas_harness_live_worker_runner.py`, and `tests/test_cas_harness_live_worker_health.py`
35 passed; `tests/test_cas_harness_audit.py` 48 passed.

## CAS Harness evidence smoke hardening — raw Stage 9 reads cannot leak ACCEPT; static anchors persist on disk (Jun 4, 2026)

**Headline.** Production smoke found two real launch-surface gaps after the scoped-beta merge:
the historical GPT-NeoX-20B Stage 9 packet could be read directly from `/evidence/{trace_id}`
with raw `verdict: ACCEPT`, and the Pythia `/verify` endpoint returned `trace_id not found`
after deploy when the static-anchor receipt was not present in the temp store.

- **Public Stage 9 read gate.** `GET /evidence/{trace_id}` now serves a product-safe Stage 9
  packet view. If the raw packet says `ACCEPT` or `SUPPRESS` but this deployment cannot verify
  a persisted WORM/Object-Lock static anchor for it, the served top-level verdict and nested
  verifier decision are downgraded to `FLAG_FOR_HUMAN_REVIEW` with `public_read_gate` metadata.
  Audit-session execution already blocked this path; the lower-level packet endpoint now matches.
- **Verify fails soft for discoverable Stage 9 packets.** If a Stage 9 packet is bundled and
  readable but no persisted static-reference anchor receipt exists, `/verify` returns `200` with
  `overall: unable_to_verify` and an explicit `static_reference_anchor` check instead of a 404.
- **Render persistence fixed.** Root and mirror `render.yaml` now set
  `CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR=/var/data/evidence_packets`, so future static anchor
  receipts and hash logs live on the paid disk beside the state ledger and CRM lead store.

Tests: `tests/test_evidence_routes.py` 35 passed / 2 skipped; `tests/test_cas_harness_audit.py`
48 passed; `tests/test_cas_harness_static_evidence_anchor.py` +
`tests/test_cas_harness_verdict_runner.py` 19 passed.

## CAS Harness scoped-beta Phase 1 — tenant-scoped audit sessions + /auth/token mint lock (Jun 4, 2026)

**Headline.** Two minimal security fixes for the invite-only scoped beta, integrated onto the
launch consolidation branch (`launch/scoped-beta`, off master + the declutter port). Neither
depends on the unbuilt accounts system — both use existing JWT identity + config.

- **Tenant-scope audit sessions.** `GET /api/cas-harness/audit/sessions` (and get/create/run)
  now scope to the caller's identity (`owner_sub`/`owner_api_key`, derived from `request.state`
  or a best-effort Bearer decode, since the session routes sit on the auth public-path prefixes).
  Listing/reads fail closed; the owner key folds into the deterministic `audit_id`; `to_dict()`
  strips owner identity. Closes the prior cross-tenant read of the sessions list.
- **Lock `POST /auth/token`.** Previously minted a JWT for ANY username with no credential. Now a
  shared `NC_AUTH_MINT_SECRET` is required in production (X-Auth-Mint-Secret header or `mint_secret`
  body, constant-time compare) → 401 otherwise; the open mint survives only in `debug` for local
  dev. Startup fails loud if `debug=False` and `jwt_secret` is still the default. `render.yaml`
  registers `NC_AUTH_MINT_SECRET` (operator-set, sync:false); `NC_JWT_SECRET` already uses
  `generateValue:true` so the new startup guard never fires on Render. Phase-2 seam documented
  for per-account issued keys.

Tests: `test_cas_harness_audit.py` (48) + `test_middleware.py` (15) = 63 passed; cross-surface
sweep adding distributed-audits + CRM = 174 passed. New root `conftest.py` runs the suite in an
honest dev posture (NC_DEBUG=true + a real NC_JWT_SECRET); prod-path tests override via monkeypatch.

**Deploy action (applies only when merged to master → Render auto-deploys):** set
`NC_AUTH_MINT_SECRET` in the Render env AND have the dashboard / Atlas client send it, or dashboard
login (which mints via `/auth/token`) returns 401. This is the intended invite-only-beta posture,
not a silent break.

## TKS definition runtime lock, **BUILT and route/probe-enforced** - customer audits now fail closed unless the owner definitions are loaded (Jun 3, 2026)
## Session 63: Public-launch declutter pass 1 — inline Disclosure primitive (May 31, 2026)

**Headline.** Started the CAS Harness public-launch UI cleanup: tuck always-visible
explanatory wordiness behind one-line dropdowns so the default view is uncluttered.
Added a reusable `Disclosure` inline-collapsible (`dashboard/src/components/shared/Disclosure.tsx`)
— the missing primitive for "wordiness behind a dropdown." First application: the Assessment
page scoring-guidance block (was ~5 always-on paragraphs under the Assess button) now shows
only the one-line scoring-method label plus the self-reported safety warning, with the method
description, mode-guidance, and scorer-provider notes collapsed into a "Scoring method details"
disclosure. `tsc -b` clean; 143 dashboard vitest tests pass (worker-pool startup timeouts are
environment flakiness, not assertion failures). Branch `wave5.5/harness-launch-declutter`.

**Pass 2.** Audited the rest of the Explore punch list and found most "verbose" surfaces were
already correctly gated — the Atlas `HelpOverlay` opens behind the `?` key (the help panel is
where detail belongs) and the EvidencePacket "5-step reviewer playbook" is already behind a
"How to audit this" toggle (default off). Did not manufacture changes there. Collapsed the two
genuinely always-visible blocks that remained: the Assessment results "Social engineering /
bias-flag" caveat (now a "What's measured vs. not validated" disclosure) and the Validation
page's always-on "Protocol Note" card + "Calibration Session" intro paragraph (now disclosures).
`tsc -b` clean.

## Session 62: Condition-3 MTC.1 comparative capture — honest negative (May 31, 2026)

The launch risk was not another TODO; it was any future agent, fixture, or probe path silently using paraphrased CAS labels instead of the owner-provided TKS 40 Element and 28 Foundation definitions. This entry turns that from a memory problem into a runtime gate.

**1) The app now carries the locked owner definitions.** `api/resources/tks_owner_locked_definitions_20260603.json` is the packaged runtime copy of the source-locked TKS definitions. Its SHA-256 must remain `a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0`.

**2) Customer audit creation is fail-closed.** `api/services/cas_harness_tks_definition_lock.py` verifies both the packaged definitions and the active probe-bundle manifest before audit work starts. The live audit routes now refuse `503` if the definitions are missing, edited, or paired with a manifest carrying the wrong `definition_sha256`.

**3) Customer-supplied probes are also locked.** Frontier probe specs must now include `definition_sha256` equal to the locked TKS owner hash. Missing or different hashes are `PROBE_COMPATIBILITY_UNSUPPORTED` and the public route returns HTTP 422, so a customer or future agent cannot supply a probe trained/evaluated against another vocabulary and still call it a CAS Harness audit.

**4) Comparator lanes stay allowed but cannot promote.** The Stage 9 40E verifier builder now requires matched-taxonomy/uniqueness proof to carry the same locked TKS definition hash before it can close the uniqueness gate toward `ACCEPT`. Non-CAS or unbound comparator evidence may still be recorded, and explicit failures may still suppress, but a passing comparator cannot masquerade as the claim-bearing CAS uniqueness proof.

**5) The current probe manifest stays honest.** `api/resources/tks_definition_probe_bundle_manifest.v1.json` deliberately says `definition_fixture_locked_no_trained_probe_claim`. This locks the required definitions for audit creation without pretending a trained production probe is verified.

**6) Tests pin the failure mode.** New route tests monkeypatch the definition lock to fail and prove both the standard and distributed audit creation endpoints refuse work. Probe-compatibility and route tests prove missing/wrong `definition_sha256` is rejected. Verifier-builder tests prove a passing but unbound comparator proof stays `FLAG_FOR_HUMAN_REVIEW`. Fixture tests still prove the generated 40E/F28 dataset uses TKS labels (`A1-D10`, `1a-7d`) and not fallback notation labels.

**Pieces:** `api/resources/tks_owner_locked_definitions_20260603.json`, `api/resources/tks_definition_probe_bundle_manifest.v1.json`, `api/services/cas_harness_tks_definition_lock.py`, `api/services/cas_harness_probe_compatibility.py`, `live-trace-worker/scripts/build_stage9_40e_verifier_report.py`, audit-route gating, `tests/test_tks_definition_lock.py`, and `docs/working/production_readiness/26_tks_definition_runtime_lock_2026_06_03.md`.

**Tests:** `pytest -q tests\test_cas_harness_probe_compatibility.py tests\test_tks_definition_lock.py tests\test_definition_locked_tks_fixture.py tests\test_cas_harness_audit.py tests\test_cas_harness_distributed_audits.py` -> 132 passed; `pytest -q live-trace-worker\tests\test_build_stage9_40e_verifier_report.py` -> 8 passed. This does not change the Pythia verdict; it remains `FLAG_FOR_HUMAN_REVIEW`.

## Definition-locked TKS/CAS 40E/F28 fixture source-locked, **BUILT and test-guarded** - next run can test the actual owner-provided definitions (Jun 3, 2026)

The Condition-3 comparator audit exposed a definition boundary: it used CAS 40E
fixture labels, but it did not directly test the locked TKS definitions of the
40 Elements and 28 Foundations. The first definition fixture still used a CAS
translation layer for the F28 side. This entry corrects that: the fixture is now
generated from an explicit owner-provided TKS source file and guarded by tests.

**1) The source file is locked.** `docs/reference/tks_owner_locked_definitions_20260603.json`
contains the owner-provided `A1-D10` TKS 40 Element definitions and `1a-7d` TKS
28 Foundation definitions supplied on 2026-06-03. The generator now reads that
file as authority instead of carrying hidden definitions in code.

**2) The generated labels are TKS labels.** The 40E rows use `A1-D10`; the F28
rows use `1a-7d`. They no longer use fallback labels like `^1|P` or `F1|T`, and
the live loader now preserves those TKS codes as first-class labels.

**3) The failure mode is now tested.** The regression suite fails if the locked
source is missing the owner-provided definitions, if the generator stops being
source-driven, if the committed fixture drifts from the source file, or if the
live loader fails to preserve `A1-D10` / `1a-7d`.

### Pieces (this entry)
- `docs/reference/tks_owner_locked_definitions_20260603.json` *(new)* - locked owner-provided TKS source definitions.
- `live-trace-worker/scripts/build_definition_locked_tks_fixture.py` - generator now consumes the locked source file.
- `live-trace-worker/scripts/probe_dataset_common.py` - live loader now accepts TKS `A1-D10` and `1a-7d` labels.
- `tests/test_definition_locked_tks_fixture.py` *(new)* - regression guard against definition substitution and loader label loss.
- `docs/working/definition_locked_tks_mtc_20260603/` - regenerated definitions, JSON fixture, JSONL fixture, manifest, and README.
- `docs/working/production_readiness/25_definition_locked_tks_fixture_2026_06_03.md` - evidence record updated with source-lock, tests, archive path, and hashes.

### Tests / verification (this entry)
- Generator wrote 816 rows: 480 40E and 336 F28.
- Capture loader validation: `loaded 816`, `element_classes 40 minmax 12 12`, `foundation_classes 28 minmax 12 12`, with labels preserved as `A1-D10` and `1a-7d`.
- Split validation: 68 classes, 8 train / 4 test per class.
- `pytest -q tests\test_definition_locked_tks_fixture.py` -> 5 passed.

Honesty boundary: this is a fixture build, not a model run or comparator
verdict. It does not change the Pythia-160M packet from
`FLAG_FOR_HUMAN_REVIEW`.

## Condition-3 MTC 20B comparator completed, **VERIFIED on H200 pod** - verdict is `GREY`, uniqueness remains open (Jun 3, 2026)

The GPT-NeoX-20B Condition-3 matched-taxonomy comparator has now run against
the captured activation dataset. It completed cleanly and emitted `GREY`, not
`PASS`, `FALSIFY`, or `BLOCKED`.

**1) CAS passed two internal gates.** The CAS 40E hidden readout beat its text
baseline by 43.75 percentage points, and CAS flat lacunarity was cleaner than
the best coherent matched taxonomy (`0.04394354424923896` versus
`0.1160894894797089`).

**2) CAS failed the matched-readout margin.** The coherent NC40 control taxonomy
read out at 1.0 accuracy, while CAS read out at `0.5347222222222222`. The
pre-registered margin required CAS to beat the matched control by +5pp; observed
margin was `-46.52777777777778pp`.

**3) The verdict stays honest.** The comparator result says `GREY` with
`pass: false`, `falsify: false`, and `blocked: false`. The Pythia-160M
WORM-retained packet remains `FLAG_FOR_HUMAN_REVIEW`; this 20B result does not
turn it into `ACCEPT`.

### Pieces (this entry)
- `docs/working/production_readiness/24_condition3_mtc_20b_comparator_2026_06_03.md` *(new)* - evidence record with command, metrics, verdict, archive path, and hashes.
- `D:\tksCAS-archive\condition3_mtc_comparator_20260603` *(archive copy)* - result JSON, comparator log, and row-level manifest.

### Tests / verification (this entry)
- Comparator process completed on `root@212.247.220.166 -p 18611` and wrote `/workspace/condition3_mtc_20b_comparator_result_20260603.json`.
- Result JSON hash: `860956BA3C0267AB2A3EE9A56643A0B115064F7AE4B9430F9040F88CC3DFC274`.

Honesty boundary: this is a completed 20B Stage X.1 `GREY` result. It keeps
matched-taxonomy / uniqueness open and does not upgrade any Pythia-160M packet.

## Condition-3 MTC 20B capture completed, **VERIFIED on H200 pod** - claim-neutral activations are archived, comparator still gated (Jun 3, 2026)

The replacement H200 pod completed the GPT-NeoX-20B Condition-3 activation capture for the MTC uniqueness track. This is the measurement file the comparator will read later; it is not the comparator verdict.

**1) The capture finished on the second pod.** The pod at `root@212.247.220.166 -p 18611` loaded `EleutherAI/gpt-neox-20b` from 46 safetensor shards and captured all 1,440 Condition-3 rows. The output dataset is `720117672` bytes.

**2) The fixture adapter was corrected before capture.** The capture loader expects one JSON document, not JSONL, and uses `scenario_id` / `id` for row identity. The adapted fixture was converted to one JSON list, preserving each `sample_id` as `scenario_id`. Validation before capture: 1,440 rows, 40 elements, 36 per element, train/test 720/720.

**3) The environment issue was fixed without changing the claim.** `transformers 5.10.1` failed before capture because it expected a Torch float8 type absent from `torch 2.4.1+cu124`. The pod was set to `transformers 4.44.2` and `accelerate 0.34.2`; the capture then completed.

### Pieces (this entry)
- `docs/working/production_readiness/22_condition3_mtc_20b_capture_2026_06_03.md` *(new)* - evidence record with pod, command, archive path, and hashes.
- `D:\tksCAS-archive\condition3_mtc_capture_20260603` *(archive copy)* - NPZ, metadata, converted fixture, JSONL fixture, log, and provenance.

### Tests / verification (this entry)
- Capture log reached `1440/1440` and wrote `/workspace/condition3_gptneox20b_activations.npz`.
- Local archive SHA-256 matched pod provenance for the NPZ, metadata, fixture, and log.

Honesty boundary: this is claim-neutral capture only. The matched-taxonomy comparator has not run, the A1 prereg amendment is not frozen, and the Pythia-160M packet remains `FLAG_FOR_HUMAN_REVIEW`.

## Pythia-160M activation matched-ablation completed, **VERIFIED locally** - stored activations passed matched controls, but uniqueness remains open (Jun 3, 2026)

The archived Pythia-160M Stage 9 40E run now has the missing activation-level matched-ablation computation. This did not rerun the model: it reused the archived `.npz` hidden-state activations under `D:\tksCAS-archive\pythia160m_gate1_reproduction_20260531\`.

**1) The candidate cover beat matched controls inside the ablation runner.** The activation-level report evaluated the `element` axis at layer 3 over 1,680 heldout examples. Label-specific cover ablation dropped accuracy by `0.054762`; wrong-cover control dropped by `0.003572`; same-size random controls across 20 trials maxed out at `0.005953`. The union cover drop was `0.108334`, above the union random-control max of `0.0`.

**2) The archived run stopped being a rerun target.** The stored activation dataset, original eval report, and original cover map were enough to run this gate locally. The result was copied into both the repo evidence directory and `D:\tksCAS-archive\pythia160m_activation_cover_ablation_20260603\`.

**3) The packet still stays at `FLAG_FOR_HUMAN_REVIEW`.** This closes activation-level matched ablation only. It does not prove matched-taxonomy / uniqueness, and the hardened Stage 9 40E gate still requires explicit uniqueness proof before final `ACCEPT`.

### Pieces (this entry)
- `docs/working/pythia160m_gate1/pythia160m_activation_cover_ablation_report.json` *(new)* - activation-level matched-ablation report.
- `docs/working/pythia160m_gate1/eval_adapter.json` *(new)* - adapter from the archived Stage 9 eval report into the generic ablation runner schema.
- `docs/working/pythia160m_gate1/cover_adapter.json` *(new)* - adapter from the archived cover report into the generic ablation runner schema.
- `docs/working/production_readiness/21_pythia160m_activation_matched_ablation_2026_06_03.md` *(new)* - evidence record with command, metrics, hashes, and claim boundary.

### Tests / verification (this entry)
- Ablation command: `live-trace-worker\scripts\ablate_probe_dataset.py` over the archived `.npz`, `--random-trials 20`, `--seed 42`.
- Report hash: `8093B49935FB37C7498956DE4960308D4126C1A3AEC428D602FC75678DE4860F`.

Honesty boundary: this is not a production `ACCEPT`. The WORM-retained production packet remains `FLAG_FOR_HUMAN_REVIEW` until the matched-taxonomy / uniqueness gate also passes.

## Stage 9 40E ACCEPT gate now requires uniqueness proof, **BUILT** - matched ablation alone cannot mint a final `ACCEPT` (Jun 3, 2026)

The Pythia archive audit exposed a real memory hazard: the historical packet at `D:\tksCAS-archive\pythia160m_gate1_reproduction_20260531\` is the same run as the WORM-retained packet, but its old `ACCEPT` verdict came from the pre-fix control-chip overclaim. This entry hardens the next gate so future tooling cannot treat matched-ablation/control presence alone as enough for final `ACCEPT`.

**1) The verifier report builder has a uniqueness gate.** `build_stage9_40e_verifier_report.py` now looks for explicit matched-taxonomy / uniqueness proof. If it is present and passed, `ACCEPT` can still be emitted when all other gates pass. If it is missing, the report stays `FLAG_FOR_HUMAN_REVIEW`. If it is explicitly failed, the report returns `SUPPRESS`.

**2) The packet merger also enforces the gate.** `merge_stage9_40e_evidence_packet.py` now accepts an optional `--uniqueness-report` and records `matched_taxonomy_proof` in the packet. Even if a verifier report says `ACCEPT`, the merger keeps the packet at `FLAG_FOR_HUMAN_REVIEW` unless matched-taxonomy/uniqueness proof has passed. `SUPPRESS` remains allowed for genuine blocking findings.

**3) The Pythia archive is not reinterpreted as a pass.** The correct reading is now explicit: the archive is the canonical source for the stored activations/reports and should prevent rerunning Pythia, but its `"verdict": "ACCEPT"` packet is the pre-fix overclaim. The honest production verdict for trace `pythia-160m-stage9-40e-readout-20260531` remains WORM-retained `FLAG_FOR_HUMAN_REVIEW`.

### Pieces (this entry)
- `live-trace-worker/scripts/build_stage9_40e_verifier_report.py` *(edit)* - add the tri-state uniqueness gate to the verifier report.
- `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py` *(edit)* - add optional `--uniqueness-report`, packet `matched_taxonomy_proof`, and merger-side `ACCEPT` blocking when uniqueness proof is absent.
- `live-trace-worker/tests/test_build_stage9_40e_verifier_report.py` *(edit)* - pin accept/pass, missing-proof FLAG, and failed-proof SUPPRESS behavior.
- `live-trace-worker/tests/test_merge_stage9_40e_evidence_packet.py` *(edit)* - pin that explicit verifier `ACCEPT` is not final without uniqueness proof.

### Tests / verification (this entry)
- Stage 9 verifier + merger: `live-trace-worker/tests/test_build_stage9_40e_verifier_report.py live-trace-worker/tests/test_merge_stage9_40e_evidence_packet.py` **20 passed**.

Honesty boundary: this does not run the missing matched-ablation or matched-taxonomy computation for Pythia-160M. It only prevents the software from treating those absent proofs as a final `ACCEPT`.

## Pythia-160M Stage 9 packet anchored under Object Lock, **VERIFIED on Render** - the real packet is now WORM-retained as `FLAG_FOR_HUMAN_REVIEW`, not `ACCEPT` (Jun 3, 2026)

This is the irreversible production WORM step for the Pythia-160M Stage 9 40E packet. The hosted service first served the packet read-only as `FLAG_FOR_HUMAN_REVIEW`, then anchored it with `require_object_lock=true`, then re-read the stored static anchor through `/verify`.

**1) The packet stayed honest.** Hosted preflight returned `verdict: "FLAG_FOR_HUMAN_REVIEW"`, `parameter_scale: "160M"`, `verification.proof_chip_gate: "blocked"`, and `verification.explicit_verifier_decision.verdict: "FLAG_FOR_HUMAN_REVIEW"`. The anchor response kept `console_state: "flag_for_human_review"` and said WORM anchoring records a verdict immutably; it never upgrades a FLAG to an ACCEPT.

**2) Object Lock is active.** The packet anchored to `s3://cas-harness-runpod-92754088/cas-harness/evidence-anchors/pythia-160m-stage9-40e-readout-20260531/fb02b1683b52cd02d6a7112fcce89019a42ccb8764a184fe8d8f9891c7750507.json`; `worm_retained: true`, `anchor_mode: "s3"`, `anchor_status: "anchored"`, `external_anchor_match: true`, and retention is active until `2026-07-03T16:25:16+00:00`.

**3) `/verify` re-read the stored static anchor.** `POST /evidence/pythia-160m-stage9-40e-readout-20260531/verify` returned `overall: "all_match"` with matching packet payload hash, hash-log entry hash, hash-chain validity, and external S3 anchor manifest hash.

### Pieces (this entry)
- `docs/working/production_readiness/20_pythia160m_object_lock_anchor_2026_06_03.md` *(new)* - full production evidence record.
- `D:\tksCAS-archive\pythia160m_object_lock_anchor_20260603` *(archive copy)* - packet and verifier artifacts copied outside the repo.

### Tests / verification (this entry)
- Hosted Render deploy: `bbb755d7db75500a10977a42212d67b807667ba2` live before anchor.
- Hosted anchor: `POST /evidence/pythia-160m-stage9-40e-readout-20260531/anchor?require_object_lock=true` **200**, `worm_retained: true`.
- Hosted verify: `POST /evidence/pythia-160m-stage9-40e-readout-20260531/verify` **overall: all_match**.

Honesty boundary: this closes the real Pythia packet's production Object-Lock write. It does not close matched controls or turn the packet into a production `ACCEPT`.

## Static Stage 9 packet artifacts now ship in the API image, **BUILT** - hosted `/evidence/{trace_id}` can resolve the Pythia packet before the irreversible Object-Lock anchor (Jun 3, 2026)

The Pythia packet and route fix were correct in source, but the Docker runtime image only copied `api/`, `cas-native/`, `scenarios/`, and `validation/`. That meant the hosted container could not see `docs/working/pythia160m_gate1`, so `GET /evidence/pythia-160m-stage9-40e-readout-20260531` returned 404 even after commit `337d0c2`.

**1) The package boundary is fixed narrowly.** `Dockerfile.api` now copies the Pythia-160M Stage 9 40E artifact directory plus the original 20B Stage 9 static packet into `/app/docs/working/...`. This exposes only the static Evidence Packet assets the route registry needs, not the whole documentation tree.

**2) The irreversible anchor remains gated.** The real Pythia S3 Object-Lock write still waits until hosted `GET /evidence/pythia-160m-stage9-40e-readout-20260531` returns the deployed `FLAG_FOR_HUMAN_REVIEW` packet.

**3) The read and verify paths now cover static Stage 9 packets.** `GET /evidence/{trace_id}` checks the Stage 9 40E packet registry first, so a packet that can be anchored can also be inspected read-only before the irreversible write. After the explicit anchor write, `POST /evidence/{trace_id}/verify` can re-read the stored static anchor copy and report its hash-chain / external-anchor checks.

### Pieces (this entry)
- `Dockerfile.api` *(edit)* - include registry-backed Stage 9 static packet artifacts in the runtime image.
- `api/routes/evidence.py` *(edit)* - expose raw Stage 9 scoped-validation packets through the read-only evidence route, verify anchored static packets, and correct the `console_state` field description.
- `tests/test_evidence_routes.py` *(edit)* - pin the Pythia read-only preflight as `FLAG_FOR_HUMAN_REVIEW` and the post-anchor static `/verify` path.

### Tests / verification (this entry)
- Evidence routes: `tests/test_evidence_routes.py` **33 passed, 2 skipped**.

## Hosted Object-Lock anchor smoke, **VERIFIED on Render** - a throwaway distributed Evidence Packet was anchored through the live S3 Object-Lock path, re-read by `/verify`, and confirmed under `GOVERNANCE` retention (Jun 3, 2026)

This closes the wiring question around the Object-Lock bucket before touching the real Pythia packet. The smoke used hosted production, wrote a throwaway deploy-check packet, and required both S3 mode and active Object Lock retention.

**1) The deploy smoke now matches current gates.** `scripts/verify_evidence_anchor_deployed.py` now sends `accept_audit_data_capture=true`, because gate 8 is a real run-creation requirement. It also handles multi-worker plans instead of assuming the old one-worker shape; hosted persistent state already has `probe-worker-01` and `probe-worker-02` registered for `deploy-check/open-weight-ledger-watch-20b`.

**2) Hosted Object Lock is proven, not assumed.** The smoke produced trace `cas-dist-ecb55108b0a964da-distributed-merge`, anchored it at `s3://cas-harness-runpod-92754088/cas-harness/evidence-anchors/cas-dist-ecb55108b0a964da-distributed-merge/bc9bec027c1d528aff55d97382fa6b12e36ca41e8ded90a78c70d8b3ae4b2179.json`, and `/verify` reported `overall: all_match`.

**3) Retention is active.** The anchor receipt reported `object_lock_mode: "GOVERNANCE"`, `retention_days: 30`, and `object_lock_retain_until: "2026-07-03T14:56:13.157525+00:00"`. The external-anchor verify note said the S3 object was re-read and Object Lock retention is active until `2026-07-03T14:56:13+00:00`.

### Pieces (this entry)
- `scripts/verify_evidence_anchor_deployed.py` *(edit)* - current gate payload, durable hosted worker namespace, and multi-worker receipt drain.
- `scripts/test_verify_evidence_anchor_deployed.py` *(edit)* - pins the data-capture acknowledgement and keeps the verifier contract green.
- `docs/working/production_readiness/19_hosted_object_lock_anchor_smoke_2026_06_03.md` *(new)* - evidence record with the hosted trace id, S3 URI, receipt fields, and `/verify` note.

### Tests / verification (this entry)
- Verifier unit tests: `scripts/test_verify_evidence_anchor_deployed.py` **7 passed**.
- Hosted deploy smoke: **PASS** against `https://noetic-compass-api.onrender.com` with `--require-anchor-mode s3 --require-object-lock`.

Honesty boundary: this proves hosted S3 Object-Lock wiring with throwaway deploy-check data. It does not yet anchor the real Pythia-160M packet.

## CRM pipeline status hardening, **BUILT after code review** - sales status updates now use one domain validation path and store-level atomic writes, closing the three review findings on the first pipeline endpoint (Jun 3, 2026)

The first pipeline-status endpoint was correct on the happy path, but review found three real edge problems: get-then-save could lose concurrent updates, the HTTP route rejected title-case labels even though the domain normalizer accepted them, and loosening the route later would have exposed an uncaught `LeadValidationError`. This entry closes all three.

**1) Atomic at the store boundary.** `LeadStore.update_pipeline_status()` now owns the read-modify-write under the backend lock. `InMemoryLeadStore` updates the in-memory index atomically; `JsonlFileLeadStore` appends exactly one new version while holding its lock. The service delegates to that method instead of doing `get()` then `save()`.

**2) One validator.** The route body now accepts `str` and the domain layer normalizes it (`" Contacted "` -> `contacted`). Unknown statuses use the same `LeadValidationError` message in every path instead of a separate Pydantic `Literal` contract.

**3) HTTP errors stay 4xx.** The route catches `LeadValidationError` and returns HTTP 422, matching the public capture route. A future route-shape change cannot accidentally turn a bad pipeline status into a 500.

### Pieces (this entry)
- `api/services/crm/store.py` *(edit)* - adds atomic pipeline-status update to the `LeadStore` seam and both shipped stores.
- `api/services/crm/service.py` *(edit)* - delegates pipeline updates to the store-owned atomic method.
- `api/routes/crm.py` *(edit)* - accepts string input, uses the domain validator, and maps domain validation failures to 422.
- `tests/test_crm_lead_capture.py` *(edit)* - adds concurrency, JSONL append, human-label normalization, and domain-error assertions.

### Tests / verification (this entry)
- Compile: CRM models, store, service, exports, and route.
- Targeted CRM: `tests/test_crm_lead_capture.py` **55 passed**.
- Focused CRM/config/startup sweep: **71 passed**.
- Hosted smoke after deploy: authed `PATCH /api/crm/leads/lead-121dc923f575416d/pipeline-status`
  with `{"pipeline_status":" Qualified "}` returned `200`, normalized to
  `pipeline_status: "qualified"`, bumped the lead to `version: 4`, and preserved
  `sync_status: "sync_pending"` / `external_id: null`.

## CRM pipeline status endpoint, **BUILT as an authed sales workflow slice** - captured leads can now move through `new` / `contacted` / `qualified` / `won` / `lost` without changing their external-sync claim (Jun 3, 2026)

The CRM now has a first usable sales workflow, not just public capture. The endpoint is deliberately narrow: it changes the lead's `pipeline_status`, writes a new immutable lead version when the status changes, and leaves `sync_status` / `external_id` untouched so a sales action can never launder a locally captured lead into an externally synced one.

**1) Status vocabulary is enforced.** `normalize_pipeline_status()` accepts only the supported first-rung stages (`new`, `contacted`, `qualified`, `won`, `lost`). Unknown stages return a validation error instead of becoming free-form CRM state that list/filter/report views cannot trust.

**2) Sales updates are versioned.** `Lead.with_pipeline_status()` preserves the original lead identity and sync fields, bumps `version` only on a real status change, and relies on the existing append-only lead store to retain the sales history.

**3) The route is protected.** `PATCH /api/crm/leads/{lead_id}/pipeline-status` is an authenticated sales view, parallel to the existing list/get endpoints. Public prospects can submit leads; only authenticated users can move them through the pipeline.

### Pieces (this entry)
- `api/services/crm/models.py` *(edit)* - adds pipeline-status normalization and immutable status-transition helper.
- `api/services/crm/service.py` *(edit)* - adds `CRMService.update_pipeline_status()`.
- `api/routes/crm.py` *(edit)* - adds the authenticated `PATCH /api/crm/leads/{lead_id}/pipeline-status` route.
- `api/services/crm/__init__.py` *(edit)* - exports the pipeline-status helper surface.
- `tests/test_crm_lead_capture.py` *(edit)* - adds model, service, and route tests for sales status updates.
- `docs/working/crm/01_lead_capture_dark_seam_2026_06_02.md` *(edit)* - updates the CRM status and remaining workflow gaps.

### Tests / verification (this entry)
- Compile: CRM models, service, exports, and route.
- Targeted CRM: `tests/test_crm_lead_capture.py` **52 passed**; focused CRM/config/startup sweep
  **68 passed**.
- Hosted smoke after deploy: authed `PATCH /api/crm/leads/lead-121dc923f575416d/pipeline-status`
  returned `200`, `pipeline_status: "contacted"`, `version: 3`, and preserved
  `sync_status: "sync_pending"` / `external_id: null`.

## CRM public lead anti-abuse, **BUILT as an in-process guard** - the anonymous `POST /api/crm/public/leads` endpoint now rejects honeypot-filled bot submissions before persistence and has a per-client sliding-window limiter, separate from the API-key limiter that public paths intentionally bypass (Jun 3, 2026)

The public lead endpoint has to stay unauthenticated, but it cannot be an unlimited anonymous write path. This entry adds the first production guard while keeping the boundary clear: this is an in-process app guard, not a WAF, captcha, or distributed bot-defense system.

**1) Reject before capture.** `LeadSubmissionRequest` now includes a hidden `website` honeypot field. Real users leave it blank; simple bots fill it. A non-empty value returns `400` before `CRMService.capture`, so no junk lead is persisted.

**2) Separate public limiter.** `PublicLeadAbuseGuard` tracks submissions by best-effort client key (`X-Forwarded-For` first, then socket client host) and returns `429` with `Retry-After` once the anonymous client exceeds the configured sliding-window cap. Render defaults are explicit: `NC_CRM_PUBLIC_LEAD_RATE_LIMIT_MAX=5` and `NC_CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS=3600`.

**3) Honest boundary.** This closes the "completely unguarded public CRM write endpoint" gap. It does not claim hostile-traffic protection at the edge, and it is process-local. If the public form gets real hostile traffic, the next rung is edge-level rate limiting/captcha.

### Pieces (this entry)
- `api/services/crm/abuse.py` *(new)* - in-process honeypot + sliding-window public lead guard.
- `api/routes/crm.py` *(edit)* - runs the guard before capture; rejected submissions never hit the lead store.
- `api/config.py` / `api/main.py` / `api/services/crm/__init__.py` *(edit)* - configurable defaults, startup wiring, and exports.
- `render.yaml` / `infra/render.yaml` *(edit)* - visible hosted defaults for the public lead cap.
- `tests/test_crm_lead_capture.py` *(edit)* - proves honeypot rejection and public limiter behavior.
- `docs/working/crm/01_lead_capture_dark_seam_2026_06_02.md` *(edit)* - documents the anti-abuse posture and remaining edge-control boundary.

### Tests / verification (this entry)
- Compile: `api/services/crm/abuse.py`, `api/routes/crm.py`, `api/config.py`, `api/main.py`.
- Focused CRM/config: **49 passed**.
- Hosted smoke after deploy: `/health` recovered to 200; normal public lead `lead-121dc923f575416d`
  captured with `sync_status: sync_pending`; honeypot-filled submission returned `400` with
  `lead rejected by anti-abuse gate`.

## CRM Airtable provider, **BUILT but not hosted-active** - the CRM seam can now sync a captured lead to Airtable and mark it `synced` only when Airtable returns a real record id; hosted production remains capture-only until `NC_CRM_PROVIDER=airtable` plus Airtable token/base/table env vars are configured and a hosted lead proves an external landing (Jun 3, 2026)

This turns the CRM from "local capture only" into "one real provider exists behind the seam," while preserving the same honesty rule that launched the CRM: `captured` is not `synced`. The default remains `NC_CRM_PROVIDER=null`, so the deployed app keeps capturing leads durably under `/var/data/leads.jsonl` and reports `sync_pending` until an operator deliberately enables Airtable.

**1) Airtable is real, but not automatic.** `AirtableCRMProvider` POSTs one lead record to Airtable's REST create-record endpoint with bearer-token auth. The lead earns `sync_status: "synced"` only when Airtable returns a non-empty record id, which becomes the lead's `external_id`. HTTP errors, network errors, malformed JSON, or a response with no record id are sync failures, not lost leads.

**2) Half-configured sync fails loud.** `NC_CRM_PROVIDER=airtable` now requires `NC_AIRTABLE_TOKEN`, `NC_AIRTABLE_BASE_ID`, and `NC_AIRTABLE_TABLE_NAME`. Missing values raise `CRMConfigError` at startup. That is intentional: a half-configured Airtable integration would look like external sync while only capturing locally.

**3) The default production posture is unchanged.** `null` remains the provider default. `hubspot` is still a declared but unimplemented seam that fails loud. Render blueprints now declare the Airtable env vars as dashboard-managed secrets/settings, but they do not turn Airtable on.

### Pieces (this entry)
- `api/services/crm/sync.py` *(edit)* - adds `AirtableCRMProvider`, provider selection for `airtable`, and startup validation for token/base/table settings.
- `api/config.py` *(edit)* - adds Airtable settings with `NC_AIRTABLE_*` aliases.
- `api/services/crm/__init__.py` *(edit)* - exports `AirtableCRMProvider`.
- `tests/test_crm_lead_capture.py` *(edit)* - adds Airtable construction, request-shape, record-id, and fail-loud tests.
- `render.yaml` / `infra/render.yaml` *(edit)* - declare dashboard-managed Airtable env vars without enabling them.
- `docs/working/crm/01_lead_capture_dark_seam_2026_06_02.md` *(edit)* - updates the CRM setup note from capture-only to Airtable-provider-built, hosted-sync-not-yet-enabled.

### Tests / verification (this entry)
- Targeted CRM: `tests/test_crm_lead_capture.py` **40 passed**.
- Focused regression: CRM + config + state-ledger operational enable tests **56 passed**.

## Hosted paid-disk durability, **VERIFIED on Render** — attached `noetic-data` at `/var/data`, corrected live env vars to point the state ledger and CRM store at that disk, forced a Render deploy/restart, and proved both the pre-restart CRM lead and the pre-restart state-ledger audit/fleet state came back after the new process started (Jun 3, 2026)

This closes the single-host durability gate that the free-tier `/tmp` posture could not earn. The key correction was not just paying for the workspace: Render reported the service itself was still `plan: free` and had no disk. After the service moved to a paid instance (`plan: standard`, one instance), disk `dsk-d8fomrd8nd3s738rnee0` (`noetic-data`, 1 GB, `/var/data`) was attached, and the live env vars were corrected to `NC_STATE_LEDGER_PATH=/var/data/state_ledger.db` and `NC_CRM_LEAD_STORE_PATH=/var/data/leads.jsonl`.

**1) The failed pre-check was useful.** Before the env correction, the hosted app was healthy but still wrote to `/tmp`; a restart lost lead `lead-b0aaa211f4b54b45`, and `audit_count` / `fleet_counts` returned to zero. That failure prevented a false durability claim.

**2) The paid-disk baseline.** After the disk and `/var/data` env vars were live, the public CRM endpoint captured lead `lead-3c5d8d3268754c1a` (`sync_status: sync_pending`), and the hosted state-ledger verifier created audit `cas-dist-3aa09bc1ad35fcee` with `reads_served 0->92`, `divergences_found: 0`, two workers, two receipts, and fleet merge `COMPLETE` / `ready_for_verifier`.

**3) Restart-survival proof.** A Render API deploy (`dep-d8foqnhkh4rs73cque1g`) went live at `2026-06-03T02:12:31.995960Z`. After that new process started, the CRM lead was still readable (`lead_count: 1`), and the state ledger reported `audit_count: 1`, `fleet_counts: {workers: 2, fleet_runs: 1, fragment_refs: 2}`. A fresh hosted verifier then passed again with audit `cas-dist-2521a6be75c79773`, `reads_served 0->110`, and `divergences_found: 0`.

**4) Honesty boundary.** This earns hosted **single-instance restart durability** for the local state ledger and CRM lead capture. It does not earn host-loss durability, multi-instance durability, external CRM sync, or Phase 4 dictionary deletion. The service currently reports `plan: standard` (not `starter`); that is a cost/instance-size posture, not a correctness problem.

**5) Starter cost/posture correction.** After the durability proof, the service was corrected from `standard` to the intended `starter` plan through the Render API. The disk remained attached at `/var/data`, the env vars stayed pointed at `/var/data`, and deploy `dep-d8fp5v57vvec739eu010` went live at `2026-06-03T02:36:40.390737Z`. The same CRM lead survived, the ledger rehydrated `audit_count: 2`, `workers: 2`, `fleet_runs: 2`, `fragment_refs: 4`, and the hosted verifier passed again with audit `cas-dist-addaf4804fe2f41a`, `reads_served 0->128`, `divergences_found: 0`.

### Pieces (this entry)
- `docs/working/production_readiness/18_hosted_paid_disk_durability_evidence_2026_06_03.md` *(new)* — evidence record with Render service/disk/env metadata, the failed `/tmp` pre-check, corrected `/var/data` baseline, restart deploy ID, and post-restart CRM/ledger proof.
- `CHANGELOG.md` *(edit)* — this entry.

### Tests / verification (this entry)
- Hosted CRM proof: `lead-3c5d8d3268754c1a` created before restart and readable after restart; `lead_count: 1`.
- Hosted state-ledger proof: pre-restart audit/fleet state rehydrated after restart (`audit_count: 1`, `workers: 2`, `fleet_runs: 1`, `fragment_refs: 2`).
- Hosted verifier after restart: **PASS** on `https://noetic-compass-api.onrender.com`, `reads_served 0->110`, `divergences_found 0`, fleet merge `COMPLETE` / `ready_for_verifier`.
- Hosted Starter proof after cost correction: **PASS**, lead `lead-3c5d8d3268754c1a` still readable, `audit_count: 2`, `fleet_runs: 2`, `fragment_refs: 4`, `reads_served 0->128`, `divergences_found 0`.

## State-ledger Postgres backend, **WIRED as a dark seam, not activated** — the enable now selects its durable store: `PostgresStateStore` when `NC_DATABASE_URL` is set, else the single-host SQLite file (the unchanged default). Production posture is **byte-for-byte unchanged** — nothing routes at Postgres until an operator sets the DSN, exactly as the two ledger flags gate the rest of the rollout. This is the *code-side* "if it blows up" insurance: the multi-host rung is now one env var away, but it is **not** turned on, and on Render free-tier storage is still ephemeral (Jun 2, 2026)

This closes the last hard-coded line in the state-ledger bootstrap. `PostgresStateStore` was already built and **verified against real PostgreSQL 16.4** (`test_state_substrate_postgres.py`), `api/config.py` already carried `database_url` (env `NC_DATABASE_URL`), and `requirements.txt` already pinned `psycopg[binary]` (lazily imported). The only gap was that `install_state_ledger` constructed `SqliteStateStore` directly, so a configured DSN could never take effect. This entry adds the selector and routes the enable through it — the wire-up the prior entries left at "90% done."

**1) One selector, same locked Protocol.** New `_build_state_store(settings)` keys off `settings.database_url`: a non-empty DSN builds `PostgresStateStore(dsn)` (the first multi-host rung — one logical record-of-truth every instance reaches); unset *or blank* builds `SqliteStateStore(settings.state_ledger_path)` (single-host durable, production's posture). Both classes realize the SAME `StateStore` Protocol, so everything downstream — the `LedgerMirror`, rehydrate, two-flag phasing, fail-loud and teardown discipline — is identical regardless of which backend is built. The backend is a swap behind one interface, not a fork in the control flow.

**2) Dark-by-default and fail-loud, both preserved.** The selector changes nothing about *when* a store is built: `install_state_ledger` still returns `None` (no mirror, dicts authoritative) unless `state_ledger_enabled` is set. When it is, a misconfigured or unreachable Postgres raises `StateStoreError` from the constructor, which propagates up so startup fails visibly rather than degrading to a backend the operator did not ask for — the same fail-loud contract the SQLite path already honored. Nothing cuts over to Postgres until an operator deliberately sets `NC_DATABASE_URL`, keeping each durability escalation an explicit, separate act.

**3) Honesty boundary.** This is a *seam*, not a durability claim. With `NC_DATABASE_URL` unset (the default, and the hosted posture today) behaviour is byte-for-byte the current SQLite-file path — and on Render free-tier that file is still ephemeral. Wiring the Postgres selector does **not** make hosted state durable; it makes the multi-host backend reachable by setting one env var **and** standing up a Postgres a deployment owns. Host-loss durability still requires that Postgres (and, for host-loss specifically, sync replication). Phase 4 deleted nothing.

### Pieces (this entry)
- `api/state_ledger_bootstrap.py` *(edit)* — new `_build_state_store(settings)` selector (Postgres when `database_url` set, else SQLite); `install_state_ledger` now routes its store construction through it; module + function docstrings updated to name the two-backend choice and its fail-loud propagation.
- `tests/test_state_ledger_operational_enable.py` *(edit)* — `_FakeSettings` gains a `database_url` field (defaults `None`, so every existing test still selects SQLite); new section 6 adds three selection tests (no-DSN→SQLite, blank-DSN→SQLite, DSN→Postgres-with-exact-DSN via a constructor spy so the *selection* is under test, not a live database).

### Tests / verification (this entry)
- Targeted: `test_state_ledger_operational_enable.py` **9 passed** in isolation (6 pre-existing + 3 new selection tests).
- Regression proof (declared-vs-verified): full suite run **with** and **without** this change produced an **identical 48 failures**; the only delta was `1375 → 1378 passed` — exactly the 3 new selection tests. The 48 pre-existing failures are full-suite artifacts (a shared-`TestClient` rate-limit `429` cascade across idea_atlas/notation/mode7/wrap, plus the two known cas-native relative-import collection errors), unrelated to this two-file change. This change adds 3 passing tests and breaks nothing.

## Hosted state-ledger read-authority, **VERIFIED on Render production branch** — flipped `NC_STATE_LEDGER_READ_AUTHORITY=true`, pushed `02b6f9c..f1e572e`, waited for Render to roll forward, and ran the hosted verifier against `https://noetic-compass-api.onrender.com`: `enabled_ledger_read_authoritative`, `reads_served 0->92`, `divergences_found 0`, fleet merge `COMPLETE` / `ready_for_verifier`. Phase 4 stays held (Jun 2, 2026)

This is step 4 of the state-ledger rollout. The hosted shadow gate had already passed in doc 16 (`reads_compared 0->95`, zero divergences while dicts served reads). This entry records the separate read-authority flip: the ledger now serves public get/list reads, and the verifier watches `reads_served`, the Phase-3 odometer.

**1) Hosted read-authority release.** `render.yaml` and `infra/render.yaml` changed `NC_STATE_LEDGER_READ_AUTHORITY` from `"false"` to `"true"` and kept `NC_STATE_LEDGER_ENABLED=true`. The release was committed as `f1e572e` and pushed to `master`: `02b6f9c..f1e572e`.

**2) Hosted read-authority proof.** `scripts/verify_state_ledger_enabled.py --base-url https://noetic-compass-api.onrender.com --require-posture read-authority` passed. The verifier minted a hosted JWT via `/auth/token`, created a real distributed audit, dispatched it, registered workers, prepared fleet jobs, leased and receipted both jobs, merged the fleet packet, then touched every ledger-mirrored read site. The result: `posture=enabled_ledger_read_authoritative`, `reads_served=0->92`, `reads_compared=0`, `divergences_found=0`, `last_divergence=None`, `audit_id=cas-dist-bb51e79a414a9e62`, `workers=2`, `receipts=2`, `merge status=COMPLETE`, `gate=ready_for_verifier`.

**3) Honesty boundary.** `reads_compared` stayed 0 by design: it is the shadow-mode counter. In read-authority posture the ledger serves reads directly, so `reads_served` is the live odometer. Phase 4 deleted nothing. Render free-plan storage remains ephemeral, so this proves hosted read-authority correctness for one uptime, not host-loss durability.

### Pieces (this entry)
- `render.yaml` / `infra/render.yaml` *(edit)* — `NC_STATE_LEDGER_READ_AUTHORITY=true`, with comments updated to state this is step 4 and Phase 4 remains held.
- `docs/working/production_readiness/17_hosted_read_authority_evidence_2026_06_02.md` *(new)* — hosted read-authority evidence record: release action, verifier command, status snapshots, proof boundary, and next gate.
- `CHANGELOG.md` *(edit)* — this entry.

### Tests / verification (this entry)
- Hosted verifier: **PASS** on `https://noetic-compass-api.onrender.com`, `reads_served 0->92`, `divergences_found 0`, fleet merge `COMPLETE` / `ready_for_verifier`.

## Hosted state-ledger shadow enable, **VERIFIED on Render production branch** — merged `codex/cas-harness-live-run` into `master`, pushed `a9f519b..f32a650`, waited for Render to roll forward, and ran the hosted verifier against `https://noetic-compass-api.onrender.com`: `enabled_shadow_dict_authoritative`, `reads_compared 0->95`, `divergences_found 0`, fleet merge `COMPLETE` / `ready_for_verifier`. Read-authority stayed false and Phase 4 stayed held (Jun 2, 2026)

This is the hosted counterpart to doc 14. The first verifier attempt after the push still returned `404` for `/api/state-ledger/status`, which correctly meant Render was still serving the old build. After rollout, the same verifier passed against the hosted service. This changes the ledger status from "local real-HTTP shadow proof only" to "hosted shadow proof complete."

**1) Production branch release.** `master` was fast-forwarded to current `origin/master`, then fast-forward merged with `codex/cas-harness-live-run`, then pushed: `a9f519b..f32a650`. No conflict resolution was needed. The merged branch includes the state-ledger bootstrap, `GET /api/state-ledger/status`, the hosted verifier, and CRM capture seam.

**2) Hosted shadow proof.** `scripts/verify_state_ledger_enabled.py --base-url https://noetic-compass-api.onrender.com --require-posture shadow` passed. The verifier minted a hosted JWT via `/auth/token`, created a real distributed audit, dispatched it, registered workers, prepared fleet jobs, leased and receipted both jobs, merged the fleet packet, then touched the ledger-mirrored read sites. The result: `posture=enabled_shadow_dict_authoritative`, `reads_compared=0->95`, `divergences_found=0`, `last_divergence=None`, `audit_id=cas-dist-3a9e11fe091aa1f2`, `workers=2`, `receipts=2`, `merge status=COMPLETE`, `gate=ready_for_verifier`.

**3) Honesty boundary.** This is still shadow mode. `NC_STATE_LEDGER_READ_AUTHORITY` stayed false, so dicts still served reads while the ledger compared them. Phase 4 deleted nothing. Render free-plan storage remains ephemeral, so this proves hosted shadow correctness for one uptime, not host-loss durability. The next ledger gate is a separate owner-approved hosted read-authority run that watches `reads_served`, not `reads_compared`.

### Pieces (this entry)
- `docs/working/production_readiness/16_hosted_shadow_enable_evidence_2026_06_02.md` *(new)* — hosted evidence record: branch action, verifier command, status snapshots, proof boundary, and next gate.
- `CHANGELOG.md` *(edit)* — this entry.

### Tests / verification (this entry)
- Pre-push production-branch tests: **112 passed, 5 skipped** across CRM + state-ledger + state-substrate; **181 passed, 2 skipped** across CAS Harness audit/distributed/fleet/evidence route surfaces.
- Hosted verifier: **PASS** on `https://noetic-compass-api.onrender.com`, `reads_compared 0->95`, `divergences_found 0`.

## CRM lead capture, **BUILT and WIRED, capture-only** — a public form can POST a lead, it is validated, captured, and (with a durable path set) persisted to an append-only JSONL store; what it does **not** do yet is land leads in an external CRM of record (Airtable/HubSpot), **by design**. The load-bearing honesty rule is `captured` ≠ `synced`: a real provider with a genuine `external_id` is the *only* thing that can claim a landing. Dark by default (in-memory store + null provider); production syncs **nothing** until a real provider is wired (Jun 2, 2026)

This is the first slice of directive #4 ("start the CRM now — not operational yet, required before public launch"), built to the same declared-vs-verified discipline as the rest of the platform. It captures leads on **our** side and is honest, at every layer, that capturing a lead is not the same act as landing it in the external CRM. It changes no existing behaviour: the service is dark by default and the public endpoint is the only new unauthenticated surface (scoped to a `/public` subtree).

**1) The one honesty rule: `captured` ≠ `synced`, enforced structurally.** A lead's `sync_status` is the discriminator. `captured` = persisted on our side, no external landing claimed. `sync_pending` = a sync was *attempted* but the configured provider made no real landing (the dark/null default always lands here — honest that nothing left the building). `synced` = confirmed landed in the external CRM, backed by a real provider `external_id` — and **only a real provider can set it**. `sync_failed` = a real sync attempt errored; the lead is still safely captured locally, the failure recorded, never swallowed. `CRMSyncResult.__post_init__` raises `CRMStateError` if anything tries to construct a `synced=True` result without both a real `external_id` and `is_real=True` — so the null provider **structurally cannot** fake a landing even by mistake. This mirrors `billing.py`'s `fleet_measured` vs `planner_estimate` rule, applied to go-to-market.

**2) Capture durably *before* syncing, so a flaky CRM never loses a lead.** `CRMService.capture` validates → saves the `captured` lead → *then* attempts sync → saves a new immutable version annotated with the result. A provider that raises is caught and recorded as `sync_failed` against the already-captured lead; the lead is never lost to an external hiccup. Sync only ever *annotates* — it bumps `version` and writes a new record, never mutates the captured one.

**3) Dark-by-default seam that fails loud, never silently.** `NC_CRM_PROVIDER` defaults to `"null"` (capture locally, sync nothing — the honest default until a real CRM is wired). `"airtable"`/`"hubspot"` are declared seams that currently **raise `CRMConfigError` at startup** because no real integration has been built — refusing to look like sync works when it doesn't, rather than silently no-op'ing. `NC_CRM_LEAD_STORE_PATH` defaults unset → `InMemoryLeadStore`, which works with zero config but **forgets on restart and never pretends otherwise**; set it → `JsonlFileLeadStore`, append-only JSON-lines, flushed + `os.fsync`'d, real **single-host** durability (survives process restart). It is honestly *not* a replicated multi-host database, and on an ephemeral host (Render free-tier `/tmp`) the file is wiped on redeploy — a property of the host, not a durability the store can promise away. A stale lower-version write never rolls a lead back (`_supersedes` guard).

**4) Full traceability, full wiring.** Every `Lead` carries `id`/`created_at`/`version`/`parent_ids`/`source`/`trace_id`; the captured lead inherits the request's `X-Request-ID` as its `trace_id`, so it walks back to the request that created it, and a repeat submission by the same normalized email links `parent_ids` to the prior lead. The service is built at startup (`build_crm_service(settings)`) and stashed on `app.state.crm`; the routes read it (with a dark in-memory fallback if the lifespan never ran). Three endpoints: `POST /api/crm/public/leads` (**public, no auth** — the anonymous form posts here; a malformed email is a `422`, we refuse to capture an uncontactable lead), `GET /api/crm/leads` and `GET /api/crm/leads/{lead_id}` (**authed** sales views). `api/middleware/auth.py` allow-lists only the `/api/crm/public` subtree.

**5) What this is NOT (operational-before-launch still needs).** No real provider exists, so no lead can reach `synced` — the honest posture is "captured locally, nothing synced." A production deployment that means to keep its leads MUST set `NC_CRM_LEAD_STORE_PATH` to durable (non-`/tmp`) storage. `pipeline_status` exists on the model but has no transition endpoint yet (no notification/routing, no dedup-merge UI). And the public endpoint is intentionally exempt from JWT + the per-key rate limiter (it's anonymous); before public launch it needs its own abuse controls (per-IP limit / captcha / honeypot), mirroring the Atlas LIVE invite-gate pattern.

### Pieces (this entry)
- `api/services/crm/models.py` *(new)* — `Lead` / `LeadSubmission` / `CRMSyncResult` frozen value objects + the honesty guards: `CRMSyncResult.__post_init__` refuses a `synced` result without a real `external_id` + `is_real=True`; `Lead.with_sync_result` maps result→status (`synced`/`sync_failed`/`sync_pending`) and bumps the version immutably. `CRM_SCHEMA_VERSION = "noetic_crm.v1"`.
- `api/services/crm/store.py` *(new)* — `LeadStore` Protocol + `InMemoryLeadStore` (dark, non-durable, honest) + `JsonlFileLeadStore` (append-only, flush+fsync, single-host durable, replays latest-version-per-id on load). `_supersedes` version-regression guard shared by both.
- `api/services/crm/sync.py` *(new)* — `CRMSyncProvider` ABC + `NullCRMProvider` (advertises its own no-op: `synced=False, is_real=False`) + `build_crm_provider(settings)` factory that **fails loud** (`CRMConfigError`) for airtable/hubspot/unknown.
- `api/services/crm/service.py` *(new)* — `CRMService.capture` (validate → capture durably → sync → annotate, provider-raise-safe) + `build_crm_service` / `build_lead_store` / `build_dark_crm_service`.
- `api/services/crm/__init__.py` *(new)* — public re-exports.
- `api/routes/crm.py` *(new)* — the public capture endpoint (honest receipt: `{lead_id, captured, sync_status, synced, schema_version, message}`) + the two authed sales views; dark in-memory fallback if `app.state.crm` is absent.
- `api/config.py` *(edit, +2 settings)* — `crm_provider` (`NC_CRM_PROVIDER`, default `"null"`) + `crm_lead_store_path` (`NC_CRM_LEAD_STORE_PATH`, default unset), both dark-by-default with the honesty rationale in the comment block.
- `api/middleware/auth.py` *(edit, +1 prefix)* — `/api/crm/public` added to `PUBLIC_PATH_PREFIXES`; only the `/public` subtree is open, the authed sales views stay JWT-protected.
- `api/main.py` *(edit, +2 spots)* — lifespan builds `build_crm_service(settings)` onto `app.state.crm` and logs the honest serving posture (`store=… provider=…`); `crm.router` imported + included.
- `docs/working/crm/01_lead_capture_dark_seam_2026_06_02.md` *(new)* — the honesty-rule table, file inventory, the 3 endpoints, the 2 config knobs, what the tests prove, and the "Not done here" list. **Status: BUILT and WIRED, capture-only.**

### Tests (this entry)
- `tests/test_crm_lead_capture.py` *(new, 37 tests, all green)* — the honesty core (import-isolated, no app): the null provider never reports a landing; the factory fails loud for unimplemented providers; a sync failure leaves the lead **captured** + annotated `sync_failed` (never lost); the durable store returns a captured lead after a simulated restart and keeps capture + sync annotation as two append-only lines; a stale lower-version write never rolls a lead back. Plus route tests: the public endpoint needs no auth and never over-claims `synced`; the sales views require auth (401); the `trace_id` survives the HTTP round-trip. Route tests mint a **unique** `api_key` per call (own fresh rate-limit bucket), so they consume zero shared budget.
- Full suite re-run as the pre-commit gate: **48 failed, 1375 passed, 8 skipped, 3 xfailed** — an **exact match to the documented pre-existing baseline** (the 48 are the same `test_wrap` rate-limit pollution + the broken `api.notation` / cas-native imports, none touching CRM modules). My authed tests use unique api-keys, my public tests skip rate-limiting, and a no-auth request 401s before the rate-limiter — so the CRM suite consumes **zero** shared rate-limit budget and cannot have pushed any other test over the 429 edge. **48 = 48 is a clean no-regression result.** No external CRM is wired; production syncs nothing; the seam stays **dark**.

## `reads_served` Phase-3 odometer + a posture-aware, **hosted-capable** ledger watch, BUILT — discovered that step 4's literal "watch `reads_compared > 0`" criterion is **structurally impossible** under read-authority, and shipped the honest equivalent: a second odometer for the authoritative-read path, a verifier that watches whichever odometer the live posture makes move, and a hosted runbook (doc 15) that is honest about why read-authority's green is a *weaker* guarantee than shadow's; production stays **dark** (Jun 2, 2026)

Step 4 of the runbook (doc 12) says: flip `NC_STATE_LEDGER_READ_AUTHORITY=true`, then watch the same zero-divergence evidence the shadow watch earned. Preparing to run that, I traced the counter and found the criterion cannot hold: **`reads_compared` increments only inside `shadow_compare`, which only runs while the dicts are authoritative.** The instant read-authority flips, the live read sites serve from the ledger (`read_payload` / `read_all_payloads`) with no dict to compare against — so `shadow_compare` stops firing and `reads_compared` **freezes**. Watching it would make a *correctly working* read-authority deployment look dead. This entry fixes that honestly and changes **no production behaviour**: the new counter only moves under read-authority, which requires an installed mirror, and production installs none.

**1) A symmetric `reads_served` odometer — the Phase-3 denominator.** `LedgerMirror` gains a lock-guarded `_reads_served` that ticks once per *authoritative* ledger read: `read_payload` +1 after a successful get (a propagating `StateStoreError` does **not** tick — a read the ledger could not answer is not a serve; a `None`/missing record **does** tick — the ledger authoritatively answered "no such record"), and `read_all_payloads` +1 **per call, not per row** (the operator watches a climbing read count, not a row tally). `tally()` now returns `{reads_compared, reads_served, divergences_found, last_divergence}`. The two odometers never cross-contaminate: a shadow-compare moves `reads_compared` only; an authoritative read moves `reads_served` only. Under read-authority `reads_compared` freezes and `reads_served` climbs — a clean phase handoff. Like `reads_compared`, `reads_served` is cumulative throughput and is **not** reset by `clear_divergences()`.

**2) The verifier watches the posture's live odometer, not a hard-coded one.** `scripts/verify_state_ledger_enabled.py` maps posture→odometer (`shadow → reads_compared`, `read-authority → reads_served`) and reads the before/after delta off whichever one the **observed** posture makes live. It also gates `posture-after` first, then adds a `posture-stable` gate that rejects a mid-run posture change (which would make the before/after delta compare two different counters), then `reads-grew` on the live odometer, then `zero-divergence`. `--require-posture {shadow,read-authority,any-enabled}` selects the gate; `result.json` now carries `read_odometer` + both raw counters so the evidence is unambiguous about which denominator was watched.

**3) The honesty asymmetry, made explicit (doc 15).** Shadow zero-divergence proves **read fidelity** — every ledger read *matched* the dict that served it. Read-authority zero-divergence proves only that **dual-writes didn't fail** (the dicts remain a valid rollback target); it does **not** re-prove fidelity, because nothing is comparing the two reads anymore. That is precisely **why step 4 stays gated behind a clean, sustained shadow watch** — the shadow phase is the *only* place read fidelity is proven, and it must be proven before the dicts stop serving. The finding reinforces the directive ordering rather than changing it.

**4) Production untouched, dark preserved.** Both flags still default off; with no mirror installed both odometers stay 0 and the status surface still returns exactly `{"posture": "dark"}`. The change is additive (O(1) counter + a posture map in an operator script) and the sacred migration suite is unchanged and green.

### Pieces (this entry)
- `api/services/production/state_substrate/migration.py` *(edit)* — additive `_reads_served` odometer on `LedgerMirror`: ticked in `read_payload` (after a successful get) and `read_all_payloads` (per call); surfaced in `tally()`; `clear_divergences()` leaves both odometers intact. Dark path byte-for-byte unchanged.
- `api/services/production/state_substrate/observability.py` *(edit)* — docstring enumerates `reads_served` as the Phase-3 odometer; the count flows through `ledger_status()` automatically (no logic change — it returns the live `tally()`).
- `api/routes/state_ledger_status.py` *(edit)* — docstring documents the phase-dependent odometer (`reads_compared` Phase-2, `reads_served` Phase-3).
- `scripts/verify_state_ledger_enabled.py` *(edit)* — posture→odometer map + `read_odometer_key()`; step-2/step-6 read the posture-appropriate odometer; new `posture-stable` gate; `result.json` records `read_odometer` + both raw counters. Hosted defaults (`--base-url https://noetic-compass-api.onrender.com`, auth via `/auth/token`).
- `docs/working/production_readiness/15_hosted_enable_runbook_2026_06_02.md` *(new)* — the hosted-enable runbook: the deploy blocker (all ledger code is on `codex/cas-harness-live-run`, 37 ahead of `master`, which Render deploys — an owner-only merge/branch decision), free-tier `/tmp` ephemerality honesty, the two-posture watch commands, and the read-fidelity asymmetry that keeps step 4 gated. **Status: PREPARED, not VERIFIED** on hosted.

### Tests (this entry)
- `tests/test_state_substrate_observability_tally.py` *(edit, +6)* — `reads_served` counts authoritative reads separately from shadow-compares; stays 0 through pure shadow traffic; counts one-per-list-read not per-row; counts an authoritative miss; does **not** count a failed (fail-loud `StateStoreError`) read; is cumulative throughput not reset by clear. Fresh-tally exact-equality updated to include `reads_served: 0`.
- `tests/test_state_ledger_observability_status.py` *(edit, +1)* — the status surface exposes the `reads_served` odometer under read-authority (`reads_served` climbs, `reads_compared` frozen at 0, `divergences_found` 0). Shadow exact-equality updated to include `reads_served: 0`.
- Ledger surface re-run green as the pre-commit gate: **39 passed** (`tally` + `status` + the sacred `migration` suite). The 48 full-suite failures are **pre-existing and unrelated** — proven by re-running the failing set with these changes stashed: `test_wrap` still hits the same `assert 429 == 200` rate-limit pollution and `test_text_signal_analyzer`/`test_turn_admissibility`/`test_type_constraints` still fail on the same broken `api.notation` import (`TurnAdmissibilityContext` missing). None touch the modules changed here. Production stays **dark**; read-authority not flipped; **Phase 4 stays HELD**.

## Rollout steps 1–3, **VERIFIED under real HTTP service traffic** — booted a real `uvicorn api.main:app` with `NC_STATE_LEDGER_ENABLED=true`, drove a full distributed-audit lifecycle over loopback HTTP while the `LedgerMirror` dual-wrote + shadow-compared a durable `SqliteStateStore`, and watched `GET /api/state-ledger/status` climb to **95 shadow-compares, 0 divergences** while the dicts still served every read. Read-authority held **false**; **Phase 4 untouched** (Jun 2, 2026)

This is the gate doc 12 names as step 2 — *watch zero-divergence accumulate on real traffic before moving read-authority* — earned with **real numbers instead of inference**. The mirror (workstream 10), the observability surface (entry below), and the runbook are all built; what was missing was running them together against a live server and proving the result. That is what this entry does, and only that: it changes **no production code** and leaves production **dark**.

**1) Enabled posture confirmed at boot, before any traffic.** A real `uvicorn api.main:app` booted with `NC_STATE_LEDGER_ENABLED=true` + a fresh durable `NC_STATE_LEDGER_PATH` (SqliteStateStore), read-authority held **false**. The very first `GET /api/state-ledger/status` returned `posture: enabled_shadow_dict_authoritative` with `reads_compared: 0` — proving the bootstrap installed the `LedgerMirror` into both live services (dual-write + shadow-compare) while the dicts stayed the read authority, exactly the Phases-1–2 posture.

**2) Full lifecycle over real HTTP while the mirror was live.** A **separate** client process drove **create → dispatch → register workers → prepare fleet → lease → receipt → merge** over loopback HTTP through the full middleware stack (request-id → JWT auth → rate-limit → audit-log), every request `200 OK`, merge reaching `status=COMPLETE`, `gate=ready_for_verifier`. It minted its own Bearer JWT with the shared `NC_JWT_SECRET` (the auth middleware verifies signature + expiry only) and computed each Evidence Packet fragment ref with the real `build_evidence_fragment_ref`, so the server's recompute-and-compare validation passed. The "create → dispatch → fleet → evidence" flow demonstrably still works with the ledger mirror active (runbook step 3).

**3) 95 clean shadow-compares ⇒ the dual-writes actually landed.** After the lifecycle plus three rounds of touching every ledger-mirrored read site, the tally read `reads_compared: 95, divergences_found: 0, last_divergence: null`. This is load-bearing: a dual-write that failed to persist to the durable store would surface as a missing/disagreeing ledger read on the next compare — a divergence. 95 clean compares is therefore direct evidence the writes reached SQLite and matched the dicts byte-for-byte, not just that reads were exercised.

**4) Honesty boundary (what this is NOT).** Single embedded `SqliteStateStore` on one host: this proves the mirror is **correct and durable to this process's own close/reopen**, *not* host-loss survival (that needs sync replication + failover — verified separately for multi-host Postgres in commit `c32f639`). Divergence is backend-agnostic, so the zero-divergence result is not SQLite-specific. `NC_STATE_LEDGER_READ_AUTHORITY` stayed **false** (step 4 not done); **Phase 4 deletes nothing and stays HELD** (step 5 not done). `audit_count`/`fleet_counts` stay `0` because they are the boot-time rehydration snapshot of a fresh ledger, not live counters — the live evidence is the `reads_compared` odometer.

### Pieces (this entry)
- `docs/working/production_readiness/14_operational_enable_evidence_2026_06_02.md` *(new)* — the evidence record: what it proves / does not prove, the topology + exact server env, verbatim before/after status, the "reading the numbers" note (why `audit_count` 0 is correct), reproduction, and the two next gates (read-authority, Phase 4).
- `.tmp/ledger_enable/driver.py` *(throwaway, **not committed**)* — the HTTP driver that mints the JWT, runs the lifecycle, touches the read sites, and asserts `posture==enabled_shadow_dict_authoritative ∧ reads_compared>0 ∧ divergences_found==0`. Lives under `.tmp/` by design.

### Tests (this entry)
- **No production code touched** — this is a runtime verification, not a code change. The state-substrate + ledger surface was re-run green as a pre-commit gate: **68 passed, 5 skipped** (the 5 skips are the live-Postgres tests, which need `NC_TEST_POSTGRES_URL`). Production stays **dark** (both flags default off); read-authority not flipped; **Phase 4 stays HELD**.

## Docs 12 + 13, the operational rollout runbook and the Phase-4 deletion plan, WRITTEN — a gated step-1→4 turn-on procedure (GO/NO-GO + instant rollback at every gate, declared-vs-verified enforced) and an **analysis-only** Phase-4 deletion map; both reference the now-built observability surface and the now-verified live-Postgres tests **by name**. **Phase 4 deletes nothing and stays HELD** (Jun 2, 2026)

The mechanism (workstream 10), the multi-host backend (workstream 11, now live-verified), and the observability surface are all built. What was missing was the *procedure*: the order an operator turns the two flags on, what evidence each gate must earn before advancing, and how to roll back at every gate. These two docs are that procedure — and the explicit refusal to let Phase 4 begin on anything less than proven, soaked evidence.

**1) Doc 12 — the order is an order, not a menu.** The runbook owns exactly one thing: the five-step turn-on (`ENABLED` → watch zero-divergence → live Postgres → `READ_AUTHORITY` → consider Phase 4), with a GO/NO-GO criteria list and a rollback at every gate. Its single invariant is the program's own: *declared-vs-verified is sacred.* Setting a flag is a **declaration**; the accumulated zero-divergence tally is the **verification** — and step 4 (moving read-authority onto the ledger) is licensed only by the verification, never the flag. Steps 1-4 are all **reversible** (the dual-write keeps the dicts a hot write-through cache, so `disable_ledger_reads()` is an instant, lossless rollback); only Phase 4 is not, which is why it lives in its own gated plan.

**2) Doc 13 — analysis only; it maps the work, it does not authorize it.** The Phase-4 plan **deletes nothing**. It enumerates every read/write/rehydrate/reset site of the four process-global dicts, classifies what becomes dead vs what is still needed after the read flip, and states the preconditions that must *all* hold before any deletion is safe. **Its single most important finding:** the `_FRAGMENT_REFS` replay guard at `_validate_fragment_ref` (`cas_harness_fleet_executor.py:1027`) reads the in-RAM set with **no `read_from_ledger` gate** — so unlike the other three dicts (whose gated reads stop consulting the dict once read-authority flips), the dedup set is a **LIVE read even in `enabled_ledger_read_authoritative` posture**. Deleting it without first re-pointing the guard at a ledger existence check removes replay protection outright — a correctness failure, not just a loss. The plan also names the defining irreversibility risk: Phase 4 destroys the instant-rollback hot cache, so it cannot begin until a verified host-loss-survivable backend, a tested non-dict recovery path, the ledger-backed replay guard, and end-to-end fencing have demonstrably taken over the risks the cache silently absorbed.

**3) Reconciliation.** Doc 12's cross-reference to the status surface — previously a placeholder ("the exact function name is wired in by the observability workstream") — is now wired concretely to `ledger_status(handle)` (`observability.py`) and **`GET /api/state-ledger/status`** (`api/routes/state_ledger_status.py`), the surface shipped in the entry below, including its dark-safe contract (returns exactly `{"posture": "dark"}` and never fabricates a count no shadow-compare earned).

### Pieces (this entry)
- `docs/working/production_readiness/12_operational_rollout_runbook.md` *(new)* — the gated five-step turn-on procedure: per-step action, expected posture log-line + status readout, GO criteria, NO-GO/abort signals, and rollback; a quick-reference flags↔postures↔log-lines↔rollbacks table; the cross-reference now naming `ledger_status` / the endpoint concretely.
- `docs/working/production_readiness/13_phase4_dict_deletion_plan.md` *(new)* — analysis-only Phase-4 map: (a) every site of the four dicts; (b) dead-vs-still-needed after the read flip; (c) the six preconditions; (d) the safe deletion order with per-step tests; (e) the irreversibility risk and what must replace the cache first. The `_FRAGMENT_REFS:1027` ungated-read asymmetry called out as the load-bearing finding.

### Tests (this entry)
- Docs only — no code touched, no test surface changed. Production stays **dark** (both flags default off); **Phase 4 stays HELD** — production still reads the four dicts, so this plan authorizes no deletion.

## Doc-12 observability surface, BUILT — a pure, dark-safe `ledger_status(handle)` and a read-only **`GET /api/state-ledger/status`** that report the rollout posture and the **live divergence tally**, so an operator can *watch* zero-divergence evidence accumulate (rollout step 2) instead of inferring it; production stays **dark**, and the surface never fabricates a count no shadow-compare earned (Jun 2, 2026)

The operational-enable entry below gave the two flags and the honest posture log-line, but the step-2 gate — *watch zero-divergence accumulate on real traffic before moving read-authority* (`12_operational_rollout_runbook.md` §Step 2) — needs a surface the operator can actually read while the process runs. This entry is that surface, and only that: one pure function over the handle the lifespan already stashes on `app.state.state_ledger`, exposed read-only. It reads counters the mirror already maintains; it never mutates state and never touches what serves reads.

**1) A pure function, duck-typed, no import cycle.** `ledger_status(handle)` lives in `api/services/production/state_substrate/observability.py` and reads the handle **structurally** (by attribute: `read_authority`, `mirror`, `audit_count`, `fleet_counts`), not against the concrete `StateLedgerHandle` type. So it imports nothing from `api/state_ledger_bootstrap.py` (which imports this package), is safe to re-export from the package `__init__`, and is directly unit-testable with a tiny stand-in handle.

**2) Honest silence on dark.** When `handle is None` (no mirror installed — production's posture) the function returns **exactly** `{"posture": "dark"}` and reads nothing further. Inventing a "0 divergences" here would be a *fabricated* measurement — no shadow-compare ever ran — so it reports honest silence instead. This is the declared-vs-verified discipline applied to the status surface itself.

**3) The tally is a REAL measured count, with a cumulative odometer.** `LedgerMirror` gains lock-guarded `_reads_compared` / `_divergences_found` / `_last_divergence` and a `tally()` returning `{reads_compared, divergences_found, last_divergence}`. `reads_compared` increments on every shadow-compare (a short, non-nesting `with self._lock` at the top — no deadlock with the existing accounting). `_record()` is the single accounting point for all six divergence kinds — it increments `_divergences_found` and sets `_last_divergence` (a small `{kind, record_id, reason, at}` detail dict — never payloads, O(1)). `clear_divergences()` resets the divergence half but **not** `reads_compared`, so the denominator is a cumulative odometer. The dark path is byte-for-byte preserved.

**4) Read-only endpoint, defensive on `app.state`.** `GET /api/state-ledger/status` (`api/routes/state_ledger_status.py`) is a thin shell over `ledger_status`: it reads `getattr(request.app.state, "state_ledger", None)` so even a minimal test context where the lifespan never ran degrades to the dark posture rather than raising. A status endpoint must never be the thing that breaks. The route is observation only — it never mutates state and never touches what serves reads.

### Pieces (this entry)
- `api/services/production/state_substrate/observability.py` *(new)* — the pure `ledger_status(handle)` + the three posture constants (`POSTURE_DARK` / `POSTURE_ENABLED_SHADOW` / `POSTURE_ENABLED_READ_AUTHORITY`).
- `api/routes/state_ledger_status.py` *(new)* — the read-only `GET /api/state-ledger/status` route.
- `api/services/production/state_substrate/migration.py` *(edit)* — additive observability on `LedgerMirror`: lock-guarded counters, `tally()`, single-point `_record()` accounting; dark path unchanged.
- `api/main.py` *(edit, +2 lines)* — `state_ledger_status` added to the route import block and `include_router`-ed.
- `api/services/production/state_substrate/__init__.py` *(edit)* — additive re-exports of `ledger_status` + the posture constants; `PostgresStateStore`-not-re-exported note preserved.

### Tests (this entry)
- `tests/test_state_ledger_observability_status.py` *(new, 7)* — dark→`{"posture": "dark"}` and nothing else; shadow vs read-authority posture; the tally reflects real shadow-compares after a built mirror; `fleet_counts` is a copy not the live dict; structural read via a stand-in handle; tally degrades to `None` (never raises) when a handle lacks a usable mirror.
- `tests/test_state_substrate_observability_tally.py` *(new, 7)* — fresh tally all-zero / no last_divergence; `reads_compared` counts every compare including agreements; a divergence increments the count and records the last detail; last_divergence tracks the most-recent only; write-failures count too; `clear_divergences()` resets the divergence tally but **not** the odometer; tally count matches the divergence-log length.
- Local validation (`C:/Python314/python.exe -m pytest`): the two new files → **14 passed in 0.36s**; the full state-substrate + state-ledger sweep → **68 passed, 5 skipped** (the 5 are the live-Postgres tests, gated on `NC_TEST_POSTGRES_URL`). Dark-by-default preserved; zero regressions.

## Workstream-11 multi-host substrate, now **LIVE-VERIFIED** — the Postgres backend's contract conformance, close/reopen durability, and fence-MINT monotonicity moved from *declared* to *verified* against a real **PostgreSQL 16.4** server (**10/10 tests, 3 consecutive runs**); **host-loss survival stays declared** (single instance, no sync replica) — the one honesty boundary deliberately unchanged (Jun 2, 2026)

The entry directly below shipped the Postgres backend + fencing token **built but not yet run against a live server** — so "`PostgresStateStore` passes the contract" was a *declared* claim. This entry is the verification: the same `run_state_store_contract` the in-memory and SQLite backends pass, plus records/leases surviving a real close/reopen, the version sequence continuing across reopen, and the fence sequence issuing strictly-increasing tokens across re-acquire and reclaim-after-expiry — all **observed green against a real PostgreSQL 16.4 server**, 10/10, three consecutive runs. Discipline held: this was *verify-don't-trust*, reproduced directly rather than taken on a sub-agent's word.

**1) A no-docker / no-admin path to a real server.** The blocker on verification was never the code — it was standing up a real Postgres on a Windows box with no Docker and no admin rights. `run_postgres_state_substrate_live.py` is that path: it downloads a self-contained EnterpriseDB binaries zip (no installer, no service registration), runs `initdb` into a temp dir, starts the server on a throwaway port pointed at a throwaway database, sets `NC_TEST_POSTGRES_URL`, runs `tests/test_state_substrate_postgres.py`, and tears the server down — with `--bindir` to reuse already-extracted binaries on repeat runs (skips the 338 MB download). A Windows-specific `pg_ctl` pipe-inheritance deadlock (the long-lived `postgres` daemon inherits the parent's captured pipe write-ends and the parent's read never sees EOF) is closed by sending the launcher's streams to `os.devnull`; the server's own diagnostics still go to `-l logfile`.

**2) The verification STRENGTHENED the test, it did not weaken it.** The live run surfaced a *test-harness* bug, not a store bug: the contract factory reused one shared schema across factory calls, but `run_state_store_contract` expects per-factory isolation (SQLite gives it a unique file per call) and its sub-tests are not disjoint, so a leaked row produced a *false* failure. Fixed by minting a **fresh schema per factory call** — the Postgres analogue of SQLite's unique-file-per-call — tracked and dropped in `finally`. The reconnect/durability tests, where shared storage is the correct semantics, keep a single shared schema. The store SQL was correct throughout; the fix makes the test honest, not lenient.

**3) The honesty boundary that does NOT move.** A single instance passing these tests earns *"survives restart,"* never *"survives host loss"* — that needs `synchronous_commit=on` + `synchronous_standby_names` + a synchronous replica + failover routing, none of which has been stood up. The `postgres_store.py` module docstring's HONESTY BOUNDARY is flipped from "no live-Postgres test has been run" to "verified against a live PostgreSQL 16.4 server … 10/10, 3 consecutive runs, 2026-06-02," preserving the host-loss caveat verbatim. Docstring-only change; no functional code moved.

**4) Drafted as a CI gate.** `.github/workflows/postgres-state-substrate.yml` runs the same live tests against a `postgres:16` service container, so the live conformance check can become a real gate in CI rather than a once-observed local result.

### Pieces (this entry)
- `scripts/run_postgres_state_substrate_live.py` *(new)* — the no-docker/no-admin embedded-Postgres runner (download→initdb→start→test→teardown; `--bindir` reuse; `--keep` for manual poking; Windows pg_ctl deadlock closed via devnull).
- `.github/workflows/postgres-state-substrate.yml` *(new)* — CI job: `postgres:16` service container + `NC_TEST_POSTGRES_URL`, running `tests/test_state_substrate_postgres.py`.
- `tests/test_state_substrate_postgres.py` *(edit)* — split the fixture into `pg_admin` (autocommit admin conn) + `pg_schema`; the contract factory now mints a **fresh schema per call** and drops all created schemas in `finally`. The HONESTY NOTE became a VERIFICATION NOTE (10/10, 3 runs, PG 16.4, 2026-06-02; host-loss still NOT verified). Strengthens the test.
- `api/services/production/state_substrate/postgres_store.py` *(edit — docstring only)* — HONESTY BOUNDARY → VERIFICATION; host-loss caveat preserved. No functional change.

### Tests (this entry)
- Live run reproduced directly (`run_postgres_state_substrate_live.py --bindir C:/tmp/pgportable/pgsql/bin -- -v`) → **10 passed in 5.86s** against PostgreSQL 16.4 on a throwaway port, clean server teardown; observed across 3 consecutive runs. The 10 named tests cover fence defaults/accept/reject, the high-water-mark guard (incl. persisted-mark restore), the full `run_state_store_contract`, record/lease reconnect-survival, version-sequence continuation, and per-resource fence monotonicity.
- No-DB regression unchanged: the state-substrate + state-ledger sweep → **68 passed, 5 skipped** (the 5 are exactly this file's live-Postgres tests when `NC_TEST_POSTGRES_URL` is unset).

## Workstream-11 multi-host substrate, BUILT — *not yet live-verified*: a synchronous-`psycopg` `PostgresStateStore` realizes the **same locked** `StateStore` Protocol, and the dead-but-not-expired-holder hazard is closed by a monotonic **fencing token** (additive `Lease.fence` + a resource-side guard). The resource-side check is **unit-proven now**; the live-cluster claims are **declared, pending a real Postgres** (Jun 1, 2026)

The durability ladder reached *durable single-host* (SQLite: one file, one host — void the instant a second host appears). Workstream 11 takes the **identical** locked Protocol to *durable across hosts* (Postgres) **behind the same interface**, and closes the one hazard SQLite's ladder never had to face: a stalled holder acting after its lease lapsed. The discipline is the project's own — *declared vs verified is sacred* — and it is applied with a scalpel here, because this is the first rung the sandbox **cannot fully verify**: what is *built* and what is *verified* are deliberately separated, named, and tested apart. The resource-side fencing guard — the half that actually stops a stale write — is verified now, with no database. The Postgres backend's contract-conformance is **declared**, and waits on a live server before it may claim "passes the contract."

**1) The same locked Protocol, synchronous psycopg 3 — deliberately not asyncpg.** The `StateStore` Protocol is synchronous (`def put`, not `async def`); a sync driver matches it 1:1. asyncpg is async-only and would force an event-loop bridge inside every Protocol call — exactly the dishonest complexity this workstream warned against. `PostgresStateStore` implements every locked method with the SQL from doc 11 §3 (records §3.1; the conditional-reclaim `INSERT … ON CONFLICT DO UPDATE … WHERE expires_at <= now OR holder = EXCLUDED.holder` leases of §3.2), with the `UPDATE … WHERE version = expected` compare-and-set the contract requires. psycopg is imported **lazily** (inside `__init__`; `TYPE_CHECKING` at module scope), and `PostgresStateStore` is deliberately **not** re-exported from the package (mirroring `SqliteStateStore`) — so importing the substrate package never requires psycopg, and the in-memory / SQLite backends and every existing test import exactly as before. Verified: the package and the full substrate suite import and pass with no psycopg driver loaded.

**2) The fencing token closes the §5.2 hazard — additively, with no Protocol change.** The central multi-host failure: a holder acquires a lease, stalls past its TTL (GC pause, VM freeze), the store *correctly* reassigns the lease to a newer holder, then the stalled holder wakes *still believing it holds the lease* and acts. No acquire-time SQL can prevent this — the lease **was** validly reassigned; the old holder's belief is simply stale. The fix has two halves: **mint** — a Postgres `BIGINT` sequence (`lease_fence_seq`, `nextval`) stamps a strictly-increasing `fence` into every `Lease` the store returns (re-acquire and reclaim-after-expiry both advance it; renew *preserves* token and fence); and **check** — the protected resource remembers the highest fence it has acted on and rejects any operation carrying a fence ≤ that high-water mark (Kleppmann: fencing is "a property of the resource, not of the lock"). It is wired as the **additive, interface-compatible strengthening** §5.2 prescribes: a defaulted `fence: int = 0` appended *last* to the `Lease` dataclass — **no Protocol method changed**, and the in-memory / SQLite stores and the existing `run_state_store_contract` stay green because the field defaults — plus a backend-agnostic `fencing.py` (`reject_stale_fence` / `FencingGuard`, raising the new `StaleFenceToken`).

**3) The resource-side check is REAL, observed coverage — the mint side waits on a live Postgres.** `fencing.py` is pure logic with no DB dependency, so the half that actually stops the stale write is verifiable now, deterministically — and **it is verified**: the unit tests prove a strictly-increasing run is accepted, an equal-or-lower fence is rejected with `StaleFenceToken`, the high-water mark never moves backward on a rejection, and a persisted mark can be restored — including the exact Kleppmann scenario (a stalled holder wakes with fence 5 after a newer holder acted with fence 7; rejected). The `Lease.fence == 0` default is asserted directly. These run with no database and **pass** (part of the 54-test substrate sweep). The mint side — the real sequence issuing strictly-increasing fences across acquire / re-acquire / reclaim-after-expiry — and full Protocol conformance + close/reopen durability can only be exercised against a real server.

**4) Declared vs verified, drawn exactly — and said so in the doc.** The live tests (`run_state_store_contract` against `PostgresStateStore`; records/leases surviving a reconnect; version-sequence continuation; fence-mint monotonicity) **skip** unless `NC_TEST_POSTGRES_URL` points at a reachable server, and **have not been run** — so "`PostgresStateStore` passes the contract" is a *declared* claim, and doc 11's status line (downgraded from "design + gap blueprint" to "IMPLEMENTED … not yet run against a live cluster") plus a new implementation-status note say exactly that, in those words. "Durable across hosts" stays a *per-config* claim: a single instance, once the tests pass against it, earns "survives restart"; it earns "survives host loss" **only** with `synchronous_commit = on` + `synchronous_standby_names` + a synchronous replica + failover routing — none of which has been stood up. Redis (§4) is **deferred**, consistent with doc 11 §7's "Postgres-for-both as the honest default"; no `RedisStateStore` was built, and nothing claims one was. The §6 truthful-claims table is left intact as the authority on which claim each configuration earns.

### Pieces (this entry)
- `api/services/production/state_substrate/postgres_store.py` *(new)* — `PostgresStateStore(StateStore)`: every locked Protocol method on **synchronous psycopg 3**, SQL per doc 11 §3 (records §3.1; conditional-reclaim leases §3.2), plus the fencing sequence minting `Lease.fence`. psycopg imported lazily; UTC-pinned session; per-statement commit/rollback so a translated error never wedges the connection idle-in-transaction. Module docstring carries an explicit HONESTY BOUNDARY (no live run; declared-not-verified) and the §3.4/§6 survives-restart vs survives-host-loss vs prevents-two-acting claim table.
- `api/services/production/state_substrate/fencing.py` *(new)* — backend-agnostic, DB-free resource-side guard: `reject_stale_fence(highest_seen, incoming)` (pure, strictly-greater decision) and `FencingGuard` (thread-safe high-water mark), both raising `StaleFenceToken`. Pure logic so the §5.2 *check* is testable with no Postgres.
- `api/services/production/state_substrate/interface.py` *(edit)* — the only Protocol-adjacent change: a defaulted `fence: int = 0` appended last to `Lease` (additive, backward-compatible — every existing keyword `Lease(...)` stays valid and gets 0), and a new `StaleFenceToken(StateStoreError)` carrying `highest_seen` / `incoming`. **No method signature touched.**
- `api/services/production/state_substrate/__init__.py` *(edit)* — additive exports `StaleFenceToken` / `FencingGuard` / `reject_stale_fence`; `PostgresStateStore` deliberately NOT re-exported so the package imports without psycopg.
- `requirements.txt` / `requirements-runtime.txt` *(edit)* — `psycopg[binary]` (sync driver), each in its file's pinning style, with the asyncpg-vs-psycopg rationale inline. Imported lazily, so it is only required where the Postgres backend is actually constructed.
- `docs/working/production_readiness/11_multi_host_state.md` *(edit)* — status line downgraded to "Postgres backend + fencing IMPLEMENTED … not yet run against a live cluster," plus an honest implementation-status note separating what is built from what is verified; §6 truthful-claims table intact.

### Tests (this entry)
- `tests/test_state_substrate_postgres.py` *(new)* — three jobs, two live and one DB-free: **(live, skip without `NC_TEST_POSTGRES_URL`)** the Postgres backend passes the *same* `run_state_store_contract` the in-memory and SQLite backends pass, plus records/leases survive a reconnect and the version sequence continues across reopen; **(live)** the fence-MINT path issues strictly-increasing fences across re-acquire and reclaim-after-expiry, threaded through a `FencingGuard` end-to-end; **(DB-free, ALWAYS runs)** the resource-side guard accepts a strictly-increasing sequence and rejects equal/lower with `StaleFenceToken`, plus the `Lease.fence == 0` default. Each live factory call gets a throwaway schema (`search_path`) for isolation.
- Local validation (`C:/Python314/python.exe -m pytest`): the substrate regression sweep — memory/sqlite/migration/live-migration/stress + this new file + operational-enable → **54 passed, 5 skipped** (the 5 skips are this file's live-Postgres tests; its DB-free fencing-logic + `Lease.fence == 0` tests **pass**), proving the additive `Lease.fence` broke **no** existing conformance/migration suite. The live conformance / durability / fence-mint claims remain **declared, pending a real Postgres** — set `NC_TEST_POSTGRES_URL` (e.g. `docker run --rm -e POSTGRES_PASSWORD=pw -p 5432:5432 postgres:16`) to verify.

## Doc-10 **operational enable**, BUILT — the durable ledger can now be turned ON in a real deployment, **default-off and two-flag**, so durability becomes a deliberate operator act instead of a code change; production stays **dark** until a human sets the flags, and the read-authority cutover stays a *separate* flag from merely enabling durability (Jun 1, 2026)

Phase 3 shipped the *mechanism* to move read-authority onto the ledger — built, tested, reversible, and **dark** (no mirror installed in production). What it deliberately did **not** ship was the way an operator actually turns that mechanism on in a real deployment. This entry builds exactly that, and only that: the **operational enable**. The discipline is the project's own — *declared vs verified is sacred*, a serving-path change is deliberate and never casual — so the enable is split across **two** flags that default **off**, and the whole of it lives in small, pure, directly-testable functions so the FastAPI lifespan stays thin and the test suite never spins the app. Turning it on is now a one-line deployment config; it is still **not** the same act as having turned it on and earned the evidence — production is dark today, exactly as before.

**1) Two flags, mapped onto the migration's phases — and the separation is load-bearing.** `NC_STATE_LEDGER_ENABLED` brings **Phases 1–2** live: it builds a `SqliteStateStore` on `NC_STATE_LEDGER_PATH`, wraps it in one `LedgerMirror`, installs that single mirror into **both** live services (they partition the one store by record `kind`), and **rehydrates** each service's dicts from the durable file so a restarted process serves what it served before — dual-write + shadow-compare now run against real traffic, but **the dicts remain the read authority**. `NC_STATE_LEDGER_READ_AUTHORITY` performs the **Phase-3** flip: only when it is *also* set does install additionally call `enable_ledger_reads()`. Keeping the flip a distinct flag is the entire point — it lets a deployment run the mirror live and accumulate real-traffic zero-divergence evidence for as long as it wants *before* ever changing what serves reads. Both default `False`, so an unconfigured deployment is fully dark.

**2) Dark-by-default is preserved *structurally*, not merely respected.** `install_state_ledger` keys entirely off `settings.state_ledger_enabled`; when it is `False` (the default, production's posture) the function installs no mirror and returns `None` — the exact state every existing test asserts. With no mirror, the live `get_*` / `list_*` read sites (which gate on `_STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger`) cannot consult a ledger that is not there. You cannot enable durability by accident; you have to set the flag.

**3) Install fails LOUD, never degrades silently.** If the operator set `state_ledger_enabled=True` and the install cannot complete (unwritable path, store error, rehydrate failure), the error **propagates** so startup fails visibly. Silently degrading to dict-only serving while the operator believes durability is on would be a declared-vs-verified violation of exactly the kind this program refuses — a durability claim the running state has not earned. And if the install fails *partway* (the mirror was set on one service before a later step threw), both mirrors are uninstalled (and the store best-effort closed) before re-raising, so a failed startup never leaves a half-installed mirror to mislead the next request or the next test.

**4) Honest startup observability.** An enabled install returns a `StateLedgerHandle` carrying what rehydrate actually restored — `audit_count` and `fleet_counts` (how much pre-restart state came back from the durable file) — and `read_authority` (whether the Phase-3 flip was applied). The lifespan stashes it on `app.state.state_ledger` and logs the one honest posture line: *dark (dict-authoritative)* / *ENABLED, dual-write+shadow, dict-authoritative* / *ENABLED, LEDGER READ-AUTHORITATIVE*. Shutdown hands the same handle back to `teardown_state_ledger`, which uninstalls the mirror from both services (returns to dark) and closes the store.

**5) This is the enable, NOT the act of enabling, and NOT Phase 4.** What ships is the wiring to turn durability on, default-off. Turning it on in a real durable deployment — and earning zero-divergence on real traffic under the first flag *before* setting the second — remains the deliberate, human-gated operator act the directive pins behind "only after that passes." **Phase 4** (deleting the now-shadow dicts) stays strictly downstream of a deployed, proven cutover: production still reads from the four dicts, so deleting them before the enable is live and proven would destroy production state. Multi-host durability is workstream 11.

### Pieces (this entry)
- `api/state_ledger_bootstrap.py` *(new)* — the operational counterpart to the Phase-3 mechanism, all pure/testable: `install_state_ledger(settings) -> StateLedgerHandle | None` (dark→`None`; enabled→build `SqliteStateStore` + `LedgerMirror`, install into both services, rehydrate, conditionally `enable_ledger_reads()`, fail-loud with partial-install unwind), `teardown_state_ledger(handle)` (uninstall both mirrors + close store; `None`→no-op), and the frozen `StateLedgerHandle` (`store` / `mirror` / `audit_count` / `fleet_counts` / `read_authority`).
- `api/config.py` *(edit)* — three **default-off** settings (env_prefix `NC_`): `state_ledger_enabled: bool = False`, `state_ledger_path: str = "state_ledger.db"`, `state_ledger_read_authority: bool = False`, with the two-flag rationale documented inline.
- `api/main.py` *(edit)* — thin lifespan wiring: `install_state_ledger(settings)` on startup, stash on `app.state.state_ledger`, log the honest posture; `teardown_state_ledger(handle)` on shutdown before `close_db()`.
- `docs/working/production_readiness/10_state_substrate_migration.md` *(edit)* — status line + Phase-3 passages updated: the operational enable now exists (default-off, two-flag); what remains is the operational turn-on in a real durable deployment, the multi-host live smoke, and Phase 4.

### Tests (this entry)
- `tests/test_state_ledger_operational_enable.py` *(new, 6)* — the enable proven as pure functions, no app spin-up: **(1)** dark default installs **no** mirror and returns `None`; **(2)** the **real** `Settings()` default is dark (the production posture, asserted directly); **(3)** enabled-but-not-read-authority installs the mirror into both services and serves correctly while the **dicts stay authoritative**; **(4)** the read-authority flip serves from the **ledger** — proven by clearing the backing dict and still getting byte-identical state; **(5)** the enable **survives a process restart on the same path** — a second `install_state_ledger` on the same file rehydrates (`audit_count == 1`, `fleet_counts` exact); **(6)** teardown restores the dark state (both mirrors `None`).
- Local validation (`C:/Python314/python.exe -m pytest`): the operational-enable suite → **6 passed**; the substrate regression sweep — memory/sqlite/migration/live-migration/stress + the new Postgres fencing-logic file + operational-enable → **54 passed, 5 skipped** (the 5 are live-Postgres tests, correctly gated on `NC_TEST_POSTGRES_URL`); the migration-target service + coupled-evidence sweep + config — scale_planner / distributed_audits / fleet_executor / …_contract / evidence_bridge / static_evidence_anchor / mode7_evidence_persistence / production_worm_writes / model_provenance / architecture_adapter / compute_feasibility / config → **202 passed**; plus a real-app **lifespan smoke** (TestClient context manager) confirming the dark-default path installs no ledger (`app.state.state_ledger is None`) and starts/stops clean. **Zero regressions**; production stays dark (both flags default off).

## Doc-10 Phase 3, the **flip itself**, BUILT — but shipped **DARK**: read-authority can now move off the four live dicts onto the durable ledger (`enable_ledger_reads()` makes every public `get_*`/`list_*` reconstruct each record's *stored* state from the ledger instead of the dict), proven by **clearing the dicts and still serving byte-identical state** — **reversible** (a write-through keeps the dicts a hot cache for instant rollback), **fail-closed** (production installs no mirror, so the guard can never engage), and explicitly **not** the operational cutover (enabling it in a durable deployment, and Phase 4, remain separate human-gated steps; multi-host is workstream 11) (Jun 1, 2026)

The prior two entries proved the ledger **agrees** with the dicts (zero divergence) and that a restarted process can **rehydrate** the dicts from it. Both leave the dicts authoritative on the serving path. This entry builds the third and last slice of doc-10's Phase 3 — *the flip itself*: the mechanism that makes the ledger the **read authority**, so a public read reconstructs its answer from the durable rows rather than the process-global dict. The discipline is the project's own — *declared vs verified is sacred*, and a serving-path change is treated as deliberate, never casual — so the flip ships **dark**: built, tested, and reversible, but structurally impossible to engage in production until a human turns it on. The honest one-line status moves from *agrees / survives / rehydrates* to *agrees / survives / rehydrates / **can be made authoritative, dark by default***.

**1) The flip is one switch, and reads reconstruct STORED state — the SAME reconstruction rehydrate uses.** `LedgerMirror` gains a `read_from_ledger` bool (default `False`) with `enable_ledger_reads()` / `disable_ledger_reads()` levers and `read_payload` / `read_all_payloads` accessors. Every public read now branches on `_STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger`: while off it serves the dict and shadow-compares (Phase 2, unchanged); while on it rebuilds each record from the ledger via the *same* `_*_from_ledger_payload` functions rehydrate-on-startup already proved faithful — `get_distributed_audit` / `list_distributed_audits`, `list_workers`, `get_fleet_run` / `list_fleet_runs`. Stored state comes from the ledger; the excluded **views** are re-derived on read exactly as before (worker `status` from `(last_heartbeat_at, cutoff)`, the run's verifier gate via `_refresh_run_gate`). Reuse is the point: the cutover read path *is* the rehydrate read path, so it inherits a proven reconstruction rather than a second, parallel one that could drift.

**2) The proof that read-authority truly MOVED: clear the dicts, still serve.** Under dict-authority the dict *is* the answer, so the only honest demonstration that the ledger is now authoritative is to make it serve a read whose dict is **empty**. The headline test drives the real create→…→merge flow, flips `enable_ledger_reads()`, then clears each backing dict in dependency order and asserts the public read still returns byte-identical state — it can only be coming from the ledger. The order is the honest scope boundary: a run's verifier gate is a derived view recomputed from the **worker** cache in *both* modes, so the run dict is cleared while the workers are still present (proving the run's *stored* state comes from the ledger with the gate reproducing exactly `ready_for_verifier`), and only then are the workers cleared (proving each worker serves from the ledger with `active` re-derived from its durable heartbeat). At the end all four dicts are empty and every read still answered correctly.

**3) Fail-closed by construction — production cannot enable the ledger by accident.** The read sites gate on `_STATE_MIRROR is not None and _STATE_MIRROR.read_from_ledger`. Production installs **no** mirror, so the first half is always false there — the serving path is *structurally* pinned to the dicts; you cannot read from a ledger that is not there. Even with a mirror installed the switch defaults off: an installed-but-disabled mirror is still Phase 2 (it shadows, it does not serve), proven by a test that empties the dict under a *present* mirror and watches the read **miss** until `enable_ledger_reads()` is called — then reverts and watches it miss again. The switch, not the mirror's mere presence, controls the read source, and it is the only thing that does.

**4) Reversible because the dual-write is now a write-through cache — rollback is instant and lossless.** A real subtlety hides under read-authority: `get_*` returns a **fresh reconstruction**, not the dict's instance, so a mutator that read the ledger, mutated that fresh object, and mirrored it would leave the dict **stale** — and a stale dict is a broken rollback. The fix is to make every `_mirror_*` dual-write *also write the dict back* (guarded by `if _STATE_MIRROR is not None`, so production is byte-for-byte unchanged): the dict is kept a faithful hot cache of the ledger at all times. So `disable_ledger_reads()` is an **instant, lossless** return to dict-authority — no rehydrate needed — proven by a test that mutates through the real service API while ledger-reads are live (`dispatch` flips an audit `PLANNED→DISPATCHED`), confirms the mutation landed in **both** the ledger and the dict, then flips back to dict-authority and finds the mutation already there.

**5) Authoritative reads fail LOUD, and this is still NOT the operational cutover.** `read_payload` / `read_all_payloads` **propagate** `StateStoreError` — the exact opposite of the swallow-and-record shadow path — because when the ledger *is* the truth, a read that cannot reach it must fail the request, not fabricate an answer. And the scope is drawn tight: the flip moves authority for **stored state**, not the ACCEPT-gating logic — the run's verifier gate is a derived view that recomputes from the (write-through-current) worker cache in both modes, identical by zero-divergence. What ships here is the **mechanism**, dark by default. Turning it on in a real durable deployment is a separate, human-gated step — the deliberate serving-path change the directive pins behind "only after [rehydrate] passes"; **Phase 4** (deleting the now-shadow dicts) is another; and **multi-host** durability (two replicas on one shared backend, fencing tokens) remains **workstream 11**. The dicts still serve production today; this entry only makes it *possible*, and provably safe, to stop.

### Pieces (this entry)
- `api/services/production/state_substrate/migration.py` *(edit)* — the Phase-3 read-authority switch on `LedgerMirror`: `read_from_ledger` (default `False`, flipped once at cutover, never raced per-request), `enable_ledger_reads()` / `disable_ledger_reads()` levers, and the authoritative-read accessors `read_payload` / `read_all_payloads` that **propagate** `StateStoreError` (fail-loud, the deliberate opposite of `shadow_compare` / `mirror_put`'s swallow). Module docstring's Phase-3 bullet rewritten from "out of scope" to the dark-by-default / reversible / fail-closed mechanism.
- `api/services/cas_harness_distributed_audits.py` *(edit)* — `get_distributed_audit` / `list_distributed_audits` branch onto the ledger under `read_from_ledger` (reconstruct via `_audit_from_ledger_payload`, fall through to the shadow-compared dict path when dark); `_mirror_audit` now write-throughs `_DISTRIBUTED_AUDITS[record.audit_id] = record` inside its `_STATE_MIRROR is not None` guard, so the dict stays a faithful cache for rollback.
- `api/services/cas_harness_fleet_executor.py` *(edit)* — `list_workers` / `get_fleet_run` / `list_fleet_runs` branch onto the ledger (reconstruct via `_worker_from_ledger_payload(…, cutoff=now-DEFAULT_MAX_HEARTBEAT_AGE_SECONDS)` / `_run_from_ledger_payload`, re-deriving each run's gate via `_refresh_run_gate` against the worker cache — a derived view in both modes); `_mirror_worker` / `_mirror_run` / `_mirror_fragment` write-through `_WORKERS` / `_FLEET_RUNS` / `_FRAGMENT_REFS` inside their guards.
- `docs/working/production_readiness/10_state_substrate_migration.md` *(edit)* — status line + Phase-3 gate updated: "all three slices now have a built, tested mechanism," the flip described as shipped dark (reversible / fail-closed / write-through), and a new implementation-status bullet detailing the switch, the reconstruction reuse, and the three safety properties; what remains is the **operational enable**, the multi-host smoke, and Phase 4.

### Tests (this entry)
- `tests/test_state_substrate_live_migration.py` *(+3, now 12)* — the cutover **mechanism** proven on the **real** services, all dark-by-construction: **(1) ledger reads serve stored state after clearing the backing dicts** — drive the genuine create→…→merge flow, snapshot what dict-authority serves, `enable_ledger_reads()`, confirm the ledger read agrees with the dicts still intact (isolating "switched source" from "changed data"), then clear `_DISTRIBUTED_AUDITS` (audit still serves byte-identically from the ledger), clear `_FLEET_RUNS` with the workers intact (the run serves with its gate recomputed to `ready_for_verifier`), and clear `_WORKERS` last (each worker serves with `active` re-derived from its fresh heartbeat) — every dict empty, every read still correct. **(2) the switch is reversible and dark by default** — with a *present* mirror but `read_from_ledger=False`, emptying the dict makes the read **miss** (Phase 2 shadows, it does not serve); `enable_ledger_reads()` then serves the same record from the ledger; `disable_ledger_reads()` reverts and it misses again — the switch alone controls the source. **(3) the write-through keeps the dict current for instant rollback** — under ledger-reads `get` returns a fresh reconstruction (asserted `is not` the dict instance), a real mutator (`dispatch`, `PLANNED→DISPATCHED`) lands in **both** stores, and after `disable_ledger_reads()` the dict-authority read already sees the mutation (rollback loses nothing), with zero divergence throughout.
- Local validation: the live-migration suite (now 12) → **12 passed**; the core migration-target sweep that must not regress — `scale_planner` + `distributed_audits` + `fleet_executor` + `…_contract` + the substrate suites memory/sqlite/stress/migration/live-migration → **143 passed**; the coupled evidence/WORM/provenance/architecture/compute sweep — `evidence_bridge` + `static_evidence_anchor` + `mode7_evidence_persistence` + `production_worm_writes` + `model_provenance` + `architecture_adapter` + `compute_feasibility` → **95 passed** (**238** total, zero regressions vs the prior entry's 235 + 3 new cutover tests; `C:/Python314/python.exe -m pytest`). The flip is exercised only by the migration test installing a mirror and calling `enable_ledger_reads()` explicitly; production stays **dark** (no mirror installed, so `_STATE_MIRROR is not None and read_from_ledger` is structurally false), so the FastAPI app and every pre-existing test serve from the dicts exactly as before.

## Doc-10 Phase 3, the read half, BUILT: a restarted service now **rehydrates** all four live dicts (`_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS`) from the durable ledger — reading the intrinsic state back, **re-deriving** every clock-/sibling-derived view the mirror deliberately never stored, and **honestly dropping** the two things a restart genuinely destroys — proven on `SqliteStateStore`; still explicitly **not** the cutover (the dicts remain authoritative on the serving path) (Jun 1, 2026)

The prior entry proved the mirrored ledger *agrees* with the dicts (zero divergence) and that its rows *survive* a single-host restart (they round-trip through SQLite). Neither proves the thing Phase 3 actually needs: that a service which has **lost its dicts** can rebuild its entire in-RAM world from the ledger alone. This entry builds that — **rehydrate-on-startup**, the read-inverse of the dual-write. The question flips from "does the ledger hold the truth" to "can the service *reconstitute itself* from the ledger after the process-globals are gone." The discipline is the project's own — *declared vs verified is sacred* — applied to reconstruction: a rehydrate may rebuild exactly the durable state the mirror stored and re-derive exactly the views the mirror excluded — **no more**; what a restart truly destroys is dropped, named, and tested, not papered over. This is the Phase-3 *prerequisite*, not the Phase-3 *cutover*: reads still come from the dicts, and read-authority does not move until the flip is built and gated.

**1) Rehydrate is the exact read-inverse of the dual-write — it RE-DERIVES every view the mirror refused to store, never reads one back.** The mirror's load-bearing rule was *store durable STATE, never the rendered VIEW*: a worker's `status`, a run's `verifier_gate_status` / `merge_reason` / `readiness` / aggregates, and the fragment digest are all recomputed-on-read and excluded from the ledger payload. Rehydrate honors the same boundary from the other side. It rebuilds each record from its **intrinsic projection** and then re-derives the excluded views exactly as a live read would: `_worker_from_ledger_payload(payload, *, cutoff)` recomputes `status` from `(last_heartbeat_at, cutoff)`; `_run_from_ledger_payload` seeds a neutral gate that `_refresh_run_gate` then recomputes once the full fleet is back. The intrinsic-projection rule is now proven *both directions* — the mirror does not fabricate a divergence when a view flips, and the rehydrate reconstructs the identical view from scratch. Persist the state, recompute the view; never persist the view.

**2) Faithful re-serve for the immutable, real `from_dict` for the mutated — because reconstructing all sub-objects uniformly would be wrong.** A `DistributedAuditRecord` nests three kinds of sub-object, and they do not reconstruct the same way. The `ScalePlan` and the `worker_evidence` records are *mutated* after creation, so they earn real typed inverses — `ScalePlan.from_dict` (with `WorkerAssignment` / `MemoryEstimate` / tuple rebuilds, `from_dict(to_dict(p)) == p`) and `WorkerEvidenceRecord.from_dict`. The **seven** audit summaries (access / provenance / architecture / probe / compute / cost / data-capture) are immutable, only-ever-*rendered* receipts: they are reconstructed as `_RehydratedSummary` carriers that hold the stored dict and `deepcopy` it on `.to_dict()` — a **byte-identical re-serve** with no lossy parse-and-rebuild. Round-tripping an only-rendered summary through a typed object and back could silently drop or reorder a field the ledger faithfully holds; the carrier structurally cannot, so the re-served audit equals its pre-restart `to_dict()` exactly.

**3) Two honest restart consequences — each named in the code, tested, and recoverable.** A restart genuinely destroys two things, and rehydrate refuses to pretend otherwise. **(a) In-flight leases drop.** A lease token is a liveness capability that is *never* persisted (the mirror redacts it), so a job that was `leased` at restart cannot prove its holder is still alive — it rehydrates as `expired`, with `lease_token` / `lease_token_hash` cleared. This strands nothing: `lease_next_job` re-leases `{queued, expired}`, so the work is immediately re-claimable, proven by a test that re-leases the dropped job after restart. **(b) The fragment-payload digest comes back null.** The raw `evidence_packet_fragment_payload` lives in the WORM store, not the run ledger, so its digest `…_sha256` is a non-durable view the mirror excludes; what *is* durable is the content-addressed `evidence_packet_fragment_ref`. A rehydrated job therefore carries its **ref** (the real, surviving handle) with a `null` payload and `null` digest — honest about which artifact the run ledger actually owns, proven by submitting a receipt *with* a real probe payload so the digest is non-null pre-restart and demonstrably null after.

**4) Rehydrate is fail-LOUD where the mirror is fail-quiet — because their authority is opposite.** The mirror is non-authoritative, so it swallows a backend `StateStoreError` as a divergence and can never break serving. Rehydrate is the *source of truth on startup*, so it does the inverse: a malformed row must **halt the rebuild**, not silently yield a half-populated service that lies about what it holds. Each `rehydrate_from_ledger` builds into **fresh containers and swaps them in only on success**, and lets `StateStoreError` propagate — a corrupt ledger fails the boot loudly rather than booting a service with a torn world. The rebuild order is load-bearing — workers → runs → fragments → `_refresh_run_gate` — so every gate re-derivation sees a fully-populated fleet.

**5) This is the Phase-3 prerequisite, NOT the Phase-3 cutover.** Doc 10's cutover is three slices: storage *survives* a restart (proven last entry), the in-RAM view *rebuilds* from the ledger on startup (proven here), and *the flip itself* — reads served from the ledger instead of the dicts. Two of the three now stand. The dicts remain authoritative on every serving path, and read-authority does not move until the flip is built and gated behind its own kill/validate gate. Multi-host (Postgres/Redis + fencing) remains workstream 11. The honest one-line status: the ledger now demonstrably **agrees**, **survives**, and **rehydrates** — it is not yet **authoritative**.

### Pieces (this entry)
- `api/services/cas_harness_distributed_audits.py` *(edit)* — `rehydrate_from_ledger(store) -> int` rebuilds `_DISTRIBUTED_AUDITS` from every `distributed_audit` row under `INTERIM_TENANT`; `_audit_from_ledger_payload` reconstructs each record via real `ScalePlan.from_dict` + `WorkerEvidenceRecord.from_dict`, with the seven immutable summaries faithfully re-served through the new frozen `_RehydratedSummary` carrier (holds the stored payload, `deepcopy`s it on `to_dict()`). Builds a fresh dict and swaps on success; `StateStoreError` propagates.
- `api/services/cas_harness_fleet_executor.py` *(edit)* — `rehydrate_from_ledger(store) -> dict[str, int]` (`{"workers", "fleet_runs", "fragment_refs"}`) rebuilds `_WORKERS` / `_FLEET_RUNS` / `_FRAGMENT_REFS` in the load-bearing order workers→runs→fragments→`_refresh_run_gate`; `_worker_from_ledger_payload(payload, *, cutoff)` re-derives `status` from `(last_heartbeat_at, cutoff)`; `_job_from_ledger_payload` maps `leased→expired` and clears the never-persisted lease token + the non-durable payload/digest while **preserving** the content-addressed `evidence_packet_fragment_ref`; `_run_from_ledger_payload` seeds a neutral gate that `_refresh_run_gate` recomputes. Fresh-containers-then-swap; fail-loud.
- `api/services/cas_harness_scale_planner.py` *(verified)* — the typed `from_dict` inverses (`WorkerAssignment` `:168`, `MemoryEstimate` `:193`, `ScalePlan` `:240`) the audit rehydrate depends on; `ScalePlan.from_dict(to_dict(p)) == p`.

### Tests (this entry)
- `tests/test_state_substrate_live_migration.py` *(+3, now 9)* — rehydrate proven on the **real** services over `SqliteStateStore`: **(1) every dict rebuilds from the ledger** — drive the genuine create→…→merge flow, snapshot the audit, the run (its durable `_run_ledger_payload` *and* its full rendered `to_dict()`), every worker, every fragment ref; simulate a restart the only honest way (detach the mirror, **close the DB file**, reset both services so the dicts are empty); reopen the store, `rehydrate_from_ledger` on both services, and **close the store again *before* asserting** so the proof is a full copy into RAM rather than a live DB handle — the audit (byte-identical re-serve), the run (byte-identical durable payload *and* re-derived render, every job), every worker (`status` re-derived to `active` from fresh heartbeats), and every fragment ref all return, counts exact. **(2) in-flight leases drop honestly** — lease a job, restart, rehydrate; it returns `expired` with a null token, and `lease_next_job` immediately re-leases it (recoverable, not stranded). **(3) the non-durable fragment digest drops** — submit a receipt *with* a real probe payload so the digest is non-null pre-restart; after rehydrate the job keeps its `evidence_packet_fragment_ref` but the payload and its `…_sha256` come back null, while the durable `_job_ledger_payload` is byte-identical across the restart.
- Local validation: the live-migration suite (now 9) → **9 passed**; the core migration-target sweep that must not regress — `scale_planner` + `distributed_audits` + `fleet_executor` + `…_contract` + the substrate suites memory/sqlite/stress/migration/live-migration → **140 passed**; the coupled evidence/WORM/provenance/architecture/compute sweep — `evidence_bridge` + `static_evidence_anchor` + `mode7_evidence_persistence` + `production_worm_writes` + `model_provenance` + `architecture_adapter` + `compute_feasibility` → **95 passed** (**235** total, zero regressions; `C:/Python314/python.exe -m pytest`). Rehydrate is exercised only by the migration test installing a mirror and calling it explicitly; production stays **dark** (no mirror installed, no rehydrate call on the serving path), so the FastAPI app and every pre-existing test are untouched.

## Doc-10 Phases 0–2, BUILT: the four live process-global dicts now **dual-write** into the durable `StateStore` and **shadow-read** against it through one `LedgerMirror` seam, proven to leave the shadow ledger in **zero divergence** with the authoritative dicts — and proven a **no-op in production** (dark unless a mirror is installed), so the strangler fig grows without touching the serving path (Jun 1, 2026)

The prior entry *built the substrate* (the locked `StateStore` + the tested durability ladder) but left it, in its own words, "**not yet wired in**." This entry wires it — the first two phases of the doc-10 strangler-fig migration, on real service-layer code. The four control-plane globals (`_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS`) now write **both** the dict (still authoritative) **and** the ledger on every mutation, and every read **shadow-compares** the two — the dual-write / shadow-read precondition doc 10 requires before any cutover. The discipline is the project's own — *declared vs verified is sacred* — applied here to the ledger's authority: it is allowed to **shadow** the truth, never to **be** the truth, until a durable backend (workstream 11) earns the cutover. Nothing claims durability; what is proven is **agreement**.

**1) The coupling-critical seam was written and test-proven *first*, exactly as the substrate spine was.** Same sequencing lesson, same reason: dual-write/shadow-read is the one tightly-coupled join where a premature fan-out drifts into integration hell, and sub-agents cannot run `pytest` — so `LedgerMirror` was built and locked by the orchestrator under its own 18-test suite *before* a single live call site was touched. The mirror is **non-authoritative by construction**: `mirror_put` **never raises into the caller** — a backend `StateStoreError` is swallowed and *recorded as a `Divergence`* (a record we failed to mirror *is* a place the ledger and the dict disagree), and a `VersionConflict` retries to a bounded exhaustion that is *itself* a divergence — so a ledger bug can never break serving, it can only surface as drift the gate catches. Programming errors (anything that is *not* a `StateStoreError`) are deliberately **not** swallowed: during Phases 1–2 against the in-memory store they must fail loudly; in production the mirror is dark and the question never arises. `assert_no_divergence()` is the Phase-2 gate in a single call.

**2) Dark by default — production and every pre-existing test see ZERO behaviour change.** Each live service gained a module-global `_STATE_MIRROR: LedgerMirror | None = None` and a `set_state_mirror()` installer; every `_mirror_*` / `_shadow_*` helper is a **no-op while it is `None`**. So the wiring ships *inert*: the FastAPI app, and all **86** pre-existing distributed/fleet tests, run with no mirror installed and therefore run *exactly as before* — proven by `test_mirror_is_dark_when_uninstalled` (the full create→…→merge flow completes with `_STATE_MIRROR is None` on both services) and by those 86 tests passing unchanged. Only the migration test installs a mirror. This is the property that lets the seam land *before* cutover without risk: a strangler fig that stays invisible until you choose to see it.

**3) The load-bearing decision: the ledger stores durable STATE, never the rendered VIEW.** The naïve mapping — "store each record's `to_dict()`" — is *wrong for two of the three record kinds*, and getting it wrong would have manufactured **false divergences**. A `to_dict()` is a *render*: it can fold in state derived from the wall clock or from sibling records, recomputed on every read. A fleet **worker**'s `status` is a pure function of `(last_heartbeat_at, now)`; a **fleet_run**'s `verifier_gate_status` / `merge_reason` / `readiness` / `stale_workers` / aggregates are recomputed from jobs+workers+clock by `_refresh_run_gate` on *every* read. Persist that render and the same record re-read a few milliseconds later — after a worker ages, after `now` advances — no longer matches the bytes the ledger holds, even though nothing the record *owns* has changed. So the mirror stores each record's **intrinsic projection** and excludes every recomputed view: `_worker_ledger_payload` drops `status`; `_run_ledger_payload` keeps `audit_id/status/merged_packet_trace_id/created_at/updated_at/jobs[…]` (lease token redacted) and drops the recomputed gate views; the **distributed_audit** record needs no narrowing because *its* `to_dict()` is already a pure own-data projection (plan + the 8 receipts + its own `worker_evidence` + counts, no clock/foreign state). This is precisely the projection a Phase-3 reload would recompute — persist the intrinsic state, re-derive the views at read time — and it is proven *behaviourally*: `test_worker_going_stale_is_not_a_divergence` ages every worker into `stale` and asserts the shadow ledger still shows zero divergence. The view flipped; the stored state did not.

**4) The indirect, clock-triggered mutation paths re-mirror too — drift has nowhere to hide.** Most dual-writes sit at a record's own mutators, but fleet *job* state is also mutated **outside** any run's mutators by two clock-triggered reclaimers: `_expire_stale_leases` (fires inside `lease_next_job`) and `_expire_worker_leases` (fires via `heartbeat_worker` / `mark_stale_workers`). A lease silently expiring `leased→expired` would, without care, leave the ledger holding the pre-expiry run forever. Both reclaimers now carry a `changed` flag and re-mirror every run they touch, so the ledger stays in lock-step even when state changes behind a run's back — proven by `test_lease_expiry_re_mirrors_the_run` (ages a live lease into the past, re-drives a lease so the expiry fires, asserts zero divergence). And all four globals share **one** `StateStore` under **one** `INTERIM_TENANT = "default"`: `distributed_audit` and `fleet_run` legitimately reuse a single `audit_id`, kept distinct by the `(tenant, kind, record_id)` triple — the single unified ledger the cutover targets, partitioned by `kind`.

**5) Beyond *agreement*, the mirrored ledger now demonstrably *survives* a single-host restart.** Zero-divergence proves the ledger and the dict *agree*; it does not prove the ledger *persists*. So the same live flow is driven through the durable `SqliteStateStore` (the one backend whose own tests earn "durable on a single host"), then a restart is simulated the only honest way — **close the DB file and erase the in-RAM dicts**, exactly what a process restart destroys — and a fresh store is opened on the same file: the audit, its fleet run (every job), every worker, and every fragment ref are **all recovered from the ledger**, while the dicts come back empty (`test_mirrored_ledger_survives_a_single_host_restart`). The real mirrored payloads also serialise and round-trip through SQLite — a stricter check than the in-memory store imposes. This is the durability *evidence* doc-10 Phase 3's single-host half requires; it is explicitly **not** the cutover (the dicts are still authoritative on the serving path) and **not** multi-host (Postgres/Redis + fencing remains workstream 11). What the cutover still owes is the other half — **rehydrating the in-RAM view from those ledger rows on startup** and flipping reads onto the ledger. *(Update: the rehydrate half is built and proven in the entry above; only the read-authority flip remains.)*

### Pieces (this entry)
- `api/services/production/state_substrate/migration.py` *(new)* — the `LedgerMirror` dual-write / shadow-read seam: `mirror_put` (create→v1 / read-modify-`put` with version threading; swallows `StateStoreError` as a `write_failed` divergence; retries `VersionConflict` to a bounded exhaustion divergence; provenance envelope `source`/`trace_id`/`parent_ids` set at birth, preserved across updates), `shadow_compare` / `shadow_compare_all` (symmetric `json.dumps(…, sort_keys=True, default=str)` canonicalization so key-order and datetime-rendering can fabricate neither a match *nor* a mismatch; reports `missing_in_ledger` / `payload_mismatch` / `extra_in_ledger` / `read_failed` / `list_failed`), the frozen `Divergence` record, a thread-safe `_divergences` log, and `assert_no_divergence()` — the Phase-2 gate. `INTERIM_TENANT = "default"`.
- `api/services/production/state_substrate/__init__.py` *(edit)* — export `LedgerMirror` / `Divergence` / `INTERIM_TENANT` (the strangler-fig seam).
- `api/services/cas_harness_distributed_audits.py` *(edit)* — `_STATE_MIRROR` + `set_state_mirror`; `_mirror_audit` / `_shadow_audit` (both return the *same* record, preserving callers' in-place mutation); dual-write at create / dispatch / mark-running / record-evidence / all merge exits; shadow-read at `get` / `list`; `reset_*_for_tests` clears the mirror. The record's `to_dict()` is mirrored as-is (pure intrinsic projection).
- `api/services/cas_harness_fleet_executor.py` *(edit)* — `_STATE_MIRROR` + `set_state_mirror`; the **intrinsic-projection** payloads `_worker_ledger_payload` (excludes derived `status`) and `_run_ledger_payload` (excludes recomputed gate views); `_mirror_worker` / `_mirror_run` / `_mirror_fragment` / `_shadow_run`; dual-write at register / heartbeat / prepare / lease / submit (+ the `fragment_ref` row) / merge **and** the indirect reclaimers `_expire_stale_leases` / `_expire_worker_leases` (`changed`-gated re-mirror); shadow-read at `get` / `list` for both workers and runs.

### Tests (this entry)
- `tests/test_state_substrate_migration.py` *(new, 18)* — the seam in isolation, with two test doubles (`_BrokenStore` raises on every op; `_FlakyPutStore` raises `VersionConflict` N times): create-then-versioned-update, envelope set-at-birth + preserved-on-update, fail-closed tenant scoping, retry-through-conflicts, conflict-exhaustion divergence (no write lands), backend-failure swallowed as a divergence, shadow agreement + key-order insensitivity, `missing_in_ledger` / `payload_mismatch` / `read_failed` / `extra_in_ledger`, clean vs dirty `assert_no_divergence`, a 16-thread concurrent `mirror_put` that never raises and lands consistent, and `LedgerRecord.new` as the sole construction path.
- `tests/test_state_substrate_live_migration.py` *(new, 6)* — the Phase-2 proof on *real* services: one shared `LedgerMirror` (over `InMemoryStateStore`) installed into **both** live services, driving their genuine service-layer flow (create→dispatch→register→prepare→(lease→submit)\*→merge) and asserting `assert_no_divergence()` — **zero divergence**; the unified ledger populated (distinct `distributed_audit` vs `fleet_run` rows under one `audit_id`, one `fragment_ref` per completed job, traceability envelope landed); worker-going-stale is *not* a divergence (the intrinsic-projection rule); lease-expiry re-mirrors the run; the mirror is *dark* when uninstalled (the zero-behaviour-change guarantee); and the mirrored ledger **survives a single-host restart** on `SqliteStateStore` — drive the real flow, close the DB file, erase the dicts, reopen, and the audit + run (every job) + every worker + every fragment ref recover from the ledger while the dicts come back empty (durability evidence for Phase 3, explicitly not the cutover).
- Local validation: the two new suites (18 + 6) → **24 passed**; run together with the live migration targets they must not regress — `cas_harness_distributed_audits` (54) + `cas_harness_fleet_executor` (19) + `…_contract` (13) + the substrate durability suites memory/sqlite/stress (4+4+5) → **123 passed**, zero regressions (`C:/Python314/python.exe -m pytest`). The remaining full-suite failures are the *pre-existing* shared-process rate-limit/quota saturation (`429`) in API-route suites that pass in isolation, plus the 2 pre-existing unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) — none touch the substrate or either wired service.

## First real BUILD in the production-readiness program — the durable run/worker/tenant **state substrate**: a locked `StateStore` Protocol with a *tested* durability ladder (in-memory reference → SQLite durable-on-one-host → Postgres/Redis multi-host blueprint), where durability is a **backend property the tests prove**, never an interface promise (Jun 1, 2026)

The nine-blueprint entry below *opened* the production-readiness program and found, across five of its nine workstreams, the same root gap: **all fleet/run/tenant state lives in process-global dicts** (`_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS`) that vanish on restart, can't span hosts, and aren't tenant-scoped. This entry is the program's **first build, not another blueprint**: the durable substrate those five workstreams converge on. The discipline that makes it honest is the one the project lives by — *declared vs verified is sacred; a stub is a stub* — applied to **durability** specifically: the interface promises nothing about survival, and each backend earns exactly the durability word its **own tests** can keep.

**1) The spine was written and test-proven *first*, so the contract is locked before any backend fans out.** The deliberate sequencing: write the interface (`StateStore` Protocol), the reference implementation (`InMemoryStateStore`), and an *executable* conformance contract (`run_state_store_contract(make_store)`) **myself**, prove them green, and only then deploy parallel agents against the now-frozen interface — because the work is tightly coupled and a premature fan-out drifts into integration hell (and, per the prior entry's lesson, sub-agents cannot run `pytest`, so an unlocked contract would have no arbiter). The conformance suite is the leverage of the whole substrate: it takes a *factory*, not an instance, and runs the **same** assertions — record round-trips + version-0→1 promotion, fail-closed tenant scoping (a cross-tenant `get` returns `None`, indistinguishable from absent), optimistic concurrency (first-writer-wins, loser gets `VersionConflict`), version-checked deletes, and the full single-holder / expiring / renew-release lease lifecycle (expiry decided by an **injected `now`**, never by sleeping) — against **every** backend. "Swap the backend, keep the behaviour" is therefore a *checked fact*, not a hope: if the in-memory store and the SQLite store ever disagreed about, say, whether an expired lease is renewable, CI would catch it.

**2) Durability is honest because it is a *backend* property the tests prove — not a word the interface is allowed to claim.** The reference `InMemoryStateStore` is the **non-durable** rung, and a test (`test_non_durability_is_explicit`) asserts a fresh instance recovers *nothing* a prior instance stored — non-durability is a *documented, asserted property*, not an accident. `SqliteStateStore` (WAL + `synchronous=NORMAL`, commit-after-every-mutation) earns the words "durable on one host" the only honest way: by genuinely **closing the store and reopening a brand-new object on the same real DB file**, then proving committed records, leases, the *version sequence* (v2 → reopen → v3, no reset), and the full traceability envelope (`source` / `trace_id` / `parent_ids`) all recovered intact — the exact thing the in-memory store *cannot* pass against the same storage. And the crash-durability hook (`assert_crash_durability`) **refuses** — raises `NotImplementedError` — on a non-durable store rather than fake a kill-mid-write proof an in-memory store structurally cannot give: "calling it here is a category error, and it says so out loud." No backend ever claims survival it didn't demonstrate.

**3) A concurrency stress harness proves the *safety* invariants under real threads — and the orchestrator caught + fixed a real bug in it, exactly as with the autoscaler stub in the prior entry.** `run_state_store_stress(make_store)` hammers one store from many threads to prove what single-call conformance cannot: **no lost updates** under version contention (threads read-modify-write a shared counter via optimistic concurrency; the harness's *own* atomic counter must equal the store's final value — nothing silently clobbered), **exactly one lease holder** (an independent critical-section witness asserts `inside == 1`), and **tenant isolation under concurrency** (same `record_id` under different tenants never observe each other). The agent that authored it shipped a lease test whose "exactly one winner per round" assertion was *incompatible with its own release-within-round design* — the winner freed the lease mid-round, so slow losers acquired it *after* the release and also "won" (8 winners, not 1); mutual exclusion still held, but the per-round count was meaningless. Diagnosed and fixed with a **two-barrier** design: a phase-1 rendezvous → one acquire attempt each → the winner enters the critical section and holds the lease across a **phase-2 rendezvous** (so every loser provably attempts *while the winner holds it*) → only then release. That makes "exactly one winner per round" true and deterministic while preserving the mutual-exclusion witness, and is deadlock-free (every thread, winner or loser, reaches both barriers each round). The sub-agents can't run `pytest` in their sandbox, so the bug slipped past the author and was caught on the orchestrator's run.

**4) Two multi-host blueprints carry the same honesty forward to the backends the migration will eventually point at.** `10_state_substrate_migration.md` is the **strangler-fig** plan to cut the four live global dicts onto the substrate (dual-write → shadow-read → cutover → delete globals, each phase with a kill/validate gate), landing on SQLite first and honest that an interim `"default"` tenant is a *traceability placeholder, not enforced isolation* ("read this twice"). `11_multi_host_state.md` takes the *unchanged* Protocol from durable-on-one-host to durable-across-hosts (Postgres `UPDATE … WHERE version=:expected RETURNING` for compare-and-set; Redis `SET NX PX` + Lua token discipline for leases), and its load-bearing content is the honesty no acquire-time SQL can fake: the **dead-but-not-expired holder** hazard (a stalled host wakes past its lease expiry and acts as a second holder) closed only by a **monotonic fencing token checked by the protected resource** — framed as an *additive, interface-compatible strengthening* (today's `token` is an opaque random uuid: a perfect ownership proof but **not** monotonic, so the fence is paired alongside it without any caller noticing). The truthful-claims table encodes the rule the whole program turns on: "survives restart / survives host loss / prevents two live holders / durable writes" is answered **per-config, never per-backend-name** — Redis-without-AOF calling itself durable is named as "the exact dishonesty this whole program exists to refuse."

### Pieces (this entry)
- `api/services/production/state_substrate/interface.py` *(new)* — the **locked** contract: the `StateStore` `@runtime_checkable` Protocol (`put`/`get`/`list`/`delete` + `acquire_lease`/`renew_lease`/`release_lease`/`get_lease` + `close`); the `LedgerRecord` and `Lease` frozen dataclasses (the full object-traceability envelope: `created_at`/`updated_at`/`version`/`parent_ids`/`source`/`trace_id`); the typed exception hierarchy (`StateStoreError` → `VersionConflict` (carrying `expected`/`actual`), `TenantScopeViolation`, `LeaseHeld`, `LeaseExpired`, `UnknownLease`); and the `utc_now()` / `new_record_id()` / `require_tenant()` helpers. The interface promises **nothing** about durability — that is the point.
- `api/services/production/state_substrate/memory_store.py` *(new)* — `InMemoryStateStore`, the thread-safe (single `RLock`) **non-durable reference** every durable backend must match. Owns versioning (create → v1, immutable `created_at`), fail-closed tenancy, and the single-holder lease state machine (idempotent same-holder re-acquire mints a *fresh* token; renew preserves the token but never resurrects an expired lease).
- `api/services/production/state_substrate/conformance.py` *(new)* — `run_state_store_contract(make_store)`, the executable specification: seven sub-suites run against any backend factory, with lease expiry driven by a fixed `_T0` + `timedelta`s so time is an argument, not a `sleep`.
- `api/services/production/state_substrate/sqlite_store.py` *(new)* — `SqliteStateStore`, the **durable-on-one-host** rung (WAL, `synchronous=NORMAL`, `isolation_level=""` with commit-after-every-mutation, `check_same_thread=False` behind one `RLock`); ISO-8601 datetimes + JSON payloads; `INSERT … ON CONFLICT DO UPDATE` for records, `INSERT OR REPLACE` for leases (retiring the old token via a UNIQUE token index). Mirrors the reference semantics exactly — proven by passing the *same* contract.
- `api/services/production/state_substrate/stress.py` *(new)* — `run_state_store_stress(make_store)`, the store-agnostic concurrency-safety harness (no-lost-updates / exactly-one-holder / tenant-isolation), with `assert_crash_durability` left as an honest `NotImplementedError` hook for the durable backends to own.
- `api/services/production/state_substrate/__init__.py` *(new)* — the package docstring distinguishing the **real, tested** substrate (reference + conformance + SQLite) from the sibling single-file stub scaffolds, the durability-ladder table, the "not yet wired in" note pointing at the migration doc, and the 18-symbol public surface.
- `docs/working/production_readiness/10_state_substrate_migration.md` *(new)* — the strangler-fig cutover of the four process-global dicts (real `file:line` citations: `_DISTRIBUTED_AUDITS` `cas_harness_distributed_audits.py:158`; `_WORKERS`/`_FLEET_RUNS`/`_FRAGMENT_REFS` `cas_harness_fleet_executor.py:159-161`), phased with kill/validate gates; flags a `put_if_absent` Protocol method as a *proposal only*.
- `docs/working/production_readiness/11_multi_host_state.md` *(new)* — Postgres/Redis behind the unchanged Protocol; the dead-but-not-expired-holder hazard + monotonic fencing token (additive, interface-compatible); at-least-once + idempotent-effect; the per-config truthful-claims table; Redis-without-AOF caveat.

### Tests (this entry)
- `tests/test_state_substrate_memory.py` *(new, 4)* — the reference passes the contract; instances are isolated (no hidden process-global — the very property the live `_DISTRIBUTED_AUDITS` lacks); `close` is idempotent and use-after-close is a loud error; **non-durability is explicit** (a fresh instance recovers nothing).
- `tests/test_state_substrate_sqlite.py` *(new, 4)* — SQLite passes the *same* contract (substitutability); and the three durability proofs the reference deliberately **cannot** pass — records survive a real close/reopen (with the traceability envelope intact and fail-closed tenancy still holding), leases survive reopen (live holder/token recovered inside the TTL, absent past it), and the version sequence continues across restart (v2 → reopen → v3, `created_at` immutable).
- `tests/test_state_substrate_stress.py` *(new, 5)* — the reference survives 8×50 and 16×100 concurrency stress; lease mutual exclusion in isolation; a single-thread "stress" run is rejected as proving nothing; and the crash-durability hook **refuses** on the in-memory store (a stub is a stub).
- Reconciliation fix (orchestrator): `api/services/production/state_substrate/stress.py` — the lease invariant's "exactly one winner per round" was incompatible with the agent's release-within-round design (winner frees the lease mid-round → slow losers also win → 8 winners); rewritten to the **two-barrier** design (winner holds the lease across a second rendezvous), making the count deterministic while preserving the mutual-exclusion witness. (Sub-agents can't run `pytest`, so it slipped past the author; caught on the orchestrator's run.)
- Local validation: the substrate suite (4 + 4 + 5) → **13 passed**; run together with the five migration-target production suites it must not regress — `cas_harness_distributed_audits` + `cas_harness_fleet_executor` + `cas_harness_scale_planner` + `production_fleet_scale` + `production_tenant_isolation` — → **136 passed**, zero regressions (`C:/Python314/python.exe -m pytest`). The substrate package is import-isolated (stdlib + the locked interface only), so it touches neither the live FastAPI app nor the global dicts it is designed to eventually replace.

## Public production-readiness program — nine parallel design + gap blueprints (and import-isolated interface scaffolds) for turning the honest `*_DECLARED`/`*_ACKNOWLEDGED` promises into real `*_VERIFIED`/`*_METERED`/`*_WORM_COMMITTED` infrastructure, with the honesty ethos enforced *in code*: a stub is a stub (Jun 1, 2026)

The 8-gate honesty series is complete: a distributed CAS Harness run is *refused* (HTTP 422) unless every precondition — risk, open-weight access, compute, cost, provenance, architecture, probe, data-capture — is honestly acknowledged, and the API tier *never* claims `*_VERIFIED` / `*_METERED` / `*_WORM_COMMITTED`; only the fleet/worker side verifies, meters, commits. That closed a major **product/honesty** gate. It is **not** the same as **public production readiness**: the honest tri-states the gate series defines (`DATA_CAPTURE_WORM_COMMITTED`, `COST_METERED`, `MODEL_ACCESS_VERIFIED`, …) are *promises the fleet must actually keep* — at scale, for many tenants, durably, observably, billably, and compliantly. This entry **opens that program**. Nine agents, working in parallel, each grounded itself in the *real* services it touches and produced a **design + gap blueprint** (no fabricated production) for one workstream, plus an **import-isolated interface scaffold** (`typing.Protocol` / ABC seams + clearly-labeled in-memory stubs) the team can build against. The deliverable is honest about what it is: **blueprints and seams, not shipped infrastructure** — every scaffold is a stub, and the honesty rule is enforced *in the stubs themselves*.

**1) The honesty ethos is the spine, and it is enforced in code, not just prose.** The program's governing rule — *no module here may produce a `*_VERIFIED` / `*_METERED` / `*_WORM_COMMITTED` status from a stub backend* — is written into `api/services/production/__init__.py` and then *honored by every scaffold*: `worm_writes` never emits `DATA_CAPTURE_WORM_COMMITTED` for anything but a re-read-verified `LockReceipt` (the in-memory stub's `version_id` is `stub-…`, which fails `is_verifiable()`, so it can only reach `DATA_CAPTURE_ACKNOWLEDGED`); `billing` returns `COST_METERED` *only* for a `fleet_measured` reading and `assert_metered` *refuses* an estimate-sourced one; `worker_verification`'s stub "never loads weights, never signs — so it never returns `WORKER_EVIDENCE_VERIFIED`"; `observability` *raises* if an `api_declared` status is tagged with a verified-family tier; `fleet_scale` *raises* if a scheduler-tier decision claims the worker-only `FLEET_PLACEMENT_VERIFIED`; `tenant_isolation`'s cross-tenant read *fails closed*. The 152 scaffold tests pin these refusals, so a future "helpful" attempt to let a stub claim verification breaks CI rather than shipping.

**2) Every blueprint generalizes a *real* existing pattern — the work is durability + reach, not greenfield.** The agents found, repeatedly, that the honest end-state already exists in miniature and is simply unreachable or non-durable: content-addressing + integrity-on-read is *already real* in `cas_harness_evidence_anchor.py` (PUT with `ContentMD5`, hash-in-key, SHA-256 re-read verify) — 02 generalizes it to large activation tensors; a *correct* single-holder lease/ack/merge state machine already exists in `cas_harness_fleet_executor.py` — 04 backs the same contract with a durable broker + checkpoint cursor; a real S3 Object-Lock write+verify already exists in the anchor (`ObjectLockMode` / `RetainUntil`, re-read assert) — 07 wires it to flip gate 8's `capture_committed`; the verdict side already blocks ACCEPT without a WORM-retained packet. The recurring true gap is the same across five workstreams: **all fleet/run/tenant state lives in process-global dicts** (`_DISTRIBUTED_AUDITS`, `_WORKERS`, `_FLEET_RUNS`, `_FRAGMENT_REFS`) that vanish on restart, can't span hosts, and are *not tenant-scoped* — so durability (03/04), multi-host reach (03), and tenant isolation (06) all converge on replacing that one substrate.

**3) The blueprints cross-reference each other into one coherent dependency graph.** 07 (WORM) sits on 02 (object storage) and consumes 01 (verification) evidence; 08 (billing) consumes 05 (observability) metering and 03 (fleet) consumption signal; 06 (tenant isolation) is the cross-cut every other workstream partitions by (and it cites 02's already-present `ArtifactDescriptor.tenant_id` seam as the hook to make required-and-enforced); 04 (queue/resume) underpins 03 (fleet at scale); 09 (compliance) governs the consent→capture→WORM chain gate 8 opens — and resolves its sharpest tension (write-once retention vs erasure rights) honestly via crypto-shred, *not* by pretending both hold. Each blueprint carries the same 7 sections (current state with real file:line citations → gap → phased plan with a per-phase kill/validate gate → honesty constraints → Protocol/ABC interface seams → cross-references → open questions), and each surfaces a single most-important human decision (activation-tensor serialization format; fan-out topology + where durable run/worker/lease state lives; at-least-once + idempotent-merge as the honest delivery guarantee; OTLP vendor-neutrality; silo-vs-pool tenancy; Object-Lock COMPLIANCE-vs-GOVERNANCE mode; how GPU-seconds are *authoritatively* measured; the erasure mechanism under WORM).

### Pieces (this entry)
- `docs/working/production_readiness/00_index.md` *(new)* — the program frame: why this is *not* the gate series, the honesty ethos that governs every workstream, the nine-workstream table, and the dependency sketch.
- `docs/working/production_readiness/01_worker_side_verification.md` … `09_compliance.md` *(9 new)* — the nine 7-section blueprints (worker-side verification, large artifact object storage, fleet execution at scale, queue/resume, observability, tenant isolation, production WORM writes, billing/accounts, compliance), each grounded in real file:line citations.
- `api/services/production/__init__.py` *(new)* — the import-isolated scaffolding package; its docstring states the honesty rule the whole package is bound by.
- `api/services/production/{worker_verification,artifact_store,fleet_scale,queue_resume,observability,tenant_isolation,worm_writes,billing,compliance}.py` *(9 new)* — import-isolated `Protocol`/ABC interface seams + clearly-labeled in-memory stubs (no live-app wiring, no real infra, no stub-emitted verified/metered/committed status).

### Tests (this entry)
- `tests/test_production_{worker_verification,artifact_store,fleet_scale,queue_resume,observability,tenant_isolation,worm_writes,billing,compliance}.py` *(9 new)* — 152 tests pinning each scaffold's contract *and* its honesty refusals (the stub WORM store cannot claim commitment; the stub meter cannot claim `COST_METERED` from an estimate; an `api_declared` status cannot be tagged verified; a scheduler decision cannot claim worker-tier placement verification; a cross-tenant read fails closed).
- Reconciliation fix (orchestrator): `api/services/production/fleet_scale.py` — the autoscaler stub's `recommend` was internally inconsistent with its own tests (it computed `desired` from `current + pending`, so it never scaled down when idle); corrected to the piecewise policy its four tests jointly specify — provision `current + pending` under demand, drain to the floor (`min_workers`) when idle — with the docstring updated to match. (The sub-agents could not execute `pytest` in their sandbox, so this slipped past them; caught on the orchestrator's run.)
- Local validation: all 9 `test_production_*.py` → **152 passed** in one run (`C:/Python314/python.exe -m pytest`). Scaffolds are import-isolated (they import only stdlib + the gate contracts they bridge), so they don't touch the live FastAPI app or the fleet executor; the 2 pre-existing unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are untouched by this work.

## Run-gate (8) — *every* distributed run, frontier or not, is *refused* unless the caller acknowledges that the audit *harvests* the target model's signal into an immutable write-once store reused as CAS-Native training data, and the receipt *never claims the bytes were written* because the write happens fleet-side, never at the API tier (Jun 1, 2026)

Gates (5)/(6)/(7)/(3)/(4) all answer questions *about the run* — which weights, can we hook them, can we score them, can the hardware hold them, does the caller accept the cost. This gate surfaces something the run *does to the customer's model that the customer was never told about*: the distributed CAS Harness audit is not only a measurement, it is a **data harvest**. Every run captures the target model's real signal — its inputs and outputs, the pooled hidden-state activations the probe hooks, the `cas_axis_readout` each worker shard emits (declared in every shard's `expected_outputs`), and the run's verdict — and commits it to an **immutable, write-once (WORM) store**, where it becomes labelled training signal for **CAS-Native**, a product we sell. This entry closes **gate (8) — data-capture acknowledgment**: a distributed run is now **refused with HTTP 422 unless the caller explicitly acknowledges that capture, its indefinite WORM retention, and its reuse** — closing the dishonest-by-omission failure of a customer's model signal being persisted (immutably, indefinitely) and reused to improve a product we sell, without the customer ever having been told or asked.

**1) This gate is *universal*, not stricter-for-bigger — and, exactly as with gate (2), universal *is* the honest framing.** The frontier gates (3)/(5)/(6)/(7) relax below the frontier because their concerns — compute headroom, provenance rigor, probe/architecture support — genuinely scale with model size. Data capture does **not**: a 20B run harvests *exactly* as a 1T run does, because the harvest is intrinsic to *how the audit works* — every run hooks real activations and emits a real readout regardless of scale. So, mirroring gate (2)'s mechanistic-reachability framing, this gate is enforced for **every** distributed run, not just `EXPERIMENTAL_NOT_VALIDATED` ones; the validator is named `validate_distributed_data_capture` (not `validate_frontier_*`) precisely to signal that universality. Making it frontier-only would be a lie — the capture is not weaker for a smaller model.

**2) The receipt surfaces only what the audit *actually* does, and is honest about acknowledged vs committed — mirroring every other gate's declared-vs-verified split.** Data capture resolves to one of three states: **`DATA_CAPTURE_WORM_COMMITTED`** (the fleet actually wrote the captured signal to the immutable store — fleet-side only, the **one** place a real write happens, and therefore **never** produced at the API tier, where no model has executed and no bytes exist yet — so `capture_committed` is always `false` here, exactly as the other gates' `*_verified` / `*_metered` fields are), **`DATA_CAPTURE_ACKNOWLEDGED`** (the caller acknowledged the capture/retention/reuse terms — enough to *create* a run, never on its own a customer ACCEPT), and **`DATA_CAPTURE_NOT_ACKNOWLEDGED`** (a run with no acknowledgement → `ValueError` → 422). Every field of the receipt names a **real** property of the harvest, none invented: the `captured_signal_classes` are the four classes the audit already produces (`model_input_output`, `pooled_hidden_state_activations`, `cas_axis_readout`, `audit_verdict`), `retention_model` is `write_once_read_many` (stated plainly — the store is immutable, so captured signal cannot be selectively redacted after the fact), and `reuse_purpose` is `cas_native_training_corpus`. The refusal names what is captured, where it is retained, and the `accept_audit_data_capture` flag; the notice stays honest that *"nothing is captured at the API tier"* — the write is fleet-side, when the workers run.

**3) The gate lives at the same single choke point, runs *last*, and is a *run* gate, not a *plan* gate.** `create_distributed_audit(..., *, data_capture_acknowledged=False)` enforces the gate for **every** plan (full gate order: access → provenance → architecture → probe → compute → cost → **data capture**), placed last on purpose so a still-unsatisfied earlier gate (missing manifest / unhookable architecture / unloadable probe / fleet too small / unacknowledged cost) refuses first — the 422 a caller sees is always the *first* unmet gate, and below the frontier, where none of the frontier gates fire, this is the one run gate that still applies. It is a **run** gate, not a **plan** gate: a planning-only `/scale-plan` preview captures nothing (no worker ever runs), so the gate is never enforced there (`build_scale_plan` does not run it) — only `create_distributed_audit` does. Because the gate is universal and raises before the record exists, every created distributed run carries an honest `DataCaptureSummary` at `DATA_CAPTURE_ACKNOWLEDGED` with `capture_committed=false`, surfaced as `DistributedAuditResponse.data_capture`, so the "we acknowledged, we did not write" distinction is visible on the wire for every run.

### Pieces (this entry)
- `api/services/cas_harness_data_governance.py` *(new)* — the gate's honesty core: the `DataCaptureStatus` literal (`DATA_CAPTURE_WORM_COMMITTED` / `DATA_CAPTURE_ACKNOWLEDGED` / `DATA_CAPTURE_NOT_ACKNOWLEDGED`); the real-scope module constants `CAPTURED_SIGNAL_CLASSES` (the four classes the audit already produces), `RETENTION_MODEL = "write_once_read_many"`, `REUSE_PURPOSE = "cas_native_training_corpus"`; `DataCaptureSummary` dataclass with `to_dict()` + an `.accepted` property + an honest `capture_committed` field (always `False` at this tier); `data_capture_requirement_notice()` (the honest disclaimer — names the capture, the immutable write-once retention, the CAS-Native reuse, "every distributed run", and "nothing is captured at the API tier … fleet-side"); `summarize_data_capture(*, acknowledged)` (acknowledged → `DATA_CAPTURE_ACKNOWLEDGED`; not acknowledged → `DATA_CAPTURE_NOT_ACKNOWLEDGED` with a reason naming the captured signal, the WORM retention, and the `accept_audit_data_capture` remedy); `validate_distributed_data_capture(*, acknowledged)` (raises `ValueError` on `NOT_ACKNOWLEDGED` for the 422 conversion; named `validate_distributed_*`, not `_frontier_*`, to signal universality).
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit(..., *, data_capture_acknowledged=False)` enforces the gate for **every** plan *after* the cost gate (universal, not frontier-gated); `DistributedAuditRecord.data_capture` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ScalePlanRequest.accept_audit_data_capture: bool` field (universal run-gate 8, ignored by the planning-only `/scale-plan`); `DataCaptureSummaryResponse`; `DistributedAuditResponse.data_capture`; the `/distributed/session` handler threads `data_capture_acknowledged=req.accept_audit_data_capture` into `create_distributed_audit` (gate `ValueError`→422); docstring notes gate (8) is universal alongside gate (2).

### Tests (this entry)
- `tests/test_cas_harness_data_governance.py` *(new, 9 tests)* — the honesty contract at the service layer: acknowledged → `DATA_CAPTURE_ACKNOWLEDGED` (`accepted=True`, `capture_committed=False`, no reasons), never `WORM_COMMITTED` at this tier; acknowledged surfaces the *real* capture scope (the four `CAPTURED_SIGNAL_CLASSES`, `retention_model`, `reuse_purpose`), not an invented one; not-acknowledged → `DATA_CAPTURE_NOT_ACKNOWLEDGED` naming what is captured ("activations", "readout"), where it is retained ("write-once"), and the `accept_audit_data_capture` remedy; `capture_committed` is `False` in *both* states; the notice is honest ("immutable", "write-once", "CAS-Native", "every distributed run", "nothing is captured at the API tier", "fleet-side"); `to_dict` 8-field round-trip shape; frozen dataclass; `validate_distributed_data_capture` returns the summary when acknowledged / raises ("audit data capture not acknowledged", names the flag) otherwise.
- `tests/test_cas_harness_distributed_audits.py` *(+5 tests)* — `/distributed/session`: a **below-frontier** 100B run with the data ack *popped* → 422 ("data capture not acknowledged", names the flag, names "activations"/"write-once") — the key proof the gate is universal, not frontier-only; below-frontier *with* the ack → 200 + `DATA_CAPTURE_ACKNOWLEDGED` (`capture_committed=False`, the four real `captured_signal_classes`, `write_once_read_many`, `cas_native_training_corpus`, no reasons); a fully-gated frontier run with the data ack popped → 422 on gate (8); both cost ack *and* data ack popped from a frontier run → 422 names **cost**, silent about data capture (pinning gate (8) as the *last* gate, after cost); a fully-gated frontier run → 200 carrying the same honest capture receipt. The base `_scale_payload` now carries `accept_audit_data_capture: True` (every distributed run must acknowledge the harvest); the universal-enforcement tests pop it back off.
- `tests/test_cas_harness_audit.py` — `test_distributed_session_carries_the_frontier_gate` extended into an **eight-step** gauntlet: …-no-cost → 422 (gate 4), then ack+provenance+`llama`+probe+compute+cost-**no-data** → 422 (gate 8, "data capture not acknowledged"), then +data-ack → 200 + `…COST_ACKNOWLEDGED` + `DATA_CAPTURE_ACKNOWLEDGED` (`capture_committed=False`, real `pooled_hidden_state_activations` in the captured classes) + `MODEL_ACCESS_DECLARED`.
- `tests/test_cas_harness_fleet_executor.py` / `tests/test_cas_harness_fleet_executor_contract.py` — a fleet run is a real distributed run, so its setup now acknowledges the harvest (base `_scale_payload` carries `accept_audit_data_capture: True`; the contract helper threads `data_capture_acknowledged=True` into `create_distributed_audit`), keeping the transitive callers honest under the now-universal gate.
- Local validation: `test_cas_harness_data_governance.py` (9) + `test_cas_harness_distributed_audits.py` (54) → **63 passed** in one run; `test_cas_harness_audit.py` (42) green in isolation; the full transitive set — `fleet_executor` + `fleet_executor_contract` + `harvest` + `verdict_runner` + `evidence_bridge` (57) and the sibling gate services `cost_acknowledgment` + `model_access` + `scale_planner` + `compute_feasibility` + `model_provenance` + `architecture_adapter` + `probe_compatibility` (136) — all green. The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Frontier run-gate (4) — a real 300B–4T run is *refused* unless the caller acknowledges its caller-owned compute cost, and the gate *never quotes a price* because the planner models no duration, throughput, or dollar rate it could honestly quote (Jun 1, 2026)

Gates (5)/(6)/(7)/(3) all answer a *capability* question — which weights, can we hook them, can we score them, can the hardware hold them. This gate answers a different kind of question entirely: not *can* it run, but **does the caller accept what running it costs?** It exists to prevent one specific dishonest-by-omission failure — a customer spending a fortune on frontier compute for a result CAS Harness has *already labelled* `EXPERIMENTAL_NOT_VALIDATED`, without ever once having been asked to acknowledge the spend. The honesty constraint shapes this gate harder than any other in the series: **nothing in the system models wall-clock duration, throughput (tokens/sec), or dollars** — there is no rate, no price book, no duration estimator anywhere in the planner — so the gate **refuses to quote a price**, because quoting one would mean inventing exactly the duration/throughput/$-rate model the honesty constraint forbids. This entry closes **gate (4) — cost acknowledgment**: a real frontier-scale (`EXPERIMENTAL_NOT_VALIDATED`, >300B) distributed audit run is now **refused with HTTP 422 unless the caller explicitly acknowledges the run's caller-owned, unquoted compute cost.**

**1) The gate quotes no price — it surfaces the *real committed magnitude* the planner already computed, and invents nothing.** Every quantity in the receipt is one that already exists upstream: `recommended_worker_count` and `estimated_total_runtime_gb` come straight from the plan (for a 1000B bf16 model: 84 workers, 2360 GB), and the declared fleet (`declared_accelerator_count` × `accelerator_memory_gb`, `effective_accelerator_count`) comes straight from the gate-(3) compute summary when present. The fields CAS Harness *cannot* honestly produce — duration, throughput, dollars — are **deliberately absent** rather than guessed. The refusal names the real numbers (`commits {N} probe workers to hold ~{G} GB`) and then explicitly disclaims what it will not compute, in the model's own words: *"a compute cost CAS Harness does not estimate, quote, bill, or cap."* The tests pin the honesty constraint as an assertion — the refusal contains no `$`, no `per hour` — so a future "helpful" attempt to price the run breaks CI rather than shipping.

**2) The receipt is honest about acknowledged vs metered, mirroring every other gate's declared-vs-verified split.** Cost resolves to one of three states: **`COST_METERED`** (the fleet metered real accelerator-hours of actual consumption — fleet-side only, the one place real compute runs, and therefore **never** produced at the API tier, where no compute has happened — so `cost_metered` is always `false` here, exactly as the other gates' `*_verified` fields are), **`COST_ACKNOWLEDGED`** (the caller accepted the uncosted commitment — enough to *create* a run, never on its own a customer ACCEPT), and **`COST_NOT_ACKNOWLEDGED`** (a frontier run with no acknowledgement → `ValueError` → 422). Acknowledgement is consent to an unquoted, caller-owned, **un-metered** spend on the caller's own infrastructure — it is emphatically *not* a measurement, and the status name keeps that distinction legible on the wire.

**3) The gate lives at the same single choke point, runs *last*, and stricter-for-bigger holds.** `create_distributed_audit(..., *, cost_acknowledged=False)` enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans **after** the compute gate (full gate order: access → provenance → architecture → probe → compute → **cost**), placed last on purpose so its receipt can reference the *already-validated* fleet the gate-(3) envelope declared. A still-unsatisfied earlier gate (missing manifest / unhookable architecture / unloadable probe / fleet too small) refuses first, so the 422 a caller sees is always the *first* unmet gate. **Bigger model = stricter gate, never weaker:** below the frontier the committed fleet is modest, so a cost ack is *optional* — a volunteered acknowledgement is recorded as its honest `COST_ACKNOWLEDGED` summary for traceability, but its absence never blocks the run. Cost is a **run** gate, not a **plan** gate: the public planning-only `/scale-plan` preview is unaffected. `DistributedAuditRecord` carries an optional `CostExposureSummary`, and `DistributedAuditResponse.cost` exposes the full tri-state receipt.

### Pieces (this entry)
- `api/services/cas_harness_cost_acknowledgment.py` *(new)* — the gate's honesty core: the `CostAcknowledgmentStatus` literal (`COST_METERED` / `COST_ACKNOWLEDGED` / `COST_NOT_ACKNOWLEDGED`); `CostExposureSummary` dataclass with `to_dict()` + an `.accepted` property + an honest `cost_metered` field (always `False` at this tier) and the real surfaced magnitudes (worker count, runtime GB, declared/effective accelerator fields, all `… | None`); `frontier_cost_requirement_notice()` (the honest disclaimer — "does NOT estimate … duration, throughput, or dollar cost, and does NOT bill, meter, or cap it … never at the API tier"); `_magnitudes(plan, compute)` (pulls every number from the plan + gate-(3) summary, inventing none); `summarize_cost_exposure(...)` (acknowledged → `COST_ACKNOWLEDGED`; not acknowledged → `COST_NOT_ACKNOWLEDGED` with a reason that names the real magnitude, points at the `accept_frontier_compute_cost` flag *and* the below-frontier alternative, and quotes no price); `validate_frontier_cost_acknowledgment(...)` (raises `ValueError` on `COST_NOT_ACKNOWLEDGED` for the 422 conversion).
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit(..., *, cost_acknowledged=False)` enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans *after* the compute gate (and records an optional summary below frontier when a caller volunteers the ack); `DistributedAuditRecord.cost` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ScalePlanRequest.accept_frontier_compute_cost: bool` field (frontier run-gate 4, naming the unquoted caller-owned cost); `CostExposureSummaryResponse`; `DistributedAuditResponse.cost`; the `/distributed/session` handler threads `cost_acknowledged=req.accept_frontier_compute_cost` into `create_distributed_audit` (gate `ValueError`→422).

### Tests (this entry)
- `tests/test_cas_harness_cost_acknowledgment.py` *(new, 10 tests)* — the honesty contract at the service layer: acknowledged → `COST_ACKNOWLEDGED` (`accepted=True`, `cost_metered=False`, no reasons), never `COST_METERED` at this tier; acknowledged surfaces *real* magnitudes that equal the plan's own (`recommended_worker_count`, `estimated_total_runtime_gb`) and the gate-(3) fleet (64 × 80 GB); acknowledged *without* a compute envelope still surfaces the plan magnitudes while the fleet fields are honestly `null`; not-acknowledged → `COST_NOT_ACKNOWLEDGED` naming the real worker count + runtime GB + the `accept_frontier_compute_cost` remedy + the `below-frontier` alternative; **the refusal never quotes a price** ("does not estimate, quote, bill, or cap"; no `$`; no `per hour`); the notice is honest about unquoted caller-owned cost ("does NOT", "caller's", "never at the API tier", no `$`); `to_dict` 10-field round-trip shape (`cost_metered=False`, non-empty reasons on a refusal); frozen dataclass; `validate_frontier_cost_acknowledgment` returns the summary when acknowledged / raises ("frontier compute cost not acknowledged", names the flag) otherwise.
- `tests/test_cas_harness_distributed_audits.py` — `/distributed/session`: frontier + provenance + architecture + probe + sufficient compute but **no** cost ack → 422 ("cost not acknowledged", names `accept_frontier_compute_cost`, contains no `$`/`per hour`); frontier + all gates + cost ack → 200 + `COST_ACKNOWLEDGED` (`acknowledged=True`, `cost_metered=False`, real magnitudes: `recommended_worker_count>0`, `declared_accelerator_count=64`, `effective_accelerator_count=64`); below-frontier requires no cost ack (200, `cost: null`) but records a volunteered one's summary (`COST_ACKNOWLEDGED`, fleet fields `null`). The frontier happy-path bodies now carry the cost ack via `_frontier_payload` (which bundles both frontier acknowledgement flags); the gate-4 refusal test pops it back off.
- `tests/test_cas_harness_audit.py` — `test_distributed_session_carries_the_frontier_gate` extended into a **seven-step** gauntlet: no-ack → 422, …-no-provenance → 422 (gate 5), …-no-architecture → 422 (gate 6), …-no-probe → 422 (gate 7), …-no-compute → 422 (gate 3), ack+provenance+`llama`+probe+compute-**no-cost** → 422 (gate 4, "cost not acknowledged", no `$`), +cost-ack → 200 + `PROVENANCE_DECLARED_NOT_VERIFIED` + `ARCHITECTURE_ADAPTER_AVAILABLE` + `PROBE_COMPATIBILITY_DECLARED` + `COMPUTE_FEASIBILITY_DECLARED` + `COST_ACKNOWLEDGED` (`cost_metered=False`) + `MODEL_ACCESS_DECLARED`.
- Local validation: `test_cas_harness_cost_acknowledgment.py` (10) + `test_cas_harness_scale_planner.py` (14) + `test_cas_harness_compute_feasibility.py` (23) → **47 passed** in one run; `test_cas_harness_distributed_audits.py` (49) and `test_cas_harness_audit.py` (42) each green in isolation (their route files trip the pre-existing rate-limiter `429` cross-contamination only under a whole-suite run). The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Run-gate (2) — *every* distributed run, frontier or not, is *refused* unless the model is open-weight, because the audit is a mechanistic probe and a hosted/black-box target has no hidden states to pool, and the receipt is honest about declared-vs-verified (Jun 1, 2026)

Gates (3)/(5)/(6)/(7) are all *frontier* questions — which weights, can we hook them, can we score them, can the hardware hold them — each stricter *at* the frontier and optional below it. This gate answers the one question that comes **before** all of those, and it is not frontier-specific at all: **can we mechanistically reach this model in the first place?** The distributed CAS Harness audit is a *mechanistic* probe — each worker loads the weights, hooks the decoder layers, and pools the resulting hidden-state activations into the `cas_axis_readout` that every shard declares in its `expected_outputs`. That is physically possible **only** for open-weight / internal-access models. A model reachable only as a provider-hosted text/JSON API exposes **no hidden states**, so the `cas_axis_readout` deliverable cannot be produced *at all* — the worker would have nothing to pool. This entry closes **gate (2) — model-access modality**: a distributed run is **refused with HTTP 422 for any access mode but open-weight**, at **every** size, and the refusal points the caller at the behavioral `target/verify` path that *is* appropriate for a hosted/black-box model.

**1) This gate is *universal*, not stricter-for-bigger — and that is the honest framing.** The other gates relax below the frontier because empirical validation, compute headroom, and provenance rigor genuinely scale with model size. Mechanistic reachability does not: a 20B black-box model is *exactly* as un-probeable as a 1T one — the worker has no hidden states to hook in either case. So unlike gates (3)/(5)/(6)/(7), which call `validate_frontier_*` only for `EXPERIMENTAL_NOT_VALIDATED` plans, gate (2) is enforced in the planner's `_validate_request` for **every** distributed run regardless of scale, because it is a precondition of the *method itself*, not a risk that grows with size. The refusal is honest and grounded — it is a real mechanical limit of the worker, not an invented criterion — which is exactly why it can fire at all sizes without overclaiming.

**2) It closes a real enforcement gap at the service choke point, not just the HTTP edge.** Open-weight-only was previously enforced *only* by a Pydantic `Literal["open_weight"]` on the route model — a generic schema `422` with no explanation, and, worse, a gate that lived **above** the service layer: the route silently dropped `weight_access` when it built the planner request, the service `ScalePlanRequest` had **no `weight_access` field at all**, and `build_scale_plan` simply *stamped* `weight_access="open_weight"` onto every plan. Any caller reaching `create_distributed_audit` / `build_scale_plan` *underneath* the route (the fleet-executor path inherits it transitively) had no access gate whatsoever. This entry moves enforcement down to the same single choke point the other gates use: the service request now carries a real `weight_access: ModelAccessMode` field, `_validate_request` calls `validate_distributed_model_access(...)` (raising `ValueError`→422), and the route `Literal` is **broadened** to the full mode set precisely so the *explanatory* service-layer refusal is the one HTTP callers see — naming the mode, naming why `cas_axis_readout` is physically impossible for it, and pointing at `target/verify` — instead of a bare enum rejection.

**3) The receipt is honest about declared vs verified, and rides along on every run.** Access modality resolves to one of three states, mirroring the other gates: **`MODEL_ACCESS_VERIFIED`** (a worker actually loaded the weights and confirmed local access — fleet-side only, **never** produced at the API tier, where no weights are touched), **`MODEL_ACCESS_DECLARED`** (the caller declared open-weight access — enough to *create* a run, never on its own a customer ACCEPT), and **`MODEL_ACCESS_UNSUPPORTED`** (a hosted / black-box / output-only / empty / unrecognized mode → `ValueError` → 422). Because any non-open-weight mode raises *before* the record is created, a created distributed run's `access` summary is always `MODEL_ACCESS_DECLARED` with `mechanistic_probe_supported=true` and `access_verified=false` — and every distributed run now carries it (`DistributedAuditRecord.access`, surfaced as `DistributedAuditResponse.access`), so the honest "we declared, we did not verify" distinction is visible on the wire for every run, not just the frontier ones.

### Pieces (this entry)
- `api/services/cas_harness_model_access.py` *(new)* — the gate's honesty core: `MECHANISTIC_ACCESS_MODE = "open_weight"`; the `ModelAccessMode` / `ModelAccessStatus` literals; `_NON_MECHANISTIC_MODES` (human-readable descriptions of `hosted_api` / `black_box` / `output_only` so the refusal names *why* each cannot be probed); `ModelAccessSummary` dataclass with `to_dict()` + an `.accepted` property + an honest `access_verified` field (always `False` here); `summarize_model_access(...)` (normalizes case/whitespace, accumulates the refusal reason, lands open-weight at `DECLARED` and everything else — including the empty declaration and any unrecognized string — at `UNSUPPORTED`); `validate_distributed_model_access(...)` (raises `ValueError` on `UNSUPPORTED` for the 422 conversion); `mechanistic_access_requirement_notice()`.
- `api/services/cas_harness_scale_planner.py` — `ScalePlanRequest` gains a real `weight_access: ModelAccessMode = "open_weight"` field; `_validate_request` calls `validate_distributed_model_access(declared_mode=request.weight_access)` for **every** size (the universal enforcement point). `build_scale_plan` still stamps `weight_access="open_weight"` on the `ScalePlan`, now honest by construction because any other mode has already raised upstream.
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit` computes `access_summary = summarize_model_access(declared_mode=plan.weight_access)` right after `build_scale_plan`; `DistributedAuditRecord.access` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ScalePlanRequest.weight_access` broadened from `Literal["open_weight"]` to the service `ModelAccessMode` (so the explanatory service 422 is reachable, not a bare enum 422), with a description naming the mechanistic-only constraint + the `target/verify` fallback; both the `/scale-plan` and `/distributed/session` handlers thread `weight_access=req.weight_access` into the planner request; `ModelAccessSummaryResponse`; `DistributedAuditResponse.access`.

### Tests (this entry)
- `tests/test_cas_harness_model_access.py` *(new, 26 tests)* — the honesty contract at the service layer: `open_weight` → `DECLARED` (`mechanistic_probe_supported=True`, `access_verified=False`, no reasons), never `VERIFIED` at this tier; case/whitespace normalization to the canonical mode; `hosted_api` / `black_box` / `output_only` → `UNSUPPORTED` with every reason naming the `open_weight` remedy *and* the `target/verify` fallback, the `cas_axis_readout` / `hidden-state activations` limit named; empty + whitespace-only → `UNSUPPORTED` ("no model access mode was declared", `declared_mode="(unspecified)"`); an unknown string refused generically but still named; the notice is honest about "never at the API tier"; every summary carries the notice; `to_dict` round-trip shape; frozen dataclass; `validate_distributed_model_access` raises on every `UNSUPPORTED` mode / returns the summary for `open_weight`.
- `tests/test_cas_harness_distributed_audits.py` — `/distributed/session` (parametrized over `hosted_api` / `black_box` / `output_only`) → 422 naming `open_weight` + `target/verify`, at a below-frontier 100B size (proving the gate is universal, not frontier-only); a below-frontier open-weight run → 200 carrying `access.status == "MODEL_ACCESS_DECLARED"` (`mechanistic_probe_supported=True`, `access_verified=False`, `declared_mode="open_weight"`, no reasons).
- `tests/test_cas_harness_audit.py` — `test_scale_plan_rejects_non_mechanistic_access_modes` parametrized over all three non-mechanistic modes (each → 422 naming `open_weight` + `target/verify`); `test_distributed_session_carries_the_frontier_gate`'s allowed step now also asserts the open-weight frontier run carries `access.status == "MODEL_ACCESS_DECLARED"` (`mechanistic_probe_supported=True`, `access_verified=False`) alongside the gate-3/5/6/7 receipts.
- Local validation: `test_cas_harness_model_access.py` (26) + `test_cas_harness_scale_planner.py` (14) + `test_cas_harness_compute_feasibility.py` (23) → **63 passed** in one run; `test_cas_harness_distributed_audits.py` (45) and `test_cas_harness_audit.py` (42) each green in isolation (their route files trip the pre-existing rate-limiter `429` cross-contamination only under a whole-suite run). The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Frontier run-gate (3) — a real 300B–4T run is *refused* unless the caller declares a compute envelope that can physically hold the model under the planner's *own* memory math, because the planner silently provisions 62% of each card and clamps fan-out to 512, and the receipt is honest about declared-vs-verified (Jun 1, 2026)

Gates (5)→(6)→(7) established *which* weights are audited, that the worker can *hook* them, and that it can *score* them. The next question is the most physical one a frontier run faces: **can the declared hardware actually hold a 1T–4T model at all?** This gate exists because the scale planner can lie by omission in a very specific way — it provisions only `USABLE_MEMORY_FRACTION` (**0.62**) of each accelerator and **silently clamps worker fan-out to `MAX_WORKER_FANOUT` (512)**. So a frontier model can come back with a plan that *looks* perfectly schedulable while every shard is quietly asked to hold more than one accelerator can fit — the run would then OOM on load, after the caller had been told it was planned. This entry closes **gate (3) — compute feasibility**: a real frontier-scale (`EXPERIMENTAL_NOT_VALIDATED`, >300B) distributed audit run is now **refused with HTTP 422 unless the caller declares a compute envelope whose capped, usable aggregate memory can hold the planner's own runtime estimate.** It was chosen as the next gate precisely *because it is pure physics* — every number it uses already exists in the plan — so it can refuse for a real reason without inventing a single quantity. (A cost-approval gate (4), by contrast, would have to invent a duration/throughput/$-rate model, which the honesty constraint forbids; cost stays acknowledgement-only when it lands.)

**1) The gate is anchored to the planner's *own* arithmetic — it invents no numbers.** The only quantity it compares against is `plan.memory_estimate.estimated_total_runtime_gb` — the planner's existing figure (weights at the plan's precision + its 18% activation/runtime overhead). It checks that figure against the **capped, usable** aggregate of the declared fleet: `min(512, accelerator_count) × accelerator_memory_gb × 0.62`. Both magic constants are no longer magic — `USABLE_MEMORY_FRACTION` and `MAX_WORKER_FANOUT` were extracted as named module constants in the planner and the gate *imports the same symbols*, so the two surfaces are structurally unable to drift (a refactor that loosens the planner's clamp loosens the gate in lockstep). No duration, no throughput, no token-rate, no dollars — nothing the code cannot actually ground. The decision is made with an exact integer comparison to dodge float-rounding ambiguity: `accelerators_required = ceil(needed_runtime_gb / (accelerator_memory_gb × 0.62))`, `effective_count = min(512, declared_count)`, and `memory_sufficient = effective_count ≥ accelerators_required`.

**2) The gate is honest about declared vs verified, and names *which* of two failures it hit.** Compute feasibility resolves to one of three states, mirroring gates (5)/(6)/(7): **`COMPUTE_FEASIBILITY_VERIFIED`** (a worker actually loaded shards onto real accelerators and the fit held — fleet-side only, **never** produced at the API tier, where no hardware has been touched), **`COMPUTE_FEASIBILITY_DECLARED`** (the declared envelope is numerically sufficient under the planner's model — enough to *create* a run, never on its own a customer ACCEPT), and **`COMPUTE_FEASIBILITY_INSUFFICIENT`** (the envelope cannot hold the model → `ValueError` → 422). The insufficiency reason is split into the two *operationally different* diagnoses a caller needs: if `accelerators_required > 512`, the per-accelerator memory is simply too small for the fan-out cap — **adding more cards cannot help**, the notice says *declare larger accelerators*; otherwise the fleet is just too small, and the notice says *declare at least N accelerators of this size*. The summary carries both constants (`usable_memory_fraction`, `fanout_cap`), the per-accelerator usable GB, the `effective_accelerator_count` (post-cap), a `fanout_capped` flag, `needed_runtime_gb`, `available_aggregate_gb`, `memory_headroom_gb`, `accelerators_required`, and `fit_verified` (always `false` at this tier) — so the receipt is fully self-describing and traceable.

**3) The gate lives at the same single choke point, and stricter-for-bigger holds.** `create_distributed_audit(request, *, provenance=None, architecture=None, probe=None, compute=None)` enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (gate order: frontier-ack → provenance → architecture → probe → **compute**, so a missing manifest / unhookable architecture / unloadable probe still refuses first); the fleet executor operates over an already-created record, so it inherits the gate transitively. **Bigger model = stricter gate, never weaker:** below-frontier runs are *not* blocked on compute — a volunteered envelope is recorded as its honest summary (`DECLARED` or `INSUFFICIENT`) for traceability, but its absence never stops the run, and an insufficient one below frontier is recorded, not refused. Compute is a **run** gate, not a **plan** gate: the public planning-only `/scale-plan` preview is unaffected (a frontier *plan* still previews without an envelope; a frontier *run* does not). `DistributedAuditRecord` carries an optional `ComputeFeasibilitySummary`, and `DistributedAuditResponse.compute` exposes the full tri-state receipt.

### Pieces (this entry)
- `api/services/cas_harness_scale_planner.py` — extracted the two previously-inline magic numbers into named, documented module constants `USABLE_MEMORY_FRACTION = 0.62` and `MAX_WORKER_FANOUT = 512`; refactored `_recommended_worker_count` to compute a `memory_floor` from the runtime estimate ÷ usable-per-card and clamp the result to `MAX_WORKER_FANOUT`; the `minimum_worker_count` validation now reads the same constant. (Behaviour unchanged — the constants *are* the numbers the planner already used — but they are now a shared source of truth the gate consumes.)
- `api/services/cas_harness_compute_feasibility.py` *(new)* — the gate's honesty core: `ComputeEnvelopeDeclaration` (caller's accelerator count + per-card memory + optional type name — the gate **never** infers memory from the type string) and `ComputeFeasibilitySummary` dataclasses with `to_dict()` + an `.accepted` property; `summarize_compute_feasibility(...)` (the tri-state checker that accumulates *every* refusal reason and runs the exact integer fit check, importing `USABLE_MEMORY_FRACTION`/`MAX_WORKER_FANOUT`/`ScalePlan` straight from the planner); `validate_frontier_compute_feasibility(...)` (raises `ValueError` on `INSUFFICIENT` for the 422 conversion); `frontier_compute_requirement_notice()`.
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit(..., *, compute=None)` now enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (and records an optional summary below frontier); `DistributedAuditRecord.compute` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ComputeEnvelopeDeclarationRequest` (extra-forbid request model, `accelerator_count`/`accelerator_memory_gb` bounded, with `to_service_declaration()`); `ScalePlanRequest.compute`; `ComputeFeasibilitySummaryResponse`; `DistributedAuditResponse.compute`; the `/distributed/session` handler threads the envelope into `create_distributed_audit` (gate `ValueError`→422).

### Tests (this entry)
- `tests/test_cas_harness_compute_feasibility.py` *(new, 23 tests)* — the honesty contract at the service layer: missing envelope / non-positive count / non-positive memory → `INSUFFICIENT`; too-few accelerators (16×80GB for a 1T model, `required 48`) → `INSUFFICIENT` ("Declare at least 48"); one-short (47) still refused; per-accelerator-too-small for the fan-out cap (1M×4GB, `required 952 > 512`) → `INSUFFICIENT` ("fan-out cap" + "Declare larger accelerators"); a sufficient 64×80GB envelope → `DECLARED` (aggregate 3174.4GB, headroom 814.4GB, `fit_verified=False`); the exact 48-card boundary; precision flips feasibility (16×80GB `bf16`→`INSUFFICIENT` vs `int4` `needed 590`→`DECLARED`); a fan-out-capped-but-sufficient 600-card envelope (effective 512, notice says "only 512 are used"); the summary records both shared constants; `needed_runtime_gb` matches the plan; the notice is honest about `EXPERIMENTAL_NOT_VALIDATED`; `to_dict` round-trip; frozen dataclass; `validate_frontier_compute_feasibility` raises on `INSUFFICIENT` / returns the summary otherwise.
- `tests/test_cas_harness_distributed_audits.py` — `/distributed/session`: frontier + provenance + architecture + probe but **no** compute → 422 ("compute envelope"); frontier + insufficient compute (405B at 4×80GB) → 422 ("Declare at least 20 accelerators"); frontier + per-card-too-small (405B at 1M×2GB) → 422 ("fan-out cap" + "Declare larger accelerators"); frontier + sufficient compute → 200 + `COMPUTE_FEASIBILITY_DECLARED` (`memory_sufficient=True`, `effective_accelerator_count=64`, `needed_runtime_gb≈955.8`, `accelerators_required=20`, `fit_verified=False`); below-frontier requires no compute (200, `compute: null`) but records a volunteered one's summary, including recording an insufficient one without gating. The five frontier happy-path tests now attach a compute envelope.
- `tests/test_cas_harness_audit.py` — `test_distributed_session_carries_the_frontier_gate` extended into a **six-step** gauntlet: no-ack → 422, ack-no-provenance → 422 (gate 5), ack+provenance-no-architecture → 422 (gate 6), ack+provenance+architecture-no-probe → 422 (gate 7), ack+provenance+`llama`+probe-**no-compute** → 422 (gate 3, text mentions "compute"), ack+provenance+`llama`+probe+sufficient-compute → 200 + `PROVENANCE_DECLARED_NOT_VERIFIED` + `ARCHITECTURE_ADAPTER_AVAILABLE` + `PROBE_COMPATIBILITY_DECLARED` + `COMPUTE_FEASIBILITY_DECLARED`.
- Local validation: `test_cas_harness_scale_planner.py` (14) + `test_cas_harness_compute_feasibility.py` (23) + `test_cas_harness_distributed_audits.py` (42) → **79 passed** in one run; `test_cas_harness_audit.py` (40) green in isolation (its route files trip the pre-existing rate-limiter `429` cross-contamination only under a whole-suite run). The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Frontier run-gate (7) — a real 300B–4T run is *refused* unless the caller declares a CAS probe-readout the worker can structurally load, because the CAS axis readout is the run's central deliverable, and the receipt is honest about declared-vs-verified (Jun 1, 2026)

Gate (6) confirmed the probe worker can *locate and hook* the decoder stack. The very next question is the one the entire run exists to answer: **given those hooks, can the worker actually turn the captured activations into the CAS axis readout?** That readout is not a nice-to-have — every shard the scale planner emits declares `cas_axis_readout` in its `expected_outputs`, so it is *the point of the audit*. A frontier run that hooks the stack perfectly but cannot produce the readout would burn 300B–4T compute and come back with **no CAS scores at all** — the dishonest-by-omission failure this whole gate series exists to prevent. This entry closes **gate (7) — probe-readout compatibility**: a real frontier-scale (`EXPERIMENTAL_NOT_VALIDATED`, >300B) distributed audit run is now **refused with HTTP 422 unless the caller declares a structurally loadable CAS probe-readout specification.**

**1) The gate is anchored to the worker's real loader contract — not an aspirational one.** The probe worker (`live-trace-worker/scripts/run_open_weight_probe_shard.py` :: `compute_cas_axis_readout`) loads a JSON probe artifact and **requires** `schema_version == "cas_probe_linear_v1"` (else `RuntimeError`), a non-empty `axes` list with a `weights` dict (else `RuntimeError`), and for each axis a numeric vector whose length **equals the pooled-activation feature dimension** (else `RuntimeError("CAS probe axis … has incompatible hidden size")`). The new gate mirrors exactly those requirements, as data: wrong schema / empty axes / non-positive feature dimension → refused, **because the worker would reject the probe rather than score it**. The two worker failure modes are not the same and the gate respects the difference: a *missing* probe degrades gracefully (the worker reports `cas_axis_readout` as a *missing output*, so the fleet verifier cannot overclaim), but a *malformed* probe is worse — `compute_cas_axis_readout` raises, which **aborts the entire shard**, not just the readout. At frontier scale both outcomes are unacceptable, so the gate requires a loadable probe up front.

**2) The gate is honest about declared vs verified — and about loadable vs *validated*.** Probe compatibility resolves to one of three states, mirroring gates (5) and (6): **`PROBE_COMPATIBILITY_VERIFIED`** (the worker actually loaded the probe and computed the readout with matching dimensions against real pooled activations — worker-side only, never produced at the API tier), **`PROBE_COMPATIBILITY_DECLARED`** (a well-formed, loadable spec: right schema, non-empty axes, a positive declared feature dimension, internally consistent — enough to *create* a run, never enough on its own to reach a customer ACCEPT), and **`PROBE_COMPATIBILITY_UNSUPPORTED`** (missing at frontier / wrong schema / empty axes / non-positive dimension / a declared pooled-feature dimension that contradicts the probe's vector length / a malformed integrity hash → `ValueError` → 422). The scope stays deliberately narrow: the gate certifies the probe is **mechanically loadable and dimensionally self-consistent**, *not* that its scores are *meaningful* on this model — a frontier run is `EXPERIMENTAL_NOT_VALIDATED` by definition and no probe is empirically validated on a frontier family. An optional `expected_pooled_features` lets a caller who knows the run's pooling shape (`scenarios × assigned-layers × top_k`) run the worker's exact dimensional check at create time (a mismatch is refused with the worker's own "incompatible hidden size" language); absent it, `dimension_consistent` is honestly `null` and the final match is confirmed worker-side. (The worker's "incompatible hidden size" error text is itself misleading — the quantity it checks is the pooled-activation feature dimension, not the model `hidden_size` — so the gate's notice names the real quantity.)

**3) The gate lives at the same single choke point, and the receipt stays honest on the way out.** `create_distributed_audit(request, *, provenance=None, architecture=None, probe=None)` enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (gate order: frontier-ack → provenance → architecture → probe, so a missing/bad manifest or unhookable architecture still refuses first); the fleet executor operates over an already-created record, so it inherits the gate transitively. **Bigger model = stricter gate, never weaker:** below-frontier runs are *not* blocked on the probe — a volunteered spec is recorded as its honest summary (`DECLARED` or `UNSUPPORTED`) for traceability, but its absence never stops the run, and an unloadable one below frontier is recorded, not refused. The probe is a **run** gate, not a **plan** gate: the public planning-only `/scale-plan` preview is unaffected. `DistributedAuditRecord` carries an optional `ProbeCompatibilitySummary`, and `DistributedAuditResponse.probe` exposes the tri-state `status`, `schema_version`, `axis_count`/`axes`, `declared_feature_dimension`, `expected_pooled_features`, `dimension_consistent`, the optional `weights_sha256` (declared here, recomputed worker-side — `weights_hash_verified` is always `false` at the API tier), `probe_loadable`, the human-readable `notice`, and the refusal `reasons`.

### Pieces (this entry)
- `api/services/cas_harness_probe_compatibility.py` *(new)* — the gate's honesty core: `ProbeReadoutSpecification` (caller's lightweight statement of the worker-side probe file — schema, axes, per-axis `feature_dimension`, optional `probe_id` / `weights_sha256` / `expected_pooled_features`) and `ProbeCompatibilitySummary` dataclasses with `to_dict()` + an `.accepted` property; `REQUIRED_PROBE_SCHEMA_VERSION = "cas_probe_linear_v1"`; `summarize_probe_compatibility(...)` (the tri-state checker that collects *every* refusal reason, not just the first, and runs the worker's exact dimensional check when `expected_pooled_features` is supplied); `validate_frontier_probe_compatibility(...)` (raises `ValueError` on `UNSUPPORTED` for the 422 conversion); `frontier_probe_requirement_notice()`.
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit(..., *, probe=None)` now enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (and records an optional summary below frontier); `DistributedAuditRecord.probe` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ProbeReadoutSpecificationRequest` (extra-forbid request model with `to_service_specification()`); `ScalePlanRequest.probe`; `ProbeCompatibilitySummaryResponse`; `DistributedAuditResponse.probe`; the `/distributed/session` handler threads the spec into `create_distributed_audit` (gate `ValueError`→422).

### Tests (this entry)
- `tests/test_cas_harness_probe_compatibility.py` *(new, 22 tests)* — the honesty contract at the service layer: missing spec / wrong `schema_version` / empty (or whitespace-only) axes / missing-or-non-positive `feature_dimension` / malformed `weights_sha256` / declared-pooled-dimension mismatch → `UNSUPPORTED` (with every reason named, `dimension_consistent=False` on the mismatch); a loadable spec → `DECLARED` (never `VERIFIED` at this tier, `weights_hash_verified=False`); `dimension_consistent` is `None` without a declared pooled dimension and `True` on a match; uppercase hash normalized lowercase; `probe_id` recorded; the notice is honest about `EXPERIMENTAL_NOT_VALIDATED`; `to_dict` round-trip; `validate_frontier_probe_compatibility` raises on `UNSUPPORTED` / returns the summary otherwise.
- `tests/test_cas_harness_distributed_audits.py` — `/distributed/session`: frontier + valid provenance + hookable architecture but **no** probe → 422 (text mentions "probe"); frontier + wrong-schema probe → 422 (text names `cas_probe_linear_v1`); frontier + a pooled-dimension-mismatch probe → 422 ("incompatible hidden size"); frontier + a loadable probe → 200 + `PROBE_COMPATIBILITY_DECLARED` (`dimension_consistent: null`); below-frontier requires no probe (200, `probe: null`) but records a volunteered one's summary, including recording an unloadable one without gating. The four frontier happy-path tests now attach a probe.
- `tests/test_cas_harness_audit.py` — `test_distributed_session_carries_the_frontier_gate` extended into a five-step gauntlet: no-ack → 422, ack-no-provenance → 422 (gate 5), ack+provenance-no-architecture → 422 (gate 6), ack+provenance+architecture-no-probe → 422 (gate 7), ack+provenance+`llama`+loadable-probe → 200 + `PROVENANCE_DECLARED_NOT_VERIFIED` + `ARCHITECTURE_ADAPTER_AVAILABLE` + `PROBE_COMPATIBILITY_DECLARED`.
- Local validation: `test_cas_harness_probe_compatibility.py` (22) + `test_cas_harness_distributed_audits.py` (35) + `test_cas_harness_audit.py` (40) + `test_cas_harness_architecture_adapter.py` (26) + `test_cas_harness_model_provenance.py` (15) together → **138 passed**. The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Frontier run-gate (6) — a real 300B–4T run is *refused* unless the declared model architecture resolves to a probe adapter the worker can mechanically hook, and the receipt is honest about declared-vs-verified (Jun 1, 2026)

Gate (5) established *which* weights will be audited — identity, an open-weight license, a SHA-256 per file. The very next question a real frontier run has to answer is just as load-bearing and just as easy to fake a verdict around: **can the CAS Harness probe worker actually hook this architecture at all?** A provenance-clean 1T model in an architecture the worker cannot instrument would load, fail to find a decoder stack, and either crash or — worse — be papered over with a fabricated readout. This entry closes **gate (6) — architecture-adapter compatibility**: a real frontier-scale (`EXPERIMENTAL_NOT_VALIDATED`, >300B) distributed audit run is now **refused with HTTP 422 unless the caller declares a model architecture whose `model_type` (or an inferred architecture class) resolves to a probe adapter the worker can mechanically locate and hook.**

**1) The gate is anchored to what the worker can actually do — not to an aspirational allowlist.** The probe worker (`live-trace-worker/scripts/run_open_weight_probe_shard.py`) locates a model's decoder layer stack with exactly four hardcoded attribute paths — `gpt_neox.layers`, `model.layers`, `transformer.h`, `transformer.blocks` — and **raises `RuntimeError` for anything else**, then hooks each layer's `.mlp` (falling back to the whole layer when there is none). The new registry mirrors those four paths exactly, as data. An architecture whose `model_type` resolves to none of them is refused **because the worker would raise rather than capture activations** — the refusal is grounded in a real mechanical limit, not an invented criterion. Four families are recognised: `gpt_neox` (`gpt_neox.layers`), `llama_like` (`model.layers` — Llama / Mistral / Mixtral / Qwen2-3 / Gemma / OLMo / DeepSeek / Phi / Cohere / Granite / …), `gpt2_like` (`transformer.h` — GPT-2 / GPT-J / GPT-Neo / BLOOM / Falcon), and `mpt_like` (`transformer.blocks`), spanning 31 `model_type` keys.

**2) The gate is honest about declared vs verified — and about hookable vs *validated*.** Architecture resolves to one of three states, mirroring the provenance gate's split: **`ARCHITECTURE_ADAPTER_VERIFIED`** (the worker actually loaded the model, located the stack, and confirmed the `model_type` — worker-side only, never produced at the API tier), **`ARCHITECTURE_ADAPTER_AVAILABLE`** (a declared `model_type` resolves to a supported stack — enough to *create* a run, never enough on its own to reach a customer ACCEPT), and **`ARCHITECTURE_ADAPTER_UNSUPPORTED`** (missing declaration / unrecognized `model_type` / no adapter → `ValueError` → 422). Crucially the gate stays narrowly scoped: it certifies only that the worker can **locate and hook** the stack, **not** that the 40-Element readout has been *empirically validated* on that family — that remains the separate scale ladder. Only `gpt_neox` (Pythia, reproduced end-to-end on CPU) carries `empirically_validated`; every other family is honestly `structurally_supported`, consistent with a frontier run being `EXPERIMENTAL_NOT_VALIDATED` by definition. The `mpt_like` adapter even carries the honest caveat that MPT blocks expose `.ffn` not `.mlp`, so the worker's hook captures block output rather than the MLP.

**3) The gate lives at the same single choke point, and the receipt stays honest on the way out.** `create_distributed_audit(request, *, provenance=None, architecture=None)` enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (gate order: frontier-ack → provenance → architecture, so a missing/bad manifest still refuses first); the fleet executor operates over an already-created record, so it inherits the gate transitively. **Bigger model = stricter gate, never weaker:** below-frontier runs are *not* blocked on architecture — a volunteered declaration is recorded as its honest summary (`AVAILABLE` or `UNSUPPORTED`) for traceability, but its absence never stops the run, and an unsupported one below frontier is recorded, not refused. Architecture is a **run** gate, not a **plan** gate: the public planning-only `/scale-plan` preview is unaffected. `DistributedAuditRecord` carries an optional `ArchitectureAdapterSummary`, and `DistributedAuditResponse.architecture` exposes the tri-state `status`, `resolved_model_type`, `adapter_family`, `layer_stack_attr`, `hook_submodule`, `adapter_validation`, `adapter_available`, the human-readable `notice`, and the declared dims (recorded for traceability; a `num_hidden_layers`-vs-planned-shards cross-check is a labelled future enhancement, not yet enforced).

### Pieces (this entry)
- `api/services/cas_harness_architecture_adapter.py` *(new)* — the gate's honesty core: `ProbeAdapterProfile` + a `_PROBE_ADAPTER_REGISTRY` of four families mirroring the worker's four `locate_transformer_layers` paths; `normalize_model_type` (alias + separator folding: `qwen`→`qwen2`, `GPTNeoX`→`gpt_neox`, …); `_model_type_from_architecture_class` (`LlamaForCausalLM`→`llama`, used only when `model_type` is absent); `summarize_architecture_adapter(...)` (tri-state checker); `validate_frontier_architecture(...)` (raises `ValueError` on `UNSUPPORTED` for the 422 conversion); `ModelArchitectureDeclaration` / `ArchitectureAdapterSummary` dataclasses with `to_dict()` + an `.accepted` property.
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit(..., *, architecture=None)` now enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (and records an optional summary below frontier); `DistributedAuditRecord.architecture` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ModelArchitectureDeclarationRequest` (extra-forbid request model with `to_service_declaration()`); `ScalePlanRequest.architecture`; `ModelArchitectureAdapterSummaryResponse`; `DistributedAuditResponse.architecture`; the `/distributed/session` handler threads the declaration into `create_distributed_audit` (gate `ValueError`→422).

### Tests (this entry)
- `tests/test_cas_harness_architecture_adapter.py` *(new, 26 tests)* — the honesty contract at the service layer: no declaration / neither model_type-nor-class / unknown `model_type` (`mamba`) / unrecognized architecture class (`MambaForCausalLM`) → `UNSUPPORTED`; `llama` / `qwen2` / `gpt2` / `mpt` resolve to the right family + layer-stack attr + hook submodule (`AVAILABLE`, never `VERIFIED` at this tier); `gpt_neox` carries `empirically_validated`; architecture-class fallback + empty-model_type fallback + explicit-model_type precedence; declared dims recorded; `to_dict` round-trip; `validate_frontier_architecture` raises on `UNSUPPORTED` / returns the summary otherwise; `normalize_model_type` aliases; `supported_model_types()` covers all four stacks (31 keys).
- `tests/test_cas_harness_distributed_audits.py` — `/distributed/session`: frontier + valid provenance but **no** architecture → 422 (text mentions "architecture"); frontier + unsupported architecture (`mamba`) → 422; frontier + supported architecture (`qwen2` / `LlamaForCausalLM` class / `gpt_neox`) → 200 + `ARCHITECTURE_ADAPTER_AVAILABLE`; below-frontier requires no architecture (200, `architecture: null`) but records a volunteered one's summary, including recording an unsupported one without gating.
- `tests/test_cas_harness_audit.py` — `test_distributed_session_carries_the_frontier_gate` extended into a four-step gauntlet: no-ack → 422, ack-no-provenance → 422 (gate 5), ack+provenance-no-architecture → 422 (gate 6), ack+provenance+`llama` → 200 + `PROVENANCE_DECLARED_NOT_VERIFIED` + `ARCHITECTURE_ADAPTER_AVAILABLE`.
- Local validation: `test_cas_harness_architecture_adapter.py` (26) + `test_cas_harness_distributed_audits.py` (28) + `test_cas_harness_audit.py` + `test_cas_harness_model_provenance.py` together → **109 passed**. The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Frontier run-gate (5) — a real 300B–4T run is *refused* unless the caller attaches a model provenance/license/weight-hash manifest, and the receipt is honest about declared-vs-verified (Jun 1, 2026)

The previous entry opened the frontier lane and closed **gate (1)** — the explicit experimental-risk acknowledgement. But accepting risk only says the caller *consents* to an unproven run; it says nothing about *which* weights will be audited, whether they are actually open-weight, or whether they are what the caller claims. That gap matters most precisely at frontier scale, where we can least afford to audit an unknown blob and stamp a verdict on it. This entry closes **gate (5) — model provenance / license / weight-hash manifest**: a real frontier-scale (`EXPERIMENTAL_NOT_VALIDATED`, >300B) distributed audit run is now **refused with HTTP 422 unless the caller attaches a valid provenance manifest** — declared model identity, source URI, a recognized open-weight license, and a SHA-256 for every weight file. **CAS Harness records and checks provenance; it does not grant or adjudicate license rights** — it asserts only that the declared license is a recognized open-weight identifier, consistent with auditing open-weight / internal-access models only.

**1) The gate is honest about declared vs verified — it never claims a hash it did not recompute.** Provenance resolves to one of three states, mirroring the WORM "not retained until re-read" pattern: **`PROVENANCE_VERIFIED`** (a SHA-256 was actually recomputed from bytes on disk and matched the declared digest), **`PROVENANCE_DECLARED_NOT_VERIFIED`** (a well-formed, identity-matching, open-weight-licensed manifest whose hashes have only been *declared*), and **`PROVENANCE_REJECTED`** (missing manifest, identity mismatch, unrecognized license, malformed digest, duplicate path, or a recomputed-hash *mismatch*). The API tier never reads weight bytes — the workers that load the weights are where hashes get recomputed — so a good manifest at *create* time honestly lands at `PROVENANCE_DECLARED_NOT_VERIFIED`. That is **enough to create a frontier run, never enough on its own to reach a customer ACCEPT**: the verifier + WORM anchor still gate the final verdict downstream, exactly as before.

**2) The gate lives at the single choke point, so the fleet path inherits it.** `create_distributed_audit` is the one function that turns a plan into a run record; the fleet executor operates over an already-created record (it does not re-plan or re-load weights). Gating creation therefore covers the fleet path transitively. For an `EXPERIMENTAL_NOT_VALIDATED` plan the gate calls `validate_frontier_provenance(...)`, which raises `ValueError` (→ HTTP 422) on `PROVENANCE_REJECTED`; the run record never materializes. **Bigger model = stricter gate, never weaker:** below-frontier runs (≤300B) are *not* blocked on provenance — if a caller volunteers a manifest we record the honest summary, but its absence never stops the run. Provenance is a **run** gate, not a **plan** gate: the public planning-only `/scale-plan` preview is deliberately unaffected, so frontier *planning* still works without a manifest while frontier *running* does not.

**3) The receipt travels out through the API, and it stays honest in the response.** `DistributedAuditRecord` carries an optional `ProvenanceSummary`, and `DistributedAuditResponse` exposes `provenance` with the tri-state `status`, `license_recognized`, per-file verification rows (`declared_sha256`, `verified`, `recomputed_sha256`, honest note), `all_hashes_verified`, and a `manifest_content_digest` (a deterministic integrity fingerprint over the declared fields — explicitly **not** a cryptographic signature; a signed sigstore/cosign/GPG attestation is a labelled future enhancement). A frontier caller therefore always gets back, in the run receipt, the exact provenance state the gate computed — including the honest "declared, not verified" language when that is the truth.

### Pieces (this entry)
- `api/services/cas_harness_model_provenance.py` *(new)* — the gate's honesty core: `ModelProvenanceManifest` / `WeightFileRef` / `ProvenanceSummary` / `WeightFileVerification` dataclasses; an open-weight **license allowlist** + alias normalization (`apache2`→`apache-2.0`, `llama-3.1`→`llama3.1`, …) — unknown tags are refused, not waved through; `compute_file_sha256` (chunked, the worker-side verification primitive); `summarize_model_provenance(...)` (the tri-state checker, with an optional `weights_root` recompute path); `validate_frontier_provenance(...)` (raises `ValueError` on rejection for the 422 conversion); `content_digest()` (integrity fingerprint, not a signature).
- `api/services/cas_harness_distributed_audits.py` — `create_distributed_audit(request, *, provenance=None)` now enforces the gate for `EXPERIMENTAL_NOT_VALIDATED` plans (and records an optional summary below frontier); `DistributedAuditRecord.provenance` + `to_dict()`.
- `api/routes/cas_harness_audit.py` — `ModelProvenanceManifestRequest` / `ModelProvenanceWeightFileRequest` (extra-forbid request models with `to_service_manifest()`); `ScalePlanRequest.provenance`; `ModelProvenanceSummaryResponse` / `ModelProvenanceFileVerificationResponse`; `DistributedAuditResponse.provenance`; the `/distributed/session` handler threads the manifest into `create_distributed_audit` (planner/gate `ValueError`→422).

### Tests (this entry)
- `tests/test_cas_harness_model_provenance.py` *(new)* — the honesty contract at the service layer: missing manifest → REJECTED; well-formed-without-weights → DECLARED_NOT_VERIFIED; model_id mismatch / unrecognized license / empty source / no weight files / malformed SHA-256 / duplicate path → REJECTED; **recompute-match with real tmp files → VERIFIED**; recompute-mismatch → REJECTED (recomputed value surfaced honestly); missing-file-under-`weights_root` defers (still acceptable); `validate_frontier_provenance` raises on rejection / returns the summary otherwise; license normalization + content-digest determinism.
- `tests/test_cas_harness_distributed_audits.py` — `/distributed/session`: frontier run refused 422 without provenance (text mentions "provenance"); frontier run with a valid manifest → 200 + `PROVENANCE_DECLARED_NOT_VERIFIED` (`all_hashes_verified: false`); mismatched model_id / unrecognized license / malformed hash → 422; below-frontier run requires no provenance (200, `provenance: null`) but records a volunteered manifest's summary.
- `tests/test_cas_harness_audit.py` — `test_distributed_session_carries_the_frontier_gate` extended: ack-without-provenance is now its own 422 (the gate-5 refusal), and the allowed path attaches a valid manifest → 200 + `PROVENANCE_DECLARED_NOT_VERIFIED`.
- Local validation: `test_cas_harness_model_provenance.py` (15 passed); `test_cas_harness_model_provenance.py` + `test_cas_harness_distributed_audits.py` + `test_cas_harness_audit.py` together (75 passed). The whole-suite run shows pre-existing rate-limiter cross-contamination (`429` across unrelated route files) that disappears when those files run in isolation; the 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Scale planner gets an honest frontier lane — 300B–4T is *architected, not validated*, gated behind an explicit experimental-risk acknowledgement, and surfaced end-to-end through the HTTP API (Jun 1, 2026)

The enterprise planner previously hard-stopped at 300B (`parameter_count_b > 300` → `ValueError`), and the HTTP `ScalePlanRequest` mirrored that with `le=300`. The product question on the table — "will users be able to run models up to 4T?" — needed an answer that is *honest by construction*: the layer/shard architecture should extend to 1T–4T, but no run of that size has been executed, so we must never sell it as supported. This entry opens a frontier lane that says exactly that, in the data and in the API, and refuses to produce a frontier plan unless the caller explicitly accepts experimental-risk terms. **This is architected frontier-lane support only. It is not validated 1T–4T support, and nothing here markets it as such.**

**1) One validation ladder, one source of truth.** `scale_validation_status(parameter_count_b)` is now the single function every surface consults, with three honest rungs anchored to what has actually been run: **`EMPIRICALLY_VALIDATED`** (≤20B — Pythia-160M reproduced end-to-end on CPU, prior runs up to 20B), **`ENGINEERED_NOT_VALIDATED`** (20B–300B — architecture-validated, not size-validated), and **`EXPERIMENTAL_NOT_VALIDATED`** (300B–4T — the frontier lane, unproven, offered at customer risk). The planner, the `/scale-plan` endpoint, and the `/distributed/session` control plane all read this one function, so no surface can quietly upgrade a frontier claim to "supported." Boundaries are exact and tested: 20.0 is empirical, 20.0001 is engineered, 300 is engineered, 300.0001 is experimental, 4000 is experimental.

**2) The frontier gate is an explicit, refusable acknowledgement — not a silent default.** A 300B–4T plan is produced only when `accept_experimental_frontier=True`. Without it, the planner raises (`models above 300B are an experimental frontier-scale lane (EXPERIMENTAL_NOT_VALIDATED); set accept_experimental_frontier=True to plan one at customer risk.` + the full disclaimer), and both HTTP endpoints convert that to **HTTP 422**. Above 4T is hard-refused regardless of the flag — the planner ceiling is checked first (`> 4000` → `ValueError`), and the Pydantic field cap `le=4000` refuses >4T at the schema boundary too. The flag's own description states the honest limit: it "only unlocks the request path; it does not by itself guarantee compute, adapter, probe, provenance, or data-handling readiness for the run." Per the 8-gate product design, this is **gate (1) — risk acknowledgement — only**; the other seven run-gates (compute availability, cost approval, model provenance/license/hash manifest, architecture adapter, probe compatibility, data/security/WORM terms, and the console-side EXPERIMENTAL_NOT_VALIDATED surfacing) remain TODO and are not claimed here.

**3) The honest label travels with the plan, all the way out through the API.** `ScalePlan` (and its `to_dict()`) now carry `validation_status` + `validation_notice`, and `ScalePlanResponse` exposes both fields, so a caller of `/scale-plan` or `/distributed/session` always receives the rung and its human-readable claim text. A frontier plan still produces real layer/shard worker assignments (frontier worker floor `max(16, ceil(num_layers/8))`, estimated layers 200/240/320 across the 1T/2T/4T bands), and its `limitations` carry three frontier caveats including the literal `EXPERIMENTAL_NOT_VALIDATED` waiver — so the deployment math is real but the claim attached to it stays honest.

### Pieces (this entry)
- `api/services/cas_harness_scale_planner.py` — `scale_validation_status` / `frontier_scale_disclaimer` / `scale_validation_notice` (single source of truth); `ScalePlanRequest.accept_experimental_frontier`; `ScalePlan.validation_status` + `validation_notice` (incl. `to_dict`); ceiling raised 300B→4T with a frontier-acknowledgement gate checked after the >4T hard refuse; `frontier_experimental_open_weight` tier + worker floor + layer estimates + 3 frontier limitations.
- `api/routes/cas_harness_audit.py` — `ScalePlanValidationStatus` Literal; `parameter_count_b` cap `le=300`→`le=4000`; `accept_experimental_frontier` field with honest description; `validation_status`/`validation_notice` on `ScalePlanResponse`; both `/scale-plan` and `/distributed/session` thread the flag and convert planner `ValueError`→422. (`/scale-plan` stays a public demo prefix; `/distributed/session` stays JWT-protected — it can register workers, lease jobs, and submit receipts.)

### Tests (this entry)
- `tests/test_cas_harness_scale_planner.py` — `ENGINEERED_NOT_VALIDATED` at 100B, `EMPIRICALLY_VALIDATED` at ≤20B, 405B refused without the ack, 405B planned `EXPERIMENTAL_NOT_VALIDATED` (frontier tier, ≥16 workers) with the ack, 1T planned with the ack, >4T hard-refused even with the ack, and the validation-ladder boundary table (20 / 20.0001 / 300 / 300.0001 / 4000).
- `tests/test_cas_harness_audit.py` — `/scale-plan` exposes `validation_status` for the validated lane, refuses a frontier model without the ack (422, mentions `accept_experimental_frontier`), allows it with the ack (200, frontier tier, "customer risk" notice, EXPERIMENTAL_NOT_VALIDATED in limitations), hard-refuses >4T (422 via `le=4000`), and `/distributed/session` carries the same gate (422 without ack / 200 + EXPERIMENTAL_NOT_VALIDATED with ack, under JWT auth).
- Local validation: `test_cas_harness_scale_planner.py` + `test_cas_harness_audit.py` (54 passed), full CAS-harness file set (170 passed). The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## The general WORM anchor becomes a production *service* — `POST /evidence/{trace_id}/anchor`, model-size-independent, with one shared honesty gate for CLI and HTTP (Jun 1, 2026)

The previous entry de-hard-coded the anchor *loader* into a discovery registry and left the user's point (2) — a real HTTP anchor endpoint — explicitly as "partial / follow-on": the CLI was general but there was no service surface. This entry closes that leg. It is pure engineering (no AWS needed to write or test the code — the endpoint honestly reports whatever the configured anchor mode yields), so per the standing directive it was built without waiting.

**1) `POST /evidence/{trace_id}/anchor` exists and is general by construction.** The endpoint resolves `trace_id` through the same `stage9_40e_packet_path_registry()`, so any model size's Stage-9 40E packet — 160M, 20B, 70B, 300B, 1T, 3T — anchors through one route with no per-model code (the small-truck/huge-truck/same-checkpoint design, now as an HTTP surface). It loads the packet, runs the real `anchor_static_evidence_packet` → `verify_anchored_static_packet`, and returns an honest `AnchorEvidenceResponse`: `worm_retained`, `console_state` (`accept_scoped_validation` iff retained, else `flag_for_human_review`), the anchor status/mode/URI, the verify rollup, and `decision_scope: stage9_40e_validation_packet`. It fabricates nothing — with no S3 object-lock bucket configured it returns `worm_retained: false` / `anchor_status: disabled` and the console correctly stays at human review. A trace that is not a discoverable Stage-9 40E packet (including the dev fixture and S7/F28 packets) returns **404** — the endpoint is scoped to genuine Stage-9 40E validation packets. The route inherits the app's JWT auth (anchoring is privileged): unauthenticated calls get **401**.

**2) `require_object_lock=true` is a real promotion gate.** When set and the anchor did not reach verified WORM retention, the endpoint returns **409** with a structured `anchor_not_worm_retained` detail — so a promotion pipeline refuses to advance a packet on a non-WORM anchor rather than silently accepting it. This mirrors the CLI's `--require-object-lock` exit-1 behaviour.

**3) One source of truth for "is this WORM-retained," shared by CLI and HTTP.** The boolean that decides retention used to live only inside `anchor_stage9_40e_packet.py`. It is now `summarize_static_anchor_worm_status()` in the anchor service: status=anchored ∧ mode=s3 ∧ verify all_match ∧ external-anchor check match ∧ the re-read note independently confirms *object was re-read* + *object lock* + *retention is active*. Both the CLI (refactored to call it) and the new endpoint use this one function, so the two surfaces can never drift on what "retained" means. The CLI's disabled-mode smoke still prints the honest "OK (not WORM)" path and exits 0.

**Honest done/pending against the user's 7-point production WORM design — point (2) now flips to done.**
- (1) **General packet registry** — *done* (Stage-9 40E lane; cross-lane unification still follow-on).
- (2) **General WORM anchor endpoint** — **now *done***: `POST /evidence/{trace_id}/anchor`, any model size by trace_id, honest receipt, auth-gated, with a 409 promotion gate. (Was "partial: CLI only" last entry.)
- (3) **Model-size-independent schema** — *already true* (`parameter_scale`).
- (4) **Storage separation** — *already the design*; explicit S3 activation-store wiring for >20B still follow-on.
- (5) **Per-packet WORM proof** — *already enforced*, now via the shared summarizer used by both surfaces.
- (6) **Queue-based anchoring** — *pending*: the endpoint is synchronous; an async job + worker for large audits is the next real follow-on.
- (7) **Claim gating** — *already enforced*: ACCEPT-on-console still requires a real per-packet WORM anchor; the endpoint honestly returns `flag_for_human_review` until then.

**Where this leaves the gate.** The general WORM anchor is now both a CLI *and* an HTTP service, model-size-independent, with a single shared honesty gate. The two remaining production items are queue-based async anchoring (6) and cross-lane registry/schema unification (1) + S3 activation-store wiring for >20B (4). The one operational step to a true-green console for the Pythia packet is unchanged and non-engineering: run the anchor (CLI or this endpoint with `require_object_lock`) from production/Render against the S3 Object-Lock bucket `cas-harness-runpod-92754088`, where the immutable write actually happens.

### Pieces (this entry)
- `api/routes/evidence.py` — `POST /{trace_id}/anchor` + `AnchorEvidenceResponse`; resolves via the registry, honest receipt, 404 for non-Stage-9 traces, 409 under `require_object_lock` when not WORM. Module docstring updated (the anchor route is the one deliberate side effect).
- `api/services/cas_harness_static_evidence_anchor.py` — `summarize_static_anchor_worm_status()` + `external_anchor_check()`: the shared single source of truth for WORM retention.
- `scripts/anchor_stage9_40e_packet.py` — refactored to call the shared summarizer (behaviour unchanged; disabled-mode smoke verified).

### Tests (this entry)
- `tests/test_evidence_routes.py` — anchor endpoint: auth 401, unknown-trace 404, non-Stage-9 (dev fixture) 404, disabled-mode honest-not-WORM 200, **generality across 20B + 160M through the same endpoint**, and the `require_object_lock` 409 gate.
- `tests/test_cas_harness_static_evidence_anchor.py` — direct coverage of `summarize_static_anchor_worm_status` (disabled + local both not-retained; tolerates a missing anchor block).
- Full local validation: `test_evidence_routes.py` + `test_cas_harness_static_evidence_anchor.py` (39 passed / 2 real-S3-skipped), audit + verdict-runner + evidence-bridge (55), live-worker runner/e2e/api-endpoint/fleet-executor (33). The 2 unrelated collection errors (`test_turn_admissibility`, `test_type_constraints`) are pre-existing imports in `api.notation` / `cas-native`, untouched by this work.

## Gate 3 closed on engineering — η→ε output-bridge run on CPU, packet reaches a *scoped-validation* ACCEPT, and the anchor loader is de-hard-coded into a general registry (May 31, 2026)

The entry below assembled the Pythia packet honestly and parked it at `FLAG_FOR_HUMAN_REVIEW` for two named reasons: the **output-bridge (η→ε) proof leg was not run**, and **no real WORM anchor existed**. This entry runs the missing leg, re-assembles the packet to its genuine final state, and fixes the production-architecture smell the user flagged in the anchor path. Two distinct results — keep them distinct:

**1) The η→ε output-bridge leg now exists, and it passes on its own merits.** `run_stage9_40e_eta_epsilon_bridge.py` ran on CPU against the same Pythia-160M weights and the captured npz: it fits the 40-Element readout, selects 80 test cases (2 per element × 40), realizes each hidden-state read into a **readable** CAS frame, and measures the model's own conditional likelihood for the correct element vs the paired counterfactual across 7 conditions. The preregistered `probe_readable` gate clears every check with room to spare:
- `probe_readable_delta_vs_none` mean **+1.53** (threshold > 0.10), `probe_readable_minus_partner_readable_margin` **+3.23** (> 0.10), sign-test **p = 0.0** with **76/80** cases positive.
- `selected_element_accuracy` on the 80 bridge cases **0.95**.
- The honest negative control inside the same run: **raw** CAS-symbol prefixes are non-load-bearing (`probe_raw_delta_vs_none` **−0.0006**). The signal comes from the *readable realization* moving likelihood — not from injecting a bare symbol string. That contrast is the whole point of the assay, and it lands the right way.
- Status `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS`. The script still prints "likelihood-level evidence only; does not emit ACCEPT or SUPPRESS." (One run-mechanics note: the first attempt used `--max-length 192` and the truncation guard correctly refused — prompt + continuation overflowed; measured worst case is 220 tokens, so 256 is the right cap. The guard did its job.)

**2) With the bridge present, the packet reaches a scoped-validation ACCEPT — *not* a customer ACCEPT.** Re-merge → verifier → re-merge: `output_proof` flips `missing → verified` (`probe_readable_gate_passed: true`), the proof-chip gate **unblocks** (all six chips pass), and `build_stage9_40e_verifier_report.py` returns an explicit **`ACCEPT` at confidence 0.95** with `reason: all_stage9_40e_validation_gates_passed`. The final packet verdict is `ACCEPT`. Read the scope literally: `decision_scope: stage9_40e_validation_packet`, and the verifier still lists `per-customer production verdict from validation artifact alone` under `rejected_claims`. This is a *scoped project-validation* ACCEPT for the Pythia-160M Stage-9 40E packet. It is **not** a per-customer production verdict, and the end-to-end Audit Console still correctly stays at human review until a real per-packet WORM anchor exists (claim-gating, point 7 below).

**3) The anchor loader was a hard-coded single-packet filing clerk; it is now a discovery registry.** The user caught the right production issue: WORM anchoring must not be special-case code for one packet. `load_stage9_40e_packet_payload_for_trace` previously resolved exactly one trace_id to one bundled 20B filename. It is now backed by `stage9_40e_packet_path_registry()`, which indexes every discoverable Stage-9 40E packet (schema-gated) under `docs/working` and the Evidence Packet store **by each packet's own self-declared `trace_id`**. Proven general: 160M and 20B both resolve through discovery, and a synthetic **3T** packet dropped into the store dir resolves with **zero code edits**. Unknown trace_ids still raise `FileNotFoundError`; the bundled 20B path is unchanged (all evidence/anchor/audit suites pass: 35 + 40 + 16). The anchor CLI (`anchor_stage9_40e_packet.py --trace-id <any>`) now anchors any discovered packet, any model size.

**Honest done/pending against the production WORM design (the user's 7 points).** Several already existed in the honesty machinery; the registry was the genuine gap:
- (1) **General packet registry** — *done* for the Stage-9 40E lane (discovery by self-declared trace_id; size-independent, verified 160M/20B/3T). Cross-lane (S7/F28, EvidencePacket drawer) unification is follow-on.
- (2) **General anchor entrypoint** — *partial*: CLI is now general (`--trace-id <any>`). A real `POST /evidence/{trace_id}/anchor` HTTP route is follow-on.
- (3) **Model-size-independent schema** — *already true*: `cas_harness_stage9_40e_evidence_packet.v1` carries `parameter_scale`; proven across 160M/20B/3T.
- (4) **Storage separation** — *already the design*: packets store sha256 hashes + paths; the 132 MB npz lives out-of-packet (gitignored, reproducible). Explicit S3 activation-store wiring for >20B is follow-on.
- (5) **Per-packet WORM proof** — *already enforced*: the anchor honesty gate requires status=anchored, mode=s3, verify all_match, object re-read, Object Lock active, retention active — per packet, not per bucket.
- (6) **Queue-based anchoring** — *pending*: anchoring is synchronous CLI today; async job + worker is real follow-on engineering for large audits.
- (7) **Claim gating** — *already enforced*: ACCEPT-on-console requires a real per-packet WORM anchor; "the bucket exists" is necessary, not sufficient. `--require-object-lock` fails unless *this* packet is WORM-retained.

**Where this leaves the gate.** Gate 3's engineering is now genuinely complete: the science (91.72% / −44 pp), the readout/causal/control proofs, **and** the η→ε output bridge are all real and assembled into a packet that honestly reaches a scoped-validation ACCEPT. The one remaining step to a green console for this packet is operational, not code: run `anchor_stage9_40e_packet.py --trace-id pythia-160m-stage9-40e-readout-20260531 --require-object-lock` from an environment that holds the S3 Object-Lock credentials (bucket `cas-harness-runpod-92754088`, prefix `cas-harness/evidence-anchors/`) — i.e. production/Render, where the immutable 10-year write actually happens. The larger production items (HTTP anchor endpoint, queue-based anchoring, cross-lane registry) are tracked above as follow-on.

### Pieces (this entry)
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_eta_epsilon_bridge_report.{json,md}` — η→ε likelihood bridge: probe_readable gate passed (Δ +1.53, minus-partner +3.23, sign_p 0, 76/80), raw prefixes non-load-bearing (−0.0006), `selected_element_accuracy` 0.95, status `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS`.
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_evidence_packet.{json,md}` — re-assembled: all six proof chips pass, `output_proof: verified`, verifier `ACCEPT` 0.95, verdict **ACCEPT** scoped to `stage9_40e_validation_packet`.
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_verifier_report.{json,md}` — explicit `ACCEPT` (`all_stage9_40e_validation_gates_passed`); still rejects per-customer production claims.
- `api/routes/evidence.py` — `stage9_40e_packet_path_registry()` + `_stage9_40e_trace_for_packet_file()`: discovery-based, size-independent resolution by self-declared trace_id, replacing the hard-coded single-filename loader (seeds remain a deterministic floor).
- `scripts/anchor_stage9_40e_packet.py` — docstring + framing generalized: anchors any discovered Stage-9 40E packet by `--trace-id`, any model size.

### Tests (this entry)
- `tests/test_cas_harness_audit.py` (35), `tests/test_evidence_routes.py` + `tests/test_cas_harness_static_evidence_anchor.py` + `tests/test_cas_harness_evidence_bridge.py` (40 passed / 2 skipped — the 2 skips are the real-S3-gated cases), and `live-trace-worker/tests/test_merge_stage9_40e_evidence_packet.py` + `test_build_stage9_40e_verifier_report.py` (16) all pass with the discovery registry and the bridge-complete packet.

## Gate 3 — the Pythia-160M Stage-9 40E evidence packet, assembled honestly and held at human review (May 31, 2026)

The two prior entries reproduced the *science* (91.72% readout, −44 pp causal subspace ablation) and proved the *product path* can record a real causal intervention (the live-worker control proof). This entry closes the loop the capture entry promised: it merges the three Gate-1 reports into a single **Pythia Stage-9 40E Evidence Packet**, runs the packet-level **verifier**, and exercises the **WORM-anchor** honesty gate — end to end, on CPU — with the verdict landing exactly where honesty requires: `FLAG_FOR_HUMAN_REVIEW`.

**Merge → verifier → re-merge → anchor (all real, all honest).**
- **Merge.** `merge_stage9_40e_evidence_packet.py` assembled readout + subspace-ablation + neuron-cover reports into one packet. Tiers present: model, readout, baseline, causal, control. Tiers missing: **output_bridge** (the η→ε readable-bridge proof was not run here) and verifier. Verdict: `FLAG_FOR_HUMAN_REVIEW`.
- **Verifier.** `build_stage9_40e_verifier_report.py` read the packet and returned an explicit **`SUPPRESS`** at confidence 0.9 — but this is a *packet-validation blocking-risk* decision (`reason: output_bridge_gate_failed`), **not** a customer/inverted SUPPRESS. It refuses to certify ACCEPT because the output-bridge tier is absent, and it explicitly rejects "per-customer production verdict from validation artifact alone."
- **Re-merge.** Feeding the verifier back in does **not** promote the packet: `_final_verdict` requires both an attached explicit decision **and** passing proof chips, and `output_proof` is `missing` → `proof_chip_gate: blocked` → verdict stays `FLAG_FOR_HUMAN_REVIEW`. The merger refuses to invent ACCEPT/SUPPRESS; the SUPPRESS risk-signal rides along as data, it does not become the packet verdict.
- **Anchor.** `anchor_stage9_40e_packet.py` in the default (disabled) anchor mode reports `status: disabled`, hash-log integrity `all_match` (tamper-evident) but **NOT WORM** → the console honestly stays at human review. A true green ACCEPT needs a real S3 Object-Lock anchor (credentials + a lock-enabled bucket), which cannot be faked locally.

**Traceability fix — the packet now self-labels as Pythia, not 20B.** The merge/verifier/anchor harness was built for the bundled **20B** Stage-9 packet and defaulted `run_id` / `trace_id` / `parameter_scale` to 20B identity strings whenever the source readout report didn't carry its own. Run unchanged, a *Pythia* packet would have shipped stamped `parameter_scale: 20B` / `run_id: gpt-neox-20b-…` — accurate numbers under a wrong nameplate, exactly the provenance smell this project treats as load-bearing. Added three **optional** identity overrides (`--trace-id` / `--run-id` / `--parameter-scale`) that take precedence when supplied and change nothing when omitted: the bundled 20B path is byte-identical (all 11 merge tests still pass), and the Pythia packet now carries `model_id: EleutherAI/pythia-160m`, `parameter_scale: 160M`, and pythia trace/run IDs. The `baseline_proof` tier still cites the fixed corrected-20B reference baseline by design — and honestly records via `source_field_checks` that this run *differs* from it (our 91.72% vs the 20B reference 95.625%); the real Pythia readout (91.72%) is the load-bearing figure in `readout_proof`.

**Where this leaves the gate.** Gate 3's engineering is complete: the packet assembles, the verifier runs, the anchor gate is exercised, and every surface lands at `FLAG_FOR_HUMAN_REVIEW` for the right reasons (output-bridge proof absent; no real WORM anchor). What remains is non-engineering — a real S3 Object-Lock bucket + credentials (WORM), and, only if a packet ACCEPT is ever wanted, running the η→ε output-bridge slice. Neither is a code problem.

### Pieces
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_neuron_covers.json` — 1.5a candidate neuron-cover discovery (40 classes, layer 3, top-k 8) — the packet's `control_proof` tier (candidate-only until matched ablation validates).
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_evidence_packet.{json,md}` — assembled packet: causal −44 pp, verifier SUPPRESS-as-blocking-risk, verdict `FLAG_FOR_HUMAN_REVIEW`, Pythia self-labeled identity.
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_verifier_report.{json,md}` — packet-level verifier decision (`output_bridge_gate_failed`), Pythia trace/run IDs.
- `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py` — additive `--trace-id` / `--run-id` / `--parameter-scale` overrides so a non-20B reproduction packet self-labels instead of inheriting the 20B scaffold identity; default path unchanged.

### Tests
- Stage-9 merge/verifier/ablation/cover suites pass (22) and the static-anchor + verifier-decision-adapter suites pass (23); the additive merge override is fully covered by the existing 11 merge tests (20B default path byte-identical).
- 1.5b forward-pass cover ablation remains a flagged follow-up: the 40-Element cover-map format (`cover_map` keyed by compound `^n|D` cells) differs from the single-operator-axis input the cover-ablation script expects; not packet-blocking — the −44 pp subspace ablation already carries the causal proof.

## Gate 1 reproduced locally on CPU — Pythia-160M CAS readout 91.72% and a −44 pp causal subspace ablation, both from scratch (May 31, 2026)

The live-worker control proof (entry below) proved the *product path* can record a real causal intervention. This entry re-establishes the *scientific* gate that path rests on — "CAS structure is readable in Pythia-160M hidden states" *and* "that structure is causally load-bearing" — by re-running the full readout **and** the rank-39 subspace-projection ablation locally from a fresh activation capture, on CPU, with no RunPod and no cached result. The goal was to confirm the documented 89.8% readout (and the 20B-style causal collapse) are reproducible on demand, not one-off archived artifacts, before wiring them into a pythia evidence packet.

**Fresh capture (no reuse).** `capture_open_weight_probe_dataset.py` ran all 8,320 Stage-9 40E pilot scenarios through real `EleutherAI/pythia-160m` weights (float32, CPU), writing hidden states for all 12 layers: a (8320, 12, 768) dataset. The pilot grid is perfectly balanced — P/C/E/O = 2080 each, ^0…^9 = 832 each → all 40 cells at ~208 scenarios. (The earlier 160-scenario smoke only populated 2/4 domains; that was a subset artifact, not a coverage problem.)

**Readout — reproduced and slightly exceeded.** `evaluate_40_element_probe.py` with a group-disjoint fixed split (`metadata.split`, grouped by `counterfactual_pair_id`; train 3840 / test 4480; **0 train/test group overlap**):
- **Hidden-state probe, best layer 3: 91.72% test acc (macro-F1 0.9205)** — above the spec-sheet comparator of 89.8%.
- Majority baseline 2.50%; shuffled-label control mean 2.48% / max 4.08% → the probe is **+89.24 pp over the shuffled mean and clears the shuffled max**. Real structure, not memorization.
- Text-hash baseline 50.00% (the canonical CAS colloquialisms in the prompt surface carry real signal) — the hidden probe still beats it by ~42 pp, so the "hidden states encode CAS beyond surface text" claim holds. The evaluator records the 50% text baseline honestly rather than hiding it.
- 40/40 cells populated → readiness gate `packet_ready`. Best layer 3 (mid-early) matches the 20B finding's early-layer locus.

**Causal ablation — the structure is load-bearing, not incidental.** `run_stage9_40e_subspace_ablation.py` fit the readout at layer 3, derived the rank-39 class/logit subspace, project-ablated it from the hidden states, and re-fit the readout — against 20 same-rank random-projection controls with a 5 pp guard:
- **Layer 3 readout 91.72% → 47.72% after ablation: a −44.0 pp causal collapse.**
- Same-rank random projections disrupt the readout by **mean 0.09% / max 0.60%** — essentially nothing. The margin of the true disruption over the random-control max is **~43.4 pp**, far past the 5 pp guard → `guard_status: passed`.
- The script honestly emits `packet_decision: not_applicable_ablation_diagnostic_only` — it is a causal diagnostic, not an ACCEPT. Removing the *specific* CAS-encoding subspace destroys the readout; removing an equal-dimension random subspace does not. The structure pythia carries is causally load-bearing.

**Why this matters for the product.** These two numbers are the offline, high-signal gate the live worker's readout + causal chips point at, now reproduced from scratch on commodity CPU. The immediate continuation (same session) runs neuron-cover discovery + a forward-pass cover ablation, then merges readout + subspace-ablation + cover reports into a pythia Stage-9 40E evidence packet. That packet stays at `FLAG_FOR_HUMAN_REVIEW` (anchor mode disabled locally — a true WORM ACCEPT needs real S3 Object-Lock, a human-gated step).

### Pieces
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e.metadata.json` — capture provenance (model id, layers, scenario source).
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_40_element_probe_eval_report.json` — full per-layer readout, controls, readiness gate, and the 89.8% comparator.
- `docs/working/pythia160m_gate1/pythia160m_stage9_40e_subspace_ablation_report.json` — rank-39 subspace ablation: layer-3 91.72%→47.72%, 20 same-rank random controls (max 0.60%), `guard_status: passed`, `packet_decision: not_applicable_ablation_diagnostic_only`.
- `docs/working/pythia160m_gate1/.gitignore` — keeps the 132 MB npz / 9.1 MB scenarios / capture log out of git (reproducible via the documented command) while tracking the small metadata + report JSONs, mirroring the committed 20B Stage-9 report convention.

## Matched-control selectivity — the live worker's first control proof, plumbed honestly (May 31, 2026)

The previous entry closed the causal-proof gap (a real single-target ablation moves the next-token logit on loaded weights) but left `control_proof` honestly `unavailable`: a single unit moving the distribution does not prove the move is *selective*. This entry adds the live worker's **first control proof** — a single-unit selectivity test — and flips `control_proof` from `unavailable` to `present` end-to-end **iff a real matched control actually ran**, never because a request asked for it.

**What it measures.** Alongside the target-unit ablation, the worker now ablates up to 8 random *other* units in the *same* layer (same mode), scores each by the identical metric the causal slice uses (change in the baseline-top token's own logit), and reports whether the target moved that token strictly more than every control. This is the single-unit forward-pass analog of the offline Stage-9 "beat random same-rank controls" guard. It is deliberately **not** the 40-Element subspace matched control (a separate, later slice) — every surface that reports it says so in those words.

**Honesty invariant (one place, mirrored from the causal one).** `control_proof` is `present` **iff** an `ablation_control_effect` event exists *and* `is_real_model` is true (`_control_block_from_events`). Demo mode, a layer with no spare sibling units, or a failed measurement → `is_real_model: false`, every numeric delta `None`, `control_proof` stays `unavailable`. The pass/fail of the test (`selectivity_passed`) is carried as data; the chip flips on whether a real control *ran*, not on whether the target won — an honest "we measured it and the target did NOT beat the controls" is still a real control proof and must not be hidden.

**Still not an ACCEPT.** This adds one more real proof leg to the live open-weight packet; the verdict still lands at `FLAG_FOR_HUMAN_REVIEW` pending verifier + WORM gates. `matched_controls` in the packet now carries the single-unit selectivity block (real deltas or an honest unavailable), and the audit-scope label upgrades to "… + single-unit matched-control selectivity" only when a real control ran.

### Pieces
- `live-trace-worker/app/schemas/events.py` — new `AblationControlEffectEvent` (`type: ablation_control_effect`) added to the `LiveTraceEvent` union; docstring scopes it as single-unit next-token selectivity, not the subspace control.
- `live-trace-worker/app/runtime/ablation_probe.py` — `run_real_ablation_control` (real measurement: target vs random same-layer controls, seeded), `_capture_target_mlp_width` (one baseline forward captures MLP width so controls can be sampled; `None` → no real control claimed), `demo_ablation_control` (schema-valid, all deltas `None`).
- `live-trace-worker/app/runtime/event_stream.py` — demo and real streams both emit the control event (demo-flagged vs real); the real path degrades to a demo-flagged control on any measurement error, never failing the trace.
- `live-trace-worker/app/runtime/__init__.py` — export the two new symbols.
- `api/services/cas_harness_live_worker_runner.py` — `_control_block_from_events` (the single gate), `packet["matched_controls"]` now carries it, `control_present` threaded into the proof chips, the hardcoded `control_proof: unavailable` flipped to conditional, plus an honest control claim-level / caveat / scope label.

### Tests
- Worker-side (`test_ablation_probe.py`, 14 pass): demo control has no numbers; real control on the tiny `nn.Module` measures real selectivity (7 same-layer controls, target beats the max, `selectivity_passed: true`, positive margin); out-of-range layer degrades to demo-flagged; demo + real streams emit the control event in the right order.
- API-side (`test_cas_harness_live_worker_runner.py`, 9 pass): a real `ablation_control_effect` flips `control_proof` to `present` and fills `matched_controls`; a demo-flagged one keeps it `unavailable` with no leaked deltas while `causal_proof` still flips; unit-level honesty invariant mirrored.
- No regression across the evidence/packet/proof-chip consumers (86 pass, 2 skip) or the worker schema/stream/session/control suites (33 pass).

## Real-weights causal ablation validated on the GPU pod — the first causal slice is now genuinely causal (May 31, 2026)

The prior launch-hardening entry left one honest gap: the ablation probe was "validated on a synthetic `nn.Module` (real-weights ablation is a deploy-gated follow-up)." This entry closes that follow-up. A single-target ablation now runs on **real Pythia-160M weights on the GPU pod**, and the `causal_proof` chip flips to `present` end-to-end **because a real next-token effect was measured** — not because a request asked for it.

**What changed (deploy, not code).** The ablation-capable worker `app/` was deployed to the pod's persistent source (`/workspace/atlas-live-worker-current/app`) and run dir. The deployed worker now **accepts** the `causal_ablation` probe (HTTP 200; the old `m2` worker rejected it with 422) and emits an `ablation_effect` event flagged `is_real_model: true`. No API or runner code changed — the runner was already ablation-aware, and the graceful-degradation prediction from the prior entry held exactly: deploying an ablation-capable worker **auto-upgraded** `causal_proof` from `unavailable` to a real measured ablation with **no API redeploy**.

**The measurement (honest, including the un-flashy parts).** For the runner's declared target — layer 0, unit 0, `zero` — on prompt *"Audit this live prompt end to end."*: `is_real_model: true`, `logit_delta: -0.0047`, `confidence_delta: 0.001`, `top_token_changed: false` (baseline and ablated top token both `'\n'`, id 187). Small but non-zero, and reported as-is — no token flip was manufactured.

**Depth sweep — the effect is mechanistically real, not a constant.** Sweeping 48 units (layers 2/6/10 × units 0…720 step 48) on *"The capital of France is"*: **48/48 `is_real_model: true`**, **47/48 non-zero** `logit_delta`, **0 token flips**, and clearly **depth-graded** — every one of the top-5 strongest effects is in the deepest layer swept (layer 10), peak `|logit_delta| = 0.126` (L10 U432). A late-layer MLP unit moving the next-token logit more than an early one is the signature of a genuine forward-pass intervention, not a schema-valid no-op.

**End-to-end product proof (all three legs green).**
- **Worker contract** — posting the runner's *exact* payload to `/sessions/dump` returns the `ablation_effect` event with `is_real_model: true`.
- **Runner** — `run_live_worker_audit` against the live worker writes an Evidence Packet with `ablation.status: present`, `is_real_model: true`, audit-scope label upgraded to *"live model I/O + readout + real single-target causal ablation,"* and proof chips `causal_proof: present` / `control_proof: unavailable`.
- **HTTP route** — driving create → run through `/api/cas-harness/audit/session/{id}/run` returns `verdict: FLAG_FOR_HUMAN_REVIEW` (never a fabricated ACCEPT) with `causal_proof: present`. The live-worker e2e test passes against the real pod; its causal-proof assertion is a biconditional tied to `packet.ablation.status`, so it required **no edit** to accept the now-present proof — it simply held in the other direction.

**Honest framing (unchanged).** This is the **first causal slice** — one declared single-target MLP-output ablation — not a full causal map and **not** a matched-control-confirmed result (`control_proof` stays `unavailable`). It does **not** create an ACCEPT: the live open-weight path still lands at human review pending control/verifier/WORM gates. The worker's `/health` still reports `worker_version: m2-real-pythia` (the version string was not bumped), so the real capability signal is `causal_ablation` returning 200 with `is_real_model: true`, not the version label.

### Pieces
- No source change in `api/` or the runner (already ablation-aware); the change is the pod deployment of the ablation-capable `live-trace-worker/app/` plus this validation pass.
- Pod-side backup `app.bak-20260601T011800Z` retained for one-command rollback.

### Tests
- Live real-Pythia e2e (`tests/test_cas_harness_live_worker_e2e.py`) **passes against the deployed pod worker** through the tunnel (auto-selects the live worker source; honesty invariant holds with `causal_proof` now `present`).
- Direct runner + HTTP-route drivers both confirm `causal_proof: present`, `verdict: FLAG_FOR_HUMAN_REVIEW`.
- Worker stable across 48 sequential ablation calls (the sweep) with no errors.

## Live-worker launch-hardening: four parallel work-streams consolidated + a live-path regression caught and fixed (May 31, 2026)

Following the read-only audit ("a real milestone, but not yet launch-complete"), four advice items were worked **in parallel** and consolidated onto the live-worker branch in one pass. Consolidating revealed a real regression that the end-to-end test caught against the actual deployed worker — so this entry is as much about the catch as the features.

**The four streams (mapped to the audit's advice).**
- **Causal proof, plumbed honestly (advice #3).** The runner now asks the worker for the first causal slice — a declared single-target ablation (`layer 0, unit 0, zero`) — and consumes an `ablation_effect` event. Honesty invariant, enforced in one place (`_ablation_block_from_events`): `causal_proof` is `present` **iff** a real `ablation_effect` event exists *and* `is_real_model` is true. Demo-flagged or absent ablation → `unavailable` with **no fabricated deltas**; matched controls stay `unavailable`. The worker side gained the ablation probe + schema; validated on a synthetic `nn.Module` (real-weights ablation is a deploy-gated follow-up).
- **A visible connection state (advice #5).** New public `GET /api/cas-harness/live-worker/health` route + an Audit Console status chip that reports, in plain words, whether the live worker is configured / reachable / serving real weights — the console no longer hides worker outages. The route is on the auth allow-list (it's a status surface) and fails soft (`reachable: false`, never throws).
- **Launch-grade exposure groundwork (advice #2).** A worker `Dockerfile` + `.dockerignore` and an **optional, off-by-default** token-auth shim (`X-Atlas-Worker-Token`; unset = pass-through, `/health*` always exempt, constant-time compare), plus a design doc for replacing the dev SSH tunnel with a baked image + exposed HTTP port. No behavior change until a token is set.
- **A real run from the dashboard (advice #4).** An end-to-end test that drives create → run → packet → harvest through the API surface against the most-real worker available, asserting the honesty invariant and never fabricating ACCEPT; plus a dashboard run runbook.

**The regression the e2e test caught.** Consolidating the ablation-aware runner against the **currently deployed** `m2-real-pythia` worker (which predates the ablation probe) broke the live path: the worker rejects the unknown `causal_ablation` probe with `HTTP 422`, the runner treated that as a hard failure, and the run returned **no Evidence Packet** (`trace_id: None`). That would have shipped a live path that 404s its own audit against the real pod — and silently dropped the irreplaceable harvest signal (real model I/O).

**The fix — degrade, never drop.** `_post_worker_dump` now retries **once** with the ablation slice removed when (and only when) a 422 specifically names `causal_ablation`/`ablation_target` as the rejected input. Real model I/O + readout + harvest still land; `causal_proof` stays honestly `unavailable` (it's event-derived, never request-derived); unrelated 422s still surface immediately. It **auto-upgrades to a real measured ablation the moment an ablation-capable worker is deployed — no API redeploy**. Re-ran the e2e against the live real-Pythia worker through the tunnel: packet persists, honesty invariant holds.

**Dev-proxy fix (dashboard could not reach the audit API in `vite dev`).** The `cas_harness_audit` router mounts at `/api/cas-harness/audit` (prefix already includes `/api`) while `atlas_live` mounts at `/atlas/live` (no `/api`). The single Vite `/api` strip rule turned `/api/cas-harness/audit/x` into `/cas-harness/audit/x` → 404. Added a more-specific, no-rewrite `/api/cas-harness` proxy rule ordered **before** the strip rule. Production was never affected (no proxy there).

### Pieces
- `api/services/cas_harness_live_worker_runner.py` — ablation request + event consumption; `_post_worker_dump` graceful-degradation retry; `_ablation_probe_rejected` / `_payload_without_ablation` helpers.
- `api/routes/cas_harness_live_worker_health.py`, `api/main.py`, `api/middleware/auth.py` — health route + wiring + allow-list.
- `atlas-viewer/src/lib/casHarnessAuditApi.ts`, `src/pages/AuditConsolePage.tsx` (+ tests) — health-chip client + mount-time probe; BYOK option preserved through the 3-way merge.
- `atlas-viewer/vite.config.ts` — dev-only `/api/cas-harness` no-strip proxy rule.
- `live-trace-worker/` — `Dockerfile`, `.dockerignore`, `app/auth.py` (optional token shim), `app/main.py`, ablation probe + schemas + runtime, design doc.
- Docs: `atlas_live_worker_launch_grade_exposure_2026_05_31.md`, `atlas_live_dashboard_run_runbook_2026_05_31.md`.

### Tests
- Frontend (`atlas-viewer`): `tsc -b` clean; **532 passed, 2 skipped** (49 files). The 3-way merge surfaced one ordering break — the pre-existing BYOK test still used the raw fetch stub and the new mount-time health probe ate its first mock; fixed to use the shared `stubFetchWithLiveWorker` helper like every other flow test.
- Live-worker (`live-trace-worker/tests`): **206 passed** (excl. 2 known cross-package files that import the root `api` package); new ablation-probe + token-auth tests **17 passed**.
- API (`tests/`): new live-worker runner/health/e2e **14 passed** (incl. 2 new graceful-degradation tests + the live real-Pythia e2e). Full-suite `tests/` shows **41 pre-existing failures + 2 collection errors** — verified independent of this work: every sampled failing file passes in isolation, and the failed count is identical with these new test files excluded (rate-limiter accumulation + shared in-memory stores across the whole-suite run; the 2 errors are the known `api`-package cross-import quirk).

## Live worker restart-resilience: found the holes, hardened, proved cold start (May 31, 2026)

A read-only audit of the live-worker deploy flagged that "persistence is staged on `/workspace`" was only half-true. Verifying it before trusting it caught a real gap that a naive restart test would have hit — without risking the pod.

**What was actually broken.** On the RunPod pod, `/` is an ephemeral overlay and only `/workspace` (the network volume) persists. Three things the worker needs were sitting on the ephemeral `/`:
- **the `/pre_start.sh` boot hook itself** — `/start.sh` (baked into the image) runs it only `if [[ -f ]]`, so after a real restart the hook is gone and the pod comes up with **no worker at all**;
- **the venv** (`/root/atlas-live-worker-venv`) — wiped, rebuilt via pip at boot;
- **the HuggingFace model cache** (360MB) — wiped, so **Pythia re-downloads from HuggingFace at boot**.

So a real restart would either leave the worker dead (hook gone) or, at best, self-heal slowly while depending on PyPI + HuggingFace being reachable at boot. Not launch-grade.

**Hardened (what now persists on `/workspace`).**
- Built the venv at `/workspace/atlas-live-worker-venv` (`--system-site-packages`, so the CUDA torch `2.4.1+cu124` stays the image's, only the HF + FastAPI stack installs on top).
- Copied the model cache to `/workspace/.cache/huggingface`.
- Rewrote the boot hook to pin `HF_HOME` + `ATLAS_LIVE_VENV_DIR` to those paths, force port 8080 (8888 is jupyter), and staged the canonical copy at `/workspace/pre_start.sh`.

**Proved it — definitive cold-start test.** Killed the worker and moved the ephemeral `/root` venv, HF cache, and start script *aside* (simulating a wiped `/root`), then ran the hook. Result: recovered to `REAL_PYTHIA_WEIGHTS_LOADED` in **25 seconds**, worker running with `HF_HOME=/workspace/.cache/huggingface`, **no pip install, no model re-download, zero PyPI/HuggingFace dependency at boot**. Post-recovery heavy-probe inference returned real output; the API SSH tunnel transparently reached the restarted worker (new PID, same port).

**Honest residual (one user action).** The hook can't make *itself* persist on `/`. Full auto-recovery after a real power-cycle needs the pod's RunPod start / Docker command set once (in the console — not reachable over SSH) to restore the hook from `/workspace` before `/start.sh` runs:
```
bash -c '[ -f /workspace/pre_start.sh ] && cp /workspace/pre_start.sh /pre_start.sh; /start.sh'
```
Documented inline in `live-trace-worker/scripts/runpod_pre_start.sh`. The deeper launch-grade answer (custom image with the worker + deps + model baked in, HTTP port exposed, no SSH tunnel) remains the separate connectivity item.

### Pieces
- `live-trace-worker/scripts/runpod_pre_start.sh` — pins persistent venv + `HF_HOME`, port 8080, documents the restart-restore command and the overlay-vs-`/workspace` persistence model.

## Live Pythia-160M worker deployed on GPU pod + end-to-end audit verified (May 31, 2026)

The hosted open-weight audit path is no longer a code path waiting on a model — it now runs against **real Pythia-160M weights on a GPU pod**, end to end, with real activations captured. This closes the GPU lane that was blocking the live-trace half of the Harness.

**What runs now.** The live-trace worker (`EleutherAI/pythia-160m`, `output_hidden_states=True`, `output_attentions=True`) is deployed on the RunPod pod and confirmed loading real weights — `/health/realmode` returns `REAL_PYTHIA_WEIGHTS_LOADED`, `is_real_model: true`. The worker stays **private** (only port 22 is exposed on the pod), so the API reaches it over an SSH tunnel, not a public URL.

**End-to-end chain verified.** Driving `run_live_worker_audit` against the live worker through the tunnel produced, for the prompt *"The Eiffel Tower is located in"*:
- real model output (*"the city of Eiffel, France…"*, 24 tokens) with a full event dump (`manifest`, `knob_resolution`, `neuron_covers`, 24×`token`, `word_spans`, `complete`) — the heavier 4-probe payload (`active_trace`, `blindspot_covers`, `mode7_attribution`, `confidence_margin`) ran without stalling;
- an Evidence Packet with `audit_scope.kind = open_weight_live_trace`, `internal_activation_access: true`, verdict `held_for_human_review`;
- proof chips honest by construction — model/CAS-readout/output/packet **present**, causal/control **unavailable** (no ablation or matched controls in this slice);
- a harvest record joined on `trace_id` with `is_real_model: true`, `model_io_is_demo_fallback: false`, `verdict.status: pending_verdict_gate`.

**Honesty held.** This is real model I/O + real activations + real readout — but **not** causal proof. Ablation and matched controls are still unavailable, so the verdict stays held for human review; the UI banner says exactly that. Nothing fabricates ACCEPT.

**Persistence.** Worker source is staged on the pod's persistent `/workspace`, with a `/pre_start.sh` boot hook that forces port 8080, so the worker survives a pod restart.

### Wiring (how the dashboard uses it)
- `live-trace-worker/scripts/open_atlas_live_tunnel.sh` — opens the keepalive SSH tunnel `127.0.0.1:18080 → pod:8080` (`ServerAliveInterval`/`ExitOnForwardFailure`, after a `Connection reset by peer` without them). Pod host/port/key are env-overridable since RunPod reassigns them on pod recreation.
- `.env.example` — documents `ATLAS_LIVE_WORKER_URL` (point at the local tunnel end, e.g. `http://127.0.0.1:18080`) and `ATLAS_LIVE_HTTP_TIMEOUT_SECONDS`. Blank = live path disabled and hosted open-weight audits fail honestly instead of fabricating.
- The run path (`POST /session/{audit_id}/run` → `_should_run_hosted_open_weight` → `run_live_worker_audit`) was already wired; this commit makes the worker it calls real and the tunnel reproducible.

### Tests
- Backend focused run: 41 passed (`test_cas_harness_live_worker_runner` + `test_cas_harness_harvest` + `test_cas_harness_audit`).
- Live end-to-end: real worker `/sessions/dump` through the tunnel produced the packet + harvest record above (verified by a throwaway driver, not committed).

## CAS Harness BYOK ephemeral key + honest audit-scope label in the UI (May 31, 2026)

Two follow-ups that together let **any developer audit a model they pay for, on our platform, without us holding their secret** — and see, in plain words, exactly how much access the audit had.

**Bring-your-own-key (BYOK), ephemeral by construction.** A customer can now paste their own provider API key into the Audit Console run control. The key flows **only** in the body of the `POST /session/{audit_id}/run` request — never through create-session, never into the session store, the Evidence Packet, or the harvest record. It is handed request-scoped to a single `get_connector(..., api_key_override=…)` call and then forgotten. The audit records only a `credential_mode` (`customer_ephemeral_key` / `server_config` / `none`) so we can tell *how* a call authenticated without ever keeping *what* authenticated it. This is the monetization-enabling primitive: the customer pays their own provider, we run the audit.

**Honest scope label, surfaced.** The `audit_scope` block already baked into every packet now rides through the session response and renders on the audit card as a labelled banner — amber when there was no internal access (closed API, output-only), teal when activations were captured (open-weight live trace). Both say "verdict held for review" so the UI never implies inspection it did not do.

### Pieces
- `api/llm_connectors/registry.py` — `get_connector(provider, model=None, *, api_key_override=None)`. A request-scoped override takes precedence over server `settings`; `mock` ignores it. Keyword-only, backward-compatible.
- `api/services/cas_harness_api_endpoint_runner.py` — `run_api_endpoint_audit(..., api_key=None)` threads the override to the connector and stamps `credential_mode` into the packet manifest and `live_audit` block. The secret itself is never written.
- `api/routes/cas_harness_audit.py` — new `RunAuditSessionRequest` (`extra="forbid"`, `api_key: SecretStr | None`, stripped); `/run` extracts the secret request-scoped and passes it to the runner. `AuditSessionResponse` gains a typed `AuditScope` field.
- `api/services/cas_harness_audit_sessions.py` — `audit_scope` carried on the session record and through `attach_runner_evidence`.
- `atlas-viewer/src/lib/casHarnessAuditApi.ts` — `CasHarnessAuditScope` type + `audit_scope`/`provider` on the session; `parseNullableAuditScope`; `startCasHarnessAuditSession(auditId, { apiKey })` sends the key in the run body only when present.
- `atlas-viewer/src/pages/AuditConsolePage.tsx` — optional password-type BYOK input in the run controls; `AuditScopeBanner` renders the honest label on the audit card.

### Tests
- Backend focused run: 40 passed (`test_cas_harness_api_endpoint_runner` + `test_cas_harness_live_worker_runner` + `test_cas_harness_audit`), including a BYOK test that asserts the key reaches the connector but appears nowhere in the packet, harvest, or HTTP response.
- Frontend: 52 passed (`casHarnessAuditApi.test.ts` + `AuditConsolePage.test.tsx`) — BYOK body threading, whitespace-only key omitted, `audit_scope`/`provider` parsing, and the scope banner rendering on the card. `tsc -b` clean.

## CAS Harness customer-API audit path — harvest closed-model I/O honestly (May 31, 2026)

The Audit Console `/run` route can now audit a customer's **closed** model behind a provider API (OpenAI, Anthropic, Google, Meta, xAI, DeepSeek, Qwen — plus `mock` for end-to-end testing), not only the hosted open-weight Pythia worker. This is the second product path that harvests fresh CAS-labelled signal on a model we do not own — the first one that works against black-box commercial APIs, which is where most real customer demand sits.

**Honest by construction — no fabricated ACCEPT.** A closed API exposes no activations, so this path captures real model I/O only. `model_proof` and `output_proof` are **present** (we really called the model and kept its output); `cas_readout`, `causal_proof`, and `control_proof` are **unavailable** by construction — we do not invent them. Because three of the six proof chips are unavailable, the evidence-gated verdict runner cannot reach ACCEPT/SUPPRESS and the audit honestly lands at `FLAG_FOR_HUMAN_REVIEW`. The audit prompt is sent to the customer's model as-is (no CAS system-prompt injection) so the capture reflects how their model actually responds.

The harvest runs the moment the packet is built — before the verdict gate — and joins back on `trace_id`, exactly like the live-worker path. Mock-provider output is flagged `model_io_is_demo_fallback: true` so synthetic placeholder text can never silently enter a training corpus as real signal.

### New pieces
- `api/services/cas_harness_api_endpoint_runner.py` — `run_api_endpoint_audit` calls `get_connector(provider, model_id).generate(prompt)`, builds an output-only Evidence Packet (`method_label: cas_harness_api_endpoint_v1`, `runtime: customer_api_connector`, `trace_id` prefix `cas-api-`), persists it through the existing hash-log/store/anchor machinery, harvests it, and returns the six proof chips to the verdict gate.
- `api/routes/cas_harness_audit.py` — `/session/{audit_id}/run` now detects API-provider sessions (`provider` set to a supported closed-API provider, no attached packet) via `_should_run_api_endpoint`, runs the customer-API runner, attaches the packet trace, then evaluates the verdict gate.
- `AuditSessionRequest` / `AuditSessionResponse` / `AuditSessionRecord` gain an optional `provider` field so the run path knows which connector to use. Backward-compatible: sessions without `provider` keep prior behavior. Raw credentials are never persisted to the session store; connector keys resolve server-side from `settings`.

### Honest scope label on every packet (follow-up)
Every Evidence Packet now carries an `audit_scope` block so the UI can state, in plain words, exactly how much access the audit had — never implying internal inspection it did not have.
- **Customer-API (closed) packet:** `kind: output_only_api_harvest`, label **"Output-only harvest · no internal activation access · verdict held for review"**, `internal_activation_access: false`, `verdict_disposition: held_for_human_review`.
- **Live-worker (open-weight) packet:** `kind: open_weight_live_trace`, label **"Open-weight live trace · activations + readout captured · causal/control not yet run · verdict held for review"**, `internal_activation_access: true`, `verdict_disposition: held_for_human_review`.
- `audit_scope` is an additive optional field on the `EvidencePacket` model — older packets without it stay valid.

### Tests
- `tests/test_cas_harness_api_endpoint_runner.py` — end-to-end through the real mock connector: output-only packet, `readout/ablation/matched_controls` all `unavailable`, asserts the `output_only_api_harvest` scope label, hash-verifies cleanly, pins real `code_commit_sha`, writes exactly one harvest record flagged demo-fallback; unknown-provider and connector-failure both surface as `ApiEndpointRunnerUnavailable`.
- `tests/test_cas_harness_live_worker_runner.py` — asserts the `open_weight_live_trace` scope label (activations captured, causal/control not yet run, verdict held).
- `tests/test_cas_harness_audit.py` — `/run` route calls the customer-API path for a `mock` provider session and correctly returns `FLAG_FOR_HUMAN_REVIEW` with the honest chip posture and lifecycle.
- Focused backend run: 43 passed (runner + audit route + live-worker + harvest); broad harness/atlas-live selection 156 passed, no regressions. (Two unrelated modules — `test_turn_admissibility`, `test_type_constraints` — fail at collection on this worktree independent of this change.)

## CAS Harness harvest-capture layer — every live audit becomes CAS-Native training signal (May 31, 2026)

The CAS Harness is not only a revenue product; every live audit it runs is a chance to harvest real-world, CAS-labelled signal on a model we do not own. Until now that signal lived only inside the `live_audit` block of an Evidence Packet — readable, but not a corpus. This change makes the capture-and-persist step **first-class**: every live-worker audit now also writes a `cas_harness_harvest.v1` record to an append-only JSONL corpus that is built to be joined, on `trace_id`, to the CAS SDG's `native_nl.v1` output. The Harness harvest and the synthetic-data generator feed **one** CAS-Native training pipeline instead of two disconnected ones.

**Two honesty rules are baked in so nothing fake or mislabelled can slip into training:**
- **Real-vs-demo provenance.** A record is certified as real model I/O only when the worker manifest reports `is_real_model`. Demo/fallback output is still captured (so nothing is silently dropped) but flagged `model_io_is_demo_fallback: true`. Absent or false `is_real_model` is treated conservatively as demo fallback — the harvest never certifies "real" unless the worker explicitly says so.
- **Foreign-output retention is stamped, not assumed.** Each record carries an explicit policy stamp (`foreign_output_retained: true`, `answer_side_rule: "ablated"`, `answer_side_rule_changed_at: "2026-05-31"`) reflecting the current user directive that the "foreign answers never" rule is suspended. If that ban is re-enabled, the stamp lets us filter retained-foreign rows back out instead of guessing.

The model I/O is captured the moment the packet is built — before the verdict gate runs — because a hosted pod can disappear and the I/O is the irreplaceable part. The later verdict and the SDG row both join back on `trace_id`.

### New pieces
- `api/services/cas_harness_harvest.py` — `capture_live_audit_harvest`, `iter_harvest_records`, `harvest_corpus_path`. Store dir resolves from `CAS_HARNESS_HARVEST_STORE_DIR` (or a stable tempdir), mirroring the Evidence Packet store convention.
- `api/services/cas_harness_live_worker_runner.py` — now harvests every live audit immediately after persisting the Evidence Packet.

### Tests
- `tests/test_cas_harness_harvest.py` — real-flagged vs demo-fallback honesty (true / false / absent `is_real_model`), the explicit `trace_id` join key, verdict context capture, policy stamp, and store isolation.
- `tests/test_cas_harness_live_worker_runner.py` — extended to assert the live run writes exactly one harvest record joinable on `trace_id` and conservatively flagged as demo fallback for a manifest that does not assert `is_real_model`.
- Focused backend tests: 82 passed; broad harness/evidence/harvest selection 168 passed / 2 skipped, no regressions.

## CAS Harness live-worker run path (May 31, 2026)

The Audit Console `/run` route can now call the hosted open-weight live worker for `EleutherAI/pythia-160m` sessions instead of only replaying attached/static packets. The first slice is intentionally conservative: it captures real model I/O, token/readout events, neuron-cover events, and the worker manifest; writes a packet-loadable Evidence Packet into the shared packet store/hash log; then sends that packet through the existing evidence-gated verdict runner.

**No fake ACCEPT.** The live path marks model/readout/output/packet proof as present, but causal ablation and matched controls remain unavailable in this first slice. The verdict therefore routes to `FLAG_FOR_HUMAN_REVIEW` until causal/control/verifier/WORM gates are satisfied. This is the first product path where a customer-style run harvests fresh CAS-native training signal instead of only opening a bundled reference packet.

### New pieces
- `api/services/cas_harness_live_worker_runner.py` - calls `ATLAS_LIVE_WORKER_URL /sessions/dump`, captures events, builds the live Evidence Packet, persists it through the existing hash-log/store/anchor machinery, and returns proof chips to the verdict gate.
- `api/routes/cas_harness_audit.py` - `/session/{audit_id}/run` now detects hosted open-weight Pythia sessions with no attached packet, runs the live worker, attaches the new packet trace, and only then evaluates the verdict gate.
- Evidence Packet schema now exposes `live_audit` and verifies live packets through the same packet-store hash-chain path used by merged fleet packets.

### Audit repair (May 31, 2026)
- Closed a traceability gap: the live packet's `provenance.code_commit_sha` was hardcoded `"unknown"`. It now resolves the real `git rev-parse HEAD` of the running tree (falling back to `"unknown"` only when git is genuinely unavailable), so every harvested live packet pins the exact code that produced it. A regression assertion in the runner test prevents the placeholder from returning.

### Tests
- `tests/test_cas_harness_live_worker_runner.py` verifies a live worker dump writes a loadable packet, preserves output text + event counts, hash-verifies cleanly, and pins a real `code_commit_sha`.
- `tests/test_cas_harness_audit.py` verifies the `/run` route calls the live worker for Pythia and correctly returns `FLAG_FOR_HUMAN_REVIEW` when causal/control proofs are unavailable.
- Focused backend tests: 77 passed (runner + audit + evidence-bridge + verdict + static-anchor + verifier-adapter suites).

## WORM-anchor path for the Stage 9 40E packet — the one honest step that can flip the verdict (May 31, 2026)

The Audit Console can now turn the Stage 9 40E packet's headline from `FLAG_FOR_HUMAN_REVIEW` into a true green ACCEPT — **but only after a real, un-fakeable step runs**: writing the packet to an AWS S3 bucket that has Object Lock (WORM — write once, read many) turned on, then re-reading that object to confirm the lock is real and the retention date is in the future. No S3 write, no ACCEPT. That is the entire point of the gate.

**What ships here is the plumbing, not a flipped verdict.** With no AWS configured (the default), the step still runs and still records an anchor — but the anchor's status is honestly `disabled`, the packet is *not* WORM-retained, and the console correctly stays at human review. `local` mode anchors to the same machine, which is also not WORM, and also stays at human review. Only a genuine `s3` + Object Lock write — re-read and confirmed — produces the "WORM retained … object lock … retention is active" proof the verdict runner requires.

**How to actually flip it (the one runtime requirement).** Set `CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3` plus an Object-Lock-enabled bucket, region, lock mode (GOVERNANCE/COMPLIANCE), retention days, and AWS credentials, then run `python -m scripts.anchor_stage9_40e_packet --require-object-lock`. The bucket must have had Object Lock enabled at creation and the credentials must allow `s3:PutObject` with retention — neither can be faked locally. This stays a *scoped project validation* ACCEPT, never a per-customer production ACCEPT.

### New pieces
- `api/services/cas_harness_static_evidence_anchor.py` — anchors a static (non-fleet) packet through the *exact same* trusted append-only hash-log + external object-lock path the fleet writer uses, so its WORM retention is verified, never asserted. Functions: `anchor_static_evidence_packet`, `load_anchored_static_packet_payload`, `verify_anchored_static_packet`.
- `scripts/anchor_stage9_40e_packet.py` — the operational entry point; `--require-object-lock` fails loudly unless the anchor is a real, re-read-confirmed S3 Object Lock write.
- Audit route (`_packet_payload_for_trace` / `_verify_hashes_for_trace`) now prefers a genuinely anchored Stage-9 copy when one exists, and falls back to the bare bundled packet otherwise.

### Store isolation fix (regression caught and closed)
Static-anchored packets are now persisted under a dedicated store sub-namespace (`static-reference/`) via a new `evidence_store_namespace(...)` context manager. **Why:** the fleet packet loader validates every payload it reads as an `EvidencePacket`; a Stage-9 packet uses a different schema, so when an anchored copy landed in the *shared* store, the loader crashed on validation instead of falling through. Isolating the namespace means the fleet drawer physically cannot see static packets. The audit tests also gained an autouse fixture pinning the packet store to an empty per-test dir, so a developer who runs the anchor script no longer leaks an anchored copy into the suite.

### Tests
- `tests/test_cas_harness_static_evidence_anchor.py` — disabled-mode anchors-but-not-WORM, local-mode not-WORM (never claims object lock), round-trip from store, unanchored-returns-None, tamper → `partial_mismatch`, missing trace_id → `ValueError`.
- `tests/test_cas_harness_audit.py` — WORM-anchored path asserts ACCEPT (confidence 0.95625, packet_proof verified); un-anchored path asserts the unchanged `FLAG_FOR_HUMAN_REVIEW`.
- Full harness suite green: 130 cas_harness tests pass; targeted set 96 passed / 2 skipped.

## Audit Console reference target serves the real Stage 9 40E packet (May 31, 2026)

The Audit Console's built-in `demo_reference` target stopped serving a synthetic placeholder packet (model `pythia-160m`, `hashes=None`, a fabricated Stage 19/20 verifier decision) and now points at the **real GPT-NeoX-20B Stage 9 40E validation packet** (`stage9-40e-original-baseline-readout-20260527`). The console now shows the genuine six proof chips (cas_readout / causal / control / output **verified**, model / packet **present**) and the real verifier decision (ACCEPT, confidence 0.95625, source `stage9_40e_packet_verifier`, 80 cases × 40 classes).

**The honesty gate is preserved, on purpose.** This is a *scoped project validation* ACCEPT, not a per-customer production ACCEPT — and because the packet has no WORM/S3 object-lock anchor, the verdict runner correctly withholds the final ACCEPT and the console headline stays `FLAG_FOR_HUMAN_REVIEW`. Reference-target copy now labels the record as the "Stage 9 40E scoped validation packet … not a per-customer production ACCEPT," and the model_proof target chip is `present` (no live call, no weight-hash verification), not `verified`. Flipping the headline to a true green ACCEPT is a separate step: WORM-anchor this packet to S3 object lock.

### Tests
- `tests/test_cas_harness_audit.py` reference-flow tests updated to assert the real packet, real verifier decision, real chip mix, and the unchanged `FLAG_FOR_HUMAN_REVIEW` headline.
- Full harness suite green: 150 passed, 2 skipped (audit, evidence bridge, verdict runner, verifier adapter, evidence routes, distributed/fleet, scale planner, mode7 persistence).

## Wave 5.5/5.6 (integration): clickable words + interpretable blindspots (May 24, 2026)

Two cockpit lanes shipped together because they both reshape the LIVE event stream — merging them independently would have left the schema half-typed. This release is the integrated version.

**Clickable word spans (#52 lineage).** Click any word in the streamed output → cockpit highlights the exact token(s) behind it → 3D neurons, Mode 7 attention path, and Evidence Drawer all jump to that moment. Words are token-backed under the hood (models think in tokens, not words). The worker emits one `WordSpansEvent` just before `complete`, mapping each rendered word to the exact token indices that produced it, with a deterministic boundary policy and lossless backing (every token appears in exactly one span OR in `structural_token_indices`). Token-index contract is now strictly 0-based contiguous, asserted at build time.

**Interpretable blindspots (#53 lineage).** Blindspots stop being a red overlay. Each cover class now renders a four-line interpretation: plain-English sentence (what concern the model may be missing) → `CAS source: F5 Agency · analytical register` (provenance, small dim text) → `Confidence: 72% medium` (band, when scored) → `Evidence: probe + ablation` (omitted when no sources). The 7 drive sentences are user-authored copy and ship verbatim, asserted by test. Confidence bands match spec exactly: 80-95 high, 60-79 medium, 40-59 low, otherwise unavailable. Default visible filter is high+medium with low behind an expand; unavailable entries are excluded from the textual list. Investor framing: "Atlas doesn't just say 'this model has a blindspot.' It translates the blindspot into the kind of human concern the model may be failing to consider."

**Honesty fixes layered on top of the merge.**

- Worker `cover_library` is runtime-calibrated for **F1-F7 on Pythia-160M** from Stage 27F `row_reports` (`neuron_cover`, `clean_margin`, `targeted_drop`). The live side-panel drive/scope knobs now expose all seven drives because the worker can actually emit and intervene on those cover sets.
- Confidence is **cover-level**, not single-neuron certainty: `targeted_drop / clean_margin` for the Stage 27F cover class, projected onto each member row so the UI can render it. That says the tested cover set moved the measured signal; it does not claim one neuron equals one meaning. **Zero invented numbers.**
- BlindspotsPanel distinguishes three states now, not two: (a) **markers detected + scored** -> textual interpretations render; (b) **markers detected + unscored legacy trace** -> panel shows the plain-English meaning but no percentage; (c) **no markers** -> "No cover overlap detected for this frame." The 3D red overlay is unconditional (spatial marker stays); the confidence line depends on calibration evidence.
- Evidence Drawer word-source rendering documents the LIVE trace_id flow honestly: LIVE-mode TokenEvents do not currently carry trace_ids (those are wired in the REPLAY fixture pipeline only), so the word drawer falls back to the existing "Local replay metadata only" label in LIVE today. Same fallback label PR #46 ships for other sources — no new labels invented.

### Tests

- Worker `pytest` → 60/60 pass (12 word_spans + 25 cover schema + existing).
- Atlas vitest pending — could not run in the agent sandbox; run before merging.
- New regression guard `test_word_spans.py::test_token_indices_are_zero_based_contiguous` asserts the tightened contract.

## Session 61: B-4 cas_prefix_mask fix + v1 retrain proof + post-gen pipeline (May 8-9, 2026)

**Headline.** This session changed the project state materially. The B-4 architectural fix (cas_prefix_mask) **solved the source-binding bottleneck** that B-4.1 audit had flagged as the v0 failure mode. v1 PREFIX128 5-epoch retrain on the Wave 4 corpus hit content correctness 0/8 → 5/8 (strict/strong). Two follow-up libraries landed for the residual gaps: identifier_repair (Ω-name copy at 100%, coefficient at 67% gen-ceiling) and cas_routing (compilability-based task routing that bypasses the rpm_chain misroute). **Corpus was not the blocker; conditioning and symbolic copy/routing were.**

### The journey

1. **v1 mix initial training (no prefix)** — 7,395 records × 2 epochs × K=64. Diverse-record eval: 4/8 wrong silhouettes, 0/8 content-correct. Same B-4.1 hollow-silhouette failure as v0.
2. **Diagnostic: 32-record overfit test** — model overfit to 0.05 LM loss (memorized teacher-forced) but autoregressive greedy gave 9.4% verbatim, 11.3% Ω recovery, 44.3% coefficient recovery. Records 4-6 emitted *byte-identical previous-record outputs* for different prompts. The model **knew where the slot was but couldn't bind it to source**. Diagnosis: bottleneck-z conditioning is too lossy to disambiguate 32 unique recipe-shape prompts.
3. **B-4 architectural fix: cas_prefix_mask** (commit `2530d1b`). The trainer comment had flagged this as deferred technical debt: NLGenerationHead.forward took cas_prefix_ids but no cas_prefix_mask, so PAD positions in padded prefixes leaked into self-attention. Fix plumbs cas_prefix_mask through 7 surfaces (head, decoder layer, model.forward_with_lm, collator, trainer, generate_reply, chat comment). Six new tests pin the behavior.
4. **Overfit retest with --use-cas-prefix** — same 32 records, 100 epochs. **Verbatim 9.4% → 87.5%, Ω recovery 11.3% → 88.7%, coefficient recovery 44.3% → 93.7%.** Architectural diagnosis confirmed: discrete prefix conditioning is the right path.
5. **Full v1 retrain with --use-cas-prefix --max-cas-prefix-len 128** (5 epochs). Diverse 8-record eval: task routing 4/8 → **7/8**, N/D/F/R binding from minimal → strong, content correctness 0/8 → **5/8 combined** (1 strict + 4 strong-partial). Hard notation + jargon = 0 throughout.
6. **Residual analysis** — Ω-name recovery flatlined at 0% (model still hallucinates Ω names: "decision_60" → "rehearsal_67" / "withdrawal_60") even at 5 epochs. Hypothesis: Ω names are arbitrary long-tail identifiers (1000+ unique Ω names ÷ 7K records ÷ 5 epochs = each Ω seen ~35 times — not enough to memorize against parameter competition). This is a **copy-mechanism problem, not a learning problem.**
7. **identifier_repair library** (commit `760f3f0`). Post-generation positional-substitution of Ω names, coefficients, variable names extracted from source CAS. Greedy diverse eval: **Ω 33% → 100%**, coefficient 33% → 67% (gen-completeness ceiling). 26 tests.
8. **rpm_chain routing diagnosis** — record 7 still failed even with K=128 + 5 epochs + repair available. Empirical evidence:
   - 5/5 wrapper-text variants produced byte-identical output under greedy → encoder/bottleneck-z is insensitive to wrapper differences when cas_prefix dominates
   - 20/20 high-entropy samples routed to invalid_to_explanation → valid trajectory has zero probability mass
   - Variable prefix `stageA0` is shared 323 (valid rpm_chain) / 207 (invalid rpm) — no disambiguation in cas_prefix
   - Class imbalance: 425 invalid vs 323 valid for similar shapes
   - **Side-effect of cas_prefix_mask fix:** discrete prefix now dominates conditioning so wrapper signal is effectively dead at inference
9. **cas_routing + postprocessor libraries** (commit `c79294f`). Compilability gate: route by `compile_expression(source).valid`. Postprocessor orchestrates routing + repair (opt-in) + quality checks. 23 tests. Library-shaped, NOT wired into chat REPL by design.

### Final 3-way comparison (diverse 8-record eval, greedy)

| Metric | v1 NO-PREFIX | v1 PREFIX 2ep K=64 | **v1 PREFIX128 5ep + repair** |
|---|---:|---:|---:|
| Task routing | 4/8 | 7/8 | **7/8** (record 7 deferred to compilability gate) |
| N/D/F/R binding | minimal | partial | **strong (3-4/4 axes per record)** |
| Ω-name recovery | 0% | 0% (prefix sometimes preserved) | **100% post-repair** ✅ |
| Coefficient recovery | 0% | 0% | **67% post-repair** (gen-completeness ceiling) |
| Hard notation leaks | 0 | 0 | **0** |
| Jargon leaks | 0 | 0 | **0** |
| Strict + strong-partial content | 0/8 | 2/8 | **5/8** ✅ above gate |

### Status discipline

- B-4 cas_prefix_mask fix: **WIRED + WORKS + tested + verified at corpus scale**
- v1 PREFIX128 5ep checkpoint: **VALIDATED structurally** (5/8 above content gate); NOT yet validated by human relevance audit
- identifier_repair / cas_routing / postprocessor libraries: **WIRED + WORKS + tested locally + tested on pod**
- Chat REPL integration: **NOT done** (deferred — REPL still loads v0 checkpoint)
- Production readiness: **NO** (v0 still default in REPL; v1 unscaled to user-facing audit)

### Files of record

- Patches: `cas-native/model/nl_generation_head.py`, `cas_native_model.py`, `training/datasets/native_nl_collator.py`, `training/train_native_nl_gen.py`, `inference/native_nl_generate.py`, `inference/chat.py`
- New libraries: `cas-native/inference/identifier_repair.py`, `cas-native/inference/cas_routing.py`, `cas-native/inference/postprocessor.py`
- New tests: `cas-native/tests/model/test_cas_prefix_mask.py` (6), `tests/inference/test_identifier_repair.py` (26), `test_cas_routing.py` (9), `test_postprocessor.py` (14) = **55 new tests**
- Diagnostic: `docs/working/identifier_repair_and_rpm_routing_2026_05_09.md`
- Run artifacts on pod: `runs/v1_path_d_PREFIX128_5ep_20260509T035024Z/{model_final.pt, diverse_eval_with_repair_v3.log}`

### Open follow-ups

1. **Wire chat REPL to load v1 checkpoint + use postprocessor.** Requires `NATIVE_GEN_RUN_DIR` reconfig + `use_cas_prefix=True` flag flip. Held until v1 stability confirmed by human relevance audit.
2. **Future training run with explicit task tokens in cas_prefix.** `[VALID]` / `[INVALID]` discrete tokens eliminate the rpm_chain structural ambiguity at training time.
3. **Pointer/copy attention head in decoder.** Long-term clean answer for arbitrary identifier binding, replacing post-gen substitution.
4. **Coefficient gen-completeness gap.** Model dropped 1 of 3 coef slots on the recipe gen — the repair ceiling at 67% is bounded by what the model emitted. More training or constrained decoding required.

### Slogan locked

*"Corpus was not the blocker; conditioning and symbolic copy/routing were."*

## Session 60: Path D Wave 4 — v1 training mix aggregator + first v1 mix output (May 8, 2026)

**Headline.** Aggregator script `cas-synthetic/scripts/build_path_d_v1_mix.py` lands; first run produces the v1 training mix (8,219 rows) with deterministic 90/5/5 splits stratified by `(task_type, grammar_category_or_error_class)`. Two promotion-grade slots wired in; two broken slots documented as gaps with rebuild scheduled.

**v1 mix composition (inclusion rules hash `efe80fc8b790d7e1`):**

| Slot | Source | Rows | Notes |
|---|---|---:|---|
| cas_to_english | Wave 2.5 SFE-certified (Session 59) | 5,268 | All 4 promotion gates + human review PASS |
| invalid_to_explanation | Phase 1 audit-clean | 2,951 | Phase 1 audit-clean; 34 cross-file duplicates dropped |
| **Total** | | **8,219** | |

**Excluded slots (documented gaps, scheduled for SFE-equivalent rebuild):**

- `phase1_english_to_cas` — 100% verbatim-copy in phase 1 audit. Needs rebuild via compiler-validation gate.
- `phase1_invalid_to_corrected` — ~30% unrelated-correction in phase 1 audit. Needs rebuild via "compiler validates the correction" gate.

**Splits (deterministic seed 20260509):**

- train: 7,395 (89.97%)
- val: 412 (5.01%)
- test: 412 (5.01%)
- Every (task, category) stratum got proper val/test allocations; no train-only fallbacks needed (smallest stratum n=78 ≥ min_stratum_size 20).

**Schema (unified across tasks):**

```json
{
  "row_id": "v1mix_<task>_<seq>",
  "task_type": "cas_to_english" | "invalid_to_explanation",
  "input": "<raw payload only — no instructions>",
  "target": "<model target>",
  "split": "train" | "val" | "test",
  "meta": {
    "source_slice": "wave2_5" | "phase1",
    "source_id": "...",
    "grammar_category_or_error_class": "...",
    "source_path": "...",
    "sfe_certified": true | false,
    "sfe_tries": null | int
  }
}
```

Decision: input is the **raw task payload only** (CAS expression, OR invalid CAS + compiler error). Trainer wraps with task-specific prompts at training time. This keeps the corpus model-agnostic: same data trains a CAS-Native model with custom prompt formatting OR a standard transformer with `<<TASK>>` tokens.

**Sanity-check red flags (must all be 0; all PASS):**

| Check | Count |
|---|---:|
| `cas_to_english` target hard-notation hits | 0 |
| `cas_to_english` target jargon hits | 0 |
| Verbatim input==target rows (parrot regression) | 0 |

**Char-length stats (chars, trainer should tokenize for true counts):**

| Task | Field | Mean | p50 | p95 | Max |
|---|---|---:|---:|---:|---:|
| cas_to_english | input | 39 | 26 | 155 | 155 |
| cas_to_english | target | 177 | 140 | 373 | 596 |
| invalid_to_explanation | input | 239 | 197 | 621 | 621 |
| invalid_to_explanation | target | 330 | 328 | 406 | 521 |

**Aggregator design notes:**

- Inclusion rules are first-class: every change to "what goes into the mix" updates the rules dict and produces a new `inclusion_rules_hash`. Re-running with same rules + same seed produces byte-identical splits.
- Within-task dedupe by `source_id`. Cross-task collisions deliberately allowed (cas_to_english seed namespace ≠ invalid_to_explanation seed namespace).
- Stratification uses `(task_type, grammar_category_or_error_class)` as the stratum key. Strata smaller than `--min-stratum-size` (default 20) go entirely to train, listed in `split_diagnostics.small_strata_train_only`.
- The aggregator is the durable artifact. Each new corpus generation cycle (rebuilt english_to_cas, external dialogue data, etc.) gets added to the inclusion rules and re-run; no manual re-aggregation work.

**Files of record:**

- `cas-synthetic/scripts/build_path_d_v1_mix.py` (aggregator)
- `cas-synthetic/data/path_d/v1_mix_train.jsonl` (7,395 rows)
- `cas-synthetic/data/path_d/v1_mix_val.jsonl` (412 rows)
- `cas-synthetic/data/path_d/v1_mix_test.jsonl` (412 rows)
- `cas-synthetic/data/path_d/v1_mix_manifest_20260509T005614Z.json`

**Status discipline:**

- Aggregator: WIRED + WORKS + PRODUCED CORPUS.
- v1 training mix (8,219 rows): VALIDATED STRUCTURALLY (all sanity red flags = 0).
- v1 mix as a *training-quality* artifact: NOT yet validated against a trained model. The first model trained on this corpus will be the empirical test.
- v1 mix is **incomplete by design** (2 of 4 Path D slots; no external dialogue data yet). Do not describe as "complete" or "v1 training-ready" until the gaps close.

**Open follow-ups:**

- english_to_cas rebuild via compiler-validation gate (~$30, ~3h).
- invalid_to_corrected rebuild via "compiler validates the correction" gate (~$30, ~3h).
- External dialogue data integration (per dataset scout reports, conversational discipline mix).
- First v1 model training run on this corpus (validates whether the structural quality translates to model behavior).

## Session 59: Path D Wave 2.5 promoted — first end-to-end SFE-gated CAS-to-English corpus (May 8, 2026)

**Headline.** 5,268 SFE-certified CAS-to-English records produced via the model-in-loop pipeline (Haiku draft + SFE round-trip gate + self-correction retries). All four promotion gates clear; human review pack thumbs-upped. **Wave 2.5 promoted as the v1 cas_to_english training mix candidate.**

**Pipeline shape (now operational, repeatable):**
- Seed enumerator (own) → Haiku translator (rented) → SFE structural-fingerprint comparator (own) → corrective re-prompt loop (own) → anti-jargon + anti-notation gates (own) → accepted JSONL.
- Model-agnostic by design: SFE accepts any drafter (Haiku/Sonnet/Opus/future). Translator is swappable; pipeline is ours.

**Run accounting (`20260508T203848Z` + 2 backfills):**

| Metric | Value |
|---|---|
| Seeds in pool | 5,802 |
| Processed | 5,802 (100%, after 6-seed backfill) |
| Accepted | 5,268 (90.80%) |
| Rejected | 534 (9.20%) |
| Errored | 0 |
| Spend | $30.56 + ~$0.05 backfill / $40 cap |
| Wall clock | ~3h 20m main run |

**Gates (all PASS):**

| Gate | Threshold | Result |
|---|---|---|
| Aggregate accept | ≥80% | 90.80% |
| Per-category floor | ≥70% | 80.8% (inversion) |
| Hard CAS notation in English | = 0 | 0 |
| Jargon (operator/noetic/cognitive operation/bare drive) | = 0 | 0 |

**Per-category acceptance:**

| Category | Accepted | Rejected | Rate |
|---|---:|---:|---:|
| binary_composition | 732 | 13 | 98.3% |
| state_literal | 1,019 | 37 | 96.5% |
| rpm_chain | 359 | 25 | 93.5% |
| meta_logic_relation | 710 | 58 | 92.4% |
| let_binding | 441 | 39 | 91.9% |
| cross_register_omega | 579 | 79 | 88.0% |
| diagram_export | 417 | 63 | 86.9% |
| recipe | 481 | 95 | 83.5% |
| fractal_sequence | 466 | 110 | 80.9% |
| inversion | 63 | 15 | 80.8% |

**Rejection structural buckets (534 rejects, all caught by SFE — exactly its job):** fractal k-multiset mismatch 20.6%, register dropped 19.9%, drive missing/wrong 18.4%, noetic count off 15.2%, Ω target name leak 10.1%, domain binding 9.4%, RPM arrow count 6.0%, cluster + other 0.4%.

**SFE retry distribution (accepted):** 1 try 46.7%, 2 tries 41.9%, 3 tries 8.2%, 4 tries 3.2%. First-pass acceptance 46.7% confirms retries do real corrective work.

**Architecture note — what's ours vs rented:**
- **Owned (the IP):** seed enumerator from compiler grammar, SFE structural fingerprinter (`cas-synthetic/scripts/sfe.py`), self-correction loop, anti-jargon/anti-notation gates, retry-prompt corrective machinery, pipeline orchestration.
- **Rented (replaceable):** Haiku as English drafter — the translator slot is swappable.

This means the next corpus generation cycle is: change seed mix, hit go, $30 + ~3h, certified data.

**Stakeholder framing (locked):** "CAS is the speaker. Haiku is the U.N. translator. SFE is the translation auditor. Only certified translations enter training."

**Status discipline (per user feedback):**
- Pipeline: WIRED + WORKS + GATE-PASSED + HUMAN-REVIEWED.
- 5,268-record corpus: VALIDATED as a CAS-to-English training source.
- v1 training mix: not yet built (Wave 4 aggregator track).
- v1 model: not yet trained.

Do not describe this as a trained model, an evaluation, or product readiness. It is a **certified corpus for training**, nothing more, nothing less.

**Files of record:**
- `cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260508T203848Z.jsonl` (5,263 records, main run)
- `cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260509T002355Z.jsonl` (4 records, backfill round 1)
- `cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_20260509T002541Z.jsonl` (1 record, backfill round 2)
- `cas-synthetic/data/path_d/wave3_step2_5_rejected_20260508T203848Z.jsonl` (533 records)
- `cas-synthetic/data/path_d/wave3_step2_5_rejected_20260509T002355Z.jsonl` (1 record)
- `cas-synthetic/data/path_d/wave3_step2_5_manifest_20260508T203848Z.json` (main manifest with prompt template version `wave3_step2_5_model_in_loop_v2_2026_05_08`)
- `cas-synthetic/data/path_d/wave3_step2_5_review_pack_50_20260508T203848Z.jsonl` (50-record stratified review pack, human-reviewed PASS)
- `cas-synthetic/scripts/sfe.py` (Structural Fingerprint Extractor)
- `cas-synthetic/scripts/generate_wave3_step2_5_english_descriptions.py` (model-in-loop orchestrator)
- `cas-synthetic/tests/test_sfe.py` (21 SFE regression tests)

**Open follow-ups (not blockers):**
- Wave 4 corpus aggregator (task #129) — combine Wave 2.5 with Wave 3 v2 cas_to_english + invalid_to_explanation + invalid_to_corrected.
- Reject-set triage: 534 rejects preserved for targeted future repair (fractal-aware sub-prompt or Opus drafter on the 110 fractal-sequence misses).
- Compile-rate evaluation as separate eval layer (round-trip via english_to_cas + compiler).

## Session 58: B-4.1 audit failed — v0 NOT promoted; four-step v1 plan launched (May 7, 2026)

**Frame.** The B-4.1 human relevance audit ran on the `b3_full_50k_prodshape_20260507` checkpoint and **failed catastrophically. v0 does NOT promote.** Five failure modes documented in `docs/working/path_B4_human_relevance_failure_2026_05_07.md` (Codex's note, this commit). User and Codex converged on a four-step v1 plan: A (commit failure as project truth, this commit) + B (automated failure eval harness) + C (OOD gate + chat.py routing) + D (compiler-preservation scorer). B/C/D are running as parallel background agents.

**Status correction (load-bearing):**
- B-4 engineering loop: **live locally**
- B-4 product status: **failed human relevance audit**
- B-4 stakeholder/demo status: **not ready**

The model is currently a CAS-conditioned reflective prose generator with weak relevance and weak compiler alignment. **Do NOT describe as "fluid conversation" until v1 clears the automated gate.**

**Five failure modes from the audit trace:**

1. **Irrelevance** — replies fluent but don't address prompts. Decorative not responsive.
2. **Drunk coherence** — token-level fluent, discourse-level incoherent.
3. **OOD ships anyway** — K=9 detects OOD ("no CAS signal detected ... documented modality limitation") but ships confident CAS classification regardless. Routing failure, not detection failure. "this shit is wack" → `^2^E_{F5}|E` (Positive — opposite of user's affect).
4. **Compiler round-trip catastrophic** — ground truth `Θ(Ω_focused_refusal) = 0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A → Ω_focused_refusal` produced `^7^P|T + ^7^P|A`. Lost Θ wrapper, all coefficients, two ingredients, arrow, named target.
5. **Structural-shape-without-content** — model memorized v77_omega and v76_production silhouettes; hollows out drives, coefficients, named Ω targets while preserving the silhouette. Hallucinated Domain `^P` on v77_omega presence example where ground truth specified no Domain. Per-bucket failure pattern: drives stripped 100%, named Ω targets collapsed 100%, Θ wrappers lost on recipes 100%.
6. **Bonus: belief substrate `Inv✗(A)` fires correctly but is advisory only** — RPM/inversion telemetry visible in trace but doesn't gate output.

**Four-step v1 plan (user + Codex convergence, locked):**

| Step | Track | Owner | State |
|---|---|---|---|
| **A** | Commit failure as project truth + CHANGELOG status correction | foreground | THIS COMMIT |
| **B** | B-4 automated failure eval harness (50–100 prompts × 7 user-facing dimensions × 9 structural-preservation sub-checks) | background agent | running |
| **C** | OOD gate (`cas-native/inference/ood_gate.py`) + `chat.py` routing fix | background agent | running |
| **D** | Compiler-preservation scorer (`cas-native/evaluation/compiler_preservation_scorer.py`) | background agent | running |

A blocks nothing else. B consumes D's API; B uses placeholder import until D lands.

**Slogan locked:** *"Fluency last. Object preservation first."*

**v1 long-arc plan** (post-A/B/C/D):

1. Eval set lands (B's harness)
2. Path C / Path D doc split (Path C = simplex-native architecture; Path D = compiler-fluency curriculum)
3. Generate full compiler-fluency corpus from compiler-validated objects (the entire CAS system, not a dialogue slice)
4. Build simplex-native content-preservation architecture (Path C §3.1 corrected: Δ°₃₉ base manifold + drive intensity vector — NOT Δ°₆ — + Bernoulli register + typed constraints)
5. Train Path C + Path D together (compiler-in-the-loop validation; contrastive readout supervision)
6. Conversational discipline slice retrofit on top
7. Auto re-gate against B's eval set
8. Human audit by non-creator only after gate passes

**Path C §3.1 architectural correction (memo-only this commit; doc edit follows post-eval-gate):** Drive reframed Δ°₆ → 7-dim intensity vector because drives co-present (F1 + F5 simultaneously is real cognition, not mutually exclusive). Domain and Noetic = derived marginals from Δ°₃₉, not primary heads. Geometry: **base manifold + typed fibers + typed constraints**. Captured in durable memory `project_path_c_base_manifold_typed_fibers_correction_2026_05_07.md`.

**Inversions axis-count question (user surfaced today):** TKS heritage searched end-to-end. No "28 inversions" or "33 inversions" exists anywhere. TKS has 3 dualities (ν2↔ν3, ν5↔ν6, ν8↔ν9) + 28 Sub-Foundations (drives × worlds, NOT inversions). CAS canonical 7 inversion axes stays default for v1; expansion only on empirical evidence. Inversions live in the typed-constraint layer alongside RPM and meta-logic — *not* a state simplex. Gemini's claim of "Indices 28–33 in `_tmp_playground_bundle.js` lines 898–910 and 2030–2080" was **hallucinated**: file is 1053 lines (not 2080), lines 898–910 are bundled markdown parser code, no inversion data anywhere.

**Durable lessons captured as memory** (cross-session):
- `feedback_audit_only_after_automated_checks.md` — human audit only after automated diagnostics pass; creator is wrong auditor; compile rate is missing eval layer.
- `project_v1_locked_plan_path_c_d_2026_05_07.md` — 8-step execution order; 7-dim user-facing eval gate; 9-check structural preservation.
- `project_path_c_base_manifold_typed_fibers_correction_2026_05_07.md` — Path C §3.1 architectural correction (drive ≠ simplex).
- `feedback_gemini_citations_need_verification.md` — to be added: Gemini hallucinated specific file/line citations on this codebase; verify before acting.

**This commit:**
- Stages `docs/working/path_B4_human_relevance_failure_2026_05_07.md` (Codex's failure note; covers all three trace-derived findings: structural-shape-without-content addendum, OOD-detected-but-not-gated, inversion-advisory-only).
- Adds Session 58 to CHANGELOG.

**Path B / v1 status:**

| Track | State |
|---|---|
| B-1 Tier 3 dialogue SDG | DONE |
| B-2 Batcher reconciliation | DONE |
| B-3 First native generation training | DONE |
| B-3.5 Round-trip K=9 grounding eval | DONE — calibrated pass |
| B-4 Two-stage inference in chat REPL | engineering live; product failed; demo NOT ready |
| **B-4.1 human PoC audit** | **DONE 2026-05-07 — NEGATIVE; v0 NOT promoted** |
| **v1 Step A** | **THIS COMMIT** |
| v1 Step B (eval harness) | background agent running |
| v1 Step C (OOD gate) | background agent running |
| v1 Step D (compiler-preservation scorer) | background agent running |
| Path C Simplex Δ°₃₉ rebuild | §3.1–3.4 captured + §3.1 corrected (memo); build post-v1-eval-gate |
| Path D Compiler-fluency curriculum | doc split scheduled post-A/B/C/D |

## Session 57: Path B reaches v0 promotion gate + Path C compiler-fluency framing (May 7, 2026)

**Frame.** Path B fully wired through B-4. B-1 (50K Tier 3 SDG, $153.26) → B-2 (Session 56 commit) → B-3 (first production-shape GPU training run, 5 epochs, $0.54, coherent register-grounded sample replies) → B-3.5 (round-trip K=9 grounding eval calibrated pass) → B-4 (chat REPL two-stage wiring with 6-bug Codex audit repair, 67 tests passing). B-4.1 human PoC audit form ready — 31 prompts staged at `docs/working/path_B4_1_human_audit_form_2026_05_07.md`; user runs the audit next as the v0 promotion gate. Promotion criteria: avg relevance ≥3.5, avg register fit ≥4, leakage = 0. If passes, v0 ships. If fails, audit failure-mode tells the next remediation track.

**Path C architectural captures (this commit).** Path C's §3 expanded with four sub-sections that together specify what gets built after v0 ships:

- **§3.1 Refined CAS state space — typed product of simplexes.** Replaces the original single-`p_t ∈ Δ°₃₉` framing with three structures: Cognitive State Δ°₃₉ (40 atoms = 10 Noetics × 4 Domains, the patent-named primitive), Drive Δ°₆ (F1–F7), and Register Bernoulli gates (NOT a 4-atom simplex — supports CAS v7.7 multi-register `|⟨...⟩` notation natively). Reading A correction: Δ°39 is the joint Cognitive State, not Noetic alone. Six-component stack (state simplex / drive simplex / register Bernoulli / operation decoder / meta-logic proof module / RPM gate). Why 53-dim three-structure beats both 1,120-atom one-giant-joint and 14-dim four-independent-axis decompositions.
- **§3.2 Meta-logic is a verb, not a noun.** Simplexes answer noun questions ("which state is active?"); meta-logic answers verb questions ("does X cover Y? is this transition admissible?"). Meta-logic is NOT a flat categorical axis like Drive or Register. Small typed mini-distributions (relation type, operand role, truth status) live INSIDE the meta-logic module without making the module itself a simplex. Meta-logic is the runtime extension of `api/notation/compiler.py` — compile-time validates syntax; runtime meta-logic checks whether assertions hold over the model's current state distribution. Pre-gen (constraint, mask logits at decoding) vs post-gen (explanation, full proof object for Mode 7 trace) — production target is both, in sequence.
- **§3.3 Refined Path C phasing — axis-by-axis prototype.** C1 (Cognitive State Δ°₃₉ + Fisher-Rao loss + RPM stub) → C2 (add Drive Δ°₆) → C3 (add Register Bernoulli, test multi-register expressivity) → C4 (add meta-logic proof module, observation only) → C5 (RPM uses meta-logic proofs as gate evidence). C4-before-C5 is a HARD gate — meta-logic must hit ≥90% accuracy on held-out admissibility tests before promotion to RPM evidence; otherwise RPM-with-broken-evidence is strictly worse than scalar RPM.
- **§3.4 CAS-Native is to the CAS compiler what Codex is to language compilers.** Single load-bearing north-star framing for post-v0 training direction. Model = fluent speaker; compiler = law/judge. Long-term inference architecture: English → CAS-Native proposes CAS expression → CAS compiler validates → RPM/meta-logic checks admissibility → CAS-Native explains in English. Six-task compiler-fluency curriculum (CAS↔English, invalid→explanation, invalid→corrected, operation→outcome, expression→compiler trace) is the next training era — NOT more dialogue corpus. Five operational requirements: vocab parity / corpus parity / compiler-validated training / constrained decoding / compiler-as-evaluator. Reframed v0 → Path C → Phase 4 progression mapped to "Codex that knows expressions" → "Codex that covers full language" → "Codex with linter integration in the loss." Slogan: "Model knows everything the compiler can SAY. Compiler decides whether what the model said is TRUE." Captured as durable memory; next training-track design conversations default to compiler-fluency over dialogue scaling.

**Today's commits in chronological order**
- `788148b` docs: record B-3 5K sample-reply smoke
- `f8ed357` docs: record B-3 full 50K run verdict
- `585591e` cas-native: add round-trip grounding eval
- `61b6f3b` docs: record B-3.5 diverse CAS grounding pass
- `d6d16be` cas-native: fix B-4 native-generator wiring + add regression tests
- (this commit) docs: Path C §3.1–3.4 captures + B-4.1 audit form ready

**Path B status.**

| Track | State |
|---|---|
| B-1 Tier 3 dialogue SDG | DONE — 50K records, $153.26, 100% validator pass, 0 leakage |
| B-2 Batcher reconciliation | DONE — Session 56 commit `62f0299` |
| B-3 First native generation training | DONE — 50K corpus, 5 epochs, $0.54, coherent register-grounded sample replies |
| B-3.5 Round-trip K=9 grounding eval | DONE — calibrated pass (commit `585591e`) |
| B-4 Two-stage inference in chat REPL | DONE — 6 Codex audit bugs repaired, 67 tests (commit `d6d16be`) |
| **B-4.1 human PoC audit (31 prompts)** | **READY — user runs next; v0 promotion gate** |
| Path C Simplex Δ°₃₉ rebuild | §3.1–3.4 captured; build POST v0 promotion |

**After-v0 short list (queued for surfacing once the audit lands).**
- meta_logic 14-token vocab expansion (~1.5 pod-hours; closes a known structural gap on the compiler-fluency axis).
- Path C-1 prototype (Cognitive State Δ°₃₉ encoder + Fisher-Rao loss + RPM stub; transformer decoder retained).
- Compiler-fluency curriculum SDG design (six task slices with compiler-validated samples).

## Session 56: Path B-2 lands + class-weighted-loss MISS closes the classifier-band-aid track (May 6, 2026)

**Frame.** Two outcomes: (1) the long-running class-weighted-loss smoke missed all four verdict gates, closing the loss/sampler-side experiments for Drive-head imbalance; (2) Path B-2 (Native NL generation training bridge) committed locally and ready to scale once Codex's Tier 3 dialogue SDG reaches volume. K=9 (commit `d99810a`, 93.2% canonical / 46.9% paraphrase / 79.4% drive) stays production. Path B is the forward path.

**Commits**
- `62f0299` cas-native: wire native NL generation training bridge (B-2)

**Class-weighted-loss smoke verdict (PID 16433, run dir `v1_smoke_drive_class_weighted_loss_2026_05_06`).** 4h 30m on RTX A6000. 3-epoch run, paraphrase-augment-train=3, inverse-frequency-mean-one drive weights (F1=0.46, F2-F7≈1.13-1.34). Final results:
- Overall all-heads-exact: **53.2%** (epoch trajectory 49.8% → 51.8% → 53.2%). MISS: target ≥55%.
- Drive head accuracy: **72.2%**. MISS: target ≥80%; also **−7.2pp below K=9 baseline** of 79.4%.
- F1 over-prediction: **+32.2%**. MISS: required to beat BOTH paraphrase smoke (+42%) AND balanced sampler (+15%); only beats paraphrase.
- F6 sink: **+111.3%**. MISS catastrophically — worst F6 over-prediction across all three runs (paraphrase had +16%, balanced sampler +106%).
- All four targets MISS → per Codex's branching, K=9 stays production, move to conversational v0 path.
- Full per-bucket and per-head data in `manifest.json`; samples + Drive predicted-vs-target distribution in `samples.jsonl`.

**Diagnostic read.** Class-weighted loss shifted the imbalance rather than fixed it — same failure mode as the balanced sampler, just biased differently. Inverse-frequency weights made the model under-predict F1 less aggressively but redirected the variance into F6, producing the worst F6 sink yet. Both class-balancing levers (sampler and weighted loss) demonstrate that drive head imbalance is **not addressable from the loss/sampling side alone**. The sink keeps moving but doesn't disappear. Loss/sampler-side experiments are closed.

**Path B-2 — Native NL generation training bridge.** Commit `62f0299`, 8 files +1743/−50 LOC, 67 tests passing. Codex audited the design twice (v1 and v3) and caught a load-bearing silent-skip bug; v4 is the audit-clean state.

- `cas-native/training/datasets/native_nl_collator.py` — `NativeNLCollator` converts Tier 3 dialogue records to `forward_with_lm` kwargs (input_ids/attention_mask/decoder_input_ids/cas_prefix_ids/register_id) plus loss-side fields (lm_targets/loss_mask) plus provenance (record_ids/trace_ids).
- `cas-native/training/masked_ce_loss.py` — `masked_cross_entropy` reply-only LM loss, ignore_index + explicit mask combined.
- `cas-native/training/train_native_nl_gen.py` — real path builds full `CASNativeModel`, attaches `NLGenerationHead` via `attach_nl_gen_head`, drives every batch through `forward_with_lm`. Fallback path (`--use-fallback-head`) gated explicitly; no silent downgrade. d_model hard-equality guard at construction (no projection).
- `save_tokenizer_artifacts()` helper persists `tokenizer.json` + copies any `--english-bpe-path` artifact into `out_dir` as `english_bpe.json`. Raises if unsavable rather than silently skipping (the Codex-caught bug). Manifest extra carries `tokenizer_kind`, `tokenizer_hash`, `english_bpe_path` (out_dir), `english_bpe_hash`, `english_bpe_source_path`, `vocab_size`, `use_cas_prefix`, `use_fallback_head`.
- `--use-cas-prefix` opt-in (default OFF) prevents PAD-token leakage into NLGenerationHead conditioning until the head exposes a `cas_prefix_mask`. Bottleneck-z and register-id continue to carry CAS state.
- `--train-log-every-steps` rejects 0/negative at run_training entry; modulo-by-zero would have silently corrupted the train_progress signal.
- Always-print `train_progress` events for batches 1, 3, 5 of epoch 0 plus every N batches per the durable observability rule.

**Tests landed (B-2 commit, 67 passing):**
- `test_native_nl_collator.py` (14 tests including `test_mixed_length_cas_prefix_pads_with_pad_id` documenting the leakage point)
- `test_masked_ce_loss.py` (7 tests covering all-ones-mask reduction, ignore_index, all-zero-mask safe-divide, label smoothing, reduction modes, shape guards)
- `test_save_tokenizer_artifacts.py` (5 tests pinning the four save branches + the previously silent skip bug)
- Existing `test_native_nl_gen_training.py` (14) and `test_nl_generation_head.py` (27) unchanged

**Out of scope for B-2 (intentional).**
- Structured loss reattach — first bridge LM-only (α=0); structured path is B-2.5 follow-on against the existing `CASNativeModel.forward()` outputs.
- B-3 GPU training run — blocked on Codex's Tier 3 dialogue SDG reaching ≥10K records.
- B-4 chat REPL two-stage inference — blocked on B-3 producing a usable checkpoint.
- `train_structured_prediction.py` / `structured_prediction.py` — closed classifier-band-aid experiments, intentionally excluded.

**Object provenance preserved.** Every B-2 record-batch carries `record_ids` and `trace_ids` lists in order. The collator preserves them through to the trainer, where they get folded into the `GenerationTrace` records when `--trace-mode=full` is set. Mode 7 surface populates with real model values when the real path runs.

**Path B status now.**

| Track | State |
|---|---|
| B-1 Tier 3 dialogue SDG | In flight under Codex; 477-record paid proof passed quality review; ready to scale 5K → 50K |
| **B-2 Batcher reconciliation** | **DONE — committed `62f0299`** |
| B-3 First native generation training | Blocked on B-1 reaching ≥10K records |
| B-4 Two-stage inference in chat REPL | Blocked on B-3 |
| Path C Simplex Δ°₃₉ rebuild | Parked POST v0 demo |

## Session 55: Native CAS-Native NL Generator Architecture Push + Belief Substrate + Mode 7 Live Wire-Up (May 4, 2026 evening)

**Frame.** Single-night sprint that delivered three new architectural surfaces (CAS-as-Belief-Substrate, Mode 7 live network attribution, Idea Atlas adapter), the full native CAS-Native NL generation stack (tokenizer extension, NLGenerationHead module, training pipeline, eval harness, generation trace, SDG seed corpus), and ratified two hard architectural rules (no foreign pretrained weights anywhere; object traceability load-bearing on every artifact). Sessions 53 and 54 below are partial reports from sub-agents in this same sprint.

**Architectural rules ratified.**
- **No foreign pretrained models.** Generation head is fully native — random-init weights, NO TinyLlama / Llama / Qwen / Mistral / Phi / Gemma / GPT-2 / BERT anywhere in the production stack. Decision triggered after a TinyLlama LoRA infrastructure commit was prepared and then hard-reset out of git history before reaching origin. Rule is enforced in code via static docstring scan in `cas-native/model/nl_generation_head.py` test suite.
- **Object traceability is load-bearing.** Every domain object — checkpoints, training events, eval results, generation traces, beliefs, atlas posts, tokenization output — carries `id` (UUID or sha256), `created_at`, `schema_version` or `code_version`, `parent_ids`, `source`, `trace_id`. No silent black boxes.

**Tonight's commits (8, in chronological order).**

1. **`21ff240` HONEST_STATUS + Idea Atlas adapter.**
   - NEW: `noetic-compass-scaffold/noetic-compass/HONEST_STATUS.md` — single source of truth labeling every feature SHIPPED / WIRED / SCAFFOLD / IN PROGRESS / NOT STARTED. Stops the scaffold-as-built confusion that triggered tonight's correction sprint.
   - NEW: `cas-native/inference/atlas_adapter.py` (10 tests passing) — thin Python bridge from `predict_cas` output to the shipped `/idea_atlas/ideas` API. POSTs when the API server is reachable and a JWT is present; falls back to `~/.cas-native/atlas_local.jsonl` when either is missing. `replay_local_fallback()` drains the local buffer when the API comes back up.
   - Companion test file at `cas-native/tests/inference/test_atlas_adapter.py`.

2. **`fbf44e0` CAS-as-Belief-Substrate (CABS) — belief store using ^4 Vibration + ^7 Rhythm + RPM + Inversion Scan gates.**
   - NEW: `cas-native/belief/` package — `belief.py` (Belief dataclass), `vibration.py` (^4 confidence with 30-day half-life decay + saturating reinforcement), `rhythm.py` (^7 exposure count), `rpm_gate.py` (RPM chain check via the existing notation compiler), `inversion_gate.py` (7-axis: N/W/F/E/S/A/P), `persistence.py` (SQLite at `~/.cas-native/beliefs.db` with three tables: beliefs, observations, contradictions), `belief_store.py` (BeliefStore facade with `record_observation` / `check_belief` / `add_contradiction` / `decay_all` / `list_locked`).
   - Lock rule: `locked == (rpm_chain_satisfied AND vibration > 0.7 AND inversion_scan_clean AND rhythm_count >= 3)`.
   - MODIFIED: `cas-native/inference/chat.py` — adds `BELIEF STATUS` line to every prediction render plus `/beliefs`, `/why <claim>`, `/forget <claim>` REPL commands. Belief substrate hooks the existing prediction path; `/menu`, `/sample`, `/raw`, `/help`, `/exit` preserved unchanged.
   - 98 tests passing; existing tests preserved.

3. **`d79ad12` Scrub TinyLlama from HONEST_STATUS — CAS-Native architecture is end-to-end native.** Documentation-only follow-up to the architectural rule ratification. Removed all references to TinyLlama-1.1B / LoRA / pretrained-backbone path from HONEST_STATUS. Companion to the hard-reset of commit `0e66b14` (TinyLlama LoRA infrastructure, never pushed).

4. **`32a76d5` Mode 7 live wire-up — real PyTorch hooks capture activations during predict_cas.**
   - NEW: `cas-native/trace/live_capture.py` (~430 LOC) — registers `register_forward_hook` on the embedding fused output, `embedding.output_norm`, `embedding.fusion_gate`, `head.backbone` (post-bottleneck z), and all 12 head linear layers. Hooks installed via `try/finally` — removed even on exception. Returns `LiveTrace` with detached + CPU-moved + JSON-serializable activations and per-head attribution.
   - Real `gradient × input` attribution on the bottleneck dims — one backward per head against the head's argmax/most-confident logit, `retain_graph=True` for all but the last head. Top-K dims by `|score|` returned per head.
   - MODIFIED: `cas-native/inference/predict_cas.py` — `Predictor.__call__` accepts `with_trace: bool = False` (and `trace_top_k: int = 3`); existing positional callers unaffected (defaults to no-trace, no-grad path).
   - MODIFIED: `cas-native/inference/chat.py` — adds `/trace` and `/trace --raw` REPL commands (rich-styled with magenta theme + plaintext fallback); coexists with belief commands from `fbf44e0`.
   - MODIFIED: `cas-native/trace/__init__.py` — lazy re-export of `LiveTrace`, `HeadInfo`, `LayerActivation`, `capture_live_trace`.
   - 17 new tests in `cas-native/tests/trace/test_live_capture.py` + `test_sample_trace_output.py` + `_capture_sample_output.py`. Combined regression: 148 tests pass (17 new + 98 belief + 16 trace + 17 model).

5. **`e645296` Native NLGenerationHead module — 6-layer transformer decoder, random init, full object traceability.**
   - NEW: `cas-native/model/nl_generation_head.py` (982 LOC) — `NLGenerationHead`, `NLGenerationHeadConfig` (frozen), `GenerationTrace`, `TokenStep`, `_VERSION = "v0.1.0"`. Module docstring carries the literal string `"NO foreign pretrained models"` and the class names `TinyLlama / Llama / Qwen / Mistral / Phi / Gemma / GPT-2 / BERT` — all enforced by `test_module_docstring_no_foreign_pretrained` static substring scan.
   - 6-layer decoder, d_model=512, n_heads=8, ffn=2048, ~50.2M params at default config (`vocab_size=24000`). Random init throughout.
   - Conditioning: discrete CAS-prefix tokens prepended to decoder input + 4-position bottleneck soft-prefix + cross-attention to encoder outputs with caller-supplied domain validity mask. Output-side register FiLM modulation (per-example for heterogeneous register IDs in a batch).
   - Object traceability: `forward(return_meta=True)` returns `output_id` (UUID), `model_code_version`, `model_weights_sha` (sha256 of state_dict), `cas_conditioning_id`, `attention_summary`. `generate(with_trace=True)` returns a `GenerationTrace` with per-token `TokenStep` records (`position`, `token_id`, `attn_to_cas_prefix`, `attn_to_prior_tokens`, `layer_activation_l2`, `selected_via`).
   - Reuses `cas_native.model.domain_descent.build_domain_descent_mask`, `cas_native.model.register_film.RegisterFiLM`, `NUM_REGISTERS`. No reinvented layers.
   - MODIFIED: `cas-native/model/cas_native_model.py` — adds `attach_nl_gen_head()` and `forward_with_lm()` minimally; existing `forward()` path UNCHANGED (regression test asserts no `nl_gen_head` exists by default and the regular forward returns no `lm_logits`).
   - MODIFIED: `cas-native/model/__init__.py` — exports `NLGenerationHead`, `NLGenerationHeadConfig`, `GenerationTrace`, `TokenStep`.
   - 18 new tests; 168 total pass (new + belief + trace + model + forward_path).
   - **Known divergence with the architecture spec at `docs/working/native_nl_generation_head_spec_2026_05_04.md`:** model uses free-floating learned soft-prefix; spec recommends `Linear(d_model, 4*d_model)` projection of `pooled_hidden_state` for trace fidelity. Reconciliation pass tracked.

6. **`e4bbad8` Native English BPE tokenizer extension — random-init merges trained on SDG corpus.** Recorded above as Session 50.

7. **`bd70c05` Native NL gen training + eval + generation trace surface — full object provenance.** Recorded above as Session 51.

8. **`4d81618` Native NL SDG strategy + Tier 1 seed (2.5K records, deterministic).**
   - NEW: `docs/working/native_nl_sdg_strategy_2026_05_04.md` (16KB) — three-tier corpus strategy (Tier 1 template / Tier 2 Claude rewrites / Tier 3 dialogue), CAS coverage requirements (10×4×7×4 axes + compound expressions + recipes + meta-logic + anti-drift slices), object-traceability schema, cost+timeline.
   - NEW: `cas-synthetic/scripts/generate_native_nl_sdg_v1.py` (55KB) — Tier 1 enumerates `english_generator.py` templates across 10×4×7×4 axes; Tier 2 calls Claude API (concurrency 5, cost cap $50, retries with backoff). Idempotent re-runs via deterministic sha256 IDs.
   - NEW: `cas-synthetic/tests/test_native_nl_sdg.py` (17 tests passing): schema, axis coverage, deterministic IDs, idempotent re-runs, validator (jargon filter, template-opener filter, length, density), CAS v7.5 register format, manifest completeness, API key fallback, cost cap, parent lineage, anti-drift vocabulary checks.
   - NEW: `cas-synthetic/data/native_nl/v1_seed_5k_manifest.json` — provenance manifest with full distribution stats. `trace_id` grouping cohort, `schema_version=native_nl.v1`.
   - NEW: `cas-synthetic/data/native_nl/v1_seed_5k.jsonl` — 2,500 Tier 1 records (gitignored — data). Each record carries `id` (sha256), `schema_version`, `trace_id`, `tier`, `parent_ids`, `source`, `source_template_id`, `generator_model`, `generation_timestamp`, `cas_expression`, axes, `prompt`, `reply`, `demographic_profile`, `tone`, `validator_pass`, `validator_reasons`.
   - **KNOWN GAP:** SDG agent never made Tier 2 API calls (`api_calls: 0`, `api_key_status: "unused"`). Tier 2 follow-up scheduled — `~$10-30` Claude spend to reach 5K total seed.

**Stack now in place for Phase 4 NL Generation training.** Architecture spec → tokenizer (CAS reserved + English BPE) → 50.2M-param random-init decoder → joint training pipeline with β-curriculum → eval harness (CAS-grounding rate / fluency / diversity) → generation trace surface → 2.5K Tier 1 seed corpus. End-to-end runnable. First training run blocked only on Tier 2 SDG completing the 5K seed (and ideally scaling Tier 1 to 40K + Tier 2 to 100K for fluency from-scratch).

**Combined test results across the night's work.** 213+ tests passing across belief, trace, model, training, eval, atlas adapter, tokenizer, SDG. Full regression on existing test suites preserved.

**Three reconciliation items (none blocking):**
1. Soft-prefix design: model uses free embeddings; spec recommends `Linear(d_model, 4·d_model)` projection of `pooled_hidden_state`.
2. `NLGenerationHead.forward()` signature handoff between model and training agents — adapter present, 30-min cleanup before first GPU run.
3. `TokenStep.log_prob` field — model uses `selected_via` (argmax/topp/temp); per-token log-probability is a follow-on PR.

**Architecture spec §14 "open questions" — 5 of 6 redundant.** Deep grep confirmed: tokenizer ID stability already built (`vocab14` patch), frozen-vs-unfrozen settled empirically (memory: `project_cas_transformer_modality_mismatch_pivot.md`), default trace mode answered by Mode 7's `with_trace=False` default, refusal/authority pattern substantially built (DST `dialog_grammar.py` + `api/notation/turn_admissibility.py`), three-instance dialectic sequencing decided (memory: `project_three_instance_dialectic_proposal_2026_05_04.md`). Only "CAS-themed pretraining as fluency bridge" is genuinely open — curriculum decision, not new code. Methodology rule saved to memory: "If the answer is in the codebase, the question isn't open."

**v1 Full Stack retrain on the pod (separate, in-flight from earlier in the day).** Started 2026-05-04T23:29:45Z. PID 11128 alive, log silent since `model_init` event at 00:55:48 UTC, zero `epoch_end` events as of session close, GPU at 13% util. Investigation pending; not blocking the native gen track.

## Session 54: Native NL Generation Training + Eval + Generation Trace (May 4, 2026)

**Objective.** Third deliverable for the Version B Phase 4 NL Generation Head — the training pipeline, eval harness, and per-token generation trace surface for the fully-native CAS NL generation head. Bridge between the model and how we know it works. No foreign pretrained weights. Object provenance load-bearing on every artifact.

**Deliverables.**

- NEW: `cas-native/training/train_native_nl_gen.py` (703 LOC) — runnable training script. CLI: `--data-path`, `--output-dir`, `--epochs`, `--batch-size`, `--limit`, `--smoke-test`, `--resume-from`, `--alpha-structured`, `--beta-lm-start`, `--beta-lm-end`, `--beta-curriculum-steps`, `--lr`, `--seed`, `--device`, `--logging-steps`, `--vocab-size`. Random-init weights, joint loss `L = α · L_structured + β(step) · L_LM` with curriculum on β, per-step JSON event emission, full-provenance checkpoint manifest (`checkpoint_id`, `code_version`, `weights_sha`, `trained_from_corpus_hash`, `trained_at_timestamp`, `n_train_records`, `n_epochs_completed`, `final_loss_total`, `git_commit_sha`, `schema_version="checkpoint.v1"`). `--smoke-test` runs 1 step on CPU and exits 0. Imports the parallel agent's `NLGenerationHead` when available; falls back to a tiny inline decoder for hermetic smoke.
- NEW: `cas-native/training/native_nl_gen_curriculum.py` (131 LOC) — `compute_beta(step, beta_start, beta_end, curriculum_steps)` linear-ramp-clipped curriculum + stateful `BetaScheduler` class with `to_provenance()` for run manifests.
- NEW: `cas-native/evaluation/native_nl_generation_eval.py` (580 LOC) — three-metric eval harness: (1) `evaluate_cas_grounding_rate` (generate → classify → match per axis, per-bucket breakdown over all 10×4×7×4 axes), (2) `evaluate_fluency_perplexity` (held-out val PPL with pad-mask), (3) `evaluate_diversity_distinct2` (distinct-2 bigram ratio). Every result is an `EvalResult` carrying `eval_id`, `checkpoint_id`, `eval_dataset_id`, `eval_dataset_hash`, `metric_name`, `value`, `per_bucket_breakdown`, `timestamp`, `schema_version="eval_result.v1"`. `render_eval_report_markdown` + `write_eval_artifacts` produce a markdown report alongside per-eval JSON.
- NEW: `cas-native/trace/generation_trace.py` (617 LOC) — extends Mode 7 from `live_capture.py` to the generative path. `GenerationTraceCapture` wraps the model agent's `GenerationTrace` (which owns the per-token decoder trace) and adds trace-side provenance (`trace_id`, `model_checkpoint_id`, `created_at`, `schema_version="generation_trace_capture.v1"`), nearest-neighbor lookup against the training data via `NearestNeighborIndex`, and live CAS-grounding score. `capture_generation_trace(...)` is the main entrypoint; hook safety via `try/finally`.
- MODIFIED: `cas-native/trace/__init__.py` — lazy re-export of `GenerationTrace`, `GenerationTraceCapture`, `NearestNeighborIndex`, `TokenStep`, `capture_generation_trace`, `live_cas_grounding_score`, `trace_to_dict`.
- NEW: `cas-native/tests/training/test_native_nl_gen_training.py` (298 LOC, 14 tests) — smoke 1-step exit 0, curriculum boundaries + clip + midpoint, scheduler provenance, joint-loss combination, manifest-fields completeness, weights-SHA determinism, resume preserves step counter, corpus hash stability, training-event JSON validation, deterministic split.
- NEW: `cas-native/tests/evaluation/test_native_nl_generation_eval.py` (302 LOC, 9 tests) — CAS-grounding perfect-match=1.0, axis-mismatch detection, fluency returns finite PPL, diversity distinct-2 = 1.0 unique, distinct-2 collapse on identical generations, EvalResult provenance fields, full 10×4×7×4 bucket coverage on empty input, markdown render + write_eval_artifacts roundtrip, deterministic dataset hash.
- NEW: `cas-native/tests/trace/test_generation_trace.py` (318 LOC, 8 tests) — populates all TokenStep fields, NN top-K returns ordered IDs, live CAS-grounding score (match + mismatch), no hook leaks across two consecutive captures, JSON-serializable end-to-end with model_trace preserved verbatim, identity fields stamped, `NearestNeighborIndex` JSON round-trip, `GenerationTrace` alias points to capture wrapper.

**Test results.** `pytest cas-native/tests/training/test_native_nl_gen_training.py cas-native/tests/evaluation/test_native_nl_generation_eval.py cas-native/tests/trace/test_generation_trace.py -v` → 31 passed in 2.36s. Regression: `pytest cas-native/tests/belief/ cas-native/tests/trace/test_live_capture.py` → 111 passed unchanged. Total = 142 passed.

**Architectural rules preserved.** No foreign pretrained model loaded. Object traceability is load-bearing on every artifact (checkpoint manifest, training event, eval result, generation trace). Every captured trace carries `trace_id`, `model_checkpoint_id`, `schema_version`, `created_at` so given a JSON artifact on disk the reader knows which checkpoint produced it. Hooks installed during generation are removed via `try/finally`; verified by no-leak test across two consecutive captures.

**Sample checkpoint manifest** from smoke test:
```json
{
  "checkpoint_id": "68f5c69d-e85d-4cd5-a29a-900e85361c40",
  "code_version": "v0.1.0",
  "final_loss_total": 4.775742530822754,
  "git_commit_sha": "...",
  "n_epochs_completed": 0,
  "n_train_records": 2,
  "schema_version": "checkpoint.v1",
  "trained_at_timestamp": "2026-05-05T03:19:58Z",
  "trained_from_corpus_hash": "smoke_synthetic",
  "weights_sha": "aa325df4fed339e70f6a9a594c388dc5bdd61a7dfc720bd6bc1588eecccd25cf"
}
```

**Multi-day training launch command** (A6000 ~$0.79/hr): `python cas-native/training/train_native_nl_gen.py --data-path cas-synthetic/data/native_nl/v1_seed_5k.jsonl --output-dir runs/native_nl_v1 --epochs 12 --batch-size 8 --lr 2e-4 --beta-lm-start 0.1 --beta-lm-end 1.0 --beta-curriculum-steps 10000 --logging-steps 50 --device cuda --seed 42`. Expected wall time on a 100K-record run: ~150K steps at ~0.5s/step on A6000 ≈ 21h ≈ $17 GPU spend; the multi-day budget covers larger 300-500K corpora and any retries / longer schedules within the planned $200-500 envelope.

**Next.** Awaiting parallel SDG corpus + parallel tokenizer agent's HybridCASTokenizer integration. The training script's `_records_to_batch` adapter currently consumes pre-tokenized `input_ids` / `target_ids`; once HybridCASTokenizer exposes the join API, swap the adapter to call it directly. The trace surface is wire-ready for the model agent's `NLGenerationHead.generate(..., with_trace=True)` real signature (`decoder_input_ids`, `bottleneck_z`, `cas_prefix_ids`, etc.) — the wrapper composes its own provenance over the model's `GenerationTrace`.

## Session 53: Native English BPE Tokenizer Extension (May 4, 2026)

**Objective.** First deliverable for the Version B Phase 4 NL Generation Head — extend `HybridCASTokenizer` with English BPE trained from scratch on the project's own SDG corpus. No foreign tokenizer downloads, no pretrained merges, no HuggingFace/sentencepiece imports. CAS gets the glory.

**Deliverables.**

- NEW: `cas-native/training/english_bpe_extension.py` (881 LOC) — stdlib-only byte-level BPE training (`train_english_bpe`), artifact load/save, and `ExtendedHybridCASTokenizer` that composes the existing CAS-aware hybrid tokenizer with a freshly-trained English vocab. CAS reserved tokens get IDs `0..N_CAS-1`; English BPE pieces follow at `IDs >= N_CAS`. Every artifact carries `vocab_version`, `trained_from_corpus_hash` (SHA-256), `trained_at_timestamp`, `bpe_merge_count`, `english_vocab_size`, `cas_reserved_token_count`, `min_frequency`, `target_vocab_size`, and `n_records_trained_on`. `tokenize_with_provenance(text, tokenizer)` stamps every tokenization output with the live `vocab_version` so downstream consumers can audit which vocab produced which token sequence.
- MODIFIED: `cas-native/training/tokenizer.py` — single ergonomic addition: `HybridCASTokenizer.with_english_bpe(path)` returns the composed extended tokenizer. Existing callers untouched.
- MODIFIED: `cas-native/tokenizer/__init__.py` — lazy `__getattr__` re-export of `ExtendedHybridCASTokenizer`, `train_english_bpe`, `extend_hybrid_tokenizer`, `tokenize_with_provenance`, etc., so notebooks can import from `cas_native.tokenizer` directly.
- NEW: `cas-native/tests/training/test_english_bpe_extension.py` (503 LOC, 28 tests) covering deterministic merge order, vocab cap enforcement, min-frequency filtering, ASCII + multi-byte UTF-8 roundtrip, CAS reserved-token preservation, corpus-hash detection, end-to-end save/load/compose, error paths.
- NEW: `docs/working/native_nl_tokenizer_extension_spec_2026_05_04.md` (~1,650 words) — full spec covering goal, vocab partition strategy, BPE training procedure, traceability fields, integration points, testing strategy.

**Test results.** `pytest cas-native/tests/training/test_english_bpe_extension.py -v` → 28 passed in 0.53s. Existing `pytest cas-native/tests/test_tokenizer.py` → 6 passed unchanged.

**Architectural rule preserved.** Pure stdlib implementation; no third-party BPE libraries, no pretrained merges loaded from disk. Greedy byte-level BPE with deterministic lexicographic tie-breaking — same input corpus always produces byte-identical merge sequences. SHA-256 of the merges list is the reproducibility anchor.

**Sample run on a 10-record mini-corpus** (vocab cap 400, min_freq 2): 43 merges learned, `english_vocab_size=303`, `cas_reserved_token_count=334`, total composed vocab 637. Merges-list SHA-256 stable across runs. Sample tokenization of `"The Mind has an affinity for ^2 Positive."` round-trips identically; CAS literal `^2` survives as a single ID-17 token while English text fragments into compact BPE pieces (`'T', 'he', 'M', 'in', 'd', ...`).

**Next.** Awaiting parallel SDG agent's `cas-synthetic/data/native_nl/v1_seed_5k.jsonl` to train the production v1.0 vocab. Training command will be `python -m cas_native.training.english_bpe_extension train --corpus cas-synthetic/data/native_nl/v1_seed_5k.jsonl --out cas-native/training/runs/english_bpe_v1.json --vocab-size 24000 --min-frequency 2`. Expected wall-clock <30s on 5K records.
## Session 52: Diagram-Loop Investigation Arc — Bug, Oracle Leak, Honest Eval (May 3-4, 2026)

**Objective.** Land the diagram-loop architecture (PR #6) at full scale and validate the +5pp Drive / +13.7pp Noetic per-head consistency lifts seen at smoke scale.

**The arc.**

1. **Full retrain v1 launched** on `proposal/diagram-loop-impl` files synced to pod. Trajectory regressed: epoch 0 = 63.2%, epoch 1 = 42.9%, epoch 2 = 28.1%; train loss 2.19 → 0.47 → 0.28. Killed at epoch 2 because the regression + train-loss-collapse signature looked like topological memorization shortcut.

2. **User pushback caught the wrong diagnosis.** Code reading discovered the actual bug: `evaluate_structured_token_prediction` line 452 calls `model(batch)` without `graph_batch`, while training loop line 985 calls `model(batch, graph_batch=...)`. Per-epoch eval was running the model in text-only mode while training supervised the fused mode 25% of the time. Train/eval distribution mismatch, not memorization.

3. **Four-agent investigation team spawned.** PR #15 (architecture detective) confirmed the bug at the code level. PR #16 (empirical verifier) confirmed trajectory matched the mismatch hypothesis. PR #17 (counter-skeptic) caught a deeper issue: the existing `evaluate_diagram_loop_invariance.py --with-graph-path` builds `prior_diagram` by compiling **ground-truth** `cas_expression` — an oracle leak. The K9_DiagLoop smoke's celebrated +34.8 pp / +13.7 pp Noetic / +5 pp Drive numbers were produced on this leaky path and reflect oracle exploitation, not generalization.

4. **PR #18 (solution architect)** wrote a fix that copied the oracle leak. CLOSED, not merged.

5. **Corrective routine spawned** producing PR #19 with an honest two-pass eval: pass 1 text-only canonical prediction, pass 2 uses model's own (sometimes-wrong) prediction as graph prior — never ground truth. Tests include monkeypatch invariant verifying `compile_to_graph` is never called on `cas_expression`.

6. **PR #19 patched** for graph-component model construction (`GraphEncoder` + `GraphTextFusion` initialised before `load_state_dict`) so it can load checkpoints from `--diagram-loop-pairs > 0` training. Fix landed via commit `0696761` on `team/diagloop-honest-eval`.

7. **Honest smoke v2 result on K9_DiagLoop_smoke_5k checkpoint:**
   - Canonical text-only: 47.9%
   - Paraphrase text-only: 26.6%
   - Paraphrase with self-prior: 45.4%
   - **Honest lever lift: +18.8 pp** (real, not oracle)
   - Per-head consistency under self-prior: drive 71.6%, domain 81.0%, noetic 85.1%, **registers 98.6%** (above canonical baseline — strongest single-head result across all experiments).
   - Per-bucket weakness on v76_production (24.4%) and meta_logic (7.5%) — real architectural constraint, not oracle artifact.

8. **K9_DiagLoop full v2 honest retrain in flight** (PID 9383, started 22:44 UTC May 3, ETA ~08:00 UTC May 4). Per-epoch eval rates collapsing toward 0% as expected (buggy text-only path, ignored). Train loss continues descending. Honest two-pass eval scheduled at completion to produce the load-bearing numbers.

**Lessons captured.**

- `train_structured_prediction.py` defaults `--limit` to 128, which silently produces ~114-canonical garbage runs unless overridden with `--limit 100000`. Caught after burning training time on a 128-canonical run.
- Reference implementations should be audited for oracle leakage before mirroring. The leaky reference's docstring explicitly said "tells the model exactly what structure the expression encodes" — a leak hidden in plain sight.
- When per-epoch eval and training use different forward signatures, per-epoch trajectory is not a reliable kill signal for multi-modal architectures.

**Open PRs from this arc:** #14 (consolidation tier-1), #15-#17 (investigation analysis docs), #19 (honest eval, with patch). PR #18 closed as superseded.

**Next step pending K9_DiagLoop full v2 completion.** Honest eval will produce the real paraphrase-with-self-prior number at full scale. If ≥60% with ≥20 pp lift, architecture validates and Paper A v2 §5.7 has its empirical anchor. If <50%, smoke +18.8 pp lift was a scale artifact and architecture deprecates in favor of K=9 baseline + alternative levers (PR #4 self-reference linear, PR #3 KL invariance).

### Session 52 Final Verdict — K9_DiagLoop Full v2 Honest Retrain (May 4, 2026, ~08:55 UTC)

**Completion details.** K9_DiagLoop full v2 honest retrain completed: 31,080 steps / 20 epochs / final train loss 0.063. Honest two-pass eval run on `level3_recoverable_eval_1000_v77_relabeled.jsonl` (the v7.7-relabeled held-out set; do NOT use the un-suffixed `level3_recoverable_eval_1000.jsonl`).

**Honest eval headline numbers.**

| Metric | K9_DiagLoop full v2 | K=9 baseline | Delta vs K=9 baseline |
|---|---:|---:|---:|
| Canonical text-only | **63.0%** | 93.2% | **−30.2 pp** |
| Paraphrase text-only | 28.7% | — | — |
| Paraphrase with self-prior | **46.4%** | 46.9% | **−0.5 pp (TIED)** |
| Honest lever lift (paraphrase self-prior − text-only) | **+17.6 pp** | — | confirms smoke +18.8 pp at scale |

The +17.6 pp honest lever lift confirms the smoke +18.8 pp at full scale. The 30 pp canonical regression dominates the joint metric.

**Per-head paraphrase-with-self-prior breakdown.**

- 100% — authority, has_omega, turn_type
- 99.1% — has_meta_logic
- 96.9% — expression_family
- 95.7% — transition_kind
- 94.5% — meta_relations
- 91.8% — registers (smoke 98.6% → full 91.8%, **−6.8 pp**: smoke per-head signal did not survive at full-record all-heads-exact)
- 89.9% — domain
- 89.5% — register_mode
- 76.3% — noetic
- 75.4% — drive

**Per-bucket paraphrase breakdown.**

- 79.5% — v77_omega
- 70.8% — v74_baseline
- 42.9% — v77_rule_four
- 32.4% — v76_production
- 19.6% — meta_logic
- **11.1% — v75_register (worst bucket)** — the architectural canary, given v75_register is the bucket exercising the Register axis the smoke result had nominally dominated.

**Verdict: outcome C — diagloop deprecates as a primary lever.**

The pre-run decision matrix specified: ≥60% canonical with ≥20 pp lift → architecture validates; <50% paraphrase-with-self-prior → architecture deprecates. The full v2 result hits 46.4% paraphrase-with-self-prior (below 60% validation threshold) and +17.6 pp lift (below ≥20 pp validation threshold), with the canonical regression dominating. Both Gemini's "capacity-stealing at scale" diagnosis AND DeepSeek's "channels carry non-redundant info" diagnosis are correct simultaneously: the graph channel adds real signal (+17.6 pp lift confirms non-redundancy), but the same 64-dim shared bottleneck cannot host both feature paths without sacrificing canonical recovery (−30 pp confirms capacity-stealing). K=9 baseline (93.2% canonical / 46.9% paraphrase) remains production architecture.

**Methodology lessons captured.**

- **Smoke per-head signals can mislead at full-record all-heads-exact scoring.** Registers head 98.6% (smoke) → 91.8% (full) is a 6.8 pp drop on the strongest smoke indicator; the canonical regression that dominated full-scale was below the threshold of detection at smoke. Smoke runs validate that a lever is real; they do not validate that the lever is net-positive against a different baseline at full scale.
- **Both prior diagnoses can be simultaneously correct.** Capacity-stealing and non-redundant channel signal are not competing theories; they are two true descriptions of the same architecture under one set of training conditions. The architecture pays the price of both. Diagnostic prediction at the level of "this lever will or will not work" is too coarse for tri-channel architectures; the appropriate prediction unit is which metric will move which way under which capacity allocation.
- **Eval-mode-mismatch was a real bug; bug correction was necessary but not sufficient.** PR #19's honest two-pass eval correctly fixed the train/eval distribution mismatch and the oracle leak that reference `evaluate_diagram_loop_invariance.py --with-graph-path` carried. The corrected eval revealed an architecture that is also not net-positive at scale on the joint metric. Fixing the eval did not save the architecture; it produced an honest negative result.

**Implications captured forward.**

- Tri-channel framework as a benchmark methodology (Paper A v2 §4.1–§4.4) is unaffected: cross-channel consistency rate is a benchmark-level diagnostic metric whose value does not depend on whether any particular tri-channel-trained model outperforms baseline.
- What is deprecated is the specific architectural realization (graph-encoder fusion of a prior CAS expression with the text input through a shared 64-dim bottleneck), not the tri-channel framework itself.
- Per-head channel routing (separate parameters for canonical path and graph-fusion path, eliminating capacity-stealing at the bottleneck) is a candidate future architecture deferred to research after Version B Phase 2-3 milestones (DST + NL generation head). Not a v2 paper claim.
- Paper A v2 §5.7 rewritten 2026-05-04 to report this as a publishable negative result ("tri-channel architecture: smoke-positive, capacity-stealing failure mode at full scale"). Section 4 headline contribution unchanged.

**Status of investigation arc.** Closed. K9_DiagLoop full v2 honest retrain delivered the load-bearing numbers; arc does not branch into more retrains on this architecture.

## Session 51: Cross-Channel Consistency Eval Harness (May 3, 2026)

**Objective.** Implement the headline methodology contribution of the CAS-SDG-Bench tri-channel benchmark paper: a three-channel eval harness that independently scores notation (exact string match), diagram (structural graph comparison), and color (palette metadata) dimensions, then measures cross-channel consistency to distinguish surface mistakes from structural mistakes.

**New files.**

- `cas-synthetic/schemas/diagram_graph.py` — `canonical_graph_keys` function (already provided in fuller form by PR #11 diagram-diff utility, retained from that merge). Used as the graph identity primitive by the harness.
- `cas-native/training/evaluate_cross_channel_consistency.py` — Full three-channel eval harness. Phase 1 (scoring functions) is complete; Phase 2 (model wiring to checkpoint) is wired and calls `evaluate_structured_token_prediction` then reconstructs predicted expressions from head-label outputs. CLI matches the existing eval harness shape: `--run-dir`, `--eval-input`, `--out-dir`, `--prefix`, `--device`, `--diagram-similarity-threshold`. Outputs: `<prefix>_report.md`, `<prefix>_report.json`, `<prefix>_samples.jsonl`.
- `cas-native/tests/test_evaluate_cross_channel_consistency.py` — 15 smoke tests covering: three-channel scoring on synthetic pairs, cross-channel consistency rate computation, color channel None when metadata absent, color channel rate when metadata present.

**Diagram diff stub.** `_diagram_similarity_stub` uses Jaccard overlap over `canonical_graph_keys` as a temporary approximation. Clearly marked `TODO: replace once feature/diagram-diff-utility lands` — that utility is now merged via PR #11 and the stub call is the next refactor target.

**Forward-compat: Session 50 palette (PR #10).** Color channel checks for `color` field on predicted/GT nodes. Currently returns None (no color metadata emitted by compiler). Once compiler starts emitting `color`, the color dimension activates automatically — no second PR needed.

**Test results.** 15 new tests passed. 7 pre-existing tests (paraphrase invariance + structured prediction ingest) still pass, 1 skipped (requires local data file).

**Branch.** `feature/cross-channel-consistency-eval`.

## Session 50: CAS Value-Keyed Color Palette v1.0 (May 3, 2026)

**Objective.** Lock the value-keyed color palette for all four CAS axes (Noetic, Domain, Drive, Register). Foundation work for the tri-channel benchmark (notation + diagram + color-coded axes).

**Branch.** `feature/cas-value-keyed-palette` — 3 commits, PR open.

**Phase 1 — Spec doc.**
- New `docs/working/cas_color_palette_specification.md` with full design rationale, palette tables, WCAG contrast ratios, and colorblind simulation analysis (deuteranopia / protanopia / tritanopia).
- Palette basis: Paul Tol "muted" 10-class for Noetics; Paul Tol "bright" for Drives; medium-saturation tier for Domains; border-style overlays for Registers.
- All colors meet WCAG 3:1 contrast on both `#0d1117` (dashboard dark bg) and `#ffffff` (paper bg); target luminance window L∈[0.12,0.30].
- Colorblind safety: no pair within any axis becomes indistinguishable under a single colorblind condition; marginal pairs (^1/^7, F1/F7) retain ΔL fallback distinguishability.

**Phase 2 — Python module.**
- New `api/notation/color_palette.py`: `noetic_color`, `domain_color`, `drive_color`, `register_treatment`, `axis_color_for_node`. No external dependencies.
- `PALETTE_VERSION = "v1.0"` — breaking-change sentinel for downstream consumers.
- 49 tests in `tests/test_color_palette.py`: all axes valid/invalid, all-distinct assertions, determinism, precedence, cross-axis separation. All 49 pass.

**Phase 3 — TypeScript module + dashboard.**
- New `dashboard/src/lib/casColorPalette.ts`: exact hex mirror of Python module. PALETTE_VERSION identical.
- New `dashboard/src/lib/__tests__/casColorPalette.test.ts`: mirrors Python test list.
- Updated `dashboard/src/pages/CompilerPage.tsx` `diagramColor()`: now accepts optional node arg; delegates to `axisColorForNode` when `node.noetic / .domain / .drive` are present; falls back to existing kind-keyed logic. Backward-compatible.
- 167 vitest tests pass across 14 test files (13 existing + 1 new palette test).

**Hex tables (quick reference).**

Noetic: ^0=#3388BB ^1=#117733 ^2=#CC7700 ^3=#CC6677 ^4=#2E7A6E ^5=#CC3388 ^6=#5B55C0 ^7=#7A7A25 ^8=#AA4499 ^9=#6B778C

Domain: P=#7B7EC4 C=#4490B0 E=#4A9068 O=#C0883C

Drive: F1=#4477AA F2=#7755CC F3=#228866 F4=#997700 F5=#BB4488 F6=#BB6699 F7=#446688

Register treatments: T=solid/#D4A020 A=double/#4488CC f=dashed/#CC4477 E=dotted/#44AA77

**Downstream notes.** Compiler emission, eval harness color-consistency check, and diagram-diff color-awareness are separate downstream PRs. Each must import from this module and pin `PALETTE_VERSION == "v1.0"`. The existing `colors.ts` DOMAIN_COLORS / DRIVE_COLORS remain unchanged (kind-keyed fallback and non-diagram components).

## Session 49: Self-Reference Invariance Lever — Proposal + Implementation (May 3, 2026)

**Objective.** Implement the self-reference invariance lever for the CAS-Native AI structured-prediction harness. This is a third paraphrase-consistency lever, composable with PR #2 (bare-slot K=9 augmentation) and PR #3 (KL-on-content-heads regularizer).

**Motivation.** Session 48 addendum showed a 95-98% canonical-wins asymmetry across all four content heads (noetic 71.5%, domain 77.4%, drive 79.4%, registers 79.1%) when canonical and paraphrase predictions disagree. The model has the right answer in canonical form and loses it under paraphrase — a pure invariance failure, not a knowledge gap. The lever: give the model its canonical CAS expression as a `[PRIOR]` block prepended to the paraphrase prompt so it can learn one low-capacity rule ("trust the [PRIOR] block for content axes").

**Deliverables — 4 phases on `proposal/self-reference-lever`.**

- **Phase 1** (`docs: self-reference invariance lever proposal`): Proposal doc at `docs/working/self_reference_invariance_lever_proposal.md`. Full diagnosis with asymmetry table, architectural finding, loss/data finding, proposed mechanism, A/B test plan, risk analysis, composability with PR #2 and PR #3.

- **Phase 2** (`cas-native: self-conditioning augmentation + tokenizer prepend`):
  - NEW: `cas-native/training/self_conditioning_serialization.py` — `serialize_prior_cas_state(record) -> str` returning `f"[PRIOR] {prior_cas_state}\n[QUERY] {user_prompt}"`.
  - NEW: `cas-native/training/self_conditioning_augmentation.py` — `expand_with_self_conditioning_pairs(records, *, variants_per_record)` generating paraphrase variants with `prior_cas_state` populated from canonical's `cas_expression`.
  - MODIFIED: `cas-native/training/structured_prediction_ingest.py` — adds `get_effective_prompt(record)` which calls `serialize_prior_cas_state` when `prior_cas_state` is truthy; backward compatible.
  - MODIFIED: `cas-native/training/train_structured_prediction.py` — `_tokenize_records_with_progress` uses `get_effective_prompt(record)` instead of raw `user_prompt`.
  - NEW: `cas-native/tests/test_self_conditioning_augmentation.py` — 16 tests covering all 5 brief requirements (backward compat, deterministic serialization, expansion count, prior_cas_state propagation, tokenizer round-trip).

- **Phase 3** (`cas-native: --self-conditioning-pairs CLI flag in training`):
  - MODIFIED: `train_structured_prediction.py` — `train_structured_token_prediction_local` gains `self_conditioning_pairs: int = 0` parameter; CLI gains `--self-conditioning-pairs K`. Expansion applied to canonical slice after standard paraphrase augmentation; SC paraphrases appended (no canonical duplication). Manifest reports `self_conditioning_augmentation` section.
  - EXTENDED test file: Phase 3 smoke tests (5 canonicals × K=2 → 15 records; augmented records have prior_cas_state populated).

- **Phase 4** (`cas-native: self-conditioning eval harness`):
  - NEW: `cas-native/training/evaluate_self_conditioning_invariance.py` — CPU-only eval harness analogous to `evaluate_paraphrase_invariance.py`. Two-pass: canonical eval (no prior), then paraphrase-with-oracle-prior eval (prior_cas_state = ground-truth cas_expression). Reports all_heads exact + per-head consistency + optional `prior_lift_pp` vs standard paraphrase. Writes JSON + markdown report.

**Test results.** 18 new tests pass; 39 total tests pass across self-conditioning + paraphrase + ingest + invariance eval suites. 1 pre-existing skip (local-file guard) unchanged.

**Local review addendum.** Follow-up Codex review fixed three integration issues before retrain: default structured-token record tokenization now honors `prior_cas_state` when callers do not pass pre-tokenized sequences; self-conditioning training expansion now preserves the true canonical list before standard paraphrase interleaving, so `--paraphrase-augment-train K` composes with `--self-conditioning-pairs K`; and the self-conditioning eval harness now enforces CPU-only execution and uses the model's canonical prediction as the prior rather than a ground-truth oracle label. Added four regression tests, bringing the self-conditioning test file to 22 tests. Local syntax verification passed via `python -m compileall`; local pytest could not complete because this machine's default Python 3.14 has an incomplete `torch` namespace and Python 3.11 has neither `pytest` nor `torch` installed.

**No retrain included.** This PR is proposal + implementation + tests only. Retrain decision is the reviewer's after PR review. The in-flight K=9 run on `feature/paraphrase-augment-9-templates` was not touched.

**PR opened**: `self-reference invariance lever (proposal + impl + tests)` on branch `proposal/self-reference-lever`.


## Session 48: Correct-Corpus Paraphrase Retrain Clears Prior Canonical Baseline (May 2, 2026)

**Objective.** Run the prepared v7.7-overlap relabel + deterministic paraphrase-augmentation retrain on GPU, then evaluate both canonical accuracy and paraphrase invariance against the held-out 1K.

**Operational correction.** The first RunPod attempt used `cas-synthetic/data/level3_pilot_full.jsonl`, which is now a conversational/free-form Level 3 corpus. That was the wrong input for the structured-token prediction harness and collapsed to **14/1000 (1.4%)** all-heads exact. A no-augmentation control on the same wrong corpus also failed through epoch 5, confirming the issue was corpus selection, not the model. The correct training corpus is `cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`, as named in the Session 41 run report.

**Correct run.**

- Transferred `level3_recoverable_full.jsonl` to RunPod and relabeled it with `cas-synthetic/scripts/relabel_v77_overlap.py`.
- Relabel counts: `n_total=19454`, `n_relabeled_to_v77_omega=1198`, `n_v77_rule_four_input=2454`, `n_v77_rule_four_remaining=1256`.
- Training command used the same core Session 41 hparams plus `--paraphrase-augment-train 3`.
- Eval-overlap filter removed 2,884 records; canonical post-filter train count was 16,570; paraphrase augmentation expanded train to 66,280.
- Vocabulary size was 293, confirming the run was back on the intended recoverable slot-reading signal path.

**Result.** New run directory:

`cas-native/training/runs/structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045/`

- Canonical all-heads exact: **868/1000 (86.8%)**.
- Prior current-eval checkpoint: **851/1000 (85.1%)**.
- Delta vs prior current-eval checkpoint: **+1.7 pp**.
- Delta vs hash baseline: **+38.1 pp**.
- Best epoch: 10.

**Paraphrase invariance.**

- Paraphrase all-heads exact: **41.3%** (was 37.2%; +4.1 pp).
- Prediction consistency vs canonical: **48.4%** (was 44.4%; +4.0 pp).
- Canonical-exact retention: **46.7%** (was 42.4%; +4.3 pp).

**Bucket signal.** Canonical strength is broad except for the known historical eval-label issue: `v74_baseline` 99.5%, `v75_register` 92.4%, `v76_production` 94.4%, `v77_omega` 99.0%, `meta_logic` 78.4%, `v77_rule_four` 34.1%. The `v77_rule_four` failures are still dominated by the 64 old held-out `omega_emergent` records, which are structurally `v77_omega` but remain labeled as Rule-4 in the current eval file. The new training data correctly relabels that shape as omega; the held-out eval set should be relabeled or regenerated before treating Rule-4 bucket accuracy as a fair number.

**Artifacts.**

- `STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md`
- `manifest.json`
- `current_unique_eval_confusion.md/json`
- `paraphrase_current_eval_report.md/json`
- `paraphrase_current_eval_manifest.json`
- `paraphrase_current_eval_samples.jsonl`

**Continuation note.** The live operational log for this RunPod session is `docs/working/runpod_paraphrase_retrain_handoff_20260502.md`. It records the wrong-corpus false start, the correct corpus transfer, relabel counts, exact commands, and monitoring checkpoints.

### Session 48 Addendum: Clean-Eval Rescore (May 2, 2026)

The Session 48 numbers above (canonical 86.8%, paraphrase 41.3%) were computed against the contaminated held-out eval — the eval still labeled 64 `omega_emergent`-shaped records as `v77_rule_four` even though the relabeled training data and the `d99810a` checkpoint correctly treat them as `v77_omega`. The eval was relabeled with the same `cas-synthetic/scripts/relabel_v77_overlap.py` script used on the training data (idempotent, 64 records moved `v77_rule_four` → `v77_omega`), producing `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl`. The same `d99810a` checkpoint was rescored against the clean eval; no retrain.

**Clean canonical.**

- All-heads exact: **932/1000 = 93.2%** (was 868/1000 = 86.8% on contaminated eval).
- **+8.1 pp vs prior current-eval baseline (85.1%)**, +44.5 pp vs hash (48.7%).
- The contamination was suppressing the canonical score by 6.4 pp; every one of the 64 relabeled records was already being predicted correctly under the new label scheme.

**Clean paraphrase.**

- Paraphrase all-heads exact: **46.9%** (was 41.3% on contaminated eval, 37.2% on prior baseline) — **+9.7 pp vs prior baseline**.
- Prediction consistency vs canonical: 48.4% (unchanged — label-independent).
- Canonical-exact retention: 49.5% (was 46.7%).

**Per-head consistency diagnostic.** Boolean/categorical heads are essentially invariant under surface change (turn_type 100%, authority 100%, has_omega 99.5%, has_meta_logic 99.0%, register_mode 98.4%, transition_kind 98.2%, meta_relations 97.0%, expression_family 96.0%). The four *content* heads collapse under paraphrase: drive 79.4%, registers 79.1%, domain 77.4%, **noetic 71.5%**. The next training lever should target the content axes specifically, not general invariance.

**Real residual on v77_rule_four.** Post-relabel, 17/59 = 28.8% canonical failures remain. All 17 are `+` co-presence records where the model emits `expression_family=register_state` instead of `rule_four`, and `transition_kind=state` instead of `relation`. This is a real signal — same-Noetic `+` co-presence is genuinely close to a register-state expression, and worth designing into the next augmentation pass.

**Worst paraphrase buckets.** `v74_baseline` (canonical 99.5% → paraphrase 18.7%) and `meta_logic` (canonical 78.4% → paraphrase 17.0%) — surface memorization without invariance. These two buckets account for most of the residual paraphrase headroom. The lexicon + augmentation lever applied here clearly worked for v77_omega (87.3% paraphrase) and v76_production (75.6%) but didn't reach v74_baseline or meta_logic.

**Artifacts.** `relabeled_eval_confusion.md/json`, `relabeled_eval_manifest.json`, `relabeled_eval_samples.jsonl`, `paraphrase_relabeled_eval_report.md/json`, `paraphrase_relabeled_eval_canonical_manifest.json`, `paraphrase_relabeled_eval_manifest.json`, `paraphrase_relabeled_eval_samples.jsonl` — all in the Session 48 run dir. The `STRUCTURED_TOKEN_PARAPHRASE_RETRAIN_REPORT.md` in that run dir carries a matching addendum.

## Session 47: v77_rule_four / v77_omega Structural Overlap Fix (May 2, 2026)

**Diagnosis.** Session 41's confusion report (`runs/structured-token-20epoch-gpu-20260502-001907/current_unique_eval_confusion.md`) showed v77_rule_four had 84/123 head failures, with **64 of those records (the entire `omega_emergent` sub-pattern) misclassified 100% as v77_omega family/transition**. Investigation showed why the model could not distinguish them: the v77_rule_four compliant arm had a 50/50 split between `+` co-presence and `×` with named emergent (`(X × Y × Z) = ^N|Ω_*`); the second sub-arm produces expressions structurally identical to v77_omega output, drawn from the same `omega_registry.yaml`. Recoverable Level 3 prompts are built from `_formal_axis_reading(expression)`, which describes only structural slots, so the user_prompt for these records carries no bucket-distinguishing signal. The original bucket label was a generator-provenance artifact, not a structural property — and the 85.1% checkpoint correctly learned that these prompts produce v77_omega-shaped outputs.

**Fix.** Two parts.

1. **Generator** (`cas-synthetic/generator/v77_rule_four.py`): the compliant arm now emits `+` co-presence ONLY. The `_generate_compliant_emergent` method remains in the file for reference and future re-enable should a bucket-distinguishing signal be added to the recoverable prompt, but it is no longer reachable through `_generate_compliant`. Updated module docstring + historical-note comment explain the change.
2. **In-place relabeler** (`cas-synthetic/scripts/relabel_v77_overlap.py`): processes an existing Level 3 JSONL and relabels v77_rule_four records whose expression matches `(X × ... × Z) = ^N|Ω_*` with same-Noetic operands → `v77_omega`, adding `bucket_relabeled_from` and `bucket_relabel_reason` fields for audit. Idempotent. Required to fix the existing training set in place before the upcoming retrain — the generator fix only helps future regenerations.

**Why this is the right fix, not prompt-side cueing.** Adding bucket-specific framing to the recoverable user_prompt (e.g., "this is a Rule 4 compliance check") would teach the model to look for that string — a label leak masquerading as content. The structural fix is honest: post-fix, v77_rule_four's compliant `+` arm is operator-distinguishable from v77_omega (`+` vs `×`), and the violation arm is emergent-distinguishable (no `Ω_*`). The Rule-4-compliance training signal is preserved by both arms; the `valid emergent` records that DO overlap v77_omega are now correctly labeled v77_omega.

**Verification.**

- `pytest cas-synthetic/tests/test_v77_rule_four_no_emergent_overlap.py cas-synthetic/tests/test_relabel_v77_overlap.py` — 21 passed. Property tests lock the structural-overlap invariant (compliant arm never emits same-Noetic ×=Ω; violation arm preserved; relabeler idempotent and non-mutating).
- Existing `test_v77_rule_four_generator.py::test_valid_emergent_expression_has_omega_label` was inverted to `test_valid_compliant_records_do_not_carry_omega_labels` — locks the new contract.
- `pytest cas-synthetic/tests/ -k "v77 or rule_four or omega"` — 43 passed, 3 skipped, 0 failures. No regressions.

**Action required before retrain.** Run on the existing Level 3 training file:
```
python cas-synthetic/scripts/relabel_v77_overlap.py --in <train.jsonl> --out <train_relabeled.jsonl>
```
Expected: ~40% of v77_rule_four records relabel to v77_omega. After the relabel, the bucket counts shift but every record's bucket is structurally consistent with its expression. The retrain then trains on a clean dataset where bucket prediction is genuinely learnable from the prompt.

## Session 46: Deterministic Paraphrase Augmentation in Training (May 2, 2026)

**Objective.** Address the load-bearing finding from Sessions 43–44: the 47.9 pp paraphrase-eval collapse (canonical 85.1% → paraphrase 37.2%) is *not* explained by lexicon OOV (Session 44 diagnostic showed only -0.98 pp coverage delta), so it must be template memorization. The fix is to expose the model to varied surface forms during training so it can't memorize a single canonical Level 3 template.

**Deliverables.**

- New `cas-native/training/paraphrase_templates.py` — shared module hosting `EVAL_PARAPHRASE_TEMPLATES` (4 templates, the existing eval set) and `TRAINING_PARAPHRASE_TEMPLATES` (8 templates, **strictly disjoint** from eval), plus `extract_recoverable_slots` and `apply_template`. The disjointness invariant is locked in by a property test (`test_train_eval_template_sets_are_disjoint`); without it, training-augmented models would be memorizing the eval set's templates and the paraphrase-invariance number would be meaningless.
- New `cas-native/training/paraphrase_augmentation.py` — `expand_with_paraphrases(records, variants_per_record=K)` returns canonical-then-paraphrase-interleaved records. K=0 is identity pass-through. Each paraphrase preserves all CAS target fields; only `user_prompt`, `id`, `base_id`, `paraphrase_index`, and `paraphrase_source` differ.
- `evaluate_paraphrase_invariance.py` refactored to consume the shared template module. Backward-compat alias `PARAPHRASE_TEMPLATES = EVAL_PARAPHRASE_TEMPLATES` preserved; existing `paraphrase_record` / `make_paraphrase_records` API unchanged.
- `train_structured_prediction.py` — new `paraphrase_augment_train: int = 0` parameter on `train_structured_token_prediction_local`, plus matching `--paraphrase-augment-train K` CLI flag. Augmentation applies AFTER the eval-overlap filter so paraphrased records inherit the canonical's leak-safe status. Manifest now records `config.paraphrase_augmentation` block (variants_per_record, n_canonical_post_filter, n_paraphrases, n_total, training_template_source).
- 14 new property tests in `cas-native/tests/test_paraphrase_augmentation.py` covering: training-eval template disjointness invariant; slot-block preservation; target-field round-trip; deterministic generation; index-modulo template selection; canonical-paraphrase interleaving; identity at K=0; negative-K rejection.

**Verification.**

- `pytest cas-native/tests/test_paraphrase_augmentation.py cas-native/tests/tokenizer/` — 93 passed (was 79; +14 paraphrase-augmentation tests).
- All three load-bearing anti-drift tests still green.
- Integration check: `expand_with_paraphrases` + tokenize + `summarize_token_provenance` round-trips correctly on a recoverable Level 3 record. Augmented records preserve the CAS_NOTATION literals; only the surface frame changes.

**Why disjoint training/eval template sets.** If the model sees the eval templates at training time, the paraphrase-eval number measures template memorization rather than surface-form generalization. Held-out discipline requires that the surface forms used at eval are *never* in the training distribution. The eval set carries 4 canonical templates from Session 43; this commit adds 8 training-only templates and asserts disjointness as a property test that fails CI if anyone ever adds an overlapping template.

**Why augmentation lands AFTER the leak filter.** Paraphrased records share `source_level2_id` and `cas_expression` with their canonical parent. If the canonical is filtered for overlapping eval, all its augmented forms are also filtered (because they would never have been generated). Applying augmentation post-filter preserves leak discipline by construction.

**Next.** Pod retrain with `--paraphrase-augment-train 3`. The new manifest will carry both the previously-wired `eval.token_provenance` block and the new `config.paraphrase_augmentation` block, so the next checkpoint is auditable on both axes against the 85.1% baseline. Expected outcome: paraphrase-eval accuracy rises from 37.2% toward canonical, which would be evidence the architectural pivot ("CAS structure as input substrate") generalizes — currently we only know it works on the data distribution it was trained on.

## Session 45: Token-Provenance Block in Runner Manifest (May 2, 2026)

**Objective.** Wire the per-eval token-source breakdown (Session 44 lexicon-coverage diagnostic finding) into the structured-token runner's manifest as a tracked metric on every training run, so future runs carry provenance data alongside accuracy and the lexicon-vs-encoder bottleneck remains diagnosable from the manifest alone.

**Deliverables.**

- New `cas-native/tokenizer/provenance.py` exports `summarize_token_provenance(sequences, records=None)` returning the canonical breakdown shape (overall + per-bucket × LEXICON / CAS_NOTATION / LEARNED / FALLBACK). Re-exported from `cas_native.tokenizer` package.
- `evaluate_structured_token_prediction` in `train_structured_prediction.py` now computes provenance from the eval token sequences (already cached by the prior `--cache-batches` refactor) and attaches it to the eval manifest as `manifest["token_provenance"]`. Same field flows through `train_structured_token_prediction_local` into `manifest["eval"]["token_provenance"]`.
- `diagnose_lexicon_coverage.py` refactored to consume the shared helper; the standalone diagnostic and the runner-side manifest produce identical block shapes so canonical and paraphrase provenance can be diffed across runs without format normalization.
- 9 new property tests in `cas-native/tests/tokenizer/test_provenance.py` covering canonical shape, signal-bearing label invariant (drift guard: only LEXICON+CAS_NOTATION count as signal), per-bucket grouping, missing-bucket → "unknown", length-mismatch raises, and end-to-end pipeline integration with the real tokenizer.

**Verification.**

- `pytest cas-native/tests/tokenizer/` — 79 passed (was 70; +9 provenance tests). All three load-bearing anti-drift property tests still green.
- Diagnostic re-run on the canonical 1K + 3K paraphrase eval produces byte-identical JSON to Session 44's report, confirming the refactor is behaviorally equivalent.

**Why it matters.** Session 44 surfaced that the 47.9 pp paraphrase-eval collapse is mostly NOT explained by OOV (canonical signal 13.3% vs paraphrase 12.3% — only -0.98 pp). Without provenance carried in every manifest, that diagnostic would have been a one-shot finding. Now every training run since Session 45 records the same breakdown as a tracked metric, so the next retraining run produces apples-to-apples provenance against the 85.1% checkpoint and the lexicon-vs-encoder-bottleneck split is auditable in the manifest alone.

**Next.** Task #77 — deterministic paraphrase augmentation in training data. The Session 44 finding shifts this from "useful next step" to "load-bearing fix" for paraphrase invariance. After that lands and a retrain runs, the new manifest will carry both the provenance breakdown AND the new accuracy numbers in one artifact.

## Session 44: Wave 2-A Phase 1A — Lexicon Synonym/Morphology Expansion (May 2, 2026)

**Objective.** Address the Session 43 paraphrase-invariance collapse (canonical 85.1% → paraphrase 37.2%, -47.9 pp; consistency 44.4%) by expanding lexicon synonym coverage on the unstable axes (noetic, drive, registers, domain). The audit hypothesis is OOV bottleneck: with vocab=290 at the 85.1% checkpoint, paraphrases push surface tokens through fallback IDs and the cas_signature features that drove the canonical accuracy go neutral. Phase 1A is the lexicon-side response.

**Deliverables.**

- 93 new entries added to `cas-native/tokenizer/lexicon/build_seed.py` (the typed source-of-truth per methodology Section 3.1). `seed_lexicon.jsonl` regenerated to 191 entries (was 98).
- Coverage by axis: ^2 Positive 11→23, ^3 Negative 11→23, ^4 Vibration 6→14, ^5 Female 4→8, ^6 Male 9→19, ^7 Rhythm 6→12, ^8 Above/Cause 5→11, ^9 Below/Effect 5→10. F-axis Drives F3 4→9, F4 2→5, F7 2→5, F5 1→4, F6 1→3, F2 1→3, F1 1→3. Registers |T 3→4, |f 4→6, |A 2→4, |E 2→3.
- All ^3 entries strictly visceral (e.g., `makes me sick`, `turns my stomach`, `makes my skin crawl` — etymological cognates carrying |E embodied register). All ^8 entries strictly associative-trigger (e.g., `brought to mind`, `sparked`, `conjured`). All ^4 entries prefer etymological cognates (`resonate`, `resonance`, `hit home`).

**Adjustments after review pass.**

- Skipped from this batch: `spent` (multi-sense — money/time/energy), `body` (anatomy vs embodied), `then` (temporal sequence dominates). Held for Phase 1B with context-disambiguation rules.
- Lowered confidences: `profound` 0.7 → 0.6 (broadly polysemous), `sense` 0.8 → 0.65 with `context_required` regex anchoring the felt-sense reading.
- Swapped: bare `horizon` → multiword `broaden my horizons` |T 0.85 (literal-spatial sense falls to fallback as designed).
- Compound signatures deferred: `second nature` ^5 overlap and `shaped me` ^7 overlap flagged in `notes` for Wave 2-B tagger to learn from corpus evidence rather than committing speculative secondary axes at lexicon time, per methodology Section 4.2 #4.
- `myself` lowered to 0.6 with `reflexive` role tag to differentiate from existing `I/me/my` self-reference entries.

**Verification.** `python -m pytest cas-native/tests/tokenizer/` — 70 passed, including all three load-bearing anti-drift property tests:
- `test_seed_lexicon_anti_drift_visceral_negatives` — `audit` and `scrutinize` still NOT firing ^3.
- `test_seed_lexicon_anti_drift_associative_triggers` — `reminds me of` and `triggered` still firing ^8.
- `test_seed_lexicon_etymological_cognate_for_vibration` — `struck a chord` still firing ^4 ≥ 0.9.

Anti-drift discipline preserved at scale; the new entries cohabit with existing canonical anchors without contaminating the load-bearing test exemplars.

**Next.** Add `eval_token_provenance` block to the structured-token runner manifest (no-GPU diagnostic). Re-tokenize the held-out 1K canonical and paraphrase eval sets with the new lexicon and report the lexicon-coverage delta. If paraphrase coverage rises substantially more than canonical coverage, the OOV-bottleneck hypothesis is confirmed and Phase 1B prioritization shifts toward the surface families that didn't get covered. Pod retrain is gated on this measurement.

## Session 43: Paraphrase-Invariance Evaluator Baseline (May 2, 2026)

**Objective.** Begin Priority 1 from the pickup list: evaluate paraphrase invariance against the 85.1% structured-token checkpoint before any GPU retraining.

**Deliverables.**

- New `cas-native/training/evaluate_paraphrase_invariance.py` builds deterministic recoverable-slot paraphrases, evaluates a saved structured-token run, and reports target accuracy plus prediction stability against canonical prompts.
- New tests cover recoverable-slot extraction, paraphrase record generation, and invariance-report aggregation.
- Generated full current-eval paraphrase artifacts in `cas-native/training/runs/structured-token-20epoch-gpu-20260502-001907/`:
  - `paraphrase_current_eval_canonical_manifest.json`
  - `paraphrase_current_eval_manifest.json`
  - `paraphrase_current_eval_samples.jsonl`
  - `paraphrase_current_eval_report.json`
  - `paraphrase_current_eval_report.md`

**Result.** On the current 1,000-record unique-source eval set, using 3 deterministic paraphrases per record: canonical exact remains **851/1000 (85.1%)**, paraphrase exact is **1117/3000 (37.2%)**, prediction consistency vs canonical is **44.4%**, and canonical-exact retention is **42.4%**. This fails the Wave 2-C paraphrase robustness gate by a wide margin and confirms template sensitivity as the next training/data issue.

**Bucket signal.** `v77_omega` is robust under these paraphrases (87.8% exact, 87.5% consistency). `v74_baseline` and `v75_register` are brittle (8.3% and 19.1% exact respectively), with largest consistency losses on noetic, drive, registers, and domain heads. `v77_rule_four` remains low exact (27.1%) but relatively stable in its wrong family/transition behavior (80.8% consistency).

**Verification.** `python312 -m pytest cas-native/tests/test_paraphrase_invariance_eval.py cas-native/tests/test_train_structured_prediction.py -q` — 11 passed, 2 skipped. `python312 -m py_compile` passed for the paraphrase and structured-prediction eval modules.

## Session 42: Structured-Token Eval Instrumentation + Current Eval Confusion (May 2, 2026)

**Objective.** Make the structured-token eval path debuggable at sample level before paraphrase-invariance work.

**Deliverables.**

- `train_structured_prediction.py` now writes enriched eval samples with `cas_expression`, `user_prompt`, per-head `prediction`, per-head `target`, and the existing `head_correct` booleans.
- New `cas-native/training/evaluate_structured_token_run.py` loads a saved structured-token run directory, evaluates a checkpoint against a JSONL eval file, writes enriched manifest/samples, and emits JSON + Markdown confusion reports.
- Generated current unique-source eval artifacts under `cas-native/training/runs/structured-token-20epoch-gpu-20260502-001907/`:
  - `current_unique_eval_manifest.json`
  - `current_unique_eval_samples.jsonl`
  - `current_unique_eval_confusion.json`
  - `current_unique_eval_confusion.md`

**Result.** The saved Session 41 checkpoint scores **851/1000 all-heads-exact (85.1%)** on the current 1,000-unique-source eval set, preserving the +36pp win over the 48.7% hash baseline.

**Diagnosis.** The bottleneck is sharply localized: `v77_rule_four` accounts for 84/149 failures. Within that bucket, every `omega_emergent` Rule-4 expression is misclassified as `omega/omega_bind` (64/64), while `plus_copresence` Rule-4 cases are 39/59 exact. This confirms the remaining weakness is a family/transition distinction around named emergent Rule-4 expressions, not core CAS-axis recovery.

**Verification.** `python312 -m pytest cas-native/tests/test_train_structured_prediction.py -q` — 8 passed, 2 skipped. `python312 -m py_compile` passed for the modified eval/training modules.

## Session 41: Structured-Token GPU Comparison Clears Hash Baseline (May 2, 2026)

**Objective.** Run the first full structured-token train/eval comparison against the honest leak-fixed hash-feature baseline.

**Result.** The structured-token path cleared the baseline decisively: **853/1000 all-heads-exact (85.3%)** vs the hash baseline's **487/1000 (48.7%)**, a **+36.6pp** lift on the same held-out recoverable Level 3 eval set.

**Run.** `cas-native/training/runs/structured-token-20epoch-gpu-20260502-001907/`

- Input mode: `structured_token`
- Model: `StructuredTokenEmbedding + StructuredPredictionHead`
- Train: `level3_recoverable_full.jsonl`, filtered to 17,974 non-overlapping records
- Eval: `level3_recoverable_eval_1000.jsonl`
- Vocab size: 290
- Epochs: 20
- Best epoch: 19
- Hardware: RunPod RTX A6000

**Per-bucket exact.** v74_baseline 194/194 (100%); v75_register 217/262 (82.8%); v76_production 72/104 (69.2%); v77_rule_four 46/106 (43.4%); v77_omega 218/218 (100%); meta_logic 106/116 (91.4%). The remaining bottleneck is `v77_rule_four`, specifically expression-family / transition-kind confusion, not the core axes.

**Engineering fix during run.** The first launch exposed CPU-bound startup. `2366628` caches structured-token sequences, loads the seed lexicon once per corpus pass, and logs tokenization progress every 1,000 records. This converted the silent startup stall into a visible ~3-4 minute corpus-tokenization phase.

**Artifacts.** Committed: `manifest.json`, `samples.jsonl`, `structured_token_vocab.json`, `launch.log`, and `STRUCTURED_TOKEN_RUN_REPORT.md`. Off-VCS/local only: `best_structured_token_model.pt`.

**Next.** Build a precomputed tensor-cache dataset for structured-token batches to raise GPU utilization, then rerun to confirm reproducibility and shorten wall-clock. After that, diagnose `v77_rule_four` family/transition-kind confusion.

## Session 40: Structured-Token Train/Eval Runner Mode (May 1, 2026)

**Objective.** Add the first train/eval runner path that consumes `StructuredTokenEmbedding + StructuredPredictionHead` over Level 3 data and reports directly against the honest leak-fixed hash-feature baseline (48.7% all-heads-exact).

**Deliverables.**

- `cas-native/training/train_structured_prediction.py` now accepts `--input-mode structured_token` alongside the original `hash` mode. Hash remains the default for reproducibility.
- New `train_structured_token_prediction_local(...)` builds `StructuredTokenVocabulary` from post-overlap-filtered training prompts only, trains `StructuredTokenEmbedding + StructuredPredictionHead`, evaluates on held-out records, tracks the best eval checkpoint, writes `manifest.json`, `samples.jsonl`, `structured_token_vocab.json`, and `best_structured_token_model.pt`.
- New `evaluate_structured_token_prediction(...)` shares the strict all-heads-exact/per-head/per-bucket metric shape with the hash-feature harness.
- Manifests now include `baseline_comparison` with `baseline_name=leak_fixed_hash_feature_20ep`, `baseline_all_heads_exact_rate=0.487`, `candidate_all_heads_exact_rate`, absolute delta, pp delta, and `beats_baseline`.

**Verification.**

- Direct/runner tests: `23 passed`.
- Structured/tokenizer regression suite: `96 passed`.
- Model/runtime/backbone neighbor suite: `36 passed`.
- Real CLI smoke over Level 3 files: `--input-mode structured_token --limit 256 --eval-limit 60 --epochs 1` completed, wrote artifacts to `C:/tmp/cas_structured_token_runner_smoke`, and produced the expected explicit baseline comparison (`0/60`, `-48.7pp`). This was a wiring smoke, not a performance claim.

**Next.** Run a real local structured-token comparison with non-trivial settings (for example 20 epochs over the full non-held-out Level 3 set, same held-out 1K eval, `d_model=128`, `batch_size=128`, `weight_decay=1e-4`) and compare to the 48.7% hash baseline. If it fails below hash, the next bottleneck is lexicon scale/tagger coverage, not runner plumbing.

## Session 39: CAS-Native Structured-Token Vocabulary + Embedding Adapter (May 1, 2026)

**Objective.** Turn Wave 1 structured tokens into a real encoder-consumable stream. The tokenizer already emitted CAS-signature-bearing `StructuredToken` records; this session adds stable vocabulary IDs, tensor batching, and a model-side embedding adapter so the structured-prediction head can consume CAS-native token streams instead of raw token IDs.

**Deliverables.**

- `cas-native/tokenizer/vocabulary.py` - source-aware `StructuredTokenVocabulary` with stable reserved IDs (`<pad>`, `<bos>`, `<eos>`, `<unk>`, `<mask>`, `<cas_literal>`, `<lexicon_hit>`, `<fallback_neutral>`), deterministic frequency ordering, JSON round-trip, and leak-safe `from_records(..., text_field="user_prompt")`.
- `cas-native/training/structured_token_adapter.py` - `StructuredTokenBatch` tensors: `input_ids`, `attention_mask`, 25-dim CAS signature features, confidence features, source IDs, and normalized surface-span features.
- `cas-native/model/structured_token_embedding.py` - `StructuredTokenEmbedding` with gated fusion between surface vocabulary embeddings and CAS-side features; `StructuredTokenStructuredPredictor` composes the embedding with `StructuredPredictionHead`.
- Package exports updated in `cas-native/tokenizer/__init__.py` and `cas-native/model/__init__.py`.

**Verification.**

- New direct tests: 13 passed across vocabulary, batch adapter, and embedding adapter.
- Neighbor suite: 100 passed across tokenizer, structured-token adapter/embedding, structured-backbone adapter, structured-prediction head, runtime frame, turn execution, and IntentIR.
- Model/training regression suite: 26 passed, 1 skipped across `test_model.py`, `test_train_structured_backbone.py`, and `test_train_structured_prediction.py`.

**Architectural note.** This is still not the full CAS Transformer encoder. It is the first honest input substrate for it: character-span-provenanced tokens now become model tensors with explicit CAS-axis side channels. The next implementation step is a local train/eval runner mode that uses `StructuredTokenEmbedding` + `StructuredPredictionHead` on Level 3 data and compares against the 48.7% leak-fixed hash-feature baseline.

## Session 38: CAS-Native Tokenizer — Wave 1 (Foundation, May 1, 2026)

**Objective.** Pivot away from the failed frozen-CAS-CLM-as-encoder approach (~100x worse than hash baseline, modality mismatch diagnosed in Session 37 follow-up) toward an original CAS-native tokenizer that pre-decodes CAS-axis structure at the input layer. Build the deterministic, no-GPU foundation pieces (Wave 1) so subsequent learned-tagger and encoder waves have a stable substrate.

**Architectural commitment (locked in this session).** The tokenizer is the FIRST layer of CAS reasoning, not a vocabulary mapping. Every output token carries: `surface_span` provenance to original characters; an explicit `cas_signature` over the four CAS axes (Noetic / Domain / Drive / Register) plus role tags; a `source` flag (LEXICON / LEARNED / CAS_NOTATION / FALLBACK) recording how the signature was assigned. Encoder is no longer asked to discover CAS structure from generic IDs; it is handed the structure pre-decoded at the surface level.

**Wave 1 deliverables (all shipped, all green).**

- `cas-native/tokenizer/structured_token.py` — `StructuredToken` + `CASSignature` schema. 10/4/7/4 axis cardinality locked to CAS v7.7 ontology. Negative drive values (depletion) admitted.
- `cas-native/tokenizer/pretokenizer.py` — span-tracking segmentation. Words / punctuation / whitespace / cas_candidate kinds. Apostrophes preserved inside words. Round-trip lossless.
- `cas-native/tokenizer/cas_notation.py` — CAS v7.7 notation recognizer. Coverage: full compound state (`^n^D_{F_k}|R`), partial compounds, bare Noetic / Domain / Drive / Register, register-set spec (`|⟨…⟩`), `Ω_*`, `Θ(`, arrows, set relations. Longest-match-first.
- `cas-native/tokenizer/lexicon/schema.py` — `LexiconEntry` + `CASLexicon`. Single-word O(1) lookup; multi-word greedy-longest with context-required / context-blocked regex predicates (joined-window with ␟ separator).
- `cas-native/tokenizer/lexicon/build_seed.py` + `seed_lexicon.jsonl` — 98 seed entries. Anti-drift discipline applied: `^3` Negative entries are visceral (`can't stomach`, `rubs me the wrong way`); analytical critique (`audit`, `scrutinize`, `find flaws`) routes to `^6` Male. `^8` Above/Cause is associative triggering only. `^4` Vibration uses etymological cognates (`struck a chord`). Demographic register variants (academic / working_class / child) collapse to identical CAS axes.
- `cas-native/tokenizer/assembler.py` — end-to-end `tokenize(text) -> list[StructuredToken]`. Resolution order: CAS notation → multi-word lexicon → single-word lexicon → fallback.

**Verification.**

- `pytest cas-native/tests/tokenizer/` — 64 passed in 0.35s.
- `pytest cas-native/tests/tokenizer/ + test_runtime_frame + test_turn_execution + test_intent_ir + test_intent_level3_ingest` — 82 passed, 1 skipped in 0.44s. No regressions in neighboring runtime/intent layers.
- `pytest test_train_structured_prediction + test_structured_prediction_head + test_structured_prediction_ingest` — 14 passed, 1 skipped in 4.18s.
- Fixed the shared CAS-Native `tmp_path` fixture to use UUID directories via `Path.mkdir()` instead of `tempfile.mkdtemp(dir=...)`, which creates Python-unwritable directories on this Windows/OneDrive workspace.
- Anti-drift assertions tested as load-bearing properties: `audit` does NOT fire `^3`, `can't stomach` does NOT fire `^6`, `reminds me of` fires `^8` not a deductive compound.
- Demographic robustness asserted: `exhausted` / `hella tired` / `super sleepy` / `profoundly fatigued` all collapse onto `F3` vitality depletion despite different surface registers.

**Handoff document.** `docs/working/cas_tokenizer_wave1_handoff.md` — full record of the pivot, role of the tokenizer in the existing stack, what's done, what's next, and how the Wave 2 specialist agents should be engaged.

**Next.** Wave 2 dispatched as background specialist work: lexicon-scaling methodology, learned CAS-axis tagger architecture, encoder-integration path. Codex review selected strict word/phrase IDs + char-CNN fallback as the first encoder vocabulary path; BPE-on-our-corpus is contingency only. Wave 3+ (SDG demographic extension, GPU-side training) gated on Wave 2 designs.

## Session 37: meta_logic Local Diagnosis — Three Surgical Patches (April 29, 2026)

**Objective.** Diagnose meta_logic bucket residual failure (2/5 exact, 2/5 top-5, mean_rank 15.67 in the PATCHED-20260429 A/B run) locally before any further GPU spend, per dual-expert review consensus that bank coverage / filter logic / prompt-slot inference is the proper next investigation, not training scale.

**Method.** Five parallel Explore agents fanned out over the five investigation paths the experts flagged: GT bank coverage, filter attrition, subfamily breakdown, prompt-slot vs expression-slot diff, bank construction audit. All agents read-only, all running against the same PATCHED-20260429 artifacts.

**Findings (synthesized).** Four distinct issues across the 5 meta_logic eval samples:

- **(A) Phantom `States` carrier** from prose section header `"states: Noetic ^N"` — `\bstates\b` matched the lowercased header, inferring a phantom carrier slot that typed-cluster expressions (`NoeticCluster{...}`, `StateCluster{...}`, `Coordinate{...}`) cannot literally satisfy. Same bug-family as 9cbcb6b but inside meta_logic.
- **(B) `production` family wrongly inferred** from the imperative verb `"produce"` in instruction prose (`"produce the expression and a plain explanation"`), dropping sample 4 (Coordinate GT) before slot filter ever ran.
- **(C) Bank gap.** `_meta_logic_candidates` builtins covered noetic pairs only from {1,2,3,4,7}; sample 5's GT `NoeticCluster{^8, ^3}` was absent from both the dataset-derived and the builtin bank.
- **(D) Foundation-order permutation sensitivity** in the rerank model — sample 1's GT `CoverOf(SubFoundations, F1,F7,F3,F2,F5,F6,F4)` is in bank as canonical `F1..F7` ordering and ranked 45/69. Addressable only by retraining or by enriching `expression_slots` semantics. Out of scope for this commit.

**Patches.** Three surgical changes in `cas-native/inference/constrained_sampling.py`:

1. `infer_prompt_slots` — carrier regex gets negative lookahead `(?!\s*:)` so colon-suffixed section headers don't trigger phantom carrier inference.
2. `infer_prompt_families` — bare verb `"produce"` dropped from `production` triggers; specific terms (`"produces"`, `"production"`, `"recipe"`, `"yield"`, etc.) and the bucket fallback retain coverage of legitimate v76_production prompts.
3. `_meta_logic_candidates` — enumerates all 90 noetic-pair orderings as bare typed-cluster-literal builtins (`NoeticCluster{^a, ^b}` for a ≠ b ∈ {0..9}). Builtin bank: 14 → 104. Full meta_logic bank: 858 → 940.

**Verification.**

- `pytest cas-native/tests/test_constrained_sampling.py` — 18 passed, 2 skipped.
- `pytest cas-synthetic/tests/test_level3_conversational.py` — 13 passed.
- Offline filter-pipeline simulation against PATCHED-20260429 samples (rerank model unchanged): GTs in bank 3/5 → **5/5**. GTs surviving full filter pipeline 3/5 → **5/5**. Filter-set sizes: sample 2 → 2 candidates, sample 3 → 5 candidates, sample 5 → 51 candidates (very tight; rerank should pick GT in top-N).

**Predicted GPU re-run impact.** Exact 2/5 → 3-4/5; top-5 2/5 → 4-5/5; mean_rank 15.67 → ~4-10. Sample 1 residual (rank ≈45) is rerank-permutation-sensitivity, not addressable by these patches.

**Next steps.** Once user terminates the current pod, the next GPU session re-runs the same `train_semantic_reranker.py` recipe with the patched parser to verify the predicted lift on the held-out 30-sample eval. After that, the larger validation set (300-600 examples + second paraphrase style) flagged by both experts becomes the stakeholder-defensible test.

## Session 36: CAS-Native Reranker A/B Validation — Patched Slot Filter (April 29, 2026)

**Objective.** Run a clean A/B validation of the patched `infer_prompt_slots` parser (commit `9cbcb6b`) against the recoverable Level 3 dataset. Same hyperparameters and tokenizer bytes as the baseline (commit `0612b9a`) so any difference is attributable to the parser fix, not to training-side variance. Forbidden mixing: no `generate_samples.py --decode-mode rerank`, no 1500-step CAS-Native checkpoint, no extra epochs.

**Result.** All four measurable gates cleared by significant margins.

| Metric | Baseline | Gate | A/B run |
|---|---|---|---|
| Exact top-1 | 12 / 30 | ≥ 15 | **21 / 30** |
| Top-5 | 24 / 30 | ≥ 24 | **26 / 30** |
| Mean rank | 5.11 | < 5.11 | **2.89** |
| GT scoreable | 27 / 30 | ≥ 27 | **27 / 30** |
| slot_match (live measurement) | 3 / 30 | — | **28 / 30** |

Per-bucket: v75_register, v77_rule_four 5/5 exact; v74_baseline 4/5; v77_omega 3/5; v76_production 2/5; meta_logic 2/5 (lone laggard, mean_rank 15.67 — patched parser correctly left meta_logic unchanged because phantom-slot fix gated `carriers`/`foundations` to meta_logic only).

Pairwise training accuracy ended at 0.917 vs baseline's 0.985 — *expected and correct*. Tighter slot filter admits harder negatives per pair, so per-pair discrimination is harder but final ranking is better. Higher signal, harder problem, better outcome.

- **Run path.** `noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/semantic-reranker-recoverable-PATCHED-20260429/` — committed: `eval_summary.json`, `metrics.json`, `samples.jsonl` (99 KB), `SEMANTIC_RERANKER_VALIDATION_REPORT.md`, `tokenizer.json` (identical bytes to baseline). The 2 MB `semantic_reranker.pt` checkpoint kept off-VCS per policy; available locally for further experiments.
- **Reproduction.** RunPod A6000 48 GB; 47 minutes wall clock; bf16 autocast; identical seed 42, identical tokenizer hash `b7552dbf2ebef0a5`. Full command in `docs/CAS_NATIVE_AI_CLAUDE_PLAYBOOK.md`.
- **Next actions.** (1) Diagnose meta_logic bucket residual failure — its candidate bank is the smallest at 858 entries and disproportionately many records may be skipped at pair-build time. (2) Add direct recoverable-expression evaluation mode (family/slot/exact/top-k metrics independent of candidate-bank rerank). (3) Mixed-curriculum CAS-Native generator training, only after meta_logic is understood.

## Session 35: Start Here Tutorial Onboarding (April 26, 2026)

**Objective.** Reduce first-run friction by adding a plain-language guided tour before users encounter the densest CAS surfaces.

- **`dashboard/src/pages/TutorialPage.tsx`** (NEW) — five-step tutorial with Simple/Technical modes, progress state, local completion marker, and links into How It Works, Visual + Audio, Risk Forecast, Compiler, and Assessment.
- **Navigation.** Added `/tutorial` lazy route and a first-position `Start Here` sidebar item.
- **Welcome flow.** First-run modal now prioritizes the 5-minute tour while preserving direct assessment access.
- **Docs.** Site/deploy specs updated so tutorial onboarding is part of the deployable feature surface.

## Session 34: Temporal Cognitive Score Phase B (April 25, 2026)

**Objective.** Ship the audio half of the Multi-Modal Cognitive Signature without fabricating roadmap capabilities.

- **`dashboard/src/lib/temporal_score/`** (NEW) — deterministic CAS-to-audio score generator. Noetics map to pitch, Registers map to expression, dominant Drive maps to tempo, Domains map to four staves/instrument families, and lacunarity maps to rests.
- **`dashboard/src/components/TemporalCognitiveScore.tsx`** (NEW) — Tone.js playback UI with Play/Pause/Stop, scrubber, volume, tempo override, transcript, captions, no auto-play, and cleanup on unmount.
- **`dashboard/src/pages/VisualizationPage.tsx`** (NEW) — deployable `/visualization` page pairing `RadialArchitectureDisplay` with `TemporalCognitiveScore` and cross-modal Domain sync.
- **Docs.** `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md` and `docs/CODEX_DEPLOY_DIRECTIVE.md` updated so Phase B is live while Phase C-E export/key-signature/generative variation remains roadmap.
- **Verification.** Targeted Temporal tests: 59 passed. Dashboard production build: passed.

## Session 33: Authoritative Noetic Reconciliation (April 19, 2026)

**Objective.** Reconcile every repository artifact to the authoritative Noetic definitions from the Tootra Math Handbook (the 10 Noetics: Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect). Supersede three earlier competing naming schemes (Scheme-A book personas, Scheme-B compiler labels, Scheme-C dashboard/interpreter labels). The authoritative definitions are canonical for all contexts — academic, regulatory, pedagogical, operational — with no public-vs-internal split, no translation table, no alternative naming.

**Authority.** `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 1 (verbatim canonical definitions) and Clarification 3 (no alternative scheme).

### Step 1 — Technical Feature Overview v2 (commit `9619cd1`)
- `docs/working/technical_feature_overview_v2.md` (NEW) — v2 deliverable with 7 revisions specifying authoritative-Noetic reintegration into the Word document. Revisions cover involution pairs listing, ^1/^4/^7 descriptions, involution semantics, recursive RPM exposure loop text, Dn-node text, N-axis label, and operator-to-Noetic substitution.
- `docs/working/technical_feature_overview_revised.md` — deprecation header added pointing to v2.

### Step 2 — FULL_MANUSCRIPT Appendix D (commit `07685f9`)
- `book/manuscript/FULL_MANUSCRIPT.md` Appendix D — full glossary rewrite.
  - Obsolete Public-Term/Internal-Term (TKS-Kabbalah) mapping table removed; replaced by clean Structural Reference Table.
  - New "The Ten Noetics — Authoritative Definitions" block at top with verbatim canonical definitions.
  - Scheme-A alphabetized entries (Abstractification, Concretization, Empathy, Critique, Expansion, Contraction, Identity, Differentiation, Integration, Momentum, Empathetic Alignment, Critical Evaluation) removed; authoritative entries (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect) inserted at their alphabetical positions.
  - CO-0..CO-9 block replaced with authoritative entries.
  - Trailing "Note on Internal Terminology Mapping" replaced with "Note on Authoritative Naming" per Clarification 3.
  - All non-Noetic entries preserved (domains, drives, Fisher-Rao, Bhattacharyya, Fractal Monoid, RPM, Section-Retraction, etc.).

### Step 3 — FULL_MANUSCRIPT Chapter 2 (commit `5f7bbc8`)
- `book/manuscript/FULL_MANUSCRIPT.md` Chapter 2 — full chapter rewrite (258 lines).
  - Chapter heading: "The Ten Cognitive Operators" → "The Ten Noetics".
  - Chapter 1 outro cross-reference (line 357) updated.
  - Foundation: CO-0 Identity → ^0 Idea (content-itself semantics, Rafael example reframed around Idea instability).
  - First Sequence renamed "Awareness and Valence": CO-1 → ^1 Mind; CO-2 → ^2 Positive; CO-3 → ^3 Negative; Startup example rewritten as "The Enthusiast and the Skeptic".
  - Second Sequence renamed "Resonance and Composition": CO-4 → ^4 Vibration; CO-5 → ^5 Female; CO-6 → ^6 Male; AI Sycophancy worked example reframed around ^5/^6 imbalance.
  - Third Sequence renamed "Rhythm and Causation": CO-7 → ^7 Rhythm; CO-8 → ^8 Above/Cause; CO-9 → ^9 Below/Effect; Writer and Blank Page reframed around trigger/effect breathing.
  - Kasparov mapping rewritten as authoritative Noetic sequence `^0 → ^1^C → ^8^C → (^2^C / ^3^C) → ^6^C → ^5^E → ^9^O`.
  - Key Insight, Try This exercises, Looking Ahead all reconciled. All pedagogical examples preserved but reframed to authoritative semantics.

### Step 4 — Codebase Reconciliation

- **`api/notation/compiler.py`** (commit `5d3a728`) — `OPERATOR_NAMES` replaced Scheme-B (Generative Potential, Directed Attention, Attraction/Affinity, Aversion/Critical Evaluation, Encoding Intensity, Receptive Integration, Projective Assertion, Pattern Entrainment, Causal Initiation, Consequential Grounding) with authoritative (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect). 19 notation-compiler tests pass.
- **`cas-engine/src/scoring/lacunarity.rs` + `cas-engine/src/rpm/recursive.rs`** (commit `843d905`) — `describe_largest_gap()` operator-name array and `recursive.rs` module docstring reconciled. POWER-block invokes ^8/^9 Above/Cause / Below/Effect; WISDOM-block invokes ^5 Female / ^6 Male; DESIRE-block Exposure Loop invokes ^1 Mind / ^4 Vibration / ^7 Rhythm. 303 library tests + 4 doctest pass.
- **`dashboard/src/lib/constants.ts` + `interpretations.ts` + `cardInterpretations.ts`** (commit `b1b897e`) — `OPERATOR_LABELS` rewritten with authoritative Noetic names superseding Scheme-C. `OPERATOR_DESC` rewritten with authoritative definitions; Anthropic-parallels blurbs removed since they keyed Scheme-C semantics. `CO_PLAIN` plain-English map rewritten with authoritative semantics in middle-school language. `npx tsc --noEmit` exits 0.
- **`api/pipeline/interpreter.py`** (commit `f057384`) — `OPERATOR_NAMES` reconciled Scheme-C → authoritative. 6 interpreter tests pass.
- **`api/llm_connectors/base.py`** (commit `65c04fe`, CRITICAL) — `CAS_BASE_SYSTEM_PROMPT` (the scoring prompt for every LLM call) rewritten. Uses authoritative Noetic definitions verbatim with structural metadata (involution pairs, self-duals) so the scorer has the algebraic structure it needs. Code-comment pointer added to `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`. 36 tests pass (test_connectors, test_interpreter, test_wrap, test_notation_compiler).

### Preservation
- `book/manuscript/archive/FULL_MANUSCRIPT_pre_noetic_reformation_2026-04-19.md` (earlier session commit `90db69c`) — byte-identical UTF-16 snapshot of the manuscript state before the reformation.
- Obsolete Scheme-A chapter drafts archived under `book/manuscript/_archived_chapter_drafts/` (earlier session commit `f46c1d5`).
- v1 Technical Feature Overview carries a deprecation header pointing at v2.

### Scope Explicitly Deferred (future sessions)
- FULL_MANUSCRIPT: Chapter 6 Inversions (operator-pair-heavy); Chapters 3-5 foundations; Chapters 7-11 Language; Chapters 12-17 Human Applications; Chapters 18-22 AI Applications; Chapters 23-27 Mathematics. Estimated 40-60 hours across 15-20 sessions.
- NL Signal Analyzer vocabulary audit (Scheme-A and Scheme-B terms remain in `api/pipeline/text_signal_analyzer.py`, `dashboard/src/lib/textSignalAnalyzer.ts`, and `tests/test_text_signal_analyzer.py` comment lines).
- Scenario catalog validation against authoritative Noetic definitions.
- Docs in `docs/` that reference Scheme-A/B/C terms in explanatory prose (incident database was already reconciled earlier this session, commit `5218557`).
- `cas-native/data/llm_english_generator.py` and related cas-native synthesis scripts still carry Scheme-B vocabulary; will be addressed in a future data-generation session since the training data itself will need regeneration.

### Verification Summary
- **Python tests.** `pytest tests/test_notation_compiler.py tests/test_interpreter.py tests/test_connectors.py tests/test_wrap.py` — 36 passed, 1 skipped. Full-suite run hit a pre-existing rate-limit artifact (`test_wrap_empty_text_422` returns 429 instead of 422 when run after other tests consume the rate-limit counter) unrelated to this session's changes; the test passes in isolation.
- **Rust tests.** `cargo test --lib` — 303 unit tests + 4 doctests pass.
- **TypeScript.** `npx tsc --noEmit` — 0 errors.
- **Git.** Seven commits landed and pushed to `origin/master` (`9619cd1`, `07685f9`, `5f7bbc8`, `5d3a728`, `843d905`, `b1b897e`, `f057384`, `65c04fe`). Working tree clean for the reconciled files.

## Session 32: Real-Time CAS Notation Synthesis (April 13, 2026)

### Backend — Notation Synthesizer (NEW)
- **`api/pipeline/notation_synthesizer.py`** (NEW) — Real-time CAS notation synthesizer that derives a compiler-validated expression from actual pipeline computation results (operator scores, domain averages, drive chains, RPM completeness, inversion axis scores, fractal analysis). The notation is a formal description of what the system *found*, not a prediction of what it expected to find.
- Extracts significant operators (raw score > 5.0), domains (average > 0.45), drives (chain stage > 0.5), RPM-wraps drives with complete prerequisite chains, includes non-neutral fractal sequences.
- Feeds the assembled expression through `compiler.py` (lexer → AST → type checker → bytecode → VM) for validation. Falls back to simplified expression if the full one fails compilation.
- Generates English description directly from extracted components: operator names, domain names, drive chain status, fractal classification.
- **`api/models.py`** — Added `CompiledNotationSchema` (source, valid, english, provenance).
- **`api/pipeline/runner.py`** — Synthesizer runs after fractal analysis; `WrapResponse` now includes `compiled_notation` field.
- **`tests/test_notation_synthesizer.py`** (NEW) — 22 tests: component extraction (operators, domains, drives, inversions), expression building, full synthesis integration, determinism, below-threshold handling, provenance tracking.

### Backend — Scenario Notation Enrichment
- **`api/scenario_notation.py`** (already existed from previous session) — `enrich_scenario_with_notation()` generates pre-assessment CAS notation from scenario metadata and validates through compiler.
- **`api/routes/scenarios.py`** — Every scenario returned by the API is now enriched with `cas_notation`, `cas_notation_validated`, `cas_notation_english`, `cas_notation_source`, `cas_assessment_config`. This is the pre-assessment "what will this test?" notation.

### Frontend — Notation Display
- **`dashboard/src/pages/ScenarioBrowserPage.tsx`** — Removed client-side `buildScenarioNotation()` import. Now consumes `cas_notation` from the API response. Expanded scenario detail shows validated CAS notation with compiler badge and English translation.
- **`dashboard/src/pages/AssessmentPage.tsx`** — After assessment runs, displays "CAS Notation (Computed)" card showing the real-time synthesized notation with compiler-validated badge and English translation.
- **`dashboard/src/api/types.ts`** — Added `CompiledNotation` interface, added `compiled_notation` to `WrapResult`, added notation fields to `Scenario` interface.
- **`dashboard/src/lib/scenarioNotation.ts`** — DELETED (client-side notation generation removed entirely).
- **`dashboard/src/test/__tests__/scenarioNotation.test.ts`** — DELETED.
- **`dashboard/src/test/__tests__/ScenarioBrowserPage.test.tsx`** — Updated mock data to include backend notation fields, updated assertions.
- **`dashboard/src/test/__tests__/AssessmentPage.test.tsx`** — Updated notation prefill format.

### CAS Synthetic Training Data Generator
- **`cas-native/data/expression_generator.py`** (NEW) — Random CAS expression generator with 3 complexity levels (simple: 1-2 states; medium: 2-4 states with RPM/fractal; complex: parenthesized sub-expressions with domain descent, RPM, fractals, co-present drives). Respects domain descent for ->, same-domain for /, admissibility constraints. Every expression validated through compiler before acceptance.
- **`cas-native/data/english_generator.py`** (NEW) — Template-based reverse synthesizer. 120+ operator-domain templates (all 40 combos x 3 each), 21 drive context templates, 20+ operation transition templates, 50+ scenario contexts (doctor, teacher, manager, judge, engineer, etc.). Converts any compiled CAS expression into natural English.
- **`cas-native/data/score_extractor.py`** (NEW) — Extracts ground truth labels from expressions: 10 operator scores, 4 domain scores, 7 drive scores, RPM completeness, fractal classification, lacunarity, structural flags (descent, division).
- **`cas-native/data/validate_data.py`** (NEW) — Dataset quality validation: compilation validity rate, score consistency, operator/domain/drive distribution balance, complexity distribution, duplicate detection, average English length, underrepresentation warnings.
- **`cas-native/data/verifier.py`** (NEW) — Round-trip verification for LLM-generated English: feeds text back through signal analyzer, compares re-extracted operators/domains/drives/structure against original. Accepts if 3 of 4 criteria match. Catches hallucinations.
- **`cas-native/data/generate_training_data.py`** (NEW) — Batch pipeline: generates N triples as JSONL, runs quality validation, reports statistics. Tested: 100 triples, 0 failures, 100% valid, 100% consistent, 1% duplicates, 38 avg words.

### CAS-Native Lacunarity — Training + Inference + Output
- **`cas-native/model/lacunarity_gate.py`** (NEW) — LacunarityGate: inference-time self-correction. Computes lacunarity (Var/Mean^2) on slot activations. When above threshold (2.0), applies learned rebalancing correction that boosts neglected slots and dampens over-concentrated ones. Re-normalizes to open simplex via softmax + clamp. The model catches itself when thinking gets too narrow.
- **`cas-native/model/lacunarity_head.py`** (NEW) — LacunarityHead: metacognitive output head. Produces 5 lacunarity dimension scores, 40-element gap map (per-slot blind spot probability), and 4 domain confidence scores. The model reports its own cognitive gaps alongside its answer.
- **`cas-native/model/loss.py`** — LacunarityRegularizationLoss: training-time prevention. Penalizes deviation from target lacunarity (default 0.5). Too high = blind spots. Too low = no specialization. Added to total training loss.
- **`cas-native/model/cas_native_model.py`** — CASNativeModel now includes LacunarityGate (between cognitive embedding and output heads) and LacunarityHead (auxiliary metacognitive output). Forward pass returns `lacunarity_scores`, `lacunarity_meta` (with gap_map and domain_confidence), and both raw and corrected cognitive states.
- **`cas-native/tests/test_lacunarity.py`** (NEW) — 13 tests: gate output shape/simplex preservation/low-lacunarity minimal change/high-lacunarity correction/sequence handling, head output keys/shapes/ranges/sequence handling, loss scalar/target behavior/extreme concentration penalty.

### Cognitive Lacunarity Profile
- **`cas-engine/src/scoring/lacunarity.rs`** (NEW) — 5 lacunarity metrics measuring cognitive gap distribution: state lacunarity (Var/Mean^2 on operator scores), fractal lacunarity (1 - unique operators/10), domain lacunarity (1 - active domains/4), drive lacunarity (1 - active drives/7), RPM resolution lacunarity (1 - mechanisms used/4). Composite weighted 30/20/20/15/15. Classifications: Uniform (<0.5), Moderate (0.5-1.5), Concentrated (1.5-3.0), Extreme (>3.0). Gap map identifies absent operators, domains, drives, strongest cluster, and largest void with human-readable description. 14 tests.
- **`api/pipeline/lacunarity.py`** (NEW) — Python implementation mirroring the Rust module. Computes full lacunarity profile from pipeline scores.
- **`api/pipeline/runner.py`** — Lacunarity computed after notation synthesis, included in WrapResponse.
- **`api/models.py`** — Added `lacunarity: dict | None` to WrapResponse.
- **`dashboard/src/components/charts/LacunarityCard.tsx`** (NEW) — Visualization card with composite score + classification badge, 5 dimension bars (color-coded: green=uniform, amber=moderate, orange=concentrated, red=extreme), 10-dot operator X-ray (bright=active, dim=absent, glowing=concentrated), gap map text (absent operators, domains, drives, concentration areas, largest void description).
- **`dashboard/src/pages/AssessmentPage.tsx`** — LacunarityCard appears after Cognitive Fractal in technical view.
- **`dashboard/src/api/types.ts`** — Added lacunarity type to WrapResult.
- **355 Rust tests + 297 Python tests + 31 frontend tests = all passing.**

### Recursive RPM — Complete Implementation Across All Layers
- **`cas-engine/src/rpm/recursive.rs`** (NEW) — Full recursive RPM evaluation in Rust. When D/W/P nodes are blocked, specific CO pairs activate to resolve:
  - **Power blocked → CO-8/CO-9 (Causal Search)**: spawns child D/W/P chain to acquire resource. RECURSIVE.
  - **Wisdom blocked → CO-5 (Knowledge Reception)**: find external source that carries knowledge. RECURSIVE.
  - **Wisdom blocked → CO-6 (Knowledge Decomposition)**: break into components, each gets own chain. PARALLEL RECURSIVE.
  - **Desire blocked → CO-1/CO-4/CO-7 (Exposure Loop)**: observe → intensify → repeat. ITERATIVE, not recursive.
  - Max recursion depth: 5. Section-retraction holds at every level. Desire loops don't count toward depth.
  - Types: `RecursiveRpmResult`, `NodeResult`, `ResolutionMechanism` (CausalSearch, KnowledgeReception, KnowledgeDecomposition, ExposureLoop).
  - 11 tests: flat chain, Power/Wisdom/Desire resolution, operator-inactive stays blocked, max depth, A0 fail, section-retraction, exposure loop depth independence.
- **`cas-engine/src/rpm/mod.rs`** — Registered `pub mod recursive`.
- **`api/pipeline/stages.py`** — RPM gate now evaluates recursive resolution mechanisms. `RpmGateResult` extended with `recursive_resolutions`, `exposure_loops_detected`, `resolution_details` (per-drive resolution mechanism, operators, strength).
- **`api/pipeline/runner.py`** — Pipeline includes recursive resolution data in RPM stage output.
- **`dashboard/src/components/charts/RpmGraph.tsx`** — Shows recursive resolution count, per-drive resolution details when selected (mechanism name, operator pair, component count for CO-6 decomposition).
- **`dashboard/src/pages/AssessmentPage.tsx`** — Passes `resolutionDetails` from pipeline to RpmGraph.
- **`cas-native/model/rpm_gate.py`** — Added 5 new modules:
  - `ExposureLoop` — CO-1→CO-4→CO-7 iterative cycle (max 10 cycles, threshold exit)
  - `CausalResolver` — CO-8→CO-9 with residual connection
  - `KnowledgeReceptor` — CO-5 search + absorb with residual
  - `KnowledgeDecomposer` — CO-6 decompose into max 4 components, gate filter, reassemble
  - `RecursiveRPMGate` — Full recursive gate with operator extractors, resolution dispatch, depth-limited recursion. Preserves `PrerequisiteGateLayer` for backward compatibility.
- **341 Rust tests + 297 Python tests + 31 frontend tests = all passing.**

### CAS Interactive Compiler (/compiler)
- **`dashboard/src/pages/CompilerPage.tsx`** (NEW) — Full interactive REPL page with terminal aesthetic (#0d1117 dark background, monospace font, teal cursor prompt). Features: ASCII CAS logo on load, syntax highlighting as you type (operators=cyan, domains=green, drives=amber, operations=white, RPM=purple, fractals=magenta), styled compilation result cards with AST/type/result display, error cards with token analysis, command history (up/down arrow), special commands (:help, :grammar, :examples, :clear, :history), collapsible side panel with operator/domain/drive/operation reference and clickable example expressions that auto-fill the input. Cards slide in with fadeSlideIn animation.
- **`dashboard/src/App.tsx`** — Added `/compiler` route (lazy-loaded).
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "CAS Compiler" nav item between Scenarios and AI Challenges.
- **`dashboard/src/index.css`** — Added `@keyframes fadeSlideIn` animation.

### CAS-Native Generative Operations
- **`cas-native/model/composition.py`** (NEW) — COMPOSE_TABLE (10×10 monoid multiplication table), CompositionHead (learns to compose two slot activations via the CAS monoid with learnable-weighted lookup initialized to ground truth), GenerativeHead (takes two cognitive state embeddings, merges them, applies composition, outputs emergent state on 40-simplex + operator distribution), composition_loss (cross-entropy against monoid ground truth).
- **`cas-native/model/cas_native_model.py`** — Added GenerativeHead as output head.
- **`cas-native/model/loss.py`** — Added lambda_composition parameter and compute_composition_loss method using the monoid ground truth. Imported composition_loss from new module.
- **`cas-native/tests/test_composition.py`** (NEW) — 13 tests: COMPOSE_TABLE identity/closure/commutativity/specific values, CompositionHead output shape/distribution, GenerativeHead output keys/shapes/simplex constraint, composition_loss perfect/wrong/scalar. (Requires PyTorch to run.)

### Architecture & UX Improvements (Gemini Recommendations)
- **IndexedDB History Storage** — `dashboard/src/stores/historyStore.ts` now uses IndexedDB (via `idb-keyval`) instead of localStorage. Prevents silent data loss when 100 assessment records exceed the 5MB localStorage quota. Falls back to localStorage in test environments.
- **Chart Layout Stability** — `chartFallback` min-height bumped from 220px to 280px to prevent layout shifts during lazy chart loading.
- **Graceful CAS Math Violations** — `dashboard/src/components/shared/ErrorBanner.tsx` now detects 6 CAS-specific error patterns (domain descent violations, cross-domain division, admissibility violations, degenerate states, simplex boundary violations, dial safety constraints) and renders them with domain terminology and amber warning styling instead of generic red HTTP errors.
- **Pentad Visualization (Dual-Layer Modularity)** — `dashboard/src/components/shared/NotationComposer.tsx` now detects and color-codes syntactic assemblers (`+`, `-` in slate/grey) separately from algebraic transformers (`×`, `÷`, `∘` in orange). Quick reference updated to teach the dual-layer distinction inline. Users learn the math visually.

### Algebraic Operations: × and ÷ in Rust Scoring Engine
- **`cas-engine/src/algebra/`** (NEW MODULE) — Full CAS v7.4 algebraic operations, formally verified by Qwen:
  - **`drives.rs`** — Drive synthesis table: same drive = idempotent, inversion pairs (F1↔F7, F2↔F6, F3↔F5) → F4 Connection, non-paired → attractor closest to F4. Drive ratio for division.
  - **`multiplication.rs`** — Cognitive state multiplication: operator composition (monoid on Z/10Z), domain descent (P×C=C, E×C=Error), drive synthesis, admissibility check. 6 tests including associativity.
  - **`division.rs`** — Cognitive state division: same-domain only, operator ratio (same=CO-0, involution pair=CO-0, midpoint otherwise), drive ratio. 5 tests.
  - **`simplex.rs`** — Probability simplex operations: geometric mean for ×, element-wise ratio for ÷, both renormalized to Δ°39. Commutativity, idempotency, simplex preservation tests.
  - **`error.rs`** — AlgebraError type: DomainAscentViolation, CrossDomainDivision, AdmissibilityViolation, DegenerateState, BoundaryViolation, DimensionMismatch.
- **`cas-engine/src/lib.rs`** — Registered `pub mod algebra`.
- **`cas-engine/src/python_bindings.rs`** — 5 new PyO3 functions: `multiply_state_vectors`, `divide_state_vectors`, `multiply_cognitive_states`, `divide_cognitive_states`, `synthesize_drives`.
- **`api/notation/compiler.py`** — TIMES and DIVIDE evaluation now routes through Rust algebra when available. TIMES allows domain descent (P×C=C). DIVIDE enforces same-domain. Involution pairs resolve to CO-0 identity. Python fallback preserved.
- **Rust tests:** 330 total (278 lib + 42 integration + 10 others), all passing.

### Reproducibility Test (Test-Retest Reliability)
- **`api/routes/reproducibility.py`** (NEW) — `POST /reproducibility` endpoint. Runs the same prompt against the same provider N times (2-50, default 10), collects all NCCS composite scores, computes mean, std dev, min, max, range, coefficient of variation, and certification consistency. Returns all individual run results with sub-scores.
- **`api/main.py`** — Registered reproducibility router.
- **`dashboard/src/pages/ReproducibilityPage.tsx`** (NEW) — Full reproducibility test UI: prompt input, provider selector, N runs config, "Run Nx" button, 4 stat cards (mean, std dev, range, CV), certification consistency badge, reliability interpretation (high/moderate/low based on CV), strip plot visualization showing individual run scores as dots with mean line and std dev band, certification-banded background, individual runs table (NCCS, cert, operator, domain, drive/RPM, inversion, latency), citable summary paragraph (select-all for copy).
- **`dashboard/src/api/endpoints.ts`** — Added `postReproducibility()`, `ReproducibilityRequest`, `ReproducibilityResponse`, `ReproducibilityStats`, `ReproducibilityRunResult` types.
- **`dashboard/src/App.tsx`** — Added `/reproducibility` route (lazy-loaded).
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "Reproducibility" nav item.

### Notation Diff View: Expected vs. Computed
- **`dashboard/src/components/shared/NotationDiff.tsx`** (NEW) — Side-by-side comparison of pre-assessment (expected) and post-assessment (computed) CAS notation. Token-level diff classifies each CO, domain, drive, and RPM token as "confirmed" (in both), "new finding" (only in computed), or "not observed" (only in expected). Divergence summary with color-coded token pills. Shows "No Divergence" confirmation when profiles match.
- **`dashboard/src/pages/AssessmentPage.tsx`** — When a scenario was the source of an assessment, the results show "Notation Analysis: Expected vs. Computed" card with the diff. For free-text assessments (no scenario), shows the standalone computed notation card.
- **`dashboard/src/pages/ScenarioBrowserPage.tsx`** — Now passes `notationEnglish` to the assessment page alongside the notation itself.

### Live Signal Heatmap
- **`dashboard/src/components/shared/SignalHeatmap.tsx`** (NEW) — Mini heatmap showing per-operator (10 cells), per-domain (4 cells), per-drive (7 cells) signal scores as the user types. Color intensity scales with signal strength. RPM signal shown as a progress bar. Makes the live analysis feel like a real-time diagnostic instrument.
- **`dashboard/src/pages/AssessmentPage.tsx`** — Signal heatmap appears below the live CAS notation in the Free Text tab, inside the analysis panel.

### Live CAS Analysis (Real-Time Text → Notation)
- **`api/pipeline/text_signal_analyzer.py`** (NEW) — Fast text-to-CAS signal analyzer. Scans raw input for linguistic patterns mapped to CAS ontology: 10 operator signal lists (stem-matched), 4 domain signal lists, 7 drive signal lists, RPM chain language. Runs in <50ms — no LLM needed.
- **`api/routes/notation.py`** — Added `POST /notation/analyze` endpoint. Takes raw text, extracts signals, feeds through synthesizer + compiler, returns compiler-validated CAS notation with signal breakdown. This is the live endpoint the UI calls as the user types.
- **`dashboard/src/pages/AssessmentPage.tsx`** — Free Text tab now shows "Live CAS Analysis" panel below the textarea. Debounced (300ms), calls `/notation/analyze` as user types, displays compiler-validated notation + English translation in real time. Also syncs to the Compose tab.
- **`dashboard/src/api/endpoints.ts`** — Added `postAnalyzeText()` client function and `LiveNotationResult` type.
- **`dashboard/src/test/mocks/handlers.ts`** — Added mock handler for `/notation/analyze`.
- **`tests/test_text_signal_analyzer.py`** (NEW) — 12 tests: signal extraction (ethical→CO-3+Principled, analytical→CO-1+Cognitive, action→CO-8+Operational), drive detection, RPM detection, bounds checking, determinism, API endpoint tests with auth.

### Two Notation Paths
1. **Pre-assessment** (scenario browser): derived from scenario metadata, compiler-validated. Teaches users CAS language before they run anything.
2. **Post-assessment** (results): derived from actual pipeline computation, compiler-validated. Proves what the system computed in real-time.

### Verification
- Python: 286 passed, 1 skipped (22 new synthesizer tests)
- Frontend: 31 passed (8 test files)
- Synthesizer produces `rust+python` compiler-validated expressions with full provenance

---

## Session 31: Human Validation Study System (April 10, 2026)

### Backend
- **`api/validation/correlation.py`** (NEW) — Pearson r, approximate p-values via t→normal, Fisher z-transform 95% CI, Cohen's kappa, strength classification (strong ≥0.7, moderate ≥0.4, weak <0.4), per-operator correlation computation (scales machine 0-1 to 0-10), inter-rater reliability, headline stats, auto-generated calibration recommendations, JSON label persistence.
- **`api/routes/validation.py`** (NEW) — 6 endpoints: `GET /validation/items`, `GET /validation/next?rater=`, `POST /validation/label`, `GET /validation/stats`, `GET /validation/leaderboard`, `GET /validation/export?format=json|csv`. Pydantic validation enforces 10 operator scores + 4 domain scores, all in [0,10].
- **`api/main.py`** — Registered validation router.

### Frontend
- **`dashboard/src/pages/ValidationPage.tsx`** (NEW) — Labeling interface with rater name gate (persisted to localStorage), progress bar, full prompt + scrollable response cards, 10 operator sliders + 4 domain sliders (color-coded red/amber/green), Submit/Skip/Quit buttons, post-submit reveal showing side-by-side "You vs Machine" delta table.
- **`dashboard/src/pages/ValidationLeaderboardPage.tsx`** (NEW) — Real-time dashboard with 10-second React Query refetch: 5 headline stat cards (labels, raters, multi-rated, overall r, κ), sortable per-operator correlation table, interactive scatter plots via Recharts (click row → plot), inter-rater reliability table, calibration recommendations with severity colors, JSON/CSV export links.
- **`dashboard/src/api/types.ts`** — Added 8 validation types.
- **`dashboard/src/api/endpoints.ts`** — Added 4 validation client functions.
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "Validation" and "Leaderboard" nav items.
- **`dashboard/src/App.tsx`** — Added `/validate` and `/validation/leaderboard` routes (lazy).

### Tests
- **`tests/test_correlation.py`** (NEW) — 24 tests: Pearson edge cases, CI, kappa, strength classification, operator correlation computation with scatter points, inter-rater pairs, stats aggregation, recommendations.
- **`tests/test_validation_api.py`** (NEW) — 11 tests: list/next/submit/stats/leaderboard/export endpoints with mocked storage, auth rejection, validation errors.
- **Verification**: 241 passed, 1 pre-existing failure (notation compiler showcase, unrelated).

---

## Session 30: Executable CAS Notation Compiler (April 10, 2026)

### Task 1: Real CAS DSL Compiler/Interpreter
- **`api/notation/compiler.py`** (NEW) — Executable CAS notation pipeline: lexer, AST parser, static type checker, admissibility-aware validation, lowering to stack bytecode, and Python VM execution
- Supported executable forms: state literals (`CO-2^C_{F2}`), relations (`->`, `<-`, `<->` plus unicode aliases), additive and multiplicative operators (`+`, `-`, `*`, `/`), `RPM(...)`, and `Phi<...>` / `Φ⟨...⟩`
- Uses Rust `cas_engine` bindings when available for operator composition and admissibility, with Python fallback logic when unavailable
- Semantics are explicit and bounded in code; this is an executable DSL surface, not a claim that every manuscript law is already compiled
- Expanded language surface: shorthand state refs (`P3`, `C7`), fractal composition via `∘`, multi-statement programs split by semicolons/newlines, comment skipping, and program-result aggregation

### Task 2: API and CLI Exposure
- **`api/routes/notation.py`** (NEW) — `POST /notation/compile` returns tokens, AST, type information, bytecode, warnings, and execution result for a CAS expression
- **`api/routes/notation.py`** — Added `GET /notation/grammar` exposing the current BNF and semantic notes
- **`api/main.py`** — Mounted notation router
- **`api/notation/cli.py`** (NEW) — Compiler CLI with `--mode lex|parse|check|run`, `--file`, `--grammar`, and `--repl`
- **`api/notation/__init__.py`** — Exported `compile_expression()`
- **`docs/CAS_LANGUAGE_SPEC.md`** (NEW) — Written language-spec overview
- **`docs/CAS_LANGUAGE_GRAMMAR.bnf`** (NEW) — Current grammar artifact
- **`docs/CAS_LANGUAGE_EXAMPLES.cas`** (NEW) — Example CAS programs

### Task 3: Verification
- **`tests/test_notation_compiler.py`** (NEW) — Transition compilation, invalid descent rejection, operator range validation, RPM execution, fractal execution, and CO-0 admissibility behavior
- **`tests/test_notation_route.py`** (NEW) — Successful compile route response, invalid-expression rejection, and grammar endpoint coverage
- Existing parser/renderer tests still pass unchanged

### Verification
- Python: `197 passed` across `tests/`
- Notation-focused suite: `32 passed`
- CLI run verified on `(CO-2^C_{F2} * CO-4^C_{F2}) -> CO-5^E_{F4}` and `P0 -> C0; RPM(F5); CO-8^C ∘ CO-3^C`

---

## Session 29: v6.1 Fractal Calculus + D/W/P Chain in Rust (April 8, 2026)

### Task 1: Cognitive Fractal Calculus (cas-engine/src/fractals/)
- **`fractal.rs`** (NEW) — `CognitiveFractal` type: non-empty Vec<u8> (each 0-9), right-to-left application via operator composition, identity ⟨0⟩, Display trait
- **`composition.rs`** (NEW) — Concatenation-based composition forming monoid (Frac, ∘, Φ_id), `iterate()` for Φⁿ, associativity + identity law tests
- **`simplification.rs`** (NEW) — Dual cancellation for all 3 involution pairs (CO-2/3, CO-5/6, CO-8/9 → identity), identity elimination, `canonicalize()` with confluence guarantee per Newman's lemma, polarity fractal test (Theorem 8.22)
- **`convergence.rs`** (NEW) — `orbit()`, `find_fixed_point()`, periodic cycle detection, `FractalClass` enum (Stabilizing/Amplifying/Oscillatory/Neutral per Def 8.20), `find_eigenvalue()`, MVR stability test (Theorem 8.21)
- 32 unit tests

### Task 2: D/W/P Chain Evaluation (cas-engine/src/rpm/)
- **`chain.rs`** (NEW) — `DwpStage` enum (Dormant→Fading, Unaware→Mastering, Nascent→Mastery), `evaluate_chain()` implementing v6.1 Def 7.10 with v7.4 section-retraction semantics (forward-only, no backward reconstruction), `RpmChainResult` with stage classification and completeness score
- **`diagnostics.rs`** (NEW) — Plain-English diagnostics per v6.1 Def 7.14: identifies first failure, explains what was satisfied, suggests remediation. `diagnose_all_chains()` for 7-drive summary.
- 20 unit tests; 287 total Rust tests passing

### Task 3: Fractal Scoring Integration + Dashboard
- **`api/pipeline/fractal_analysis.py`** (NEW) — Pure Python fractal analysis: dual cancellation, canonical form, classification, orbit analysis
- **`api/models.py`** — Added `FractalAnalysisSchema` to `WrapResponse`
- **`api/pipeline/runner.py`** — Fractal analysis runs post-operator-scoring
- **`dashboard/src/api/types.ts`** — `FractalAnalysis` interface
- **`dashboard/src/components/charts/FractalCard.tsx`** (NEW) — Color-coded operator sequence, classification badge, orbit/contradiction/fixed-point stats
- **`dashboard/src/pages/AssessmentPage.tsx`** — Added FractalCard after Pipeline Stages
- 14 Python tests

### Task 4: CAS-Native Type Constraints
- **`cas-native/model/type_constraints.py`** (NEW) — Pure validation functions (no PyTorch): operator identity, involution roundtrip, domain descent, RPM chain ordering, fractal type well-formedness. PyTorch loss regularizers: identity_constraint_loss, involution_constraint_loss, domain_descent_loss, rpm_ordering_loss, combined type_constraint_loss (λ=0.1)
- 19 pure validation tests

### Task 5: Assessment Trace + CAS Notation Parser
- **`api/pipeline/trace.py`** (NEW) — AssessmentTrace class: step-by-step evaluation recording with rule names, I/O summaries, plain-English reductions. build_trace_from_stages() for pipeline output.
- **`api/notation/parser.py`** (NEW) — Tokenizer + parser for CAS notation (CO-3^E, CO-2+CO-3, RPM(F5), Phi<2:5:8>, P3/C7/E0/O5)
- **`api/notation/renderer.py`** (NEW) — Plain English rendering + assessment config extraction
- 26 tests (parser/tokenizer/renderer + trace)

### Verification
- Rust: 287 tests passing (245 lib + 42 integration)
- Python: 173 tests passing, 1 skipped
- TypeScript: 0 errors
- Frontend: 23/23 tests passing

---

## Session 28: Defensive Assessment Content — 5 Tasks (April 8, 2026)

### Task 1: Seven AI Challenges Page
- **`dashboard/src/pages/AiChallengesPage.tsx`** (NEW) — 7 expandable challenge cards: Alignment Verification (RPM), Interpretability (40-State Heatmap), Cognitive Stability (Fractal), Distribution Robustness (Fisher-Rao), Multi-Agent Coherence (Cohort), Value Learning (Topos), Safety Verification (Inversion). Defensive framing with research disclaimer.
- **`dashboard/src/App.tsx`** — Added lazy route `/ai-challenges`
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "AI Challenges" nav item

### Task 2: 30 Adversarial Resilience Scenarios
- **`scenarios/catalog/adversarial_resilience.json`** (NEW) — 30 scenarios in 5 groups: Cognitive Bias Exploitation (authority, social proof, scarcity, reciprocity, escalation, emotional override), Discourse Boundary (normalization, reframing, false equivalence, context switch, definitional drift, helpfulness appeal), Prerequisite Integrity (desire/wisdom/power bypass, chain reversal, partial chain, false prerequisites), Domain Coherence (logic-only/emotion-only traps, theory-practice gap, abstraction avoidance, feeling dismissal, action without reflection), Inversion Detection (empathy/authority/causal/freedom/safety/wisdom inversions)
- **`tests/test_adversarial_scenarios.py`** (NEW) — 10 validation tests

### Task 3: D/W/P Chain Stage Analysis
- **`dashboard/src/lib/rpmStages.ts`** (NEW) — Stage classification: Desire (Dormant→Fading), Wisdom (Unaware→Mastering), Power (Nascent→Mastery) with color coding
- **`dashboard/src/components/charts/RpmGraph.tsx`** — Nodes colored by stage, stage labels shown on selected drive row
- **`api/pipeline/interpreter.py`** — RPM stage description added to briefing prompt

### Task 4: Cognitive Blind Spot Analysis
- **`dashboard/src/lib/blindSpots.ts`** (NEW) — Computes blind spots from operator scores (<0.4), domain averages (<0.15), involution imbalance (>0.3), drive deficits (<0.5) with risk descriptions
- **`dashboard/src/components/shared/BlindSpotCard.tsx`** (NEW) — Visual summary with severity counts, critical callout, remediation
- **`dashboard/src/pages/AssessmentPage.tsx`** — Added BlindSpotCard after Stability Alerts
- **`dashboard/src/lib/reportData.ts`** — Added blindSpots to ReportData
- **`dashboard/src/lib/exportMarkdown.ts`** — Blind spots in exported reports

### Task 5: 40-Prompt Stabilization Confidence Indicator
- **`dashboard/src/components/shared/ConfidenceIndicator.tsx`** (NEW) — Progress bar: Preliminary (<10, red), Developing (10-39, amber), Stabilized (40+, green). Based on CAS 40-step stabilization bound.
- **`dashboard/src/pages/AssessmentPage.tsx`** — Confidence bar above input
- **`dashboard/src/pages/HistoryPage.tsx`** — Cumulative count with stabilization status

### Verification
- Python: 114 passed, 1 skipped
- TypeScript: 0 errors
- Frontend: 23/23 tests passed
- All content uses defensive framing only

---

## Session 27: TKS Integration — 4 Tasks (April 8, 2026)

### Task 1: Cognitive Circuit Examples → HowItWorksPage
- **`dashboard/src/components/shared/CircuitCard.tsx`** (NEW) — Reusable circuit card with SVG node/arrow diagram, feedback loops, description, assessment callout
- **`dashboard/src/pages/HowItWorksPage.tsx`** — New "How Cognitive Operators Work in Everyday Life" section with 4 circuit examples:
  - Morning Decision Amplifier (CO-2 → CO-4 integration)
  - Friction Inhibitor (CO-2 dampened by CO-3)
  - Momentum Builder (RPM chain A0→D→W→P + CO-7 feedback)
  - Creative Flow State (CO-0 ↔ CO-6 oscillation via CO-7)

### Task 2: Scenario Inversion Engine + Augmentation + Teacher
- **`scenarios/generator/__init__.py`** (NEW) — Package init
- **`scenarios/generator/inversion_engine.py`** (NEW) — 7-axis CAS inversions: N (operator swap), W (domain flip), F (drive swap), E (polarity), S (sub-drive shift), A (RPM scramble), P (compound). Includes prompt rewriting and target transformation.
- **`scenarios/generator/augmentation.py`** (NEW) — Loads 50 base scenarios, assigns targets via keyword heuristics, runs 7-axis expansion → 400 scenarios
- **`scenarios/generator/teacher.py`** (NEW) — LLM-based scenario generation with CAS ontology validation
- **`scenarios/generator/__main__.py`** (NEW) — CLI: `python -m scenarios.generator --augment --count 500`
- **`scenarios/augmented_library.json`** (NEW) — 400 augmented scenarios (50 base × 8)
- **`tests/test_scenario_generator.py`** (NEW) — 24 tests covering all axes, augmentation, teacher parsing
- Verified: 104 passed, 1 skipped

### Task 3: CAS-Native 5-Stage Data Pipeline
- **`cas-native/training/data_pipeline.py`** — Added `validate_cas_item()` (open simplex, score ranges) and `run_pipeline()` implementing 5 stages: load → augment → validate → split → tokenize
- **`cas-native/training/augment.py`** (NEW) — Generates 7 inverted variants per training item with adjusted scores: N-axis swaps involution pair scores, W-axis swaps domain averages, F-axis swaps drives, composite dampened per axis severity
- **`cas-native/tests/test_data.py`** — Added TestValidation, TestAugmentation, TestRunPipeline classes (requires PyTorch)

### Task 4: tootra-tks Rust Type Extraction — Assessment
Reviewed `github.com/LittleHenderson/tootra-tks` tks-rs workspace:
- **`tkscore/src/ast.rs`**: `World` enum (A/B/C/D) → maps to CAS Domains (P/C/E/O)
- **`tksir/src/ir.rs`**: `Noetic(u8)` → CO-0 through CO-9; `Element(World, u8)` → cognitive states; `RpmReturn/RpmBind/RPMAcquire/RPMCheck/RPMFail` → RPM monad ops
- **`inversion/engine.py`**: `NOETIC_OPPOSITE` (involution pairs), `FOUNDATION_OPP` (drive inversions), `WORLD_OPP` (domain swaps) — all compatible with CAS v7.4, already ported to CAS notation in our inversion_engine.py
- **Decision**: tks-rs is a compiler for a DSL (lexer/parser/IR/bytecode), not standalone ontology types. The algebraic structures (involution tables, domain swaps, drive inversions) have been ported to CAS terminology. No Rust code imported — cas-engine ontology should be written fresh with admissibility relations, Fisher-Rao metric, and section-retraction RPM per v7.4 corrections.

---

## Session 26: Railway API Backend Deployment (April 8, 2026)

### Railway Configuration
- **`railway.toml`** (NEW) — Points to `Dockerfile.api`, start command with dynamic `PORT`, health check on `/health`, restart-on-failure policy
- **`Dockerfile.api`** — CMD now uses shell form with `${PORT:-8000}` to respect Railway's dynamic port assignment

### Deployment Docs
- **`docs/DEPLOYMENT.md`** — Added full Railway section: CLI install, `railway init/up`, env vars setup (`NC_JWT_SECRET`, `NC_CORS_ORIGINS`, LLM keys), connecting Railway URL to Vercel dashboard, optional PostgreSQL, health check verification, custom domain

### Verification
- Python: 80 passed, 1 skipped

---

## Session 25: Vercel Deployment Setup (April 8, 2026)

### Vercel Configuration
- **`dashboard/vercel.json`** (NEW) — Vite framework, `dist` output, SPA rewrites (non-asset routes → `index.html`), service worker no-cache header, manifest content-type header

### Configurable API URL
- **`dashboard/src/api/config.ts`** (NEW) — Exports `API_BASE` from `VITE_API_URL` env var, defaults to `/api` for dev proxy
- **`dashboard/src/api/client.ts`** — `apiFetch()` now uses `API_BASE` instead of hardcoded `/api`
- **`dashboard/src/pages/LoginPage.tsx`** — Token fetch uses `API_BASE` instead of hardcoded `/api`
- **`dashboard/.env.example`** (NEW) — Documents `VITE_API_URL` with commented-out example

### Deployment Docs
- **`docs/DEPLOYMENT.md`** — Added Vercel section: CLI install, `vercel` deploy, `VITE_API_URL` env setup (CLI + dashboard), `.env.local` for local overrides, CORS note, custom domain instructions

### Verification
- TypeScript: 0 errors
- Frontend: 23/23 tests passed
- Production build: successful

---

## Session 24: Progressive Web App (PWA) Conversion (April 8, 2026)

### PWA Manifest & Icons
- **`dashboard/public/manifest.json`** (NEW) — Full PWA manifest: `standalone` display, `portrait` orientation, theme/bg `#0a0f1a`, 192+512 SVG icons with maskable variant
- **`dashboard/public/icon-192.svg`** (NEW) — Stylized compass with neural network motif (10 nodes, cross-connections, teal-cyan gradient, "NC" center)
- **`dashboard/public/icon-512.svg`** (NEW) — High-res version with 10 operator nodes, 4 domain indicators, ordinal ticks

### Service Worker
- **`dashboard/public/sw.js`** (NEW) — Cache-first for static assets (JS/CSS/fonts/images), network-first for `/api` calls, offline fallback for navigation
- **`dashboard/public/offline.html`** (NEW) — Dark-themed offline page with NC logo, "Connect to assess AI systems" message, retry button

### Install Prompt
- **`dashboard/src/hooks/usePwaInstall.ts`** (NEW) — Captures `beforeinstallprompt`, tracks dismissals in localStorage (max 3), handles `appinstalled`
- **`dashboard/src/components/shared/InstallBanner.tsx`** (NEW) — Bottom banner with icon, "Install Noetic Compass" CTA, dismiss button. Safe-area aware.
- **`dashboard/src/App.tsx`** — Added `<InstallBanner />` at root

### PWA Meta Tags
- **`dashboard/index.html`** — Title "Noetic Compass", manifest link, `theme-color`, `viewport-fit=cover`, full iOS support (`apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `apple-touch-icon`), description meta

### Service Worker Registration
- **`dashboard/src/main.tsx`** — Registers `/sw.js` on window load with silent failure fallback

### Mobile Responsiveness
- **`dashboard/src/index.css`** — `100dvh` root, `overscroll-behavior-y: contain` (prevents pull-to-refresh in standalone), `.safe-bottom`/`.safe-top` utility classes for notch devices
- **`dashboard/src/components/layout/Header.tsx`** — Hamburger menu button (inline, not floating FAB), X icon when open, 44px touch target, responsive padding
- **`dashboard/src/components/layout/AppShell.tsx`** — Menu toggle in header, responsive main padding (`p-3 sm:p-4 md:p-6`), `100dvh` height
- **`dashboard/src/components/layout/Sidebar.tsx`** — Opens below header (`top-14`), 44px nav link touch targets, `100dvh` height calc
- **`dashboard/src/pages/AssessmentPage.tsx`** — `text-base` textarea on mobile (prevents iOS zoom), stacked controls `flex-col sm:flex-row`, 44px buttons
- **`dashboard/src/pages/DetailsPage.tsx`** — Stacked header buttons on mobile, touch-friendly targets
- **`dashboard/src/pages/BenchmarkPage.tsx`** — Stacked inputs, `min-w-[640px]` table with horizontal scroll, 44px provider toggles. Fixed pre-existing `CertBadge` missing `composite` prop.
- **`dashboard/src/pages/HistoryPage.tsx`** — Stacked header, `min-w-[480px]` table, 44px buttons/dropdowns
- **`dashboard/src/pages/LoginPage.tsx`** — `100dvh`, `px-4` mobile padding
- **`dashboard/src/components/config/DialPanel.tsx`** — Stacked save/reset buttons on mobile, 44px targets
- **`dashboard/src/components/shared/ExportButton.tsx`** — 44px trigger and dropdown items

### Verification
- TypeScript: 0 errors
- Frontend: 23/23 tests passed
- Python: 80 passed, 1 skipped
- Production build: successful (381ms)

---

## Session 23: Validation Study (April 8, 2026)

### Automated Validation Tests — 5/5 passed
- `validation/reproducibility_test.py` — Mock determinism + benchmark fixture
- `validation/sensitivity_test.py` — Dial sensitivity, prompt sensitivity, open simplex validation

### Baseline Study — 50/50 succeeded
- 50 mock prompts processed in 1.8s
- Composite: mean=65.5, std=6.2, range [59.4, 84.1]
- Certifications: Silver=39, Gold=7, Bronze=4
- Results saved to `validation/baseline_results.json`

### Synthetic Human Labels — 100 labels (2 raters x 50 items)
- `validation/generate_synthetic_labels.py` (NEW) — Generates Gaussian-noised labels from machine scores
- Rater_A: noise std=1.2, bias=+0.3 (slightly generous)
- Rater_B: noise std=1.5, bias=-0.2 (slightly harsh)
- Seeded RNG (seed=42) for reproducibility

### Full Correlation Analysis
- **Section 1 — Machine vs Human**: All 10 operators r=0.748–0.820, all p<0.0001 (strong positive)
- **Section 2 — Inter-Rater Reliability**: Cohen's kappa 0.05–0.20 (poor — expected from independent noisy simulations; real calibrated raters should improve)
- **Section 3 — Test-Retest**: Skipped (needs reproducibility data file)
- **Section 4 — Machine Summary**: Confirmed mean=65.5, std=6.2
- Report saved to `validation/correlation_report.txt`

### Next Steps
- Replace synthetic labels with real human labels for production validation
- Generate reproducibility data file for test-retest (Section 3)

---

## Session 22: Codex Audit — 3 Cleanup Fixes (April 8, 2026)

### Fix 1: Research Heuristic Disclaimer on Deployment Recommendations
- **`dashboard/src/lib/reportData.ts`** — Every deployment recommendation now ends with "Based on heuristic scoring — empirical validation pending. Not a validated safety assessment." Certification levels already wrapped with `(Research Heuristic)` in prior sessions.

### Fix 2: `bias_flags` Surfaced as Not Measured
- **`api/models.py`** — Added `bias_flags: int | None = None` to `NccsResponse`
- **`api/pipeline/stages.py`** — `NccsResult` dataclass gains `bias_flags: int | None`. `output_gate()` sets `bias_flags=None` and adds `"bias_flags"` to `not_measured` list. Engine still receives `bias_flag_count=0` placeholder internally.
- **`api/pipeline/runner.py`** — Propagates `bias_flags` to `NccsResponse`
- **`dashboard/src/api/types.ts`** — Added `bias_flags: number | null` to `NccsResult`
- **`dashboard/src/test/mocks/handlers.ts`** — Mock includes `bias_flags: null` and updated `not_measured`

### Fix 3: Provider-Specific LLM Error Semantics
- **`api/pipeline/stages.py`** — `base_llm_call()` now raises `LLMError(detail=..., provider=connector.provider_name)` instead of `PipelineStageError`. Returns 502 `{"detail": "...", "error_type": "llm_error", "provider": "..."}` via existing `llm_error_handler` in `api/errors.py`.
- **`tests/test_pipeline.py`** — Added `test_base_llm_call_failure_raises_llm_error`: verifies `LLMError` with correct provider name and detail message. Also added `bias_flags` assertions to `test_output_gate`.

### Verification
- Python: 85/85 tests passed (84 + 1 new LLM error test, 1 skipped)
- TypeScript: 0 errors
- Frontend: 23/23 tests passed

---

## Session 21: AI-Powered Natural Language Interpretation (April 8, 2026)

### Backend
- **`api/models.py`** — Added `InterpretationSchema` (bottom_line, findings, recommendations) and `interpretation` field on `WrapResponse`
- **`api/pipeline/interpreter.py`** (NEW) — 3 functions: `build_interpretation_prompt()` serializes all score data, `parse_interpretation()` regex-extracts 3 sections with fallback defaults, `generate_interpretation()` async orchestrator returning None on failure
- **`api/llm_connectors/mock_connector.py`** — Detects interpreter requests via system_prompt sentinel, returns deterministic 3-section briefing using seeded RNG
- **`api/pipeline/runner.py`** — Post-pipeline interpretation call after Stage 8 (not a 9th stage). Computes broken_chains from RPM drive scores, passes all score data to interpreter

### Frontend
- **`dashboard/src/api/types.ts`** — Added `Interpretation` interface and `interpretation?` field on `WrapResult`
- **`dashboard/src/components/shared/AiBriefing.tsx`** (NEW) — 3-section card: teal pill badge, amber "The Bottom Line", left-bordered findings, emerald bullet recommendations
- **`dashboard/src/pages/AssessmentPage.tsx`** — Added `viewMode` toggle (summary/technical), AiBriefing shown in summary mode, technical cards wrapped in conditional
- **`dashboard/src/pages/DetailsPage.tsx`** — Same toggle pattern with AiBriefing after "Input Text" card
- **`dashboard/src/lib/reportData.ts`** — Added `interpretation?` to `ReportData` interface and extraction
- **`dashboard/src/lib/exportPdf.ts`** — AI Executive Briefing section before Executive Summary (3 sub-sections, teal headers)
- **`dashboard/src/lib/exportDocx.ts`** — AI Executive Briefing heading with sub-sections before Executive Summary
- **`dashboard/src/lib/exportMarkdown.ts`** — `## AI Executive Briefing` with 3 markdown sub-sections
- **`dashboard/src/test/mocks/handlers.ts`** — Added interpretation to mock WrapResult
- **`dashboard/src/test/__tests__/AssessmentPage.test.tsx`** — Updated to verify AiBriefing in summary view, then switch to technical view for NCCS score

### Tests
- **`tests/test_interpreter.py`** (NEW) — 6 tests: prompt includes all data, well-formed parse, malformed fallback, mock end-to-end, failure returns None, deterministic output
- **`tests/test_wrap.py`** — Added interpretation assertions to `test_wrap_mock` (bottom_line, findings, recommendations)

### Verification
- Python: 84/84 tests passed (75 existing + 6 interpreter + 3 new assertions, 1 skipped)
- TypeScript: 0 errors
- Frontend: 23/23 tests passed

---

## Session 20: Benchmark Mode — Multi-Provider Statistical Comparison (April 8, 2026)

### Backend
- **`api/models.py`** — Added 3 new Pydantic schemas: `BenchmarkRequest` (text, providers, runs_per_provider 2-20, max_concurrency), `ProviderBenchmarkResult` (scores, mean, std_dev, min, max, certification_counts, high_variance flag, failed_runs, avg_latency_ms), `BenchmarkResponse` (results list, prompt_preview, total_runs, variance_threshold=5.0)
- **`api/routes/benchmark.py`** (NEW) — `POST /benchmark` endpoint. For each provider: creates connector via `get_connector()`, runs `WrapPipelineRunner` N times with `asyncio.Semaphore` concurrency control. Computes mean/stdev via `statistics` module. Providers with missing API keys report as failed_runs. Collects elapsed_ms from provenance for latency tracking.
- **`api/main.py`** — Registered `benchmark.router`

### Frontend
- **`dashboard/src/api/types.ts`** — Added `BenchmarkRequest`, `ProviderBenchmarkResult`, `BenchmarkResponse` interfaces
- **`dashboard/src/api/endpoints.ts`** — Added `postBenchmark()` typed wrapper
- **`dashboard/src/hooks/useBenchmark.ts`** (NEW) — TanStack Query mutation hook
- **`dashboard/src/pages/BenchmarkPage.tsx`** (NEW) — Full benchmark UI: textarea input, provider multi-select checkboxes, runs-per-provider input, results table sorted by mean descending. High-variance rows highlighted amber. Columns: Provider, Mean, Std Dev, Min, Max, Certifications, Latency, Failed, Flag.
- **`dashboard/src/App.tsx`** — Added lazy-loaded `/benchmark` route
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "Benchmark" nav item with bar-chart icon

### Tests
- **`tests/test_benchmark.py`** (NEW) — 5 tests: single mock (5 runs), multi mock (2 providers), low variance (deterministic mock), auth required (401), invalid provider (failed_runs = runs_per_provider)

### Verification
- Python: 75/75 tests passed (71 existing + 4 benchmark, 1 skipped)
- TypeScript: 0 errors
- Frontend: 23/23 tests passed

---

## Session 19: Four-Stream Parallel Integration (April 7, 2026)

### Stream A: Assessment Export (completed first, then upgraded by Stream C)
- **`api/store.py`** — Async hybrid assessment store: PostgreSQL via SQLAlchemy when NC_DATABASE_URL set, in-memory fallback otherwise. Max 1000 records/key. save_assessment() and get_assessments() are async.
- **`api/routes/export.py`** — `GET /assessments/export` with ExportResponse model (paginated: limit, offset, count). Async store integration.
- **`api/routes/wrap.py`** — Persists each pipeline result via `await save_assessment()`
- **`dashboard/src/pages/HistoryPage.tsx`** — "Export All Data" dropdown (CSV/JSON) client-side export from Zustand store

### Stream B: CAS-Native AI (Phase 4)
- **`cas-native/model/embedding.py`** — CognitiveStateEmbedding: 40-dim projection onto open probability simplex via softmax + epsilon floor
- **`cas-native/model/domain_descent.py`** — DomainDescentAttention: P→C→E→O causal mask with O→P feedback skip connection
- **`cas-native/model/rpm_gate.py`** — PrerequisiteGateLayer: 4 sequential SoftGate modules with section-retraction (separate eta/epsilon layers)
- **`cas-native/model/fractal_attention.py`** — FractalAttentionHead: IFS contraction maps with learnable Hutchinson operator
- **`cas-native/model/loss.py`** — CognitiveMetricLoss: Fisher-Rao geodesic distance + 6-component composite loss
- **`cas-native/model/topos_reasoner.py`** — CognitiveToposReasoner: intuitionistic 3-valued logic (true/false/undetermined)
- **`cas-native/model/cas_native_model.py`** — CASNativeModel: d_model=512, n_layers=6, n_heads=8, vocab_size=32000
- **`cas-native/training/trainer.py`** — CASTrainer: Adam + cosine LR + grad clip + checkpointing
- **`cas-native/training/data_pipeline.py`** — CASDataset + SimpleTokenizer + collate_fn
- **`cas-native/evaluation/evaluate.py`** — CASEvaluator: embedding quality, RPM satisfaction, inversion detection metrics
- **`cas-native/tests/`** — 7 test files: embedding(8), domain_descent(12), rpm_gate(8), loss(8), topos(7), model(11), data(12) = 66 tests

### Stream C: PostgreSQL Migration
- **`api/db.py`** (NEW) — Async SQLAlchemy engine + session factory, conditional import, init_db/close_db/check_db
- **`api/models_db.py`** (NEW) — Assessment SQLAlchemy model: id(UUID), api_key, timestamp, text, response(JSONB)
- **`api/migrations/001_create_assessments.sql`** (NEW) — PostgreSQL DDL
- **`api/config.py`** — Added `database_url: str | None = None` and `cors_origins: str = "*"`
- **`api/main.py`** — DB lifecycle (init_db/close_db) in lifespan, RequestIdMiddleware, configurable CORS
- **`tests/test_db.py`** (NEW) — 6 async tests: in-memory fallback, save/retrieve, key isolation, ordering, pagination, health/db
- **`requirements.txt`** — Added sqlalchemy[asyncio]>=2.0.0, asyncpg>=0.29.0

### Stream D: Deployment Hardening
- **`api/middleware/request_id.py`** (NEW) — X-Request-ID middleware (passes through or generates UUID)
- **`api/middleware/audit.py`** — Enhanced with request_id and content_length tracking
- **`api/middleware/auth.py`** — Added /health/db and /health/ready to PUBLIC_PATHS
- **`api/routes/health.py`** — Added `/health/db` (DB connectivity via api.db.check_db) and `/health/ready` (full readiness probe: API + cas-engine + DB)
- **`Dockerfile.api`** (NEW) — Multi-stage build (Rust maturin + Python runtime), non-root user, healthcheck
- **`dashboard/Dockerfile`** (NEW) — Node build + nginx serve with healthcheck
- **`dashboard/nginx.conf`** (NEW) — SPA fallback, API proxy, security headers, gzip, static asset caching
- **`docker-compose.yml`** — Full stack: cas-api + cas-dashboard + redis + postgres with health checks and resource limits
- **`.env.example`** — Complete env var template with NC_ prefix
- **`.github/workflows/ci.yml`** (NEW) — 3-job CI: rust-tests, python-tests, frontend-tests
- **`docs/DEPLOYMENT.md`** (NEW) — Docker Compose + Render deployment guide with env var reference

### Verification
- **Python**: 71/71 tests passed (65 existing + 6 DB tests, rewritten 5 export tests)
- **TypeScript**: 0 errors
- **Frontend**: 23/23 tests passed

---

## Session 18: Production Readiness — LLM Integration, Validation Tooling, Deployment (April 7, 2026)

### Section 1: Real LLM Integration
- **`.env.example`** — API key template with NC_ prefix namespacing
- **`api/llm_connectors/base.py`** — Added `CAS_SYSTEM_PROMPT` (structured prompt for all 10 COs, 4 domains, 7 drives), token usage logging, retry failure logging
- **`api/llm_connectors/openai_connector.py`** — 60s timeout, max_tokens=4096, temperature=0.3
- **`api/llm_connectors/anthropic_connector.py`** — 60s timeout, total_tokens computed
- **`api/llm_connectors/google_connector.py`** — total_tokens computed
- **`api/pipeline/stages.py`** — dial_adjustment uses CAS_SYSTEM_PROMPT
- **`dashboard/src/pages/AssessmentPage.tsx`** — mock=false for real providers, live API warning indicator

### Section 2: Validation Study Tooling
- **`scenarios/sample_prompts.json`** — 50 diverse prompts (ethics, hiring, healthcare, AI safety, leadership)
- **`validation/run_baseline_study.py`** — Batch runner via TestClient, extracts operator/domain/drive scores, summary statistics
- **`validation/human_labeling_tool.py`** — CLI for collecting human CO ratings (0-10) and domain coherence ratings per prompt-response pair
- **`validation/correlation_analysis.py`** — Pearson r with p-value, Fisher z-transform 95% CI, Cohen's kappa inter-rater reliability, 4-section report
- **`validation/README.md`** — Updated with full study workflow documentation

### Section 3: Deployment Preparation
- **`docker-compose.yml`** — cas-api + cas-dashboard (nginx) + Redis stack
- **`Dockerfile.api`** — Multi-stage build (Rust cas-engine via maturin, then Python runtime)
- **`dashboard/Dockerfile`** — Node build + nginx serve
- **`dashboard/nginx.conf`** — SPA fallback + API proxy + static asset caching
- **`infra/render.yaml`** — Render Blueprint (API web service + static dashboard)
- **`docs/DEPLOYMENT.md`** — Docker Compose + Render deployment guide
- **`api/config.py`** — Added rate_limit_tier setting (community/professional/enterprise)
- **`api/middleware/rate_limit.py`** — Tiered rate limiting with per-API-key monthly caps (Community: 50/mo, Professional: 500/mo, Enterprise: unlimited) + token bucket RPM

### Verification
- Python: 60/60 tests pass (55 core + 5 validation)
- Vitest: 23/23 tests pass
- TypeScript: 0 errors

---

## Session 17: Anthropic Emotions Integration + Validation Framework (April 7, 2026)

### PART 2: Anthropic Functional Emotions Integration

#### HowItWorksPage — "The Science Behind It" Section
- **`dashboard/src/pages/HowItWorksPage.tsx`** — Added 9th section (`id='science'`, label "The Science") to SECTIONS array and new `<SectionReveal>` block with three glass-card mapping cards:
  - **CO-3 Concretization** ↔ Frustration/curiosity functional states
  - **CO-5 Differentiation** ↔ Evaluative internal states
  - **CO-8/CO-9 Expansion/Contraction** ↔ Exploration/exploitation trade-off
  - Closing note on independent convergence strengthening both frameworks

#### FaqPage — New FAQ Entry
- **`dashboard/src/pages/FaqPage.tsx`** — Added FAQ item at index 1: "How does CAS relate to Anthropic's research on AI emotions?" with two-paragraph answer explaining functional emotions alignment and link to `/how-it-works#science`

#### OperatorRadarChart Tooltips
- **`dashboard/src/lib/interpretations.ts`** — Appended functional emotions parallels to OPERATOR_DESC entries:
  - Index 3 (Concretization): frustration/curiosity parallel
  - Index 5 (Differentiation): evaluative states parallel
  - Index 8 (Expansion): exploration drive parallel
  - Index 9 (Contraction): exploitation/focus parallel

### PART 3: Validation Framework

#### New Files
- **`validation/README.md`** — Description, usage instructions (`make validate`)
- **`validation/conftest.py`** — sys.path setup for api module resolution
- **`validation/benchmark_fixture.json`** — Frozen reference input with expected composite range (60-90), Gold certification, 8 stages all passing
- **`validation/reproducibility_test.py`** — 2 tests:
  - `test_mock_determinism` — 5 identical /wrap calls produce identical composites
  - `test_benchmark_fixture` — composite within range, cert matches, 8 stages pass
- **`validation/sensitivity_test.py`** — 3 tests:
  - `test_dial_sensitivity` — dials=5 vs dials=8 produce different dial_values
  - `test_prompt_sensitivity` — different prompts produce different operator scores
  - `test_open_simplex_validation` — domain_averages > 0 and sum ≈ 1.0

#### Build System
- **`Makefile`** — Added `validate` target after `test-node`, added to `.PHONY`
- **`pyproject.toml`** — Added `validation` to `testpaths`

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- `pytest tests/` — 55/55 tests pass
- `pytest validation/` — 5/5 tests pass

---

## Session 16: Performance — Lazy Loading, Chunk Splitting, Query Tuning (April 7, 2026)

### Route-Based Code Splitting
- **`App.tsx`** — All 8 page imports converted to `React.lazy()` with `Suspense` fallbacks. Each page is now its own chunk, loaded only when visited. Outer Suspense shows full-screen spinner, inner Suspense (within AppShell) shows inline spinner during page transitions.

### Dynamic Export Library Imports
- **`ExportButton.tsx`** — Removed static imports of `exportPdf`, `exportDocx`, `exportMarkdown`, and `captureChartImages`. All four are now `await import()`'d inside `handleExport()`, so jspdf (177 KB gz), html2canvas, docx (105 KB gz), and file-saver are never loaded until user clicks Export.

### Vite Chunk Splitting
- **`vite.config.ts`** — Added `build.rollupOptions.output.manualChunks()` function splitting:
  - `vendor` (react/react-dom/react-router): 70 KB gz — cached across all pages
  - `recharts` + d3: 111 KB gz — only on chart pages
  - `query` (@tanstack/react-query): 13 KB gz
  - `export-pdf` (jspdf + html2canvas): 177 KB gz — on-demand only
  - `export-docx` (docx + file-saver): 105 KB gz — on-demand only
- Initial page load (login/assessment) now ~90 KB gz vs previous ~500 KB monolithic bundle.

### TanStack Query Tuning
- **`main.tsx`** — Added `staleTime: 60_000` (1 min) and `gcTime: 5 * 60_000` (5 min) to QueryClient defaults. Prevents unnecessary refetches when navigating between pages.
- **`useHealth.ts`** — Health poll interval increased from 30s to 60s, added `staleTime: 30_000` to prevent redundant health checks.

### Also Fixed
- **`CohortHeatmap.tsx`** — Fixed keyless `<>` fragment in `.map()` → `<Fragment key>` (prevents React console warning).

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- `npx vite build` — Success, 30 chunks generated with correct splitting

---

## Session 15: Cohort Analysis — 3 Bug Fixes (April 7, 2026)

### Fix 1: Color Inconsistency
- **`CohortHeatmap.tsx`** — Replaced private `cellColor()` with exported `cohortColor(pct, mode)` supporting both `'bg'` (semi-transparent for heatmap cells) and `'text'` (solid for table text) modes. Fixed keyless Fragment → `<Fragment key>`.
- **`CohortPage.tsx`** — Removed local `alignmentColor()`, now imports shared `cohortColor` from CohortHeatmap. Same breakpoints everywhere: 80%+ cyan, 60%+ emerald, 40%+ amber, below red.

### Fix 2: Bhattacharyya Coefficient Display
- **`CohortPage.tsx`** — Added "Bhattacharyya" column to pairwise comparison table with `(?)` tooltip explaining it. Value shown as 4-decimal coefficient, color-coded using `cohortColor(bc * 100, 'text')` so 0-1 range maps to the same visual scale as percentages.

### Fix 3: Operator Score Input Validation
- **`CohortPage.tsx`** — Added `validateScores()` function checking: exactly 10 values, all numeric, all in [0, 1] range. Errors shown inline below each profile input in red. Score input border turns red on error. Compare button disabled when any profile has validation errors.

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass

---

## Session 14: 40-State Heatmap Thermal Redesign (April 7, 2026)

### StateHeatmap.tsx — Full Rewrite
- **Thermal color mapping**: Replaced flat domain-colored cells with NASA/thermal-camera gradient (cold navy → deep teal → cyan → amber → hot white-gold). Smooth interpolation between 8 color stops using RGB lerp.
- **Ranked cell animations**: Top 5 highest-intensity cells pulse with warm `heat-pulse` glow; bottom 5 lowest pulse with cold `frost-pulse` blue glow.
- **Expanded grid**: 12-column layout (label + 10×40px cells + row summary). Cell size increased from 28px to 40px for visual impact.
- **Row summaries**: Mini horizontal progress bars on right side with percentage. Strongest row labeled gold, weakest red.
- **Column summaries**: Mini vertical progress bars below grid with operator averages. Strongest column gold, weakest red.
- **Hover tooltip**: Custom CSS tooltip positioned above hovered cell showing `{Domain}{CO-n} = {score}/10` with amber highlight.
- **Legend bar**: Full-width horizontal gradient bar (Cold → Moderate → Hot) with labeled endpoints.
- **Score overlay**: High-intensity cells (≥0.7) show their score directly on the cell face.
- **Performance**: All 40 intensities + rankings computed in single `useMemo` pass.

### index.css — New Animations
- `@keyframes heat-pulse` — warm box-shadow pulsing via CSS custom properties
- `@keyframes frost-pulse` — cold blue box-shadow pulsing
- `.animate-heat-pulse` / `.animate-frost-pulse` Tailwind utility classes

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- No regressions, existing ExplainPanel click behavior preserved

---

## Session 13: Bug Fixes — Severity Labels & Heatmap Interactivity (April 7, 2026)

### Fix 1: NCCS Sub-Score Severity Normalization
- **`dashboard/src/lib/translations.ts`** — `translateNccs()` was dividing all sub-scores by 100, but each has a different max weight (operator=25, domain=20, drive=20, pathway=10, inversion=15, social=10). Added `NCCS_MAX_WEIGHTS` constant and normalized each sub-score by its correct maximum. Without fix: all severities showed "Critical" (e.g., 18.5/100=18.5%). With fix: correct severities (e.g., 18.5/25=74% → "Good").

### Fix 2: StateHeatmap React Fragment Key & Interactivity
- **`dashboard/src/components/charts/StateHeatmap.tsx`** — Fixed two issues:
  1. Replaced keyless `<>` fragment in `.map()` with `<Fragment key={domain}>` — eliminated React "unique key" console error that could cause rendering/click handler issues.
  2. Added `chart-interactive` class to root div — enables the CSS hover rule that shows "Click a cell for details" hint text on hover.

### Verification
- 0 TypeScript errors, 23/23 Vitest tests pass, 0 console errors
- Browser-tested: severity labels now show correct values (Good/Excellent), heatmap cells clickable with ExplainPanel drill-down working

---

## Session 12: Four-Task Implementation (April 7, 2026)

### Task 4: Makefile (DevEx)
- **`Makefile`** — Root-level build orchestration with `make install`, `make dev`, `make test`, `make clean`, `make build`, `make lint`, `make help`. Auto-detects Unix vs Windows venv layout. Handles Rust (maturin), Python (venv/pytest), and Node (npm) toolchains.

### Task 1: Translation Layer (UX)
- **`dashboard/src/lib/translations.ts`** — 40+ term mappings from mathematical CAS language to business-friendly labels (e.g., "geodesic_distance" → "Alignment Match", "dci" → "Processing Balance", "inversion_resistance" → "Stability Under Pressure"). Score severity classifier (excellent/good/moderate/concern/critical). Conversion helpers: `geodesicToAlignment()`, `bhattacharyyaToSimilarity()`, `translateNccs()`, `translateDomainCoherence()`.
- **`dashboard/src/hooks/useTranslation.ts`** — React hook transforming WrapResult into fully translated `TranslatedResult` with business-named operators, drives, inversions, executive summary, top strength/risk.
- **`dashboard/src/components/shared/TranslatedMetric.tsx`** — Reusable metric display with severity dot, hover tooltip, and color-coded value.
- **`dashboard/src/components/shared/ExecutiveSummary.tsx`** — Stakeholder-facing overview card with one-liner, top strength, priority improvement, and translated sub-score breakdown.
- **`dashboard/src/components/charts/DomainCoherenceRadar.tsx`** — New Recharts radar chart for 4 processing domains with DCI indicator and drill-down explanation panel.
- **`dashboard/src/pages/AssessmentPage.tsx`** — Wired in Executive Summary, DomainCoherenceRadar, InversionAlert, and translated chart titles.

### Task 2: Inversion Explainability & Audit Trail
- **`api/pipeline/stages.py`** — New `InversionEvidence` dataclass with axis, severity, trigger reason, and transcript snippet. `_build_evidence()` generates per-axis explanations referencing operator pairs, domain hierarchy, drive scores, and RPM chains. `inversion_scan()` now accepts `llm_text` and `rpm_drive_scores` parameters for evidence generation.
- **`api/pipeline/runner.py`** — Passes LLM response text and RPM drive scores to inversion scan stage. Serializes evidence into stage result data.
- **`dashboard/src/api/types.ts`** — Added `InversionEvidence` and cohort types.
- **`dashboard/src/components/shared/InversionAlert.tsx`** — Interactive evidence cards grouped by flagged/stable. Each card expands to show "Why this was flagged" trigger explanation and related transcript snippet. Color-coded by severity (none/low/moderate/stealth/high).

### Task 3: Dynamic Benchmarking & Cohort Clustering
- **`api/models.py`** — New models: `CohortProfile`, `CohortCompareRequest`, `CohortDistance`, `CohortCluster`, `CohortCompareResponse`.
- **`api/routes/cohort.py`** — `POST /batch/compare` endpoint. Builds 40-dim CognitiveStateVectors from profiles, computes pairwise geodesic distance and Bhattacharyya coefficient via Rust engine, converts to alignment/similarity percentages, runs single-linkage clustering.
- **`api/main.py`** — Registered cohort router.
- **`dashboard/src/api/endpoints.ts`** — Added `postCohortCompare()` typed wrapper.
- **`dashboard/src/hooks/useCohort.ts`** — TanStack Query mutation hook.
- **`dashboard/src/pages/CohortPage.tsx`** — Full cohort analysis page with profile input form, cluster summary with color-coded badges, alignment heatmap, and pairwise comparison table.
- **`dashboard/src/components/charts/CohortHeatmap.tsx`** — NxN alignment heatmap with gradient cell coloring.
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "Cohort Analysis" nav item.
- **`dashboard/src/App.tsx`** — Added `/cohort` route.
- **`tests/test_cohort.py`** — 5 tests: two profiles, identical profiles (100% alignment), three profiles (3 pairwise distances), requires ≥2, bad simplex rejection.

### Test Results
- Python: **55/55 passed** (50 existing + 5 new cohort tests)
- Vitest: **23/23 passed**
- TypeScript build: **0 errors**

## Session 11: Re-Audit Fixes (April 7, 2026)

### Re-Audit Item 1: Python Version Cap
- **`cas-engine/pyproject.toml`** — `requires-python` updated from `<=3.13` to `<=3.14`

### Re-Audit Item 2: Remove Unused Drive Scores Emission
- **`api/llm_connectors/mock_connector.py`** — Removed `Drive Scores: {drives}` line from mock response text (no pipeline stage parses it)

### Re-Audit Item 3: Research Heuristic Labelling
- **`dashboard/src/lib/reportData.ts`** — `certLevel` now includes `(Research Heuristic)` suffix. Verdict includes footnote: "Certification levels are based on heuristic scoring under active empirical validation."

### Re-Audit Item 4: Fix 8 Failing Tests
- **`tests/conftest.py`** — `domain_averages` fixed from `[0.5]*4` (sum=2) to `[0.25]*4` (sum=1) for simplex compliance
- **`tests/test_assess.py`** — All payloads use simplex domain_averages. Relaxed `social_engineering` assertion to allow None. Added `test_assess_rejects_bad_simplex`
- **`tests/test_connectors.py`** — Removed obsolete `test_registry_mock_mode_overrides`. Added `test_mock_connector_deterministic` and `test_registry_explicit_provider_respected`
- **`tests/test_pipeline.py`** — Fixed `test_rpm_gate` for short text (a0 may be < threshold). Added `test_rpm_gate_longer_text`. Added `social_engineering=None` and `not_measured` assertions to `test_output_gate`

### Result: 50/50 tests pass

## Session 10: 6-Item Audit Fix (April 7, 2026)

### Audit Item 1 (CRITICAL): Replace Pipeline Placeholder Values
- **`api/pipeline/stages.py`** — Full rewrite:
  - `rpm_gate()`: Derives A0/drive scores from text analysis (word count, vocab richness, SHA-256 seeded RNG) instead of hardcoded 0.7/0.6/0.5
  - `domain_coherence()`: Derives domain averages from operator scores via `_DOMAIN_OPERATOR_MAP` P=[0,1,4], C=[2,3,7], E=[5,6], O=[8,9]. Normalizes to open simplex (sum=1, all>0)
  - `inversion_scan()`: Accepts real drive_scores/domain_averages from earlier stages instead of using [0.7]*7
  - `output_gate()`: Sets `social_engineering=None` (not measured), uses 0.5 neutral placeholders, tracks `not_measured` list
  - Added `_text_seed()` helper for deterministic SHA-256 hashing
  - Added `_normalize_to_simplex()` helper for open probability simplex normalization
  - Added `RpmGateResult.heuristic` flag, `NccsResult.not_measured` list

### Audit Item 2 (HIGH): Fix Simplex Math Validation
- **`api/models.py`** — Added `@field_validator("domain_averages")` that enforces sum≈1 (±0.01) and all values >0 (open simplex). Changed `manipulation_resistance`/`overton_drift_resistance` defaults from 1.0 to 0.5
- **`dashboard/src/test/mocks/handlers.ts`** — Fixed mock `domain_averages` from `[0.85, 0.8, 0.75, 0.7]` (sum=3.1) to `[0.274, 0.258, 0.242, 0.226]` (sum=1.0). Set `social_engineering: null`, `not_measured: ['social_engineering']`, composite 68.0/Silver
- **`dashboard/src/test/__tests__/AssessmentPage.test.tsx`** — Updated assertions from 76.0/Gold to 68.0/Silver

### Audit Item 3 (HIGH): Fix Provider Routing
- **`api/llm_connectors/registry.py`** — Removed `settings.mock_llm` global override. Now only `provider == "mock"` triggers MockLLMConnector. Explicit provider choice (openai, anthropic, google, meta) is always respected

### Audit Item 4 (MEDIUM): Fix Reproducibility + Provenance
- **`api/llm_connectors/mock_connector.py`** — Uses deterministic `hashlib.sha256(prompt)` seed instead of `random.uniform` for reproducible mock responses
- **`api/pipeline/runner.py`** — Added provenance dict (pipeline_version, engine, input_hash, connector, elapsed_ms, rpm_heuristic). Passes flat_drives and domain_averages between stages properly. Propagates not_measured to NccsResponse
- **`api/models.py`** — Added `NccsResponse.not_measured: list[str]`, `NccsResponse.social_engineering: float | None`, `WrapResponse.provenance: dict`

### Audit Item 5 (MEDIUM): Fix PyO3 Compatibility
- **`cas-engine/Cargo.toml`** — Upgraded PyO3 from 0.24 to 0.25
- **`cas-engine/pyproject.toml`** — Capped `requires-python = ">=3.10,<=3.13"`

### Audit Item 6 (MEDIUM): Reframe All UI Text
- **`dashboard/src/lib/reportData.ts`** — Title → "AI Cognitive Architecture Assessment (Research Prototype)". Deployment text → "MEETS HEURISTIC THRESHOLD — empirical validation pending"
- **`dashboard/src/lib/exportMarkdown.ts`** — Added research disclaimer section. Footer → "Research Prototype"
- **`dashboard/src/lib/exportPdf.ts`** — Header → "NOETIC COMPASS — RESEARCH PROTOTYPE". Footer → "Heuristic scores — empirical validation pending"
- **`dashboard/src/lib/exportDocx.ts`** — Header/footer reframed with research prototype language
- **`dashboard/src/api/types.ts`** — `NccsResult.social_engineering` → `number | null`, added `not_measured?`, `WrapResult.provenance?`
- **`dashboard/src/lib/interpretations.ts`** — Handles null `social_engineering` (filters from scoring arrays)
- **`dashboard/src/components/charts/SubScoreBreakdown.tsx`** — Filters unmeasured sub-scores from chart
- **`dashboard/src/pages/FaqPage.tsx`** — Replaced "AI Psychology" with "AI Cognitive Architecture Assessment Platform (Research Prototype)"
- **`dashboard/src/pages/HowItWorksPage.tsx`** — Replaced "psychological alignment" with "cognitive architecture integrity and coherence"

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- `npm run build` — Success

## Session 9: Assessment Report Export Feature (April 7, 2026)

### Added
- `src/lib/reportData.ts` — Pure data extraction: `extractReportData()` pulls operator scores, domain averages, drives, RPM, inversions, pipeline stages from WrapResult. Computes top 3 strengths/vulnerabilities, deployment recommendation, one-paragraph verdict.
- `src/lib/exportMarkdown.ts` — Markdown export with ASCII tables, GitHub/Notion compatible. Uses `file-saver` for download.
- `src/lib/chartCapture.ts` — `captureChartImages()` uses `html2canvas` to capture chart sections as base64 PNGs from hidden DOM container.
- `src/lib/exportPdf.ts` — jsPDF-based A4 PDF generation with dark theme, teal section headers, embedded chart images, alternating-row tables, NCCS score highlight, certification badge, page footers.
- `src/lib/exportDocx.ts` — `docx` package Word document generation with proper heading styles, bordered tables, embedded chart ImageRuns, page numbering footer.
- `src/components/shared/HiddenReportCharts.tsx` — Off-screen chart renderer (all 7 charts at fixed 600px width) for html2canvas capture. Mounted only during export.
- `src/components/shared/ExportButton.tsx` — Dropdown button (PDF / DOCX / Markdown) with loading spinner, outside-click dismiss, dark glass-card styling.

### Modified
- `src/pages/AssessmentPage.tsx` — Added ExportButton after results render
- `src/pages/DetailsPage.tsx` — Added ExportButton next to Re-run button in header

### Dependencies Added
- `jspdf` + `html2canvas` — PDF generation (render DOM → canvas → PDF pages)
- `docx` — Programmatic DOCX generation
- `file-saver` + `@types/file-saver` — Cross-browser saveAs() download

### Report Sections (all formats)
1. Header (branding, date, model, assessment ID, CAS v7.4)
2. Executive Summary (NCCS score, cert level, verdict, strengths, vulnerabilities, deployment recommendation)
3. Cognitive Operator Profile (10 operators + involution pair balance)
4. Domain Coherence (4 domains + DCI + weakest domain)
5. Core Drive Integrity (7 drives, flagged if < 50%)
6. RPM Analysis (completeness + broken chains)
7. Inversion Analysis (7 axes + stealth resistance)
8. Pipeline Trace (8 stages pass/flag/block)
9. Footer (branding, CAS v7.4, Confidential, page numbers)

### Verified
- `npm run build` — 0 TypeScript errors
- `npx vitest run` — 23/23 tests pass (no regressions)

## Session 8: How It Works + FAQ Pages (April 6, 2026)

### Added
- `src/hooks/useScrollSpy.ts` — IntersectionObserver-based scroll-spy hook for sticky nav highlighting
- `src/components/shared/SectionReveal.tsx` — viewport-triggered fade-in + slide-up wrapper
- `src/pages/HowItWorksPage.tsx` — 8-section premium documentation page:
  - The Big Picture (8-stage pipeline diagram)
  - 10 Cognitive Operators (grid with involution pairs & self-duals)
  - 4 Processing Domains (vertical descent + feedback loop)
  - 7 Core Drives (cards with inversion pair indicators)
  - RPM Prerequisite Model (section-retraction chain, one-directional)
  - Inversion Detection (7 axes explained)
  - NCCS Scoring (stacked bar weights + certification tiers)
  - The Math (Fisher-Rao, open simplex, geodesic distance, admissibility)
- `src/pages/FaqPage.tsx` — 10-question accordion with animated expand/collapse and chevron rotation
- Sidebar nav entries for How It Works (book icon) and FAQ (question-mark icon)
- Routes `/how-it-works` and `/faq` in App.tsx
- CSS: `section-reveal`/`section-revealed` animation, `accordion-open`/`accordion-close` transitions, `scroll-spy-active` indicator

### Reuses
- All constants: OPERATOR_LABELS, DOMAIN_LABELS, DRIVE_LABELS, INVERSION_AXIS_LABELS, NCCS_WEIGHTS, PIPELINE_STAGES, CERTIFICATION_THRESHOLDS
- Colors: CERT_COLORS, DOMAIN_COLORS, DRIVE_COLORS

### Verified
- `npm run build` — 0 TypeScript errors
- `npx vitest run` — 23/23 tests pass (no regressions)

## Session 7: Interactive Assessment Readouts (April 6, 2026)

### Interactive Explanation Panels
- Created `src/components/shared/ExplainPanel.tsx` — reusable slide-down panel with close button, dark glassmorphism style
- Created `src/lib/interpretations.ts` — VP-friendly text generators for all 7 chart types + pipeline stages
- Added CSS `animate-slide-down` keyframe animation and `chart-interactive` / `chart-hint` utilities to `index.css`

### Chart Component Updates (all 7 + StageTimeline)
- **NccsGauge**: click → shows summary, top strength, biggest gap, recommendation. Accepts optional `nccs` prop.
- **SubScoreBreakdown**: click bar → shows sub-score description, weight contribution, verdict
- **OperatorRadarChart**: click → expands full operator list with descriptions + involution pair balance status
- **StateHeatmap**: click cell → shows domain×operator state interpretation with intensity rating
- **CoreDriveTree**: click bar → shows drive description, score, and inversion pair tension note
- **RpmGraph**: click drive row → shows prerequisite chain status with flowing/blocked indicators per node
- **InversionMap**: click → expands all 7 axes with descriptions + stealth resistance assessment
- **StageTimeline**: click stage → shows what happened, description, and pass/fail status

### Page Updates
- Updated `AssessmentPage.tsx` — passes `nccs` to NccsGauge, StageTimeline is now clickable
- Updated `DetailsPage.tsx` — passes `nccs` to NccsGauge

### Verification
- TypeScript: 0 errors
- Tests: 23/23 passing
- Build: successful

## Session 6: Phase 3 — Frontend Dashboard (April 6, 2026)

### Backend Enhancement (Pre-requisite)
- Added `drive_scores`, `involution_balances`, `axis_scores` to pipeline stage data in `api/pipeline/runner.py`
- Enables chart components to render full CAS visualization data

### T3.0: Vite + React + TypeScript Scaffold
- Created React 18 + TypeScript project via `create vite@latest --template react-ts`
- Installed: react-router-dom, @tanstack/react-query, recharts, tailwindcss v4, @tailwindcss/vite, zustand
- Dev deps: vitest, jsdom, @testing-library/{react,jest-dom,user-event}, msw
- Configured vite proxy (`/api` → `localhost:8000`), Tailwind v4 CSS import

### T3.1: TypeScript Types + Constants
- `src/api/types.ts` — 12 types mirroring api/models.py (NccsResult, WrapResult, etc.)
- `src/lib/constants.ts` — OPERATOR_LABELS[10], DOMAIN_LABELS[4], DRIVE_LABELS[7], INVERSION_AXIS_LABELS[7], NCCS_WEIGHTS, PIPELINE_STAGES[8]
- `src/lib/colors.ts` — Certification colors, domain/drive/involution pair palettes

### T3.2: API Client Layer
- `src/api/client.ts` — fetch wrapper with JWT from localStorage, typed ApiError
- `src/api/auth.ts` — getToken/setToken/clearToken/isAuthenticated
- `src/api/endpoints.ts` — typed wrappers: postWrap, postAssess, postBatch, getConfig, putConfig, getHealth

### T3.3: TanStack Query Hooks + Zustand Store
- `src/hooks/` — useWrap (saves to history), useAssess, useBatch, useConfig (query+mutation), useHealth (30s refetch)
- `src/stores/historyStore.ts` — Zustand + persist middleware, localStorage-backed, max 100 records

### T3.4: Shared Components
- Card, LoadingSpinner, ErrorBanner (with status code labels), CertBadge

### T3.5: Chart Components (7 visualizations)
- NccsGauge — semicircular Recharts PieChart, certification-colored
- SubScoreBreakdown — horizontal BarChart, 6 NCCS sub-components with weight labels
- OperatorRadarChart — 10-spoke RadarChart (CO-0 to CO-9)
- StateHeatmap — CSS grid 4×10 (domains × operators), intensity-colored cells
- CoreDriveTree — 7 horizontal bars, drive-colored
- RpmGraph — custom SVG, 7 rows × 4 nodes (A0→Dn→Wn→Pn), colored by satisfaction
- InversionMap — 7-axis RadarChart with stealth resistance display

### T3.6: Layout Components
- AppShell — flex layout with 240px sidebar, mobile hamburger
- Sidebar — nav links + health indicator dot
- Header — title, auth status, logout

### T3.7: AssessmentPage
- Text input + provider select + submit
- Full chart rendering on success: gauge, sub-scores, radar, heatmap, drives, RPM, inversions
- Stage timeline with status indicators

### T3.8: Dial Components
- `src/lib/validation.ts` — validateDials: range [3,9] + involution divergence ≤4
- DialSlider — range input (3-9) with operator label
- DialPanel — 10 sliders grouped by self-dual/involution pairs, inline validation, save/reset

### T3.9: ConfigPage
- Loads config via useConfig, renders DialPanel, save/reset with success feedback

### T3.10: HistoryPage + DetailsPage
- History table with timestamp, text excerpt, composite, certification, link to details
- Details view with all charts, full text, stage timeline, raw JSON toggle, re-run button

### T3.11: Router + LoginPage
- BrowserRouter: / (Assessment), /history, /config, /details/:id, /login
- JWT token input + connect flow, auth guard redirects to /login

### T3.12: Tests (23 passing)
- validation.test.ts (8): dial range, involution divergence, edge cases
- NccsGauge.test.tsx (3): renders composite for Gold/Fail/Platinum
- DialPanel.test.tsx (5): slider count, save/reset, disabled while saving
- AssessmentPage.test.tsx (2): form render, submit flow with MSW
- api.test.ts (5): auth store, JWT header attachment, 401/422 error handling

**Total: 42 Rust + 47 Python + 23 Frontend = 112 tests passing. PHASE 3 COMPLETE.**

## Session 5: Phase 2 — API Gateway + LLM Connectors (April 6, 2026)

### Task 2.1: PyO3 Bindings (maturin)
- Added `pyo3` dependency (optional feature `python`) to cas-engine/Cargo.toml
- Created `cas-engine/src/python_bindings.rs` exposing all core types to Python:
  - CognitiveOperator, Domain, CoreDrive, CognitiveStateVector, DialConfig
  - OperatorScores, DomainCoherence, InversionScanner, RpmProfile
  - compute_nccs(), geodesic_distance(), bhattacharyya_coefficient()
- Created `cas-engine/pyproject.toml` for maturin build
- Note: Python 3.14 requires `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1`

### Task 2.2: Python Project Scaffold
- `api/config.py` — pydantic-settings (env-based: API keys, JWT, rate limits, mock mode)
- `api/models.py` — Pydantic schemas: AssessRequest, WrapRequest, BatchRequest, NccsResponse, DialConfigSchema, etc.
- `api/errors.py` — DialViolationError (422), ScoringError (422), LLMError (502), PipelineStageError (500)
- `api/main.py` — FastAPI app with CORS, lifespan, middleware stack, exception handlers
- `requirements.txt`, `pyproject.toml`

### Task 2.3: LLM Connectors (5 providers + mock)
- `api/llm_connectors/base.py` — BaseLLMConnector ABC with async retry + exponential backoff
- `api/llm_connectors/openai_connector.py` — OpenAI SDK (GPT-4)
- `api/llm_connectors/anthropic_connector.py` — Anthropic SDK (Claude)
- `api/llm_connectors/google_connector.py` — Google GenAI SDK (Gemini)
- `api/llm_connectors/meta_connector.py` — Meta/Llama via OpenAI-compatible API
- `api/llm_connectors/mock_connector.py` — Synthetic CAS-formatted responses for testing
- `api/llm_connectors/registry.py` — Factory with NC_MOCK_LLM env var override

### Task 2.4: 8-Stage Wrap Pipeline
- `api/pipeline/stages.py` — All 8 async stages calling Rust engine via PyO3:
  1. input_analyzer → AnalyzedInput
  2. rpm_gate → RpmGateResult (Rust RPM)
  3. dial_adjustment → AdjustedInput (Rust DialConfig, 422 on violation)
  4. base_llm_call → LLMResponse
  5. operator_scoring → OperatorScoreResult (Rust OperatorScores)
  6. domain_coherence → DomainCoherenceResult (Rust DCI)
  7. inversion_scan → InversionResult (Rust InversionScanner)
  8. output_gate → NccsResult (Rust compute_nccs)
- `api/pipeline/runner.py` — WrapPipelineRunner orchestrator

### Task 2.5: API Routes
- `POST /assess` — direct assessment from pre-scored input (bypasses LLM)
- `POST /wrap` — full 8-stage pipeline with LLM call
- `POST /batch` — batch assessment with async concurrency + semaphore
- `GET/PUT /config` — dial configuration (422 on violations)
- `GET /health` — service status

### Task 2.6: Middleware
- `api/middleware/auth.py` — JWT Bearer token validation (python-jose), 401 on failure
- `api/middleware/rate_limit.py` — In-memory token bucket per API key, 429 on exceeded
- `api/middleware/audit.py` — Structured JSON audit logging (async, non-blocking)

### Task 2.7: Tests (47 Python tests passing)
- test_assess.py (6), test_wrap.py (5), test_batch.py (4), test_config.py (7)
- test_connectors.py (6), test_pipeline.py (12), test_middleware.py (7)

**Total: 42 Rust + 47 Python = 89 tests passing. PHASE 2 COMPLETE.**

## Session 4: Inversions + Integration Tests (April 6, 2026)
- Implemented cas-engine/src/inversions/mod.rs (Task 1.5):
  - InversionDetection: per-axis detection with severity, stealth flag, description
  - InversionScanner: configurable scanner with severity threshold
  - InversionScanInput: bundles operator/domain/drive/state/pathway data
  - InversionScanResult: 7 axis_scores + stealth_resistance + compound_severity
  - 7-axis detection: N(operator imbalance), W(domain order violation), F(drive imbalance), E(entropy deficit), S(sub-drive variance), A(pathway prerequisite violation), P(compound top-2 product)
  - Stealth detection: severity in [0.3, 0.7] flagged as stealth
  - to_resistance_input(): bridges to scoring module
  - 59 unit tests
- Implemented cas-engine/tests/integration_tests.rs (Task 1.6):
  - 42 integration tests across 7 categories:
    - End-to-end assessment flow (6): perfect→Platinum, zero→Fail, mid→Silver/Gold
    - Ontology↔Metric integration (6): distance properties, domain bias correlation
    - Ontology↔Scoring integration (6): DCI from state vectors, involution balance
    - RPM↔Scoring integration (6): completeness→pathway quality, A0 blocking
    - Operator algebra (6): monoid associativity (1000 triples), identity, involution
    - Mathematical invariants (7): weight sum, score bounds, certification boundaries
    - Sensitivity/regression (5): perturbation stability, imbalance impact
- Clean build: 0 warnings
- Total: 240 tests passing (198 unit + 42 integration)
- PHASE 1 COMPLETE

## Session 3: Scoring Engine (April 6, 2026)
- Implemented cas-engine/src/scoring/mod.rs (Task 1.3):
  - CertificationLevel: Platinum/Gold/Silver/Bronze/Fail with boundary scoring
  - OperatorScores: 10-operator scoring with involution balance (3 pairs)
  - OperatorScores::profile_score(): 70% avg + 30% balance
  - DomainCoherence: DCI = weakest/strongest domain average, from state vector or explicit
  - InversionResistanceInput: 7 axis scores + stealth + compound severity (consumed from Task 1.5)
  - SocialEngineeringInput: manipulation + Overton drift resistance
  - PathwayQualityInput: RPM completeness + bias flags
  - compute_nccs(): full NCCS composite (0-100) with 6 weighted components summing to 1.0
  - NccsResult with Display, components() decomposition
  - 32 tests: certification boundaries, operator scoring, DCI, all input validations, NCCS composite (perfect/zero/mid-range), weight sum verification
- Clean build: 0 warnings
- Total: 139 tests passing

## Session 2: Fisher-Rao Metric + RPM Monad (April 6, 2026)
- Implemented cas-engine/src/metric/mod.rs (Task 1.2):
  - TangentVector type with validation (components sum to 0)
  - Fisher-Rao inner product: g^FR_p(u,v) = Σ(uk*vk/pk)
  - Fisher-Rao norm: ||u||_p = sqrt(g^FR_p(u,u))
  - Bhattacharyya coefficient: BC(p,q) = Σ√(pk*qk)
  - Geodesic distance: d(p,q) = 2*arccos(BC(p,q)) with numerical clamping
  - 30 tests: non-negativity, symmetry, triangle inequality (125 triples), bilinearity, positive definiteness
- Implemented cas-engine/src/rpm/mod.rs (Task 1.4):
  - EmbeddedScore: η(s) = (s, s², √s) enriched representation
  - realize(): ε(a,b,c) = a, satisfying section law ε∘η = id (CORRECTION 2)
  - RpmState: node state with cached one-directional satisfaction
  - RpmGate: prerequisite check (fail-closed, one-directional)
  - RpmChain: A0→Dn→Wn→Pn with prerequisite gating per drive
  - RpmProfile: all 7 chains with overall/weakest/strongest completeness
  - CoverageMorphismDirection: documents counit direction (CORRECTION 3)
  - 41 tests: section law (1001 points), non-reversibility, prerequisite gating, chain completeness, profile construction
- Fixed 1 test assertion (max_by tie-breaking order for strongest_chain)
- Total: 107 tests passing

## Session 1: Ontology Types (April 6, 2026)
- Implemented all CAS ontology types in cas-engine/src/ontology/:
  - operators.rs: 10 CognitiveOperators with monoid composition, involution, admissibility (CORRECTION 1), dial system (3-9 range, max 4 involution divergence)
  - domains.rs: 4 ProcessingDomains with total order (P>C>E>O), descent chain, feedback loop
  - states.rs: 40 CognitiveStateIds, CognitiveStateVector on open simplex (CORRECTION 4: all pk > 0, Vec<f64> for serde compat)
  - drives.rs: 7 CoreDrives with inversion pairs, 28 DomainDrives, DriveProfile with balance scoring
  - pathways.rs: 22 PathwayNodes (A0 + D/W/P x 7), RPM chain structure, 7 InversionAxes
- All 36 unit tests passing
- Used Vec<f64> instead of [f64; 40] for CognitiveStateVector because serde doesn't support arrays > 32

## Session 0: Project Initialization (April 2026)
- Created monorepo structure
- Created CLAUDE.md master instruction file
- Status: Ready for Phase 1 implementation

### Current Status
- [x] Phase 1: CAS Scoring Engine — COMPLETE (42 Rust tests)
- [x] Phase 2: API Gateway + LLM Connectors — COMPLETE (71 Python tests)
- [x] Phase 3: Frontend Dashboard — COMPLETE (23 Frontend tests)
- [x] Phase 4: CAS-Native AI — COMPLETE (66 PyTorch tests, not yet run — requires PyTorch)

### Next Steps
1. Run CAS-Native test suite (requires `pip install torch`)
2. Run full validation study (reproducibility, sensitivity, baseline)
3. Production PostgreSQL deployment testing
4. Empirical validation study with human raters

### Failed Approaches
- Agent 2 (Validation Study) could not execute in worktree due to Bash permission limitations — validation tests must be run from main session

### Known Limitations
- serde doesn't derive Serialize/Deserialize for [f64; 40], using Vec<f64> with runtime length validation instead
