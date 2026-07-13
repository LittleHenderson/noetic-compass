# CAS Harness — Operational Status & Consolidation Map

**Date:** 2026-06-30 · **Author:** operational sweep (Claude Code) · **Confidential**
**Purpose:** single command-center for the goal "complete the CAS Harness build, make it operational, fix findings, gather all files, red-team, update spec." Preserves reserved-language claim words exactly.

---

## 0. Current maintenance snapshot (2026-07-12)

This entry supersedes the 2026-06-30 branch, test, CORS, and RPM/diode status below where they differ. It does not strengthen a product, hosted-production, customer-production, or `ACCEPT` claim.

**Maintenance repair merged and deployed.** [PR #137](https://github.com/LittleHenderson/noetic-compass/pull/137) merged `fix/cas-harness-findings-20260630` into `master` at merge commit `66b943f9`. Current verified source evidence remains `1526 passed, 8 skipped, 3 xfailed` for the full API suite, `358 passed` for the CAS Harness selection, `233 passed` for the worker tree, and `22 passed` for focused middleware/CORS. The two previously reported pytest collection blockers are fixed. The pre-merge Vercel preview failure was project-membership policy for commit author `wakil`, not a Python test failure. Merge/deploy status does not create customer-production proof or `ACCEPT`.

**CORS/middleware boundary.** Browser-managed CORS credentials are disabled for every origin while explicit Bearer `Authorization` headers remain available. Effective order is `CORS -> RequestId -> AuditLog -> JWTAuth -> RateLimit`. Hosted Render proof on 2026-07-12 confirms exact-origin and Vercel-preview protected-route `401` responses include `Access-Control-Allow-Origin` and `X-Request-ID` with no `Access-Control-Allow-Credentials`; Bearer-header preflight returns 200 with `authorization` allowed and still no browser-managed credential header. Hosted deterministic `429` proof remains `OPEN` pending a hardened valid-token path. Durable append-only security-audit storage remains `OPEN`.

**RPM/diode red-team correction.** Status is exactly `PROTOTYPE` / `ENGINEERED-NOT-VALIDATED`; real-model result `unavailable`; verdict ceiling `FLAG_FOR_HUMAN_REVIEW`; product, causal, prevention, and removal claims `NOT LICENSED`; empirical bridge `OPEN`. The tool is not in the product branch, and its two files are removed from the legal-branch tip pending rebuild.

**Source inventory.** The authoritative GitHub, local-worktree, code-root, archive-root, and claim-boundary map is [CAS Harness Source and Evidence Inventory - 2026-07-12](cas_harness_source_inventory_20260712.md).

**Hosted worker deployment boundary.** [PR #138](https://github.com/LittleHenderson/noetic-compass/pull/138) merged into `master` at `b9e47ebe` after `1546 passed, 8 skipped, 3 xfailed`. The deployed API now refuses every remote worker URL before network access unless `ATLAS_LIVE_WORKER_TOKEN` is configured; hosted health reports `configuration_error: worker_token_required`, and `/atlas/live/health/realmode` returns 503 `atlas_live_worker_token_required`. The dead hard-coded 8888 URL is removed, URL/token are dashboard-managed, and the 8080 no-SSH hosted WORM smoke/runbook are present. Actual hosted worker operation remains `OPEN`: the old RunPod pod is absent, a persistent GPU worker has not been redeployed, and no new hosted live audit/WORM packet proof exists.

**Public audit UI merged and deployed.** [PR #139](https://github.com/LittleHenderson/noetic-compass/pull/139) merged into `master` at `1c60d7f5`. The deployed Render Atlas Viewer now exposes the bounded five-stage Audit Console, hardened Evidence Packet actions, protected-token controls, truthful failure/progress states, and `can_run_audit` fail-closed behavior. Verification is `552 passed, 2 skipped`; TypeScript compilation and the production build also passed. `https://atlas-viewer-app.onrender.com/audit-console` is the current verified UI endpoint.

**Custom-domain delivery gate — `present` and operational.** Public DNS authoritatively returns `CNAME atlas-viewer-app.onrender.com`. The trusted certificate has `CN=atlas.noeticcompass.com` and is valid from 2026-07-12 through 2026-10-10. `https://atlas.noeticcompass.com/audit-console` returns HTTP 200, while HTTP returns 301 to the same HTTPS path. At 2026-07-13T00:12:18Z the custom host returned `strict-transport-security: max-age=31536000; includeSubDomains`, added through the Render dashboard; the Render origin retained `max-age=315360000; includeSubdomains; preload`. Custom/origin HTML bytes are identical at SHA-256 `09b1b0367c2282db22796d9fe636846e30ce38c896114f91dda122686bbc3691`; both reference `/assets/index-AZfLzoo4.js`, whose custom/origin bytes are identical at SHA-256 `a4640e74a2d2f66944101a2af14460fe07209ce717fd837f494362c4740d7a1f`. Current-bundle markers include `Start a new audit`, `Reference/demo`, `Protected API token`, and `can_run_audit`. This closes only the DNS/TLS/custom-host delivery gate; it does not strengthen overall product readiness or any account, worker, research, causal, or `ACCEPT` claim.

**Account backend checkpoint — pushed, dark, source only.** Commit `010ea8f13e2fde623369772b06679e86aec8245f` on `build/cas-account-hardening-20260712` closes the final backend red-team correction slice while retaining `NC_ACCOUNTS_ENABLED=false` by default. Its prior authoritative full API/service run is `1652 passed, 8 skipped, 3 xfailed`; the final correction slice is `87 passed`. This does not claim a later standalone full backend rerun.

**Customer account UI checkpoint — pushed, dark, source only.** Commit `0f17cb562ff6a01f3598363b9fbddbc154e467a9` on `build/cas-account-ui-20260712` adds the hardened account-credential flow. TypeScript compilation passed; focused verification is `52/52 passed`; the full UI suite is `581 passed, 2 skipped`; and the production build passed. `VITE_ACCOUNTS_ENABLED=false` and `NC_ACCOUNTS_ENABLED=false` remain the defaults. Customer fleet operation remains `OPEN`, and hosted tenant-bound fleet proof is `unavailable`.

**Mode7 persistence-linkage checkpoint — pushed, source only.** Commit `9ea1d13ade721606f72c17e143a225618fbc659e` on `fix/mode7-final-trace-20260712` makes streamed head-commit linkage use the same persistence-backed trace id as the final event and keeps both empty when persistence fails. Verification is `12` Mode7 tests, `17` SGGS tests, and `2` targeted persistence/linkage tests. Merge, deploy, and hosted proof remain `OPEN`.

**Detached integration proof — source only.** A disposable detached combination at `aeb86374`, using exact backend `010ea8f1` plus Mode7 `9ea1d13a`, passed `1654 passed, 8 skipped, 3 xfailed` and `git diff --check`. Neither source branch was changed. Merge, deploy, paid/public account readiness, and hosted account-mode proof remain `OPEN` / `unavailable`.

**PR publication boundary.** GitHub GraphQL PR publication/status calls were blocked by host socket policy in this environment, so PR status is `OPEN`; remote branch refs are present. Direct review routes are [account backend](https://github.com/LittleHenderson/noetic-compass/compare/master...build%2Fcas-account-hardening-20260712), [customer account UI](https://github.com/LittleHenderson/noetic-compass/compare/master...build%2Fcas-account-ui-20260712), and [Mode7 linkage](https://github.com/LittleHenderson/noetic-compass/compare/master...fix%2Fmode7-final-trace-20260712).

**P0 paid/multi-replica blockers.** (1) Evidence Packet bytes/hash chains remain host-local; the S3 anchor stores only manifest/hash/path metadata, so replicas cannot read each other and chains may diverge. Closure requires tenant-keyed immutable object storage, a durable packet index, concurrency-safe/WORM receipt, restart proof, and two-replica proof. (2) Deployed `master` still lacks the hardened customer account flow. Unmerged `0f17cb56` supplies per-account login, invite redemption, credential rotation/logout UX plus an explicit operator-only bootstrap/recovery boundary, but closure requires reviewed merge, deliberate flag enablement, and hosted end-to-end proof. (3) Distributed/fleet execution remains `OPEN` in account mode without tenant-scoped service credentials, mTLS, and capabilities; hosted tenant-bound fleet proof is `unavailable`. (4) No paid entitlement system exists: quota is hardcoded and plan/subscription/license/billing attribution plus compute/storage quotas are absent.

**P1 production-hardening blockers.** (5) The run lease blocks simultaneous duplicate spend but lacks durable phase/provider idempotency/crash reconciliation, so an orphan `RUNNING` attempt or packet can repeat spend after expiry. (6) Synchronous single-connection Postgres plus `RLock` blocks the async auth hot path; an async pool or bounded offload with reconnects/timeouts is required. (7) Account disable/reactivate/list/support lifecycle endpoints are absent, including the required `auth_epoch` bump, session revocation, and durable security receipt.

**P2 residual controls.** Rate limits are process-local and the global session scan is racy; global email uniqueness prevents multi-organization membership; security events are ordinary logs rather than immutable tenant-scoped audit events. These do not change the `OPEN` / `unavailable` launch status above.

Red-team bypass findings: the surface-screen gate trusted an unbound self-attested string; `n_random=0` with out-of-range `subsumption_threshold=2.0` manufactured `PASS_DIRECTIONAL_PENDING_REVIEW`; hidden-minus-char/length and rank/accuracy-matched non-prerequisite controls were absent; missed reverse collapse was mislabeled as survival; invalid group splits fell back; CLI NPZ loading used `allow_pickle=True`; reverse-causality/no-dependence wording overclaimed the measurement; reports lacked `PROTOTYPE`, provenance, and split evidence; and CI/API/Evidence-Packet/runbook integration was absent. No real-model or product result exists.

## 1. Where CAS Harness actually lives (branch topology)

| Branch | Role | CAS Harness content |
|---|---|---|
| **`origin/master`** | **Product source of truth** (hosted Render proof, WORM, CRM, state ledger) | **22 `cas_harness_*` services**, `cas_harness_audit.py` + `cas_harness_live_worker_health.py` routes, full `tests/test_cas_harness_*`, `live-trace-worker/` |
| `codex/cascompass-legal-live-source` (**current working tree**) | Legal / landing site source | 1 service (`scale_planner`), the **spec sheet** + all `docs/working/cas_harness_*`; **256 commits ahead / 159 behind** master |
| `codex/cas-harness-live-run` (PR #130, DRAFT) | Hosted live-worker audits | live-run wiring |
| `codex/cas-harness-public-beta-candidate` | Beta candidate | the CJT/PCBA W0 pipeline scripts (surface screen, bank builder, evaluator, capture) |
| `fix/cas-harness-findings-20260630` (**new, local worktree, not pushed**) | This sweep's fixes | commit `5583f7bf` |

**Key fact:** the product is on `master`; your active checkout is the legal branch. Work is fragmented across `master` + **15 open PRs** + **30+ harness/atlas/cockpit/evidence branches**. Consolidation is a real, outstanding need (see §7).

---

## 2. Code surface (on `master`)

- **22 services** (`api/services/cas_harness_*.py`): `verdict_runner`, `evidence_bridge`, `evidence_anchor`, `static_evidence_anchor`, `harvest`, `fleet_executor`, `fleet_verifier`, `distributed_audits`, `audit_sessions`, `merged_evidence_packets`, `scale_planner`, `architecture_adapter`, `compute_feasibility`, `cost_acknowledgment`, `data_governance`, `model_access`, `model_provenance`, `probe_compatibility`, `api_endpoint_runner`, `live_worker_runner`, `tks_definition_lock`, `verifier_decision_adapter`.
- **Routes:** `cas_harness_audit.py`, `cas_harness_live_worker_health.py`, `evidence.py`, `atlas_live.py` (+ `explainer`, `mode7`, `idea_atlas`).
- **Worker:** `live-trace-worker/scripts/` (14 scripts incl. `run_stage9_40e_subspace_ablation.py`, `discover_stage9_40e_neuron_covers.py`, `merge_stage9_40e_evidence_packet.py`, `evaluate_40_element_probe.py`).
- **Frontend:** `atlas-viewer/` (Vite/React) — routes `/audit-console` (default) and `/cockpit`; proxies `/api` → `http://localhost:8000`.

---

## 3. Operational verification (local, this sweep)

| Layer | Result |
|---|---|
| API boot (`uvicorn api.main:app`) | ✅ `{"status":"ok","version":"0.1.0","engine":"cas-engine"}` |
| Auth token mint (`/auth/token`, `NC_DEBUG=true`) | ✅ mints JWT |
| Public paths | `/health`, `/health/db`, `/health/ready`, `/auth/token`, `/docs`, `/openapi.json`, `/redoc` (all else needs a token) |
| **Harness API unit tests** (`tests/ -k cas_harness`) | ✅ **358 passed** (2 unrelated `cas-native` collection errors) |
| **Worker/ablation suite** (`live-trace-worker`, stage9/subspace/neuron/bridge/merge/s7_f28) | ✅ **79 passed** (was 78/1 before fix) |

Run recipe (Windows PowerShell): API via `.venv` python + `uvicorn`; worker tests via **system Python 3.14** (has numpy/sklearn; the `.venv` does not). Full recipe in the terminal instructions delivered 2026-06-30.

---

## 4. Findings

**Fixed (branch `fix/cas-harness-findings-20260630`, commit `5583f7bf`, NOT pushed):**
1. **Stale test** — `test_s7_f28_evidence_packet_merge::test_merger_builds_packet_with_six_pass_ready_proof_chips` expected the audit normalizer to downgrade `cas_readout`/`output_proof` `verified→present`. That predates the "pass embedded proof chips through verbatim" behavior pinned by the canonical `test_stage9_packet_uses_embedded_verification_proof_chips` (`verified` verbatim). Aligned the stale expectations. Worker suite 78/1 → **79 passed**.
2. **sklearn deprecation** — removed `n_jobs=-1` from 4 `LogisticRegression` constructions (`discover_stage9_40e_neuron_covers`, `evaluate_40_element_probe` ×2, `run_stage9_40e_subspace_ablation`). No-op on lbfgs; `FutureWarning` on sklearn 1.8, removed in 1.10. Behavior-neutral.

**Noted (not yet fixed):**
3. **cas-native pytest collection error** — `cas-native/model/type_constraints.py:18` uses a relative import with no parent package, breaking collection of `test_turn_admissibility.py` + `test_type_constraints.py` and polluting the API test run (worked around with `--continue-on-collection-errors`). Tangential to CAS Harness; low priority. Fix = make `cas-native/model` an importable package (conftest `sys.path`/`__init__.py`) or absolute imports.
4. **Transient `MemoryError`** during the heavy ablation test under load (many worktrees + API server running); passed on retry. Not a code defect; note as a CI resource consideration.

**Red-team of the launch/auth surface:** running (separate agent); findings appended in §8.

---

## 5. New capability built this session — the CJT/RPM knockout tool

`live-trace-worker/scripts/run_rpm_diode_asymmetric_ablation.py` (+ `tests/test_rpm_diode_asymmetric_ablation.py`, **7 passed**) — the fixed-probe (no-retrain) cross-ablation the CJT/RPM assessment identified as the one missing primitive. It gives CAS Harness a **causal-necessity** proof the shipped (retrain-based) ablation can't produce, plus a **subsumption control** that correctly downgrades a confounded directional result to `GREY` instead of a false PASS. Verdict ceiling `FLAG_FOR_HUMAN_REVIEW` (no `ACCEPT`). Currently on the legal-branch working tree; belongs on the product branch alongside `run_stage9_40e_subspace_ablation.py`. See `cas_harness_cjt_rpm_assessment_20260630.md`.

---

## 6. Spec sheet versions

- **Current:** `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md` (+ `.pdf`) — the update target.
- **Historical:** `noetic-compass-scaffold/noetic-compass/docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_6…v2_0_INVESTOR_EXTERNAL_NDA_*.md` (superseded).
- The spec lives on the **legal branch (HEAD)**, not master.

---

## 7. Consolidation recommendation

The single biggest structural risk is fragmentation: product on `master`, spec+docs+CJT tool on other branches, 15 open PRs, 30+ related branches. Recommended (owner-gated) sequence:
1. Decide the **source of truth** — recommend `master` for product code; keep the legal branch for the landing/spec.
2. Triage the 15 open PRs: land or close each (many are stale May-2026 atlas/cockpit PRs).
3. Move the CJT tool + this sweep's fixes onto `master` via one PR.
4. Retire dead worktrees under `C:\tmp\` (10+ exist).

---

## 8. Red-team findings (launch/auth surface on `master`)

Authorized security review of `api/` request flows. 6 findings; several previously-feared issues are **correctly defended**.

**Fixed this sweep** (branch `fix/cas-harness-findings-20260630`, commit `9b44a6d1`, NOT pushed; `415 passed`):
- **[#4 HIGH] CORS wildcard + credentials** (`main.py:154-162`, `config.py`): default `allow_origins=["*"]` with `allow_credentials=True` reflects the request Origin back with `Access-Control-Allow-Credentials: true`, letting any site make credentialed cross-origin calls. **Fixed:** credentials now enabled only for an explicit origin allowlist; the Vercel-alias regex path is unchanged so demos still work. (Runtime confirmation on the pinned Starlette still advised.)
- **[#5 MEDIUM] Audit log missed failed-auth** (`main.py:166-169`): `AuditLogMiddleware` sat innermost, so `JWTAuthMiddleware`'s 401 short-circuited before it ran — credential-stuffing on `/auth/token`, forged-token probes, and unauthorized-access attempts were never logged. **Fixed:** reordered so AuditLog wraps JWTAuth (RequestId stays outermost).

**OPEN — owner-gated (NOT changed; deliberate design or larger work):**
- **[#1 HIGH] Public alpha audit-session lifecycle** (`middleware/auth.py:33-43`): `/api/cas-harness/audit/session`, `/session/{id}/run`, `/sessions` are public by `startswith` matching. An anonymous caller can create + run audits (spending server-config LLM keys, writing WORM/harvest). **This is INTENTIONAL for the alpha** (comment `auth.py:14-18`; pinned by `test_verify_reference_model_target_public_for_alpha_console`, `test_anonymous_callers_share_only_the_anonymous_bucket`). Mitigated by fail-closed anonymous-bucket owner scoping. **Paid-launch decision:** gate these behind JWT + require BYOK for anonymous runs. Do not flip without owner sign-off (breaks alpha tests).
- **[#2/#3 HIGH] No RBAC on privileged ops** (`middleware/auth.py:108-125` mints `role` but nothing consumes it): any authed token can register fleet workers, lease jobs, submit merge fragments, create frontier runs, and `POST /evidence/{trace_id}/anchor` (irreversible WORM write) / read any packet by `trace_id` (IDOR). **Fix (larger):** a `require_role` dependency gating anchoring + frontier-creation to operator, and worker register/lease/receipt to a fleet service credential; owner-scope evidence reads/anchors.
- **[#6 MEDIUM] Debug-mode open mint** (`routes/auth.py:49-81`): with `auth_mint_secret` unset AND `debug=True`, `/auth/token` mints a JWT for any username. Prod is fail-closed (unset secret + `debug=False` → 401). **Launch step:** remove the debug-gated open mint before external users.

**Correctly defended (do NOT worry about these):**
- Prod JWT-secret enforcement — app refuses to start on the default secret when `debug=False` (`main.py:73-77`).
- Prod `/auth/token` fail-closed — constant-time `hmac.compare_digest`, not a client-shipped secret.
- Audit-session owner scoping (IDOR) — fail-closed; owner key from `sub`+`api_key`, deterministic salted `audit_id`, `_owns` re-checks, identity stripped from `to_dict` (`cas_harness_audit_sessions.py:194-234,318-327`).
- SSRF via customer `endpoint_url` — validated https/localhost, only recorded (never fetched); outbound calls use server-configured base URLs.
- Path traversal in evidence verify — allowlisted roots + sanitized trace_id components + size caps.
- Invite redemption, TKS definition-lock (fail-close on hash mismatch), data-capture governance gate (422).

---

## 9. What only YOU can do (owner-gated)

1. **Landing decision:** approve moving `fix/cas-harness-findings-20260630` (and the CJT tool) onto `master` via PR. Pushing to `master` auto-deploys Render — that's why I have not pushed.
2. **Source-of-truth decision:** confirm `master` = product branch; give the OK to consolidate PRs/branches against it.
3. **Production secrets** (for a real hosted run): `NC_AUTH_MINT_SECRET`, S3/WORM credentials + bucket, `NC_DATABASE_URL` (managed Postgres for multi-instance), Airtable CRM keys.
4. **GPU worker:** a RunPod/GPU box running the `live-trace-worker` with real model weights is required for any **live** model audit (and for the CJT empirical bridge). Local runs = console + reference packets only.
5. **Vercel MCP auth:** the `plugin:vercel:vercel` server needs authorization in an interactive session before its tools work.
6. **Legal/IP sign-off** on any spec-sheet claim changes before external distribution.
