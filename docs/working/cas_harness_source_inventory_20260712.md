# CAS Harness Source and Evidence Inventory - 2026-07-12

Status: operational-reconciliation snapshot. This inventory locates source and evidence; it does not promote a research result into a product claim. `FLAG_FOR_HUMAN_REVIEW` is not `ACCEPT`, and `OPEN` is not complete.

## 1. Authoritative decision sources

- Production dashboard: `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md`.
- Current legal/spec claim sheet: `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md`.
- Operational status: `docs/working/cas_harness_operational_status_20260630.md`.
- Product repository: `https://github.com/LittleHenderson/noetic-compass`.
- Public product branch: `origin/master` at `1c60d7f5` after merged PRs #137, #138, and #139.

The production TODO controls status and next-action wording. This inventory is a locator and reconciliation aid.

## 2. Current hosted truth

- `https://noetic-compass-api.onrender.com/health` returns HTTP 200.
- Merged PR #137 is deployed. Origin-bearing protected-route 401 responses for both `https://atlas.noeticcompass.com` and a representative Vercel preview origin include `Access-Control-Allow-Origin` and `X-Request-ID`, and omit `Access-Control-Allow-Credentials`.
- Bearer-header preflight returns HTTP 200 with the requested `authorization` header allowed and no browser-managed credential header.
- Hosted deterministic 429 CORS proof remains `OPEN` until a valid hardened account token can drive the quota/rate-limit path.
- Hosted worker status after deployed PR #138 is `configured: true`, `reachable: false`, `real_weights: false`, `configuration_error: worker_token_required`; `/atlas/live/health/realmode` returns 503 `atlas_live_worker_token_required` without contacting the dead endpoint. The obsolete RunPod proxy returns HTTP 404 on both 8888 and 8080. Source/configuration fail-closed behavior is present, while actual hosted live-worker operation remains `OPEN`.
- PR #139 is merged at `1c60d7f5`. The bounded five-stage Audit Console, hardened Evidence Packet actions, protected-token controls, truthful failure/progress states, and `can_run_audit` fail-closed behavior are deployed at `https://atlas-viewer-app.onrender.com/audit-console`; source verification is `552 passed, 2 skipped`, TypeScript compilation passed, and the production build passed.
- DNS/TLS/custom-host delivery is `present` and operational. Public DNS authoritatively returns `CNAME atlas-viewer-app.onrender.com`; the trusted certificate has `CN=atlas.noeticcompass.com` and is valid from 2026-07-12 through 2026-10-10; `https://atlas.noeticcompass.com/audit-console` returns HTTP 200; and HTTP redirects 301 to the same HTTPS path. At 2026-07-13T00:12:18Z the custom host returned `strict-transport-security: max-age=31536000; includeSubDomains`, added through the Render dashboard, while the Render origin retained `max-age=315360000; includeSubdomains; preload`.
- Custom/origin delivery parity is mechanically present: both HTML responses have SHA-256 `09b1b0367c2282db22796d9fe636846e30ce38c896114f91dda122686bbc3691`; both reference `/assets/index-AZfLzoo4.js`; and both bundle responses have SHA-256 `a4640e74a2d2f66944101a2af14460fe07209ce717fd837f494362c4740d7a1f`. Current-bundle markers include `Start a new audit`, `Reference/demo`, `Protected API token`, and `can_run_audit`.
- Production account mode remains dark with `NC_ACCOUNTS_ENABLED=false`. Commit `df7c3e1e` is unmerged source hardening with `171 passed` in the combined focused verification and `188 passed` in an independent red-team run. Paid/public account readiness remains `OPEN` and hosted account-mode proof is `unavailable`.

## 3. Canonical source roots

All product code is under `noetic-compass-scaffold/noetic-compass/`.

| Area | Authoritative roots | Notes |
|---|---|---|
| HTTP product API | `api/routes/cas_harness_audit.py`, `api/routes/cas_harness_live_worker_health.py`, `api/routes/evidence.py` | Audit lifecycle, worker health, packet read/verify/anchor |
| Product services | `api/services/cas_harness_*.py` | Audit runners, scale planner, distributed/fleet execution, evidence bridge, verifier, WORM |
| Durable state | `api/services/production/state_substrate/`, `api/state_ledger_bootstrap.py` | SQLite single-host proof and Postgres contract/fencing path |
| Accounts/security | `api/services/accounts/`, `api/services/sessions/`, `api/middleware/auth.py`, `api/dependencies/authz.py` | Hardened source at unmerged `df7c3e1e`; keep dark pending the paid/multi-replica gates below |
| Usage quotas | `api/services/quotas.py` | Tenant-isolated idempotent source path exists at `df7c3e1e`; plan entitlement, billing attribution, and compute/storage quotas remain `OPEN` |
| Worker | `live-trace-worker/` | Real open-weight capture/ablation worker, Docker and restart tooling |
| Launch UI | `atlas-viewer/src/pages/AuditConsolePage.tsx`, `atlas-viewer/src/components/audit/`, `atlas-viewer/src/lib/casHarnessAuditApi.ts` | Current command center and Evidence Packet UI |
| Evidence and WORM | `api/routes/evidence.py`, `api/services/cas_harness_static_evidence_anchor.py`, `api/services/cas_harness_evidence_anchor.py` | Production S3 Object-Lock path and honest packet gates |
| Product tests | `tests/test_cas_harness_*.py`, `tests/test_evidence*.py`, `atlas-viewer/src/**/*Audit*.test.tsx` | Primary regression roots |
| Readiness documents | `docs/working/production_readiness/` | State, fleet, compliance, rollout, WORM, and hosted evidence documents |

A tracked-name search on current master returns 72 directly named CAS Harness, Audit Console, and Evidence Packet files. This is a convenience count, not a complete boundary: shared auth, state, middleware, CRM, and generic evidence files are also load-bearing.

Useful discovery command:

```powershell
git ls-files *cas_harness* *CasHarness* *AuditConsole* *EvidencePacket*
```

## 4. GitHub reconciliation

### Completed or retired

- PR #137 `fix(cas-harness): harden CORS, auth audit, and CI isolation` is merged into `master`.
- PR #138 `fix(cas-harness): harden hosted worker deployment` is merged and deployed. Remote worker targets now require a server-side token before any network access; Render worker URL/token are dashboard-managed; the no-SSH 8080 smoke and runbook are present.
- PR #139 is merged into `master` at `1c60d7f5`. The five-stage public audit flow and its independent hardening fixes are deployed on the Render Atlas Viewer; `552 passed, 2 skipped`, TypeScript compilation, and production build are present as source verification.
- PR #130 is closed as a literal no-op: its head was an ancestor of master and its merge tree equaled current master.
- `wave5.5/harness-launch-declutter` must be retired as a deployment source. It is stale and would delete the modern Audit Console, API client, tests, progress, verdict, verification, and FAQ surfaces.

### Open items requiring deliberate treatment

- PR #135: superseded security-incomplete account work. Do not enable or merge it as launch-ready. Replacement source is committed at `df7c3e1e`, but that replacement remains unmerged and dark pending the explicit paid-launch gates below.
- PR #128: useful Grok provenance work, but it conflicts with the newer Stage 9 packet merger and requires manual claim-safe reconciliation.
- PRs #79 and #77: historical rollout/M4 planning branches. They are not current product bases and must not overwrite master.
- PRs #53, #51, #50, #49, #48, and #47: older cockpit, worker-proof, demo, research, health, and scenario work. Reconcile individual commits only after comparing each assertion and test to current master; never merge the stack blindly.
- PRs #34, #33, and #32: older SDG/CAS-native work outside the immediate CAS Harness launch path.

### Current integration and tracking branches

- `build/cas-harness-operational-20260712`: account/tenant/quota integration base; the worker hardening formerly stacked here is already separated and merged through PR #138.
- `build/cas-account-hardening-20260712`: source commit `df7c3e1e` for per-account credentials, durable sessions, bootstrap/recovery, same-tenant RBAC, platform-only tenant provisioning, auth-epoch invalidation, durable audit sessions, idempotent quotas, fail-closed evidence ownership, and fenced run claims. Verification is `171 passed` combined and `188 passed` independent; it is not deployed.
- `build/cas-ui-launch-20260712`: merged through PR #139 at `1c60d7f5`; no longer an unmerged deployment source.
- `docs/cas-harness-status-20260712`: this inventory and current spec/status reconciliation.

Unmerged branches remain engineering work until committed, tested, pushed, reviewed, merged, deployed, and hosted-proven. The PR #139 branch is retained here only as merged provenance.

## 5. Local and offline evidence roots

The large artifact archive is `D:\tksCAS-archive\` and currently contains 71 top-level entries. Keep large activations and model artifacts there; keep summaries, manifests, hashes, and claim decisions in Git.

High-signal roots:

- `pythia160m_gate1_reproduction_20260531`: canonical Pythia-160M Gate 1/3 reproduction set. Its archived pre-fix packet contains an overclaimed `ACCEPT`; the honest current verdict is `FLAG_FOR_HUMAN_REVIEW`.
- `pythia160m_activation_cover_ablation_20260603`: activation-level candidate versus matched ablation work; evidence toward control closure, not final `control_proof: present`.
- `pythia160m_object_lock_anchor_20260603`: production Object-Lock anchor evidence.
- `gpt_neox_20b_stage9_original_40e_closure_20260527`: saved Stage 9 original 40E hidden-readout artifacts.
- `gpt_neox_20b_stage9_original_40e_causal_proof_20260528`: saved Stage 9 causal artifacts.
- `gpt_neox_20b_stage9_original_40e_bridge_proof_20260528`: saved eta-to-epsilon bridge artifacts.
- `condition3_mtc_capture_20260603` and `condition3_mtc_comparator_20260603`: GPT-NeoX Condition-3 blind matched-taxonomy evidence. Comparator verdict is `GREY`; it is not Pythia uniqueness proof.
- `definition_locked_tks_mtc_20260603`: owner-definition-locked TKS40/F28 fixture artifacts.
- `cas_harness_prompt_injection_audit_packet_20260615`: bounded prompt-injection audit packet; stronger prevention/removal claims remain `NOT LICENSED`.
- `cjt_bias_vibration_*_qwen_20260618`: PCBA/CJT W0 and causal follow-ups.
- `grounded_factual_qa_*`, `outcome_native_hallucination_*`, and `hidden_prompt_injection_*`: outcome-native and pre-answer research lanes; hidden-state detection/prevention product claims remain `OPEN` / `NOT LICENSED` unless a later claim audit says otherwise.
- `w0_rpm_lacunarity_all_layers_qwen_20260611`: historical RPM/lacunarity artifacts. The rejected asymmetric-ablation product prototype is not restored by this archive.

Other top-level archive families are retained under the same root: CAS68 recipe audit, detection probes, enabled-predicate captures, Qwen confirmatory/v6 runs, pre-speech causal work, structural/topos bridge work, typed probes, checkpoints, and RunPod runs.

## 6. Claim and exclusion ledger

- RPM/diode executor: `PROTOTYPE`; `ENGINEERED-NOT-VALIDATED`; real-model result `unavailable`; ceiling `FLAG_FOR_HUMAN_REVIEW`; product/causal/prevention claims `NOT LICENSED`; empirical bridge `OPEN`. The unsafe prototype is removed from the product branch.
- Pythia-160M WORM packet: immutable and `FLAG_FOR_HUMAN_REVIEW`, not `ACCEPT`.
- `control_proof`: `unavailable` on the live customer path until matched controls actually run and are packet-bound.
- Hosted CORS exact/preview 401 and preflight: present as hosted engineering evidence after PR #137. Hosted deterministic 429 remains `OPEN`.
- Hosted live worker: source/configuration policy is deployed and fail-closed; actual worker operation remains `OPEN` because the configured RunPod endpoint is absent.
- Launch UI and custom-domain delivery: `present` and operational after PR #139, with trusted TLS, HTTP-to-HTTPS redirect, HTML/bundle byte parity against the Render origin, and HSTS.
- Paid accounts, billing, quotas, and customer management: `OPEN`; hosted account-mode proof is `unavailable`; keep `NC_ACCOUNTS_ENABLED=false`.
- Compliance minimum and legal/customer-data consent: `OPEN` pending owner/legal sign-off.

## 7. Paid-account red-team gates

The `df7c3e1e` verification counts are source evidence, not paid/multi-replica readiness.

**P0 — paid/multi-replica blockers:**

1. Evidence Packet bytes and hash chains are host-local. The S3 anchor stores only manifest/hash/path metadata, so replicas cannot read one another's packet bytes and their chains may diverge. Required closure: a tenant-keyed immutable object store, durable packet index, concurrency-safe/WORM receipt, restart proof, and two-replica proof.
2. The client account flow is incompatible with the hardened API: login/refresh still posts a username and relies on a baked legacy mint secret, and no bootstrap/redeem/rotate/recovery UX exists. Required closure: the per-account `api_credential` client flow plus end-to-end verification.
3. Distributed/fleet execution is unavailable in account mode because tenant-scoped service credentials, mTLS, and capabilities are absent.
4. No paid entitlement system exists. Quota remains hardcoded, with no plan/subscription/license/billing attribution or compute/storage quotas.

**P1 — production-hardening blockers:**

5. The run lease prevents simultaneous duplicate spend, but there is no durable phase/provider idempotency/crash reconciliation; an orphan `RUNNING` attempt or packet can repeat spend after the lease expires.
6. Synchronous single-connection Postgres plus `RLock` blocks the async authentication hot path. Required closure: an async pool or bounded offload with reconnects and timeouts.
7. No account disable/reactivate/list/support lifecycle endpoint exists with an `auth_epoch` bump, session revocation, and a durable security receipt.

**P2 — residual controls:** process-local rate limits and a racy global session scan; global email uniqueness that blocks multi-organization membership; and security events written as ordinary logs rather than immutable tenant-scoped audit events.

## 8. Reconciliation rules

1. Build public product work from current `master`, never from the stale wave branch.
2. Preserve large raw artifacts in `D:\tksCAS-archive\`; commit only summaries/manifests/hashes needed for reproducibility.
3. Do not use a passing synthetic test as a real-model result.
4. Do not convert `FLAG_FOR_HUMAN_REVIEW` into `ACCEPT` without every verifier gate, matched control, and WORM condition.
5. Do not describe worker/account source as operational until hosted smoke proves the actual route. PR #139 UI and custom-domain delivery are `present` and operational; this does not close the separate worker, account, billing, compliance, research, or customer-production gates.
6. Any new evidence root must be added here and to the production TODO with its exact claim boundary.
