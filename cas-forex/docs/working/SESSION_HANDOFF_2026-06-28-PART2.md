# CAS Forex — Session Handoff (2026-06-28, Part 2 — "live & profitable" finish line)

Branch: `codex/cascompass-legal-live-source` · Latest commit: `f84cad78` (pushed, in sync).
Read this, then `docs/working/SESSION_HANDOFF_2026-06-28.md` (Part 1, still valid background) and `CHANGELOG.md` head.

Owner = "Little Henderson / Wakil". Not a developer — **every capability is an in-app control, never an env/CLI step.** Plain language, no jargon, honest ONCE, never moralize, never baby him. Mobile-first.

---

## 0. THE GOAL THIS SESSION — and the honest reframe (state once, don't repeat)

Goal as the owner put it: make CAS Forex **LIVE and PROFITABLE according to the standards originally set for it.** The original standard is the 30-trading-day paper proof of the index-TSMOM-126 strategy (US30/NAS100 D1) in `cas_forex/paper_proof.py`.

The audit caught that the proof **did not measure profit** — it only checked the demo broker was online + chain-verified for 30 days; a 30-day proof of zero-trade or losing days would have PASSED. It was also stuck at 3/30 (advanced only by a CLI step the owner can't run) and index-TSMOM-126 has only a thin backtest (5 windows, 60% positive, graded "not promoted / sparse") — i.e. **no proven edge yet**.

Owner decisions (asked + answered this session):
1. **Profit bar** → "Made money + safe drawdown": pass needs net-positive P&L + max drawdown ≤ 8% + real trades on most days. Adjustable in-app.
2. **Advance** → automatic daily auto-runner with on/off.
3. **Order route** → MT4 EA mailbox (build panel + fix the round-trip).

**What code CAN'T do (irreducible — say it plainly):** 27 more real weekday trading days must elapse with the demo terminal connected (~5.5 weeks). Real live money additionally needs the owner's in-app toggles + a funded real (non-demo) account + a running terminal. No code shortcuts this.

---

## 1. WHAT THIS SESSION SHIPPED (all committed + pushed, `12e07529..f84cad78`)

1. **The proof now measures profit** (`3167fb60`). `summarize_paper_proof.passed` now also requires net-positive realized P&L + max drawdown ≤ limit + real trades on most days. MT5 demo receipt sums realized P&L from deal history (profit+commission+swap+fee) → `realized_pnl` flows through `validate_paper_broker_receipt` + `append_paper_proof_day` into each daily summary. New `cas_forex/proof_control.py` holds owner-adjustable thresholds (defaults: net-positive, DD 8% from the plan, trade-days fraction 0.5, seed $2000). `PaperTradingSessionReport` gained `net_pnl_usd / max_drawdown_pct / days_with_trades / min_trade_days_required / profit_passed / broker_verified_days`. Anti-gaming: only broker-verified days count; a plan-only ledger can never pass (regression-tested).
2. **In-app proof advance** (`eed98c9e`). `cas_forex/proof_runner.py` = owner-controlled daily auto-runner (mirrors `dispatch_loop`) + `run_proof_day_now()` manual path; paper-only, idempotent, retries if the demo terminal is down. Routes `POST /api/forex/proof-control/{run-now,auto/start,auto/stop,thresholds,thresholds/reset}` + `GET /state`. `paper_proof.index_tsmom_126_proof_dir()` is the single proof-dir source of truth. `paper_daily_schedule` adds `recommended_action` (in-app text) beside the CLI `recommended_command`.
3. **Proof UI** (`900b5da0`, `a61ff4cc`). `ui/src/components/ProofControlPanel.tsx` on the Proof page: profit metrics (verified days, net P&L, drawdown, trade-days, profit check), the honest "what's left", **Record today's proof day** button, **daily auto-runner** on/off, and the tunable thresholds. `api.ts` proof-control helpers. Next-action switched from the CLI string to `recommended_action`. NOTE: `a61ff4cc` also carries pre-existing (06-23/24) reconciliation/MT5-probe UI WIP in `evidence.ts`/`fixtures.ts`/`ProofPage.tsx` (type-coupled; committed together to stay tsc-green).
4. **MT4 EA mailbox in-app route** (`78319cea`). New `cas_forex/mt4_control.py` (enable + mailbox_dir overrides + EA heartbeat reader). **Fixed the round-trip**: `MT4EABridge.execute_order` now ALSO writes the EA-readable `commands/<id>.json` via `MT4MailboxBridge` (kept `orders.jsonl` as audit log) — before, the EA never saw dispatched orders. `is_connected` uses heartbeat freshness. Route `GET/POST /api/forex/mt4-bridge/{state,update,reset,heartbeat}`. Settings "MT4 Bridge — Stable File Route" panel (on/off, mailbox folder, EA link LIVE/STALE/NO_HEARTBEAT, one-tap "Use MT4 for dispatch").
5. **Honest authority status** (`f84cad78`). ModeBanner (every page) + Settings Owner-Control/Broker-Config/Legal-Gates now read live owner-flag sources (authorityBoundary, live-enable, broker-control, proof readiness, MT4 link) instead of hardcoded literals. Dropped "PAPER_MT5 / live_mode=false / Broker Health: DISCONNECTED / stale 1/30". **Invariant preserved: a connected DEMO never licenses live** (status is owner-flag driven, never the flaky MT5 IPC).

Suite: **1177 passing, 0 failing.** UI tsc clean.

---

## 2. OPERATING THE APP (servers are now owned by THIS session)

This session **took over both dev servers** (the prior session's were orphaned/stale). They run under `preview_*` now; serverIds change on restart — run `preview_list`.
- **cas-forex-api** — `C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765`. No --reload: **restart after any Python edit** (`preview_stop <id>` then `preview_start cas-forex-api`; if a stale process holds 8765, free it: PowerShell `Get-NetTCPConnection -LocalPort 8765 | %{ Stop-Process -Id $_.OwningProcess -Force }`).
- **cas-forex-ui** — Vite, port 5174, HMR (picks up .tsx edits live).
- Tests: `C:\Python314\python.exe -m pytest tests/ -q -p no:cacheprovider` (~70s). UI: `cd ui && npx tsc --noEmit`.
- Open on owner's screen: `Start-Process "http://localhost:5174/?page=proof"`. `preview_screenshot` is flaky this session — verify via `preview_eval` DOM reads (labels are CSS-uppercased, so match case-insensitively).

---

## 3. PENDING / NEXT

1. **Owner action to actually advance the proof**: on a weekday with the MT5 demo terminal connected, press **Record today's proof day** (Proof page) or turn the **daily auto-runner** ON. 27 verified days remain. The demo terminal must stay connected on trading days.
2. **The edge is unproven** — index-TSMOM-126 is a sparse research lead. Never present it as "profitable/proven" until a profit-measuring proof passes AND the walk-forward is broadened (more windows, broker-grade spread/slippage, OOS). Honest copy already avoids this; keep it that way.
3. **Durability gap (from the critic, not yet done)**: owner live-enable + payment-provider overrides are process-global and reset on restart — "authorized" silently reverts on a restart, and the in-app `payment_api_key` is lost. Consider persisting owner authorization to a durable store loaded on startup (keep the key secret), and label transient vs persisted in the UI.
4. **MT4 live path** is intentionally paper today; LIVE_MT4 needs the EA's own `LiveTradingAllowed` input + per-command authorization (separate, by design).

---

## 4. WORKING-TREE LANDMINES (don't regress)

- **Repo cleanup done (`8747a4f5`)**: the cas-forex working tree is now FULLY COMMITTED and clean. ~104 previously-untracked but tested modules/tests/scripts + the `mt4/` EAs + the reconciliation/instruments WIP + `strategy_leads.json` + requirements/gitignore/launch.json were committed in one coherence commit (the committed history was latently broken — `api/server.py` imported untracked routers; the MT4 bridge imported untracked `mt4_mailbox_bridge`). App imports clean (144 routes); suite green (1177).
- **The rest of the monorepo is intentionally untouched**: the parent `tksCAS` repo still has 600+ uncommitted/deleted files in OTHER projects (`cas-synthetic/`, `noetic-compass-scaffold/`, `.claude/worktrees/`). That is out of CAS-Forex scope — do NOT `git add -A` from the repo root.
- Ignored + intentionally uncommitted: `.env` (secrets), `evidence_runs/` (proof ledgers), `.claude/settings.local.json` (local permission state), `__pycache__`.
- Real-money gate is fail-closed at the bridge (`mt5_bridge._live_gate_block`, strict `is_demo_account`). Profit thresholds and the auto-runner never touch the live gate. Don't regress.
- Co-author trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Commit + push after each unit.
- Do NOT re-chase the MT5 Python IPC (Part-1 §2): unfixable-from-here env instability. The MT4 file mailbox is the stable route.
