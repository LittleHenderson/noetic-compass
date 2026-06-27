# CAS Forex — Session Handoff (2026-06-27)

Branch: `codex/cascompass-legal-live-source` · Latest commit: `c4be2e49` (pushed).
Owner = "Little Henderson / Wakil". He is NOT a developer — **every capability must be an in-app control, never an env var or CLI step he has to run.** He drives with full control; expose settings, don't hide them. Be honest once, never moralize, never fake optimism. Plain language.

---

## 0. OPERATING THE APP (do this first)

Two dev servers are defined in `cas-forex/.claude/launch.json` and managed by the `preview_*` MCP tools. Run `preview_list` to get current serverIds (they change on restart).

- **cas-forex-api** — `C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765`.
  - MUST use the **absolute** `C:\Python314\python.exe` (the preview tool's bare `python` resolves to a 3.12 with no uvicorn). 3.14 has fastapi+uvicorn+anthropic.
  - Host is `0.0.0.0` so the owner's phone can reach it over WiFi.
- **cas-forex-ui** — `npm --prefix ui run dev -- --host 0.0.0.0` (Vite, port 5174). `--host 0.0.0.0` so the phone can load it.
- After editing a Python route or any backend, **restart cas-forex-api** (uvicorn has no --reload). UI hot-reloads via Vite HMR.
- **Phone access (owner is mobile-first):** PC LAN IP is **`10.0.0.6`**. Phone browser → `http://10.0.0.6:5174`, then in-app **Settings → "Phone / APK Connection"** set API address to `http://10.0.0.6:8765/api/forex`. Direct-link any page bypassing the menu: `http://10.0.0.6:5174/?page=settings` (also `?page=windows`, `?page=optimizer`, etc. — the app reads `?page=` from the URL).
- `ANTHROPIC_API_KEY` IS set in the API server's environment (the assistant returns real Claude replies; `GET /api/forex/assistant/status` → `configured:true`).

### Verifying UI changes
Use `preview_eval`/`preview_inspect`/`preview_resize` on the **UI** serverId. GOTCHA: React state updates are async — after a `.click()` that sets state, the DOM updates on the *next* tick, so check in a **separate** eval, or use `(async()=>{ ...; await new Promise(r=>setTimeout(r,600)); return ... })()` to catch transient states (e.g. the assistant "thinking" indicator). `viteOverlay` present = compile error; absent = compiled. Console "Failed to reload" lines are usually **stale** mid-edit errors — check `preview_logs` timestamps before trusting them.

### Tests
`python -m pytest tests/ -q -p no:cacheprovider` (~75s, ~1133 passing). A stray `tmppcba-pytest` dir at repo root breaks bare `pytest` collection → always scope to `tests/`. There is ONE pre-existing unrelated failure historically in daily-report date tests (was fixed earlier; if it reappears it's the stale-date class). Git LF→CRLF warnings on Windows are benign.

---

## 1. THE TWO NEXT TASKS (priority order from the owner)

### TASK A — DONE (2026-06-27, next session). "Go Live — Owner Switches" panel shipped.
Built per the spec below: `cas_forex/live_enable_control.py` (override module) + `api/routes/live_enable.py` + Settings "Go Live — Owner Switches" panel (6 toggles in 3 groups + live runtime-gate readout + honest caveat). `runtime_gates._resolve_config` now consults `apply_live_enable_overrides` (no-op when unset, fail-closed). Verified end-to-end in the UI (all-on → gate AUTHORIZED, Reset reverts). Tests: `tests/test_live_enable_control.py`. **Original spec kept below for reference.**

### TASK A (TOP PRIORITY — COMPLETE) — In-app toggle buttons to ENABLE LIVE TRADING
The owner is furious that going live requires editing `.env`. He wants **toggle switches in the app** for everything `runtime_gates.evaluate_live_trading` checks that is currently env-only:

1. **Account / source-of-funds acknowledgments** → config flags `personal_account_ack`, `no_pooled_capital_ack` (config.py). Currently env `CAS_FOREX_PERSONAL_ACCOUNT_ACK`, `CAS_FOREX_NO_POOLED_CAPITAL_ACK`. → in-app **signed-acknowledgment toggles** (with the consequence text shown).
2. **Live mode config** → `live_mode` (ON), `prefer_mt5`/`mt5_path` confirmed. (Broker `hugosway` + MT5 creds are ALREADY set per the live-state block.) → in-app **toggle**.
3. **Owner-enable flags** → `owner_enable_live_trading=true` AND `live_trading_licensed=true`. → in-app **toggles**.

**HOW TO BUILD IT — follow the existing override pattern (this is the established, safe way):**
- I already built TWO runtime-override surfaces you should copy verbatim in shape:
  - `cas_forex/broker_control.py` + `api/routes/broker_control.py` + Settings `RiskControlPanel`-style UI.
  - `cas_forex/risk_control.py` + `api/routes/risk_control.py` + `ui/src/pages/SettingsPage.tsx` `RiskControlPanel`.
  - Pattern: a module-level `_OVERRIDES` dict + `set_*_overrides()` / `resolve_*()` / `clear_*_overrides()`; an API route with `GET /state`, `POST /update`, `POST /reset`; a Settings panel with controls calling the api.ts helpers.
- **Create `cas_forex/live_enable_control.py`**: runtime overrides for `personal_account_ack`, `no_pooled_capital_ack`, `live_mode`, `prefer_mt5`, `owner_enable_live_trading`, `live_trading_licensed`. `resolve_live_enable(config)` = override-over-config.
- **The critical wiring:** `runtime_gates.py` reads these straight off `config` today (e.g. `evaluate_live_trading` lines ~84-119). It must instead read the **resolved** values (override > config). Either (a) have runtime_gates consult `live_enable_control.resolve_live_enable(config)`, or (b) wrap config. Do this carefully — `runtime_gates` is the single real-money authorization point and is covered by many tests; keep it fail-closed and re-run the full suite.
- **API route** `api/routes/live_enable.py` (`GET /state`, `POST /update`, `POST /reset`), register in `api/server.py`. `POST /update` should re-evaluate and return `runtime_gates.build_runtime_gates_report()` so the UI shows what's still missing.
- **UI**: a **"Go Live — Owner Switches"** panel on the Settings page (next to Risk Control), with labelled toggle switches for each flag + the two acks, and a live readout of `runtime_gates` (each capability AUTHORIZED / what's missing). When all green, the assistant's `_live_state_block` and `/settings/runtime-gates` will already reflect it.

**SAFETY / HONESTY (state once in the UI, don't moralize):** flipping these toggles is the owner satisfying the gate — consistent with `runtime_gates`' design ("the owner turns a capability on by satisfying its requirements"). BUT: (1) toggles alone still place NO orders — there is no order-dispatch *loop* wired to a scheduler yet (the engines exist: `order_dispatch.py`/`agent_dispatch.py`, but nothing runs them on a timer in production); (2) the bridge-level gate (`MT5Bridge.execute_order` + `_live_gate_block`, fail-closed `is_demo_account`) still enforces authorization at order time; (3) label each toggle with its real consequence. Do NOT silently make real-money trading one tap away without the readout showing exactly what each switch does.

### TASK B — DONE (2026-06-27, next session). "Trading Windows" cockpit shipped.
Built per the spec below: `api/routes/chart.py` (`GET /chart/window` TTL-cached + `GET /chart/symbols`) + `POST /order-dispatch/manual` (gated paper dispatch) + `ui/src/components/TradingWindow.tsx` + `ui/src/pages/WindowsPage.tsx` (2×2 grid) + nav "Live Charts" (`?page=windows`). Verified end-to-end (4 panes real candles+quotes, selectors reload, Buy=paper fill, Pause works, honest Live label, mobile single-column). Tests: `tests/test_chart_route.py`. **Original spec kept below for reference.**

### TASK B (COMPLETE) — Live "Trading Windows" cockpit
Owner wants a page like MT4 / TradingView: **4 live chart windows** = **Live**, **Demo**, **Strategy A**, **Strategy B** — real-time price movement of what the CAS agents are watching/testing, primarily to **watch/analyze**, with **optional controls** (manual buy/sell, pause) for live OR agent-initiated executions.

**Done so far:** fixed `YFinanceConnector.fetch_historical` (commit `c4be2e49`) — it was passing an invalid Yahoo `period` and returning 0 bars; now returns real OHLC (verified EUR/USD M5 → 40 bars, XAU/USD H1 → 40 bars). So **real candle data is now available.**

**What's left to build:**
1. **Backend** `api/routes/chart.py`: `GET /window?symbol=&timeframe=&bars=` → `{candles:[{time,open,high,low,close}], quote:{bid,ask,mid,spread,is_market_open,session}, source, live_feed}`. Use `cas_forex.market_data.connector.get_connector()` (factory at connector.py:235) → `fetch_historical(symbol,bars,timeframe)` + `fetch_snapshot(symbol)`. **Add a small in-process TTL cache (~20s)** keyed by (symbol,timeframe,bars) — yfinance is slow/rate-limited and uvicorn is single-worker, so don't fetch on every poll. Register in `api/server.py`.
2. **api.ts**: `fetchChartWindow(symbol, timeframe, bars)`.
3. **`ui/src/components/TradingWindow.tsx`**: header (role label + symbol selector + timeframe selector + status chip + last bid/ask) → reuse `ui/src/components/charts/CandlestickChart.tsx` (pure SVG, props `{candles, symbol, height}`) → footer with open-position/P&L (from `/movement/snapshot`) + control bar (Buy/Sell, Pause). Poll `fetchChartWindow` on an interval (~10-15s; the TTL cache covers faster UI polling). Show a live price line/last-price that updates between bar refreshes from the quote.
4. **`ui/src/pages/WindowsPage.tsx`**: 2×2 grid of 4 `TradingWindow`s with role labels Live / Demo / Strategy A / Strategy B. Strategy windows' symbol defaults from the top strategy leads / `forex-fury-replay-candidates`; Live/Demo from the broker/movement.
5. **Nav**: add `"windows"` to the `Page` union + `PAGE_IDS` in `ui/src/App.tsx` AND to `Shell.tsx` `NAV_ITEMS` (label e.g. "Windows" or "Live Charts") AND render `<WindowsPage/>` in App.tsx.
6. **Controls (secondary — watching is primary):** Buy/Sell should route a manual `TradeIntent` through the **gated** dispatch (`order_dispatch`/`agent_dispatch`) so it's paper-safe by default; a thin `POST /order-dispatch/manual {symbol,direction,lots,sl,tp}` endpoint may be cleanest. Pause = UI-local poll toggle.
**HONEST LABELS:** "Live" needs a connected broker feed (not running today) — until then label it clearly (e.g. "LIVE — no broker feed; showing market data" or disabled). yfinance is delayed/limited retail data, not tick-real-time — call it "near-real-time", don't imply a pro feed.

---

## 2. BACKGROUND WORK STATUS
- The **assistant-grounding audit** (workflow `wvj16sn0d`) COMPLETED and its findings were applied (assistant prompt rewrite + nav fix). Output file: `…/tasks/wvj16sn0d.output` (synthesis has the corrected prompt + a "what's real vs env-only" map — useful reference).
- **DONE (next session):** the comprehensive UI audit ran (36-agent workflow, 19 pages + adversarial verify). 13 confirmed issues fixed + 2 runtime key bugs the static pass missed. Daily Report `[object Object]` AND blank-section-title bugs fixed; Strategy Compare diff (was fully broken: 422 + `.map` crash) fixed; Ledger crash-guard added; PCBA/Optimizer/History/Cond-Lab render bugs fixed. 11 pages were clean. See CHANGELOG entry "Comprehensive UI audit + 15 fixes". **Original note below for reference.**
- A **comprehensive page-by-page UI audit was PROMISED to the owner but NOT actually launched** (I described it but never called Workflow). The owner explicitly wants "find everything else broken so we stop hitting these one at a time." **The next agent should launch this**: a Workflow fanning agents across all 18 pages to find dead/unwired controls, looks-interactive-but-read-only elements, endpoints that error, and render bugs. **Known bug already found to seed it:** Daily Report renders `by_status` as `[object Object]` (an object dumped instead of formatted) — see `ui/src/pages/DailyReportPage.tsx`. Owner found the Fury "Promote to paper lane" dead-looking button himself (now fixed via override) — that class of "wired but the backend rejects / no feedback" is what the audit must catch.

---

## 3. WHAT SHIPPED THIS SESSION (all pushed)
- `order_dispatch.py` + `money_movement.py` + `payment_providers.py` — the two missing engines (signal→gate→bridge→ledger; deposit/withdraw/payout/reinvest gated). Stripe skeleton.
- `agent_dispatch.py` — real agent signals → overseer → gated dispatch; `scripts/run_agent_dispatch_cycle.py`.
- API routes: `order-dispatch`, `money-movement`, `broker-control`, `risk-control`, `assistant`.
- **broker_control** — platform select (auto/mt5/mt4/simulated) + `broker_strictness` loose/normal/strict (loosen OR harden both MT5 & MT4).
- **MT5 bridge hardening** — live gate enforced at the BRIDGE (`is_demo_account` STRICT/fail-closed; `close_position` gated; substring fail-open removed).
- **money_movement** — withdraw bound to allowlisted destination; `movement_max_usd` cap; provider errors → FAILED not 500; API `?confirm=true` second layer.
- **risk_control** — any concurrent count / loss cap or UNLIMITED, runtime, with Settings "Risk Control — You Drive" panel.
- **Floating AI assistant** (`FloatingAssistant.tsx`) on every page + `/assistant/chat` → real Claude, grounded prompt + injected live state, "thinking" animation.
- **Mobile nav hamburger** (Shell.tsx + App.css) — Settings reachable on phone.
- **Quick Start** — MT5 Algo-Trading steps + MT4 card.
- **Fury promote** — `allow_unverified` owner override ("Promote anyway (unverified)").
- **YFinance connector** period fix (real bars).
- Memory: `project_cas_forex_dispatch_money_broker_control.md` records the gate invariants — DO NOT regress them.

---

## 4. KEY FILES / PATTERNS
- Runtime-override pattern (copy for Task A): `cas_forex/risk_control.py`, `api/routes/risk_control.py`, `RiskControlPanel` in `ui/src/pages/SettingsPage.tsx`, helpers in `ui/src/data/api.ts`.
- Real-money gate (single source of truth, fail-closed): `cas_forex/runtime_gates.py` (`evaluate_live_trading` etc.), enforced again at `cas_forex/broker/mt5_bridge.py` (`_live_gate_block`, `is_demo_account`).
- Dispatch: `cas_forex/order_dispatch.py` (`TradeIntent`, `dispatch_order`, `build_dispatch_report`), `cas_forex/agent_dispatch.py`. Bridge factory: `broker_control.select_bridge()` (used by the loop) and `mt5_bridge.get_bridge()`.
- UI shell/nav: `ui/src/App.tsx` (page union + render), `ui/src/components/Shell.tsx` (NAV_ITEMS + hamburger), `ui/src/App.css` (`.shell-nav*`, hamburger `@media (max-width:860px)`).
- Chart: `ui/src/components/charts/CandlestickChart.tsx`. Market data: `cas_forex/market_data/connector.py` (`get_connector`, `fetch_historical`, `fetch_snapshot`).
- Assistant: `api/routes/assistant.py` (SYSTEM_PROMPT + `_live_state_block`).

## 5. IMMEDIATE NEXT STEPS for the next agent
1. Read `CHANGELOG.md` head + this file.
2. `preview_list` → confirm both servers up; if not, `preview_start` each.
3. **Build Task A (in-app live-enable toggles)** following the risk_control override pattern; wire runtime_gates to consult the overrides; add the Settings "Go Live — Owner Switches" panel with toggles + a runtime-gate readout; run full `tests/`; commit+push.
4. **Build Task B (Trading Windows)** — connector already fixed; build `chart.py` endpoint (cached) → `TradingWindow.tsx` → `WindowsPage.tsx` → nav.
5. **Launch the comprehensive UI audit workflow** and fix the `[object Object]` Daily Report bug + whatever it surfaces.
6. Commit + push after each unit; chain `git push` to the commit. Branch off master only if needed (already on the feature branch).
