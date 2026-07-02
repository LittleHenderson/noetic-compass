# CAS Forex — Session Handoff (2026-07-01: landing the in-flight work + the finish plan)

Branch: `codex/cascompass-legal-live-source`. Read this, then `CHANGELOG.md` head, then
`SESSION_HANDOFF_2026-06-28-PART3-EDGE.md` (the edge verdict — still governing).
The per-unit build log for everything landed here is the parent repo's
`docs/working/cas_harness_production_todo.md` (266 dated entries, newest first). Its
Mandatory Agent Rule applies: read it before advising, update it before finishing.

Owner = "Little Henderson / Wakil". NOT a developer — every capability is an in-app
control, never an env/CLI step he runs. Plain language. Honest once, never moralize,
never baby him. He drives. He has granted blanket tool permission for this project
(see `.claude/settings.json` allowlist).

---

## 0. THE OWNER'S GOAL (stated 2026-07-01, verbatim intent)

Finish CAS Forex as the psychology-removing execution system: the human sets mission,
capital, broker, and authority; the AI watches/analyzes/strategizes/tests/executes with
risk limits, principal lock, compounding logic, and owner-controlled live switches, then
records what happened so it can adapt. **Funding custody stays broker-side**: CAS is a
broker handoff + verification loop, never a place where raw bank/card details are typed.
Winnings are deposited to the owner's chosen bank account via the broker withdrawal path
(verified-profit sweep), not by CAS holding money. And the app must be **usable and
installable on the owner's phone**.

## 1. WHAT THIS SESSION DID

1. **Inventoried + landed the 2026-06-29→07-01 in-flight work** (127 modified + ~130 new
   files): live-money spine (auto-halt, broker-reality ACCEPT, broker-truth monitor,
   live pilot, dry-run review, recovery, order-attempt audit, payout recovery,
   verified-profit sweep), runtime-gate redesign (owner authority boundary + advisory
   tier), WASTE adaptation loop, funding handoff UI, dashboard first-paint overhaul.
   See the CHANGELOG 2026-07-01 entry for the full map.
2. **Verified green end-to-end**: pytest **1707 passed / 0 failed** (~15–17 min), UI
   `npx tsc --noEmit` clean, `npm run build` clean (PWA precache 8 entries ~182 KiB).
3. **Fixed 4 stale tests** (no app-code changes): 2× broker-truth advisory-tier gate
   contract, 1× MT4 mailbox heartbeat fail-loud contract, 1× dashboard-fast test now
   derives expectations from the live evidence files instead of freezing day counts and
   `$28.48` (it broke at `$28.76` and would break every proof day otherwise).
4. **Verified the funding loop live**: Settings shows `BROKER FUNDING HANDOFF` /
   `Open Broker Portal` / `NO RAW BANK/CARD STORAGE` / `Sync Broker Snapshot`;
   `/api/forex/reconciliation/account?sync_to_broker=true` returns 7/7 checks OK
   (`BROKER_API_VERIFIED`, chain verified) against the demo terminal. Confirmed NO
   raw card/bank fields exist anywhere in the app (grep-verified; `paper_proof.py`
   stores hashed account ids and `auto_deposit_or_card_transfer_allowed: False`).
5. **Committed + pushed** the whole body in coherent units (backend / UI / docs).
6. Widened `.claude/settings.json` permissions per the owner's explicit blanket grant.

## 2. CURRENT TRUE STATE (claim-status separated)

- **Real + working**: the app runs (API :8765, UI :5174), WASTE loop heartbeat is LIVE
  (header shows the real stage), proof auto-runner is ON and has advanced to
  **5/30 broker-verified days** (0 trades yet — the bot isn't placing paper trades until
  the loop's TEST gate passes something), reconciliation + evidence chains verify.
- **Not passed / open**: the 30-day profit proof (`NOT PASSED`, needs 30 verified days +
  net-positive + DD ≤ 8% + trades on most days). The **edge is unproven** — every tested
  lever is NO_SKILL/no-edge vs the null (PART3-EDGE). The WASTE adaptive loop is the
  owner-ratified path; its TEST gate is fail-closed, so no-edge ⇒ no-execute, honestly.
- **CURRENTLY NOT LICENSED (owner-gated, by design)**: live trading, auto-deposit,
  bank/card movement, payout automation. Each gate reports exactly what's missing.
- **Unavailable**: WORM anchoring (local hash chain only — labeled in-app).

## 3. WHAT'S NEXT (the finish line)

1. **Phone access (in progress this session)**: PWA is buildable and installable
   (manifest + generated SW + icons; `docs/MOBILE_APP.md` documents Android/iPhone
   install + the API-URL override in Settings). Remaining: serve `ui/dist` reachable from
   the phone (LAN `http://<PC-IP>:5174` via `npm run mobile:preview`, or tunnel for
   HTTPS install banners), verify on-phone install + live API reads, and consider
   removing the legacy `ui/public/sw.js` (the vite-plugin-pwa build overwrites it in
   `dist/` — it's dead weight, not a conflict).
2. **Funding-loop polish**: make the "fund at broker → CAS verifies" separation
   unmistakable (the production-todo names this the next product emphasis) — e.g. a
   single guided "Fund & Verify" flow on Quick Start.
3. **Proof track**: keep the demo terminal connected on weekdays; the auto-runner
   records days. Real trades require the WASTE loop's TEST gate to pass a candidate
   (edge threshold slider, default 65%) — nothing bypasses the null gate.
4. **Live path** (owner actions when HE decides): fund real account at broker portal →
   Sync Broker Snapshot → owner ACCEPT broker-reality terms → passing + ACCEPTED
   live-order dry run → small live pilot ACCEPT → flip the live switches. All in-app.

## 4. OPERATING NOTES

- Servers via `preview_*` MCP (`.claude/launch.json`): **cas-forex-api** =
  `C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765`
  (restart after Python edits — no --reload); **cas-forex-ui** = Vite :5174 (HMR).
- Tests: `C:/Python314/python.exe -m pytest tests/ -q -p no:cacheprovider`
  (**~15–17 min now** — plan around it; it was ~70 s at 1217 tests). UI:
  `cd ui && npx tsc --noEmit`; build: `npm run build`.
- The dashboard-fast test reads LIVE evidence (`evidence_runs/`) — expectations are
  derived, not frozen; don't reintroduce hardcoded day counts or risk totals.
- Landmines unchanged from PART2/PART3 handoffs: never `git add -A` from repo root;
  `evidence_runs/` + external data stay git-ignored; MT5 Python IPC is unstable — the
  MT4 mailbox (now heartbeat-gated) is the stable route; null discipline is sacred.
