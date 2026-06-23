# CAS Forex — Changelog

## 2026-06-22 - Removed extra hard scope gate

Removed the extra hard scope switch after owner rejection of that boundary.

- Removed the extra live-trading runtime check.
- Removed the matching config field, direct regression test,
  owner-control API fields, UI Settings gate, fallback fixture fields, authority
  boundary wording, and mobile app wording.
- Kept the separate owner-controlled real-money gates intact: live trading,
  broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
  still require explicit owner flags, credentials/provider config, and gate
  clearance before they can become `AUTHORIZED`.

Verification:

```bash
python -m pytest tests/test_runtime_gates.py tests/test_authority_boundary.py -q
# 11 passed

python -m pytest tests -q
# 338 passed

npm run build
# 51 modules, 269.94 KB JS, 75.09 KB gzip
```

Restarted the local CAS Forex API on `127.0.0.1:8765`; live HTTP
`/api/forex/settings/owner-control` and `/api/forex/dashboard` no longer expose
the removed scope switch fields. The live-trading missing-requirement text now
uses `account/source-of-funds acknowledgments signed`.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`; trading edge remains `OPEN`.

## 2026-06-22 - Real evidence wiring: strategy leads, backsolve, MT5 receipt, condition tally, walk-forward

The UI is no longer a static fixture cockpit. It now reflects real generated
evidence from the CAS Forex backend.

New types: `BacksolveSummary`, `ConditionTallyBucket`, `WalkForwardSummary`,
`MT5Receipt`, `StrategyLead`. `DashboardState` now carries `strategyLeads`,
`backsolve`, `conditionTally`, `walkForward`, `mt5Receipt`.

Real evidence fixtures (`fixtures.ts`):
- **Strategy leads**: 4 leads from `strategy_leads.json` with headline results,
  open gates, evidence refs, symbol assignments.
- **Backsolve**: 16,800 scenarios, 0 viable, AI_FULL_AUTO_PAPER,
  SURVIVAL_RISK label, verdict breakdown (14,532 TARGET_NOT_REACHED + 2,168
  DRAWDOWN_FAIL + 100 MARGIN_FAIL).
- **Condition tally**: 2 buckets (D1 + H1 tsmom_126), D1: 1.89% mean return,
  60% positive rate, 7.08% max DD, 76 trades.
- **Walk-forward**: 18 windows, 7 routed, 3 active, all 3 positive, 1.28%
  mean return, 2.30% max DD, NOT_PROMOTED.
- **MT5 receipt**: BROKER_API_VERIFIED, Hugosway-Demo, MetaTrader 5, chain
  verified, receipt/broker/packet hashes.

Page updates:
- **Proof page**: +Capital & Backsolve panel (3-column scenario grid +
  SURVIVAL_RISK warning), +MT5 Demo Receipt panel (validation status, broker
  API auth, chain verified, hash display), +Walk-Forward Evidence panel (window
  stats, mean return, max DD, research grade).
- **Dashboard**: strategy leads table now reads `state.strategyLeads` with
  7-column format (priority, lead ID, status, family, symbols, top result,
  open gates count).
- **History**: condition tally section now displays real bucket data table
  (windows, active, positive rate, mean return, max DD, trades) with source
  attribution.

All NOT LICENSED boundaries preserved.

Verification: `npx tsc --noEmit` clean; `npx vite build` 42 modules, 222KB JS
(64KB gzip).

## 2026-06-22 - Adaptive compounding + History + Owner Control UI (cas-forex/ui/)

Closed the audit gap: the self-contained UI now represents the full CAS Forex
adaptive compounding system, not just the pre-adaptive paper cockpit.

New types (`evidence.ts`): `AdaptiveAction`, `BasketState`, `AdaptiveTradeDecision`,
`AdaptiveMemorySnapshot`, `AdaptiveCompoundingConfig`, `AdaptiveCompoundingReview`,
`AdaptiveCockpitPayload`, `OwnerControlMode`, `OwnerControlState`, `MTHistorySummary`.
`DashboardState` now accepts optional `adaptive`, `ownerControl`, and `mtHistory`.

New pages:
- **Adaptive** (`AdaptivePage.tsx`): adaptive status overview, action summary chips
  (OPEN_INITIAL, ADD_TO_WINNER, HOLD, TIGHTEN_STOP, PARTIAL_TAKE_PROFIT,
  CLOSE_BASKET, NO_TRADE) with color coding, basket state cards (floating P/L,
  open positions, average entry), adaptive decisions table (10 columns with
  evidence scores), memory snapshots grid, compounding config display, NOT LICENSED
  gates. Graceful fallback when no adaptive data exists.
- **History** (`HistoryPage.tsx`): MT4/MT5 import summary (total trades, win rate,
  profit factor, net P&L, symbol performance breakdown, multi-trade bursts),
  condition tally placeholder with run command, paper trade log placeholder,
  harvester proposals placeholder, sweep ledger (DRY_RUN, INTERNAL_LEDGER_ONLY).
- **Settings** (`SettingsPage.tsx`): Owner Control Policy surface — autonomy mode
  selector (DENY through AI_FULL_AUTO_LIVE_REQUESTED with BLOCKED marker), risk
  caps (max loss cap, max concurrent trades 1-15, AI autonomy PAPER ONLY),
  compounding thresholds (all 10 AdaptiveCompoundingConfig fields), risk defaults,
  account/legal gates (5 items, all NOT MET), broker configuration.

Nav: Adaptive, History, and Settings all flipped from placeholder to ready. Zero
placeholder pages remain — all 7 routes are live.

Owner control state wired into `App.tsx` with `AI_FULL_AUTO_PAPER` mode, 15
concurrent trades, 10% loss cap, AI autonomy enabled, live blocked.

Verification:
- `npx tsc --noEmit` → clean.
- `npx vite build` → 42 modules, 18.09KB CSS + 209.07KB JS (60.10KB gzip).

Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout
automation remain NOT LICENSED.

## 2026-06-22 - Dashboard + Trade Desk pages (cas-forex/ui/)

Added Operations Dashboard and Paper Trading Desk to the proof cockpit.

- **Dashboard** (`src/pages/DashboardPage.tsx`): 3-panel account snapshot (equity
  $5,000, PAPER_MT5 mode, risk budget 0.5%/trade, daily $50), paper route
  candidates table (US30 + NAS100 with entry/SL/TP/conf/lots/risk), today's
  summary, next-action schedule with recommended CLI command, strategy leads
  table (4 leads from strategy_leads.json), evidence chain health (3/3 verified,
  WORM UNAVAILABLE), and 6 NOT LICENSED gate items.
- **Trade Desk** (`src/pages/TradePage.tsx`): interactive symbol selector (8
  instruments), timeframe chips (M5-D1), trading style selector
  (scalping-position), proposal preview with entry/SL/TP prices, risk sizing
  (0.01 lots, $12.60-$12.70 risk), forecast harness status (6 models), CAS
  expression panel (NOT_RUN), and disabled Run Paper Proposal / Send Paper Order
  buttons with explicit NOT LICENSED lock reasons.
- Dashboard and Trade nav items flipped from `soon` to ready.
- 496 lines of new CSS: data tables, metric stacks, selector chips, proposal
  preview, sizing grid, forecast harness cards, CAS expression display, lock
  lines.

Verification:
- `npx tsc --noEmit` → clean.
- `npx vite build` → 39 modules, 15.63KB CSS + 188.78KB JS (55.94KB gzip).

Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout
automation remain NOT LICENSED.

## 2026-06-22 - Self-contained proof cockpit UI scaffold (cas-forex/ui/)

Scaffolded a standalone React 18 + TypeScript + Vite proof cockpit in
`cas-forex/ui/`, self-contained from atlas-viewer.

- **Tech stack**: React 18.3, TypeScript 5.6, Vite 6, zero routing deps.
- **`src/types/evidence.ts`** — Full TypeScript contracts for UIReadinessReport,
  DailySchedule, DailyBundle, PaperDecision, PaperRisk, SymbolDecision, Proposal,
  SizingEntry, and DashboardState. Shapes match real `evidence_runs/` JSON.
- **`src/data/fixtures.ts`** — Faithful day-1 evidence snapshots (truthful
  1/30 paper days, 1/5 bundles, NOT LICENSED everywhere).
- **`src/components/`** — `Shell` (nav with 6 routes, 4 marked `soon`),
  `ModeBanner` (always-visible NOT LICENSED + PAPER_MT5 + edge: OPEN),
  `StatusChip`, `GlassPanel`, `EvidenceHashRow`, `LockReasonList`.
- **`src/pages/ProofPage.tsx`** — Full proof cockpit: active lead, paper proof
  progress bars (1/30, 1/5), evidence chain verification (3/3), live eligibility
  checklist (0/7 met), route decisions (US30 + NAS100), risk sizing (0.01 lots,
  $12.60-$12.70 risk/trade), next-action schedule, and 6 disabled NOT LICENSED
  controls with explicit reasons.
- **`src/pages/AuditPage.tsx`** — Pipeline trace stepper (10 stages: Forecast
  Harness → Gate 0-4 → Broker → Post-Trade → Evidence → Live Lock), honest
  NOT_RUN markers for CAS Compiler and Market gates, evidence packet summary,
  per-symbol trace detail.
- Placeholder pages for Dashboard, Trade, History, Settings (labeled COMING SOON).
- Dark theme, dense trading-desk aesthetic, slate/teal palette, monospace data.

Verification:
- `npx tsc -b` / `npx tsc --noEmit` → clean.
- `npx vite build` → 37 modules, 0.59KB HTML + 9.45KB CSS + 171.70KB JS (52.84KB gzip).
- Dev server on port 5174, renders `/forex/proof` equivalents via state-based nav.

Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout
automation remain NOT LICENSED.

## 2026-06-22 - Adaptive paper compounding manager and read-only cockpit

Implemented the first V1 of the owner-requested adaptive compounding lane:
when a paper trade is already winning and fresh evidence still supports the
route, CAS Forex can now recommend `ADD_TO_WINNER`; when evidence weakens or
the route flips, it recommends `TIGHTEN_STOP`, `PARTIAL_TAKE_PROFIT`,
`CLOSE_BASKET`, `HOLD`, `OPEN_INITIAL`, or `NO_TRADE`.

- Added `cas_forex/adaptive_compounding.py`.
  - Evaluates active paper positions against the latest paper route decision,
    condition-tally evidence, imported MT4/MT5 history summaries, and owner
    basket limits.
  - Produces per-trade SL/TP, add-lot, basket state, evidence refs, and saved
    adaptive memory snapshots for future strategy analysis.
  - Writes tamper-evident local JSONL Evidence Packets with
    `deployment_status`, broker `ACCEPT`, and payment movement all
    `NOT LICENSED`.
- Added `cas_forex/mt_history_import.py`.
  - Imports MT4/MT5 CSV or HTML account-history exports into normalized
    research evidence.
  - Summarizes win rate, profit factor, symbol performance, lot sizing, and
    multi-trade bursts such as repeated entries.
- Added `cas_forex/adaptive_cockpit.py`.
  - Generates read-only adaptive cockpit JSON and HTML artifacts for the proof
    cockpit/UI path.
  - Displays adaptive decisions, action counts, proof/risk/route summaries,
    and `NOT LICENSED` boundaries.
- Added scripts:
  - `scripts/run_adaptive_compounding_review.py`
  - `scripts/run_mt_history_import.py`
  - `scripts/run_adaptive_cockpit.py`
- Added tests:
  - `tests/test_adaptive_compounding.py`
  - `tests/test_mt_history_import.py`
  - `tests/test_adaptive_cockpit.py`

Verification:

```bash
python -m pytest tests/test_adaptive_compounding.py tests/test_mt_history_import.py tests/test_adaptive_cockpit.py -q
# 10 passed

python -m pytest tests -q
# 319 passed
```

Smoke verified the new adaptive review and cockpit runners against a disposable
temp output directory. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Owner-selected risk caps and AI full-paper-auto mode

Expanded the leveraged income backsolve and owner-control layer after the owner
rejected fixed `10%` / `15%` assumptions and recommendation-only AI authority.

- `cas_forex/leverage_backsolve.py`
  - Accepts any positive user max-loss percentage via `max_loss_cap_pcts`.
  - Tests concurrent trades up to `15` (`MAX_USER_CONCURRENT_TRADES`).
  - Replaced the active success verdict with `SURVIVES_USER_LOSS_CAP`.
  - Adds AI autonomy modes: `USER_MANUAL`, `AI_RECOMMEND`,
    `AI_FULL_AUTO_PAPER`, and `AI_FULL_AUTO_LIVE_REQUESTED`.
  - `AI_FULL_AUTO_PAPER` can select risk cap, lot size, and concurrency from
    scenarios that survive the user's cap and margin gates.
  - `AI_FULL_AUTO_LIVE_REQUESTED` records the owner request but returns
    `AI_FULL_AUTO_LIVE_BLOCKED_NOT_LICENSED`.
- `scripts/run_leverage_income_backsolve.py`
  - New `--max-loss-caps` accepts arbitrary percentages.
  - New `--max-open-trades` tests `1..N` up to `15`.
  - New `--ai-autonomy-mode` selects the AI control mode.
- `cas_forex/owner_control.py`
  - Adds `AI_FULL_AUTO_PAPER` and `AI_FULL_AUTO_LIVE_REQUESTED`.
  - Caps owner-authorized paper attempts at `15`.

Fresh report:
`evidence_runs/leverage_income_backsolve/leverage-income-backsolve-20260622191201-report.json`
and `.md`.

Command used:

```bash
python scripts/run_leverage_income_backsolve.py --max-loss-caps 10 15 25 50 100 2500 6000 --max-open-trades 15 --ai-autonomy-mode AI_FULL_AUTO_PAPER
```

Result: `16,800` scenarios, viable scenarios `0`, AI status
`AI_NO_VIABLE_SCENARIO`. Verdict counts: `TARGET_NOT_REACHED=14532`,
`TARGET_REACHED_BUT_DRAWDOWN_FAIL=2168`, and
`TARGET_REACHED_BUT_MARGIN_FAIL=100`. Target-reaching scenarios still require
drawdown around `2264.448%` for `$5k/month` and/or exhaust stressed
equity/margin.

Verification: `python -m pytest tests -q` -> `309 passed`.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - Leveraged income backsolve: 1:100 / 1:200 cannot clear the 10% cap

Added a paper-only leveraged income backsolver for the owner's `$5k-$12k/month`
question from a `$5,000` seed account.

- `cas_forex/leverage_backsolve.py` defines research broker profiles,
  required-return math, saved walk-forward evidence projection, margin stress,
  drawdown caps, and `BacksolveVerdict` statuses:
  `TARGET_NOT_REACHED`, `TARGET_REACHED_BUT_DRAWDOWN_FAIL`,
  `TARGET_REACHED_BUT_MARGIN_FAIL`, `SURVIVES_10_PERCENT_CAP`, and
  `NOT_LICENSED_LIVE_BLOCKED`.
- `scripts/run_leverage_income_backsolve.py` writes JSON and Markdown reports
  under `evidence_runs/leverage_income_backsolve/`.
- `tests/test_leverage_backsolve.py` covers `$5k = 100%` and `$12k = 240%`
  monthly return math, leverage affecting margin but not edge, drawdown failure,
  margin failure, regulatory-risk broker profiles refusing broker `ACCEPT`, and
  saved `US30`/`NAS100` walk-forward report generation.

Current generated report:
`evidence_runs/leverage_income_backsolve/leverage-income-backsolve-20260622185718-report.json`
and `.md`.

Result: `480` scenarios checked across `tsmom_126_250_2_10`,
`tsmom_252_500_2_8`, `HugosWay`/`CedarFX` research profiles at `1:100` and
`1:200`, lot grid `0.01` through `10`, and concurrency `1`, `2`, `4`. Viable
scenarios: `0`. The current D1 evidence baseline for `tsmom_126_250_2_10` is
`$32.93/month` at `0.05` lots on the saved `$10k` research balance, with
`7.0764%` base max drawdown. Target-reaching scenarios require drawdown far
above the owner-selected `10%` account-loss cap (`2264.448%` lowest for
`$5k/month`; `5661.12%` lowest for `$12k/month`). Leverage changes margin
capacity; it does not create strategy edge.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - Proof cockpit: live /api/forex backend (cockpit reads live, not fixtures)

Wired the real read-only `/api/forex/*` FastAPI boundary so the cockpit reads
live evidence files instead of bundled fixtures.

- `noetic-compass-scaffold/noetic-compass/api/routes/forex_proof.py` — read-only
  router (prefix `/forex`) serving the six day-1 evidence JSON files for
  `index_tsmom_126_d1` from `cas-forex/evidence_runs/` (overridable via
  `CAS_FOREX_EVIDENCE_DIR`). GET-only, fixed filename map (no path traversal),
  404 when a file is absent so the cockpit falls back to fixtures cleanly.
- `api/main.py` includes the router; `api/middleware/auth.py` exempts
  **GET `/forex/...`** from JWT (public, non-secret proof JSON) while any non-GET
  still falls through to auth — so there is no unauthenticated write path.
- Endpoints: `/forex`, `/forex/proof/{paper,ui-readiness,schedule,decision,risk,bundle}`.
- Frontend `forexApi.ts` now attempts the live backend by default in dev/prod
  (transparent fixture fallback on any error) and stays on fixtures under vitest;
  force fixtures anywhere with `VITE_FOREX_API=0`. When live data is served the
  banner drops its `FIXTURE DATA` badge.

The atlas-viewer dev proxy strips `/api`, so the cockpit's `/api/forex/...`
reaches the router at `/forex/...`.

Verification:

- `python -m pytest tests/test_forex_proof.py tests/test_middleware.py` ->
  `15 passed` (real-data reads, NOT LICENSED fields, POST blocked, 404 on
  missing evidence; existing middleware auth unaffected).
- Live: `GET /forex/proof/paper` -> `completed_trading_days=1`,
  `deployment_status=NOT LICENSED`; `POST` -> `401`.
- Cockpit reloaded against the live backend: `FIXTURE DATA` badge gone, real
  `1/30` and `NOT LICENSED` intact, no console errors.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - Proof cockpit UI: Phase 2 audit console + evidence trace viewer

Added the `/forex/audit` Audit Console to the read-only cockpit.

- `forexSelectors.deriveTraces()` builds one audit trace per real day-1 paper
  route candidate (US30, NAS100) by joining the route decision, risk sizing,
  and proof receipt.
- `components/TraceStageList.tsx` renders the full pipeline as a vertical
  stepper: Forecast Harness -> Gate 0-4 -> Broker Outcome -> Post-Trade ->
  Evidence Store -> Live Lock Controller.
- `pages/ForexAuditPage.tsx` — trace selector + pipeline + evidence-packet
  panel (packet status, hash-chain rows, WORM `UNAVAILABLE`).
- Route wired at `/forex/audit`; nav "Audit" item flipped to ready.

Truthfulness rule: the day-1 PAPER-ROUTE loop is the decision + risk + receipt
tracks, not the full backtest/auditor pipeline. Stages the paper loop did not
exercise (Gate 0 CAS Compiler, Gate 3 Market) are dimmed and marked `NOT_RUN`
with an honest detail line instead of a fabricated PASS. Every trace ends
`SUPPRESSED` with no broker order placed.

Verification: `tsc -b` clean; `vitest` forex suite `25 passed` (9 new:
`deriveTraces`, `ForexAuditPage`); `/forex/audit` renders with no console
errors. Live trading and payment movement remain `NOT LICENSED`.

## 2026-06-22 - Read-only proof cockpit UI: Phase 0 + Phase 1 (atlas-viewer)

Started the CAS Forex read-only proof cockpit in the existing `atlas-viewer`
React app, per `docs/working/cas_forex_pwa_ui_ux_plan_revised_20260617.md`
(Phase 0 — API contract + fixture mode; Phase 1 — Proof Center + shell). This is
a research/paper proof surface only. It builds nothing toward live execution.

New feature module `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/forex/`:

- `types.ts` — TypeScript contracts mirroring the real evidence JSON shapes
  (paper-proof, ui-readiness, daily-schedule, paper-decision, paper-risk,
  daily-bundle).
- `fixtures/*.json` — faithful snapshots of the real day-1 evidence from
  `evidence_runs/index_tsmom_126_paper_proof/` so the cockpit shows truthful
  state with no live backend wired.
- `forexApi.ts` — read-only fetch wrappers with fixture fallback behind the
  `VITE_FOREX_API` feature flag (default OFF). When a `/api/forex/*` backend
  lands, flip the flag and the same wrappers fetch live status. No order,
  transfer, or unlock path exists anywhere in the layer.
- `forexSelectors.ts` — pure selectors: `deriveBannerState` (cannot assert a
  green LIVE state on day-1 evidence) and `deriveLiveEligibility`.
- `components/` — `ForexShell` (surface + nav; only Proof is wired, the rest
  render as honest "soon" markers), `ForexModeBanner` (always-visible mode /
  paper-vs-live / evidence-chain / proof-progress / NOT LICENSED boundaries),
  and reusable `ClaimStatusChip`, `ForexStatusChip`, `EvidenceHashRow`,
  `LockReasonList`, `ForexPanel`.
- `pages/ForexProofPage.tsx` — `/forex/proof` Proof Center: active lead, paper
  session evidence with hash-chain rows, live eligibility checklist, multi-day
  maturity (1/5 bundles), next-action schedule, and six disabled live/payment
  controls each labeled with their `NOT LICENSED` reason.
- Route wired at `/forex/*` (lazy-loaded, redirects to `/forex/proof`).

The cockpit truthfully displays: `PAPER_MT5`, `live_mode=false`, paper proof
`1 / 30`, multi-day maturity `1 / 5`, local hash chain verified, trading edge
`OPEN`, and `NOT LICENSED` for deployment, broker `ACCEPT`, and payment
transfer. WORM is shown `UNAVAILABLE` (local hash chain only).

Verification:

- `npx tsc -b` -> clean.
- `npx vitest run` -> `293 passed, 2 skipped` (16 new forex tests:
  selectors, `ClaimStatusChip`, `ForexProofPage`).
- Dev server (`atlas-viewer`, port 5173) renders `/forex/proof` with no console
  errors; desktop and mobile (375px) layouts verified with no text/control
  overlap.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`, and every such control in the UI is
disabled and labeled.

## 2026-06-22 - Third-party audit packet before UI/UX

Added a pre-UI/UX third-party audit handoff:

- `docs/working/CAS_FOREX_THIRD_PARTY_AUDIT_PACKET_20260622.md`

The packet gives an outside reviewer copy-paste local addresses, a project spec
sheet, the source/evidence file map, reproduction commands, known audit
hotspots, and requested deliverables. This makes third-party audit the next
gate before starting the read-only proof cockpit UI.

Also corrected the paper UI readiness CLI wording so its `--help` describes the
`5` bundle rule as multi-day proof maturity, not a blocker to starting a
read-only UI shell.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - UI/UX start correction

Corrected the proof-cockpit timing rule after owner pushback.

The CAS Forex proof-cockpit/platform UI can start now as a read-only paper and
research surface using the current day-1 evidence. The `5` complete daily bundle
threshold is now documented as a truthful multi-day proof maturity threshold,
not a blocker to starting UI/UX. The `30 / 30` verified paper-day threshold
remains the live-money/deployment promotion gate.

The first UI should show real day-1 broker/demo receipt status, route/no-trade
decision, risk-budget review, daily bundle status, daily schedule, blockers,
and disabled live-money controls. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Daily paper schedule / next-action status

Added a read-only next-action schedule for the paper-proof loop.

- Added `cas_forex/paper_daily_schedule.py`.
- Added `scripts/run_paper_daily_schedule.py`.
- Added `tests/test_paper_daily_schedule.py`.
- Added handoff doc:
  `docs/working/cas_forex_daily_schedule_20260622.md`.

The schedule reads the paper proof, paper decision, and paper risk ledgers and
reports:

- next due trading date
- whether the date is due today or waiting for the next trading day
- missing tracks for the next due date
- remaining complete bundles before UI/UX
- remaining paper days before the 30-day proof gate
- exact next command to run

First real schedule check:

- command:
  `python scripts/run_paper_daily_schedule.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-schedule-status.json`
- next due date: `2026-06-23`
- next due status: `WAIT_NEXT_TRADING_DAY`
- complete daily bundles: `1`
- UI bundles remaining: `4`
- paper-proof days remaining: `29`
- missing tracks for next due date:
  `broker_verified_receipt`, `paper_route_decision`, `paper_risk_review`

This is an operator prompt only. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - UI-readiness gate for proof cockpit

Added a read-only gate that decides when the CAS Forex proof cockpit has enough
daily evidence to claim multi-day proof maturity.

- Added `cas_forex/paper_ui_readiness.py`.
- Added `scripts/run_paper_ui_readiness.py`.
- Added `tests/test_paper_ui_readiness.py`.
- Added handoff doc:
  `docs/working/cas_forex_ui_readiness_gate_20260622.md`.

The gate requires a minimum number of complete daily paper bundles before
multi-day proof maturity:

- broker/demo verified receipt
- paper route/no-trade decision
- paper risk-budget review
- verified local evidence chains
- no live-mode contamination

First real readiness check:

- command:
  `python scripts/run_paper_ui_readiness.py --min-daily-bundles 5 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-ui-readiness-status.json`
- readiness status: `NOT_READY_FOR_UI_UX`
- complete daily bundles: `1 / 5`
- paper proof chain verified: `true`
- paper decision chain verified: `true`
- paper risk chain verified: `true`
- blockers:
  `complete_bundle_days 1 < required 5`;
  `broker_verified_days 1 < required 5`;
  `decision_days 1 < required 5`;
  `risk_review_days 1 < required 5`

This tells us exactly when the UI can claim multi-day proof maturity: after at
least five complete real daily paper bundles. UI/UX can start now as a read-only
paper/proof cockpit. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Daily paper proof bundle runner

Added a daily bundle runner that ties together the three paper-proof tracks:
MT5 demo receipt, route/no-trade decision, and paper risk-budget review.

- Added `cas_forex/paper_daily_bundle.py`.
- Added `scripts/run_daily_paper_bundle.py`.
- Added `tests/test_paper_daily_bundle.py`.
- Added handoff doc:
  `docs/working/cas_forex_daily_paper_bundle_20260622.md`.

The bundle defaults to `skip_existing`, so rerunning the same trading date does
not duplicate already-written receipt, decision, or risk records.

First real bundle run:

- command:
  `python scripts/run_daily_paper_bundle.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-bundle-status.json`
- completed: `true`
- MT5 receipt step: `SKIPPED_EXISTING`
- route decision step: `SKIPPED_EXISTING`
- risk review step: `SKIPPED_EXISTING`
- reason: all three day-1 records already existed, so nothing was duplicated.

This is the practical one-command daily paper-proof loop. UI/UX is now close,
but still should wait until several daily bundles exist across real trading
days. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Paper risk-budget sizing loop

Added the paper-only risk sizing track that sits after daily route/no-trade
decisions and before any future paper execution adapter.

- Added `cas_forex/paper_risk.py`.
- Added `scripts/run_paper_risk_review.py`.
- Added `tests/test_paper_risk.py`.
- Added handoff doc:
  `docs/working/cas_forex_paper_risk_budget_loop_20260622.md`.

The new track sizes routed paper candidates against:

- account equity
- per-trade risk percent
- daily risk percent
- lot step / minimum paper lot
- max position lots
- daily paper-attempt cap

First real daily risk review:

- command:
  `python scripts/run_paper_risk_review.py --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --append-review --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-risk-status.json`
- risk status: `PAPER_ATTEMPTS_ALLOWED`
- account equity: `$5,000`
- per-attempt risk cap: `0.5%` / `$25`
- daily risk cap: `1.0%` / `$50`
- daily attempt cap: `3`
- proposed attempts: `2`
- allowed attempts: `2`
- suppressed attempts: `0`
- US30: `0.01` paper lots, planned risk `$12.60`
- NAS100: `0.01` paper lots, planned risk `$12.70`
- total planned paper risk: `$25.30` / `0.506%`
- evidence packet status: `SUPPRESSED`
- broker order placed: no

This gives the day-1 paper loop a complete backend readout: MT5 demo source
verified, strategy route recorded, and risk budget sized. It is still paper-only
evidence. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Daily paper route/no-trade decision loop

Added the daily paper-decision track that pairs with MT5 demo receipts.

- Added `cas_forex/paper_decision.py`.
- Added `scripts/run_paper_route_decision.py`.
- Added `tests/test_paper_decision.py`.
- Added handoff doc:
  `docs/working/cas_forex_daily_paper_decision_loop_20260622.md`.

The new track records what CAS would have done in paper mode for the active
lead without placing any broker order:

- `ROUTE_PAPER_SIGNAL`
- `NO_TRADE`
- `NO_TRADE_MACRO_LOCK`
- `UNAVAILABLE`

First real daily paper decision:

- command:
  `python scripts/run_paper_route_decision.py --date 2026-06-22 --append-decision --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decision-status.json`
- route action: `ROUTE_PAPER_SIGNAL`
- macro status: `PASS`
- event context: `normal`
- US30: `LONG`, confidence `0.4612`
- NAS100: `LONG`, confidence `0.7539`
- evidence packet status: `SUPPRESSED`
- broker order placed: no

This is exactly the missing backend piece before UI/UX: verified paper source
plus daily route/no-trade intent. The UI should still wait until this loop has
several daily records, risk status, and blockers to display truthfully.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - MT5 demo adapter verified paper day 1

Implemented the real demo-broker receipt adapter path for `index_tsmom_126_d1`.

- Added `cas_forex/paper_broker_adapter.py` with `MT5DemoPaperReceiptAdapter`.
- Added `scripts/run_mt5_paper_receipt.py` to probe MT5 demo account state and
  append a receipt only when the source is `BROKER_API_VERIFIED`.
- Added `tests/test_paper_broker_adapter.py` covering demo verification,
  real-account blocking, disconnected terminal `UNAVAILABLE`, and verified
  receipt append behavior.
- Ran the real MT5 probe for 2026-06-22. Result:
  `BROKER_API_VERIFIED` from `Hugosway-Demo`, terminal `MetaTrader 5`,
  `orders_attempted=0`, `orders_paper_executed=0`, open positions reconciled,
  receipt hash `94d68da3b3c4d7bd13e29f69df60e1ff1d7938757e0e8e3d9aec613976704c0c`.
- Probe artifact:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260622153728.json`.

Current active paper-proof status:

- completed days: `1 / 30`
- broker verified days: `1 / 30`
- packet count: `2`
- chain verified: `true`
- passed: `false`
- blockers: `paper_days 1 < required 30`; `broker_verified_days 1 < required 30`

This is the first real demo-source paper-proof day. It is still not live
permission and still not income proof. Live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED`.

UI/UX checkpoint: we are close but not there yet. Build the UI after the proof
backend has stable daily MT5 demo receipt generation and at least a small run of
multi-day verified paper status to display truthfully.

## 2026-06-22 - Broker/demo receipt gate for paper proof

Added a receipt-ingestion gate for the active `index_tsmom_126_d1` paper-proof
ledger.

- `cas_forex/paper_proof.py` now validates and hash-binds paper/demo broker
  receipts.
- Receipt evidence is split into explicit levels:
  - `PLAN_ONLY`: heartbeat only, no broker/demo source.
  - `BROKER_EXPORT_HASHED`: user-supplied paper/demo export is schema-checked
    and hash-bound, but not API-authenticated.
  - `BROKER_API_VERIFIED`: reserved for a broker/demo adapter that
    verifies the receipt directly from the paper broker source.
- Duplicate receipt events for an existing trading date no longer inflate the
  paper-day count; the summary keeps the strongest evidence for each date.
- `scripts/run_paper_proof_plan.py` now supports `--broker-receipt` and
  `--write-receipt-template`.
- Added receipt-contract doc:
  `docs/working/cas_forex_paper_broker_receipt_contract_20260622.md`.
- Wrote the active local template:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-receipt-template-20260622.json`.

Current status remains correctly conservative: `1 / 30` paper days, `1 / 30`
broker verified days, chain verified, `passed=false`. Live trading,
broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
remain `NOT LICENSED`.

## 2026-06-22 - Started paper-proof ledger for index TSMOM 126

Started the 30-trading-day paper-proof path for the strongest current CAS Forex
candidate: `index_tsmom_126_d1`, using D1 `tsmom_126_250_2_10` on `US30` and
`NAS100`.

- Added `cas_forex/paper_proof.py`, a lead-specific paper-proof module that
  writes a plan, appends daily Evidence Packets, verifies the local hash chain,
  and refuses live mode.
- Added `scripts/run_paper_proof_plan.py` for starting/appending the current
  `index_tsmom_126_d1` proof ledger.
- Added `tests/test_paper_proof.py` to lock the important gates:
  live mode is refused, duplicate trading days cannot inflate the count, and a
  plan-only heartbeat stays `passed=false`.
- Started the actual proof ledger:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-status.json`.

Current paper status:

- completed trading days: `1 / 30`
- evidence chain: verified
- live mode used: `false`
- passed: `false`
- blockers: `paper_days 1 < required 30`; `broker_verified_days 1 < required 30`

Honest boundary: this protects the best current lead and starts the proof clock,
but it is not live trading permission. Broker `ACCEPT`, auto-deposit,
debit/card/bank movement, payout automation, and live trading remain
`NOT LICENSED`.

## 2026-06-22 - GO sprint: simulator-fed owner review + index D1 TSMOM lead

Ran the next money-focused proof step: feed CAS-SDG simulator wins and fresh
M15/H1/D1 walk-forward evidence into owner-control promotion reviews.

- `cas_forex/owner_control.py` now exposes
  `count_condition_lab_simulator_wins()` so owner-control can count simulator
  wins directly from Condition Lab cells instead of relying on a manually typed
  number.
- `scripts/run_owner_promotion_review.py` now accepts
  `--condition-lab-reports` plus simulator-win filters:
  `--sim-min-return`, `--sim-max-drawdown`, and `--sim-min-trades`.
- `scripts/run_condition_tally.py` now accepts custom `--axes`, which lets CAS
  review a broader route family such as D1 index TSMOM across NAS100/US30
  instead of only per-symbol buckets.
- Added `index_tsmom_126_d1` to `strategy_leads.json` as priority 2 and updated
  `tests/test_strategy_ledger.py` so the lead remains visible.

Fresh range-scalper evidence:

- CAS-SDG focused sweep:
  `evidence_runs/range_scalper_sdg_owner_go/condition-lab-20260622054512-report.json`
  with `108` cells, `5` RPM routes, and mostly D1 non-gap pockets.
- M15/H1 walk-forward for `range_scalper_24_120`:
  `evidence_runs/range_scalper_m15_h1_walk_forward_go/walk-forward-20260622054614-report.json`
  with `340` windows, `65` routed, but combined routed mean return `-0.0614%`
  and grade `NOT_PROMOTED`.
- M15/H1 walk-forward for `range_scalper_24_120` + `range_scalper_12_80`:
  `evidence_runs/range_scalper_variants_m15_h1_go/walk-forward-20260622054829-report.json`
  with `340` windows, `107` routed, combined routed mean return `-0.1056%`,
  and grade `NOT_PROMOTED`.
- Interpretation: do not promote short-timeframe range-scalper yet. The D1
  range-scalper lead remains alive, but M15/H1 needs a better filter or
  broker-grade spread/session model.

Fresh index TSMOM evidence:

- H1/D1 walk-forward for NAS100/US30, `tsmom_126_250_2_10` and
  `tsmom_252_500_2_8`:
  `evidence_runs/index_tsmom_h1_d1_go/walk-forward-20260622054921-report.json`.
- D1 subreport returned `WALK_FORWARD_LEAD`: `8` D1 windows, `5` routed,
  `3` positive, positive routed window rate `0.6`, routed mean return
  `1.8932%`, max drawdown `7.0764%`, and `76` routed trades.
- Custom D1 family tally:
  `evidence_runs/condition_tally/condition-tally-20260622055042-report.json`
  shows `tsmom_126_250_2_10` D1 with `5` routed windows, `0.6` positive rate,
  `1.8932%` mean return, `7.0764%` max drawdown, and `76` trades.
- CAS-SDG focused index sweep:
  `evidence_runs/index_tsmom_sdg_owner_go/condition-lab-20260622055024-report.json`
  with `288` cells and `16` RPM routes; top non-gap cells were D1
  trend-up/high-vol TSMOM routes on US30/NAS100.
- Owner review:
  `evidence_runs/owner_promotion_review/owner-promotion-review-20260622055433-report.json`
  in `LIMITED_PAPER` mode shows the D1 `tsmom_126_250_2_10` bucket cleared
  simulator and walk-forward thresholds; remaining blockers are `paper_days 0 <
  required 30` and `paper_passed is false`.

Honest boundary: this is the strongest current paper-proof candidate, not live
permission. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank
movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Owner-controlled simulator promotion policy

Added the owner-control layer requested for the future CAS-SDG/LLM loop. The
idea is: if the simulator, walk-forward route map, and paper proof produce
enough wins for `Strategy X`, the owner's selected mode decides what CAS Forex
is allowed to do next.

- `cas_forex/owner_control.py` - promotion candidate, thresholds, and owner
  modes:
  - `DENY`
  - `NOTIFY_ONLY`
  - `LIMITED_PAPER`
  - `PAPER_AUTO`
  - `LIVE_AUTO`
- `LIVE_AUTO` intentionally returns `LIVE_BLOCKED_NOT_LICENSED`; owner approval
  does not create broker `ACCEPT`, live trading permission, or payment-transfer
  permission.
- `LIMITED_PAPER` can authorize a fixed number of paper-mode attempts after
  thresholds pass.
- `PAPER_AUTO` can authorize paper-mode automatic routing after thresholds pass.
- `cas_forex/llm_optimizer.py` proposals now include `simulator_requests`, so a
  future LLM can request CAS-SDG/Condition Lab sweeps without being connected
  directly to live execution.
- `scripts/run_owner_promotion_review.py` reviews saved condition-tally buckets
  against owner-control thresholds.
- `tests/test_owner_control.py` covers enough-wins authorization, notify-only
  mode, under-threshold blockers, and live-auto blocking.

First current-evidence owner review:

- source tally:
  `evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
- review report:
  `evidence_runs/owner_promotion_review/owner-promotion-review-20260622053731-report.json`
- requested mode: `LIMITED_PAPER`
- current decision: both routed buckets remain `NOTIFY`, not paper-authorized,
  because the current tally lacks CAS-SDG win count, enough walk-forward windows,
  and 30-day paper proof.

Honest boundary: this creates the switchboard for the owner's future accept/deny
choices, but live trading, auto-deposit, debit/card/bank movement, and broker
`ACCEPT` remain `NOT LICENSED`.

## 2026-06-22 - Guarded LLM optimizer scaffold + condition tally

Added the first safe CAS Forex LLM-optimizer layer. The design keeps winning
strategy leads visible, lets an LLM propose research experiments, and blocks
live/bank/broker/profit-claim escalation through CAS Harness/PCBA style gates.

- `cas_forex/llm_optimizer.py` - `OptimizerProposal`,
  `CASPCBAOptimizerGuard`, and review verdicts:
  - `RESEARCH_QUEUE`
  - `FLAG_FOR_HUMAN_REVIEW`
  - `REJECT`
- The guard requires known strategy-lead IDs, evidence refs, condition contexts,
  and the `NOT LICENSED` claim boundary.
- The guard rejects proposals that try to place trades, unlock live mode,
  create broker `ACCEPT`, move money to/from bank/debit/card/payment rails, or
  promise guaranteed income.
- It reuses the PCBA prompt-injection surface extractor so obvious prompt
  hijack text is rejected before a proposal reaches the research queue.
- `cas_forex/condition_tally.py` - walk-forward condition scoreboard grouped by
  symbol, timeframe, event context, regime, route action, setting, return,
  drawdown, and trade count.
- `scripts/run_condition_tally.py` - converts saved walk-forward JSON reports
  into condition tally artifacts.
- `tests/test_llm_optimizer.py` and `tests/test_condition_tally.py` lock the
  core safety and tally behavior.
- `docs/working/cas_forex_llm_optimizer_plan_20260622.md` records the target
  architecture and open-weight model benchmark plan.
- First tally artifact from the corrected D1 walk-forward report:
  `evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
  with `18` windows, `7` routed windows, `11` `NO_TRADE` windows, and
  `normal` event context on all legacy windows.

Honest boundary: this is a guarded research assistant scaffold, not
hallucination prevention proof, not live trading permission, and not a path to
automatic bank/debit/card transfers. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Event-aware condition axis for multi-timeframe RPM routing

Started the next requested switching layer: event-aware routing. CAS FOREX can
now include event context in Condition Lab cells, nested lacunarity keys, and
RPM route keys.

- `cas_forex/event_context.py` - event-context labels and helpers:
  - `normal`
  - `pre_NFP` / `post_NFP`
  - `pre_CPI` / `post_CPI`
  - `pre_FOMC` / `post_FOMC`
  - `pre_RATE_DECISION` / `post_RATE_DECISION`
  - `pre_GDP` / `post_GDP`
  - `pre_UNEMPLOYMENT` / `post_UNEMPLOYMENT`
  - `pre_CENTRAL_BANK_SPEECH` / `post_CENTRAL_BANK_SPEECH`
  - `weekend_gap`, `liquidity_thin`, `conflict_shock`
- `ConditionCell` now carries `event_context`.
- Synthetic CAS-SDG sweeps accept `--event-contexts` and scale synthetic
  volatility by event context, so `conflict_shock` and post-release contexts can
  be stress-tested separately from normal markets.
- Real-data Condition Lab and walk-forward runs can opt into
  `--real-event-source static_macro` / `--event-source static_macro`; this uses
  the static 2026 seed macro calendar as a research label source only.
- Nested lacunarity now defaults to:
  `source -> symbol -> time_scale -> timeframe -> event_context -> regime -> vol_mult -> family`.
- RPM route keys now include `event_context`, so routes learned under `normal`
  conditions are not blindly applied during NFP/FOMC/conflict-style contexts.
- Added tests for macro pre/post windows, manual conflict windows, synthetic
  event-context cells, and event-context walk-forward route keys.

First compact synthetic event-context run:

- command: `python scripts/run_condition_lab.py --source synthetic --symbols NAS100 EUR/USD --settings tsmom_252_500_2_8 range_scalper_24_120 --regimes trend_up range --vol-mults 1.0 --timeframes M15 H1 D1 --event-contexts normal pre_NFP post_NFP conflict_shock --seeds 1 --bars 300 --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 0.5 --rpm-min-return 0.5 --output-dir evidence_runs/event_context_focus`
- cells: `96`
- overall nested-lacunarity gap fraction: `0.9062`
- RPM routes: `1`; `NO_TRADE`: `47`
- only routed condition: synthetic `EUR/USD` `D1` `post_NFP` `trend_up` -> `tsmom_252_500_2_8`
- report: `evidence_runs/event_context_focus/condition-lab-20260622050947-report.json`

First real-data static-macro smoke:

- report: `evidence_runs/event_context_walk_forward_smoke/walk-forward-20260622051001-report.json`
- windows: `8`
- routes: `0`
- `NO_TRADE`: `8`
- readout: adding event context made sparse/untrained macro windows route to
  `NO_TRADE`, which is the conservative behavior we want until event-specific
  evidence exists.

Honest boundary: this is an event-aware route-map scaffold, not a finished
news/conflict trading system. The static 2026 macro calendar is only a seed;
historical macro releases and geopolitical/conflict shock windows still need
provider-backed or curated data. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Strategy lead ledger + analyze/simulate/switch status audit

Added a durable strategy-lead memory so current winning research leads stay in
front while new CAS Forex strategies are explored.

- `strategy_leads.json` - machine-readable ledger of active research leads,
  watchlist strategies, evidence refs, open gates, and deployment status.
- `cas_forex/strategy_ledger.py` - loader/validator that preserves the
  `NOT LICENSED` claim boundary.
- `tests/test_strategy_ledger.py` - regression checks that the active leads
  remain recorded and their evidence refs resolve.
- `docs/working/cas_forex_winning_strategy_ledger_20260622.md` - human-readable
  strategy ledger plus a direct status audit of the analyze/simulate/switch-up
  program.

Current active leads:

- `range_scalper_filtered_fx_d1` - priority 1, `range_scalper_24_120`,
  promoted next for `EUR/USD` and `GBP/USD`, with `AUD/USD` on watchlist and
  `USD/JPY` / `USD/CAD` excluded until condition-specific proof.
- `index_tsmom_252_d1` - priority 2, `tsmom_252_500_2_8`, promoted next for
  `NAS100` and `US30`, but blocked on better index trend/range detection after
  the first D1 walk-forward run stayed `NO_TRADE` on recent index windows.
- `meanrev_trend_filter_fx_d1` - watchlist only; thin and cost-sensitive.

Analyze/simulate/switch-up audit:

- Tried as synthetic CAS-SDG regime simulator.
- Tried as real-data hard switching on daily and H1; switching did not beat the
  best single FX-major strategy.
- Rebuilt as Condition Lab with settings, real slices, CJT regions, nested
  lacunarity, and RPM route/no-trade maps.
- Extended across temporal nested lacunarity (`S1`, `M1`, `H1`, `D1`, `MN1`,
  `Y1`).
- First walk-forward RPM test preserved the range-scalper lead on active future
  windows but remains `NOT_PROMOTED` because route coverage is sparse.

Event/news factoring status:

- Present: `MacroGate` handles static seed `NFP`, `CPI`, `FOMC`, `GDP`,
  `UNEMPLOYMENT`, `CENTRAL_BANK_SPEECH`, and `RATE_DECISION`; CJT macro-shock
  diagnostics route to `LIVE_LOCKED`.
- Not complete: historical backtests do not yet evaluate real macro event
  timing per candle, and conflict/geopolitical shocks are not yet a first-class
  Condition Lab / RPM axis.

Next correct build: add event-context axes (`normal`, `pre_NFP`, `post_NFP`,
`FOMC`, `CPI`, `conflict_shock`, `weekend_gap`, `liquidity_thin`) and train
multi-timeframe/mode RPM routes that can switch setting + timeframe, reduce
risk, or choose `NO_TRADE`. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Walk-forward RPM validation for current profit leads

Added a walk-forward validation layer for the Condition Lab so CAS can train an
RPM route map on one historical window, freeze it, and evaluate only the next
untouched future window.

- `cas_forex/walk_forward.py` - reusable walk-forward route evaluator:
  - splits candles into train/test windows
  - builds real-data Condition Lab cells on the training window only
  - freezes the RPM route table
  - labels the future test window by regime and volatility bucket
  - applies only the exact trained route, otherwise emits `NO_TRADE`
  - uses prior training bars as signal lookback context while allowing trades
    only inside the future test window
  - summarizes routed, active-routed, positive, drawdown, trade-count, and
    research-grade metrics
- `scripts/run_walk_forward_condition_lab.py` - CLI for Yahoo proxy
  walk-forward runs.
- Added tests for walk-forward index ranges, future-condition labeling,
  strategy lookback context, and JSON serialization.

First corrected D1 walk-forward focus run:

- command: `python scripts/run_walk_forward_condition_lab.py --symbols NAS100 US30 EUR/USD GBP/USD AUD/USD --settings tsmom_252_500_2_8 range_scalper_24_120 --timeframes D1 --period 5y --train-bars 756 --test-bars 126 --step-bars 126 --train-segment-bars 252 --train-step-bars 63 --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 0.5 --rpm-min-trades 1 --rpm-max-dd 20 --rpm-min-return 0 --output-dir evidence_runs/walk_forward_condition_lab`
- report: `evidence_runs/walk_forward_condition_lab/walk-forward-20260622044930-report.json`
- chart: `docs/working/cas_forex_walk_forward_rpm_chart_20260622.png`
- windows: `18`
- routed windows: `7`
- active routed windows: `3`
- positive active routed windows: `3 / 3`
- positive routed window rate: `0.4286`
- active routed mean return: `1.2827%`
- routed total return-percent sum: `3.8480%`
- routed max drawdown: `2.2980%`
- total routed trades: `32`
- research grade: `NOT_PROMOTED`

Readout: the corrected walk-forward harness preserved the range-scalper lead
on active future windows (`EUR/USD` and `GBP/USD`) but did not promote it
because route coverage is still sparse and inactive/no-route windows dominate.
`NAS100` and `US30` stayed `NO_TRADE` in this D1 run because the current
real-slice detector labeled the future windows as range and the trained route
map did not find an acceptable index route. This is useful evidence for the
next target: improve condition detection and test broker-grade/intraday data.
Live trading remains `NOT LICENSED`.

## 2026-06-22 - Temporal nested lacunarity across second/minute/hour/day/month/year

Added the user's requested time-axis nesting to the CAS FOREX Condition Lab so
CJT, nested lacunarity, and RPM routing can reason over temporal scale instead
of treating all bars as if they were daily bars.

- `cas_forex/condition_lab.py` now carries `timeframe` and `time_scale` on every
  `ConditionCell`.
- Added canonical CAS timeframe helpers for `S1`, `M1`, `H1`, `D1`, `W1`,
  `MN1`, and `Y1`, plus aliases such as `1m`, `1h`, `1mo`, and `1y`.
- Synthetic CAS-SDG sweeps now accept multiple `--timeframes` and scale
  volatility by approximate bar duration, enabling second/minute/hour/day/month/
  year stress maps.
- Nested lacunarity now defaults to:
  `source -> symbol -> time_scale -> timeframe -> regime -> vol_mult -> family`.
- RPM route keys now include `time_scale` and `timeframe`, so the router can
  choose different settings or `NO_TRADE` for M1 scalping versus D1 swing versus
  MN1/Y1 longer-horizon behavior.
- `scripts/run_condition_lab.py` now supports `--timeframes` and uses Yahoo-safe
  real-data defaults where available. True second bars and native yearly bars
  are explicitly skipped for real-data Yahoo runs until broker tick data or an
  aggregation layer is added.
- Added regression tests for timeframe classification, provider interval
  mapping, synthetic multi-timeframe cell generation, default temporal
  lacunarity keys, and RPM route-key changes.

First compact synthetic temporal run:

- command: `python scripts/run_condition_lab.py --source synthetic --symbols NAS100 --settings tsmom_252_500_2_8 range_scalper_24_120 --regimes trend_up range --vol-mults 1.0 --timeframes S1 M1 H1 D1 MN1 Y1 --seeds 1 --bars 300 --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 0.5 --rpm-min-return 0.5 --output-dir evidence_runs/temporal_lacunarity_focus`
- cells: `24`
- overall nested-lacunarity gap fraction: `0.8750`
- temporal pattern: `S1`, `M1`, and `H1` were `100%` gap in this compact
  two-strategy sweep; `D1`, `MN1`, and `Y1` were `75%` gap.
- RPM routes: `1`; `NO_TRADE`: `11`
- only routed condition: synthetic `NAS100` `Y1` `trend_up` -> `tsmom_252_500_2_8`
- report: `evidence_runs/temporal_lacunarity_focus/condition-lab-20260622044212-report.json`
- chart: `docs/working/cas_forex_temporal_lacunarity_chart_20260622.png`
- verification: `python -m pytest tests -q` -> `239 passed`

Honest read: this is the correct architecture for multi-timeframe CAS routing,
but the first run is a focused stress test, not a live edge. Short timeframes
need broker-grade/tick data, spread/slippage realism, and walk-forward proof
before they can be trusted. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Capital goal planner + low-volatility range-scalper research lead

Added explicit capital-goal math and a Forex-Fury-inspired research strategy
without copying proprietary code or claiming guaranteed returns.

- `cas_forex/capital_plan.py` - converts seed capital and monthly income target
  into required monthly return, feasibility status, notes, and a linked
  `ProfitSweepPolicy`.
- The user's stated range (`$2k-$5k` seed, `$5k-$12k/month` target) requires
  roughly `100%` to `600%` monthly returns, so the planner classifies all four
  corners as `SURVIVAL_RISK`.
- `forecast/strategies.py` now includes `make_low_vol_range_scalper_signal()`:
  a public-pattern range/low-volatility fade inspired by EA descriptions such
  as Forex Fury's published low-volatility/range approach. This is a CAS
  research candidate, not a copy of proprietary set files.
- `scripts/run_real_backtest.py` now supports `--model range_scalper`.
- `condition_lab.py` now includes `range_scalper_24_120` and
  `range_scalper_12_80` setting variants.
- Added tests for the capital planner, linked sweep policy, and range-scalper
  signal behavior.

Forex Fury public-source synthesis checked on 2026-06-22: the official site
describes a customizable MT4/MT5 EA, verified third-party tracking, no fixed
monthly return, 0-7 trades/day, and a range-based method designed for low
volatility, often trading one hour per day and one pair per account. CAS Forex
should test that pattern, not trust the marketing.

Initial research-only runs, 5y daily Yahoo proxy data, `0.05` lots, `1.0`
spread + `1.0` extra cost:

- `range_scalper` on 5 FX majors: portfolio `+$1,572.25`; EUR/USD `+7.41%`,
  GBP/USD `+17.75%`, AUD/USD `+1.69%`, USD/JPY `-9.06%`, USD/CAD `-2.07%`;
  CAS gating improved P&L and lowered avg max DD (`4.88%` vs `6.55%`);
  chain verified; `report.passed=true` as research signal only.
- `range_scalper` on filtered EUR/USD, GBP/USD, AUD/USD: portfolio
  `+$2,686.37`; avg max DD `2.38%`; chain verified; `report.passed=true`
  because CAS lowered drawdown, though raw P&L was higher.

Honest read: this is a second positive research lead alongside index TSMOM.
It is not enough to fund live trading or promise `$5k-$12k/month`. Promote it
to condition-lab and walk-forward testing, then paper proof. Live trading and
provider/bank/card automation remain `NOT LICENSED`.

## 2026-06-22 - CAS condition lab: SDG + real slices + CJT/lacunarity/RPM routing

Added the deeper simulator layer requested by the user: a condition laboratory
that plays strategy settings across synthetic CAS-SDG regimes and real market
windows, then uses CJT regions, nested lacunarity, and RPM prerequisites to
produce a route/no-trade map.

- `cas_forex/condition_lab.py` - reusable condition-lab engine:
  - named strategy-setting registry (`trend_sma`, `breakout`, `meanrev`,
    `tsmom`, `pullback`)
  - deterministic synthetic sampling
  - real-data window slicing with regime + volatility labeling
  - CJT operating-region classification per setting/condition cell
  - nested lacunarity over `source -> symbol -> regime -> vol -> family`
  - RPM route table that selects the best non-gap setting or emits `NO_TRADE`
- `scripts/run_condition_lab.py` - CLI for synthetic, real, or combined sweeps.
- `regime_sim.generate_regime_candles()` is now instrument-aware for
  `NAS100`, `US30`, and `XAU/USD` instead of using FX-scale default prices.
- Added regression coverage for deterministic seeds, index-scale synthetic
  generation, strategy-setting registry, nested lacunarity, and RPM routing.

Focused synthetic run:

- cells: `168`
- overall nested-lacunarity gap fraction: `0.8333`
- RPM routes: `19`; `NO_TRADE`: `23`
- report: `evidence_runs/condition_lab_focus/condition-lab-20260622042700-report.json`

Focused real-slice run:

- cells: `20`
- overall nested-lacunarity gap fraction: `0.1500`
- RPM routes: `5`; `NO_TRADE`: `0`
- top route examples:
  - real `NAS100` range vol `1.0` -> `tsmom_252_500_2_8`
  - real `US30` range vol `0.5` -> `tsmom_126_250_2_10`
  - real `US30` trend_up vol `1.0` -> `tsmom_126_250_2_10`
- report: `evidence_runs/condition_lab_focus/condition-lab-20260622042733-report.json`

Honest read: the simulator now exists and can generate switching hypotheses.
It does not prove live edge. The next step is to add walk-forward splitting so
RPM routes are learned on one window and judged on untouched future windows.
Live trading remains `NOT LICENSED`.

## 2026-06-22 - Strategy edge sprint: index time-series momentum is the first real research lead

Pushed beyond the first generic index smoke tests and added two new research
strategy families for NAS100/US30:

- `forecast/strategies.py` now includes:
  - `make_time_series_momentum_signal()` - daily-bar trend following / TSMOM,
    long-or-flat by default for indices.
  - `make_trend_pullback_signal()` - buys short pullbacks inside a larger trend.
- `scripts/run_real_backtest.py` now supports `--model tsmom` and
  `--model pullback`, with explicit strategy parameters.
- `backtest/engine.py` now recomputes ATR each bar instead of reusing the warmup
  ATR for the whole test, and rounds proposal entry/SL/TP by instrument metadata.
- `verifier/auditor.py` now suppresses all risk-gate failures, not only drawdown
  live locks. This makes `max_open_positions`, exposure, and correlated-exposure
  failures actually block new trades in the backtest path.
- Added regression coverage for the new strategy signals, rolling ATR, and
  non-lock risk suppression.

Research-only results, NAS100 + US30, 5y daily Yahoo proxy data, `0.1` lots,
`1.0` spread + `1.0` extra cost:

- Raw TSMOM 126: `+123.5%` portfolio, but avg max DD `58.6%` - dangerous
  overtrading profile, not promotable.
- TSMOM 126 max1: `+6.8%` portfolio, avg max DD `4.3%`.
- TSMOM 126 max2: `+13.2%` portfolio, avg max DD `7.6%`.
- TSMOM 126 TP10 max2: `+17.2%` portfolio, avg max DD `5.7%`.
- Pullback 126: `+9.1%` portfolio, avg max DD `6.9%`.
- TSMOM 252 with correlated-exposure cap: `+31.6%` portfolio, avg max DD
  `6.8%`; this is the current best controlled research lead.

Chart: `docs/working/cas_forex_strategy_edge_sprint_chart_20260622.png`.

Honest read: this is the first meaningful positive index research signal, but it
is still in-sample, Yahoo proxy data, and daily-bar only. Promote TSMOM 252 to
walk-forward validation and broker-grade bid/ask testing. Do not promote raw
overtrading. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Index/gold instrument metadata + first NAS100/US30/XAU research smoke

Added the first non-FX instrument layer so CAS Forex no longer has to pretend that
indices and gold are currency pairs.

- `cas_forex/instruments.py` - central metadata registry for FX, `NAS100`, `US30`,
  and `XAU/USD`: research movement unit, point value, contract size, default mid,
  Yahoo ticker, and MT5 symbol.
- `schemas/forecast.py` now gets `SUPPORTED_SYMBOLS` and `pip_multiplier()` from
  the registry. Existing FX pip behavior stays compatible; indices/gold now return
  research points.
- `backtest/engine.py` now uses metadata-backed price units, point value per lot,
  and USD notional estimates, including before a position is open.
- `market_data/connector.py` and `scripts/run_real_backtest.py` now map `NAS100`
  -> `^NDX`, `US30` -> `^DJI`, and `XAU/USD` -> `GC=F` for Yahoo proxy data.
- `schemas/order.py` and `broker/mt5_bridge.py` now use registry-backed broker
  symbols such as `XAUUSD`.
- Added regression coverage for NAS100 point P&L, XAU/USD contract point value,
  and non-FX Yahoo/MT5 symbol mappings.

Verification: `python -m pytest tests -q` -> `220 passed`.

First research-only Yahoo proxy runs, using 5y daily data, `0.1` lots, `1.0`
spread + `1.0` extra cost:

- `breakout`, `NAS100 US30 XAU/USD`: portfolio `-$9,833.96`; NAS100 `+0.55%`,
  US30 `+2.44%`, XAU/USD `-101.34%`; chain verified; `report.passed=false`.
- `sma`, `NAS100 US30`: portfolio `-$954.72`; NAS100 `+3.63%`, US30 `-13.18%`;
  chain verified; `report.passed=false`.
- `breakout`, `NAS100 US30`: portfolio `+$299.62`; NAS100 `+0.55%`, US30
  `+2.44%`; chain verified; `report.passed=false` because CAS gating did not
  improve P&L/drawdown versus raw and buy-and-hold massively outperformed
  (`NAS100 +115.08%`, `US30 +52.21%`).

Honest read: indices are now wired and runnable, but the first generic index
strategies are not deployable edges. XAU/USD should be isolated or deprioritized
until it has a separate gold-specific strategy. The next real edge attempt should
encode the owner's 2020 NAS30/NAS100 rules, add trailing/time exits, and run
walk-forward validation with broker-grade bid/ask data. Live trading remains
`NOT LICENSED`.

## 2026-06-21 — Detector tuning + intraday switching: cost drag is the wall, no config beats break-even

Followed the switching test with (A) detector-threshold tuning on daily and (B)
intraday H1. Added detector CLI args (`--er-trend/--detect-window/--hi-vol/--lo-vol/
--shock-z`) to `run_switching_backtest.py`.

(A) Daily er_trend sweep — MORE trend detection = WORSE switching (monotonic):
  er 0.15 -$7,360 | 0.20 -$6,479 | 0.25 -$5,631 | 0.35 -$2,040.
  Every "trend" call routes to breakout/trend, which lose on daily, so seeing more
  trends destroys value. Can't tune a daily edge into existence; meanrev_tf (~+$9) wins.

(B) Intraday H1 (real 2y, ~12,300 bars/pair, cost 1.5p): EVERYTHING loses —
  trend_sma -$10,404 | breakout -$6,196 | meanrev -$4,862 | SWITCH -$4,715 |
  meanrev_tf -$4,123 (best). SWITCH again ~= meanrev (detector still 91.6% range at H1).
  The killer is COST DRAG: meanrev_tf made +$3.72 on daily (286 trades) but loses
  -$4,123 on H1 (4,654 trades) — same strategy, ~16x more trades x cost. ~85% of the
  H1 loss is trading cost.

Synthesis after a thorough search (4 strategy families, 2 forecasters incl. Chronos,
regime sim, detection, hard switching, detector tuning, daily + H1): NO configuration
produces a cost-surviving edge. The ceiling is daily mean-rev+filter at literal
break-even (+$3.72), which evaporates at realistic costs. The wall is cost drag eating
thin edges, worse at higher frequency.

Genuinely untested (tied to user's real 2020 success): the user's OWN discretionary
entry rules encoded, and NAS30 / index instruments (indices trend more strongly than FX
majors; we have only tested FX majors, which mean-revert). Live trading remains NOT
LICENSED. 217 tests pass.

## 2026-06-21 — Regime detector + switching on REAL data: switching does NOT beat the best single strategy (on daily)

Built the live regime detector + RPM switching and tested it on real 5y daily data
against every single strategy.

- `forecast/strategies.py` — `make_sma_trend_signal` (composable SMA, routable).
- `regime_sim.py` — `detect_regime` (Kaufman efficiency ratio + vol-vs-baseline +
  shock z-score + vol-of-vol), `DEFAULT_ROUTING` (sim's RPM seed), and
  `make_regime_switching_signal` (detect each bar -> route -> sit out on lacuna).
- `scripts/run_switching_backtest.py` — SWITCH vs each single strategy on real data.

Result (real 5y daily, cost 1.5p, $50k):
  trend_sma  -$15,055 | meanrev -$729 | meanrev_tf +$3.72 | breakout -$8,144 |
  SWITCH     -$2,048
Best = meanrev_tf (+$3.72). SWITCH did NOT beat it (-$2,048).

Why (the mechanism): the detector classifies **97% of real daily bars as "range"**,
so SWITCH ~= plain meanrev, plus rare trend/breakout detours that lost money. Daily
bars are too coarse/homogeneous for hard switching to add value — there isn't enough
regime variety, and the trend calls aren't reliable/timely on daily.

Honest read: the regime-switching MACHINERY works end-to-end, but on daily data the
useful "regime intelligence" is the lightweight trend FILTER already baked into
meanrev_tf (a soft regime-awareness), not a separate hard switch. Switching's real
shot is INTRADAY, where regimes vary and change more (ties to the multi-timeframe
requirement). meanrev_tf remains the incumbent (break-even). NOT LICENSED. 217 tests pass.

## 2026-06-21 — Strategy-condition simulator (CAS-SDG for regimes): CJT + nested lacunarity + RPM routing

Built the user's idea: a market-REGIME simulator that plays every strategy across
every condition and uses the CAS machinery to map where edge lives. Working v0.

- `cas_forex/regime_sim.py` — seeded synthetic OHLC generator for 7 regimes
  (trend_up/down, range, high_vol, low_vol, vol_cluster, shock); CJT operating-region
  classifier (cutoff/active/saturation/breakdown + gain beta); nested lacunarity
  (gap map across strategy x regime x volatility); best-strategy-per-regime (RPM seed).
- `scripts/run_strategy_simulator.py` — sweeps strategies x regimes x vol x seeds,
  prints the matrix + nested lacunarity + RPM routing seed, writes a JSON report.

First run (4 strategies x 7 regimes x 3 vol x 5 seeds, cost 1.5p) cleanly recovers
known structure — which validates the simulator:
- Trend/breakout WIN in trends (breakout +13.2%/+12.2% up/down) and LOSE in range.
- Mean-reversion WINS in range (+0.9%) and loses in trends.
- No single strategy wins everywhere (overall lacunarity 0.58 — 58% of cells are gaps).

RPM routing seed (regime -> best validated strategy):
  trend_up/down/high_vol -> breakout; range/shock -> meanrev; low_vol -> trend_sma;
  vol_cluster -> NONE (honest lacuna, do not trade).

Reframe (the productive insight): the edge — if any — is in REGIME DETECTION +
SWITCHING, not one magic strategy. The honest next frontier is detecting the live
regime reliably on REAL data and validating the routing out-of-sample (the RPM
prerequisite question). Synthetic regimes characterize behavior, not live edge.
Live trading remains NOT LICENSED. 217 tests pass.

## 2026-06-21 — Realistic-cost test: the thin edge does NOT survive normal costs

Added a configurable round-trip cost knob (`extra_cost_pips` = commission + slippage
on top of spread; `--spread-pips` / `--extra-cost-pips`) and swept the trend-filtered
mean-reversion (the only positive strategy) across realistic cost levels.

5y portfolio P&L (gated, $50k):
- 1.0 pip total cost (very optimistic):  +$91   PASS
- 1.5 pips (optimistic ECN+commission):  +$28   PASS
- 2.0 pips (normal retail):              -$31   FAIL
- 2.5 pips (standard account):           -$95   FAIL

Verdict: the edge breaks even at ~1.5-2.0 pips and is negative at realistic retail
all-in costs (majors typically 1.5-2.5 pips spread+commission+slippage). So the
trend-filtered mean-reversion is NOT a deployable, cost-surviving strategy — it is
positive only under optimistic cost assumptions, and even then ~$0 over 5 years on
$50k. This is the honest make-or-break result: no deployable edge yet across 4
strategy families tested (trend SMA, Chronos, mean-rev, mean-rev+filter).

Implication for the $5-12k/month target: not reachable. Best strategy made ~$0 over
5y on $50k; $5-12k/month on a $2-5k seed is +100-600%/month (martingale-blowup
territory), not a real return. A realistic 2-5%/month would need a ~$100-250k account
to clear $5k/month — and even that is exceptional and not guaranteed.

Added/changed:
- `backtest/engine.py` — `extra_cost_pips` (round-trip commission+slippage), deducted
  with spread on close. Default 0.0 (tests unchanged).
- `scripts/run_real_backtest.py` — `--spread-pips`, `--extra-cost-pips`.
- 217 tests pass.

## 2026-06-21 — Strategy pivot: mean-reversion + trend filter = first POSITIVE backtest (thin)

Acted on the research insight that FX majors range 70-80% of the time, so our
trend-follower was the wrong strategy class (it lost most on the most mean-reverting
pair, USD/CAD). Added rule-based strategies + user-controllable risk budget and
re-ran the same real-data harness (5y daily, 5 majors).

Progression (portfolio P&L on $50k, gated):
- Trend SMA:               -$15,098   (avg max DD 41%)
- Chronos:                 -$15,574   (avg max DD 49%)
- Mean-reversion (z-fade):    -$523    (avg max DD 6%)   <- ~30x less bad, ~break-even
- Mean-reversion + trend filter: +$105.62 (avg max DD 3.5%)  <- FIRST passed=True

The trend filter (skip fades that fight a >150bps move over 60 bars — a theory-backed
fix, not curve-fitting) made it net positive: 3/5 pairs clearly positive (EUR/USD
+1.56%, GBP/USD +3.47%, AUD/USD +3.26%), beating buy-and-hold on every ranging pair.
Only USD/CAD (-6.1%) still loses (it trended up). Evidence chains verified.

CRITICAL honesty caveat — the edge is razor-thin and NOT yet deployable:
- +$105.62 over 286 gated trades = ~$0.37/trade = ~0.74 pip/trade edge.
- The backtest already charges a 1-pip spread; ONE more pip of real cost
  (commission + slippage) is ~$143 across 286 trades and FLIPS IT NEGATIVE.
- So this is positive-after-1-pip-spread, NOT positive-after-realistic-costs.
- One parameter set, one dataset, in-sample. Needs out-of-sample / walk-forward
  validation + realistic cost modeling before ANY capital. report.passed is a
  research signal, not a license. Live trading remains NOT LICENSED.

Real progress nonetheless: we moved from "definitely loses" to "plausibly
break-even with low drawdown," and confirmed the lever is strategy class + regime
filter, not forecaster sophistication.

Added/changed:
- `forecast/strategies.py` — mean-reversion (z-fade, optional trend filter) and
  Donchian breakout signals; no martingale / grid / no-stop modes (real money).
- `backtest/engine.py` — signals may set ATR stop/target multiples; risk limits now
  all sourced from config (single source of truth for the risk budget).
- `scripts/run_real_backtest.py` — `--model meanrev|breakout`, mean-rev params, and
  RISK BUDGET flags (`--starting-balance --position-lots --risk-per-trade-pct
  --max-daily-dd --max-weekly-dd --max-open-positions --max-position-lots`).
- 217 tests pass throughout.

## 2026-06-21 — Chronos-Bolt re-run confirms NO edge across TWO forecasters

Wired Amazon Chronos-Bolt (`forecast/chronos_signal.py`) as a pluggable directional
signal and re-ran the exact same real-data harness (5y daily Yahoo, 5 majors), with
SL/TP held identical so only the forecaster changed (SMA → ML model). Evidence chain
verified: 19,660 hash-chained packets across 5 files, all re-verified.

Result (REAL): Chronos also **loses** — portfolio **-$15,574 gated / -$17,007 raw**
on $50k, vs the SMA run's -$15,098 / -$16,296. Per pair (gated%): EUR/USD -22.0,
GBP/USD -81.1, USD/JPY +38.6, AUD/USD -101.6 (account wiped), USD/CAD +10.2.
Buy-and-hold beat the strategy on every pair, including the two "winners" (USD/JPY
b&h +46.3 vs +38.6; USD/CAD b&h +14.6 vs +10.2).

Decisive read: swapping a simple moving average for a real ML forecaster moved the
needle by ~$0.5k on -$15k — i.e. **the edge problem is NOT a forecaster-quality
problem.** Two structurally different models both lose on majors over 5 years.

Consistent finding across BOTH models: the **CAS gating layer reduces loss and
drawdown** (gated beat raw on P&L and avg max DD in both runs; suppressed 1,118
Chronos trades) and the new blow-up guard prevented crashes when the ungated AUD/USD
and GBP/USD arms hit ~100% loss / ~100% drawdown. Honest nuance: on the two
profitable pairs the gates slightly REDUCED gains (USD/CAD gated +10.2 vs raw +19.5)
— the gates cut both tails; net-positive only because losers dominate.

Strategic implication: the validated, sellable asset is the safety/audit chassis, not
a profitable bot. A trading edge remains OPEN and is the hard, unsolved part; next
lever is a different strategy class or timeframe (per the user multi-timeframe
requirement), NOT a bigger model. Live trading remains NOT LICENSED.

Added/changed:
- `forecast/chronos_signal.py` — cached CPU Chronos-Bolt → (Direction, confidence).
- `backtest/engine.py` — optional `signal_fn` hook (SMA default unchanged); blow-up
  guard (stop trading when balance <= 0; clamp risk_per_trade_pct at 100%).
- `scripts/run_real_backtest.py` — `--model {sma,chronos}`.
- Artifacts: `evidence_runs/real_backtest/real-chronos-20260622003352-report.json`.
- 217 tests pass throughout.

## 2026-06-21 — First REAL-data comparative backtest: safety layer works, strategy has NO edge

Ran the first backtest on REAL market data instead of synthetic candles. Pulled 5
years of daily candles from Yahoo Finance (1,300 bars/pair, 2021-06-22 → 2026-06-22,
no API key, no GPU) for EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD and ran the full
CAS Forex pipeline three ways: `cas_gated` (SMA proposals through the 5-gate auditor),
`raw_model` (same proposals, gates removed), and `buy_hold` / `no_trade` baselines.

Result (REAL, evidence-chain verified): the built-in SMA5/20/50 daily strategy **LOSES
money** with or without CAS gating — portfolio P&L **-$15,097.88 gated vs -$16,296.32
raw** on $50,000 starting capital (5 × $10k), avg max drawdown 41.5% gated / 46.0% raw.
Buy-and-hold beat the strategy on most pairs (e.g. USD/JPY b&h +46.3% vs gated +9.3%).

Honest read:
- The **CAS safety/gating layer does its job**: it suppressed 695 trades, lost ~$1,198
  (~7.4%) less than the ungated arm, and lowered average max drawdown (41.5% vs 46.0%).
  It reduces damage — it cannot turn a losing strategy into a winning one.
- The **trading edge does not exist** with the current model. `report.passed = False`
  (no positive edge vs no-trade). This confirms live trading SHOULD remain NOT LICENSED:
  trading this model live would lose money.
- Evidence is real and verifiable: 13,554 hash-chained Evidence Packets across 5 files,
  all chains independently re-verified. 217 tests still pass (additive change only).

Next lever for an actual edge (in priority order): wire a real forecaster (Chronos stub
at `forecast/models.py:112`, or a TimeGPT key), then re-run this exact harness; the
strategy — not the safety chassis — is the bottleneck.

Added:
- `scripts/run_real_backtest.py` — real-data (Yahoo) comparative backtest:
  cas_gated vs raw_model vs buy_hold vs no_trade, writes a real BacktestEvidenceReport
  + verifiable hash-chain, with an explicit research-signal (not license) pass criterion.
- Run artifact: `evidence_runs/real_backtest/real-20260621234945-report.json`.

Known caveat (follow-up): the macro gate is evaluated at wall-clock now, not at the
candle's historical timestamp, so macro blackouts are effectively inert in backtests
(`backtest/engine.py` builds the snapshot with `timestamp=utc_now()`).

## 2026-06-19 — Closed-book KWIK hallucination probe: measured ceiling, NOT LICENSED

Ran the decisive pre-answer hidden-state hallucination experiment in the one framing where
text controls are structurally weak — closed-book "knows-what-it-knows" (TriviaQA no-context,
hidden state captured at the last prompt token before any answer is emitted, label = did the
model's own greedy answer match). This is the literature SOTA direction (SAPLMA / semantic
entropy) and the only honest route to a real +0.15 margin.

Result (REAL, leakage-safe, N=2500 each): the framing **works** — residual signal climbed off
the chance floor (grounded 0.45 → KWIK 0.68), proving the hidden state carries genuine
text-independent "do I know this" information. But it **plateaus below the license gate**:
hidden BA ≈ 0.75, margin ≈ +0.12 over text, residual 0.68 — short of +0.15 / 0.75. The wall is
flat: 7B → 14B moved the margin +0.000, and a nonlinear MLP + layer ensemble land on the same
~0.75. This matches the published ceiling (~0.7–0.85 AUROC) for pre-answer hidden-state probes.

Then, per user request, COUPLED the hidden-state probe with semantic entropy (10× sampling on
14B, leakage-safe stacking). Result: coupled BA 0.7345 vs hidden-only 0.732 — a +0.002 gain. The
two signals are **redundant, not complementary** (the 14B is often confidently wrong: mean
entropy 0.379 nats), so entropy adds almost nothing. Held-out generalization flipped to PASS
(0.757), proving an information ceiling rather than overfitting; floor/margin/residual still fail.

Verdict: hallucination detection remains **OPEN / NOT LICENSED** at the specified bars — now a
*measured* ceiling confirmed from five independent angles (framing, scale, readout, probe,
method-coupling), not an untested assumption. No fabrication.

Added:
- `closedbook_kwik_capture.py` — KWIK capture (last-token + mean-pool hidden, greedy label).
- `lic_eval_closedbook.py` — leakage-safe gate (readout×layer selection, residual, held-out,
  selection-aware 1000-perm).
- `kwik_enhanced_probe.py` — ceiling check (ensemble + MLP) confirming the plateau.
- `kwik_semantic_entropy.py` — batched 10× sampling + discrete semantic entropy.
- `lic_eval_coupled.py` — coupled (hidden + semantic entropy) leakage-safe gate.
- `docs/working/hallucination_kwik_ceiling_findings_20260619.md` — full findings + A/B/C fork.

## 2026-06-17 — CJT/PCBA Tier-B/C research code + honest gates

Built the research-tier and gated CJT/PCBA work: real, runnable code plus honest
readiness gates. No higher-authority claim was flipped to LICENSED — those need
GPU traces, external red-team, or legal review (all still OPEN / NOT LICENSED).

Added:
- `cas_forex/cjt_compiler.py` (B) — compiles one `CJT<>` statement: runs embedded
  CAS literals through the real CAS compiler bridge and emits E-CJT-001..008
  validation findings. `is_production_cjt_syntax_enabled()` stays False.
- `cas_forex/cjt_analysis.py` (B) — analytical β (large/small-signal), gm, and
  operating-region classification via Fisher-Rao geometry. `validated` is always
  False — analytical estimate, not measured against real traces (Q-002).
- `cas_forex/ccb_designs.py` (B) — the 5 Cognitive Circuit Boards (CSB, COB,
  CDAB, CMB, CPMB) encoded as executable `CrcCircuit` specs that pass CRC
  ERROR-free. Well-formed designs, NOT runtime-safety guarantees.
- `cas_forex/ccb_readiness.py` (C) — readiness gates that report each CCB safety
  claim, governance proof, and the CjtPredictionHead as NOT LICENSED / OPEN with
  required external evidence missing.
- `docs/working/cjt_w0_labeled_readout_experiment_design_20260617.md` (C) —
  design for the failed-Qwen-W0-gate follow-up (CJT labels + controls + pass
  criteria). Research design only; not run.
- `tests/test_cjt_tier_bc.py` — 17 tests incl. negative claim-boundary proofs.

Tests: `python -m pytest tests -q` → 217 passed (zero regressions).

## 2026-06-17 — CJT/PCBA Tier-A evidence + visualization layer

Built the buildable-now ("Tier A") CJT/PCBA stack recommended in
`docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`. All
additive, evidence-only, claim-bounded (no path to live trading or broker
ACCEPT).

Added:
- `cas_forex/cas_state_utils.py` — surface parser for CAS state literals
  (`^k^D_{Fd}|R`): Noetic/Domain/Drive/Register extraction, domain precedence,
  involution-pair check. Not the compiler — surface only.
- `cas_forex/cjt_diagnostics.py` (A-1) — maps forex conditions (weak edge,
  forecast disagreement, single-model overconfidence, macro shock, drawdown,
  broker mismatch, beta drift) into `CjtCircuitDiagnostic` sidecars with
  claim-ceiling routing (SUPPRESS / FLAG_FOR_HUMAN_REVIEW / LIVE_LOCKED).
- `cas_forex/crc_linter.py` (A-3) — Cognitive Rule Check: static design-time
  linter (CRC-001..008) over CJT/via/fuse circuit specs. Flags invalid bias
  domain, short circuits, reverse-flow bypass, push-pull gain divergence,
  cascade depth, gain firewall, and fuse-after-protected. Static only; a
  well-formed circuit is NOT a runtime-safety guarantee.
- `cas_forex/cjt_circuit_view.py` (A-2) — deterministic markdown/ASCII renderer
  for diagnostics and CRC reports (Cause→[Bias]→Effect, region, β, gate).
- `cas_forex/cjt_differential.py` (A-4) — differential-pair matched-control via
  Fisher-Rao geodesic distance on the open simplex; emits FLAG_FOR_HUMAN_REVIEW
  above threshold. Heuristic, not proof.
- `tests/test_cjt_pcba_tier_a.py` — 23 tests covering all of the above.

Tests: `python -m pytest tests -q` → 200 passed (zero regressions).
