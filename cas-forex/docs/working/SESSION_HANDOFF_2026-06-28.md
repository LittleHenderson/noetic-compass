# CAS Forex — Session Handoff (2026-06-28)

Branch: `codex/cascompass-legal-live-source` · Latest commit: `058ce3ca` (pushed, in sync).
Read this FIRST, then `CHANGELOG.md` head. Prior handoff: `docs/working/SESSION_HANDOFF_2026-06-27.md` (still useful background).

Owner = "Little Henderson / Wakil". He is NOT a developer — **every capability must be an in-app control, never an env var or CLI step he runs.** He drives with full control; expose settings, don't hide them. Plain language, no jargon. Be honest ONCE, never moralize, never fake optimism, never baby him. Mobile-first.

---

## 0. OPERATING THE APP (do this first)

Two dev servers in `cas-forex/.claude/launch.json`, managed by the `preview_*` MCP tools. Run `preview_list` for current serverIds (they change every restart).

- **cas-forex-api** — `C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765`.
  - MUST use the absolute `C:\Python314\python.exe` (3.14, has fastapi+uvicorn+anthropic+MetaTrader5). The preview tool's bare `python` is a 3.12 without uvicorn.
  - After editing ANY Python route/module, **restart cas-forex-api** (uvicorn has no --reload).
- **cas-forex-ui** — `npm --prefix ui run dev -- --host 0.0.0.0` (Vite, port 5174). Hot-reloads via HMR.
- Tests: `C:\Python314\python.exe -m pytest tests/ -q -p no:cacheprovider` (~50-65s). **Suite is fully green (1159+ passing, 0 failing).**
- UI typecheck: `cd ui && npx tsc --noEmit` (must be clean before commit).

### Opening the app on the OWNER's screen
The `preview_*` browser is a SEPARATE headless browser — it is NOT the owner's screen. To open the real app for him: `PowerShell: Start-Process "http://localhost:5174/?page=windows"`. If his tab looks blank/stale after your edits, that's a stuck Vite HMR overlay — tell him to hard-refresh (Ctrl+Shift+R) or open a fresh tab. The saved code is fine (tsc + tests pass each commit).

### Verifying UI changes
`preview_eval`/`preview_inspect`/`preview_resize` on the UI serverId. GOTCHA: React state is async — check state changes in a SEPARATE eval. `vite-error-overlay` present = compile error. **`preview_screenshot` times out reliably this session (renderer-capture glitch) — use DOM inspection via `preview_eval` instead, or `mcp__visualize__show_widget` to render a faithful picture in chat.**

### Phone access
PC LAN IP `10.0.0.6`. Phone → `http://10.0.0.6:5174`, then Settings → "Phone / APK Connection" set API to `http://10.0.0.6:8765/api/forex`. Direct-link any page: `?page=windows|settings|dashboard|...`.

---

## 1. WHAT THIS SESSION SHIPPED (all committed + pushed, this branch)

In commit order (newest first), `06816cf5..058ce3ca`:

- **Dashboard blank-out + missing floating assistant** (`62c4c1e7`) — SAME root cause: DashboardPage threw (`.join` on heterogeneous strategy leads, 8 of 12 `ff-lead-*` lack `symbols_promoted_for_next_tests`), and with NO error boundary the uncaught throw unmounted the WHOLE app (incl. the floating assistant). Guarded the lead reads; added `ui/src/components/ErrorBoundary.tsx` around the page area in `App.tsx`. (+ `06cde7fa` guards the 2nd `.join` on `movement.symbols`.)
- **In-app authorization toggles for ALL 5 capabilities + sweep-ledger licensing** (`c2b81ed4`) — extended `cas_forex/live_enable_control.py` beyond live_trading to broker_accept / auto_deposit / bank_card_movement / payout_automation (the sweep ledger) + shared payment-provider section (provider, API key = password stored-but-never-returned, payout destination, allowlist). `api/routes/live_enable.py` GET/POST `/authorization`. Settings panel "Path to Authorize Everything — Owner Switches" (functional toggles, was read-only). **Assistant system prompt (`api/routes/assistant.py`) rewritten** — it was STALE (told the owner to edit `.env`); now points to the in-app toggle panels and never instructs `.env`.
- **Comprehensive UI audit + fixes** (`666d0fa0`, `91c0e50f`, `c5bfbd1b`) — 19-page multi-agent audit. Fixed: Daily Report `[object Object]` + blank section titles (`section_name` not `name`), Strategy-Compare diff fully broken (wrong query params + `field_diffs`/`a_value`/`b_value` field names), Ledger crash-guard, PCBA booleans, Optimizer mojibake, Condition Lab guards, M1+M5 timeframes (`dfcd6f84`).
- **Trading Windows = real terminal** (`0bc3553b`, `8c73e480`) — account bar + MT4-style "Open Positions" table (all positions) + per-pane positions, from `/movement/snapshot`. Market OPEN/CLOSED + Asian/London/NY session strip with live "reopens in… (Sun 22:00 UTC)" countdown. Strategy panes default to symbols WITH open positions (US30/NAS100).
- **Paper dispatch loop on a timer** (`62f2109a`, `1a252b0d`, `6760b67b`) — THE #1 functional gap closed. `cas_forex/dispatch_loop.py` (background thread runs the gated `run_agent_dispatch_cycle` on a timer) + `api/routes/dispatch_loop.py` + "Auto-Trade Loop" panel on Trading Windows. Interval is owner-set 1s–24h, changeable live ("Apply"). Targeting: "Trade only" symbol chips + "During sessions" chips (idles off-session). Paper-safe; `?confirm=true` only when live is authorized.
- **MT5 live connection** (`17bfecdd`, `b915082a`, `34d50131`, `058ce3ca`) — see §2.
- 6 long-standing `strategy_ledger`/`llm_optimizer` test failures FIXED (`0bc3553b`) — validator now accepts the Fury `PROMOTED_PAPER_LANE` record type. Suite fully green.

---

## 2. MT5 CONNECTIVITY — READ THIS BEFORE TOUCHING IT (saved you hours)

The owner connected MetaTrader 5 (HugosWay was the broker, but he ended up on a **MetaQuotes-Demo** account `108941161` created via the generic MT5 terminal). `.env` holds `CAS_FOREX_MT5_LOGIN=108941161`, `CAS_FOREX_MT5_SERVER=MetaQuotes-Demo`, `CAS_FOREX_MT5_PASSWORD=…` (8 chars). `MetaTrader5` pip pkg 5.0.5735 is installed in the user site; terminal is build 5836.

**Three real bugs were fixed and the connection was PROVEN working once** (pulled the real account: $100k demo, live EURUSD ticks, `is_demo=True`):
1. `17bfecdd` — `_add_local_mt5_deps()` prepended a broken vendored `.mt5deps/MetaTrader5` (missing `_core` for py3.14) ahead of the real install → "mt5 not imported". Now prefers the working install.
2. `b915082a` — bridge forced a re-login (`initialize(login,password,server)`) → "IPC send failed (-10001)" against an already-logged-in terminal. Now ATTACHES first (bare `initialize()`), re-logins only on account mismatch.
3. Windows Defender exclusions (owner added `C:\Python314\python.exe` + the MT5 `terminal64.exe`) turned "IPC timeout (-10005)" into a working pipe.

**CONCLUSION (do not re-litigate): MetaTrader's Python IPC is UNSTABLE on this machine.** It connected cleanly ONCE, then hung (60–90s) or fast-failed on essentially every subsequent attempt, *even with the terminal fully connected*. Root cause is environment-level (bleeding-edge Python 3.14 + terminal build 5836 + the background-process context the API runs in), NOT app code. Aggressive probing makes it worse (killed processes leak IPC connections that jam the terminal until a terminal restart). **Don't chase the Python IPC further** — diminishing returns; you can't fix an env IPC instability remotely.

What's built + safe: `cas_forex/mt5_live.py` (ONE persistent, cached, read-only connection — never per-request) + `api/routes/mt5_live.py` GET `/mt5/account`, POST `/mt5/refresh` (SYNC handlers → FastAPI threadpools them so a slow read never freezes the event loop) + "MetaTrader 5 — Connected Account" panel atop Trading Windows. `058ce3ca` made it degrade gracefully: 8s connect timeout (`MT5_INIT_TIMEOUT_MS`) + 20s back-off on failure, so it shows the account WHEN the pipe opens and a clean "not connected" otherwise — never hangs.

**The robust path for REAL broker order routing is the MT4 EA file-mailbox, NOT the Python IPC** — it's file-based. EA already in repo: `mt4/Experts/CASForexBridgeEA.mq4`; Python side `cas_forex/broker/mt4_mailbox_bridge.py`; config `MT4_MAILBOX_DIR` + `MT4_ENABLED` (currently env-only — building an in-app MT4 panel was offered to the owner).

---

## 3. PENDING / NEXT (owner's queue)

The owner's last decision point (he was asked which way to go): **recommendation = (a) start the paper Auto-Trade Loop now to build proof, and (b) wire the MT4 EA file-mailbox as the reliable real-order route.** He has NOT yet answered. When he does:

1. **Start the paper Auto-Trade Loop** on his chosen symbols/session (Trading Windows → Auto-Trade Loop → set symbols/sessions/interval → Start). Paper-safe; builds the 30-day proof. This is the stable, no-MT5 path.
2. **Task #10 (in tracker): gate / NOT LICENSED status accuracy** — the Authority Boundary + "Path to Authorize" readout has STATIC hardcoded values (e.g. "Broker Health: DISCONNECTED", "Live Broker: NOT LICENSED") not wired to reality. Wire it to the STABLE sources (creds present, broker selected, paper-proof progress) and mark what's genuinely satisfied vs missing. **DO NOT tie live status to the flaky MT5 connection** (it'd flicker). **NEVER let a connected DEMO auto-authorize live** — live stays NOT LICENSED until the owner flips the owner-enable toggles. Make status honest, not looser.
3. **Route the paper loop through the connected broker** (the owner's "Part B") — was gated on a stable MT5 connection, which we don't have. Pivot to the MT4 EA mailbox route, OR keep the loop on the simulator (stable). If you do wire MT5 execution, the loop's bridge MUST reuse a single persistent connection (not `select_bridge()` per cycle, which re-jams the IPC).
4. **MT4 Bridge in-app panel** (offered, not built) — a Settings field for the `MQL4\Files\CASForexMailbox` path + Enable toggle + EA-heartbeat status, so MT4 setup is in-app too (no env).
5. **Comprehensive UI audit follow-ups** — the audit found 11 clean pages; the fixes are done. No open audit items.

---

## 4. KEY FILES / PATTERNS

- Runtime override pattern (copy for new in-app controls): `cas_forex/live_enable_control.py` + `cas_forex/risk_control.py` + their `api/routes/*` + the Settings panels (`GoLivePanel`, `AuthorizePanel`, `RiskControlPanel` in `ui/src/pages/SettingsPage.tsx`). Shape: module `_OVERRIDES` dict + `set_/resolve_/clear_`; route GET `/state` + POST `/update` + `/reset`; Settings panel calling `ui/src/data/api.ts` helpers.
- Real-money gate (single source of truth, fail-closed): `cas_forex/runtime_gates.py` (`evaluate_live_trading`, `build_runtime_gates_report`), re-enforced at `cas_forex/broker/mt5_bridge.py` (`_live_gate_block`, fail-closed `is_demo_account`). `runtime_gates._resolve_config` consults `live_enable_control.apply_live_enable_overrides` (no-op when no overrides).
- Dispatch: `cas_forex/order_dispatch.py`, `cas_forex/agent_dispatch.py` (`run_agent_dispatch_cycle`, `collect_route_intents`), `cas_forex/dispatch_loop.py` (the timer). Bridge factory: `cas_forex/broker/mt5_bridge.py::get_bridge()` + `broker_control.select_bridge()`.
- Trading Windows: `ui/src/pages/WindowsPage.tsx` (account bar, market strip, Auto-Trade Loop, MT5 panel, 4 panes), `ui/src/components/TradingWindow.tsx`, chart `ui/src/components/charts/CandlestickChart.tsx`. Backend `api/routes/chart.py` (TTL-cached candles+quote), `api/routes/mt5_live.py`.
- UI shell/nav: `ui/src/App.tsx` (page union + render + ErrorBoundary), `ui/src/components/Shell.tsx` (NAV_ITEMS; "Live Charts" = `?page=windows`).
- Assistant: `api/routes/assistant.py` (SYSTEM_PROMPT + `_live_state_block`).

---

## 5. WORKING-TREE LANDMINES (don't regress)

- **Pre-existing uncommitted WIP**: `ui/src/pages/OptimizerPage.tsx` (~1716 lines), `LedgerPage.tsx`, `HistoryPage.tsx` carried large uncommitted changes BEFORE this session (they were `M` in the initial git status). They got committed in `c5bfbd1b` WITH that WIP (owner approved). If you see big diffs there you didn't make, that's the pre-existing work — don't be surprised, don't blame your changes.
- `strategy_leads.json` is a working-tree-modified DATA file (the Fury `PROMOTED_PAPER_LANE` entries). The VALIDATOR was fixed to accept them (`cas_forex/strategy_ledger.py`); do NOT commit `strategy_leads.json` itself unless asked.
- Git on Windows: LF→CRLF warnings on every `git add` are benign. Commit/push after each unit; chain `git push` to the commit. Already on the feature branch.
- Co-author trailer on commits: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## 6. IMMEDIATE NEXT STEPS for the next agent
1. Read this file + `CHANGELOG.md` head.
2. `preview_list` → confirm both servers up; if not, `preview_start` each.
3. Wait for the owner's answer on the paper-loop-vs-MT4-mailbox decision (§3). Default recommendation: start the paper loop on his symbols/session, then wire the MT4 EA mailbox.
4. Do NOT re-chase the MT5 Python IPC (§2) — it's an unfixable-from-here env instability.
5. Task #10 (gate status accuracy) is a good independent next build — wire to STABLE sources, keep live fail-closed.
