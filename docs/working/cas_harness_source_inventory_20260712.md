# CAS Harness Source and Evidence Inventory - 2026-07-12

Status: operational-reconciliation snapshot. This inventory locates source and evidence; it does not promote a research result into a product claim. `FLAG_FOR_HUMAN_REVIEW` is not `ACCEPT`, and `OPEN` is not complete.

## 1. Authoritative decision sources

- Production dashboard: `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md`.
- Current legal/spec claim sheet: `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md`.
- Operational status: `docs/working/cas_harness_operational_status_20260630.md`.
- Product repository: `https://github.com/LittleHenderson/noetic-compass`.
- Public product branch: `origin/master` at `66b943f9` after merged PR #137.

The production TODO controls status and next-action wording. This inventory is a locator and reconciliation aid.

## 2. Current hosted truth

- `https://noetic-compass-api.onrender.com/health` returns HTTP 200.
- Merged PR #137 is deployed. Origin-bearing protected-route 401 responses for both `https://atlas.noeticcompass.com` and a representative Vercel preview origin include `Access-Control-Allow-Origin` and `X-Request-ID`, and omit `Access-Control-Allow-Credentials`.
- Bearer-header preflight returns HTTP 200 with the requested `authorization` header allowed and no browser-managed credential header.
- Hosted deterministic 429 CORS proof remains `OPEN` until a valid hardened account token can drive the quota/rate-limit path.
- Hosted worker status is currently `configured: true`, `reachable: false`, `real_weights: false`; the obsolete RunPod proxy returns HTTP 404 on both 8888 and 8080. Hosted live-worker operation therefore remains `OPEN`.
- Production account mode remains dark. Paid/public account readiness is `OPEN` and hosted account-mode proof is `unavailable`.

## 3. Canonical source roots

All product code is under `noetic-compass-scaffold/noetic-compass/`.

| Area | Authoritative roots | Notes |
|---|---|---|
| HTTP product API | `api/routes/cas_harness_audit.py`, `api/routes/cas_harness_live_worker_health.py`, `api/routes/evidence.py` | Audit lifecycle, worker health, packet read/verify/anchor |
| Product services | `api/services/cas_harness_*.py` | Audit runners, scale planner, distributed/fleet execution, evidence bridge, verifier, WORM |
| Durable state | `api/services/production/state_substrate/`, `api/state_ledger_bootstrap.py` | SQLite single-host proof and Postgres contract/fencing path |
| Accounts/security | `api/services/accounts/`, `api/services/sessions/`, `api/middleware/auth.py`, `api/dependencies/authz.py` | Unmerged hardening work; not launch-ready yet |
| Usage quotas | `api/services/quotas.py` | Engine exists; production route wiring and hardened account identity are still being integrated |
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
- PR #130 is closed as a literal no-op: its head was an ancestor of master and its merge tree equaled current master.
- `wave5.5/harness-launch-declutter` must be retired as a deployment source. It is stale and would delete the modern Audit Console, API client, tests, progress, verdict, verification, and FAQ surfaces.

### Open items requiring deliberate treatment

- PR #135: mechanically clean but security-incomplete. Do not enable or merge as launch-ready; it permits legacy-token session bypass, uses a browser-visible global mint secret, has no first-owner bootstrap, permits tenant/role escalation, is not crash-atomic, and leaks store handles. A hardened replacement is in progress.
- PR #128: useful Grok provenance work, but it conflicts with the newer Stage 9 packet merger and requires manual claim-safe reconciliation.
- PRs #79 and #77: historical rollout/M4 planning branches. They are not current product bases and must not overwrite master.
- PRs #53, #51, #50, #49, #48, and #47: older cockpit, worker-proof, demo, research, health, and scenario work. Reconcile individual commits only after comparing each assertion and test to current master; never merge the stack blindly.
- PRs #34, #33, and #32: older SDG/CAS-native work outside the immediate CAS Harness launch path.

### Active local integration branches

- `build/cas-harness-operational-20260712`: account/tenant/quota integration base plus worker configuration hardening.
- `build/cas-account-hardening-20260712`: secure per-account credential, session, bootstrap, RBAC, transaction-recovery, and lifecycle rebuild.
- `build/cas-ui-launch-20260712`: five-stage public Audit Console shell and Evidence Packet actions.
- `docs/cas-harness-status-20260712`: this inventory and current spec/status reconciliation.

These branches are engineering work until committed, tested, pushed, reviewed, merged, deployed, and hosted-proven.

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
- Hosted live worker: `OPEN` because the configured RunPod endpoint is absent.
- Paid accounts, billing, quotas, and customer management: `OPEN`.
- Compliance minimum and legal/customer-data consent: `OPEN` pending owner/legal sign-off.

## 7. Reconciliation rules

1. Build public product work from current `master`, never from the stale wave branch.
2. Preserve large raw artifacts in `D:\tksCAS-archive\`; commit only summaries/manifests/hashes needed for reproducibility.
3. Do not use a passing synthetic test as a real-model result.
4. Do not convert `FLAG_FOR_HUMAN_REVIEW` into `ACCEPT` without every verifier gate, matched control, and WORM condition.
5. Do not describe worker/account/UI branches as deployed until hosted smoke proves the actual route.
6. Any new evidence root must be added here and to the production TODO with its exact claim boundary.

