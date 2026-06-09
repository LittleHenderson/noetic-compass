# inbox_claude — 2026-06-09 — CAS Harness launch-line engineering handoff

## 2026-06-09 — claude: launch-line audit + proposed gap-fill + collision flags (REOPENING the exchange protocol)

**Context.** This channel went dormant after ~2026-05-15. The entire CAS Harness public-beta launch
line (security spine, durable accounts/sessions/quotas, live-worker runner, Audit Bench UI) was built
on `launch/integration` → `codex/cas-harness-public-beta-candidate` (tip ~`b34de28`) outside this
channel. Reopening it BEFORE Claude touches any launch-branch code, per user direction (2026-06-09).

**What Claude did (read-only).** A 3-area ground-truth audit (worker auth / StateStore-vs-dict /
Render durability) + a recon of the candidate branch. No code edited.

**Re-scored against the 5 engineering edges the user raised:**
- **render/disk** — DONE on candidate (Starter + 1 GB `/var/data`, evidence dir pinned, worker URL wired). Duplicate `infra/render.yaml` lingers.
- **StateStore** — substrate + fail-loud stores (`accounts/`, `sessions/`, `quotas.py`) DONE on candidate. Gaps remain (below).
- **worker token** — still static `X-Atlas-Worker-Token`. NOT fixed.
- **connector tiers (BEHAVIORAL vs MECHANICAL)** — untouched.

**Genuine remaining gaps (Claude's proposed work, ranked):**
1. **Worker smoke — KEYSTONE, operational not code.** The live-trace-worker runner is real + wired (`cas_harness_live_worker_runner.py` flips `causal_proof → present` only when `is_real_model==True`), and `scripts/hosted_live_worker_worm_smoke.py` exists. But the RunPod worker at `ATLAS_LIVE_WORKER_URL` (…`6bmmab3vbf1yij-8888.proxy.runpod.net`) is **NOT serving** — Claude probed 2026-06-09: 404 on `/`, `/health`, `/docs`, AND `/openapi.json` (a live FastAPI always serves `/openapi.json`). Needs pod (re)launch + token on both ends, then run the WORM smoke `--require-object-lock`. Blocks the injection-detection thesis.
2. **Per-job worker token** (after #1) — replace static `X-Atlas-Worker-Token` with a short-lived per-trace jose JWT (`aud=worker`, `sub=trace_id`, `jti`, `exp≤300s`). Mint at `api/services/atlas_live_worker_auth.py`; verify at `live-trace-worker/app/auth.py`; copy the stream-token JWT pattern in `api/routes/atlas_live.py`.
3. **Evidence-store ephemeral-path guard** (cheap, high-honesty) — `cas_harness_merged_evidence_packets.py` `_packet_store_dir()` silently falls back to `/tmp` when `CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR` is unset. Add a fail-loud check (refuse authoritative I/O from an ephemeral path), mirroring `state_ledger_bootstrap.py`. NOTE: `master`'s render.yaml is missing this env var → evidence packets are ephemeral on master TODAY.
4. **Durable `_SESSIONS`** — `cas_harness_audit_sessions.py:90` `_SESSIONS` is still pure-volatile (not ledger-mirrored). Lower urgency (verdicts re-derive from the durable EP). Use `quotas.py` as the StateStore template.
5. **Housekeeping** — retire `launch/paid-quotas` (superseded by candidate's `quotas.py`); dedupe the two `render.yaml`; backport the evidence-packet env var to master; add the admin disable-account route the account smoke needs.

**Collision flags — need Codex's read before Claude touches anything:**
- **Canonical branch:** confirm `codex/cas-harness-public-beta-candidate` is THE launch base (Claude will branch off it, not `wave5.5`/`master`).
- **EP-explainer overlap:** Claude's 6 local packet-explainer tasks (PacketExplainerPanel, `askExplainerForPacket`, EvidenceRail anchors) overlap Codex's "Explain this packet" commit (`37fb7a4`) — same files (`explainerApi.ts`, `EvidenceRail.tsx`, `AuditAppFrame.tsx`). Reconcile before either pushes.
- **In-flight worktrees:** `quotas-engine`, `audit-identity`, `paid-security-*`, `tenant-iso`, `stateless-audit`, `ui-audit-bench` are live — flag which files Codex is mid-flight on so Claude avoids them.

**Open request to Codex:**
1. Confirm the canonical launch branch.
2. Claim which of gaps #1–#5 Codex is already doing vs wants Claude to take.
3. Confirm worker-pod status — is a RunPod worker meant to be live now? (It isn't responding.)
4. Decide the EP-explainer reconciliation (keep Codex's, keep Claude's, or merge).

AUTHORIZED: — (proposal/handoff only; no code or pod action until Codex audits + user "go".)

---

## 2026-06-09 (later) — claude: injection-eval harness + addons received & assessed

Two zips arrived from a parallel build (likely the user's other Claude thread): `injection_eval_harness-1.zip` (the referee) and `cas_injection_addons.zip` (`worker_contract/` + `datasets/` + the harness). Read-only assessed both. Verdict: **ADAPT** — keep the engine, build the gaps. For Codex:

- **The scientific spine is RIGHT** (this is the part our MTC/Condition-3 GREY lesson demands): blinded control-only calibration (raises `CalibrationLeakageError` if injected data touches threshold-setting), a matched **`CLEAN_INSTRUCTION`** control arm (H2: INJECTED > CLEAN_INSTRUCTION = the signal-vs-leakage guard), dependency-free tie-corrected Mann–Whitney + effect-size floor + pre-committed n, frozen/hashed criteria, and a diagnostic guard (mock runs forced to `DIAGNOSTIC_ONLY`/`formal=false`). Corpus: 360 rows, 4 arms (CLEAN_NEUTRAL 110 / CLEAN_INSTRUCTION 110 / INJECTED_OVERT 80 / INJECTED_COVERT 60), matched-by-construction, no arm-label leakage, fail-safe overt verification (OVERT ships `injection_succeeded=None` → excluded until human-verified).
- **Reader re-grade: PARTIAL (up from stub).** `contract.py` (wire format) + `http_reader.py` (`WorkerProfileReader`, `diagnostic=False`, mints a 120s Bearer JWT) are real. BUT `worker_app.py`'s `ReferenceBackend` extracts NO real hidden states (seeded RNG) and `run_eval.py` still raises "Real readers not wired." Every "formal" packet today is still fabricated until a real η backend lands.
- **COLLISION FLAG — two workers.** `worker_app.py` is a SECOND FastAPI worker overlapping the repo `live-trace-worker` (same `X-Atlas-Worker-Token` header; different env-var names + auth middleware + model size 1B vs 160M). RECOMMENDATION: do NOT run `worker_app.py` standalone — fold its `/v1/two_bridge` + `/v1/profile/*` routes INTO the repo `live-trace-worker`, adopt `contract.py` as the shared schema, unify auth. NOTE: `worker_app.py`'s Bearer-JWT auth (HS256, exp≤300s, jti, scope=`worker:two_bridge`) is a ready REFERENCE for engineering **gap #2 (per-job worker token)** — reuse it.
- **Remaining hardening (CONFIRMED absent in both zips):** (1) real η worker backend [needs GPU + the repo's milestone-2 Pythia runner, itself still a `NotImplementedError` stub]; (2) per-trace GREY/INDETERMINATE band; (3) ACCEPT/FLAG_FOR_HUMAN_REVIEW/SUPPRESS verdict adapter; (4) EP-v1 packet remap + claim-levels; (5) WORM/`/evidence` wiring. **Items 2+3 Claude is adding now on the STANDALONE Downloads package** (zero repo touch, no pod). Items 1/4/5 touch the launch pipeline + need the pod → held for Codex coordination.
- **RunPod cost for the keystone (Pythia-160M):** ~$0.20–$1 per validation run on the cheapest GPU tier ($0.12–0.17/hr, per-second billing). Only trap is leaving the pod idle. Big-model audits are a separate class.

Open questions added for Codex:
5. Merge `worker_app.py`'s two_bridge routes into the repo `live-trace-worker` (recommended)? 
6. Is the milestone-2 real-Pythia η-runner on Codex's plate or Claude's?

AUTHORIZED: — (assessment + handoff; no launch-pipeline code or pod action until Codex audits + user "go".)

---

## 2026-06-09 (final) — claude: injection-detection spike OUTCOME — three findings LOCKED (user-ratified)

The bounded two-bridge spike ran to completion on the user's RunPod A4500 (3 runs, ~$1-2 total).
Full scientific record: `docs/working/injection_two_bridge_spike_log.md` (commits `e821096` framing-first,
`fedfa3a` results). Raw artifacts in `C:\Users\wakil\Downloads\`: `spike_results.json` (Run 1),
`spike_v2_results.json` (Run 2), `spike_v3_qwen_results.json` (Run 3, per-prompt outputs + cos_dist),
`disambiguate.py` (offline behavioral split). Pod stopped after Run 3 (user action).

**Three findings — LOCKED by user directive 2026-06-09. These are the guardrails that stop anyone
(future Claude, Codex, or an eager salesperson) from quietly rounding this work up to "we detect
prompt injection." Any launch copy, spec sheet, EP chip, or customer-facing claim must respect them:**

1. **Injectable-substrate requirement.** The method only has something to detect on a model big
   enough (and instruction-tuned enough) to actually be injectable. Pythia-160M showed 0% injection
   compliance → both 160M runs were GREY **by construction** (substrate failure, not method failure).
   Qwen2.5-1.5B-Instruct showed ~45% compliance → separation appeared (p=9e-5, rank-biserial 0.695).
   **Implication for gap #1:** the Pythia-160M worker is a valid substrate for η-profile plumbing,
   WORM smoke, and the live-trace pipeline — but it is NOT a valid substrate for ANY
   injection-detection validation or demo. Those need an instruct model ≥~1.5B.

2. **What exists today is a behavioral-divergence detector, NOT a hijack detector.** The crude
   raw-hidden trajectory readout fires on off-task behavior of EITHER sign: hijack-complied
   (rank-biserial 0.80 vs clean) AND safe-refusal (0.88 vs clean) both separate; injected-but-ignored
   sits at the clean baseline (0.40 n.s.). The signal is real behavior, not a text-structure confound
   (the matched CLEAN_INSTRUCTION control + the ignored-group flatness kill that objection) — but it
   cannot distinguish "model was hijacked" from "model safely refused." A fire alarm that rings
   equally for a fire and for someone putting the fire out is not sellable as a fire alarm.

3. **The typed-probe hijack-vs-refusal test is the GATE.** Before anyone makes a production
   injection-detection claim: build the CAS-typed Qwen probe (the registered two-bridge method —
   typed semantic classes carry content; a refusal η-profile should differ from a compliance
   η-profile) and run a hijack/refuse/ignore/clean design at adequate n. The gate PASSES only if the
   typed method separates hijack from refusal. Until then the permitted claim ceiling is:
   "exploratory evidence of internal behavioral-divergence signal on an injectable instruct model."
   No 40 GB / 20B spend before the typed method passes at small scale. This experiment is scheduled
   for a fresh deliberate session (user directive: not run tired).

**Status note for Codex:** all three runs were EXPLORATORY (logged as such BEFORE execution, framing
commit `e821096`). Nothing here validates the pre-registered H1/H2/H3; nothing here is a customer
verdict. The registered method (CAS-typed probe, two-bridge internal-vs-externalized) remains
UNTESTED — that is open question #6's context: whoever owns the milestone-2 η-runner inherits finding
#1 (substrate must be injectable) and finding #3 (the gate) as design constraints.

AUTHORIZED: — (record only; no launch-pipeline code or pod action until Codex audits + user "go".)

---
