# CAS Forex — Session Handoff (2026-06-28, PART 3: the EDGE investigation)

Branch: `codex/cascompass-legal-live-source` · latest commit before this doc: `a4c94585` (pushed, in sync).
Read this FIRST, then `CHANGELOG.md` head. Prior handoffs (still useful background): `SESSION_HANDOFF_2026-06-28.md`, `SESSION_HANDOFF_2026-06-28-PART2.md`.

Owner = "Little Henderson / Wakil". NOT a developer — every capability must be an in-app control, never an env var or CLI step *he* runs. Plain language, no jargon. Be honest ONCE, never moralize, never fake optimism, never baby him. He drives.

---

## 0. THE ONE THING TO UNDERSTAND FIRST

This session moved from "finish the build" to **honestly answering whether CAS Forex has a trading edge.** The answer, established rigorously: **there is NO demonstrated edge.** Price-only signals have no edge at any scale (all-gaps); every strategy-assembly tool (PCBA, CJT, Fury, optimizer, condition_lab) organizes/tunes the same edgeless price rules; and the first real new-information test (macro surprise) showed no *significant* skill at daily resolution.

A **null control** (shuffled-label / random-routing) has now caught **three** different "apparent edges" that looked real on raw stats. The discipline of this codebase is now: **nothing is an edge until it beats a null, out-of-sample, after cost.** The next instance must protect that. Do NOT build or claim a fake edge. Do NOT fabricate data. If you find yourself excited by a raw hit-rate or P&L, run the null first.

The ONE promising lever still open: an **intraday/tick post-release macro test** (§5.1). Everything is built to run it; it needs tick/M1 FX data, which is free and obtainable.

---

## 1. ULTIMATE GOAL (unchanged)

Make CAS Forex **live AND profitable** per the standard coded in `cas_forex/paper_proof.py`: a **30-trading-day, broker-verified paper proof** of net-positive P&L + max drawdown ≤ 8% + real trades on most days (the profit gates shipped earlier this session). Passing that proof IS "profitable."

- **"Live":** essentially built. Owner flips in-app toggles (Go Live + Path to Authorize), the MT4 EA mailbox is the reliable order route, the gate is fail-closed. Needs his action + a funded broker + a running terminal. Not a code blocker.
- **"Profitable":** blocked on a real edge, which this session showed does not exist in anything tested so far. No code makes a strategy profitable; the proof *measures* it, and the edge has to come from somewhere real.

---

## 2. WHAT THIS SESSION DID (by area, newest insight last)

### 2a. Finish-line build (was already committed; verified)
The profit-measuring proof, in-app auto-advance (no CLI), Proof Control UI, MT4 mailbox route, and honest authority status were already on the branch (commits `3167fb60`..`f84cad78`). Verified: app imports 144 routes, suite green. Started the **proof auto-runner** (it was OFF) — now runs once/trading-day. Proof ledger is at **3/30 verified days, 0 trades, net $0** (the existing days are demo heartbeats; the bot isn't actually trading yet, and the demo terminal must be connected for verified days).

### 2b. Monorepo cleanup (commits `8747a4f5`, `b5675251`, `c672b382`, `04f7df27`, `08cf794a`, `61d83085`, `01d3c15c`)
The repo history was **latently broken**: ~104 tested CAS Forex files were untracked, yet committed code imported them (`api/server.py` imported untracked routers; the MT4 bridge imported untracked `mt4_mailbox_bridge`). Committed them ("make the repo whole"). Then cleaned the whole monorepo: **restored 28 accidentally-deleted eval packs** (`cas-synthetic/data/path_d/v1_eval_pack_*`), landed real `.gitignore`s (root was 1 line), committed genuine work across cas-synthetic / docs / scaffold / subprojects. Big ML data + CAS-Forex `evidence_runs/` are **kept on disk but git-ignored** — see memory `reference_tkscas_monorepo_gitignore_data_policy`. **Never `git add -A` from repo root.**

### 2c. Archived CAS Forex output to D:
`D:\tksCAS-archive\cas-forex-evidence_runs_20260628_101216` (1552 files, 494 MB, 3 sha256 confirms). Owner plans to move to cloud later.

### 2d. THE EDGE INVESTIGATION (the heart — read carefully)
- **`cas_forex/edge_oos.py`** (commits `d7ba0062`, `e2fa510b`) — leak-free OOS regime-switching test: routing learned on TRAIN only, per-bar causal switcher trades the held-out test, realistic 2pt cost, measured vs **best-single + a RANDOM-ROUTING null + buy-hold**. Result: **NO EDGE — switching never beats the random null (0% of windows) at any cost.** The headline return flips sign on a data refetch (+40% / −2.7%) — pure beta/noise.
- **All assembly tools are dead ends** (verified by read-only agents): PCBA / CJT / CCB are governance/compiler/gating layers in CAS *cognitive-state* space — they never touch price. Forex Fury imports/ranks third-party `.set` files by the vendor's own backtest. condition_lab's 13 settings are re-parameterizations of the same 6 trailing-price rules. The LLM optimizer has no LLM/model. **13-setting condition_lab grid through edge_oos** (`scripts/run_edge_oos_conlab.py`, commit `2366d812`): 4 settings positive standalone (beta in patches) but selecting among them forward → NO_EDGE (0% beats null).
- **CAS Harness** can't help: it's an LLM-interpretability platform over text/cognition — wrong domain, never forecasts price.
- **28 Foundations + CAS recipes** can't supply the bias-state: a recipe `Θ(Ω)=Σ w·X→Ω` is compositional (actual yield is an *input*, not a forecast); the Foundations are a taxonomy. Both organize, neither predicts. Useful framing: the recipe **limiting reagent names NEW INFORMATION as the missing ingredient** (`Θ(Ω_profit)=a·price + b·NEW_INFO → profit`, limiting reagent = NEW_INFO ≈ 0 → yield ≈ 0).

### 2e. Discipline frame (commit `c759c5a2`) + bias-state map (`7399b735`)
Agent-built (worktree-isolated), main-agent integrated + leak-reviewed:
- **`cas_forex/cascade_forecast.py`** — projects the regime cascade forward, decays confidence as a running product (monotone, faster at higher β), flags **breakdown** (runaway→involution inversion, trend→reversal) and **open-cause gap** (a scheduled macro event in the horizon). Pure discipline; NO directional edge.
- **`cas_forex/nested_lacunarity.py`** — the **bias-state map**: leak-free OOS gap/non-gap per (symbol × timeframe × regime) cell, nested by tf→regime→symbol, fractal-coherent cell finder. The multi-timeframe leak is killed **structurally** (`TimeframeAlignedView` exposes only closed higher-TF bars via a name-mangled list + bisect — a forming bar is unreachable).
- **Measured D1+H1: ALL_GAPS (28/28 cells, 0 non-gap).** H1 (finer, untested) surfaced no hidden edge.

### 2f. Macro-surprise new-information cell (commits `b7d6e9f5`, `a4c94585`) — THE FIRST REAL NEW-INFO TEST
- **`cas_forex/macro_surprise.py`** — the open-cause (^8) channel as a recipe. surprise=(actual−forecast) causally z-scored; strictly-after-release move; sign learned on train; OOS net of cost vs a **shuffled-surprise null**. Instrument **validated** (planted signal→CANDIDATE_EDGE; pure noise with a 0.67 hit rate + 2.3%→NO_SKILL because the shuffle does as well). `evaluate_surprise_return_pairs` is the reusable OOS+null core.
- **Real data:** HuggingFace dataset `Ehsanrs2/Forex_Factory_Calendar` (Forecast=consensus + Actual + release date; verified real against the Apr-2025 NFP print). Runner `scripts/run_macro_surprise_real.py`.
- **Result (811 surprises, 28 US high-impact indicators, 2021–2026, daily event-study vs EUR/USD): NO_SKILL.** The instrument learned the correct economics unaided (sign=−1: hot US data → EUR/USD down), got **56.3% hit + 7.45%** — but the null p95 is **+9.52%**, so it does NOT clear the 95% bar. **Important nuance:** the real signal sits *above the null mean* (~85–90th pct) — a faint tilt, not flat zero — but a *daily* return dilutes the true seconds-to-minutes macro reaction below significance.

---

## 3. THE FULL EDGE MAP (one table to remember)

| Lever | Verdict |
|---|---|
| Strategies + all assembly tools (PCBA, CJT, Fury, optimizer, condition_lab, regime-switching) | ❌ no edge (governance, or tuning of the same price rules) |
| CAS Harness | ❌ wrong domain (audits cognition, not price) |
| 28 Foundations / CAS recipes | ❌ organize/compose, don't predict; recipe names NEW INFO as limiting reagent |
| Price-only across timeframes (nested lacunarity, D1+H1) | ❌ ALL_GAPS |
| Intraday/scalping (M1/M5/M15) bias-state map | ⚠️ INCONCLUSIVE — crashed on an engine bug (see §5.2), NOT measured |
| **Macro surprise → EUR/USD (daily)** | ⚠️ **NO_SKILL but a faint tilt; daily dilutes the real reaction** |
| **Macro surprise → intraday/tick (the open door)** | ❓ **UNTESTED — needs tick/M1 FX data (free, obtainable) — §5.1** |

---

## 4. KEY FILES (all committed, suite green at 1217 passed)

- Edge measurement: `cas_forex/edge_oos.py` (+ `scripts/run_edge_oos.py`, `run_edge_oos_conlab.py`), tests `tests/test_edge_oos.py`.
- Bias-state map: `cas_forex/nested_lacunarity.py` (+ `scripts/run_nested_lacunarity.py`), tests `tests/test_nested_lacunarity.py`.
- Cascade discipline: `cas_forex/cascade_forecast.py`, tests `tests/test_cascade_forecast.py`.
- Macro new-info cell: `cas_forex/macro_surprise.py` (+ `scripts/run_macro_surprise_real.py`), tests `tests/test_macro_surprise.py`.
- The regime stack it builds on: `cas_forex/regime_sim.py` (detect_regime, lacunarity, DEFAULT_ROUTING), `cas_forex/walk_forward.py`, `cas_forex/backtest/engine.py`, `cas_forex/condition_lab.py`, `cas_forex/forecast/strategies.py`.
- The standard: `cas_forex/paper_proof.py` (30-day proof), `cas_forex/proof_control.py` (profit thresholds + auto-runner), `cas_forex/proof_runner.py`.
- Findings doc: `docs/working/cas_forex_edge_oos_finding_20260628.md`.

---

## 5. WHAT NEEDS TO BE DONE (prioritized)

### 5.1 ⭐ THE intraday/tick macro test (the one promising open door)
The daily macro test under-resolved the reaction. Do it at the scale macro moves actually happen:
1. **Get free tick/M1 FX history** (NOT yfinance — its M1 is 7 days only). Sources: **HistData.com** (free per-month M1 CSV ZIPs, years of history, e.g. EURUSD) or **Dukascopy** (free tick). Both are no-auth/free downloads.
2. **Use canonical release times** (the FF scraped intraday timestamps are unreliable; the *schedule* is reliable). US 8:30 ET releases (NFP, CPI, PPI, Retail Sales, Core PCE, Avg Hourly Earnings, GDP) = **12:30 UTC during EDT (Mar–Nov) / 13:30 UTC during EST (Nov–Mar)** — handle DST. ISM = 10:00 ET. FOMC statement = 14:00 ET. Assign per indicator.
3. Measure the EUR/USD move in the **5–30 min after each release** (M1 bars), reuse `cas_forex/macro_surprise.evaluate_surprise_return_pairs` (the OOS + shuffled-null core), per-indicator causal z-score, realistic FX cost.
4. Re-download the FF calendar (consensus+actual+date) — it is NOT in the repo (see §8).
5. **Decision rule fixed in advance:** beat the shuffled-null p95 OOS after cost, or NO_SKILL. Report sample size. Do NOT tune to pass.
This is the honest shot at turning the faint daily tilt into a real verdict. It will likely still be NO_SKILL (markets price consensus in seconds, and retail can't capture the first-second move) — but it's the one test left that could legitimately surprise, and it must be run before concluding new-information is also dead.

### 5.2 Fix the intraday-engine bug + finish the scalping bias-state map
The M1/M5/M15 nested-lacunarity run **crashed** (not all-gaps): at fine scale the ATR-based take-profit rounds to == entry price, and `backtest/engine.py::_generate_proposal` raises `ForecastProposal` "LONG take_profit must be > entry_price". Fix: enforce a **minimum stop/target distance** (e.g. ≥ 1 price-unit / ≥ 1 pip), or skip the trade when SL/TP collapse to the entry. Then re-run `scripts/run_nested_lacunarity.py --real --timeframes M1 M5 M15`.

### 5.3 The proof track (mechanical, but gated on reality)
Proof is auto-running but stuck at 3/30 with **0 trades**. To advance with *real* trades it needs: (a) the MT5 demo terminal connected (flaky IPC — see PART2 handoff; the MT4 mailbox is the stable route), and (b) the bot actually placing paper trades (the Auto-Trade Loop running). And it will measure a no-edge strategy until §5.1/§5.2 find one. Honest: don't present proof progress as progress toward profit while the edge is unproven.

### 5.4 Live path (owner actions, not code)
Owner flips the in-app toggles (owner_enable_live_trading + live_trading_licensed + live_mode + the two acks), connects a funded real (non-demo) account + running terminal. The gate stays fail-closed; a connected DEMO never auto-authorizes live.

---

## 6. HOW TO RUN / OPERATE
- Servers in `cas-forex/.claude/launch.json` via `preview_*` MCP. **cas-forex-api** = `C:\Python314\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8765` (MUST be the absolute 3.14 python; restart after any Python change — no --reload). **cas-forex-ui** = `npm --prefix ui run dev` (Vite :5174, HMR). If "another chat" owns the ports and they're stale/dead, `preview_start` will reclaim them.
- Tests: `C:/Python314/python.exe -m pytest tests/ -q -p no:cacheprovider` (~50–60s, **1217 passed, 0 failed**). Run before every commit.
- UI typecheck: `cd ui && npx tsc --noEmit` before committing UI.
- Open the app for the owner: `Start-Process "http://localhost:5174/?page=windows"`.

---

## 7. INVARIANTS & LANDMINES (do not regress)
- **Null control is sacred.** Every edge claim must beat a shuffled-label / random-routing null OOS after realistic cost. It has caught 3 fake edges; trust it over raw hit-rate/P&L.
- **NEVER fabricate market or macro data.** The macro cell consumes a pluggable real source; its `synthetic_*` helpers are HARNESS-VALIDATION-ONLY (a synthetic edge is not a market result).
- **No lookahead.** detect_regime is causal (trailing closes); nested_lacunarity's TF guard is structural; macro surprise uses prior-events-only z-score + strictly-after-release moves. Keep it that way; add a no-leakage test for any new signal.
- **Real-money gate stays fail-closed** (`runtime_gates.py`, `broker/mt5_bridge.py::_live_gate_block`, `is_demo_account` strict). A connected demo never authorizes live.
- **Git:** big ML data + `evidence_runs/` are git-ignored on disk — never `git add -A` from repo root. The FF calendar CSV and downloaded tick data are external — do NOT commit them. LF→CRLF warnings are benign. Commit + push per unit. Co-author trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## 8. DATA NOTES (important — some data is ephemeral)
- **FF economic calendar:** `Ehsanrs2/Forex_Factory_Calendar` on HuggingFace, file `forex_factory_cache.csv` (68 MB, 2007→2025-04). Download: `curl -sL -o ff_calendar.csv "https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/resolve/main/forex_factory_cache.csv"`. It was downloaded to the **session scratchpad** (ephemeral — GONE in a new session). RE-DOWNLOAD it; do not commit it. Columns: DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail. The "Detail" field encodes the sign convention ("'Actual' greater than 'Forecast' is good for currency").
- **Price data:** yfinance — D1 ~5y, H1 ~2y, M5/M15/M30 ~60d, **M1 only ~7d** (too short for years of intraday — use HistData/Dukascopy for that). Index proxies are ^DJI/^NDX cash (not the tradeable CFD); FX `=X` is indicative MID with NO real spread — any non-gap on this data must be re-tested on broker candles.

---

## 9. MEMORY POINTERS (already written)
- `project_cas_forex_regime_switching_simulator` — RESOLVED: no OOS edge; nested lacunarity ALL_GAPS; macro-surprise daily NO_SKILL; the intraday-macro open door. **Read this.**
- `reference_tkscas_monorepo_gitignore_data_policy` — the git/data policy (don't add-A; what's ignored).
- `project_cas_forex_live_profitable_finish_2026_06_28`, `project_cas_forex_first_real_backtest_no_edge_2026_06_21`, `feedback_no_defeatist_framing_in_cas_forex`, `feedback_user_drives_full_control_no_babying`.

---

## 10. HONEST STATUS SEPARATION (say it this way to the owner)
- **Built + tested:** the full measurement apparatus (edge_oos, nested_lacunarity, cascade_forecast, macro_surprise) — all null-guarded, suite green. The discipline frame works.
- **Measured = no edge:** price-only at every scale (all-gaps); all assembly tools; macro surprise at daily resolution (faint tilt, not significant).
- **Not yet tested:** intraday/tick macro reaction (§5.1) — the one open door, data is free.
- **Inconclusive:** scalping bias-state map (crashed, §5.2).
- **Not licensed / owner-gated:** live trading, broker accept, money movement — all fail-closed, awaiting owner toggles + funded broker.
- The honest bottom line for the owner, stated once: the app is built and the machinery to *find and prove* an edge honestly is now complete — but no edge has been found in anything tested, and the only promising lever left (intraday macro) likely also fails. "Profitable" is not yet real, and may not become real; the value delivered is a rigorous, traceable system that refuses to fool itself.
